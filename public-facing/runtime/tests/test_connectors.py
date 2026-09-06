import copy
import asyncio
import json
import os
import socket
import subprocess
import sys

import pytest

from agent_sherlock.connectors import (
    ConnectorError,
    ConnectorGateway,
    FixtureTransport,
    MCPTransport,
    composio_hubspot_connection_config,
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


@pytest.mark.parametrize("header, header_value", [
    ("Authorization", "Bearer {credential}"),
    ("authorization", "bearer {credential}"),
    ("AUTHORIZATION", "\tBEARER\t{credential}\t"),
    ("Proxy-Authorization", "Bearer {credential}"),
    ("pRoXy-AuThOrIzAtIoN", "  bEaReR \t {credential}  "),
])
async def test_bare_bearer_credentials_are_redacted_from_crm_fields(fixture_gateway, monkeypatch, header, header_value):
    gateway, transport = fixture_gateway
    credential = "fictionalOpaqueCredential.17+/=="
    configured_value = header_value.format(credential=credential)
    monkeypatch.setenv("SHERLOCK_TEST_BEARER_HEADER", configured_value)
    gateway.connections["fictional-demo"]["transport"]["headers_from_env"] = {header: "SHERLOCK_TEST_BEARER_HEADER"}
    transport.records["company-001"].update({
        "notes": credential,
        "description": f"Accidental provider echo: {credential}.",
        "details": [{"text": credential}],
        "header_echo": configured_value,
    })

    result = await gateway.read_record("fictional-demo", "company-001")

    assert result["fields"]["notes"] == "[REDACTED]"
    assert result["fields"]["description"] == "Accidental provider echo: [REDACTED]."
    assert result["fields"]["details"] == [{"text": "[REDACTED]"}]
    assert credential not in json.dumps(result)
    assert result["fields"]["name"] == "Fictional Acorn Studio"


async def test_header_and_environment_reference_collisions_preserve_all_redaction(fixture_gateway, monkeypatch):
    gateway, transport = fixture_gateway
    stdio_value = "fictionalChildEnvironmentCredential"
    credential = "fictionalHeaderCredential.29"
    other_header_value = "fictionalOtherHeaderCredential"
    other_header_variable = "SHERLOCK_TEST_OTHER_HEADER"
    monkeypatch.setenv("SHERLOCK_TEST_STDIO_VALUE", stdio_value)
    monkeypatch.setenv("SHERLOCK_TEST_HTTP_VALUE", f"Bearer {credential}")
    monkeypatch.setenv(other_header_variable, other_header_value)
    gateway.connections["fictional-demo"]["transport"].update({
        "env_from": {"Authorization": "SHERLOCK_TEST_STDIO_VALUE"},
        "headers_from_env": {"Authorization": "SHERLOCK_TEST_HTTP_VALUE", "X-Api-Key": other_header_variable},
    })
    transport.records["company-001"].update({
        "child_echo": stdio_value,
        "bare_echo": credential,
        "full_echo": f"Bearer {credential}",
        "other_echo": other_header_value,
    })

    result = await gateway.read_record("fictional-demo", "company-001")

    for field in ("child_echo", "bare_echo", "full_echo", "other_echo"):
        assert result["fields"][field] == "[REDACTED]"
    assert not any(value in json.dumps(result) for value in (stdio_value, credential, other_header_value))


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


@pytest.mark.parametrize("empty", [False, True])
async def test_search_accepts_omitted_final_page_cursor(fixture_gateway, empty):
    gateway, transport = fixture_gateway
    mapping = gateway.connections["fictional-demo"]["operations"]["search_records"]
    mapping["result"]["next_cursor"] = "paging.next.after"
    original = transport.call_tool

    async def final_page(name, arguments):
        response = await original(name, arguments)
        if name == "fictional_search_records":
            response["structuredContent"].pop("next_cursor", None)
            if empty:
                response["structuredContent"]["records"] = []
        return response

    transport.call_tool = final_page
    result = await gateway.search_records("fictional-demo", "Acorn")
    assert result["more_results"] is False
    assert len(result["records"]) == (0 if empty else 1)
    assert result["coverage"] == "bounded_search"


async def test_inspection_executes_no_tools_and_does_not_approve_mappings(fixture_gateway):
    gateway, transport = fixture_gateway
    gateway.connections["fictional-demo"]["operations"] = {}
    inspected = await gateway.inspect_tools("fictional-demo")
    assert len(inspected["tools"]) == 4
    assert inspected["account_verified"] is False
    assert inspected["review_required"] is True
    assert not transport.calls
    assert gateway.connections["fictional-demo"]["operations"] == {}


async def test_write_preview_requires_complete_payload_and_native_id(fixture_gateway):
    gateway, _ = fixture_gateway
    call = gateway.write_preview("fictional-demo", "company-001", {"industry": "Other"})
    assert call["arguments"]["fields"] == {"industry": "Other"}
    gateway.connections["fictional-demo"]["operations"]["update_fields"]["arguments"]["fields"] = {"industry": "hidden constant"}
    with pytest.raises(ConnectorError) as error:
        gateway.write_preview("fictional-demo", "company-001", {"industry": "Other"})
    assert error.value.code == "unsafe_mapping"


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


async def test_official_sdk_streamable_http_local_fixture(tmp_path):
    """Exercise HTTP transport only against a fictional loopback subprocess."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    server = tmp_path / "http_fixture.py"
    server.write_text(f'''from mcp.server import MCPServer
mcp = MCPServer("Fictional HTTP CRM test")
@mcp.tool()
def account_info() -> dict:
    return {{"account_id": "fictional-http-account"}}
if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port={port})
''')
    process = subprocess.Popen([sys.executable, str(server)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            if process.poll() is not None:
                pytest.fail("Local fictional HTTP server stopped before startup")
            try:
                _, writer = await asyncio.open_connection("127.0.0.1", port)
                writer.close()
                await writer.wait_closed()
                break
            except OSError:
                await asyncio.sleep(0.03)
        else:
            pytest.fail("Local fictional HTTP server did not start")
        async with MCPTransport({"type": "streamable_http", "url": f"http://127.0.0.1:{port}/mcp"}).open() as client:
            tools = await client.list_tools()
            assert tools.tools[0].name == "account_info"
            result = await client.call_tool("account_info", {})
            payload = result.structured_content or json.loads(result.content[0].text)
            assert payload["account_id"] == "fictional-http-account"
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


class NativeComposioContractFixture(FixtureTransport):
    """Fictional direct-tool envelope contract, not a live Composio recording.

    Native slugs/argument names and successful/data envelope follow Composio's
    public HubSpot catalog. These minimal test schemas are intentionally NOT
    shipped as production schema pins: real endpoints must be inspected.
    """

    ALIASES = {
        "HUBSPOT_GET_ACCOUNT_INFO": "fictional_account",
        "HUBSPOT_GET_COMPANY": "fictional_get_record",
        "HUBSPOT_SEARCH_COMPANIES": "fictional_search_records",
        "HUBSPOT_UPDATE_COMPANY": "fictional_update_fields",
    }

    def __init__(self):
        super().__init__()
        self.schemas = {
            "HUBSPOT_GET_ACCOUNT_INFO": {"type": "object", "properties": {}, "additionalProperties": False},
            "HUBSPOT_GET_COMPANY": {"type": "object", "properties": {"companyId": {"type": "string"}, "properties": {"type": "array", "items": {"type": "string"}}}, "required": ["companyId"], "additionalProperties": False},
            "HUBSPOT_SEARCH_COMPANIES": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}, "properties": {"type": "array", "items": {"type": "string"}}}, "required": ["query", "limit"], "additionalProperties": False},
            "HUBSPOT_UPDATE_COMPANY": {"type": "object", "properties": {"companyId": {"type": "string"}, "properties": {"type": "object", "additionalProperties": {"type": "string"}}}, "required": ["companyId", "properties"], "additionalProperties": False},
        }
        self.successful = True

    async def call_tool(self, name, arguments):
        translated = {"account_id": self.account_id}
        if "companyId" in arguments:
            translated["record_id"] = arguments["companyId"]
        if name == "HUBSPOT_UPDATE_COMPANY":
            translated["fields"] = arguments["properties"]
        if name == "HUBSPOT_SEARCH_COMPANIES":
            translated.update(query=arguments["query"], limit=arguments["limit"])
        response = await super().call_tool(self.ALIASES[name], translated)
        data = response.get("structuredContent", {})
        if name == "HUBSPOT_GET_ACCOUNT_INFO":
            data = {"hubId": self.account_id}
        elif "id" in data:
            data = {"id": data["id"], "properties": data["fields"]}
        elif "records" in data:
            data = {"results": [{"id": row["id"], "properties": row["fields"]} for row in data["records"]]}
        return {"structuredContent": {"data": json.dumps(data), "successful": self.successful, "error": None}, "isError": False}


async def test_composio_direct_tool_mapping_contract_and_reviewed_schema_generator(tmp_path):
    from agent_sherlock.changes import ChangeManager

    transport = NativeComposioContractFixture()
    inspect_gateway = ConnectorGateway({"connections": {"composio": {"account_id": "fictional-account", "operations": {}}}}, {"composio": transport})
    inspected = await inspect_gateway.inspect_tools("composio")
    config = composio_hubspot_connection_config(inspected, connection_id="composio", account_id="fictional-account", transport={"type": "streamable_http", "url": "https://example.com/operator-supplied-direct-session"}, properties=["name", "research_summary"], account_id_path="data.hubId")
    gateway = ConnectorGateway(config, {"composio": transport})
    assert (await gateway.status("composio"))["account_verified"] is True
    assert (await gateway.search_records("composio", "Acorn"))["records"][0]["record_id"] == "company-001"
    manager = ChangeManager(tmp_path / "composio-contract.sqlite3", gateway)
    change = await manager.propose("composio", "company-001", {"research_summary": "Fictional direct-tool finding"}, [{"source_url": "https://example.com/fictional"}])
    assert change["payload"]["provider_call"]["arguments"] == {"companyId": "company-001", "properties": {"research_summary": "Fictional direct-tool finding"}}
    manager.authorize(change["proposal_id"], change["payload_hash"])
    assert (await manager.apply(change["proposal_id"]))["state"] == "verified"
    with pytest.raises(ConnectorError) as error:
        gateway.write_preview("composio", "company-001", {"unreviewed_field": "x"})
    assert error.value.code == "unsupported_fields"
    transport.successful = False
    with pytest.raises(ConnectorError) as error:
        await gateway.read_record("composio", "company-001")
    assert error.value.code == "tool_error"


def test_composio_generator_rejects_shared_meta_tool_endpoint():
    with pytest.raises(ConnectorError) as error:
        composio_hubspot_connection_config({"tools": [{"name": "COMPOSIO_MULTI_EXECUTE_TOOL", "input_schema": {"type": "object"}}]}, connection_id="composio", account_id="fictional", transport={}, properties=["name"], account_id_path="data.hubId")
    assert error.value.code == "missing_composio_tools"
