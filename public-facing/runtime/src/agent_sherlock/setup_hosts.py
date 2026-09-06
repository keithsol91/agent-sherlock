"""Pure host-path and configuration helpers for the local installer."""

from __future__ import annotations

import json
from pathlib import Path
import tomllib


_SERVER_NAME = "agent-sherlock"


def _check_host(host: str) -> None:
    if host not in ("claude-code", "codex"):
        raise ValueError("Host must be claude-code or codex.")


def host_locations(
    host: str,
    scope: str,
    project: Path,
    home: Path,
    codex_home: Path | None = None,
) -> tuple[Path, Path]:
    """Return the config file and skills directory without touching the disk.

    The caller supplies any CODEX_HOME override. Codex skills use .agents,
    independently of that override. Claude's custom configuration directory
    is handled by the caller rather than inferred from the process environment.
    """
    _check_host(host)
    if scope not in ("user", "project"):
        raise ValueError("Scope must be user or project.")
    if host == "claude-code":
        if scope == "project":
            return project / ".mcp.json", project / ".claude" / "skills"
        return home / ".claude.json", home / ".claude" / "skills"
    if scope == "project":
        return project / ".codex" / "config.toml", project / ".agents" / "skills"
    config_root = codex_home if codex_home is not None else home / ".codex"
    return config_root / "config.toml", home / ".agents" / "skills"


def _validate_entry(entry: dict) -> None:
    if (
        not isinstance(entry, dict)
        or not set(entry).issubset({"command", "args", "env"})
        or not isinstance(entry.get("command"), str)
        or not entry["command"]
        or not isinstance(entry.get("args"), list)
        or not all(isinstance(arg, str) for arg in entry["args"])
    ):
        raise ValueError("Sherlock's server entry needs a command and a list of string arguments.")
    if "env" in entry and (
        not isinstance(entry["env"], dict)
        or not all(isinstance(key, str) and isinstance(value, str) for key, value in entry["env"].items())
    ):
        raise ValueError("Sherlock's environment settings must contain string names and values.")
    strings = [entry["command"], *entry["args"]]
    for key, value in entry.get("env", {}).items():
        strings.extend((key, value))
    try:
        for value in strings:
            value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("Sherlock's server entry contains invalid Unicode.") from None


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON setting.")
        result[key] = value
    return result


def _invalid_json_constant(value: str) -> None:
    raise ValueError("Invalid JSON constant.")


def _merge_claude(existing_text: str | None, entry: dict) -> str:
    try:
        config = {} if existing_text is None else json.loads(
            existing_text, object_pairs_hook=_unique_object, parse_constant=_invalid_json_constant
        )
    except (ValueError, TypeError, RecursionError):
        raise ValueError("Claude Code configuration is invalid JSON or contains duplicate settings.") from None
    if not isinstance(config, dict) or not isinstance(config.get("mcpServers", {}), dict):
        raise ValueError("Claude Code configuration and mcpServers must be JSON objects.")
    servers = config.get("mcpServers", {})
    desired = {"type": "stdio", **entry}
    if _SERVER_NAME in servers:
        current = servers[_SERVER_NAME]
        if isinstance(current, dict) and {"type": "stdio", **current} == desired:
            return existing_text
        raise ValueError("Claude Code already has different agent-sherlock settings; review them before installing.")
    config.setdefault("mcpServers", {})[_SERVER_NAME] = desired
    return json.dumps(config, ensure_ascii=False, indent=2) + "\n"


def _toml_string(value: str) -> str:
    # JSON escaping is also valid for TOML basic strings, with DEL additionally
    # escaped. Keep Unicode literal to avoid JSON's surrogate-pair escapes.
    return json.dumps(value, ensure_ascii=False).replace("\x7f", "\\u007f")


def _merge_codex(existing_text: str | None, entry: dict) -> str:
    original = "" if existing_text is None else existing_text
    try:
        config = tomllib.loads(original)
    except (ValueError, TypeError, RecursionError):
        raise ValueError("Codex configuration is invalid TOML or contains duplicate settings.") from None
    servers = config.get("mcp_servers", {})
    if not isinstance(servers, dict):
        raise ValueError("Codex mcp_servers must be a TOML table.")
    if _SERVER_NAME in servers:
        if servers[_SERVER_NAME] == entry:
            return original
        raise ValueError("Codex already has different agent-sherlock settings; review them before installing.")

    lines = [
        "[mcp_servers.agent-sherlock]",
        f"command = {_toml_string(entry['command'])}",
        "args = [" + ", ".join(_toml_string(arg) for arg in entry["args"]) + "]",
    ]
    if "env" in entry:
        pairs = ", ".join(f"{_toml_string(key)} = {_toml_string(value)}" for key, value in entry["env"].items())
        lines.append("env = {" + pairs + "}")
    separator = "" if not original else "\n" if original.endswith("\n") else "\n\n"
    merged = original + separator + "\n".join(lines) + "\n"
    # Inline tables can prevent adding a child table. Validate the whole result
    # before returning anything to the installer; never rewrite existing text.
    try:
        tomllib.loads(merged)
    except (ValueError, RecursionError):
        raise ValueError("Codex configuration cannot safely accept a new agent-sherlock table; review its mcp_servers layout.") from None
    return merged


def merge_config(host: str, existing_text: str | None, entry: dict) -> str:
    """Add Sherlock only if absent, returning unchanged text for a matching entry.

    This function neither reads nor writes files. Invalid configurations and
    existing conflicting registrations fail without including setting values.
    """
    _check_host(host)
    _validate_entry(entry)
    if existing_text is not None and not isinstance(existing_text, str):
        raise ValueError("Existing host configuration must be text.")
    if host == "claude-code":
        return _merge_claude(existing_text, entry)
    return _merge_codex(existing_text, entry)
