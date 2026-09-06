import json
import sqlite3

import pytest

from agent_sherlock.config import load_settings
from agent_sherlock.operations import backup, restore, service_lock
from agent_sherlock.storage import Store


def seed(settings):
    with Store(settings.database, settings.profile) as store:
        return store.create_case("Fictional Clinic", "fictional-clinic", "medical", "client")


def test_backup_restore_preserves_cases_but_does_not_replay_external_approvals(tmp_path):
    original = load_settings(tmp_path / "original", "clinic")
    case = seed(original)
    with sqlite3.connect(original.changes_database) as db:
        db.execute("CREATE TABLE approvals (state TEXT)")
        db.execute("INSERT INTO approvals VALUES ('approved')")
    destination = tmp_path / "backup"
    snapshot = backup(original, destination)
    assert "changes.sqlite3" in snapshot["manifest"]["files"]
    recovered = load_settings(tmp_path / "recovered", "clinic")
    result = restore(recovered, destination, "clinic")
    assert result["crm_proposals_restored"] is False
    assert not recovered.changes_database.exists()
    with Store(recovered.database, recovered.profile) as store:
        assert store.get_case(case["id"])["subject"] == "Fictional Clinic"


def test_restore_rejects_other_profile_tampering_and_overwrite(tmp_path):
    original = load_settings(tmp_path / "original", "a")
    seed(original)
    backup(original, tmp_path / "backup")
    with pytest.raises(ValueError, match="empty"):
        restore(original, tmp_path / "backup", "a")
    other = load_settings(tmp_path / "other", "b")
    with pytest.raises(ValueError, match="does not match"):
        restore(other, tmp_path / "backup", "b")
    recovered = load_settings(tmp_path / "recovered", "a")
    (tmp_path / "backup/cases.sqlite3").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="integrity"):
        restore(recovered, tmp_path / "backup", "a")
    assert not recovered.database.exists()


def test_backup_blocks_while_service_owns_profile(tmp_path):
    settings = load_settings(tmp_path / "data", "a")
    seed(settings)
    with service_lock(settings):
        with pytest.raises(ValueError, match="service is running"):
            backup(settings, tmp_path / "backup")
    assert not (tmp_path / "backup").exists()


def test_backup_rejects_manifest_path_escape(tmp_path):
    settings = load_settings(tmp_path / "data", "a")
    source = tmp_path / "fake"
    source.mkdir()
    (source / "manifest.json").write_text(json.dumps({"format": 1, "profile": "a", "files": {"../escape": "hash"}}))
    with pytest.raises(ValueError, match="invalid data files"):
        restore(settings, source, "a")

