# Contributing to Agent Sherlock

Start with the [README](README.md) and the [runtime](public-facing/runtime/README.md).
Sherlock is an agent skill pack and local MCP service. Research comes from the
host agent's tools; case storage and controlled CRM operations belong to the
runtime. Keep those responsibilities clear in changes and documentation.

## Run the checks

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run
these commands from the repository root:

```sh
uv sync --locked --project public-facing/runtime
uv run --locked --project public-facing/runtime pytest public-facing/runtime/tests
python3 -m unittest discover -s tests -v
python3 scripts/package_release.py
python3 scripts/release_check.py dist/agent-sherlock
```

Use fictional fixtures and isolated temporary data directories. The automated
suite must work without a model subscription, CRM account, Slack workspace, or
provider credential. A passing fixture test does not establish live provider
compatibility; document authorized live validation separately.

## Propose a change

For a bug, include the command, platform, version, expected result, actual
result, and a small fictional reproduction. For an integration, describe the
account identity check, permissions, supported operations, and confirmation
that reads and writes reach the intended records. Never include credentials,
customer records, raw exports, or private URLs in an issue or pull request.

Keep pull requests focused. Explain the user-visible result, relevant tests,
and remaining limits. Add tests when behavior changes, especially for storage,
isolation, evidence correction, approvals, and retry behavior. Update the user
instructions alongside changed commands or tool contracts.

## Skills and interface work

[Public skills](public-facing/skills/) are the canonical operating instructions.
Keep them portable, specific to Sherlock, and consistent with actual MCP tools.
Treat retrieved pages and CRM fields as evidence, not instructions granting
permission to call tools. Research findings need source and observation time;
unavailable evidence must not become a claim of zero activity.

For visual work, follow [AGENTS.md](AGENTS.md) and the bundled design system.
Use the approved identity and tokens. Do not add fake customer examples,
integration badges, results, or unsupported product claims.

See [SECURITY.md](SECURITY.md) for vulnerability reporting and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community expectations.
