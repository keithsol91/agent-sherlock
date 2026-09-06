"""Reviewed CRM operation mappings over MCP; no arbitrary tool execution surface.

Mappings are operator configuration, never model-generated executable code. A
mapping pins the complete input schema and binds all operations to one account.
Generic discovery is not a claim that a particular CRM has been verified.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
import re
import sqlite3
from contextlib import asynccontextmanager, closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


class ConnectorError(ValueError):
    """A public-safe connector failure. Never include upstream error bodies."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


_SECRET_KEY = re.compile(r"(?:password|secret|token|authorization|api[_-]?key|cookie|credential)", re.I)
_SECRET_VALUE = re.compile(r"(?:Bearer\s+\S+|xox[baprs]-[\w-]+|sk-[\w-]{16,}|gh[pousr]_[\w]{16,})", re.I)
_FORBIDDEN_TOOL = re.compile(r"(?:^COMPOSIO_(?:MULTI_EXECUTE_TOOL|REMOTE_.*|MANAGE_CONNECTIONS)$|(?:^|_)(?:proxy|execute|exec|shell|bash|python|eval)(?:_|$))", re.I)
_OPERATIONS = {"identify_account", "search_records", "get_record", "update_fields"}


def safe_value(value: Any, secrets: tuple[str, ...] = ()) -> Any:
    """Redact credential-shaped keys/values and explicitly configured secrets."""
    if isinstance(value, dict):
        return {str(k): "[REDACTED]" if _SECRET_KEY.search(str(k)) else safe_value(v, secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [safe_value(v, secrets) for v in value]
    if isinstance(value, str):
        value = _SECRET_VALUE.sub("[REDACTED]", value)
        for secret in secrets:
            if len(secret) >= 4:
                value = value.replace(secret, "[REDACTED]")
        return value
    return value


def validate_fields(fields: Any) -> dict[str, Any]:
    if not isinstance(fields, dict) or not fields or len(fields) > 50:
        raise ConnectorError("invalid_fields", "Provide between one and fifty named CRM fields.")
    if any(not isinstance(key, str) or not key or len(key) > 200 or _SECRET_KEY.search(key) for key in fields):
        raise ConnectorError("invalid_fields", "CRM field names must be nonempty and cannot designate credentials.")
    try:
        encoded = canonical_json(fields)
    except (TypeError, ValueError):
        raise ConnectorError("invalid_fields", "CRM values must be finite JSON values.") from None
    if len(encoded) > 100_000 or safe_value(fields) != fields:
        raise ConnectorError("invalid_fields", "CRM values exceed limits or contain credential-shaped values.")
    return copy.deepcopy(fields)


def _path(value: Any, path: str) -> Any:
    if not isinstance(path, str):
        raise ConnectorError("invalid_mapping", "Result paths must be dotted object keys.")
    current = value
    for part in path.split(".") if path else []:
        if not isinstance(current, dict) or part not in current:
            raise ConnectorError("invalid_result", "A required mapped result field is missing.")
        current = current[part]
    return current


def _render(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, str) and value.startswith("$"):
        name = value[1:]
        if name not in context:
            raise ConnectorError("invalid_mapping", "The operation uses an unavailable argument placeholder.")
        return copy.deepcopy(context[name])
    if isinstance(value, dict):
        return {key: _render(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [_render(item, context) for item in value]
    return value


def _placeholders(value: Any) -> list[str]:
    if isinstance(value, str) and value.startswith("$"):
        return [value]
    if isinstance(value, dict):
        return [part for item in value.values() for part in _placeholders(item)]
    if isinstance(value, list):
        return [part for item in value for part in _placeholders(item)]
    return []


def _normalize_output(payload: dict, mapping: dict) -> dict:
    result = mapping.get("result", {})
    success_path = result.get("success")
    if success_path is not None and _path(payload, success_path) is not True:
        raise ConnectorError("tool_error", "The mapped CRM result did not report success; upstream details were withheld.")
    # Some native connectors serialize their provider response into a JSON
    # string. Decode only paths explicitly selected in reviewed configuration.
    paths = result.get("json_decode_paths", [])
    if not isinstance(paths, list) or len(paths) > 10:
        raise ConnectorError("invalid_mapping", "JSON decoding paths must be a bounded list.")
    for path in paths:
        value = _path(payload, path)
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                raise ConnectorError("invalid_result", "A mapped CRM JSON response could not be decoded.") from None
            if not isinstance(value, (dict, list)):
                raise ConnectorError("invalid_result", "A mapped CRM response must contain a JSON object or list.")
            parts = path.split(".")
            parent = _path(payload, ".".join(parts[:-1]))
            parent[parts[-1]] = value
    return payload


def _structured(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        if result.get("isError") or result.get("is_error"):
            raise ConnectorError("tool_error", "The CRM tool reported an error; its private response was withheld.")
        payload = result.get("structuredContent", result.get("structured_content"))
        content = result.get("content", [])
    else:
        if getattr(result, "is_error", False):
            raise ConnectorError("tool_error", "The CRM tool reported an error; its private response was withheld.")
        payload = getattr(result, "structured_content", None)
        content = getattr(result, "content", [])
    if payload is None:
        texts = [item.get("text") if isinstance(item, dict) else getattr(item, "text", None) for item in content]
        texts = [text for text in texts if isinstance(text, str)]
        if len(texts) != 1:
            raise ConnectorError("invalid_result", "The CRM tool must return one JSON object or structured output.")
        try:
            payload = json.loads(texts[0])
        except (ValueError, TypeError):
            raise ConnectorError("invalid_result", "The CRM tool did not return parseable JSON.") from None
    if not isinstance(payload, dict):
        raise ConnectorError("invalid_result", "The CRM tool must return a JSON object.")
    return payload


class MCPTransport:
    """A short-lived, explicit MCP connection using the official Python SDK v2.

    OAuth provisioning belongs to the user's MCP server/client. HTTP bearer
    headers and subprocess environment values are referenced by environment
    variable name; credentials are not stored in connector configuration.
    """

    def __init__(self, config: dict[str, Any]):
        self.config = copy.deepcopy(config)

    @asynccontextmanager
    async def open(self):
        from mcp import Client, StdioServerParameters, stdio_client

        kind = self.config.get("type")
        if kind == "stdio":
            env = _environment_values(self.config.get("env_from", {}))
            command = self.config.get("command")
            args = self.config.get("args", [])
            if not isinstance(command, str) or not command or not isinstance(args, list) or any(not isinstance(arg, str) for arg in args):
                raise ConnectorError("invalid_transport", "The local MCP command and argument list are required.")
            parameters = StdioServerParameters(command=command, args=args, env=env, cwd=self.config.get("cwd"))
            # Provider stderr may contain credentials. It never reaches the host.
            with open(os.devnull, "w") as errlog:
                async with Client(stdio_client(parameters, errlog=errlog)) as client:
                    yield client
        elif kind == "streamable_http":
            import httpx2
            from mcp.client.streamable_http import streamable_http_client

            url = self.config.get("url", "")
            parsed = urlsplit(url)
            loopback = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
            if not parsed.hostname or parsed.username or parsed.password or parsed.fragment or (parsed.scheme != "https" and not (parsed.scheme == "http" and loopback)):
                raise ConnectorError("invalid_transport", "Use an HTTPS MCP endpoint or local loopback HTTP endpoint without embedded credentials.")
            headers = _environment_values(self.config.get("headers_from_env", {}))
            async with httpx2.AsyncClient(headers=headers, timeout=httpx2.Timeout(15, read=30)) as http_client:
                async with Client(streamable_http_client(url, http_client=http_client)) as client:
                    yield client
        else:
            raise ConnectorError("invalid_transport", "Only configured stdio and Streamable HTTP transports are supported.")


def _environment_values(mapping: Any) -> dict[str, str]:
    if not isinstance(mapping, dict):
        raise ConnectorError("invalid_transport", "Environment references must be an object.")
    values = {}
    for key, variable in mapping.items():
        if not isinstance(key, str) or not isinstance(variable, str) or not variable or not os.environ.get(variable):
            raise ConnectorError("missing_credentials", "A configured MCP credential environment variable is unavailable.")
        values[key] = os.environ[variable]
    return values


class ConnectorGateway:
    def __init__(self, config: dict[str, Any], transports: dict[str, Any] | None = None):
        self.connections = copy.deepcopy(config.get("connections", {}))
        if not isinstance(self.connections, dict):
            raise ConnectorError("invalid_config", "Connections must be an object keyed by local connection ID.")
        self.transports = dict(transports or {})

    def _config(self, connection_id: str) -> dict[str, Any]:
        config = self.connections.get(connection_id)
        if not isinstance(config, dict) or not isinstance(config.get("account_id"), str) or not config["account_id"]:
            raise ConnectorError("unknown_connection", "The connection is missing or has no explicit account binding.")
        if not isinstance(config.get("operations"), dict):
            raise ConnectorError("invalid_mapping", "The connection has no reviewed operation mappings.")
        return config

    def connection_fingerprint(self, connection_id: str) -> str:
        return digest(self._config(connection_id))

    def _transport(self, connection_id: str):
        if connection_id in self.transports:
            return self.transports[connection_id]
        config = self._config(connection_id).get("transport", {})
        if config.get("type") == "fictional_fixture":
            if not config.get("state_path"):
                raise ConnectorError("invalid_transport", "The fictional fixture requires a local state path.")
            return FixtureTransport(state_path=config["state_path"])
        return MCPTransport(config)

    def _secrets(self, connection_id: str) -> tuple[str, ...]:
        transport = self._config(connection_id).get("transport", {})
        references = {**transport.get("env_from", {}), **transport.get("headers_from_env", {})}
        return tuple(os.environ[value] for value in references.values() if isinstance(value, str) and value in os.environ)

    def _mapping(self, connection_id: str, operation: str) -> dict[str, Any]:
        mapping = self._config(connection_id)["operations"].get(operation)
        if operation not in _OPERATIONS or not isinstance(mapping, dict):
            raise ConnectorError("unsupported_operation", "This CRM operation has no reviewed mapping.")
        tool = mapping.get("tool", "")
        if not isinstance(tool, str) or not tool or _FORBIDDEN_TOOL.search(tool):
            raise ConnectorError("unsafe_mapping", "Generic executors and connection-management tools cannot be mapped as CRM operations.")
        if not isinstance(mapping.get("input_schema"), dict) or not isinstance(mapping.get("arguments"), dict):
            raise ConnectorError("unreviewed_schema", "The operation requires a reviewed input schema and explicit arguments.")
        return mapping

    def has_operation(self, connection_id: str, operation: str) -> bool:
        try:
            self._mapping(connection_id, operation)
            return True
        except ConnectorError:
            return False

    def write_preview(self, connection_id: str, record_id: str, fields: dict) -> dict:
        """Resolve the exact provider payload for the operator's review."""
        _validate_record_id(record_id)
        fields = validate_fields(fields)
        mapping = self._mapping(connection_id, "update_fields")
        placeholders = _placeholders(mapping["arguments"])
        if placeholders.count("$record_id") != 1 or placeholders.count("$fields") != 1:
            raise ConnectorError("unsafe_mapping", "An update mapping must bind the exact record ID and complete field object once each.")
        config = self._config(connection_id)
        allowed = config.get("writable_fields")
        if allowed is not None and (not isinstance(allowed, list) or not set(fields).issubset(allowed)):
            raise ConnectorError("unsupported_fields", "These fields are outside this connection's reviewed writable field list.")
        arguments = _render(mapping["arguments"], {"account_id": config["account_id"], "record_id": record_id, "fields": fields})
        if safe_value(arguments, self._secrets(connection_id)) != arguments:
            raise ConnectorError("sensitive_payload", "The mapped provider payload contains credential values.")
        return {"tool": mapping["tool"], "arguments": arguments, "input_schema_hash": digest(mapping["input_schema"])}

    async def _tools(self, session: Any) -> dict[str, dict[str, Any]]:
        tools = {}
        cursor = None
        seen = set()
        for _ in range(100):
            result = await session.list_tools(cursor=cursor)
            rows = result.get("tools", []) if isinstance(result, dict) else result.tools
            for tool in rows:
                name = tool.get("name") if isinstance(tool, dict) else tool.name
                schema = tool.get("inputSchema", tool.get("input_schema")) if isinstance(tool, dict) else tool.input_schema
                if name in tools:
                    raise ConnectorError("invalid_discovery", "The MCP server returned duplicate tool names.")
                tools[name] = schema
            cursor = result.get("nextCursor", result.get("next_cursor")) if isinstance(result, dict) else result.next_cursor
            if not cursor:
                return tools
            if cursor in seen:
                break
            seen.add(cursor)
        raise ConnectorError("invalid_discovery", "Tool discovery pagination did not complete.")

    async def _call(self, session: Any, tools: dict, connection_id: str, operation: str, context: dict) -> dict:
        from jsonschema import Draft202012Validator

        mapping = self._mapping(connection_id, operation)
        schema = tools.get(mapping["tool"])
        if schema != mapping["input_schema"]:
            raise ConnectorError("schema_changed", "The mapped tool is missing or its schema changed; operator review is required.")
        arguments = _render(mapping["arguments"], context)
        try:
            Draft202012Validator.check_schema(schema)
            errors = list(Draft202012Validator(schema).iter_errors(arguments))
        except Exception:
            raise ConnectorError("invalid_mapping", "The reviewed input schema is invalid.") from None
        if errors:
            raise ConnectorError("invalid_arguments", "Mapped CRM arguments do not satisfy the reviewed tool schema.")
        result = await session.call_tool(mapping["tool"], arguments)
        return _normalize_output(_structured(result), mapping)

    @asynccontextmanager
    async def _bound(self, connection_id: str):
        config = self._config(connection_id)
        try:
            async with asyncio.timeout(45):
                async with self._transport(connection_id).open() as session:
                    tools = await self._tools(session)
                    context = {"account_id": config["account_id"]}
                    identity = await self._call(session, tools, connection_id, "identify_account", context)
                    mapping = self._mapping(connection_id, "identify_account")
                    observed = _path(identity, mapping.get("result", {}).get("account_id", "account_id"))
                    if str(observed) != config["account_id"]:
                        raise ConnectorError("account_mismatch", "The connected CRM account does not match this connection's approved account.")
                    yield session, tools, context
        except ConnectorError:
            raise
        except TimeoutError:
            raise ConnectorError("transport_timeout", "The CRM connection timed out; no upstream details were returned.") from None
        except Exception:
            raise ConnectorError("transport_error", "The CRM connection failed; no upstream details were returned.") from None

    def _check_result_account(self, connection_id: str, result: dict, mapping: dict) -> None:
        account_path = mapping.get("result", {}).get("account_id")
        if account_path is not None and str(_path(result, account_path)) != self._config(connection_id)["account_id"]:
            raise ConnectorError("account_mismatch", "The CRM result belongs to a different account.")

    def _record(self, connection_id: str, item: dict, mapping: dict) -> dict[str, Any]:
        paths = mapping.get("result", {})
        record_id = _path(item, paths.get("record_id", "id"))
        fields = _path(item, paths.get("fields", "fields"))
        if not isinstance(record_id, (str, int)) or isinstance(record_id, bool) or not str(record_id) or not isinstance(fields, dict):
            raise ConnectorError("invalid_result", "The CRM record is missing its native ID or fields.")
        config = self._config(connection_id)
        snapshot = {"connection_id": connection_id, "account_id": config["account_id"], "record_id": str(record_id), "fields": safe_value(fields, self._secrets(connection_id))}
        snapshot["snapshot_hash"] = digest(snapshot)
        snapshot["observed_at"] = utc_now()
        snapshot["provider"] = config.get("provider", "custom-mcp")
        return snapshot

    async def status(self, connection_id: str) -> dict[str, Any]:
        async with self._bound(connection_id) as (_, tools, _):
            operations = {}
            for operation in _OPERATIONS:
                try:
                    mapping = self._mapping(connection_id, operation)
                    operations[operation] = "configured_schema_matches" if tools.get(mapping["tool"]) == mapping["input_schema"] else "schema_changed"
                except ConnectorError:
                    operations[operation] = "not_configured"
            config = self._config(connection_id)
            return {"connection_id": connection_id, "account_id": config["account_id"], "provider": config.get("provider", "custom-mcp"), "account_verified": True, "operations": operations, "support_status": "configured_experimental", "note": "Account and schema checks do not certify provider behavior or all CRM capabilities."}

    async def inspect_tools(self, connection_id: str) -> dict[str, Any]:
        """Read-only CLI setup aid: list schemas without invoking any CRM tool.

        Inspecting schemas does not approve them. The operator must review the
        tool semantics, account binding, argument templates and result mapping.
        This method deliberately does not create or modify configuration.
        """
        self._config(connection_id)
        try:
            async with asyncio.timeout(45):
                async with self._transport(connection_id).open() as session:
                    discovered = await self._tools(session)
                    tools = [{"name": name, "input_schema": safe_value(schema, self._secrets(connection_id)), "input_schema_hash": digest(schema), "generic_executor_blocked": bool(_FORBIDDEN_TOOL.search(name))} for name, schema in discovered.items()]
                    return {"connection_id": connection_id, "account_verified": False, "review_required": True, "tools": tools, "note": "Discovery only. Tool schemas and descriptions are untrusted until reviewed; no CRM tool was executed."}
        except ConnectorError:
            raise
        except Exception:
            raise ConnectorError("discovery_failed", "MCP tool discovery failed; upstream details were withheld.") from None

    async def read_record(self, connection_id: str, record_id: str) -> dict[str, Any]:
        _validate_record_id(record_id)
        mapping = self._mapping(connection_id, "get_record")
        async with self._bound(connection_id) as (session, tools, context):
            result = await self._call(session, tools, connection_id, "get_record", {**context, "record_id": record_id})
            self._check_result_account(connection_id, result, mapping)
            record = self._record(connection_id, result, mapping)
            if record["record_id"] != record_id:
                raise ConnectorError("record_mismatch", "The CRM returned a different native record ID.")
            return record

    async def search_records(self, connection_id: str, query: str, limit: int = 20) -> dict[str, Any]:
        if not isinstance(query, str) or not query.strip() or len(query) > 2_000 or type(limit) is not int or not 1 <= limit <= 100:
            raise ConnectorError("invalid_query", "Use a nonempty search query and a limit between one and one hundred.")
        mapping = self._mapping(connection_id, "search_records")
        async with self._bound(connection_id) as (session, tools, context):
            result = await self._call(session, tools, connection_id, "search_records", {**context, "query": query, "limit": limit})
            self._check_result_account(connection_id, result, mapping)
            rows = _path(result, mapping.get("result", {}).get("records", "records"))
            if not isinstance(rows, list):
                raise ConnectorError("invalid_result", "CRM search did not return a record list.")
            records = [self._record(connection_id, row, mapping) for row in rows[:limit]]
            cursor_path = mapping.get("result", {}).get("next_cursor")
            try:
                more = _path(result, cursor_path) if cursor_path else None
            except ConnectorError:
                more = None  # Providers commonly omit the final-page cursor.
            more_results = bool(more) if cursor_path else None
            if len(rows) > limit:
                more_results = True
            return {"connection_id": connection_id, "account_id": self._config(connection_id)["account_id"], "records": records, "coverage": "bounded_search", "more_results": more_results, "note": "This search is not proof of exhaustive account history."}

    async def update_fields(self, connection_id: str, record_id: str, fields: dict[str, Any]) -> None:
        """Internal operation for ChangeManager. Do not expose as an MCP tool."""
        _validate_record_id(record_id)
        fields = validate_fields(fields)
        self.write_preview(connection_id, record_id, fields)
        if safe_value(fields, self._secrets(connection_id)) != fields:
            raise ConnectorError("invalid_fields", "Credential values cannot be saved as CRM fields.")
        self._mapping(connection_id, "update_fields")
        async with self._bound(connection_id) as (session, tools, context):
            await self._call(session, tools, connection_id, "update_fields", {**context, "record_id": record_id, "fields": fields})


def _validate_record_id(record_id: str) -> None:
    if not isinstance(record_id, str) or not record_id or len(record_id) > 500:
        raise ConnectorError("invalid_record_id", "An exact native CRM record ID is required.")


def composio_hubspot_connection_config(
    inspected: dict, *, connection_id: str, account_id: str,
    transport: dict, properties: list[str], account_id_path: str,
) -> dict:
    """Generate a local draft from operator-reviewed native tool discovery.

    For Composio's session MCP direct-tools preset, never its shared meta-tool
    endpoint. Tool names and company argument names follow the official catalog;
    the current input schemas come from the user's endpoint. The account result
    path must be supplied from verified account-tool documentation/output because
    discovering a tool alone cannot establish its actual provider response.

    This function does not connect an account, approve mappings, or certify the
    integration. Inspect the generated configuration before writing it locally.
    """
    required = {
        "identify_account": "HUBSPOT_GET_ACCOUNT_INFO",
        "get_record": "HUBSPOT_GET_COMPANY",
        "search_records": "HUBSPOT_SEARCH_COMPANIES",
        "update_fields": "HUBSPOT_UPDATE_COMPANY",
    }
    if not isinstance(properties, list) or not properties or any(not isinstance(item, str) or not item or _SECRET_KEY.search(item) for item in properties):
        raise ConnectorError("invalid_properties", "Choose explicit noncredential company property names to read and save.")
    if not isinstance(account_id_path, str) or not account_id_path or account_id_path.startswith("$"):
        raise ConnectorError("invalid_mapping", "An operator-reviewed account result path is required.")
    rows = inspected.get("tools", [])
    schemas = {row.get("name"): row.get("input_schema") for row in rows if isinstance(row, dict)}
    if any(not isinstance(schemas.get(tool), dict) for tool in required.values()):
        raise ConnectorError("missing_composio_tools", "The Composio endpoint must expose the four native HubSpot company tools through its direct-tools preset.")
    args = {
        "identify_account": {},
        "get_record": {"companyId": "$record_id", "properties": properties},
        "search_records": {"query": "$query", "limit": "$limit", "properties": properties},
        "update_fields": {"companyId": "$record_id", "properties": "$fields"},
    }
    results = {
        "identify_account": {"account_id": account_id_path},
        "get_record": {"record_id": "data.id", "fields": "data.properties"},
        "search_records": {"records": "data.results", "record_id": "id", "fields": "properties", "next_cursor": "data.paging.next.after"},
        "update_fields": {},
    }
    operations = {operation: {"tool": tool, "input_schema": copy.deepcopy(schemas[tool]), "arguments": args[operation], "result": {"success": "successful", "json_decode_paths": ["data"], **results[operation]}} for operation, tool in required.items()}
    return {"connections": {connection_id: {"provider": "composio-hubspot-experimental", "account_id": account_id, "transport": copy.deepcopy(transport), "writable_fields": list(properties), "operations": operations}}}


_FIXTURE_SCHEMAS = {
    "fictional_account": {"type": "object", "properties": {}, "additionalProperties": False},
    "fictional_get_record": {"type": "object", "properties": {"account_id": {"type": "string"}, "record_id": {"type": "string"}}, "required": ["account_id", "record_id"], "additionalProperties": False},
    "fictional_search_records": {"type": "object", "properties": {"account_id": {"type": "string"}, "query": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["account_id", "query", "limit"], "additionalProperties": False},
    "fictional_update_fields": {"type": "object", "properties": {"account_id": {"type": "string"}, "record_id": {"type": "string"}, "fields": {"type": "object"}}, "required": ["account_id", "record_id", "fields"], "additionalProperties": False},
}


def fixture_connection_config(state_path: str | Path | None = None) -> dict[str, Any]:
    """Public fictional demo mapping, never a real provider configuration."""
    mapping = {}
    for operation, name, args in [
        ("identify_account", "fictional_account", {}),
        ("get_record", "fictional_get_record", {"account_id": "$account_id", "record_id": "$record_id"}),
        ("search_records", "fictional_search_records", {"account_id": "$account_id", "query": "$query", "limit": "$limit"}),
        ("update_fields", "fictional_update_fields", {"account_id": "$account_id", "record_id": "$record_id", "fields": "$fields"}),
    ]:
        mapping[operation] = {"tool": name, "input_schema": copy.deepcopy(_FIXTURE_SCHEMAS[name]), "arguments": args, "result": {"account_id": "account_id", "record_id": "id", "fields": "fields", "records": "records", "next_cursor": "next_cursor"}}
    return {"connections": {"fictional-demo": {"provider": "fictional-crm", "account_id": "fictional-account", "transport": {"type": "fictional_fixture", "state_path": str(state_path) if state_path else None}, "operations": mapping}}}


class FixtureTransport:
    """Fictional CRM test transport, optionally persisted across CLI invocations."""

    def __init__(self, records: dict[str, dict] | None = None, *, account_id: str = "fictional-account", state_path: str | Path | None = None):
        self.account_id = account_id
        self.records = copy.deepcopy(records if records is not None else {"company-001": {"name": "Fictional Acorn Studio", "industry": "Design", "research_summary": "No research saved yet."}})
        self.schemas = copy.deepcopy(_FIXTURE_SCHEMAS)
        self.calls: list[tuple[str, dict]] = []
        self.state_path = Path(state_path).expanduser() if state_path else None
        if self.state_path:
            self.state_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with closing(sqlite3.connect(self.state_path)) as db, db:
                db.execute("CREATE TABLE IF NOT EXISTS fictional_crm (account_id TEXT, record_id TEXT, fields TEXT, PRIMARY KEY(account_id, record_id))")
                for record_id, fields in self.records.items():
                    db.execute("INSERT OR IGNORE INTO fictional_crm VALUES (?, ?, ?)", (account_id, record_id, canonical_json(fields)))
            os.chmod(self.state_path, 0o600)

    def _load(self) -> dict:
        if not self.state_path:
            return copy.deepcopy(self.records)
        with closing(sqlite3.connect(self.state_path)) as db, db:
            return {record_id: json.loads(fields) for record_id, fields in db.execute("SELECT record_id, fields FROM fictional_crm WHERE account_id=?", (self.account_id,))}

    @asynccontextmanager
    async def open(self):
        yield self

    async def list_tools(self, *, cursor=None):
        return {"tools": [{"name": name, "inputSchema": schema} for name, schema in self.schemas.items()]}

    async def call_tool(self, name: str, arguments: dict):
        self.calls.append((name, copy.deepcopy(arguments)))
        if name == "fictional_account":
            payload = {"account_id": self.account_id, "fictional": True}
        elif arguments.get("account_id") != self.account_id:
            return {"isError": True, "content": [{"type": "text", "text": "Account mismatch."}]}
        elif name == "fictional_search_records":
            records = [{"id": rid, "fields": fields} for rid, fields in self._load().items() if arguments["query"].casefold() in canonical_json(fields).casefold()]
            limit = arguments["limit"]
            payload = {"account_id": self.account_id, "records": records[:limit], "next_cursor": "more" if len(records) > limit else None}
        elif name in {"fictional_get_record", "fictional_update_fields"}:
            records = self._load()
            record_id = arguments["record_id"]
            if record_id not in records:
                return {"isError": True, "content": [{"type": "text", "text": "Record missing."}]}
            fields = records[record_id]
            if name == "fictional_update_fields":
                fields.update(arguments["fields"])
                if self.state_path:
                    with closing(sqlite3.connect(self.state_path)) as db, db:
                        db.execute("UPDATE fictional_crm SET fields=? WHERE account_id=? AND record_id=?", (canonical_json(fields), self.account_id, record_id))
                else:
                    self.records[record_id] = copy.deepcopy(fields)
            payload = {"account_id": self.account_id, "id": record_id, "fields": fields}
        else:
            return {"isError": True, "content": [{"type": "text", "text": "Unknown fictional tool."}]}
        return {"structuredContent": copy.deepcopy(payload), "isError": False}
