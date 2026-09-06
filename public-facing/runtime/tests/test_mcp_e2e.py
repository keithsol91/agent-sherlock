"""Actual MCP protocol journeys using fictional data, never real provider access.

The memory transport exercises the same registered protocol handlers; the stdio
transport launches the public CLI as an independent subprocess. These establish
protocol behavior, not compatibility with an untested third-party agent host.
"""

from contextlib import asynccontextmanager
import json
from pathlib import Path
import sys
import tempfile

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.memory import create_client_server_memory_streams

from agent_sherlock.changes import ChangeManager
from agent_sherlock.config import load_settings
from agent_sherlock.connectors import ConnectorGateway, fixture_connection_config
from agent_sherlock.server import build_server


SOURCE_DIRECTORY = Path(__file__).resolve().parents[1] / "src"
OBSERVED_AT = "2026-09-06T00:00:00Z"


def decode_result(response) -> dict:
    if response.structured_content is not None:
        return response.structured_content
    texts = [item.text for item in response.content if item.type == "text"]
    assert len(texts) == 1, "Expected one structured Sherlock result"
    return json.loads(texts[0])


async def call_ok(client: ClientSession, name: str, **arguments) -> dict:
    response = await client.call_tool(name, arguments)
    assert not response.is_error, response
    payload = decode_result(response)
    assert payload["ok"] is True, payload
    return payload["result"]


async def call_error(client: ClientSession, name: str, **arguments) -> dict:
    response = await client.call_tool(name, arguments)
    payload = decode_result(response)
    assert payload["ok"] is False, payload
    assert payload["error"]["code"]
    return payload["error"]


@asynccontextmanager
async def memory_session(settings):
    server = build_server(settings)
    # SDK 2.1.1 exposes arbitrary streams at this lower-level server boundary.
    lowlevel = server._lowlevel_server
    async with create_client_server_memory_streams() as (client_streams, server_streams):
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(lowlevel.run, *server_streams, lowlevel.create_initialization_options())
            async with ClientSession(*client_streams, read_timeout_seconds=15) as client:
                initialized = await client.initialize()
                assert initialized.server_info.name == "Agent Sherlock"
                yield client
            tasks.cancel_scope.cancel()


@asynccontextmanager
async def stdio_session(data_dir: Path, profile: str, config_path: Path | None = None):
    arguments = ["-m", "agent_sherlock", "--data-dir", str(data_dir), "--profile", profile]
    if config_path:
        arguments.extend(["--config", str(config_path)])
    arguments.append("serve")
    parameters = StdioServerParameters(
        command=sys.executable,
        args=arguments,
        # The SDK inherits only normal OS variables. No user provider config or
        # credentials are imported; these explicit settings are all temporary.
        env={"PYTHONPATH": str(SOURCE_DIRECTORY), "PYTHONDONTWRITEBYTECODE": "1"},
        cwd=data_dir.parent,
    )
    with tempfile.TemporaryFile(mode="w+") as errors:
        async with stdio_client(parameters, errlog=errors) as streams:
            async with ClientSession(*streams, read_timeout_seconds=15) as client:
                initialized = await client.initialize()
                assert initialized.server_info.name == "Agent Sherlock"
                yield client
        errors.seek(0)
        assert "Traceback" not in errors.read(), "The subprocess emitted an unexpected traceback"


def configure_fixture(tmp_path: Path, data_dir: Path, profile: str) -> tuple[Path, dict]:
    config = fixture_connection_config(data_dir / profile / "demo-crm.sqlite3")
    config_path = tmp_path / f"{profile}-fictional-config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path, config


async def test_memory_protocol_four_workflows_and_operator_controlled_fixture_save(tmp_path):
    data_dir = tmp_path / "local cases"
    config_path, config = configure_fixture(tmp_path, data_dir, "alpha")
    settings = load_settings(data_dir, "alpha", config_path)
    async with memory_session(settings) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools.tools}
        assert {"case_create", "evidence_add", "finding_add", "recall_search", "research_prepare", "crm_read", "change_propose", "change_apply"} <= names
        assert not any("approv" in name or "authoriz" in name for name in names)
        update = next(tool for tool in tools.tools if tool.name == "case_update")
        assert "expected_revision" in update.input_schema["required"]

        connection = await call_ok(client, "crm_status", connection_id="fictional-demo")
        assert connection["account_verified"] is True
        assert connection["provider"] == "fictional-crm"
        record = await call_ok(client, "crm_read", connection_id="fictional-demo", record_id="company-001")
        case = await call_ok(client, "case_create", subject=record["fields"]["name"],
                             entity_id="fictional-crm:fictional-account:company-001", category="design", case_type="client",
                             metadata={"fictional": True, "account_id": record["account_id"], "crm_record_id": record["record_id"]})
        plan = await call_ok(client, "research_prepare", case_id=case["id"],
                             question="Which organic content idea fits this fictional account?", scopes=["organic", "website"])
        run_id = plan["plan"]["id"]
        organic = await call_ok(client, "evidence_add", case_id=case["id"],
                                source_uri="https://acorn.example/organic", observed_at=OBSERVED_AT,
                                content="Fictional posts explain how small creative teams work.",
                                metadata={"fictional": True, "scope": "organic", "research_run_id": run_id})
        await call_ok(client, "evidence_add", case_id=case["id"], source_uri="https://acorn.example/about",
                      observed_at=OBSERVED_AT, content="Fictional Acorn Studio creates design systems.",
                      metadata={"fictional": True, "scope": "website", "research_run_id": run_id})
        finding = await call_ok(client, "finding_add", case_id=case["id"],
                                statement="Consider an educational series about creative team workflows.",
                                evidence_ids=[organic["id"]], kind="inferred", confidence="medium")
        coverage = await call_ok(client, "research_status", case_id=case["id"])
        assert coverage["state"] == "evidence_recorded"
        assert all(scope["observed_count"] == 1 for scope in coverage["coverage"].values())
        recalled = await call_ok(client, "recall_search", query="educational series")
        assert recalled["matches"][0]["findings"][0]["id"] == finding["id"]

        summary = "Fictional research suggests educational creative-team content."
        proposal = await call_ok(client, "change_propose", connection_id="fictional-demo", record_id="company-001",
                                 fields={"research_summary": summary},
                                 evidence=[{"case_id": case["id"], "evidence_id": organic["id"], "source_uri": organic["source_uri"]}])
        assert proposal["state"] == "proposed"
        await call_error(client, "change_apply", proposal_id=proposal["proposal_id"])
        unchanged = await call_ok(client, "crm_read", connection_id="fictional-demo", record_id="company-001")
        assert unchanged["fields"] == record["fields"]

        # This is the test's simulated local operator, outside the MCP surface.
        operator = ChangeManager(settings.changes_database, ConnectorGateway(config))
        operator.authorize(proposal["proposal_id"], proposal["payload_hash"])
        applied = await call_ok(client, "change_apply", proposal_id=proposal["proposal_id"])
        assert applied["state"] == "verified"
        readback = await call_ok(client, "crm_read", connection_id="fictional-demo", record_id="company-001")
        assert readback["fields"]["research_summary"] == summary
        await call_error(client, "change_apply", proposal_id=proposal["proposal_id"])


async def test_stdio_clean_start_restart_and_new_research_requires_fresh_coverage(tmp_path):
    data_dir = tmp_path / "cold start data with spaces"
    async with stdio_session(data_dir, "org-one") as client:
        status = await call_ok(client, "sherlock_status")
        assert status["profile"] == "org-one"
        assert status["configured_connections"] == []
        assert status["connections_verified"] is False
        case = await call_ok(client, "case_create", subject="Fictional Harbor Clinic", entity_id="harbor",
                             category="medical", case_type="client", metadata={"fictional": True, "retained": "owner context"})
        plan = await call_ok(client, "research_prepare", case_id=case["id"], question="What has the clinic published?", scopes=["organic"])
        evidence = await call_ok(client, "evidence_add", case_id=case["id"], source_uri="https://harbor.example/post",
                                 observed_at=OBSERVED_AT, content="Fictional clinic published patient education.",
                                 metadata={"scope": "organic", "research_run_id": plan["plan"]["id"]})
        await call_ok(client, "finding_add", case_id=case["id"], statement="Patient education appears in the fictional content.",
                      evidence_ids=[evidence["id"]], kind="observed")
        assert (await call_ok(client, "research_status", case_id=case["id"]))["state"] == "evidence_recorded"
        fresh = await call_ok(client, "research_prepare", case_id=case["id"], question="What changed since last time?", scopes=["organic"])
        assert fresh["plan"]["id"] != plan["plan"]["id"]
        coverage = await call_ok(client, "research_status", case_id=case["id"])
        assert coverage["state"] == "incomplete_coverage"
        assert coverage["coverage"]["organic"]["source_count"] == 0

    async with stdio_session(data_dir, "org-one") as restarted:
        recalled = await call_ok(restarted, "recall_search", query="patient education")
        assert [item["id"] for item in recalled["matches"]] == [case["id"]]
        saved = await call_ok(restarted, "case_get", case_id=case["id"])
        assert saved["metadata"]["retained"] == "owner context"
        assert saved["metadata"]["research_plan"]["id"] == fresh["plan"]["id"]
        assert (await call_ok(restarted, "recall_count", category="medical"))["count"] == 1
        assert (await call_ok(restarted, "research_status", case_id=case["id"]))["state"] == "incomplete_coverage"

    async with stdio_session(data_dir, "other-org") as isolated:
        assert (await call_ok(isolated, "case_list"))["cases"] == []
        assert (await call_ok(isolated, "recall_search", query="patient education"))["matches"] == []
        await call_error(isolated, "case_get", case_id=case["id"])


async def test_stdio_protocol_rejects_cross_case_evidence_and_reports_revision_conflict(tmp_path):
    async with stdio_session(tmp_path / "validation data", "validation") as client:
        first = await call_ok(client, "case_create", subject="Fictional First", entity_id="first")
        second = await call_ok(client, "case_create", subject="Fictional Second", entity_id="second")
        source = await call_ok(client, "evidence_add", case_id=first["id"], source_uri="https://first.example",
                               observed_at=OBSERVED_AT, content="Fictional first company information.")
        rejected = await call_error(client, "finding_add", case_id=second["id"], statement="Cannot borrow unrelated evidence.",
                                    evidence_ids=[source["id"]], kind="observed")
        assert rejected["code"] == "ValidationError"
        unchanged = await call_ok(client, "case_get", case_id=second["id"])
        assert unchanged["revision"] == 1
        conflict = await call_error(client, "case_update", case_id=first["id"], expected_revision=1, subject="Stale version")
        assert conflict["code"] == "RevisionConflictError"
        assert (await call_ok(client, "case_get", case_id=first["id"]))["subject"] == first["subject"]


async def test_protocol_auto_binds_current_research_run_and_rejects_explicit_stale_run(tmp_path):
    settings = load_settings(tmp_path / "research runs", "research")
    async with memory_session(settings) as client:
        case = await call_ok(client, "case_create", subject="Fictional Study Account", entity_id="study")
        first_plan = await call_ok(client, "research_prepare", case_id=case["id"], question="What is visible today?", scopes=["website"])
        source = await call_ok(client, "evidence_add", case_id=case["id"], source_uri="https://study.example/about",
                               observed_at=OBSERVED_AT, content="Fictional company context.", metadata={"scope": "website"})
        assert source["metadata"]["research_run_id"] == first_plan["plan"]["id"]
        assert (await call_ok(client, "research_status", case_id=case["id"]))["state"] == "evidence_recorded"

        current_plan = await call_ok(client, "research_prepare", case_id=case["id"], question="What changed in the next review?", scopes=["website"])
        before = await call_ok(client, "case_get", case_id=case["id"])
        error = await call_error(client, "evidence_add", case_id=case["id"], source_uri="https://study.example/delayed",
                                 observed_at=OBSERVED_AT, content="Fictional result from an old research run.",
                                 metadata={"scope": "website", "research_run_id": first_plan["plan"]["id"]})
        assert "plan changed" in error["message"]
        after = await call_ok(client, "case_get", case_id=case["id"])
        assert after["revision"] == before["revision"]
        assert len(after["evidence"]) == 1
        assert after["metadata"]["research_plan"]["id"] == current_plan["plan"]["id"]
        assert (await call_ok(client, "research_status", case_id=case["id"]))["coverage"]["website"]["source_count"] == 0
