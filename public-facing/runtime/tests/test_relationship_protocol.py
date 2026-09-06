"""Fictional relationship workflows through the shipped CLI and MCP transport."""
from copy import deepcopy
from datetime import datetime, timezone
import json

from agent_sherlock.cli import main
from agent_sherlock.config import load_settings
from agent_sherlock.operations import backup, restore, service_lock
from agent_sherlock.relationships import Relationships
from agent_sherlock.storage import Store
from test_mcp_e2e import call_ok, call_error, stdio_session
from test_relationships import fictional_record


def current_fixture(*, moved=False):
    record = fictional_record(moved=moved)
    now = datetime.now(timezone.utc).isoformat()
    record["last_meaningful_contact_at"] = "2023-09-01T12:00:00Z"
    for obj, key in ((record["history_coverage"], "checked_at"), (record["current_employment"], "observed_at"), (record["source_status"], "verified_at")):
        obj[key] = now
    return record


async def test_stdio_import_review_feedback_restart_and_profile_isolation(tmp_path):
    data = tmp_path / "fictional relationship profiles"
    record = current_fixture(moved=True)
    async with stdio_session(data, "relationships") as client:
        names = {tool.name for tool in (await client.list_tools()).tools}
        assert {"relationship_import", "relationship_get", "relationship_list", "relationship_evaluate", "relationship_queue", "relationship_feedback"} <= names
        imported = await call_ok(client, "relationship_import", records=[record])
        assert imported["provider_calls"] == 0
        relation = imported["relationships"][0]
        listed = await call_ok(client, "relationship_list", limit=1)
        assert listed["relationships"][0]["id"] == relation["id"]
        evaluation = await call_ok(client, "relationship_evaluate")
        assert evaluation["results"][0]["skill"] == "pitched_contact_moved"
        review = (await call_ok(client, "relationship_queue"))["reviews"][0]
        result = await call_ok(client, "relationship_feedback", review_id=review["id"], action="wrong_employer", expected_revision=review["revision"], note="Fictional owner cannot verify this employer")
        assert result["state"] == "needs_verification"
        error = await call_error(client, "relationship_feedback", review_id=review["id"], action="reopen", expected_revision=review["revision"], note="Stale owner view")
        assert error["code"] == "RevisionConflictError"
        case = await call_ok(client, "case_get", case_id=relation["case_id"])
        assert case["relationship"]["local_state"]["verification_required"] == "wrong_employer"
        assert (await call_ok(client, "recall_count"))["count"] == 0
    async with stdio_session(data, "relationships") as client:
        restored = await call_ok(client, "relationship_get", relationship_id=relation["id"], include_history=True)
        assert restored["record"]["original_company"] == record["original_company"]
        assert restored["local_state"]["verification_required"] == "wrong_employer"
        assert (await call_ok(client, "relationship_queue"))["reviews"] == []
    async with stdio_session(data, "unrelated") as client:
        assert (await call_ok(client, "relationship_list"))["relationships"] == []
        await call_error(client, "relationship_get", relationship_id=relation["id"])
        await call_error(client, "relationship_feedback", review_id=review["id"], action="exclude", expected_revision=result["revision"])


def test_cli_import_evaluate_feedback_and_profile_lock(tmp_path, capsys):
    data = tmp_path / "data"
    source = tmp_path / "fictional.json"
    source.write_text(json.dumps({"schema_version": 1, "relationships": [current_fixture()]}))
    prefix = ["--data-dir", str(data), "--profile", "fictional"]
    assert main(prefix + ["relationship-import", str(source)]) == 0
    imported = json.loads(capsys.readouterr().out)
    assert imported["provider_calls"] == 0
    assert main(prefix + ["relationship-evaluate"]) == 0
    assert json.loads(capsys.readouterr().out)["results"][0]["state"] == "ready"
    assert main(prefix + ["relationship-queue"]) == 0
    review = json.loads(capsys.readouterr().out)["reviews"][0]
    assert main(prefix + ["relationship-feedback", review["id"], "already_in_touch", "--expected-revision", str(review["revision"])]) == 0
    assert json.loads(capsys.readouterr().out)["state"] == "handled"
    settings = load_settings(data, "fictional")
    with service_lock(settings):
        assert main(prefix + ["relationship-evaluate"]) == 2
    assert "service is running" in capsys.readouterr().err


def test_backup_restore_includes_relationship_history_reviews_and_feedback(tmp_path):
    settings = load_settings(tmp_path / "original", "fictional")
    record = current_fixture()
    with Store(settings.database, settings.profile) as store:
        service = Relationships(store)
        relation = service.upsert(record)
        changed = current_fixture(moved=True)
        service.upsert(changed, expected_revision=relation["revision"], reason="New fictional employer verified")
        service.evaluate_all()
        review = service.queue()["reviews"][0]
        service.feedback(review["id"], "exclude", expected_revision=review["revision"])
        exported = store.export_profile()
        assert len(exported["relationship_history"]) == 1
        assert len(exported["relationship_review_events"]) == 1
    backup(settings, tmp_path / "snapshot")
    recovered = load_settings(tmp_path / "recovered", "fictional")
    restore(recovered, tmp_path / "snapshot", "fictional")
    with Store(recovered.database, recovered.profile) as store:
        service = Relationships(store)
        restored = service.get(relation["id"], include_history=True)
        assert restored["history"][0]["record"]["current_employment"]["company_id"] == "fictional-acorn"
        assert restored["local_state"]["excluded"] is True
        assert service.queue()["reviews"] == []
        assert len(service.queue(state="suppressed")["reviews"]) == 1
