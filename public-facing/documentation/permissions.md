# Data, connection, and write permissions

Sherlock's local MCP process is bound to one data directory and profile at startup. Its tools cannot select another profile. A profile is an organizational boundary within the trusted operating-system account, not a hosted multi-tenant authentication system. Anyone who can read its files or control its process may access its records.

## Choose where data lives

Use explicit `--data-dir`, `--profile`, and, when needed, `--config` options before the CLI subcommand. Their environment equivalents are `SHERLOCK_DATA_DIR`, `SHERLOCK_PROFILE`, and `SHERLOCK_CONFIG`. The default profile is `default`.

Default data roots are:

| Platform | Default root |
| --- | --- |
| macOS | `~/Library/Application Support/AgentSherlock` |
| Linux | `$XDG_DATA_HOME/agent-sherlock`, falling back to `~/.local/share/agent-sherlock` |
| Windows | `%LOCALAPPDATA%/AgentSherlock` |

Each profile has its own case and change stores. A configuration's optional `profile` value must match the selected profile. Configuration files are JSON and are loaded only when selected explicitly or through `SHERLOCK_CONFIG`; the runtime does not promise automatic `.env` loading.

Use separate processes/profiles for distinct trusted work contexts. This build permits one server process per profile, so two hosts cannot concurrently open the same profile through separate Sherlock servers. Do not expose a profile containing multiple customers' confidential records to an untrusted shared channel or remote caller. Shared/team hosting, authentication, and Slack sender-to-data authorization require their own deployment design and verification.

Your host may send research, CRM results, or retrieved evidence to its model provider as part of the conversation. Sherlock's local storage does not make that host's processing local. Host transcripts, provider records, backups, and exports have separate retention behavior.

## Connect your own CRM deliberately

The no-key demo creates a fictional local connection without contacting external providers. For an optional real connection, use the [integration guide and configuration examples](integrations.md) and the actual adapter schema. Keep that private config outside the repository. Use environment-variable references for credentials rather than placing token values in examples, shell arguments, or chat.

Confirm the selected account identity, supported object types and fields, required scopes, and readback behavior before enabling writes. For a Composio/custom MCP gateway, discover and map its real tool names and response paths. The gateway's own login and permissions remain its responsibility; Sherlock does not create a Composio account or install a provider app for you.

Start with reads and a user-owned test account. `crm_status` reports the connection state, `crm_search` locates candidates, and `crm_read` verifies the chosen record. A configured account label or a generic MCP handshake does not prove the credentials, record mappings, or granted scopes work. See [compatibility.md](compatibility.md) for evidence levels.

## Approve one exact change

The agent uses `change_propose` to prepare a field update. You review the record identity, current and proposed values, evidence, and the exact rendered provider tool call before applying it. Connection-level `writable_fields`, when configured, limits the fields available even for a manually approved proposal.

Using the variables from the install guide, run this yourself in an interactive terminal:

```sh
uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" --profile personal review PROPOSAL_ID
```

If the server uses a private configuration, include the same selection before `review`:

```sh
uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" --profile personal --config "/absolute/path/to/private/sherlock.json" review PROPOSAL_ID
```

Replace `PROPOSAL_ID` with the identifier returned by `change_propose`. Read the preview and choose approval or rejection. The agent has no MCP approval tool and must not automate your review prompt. Approved proposals can then be submitted through `change_apply`; inspect `change_status` for their actual outcome.

Approval covers that proposal, not arbitrary future changes. A changed target, changed values, missing permission, or stale source record may require a new proposal. Use `change_reconcile` for interrupted, partial, or uncertain outcomes; it reads the destination without repeating the mutation. Only its actual verified result establishes the saved state.

This is a boundary within Sherlock's MCP interface, not proof that an unrestricted host cannot act as you. An agent with unrestricted access to your shell, files, or another CRM connector may bypass application-level restrictions. Keep host permissions appropriate to that trust level. The Sherlock skills explicitly prohibit self-approval through shell commands, editing the approval store, or modifying autosave policy.

## Optional autosave

Approval-required writes are the default. The operator-owned JSON config supports `policy.autosave.enabled` and an array of `policy.autosave.rules`. Each rule must match `connection_id`, `account_id`, and `action`, and name its allowed `fields`. The current action is `update_fields`. An optional `record_ids` list narrows the rule to those records; omitting it permits matching field updates to any record in the bound account. Wildcard field and record entries are not supported.

Keep autosave disabled during initial setup. To opt in, review the specific connection, account, action, fields, and record scope before setting `enabled` to true and restarting the service with that config. A skill, source page, or CRM note cannot grant autosave authority. The agent must not enable or expand its own policy.

A CRM token having write scope is not itself approval to use it. Host-level “allow this tool” settings are also separate from Sherlock's proposal policy. Autosave does not certify that a provider supports the requested field/action or that a failed write succeeded.

## Disconnect, export, or delete

Remove or disable the intended connection in the selected private config and restart its Sherlock process. Revoke the provider credential separately when you want provider-side access removed. Disconnecting does not delete previously saved case evidence.

Export, backup, restore, and case deletion are local operator CLI commands. For a selected case:

```sh
uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" --profile personal delete-case CASE_ID --confirm CASE_ID
```

Replace both occurrences with the same exact case ID after checking the scope. Verify it is absent from case retrieval and recall afterward. This removes Sherlock's local case data; it does not retract existing exports, host conversations, backups, or external CRM records. Do not describe it as deletion from every system.
