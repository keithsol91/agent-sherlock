# Changelog

## 0.2.1a2 — 6 September 2026

- Simplified the homepage by presenting relationship recovery as numbered capability 05 alongside Sherlock's four existing capabilities, with deeper workflow details linked from the card.

## 0.2.1a1 — 6 September 2026

- Added a guided, local-first installer for Claude Code, Codex, and manual agent hosts. It copies only reviewed product files, preserves conflicting host settings, verifies fictional local persistence before registration, and does not connect providers or enable writes.
- Added a reviewed SHA-256 manifest for every shipped binary asset, expanded credential-pattern detection, and changed release scans to report every match without revealing values.
- Added the relationship-recovery workflow to the public homepage with the verified dormancy and employer-move rules and explicit operator-review boundary.

## 0.2.0a1 — 6 September 2026

- Added dormant pitch relationships and pitched-contact employer moves as two portable skills.
- Added deterministic, paginated, profile-local imports and owner reviews with source coverage,
  revisions, retained original pitch history, local exclusions, and feedback.
- Added schema-1-to-2 migration and fictional runtime/protocol coverage.
- Bundled the new skills' guides and fictional examples so copied skill folders are self-contained.
- Redacted bare Bearer credentials from provider results and rejected them in proposed change inputs.
- Prevented the release builder from overwriting existing directories, manifests, ZIPs, or symlink targets; failures clean up only outputs created by that run.
- Clarified that a chosen host and model provider may process relationship data returned through MCP.
- Host collection, provider validation, optional scheduling, and external delivery remain separate.

Back up with the previous runtime and stop its profile service before upgrading.
Schema 2 requires a pre-upgrade backup and the matching older runtime for rollback.
See [relationship storage and upgrades](public-facing/documentation/relationships.md#storage-and-upgrades).


## 0.1.0a1 — 6 September 2026

First installable public preview, published with owner approval under MIT for
original code and skills; see [release verification](docs/RELEASE.md).

- Added a local stdio MCP service with profile-scoped case storage, evidence,
  sourced findings, correction history, research coverage, and structured recall.
- Added a router skill plus competitor research, account context, case files,
  and recall skills for a user's existing agent.
- Added configurable CRM adapters, exact-change proposal review, scoped
  automatic-save policy, destination readback, and uncertain-write recovery.
  Fixture coverage and live provider verification are reported separately.
- Added fictional no-provider examples, diagnostics, export, backup, restore,
  and deliberate case deletion.
- Added installation, permissions, compatibility, and daily-use guides; a
  GitHub-oriented README; contribution and security guidance; issue forms;
  locked runtime checks and a scanned public distribution builder.

The static website keeps the approved Sherlock visual direction and labels
fictional Slack conversations. This candidate does not supply a hosted service,
standalone Slack bot, or automatic connection to a user's accounts.
