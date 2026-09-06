# Agent Sherlock

This directory is the standalone public product project for Agent Sherlock. It is separate from the live Hermes sales-intelligence profile.

## Work safely

- Start visual and interface work by reading `design/agent-sherlock/AGENT-INSTRUCTIONS.md` and `design/agent-sherlock/DESIGN-SYSTEM.md`, then visually inspecting `design/agent-sherlock/reference/approved-homepage.png`.
- Use the supplied tokens, fonts, components, and approved cartoon identity. The archived dark Case Desk concept is historical reference only.
- Keep all public examples fictional or explicitly labeled. Verify product behavior before describing a capability, integration, write, repository, license, or deployment as real.
- Never copy in Hermes configuration, credentials, customer data, Slack/CRM exports, runtime state, private reports, operational scripts, or deployment controls.
- Do not create a public repository, publish a site, connect a provider, or enable a live integration without explicit approval.

## Product and release checks

- `public-facing/runtime/` is the local Python MCP service. It is started by an agent host over stdio, not as a public web server.
- `public-facing/skills/` contains the canonical seven operating skills. `public-facing/documentation/` contains user setup and daily workflows.
- Preserve profile isolation, evidence provenance, revision checks, operator approval, and destination readback when changing persistence or CRM behavior.
- Run runtime checks with `uv run --locked --project public-facing/runtime pytest public-facing/runtime/tests` and packaging checks with `python3 -m unittest discover -s tests -v`.
- Public distributions are built by `scripts/package_release.py`; review the exact resulting tree using `scripts/release_check.py`. Do not publish the workspace wholesale or include local `.vercel`, environments, data, backups, or QA artifacts.

## Project layout

- `public-facing/` is the active website/application build surface.
- `design/agent-sherlock/` is the bundled design-system source of truth.
- `brand/source/` preserves the original user-supplied downloads.
- `archive/previous-case-desk-concept/` preserves the earlier prototype without making it part of the active visual direction.
