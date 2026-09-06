# Connect a CRM through Sherlock

The local gateway maps a small set of reviewed CRM operations to tools exposed by another MCP server. It supports local stdio and configured Streamable HTTP transports. The adapter is available in this build; live HubSpot/Composio and custom-CRM account validation remains pending. There is no automatic provider signup, hidden shared account, or blanket compatibility claim.

## Start with fictional CRM data

[fictional-crm.json](examples/fictional-crm.json) is a complete mapping generated from the runtime's fictional fixture contract. Its provider, account, records, and tools are fictional. Replace its state path with a private local file path and keep the `demo` profile. It contains no real CRM credential and makes no external CRM calls.

The fixture provides `Fictional Acorn Studio`, record `company-001`, through connection `fictional-demo`. Use it to practice `crm_status`, `crm_search`, `crm_read`, and the proposal → operator review → apply → readback workflow. An approved fixture write changes the local fixture only. The ordinary `demo` command demonstrates local case/evidence/recall; it does not establish live CRM connectivity.

## Prepare a real connection

1. Select your own provider account and supported MCP endpoint/process through the provider's setup flow. Confirm permissions and the exact account identity. Use a test account for initial mutation checks.
2. Copy [remote-crm.template.json](examples/remote-crm.template.json) to a private location outside the checkout. Replace its endpoint and account placeholder. The template is intentionally incomplete: empty `operations` cannot perform CRM work.
3. Make the provider-required authentication header available to the Sherlock process through the named environment variable. `headers_from_env` copies the environment value as the full header value; it does not add a `Bearer` prefix. Use the exact header names/scheme required by your endpoint. Do not place secrets in shell arguments, the template, or chat.
4. With the selected private config, inspect the endpoint's tools and schemas using the operator CLI `connector-inspect CONNECTION_ID`. This contacts the configured MCP endpoint and runs tool discovery only; it does not call the listed CRM tools or approve their behavior.
5. Review and add the required operation mappings below, then restart Sherlock with that config. Use `crm_status` to verify the actual account and schema bindings, followed by a bounded search and exact record read.
6. Enable a reviewed `update_fields` mapping only when you intend to test that action. Preserve approval-required policy and use one specifically approved fictional/test record update. Verify the destination values and record the result in the compatibility matrix.

Use the source launcher and global-option ordering from [install.md](install.md). For example, after replacing `my-crm` and the config path:

```sh
uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" --profile personal --config "/absolute/path/to/private/sherlock.json" connector-inspect my-crm
```

The runtime does not automatically consume another host's CRM connector registration, OAuth token, or tool inventory. Configure the upstream MCP connection explicitly. Keep the upstream direct CRM write tools out of an agent's separate tool surface if you expect all its writes to pass through Sherlock's controls.

## Mapping contract

Each connection has an explicit `account_id`, transport, and `operations` map. The complete [fictional example](examples/fictional-crm.json) shows the structure without suggesting real-provider tool names.

| Operation | Required behavior | Arguments available to the template |
| --- | --- | --- |
| `identify_account` | Read the actual connected account identity and return it for comparison with `account_id`. | `$account_id` |
| `search_records` | Return bounded candidate records with native IDs and field objects. | `$account_id`, `$query`, `$limit` |
| `get_record` | Read one exact native record and its current fields for context, stale checks, and readback. | `$account_id`, `$record_id` |
| `update_fields` | Update the exact mapped record fields; only Sherlock's change manager invokes this operation. | `$account_id`, `$record_id`, `$fields` |

A mapping includes the native `tool`, the complete reviewed `input_schema`, an `arguments` object, and `result` paths. Arguments can include literal reviewed values, such as a specific object type, and the exact placeholders above. Placeholders replace whole JSON values; there is no expression evaluation or string-template language.

Result extraction uses dotted object-key paths, not JSONPath expressions or array indexes. Relevant keys are `account_id`, `records`, `record_id`, `fields`, and optional `next_cursor`. Record ID/field paths apply to each record object in search results. The upstream tool must return structured JSON or one parseable JSON-object text response. A schema change stops execution for operator review.

The identity operation must establish the connected account from provider data; returning the configured label alone is not a meaningful account check. The search route is bounded and does not promise full CRM history or automatic pagination. The current controlled mutation is field updates; record creation, deletion, outreach, and arbitrary tool execution are not exposed through this gateway.

## HubSpot through Composio

Use a per-user Composio session that exposes native tools through the direct-tools preset, with MCP enabled. Bind the intended existing connected HubSpot account explicitly. The shared Composio Connect route with generic execution/meta tools is not supported by Sherlock's controlled gateway. Composio documents both [MCP direct-tool sessions](https://docs.composio.dev/docs/sessions-via-mcp) and [connected-account selection](https://docs.composio.dev/docs/configuring-sessions#account-selection).

This operator setup template requires the selected IDs and reviewed native tool slugs first; it is not runnable with guessed values. Composio is an optional separate dependency, not installed by Sherlock:

```python
from composio import Composio, SESSION_PRESET_DIRECT_TOOLS

composio = Composio()
session = composio.sessions.create(
    user_id=selected_composio_user_id,
    toolkits=["hubspot"],
    connected_accounts={"hubspot": [selected_connected_account_id]},
    tools={"hubspot": {"enable": reviewed_native_tool_slugs}},
    session_preset=SESSION_PRESET_DIRECT_TOOLS,
    mcp=True,
)
# Configure Sherlock privately from session.mcp.url and session.mcp.headers.
# Do not print authentication headers or commit the session configuration.
```

Review the session's actual native tools before creating Sherlock mappings. The selected set must provide account identity, search, exact record read, and, when enabled, field updates. Keep generic executors, connection-management, and remote-code tools out of those mappings. If the required identity/readback behavior cannot be supplied, the connection remains unsupported for the corresponding workflow.

## Compatibility by CRM, route, and operation

| CRM / route | Identity, search, and read | Field proposal / approval | Field apply / readback | Evidence status |
| --- | --- | --- | --- | --- |
| Fictional CRM / local fixture | Implemented fixture contract | Operator review or explicit fixture policy | Local fixture update and readback | Local verification only; never real-provider proof. |
| HubSpot / Composio direct-tools session | Requires reviewed native schemas and bound account | Available through the generic mapping contract | Requires live test-account verification | Adapter available; live-account validation pending. |
| Other CRM / custom stdio MCP | Requires reviewed mappings | Available for mapped field updates | Requires provider-specific readback | Experimental until that exact route is verified. |
| Other CRM / custom Streamable HTTP MCP | Requires reviewed mappings and auth header setup | Available for mapped field updates | Requires provider-specific readback | Experimental until that exact route is verified. |
| Composio Connect / generic meta executor | Not an accepted controlled operation mapping | Unsupported | Unsupported | Use a reviewed native-tool route instead. |

Track actual tested host/provider versions and operations using [compatibility.md](compatibility.md). Installing a skill, discovering tools, passing a fixture test, and successfully updating a real CRM record are separate results. See [permissions.md](permissions.md) for the approval contract and [operations.md](operations.md) for recovery.
