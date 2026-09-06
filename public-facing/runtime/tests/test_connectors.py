import copy
import json
import os
import sys

import pytest

from agent_sherlock.connectors import (
    ConnectorError,
    ConnectorGateway,
    FixtureTransport,
    MCPTransport,
    fixture_connection_config,
)


@pytest.fixture
def fixture_gateway():
    transport = FixtureTransport()
    gateway = ConnectorGateway(fixture_connection_config(), {"fictional-demo": transport})
    return gateway, transport


async def test_account_schema_and_record_binding(fixture_gateway):
    gateway, transport = fixture_gateway
    status = await gateway.status("fictional-demo")
    assert status["account_verified"] is True
    assert status["support_status"] == "configured_experimental"
    record = await gateway.read_record("fictional-demo", "company-001")
    assert record["fields"]["name"] == "Fictional Acorn Studio"
    assert record["account_id"] == "fictional-account"
    assert transport.calls[-2][0] == "fictional_account"
    assert transport.calls[-1][1] == {"account_id": "fictional-account", "record_id": "company-001"}
    search = await gateway.search_records("fictional-demo", "Acorn")
    assert search["records"][0]["record_id"] == "company-001"
    assert search["coverage"] == "bounded_search"


async def test_wrong_account_stops_before_record_access(fixture_gateway):
    gateway, transport = fixture_gateway
    transport.account_id = "another-account"
    with pytest.raises(ConnectorError, match="approved account"):
        await gateway.read_record("fictional-demo", "company-001")
    assert [name for name, _ in transport.calls] == ["fictional_account"]


async def test_missing_or_changed_schema_fails_closed(fixture_gateway):
    gateway, transport = fixture_gateway
    transport.schemas["fictional_get_record"]["required"].append("new_parameter")
    with pytest.raises(ConnectorError) as error:
        await gateway.read_record("fictional-demo", "company-001")
    assert error.value.code == "schema_changed"
    assert all(name != "fictional_get_record" for name, _ in transport.calls)


async def test_missing_capability_is_not_guessed(fixture_gateway):
    gateway, _ = fixture_gateway
    del gateway.connections["fictional-demo"]["operations"]["search_records"]
    with pytest.raises(ConnectorError) as error:
        await gateway.search_records("fictional-demo", "Acorn")
    assert error.value.code == "unsupported_operation"


@pytest.mark.parametrize("tool", ["COMPOSIO_MULTI_EXECUTE_TOOL", "COMPOSIO_REMOTE_BASH_TOOL", "crm_proxy", "execute", "run_python", "COMPOSIO_MANAGE_CONNECTIONS"])
async def test_meta_executor_cannot_be_disguised_as_crm_read(fixture_gateway, tool):
    gateway, transport = fixture_gateway
    gateway.connections["fictional-demo"]["operations"]["get_record"]["tool"] = tool
    with pytest.raises(ConnectorError) as error:
        await gateway.read_record("fictional-demo", "company-001")
    assert error.value.code == "unsafe_mapping"
    assert not transport.calls


async def test_arguments_are_validated_before_tool_call(fixture_gateway):
    gateway, transport = fixture_gateway
    gateway.connections["fictional-demo"]["operations"]["get_record"]["arguments"]["unexpected"] = "extra"
    with pytest.raises(ConnectorError) as error:
        await gateway.read_record("fictional-demo", "company-001")
    assert error.value.code == "invalid_arguments"
    assert all(name != "fictional_get_record" for name, _ in transport.calls)


async def test_unknown_argument_placeholder_is_not_interpreted(fixture_gateway):
    gateway, _ = fixture_gateway
    gateway.connections["fictional-demo"]["operations"]["get_record"]["arguments"]["record_id"] = "$os.environ"
    with pytest.raises(ConnectorError) as error:
        await gateway.read_record("fictional-demo", "company-001")
    assert error.value.code == "invalid_mapping"


async def test_sensitive_provider_values_are_redacted(fixture_gateway, monkeypatch):
    gateway, transport = fixture_gateway
    monkeypatch.setenv("SHERLOCK_TEST_HEADER", "fictional-opaque-secret-1234")
    gateway.connections["fictional-demo"]["transport"]["headers_from_env"] = {"Authorization": "SHERLOCK_TEST_HEADER"}
    transport.records["company-001"].update({"api_token": "fake-provider-secret", "notes": "fictional-opaque-secret-1234", "other": "Bearer do-not-return-this"})
    result = await gateway.read_record("fictional-demo", "company-001")
    assert result["fields"]["api_token"] == "[REDACTED]"
    assert result["fields"]["notes"] == "[REDACTED]"
    assert "do-not-return-this" not in json.dumps(result)


async def test_upstream_errors_never_expose_error_body(fixture_gateway):
    gateway, transport = fixture_gateway
    original = transport.call_tool

    async def failing(name, arguments):
        if name == "fictional_get_record":
            return {"isError": True, "content": [{"type": "text", "text": "Bearer secret-in-upstream-error"}]}
        return await original(name, arguments)

    transport.call_tool = failing
    with pytest.raises(ConnectorError) as error:
        await gateway.read_record("fictional-demo", "company-001")
    assert "secret-in-upstream-error" not in str(error.value)


async def test_wrong_record_result_rejected(fixture_gateway):
    gateway, transport = fixture_gateway
    original = transport.call_tool

    async def wrong_record(name, arguments):
        result = await original(name, arguments)
        if name == "fictional_get_record":
            result["structuredContent"]["id"] = "company-002"
        return result

    transport.call_tool = wrong_record
    with pytest.raises(ConnectorError) as error:
        await gateway.read_record("fictional-demo", "company-001")
    assert error.value.code == "record_mismatch"


async def test_discovery_pagination_is_complete_before_execution(fixture_gateway):
    gateway, transport = fixture_gateway
    schemas = list(transport.schemas.items())

    async def paginated(*, cursor=None):
        selected = schemas[:2] if cursor is None else schemas[2:]
        return {"tools": [{"name": name, "inputSchema": schema} for name, schema in selected], "nextCursor": "second" if cursor is None else None}

    transport.list_tools = paginated
    result = await gateway.search_records("fictional-demo", "Acorn")
    assert result["records"]


async def test_fictional_transport_persists_across_instances(tmp_path):
    config = fixture_connection_config(tmp_path / "fixture.sqlite3")
    first = ConnectorGateway(config)
    await first.update_fields("fictional-demo", "company-001", {"research_summary": "Fictional finding"})
    second = ConnectorGateway(config)
    assert (await second.read_record("fictional-demo", "company-001"))["fields"]["research_summary"] == "Fictional finding"
    if os.name != "nt":
        assert (tmp_path / "fixture.sqlite3").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("url", ["http://public.example/mcp", "https://" + "user:secret@" + "example.com/mcp", "file:///tmp/mcp"])
async def test_transport_rejects_insecure_or_embedded_credentials(url):
    with pytest.raises(ConnectorError) as error:
        async with MCPTransport({"type": "streamable_http", "url": url}).open():
            pytest.fail("Untrusted transport opened")
    assert error.value.code == "invalid_transport"


async def test_official_sdk_stdio_round_trip_with_local_subprocess(tmp_path):
    """Real protocol transport, solely a fictional local MCP subprocess."""
    server = tmp_path / "fixture_server.py"
    server.write_text('''from mcp.server import MCPServer
mcp = MCPServer("Fictional CRM test")
@mcp.tool()
def account_info() -> dict:
    return {"account_id": "fixture-sdk-account"}
@mcp.tool()
def company_read(account_id: str, record_id: str) -> dict:
    return {"account_id": account_id, "id": record_id, "properties": {"name": "Fictional SDK Company"}}
if __name__ == "__main__":
    mcp.run()
''')
    transport_config = {"type": "stdio", "command": sys.executable, "args": [str(server)]}
    # Only test code turns discovery into a mapping. Production requires local
    # operator review rather than silently accepting whatever schema appears.
    async with MCPTransport(transport_config).open() as client:
        tools = (await client.list_tools()).tools
        schemas = {tool.name: tool.input_schema for tool in tools}
    gateway = ConnectorGateway({"connections": {"sdk-fixture": {
        "provider": "fictional-sdk", "account_id": "fixture-sdk-account", "transport": transport_config,
        "operations": {
            "identify_account": {"tool": "account_info", "input_schema": schemas["account_info"], "arguments": {}, "result": {"account_id": "account_id"}},
            "get_record": {"tool": "company_read", "input_schema": schemas["company_read"], "arguments": {"account_id": "$account_id", "record_id": "$record_id"}, "result": {"account_id": "account_id", "record_id": "id", "fields": "properties"}},
        },
    }}})
    record = await gateway.read_record("sdk-fixture", "native-id-17")
    assert record["record_id"] == "native-id-17"
    assert record["fields"]["name"] == "Fictional SDK Company"
