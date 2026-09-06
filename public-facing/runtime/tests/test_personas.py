"""Twenty independent synthetic journeys, not claims of twenty human beta users.

Each persona starts a real CLI/stdin-stdout MCP subprocess in a fresh directory,
uses a fictional local CRM, records research and durable cases, corrects recall,
restarts, and checks a second organization cannot read the first one's context.
All providers, companies and observations in this suite are fictional.
"""

import pytest

from test_mcp_e2e import OBSERVED_AT, call_error, call_ok, configure_fixture, stdio_session


PERSONAS = [
    ("solo-founder", "medical", "observed", True),
    ("agency-strategist", "finance", "restricted", False),
    ("sales-representative", "automotive", "observed", True),
    ("account-manager", "retail", "failed", False),
    ("research-analyst", "nonprofit", "observed", True),
    ("content-director", "medical", "partial", False),
    ("revenue-operations", "finance", "observed", True),
    ("consultant", "automotive", "unavailable", False),
    ("customer-success", "retail", "observed", True),
    ("marketing-generalist", "nonprofit", "not_attempted", False),
    ("new-team-member", "medical", "observed", False),
    ("returning-researcher", "finance", "restricted", True),
    ("regional-director", "automotive", "observed", False),
    ("project-manager", "retail", "failed", True),
    ("independent-operator", "nonprofit", "observed", False),
    ("support-specialist", "medical", "partial", True),
    ("business-developer", "finance", "observed", False),
    ("partnerships-lead", "automotive", "unavailable", True),
    ("editor", "retail", "observed", False),
    ("operations-manager", "nonprofit", "not_attempted", True),
]


@pytest.mark.parametrize("role,category,organic_state,has_alias", PERSONAS, ids=[item[0] for item in PERSONAS])
async def test_independent_persona_journey(tmp_path, role, category, organic_state, has_alias):
    profile = role
    data_dir = tmp_path / f"fresh {role} data"
    config_path, _ = configure_fixture(tmp_path, data_dir, profile)
    entity_id = "fictional-crm:fictional-account:company-001"
    old_wording = f"Superseded {role} recommendation"
    corrected_wording = f"Verified {role} context for an educational content series."

    async with stdio_session(data_dir, profile, config_path) as client:
        status = await call_ok(client, "sherlock_status")
        assert status["profile"] == profile
        assert status["configured_connections"] == ["fictional-demo"]
        assert (await call_ok(client, "case_list"))["cases"] == []

        crm = await call_ok(client, "crm_status", connection_id="fictional-demo")
        assert crm["account_verified"] is True
        search = await call_ok(client, "crm_search", connection_id="fictional-demo", query="Acorn", limit=5)
        assert len(search["records"]) == 1
        record = await call_ok(client, "crm_read", connection_id="fictional-demo", record_id=search["records"][0]["record_id"])
        case = await call_ok(client, "case_create", subject=f"Fictional Acorn account for {role}", entity_id=entity_id,
                             category=category, case_type="client", metadata={"fictional": True, "persona": role})
        if has_alias:
            await call_ok(client, "case_create", subject=f"Fictional Acorn alias for {role}", entity_id=entity_id,
                          category=category, case_type="client")
        await call_ok(client, "case_create", subject=f"Fictional unrelated prospect for {role}", entity_id="fictional-prospect",
                      category=category, case_type="lead")

        plan = await call_ok(client, "research_prepare", case_id=case["id"],
                             question=f"What should the {role} remember about this fictional account?", scopes=["website", "organic"])
        run_id = plan["plan"]["id"]
        source = await call_ok(client, "evidence_add", case_id=case["id"], source_uri=f"https://{role}.example/about",
                               observed_at=OBSERVED_AT, source_state="observed",
                               content=f"Fictional {role} account uses educational content for its audience.",
                               metadata={"scope": "website", "research_run_id": run_id, "fictional": True})
        await call_ok(client, "evidence_add", case_id=case["id"], source_uri=f"https://{role}.example/organic",
                      observed_at=OBSERVED_AT, source_state=organic_state,
                      content="Fictional collection result; only the explicit source state establishes collection status.",
                      metadata={"scope": "organic", "research_run_id": run_id, "fictional": True})
        finding = await call_ok(client, "finding_add", case_id=case["id"], statement=old_wording,
                                evidence_ids=[source["id"]], kind="inferred", confidence="medium")
        coverage = await call_ok(client, "research_status", case_id=case["id"])
        assert coverage["state"] == ("evidence_recorded" if organic_state == "observed" else "incomplete_coverage")
        if organic_state != "observed":
            assert coverage["coverage"]["organic"]["limitations"][0]["state"] == organic_state

        corrected = await call_ok(client, "finding_correct", finding_id=finding["id"], statement=corrected_wording,
                                  reason="Fictional owner clarified the desired account context.")
        assert corrected["history"][0]["statement"] == old_wording
        assert (await call_ok(client, "recall_search", query=old_wording))["matches"] == []
        recalled = await call_ok(client, "recall_search", query=corrected_wording, category=category)
        assert [item["id"] for item in recalled["matches"]] == [case["id"]]
        assert recalled["matches"][0]["findings"][0]["evidence_ids"] == [source["id"]]
        count = await call_ok(client, "recall_count", category=category)
        assert count["count"] == 1
        assert count["case_count"] == (2 if has_alias else 1)
        assert count["entity_ids"] == [entity_id]

        # Every persona proves the default policy blocks an unapproved CRM save.
        proposal = await call_ok(client, "change_propose", connection_id="fictional-demo", record_id=record["record_id"],
                                 fields={"research_summary": corrected_wording},
                                 evidence=[{"source_uri": source["source_uri"], "case_id": case["id"], "evidence_id": source["id"]}])
        assert proposal["state"] == "proposed"
        await call_error(client, "change_apply", proposal_id=proposal["proposal_id"])
        still_original = await call_ok(client, "crm_read", connection_id="fictional-demo", record_id=record["record_id"])
        assert still_original["fields"] == record["fields"]

    # A new process/new MCP session must recover both the case and proposal.
    async with stdio_session(data_dir, profile, config_path) as restarted:
        case_again = await call_ok(restarted, "case_get", case_id=case["id"])
        assert case_again["findings"][0]["statement"] == corrected_wording
        assert case_again["findings"][0]["history"][0]["statement"] == old_wording
        assert (await call_ok(restarted, "recall_count", category=category))["count"] == 1
        persisted_proposal = await call_ok(restarted, "change_status", proposal_id=proposal["proposal_id"])
        assert persisted_proposal["state"] == "proposed"

    # Another organization in the same local data root is still a clean profile.
    async with stdio_session(data_dir, "separate-organization") as isolated:
        assert (await call_ok(isolated, "case_list"))["cases"] == []
        assert (await call_ok(isolated, "recall_search", query=corrected_wording))["matches"] == []
        assert (await call_ok(isolated, "recall_count", category=category))["count"] == 0
        await call_error(isolated, "case_get", case_id=case["id"])
        await call_error(isolated, "change_status", proposal_id=proposal["proposal_id"])
