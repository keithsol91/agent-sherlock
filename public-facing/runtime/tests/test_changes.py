import asyncio
import json
import sqlite3
from contextlib import closing

import pytest

from agent_sherlock.changes import ChangeError, ChangeManager
from agent_sherlock.connectors import ConnectorError, ConnectorGateway, FixtureTransport, fixture_connection_config


EVIDENCE = [{"source_url": "https://example.com/fictional", "observation": "Fictional example evidence", "observed_at": "2026-09-06"}]


@pytest.fixture
def setup(tmp_path):
    transport = FixtureTransport()
    gateway = ConnectorGateway(fixture_connection_config(), {"fictional-demo": transport})
    manager = ChangeManager(tmp_path / "changes.sqlite3", gateway)
    return manager, gateway, transport


async def proposal(manager, fields=None):
    return await manager.propose("fictional-demo", "company-001", fields or {"research_summary": "A sourced fictional finding."}, EVIDENCE)


def writes(transport):
    return [call for call in transport.calls if call[0] == "fictional_update_fields"]


async def test_default_proposes_without_writing_and_requires_exact_local_authorization(setup):
    manager, _, transport = setup
    change = await proposal(manager)
    assert change["state"] == "proposed"
    assert not writes(transport)
    assert change["payload"]["account_id"] == "fictional-account"
    assert change["payload"]["record_id"] == "company-001"
    assert change["payload"]["before"]["research_summary"] == "No research saved yet."
    with pytest.raises(ChangeError) as error:
        await manager.apply(change["proposal_id"])
    assert error.value.code == "approval_required"
    with pytest.raises(ChangeError) as error:
        manager.authorize(change["proposal_id"], "not-the-reviewed-hash")
    assert error.value.code == "hash_mismatch"
    manager.authorize(change["proposal_id"], change["payload_hash"])
    applied = await manager.apply(change["proposal_id"])
    assert applied["state"] == "verified"
    assert applied["result"]["readback"]["research_summary"] == "A sourced fictional finding."
    assert len(writes(transport)) == 1
    with pytest.raises(ChangeError):
        await manager.apply(change["proposal_id"])
    assert len(writes(transport)) == 1


async def test_stale_snapshot_stops_before_write(setup):
    manager, _, transport = setup
    change = await proposal(manager)
    manager.authorize(change["proposal_id"], change["payload_hash"])
    transport.records["company-001"]["industry"] = "Changed by another CRM user"
    result = await manager.apply(change["proposal_id"])
    assert result["state"] == "stale"
    assert result["result"]["write_attempted"] is False
    assert not writes(transport)


async def test_changed_connection_invalidates_authorization(setup):
    manager, gateway, transport = setup
    change = await proposal(manager)
    manager.authorize(change["proposal_id"], change["payload_hash"])
    gateway.connections["fictional-demo"]["account_id"] = "other-account"
    with pytest.raises(ChangeError) as error:
        await manager.apply(change["proposal_id"])
    assert error.value.code == "connection_changed"
    assert not writes(transport)


async def test_tampered_stored_payload_is_rejected(setup):
    manager, _, transport = setup
    change = await proposal(manager)
    manager.authorize(change["proposal_id"], change["payload_hash"])
    change["payload"]["fields"]["research_summary"] = "Changed after authorization"
    with closing(sqlite3.connect(manager.db_path)) as db, db:
        db.execute("UPDATE sherlock_changes SET payload=? WHERE id=?", (json.dumps(change["payload"]), change["proposal_id"]))
    with pytest.raises(ChangeError) as error:
        await manager.apply(change["proposal_id"])
    assert error.value.code == "payload_changed"
    assert not writes(transport)


async def test_rejection_and_expiry_do_not_write(setup):
    manager, _, transport = setup
    rejected = await proposal(manager)
    manager.reject(rejected["proposal_id"])
    with pytest.raises(ChangeError):
        manager.authorize(rejected["proposal_id"], rejected["payload_hash"])
    expired = await proposal(manager)
    manager.authorize(expired["proposal_id"], expired["payload_hash"])
    with closing(sqlite3.connect(manager.db_path)) as db, db:
        db.execute("UPDATE sherlock_changes SET expires_at=0 WHERE id=?", (expired["proposal_id"],))
    assert (await manager.apply(expired["proposal_id"]))["state"] == "expired"
    assert not writes(transport)


async def test_one_apply_claim_survives_concurrent_requests(setup):
    manager, _, transport = setup
    change = await proposal(manager)
    manager.authorize(change["proposal_id"], change["payload_hash"])
    results = await asyncio.gather(manager.apply(change["proposal_id"]), manager.apply(change["proposal_id"]), return_exceptions=True)
    assert sum(isinstance(result, ChangeError) for result in results) == 1
    assert len(writes(transport)) == 1
    assert manager.get(change["proposal_id"])["state"] == "verified"


async def test_lost_success_response_is_reconciled_not_retried(setup):
    manager, _, transport = setup
    change = await proposal(manager)
    manager.authorize(change["proposal_id"], change["payload_hash"])
    original = transport.call_tool

    async def lost_response(name, arguments):
        result = await original(name, arguments)
        if name == "fictional_update_fields":
            raise TimeoutError("Bearer private-error-value")
        return result

    transport.call_tool = lost_response
    result = await manager.apply(change["proposal_id"])
    assert result["state"] == "verified"
    assert result["result"]["write_error"] == "transport_timeout"
    assert "private-error-value" not in json.dumps(result)
    assert len(writes(transport)) == 1


async def test_ambiguous_write_does_not_repeat_and_can_be_reconciled(setup):
    manager, _, transport = setup
    change = await proposal(manager)
    manager.authorize(change["proposal_id"], change["payload_hash"])
    original = transport.call_tool
    attempts = []

    async def uncertain(name, arguments):
        if name == "fictional_update_fields":
            attempts.append(arguments)
            raise TimeoutError()
        return await original(name, arguments)

    transport.call_tool = uncertain
    result = await manager.apply(change["proposal_id"])
    assert result["state"] == "outcome_unknown"
    with pytest.raises(ChangeError):
        await manager.apply(change["proposal_id"])
    assert len(attempts) == 1
    # Simulate a late provider commit. Recovery reads only.
    transport.records["company-001"].update(change["payload"]["fields"])
    assert (await manager.reconcile(change["proposal_id"]))["state"] == "verified"
    assert len(attempts) == 1


async def test_partial_provider_save_remains_partial(setup):
    manager, _, transport = setup
    change = await proposal(manager, {"research_summary": "Fictional finding", "industry": "Fictional new industry"})
    manager.authorize(change["proposal_id"], change["payload_hash"])
    original = transport.call_tool

    async def partial(name, arguments):
        if name == "fictional_update_fields":
            arguments = {**arguments, "fields": {"research_summary": arguments["fields"]["research_summary"]}}
        return await original(name, arguments)

    transport.call_tool = partial
    result = await manager.apply(change["proposal_id"])
    assert result["state"] == "partial"
    assert result["result"]["verified_fields"] == ["research_summary"]
    assert len(writes(transport)) == 1


async def test_operator_autosave_policy_is_narrow_and_revocable(setup):
    manager, _, transport = setup
    manager.policy = {"autosave": {"enabled": True, "rules": [{"connection_id": "fictional-demo", "account_id": "fictional-account", "action": "update_fields", "fields": ["research_summary"], "record_ids": ["company-001"]}]}}
    allowed = await proposal(manager)
    denied = await proposal(manager, {"industry": "A different industry"})
    assert allowed["state"] == "approved"
    assert allowed["authorization"] == "operator_policy"
    assert denied["state"] == "proposed"
    manager.policy = {}
    with pytest.raises(ChangeError) as error:
        await manager.apply(allowed["proposal_id"])
    assert error.value.code == "policy_changed"
    assert not writes(transport)


async def test_autosave_explicitly_enabled_rule_applies(setup):
    manager, _, transport = setup
    manager.policy = {"autosave": {"enabled": True, "rules": [{"connection_id": "fictional-demo", "account_id": "fictional-account", "action": "update_fields", "fields": ["research_summary"]}]}}
    change = await proposal(manager)
    assert (await manager.apply(change["proposal_id"]))["state"] == "verified"
    assert len(writes(transport)) == 1


async def test_profile_database_isolation(setup, tmp_path):
    manager, gateway, _ = setup
    change = await proposal(manager)
    other = ChangeManager(tmp_path / "other-profile" / "changes.sqlite3", gateway)
    with pytest.raises(ChangeError) as error:
        other.get(change["proposal_id"])
    assert error.value.code == "unknown_proposal"


async def test_restart_preserves_proposal_and_authorization(setup):
    manager, gateway, _ = setup
    change = await proposal(manager)
    manager.authorize(change["proposal_id"], change["payload_hash"])
    resumed = ChangeManager(manager.db_path, gateway)
    assert (await resumed.apply(change["proposal_id"]))["state"] == "verified"


async def test_noop_and_secret_payloads_are_rejected(setup):
    manager, _, transport = setup
    with pytest.raises(ChangeError) as error:
        await proposal(manager, {"industry": "Design"})
    assert error.value.code == "no_change"
    with pytest.raises(ValueError):
        await proposal(manager, {"api_key": "some credential"})
    with pytest.raises(ChangeError):
        await manager.propose("fictional-demo", "company-001", {"industry": "Other"}, [{"source": "Bearer dont-store-this"}])
    assert not writes(transport)


@pytest.mark.parametrize("header, header_value", [
    ("Authorization", "Bearer {credential}"),
    ("authorization", "bearer {credential}"),
    ("AUTHORIZATION", "\tBEARER\t{credential}\t"),
    ("Proxy-Authorization", "Bearer {credential}"),
    ("pRoXy-AuThOrIzAtIoN", "  bEaReR \t {credential}  "),
])
@pytest.mark.parametrize("location", ["fields", "evidence"])
async def test_bare_bearer_credential_cannot_enter_proposal_storage(setup, monkeypatch, header, header_value, location):
    manager, gateway, transport = setup
    credential = "fictionalProposalCredential.53+/=="
    monkeypatch.setenv("SHERLOCK_TEST_PROPOSAL_HEADER", header_value.format(credential=credential))
    gateway.connections["fictional-demo"]["transport"]["headers_from_env"] = {header: "SHERLOCK_TEST_PROPOSAL_HEADER"}
    fields = {"research_summary": "A sourced fictional finding."}
    evidence = EVIDENCE
    if location == "fields":
        fields["research_summary"] = f"Accidental copied value: {credential}"
    else:
        evidence = [{"source_url": "https://example.com/fictional", "observation": {"copied_value": credential}}]

    with pytest.raises((ChangeError, ConnectorError)) as error:
        await manager.propose("fictional-demo", "company-001", fields, evidence)

    assert error.value.code == "sensitive_payload"
    assert credential not in str(error.value)
    assert not writes(transport)
    assert manager.list_pending() == []
    with closing(sqlite3.connect(manager.db_path)) as db, db:
        assert db.execute("SELECT COUNT(*) FROM sherlock_changes").fetchone()[0] == 0
    assert credential.encode() not in manager.db_path.read_bytes()


async def test_readback_failure_is_unknown_and_recovery_is_read_only(setup):
    manager, gateway, transport = setup
    change = await proposal(manager)
    manager.authorize(change["proposal_id"], change["payload_hash"])
    original = gateway.read_record
    reads = 0

    async def fail_after_write(*args):
        nonlocal reads
        reads += 1
        if reads == 2:
            raise RuntimeError("credential-containing-private-response")
        return await original(*args)

    gateway.read_record = fail_after_write
    result = await manager.apply(change["proposal_id"])
    assert result["state"] == "outcome_unknown"
    assert "credential-containing-private-response" not in json.dumps(result)
    assert (await manager.reconcile(change["proposal_id"]))["state"] == "verified"
    assert len(writes(transport)) == 1
