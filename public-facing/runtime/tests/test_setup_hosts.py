import copy
import json
from pathlib import Path, PureWindowsPath
import tomllib

import pytest

from agent_sherlock.setup_hosts import host_locations, merge_config


@pytest.fixture
def entry():
    return {"command": "/local/Sherlock/.venv/bin/python", "args": ["-m", "agent_sherlock", "serve"]}


@pytest.mark.parametrize(
    "host,scope,config,skills",
    [
        ("claude-code", "user", "/fictional-home/.claude.json", "/fictional-home/.claude/skills"),
        ("claude-code", "project", "/project/.mcp.json", "/project/.claude/skills"),
        ("codex", "user", "/fictional-home/.codex/config.toml", "/fictional-home/.agents/skills"),
        ("codex", "project", "/project/.codex/config.toml", "/project/.agents/skills"),
    ],
)
def test_host_locations(host, scope, config, skills):
    assert host_locations(host, scope, Path("/project"), Path("/fictional-home")) == (Path(config), Path(skills))


def test_codex_home_override_only_changes_user_configuration():
    project, home, override = Path("/project"), Path("/fictional-home"), Path("/custom/codex")
    assert host_locations("codex", "user", project, home, override) == (
        override / "config.toml", home / ".agents/skills"
    )
    assert host_locations("codex", "project", project, home, override) == (
        project / ".codex/config.toml", project / ".agents/skills"
    )
    assert host_locations("claude-code", "user", project, home, override) == (
        home / ".claude.json", home / ".claude/skills"
    )


def test_locations_do_not_read_environment_or_create_directories(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "ignored"))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "also-ignored"))
    home, project = tmp_path / "home", tmp_path / "project"
    assert host_locations("codex", "user", project, home)[0] == home / ".codex/config.toml"
    assert host_locations("claude-code", "user", project, home)[0] == home / ".claude.json"
    assert list(tmp_path.iterdir()) == []


def test_windows_locations_preserve_path_semantics():
    project, home = PureWindowsPath(r"C:\Projects\Sherlock Demo"), PureWindowsPath(r"C:\Users\Zoë")
    override = PureWindowsPath(r"D:\Codex Config")
    assert host_locations("codex", "user", project, home, override) == (
        override / "config.toml", home / ".agents" / "skills"
    )
    assert host_locations("claude-code", "project", project, home) == (
        project / ".mcp.json", project / ".claude" / "skills"
    )


@pytest.mark.parametrize("host,scope", [("unknown", "user"), ("codex", "local"), ("claude", "project")])
def test_invalid_host_or_scope(host, scope):
    with pytest.raises(ValueError):
        host_locations(host, scope, Path("/project"), Path("/home/test"))


def test_claude_adds_stdio_and_preserves_other_settings(entry):
    previous = {"theme": "dark", "projects": {"/demo": {"hasTrustDialogAccepted": True}},
                "mcpServers": {"fictional-demo": {"type": "http", "url": "https://example.invalid/mcp"}}}
    merged = json.loads(merge_config("claude-code", json.dumps(previous), entry))
    assert merged.pop("mcpServers") == {
        **previous["mcpServers"], "agent-sherlock": {"type": "stdio", **entry}
    }
    assert merged == {key: value for key, value in previous.items() if key != "mcpServers"}


@pytest.mark.parametrize("explicit_type", [False, True])
def test_claude_matching_entry_returns_original_formatting(entry, explicit_type):
    current = {**entry, **({"type": "stdio"} if explicit_type else {})}
    original = "\n" + json.dumps({"mcpServers": {"agent-sherlock": current}}, separators=(",", ":")) + "\n\n"
    assert merge_config("claude-code", original, entry) == original


@pytest.mark.parametrize("host", ["claude-code", "codex"])
def test_new_config_round_trip_and_idempotence_do_not_mutate_entry(host, entry):
    entry["env"] = {"SHERLOCK_PROFILE": "fictional-demo"}
    before = copy.deepcopy(entry)
    merged = merge_config(host, None, entry)
    parsed = json.loads(merged) if host == "claude-code" else tomllib.loads(merged)
    expected = {"type": "stdio", **entry} if host == "claude-code" else entry
    section = "mcpServers" if host == "claude-code" else "mcp_servers"
    assert parsed[section]["agent-sherlock"] == expected
    assert merge_config(host, merged, entry) == merged
    assert entry == before


@pytest.mark.parametrize("ending", ["", "\n", "\r\n"])
def test_codex_keeps_original_text_and_comments_exactly(entry, ending):
    original = '# Local preference\nmodel = "example-model"\n\n[mcp_servers.fictional]\ncommand = "demo" # keep this' + ending
    merged = merge_config("codex", original, entry)
    assert merged.startswith(original)
    parsed = tomllib.loads(merged)
    assert parsed["model"] == "example-model"
    assert parsed["mcp_servers"] == {"fictional": {"command": "demo"}, "agent-sherlock": entry}


def test_codex_matching_alternate_toml_layout_returns_identical_text(entry):
    original = '''# Preserve single quotes and spacing.
[mcp_servers.'agent-sherlock']
args = ['-m', 'agent_sherlock', 'serve']
command = '/local/Sherlock/.venv/bin/python'
'''
    assert merge_config("codex", original, entry) == original


@pytest.mark.parametrize("host", ["claude-code", "codex"])
def test_windows_unicode_quotes_and_control_characters_round_trip(host):
    entry = {
        "command": r'C:\Users\Zoë\Sherlock 🕵\Scripts\python.exe',
        "args": ["-m", "agent_sherlock", "serve", 'quote" slash\\ newline\n tab\t \x00\x7f'],
        "env": {'dot.key " 🕵': "line\n\b\f\r\t\\\x1f\x7f é"},
    }
    merged = merge_config(host, None, entry)
    parsed = json.loads(merged) if host == "claude-code" else tomllib.loads(merged)
    section = "mcpServers" if host == "claude-code" else "mcp_servers"
    actual = parsed[section]["agent-sherlock"]
    if host == "claude-code":
        assert actual.pop("type") == "stdio"
    assert actual == entry


@pytest.mark.parametrize("host", ["claude-code", "codex"])
@pytest.mark.parametrize("change", ["command", "args", "env", "extra"])
def test_conflicting_sherlock_settings_fail_without_exposing_values(host, entry, change):
    other = copy.deepcopy(entry)
    secret = "fictional-private-marker"
    other[change] = {"TOKEN": secret} if change == "env" else [secret] if change == "args" else secret
    if host == "claude-code":
        original = json.dumps({"mcpServers": {"agent-sherlock": other}})
    else:
        original = merge_config("codex", None, entry)
        if change == "extra":
            original += f'extra = "{secret}"\n'
        else:
            original = merge_config("codex", None, other)
    with pytest.raises(ValueError, match="already has different agent-sherlock settings") as caught:
        merge_config(host, original, entry)
    assert secret not in str(caught.value)


@pytest.mark.parametrize("original", [
    "", "{broken private-marker", "[]", '{"mcpServers":[]}',
    '{"mcpServers":{"agent-sherlock":null}}',
    '{"private-marker":1,"private-marker":2}',
    '{"mcpServers":{"fictional":{"command":"a","command":"b"}}}',
    '{"preference":NaN}', '{"preference":Infinity}',
])
def test_malformed_or_duplicate_claude_config_is_rejected(entry, original):
    with pytest.raises(ValueError) as caught:
        merge_config("claude-code", original, entry)
    assert "private-marker" not in str(caught.value)


@pytest.mark.parametrize("original", [
    'private-marker = "unterminated', 'private-marker = 1\nprivate-marker = 2',
    'mcp_servers = []', 'mcp_servers = "private-marker"',
    '[mcp_servers.agent-sherlock]\n[mcp_servers.agent-sherlock]',
    '[mcp_servers]\nagent-sherlock = "private-marker"',
])
def test_malformed_or_duplicate_codex_config_is_rejected(entry, original):
    with pytest.raises(ValueError) as caught:
        merge_config("codex", original, entry)
    assert "private-marker" not in str(caught.value)


def test_codex_inline_parent_table_cannot_be_rewritten(entry):
    original = 'mcp_servers = { fictional = { command = "demo" } }\n'
    with pytest.raises(ValueError, match="cannot safely accept"):
        merge_config("codex", original, entry)


@pytest.mark.parametrize("host", ["claude-code", "codex"])
@pytest.mark.parametrize("bad_entry", [
    {}, {"command": "", "args": []}, {"command": 3, "args": []},
    {"command": "demo", "args": "serve"}, {"command": "demo", "args": [3]},
    {"command": "demo", "args": [], "env": []},
    {"command": "demo", "args": [], "env": {"TOKEN": 4}},
    {"command": "demo", "args": [], "unexpected": "private-marker"},
    {"command": "demo\ud800", "args": []},
])
def test_invalid_entries_fail_cleanly(host, bad_entry):
    with pytest.raises(ValueError) as caught:
        merge_config(host, None, bad_entry)
    assert "private-marker" not in str(caught.value)


def test_merge_rejects_unknown_host(entry):
    with pytest.raises(ValueError, match="Host must be"):
        merge_config("unknown", None, entry)
