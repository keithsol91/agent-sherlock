# Agent Sherlock: website, skills, and runtime

Sherlock helps your agent investigate competitors, maintain sourced case files,
work with account context, and recall earlier findings. This directory contains
the public website and the local service that supports those workflows.

Your agent supplies the model, reasoning, and research tools. Sherlock's MCP
service runs locally and stores evidence in a configured profile. Provider
connections and external writes are configured separately. The static website
is documentation and examples; it does not launch the service or connect a CRM.

## Get started

Use the [installation guide](documentation/install.md) for the complete first-run
path, including a setup prompt for your agent. Python 3.11 or newer and `uv`
are required. Read the guide's source-path instructions carefully; the repository
root is one directory above this file.

Start with fictional fixtures and local checks. Then connect an agent host that
supports a local MCP process, install the relevant skills, and verify that it
can save and recall fictional evidence. Model providers and connected services
may charge separately.

Continue with [daily workflows](documentation/daily-recipes.md) and the
[compatibility record](documentation/compatibility.md). The
[runtime README](runtime/README.md) describes the local Python package.

## Workflow skills

| Skill | Purpose |
| --- | --- |
| [Agent Sherlock](skills/agent-sherlock/SKILL.md) | Select the workflow and establish evidence and permission rules. |
| [Competitor research](skills/sherlock-competitor-research/SKILL.md) | Build a sourced competitor brief using the host's available research tools. |
| [Account context](skills/sherlock-account-context/SKILL.md) | Resolve the CRM record and manage proposed changes through the controlled workflow. |
| [Case files](skills/sherlock-case-files/SKILL.md) | Preserve evidence, corrections, and the history of an investigation. |
| [Recall](skills/sherlock-recall/SKILL.md) | Retrieve prior findings with sources, dates, and coverage limitations. |

Load skills using your agent host's supported installation method. Skills are
instructions; installing them alone does not install the MCP service or connect
a provider. Consult the runtime guide for current tool and command contracts.

## Website development

From the repository root, serve the static website locally:

```sh
python3 -m http.server 8080 --bind 127.0.0.1 --directory public-facing
```

Open [the local website](http://127.0.0.1:8080/) or
[the setup overview](http://127.0.0.1:8080/docs.html#getting-started).
This is a static preview, not a running Sherlock MCP service.

The site uses local fonts and assets. The Slack gallery contains fictional
companies, counts, and conversations; it is an example of the intended answer
format, not evidence of a public Slack installation.

| Path | Contents |
| --- | --- |
| `index.html`, `docs.html` | Homepage and setup overview. |
| `styles.css` | Site composition using shared design tokens. |
| `assets/styles/`, `assets/fonts/` | Bundled design styles, fonts, and their licenses. |
| `assets/examples/`, `examples/` | Fictional Slack examples and their presentation. |
| `skills/` | Portable Markdown skill files. |
| `documentation/` | Installation, workflows, compatibility, and operating guides. |
| `runtime/` | Python MCP package, locked dependencies, and tests. |

## Design and verification

Before changing an interface, read the
[agent instructions](../design/agent-sherlock/AGENT-INSTRUCTIONS.md),
[design system](../design/agent-sherlock/DESIGN-SYSTEM.md),
[tokens](../design/agent-sherlock/tokens/tokens.json), and
[component guidance](../design/agent-sherlock/docs/components.md). Visually
inspect the approved reference. Reuse the cream, ink, gold, and pale-blue
palette, Fraunces and Inter, and the approved cartoon identity.

The current hero illustration is a candidate asset. Numbered capability items
are text treatments pending the dedicated illustrations from the design
reference. The earlier Case Desk concept is archived outside this directory
and is not the active visual direction.

Before a public release, verify all setup commands and links, responsive
layouts, keyboard controls, and the exact host/provider claims. Keep local
tests, configured connections, verified live operations, and publication as
separate results. Never add credentials, private customer records, or runtime
data to this public source tree.
