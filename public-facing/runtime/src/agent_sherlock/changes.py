"""Exact CRM proposals, local-operator authorization, and verified application.

There is intentionally no agent-facing approval mechanism. ``authorize`` is for
the local CLI only. An agent that has unrestricted shell/filesystem access can
act as the local user; this module is not an OS-level boundary against that host.
"""

from __future__ import annotations

import copy
import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .connectors import ConnectorError, ConnectorGateway, canonical_json, digest, safe_value, utc_now, validate_fields


class ChangeError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


_TERMINAL = {"verified", "rejected", "stale", "expired", "partial", "outcome_unknown", "failed"}


class ChangeManager:
    """Persist proposals in a DB isolated by the caller's profile path.

    ``policy`` is loaded from operator-owned local configuration. It cannot be
    supplied to the MCP tools by the model. Default policy always requires the
    operator to authorize each exact proposal using its payload hash.
    """

    def __init__(self, db_path: str | Path, gateway: ConnectorGateway, policy: dict[str, Any] | None = None):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.gateway = gateway
        self.policy = copy.deepcopy(policy or {})
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS sherlock_changes (
                id TEXT PRIMARY KEY, payload TEXT NOT NULL, payload_hash TEXT NOT NULL,
                state TEXT NOT NULL, created_at TEXT NOT NULL, expires_at REAL NOT NULL,
                authorization TEXT, updated_at TEXT NOT NULL, result TEXT
            )""")
        os.chmod(self.db_path, 0o600)

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def _row(self, proposal_id: str) -> dict:
        with self._db() as db:
            row = db.execute("SELECT * FROM sherlock_changes WHERE id=?", (proposal_id,)).fetchone()
        if row is None:
            raise ChangeError("unknown_proposal", "No proposal exists in this local profile with that ID.")
        return dict(row)

    @staticmethod
    def _view(row: dict) -> dict:
        return {"proposal_id": row["id"], "state": row["state"], "payload_hash": row["payload_hash"], "payload": json.loads(row["payload"]), "created_at": row["created_at"], "expires_at": row["expires_at"], "authorization": row["authorization"], "updated_at": row["updated_at"], "result": json.loads(row["result"]) if row["result"] else None}

    def get(self, proposal_id: str) -> dict:
        return self._view(self._row(proposal_id))

    def list_pending(self) -> list[dict]:
        with self._db() as db:
            rows = db.execute("SELECT * FROM sherlock_changes WHERE state IN ('proposed', 'approved', 'executing') ORDER BY created_at DESC LIMIT 100").fetchall()
        return [self._view(dict(row)) for row in rows]

    async def propose(self, connection_id: str, record_id: str, fields: dict[str, Any], evidence: list[dict], expires_in: int = 900) -> dict:
        fields = validate_fields(fields)
        if not self.gateway.has_operation(connection_id, "update_fields"):
            raise ChangeError("unsupported_write", "This connection has no reviewed field-update operation.")
        provider_call = self.gateway.write_preview(connection_id, record_id, fields)
        if type(expires_in) is not int or not 30 <= expires_in <= 86_400:
            raise ChangeError("invalid_expiry", "Proposal expiry must be between thirty seconds and one day.")
        if not isinstance(evidence, list) or not evidence or len(evidence) > 50 or any(not isinstance(item, dict) for item in evidence):
            raise ChangeError("invalid_evidence", "Provide one to fifty source evidence objects for this change.")
        try:
            if len(canonical_json(evidence)) > 100_000:
                raise ValueError
        except (TypeError, ValueError):
            raise ChangeError("invalid_evidence", "Evidence must contain bounded finite JSON values.") from None
        before = await self.gateway.read_record(connection_id, record_id)
        if all(key in before["fields"] and before["fields"][key] == value for key, value in fields.items()):
            raise ChangeError("no_change", "These field values already match the CRM record.")
        # Unknown credential values are never serialized into a review payload.
        secrets = self.gateway._secrets(connection_id)
        if safe_value(fields, secrets) != fields or safe_value(evidence, secrets) != evidence:
            raise ChangeError("sensitive_payload", "The proposal contains credential-shaped or configured secret values.")
        payload = {
            "action": "update_fields", "connection_id": connection_id,
            "connection_fingerprint": self.gateway.connection_fingerprint(connection_id),
            "account_id": before["account_id"], "record_id": before["record_id"],
            "before": {key: copy.deepcopy(before["fields"].get(key)) for key in fields},
            "previously_missing_fields": [key for key in fields if key not in before["fields"]],
            "before_snapshot_hash": before["snapshot_hash"],
            "fields": fields, "evidence": copy.deepcopy(evidence), "evidence_hash": digest(evidence),
            "provider_call": provider_call,
            "readback_fields": sorted(fields),
        }
        proposal_id = str(uuid.uuid4())
        stamp = utc_now()
        authorization = "operator_policy" if self._auto_allowed(payload) else None
        state = "approved" if authorization else "proposed"
        with self._db() as db:
            db.execute("INSERT INTO sherlock_changes VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)", (proposal_id, canonical_json(payload), digest(payload), state, stamp, time.time() + expires_in, authorization, stamp))
        return self.get(proposal_id)

    def _auto_allowed(self, payload: dict) -> bool:
        autosave = self.policy.get("autosave", {})
        if not isinstance(autosave, dict) or autosave.get("enabled") is not True:
            return False
        rules = autosave.get("rules", [])
        if not isinstance(rules, list):
            return False
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            if any(rule.get(key) != payload[key] for key in ("connection_id", "account_id", "action")):
                continue
            allowed_fields = rule.get("fields")
            if not isinstance(allowed_fields, list) or not allowed_fields or any(not isinstance(item, str) or not item or item == "*" for item in allowed_fields):
                continue
            if not set(payload["fields"]).issubset(allowed_fields):
                continue
            records = rule.get("record_ids")
            if records is not None and (not isinstance(records, list) or payload["record_id"] not in records or "*" in records):
                continue
            return True
        return False

    def authorize(self, proposal_id: str, payload_hash: str) -> dict:
        """Local operator CLI only. Never register this method as an MCP tool."""
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM sherlock_changes WHERE id=?", (proposal_id,)).fetchone()
            if row is None:
                raise ChangeError("unknown_proposal", "No proposal exists in this local profile with that ID.")
            if row["payload_hash"] != payload_hash or digest(json.loads(row["payload"])) != payload_hash:
                raise ChangeError("hash_mismatch", "The proposal does not match the exact reviewed payload hash.")
            if row["state"] != "proposed":
                raise ChangeError("invalid_state", "Only a proposed change can receive operator authorization.")
            if row["expires_at"] <= time.time():
                raise ChangeError("expired", "The proposal expired; create and review a fresh proposal.")
            db.execute("UPDATE sherlock_changes SET state='approved', authorization='local_operator', updated_at=? WHERE id=?", (utc_now(), proposal_id))
        return self.get(proposal_id)

    def reject(self, proposal_id: str) -> dict:
        with self._db() as db:
            changed = db.execute("UPDATE sherlock_changes SET state='rejected', updated_at=? WHERE id=? AND state IN ('proposed', 'approved')", (utc_now(), proposal_id)).rowcount
        if not changed:
            raise ChangeError("invalid_state", "Only proposed or approved changes can be rejected.")
        return self.get(proposal_id)

    def _set(self, proposal_id: str, state: str, result: dict) -> dict:
        if state not in _TERMINAL:
            raise ValueError("Invalid terminal state")
        with self._db() as db:
            db.execute("UPDATE sherlock_changes SET state=?, result=?, updated_at=? WHERE id=?", (state, canonical_json(result), utc_now(), proposal_id))
        return self.get(proposal_id)

    def _claim(self, proposal_id: str) -> dict:
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM sherlock_changes WHERE id=?", (proposal_id,)).fetchone()
            if row is None:
                raise ChangeError("unknown_proposal", "No proposal exists in this local profile with that ID.")
            payload = json.loads(row["payload"])
            if digest(payload) != row["payload_hash"]:
                raise ChangeError("payload_changed", "The stored proposal no longer matches its reviewed hash.")
            if row["state"] != "approved":
                raise ChangeError("approval_required" if row["state"] == "proposed" else "invalid_state", "This change is not authorized for execution; completed or uncertain writes cannot be retried.")
            if row["expires_at"] <= time.time():
                db.execute("UPDATE sherlock_changes SET state='expired', updated_at=? WHERE id=?", (utc_now(), proposal_id))
                return {"expired": True}
            if row["authorization"] == "operator_policy" and not self._auto_allowed(payload):
                raise ChangeError("policy_changed", "The current local autosave policy no longer permits this exact change.")
            if row["authorization"] not in {"operator_policy", "local_operator"}:
                raise ChangeError("approval_required", "A local authorization is required.")
            if self.gateway.connection_fingerprint(payload["connection_id"]) != payload["connection_fingerprint"]:
                raise ChangeError("connection_changed", "The connection configuration changed after this proposal was prepared.")
            db.execute("UPDATE sherlock_changes SET state='executing', updated_at=? WHERE id=?", (utc_now(), proposal_id))
        return payload

    async def apply(self, proposal_id: str) -> dict:
        """Apply once, then verify. An uncertain outcome never triggers a write retry."""
        payload = self._claim(proposal_id)
        if payload.get("expired"):
            return self.get(proposal_id)
        connection_id, record_id = payload["connection_id"], payload["record_id"]
        try:
            current = await self.gateway.read_record(connection_id, record_id)
        except Exception:
            return self._set(proposal_id, "failed", {"reason": "prewrite_read_failed", "write_attempted": False})
        if current["account_id"] != payload["account_id"] or current["snapshot_hash"] != payload["before_snapshot_hash"]:
            return self._set(proposal_id, "stale", {"reason": "record_changed_since_preview", "write_attempted": False})
        write_error = None
        try:
            await self.gateway.update_fields(connection_id, record_id, payload["fields"])
        except Exception as error:
            # Even an error can follow a successful provider write. Do not retry.
            write_error = error.code if isinstance(error, ConnectorError) else "write_response_unavailable"
        return await self._verify(proposal_id, payload, write_error=write_error)

    async def reconcile(self, proposal_id: str) -> dict:
        """Read-only recovery after a crash or uncertain/partial write result."""
        row = self._row(proposal_id)
        if row["state"] not in {"executing", "outcome_unknown", "partial"}:
            raise ChangeError("invalid_state", "Only an interrupted, uncertain, or partial change can be reconciled.")
        payload = json.loads(row["payload"])
        if digest(payload) != row["payload_hash"] or self.gateway.connection_fingerprint(payload["connection_id"]) != payload["connection_fingerprint"]:
            raise ChangeError("payload_changed", "Proposal or connection changed; automatic reconciliation is unavailable.")
        return await self._verify(proposal_id, payload, write_error="reconciliation_only")

    async def _verify(self, proposal_id: str, payload: dict, *, write_error: str | None) -> dict:
        try:
            after = await self.gateway.read_record(payload["connection_id"], payload["record_id"])
        except Exception:
            return self._set(proposal_id, "outcome_unknown", {"reason": "readback_unavailable", "write_error": write_error, "retry_write": False})
        if after["account_id"] != payload["account_id"]:
            return self._set(proposal_id, "outcome_unknown", {"reason": "readback_account_mismatch", "retry_write": False})
        matches = [key for key, value in payload["fields"].items() if key in after["fields"] and after["fields"][key] == value]
        result = {"verified_fields": matches, "readback": {key: after["fields"].get(key) for key in payload["fields"]}, "observed_at": after["observed_at"], "write_error": write_error, "retry_write": False}
        if len(matches) == len(payload["fields"]):
            return self._set(proposal_id, "verified", result)
        if matches:
            result["reason"] = "only_some_requested_fields_match"
            return self._set(proposal_id, "partial", result)
        result["reason"] = "requested_values_not_confirmed"
        return self._set(proposal_id, "outcome_unknown", result)
