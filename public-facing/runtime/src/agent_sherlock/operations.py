"""Operator-only backup/restore; backups contain private data, never connector secrets."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

from . import __version__
from .config import Settings

DATA_FILES = ("cases.sqlite3", "changes.sqlite3", "fixture-crm.sqlite3")


@contextmanager
def service_lock(settings: Settings):
    """Prevent a second server or a backup/restore during service operation."""
    path = settings.profile_dir / "service.lock"
    stream = path.open("a+b")
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
    except (BlockingIOError, PermissionError) as exc:
        if not locked:
            raise ValueError("This profile's service is running. Stop it before another server, backup, or restore.") from exc
        raise
    finally:
        if locked:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def backup(settings: Settings, destination: str | Path) -> dict:
    destination = Path(destination).expanduser().resolve()
    if destination.exists():
        raise ValueError("Backup destination must be a new directory.")
    if destination.is_relative_to(settings.profile_dir):
        raise ValueError("Store backups outside the active profile directory.")
    with service_lock(settings):
        if not settings.database.is_file():
            raise ValueError("This profile has no case database to back up. Run doctor or initialize the service first.")
        if any((settings.profile_dir / name).is_symlink() for name in DATA_FILES):
            raise ValueError("Data files must not be symbolic links.")
        destination.mkdir(parents=True, mode=0o700)
        files = {}
        for name in DATA_FILES:
            source = settings.profile_dir / name
            if not source.exists():
                continue
            if source.is_symlink():
                raise ValueError("Data files must not be symbolic links.")
            target = destination / name
            if name.endswith(".sqlite3"):
                with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
                    with closing(sqlite3.connect(target)) as snapshot:
                        original.backup(snapshot)
            else:
                shutil.copyfile(source, target)
            target.chmod(0o600)
            files[name] = digest(target)
        manifest = {"format": 1, "version": __version__, "profile": settings.profile, "files": files}
        (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return {"backup_directory": str(destination), "manifest": manifest,
                "private_data": True, "credentials_included": False}


def restore(settings: Settings, source: str | Path, confirmation: str) -> dict:
    source = Path(source).expanduser().resolve()
    if confirmation != settings.profile:
        raise ValueError("Confirm the exact destination profile name.")
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    files = manifest.get("files")
    if manifest.get("format") != 1 or manifest.get("profile") != settings.profile:
        raise ValueError("Backup format or organization profile does not match.")
    if not isinstance(files, dict) or "cases.sqlite3" not in files or not set(files) <= set(DATA_FILES):
        raise ValueError("Backup manifest contains invalid data files.")
    for name, expected in files.items():
        item = source / name
        if item.is_symlink() or digest(item) != expected:
            raise ValueError("Backup integrity check failed.")
        if name.endswith(".sqlite3"):
            with closing(sqlite3.connect(item.as_uri() + "?mode=ro", uri=True)) as db:
                if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("Backup database integrity check failed.")
    with service_lock(settings):
        # Restore into an empty profile only: never replace newer data or resurrect old approvals.
        if any((settings.profile_dir / name).exists() for name in DATA_FILES):
            raise ValueError("Restore requires an empty profile directory. Preserve existing data first.")
        try:
            for name in files:
                if name == "changes.sqlite3":
                    # External effects cannot be rolled back; proposals must be created afresh.
                    continue
                target = settings.profile_dir / name
                shutil.copyfile(source / name, target)
                target.chmod(0o600)
        except Exception:
            for name in files:
                target = settings.profile_dir / name
                if target.exists():
                    target.unlink()
            raise
    return {"restored_profile": settings.profile,
            "crm_proposals_restored": False,
            "note": "CRM effects are not rolled back. Reconcile live records and create fresh proposals. Backups retain deleted data until you remove them."}
