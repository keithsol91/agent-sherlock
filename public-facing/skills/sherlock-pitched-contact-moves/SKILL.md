---
name: sherlock-pitched-contact-moves
description: Find a person actually pitched at one company who is now verified at another, retaining the original relationship and preparing an owner review without a two-year waiting rule.
---

# Pitched contact moves

Use this skill when reviewing whether people previously pitched have moved to another company. The relationship and verified employer change are sufficient reasons to surface a review; no news story, creative idea, or two-year delay is required.

Discover the relationship tools and read the bundled [portable contract and workflow](references/relationships.md) before the first import or recurring setup. The user's host supplies authorized history and employment sources. Sherlock does not install or independently operate Sales Navigator.

Review all authorized imported relationships through `relationship_list` pagination, including older losses and relationships added later. Inspect local opt-outs before enrichment. Verify that the same person was actually pitched at the original company. Resolve current-employer identity using a dated source and stable company ID. Names, a company association, a search snippet, or an ambiguous multi-employer profile are insufficient.

Keep the original pitch-company record when employment changes. Update observations with the current relationship revision and a reason; do not rewrite the person as if the original pitch happened at the new employer. Bind active-client, open-deal, and exclusion checks to the new destination company. Disclose incomplete history and missing sources instead of assuming a clear path to reconnect.

Use `relationship_evaluate` and inspect `pitched_contact_moved` reviews in `relationship_queue`. Show the original pitch, former employer, verified new employer and role, owner, source dates, recent-contact checks, and coverage. Multiple old deals should produce one review for the same person and destination company. A review is not a delivered outreach message or a newly created CRM opportunity.

Record owner feedback through `relationship_feedback` using its current review revision. Corrected identity or employer evidence requires a revisioned import and explicit reopening of a correction hold. Local learning never becomes shared public customer history. An optional host schedule requires its own explicit setup and must use the chosen profile and supported locking workflow.

When reopening a review, preserve unrelated exclusions and correction holds. Supply `clear_holds` only for the specific person holds the owner intends to clear, and report the returned `feedback_scope`.
