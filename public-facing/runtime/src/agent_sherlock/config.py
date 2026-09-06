"""Operator configuration. MCP callers cannot select a different data profile."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


def default_data_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "AgentSherlock"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/AgentSherlock"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "agent-sherlock"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    profile: str
    config: dict

    @property
    def profile_dir(self) -> Path:
        return self.data_dir / self.profile

    @property
    def database(self) -> Path:
        return self.profile_dir / "cases.sqlite3"

    @property
    def changes_database(self) -> Path:
        return self.profile_dir / "changes.sqlite3"

    def ensure_directory(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.profile_dir.is_symlink():
            raise ValueError("The profile directory must not be a symbolic link.")
        self.profile_dir.mkdir(exist_ok=True, mode=0o700)
        if os.name != "nt":
            self.profile_dir.chmod(0o700)


def load_settings(data_dir: str | Path | None = None, profile: str | None = None,
                  config_path: str | Path | None = None, *, ignore_config: bool = False) -> Settings:
    profile = profile or os.environ.get("SHERLOCK_PROFILE", "default")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", profile):
        raise ValueError("Profile must contain 1–64 letters, digits, underscores, or hyphens.")
    root = Path(data_dir or os.environ.get("SHERLOCK_DATA_DIR") or default_data_dir()).expanduser().resolve()
    config: dict = {}
    path = None if ignore_config else config_path or os.environ.get("SHERLOCK_CONFIG")
    if path:
        raw = Path(path).expanduser().read_text(encoding="utf-8")
        if len(raw) > 1_000_000:
            raise ValueError("Configuration exceeds the 1 MB limit.")
        config = json.loads(raw)
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a JSON object.")
        if config.get("profile", profile) != profile:
            raise ValueError("Configuration profile does not match the selected profile.")
        if not isinstance(config.get("connections", {}), dict):
            raise ValueError("Connections must be a JSON object keyed by connection ID.")
        if not isinstance(config.get("policy", {}), dict):
            raise ValueError("Policy must be a JSON object.")
        for connection_id, connection in config.get("connections", {}).items():
            if not connection_id or not isinstance(connection, dict):
                raise ValueError("Each connection needs an ID and a configuration object.")
            if not isinstance(connection.get("account_id"), str) or not connection["account_id"]:
                raise ValueError("Each connection needs an explicit account_id string.")
            if not isinstance(connection.get("operations"), dict) or not isinstance(connection.get("transport"), dict):
                raise ValueError("Each connection needs operations and transport objects.")
    settings = Settings(root, profile, config)
    settings.ensure_directory()
    return settings
