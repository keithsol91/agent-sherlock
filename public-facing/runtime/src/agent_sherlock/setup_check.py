"""Exercise an installed runtime over stdio using only temporary fictional data."""

from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
import json
import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


_REQUEST_TIMEOUT_SECONDS = 15
_CHECK_TIMEOUT_SECONDS = 90
_EXPECTED_TOOLS = frozenset({
    "sherlock_status", "case_create", "case_get", "case_list", "case_update",
    "evidence_add", "finding_add", "finding_correct", "research_prepare",
    "research_status", "recall_search", "recall_count", "crm_status", "crm_search",
    "crm_read", "change_propose", "change_apply", "change_status", "change_reconcile",
    "relationship_import", "relationship_get", "relationship_list",
    "relationship_evaluate", "relationship_queue", "relationship_feedback",
})
_CHECK_LOG_CONTEXT = ContextVar("sherlock_setup_check", default=False)


class _CheckLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not _CHECK_LOG_CONTEXT.get()


@contextmanager
def _quiet_protocol_logs():
    # Invalid subprocess stdout can otherwise appear in SDK parse-error logs.
    # Task-local filtering leaves concurrent, unrelated MCP sessions unchanged.
    token = _CHECK_LOG_CONTEXT.set(True)
    log_filter = _CheckLogFilter()
    loggers = [logger for name, logger in list(logging.Logger.manager.loggerDict.items())
               if isinstance(logger, logging.Logger) and (name == "client" or name.startswith("mcp."))]
    for logger in loggers:
        logger.addFilter(log_filter)
    try:
        yield
    finally:
        for logger in loggers:
            logger.removeFilter(log_filter)
        _CHECK_LOG_CONTEXT.reset(token)


@asynccontextmanager
async def _session(parameters: StdioServerParameters):
    # The SDK closes stdin, waits, and escalates to process-tree termination
    # within bounded windows. All handles close before TemporaryDirectory exits,
    # including on Windows and when a request times out.
    with open(os.devnull, "w", encoding="utf-8") as errors:
        async with stdio_client(parameters, errlog=errors) as streams:
            async with ClientSession(*streams, read_timeout_seconds=_REQUEST_TIMEOUT_SECONDS) as client:
                yield client


async def _call(client: ClientSession, name: str, **arguments) -> dict:
    response = await client.call_tool(name, arguments)
    if response.is_error:
        raise ValueError("Tool failed.")
    payload = response.structured_content
    if payload is None:
        texts = [item.text for item in response.content if item.type == "text"]
        if len(texts) != 1:
            raise ValueError("Invalid tool response.")
        payload = json.loads(texts[0])
    if not isinstance(payload, dict) or payload.get("ok") is not True or not isinstance(payload.get("result"), dict):
        raise ValueError("Invalid tool result.")
    return payload["result"]


def _require(condition: bool) -> None:
    if not condition:
        raise ValueError("Verification did not match.")


async def verify_runtime(python_executable: str | Path) -> dict:
    """Verify a fully installed Python environment without reading user settings.

    The check never invokes an external/provider tool. Its empty provider config,
    profile, databases, and working directory belong to one temporary directory.
    Failures expose only the stage, never raw subprocess output or exceptions.
    """
    stage = "Python executable validation"
    try:
        # Resolving this symlink would bypass the virtual environment on POSIX.
        python = Path(python_executable).expanduser().absolute()
        _require(python.is_file())
        with _quiet_protocol_logs(), TemporaryDirectory(prefix="sherlock-setup-check-") as directory:
            root = Path(directory)
            config = root / "empty.json"
            stage = "temporary configuration"
            config.write_text('{"connections": {}}\n', encoding="utf-8")
            parameters = StdioServerParameters(
                command=str(python),
                args=["-I", "-m", "agent_sherlock", "--data-dir", str(root / "data"),
                      "--profile", "setup-check", "--config", str(config), "serve"],
                cwd=str(root),
                # stdio_client adds only the SDK's normal OS environment allowlist.
                env={"PYTHONDONTWRITEBYTECODE": "1"},
            )
            with anyio.fail_after(_CHECK_TIMEOUT_SECONDS):
                stage = "MCP startup"
                async with _session(parameters) as client:
                    initialized = await client.initialize()
                    _require(initialized.server_info.name == "Agent Sherlock")
                    stage = "tool discovery"
                    tools = await client.list_tools()
                    names = {tool.name for tool in tools.tools}
                    _require(names == _EXPECTED_TOOLS and len(tools.tools) == len(names))
                    stage = "runtime status"
                    status = await _call(client, "sherlock_status")
                    _require(status.get("profile") == "setup-check"
                             and status.get("transport") == "stdio"
                             and status.get("storage") == "local_sqlite"
                             and status.get("configured_connections") == []
                             and status.get("connections_verified") is False)
                    stage = "fictional case creation"
                    case = await _call(client, "case_create", subject="Fictional Setup Check Studio",
                                       entity_id="fictional-setup-check-studio", case_type="client",
                                       category="setup-check", metadata={"fictional": True})
                    stage = "fictional evidence creation"
                    evidence = await _call(client, "evidence_add", case_id=case["id"],
                                           source_uri="https://setup-check.example/fictional-note",
                                           observed_at="2026-01-01T00:00:00Z",
                                           content="Fictional studio requested a sample relationship review.",
                                           metadata={"fictional": True})
                    stage = "fictional finding creation"
                    finding = await _call(client, "finding_add", case_id=case["id"],
                                          statement="Fictional studio requested a sample relationship review.",
                                          evidence_ids=[evidence["id"]], kind="observed")
                    stage = "case readback"
                    saved = await _call(client, "case_get", case_id=case["id"])
                    _require(saved.get("id") == case["id"] and saved.get("subject") == case["subject"]
                             and saved.get("entity_id") == case["entity_id"]
                             and saved.get("metadata") == {"fictional": True}
                             and saved.get("evidence") == [evidence] and saved.get("findings") == [finding])
                    stage = "case recall"
                    recall = await _call(client, "recall_search", query="sample relationship review")
                    _require(recall.get("matches") == [saved])
                    stage = "first subprocess shutdown"

                stage = "MCP restart"
                async with _session(parameters) as restarted:
                    initialized = await restarted.initialize()
                    _require(initialized.server_info.name == "Agent Sherlock")
                    stage = "restart persistence"
                    restored = await _call(restarted, "case_get", case_id=case["id"])
                    _require(restored == saved)
                    recalled = await _call(restarted, "recall_search", query="sample relationship review")
                    _require(recalled.get("matches") == [saved])
                    stage = "restarted subprocess shutdown"
            stage = "temporary data cleanup"
        return {"passed": True, "tools_discovered": len(names), "case_round_trip": True,
                "restart_persistence": True, "provider_calls": 0}
    except Exception:
        raise ValueError(f"Runtime setup check failed during {stage}.") from None
