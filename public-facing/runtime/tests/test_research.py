from agent_sherlock import research
from agent_sherlock.storage import Store


def test_new_research_cannot_reuse_old_coverage(tmp_path):
    with Store(tmp_path / "cases.sqlite3") as store:
        case = store.create_case("Fictional Example", "fictional-example")
        plan = research.prepare(store, case["id"], "What changed?", ["organic", "community"])
        store.add_evidence(case["id"], source_uri="https://fictional.example/posts", observed_at="2026-09-01T00:00:00Z",
                           metadata={"scope": "organic", "research_run_id": plan["plan"]["id"]})
        status = research.status(store, case["id"])
        assert status["coverage"]["organic"]["state"] == "observed"
        assert status["coverage"]["community"]["state"] == "not_attempted"
        research.prepare(store, case["id"], "What changed this week?", ["organic"])
        assert research.status(store, case["id"])["coverage"]["organic"]["state"] == "not_attempted"


def test_unavailable_evidence_never_becomes_zero_activity(tmp_path):
    with Store(tmp_path / "cases.sqlite3") as store:
        case = store.create_case("Fictional Example", "fictional-example")
        plan = research.prepare(store, case["id"], "What ads are visible?", ["paid_creative"])
        store.add_evidence(case["id"], source_uri="https://fictional.example/ads", observed_at="2026-09-01T00:00:00Z",
                           source_state="restricted", metadata={"scope": "paid_creative", "research_run_id": plan["plan"]["id"]})
        status = research.status(store, case["id"])
        assert status["state"] == "incomplete_coverage"
        assert status["coverage"]["paid_creative"]["limitations"][0]["state"] == "restricted"

