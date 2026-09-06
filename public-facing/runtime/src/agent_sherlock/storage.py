"""Profile-scoped durable cases and evidence; no provider or model dependencies.

All SQL values are bound parameters. Every public operation uses the profile fixed
at construction. A profile is an organizational namespace, not authentication
against another process running as the same operating-system user.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import threading
from typing import Any, Iterator
from urllib.parse import parse_qsl, urlsplit
from uuid import uuid4


SOURCE_STATES = ("observed", "partial", "unavailable", "restricted", "failed", "not_attempted")
CASE_TYPES = ("account", "client", "lead", "competitor", "research")
FINDING_KINDS = ("observed", "inferred", "user_supplied")
MAX_CONTENT_LENGTH = 12_000
SCHEMA_VERSION = 2


class StoreError(Exception):
    """A safe, actionable local-storage error."""


class ValidationError(StoreError, ValueError):
    pass


class NotFoundError(StoreError, LookupError):
    pass


class RevisionConflictError(StoreError):
    pass


_SECRET_KEY = re.compile(r"^(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|authorization|token|secret|signature|sig)$", re.I)
_SECRET_VALUE = re.compile(
    r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"
    r"|\b(?:xox[baprs]-[A-Za-z0-9-]{8,}|gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,})"
    r"|\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}|\bAKIA[A-Z0-9]{16}\b"
    r"|\bBearer\s+[A-Za-z0-9._~+/-]{8,}"
    r"|\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|authorization)\s*[:=]\s*[\"']?[^\s\"']+",
    re.I,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _text(value: Any, name: str, maximum: int, *, empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be text")
    value = value.strip()
    if (not value and not empty) or len(value) > maximum or "\x00" in value:
        raise ValidationError(f"{name} must contain {'0' if empty else '1'} to {maximum} characters without NUL")
    # This catches common accidental credentials; it is not a universal DLP claim.
    if _SECRET_VALUE.search(value):
        raise ValidationError(f"{name} appears to contain a credential; remove it before saving")
    return value


def _metadata(value: dict[str, Any] | None) -> str:
    if value is None:
        return "{}"
    if not isinstance(value, dict):
        raise ValidationError("metadata must be an object")

    def check(item: Any, depth: int = 0) -> None:
        if depth > 12:
            raise ValidationError("metadata is nested too deeply")
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str) or _SECRET_KEY.fullmatch(key):
                    raise ValidationError("metadata must use text keys and must not contain credential fields")
                _text(key, "metadata key", 200)
                check(child, depth + 1)
        elif isinstance(item, (list, tuple)):
            for child in item:
                check(child, depth + 1)
        elif isinstance(item, str):
            _text(item, "metadata value", MAX_CONTENT_LENGTH, empty=True)
        elif item is not None and not isinstance(item, (bool, int, float)):
            raise ValidationError("metadata must contain only JSON values")

    try:
        check(value)
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as error:
        if isinstance(error, ValidationError):
            raise
        raise ValidationError("metadata must contain finite JSON values") from error
    if len(encoded.encode("utf-8")) > 16_000:
        raise ValidationError("metadata must not exceed 16000 UTF-8 bytes")
    return encoded


def _observed_at(value: str) -> str:
    value = _text(value, "observed_at", 80)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timezone required")
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError as error:
        raise ValidationError("observed_at must be an ISO 8601 datetime with a timezone") from error


def _source_uri(value: str) -> str:
    value = _text(value, "source_uri", 2048)
    try:
        parsed = urlsplit(value)
        if not parsed.scheme or parsed.scheme.lower() in {"javascript", "data", "file"}:
            raise ValueError("unsupported source scheme")
        if parsed.scheme.lower() in {"http", "https"} and not parsed.hostname:
            raise ValueError("missing source host")
        if any(character.isspace() for character in value):
            raise ValueError("unescaped whitespace in URL")
        _ = parsed.port  # Force validation of malformed ports, if present.
        if parsed.username or parsed.password:
            raise ValueError("credentials in URL")
        parameters = parse_qsl(parsed.query) + parse_qsl(parsed.fragment)
        if any(_SECRET_KEY.fullmatch(key) or key.casefold() == "key" for key, _ in parameters):
            raise ValueError("credential query parameter")
    except ValueError as error:
        raise ValidationError("source_uri must be a valid source locator without embedded credentials") from error
    return value


def _confidence(value: Any) -> str:
    if value is None or value in ("low", "medium", "high"):
        return json.dumps(value)
    if isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 1:
        return json.dumps(value)
    raise ValidationError("confidence must be null, low/medium/high, or a number from 0 to 1")


_SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    profile TEXT NOT NULL, id TEXT NOT NULL, entity_id TEXT NOT NULL,
    subject TEXT NOT NULL, category TEXT, case_type TEXT NOT NULL,
    status TEXT NOT NULL, revision INTEGER NOT NULL, metadata TEXT NOT NULL,
    search_text TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    PRIMARY KEY (profile, id)
);
CREATE INDEX IF NOT EXISTS case_scope ON cases(profile, case_type, category, entity_id);
CREATE TABLE IF NOT EXISTS evidence (
    profile TEXT NOT NULL, id TEXT NOT NULL, case_id TEXT NOT NULL,
    source_uri TEXT NOT NULL, observed_at TEXT NOT NULL, source_state TEXT NOT NULL,
    content TEXT NOT NULL, metadata TEXT NOT NULL, search_text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (profile, id),
    FOREIGN KEY (profile, case_id) REFERENCES cases(profile, id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS evidence_case ON evidence(profile, case_id);
CREATE TABLE IF NOT EXISTS findings (
    profile TEXT NOT NULL, id TEXT NOT NULL, case_id TEXT NOT NULL,
    statement TEXT NOT NULL, kind TEXT NOT NULL, confidence TEXT NOT NULL,
    revision INTEGER NOT NULL, correction_reason TEXT, search_text TEXT NOT NULL,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    PRIMARY KEY (profile, id),
    FOREIGN KEY (profile, case_id) REFERENCES cases(profile, id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS finding_case ON findings(profile, case_id);
CREATE TABLE IF NOT EXISTS finding_evidence (
    profile TEXT NOT NULL, finding_id TEXT NOT NULL, evidence_id TEXT NOT NULL,
    PRIMARY KEY (profile, finding_id, evidence_id),
    FOREIGN KEY (profile, finding_id) REFERENCES findings(profile, id) ON DELETE CASCADE,
    FOREIGN KEY (profile, evidence_id) REFERENCES evidence(profile, id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS finding_history (
    profile TEXT NOT NULL, finding_id TEXT NOT NULL, revision INTEGER NOT NULL,
    snapshot TEXT NOT NULL, corrected_at TEXT NOT NULL,
    PRIMARY KEY (profile, finding_id, revision),
    FOREIGN KEY (profile, finding_id) REFERENCES findings(profile, id) ON DELETE CASCADE
);
"""


class Store:
    """A fixed-profile store. Public methods are safe across threads/processes.

    SQLite WAL plus a busy timeout handles competing local agent processes; writes
    take an immediate transaction and optimistic case revisions prevent lost edits.
    """

    def __init__(self, db_path: str | Path, profile: str = "default") -> None:
        self._profile = _text(profile, "profile", 80)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", self._profile):
            raise ValidationError("profile must use letters, numbers, dots, underscores or hyphens")
        self.db_path = Path(db_path).expanduser() if str(db_path) != ":memory:" else Path(":memory:")
        self._lock = threading.RLock()
        self._closed = False
        if str(db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            descriptor = os.open(self.db_path, os.O_CREAT | os.O_WRONLY, 0o600)
            os.close(descriptor)
        self._conn = sqlite3.connect(str(self.db_path), timeout=10, isolation_level=None, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        try:
            self._conn.execute("PRAGMA busy_timeout=10000")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.execute("PRAGMA secure_delete=ON")
            self._conn.execute("PRAGMA journal_mode=WAL")
            version = self._conn.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1, SCHEMA_VERSION):
                raise StoreError("Database schema is newer or unsupported; use a compatible Sherlock release")
            from .relationships import SCHEMA as RELATIONSHIP_SCHEMA
            # Version 1 adds no data transform: create the new related tables in
            # one transaction, preserving every existing case and its revision.
            self._conn.executescript("BEGIN IMMEDIATE;\n" + _SCHEMA + RELATIONSHIP_SCHEMA
                                     + f"\nPRAGMA user_version={SCHEMA_VERSION};\nCOMMIT;")
        except Exception:
            self._conn.close()
            raise

    @property
    def profile(self) -> str:
        return self._profile

    @contextmanager
    def _transaction(self, *, write: bool = False) -> Iterator[None]:
        with self._lock:
            if self._closed:
                raise StoreError("Store is closed")
            try:
                self._conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                yield
                self._conn.execute("COMMIT")
            except Exception as error:
                if self._conn.in_transaction:
                    self._conn.execute("ROLLBACK")
                if isinstance(error, sqlite3.Error):
                    raise StoreError("Local storage operation failed; check database access and retry") from error
                raise

    def _case_row(self, case_id: str) -> sqlite3.Row:
        row = self._conn.execute("SELECT * FROM cases WHERE profile=? AND id=?", (self.profile, case_id)).fetchone()
        if row is None:
            raise NotFoundError("Case not found in this profile")
        return row

    def _touch(self, case_id: str) -> None:
        self._conn.execute("UPDATE cases SET revision=revision+1, updated_at=? WHERE profile=? AND id=?", (_now(), self.profile, case_id))

    @staticmethod
    def _public_row(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result.pop("search_text", None)
        if "metadata" in result:
            result["metadata"] = json.loads(result["metadata"])
        if "confidence" in result:
            result["confidence"] = json.loads(result["confidence"])
        return result

    def _finding(self, row: sqlite3.Row, *, history: bool = True) -> dict[str, Any]:
        result = self._public_row(row)
        result["evidence_ids"] = [item[0] for item in self._conn.execute(
            "SELECT evidence_id FROM finding_evidence WHERE profile=? AND finding_id=? ORDER BY evidence_id", (self.profile, row["id"]))]
        if history:
            result["history"] = [dict(json.loads(item["snapshot"]), corrected_at=item["corrected_at"]) for item in self._conn.execute(
                "SELECT snapshot, corrected_at FROM finding_history WHERE profile=? AND finding_id=? ORDER BY revision", (self.profile, row["id"]))]
        return result

    def _get_case(self, case_id: str) -> dict[str, Any]:
        result = self._public_row(self._case_row(case_id))
        result["evidence"] = [self._public_row(row) for row in self._conn.execute(
            "SELECT * FROM evidence WHERE profile=? AND case_id=? ORDER BY created_at,id", (self.profile, case_id))]
        result["findings"] = [self._finding(row) for row in self._conn.execute(
            "SELECT * FROM findings WHERE profile=? AND case_id=? ORDER BY created_at,id", (self.profile, case_id))]
        relationship = self._conn.execute("SELECT id,revision,record_json,local_state FROM relationships WHERE profile=? AND case_id=?", (self.profile, case_id)).fetchone()
        if relationship:
            result["relationship"] = {"id": relationship["id"], "revision": relationship["revision"],
                                      "record": json.loads(relationship["record_json"]), "local_state": json.loads(relationship["local_state"])}
        result["source_counts"] = {state: sum(item["source_state"] == state for item in result["evidence"]) for state in SOURCE_STATES}
        result["collection_status"] = self._collection_status(result["source_counts"])
        return result

    @staticmethod
    def _collection_status(counts: dict[str, int]) -> str:
        if not sum(counts.values()):
            return "no_sources_recorded"
        if counts["observed"] and sum(counts.values()) == counts["observed"]:
            return "all_recorded_sources_observed"
        return "partial_or_unavailable"

    def create_case(self, subject: str, entity_id: str, category: str | None = None, case_type: str = "account", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        subject = _text(subject, "subject", 300)
        entity_id = _text(entity_id, "entity_id", 300)
        category = _text(category, "category", 100).casefold() if category is not None else None
        if case_type not in CASE_TYPES:
            raise ValidationError(f"case_type must be one of {', '.join(CASE_TYPES)}")
        encoded = _metadata(metadata)
        case_id, timestamp = uuid4().hex, _now()
        with self._transaction(write=True):
            self._conn.execute("INSERT INTO cases VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (self.profile, case_id, entity_id, subject, category, case_type, "open", 1, encoded, subject.casefold(), timestamp, timestamp))
            return self._get_case(case_id)

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        with self._transaction():
            try:
                return self._get_case(case_id)
            except NotFoundError:
                return None

    def list_cases(self) -> list[dict[str, Any]]:
        with self._transaction():
            return [self._public_row(row) for row in self._conn.execute("SELECT * FROM cases WHERE profile=? ORDER BY updated_at DESC,id", (self.profile,))]

    def update_case(self, case_id: str, *, expected_revision: int, subject: str | None = None, category: str | None = None, status: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        if not isinstance(expected_revision, int) or isinstance(expected_revision, bool) or expected_revision < 1:
            raise ValidationError("expected_revision must be a positive integer")
        if status is not None and status not in ("open", "closed", "archived"):
            raise ValidationError("status must be open, closed or archived")
        subject = _text(subject, "subject", 300) if subject is not None else None
        category = _text(category, "category", 100).casefold() if category is not None else None
        encoded = _metadata(metadata) if metadata is not None else None
        with self._transaction(write=True):
            old = self._case_row(case_id)
            if old["revision"] != expected_revision:
                raise RevisionConflictError("Case changed; reload its current revision before updating")
            new_subject = subject if subject is not None else old["subject"]
            self._conn.execute("UPDATE cases SET subject=?, category=?, status=?, metadata=?, search_text=?, revision=revision+1, updated_at=? WHERE profile=? AND id=?",
                (new_subject, category if category is not None else old["category"], status if status is not None else old["status"], encoded if encoded is not None else old["metadata"], new_subject.casefold(), _now(), self.profile, case_id))
            return self._get_case(case_id)

    def add_evidence(self, case_id: str, *, source_uri: str, observed_at: str, source_state: str = "observed", content: str = "", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        source_uri = _source_uri(source_uri)
        observed_at = _observed_at(observed_at)
        if source_state not in SOURCE_STATES:
            raise ValidationError(f"source_state must be one of {', '.join(SOURCE_STATES)}")
        content = _text(content, "content", MAX_CONTENT_LENGTH, empty=True)
        encoded = _metadata(metadata)
        evidence_id = uuid4().hex
        with self._transaction(write=True):
            self._case_row(case_id)
            self._conn.execute("INSERT INTO evidence VALUES (?,?,?,?,?,?,?,?,?,?)",
                (self.profile, evidence_id, case_id, source_uri, observed_at, source_state, content, encoded, content.casefold(), _now()))
            self._touch(case_id)
            return self._public_row(self._conn.execute("SELECT * FROM evidence WHERE profile=? AND id=?", (self.profile, evidence_id)).fetchone())

    def _validate_evidence(self, case_id: str, evidence_ids: Any, kind: str) -> list[str]:
        if not isinstance(evidence_ids, (list, tuple)) or any(not isinstance(item, str) for item in evidence_ids):
            raise ValidationError("evidence_ids must be a list of evidence identifiers")
        identifiers = sorted(set(evidence_ids))
        if len(identifiers) > 100:
            raise ValidationError("A finding may reference at most 100 evidence items")
        if kind != "user_supplied" and not identifiers:
            raise ValidationError("Observed and inferred findings require supporting evidence")
        for evidence_id in identifiers:
            row = self._conn.execute("SELECT source_state FROM evidence WHERE profile=? AND case_id=? AND id=?", (self.profile, case_id, evidence_id)).fetchone()
            if row is None:
                raise ValidationError("Evidence must belong to this case and profile")
            if row["source_state"] not in ("observed", "partial"):
                raise ValidationError("Unavailable or uncollected sources cannot support a finding")
        return identifiers

    def add_finding(self, case_id: str, *, statement: str, evidence_ids: list[str] | tuple[str, ...] = (), kind: str = "observed", confidence: Any = None) -> dict[str, Any]:
        statement = _text(statement, "statement", 4000)
        if kind not in FINDING_KINDS:
            raise ValidationError(f"kind must be one of {', '.join(FINDING_KINDS)}")
        encoded_confidence = _confidence(confidence)
        finding_id, timestamp = uuid4().hex, _now()
        with self._transaction(write=True):
            self._case_row(case_id)
            identifiers = self._validate_evidence(case_id, evidence_ids, kind)
            self._conn.execute("INSERT INTO findings VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (self.profile, finding_id, case_id, statement, kind, encoded_confidence, 1, None, statement.casefold(), timestamp, timestamp))
            self._conn.executemany("INSERT INTO finding_evidence VALUES (?,?,?)", [(self.profile, finding_id, item) for item in identifiers])
            self._touch(case_id)
            return self._finding(self._conn.execute("SELECT * FROM findings WHERE profile=? AND id=?", (self.profile, finding_id)).fetchone())

    def correct_finding(self, finding_id: str, *, statement: str, reason: str, evidence_ids: list[str] | tuple[str, ...] | None = None, expected_revision: int | None = None) -> dict[str, Any]:
        statement = _text(statement, "statement", 4000)
        reason = _text(reason, "reason", 1000)
        if expected_revision is not None and (not isinstance(expected_revision, int) or isinstance(expected_revision, bool) or expected_revision < 1):
            raise ValidationError("expected_revision must be a positive integer")
        with self._transaction(write=True):
            row = self._conn.execute("SELECT * FROM findings WHERE profile=? AND id=?", (self.profile, finding_id)).fetchone()
            if row is None:
                raise NotFoundError("Finding not found in this profile")
            if expected_revision is not None and expected_revision != row["revision"]:
                raise RevisionConflictError("Finding changed; reload its current revision before correcting")
            previous = self._finding(row, history=False)
            identifiers = self._validate_evidence(row["case_id"], previous["evidence_ids"] if evidence_ids is None else evidence_ids, row["kind"])
            timestamp = _now()
            self._conn.execute("INSERT INTO finding_history VALUES (?,?,?,?,?)", (self.profile, finding_id, row["revision"], json.dumps(previous, ensure_ascii=False), timestamp))
            self._conn.execute("UPDATE findings SET statement=?, correction_reason=?, search_text=?, revision=revision+1, updated_at=? WHERE profile=? AND id=?",
                (statement, reason, statement.casefold(), timestamp, self.profile, finding_id))
            self._conn.execute("DELETE FROM finding_evidence WHERE profile=? AND finding_id=?", (self.profile, finding_id))
            self._conn.executemany("INSERT INTO finding_evidence VALUES (?,?,?)", [(self.profile, finding_id, item) for item in identifiers])
            self._touch(row["case_id"])
            return self._finding(self._conn.execute("SELECT * FROM findings WHERE profile=? AND id=?", (self.profile, finding_id)).fetchone())

    def recall_search(self, query: str, *, category: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        query = _text(query, "query", 1000).casefold()
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValidationError("limit must be an integer from 1 to 100")
        category = _text(category, "category", 100).casefold() if category is not None else None
        with self._transaction():
            rows = self._conn.execute("""
                SELECT c.id FROM cases c WHERE c.profile=? AND (? IS NULL OR c.category=?) AND (
                    instr(c.search_text, ?) > 0 OR EXISTS (
                        SELECT 1 FROM findings f WHERE f.profile=c.profile AND f.case_id=c.id AND instr(f.search_text, ?) > 0
                    ) OR EXISTS (
                        SELECT 1 FROM evidence e WHERE e.profile=c.profile AND e.case_id=c.id AND e.source_state IN ('observed','partial') AND instr(e.search_text, ?) > 0
                    )
                ) ORDER BY c.updated_at DESC,c.id LIMIT ?
                """, (self.profile, category, category, query, query, query, limit)).fetchall()
            return [self._get_case(row["id"]) for row in rows]

    def recall_count(self, category: str | None = None, *, case_type: str = "client") -> dict[str, Any]:
        category = _text(category, "category", 100).casefold() if category is not None else None
        if case_type not in CASE_TYPES:
            raise ValidationError(f"case_type must be one of {', '.join(CASE_TYPES)}")
        with self._transaction():
            rows = self._conn.execute("SELECT id,entity_id,category FROM cases WHERE profile=? AND case_type=? AND (? IS NULL OR category=?)", (self.profile, case_type, category, category)).fetchall()
            entities = sorted({row["entity_id"] for row in rows})
            counts = dict.fromkeys(SOURCE_STATES, 0)
            for row in self._conn.execute("""SELECT e.source_state,COUNT(*) AS count FROM evidence e JOIN cases c ON c.profile=e.profile AND c.id=e.case_id
                WHERE c.profile=? AND c.case_type=? AND (? IS NULL OR c.category=?) GROUP BY e.source_state""", (self.profile, case_type, category, category)):
                counts[row["source_state"]] = row["count"]
            return {"profile": self.profile, "scope": {"case_type": case_type, "category": category}, "count": len(entities), "entity_ids": entities,
                "case_count": len(rows), "source_counts": counts, "collection_status": self._collection_status(counts),
                "coverage": "Saved cases in this profile only; this is not a count of an entire CRM or unknown history."}

    def delete_case(self, case_id: str) -> bool:
        with self._transaction(write=True):
            cursor = self._conn.execute("DELETE FROM cases WHERE profile=? AND id=?", (self.profile, case_id))
            return cursor.rowcount > 0

    def export_profile(self) -> dict[str, Any]:
        with self._transaction():
            ids = [row[0] for row in self._conn.execute("SELECT id FROM cases WHERE profile=? ORDER BY created_at,id", (self.profile,))]
            result = {"schema_version": SCHEMA_VERSION, "profile": self.profile, "exported_at": _now(), "cases": [self._get_case(case_id) for case_id in ids]}
            for table in ("relationships", "relationship_history", "relationship_reviews", "relationship_review_events"):
                result[table] = [dict(row) for row in self._conn.execute(f"SELECT * FROM {table} WHERE profile=? ORDER BY rowid", (self.profile,))]
            return result

    def backup(self, destination: str | Path) -> Path:
        """Create a new SQLite backup containing only this profile.

        Clone to memory, remove other profiles, then vacuum before writing so the
        resulting file has neither foreign rows nor their deleted page contents.
        Existing destinations are never overwritten. Existing backups are separate
        user-owned files and are not silently removed by delete_case.
        """
        destination = Path(destination).expanduser()
        if str(self.db_path) != ":memory:" and destination.resolve() == self.db_path.resolve():
            raise ValidationError("Backup destination must differ from the live database")
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self._lock:
            if self._closed:
                raise StoreError("Store is closed")
            memory = sqlite3.connect(":memory:")
            created = False
            try:
                self._conn.backup(memory)
                memory.execute("PRAGMA foreign_keys=ON")
                memory.execute("PRAGMA secure_delete=ON")
                memory.execute("DELETE FROM cases WHERE profile != ?", (self.profile,))
                memory.commit()
                memory.execute("VACUUM")
                descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.close(descriptor)
                created = True
                backup = sqlite3.connect(destination)
                try:
                    memory.backup(backup)
                finally:
                    backup.close()
                return destination
            except Exception:
                if created:
                    destination.unlink(missing_ok=True)
                raise
            finally:
                memory.close()

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._conn.close()
                self._closed = True

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
