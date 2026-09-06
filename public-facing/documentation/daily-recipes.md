# Use Sherlock during the workday

Ask your existing agent to use the `agent-sherlock` skill, or select one of its four workflow skills. Your host supplies reasoning and any available research tools. Sherlock maintains the selected profile's cases and evidence. Tool names below are the server's names; hosts may add prefixes.

## Investigate a competitor

> Use Sherlock to compare our company with the two competitors at these verified URLs. Focus on organic themes, public audience questions, and visible ad concepts from the last 30 days. Save a sourced case and suggest three experiments. Tell me which sources you could not inspect.

The agent resolves identities, creates or reuses a case, uses `research_prepare` to record the research question and scope, and researches through the host's tools. It records sources with `evidence_add`, including the matching `metadata.scope`, saves supported findings with `finding_add`, and checks `research_status`. The server associates evidence with the current research run. The brief should distinguish facts, inference, recommendations, and missing coverage. A research plan does not mean collection has happened.

## Prepare for an account conversation

> Use my selected CRM connection to find this company by domain. Read the existing record, review the relevant case, and prepare a concise brief with recent evidence and open questions. Propose any useful CRM changes for review.

`crm_status` checks the connection, `crm_search` finds candidates, and `crm_read` inspects the chosen record. The agent resolves duplicates and saves research in the correct case before using `change_propose`. A proposal does not modify the external CRM.

For approval-required changes, review the exact proposal in your own terminal using the command pattern in [permissions.md](permissions.md). The agent cannot approve a proposal through MCP. After approval, it uses `change_apply` and `change_status`; use the read-only `change_reconcile` path for interrupted, partial, or uncertain outcomes.

## Keep a living case up to date

> Add this new source to the company case. It changes our earlier conclusion about their launch date. Preserve the earlier evidence and record why the finding changed.

The agent reads the case with `case_get`, adds the new observation, and uses `finding_correct` with the reason and supporting evidence. Case edits use the actual revision returned by the runtime where `case_update` requires it. The result should identify what changed and show the saved case. Saving locally does not also update HubSpot.

Use `case_type='client'` only for records that actually represent client experience. An account under investigation is not automatically a client. Use categories consistently when you want reliable category counts.

## Recall experience for a pitch or another agent

> Which recorded clients have we worked with in automotive? Count each company once, show what we did, link the evidence, and tell me whether the record set is complete enough to support the count.

The agent uses `recall_search`, inspects relevant cases, and uses `recall_count` for supported structured counts. Counts depend on case classification, category, deduplication, and available history. Zero matches means no relevant saved context was found, not proof that the work never happened.

> Give my strategy agent the useful context from the latest competitor case, including the sources, observation dates, and unanswered questions.

Sherlock can return the context packet. Sending it to another person, workspace, or external agent is a separate host action with its own destination permission. Never equate a retrieved packet with delivery.

## Use Sherlock through Slack

Each installer must connect their own Slack workspace/account and app or connector credentials using [Slack setup](slack.md). The current route uses your selected host's Slack handling. A standalone Slack bot is not included in this preview.

Bind the verified workspace and app/bot identity, allowed channels and senders, and intended Sherlock profile before routing requests to its skills. The host controls Slack access and reply routing; Sherlock's profile selects the local case store. Do not point mutually untrusted Slack users at a single trusted profile and assume channel visibility will enforce case access.

Use a fictional test case and an authorized test channel to verify recall and delivery separately. Read the authorized reply back in the intended workspace/channel/thread before claiming Slack delivery works. The existing website's Slack conversations are authored demonstrations, not successful installation tests for your workspace.

## Export and protect your records

Using the variables from the [install guide](install.md), export to a private file. Stop the Sherlock MCP process for this profile before running backup:

```sh
uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" --profile personal export > "$HOME/sherlock-export.json"
uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" --profile personal backup "$HOME/sherlock-backup"
```

Choose an unused export path to preserve previous exports. Backup requires a new destination directory outside the active profile. These files contain your case data; store them privately. Restore requires an empty destination profile with the same profile name as the backup and does not restore old CRM proposals. See the concrete recovery command in [troubleshooting](troubleshooting.md).
