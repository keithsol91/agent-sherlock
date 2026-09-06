<p align="center">
  <img src="public-facing/assets/sherlock-hero-candidate.png" alt="Sherlock examining a clue beside his blue case folder" width="240" />
</p>

# Agent Sherlock

**An AI detective for the agent you already use.** Investigate competitors,
prepare account briefs, keep living case files, and recall the evidence your
next conversation needs.

Sherlock adds seven skills and a small local service to your agent. Your agent
does the research and reasoning. Sherlock saves the sources, findings, and
case history so you can pick up where you left off.

[Get started](#try-sherlock) · [Install in your agent](public-facing/documentation/install.md)
· [Daily recipes](public-facing/documentation/daily-recipes.md)
· [Compatibility](public-facing/documentation/compatibility.md)
· [Contribute](CONTRIBUTING.md)

> **Early preview · 0.2.1a2.** The guided setup below is included in this
> release. Host acceptance and provider checks remain separate and are recorded
> in the compatibility guide.

## Try Sherlock

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) once; it
can also install the Python version Sherlock needs. In this working copy,
open a terminal in the folder containing this README and run:

```sh
uv run --locked --project public-facing/runtime sherlock setup
```

Choose **Claude Code**, **Codex**, or **another agent**, then review the suggested
locations. Setup installs Sherlock and all seven skills, checks that a fictional
case can be saved and recalled after a restart, and prepares the connection to
your agent. The default locations keep the installed copy and your case files
outside the download folder. You do not need API keys for this step.

When setup finishes, restart your agent and follow the printed next step.
Claude Code and Codex may ask you to trust or enable the new connection.
For another agent, setup gives you the settings to add manually. Installing the
files and passing the local check are separate from your agent accepting them.

See the [installation guide](public-facing/documentation/install.md) for a demo,
custom options, and manual installation. Slack and CRM connections are optional
later steps.

## Let your agent handle setup

Open this checkout in your local agent and paste:

```text
Set up Agent Sherlock from this checkout. Read README.md and
public-facing/documentation/install.md. Use the guided setup for this local
agent with the default private storage and all seven skills. Preserve existing
settings and stop if a Sherlock entry or skill conflicts. Report the local
check result, installed locations, and any restart or trust step I must finish.
Keep this to installation: do not request credentials, connect Slack or a CRM,
enable automatic saves, send messages, or publish anything.
```

This is for an agent running locally with permission to install tools. A remote
chat window cannot execute local commands just because it can read this page.
Host-specific instructions and actual test coverage are in the
[compatibility guide](public-facing/documentation/compatibility.md).

## What Sherlock helps you do

| Workflow | What you ask | What you get |
| --- | --- | --- |
| **Competitor research** | “What changed in their social strategy?” | A research scope, source-backed findings, coverage gaps, and ideas to test. Your host supplies search and browsing. |
| **Account context** | “Prepare me for this account conversation.” | Existing-record context through your configured CRM, a sourced brief, and proposed changes with controlled execution. |
| **Living case files** | “Update this case with the new evidence.” | Persistent evidence and findings, correction history, and open questions within the selected profile. |
| **Recall** | “Which recorded clients have we worked with in automotive?” | Relevant saved context and structured counts that distinguish clients, cases, incomplete history, and fictional examples. |

Research separates organic activity, audience conversations, and visible paid
creative. Public engagement does not reveal private spend, targeting, revenue,
or return on ad spend. Findings retain their sources and observation dates.

## Review the relationships you have already built

The [relationship workflows](public-facing/documentation/relationships.md) add two
local reviews: actual pitched contacts still at the same employer after at least
24 months since the latest meaningful conversation found, and actual pitched
contacts verified at a different employer without a two-year waiting rule.
Import all authorized historical relationships and keep adding new ones. The
runtime preserves original pitch context, source coverage, corrections, and a
deduplicated owner queue. It does not collect from Sales Navigator, send outreach,
or enable a schedule; your host supplies configured sources and optional recurrence.

## Your tools. Your records. Your decisions.

- **Use your existing agent.** Sherlock supplies instructions and MCP tools;
  it does not require a separate model subscription for local storage or the demo.
- **Keep data local.** Choose a private data directory and profile. Export and
  backup your records using the documented commands. This is a local trusted
  operator model, not a hosted team access-control service.
- **Control CRM changes.** Start with exact-change approval. Review proposals in
  your own terminal; a chat “yes” alone is not runtime approval. Optional
  automatic saves need explicit action and field rules. Follow
  [permissions and CRM setup](public-facing/documentation/permissions.md).
- **Choose a connector deliberately.** Composio and custom CRM MCP connections
  require real tool mappings, account identity, permissions, and readback. The
  compatibility guide records what has actually been verified.
- **Connect your own Slack workspace.** Each installer supplies their own Slack
  connection, credentials, channel choices, and permissions. The current route
  uses a Slack-capable host that you configure and authorize; Sherlock's local
  recall supplies saved context for that workflow. This repository does not
  install a standalone Slack bot. Follow the [Slack setup guide](public-facing/documentation/slack.md).
  Website conversations are fictional demonstrations.

Sherlock is free. Model providers and connected services may charge separately.
See the [release record](docs/RELEASE.md) for test evidence and remaining launch
steps, and [third-party notices](THIRD_PARTY_NOTICES.md) for artwork and marks.

## Explore the repository

| Path | Purpose |
| --- | --- |
| [public-facing/skills](public-facing/skills/) | The router skill and six workflow skills |
| [public-facing/runtime](public-facing/runtime/) | Python MCP service, pinned dependency lock, and runtime tests |
| [public-facing/documentation](public-facing/documentation/) | Installation, daily use, permissions, compatibility, and troubleshooting |
| [public-facing](public-facing/) | Static product website and fictional examples |
| [design/agent-sherlock](design/agent-sherlock/) | Bundled design source and approved reference |
| [scripts](scripts/) | Allowlisted distribution builder and public-file checks |

For a bug, use the repository's issue form with a fictional reproduction.
For security concerns, follow [SECURITY.md](SECURITY.md). Contributions should
include working commands, truthful capability claims, and relevant tests:
[CONTRIBUTING.md](CONTRIBUTING.md).
