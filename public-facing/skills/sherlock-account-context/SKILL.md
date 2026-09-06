---
name: sherlock-account-context
description: Match a lead or company to its CRM record, combine research with account context, and manage reviewed CRM changes through Agent Sherlock.
---

# Account context

Discover Sherlock's configured CRM capabilities with `crm_status` and the live tool schemas. Use `crm_search` and `crm_read` through the actual available adapter or mapped MCP gateway. A familiar provider name or a listed tool does not prove that the user's account, authentication, permissions, or field mapping works.

Read the selected connection's identity and the relevant existing record. Match company domain, CRM record ID, and available account context; surface duplicates or ambiguous matches. An unconnected provider, missing scope, unsupported object, or incompatible response needs an actionable explanation, not a guessed record or invented result.

Research with the host's available tools and preserve source/date evidence in the correct Sherlock case. Show useful account context, conflicts, missing information, and suggested next steps.

For an external change:

1. Identify the provider, account, object type, record ID, exact action, fields, values, and supporting evidence.
2. Use `change_propose` and show the proposed change clearly. A proposed change has not been saved to the CRM.
3. Direct the operator to run the local CLI `sherlock review PROPOSAL_ID`, using the same data directory/profile/config as the MCP server. The operator reviews the exact preview and chooses approval or rejection. There is no MCP approval tool. Do not pipe input into the prompt, type approval on the operator's behalf, or edit the approval database. An active, explicit autosave policy may cover every requested action and field in that account; never activate or broaden that policy yourself.
4. Use `change_apply` for the approved or policy-covered proposal and inspect `change_status`. Readback is required for a verified-saved claim. A success acknowledgment without readback is not verified saving.

Do not bypass Sherlock's write controls by calling the underlying CRM/gateway tool directly. For an interrupted, partial, or uncertain proposal use `change_reconcile`, which reads the destination without issuing another write. Preserve the proposal ID and inspect the returned state; do not repeatedly call `change_apply` or create replacement proposals to force a retry.

Declined approval, missing permissions, stale prior values, partial failure, and verification failure must remain visible. Stop dependent changes if identity or outcome is uncertain. Never create records, delete data, change owners, or send outreach unless that specific action is implemented and authorized.
