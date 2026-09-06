# Agent Sherlock local service

Sherlock saves case files, evidence, and findings for your agent to use later.
Your agent supplies the model and research tools. This is a local MCP service,
started by the agent over stdio; it does not run a public web server.

From the repository's top folder, with [uv](https://docs.astral.sh/uv/getting-started/installation/)
installed:

```sh
uv run --locked --project public-facing/runtime sherlock setup
```

Choose Claude Code, Codex, or another local agent. Setup installs a managed copy
and all seven skills, verifies local saving and recall with fictional data, and
prints the next step. Restart your agent to finish loading the installation.
Other agents need the generated connection settings added manually.

The package version is 0.2.1a1. Guided setup is included in this release. The
package is not published to a Python package registry. See the
[installation guide](../documentation/install.md) for the managed setup path,
manual path, and custom options.

Slack and CRM connections are optional later steps. Installation does not
connect accounts or request credentials. Local checks, host acceptance, and
provider verification have separate results; see [compatibility](../documentation/compatibility.md).
