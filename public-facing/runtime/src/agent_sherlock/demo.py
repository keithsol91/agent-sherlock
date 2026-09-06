"""Repeatable fictional examples. This module makes no network calls."""

from . import research
from .storage import Store


def run_demo(store: Store) -> dict:
    existing = {case["entity_id"]: case for case in store.list_cases()}
    examples = [
        ("fictional-northstar", "Northstar Example Clinic", "medical", "client"),
        ("fictional-harbor", "Harbor Example Health", "medical", "client"),
        ("fictional-orbit", "Orbit Example Motors", "automotive", "competitor"),
    ]
    output = []
    for entity_id, subject, category, case_type in examples:
        case = existing.get(entity_id)
        if case is None:
            case = store.create_case(subject, entity_id, category, case_type, {"fictional": True})
            plan = research.prepare(store, case["id"], "What context should our team remember?", ["website"])
            source = store.add_evidence(
                case["id"], source_uri="https://" + entity_id + ".example/about",
                observed_at="2026-09-06T00:00:00+00:00", source_state="observed",
                content=f"Fictional example: {subject} requested educational short-form video concepts.",
                metadata={"scope": "website", "fictional": True, "research_run_id": plan["plan"]["id"]},
            )
            store.add_finding(
                case["id"], statement=f"{subject}: educational video concepts are a useful starting point (fictional).",
                evidence_ids=[source["id"]], kind="observed",
            )
        output.append(store.get_case(case["id"]))
    return {
        "fictional": True, "network_calls": 0, "profile": store.profile,
        "cases": output, "medical_clients": store.recall_count("medical"),
        "recall": store.recall_search("educational"),
        "coverage": [research.status(store, case["id"]) for case in output],
        "note": "Demonstrates local evidence, account context, cases, and recall. Real CRM and research providers are not connected.",
    }
