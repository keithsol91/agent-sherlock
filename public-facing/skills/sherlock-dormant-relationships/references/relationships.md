# Portable relationship contract

This reference is bundled with the skill so it remains available when only the skill folder is installed. It describes the public profile-local relationship runtime, not a live CRM or employment-provider integration.

## Required host capability

Use the host's registered Sherlock relationship tools: `relationship_list`, `relationship_get`, `relationship_import`, `relationship_evaluate`, `relationship_queue`, and `relationship_feedback`. If they are unavailable, report that the runtime must be configured before importing or evaluating records. Copying this skill does not install the runtime, configure a provider, schedule a task, or authorize delivery.

The host supplies authorized CRM/history and employment observations. Check local exclusions and enrichment opt-outs before gathering more information. This runtime validates and stores supplied evidence; it does not independently establish source accuracy.

## Version 1 input

The [fictional import example](fictional-relationship.json) contains one complete record for this skill. Every identity and source is fictional. Its fixed dates are an illustration; never change observation dates to make stale real evidence appear fresh.

A CLI import file uses `{"schema_version": 1, "relationships": [...]}`. The MCP `relationship_import` tool instead receives that array as its `records` argument. New records may appear directly in the array. Changes use `{"record": {...}, "expected_revision": 2, "reason": "Verified new employment observation"}`; obtain the actual revision with `relationship_get` first. Imports are atomic batches of at most 100 records; an invalid entry rolls back its batch. Identical retries are no-ops.

| Field | Required meaning |
| --- | --- |
| `id`, `person.id`, `original_company.id` | Stable relationship and entity identities, namespaced by upstream provider/account. Names are display context, not identity. |
| `person`, `original_company`, `owner` | Identity and display context. `original_company.verified=true` means that company was resolved against actual pitch evidence. |
| `pitch_verified`, `pitch_evidence` | Actual pitched-person proof. Each evidence item has a credential-free `source` locator, timezone-aware `occurred_at`, and `kind`. A contact/company association alone is insufficient. |
| `last_meaningful_contact_at`, `last_contact_source` | Latest substantive conversation found and its source. Record edits, email opens, automatic sequences, and internal notes do not establish this date. |
| `history_coverage` | `status` (`complete`, `partial`, or `unavailable`), `scope`, `checked_at`, and optional `exhaustive`. Complete means successful pagination of the named sources; it does not imply every communication channel was accessible. |
| `current_employment` | Canonical `company_id`, company name/domain, title, `profile_url`, `observed_at`, `identity_verified`, `ambiguous`, and optional `positions`. Resolve competing employers instead of choosing one without evidence. |
| `source_status` | Current destination `company_id`; explicitly known boolean `open_deal`, `active_client`, `do_not_contact`, and `enrichment_opt_out`; `recent_outreach_at` when present; and `verified_at`. Bind these checks to the current employer. |
| `deal_status` | Historical `open`, `won`, `lost`, or `unknown`. Fresh destination checks govern suppression; a historical label is not a current account check. |

Source locators need a scheme such as `https://`, `crm://`, or `user-supplied://`. Dates require an explicit timezone. Missing, future, or stale observations remain unverified. Each current record is limited to 16 KB and 100 pitch evidence items; retain earlier observations in revision history.

One person and original company have one relationship, with multiple deals retained as evidence. Employment changes update `current_employment`, never the original pitch-company identity. Evaluation uses the newest employment observation across that person's relationships; equally dated conflicting employers need review. If the destination has its own actual pitch relationship, use that company's dormant review instead of duplicating a move alert.

## Collection and review

1. Read `relationship_list` or `relationship_get` before host enrichment; imports preserve local holds.
2. Collect the authorized source pages and update records with their current revisions and reasons.
3. Run `relationship_evaluate`, then inspect `relationship_queue` for the skill's reviews.
4. Follow every `next_cursor` as `after_id` until null for the intended cohort. A filtered page may be empty while another cursor remains. Preserve a checkpoint when the host's batch/time budget is reached.

The default dormant threshold is 24 calendar months since the latest meaningful conversation found, with no upper age cutoff. A verified move has no two-year wait. Employment, destination status, and declared-history checks must be no more than seven days old by default. Existing clients, open deals, opt-outs, exclusions, and meaningful contact or outreach within 30 days suppress a review. Unknown flags or incomplete coverage need verification.

For dormancy, a newer outreach/email signal inside the dormant interval requires clarification; an older call alone cannot establish years of silence. Reading the queue rechecks freshness. Describe “latest conversation found in the declared sources,” preserving the possibility of unlogged conversations. Show person, original company/pitch, current employer/role, owner, dates, and coverage. A ready review is not delivered outreach or a created opportunity.

## Owner feedback

Use `relationship_feedback` with `review_id`, its displayed `expected_revision`, and the action. Read `feedback_scope` in the result.

| Action | Local effect |
| --- | --- |
| `reconnect` | Marks handled and records intent. Sending is a separate authorized host action. |
| `already_in_touch` | Handles this target and applies a 30-day person-wide contact cooldown. A different employer does not inherit a two-year wait. |
| `snooze` | Requires a future `until`; eligible reviews return after reevaluation when due. |
| `wrong_identity`, `wrong_employer`, `never_pitched` | Require a reason and hold the person's reviews. Correct facts with a revisioned import before explicit reopening. |
| `exclude`, `enrichment_opt_out` | Suppress the person's reviews across pitch relationships; check these before enrichment. |
| `reopen` | Requires a reason and reconsiders this target. Preserve other holds unless the owner explicitly names `excluded`, `enrichment_opt_out`, or `verification_required` in `clear_holds`. Source opt-outs still apply. |
| `outcome` | Adds a factual outcome note; it does not claim unattempted outreach failed. |

Feedback does not modify CRM records, owners, or communication history. Sherlock stores raw history and feedback in the selected local profile and does not independently upload them or contribute them to shared public training. Retrieved data is returned to the chosen agent host, which may send it to its model provider. The host's and provider's processing and retention policies apply; local storage does not make their processing local.

Public method improvements use reviewed code/skill changes and fictional regressions, not automatic sharing of customer feedback.

## Optional recurrence

Agree on the selected profile, source accounts/cohort, cadence, batch/time cap, owner-review destination, and delivery permission before enabling a supported host schedule. A weekly run can import changes, refresh due eligible observations, evaluate all pages, and deliver a small owner-selected number of ready cards with coverage.

Use the existing MCP service when the host owns it. Standalone CLI relationship commands acquire the same profile lock and refuse to run while that service holds it; do not start a competing service or bypass the lock. Hosts without a scheduler can run the workflow manually. Installing this skill enables neither recurrence nor a destination.
