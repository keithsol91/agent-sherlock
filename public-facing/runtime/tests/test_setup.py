"""Installer boundaries use only disposable projects, settings, and software."""
import json
import os
from pathlib import Path
import sys

import pytest

from agent_sherlock import setup, setup_check
from agent_sherlock.cli import main


@pytest.fixture
def options(tmp_path):
    source = tmp_path / "download" / "public-facing"
    code = source / "runtime/src/agent_sherlock"
    code.mkdir(parents=True)
    (code / "__main__.py").write_text("# Fictional installer fixture\n")
    for name in ("pyproject.toml", "uv.lock", "README.md"):
        (source / "runtime" / name).write_text("Fictional installer fixture\n")
    for name in setup.SKILLS:
        directory = source / "skills" / name / "references"
        directory.mkdir(parents=True)
        (directory.parent / "SKILL.md").write_text("# Fictional skill\n[Guide](references/guide.md)\n")
        (directory / "guide.md").write_text("Fictional guide.\n")
    # These files are not product files and must never enter the managed copy.
    (source / "runtime/.env").write_text("fictional private configuration")
    (source / "runtime/cases.sqlite3").write_text("fictional case data")
    project = tmp_path / "project with spaces"
    project.mkdir()
    return dict(host="claude-code", scope="project", source=source, project=project,
                home=tmp_path / "fake user", data_dir=tmp_path / "private data",
                install_dir=tmp_path / "installed software", uv_command=sys.executable)


@pytest.fixture
def local_checks(monkeypatch):
    calls = []

    def sync(plan):
        calls.append("sync")
        plan.python.parent.mkdir(parents=True, exist_ok=True)
        plan.python.write_text("fictional interpreter; never executed")

    async def verify(python):
        calls.append("verify")
        assert Path(python).is_file()
        return {"passed": True, "tools_discovered": 25, "case_round_trip": True,
                "restart_persistence": True, "provider_calls": 0}

    monkeypatch.setattr(setup, "_sync_runtime", sync)
    monkeypatch.setattr(setup_check, "verify_runtime", verify)
    return calls


def test_preview_does_not_write_or_inherit_provider_settings(options, monkeypatch):
    monkeypatch.setenv("SHERLOCK_CONFIG", "fictional-private-config-that-must-not-be-read")
    monkeypatch.setenv("SHERLOCK_PROFILE", "private-other-profile")
    monkeypatch.setenv("SHERLOCK_DATA_DIR", "private-other-folder")
    plan = setup.plan_setup(**options)
    assert plan.profile == "default"
    assert plan.operator_before is None
    assert not plan.install_dir.exists() and not plan.data_dir.exists()
    assert list(plan.project.iterdir()) == []
    assert not any(name.endswith((".env", ".sqlite3")) for name in plan.files)


@pytest.mark.parametrize("host", ["claude-code", "codex", "manual"])
def test_install_and_identical_rerun_preserve_other_settings(options, local_checks, host):
    options["host"] = host
    plan = setup.plan_setup(**options)
    if host != "manual":
        plan.host_config.parent.mkdir(parents=True, exist_ok=True)
        original = (b'{"unrelated":{"keep":true}}\n' if host == "claude-code" else b'# Keep this comment\nmodel = "existing-model"\n')
        plan.host_config.write_bytes(original)
        plan = setup.plan_setup(**options)
    else:
        original = None
    result = setup.apply_setup(plan)
    assert result["local_checks"]["passed"] is True
    assert result["status"] == ("manual_setup_pending" if host == "manual" else "host_restart_required")
    assert len(list(plan.skills_dir.glob("*/SKILL.md"))) == 7
    assert setup.bundle_files(plan.bundle) == plan.files
    assert json.loads(plan.operator_config.read_text())["connections"] == {}
    if original is not None:
        assert Path(result["backup"]).read_bytes() == original
        if os.name != "nt":
            assert Path(result["backup"]).stat().st_mode & 0o777 == 0o600
    host_bytes = plan.host_config.read_bytes()
    second = setup.apply_setup(setup.plan_setup(**options))
    assert second["backup"] is None
    assert plan.host_config.read_bytes() == host_bytes
    assert local_checks == ["sync", "verify", "sync", "verify"]


def test_existing_skill_conflict_stops_before_any_setup_writes(options):
    plan = setup.plan_setup(**options)
    existing = plan.skills_dir / setup.SKILLS[0]
    existing.mkdir(parents=True)
    (existing / "SKILL.md").write_text("Keep the operator's version")
    with pytest.raises(ValueError, match="differs"):
        setup.plan_setup(**options)
    assert (existing / "SKILL.md").read_text() == "Keep the operator's version"
    assert not plan.install_dir.exists() and not plan.data_dir.exists()


def test_existing_mcp_conflict_stops_before_any_setup_writes(options):
    plan = setup.plan_setup(**options)
    plan.host_config.write_text('{"mcpServers":{"agent-sherlock":{"command":"existing-program"}}}')
    original = plan.host_config.read_bytes()
    with pytest.raises(ValueError):
        setup.plan_setup(**options)
    assert plan.host_config.read_bytes() == original
    assert not plan.install_dir.exists() and not plan.data_dir.exists()


def test_failed_runtime_check_does_not_configure_host(options, local_checks, monkeypatch):
    plan = setup.plan_setup(**options)

    async def failure(python):
        raise ValueError("Fictional local check failure")

    monkeypatch.setattr(setup_check, "verify_runtime", failure)
    with pytest.raises(ValueError, match="local check"):
        setup.apply_setup(plan)
    assert not plan.host_config.exists() and not plan.skills_dir.exists()
    assert not plan.operator_config.exists()


def test_concurrent_host_change_is_not_overwritten(options, local_checks, monkeypatch):
    plan = setup.plan_setup(**options)
    latest = b'{"owner_update":"preserve"}'

    async def verify(python):
        plan.host_config.write_bytes(latest)
        return {"passed": True}

    monkeypatch.setattr(setup_check, "verify_runtime", verify)
    with pytest.raises(ValueError, match="changed during setup"):
        setup.apply_setup(plan)
    assert plan.host_config.read_bytes() == latest
    assert not list(plan.skills_dir.glob("*/SKILL.md"))


def test_partial_skill_copy_failure_cleans_only_new_files_and_allows_retry(options, local_checks, monkeypatch):
    plan = setup.plan_setup(**options)
    write = setup._new_file

    def fail_reference(path, data):
        if path.is_relative_to(plan.skills_dir) and path.name == "guide.md":
            raise OSError("Fictional disk failure")
        return write(path, data)

    monkeypatch.setattr(setup, "_new_file", fail_reference)
    with pytest.raises(OSError, match="disk failure"):
        setup.apply_setup(plan)
    assert not (plan.skills_dir / setup.SKILLS[0]).exists()
    assert not plan.host_config.exists()
    monkeypatch.setattr(setup, "_new_file", write)
    assert setup.apply_setup(setup.plan_setup(**options))["local_checks"]["passed"]


def test_setup_lock_can_be_reused_without_deleting_it(options):
    directory = options["install_dir"]
    with setup._setup_lock(directory):
        with pytest.raises(ValueError, match="Another Sherlock setup"):
            with setup._setup_lock(directory):
                pytest.fail("Concurrent setup acquired the lock")
    with setup._setup_lock(directory):
        pass


@pytest.mark.parametrize("kind", ["config", "skill", "bundle", "venv"])
def test_symlink_targets_are_not_followed(options, local_checks, kind):
    plan = setup.plan_setup(**options)
    foreign = options["home"] / "foreign"
    foreign.mkdir(parents=True)
    (foreign / "sentinel.txt").write_text("Keep unrelated files")
    if kind == "config":
        target = plan.host_config
        source = foreign / "sentinel.txt"
    elif kind == "skill":
        target = plan.skills_dir / setup.SKILLS[0]
        source = foreign
    else:
        plan.bundle.parent.mkdir(parents=True)
        if kind == "venv":
            setup._copy_files(plan.bundle, plan.files)
            target = plan.bundle / "runtime/.venv"
        else:
            target = plan.bundle
        source = foreign
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.symlink_to(source, target_is_directory=source.is_dir())
    except OSError:
        pytest.skip("Creating symlinks is unavailable on this test system")
    with pytest.raises(ValueError, match="symbolic link"):
        setup.plan_setup(**options)
    assert (foreign / "sentinel.txt").read_text() == "Keep unrelated files"
    assert local_checks == []


def test_data_and_operator_configuration_stay_outside_project(options):
    with pytest.raises(ValueError, match="outside"):
        setup.plan_setup(**{**options, "data_dir": options["project"] / "data"})
    with pytest.raises(ValueError, match="outside"):
        setup.plan_setup(**{**options, "operator_config": options["project"] / "private.json"})


def test_operator_and_host_config_cannot_be_the_same_file(options):
    path = options["data_dir"] / "same.json"
    with pytest.raises(ValueError, match="different files"):
        setup.plan_setup(**options, operator_config=path, host_config=path)


def test_cli_dry_run_does_not_create_data_directories(tmp_path, capsys):
    project = tmp_path / "project"
    project.mkdir()
    data = tmp_path / "private"
    software = tmp_path / "software"
    assert main(["--data-dir", str(data), "setup", "--host", "codex", "--scope", "project",
                 "--project", str(project), "--install-dir", str(software), "--dry-run", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "preview"
    assert not data.exists() and not software.exists() and not list(project.iterdir())
