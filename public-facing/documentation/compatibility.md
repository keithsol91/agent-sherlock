# Compatibility and evidence

Read this table as a record of what has been checked, not a promise that a matching product name guarantees interoperability. Host versions and MCP tool schemas can change. Configuration recipes were checked against official sources on 6 September 2026; live host and provider checks must be recorded against the release candidate separately.

| Surface | Intended connection | Current evidence / boundary |
| --- | --- | --- |
| Local Python runtime | Source checkout, Python 3.11+, stdio MCP | Implementation and local test results are maintained with the runtime; inspect the release verification record. |
| Claude Code | Local stdio MCP plus skill folders | Claude Code 2.1.261: limited fictional case/evidence/recall, skill loading, and restart smoke passed; see the scoped evidence below. |
| Codex local clients | Local stdio MCP plus skill folders | Official setup syntax and local CLI help checked; Sherlock host smoke pending. |
| Hermes | `mcp_servers` YAML plus skill folders | Official configuration shape checked; Sherlock host smoke pending. |
| OpenClaw | Outbound `mcp.servers` registry plus workspace skills | Current official registry documented; Sherlock host smoke pending. Legacy mcporter needs separate validation. |
| ChatGPT web / remote host | Separate authenticated remote MCP deployment | Not supplied by this local stdio build. Do not paste a local filesystem path into a remote-server URL field. |
| HubSpot via configured adapter | User-owned CRM account and required scopes | Fixture/contract tests and live-account verification are separate. Do not infer a working connection from a successful demo. |
| Composio or custom CRM MCP | Explicitly mapped gateway tools and account identity | Compatibility depends on actual tool schemas, records, readback, and write policy. Generic MCP support alone is insufficient. |
| Research sources | Existing host search/browser or user-supplied sources | Sherlock stores evidence; the local service does not itself crawl social platforms or buy research access. |
| Slack | User's selected host/channel integration | Delivery configuration and end-to-end verification are separate from local recall. A standalone public Slack bot is not implied. |

## How a connection earns a compatibility label

- **Documented:** the installation/configuration recipe matches the upstream reference.
- **Protocol tested:** initialization, tool discovery, input validation, and a tool call passed using an MCP client against this build.
- **Workflow tested with fixtures:** a full workflow passed with fictional data and controlled failures.
- **Host tested:** the named host/version discovered and invoked this Sherlock build, including persistence across a restart.
- **Live provider read tested:** the account identity, required scopes, search, record read, and expected field shapes were verified in an authorized external test account.
- **Live provider write tested:** one specifically approved test mutation was applied, read back, and reconciled in that account. This label does not cover untested actions or object types.

## Claude Code host smoke — 6 September 2026

Claude Code 2.1.261 used Sherlock 0.1.0a1 from review snapshot `6c5198a` with Python 3.12.13, a temporary strict MCP configuration, and an isolated fictional profile. Actual MCP calls created a case, added evidence and a finding, then read and recalled those records. A second host process loaded `agent-sherlock` and `sherlock-recall` through its Skill tool and retrieved the same persisted records. Both runs completed with no permission denials.

The initial harness disabled all setting sources, which prevented skill discovery; allowing the temporary project's settings fixed that test setup. This evidence covers the temporary host configuration and the named workflows. It does not establish persistent `mcp add` installation, other hosts, live website research, CRM access, Slack delivery, or a human beta. Fictional source content was supplied to the host; it was not independently fetched from the example domain. Detailed local test artifacts remain outside the public package.

Maintain labels per host, provider, object, and action. A read test does not certify writes. A mock response does not certify provider authentication. A gateway's `tools/list` result does not certify its field mappings or account isolation.

For a custom CRM gateway, validate the actual search/read/write tools, request arguments, result extraction paths, record IDs, account identity, supported fields, error semantics, and readback capability. Preserve the connector's unsupported state when this contract cannot be satisfied. Do not guess a Composio tool slug, installed toolkit version, HubSpot portal, or schema from its name.

## Record a reproducible verification

Capture the Sherlock commit/version, host/version, OS/runtime, profile alias, adapter/tool schema version, tested operations, fixture versus live status, result, and remaining limitations. Use aliases for external test accounts. Omit secrets and private payloads from shared evidence. A successful pilot should also exercise token expiry, missing permissions, uncertain writes, restart, correction, and deletion/recall behavior.

These guides intentionally avoid a blanket “works with every agent/CRM” claim. Use the [install guide](install.md) to reproduce the relevant local path, then promote its label only after the matching evidence exists.
