"""Fictional, deterministic relationship journeys; no connected account data."""
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import sqlite3

import pytest

from agent_sherlock.relationships import Relationships, evaluate
from agent_sherlock.storage import Store, ValidationError, RevisionConflictError, SCHEMA_VERSION

NOW = "2026-09-06T12:00:00Z"


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr("agent_sherlock.relationships._now", lambda: NOW)



def fictional_record(*, moved=False, rid="fictional-person:fictional-acorn"):
    company = "fictional-birch" if moved else "fictional-acorn"
    return {
        "id": rid, "fictional": True,
        "person": {"id": "fictional-person", "name": "Fictional Alex Reed", "linkedin_url": "https://social.example/in/fictional-alex"},
        "original_company": {"verified": True, "id": "fictional-acorn", "name": "Fictional Acorn", "domain": "acorn.example"},
        "owner": {"id": "fictional-owner", "name": "Fictional Owner"},
        "pitch_verified": True,
        "pitch_evidence": [{"source": "crm://fictional/meetings/1", "occurred_at": "2023-08-01T12:00:00Z", "kind": "pitch_meeting"}],
        "last_meaningful_contact_at": "2024-09-06T12:00:00Z", "last_contact_source": "crm://fictional/emails/1",
        "history_coverage": {"status": "complete", "scope": "Fictional CRM logged communications", "exhaustive": False, "checked_at": NOW},
        "current_employment": {"company_id": company, "company_name": "Fictional Birch" if moved else "Fictional Acorn",
            "company_domain": "birch.example" if moved else "acorn.example", "title": "Marketing Director",
            "profile_url": "https://social.example/in/fictional-alex", "observed_at": NOW, "identity_verified": True, "ambiguous": False, "positions": [{"company_id": company}]},
        "source_status": {"company_id": company, "open_deal": False, "active_client": False, "do_not_contact": False,
                          "enrichment_opt_out": False, "recent_outreach_at": None, "verified_at": NOW}, "deal_status": "lost",
    }


@pytest.mark.parametrize("moved,expected", [(False, "dormant_relationship"), (True, "pitched_contact_moved")])
def test_two_skills_preserve_original_pitch_context(moved, expected):
    record = fictional_record(moved=moved)
    if moved:
        record["last_meaningful_contact_at"] = "2026-06-01T12:00:00Z"
    result = evaluate(record, now=NOW)
    assert result["state"] == "ready"
    assert result["skill"] == expected
    assert result["original_company"] == record["original_company"]
    assert result["history_coverage"]["exhaustive"] is False
    assert "declared sources" in result["coverage_note"]


@pytest.mark.parametrize("contact,expected", [("2024-09-06T12:00:00Z", "ready"), ("2024-09-06T12:00:01Z", "not_eligible"),
                                              ("2014-09-06T12:00:00Z", "ready")])
def test_calendar_threshold_and_no_old_age_upper_cutoff(contact, expected):
    record = fictional_record()
    record["last_meaningful_contact_at"] = contact
    record["pitch_evidence"][0]["occurred_at"] = "2014-01-01T00:00:00Z"
    assert evaluate(record, now=NOW)["state"] == expected


def test_leap_day_calendar_anniversary():
    record = fictional_record()
    now = "2026-02-28T12:00:00Z"
    record["last_meaningful_contact_at"] = "2024-02-29T12:00:00Z"
    for obj, key in ((record["history_coverage"], "checked_at"), (record["current_employment"], "observed_at"), (record["source_status"], "verified_at")):
        obj[key] = now
    assert evaluate(record, now=now)["state"] == "not_eligible"
    assert evaluate(record, now="2026-03-01T12:00:00Z")["state"] == "ready"


@pytest.mark.parametrize("path,value,expected", [
    (("pitch_verified",), False, "not_eligible"),
    (("pitch_evidence",), [], "needs_verification"),
    (("last_meaningful_contact_at",), None, "needs_verification"),
    (("last_contact_source",), None, "needs_verification"),
    (("history_coverage", "status"), "partial", "needs_verification"),
    (("history_coverage", "status"), "unavailable", "needs_verification"),
    (("history_coverage", "scope"), "", "needs_verification"),
    (("current_employment", "identity_verified"), False, "needs_verification"),
    (("current_employment", "ambiguous"), True, "needs_verification"),
    (("current_employment", "observed_at"), "2026-08-29T12:00:00Z", "needs_verification"),
    (("current_employment", "observed_at"), "2026-09-07T12:00:00Z", "needs_verification"),
    (("current_employment", "profile_url"), None, "needs_verification"),
    (("source_status", "company_id"), "another-company", "needs_verification"),
    (("source_status", "open_deal"), True, "suppressed"),
    (("source_status", "active_client"), True, "suppressed"),
    (("source_status", "active_client"), None, "needs_verification"),
    (("source_status", "do_not_contact"), True, "suppressed"),
    (("source_status", "enrichment_opt_out"), True, "suppressed"),
    (("source_status", "recent_outreach_at"), "2026-08-20T12:00:00Z", "suppressed"),
    (("last_meaningful_contact_at",), "2026-08-20T12:00:00Z", "suppressed"),
])
def test_gates(path, value, expected):
    record = fictional_record()
    obj = record
    for key in path[:-1]:
        obj = obj[key]
    obj[path[-1]] = value
    assert evaluate(record, now=NOW)["state"] == expected


def test_multiple_employers_and_new_pitch_do_not_fabricate_dormancy():
    record = fictional_record()
    record["current_employment"]["positions"].append({"company_id": "fictional-birch"})
    assert evaluate(record, now=NOW)["state"] == "needs_verification"
    record = fictional_record()
    record["pitch_evidence"][0]["occurred_at"] = "2026-01-01T00:00:00Z"
    assert "pitch_newer_than_last_contact" in evaluate(record, now=NOW)["reasons"]


def test_import_revision_history_and_unchanged_retry(tmp_path):
    with Store(tmp_path / "cases.sqlite3", "alpha") as store:
        service = Relationships(store)
        record = fictional_record()
        created = service.upsert(record)
        assert service.upsert(record)["changed"] is False
        assert len(store.list_cases()) == 1
        moved = fictional_record(moved=True)
        with pytest.raises(RevisionConflictError):
            service.upsert(moved)
        saved = service.upsert(moved, expected_revision=created["revision"], reason="Verified employer changed")
        loaded = service.get(record["id"], include_history=True)
        assert loaded["record"]["original_company"] == record["original_company"]
        assert loaded["history"][0]["record"]["current_employment"]["company_id"] == "fictional-acorn"
        assert store.get_case(saved["case_id"])["relationship"]["id"] == record["id"]
        assert store.recall_count()["count"] == 0  # Pitch relationships never become clients.
        assert service.get(record["id"])["revision"] == 2


def test_import_batch_atomic_and_stable_identity(tmp_path):
    with Store(tmp_path / "cases.sqlite3", "alpha") as store:
        service = Relationships(store)
        first = fictional_record()
        duplicate = fictional_record(rid="second-id-for-same-person-company")
        with pytest.raises(ValidationError, match="already have"):
            service.import_records([first, duplicate])
        assert store.list_cases() == []
        assert service.list()["relationships"] == []
        service.upsert(first)
        changed_person = deepcopy(first)
        changed_person["person"]["id"] = "different-person"
        with pytest.raises(ValidationError, match="cannot change"):
            service.upsert(changed_person, expected_revision=1, reason="Attempted identity replacement")


def test_queue_idempotence_move_supersedes_and_feedback_survives_restart(tmp_path):
    path = tmp_path / "cases.sqlite3"
    with Store(path, "alpha") as store:
        service = Relationships(store)
        original = service.upsert(fictional_record())
        first = service.evaluate_all(now=NOW)["results"][0]
        second = service.evaluate_all(now=NOW)["results"][0]
        assert first["review_id"] == second["review_id"]
        assert len(service.queue()["reviews"]) == 1
        current = service.queue()["reviews"][0]
        feedback = service.feedback(current["id"], "exclude", expected_revision=current["revision"])
        assert feedback["state"] == "suppressed"
    with Store(path, "alpha") as store:
        service = Relationships(store)
        existing = service.get(original["id"])
        service.upsert(fictional_record(moved=True), expected_revision=existing["revision"], reason="Verified new employer")
        result = service.evaluate_all(now=NOW)["results"][0]
        assert result["state"] == "suppressed"
        assert service.queue()["reviews"] == []
        assert len(service.queue(state="superseded")["reviews"]) == 1


def test_moved_queue_deduplicates_two_original_pitch_companies(tmp_path):
    with Store(tmp_path / "cases.sqlite3", "alpha") as store:
        service = Relationships(store)
        first = fictional_record(moved=True)
        second = deepcopy(first)
        second["id"] = "same-person:another-pitched-company"
        second["original_company"] = {"verified": True, "id": "fictional-cedar", "name": "Fictional Cedar", "domain": "cedar.example"}
        service.import_records([first, second])
        service.evaluate_all(now=NOW)
        assert len(service.queue()["reviews"]) == 1
        assert len(service.list()["relationships"]) == 2


def test_feedback_revision_and_reopen_optout(tmp_path):
    with Store(tmp_path / "cases.sqlite3", "alpha") as store:
        service = Relationships(store)
        service.upsert(fictional_record())
        service.evaluate_all(now=NOW)
        review = service.queue()["reviews"][0]
        excluded = service.feedback(review["id"], "enrichment_opt_out", expected_revision=review["revision"])
        with pytest.raises(RevisionConflictError):
            service.feedback(review["id"], "reopen", expected_revision=review["revision"], note="Owner corrected preference")
        reopened = service.feedback(review["id"], "reopen", expected_revision=excluded["revision"], note="Owner opted back in", clear_holds=["enrichment_opt_out"])
        assert reopened["state"] == "needs_verification"
        service.evaluate_all(now=NOW)
        assert len(service.queue()["reviews"]) == 1


def test_pagination_no_older_records_lost(tmp_path):
    with Store(tmp_path / "cases.sqlite3", "alpha") as store:
        service = Relationships(store)
        for index in range(3):
            record = fictional_record(rid=f"record-{index}")
            record["person"]["id"] = f"fictional-person-{index}"
            service.upsert(record)
        first = service.list(limit=2)
        assert len(first["relationships"]) == 2 and first["next_cursor"]
        assert len(service.list(limit=2, after_id=first["next_cursor"])["relationships"]) == 1
        first = service.evaluate_all(now=NOW, limit=2)
        assert first["evaluated"] == 2
        assert service.evaluate_all(now=NOW, limit=2, after_id=first["next_cursor"])["evaluated"] == 1
        assert len(service.queue()["reviews"]) == 3


def test_export_backup_isolation_deletion_and_v1_migration(tmp_path):
    path = tmp_path / "shared.sqlite3"
    with Store(path, "alpha") as store:
        case = store.create_case("Fictional Existing", "fictional-existing")
        revision = case["revision"]
    # Reproduce a genuine pre-feature schema, keeping existing case content.
    with closing(sqlite3.connect(path)) as db, db:
        for table in ("relationship_review_events", "relationship_reviews", "relationship_history", "relationships"):
            db.execute("DROP TABLE " + table)
        db.execute("PRAGMA user_version=1")
    with Store(path, "alpha") as store:
        assert store.get_case(case["id"])["revision"] == revision
        assert store._conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        service = Relationships(store)
        relation = service.upsert(fictional_record())
        service.evaluate_all(now=NOW)
        assert len(store.export_profile()["relationships"]) == 1
    with Store(path, "beta") as store:
        assert Relationships(store).list()["relationships"] == []
        Relationships(store).upsert(fictional_record(rid="other-profile-private"))
    with Store(path, "alpha") as store:
        destination = store.backup(tmp_path / "snapshot.sqlite3")
        assert "other-profile-private" not in json.dumps(store.export_profile())
        assert store.delete_case(relation["case_id"])
        assert Relationships(store).list()["relationships"] == []
        assert Relationships(store).queue(state=None)["reviews"] == []
        for table in ("relationship_history", "relationship_review_events"):
            assert not store._conn.execute(f"SELECT 1 FROM {table} WHERE profile='alpha'").fetchone()
    with Store(destination, "alpha") as store:
        assert len(Relationships(store).list()["relationships"]) == 1
    with Store(destination, "beta") as store:
        assert Relationships(store).list()["relationships"] == []


def test_secrets_and_invalid_flags_cannot_enter_relationship_state(tmp_path):
    with Store(tmp_path / "cases.sqlite3", "alpha") as store:
        service = Relationships(store)
        record = fictional_record()
        record["person"]["password"] = "private"
        with pytest.raises(ValidationError, match="credential"):
            service.upsert(record)
        record = fictional_record()
        record["source_status"]["open_deal"] = "false"
        with pytest.raises(ValidationError, match="true, false"):
            service.upsert(record)
        assert service.list()["relationships"] == []


def test_stale_ready_card_is_not_presented_as_fresh_without_an_evaluation(monkeypatch, tmp_path):
    with Store(tmp_path / "cases.sqlite3", "alpha") as store:
        service = Relationships(store)
        service.upsert(fictional_record())
        service.evaluate_all(now=NOW)
        assert len(service.queue()["reviews"]) == 1
        monkeypatch.setattr("agent_sherlock.relationships._now", lambda: "2026-09-15T12:00:00Z")
        assert service.queue()["reviews"] == []
        assert service.queue(state="needs_verification")["reviews"][0]["refresh_required"] is True


def test_identical_evaluation_does_not_invalidate_owner_revision(tmp_path):
    with Store(tmp_path / "cases.sqlite3", "alpha") as store:
        service = Relationships(store)
        service.upsert(fictional_record())
        service.evaluate_all(now=NOW)
        review = service.queue()["reviews"][0]
        service.evaluate_all(now=NOW)
        assert service.queue()["reviews"][0]["revision"] == review["revision"]


def test_latest_person_employer_observation_resolves_older_pitch_snapshots(tmp_path):
    with Store(tmp_path / "cases.sqlite3", "alpha") as store:
        service = Relationships(store)
        original = fictional_record()
        original["current_employment"]["observed_at"] = "2026-09-05T12:00:00Z"
        service.upsert(original)
        service.evaluate_all(now=NOW)
        other = fictional_record(moved=True, rid="same-person:fictional-cedar")
        other["original_company"] = {"verified": True, "id": "fictional-cedar", "name": "Fictional Cedar"}
        service.upsert(other)
        assert service.queue()["reviews"] == []  # Earlier same-company card invalidated on read.
        service.evaluate_all(now=NOW)
        reviews = service.queue()["reviews"]
        assert len(reviews) == 1
        assert reviews[0]["target_company_id"] == "fictional-birch"
        revision = reviews[0]["revision"]
        service.evaluate_all(now=NOW)
        assert service.queue()["reviews"][0]["revision"] == revision


def test_matching_timestamp_conflicting_employers_need_verification(tmp_path):
    with Store(tmp_path / "cases.sqlite3", "alpha") as store:
        service = Relationships(store)
        first = fictional_record()
        second = fictional_record(moved=True, rid="same-person:fictional-cedar")
        second["original_company"] = {"verified": True, "id": "fictional-cedar", "name": "Fictional Cedar"}
        service.import_records([first, second])
        service.evaluate_all(now=NOW)
        assert service.queue()["reviews"] == []
        assert all(r["state"] == "needs_verification" for r in service.queue(state=None)["reviews"])


def test_already_pitched_destination_uses_its_dormant_relationship(tmp_path):
    with Store(tmp_path / "cases.sqlite3", "alpha") as store:
        service = Relationships(store)
        first = fictional_record(moved=True)
        second = fictional_record(moved=True, rid="same-person:fictional-birch")
        second["original_company"] = {"verified": True, "id": "fictional-birch", "name": "Fictional Birch"}
        service.import_records([first, second])
        service.evaluate_all(now=NOW)
        reviews = service.queue()["reviews"]
        assert len(reviews) == 1
        assert reviews[0]["skill"] == "dormant_relationship"


def test_old_call_and_newer_email_do_not_create_a_dormant_card():
    record = fictional_record()
    record["last_meaningful_contact_at"] = "2023-09-01T12:00:00Z"
    record["source_status"]["recent_outreach_at"] = "2025-03-01T12:00:00Z"
    result = evaluate(record, now=NOW)
    assert result["state"] == "needs_verification"
    assert result["reasons"] == ["newer_outreach_requires_contact_review"]
    moved = fictional_record(moved=True)
    moved["source_status"]["recent_outreach_at"] = "2025-03-01T12:00:00Z"
    assert evaluate(moved, now=NOW)["state"] == "ready"


def test_supplied_company_name_without_historical_verification_is_not_ready():
    record = fictional_record()
    record["original_company"].pop("verified")
    assert evaluate(record, now=NOW)["state"] == "needs_verification"


def test_owner_outcomes_are_retrievable_and_do_not_convert_source_flags_to_local_optouts(tmp_path):
    with Store(tmp_path / "cases.sqlite3", "alpha") as store:
        service = Relationships(store)
        record = fictional_record()
        record["source_status"]["do_not_contact"] = True
        service.upsert(record)
        service.evaluate_all(now=NOW)
        review = service.queue(state="suppressed")["reviews"][0]
        service.feedback(review["id"], "outcome", expected_revision=review["revision"], note="Fictional owner confirmed source record needs correction")
        saved = service.get(record["id"], include_history=True)
        assert saved["local_state"] == {}
        assert saved["review_events"][0]["action"] == "outcome"
        record["source_status"]["do_not_contact"] = False
        service.upsert(record, expected_revision=saved["revision"], reason="Corrected fictional source flag")
        service.evaluate_all(now=NOW)
        assert len(service.queue()["reviews"]) == 1


def test_unverified_company_record_does_not_replace_a_verified_move_anchor(tmp_path):
    with Store(tmp_path / "cases.sqlite3", "alpha") as store:
        service = Relationships(store)
        verified = fictional_record(moved=True)
        unverified = fictional_record(moved=True, rid="unverified-history")
        unverified["original_company"] = {"id": "fictional-cedar", "name": "Fictional Cedar", "verified": False}
        unverified["pitch_evidence"][0]["occurred_at"] = "2025-01-01T00:00:00Z"
        service.import_records([verified, unverified])
        service.evaluate_all(now=NOW)
        review = service.queue()["reviews"][0]
        assert review["relationship_id"] == verified["id"]
        assert review["result"]["original_company"]["verified"] is True


def test_recent_pitch_itself_suppresses_a_move_even_with_incomplete_contact_normalization():
    record = fictional_record(moved=True)
    record["pitch_evidence"][0]["occurred_at"] = "2026-09-01T00:00:00Z"
    assert evaluate(record, now=NOW)["reasons"] == ["recent_pitch_contact"]
    record["pitch_evidence"][0]["occurred_at"] = "2026-05-01T00:00:00Z"
    assert evaluate(record, now=NOW)["reasons"] == ["pitch_newer_than_last_contact"]


def test_reopen_does_not_clear_unrelated_person_exclusions(tmp_path):
    with Store(tmp_path / "cases.sqlite3", "alpha") as store:
        service = Relationships(store)
        service.upsert(fictional_record())
        service.evaluate_all(now=NOW)
        review = service.queue()["reviews"][0]
        excluded = service.feedback(review["id"], "exclude", expected_revision=review["revision"])
        reopened = service.feedback(review["id"], "reopen", expected_revision=excluded["revision"], note="Only reconsider this review")
        assert reopened["state"] == "suppressed"
        assert reopened["feedback_scope"]["cleared_holds"] == []
        assert reopened["feedback_scope"]["remaining_person_state"]["excluded"] is True
        service.evaluate_all(now=NOW)
        assert service.queue()["reviews"] == []


def test_already_in_touch_cooldown_is30days_for_a_new_employer(monkeypatch, tmp_path):
    with Store(tmp_path / "cases.sqlite3", "alpha") as store:
        service = Relationships(store)
        relation = service.upsert(fictional_record())
        service.evaluate_all(now=NOW)
        review = service.queue()["reviews"][0]
        service.feedback(review["id"], "already_in_touch", expected_revision=review["revision"])
        moved = fictional_record(moved=True)
        current = service.get(relation["id"])
        service.upsert(moved, expected_revision=current["revision"], reason="Verified new employer")
        assert service.evaluate_all(now=NOW)["results"][0]["state"] == "suppressed"
        later = "2026-10-07T12:00:00Z"
        for obj, key in ((moved["history_coverage"], "checked_at"), (moved["current_employment"], "observed_at"), (moved["source_status"], "verified_at")):
            obj[key] = later
        current = service.get(relation["id"])
        service.upsert(moved, expected_revision=current["revision"], reason="New dated source refresh")
        monkeypatch.setattr("agent_sherlock.relationships._now", lambda: later)
        result = service.evaluate_all(now=later)["results"][0]
        assert result["state"] == "ready"
        assert service.queue()["reviews"][0]["skill"] == "pitched_contact_moved"


def test_never_pitched_feedback_holds_sibling_relationships_and_future_imports(tmp_path):
    with Store(tmp_path / "cases.sqlite3", "alpha") as store:
        service = Relationships(store)
        first = fictional_record(moved=True)
        second = fictional_record(moved=True, rid="same-person:fictional-cedar")
        second["original_company"] = {"id": "fictional-cedar", "name": "Fictional Cedar", "verified": True}
        service.import_records([first, second])
        service.evaluate_all(now=NOW)
        review = service.queue()["reviews"][0]
        service.feedback(review["id"], "never_pitched", expected_revision=review["revision"], note="Owner says this person's supposed pitch history needs review")
        third = fictional_record(moved=True, rid="same-person:fictional-maple")
        third["original_company"] = {"id": "fictional-maple", "name": "Fictional Maple", "verified": True}
        service.upsert(third)
        service.evaluate_all(now=NOW)
        assert service.queue()["reviews"] == []
        assert all(r["result"]["reasons"] == ["never_pitched"] for r in service.queue(state="needs_verification")["reviews"])


def test_snooze_survives_domain_and_profile_locator_changes(tmp_path):
    with Store(tmp_path / "cases.sqlite3", "alpha") as store:
        service = Relationships(store)
        record = fictional_record(moved=True)
        relation = service.upsert(record)
        service.evaluate_all(now=NOW)
        review = service.queue()["reviews"][0]
        service.feedback(review["id"], "snooze", expected_revision=review["revision"], until="2026-12-01T00:00:00Z")
        record["current_employment"].pop("company_domain")
        record["current_employment"]["profile_url"] = "https://social.example/in/fictional-alex-renamed"
        service.upsert(record, expected_revision=service.get(relation["id"])["revision"], reason="Same company ID with updated profile locator")
        service.evaluate_all(now=NOW)
        snoozed = service.queue(state="snoozed")["reviews"]
        assert len(snoozed) == 1
        assert snoozed[0]["id"] == review["id"]
        assert service.queue()["reviews"] == []


@pytest.mark.parametrize("adverse", ["recent_outreach", "ambiguous", "unverified_identity", "conflicting_position"])
def test_equal_time_peer_observations_preserve_adverse_signals(tmp_path, adverse):
    with Store(tmp_path / "cases.sqlite3", "alpha") as store:
        service = Relationships(store)
        first = fictional_record(moved=True, rid="a-first-record")
        second = fictional_record(moved=True, rid="z-later-record")
        second["original_company"] = {"id": "fictional-cedar", "name": "Fictional Cedar", "verified": True}
        if adverse == "recent_outreach":
            second["source_status"]["recent_outreach_at"] = "2026-09-01T12:00:00Z"
        elif adverse == "ambiguous":
            second["current_employment"]["ambiguous"] = True
        elif adverse == "unverified_identity":
            second["current_employment"]["identity_verified"] = False
        else:
            second["current_employment"]["positions"].append({"company_id": "fictional-other-employer"})
        service.import_records([first, second])
        results = service.evaluate_all(now=NOW)["results"]
        assert service.queue()["reviews"] == []
        assert all(result["state"] in ("suppressed", "needs_verification") for result in results)
