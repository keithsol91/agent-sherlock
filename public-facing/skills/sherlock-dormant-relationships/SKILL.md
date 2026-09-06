---
name: sherlock-dormant-relationships
description: Review people actually pitched who remain at the same company after at least 24 months since the latest meaningful contact found in the declared sources.
---

# Dormant pitch relationships

Use this skill for a one-time or explicitly scheduled review of old pitch relationships. A new campaign, news event, or creative idea is not required. Include all imported historical relationships and keep adding new ones; do not limit history to recent losses or discard relationships older than three years.

Discover `relationship_list`, `relationship_get`, `relationship_import`, `relationship_evaluate`, `relationship_queue`, and `relationship_feedback`. Read the bundled [portable contract and workflow](references/relationships.md) before preparing the first import or setting up recurrence. The host supplies authorized CRM/history and employment observations; Sherlock does not supply a Sales Navigator connector.

Follow every `next_cursor` within the authorized cohort. Check local opt-outs before collecting more information. Match the actual pitched person and original company using stable IDs and pitch evidence, then refresh their current employer and the destination account's open-deal/client/exclusion state. A contact association alone does not prove a pitch. Log changes through revisioned imports with a reason; keep the original company history.

Evaluate and read the `dormant_relationship` reviews. The default threshold is 24 calendar months since the latest meaningful conversation found, with no upper age cutoff. CRM record edits, email opens, automatic sequences, and internal notes do not reset that clock. Evidence must support the actual date and source. Complete coverage means successful collection from the named sources; it does not prove access to all communication channels. Partial or unavailable history belongs in the verification queue.

Present the person, company, owner, original pitch evidence, latest meaningful contact found, elapsed time, verified current employer, and source coverage. Use scoped wording such as “latest conversation found in CRM logs,” never an absolute “we have not spoken” when other channels are unknown. Do not invent a re-engagement angle or automatically send a message.

Record the owner's decision with the review's current revision. Reconnect marks intent only. Snoozes, exclusions, opt-outs, corrections, and outcomes remain local to the selected profile. Recurrence uses an explicitly enabled host schedule and a separately authorized destination; installing this skill does not enable either.

When reopening a review, preserve unrelated exclusions and correction holds. Supply `clear_holds` only for the specific person holds the owner intends to clear, and report the returned `feedback_scope`.
