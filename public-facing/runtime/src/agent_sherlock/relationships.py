"""Deterministic, profile-local reviews of proven pitch relationships.

The host supplies dated source observations. This module neither collects data,
schedules itself, sends outreach, nor mutates a CRM.
"""
from __future__ import annotations

import calendar
from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any
from uuid import uuid4

from .storage import (Store, ValidationError, NotFoundError, RevisionConflictError,
                      _metadata, _text, _observed_at, _source_uri, _now)

CONTRACT_VERSION = 1
SKILLS = ("dormant_relationship", "pitched_contact_moved")
FEEDBACK = ("reconnect", "already_in_touch", "wrong_identity", "wrong_employer",
            "never_pitched", "snooze", "exclude", "enrichment_opt_out", "reopen", "outcome")
DEFAULTS = {"dormant_months": 24, "freshness_days": 7, "recent_outreach_days": 30}

SCHEMA = """
CREATE TABLE IF NOT EXISTS relationships (
 profile TEXT NOT NULL, id TEXT NOT NULL, case_id TEXT NOT NULL,
 person_id TEXT NOT NULL, pitch_company_id TEXT NOT NULL,
 revision INTEGER NOT NULL, record_json TEXT NOT NULL, local_state TEXT NOT NULL,
 updated_at TEXT NOT NULL, PRIMARY KEY(profile,id),
 UNIQUE(profile,person_id,pitch_company_id), UNIQUE(profile,case_id),
 FOREIGN KEY(profile,case_id) REFERENCES cases(profile,id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS relationship_history (
 profile TEXT NOT NULL, relationship_id TEXT NOT NULL, revision INTEGER NOT NULL,
 snapshot TEXT NOT NULL, reason TEXT NOT NULL, recorded_at TEXT NOT NULL,
 PRIMARY KEY(profile,relationship_id,revision),
 FOREIGN KEY(profile,relationship_id) REFERENCES relationships(profile,id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS relationship_reviews (
 profile TEXT NOT NULL, id TEXT NOT NULL, relationship_id TEXT NOT NULL,
 person_id TEXT NOT NULL, skill TEXT NOT NULL, target_company_id TEXT NOT NULL,
 state TEXT NOT NULL, result_json TEXT NOT NULL, revision INTEGER NOT NULL,
 decision TEXT, snoozed_until TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 PRIMARY KEY(profile,id), UNIQUE(profile,person_id,skill,target_company_id),
 FOREIGN KEY(profile,relationship_id) REFERENCES relationships(profile,id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS relationship_review_events (
 profile TEXT NOT NULL, id TEXT NOT NULL, review_id TEXT NOT NULL,
 action TEXT NOT NULL, note TEXT NOT NULL, recorded_at TEXT NOT NULL,
 PRIMARY KEY(profile,id),
 FOREIGN KEY(profile,review_id) REFERENCES relationship_reviews(profile,id) ON DELETE CASCADE
);
"""


def _date(value: str) -> datetime:
    return datetime.fromisoformat(_observed_at(value).replace("Z", "+00:00"))


def _month_cutoff(now: datetime, months: int) -> datetime:
    year, month = divmod(now.year * 12 + now.month - 1 - months, 12)
    month += 1
    return now.replace(year=year, month=month, day=min(now.day, calendar.monthrange(year, month)[1]))


def _object(value: Any, name: str) -> dict:
    if not isinstance(value, dict):
        raise ValidationError(f"{name} must be an object")
    return value


def _bools(data: dict, names: tuple[str, ...], label: str) -> None:
    for name in names:
        if name in data and data[name] is not None and type(data[name]) is not bool:
            raise ValidationError(f"{label}.{name} must be true, false, or null")


def normalize(record: dict) -> dict:
    """Validate the portable v1 contract; do not guess missing evidence."""
    data = json.loads(_metadata(_object(record, "record")))
    allowed = {"id", "person", "original_company", "owner", "pitch_verified", "pitch_evidence",
               "last_meaningful_contact_at", "last_contact_source", "history_coverage",
               "current_employment", "source_status", "deal_status", "fictional"}
    if set(data) - allowed:
        raise ValidationError("Unknown relationship fields: " + ", ".join(sorted(set(data) - allowed)))
    for key in ("person", "original_company"):
        obj = _object(data.get(key), key)
        obj["id"] = _text(obj.get("id"), key + ".id", 300)
        obj["name"] = _text(obj.get("name"), key + ".name", 300)
    key = data["person"]["id"] + "\0" + data["original_company"]["id"]
    data["id"] = _text(data.get("id") or hashlib.sha256(key.encode()).hexdigest(), "id", 300)
    _bools(data, ("pitch_verified", "fictional"), "record")
    _bools(data["original_company"], ("verified",), "original_company")
    if data["original_company"].get("source"):
        data["original_company"]["source"] = _source_uri(data["original_company"]["source"])
    if data.get("deal_status") not in (None, "open", "won", "lost", "unknown"):
        raise ValidationError("deal_status must be open, won, lost, or unknown")
    pitches = data.get("pitch_evidence", [])
    if not isinstance(pitches, list) or len(pitches) > 100:
        raise ValidationError("pitch_evidence must contain at most 100 bounded evidence objects")
    for item in pitches:
        item = _object(item, "pitch evidence")
        item["source"] = _source_uri(item.get("source"))
        item["occurred_at"] = _observed_at(item.get("occurred_at"))
        item["kind"] = _text(item.get("kind"), "pitch evidence kind", 100)
        if item.get("observed_at") is not None:
            item["observed_at"] = _observed_at(item["observed_at"])
    data["pitch_evidence"] = pitches
    for key in ("owner", "history_coverage", "current_employment", "source_status"):
        data[key] = _object(data.get(key, {}), key)
    coverage, employment, status = data["history_coverage"], data["current_employment"], data["source_status"]
    if coverage.get("status") not in (None, "complete", "partial", "unavailable"):
        raise ValidationError("history_coverage.status must be complete, partial, or unavailable")
    _bools(coverage, ("exhaustive",), "history_coverage")
    if coverage.get("scope") is not None:
        coverage["scope"] = _text(coverage["scope"], "history_coverage.scope", 1000, empty=True)
    if status.get("source"):
        status["source"] = _source_uri(status["source"])
    _bools(employment, ("identity_verified", "ambiguous"), "current_employment")
    _bools(status, ("open_deal", "active_client", "do_not_contact", "enrichment_opt_out"), "source_status")
    for container, key in ((data, "last_meaningful_contact_at"), (coverage, "checked_at"),
                           (employment, "observed_at"), (status, "verified_at"), (status, "recent_outreach_at")):
        if container.get(key) is not None:
            container[key] = _observed_at(container[key])
    for container, key in ((employment, "company_id"), (status, "company_id")):
        if container.get(key) is not None:
            container[key] = _text(container[key], key, 300)
    for container, key in ((data["person"], "linkedin_url"), (employment, "profile_url")):
        if container.get(key):
            container[key] = _source_uri(container[key])
    if data.get("last_contact_source"):
        data["last_contact_source"] = _source_uri(data["last_contact_source"])
    positions = employment.get("positions", [])
    if not isinstance(positions, list) or any(not isinstance(p, dict) for p in positions):
        raise ValidationError("current_employment.positions must be a list of objects")
    for item in positions:
        if item.get("company_id") is not None:
            item["company_id"] = _text(item["company_id"], "position company_id", 300)
    return data


def policy_config(policy: dict | None = None) -> dict:
    result = dict(DEFAULTS)
    if policy is not None:
        if not isinstance(policy, dict) or set(policy) - set(DEFAULTS):
            raise ValidationError("Relationship policy accepts dormant_months, freshness_days, recent_outreach_days")
        result.update(policy)
    ranges = {"dormant_months": (24, 120), "freshness_days": (1, 30), "recent_outreach_days": (1, 365)}
    for key, (low, high) in ranges.items():
        if type(result[key]) is not int or not low <= result[key] <= high:
            raise ValidationError(f"{key} must be an integer from {low} to {high}")
    return result


def evaluate(record: dict, *, now: str | None = None, policy: dict | None = None,
             local_state: dict | None = None) -> dict:
    """Pure classification. Complete coverage refers only to named sources."""
    data = normalize(record)
    at = _date(now or _now())
    rules = policy_config(policy)
    employment, coverage, status = data["current_employment"], data["history_coverage"], data["source_status"]
    target = employment.get("company_id")
    original = data["original_company"]["id"]
    skill = "dormant_relationship" if target == original else "pitched_contact_moved" if target else None
    result = {"relationship_id": data["id"], "person": data["person"], "original_company": data["original_company"],
              "owner": data["owner"], "skill": skill, "target_company_id": target,
              "current_employment": employment, "pitch_evidence": data["pitch_evidence"],
              "last_meaningful_contact_at": data.get("last_meaningful_contact_at"),
              "last_contact_source": data.get("last_contact_source"), "history_coverage": coverage, "source_status": status,
              "evaluated_at": at.isoformat().replace("+00:00", "Z"), "policy": rules,
              "state": "needs_verification", "reasons": [],
              "coverage_note": "Latest meaningful conversation found in the declared sources; unlogged or unavailable communications may exist."}

    def finish(state: str, *reasons: str) -> dict:
        result.update(state=state, reasons=list(reasons))
        return result

    local = local_state or {}
    if local.get("excluded") or status.get("do_not_contact") is True:
        return finish("suppressed", "do_not_contact")
    if local.get("enrichment_opt_out") or status.get("enrichment_opt_out") is True:
        return finish("suppressed", "enrichment_opt_out")
    if local.get("verification_required"):
        return finish("needs_verification", local["verification_required"])
    if local.get("recent_owner_contact_at") and _date(local["recent_owner_contact_at"]) >= at - timedelta(days=rules["recent_outreach_days"]):
        return finish("suppressed", "recent_owner_confirmed_contact")
    if data["original_company"].get("verified") is not True:
        return finish("needs_verification", "original_pitch_company_unverified")
    if data.get("pitch_verified") is not True:
        return finish("not_eligible", "actual_pitch_not_verified")
    if not data["pitch_evidence"]:
        return finish("needs_verification", "pitch_evidence_missing")
    latest_pitch = max(_date(p["occurred_at"]) for p in data["pitch_evidence"])
    if latest_pitch > at:
        return finish("needs_verification", "future_pitch_evidence")
    if latest_pitch >= at - timedelta(days=rules["recent_outreach_days"]):
        return finish("suppressed", "recent_pitch_contact")
    if employment.get("identity_verified") is not True or employment.get("ambiguous") is not False:
        return finish("needs_verification", "person_or_employer_ambiguous")
    position_ids = {p.get("company_id") for p in employment.get("positions", []) if p.get("company_id")}
    if not target or (position_ids and position_ids != {target}):
        return finish("needs_verification", "current_employer_not_resolved")
    if not employment.get("profile_url"):
        return finish("needs_verification", "employment_source_missing")
    fresh_after = at - timedelta(days=rules["freshness_days"])
    for key, value in (("employment", employment.get("observed_at")), ("source_status", status.get("verified_at"))):
        if not value or not fresh_after <= _date(value) <= at:
            return finish("needs_verification", key + "_stale_or_unavailable")
    # The destination-company ID must be resolved by the importer. Domain aliases
    # can be reconciled upstream, but names and domains alone never rewrite IDs.
    if status.get("company_id") != target:
        return finish("needs_verification", "destination_status_not_bound")
    for flag in ("do_not_contact", "enrichment_opt_out", "active_client", "open_deal"):
        if status.get(flag) is True:
            return finish("suppressed", flag)
        if status.get(flag) is not False:
            return finish("needs_verification", flag + "_unknown")
    outreach = status.get("recent_outreach_at")
    if outreach and _date(outreach) > at:
        return finish("needs_verification", "future_outreach_timestamp")
    if outreach and _date(outreach) >= at - timedelta(days=rules["recent_outreach_days"]):
        return finish("suppressed", "recent_outreach")
    if coverage.get("status") == "unavailable" or not coverage.get("status"):
        return finish("needs_verification", "history_unavailable")
    if coverage.get("status") != "complete":
        return finish("needs_verification", "history_partial")
    if not coverage.get("scope") or not coverage.get("checked_at") or not fresh_after <= _date(coverage["checked_at"]) <= at:
        return finish("needs_verification", "history_scope_or_freshness_missing")
    contact = data.get("last_meaningful_contact_at")
    if contact and (_date(contact) > at or not data.get("last_contact_source")):
        return finish("needs_verification", "contact_date_or_source_invalid")
    if contact and _date(contact) >= at - timedelta(days=rules["recent_outreach_days"]):
        return finish("suppressed", "recent_meaningful_contact")
    if contact and latest_pitch > _date(contact):
        return finish("needs_verification", "pitch_newer_than_last_contact")
    if skill == "dormant_relationship":
        if outreach and _date(outreach) > _month_cutoff(at, rules["dormant_months"]):
            return finish("needs_verification", "newer_outreach_requires_contact_review")
        if not contact:
            return finish("needs_verification", "last_meaningful_contact_unknown")
        if _date(contact) > _month_cutoff(at, rules["dormant_months"]):
            return finish("not_eligible", "dormancy_threshold_not_met")
        result["age_band"] = "24_to_36_months" if _date(contact) > _month_cutoff(at, 36) else "36_months_or_older"
    return finish("ready", "same_company_dormant" if skill == "dormant_relationship" else "verified_new_company")


class Relationships:
    def __init__(self, store: Store, policy: dict | None = None):
        self.store = store
        self.policy = policy_config(policy)

    def _row(self, relationship_id: str):
        row = self.store._conn.execute("SELECT * FROM relationships WHERE profile=? AND id=?", (self.store.profile, relationship_id)).fetchone()
        if row is None:
            raise NotFoundError("Relationship not found in this profile")
        return row

    @staticmethod
    def _public(row) -> dict:
        return {"id": row["id"], "case_id": row["case_id"], "revision": row["revision"],
                "record": json.loads(row["record_json"]), "local_state": json.loads(row["local_state"]), "updated_at": row["updated_at"]}

    def get(self, relationship_id: str, *, include_history: bool = False) -> dict:
        with self.store._transaction():
            result = self._public(self._row(relationship_id))
            if include_history:
                result["history"] = [dict(revision=r["revision"], record=json.loads(r["snapshot"]), reason=r["reason"], recorded_at=r["recorded_at"])
                                     for r in self.store._conn.execute("SELECT * FROM relationship_history WHERE profile=? AND relationship_id=? ORDER BY revision", (self.store.profile, relationship_id))]
                result["review_events"] = [dict(r) for r in self.store._conn.execute(
                    "SELECT e.id,e.review_id,e.action,e.note,e.recorded_at FROM relationship_review_events e JOIN relationship_reviews r ON r.profile=e.profile AND r.id=e.review_id WHERE r.profile=? AND r.person_id=? ORDER BY e.recorded_at,e.id",
                    (self.store.profile, result["record"]["person"]["id"]))]
            return result

    def list(self, *, limit: int = 100, after_id: str | None = None) -> dict:
        self._limit(limit)
        with self.store._transaction():
            rows = self.store._conn.execute("SELECT * FROM relationships WHERE profile=? AND id>? ORDER BY id LIMIT ?", (self.store.profile, after_id or "", limit + 1)).fetchall()
            return {"relationships": [self._public(r) for r in rows[:limit]], "next_cursor": rows[limit-1]["id"] if len(rows) > limit else None}

    @staticmethod
    def _limit(limit: int) -> None:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValidationError("limit must be an integer from 1 to 100")

    def upsert(self, record: dict, *, expected_revision: int | None = None, reason: str = "") -> dict:
        return self.import_records([{"record": record, "expected_revision": expected_revision, "reason": reason}])["relationships"][0]

    def import_records(self, records: list[dict]) -> dict:
        if not isinstance(records, list) or not 1 <= len(records) <= 100:
            raise ValidationError("Import 1 to 100 relationship records per batch")
        prepared = []
        for entry in records:
            entry = _object(entry, "import entry")
            record = normalize(entry.get("record", entry))
            revision = entry.get("expected_revision") if "record" in entry else None
            if revision is not None and (type(revision) is not int or revision < 1):
                raise ValidationError("expected_revision must be a positive integer")
            prepared.append((record, revision, _text(entry.get("reason", ""), "reason", 1000, empty=True)))
        if len({d[0]["id"] for d in prepared}) != len(prepared):
            raise ValidationError("A batch must not repeat a relationship ID")
        with self.store._transaction(write=True):
            return {"relationships": [self._upsert(*item) for item in prepared], "provider_calls": 0}

    def _upsert(self, record: dict, expected_revision: int | None, reason: str) -> dict:
        db, profile = self.store._conn, self.store.profile
        rid = record["id"]
        person_id, company_id = record["person"]["id"], record["original_company"]["id"]
        row = db.execute("SELECT * FROM relationships WHERE profile=? AND id=?", (profile, rid)).fetchone()
        other = db.execute("SELECT id FROM relationships WHERE profile=? AND person_id=? AND pitch_company_id=?", (profile, person_id, company_id)).fetchone()
        if other and other["id"] != rid:
            raise ValidationError("This person and pitch company already have a relationship; use its stable ID")
        encoded = json.dumps(record, sort_keys=True, ensure_ascii=False)
        timestamp = _now()
        if row:
            if (row["person_id"], row["pitch_company_id"]) != (person_id, company_id):
                raise ValidationError("A relationship cannot change its person or original pitch company identity")
            if row["record_json"] == encoded:
                return dict(self._public(row), changed=False)
            if expected_revision != row["revision"]:
                raise RevisionConflictError("Relationship changed; read its current revision before updating")
            if not reason:
                raise ValidationError("Updating relationship evidence requires a reason")
            db.execute("INSERT INTO relationship_history VALUES (?,?,?,?,?,?)", (profile, rid, row["revision"], row["record_json"], reason, timestamp))
            db.execute("UPDATE relationships SET revision=revision+1,record_json=?,updated_at=? WHERE profile=? AND id=?", (encoded, timestamp, profile, rid))
            case_id = row["case_id"]
            # New facts invalidate displayed classifications until explicitly evaluated.
            db.execute("UPDATE relationship_reviews SET state='needs_verification',revision=revision+1,updated_at=? WHERE profile=? AND person_id=?", (timestamp, profile, person_id))
        else:
            if expected_revision is not None:
                raise RevisionConflictError("New relationships do not have an expected revision")
            case_id = uuid4().hex
            subject = record["person"]["name"] + " / " + record["original_company"]["name"]
            db.execute("INSERT INTO cases VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (profile, case_id, "relationship:" + rid, subject[:300], None, "lead", "open", 1,
                       json.dumps({"relationship_id": rid, "fictional": record.get("fictional", False)}), subject.casefold(), timestamp, timestamp))
            db.execute("INSERT INTO relationships VALUES (?,?,?,?,?,?,?,?,?)", (profile, rid, case_id, person_id, company_id, 1, encoded, "{}", timestamp))
        # Preserve compact dated observations in the ordinary case evidence as well
        # as the complete, revisioned relationship snapshot.
        sources = [(p["source"], p.get("observed_at") or record["history_coverage"].get("checked_at") or timestamp,
                    "Host-supplied pitch evidence: " + p["kind"] + "; occurred at " + p["occurred_at"])
                   for p in record["pitch_evidence"]]
        emp = record["current_employment"]
        if emp.get("profile_url") and emp.get("observed_at"):
            sources.append((emp["profile_url"], emp["observed_at"], "Employment observation: " + str(emp.get("company_name", "unresolved"))))
        if record.get("last_contact_source") and record.get("last_meaningful_contact_at"):
            sources.append((record["last_contact_source"], record["history_coverage"].get("checked_at") or timestamp,
                            "Latest meaningful conversation found in declared sources; occurred at " + record["last_meaningful_contact_at"]))
        for source, date, content in sources:
            evidence_id = hashlib.sha256((rid + source + date + content).encode()).hexdigest()
            db.execute("INSERT OR IGNORE INTO evidence VALUES (?,?,?,?,?,?,?,?,?,?)", (profile, evidence_id, case_id, source, date, "observed", content,
                       json.dumps({"scope": "user_history", "collection_provenance": "host_supplied", "relationship_id": rid}), content.casefold(), timestamp))
        self.store._touch(case_id)
        return dict(self._public(self._row(rid)), changed=True)

    def _person_state(self, person_id: str, *, include_source: bool = True) -> dict:
        state = {}
        rows = self.store._conn.execute("SELECT local_state,record_json FROM relationships WHERE profile=? AND person_id=?", (self.store.profile, person_id))
        for row in rows:
            for key, value in json.loads(row["local_state"]).items():
                if value:
                    state[key] = value
            source = json.loads(row["record_json"])["source_status"]
            if include_source and source.get("do_not_contact") is True:
                state["excluded"] = True
            if include_source and source.get("enrichment_opt_out") is True:
                state["enrichment_opt_out"] = True
        return state

    def _person_rows(self, person_id: str) -> list:
        return self.store._conn.execute("SELECT * FROM relationships WHERE profile=? AND person_id=? ORDER BY id", (self.store.profile, person_id)).fetchall()

    def _evaluation(self, row, timestamp: str) -> dict:
        # Employment belongs to the lifelong person, not an individual old deal.
        # Resolve their newest stored observation across all pitch relationships.
        record = json.loads(row["record_json"])
        peers = [json.loads(peer["record_json"]) for peer in self._person_rows(row["person_id"])]
        observations = [p["current_employment"] for p in peers if p["current_employment"].get("observed_at")]
        if observations:
            latest = max((item["observed_at"] for item in observations), key=_date)
            newest = [item for item in observations if item["observed_at"] == latest]
            record["current_employment"] = dict(newest[0])
            record["current_employment"]["identity_verified"] = all(item.get("identity_verified") is True for item in newest)
            record["current_employment"]["ambiguous"] = (
                any(item.get("ambiguous") is not False for item in newest)
                or len({item.get("company_id") for item in newest}) > 1
            )
            positions = {json.dumps(position, sort_keys=True): position for item in newest for position in item.get("positions", [])}
            record["current_employment"]["positions"] = [positions[key] for key in sorted(positions)]
        target = record["current_employment"].get("company_id")
        statuses = [p["source_status"] for p in peers if p["source_status"].get("company_id") == target and p["source_status"].get("verified_at")]
        if statuses:
            latest = max((item["verified_at"] for item in statuses), key=_date)
            newest = [item for item in statuses if item["verified_at"] == latest]
            record["source_status"] = dict(newest[0])
            for flag in ("open_deal", "active_client", "do_not_contact", "enrichment_opt_out"):
                values = [item.get(flag) for item in newest]
                record["source_status"][flag] = True if True in values else False if all(v is False for v in values) else None
            outreach = [item["recent_outreach_at"] for item in newest if item.get("recent_outreach_at")]
            record["source_status"]["recent_outreach_at"] = max(outreach, key=_date) if outreach else None
        else:
            record["source_status"] = {}
        histories = [p["history_coverage"] for p in peers if p["history_coverage"].get("checked_at")]
        if histories:
            latest = max((item["checked_at"] for item in histories), key=_date)
            newest = [item for item in histories if item["checked_at"] == latest]
            # A conflicting incomplete observation is not upgraded by another
            # pitch record that happens to claim completeness at the same time.
            rank = {"unavailable": 0, "partial": 1, "complete": 2}
            record["history_coverage"] = min(newest, key=lambda h: rank.get(h.get("status"), 0))
        contacts = [p for p in peers if p.get("last_meaningful_contact_at")]
        if contacts:
            latest = max(contacts, key=lambda p: _date(p["last_meaningful_contact_at"]))
            record["last_meaningful_contact_at"] = latest["last_meaningful_contact_at"]
            record["last_contact_source"] = latest.get("last_contact_source")
        result = evaluate(record, now=timestamp, policy=self.policy, local_state=self._person_state(row["person_id"]))
        result.update(case_id=row["case_id"], relationship_revision=row["revision"], related_relationship_ids=[p["id"] for p in peers])
        if result["state"] == "ready" and result["skill"] == "pitched_contact_moved" and any(
                p["original_company"]["id"] == target and p["original_company"].get("verified") is True and p.get("pitch_verified") is True and p["pitch_evidence"] for p in peers):
            result.update(state="not_eligible", reasons=["destination_already_has_pitch_relationship"])
        return result

    def _movement_anchor(self, row, result: dict):
        if result["skill"] != "pitched_contact_moved":
            return row
        candidates = []
        for peer in self._person_rows(row["person_id"]):
            record = json.loads(peer["record_json"])
            if record["original_company"]["id"] != result["target_company_id"] and record["original_company"].get("verified") is True and record.get("pitch_verified") is True and record["pitch_evidence"]:
                latest_pitch = max(_date(p["occurred_at"]) for p in record["pitch_evidence"])
                if latest_pitch <= _date(result["evaluated_at"]):
                    candidates.append((latest_pitch, peer["id"], peer))
        return max(candidates, key=lambda item: item[:2])[2] if candidates else row

    def evaluate_all(self, *, now: str | None = None, limit: int = 100, after_id: str | None = None) -> dict:
        self._limit(limit)
        timestamp = _observed_at(now or _now())
        db, profile = self.store._conn, self.store.profile
        with self.store._transaction(write=True):
            rows = db.execute("SELECT * FROM relationships WHERE profile=? AND id>? ORDER BY id LIMIT ?", (profile, after_id or "", limit + 1)).fetchall()
            results = []
            for row in rows[:limit]:
                result = self._evaluation(row, timestamp)
                row = self._movement_anchor(row, result)
                result = self._evaluation(row, timestamp)
                # Unresolved identity stays inspectable, but never becomes a ready card.
                skill, target = result["skill"] or "unresolved", result["target_company_id"] or "unresolved"
                review_id = hashlib.sha256((row["person_id"] + "\0" + skill + "\0" + target).encode()).hexdigest()
                old = db.execute("SELECT * FROM relationship_reviews WHERE profile=? AND id=?", (profile, review_id)).fetchone()
                state = result["state"]
                if old and old["decision"] in ("already_in_touch", "reconnect"):
                    state = "handled"
                if old and old["snoozed_until"] and _date(old["snoozed_until"]) > _date(timestamp) and state == "ready":
                    state = "snoozed"
                encoded = json.dumps(result, sort_keys=True, ensure_ascii=False)
                if old:
                    previous_result = json.loads(old["result_json"])
                    previous_result.pop("evaluated_at", None)
                    compared_result = dict(result)
                    compared_result.pop("evaluated_at", None)
                    changed = int(previous_result != compared_result or old["state"] != state or old["relationship_id"] != row["id"])
                    db.execute("UPDATE relationship_reviews SET relationship_id=?,state=?,result_json=?,revision=revision+?,updated_at=? WHERE profile=? AND id=?",
                               (row["id"], state, encoded, changed, timestamp, profile, review_id))
                else:
                    db.execute("INSERT INTO relationship_reviews VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (profile, review_id, row["id"], row["person_id"], skill, target, state, encoded, 1, None, None, timestamp, timestamp))
                # Retire earlier employer cards for the person, even when a new
                # employer arrived through a different historical pitch record.
                db.execute("UPDATE relationship_reviews SET state='superseded',revision=revision+1,updated_at=? WHERE profile=? AND person_id=? AND target_company_id!=? AND state!='superseded'",
                           (timestamp, profile, row["person_id"], target))
                results.append(dict(result, review_id=review_id, review_state=state))
            return {"evaluated": len(results), "results": results, "next_cursor": rows[limit-1]["id"] if len(rows) > limit else None,
                    "coverage": "This page of imported relationships in the selected profile", "provider_calls": 0}

    @staticmethod
    def _review(row) -> dict:
        result = dict(row)
        result.pop("profile")
        result["result"] = json.loads(result.pop("result_json"))
        return result

    def queue(self, *, state: str | None = "ready", limit: int = 100, after_id: str | None = None) -> dict:
        self._limit(limit)
        valid = {"ready", "needs_verification", "not_eligible", "suppressed", "snoozed", "handled", "superseded"}
        if state is not None and state not in valid:
            raise ValidationError("Unknown review state")
        with self.store._transaction():
            rows = self.store._conn.execute("SELECT * FROM relationship_reviews WHERE profile=? AND id>? ORDER BY id LIMIT ?",
                                           (self.store.profile, after_id or "", limit + 1)).fetchall()
            reviews = []
            for row in rows[:limit]:
                review = self._review(row)
                if review["state"] == "ready":
                    relation = self._row(row["relationship_id"])
                    current = self._evaluation(relation, _now())
                    if current["skill"] != row["skill"] or current["target_company_id"] != row["target_company_id"]:
                        current.update(state="needs_verification", reasons=["employer_changed_evaluate_again"])
                    if current["state"] != "ready":
                        review["state"] = current["state"]
                        review["result"] = dict(current, case_id=relation["case_id"], relationship_revision=relation["revision"])
                        review["refresh_required"] = True
                if state is None or review["state"] == state:
                    reviews.append(review)
            return {"reviews": reviews, "next_cursor": rows[limit-1]["id"] if len(rows) > limit else None,
                    "coverage": "Filters apply after freshness checks; follow next_cursor even for an empty filtered page.",
                    "delivery": "local_review_queue_only"}

    def feedback(self, review_id: str, action: str, *, expected_revision: int, note: str = "", until: str | None = None, clear_holds: list[str] | None = None) -> dict:
        if action not in FEEDBACK:
            raise ValidationError("Choose a supported relationship feedback action")
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValidationError("expected_revision must be a positive integer")
        note = _text(note, "note", 1000, empty=True)
        clear_holds = clear_holds or []
        if not isinstance(clear_holds, list) or any(hold not in ("excluded", "enrichment_opt_out", "verification_required") for hold in clear_holds):
            raise ValidationError("clear_holds must name exact supported person holds")
        if clear_holds and action != "reopen":
            raise ValidationError("Only reopen can explicitly clear named holds")
        timestamp = _now()
        if until is not None:
            until = _observed_at(until)
        if action == "snooze" and (not until or _date(until) <= _date(timestamp)):
            raise ValidationError("Snooze requires a future until timestamp")
        if action != "snooze" and until is not None:
            raise ValidationError("until is only used for snooze")
        if action in ("wrong_identity", "wrong_employer", "never_pitched", "reopen", "outcome") and not note:
            raise ValidationError("This feedback requires a reason or outcome note")
        db, profile = self.store._conn, self.store.profile
        with self.store._transaction(write=True):
            row = db.execute("SELECT * FROM relationship_reviews WHERE profile=? AND id=?", (profile, review_id)).fetchone()
            if row is None:
                raise NotFoundError("Review not found in this profile")
            if row["revision"] != expected_revision:
                raise RevisionConflictError("Review changed; read its current revision before feedback")
            local = self._person_state(row["person_id"], include_source=False)
            state, decision, snooze = row["state"], row["decision"], row["snoozed_until"]
            if action in ("reconnect", "already_in_touch"):
                state, decision, snooze = "handled", action, None
                if action == "already_in_touch":
                    local["recent_owner_contact_at"] = timestamp
            elif action == "snooze":
                state, decision, snooze = "snoozed", None, until
            elif action in ("exclude", "enrichment_opt_out"):
                local["excluded" if action == "exclude" else action] = True
                state = "suppressed"
            elif action in ("wrong_identity", "wrong_employer", "never_pitched"):
                local["verification_required"] = action
                state = "needs_verification"
            elif action == "reopen":
                for hold in clear_holds:
                    local.pop(hold, None)
                state = "suppressed" if local.get("excluded") or local.get("enrichment_opt_out") else "needs_verification"
                decision, snooze = None, None
            for relation in db.execute("SELECT id,case_id FROM relationships WHERE profile=? AND person_id=?", (profile, row["person_id"])).fetchall():
                db.execute("UPDATE relationships SET local_state=?,revision=revision+1,updated_at=? WHERE profile=? AND id=?", (json.dumps(local), timestamp, profile, relation["id"]))
                self.store._touch(relation["case_id"])
            if action in ("exclude", "enrichment_opt_out", "wrong_identity", "wrong_employer", "never_pitched") or (action == "reopen" and clear_holds):
                db.execute("UPDATE relationship_reviews SET state=?,revision=revision+1,updated_at=? WHERE profile=? AND person_id=?", (state, timestamp, profile, row["person_id"]))
            db.execute("UPDATE relationship_reviews SET state=?,decision=?,snoozed_until=?,revision=revision+1,updated_at=? WHERE profile=? AND id=?", (state, decision, snooze, timestamp, profile, review_id))
            db.execute("INSERT INTO relationship_review_events VALUES (?,?,?,?,?,?)", (profile, uuid4().hex, review_id, action, note, timestamp))
            result = self._review(db.execute("SELECT * FROM relationship_reviews WHERE profile=? AND id=?", (profile, review_id)).fetchone())
            result["feedback_scope"] = {"review_id": review_id, "person_id": row["person_id"],
                                        "target_company_id": row["target_company_id"], "cleared_holds": sorted(set(clear_holds)),
                                        "remaining_person_state": local, "external_changes": False}
            return result
