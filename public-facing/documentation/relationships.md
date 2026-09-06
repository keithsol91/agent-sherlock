# Review past pitch relationships

Two portable skills share one profile-local review system:

- **Dormant relationships:** the person actually pitched remains at the same company, and the latest meaningful conversation found in the named sources is at least 24 calendar months old. There is no upper age cutoff.
- **Pitched contact moves:** the actual pitched person is verified at a different company. This skill has no two-year waiting requirement.

Neither requires a creative idea, a news trigger, or the original loss reason to remain relevant. Keep all authorized past lost relationships and add new relationships as they are established. A person who has not actually been pitched can be stored, but does not qualify for either ready queue.

## What this build supplies

The local runtime validates imported observations, stores original pitch-company history and revisions, evaluates the rules, and maintains a deduplicated owner-review queue. It does not collect LinkedIn data, fetch a CRM's full communication history, connect a provider, schedule itself, send messages, or create opportunities. The website remains a static overview of a local product.

Use the host's authorized source tools or a customer-owned structured import. The current experimental HubSpot template covers company records only: contacts, deals, associations, communications, pagination, and current-employment collection require separately configured and verified host/provider workflows. Do not describe a passing fictional test as a verified Sales Navigator or HubSpot relationship integration.

## Portable input version 1

Use [fictional-relationships.json](examples/fictional-relationships.json) for the exact shape. Every sample person, company, source, and owner is fictional. The fixed observations will become stale; do not refresh dates without obtaining corresponding new evidence.

Each record has a stable `id`, `person.id`, and `original_company.id`. Namespace upstream IDs by provider/account during normalization. One person and original company have one relationship; multiple historical deals are pitch evidence for that relationship. A new employer changes `current_employment`, never the original-company identity. Evaluation uses the newest employment observation across the person's pitch relationships; conflicting equally dated employers need verification. If the destination already has an actual pitch relationship, that company uses its own dormant review instead of a duplicate employer-move alert. Historical snapshots and case evidence remain available after an update.

| Field | Meaning |
| --- | --- |
| `person`, `original_company`, `owner` | Stable identity and display context; match IDs rather than names. `original_company.verified=true` means the original employer was resolved against actual pitch evidence, not supplied by name alone. |
| `pitch_verified`, `pitch_evidence` | Actual pitch proof, with each item's `source` locator, `occurred_at` timezone-aware timestamp, and `kind`. A CRM association is insufficient. |
| `last_meaningful_contact_at`, `last_contact_source` | Latest substantive conversation found and its source locator. Exclude record edits, email opens, automatic sequences, and internal notes. |
| `history_coverage` | `status` (`complete`, `partial`, `unavailable`), `scope`, `checked_at`, and optional `exhaustive`. Complete means all requested pages from the declared sources were fetched, not all possible communication channels. |
| `current_employment` | `company_id`, company name/domain, role, `profile_url`, `observed_at`, `identity_verified`, `ambiguous`, and optional `positions`. Multiple conflicting employer IDs need resolution. |
| `source_status` | Destination `company_id`; explicitly known booleans `open_deal`, `active_client`, `do_not_contact`, `enrichment_opt_out`; `recent_outreach_at` when present; and `verified_at`. The company binding must match the current employer. Resolve verified domain aliases upstream to the same canonical ID. |
| `deal_status` | Historical deal status (`open`, `won`, `lost`, `unknown`). Current destination suppression is based on the fresh `source_status`, not a stale historical label. |

Source locators must have a scheme, such as `https://…`, `crm://…`, or `user-supplied://…`, without credentials. Dates require an explicit timezone. Missing, future-dated, or stale evidence cannot silently become verified facts. Each current record is limited to 16 KB and 100 pitch evidence items; retain earlier evidence through the existing revision history rather than sending unbounded exports. Imports are bounded to 100 records and are atomic. Continue with subsequent batches to cover the whole authorized history.

Before gathering additional data, inspect `relationship_get` or `relationship_list` for local exclusions and enrichment opt-outs. A new import does not reset them.

Sherlock stores owner feedback and raw relationship history in the selected local profile. It does not independently upload them or contribute them to shared public training. Retrieved data is returned to your chosen agent host, which may send it to its model provider. The host's and provider's processing and retention policies apply; local storage does not make their processing local. See [permissions](permissions.md).

## Import, evaluate, and review

Use the source path and private data directory from the [install guide](install.md). Global flags precede the command:

```sh
uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" --profile personal relationship-import "/absolute/path/to/private/relationships.json"
uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" --profile personal relationship-evaluate --limit 100
uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" --profile personal relationship-queue --state ready
```

The file envelope is `{"schema_version": 1, "relationships": [...]}`. A new record may appear directly in the array. An updated record uses `{"record": {...}, "expected_revision": 2, "reason": "Verified employment changed"}`. Read its real revision first. Identical retries are no-ops; changes require the current revision and a reason. A failed entry rolls back its entire import batch.

MCP tools mirror the workflow: `relationship_import`, `relationship_list`, `relationship_get`, `relationship_evaluate`, `relationship_queue`, and `relationship_feedback`. Imports and evaluations write local state. None contacts a provider. `relationship_get(include_history=true)` returns prior observations. `case_get` includes the current relationship; ordinary case evidence remains searchable. Relationship cases use the `lead` type and never count as client experience.

List, evaluation, and queue responses contain `next_cursor`. Pass it as `after_id` (CLI `--after-id`) until null for the intended cohort. A filtered queue page can be empty while `next_cursor` is non-null. Do not mistake one bounded page for a complete review of the CRM. The host should retain the checkpoint and resume on the next run when its authorized batch or time budget is reached.

Ready reviews require employment, account-status, and scoped-history observations no more than seven days old by default. Existing clients, open deals, opt-outs, exclusions, and recent outreach or meaningful contact within 30 days suppress reviews. Unknown suppression flags and incomplete source coverage need verification. A newer outreach/email signal inside the dormant interval holds a dormant review until its relationship to meaningful-contact history is resolved; an old call alone cannot establish dormancy when newer email is present. Dormant reviews use a calendar-month threshold; moved reviews retain the recent-contact suppression without acquiring a two-year wait.

The runtime does not independently verify source accuracy. A review reports the latest conversation **found in its declared sources**, not a claim that no unlogged call, private message, or external email occurred. Reading the queue checks freshness again so an old ready card is not presented as current.

## Owner decisions and improvement

Use `relationship_feedback` with `review_id`, the displayed `expected_revision`, and an action:

| Action | Local effect |
| --- | --- |
| `reconnect` | Mark handled; records the owner's intent only. Sending requires a separately authorized host action. |
| `already_in_touch` | Mark this target review handled and apply a 30-day person-wide contact cooldown. A different employer is eligible again after that cooldown and fresh verification; it does not inherit a two-year wait. |
| `snooze` | Supply a future `until` timestamp; eligible reviews return after reevaluation when due. |
| `wrong_identity`, `wrong_employer`, `never_pitched` | Add a reason and hold the person's reviews for verification. Correct source evidence with a revisioned import, then explicitly reopen. |
| `exclude`, `enrichment_opt_out` | Suppress this person's reviews across their imported pitch relationships; check before host enrichment. |
| `reopen` | Add a reason to reconsider this target review. Person exclusions and correction holds remain unless explicitly listed in `clear_holds` (`excluded`, `enrichment_opt_out`, or `verification_required`). The response returns the exact cleared/remaining scope. Imported source opt-outs still apply until that source is corrected. |
| `outcome` | Add a factual outcome note without claiming an unattempted suggestion failed. |

Use `relationship-feedback REVIEW_ID ACTION --expected-revision REVISION --note "Owner explanation"` for the equivalent local CLI; use `--clear-hold verification_required` with reopen only when that specific correction hold should be cleared. Feedback does not change CRM owners, source records, or communication history. Actual fact corrections belong in revisioned imports. Improvements to public methods should be reviewed code/skill updates with fictional regression cases; private feedback is not shared automatically.

## Optional recurring host review

Nothing recurs until the owner enables a supported host schedule. Agree on the selected profile, authorized source accounts/cohort, cadence, batch/time cap, owner-review destination, and delivery permission. An optional weekly recipe is: import new/changed relationships, refresh due evidence for eligible non-opted-out people, evaluate pages, and deliver only a small owner-selected number of ready cards plus a coverage summary. Keep the source checkpoint so older and newly added relationships are eventually processed.

When the host already owns the profile's MCP server, use its existing relationship tools. Standalone relationship CLI commands acquire the same profile service lock and will refuse to run while that server holds it. Do not schedule a second server or work around the lock. Hosts without a suitable scheduler can run the same workflow manually. Scheduling availability and actual destination delivery need host-specific verification.

## Storage and upgrades

This development change upgrades the cases database from schema 1 to 2 in a transaction, preserving existing case revisions and evidence. New relationship tables use the same profile and case deletion boundary. Export and backups include relationships, review state, prior snapshots, and feedback events. Deleting the associated case deletes its local relationship data; separate backups, host conversations, and original CRM records retain their own copies.

Back up before upgrading and stop the profile service first. An older schema-1 runtime cannot read schema 2; rollback requires a pre-upgrade backup with the matching older runtime. See [operations](operations.md) and [permissions](permissions.md). Profiles remain trusted local namespaces, not authentication for a hosted team service.
