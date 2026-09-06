# Install Sherlock in your agent

Sherlock adds skills and local case storage to an agent you already use. The
agent supplies the model and research tools. Start with installation; Slack and
CRM connections can come later.

> Guided setup is included in public release 0.2.1a1. If you are using an
> earlier release without `sherlock setup`, use
> [manual installation](#manual-installation).

## Quick setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) once.
   It can also install Python 3.11 or later, which Sherlock needs.
2. Open a terminal in this checkout's top folder, where `README.md` and
   `public-facing/` are located.
3. Run this command:

```sh
uv run --locked --project public-facing/runtime sherlock setup
```

Choose **Claude Code**, **Codex**, or **another agent**. Review the suggested
locations and continue. The defaults install Sherlock for your user account,
include all seven skills, and keep case files in a private folder using the
`default` profile. A profile is a separate set of case files.

With the default locations, setup copies the runtime and skills into a managed
folder outside this checkout and installs the locked dependencies. It tests the actual local connection by
creating a fictional case, adding evidence and a finding, and recalling them
after restarting Sherlock. This check uses isolated test data. Once it passes,
setup adds Sherlock to the selected agent's settings and installs the skills.
It prints the installed locations and the next step. After a successful default setup,
the downloaded source folder is no longer needed to run that installed copy.

For **another agent**, setup prepares the local installation and gives you a
connection settings file and skill paths. Add these using your agent's own
instructions; that final connection remains a manual step.

Setup needs network access to download Python or dependencies when they are
missing. It does not ask for API keys, connect accounts, or send messages. By
default it creates an empty private operator configuration for the selected
profile; it does not import another agent's connections.

## Finish in your agent

Restart your agent after setup. Accept its trust or connection prompt if one
appears. In Claude Code, check `/mcp`; in Codex, inspect the available MCP tools.
Ask your agent to call `sherlock_status` and confirm that Sherlock's skills are
available. The [compatibility guide](compatibility.md) distinguishes local tests
from tests inside each named agent.

The installer can verify the local service and write connection settings. Your
agent still has to load and accept them. Slack delivery and CRM access each
need their own setup and verification later.

## Let your agent handle installation

Open this checkout in a local agent that can run commands and paste:

```text
Set up Agent Sherlock from this checkout. Read README.md and
public-facing/documentation/install.md. Use the guided setup for this local
agent with the default private storage and all seven skills. Preserve existing
settings and stop if a Sherlock entry or skill conflicts. Report the local
check result, installed locations, and any restart or trust step I must finish.
Keep this to installation: do not request credentials, connect Slack or a CRM,
enable automatic saves, send messages, or publish anything.
```

A remote chat window cannot install software on your computer simply by reading
this prompt. Use a local agent with permission to install tools.

## Preview or customize setup

Most people can use the defaults. To preview the planned locations and changes
without having setup write them:

```sh
uv run --locked --project public-facing/runtime sherlock setup --host codex --dry-run
```

The `uv run` launcher may still download or prepare its own dependencies before
Sherlock starts. `--dry-run` prevents setup's installation and host-setting
writes.

To install in a chosen agent without interactive questions:

```sh
uv run --locked --project public-facing/runtime sherlock setup --host claude-code --yes
```

Use `--host codex` for Codex or `--host manual` for another agent. `--yes` accepts
the planned setup; it does not bypass conflicts, local verification, or the
agent's own trust prompts. An identical rerun is safe. If an existing Sherlock
entry or skill differs, setup stops for you to resolve it. Unrelated settings
are preserved, and edited host configuration files receive private backups.

| Option | When to use it |
| --- | --- |
| `--scope user` | Default: make Sherlock available to your user account. |
| `--scope project --project "/absolute/path/to/project"` | Make the agent settings and skills apply to one project. |
| `--install-dir PATH` | Choose where the managed runtime and skills are installed. |
| `--host-config PATH` | Select a custom host configuration file. |
| `--skills-dir PATH` | Select a custom destination for the seven skills. |
| `--json` | Return setup results in a format scripts can read. |

Global options go **before** `setup` or another subcommand. For example:

```sh
uv run --locked --project public-facing/runtime sherlock --data-dir "/absolute/path/to/private/sherlock-data" --profile personal setup --host codex
```

`--config PATH` is also a global option for an explicitly selected operator
configuration. Keep the same data directory, profile, and configuration when
running later commands. The setup summary gives you the installed paths to use.
For scripts, combine `--json` with an explicit `--host` and either `--dry-run`
or `--yes`.

## Try a fictional demo

To try Sherlock's local case and recall features before installing it in an agent:

```sh
uv run --locked --project public-facing/runtime sherlock demo
```

The demo uses fictional records in a separate demo profile. It needs no API keys
and does not connect your CRM, use a model, or send messages. The first run may
download dependencies. A passing demo confirms that local demonstration only.

## Manual installation

Use this path when you want to manage the files yourself or are installing an
earlier release. Download the [source repository](https://github.com/keithsol91/agent-sherlock)
with **Code → Download ZIP**, then extract it. Install uv first.

The commands in this section use a macOS or Linux shell. The runtime and
fictional demo have Windows test coverage; native Windows host installation and
WSL need separate verification. These variable assignments are not PowerShell
syntax.

Choose a permanent location for the source folder: the manual host connection
will use it. Set `SHERLOCK_ROOT` to its `public-facing` folder and choose a
private data folder outside the source. Replace the example path below and
keep the quotes around paths with spaces.

```sh
SHERLOCK_ROOT="/absolute/path/to/agent-sherlock/public-facing"
SHERLOCK_DATA="$HOME/agent-sherlock-data"
uv sync --locked --project "$SHERLOCK_ROOT/runtime"
uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" --profile personal doctor
uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" demo
```

Choose one host below. Preserve unrelated host settings and existing skill
folders. If a Sherlock entry or skill already exists, compare it before making
changes. If the host cannot find uv, use the absolute executable path printed
by `command -v uv`.

### Claude Code

For your user account:

```sh
claude mcp add --transport stdio --scope user agent-sherlock -- uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" --profile personal serve
```

Copy all seven directories from `$SHERLOCK_ROOT/skills/` into `~/.claude/skills/`.
The user MCP settings live in `~/.claude.json`. For one project, run the command
from that project with `--scope project` and put the skills in `.claude/skills/`;
the MCP entry goes in `.mcp.json`. Restart Claude Code and check `/mcp`.
See the official [MCP](https://code.claude.com/docs/en/mcp) and
[skills](https://code.claude.com/docs/en/skills) guides.

### Codex

```sh
codex mcp add agent-sherlock -- uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" --profile personal serve
```

Copy all seven skill directories into `~/.agents/skills/`. The user MCP settings
live in `~/.codex/config.toml`, or `config.toml` under a custom `CODEX_HOME`.
For one trusted project, use `.codex/config.toml` and `.agents/skills/` in that
project. Start a fresh local Codex session and inspect its MCP tools.
See the official [MCP](https://developers.openai.com/codex/mcp) and
[skills](https://learn.chatgpt.com/docs/build-skills) guides.

### Hermes

Add this entry to the intended Hermes profile's `config.yaml`. Replace the two
example paths with absolute paths and preserve the rest of the configuration.

```yaml
mcp_servers:
  agent-sherlock:
    command: uv
    args:
      - run
      - --locked
      - --project
      - /absolute/path/to/agent-sherlock/public-facing/runtime
      - sherlock
      - --data-dir
      - /absolute/path/to/private/sherlock-data
      - --profile
      - personal
      - serve
```

Copy the seven skill directories into the intended profile's skills directory,
then start a new session or use the host's documented reload path. Use your own
profile settings. See the official [MCP reference](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference)
and [skills guide](https://hermes-agent.nousresearch.com/docs/guides/work-with-skills).

### OpenClaw

Use the outbound MCP registry. Replace the example paths before running:

```sh
openclaw mcp set agent-sherlock '{"command":"uv","args":["run","--locked","--project","/absolute/path/to/agent-sherlock/public-facing/runtime","sherlock","--data-dir","/absolute/path/to/private/sherlock-data","--profile","personal","serve"]}'
openclaw mcp probe agent-sherlock --json
```

Copy the seven skill directories into the intended agent workspace's `skills/`.
Start a fresh session with a tool profile that exposes the configured MCP tools.
`openclaw mcp serve` exposes OpenClaw itself; it does not register Sherlock.
Older versions using a separate mcporter registry need their own verified setup.
See the official [MCP](https://docs.openclaw.ai/cli/mcp) and
[skills](https://docs.openclaw.ai/tools/skills) guides.

### Verify a manual connection

Ask the host to discover Sherlock's tools and call `sherlock_status`. For a
persistence check, temporarily select a dedicated test profile in the host's
Sherlock settings. Create and read a fictional case with `case_create` and
`case_get`, add fictional evidence and a finding, and retrieve it with
`recall_search`. Restart the host and confirm that the same records are still
available, then switch back to your chosen profile. Use the tool schemas the
host discovers; it may add a prefix to tool names.

`serve` is a local stdio service: your agent starts it and talks to it directly.
It does not open a web page or run a public web server.

Next: [daily recipes](daily-recipes.md), [troubleshooting](troubleshooting.md),
[Slack setup](slack.md), [CRM integrations](integrations.md), and
[permissions](permissions.md).
