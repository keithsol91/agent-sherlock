"""Guided local installation. Provider connections are a separate operator step."""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Callable
from uuid import uuid4

from .config import default_data_dir, load_settings
from .setup_hosts import host_locations, merge_config


SKILLS = (
    "agent-sherlock", "sherlock-account-context", "sherlock-case-files",
    "sherlock-competitor-research", "sherlock-recall",
    "sherlock-dormant-relationships", "sherlock-pitched-contact-moves",
)
DOCS = (
    "install.md", "permissions.md", "slack.md", "integrations.md",
    "compatibility.md", "daily-recipes.md", "operations.md",
    "relationships.md", "troubleshooting.md",
)


def _file_path(path: Path) -> Path:
    path = path.expanduser().absolute()
    return path.parent.resolve() / path.name


def _read(path: Path) -> bytes | None:
    if path.is_symlink():
        raise ValueError(f"Setup will not follow a symbolic link: {path}")
    if not path.exists():
        return None
    if not path.is_file() or path.stat().st_size > 8_000_000:
        raise ValueError(f"Setup needs a normal configuration file smaller than 8 MB: {path}")
    return path.read_bytes()


def _tree(path: Path) -> dict[str, bytes]:
    if path.is_symlink():
        raise ValueError(f"Setup will not copy or replace a symbolic link: {path}")
    if not path.is_dir():
        raise ValueError(f"Setup needs a regular folder: {path}")
    result = {}
    for item in sorted(path.rglob("*")):
        if item.is_symlink():
            raise ValueError(f"Setup will not copy or replace a symbolic link: {item}")
        if item.is_file():
            result[item.relative_to(path).as_posix()] = item.read_bytes()
    return result


def bundle_files(source: Path) -> dict[str, bytes]:
    """Copy product files only, never a checkout, environment, or case store."""
    if any(path.is_symlink() for path in (source, source / "runtime", source / "skills", source / "documentation")):
        raise ValueError("Setup needs regular source folders, not symbolic links.")
    result = {}
    for name in ("pyproject.toml", "uv.lock", "README.md"):
        path = source / "runtime" / name
        value = _read(path)
        if value is None:
            raise ValueError("Use setup from the downloaded Sherlock source bundle, which includes runtime and skills.")
        result[f"runtime/{name}"] = value
    code = source / "runtime/src/agent_sherlock"
    if not code.is_dir() or code.is_symlink():
        raise ValueError("The Sherlock runtime source folder is missing or is a symbolic link.")
    for path in sorted(code.rglob("*.py")):
        if any(part == "__pycache__" for part in path.parts):
            continue
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != source and p.is_relative_to(source)):
            raise ValueError("Setup will not copy symbolic links from the runtime.")
        result[path.relative_to(source).as_posix()] = path.read_bytes()
    for name in SKILLS:
        items = _tree(source / "skills" / name)
        if "SKILL.md" not in items:
            raise ValueError(f"The source bundle is missing the {name} skill.")
        for relative, data in items.items():
            parts = Path(relative).parts
            if any(part.startswith(".") or part == "__pycache__" for part in parts):
                continue
            if Path(relative).suffix not in {".md", ".json", ".txt", ".py"}:
                raise ValueError(f"Unexpected file in an operating skill: {name}/{relative}")
            result[f"skills/{name}/{relative}"] = data
    for name in DOCS:
        data = _read(source / "documentation" / name)
        if data is not None:
            result[f"documentation/{name}"] = data
    examples = source / "documentation/examples"
    if examples.exists():
        for name, data in _tree(examples).items():
            if Path(name).suffix == ".json" and not any(p.startswith(".") for p in Path(name).parts):
                result[f"documentation/examples/{name}"] = data
    return result


def _fingerprint(files: dict[str, bytes]) -> str:
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:20]


def _private_dir(path: Path) -> None:
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError(f"Setup will not write through a symbolic link: {part}")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)


def _identity(path: Path) -> tuple[int, int]:
    info = path.lstat()
    return info.st_dev, info.st_ino


def _new_file(path: Path, data: bytes) -> tuple[int, int]:
    _private_dir(path.parent)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    info = os.fstat(fd)
    identity = (info.st_dev, info.st_ino)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
    except BaseException:
        if path.exists() and not path.is_symlink() and _identity(path) == identity:
            path.unlink()
        raise
    return identity


def _copy_files(destination: Path, files: dict[str, bytes]) -> None:
    destination.mkdir(mode=0o700)
    owned = [(destination, _identity(destination))]
    try:
        for name, data in files.items():
            target = destination / name
            for parent in reversed(target.parent.parents):
                if parent.is_relative_to(destination) and not parent.exists():
                    parent.mkdir(mode=0o700)
                    owned.append((parent, _identity(parent)))
            if not target.parent.exists():
                target.parent.mkdir(mode=0o700)
                owned.append((target.parent, _identity(target.parent)))
            owned.append((target, _new_file(target, data)))
    except BaseException:
        for path, identity in reversed(owned):
            try:
                if not path.is_symlink() and _identity(path) == identity:
                    path.rmdir() if path.is_dir() else path.unlink()
            except OSError:
                pass  # Never remove an unrelated child or a replacement.
        raise


@dataclass
class SetupPlan:
    host: str
    scope: str
    project: Path
    source: Path
    install_dir: Path
    bundle: Path
    files: dict[str, bytes]
    data_dir: Path
    profile: str
    operator_config: Path
    operator_before: bytes | None
    host_config: Path
    host_before: bytes | None
    host_after: bytes
    skills_dir: Path
    uv_command: str

    @property
    def python(self) -> Path:
        return self.bundle / "runtime/.venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

    def summary(self) -> dict:
        return {
            "host": self.host, "scope": self.scope,
            "runtime_directory": str(self.bundle / "runtime"),
            "data_directory": str(self.data_dir), "profile": self.profile,
            "operator_config": str(self.operator_config),
            "host_config": str(self.host_config), "skills_directory": str(self.skills_dir),
            "skills": list(SKILLS), "host_config_changes": self.host_before != self.host_after,
            "provider_connections": "unchanged; setup makes no provider calls",
        }


def plan_setup(*, host: str, scope: str = "user", project: Path | None = None,
               source: Path | None = None, home: Path | None = None,
               data_dir: Path | None = None, profile: str = "default",
               install_dir: Path | None = None, operator_config: Path | None = None,
               host_config: Path | None = None, skills_dir: Path | None = None,
               uv_command: str | None = None, codex_home: Path | None = None) -> SetupPlan:
    """Read-only preflight; no data directories, config, or host settings created."""
    if host not in {"claude-code", "codex", "manual"} or scope not in {"user", "project"}:
        raise ValueError("Choose Claude Code, Codex, or manual setup, with user or project scope.")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", profile):
        raise ValueError("Use a profile name of 1–64 letters, digits, underscores, or hyphens.")
    source = (source or Path(__file__).parents[3]).expanduser().resolve()
    project = (project or Path.cwd()).expanduser().resolve()
    home = (home or Path.home()).expanduser().resolve()
    if not project.is_dir():
        raise ValueError("Choose an existing project folder.")
    files = bundle_files(source)
    install_dir = (install_dir or default_data_dir() / "_install").expanduser().resolve()
    data_dir = (data_dir or default_data_dir()).expanduser().resolve()
    if data_dir.is_relative_to(source) or install_dir.is_relative_to(source):
        raise ValueError("Choose private data and installation folders outside the downloaded source bundle.")
    if scope == "project" and data_dir.is_relative_to(project):
        raise ValueError("Keep private Sherlock data outside the project folder.")
    bundle = install_dir / "bundles" / _fingerprint(files)
    if bundle.is_symlink() or bundle.parent.is_symlink():
        raise ValueError("The managed installation must not be a symbolic link.")
    if (bundle / "runtime/.venv").is_symlink():
        raise ValueError("The managed Python environment must not be a symbolic link.")
    if bundle.exists() or bundle.is_symlink():
        if bundle_files(bundle) != files:
            raise ValueError("The managed Sherlock copy has changed. Choose a new installation folder; setup will not replace it.")
    python = bundle / "runtime/.venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    operator_config = _file_path(operator_config or data_dir / profile / "config.json")
    if operator_config.is_relative_to(source) or (scope == "project" and operator_config.is_relative_to(project)):
        raise ValueError("Keep the private operator configuration outside the source and project folders.")
    operator_before = _read(operator_config)
    if operator_before is not None:
        try:
            config = json.loads(operator_before)
            if not isinstance(config, dict) or config.get("profile", profile) != profile:
                raise ValueError
        except (ValueError, UnicodeError):
            raise ValueError("The existing private configuration is invalid or belongs to another profile.") from None
    entry = {"command": str(python), "args": ["-I", "-m", "agent_sherlock", "--data-dir", str(data_dir),
            "--profile", profile, "--config", str(operator_config), "serve"]}
    if host == "manual":
        config_target = install_dir / "manual" / f"{profile}-{_fingerprint(files)}.mcp.json"
        skills_target = bundle / "skills"
    else:
        config_target, skills_target = host_locations(host, scope, project, home, codex_home)
    config_target = _file_path(host_config or config_target)
    skills_target = _file_path(skills_dir or skills_target)
    if config_target == operator_config:
        raise ValueError("The agent configuration and private Sherlock configuration must be different files.")
    if host != "manual" and (config_target.is_relative_to(bundle) or skills_target.is_relative_to(bundle)):
        raise ValueError("Keep the agent's settings and installed skills outside the managed runtime bundle.")
    before = _read(config_target)
    try:
        after = merge_config("claude-code" if host == "manual" else host,
                             before.decode("utf-8") if before is not None else None, entry).encode("utf-8")
    except UnicodeError:
        raise ValueError("The host configuration must be a UTF-8 text file.") from None
    if host != "manual" or skills_dir is not None:
        for name in SKILLS:
            target = skills_target / name
            prefix = f"skills/{name}/"
            expected = {key.removeprefix(prefix): value for key, value in files.items() if key.startswith(prefix)}
            if target.exists() or target.is_symlink():
                if _tree(target) != expected:
                    raise ValueError(f"An existing {name} skill differs. Keep it or move it aside before rerunning setup: {target}")
    uv_command = uv_command or shutil.which("uv")
    if not uv_command:
        raise ValueError("Install uv first, then rerun setup. See the installation guide.")
    return SetupPlan(host, scope, project, source, install_dir, bundle, files, data_dir, profile,
                     operator_config, operator_before, config_target, before, after, skills_target, str(uv_command))


@contextmanager
def _setup_lock(directory: Path):
    _private_dir(directory)
    lock = directory / "setup.lock"
    if lock.is_symlink():
        raise ValueError("Setup will not follow a symbolic link for its installation lock.")
    stream = lock.open("a+b")
    stream.seek(0)
    stream.write(b"0")
    stream.flush()
    stream.seek(0)
    locked = False
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        locked = True
        yield
    except (BlockingIOError, PermissionError):
        if not locked:
            raise ValueError("Another Sherlock setup is running. Let it finish, then retry.") from None
        raise
    finally:
        if locked:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()


def _sync_runtime(plan: SetupPlan) -> None:
    if (plan.bundle / "runtime/.venv").is_symlink():
        raise ValueError("The managed Python environment must not be a symbolic link.")
    env = dict(os.environ)
    for name in ("SHERLOCK_CONFIG", "SHERLOCK_PROFILE", "SHERLOCK_DATA_DIR", "VIRTUAL_ENV",
                 "PYTHONPATH", "PYTHONHOME", "UV_PROJECT_ENVIRONMENT", "UV_WORKING_DIR"):
        env.pop(name, None)
    try:
        result = subprocess.run([plan.uv_command, "sync", "--locked", "--no-dev", "--no-progress",
                                 "--project", str(plan.bundle / "runtime")],
                                env=env, capture_output=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        raise ValueError("Dependency installation could not finish. Check uv and your network, then rerun setup.") from None
    if result.returncode or not plan.python.is_file():
        raise ValueError("Dependency installation failed. Check uv and your package download access, then rerun setup.")


def _save_host_config(plan: SetupPlan) -> str | None:
    if _read(plan.host_config) != plan.host_before:
        raise ValueError("The host configuration changed during setup. Rerun setup to preserve the latest settings.")
    if plan.host_before == plan.host_after:
        return None
    _private_dir(plan.host_config.parent)
    backup = None
    if plan.host_before is not None:
        backup = plan.install_dir / "backups" / uuid4().hex / plan.host_config.name
        _new_file(backup, plan.host_before)
    fd, temporary = tempfile.mkstemp(prefix=".sherlock-", dir=plan.host_config.parent)
    temporary = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(plan.host_after)
        if _read(plan.host_config) != plan.host_before:
            raise ValueError("The host configuration changed during setup. Rerun setup to preserve the latest settings.")
        if plan.host_before is None:
            # Link a completed file into place without replacing a concurrent file.
            os.link(temporary, plan.host_config)
        else:
            os.replace(temporary, plan.host_config)
    finally:
        temporary.unlink(missing_ok=True)
    return str(backup) if backup else None


def apply_setup(plan: SetupPlan, *, progress: Callable[[str], None] = lambda message: None) -> dict:
    from .setup_check import verify_runtime
    with _setup_lock(plan.install_dir):
        progress("Preparing Sherlock in your private installation folder…")
        if plan.bundle.is_symlink() or plan.bundle.parent.is_symlink():
            raise ValueError("The managed installation must not be a symbolic link.")
        if not plan.bundle.exists():
            _private_dir(plan.bundle.parent)
            with tempfile.TemporaryDirectory(prefix="sherlock-copy-", dir=plan.bundle.parent) as folder:
                staged = Path(folder) / "bundle"
                _copy_files(staged, plan.files)
                # A conflicting installation is never overwritten.
                plan.bundle.mkdir(mode=0o700)
                try:
                    for child in staged.iterdir():
                        shutil.move(str(child), str(plan.bundle / child.name))
                except Exception:
                    # This new, private bundle is not referenced by any host yet.
                    shutil.rmtree(plan.bundle)
                    raise
        elif bundle_files(plan.bundle) != plan.files:
            raise ValueError("The managed Sherlock copy changed after the setup preview. Rerun setup.")
        progress("Installing the locked software dependencies…")
        _sync_runtime(plan)
        progress("Checking tool discovery, a fictional case, and recall after restart…")
        checks = asyncio.run(verify_runtime(plan.python))
        if checks.get("passed") is not True:
            raise ValueError("The local installation check did not pass. Host settings were not changed.")
        if _read(plan.operator_config) != plan.operator_before:
            raise ValueError("Your operator configuration changed during setup. Rerun setup.")
        if plan.operator_before is None:
            _new_file(plan.operator_config, (json.dumps({"profile": plan.profile, "connections": {}, "policy": {}}, indent=2) + "\n").encode())
        # Validates the selected operator file locally; never calls a provider.
        load_settings(plan.data_dir, plan.profile, plan.operator_config)
        created = []
        try:
            if plan.skills_dir != plan.bundle / "skills":
                _private_dir(plan.skills_dir)
                for name in SKILLS:
                    prefix = f"skills/{name}/"
                    expected = {key.removeprefix(prefix): value for key, value in plan.files.items() if key.startswith(prefix)}
                    target = plan.skills_dir / name
                    if target.exists() or target.is_symlink():
                        if _tree(target) != expected:
                            raise ValueError(f"The {name} skill changed during setup. No existing skill was replaced.")
                    else:
                        _copy_files(target, expected)
                        created.append((target, expected))
            backup = _save_host_config(plan)
        except Exception:
            for target, expected in reversed(created):
                if not target.is_symlink() and _tree(target) == expected:
                    shutil.rmtree(target)
            raise
    return {**plan.summary(), "status": "manual_setup_pending" if plan.host == "manual" else "host_restart_required",
            "local_checks": checks, "backup": backup,
            "next": ("Use the generated MCP configuration and complete skill folders in your agent's setup."
                     if plan.host == "manual" else "Reopen your agent, complete any trust prompts, and confirm Sherlock appears in its tools."),
            "accounts": "Connect your own Slack and CRM separately when you are ready."}


def run_setup(args) -> int:
    host = args.host
    if host is None:
        if not sys.stdin.isatty() or args.json:
            raise ValueError("Choose --host claude-code, --host codex, or --host manual.")
        print("Where would you like to use Sherlock?\n  1. Claude Code\n  2. Codex\n  3. Another agent")
        selected = input("Choose 1, 2, or 3: ").strip()
        host = {"1": "claude-code", "2": "codex", "3": "manual"}.get(selected)
        if host is None:
            raise ValueError("Choose one of the listed agents and rerun setup.")
    if host == "claude-code" and args.scope == "user" and os.environ.get("CLAUDE_CONFIG_DIR"):
        if not args.host_config or not args.skills_dir:
            raise ValueError("Claude uses a custom settings location. Supply its --host-config and --skills-dir paths explicitly.")
    plan = plan_setup(host=host, scope=args.scope, project=args.project,
                      data_dir=Path(args.data_dir) if args.data_dir else None,
                      profile=args.profile or "default", install_dir=args.install_dir,
                      operator_config=Path(args.config) if args.config else None,
                      host_config=args.host_config, skills_dir=args.skills_dir,
                      codex_home=Path(os.environ["CODEX_HOME"]) if os.environ.get("CODEX_HOME") else None)
    if args.dry_run:
        print(json.dumps({"status": "preview", **plan.summary()}, indent=2))
        return 0
    if not args.yes:
        if not sys.stdin.isatty() or args.json:
            raise ValueError("Use --dry-run to review the setup, then add --yes to install without a terminal prompt.")
        print(f"\nSherlock will use {plan.data_dir} for private data.")
        print(f"Agent settings: {plan.host_config}\nSkills: {plan.skills_dir}")
        print("Existing settings are preserved. No Slack or CRM account will be connected.")
        if input("Install Sherlock? [Y/n] ").strip().lower() not in {"", "y", "yes"}:
            print("Setup cancelled. No setup files were changed.")
            return 0
    result = apply_setup(plan, progress=lambda message: print(message, file=sys.stderr))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("\nSherlock's local checks passed.")
        print(result["next"])
        print(f"Installed runtime: {plan.bundle / 'runtime'}\nPrivate data: {plan.data_dir}\nProfile: {plan.profile}")
        print(f"Sherlock configuration: {plan.operator_config}\nAgent configuration: {plan.host_config}\nSkill folders: {plan.skills_dir}")
        if result["backup"]:
            print(f"Previous settings backup: {result['backup']}")
        print(result["accounts"])
    return 0
