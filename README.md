<p align="center">
  <img src="public-facing/assets/sherlock-hero-candidate.png" alt="Sherlock examining a clue beside his blue case folder" width="240" />
</p>

# Agent Sherlock

**An AI detective for the agent you already use.** Investigate competitors,
prepare account briefs, keep living case files, and recall the evidence your
next conversation needs.

Sherlock is seven portable skills plus a local MCP service. Your agent does the
research and reasoning. Sherlock keeps the sources, findings, history, relationship reviews, and
controlled CRM changes organized in your own profile.

[Get started](#try-sherlock) · [Install in your agent](public-facing/documentation/install.md)
· [Daily recipes](public-facing/documentation/daily-recipes.md)
· [Compatibility](public-facing/documentation/compatibility.md)
· [Contribute](CONTRIBUTING.md)

> **Early preview · 0.2.0a1.** Start with the fictional demo, then connect your
> chosen agent. Named agent and CRM connections have individual verification
> states in the compatibility guide. A passing demo does not certify a live
> CRM connection, delivered Slack message, or every host.

## Try Sherlock

Download this repository with **Code → Download ZIP**, extract it, and open a
terminal in the extracted repository folder. Install
[uv](https://docs.astral.sh/uv/getting-started/installation/) first. The runtime
requires Python 3.11 or later; uv can provision a compatible Python when needed.

With Git installed, you can clone it instead:

```sh
git clone https://github.com/keithsol91/agent-sherlock.git
cd agent-sherlock
```

Then run:

```sh
uv run --locked --project public-facing/runtime sherlock demo
```

The demo uses fictional records in a separate demo profile. It exercises a local
case, evidence, research coverage, and recall without API keys. The
first run downloads the locked software dependencies; the demo does not connect
your CRM, use a model, or send messages.

For local configuration diagnostics:

```sh
uv run --locked --project public-facing/runtime sherlock doctor
```

The [installation guide](public-facing/documentation/install.md) covers host
setup, explicit data paths, skill installation, and the first persistent case.
Global flags such as `--data-dir` and `--profile` go before the subcommand.

## Let your agent handle setup

Open this checkout in your local agent and paste:

```text
Set up Agent Sherlock from this checkout. Read README.md and
public-facing/documentation/install.md, compatibility.md, and permissions.md.
Run the locked setup, doctor, and fictional demo. Install all seven public-facing
skill folders and register this checkout's local stdio MCP service with this
host, preserving unrelated configuration. Use an explicit private data directory
and profile. Verify tool discovery and a fictional case save/read/recall across
a restart. Report what passed and what still needs my input. Keep CRM writes
approval-required; leave provider connections and automatic saves for a separate
setup decision with me.
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
