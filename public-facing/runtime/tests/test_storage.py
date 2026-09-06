"""Storage invariants tested against real SQLite, not mocked persistence."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from agent_sherlock.storage import (
    MAX_CONTENT_LENGTH,
    NotFoundError,
    RevisionConflictError,
    Store,
    StoreError,
    ValidationError,
)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sherlock storage ")
        self.path = Path(self.temp.name) / "cases.sqlite3"
        self.store = Store(self.path, profile="alpha")
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.store.close)

    def case(self, subject="Example Clinic", entity_id="company:clinic", category="medical", case_type="client"):
        return self.store.create_case(subject, entity_id, category, case_type)

    def evidence(self, case_id, content="Offers preventive care", state="observed"):
        return self.store.add_evidence(case_id, source_uri="https://example.test/about", observed_at="2026-09-06T10:00:00-04:00", source_state=state, content=content)

    def test_profile_isolation_all_read_write_surfaces(self):
        case = self.case()
        evidence = self.evidence(case["id"])
        finding = self.store.add_finding(case["id"], statement="Clinic provides preventive care", evidence_ids=[evidence["id"]])
        with Store(self.path, "beta") as other:
            self.assertIsNone(other.get_case(case["id"]))
            self.assertEqual(other.list_cases(), [])
            self.assertEqual(other.recall_search("Clinic"), [])
            self.assertEqual(other.recall_count()["count"], 0)
            self.assertEqual(other.export_profile()["cases"], [])
            self.assertFalse(other.delete_case(case["id"]))
            with self.assertRaises(NotFoundError):
                other.update_case(case["id"], expected_revision=3, subject="Changed")
            with self.assertRaises(NotFoundError):
                other.add_evidence(case["id"], source_uri="https://example.test", observed_at="2026-09-06T00:00:00Z")
            with self.assertRaises(NotFoundError):
                other.correct_finding(finding["id"], statement="Changed", reason="Correction")
        self.assertEqual(self.store.get_case(case["id"])["subject"], "Example Clinic")

    def test_cross_case_and_cross_profile_evidence_rejected_atomically(self):
        first = self.case()
        second = self.case("Other Clinic", "company:other")
        evidence = self.evidence(first["id"])
        with self.assertRaises(ValidationError):
            self.store.add_finding(second["id"], statement="Unsupported claim", evidence_ids=[evidence["id"]])
        self.assertEqual(self.store.get_case(second["id"])["revision"], 1)
        self.assertEqual(self.store.get_case(second["id"])["findings"], [])
        with Store(self.path, "beta") as other:
            foreign = other.create_case("Foreign", "foreign")
            with self.assertRaises(ValidationError):
                other.add_finding(foreign["id"], statement="Wrong profile", evidence_ids=[evidence["id"]])

    def test_findings_require_usable_evidence_and_explicit_kind(self):
        case = self.case()
        unavailable = self.evidence(case["id"], content="Access denied", state="restricted")
        for kind in ("observed", "inferred"):
            with self.assertRaises(ValidationError):
                self.store.add_finding(case["id"], statement="Unsupported", kind=kind)
            with self.assertRaises(ValidationError):
                self.store.add_finding(case["id"], statement="Unsupported", kind=kind, evidence_ids=[unavailable["id"]])
        finding = self.store.add_finding(case["id"], statement="Owner says they serve local patients", kind="user_supplied")
        self.assertEqual(finding["kind"], "user_supplied")
        self.assertEqual(finding["evidence_ids"], [])

    def test_correction_retains_history_but_recall_uses_current_statement(self):
        case = self.case()
        evidence = self.evidence(case["id"])
        finding = self.store.add_finding(case["id"], statement="Old unsupported wording", evidence_ids=[evidence["id"]], confidence="medium")
        revised = self.store.correct_finding(finding["id"], statement="Provides primary care", reason="Owner corrected the wording", expected_revision=1)
        self.assertEqual(revised["revision"], 2)
        self.assertEqual(revised["history"][0]["statement"], "Old unsupported wording")
        self.assertEqual(revised["history"][0]["evidence_ids"], [evidence["id"]])
        self.assertEqual(self.store.recall_search("unsupported wording"), [])
        self.assertEqual(len(self.store.recall_search("primary care")), 1)
        with self.assertRaises(RevisionConflictError):
            self.store.correct_finding(finding["id"], statement="Stale edit", reason="Concurrent writer", expected_revision=1)
        current = self.store.get_case(case["id"])
        self.assertEqual(current["revision"], 4)
        self.assertEqual(len(current["findings"][0]["history"]), 1)

    def test_distinct_client_counts_use_entity_ids_not_aliases_or_leads(self):
        self.case()
        self.case("Clinic Alternate Name", "company:clinic")
        self.case("Second Clinic", "company:second")
        self.case("Prospect", "company:prospect", case_type="lead")
        self.case("Competitor", "company:competitor", case_type="competitor")
        self.case("Bank", "company:bank", category="finance")
        count = self.store.recall_count("MEDICAL")
        self.assertEqual(count["count"], 2)
        self.assertEqual(count["case_count"], 3)
        self.assertEqual(count["entity_ids"], ["company:clinic", "company:second"])
        self.assertEqual(self.store.recall_count()["count"], 3)
        self.assertEqual(self.store.recall_count("missing")["collection_status"], "no_sources_recorded")

    def test_collection_counts_do_not_report_failures_as_zero_activity(self):
        case = self.case()
        self.evidence(case["id"])
        self.evidence(case["id"], "Provider timed out", "failed")
        self.evidence(case["id"], "No credentials configured", "not_attempted")
        current = self.store.get_case(case["id"])
        self.assertEqual(current["source_counts"]["observed"], 1)
        self.assertEqual(current["source_counts"]["failed"], 1)
        self.assertEqual(current["source_counts"]["not_attempted"], 1)
        self.assertEqual(current["collection_status"], "partial_or_unavailable")
        self.assertEqual(self.store.recall_count()["source_counts"], current["source_counts"])
        self.assertEqual(self.store.recall_search("Provider timed out"), [])

    def test_literal_search_handles_sql_metacharacters_and_unicode(self):
        literal = self.case("100%_Clinic Straße ' OR 1=1 --", "literal")
        self.case("Another clinic", "other")
        for query in ("%_", "' OR 1=1 --", "STRASSE"):
            matches = self.store.recall_search(query)
            self.assertEqual([item["id"] for item in matches], [literal["id"]])
        self.assertEqual(self.store.recall_search("%_", category="finance"), [])
        with self.assertRaises(ValidationError):
            self.store.recall_search("", limit=20)
        with self.assertRaises(ValidationError):
            self.store.recall_search("clinic", limit=0)

    def test_delete_removes_evidence_findings_links_history_and_recall(self):
        case = self.case()
        evidence = self.evidence(case["id"])
        finding = self.store.add_finding(case["id"], statement="Original", evidence_ids=[evidence["id"]])
        self.store.correct_finding(finding["id"], statement="Corrected", reason="Verified")
        self.assertTrue(self.store.delete_case(case["id"]))
        self.assertFalse(self.store.delete_case(case["id"]))
        self.assertEqual(self.store.export_profile()["cases"], [])
        self.assertEqual(self.store.recall_search("Corrected"), [])
        self.assertEqual(self.store.recall_count()["count"], 0)
        with closing(sqlite3.connect(self.path)) as db:
            for table in ("cases", "evidence", "findings", "finding_evidence", "finding_history"):
                self.assertEqual(db.execute(f"SELECT COUNT(*) FROM {table} WHERE profile=?", ("alpha",)).fetchone()[0], 0)
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_restart_persists_and_stale_revision_cannot_overwrite(self):
        case = self.case()
        self.evidence(case["id"])
        self.store.close()
        with Store(self.path, "alpha") as restarted:
            self.assertEqual(restarted.get_case(case["id"])["revision"], 2)
            with self.assertRaises(RevisionConflictError):
                restarted.update_case(case["id"], expected_revision=1, subject="Stale overwrite")
            updated = restarted.update_case(case["id"], expected_revision=2, subject="Verified Clinic")
            self.assertEqual(updated["revision"], 3)
            self.assertEqual(len(updated["evidence"]), 1)

    def test_competing_connections_preserve_all_writes(self):
        case = self.case()

        def append(index):
            with Store(self.path, "alpha") as writer:
                writer.add_evidence(case["id"], source_uri=f"fixture://source/{index}", observed_at="2026-09-06T00:00:00Z", content=f"Evidence {index}")

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(append, range(12)))
        current = self.store.get_case(case["id"])
        self.assertEqual(len(current["evidence"]), 12)
        self.assertEqual(current["revision"], 13)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("PRAGMA journal_mode").fetchone()[0], "wal")

    def test_backup_round_trip_is_profile_scoped_and_does_not_overwrite(self):
        case = self.case()
        evidence = self.evidence(case["id"])
        finding = self.store.add_finding(case["id"], statement="Original", evidence_ids=[evidence["id"]])
        self.store.correct_finding(finding["id"], statement="Corrected", reason="Source clarification")
        unique_foreign_content = "FOREIGN_PROFILE_ONLY_485430813975"
        with Store(self.path, "beta") as other:
            other.create_case(unique_foreign_content, "foreign")
        destination = Path(self.temp.name) / "backups" / "alpha.sqlite3"
        self.assertEqual(self.store.backup(destination), destination)
        with Store(destination, "alpha") as restored:
            self.assertEqual(restored.get_case(case["id"]), self.store.get_case(case["id"]))
        with Store(destination, "beta") as foreign:
            self.assertEqual(foreign.list_cases(), [])
        self.assertNotIn(unique_foreign_content.encode(), destination.read_bytes())
        with self.assertRaises(FileExistsError):
            self.store.backup(destination)
        with self.assertRaises(ValidationError):
            self.store.backup(self.path)

    def test_validation_bounds_timestamps_and_obvious_credentials(self):
        case = self.case()
        bad_arguments = [
            {"content": "x" * (MAX_CONTENT_LENGTH + 1)},
            {"observed_at": "2026-09-06T00:00:00"},
            {"source_uri": ("https://" + "user:password@" + "example.test")},
            {"source_uri": "https://example.test?access_token=private"},
            {"source_uri": "https://example.test:invalid-port"},
            {"content": "Authorization: Bearer super-secret-credential"},
            {"content": "sk-proj-" + "fictional" * 8},
            {"metadata": {"api_key": "do-not-store"}},
            {"metadata": {"score": float("nan")}},
        ]
        for change in bad_arguments:
            arguments = {"source_uri": "https://example.test", "observed_at": "2026-09-06T00:00:00Z", **change}
            with self.subTest(change=tuple(change)), self.assertRaises(ValidationError):
                self.store.add_evidence(case["id"], **arguments)
        self.assertEqual(self.store.get_case(case["id"])["revision"], 1)
        evidence = self.evidence(case["id"])
        self.assertEqual(evidence["observed_at"], "2026-09-06T14:00:00Z")

    def test_fixed_profile_and_closed_store(self):
        with self.assertRaises(AttributeError):
            self.store.profile = "beta"
        self.store.close()
        with self.assertRaises(StoreError):
            self.store.list_cases()


if __name__ == "__main__":
    unittest.main()
