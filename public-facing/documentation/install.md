# Install Agent Sherlock from this checkout

Sherlock is a Python MCP service plus five portable instruction skills. Your existing agent supplies the model, research tools, and optional connected services. This preview is installed from the [GitHub source repository](https://github.com/keithsol91/agent-sherlock). Read the [compatibility status](compatibility.md) before choosing a host.

Each installer connects their own Slack workspace/account using their own app installation and credentials. Installing Sherlock does not connect Slack automatically or supply the author's workspace, app, credentials, or history. The current path uses the installer's selected host to handle Slack; see [Slack setup](slack.md).

## First run without provider keys

You need Python 3.11 or later and [uv](https://docs.astral.sh/uv/getting-started/installation/). The commands below use a POSIX shell on macOS or Linux. Runtime tests and the fictional demo pass on Windows with Python 3.11 and 3.13; interactive Windows agent setup and WSL remain unverified. The shell examples below are not native PowerShell commands.

Set the source directory to the folder containing `runtime/`, `skills/`, and `documentation/`. Replace the example path with your downloaded checkout's absolute path. Keep the quotes when it contains spaces. Choose a private data directory outside the checkout.

```sh
SHERLOCK_ROOT="/absolute/path/to/Agent Sherlock/public-facing"
SHERLOCK_DATA="$HOME/agent-sherlock-data"
uv sync --locked --project "$SHERLOCK_ROOT/runtime"
uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" --profile personal doctor
uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" demo
```

Dependency installation can use the network. The demo itself uses fictional records in a separate demo profile and does not require CRM, model, or research-provider keys. It creates a private demo config and a fictional CRM store, and prints their actual location plus the fixture record/connection IDs. The summary includes `fictional: true`, `network_calls: 0`, and two fictional medical clients. Add `--full` after `demo` for the expanded case/evidence output. This proves the local demonstration path only. A passing doctor does not prove a live provider connection or host installation.

Global options such as `--data-dir`, `--profile`, and `--config` go **before** `doctor`, `demo`, `serve`, and the other subcommands. Keep the same data directory and profile in your host configuration and later operating commands.

## Give this to your agent

After replacing the source path, paste this into the local host you want to use:

```text
Set up Agent Sherlock from /absolute/path/to/Agent Sherlock/public-facing.
Read documentation/install.md, documentation/compatibility.md,
documentation/permissions.md, and documentation/slack.md. Inspect the package's help and configuration
example. Use a private data directory outside the source checkout. Run doctor
and the fictional no-provider demo, then register the local stdio MCP server
with this host and install all five folders from skills/ in its supported
skills directory. Preserve unrelated host settings and existing skill files;
show me conflicts before replacing them. Use the same selected profile for
the host and CLI. Verify tool discovery and case save/read/recall in a test
profile, then report which checks actually passed. Keep approval-required CRM
writes as the default. Next resolve my selected Slack workspace/account, my
app installation and credentials, allowed channels and senders, and the
Sherlock profile they may access. Resolve my selected CRM account as well.
Configure those provider connections only within my authorization; use any
scope I have already authorized and ask only for missing information or scope.
Do not assume the author or this host has already connected my accounts.
Keep credentials private. Verify the authorized Slack destination and read
back any authorized test reply there. Report local recall, Slack delivery,
and CRM verification separately. Do not enable autosave or publish anything.
```

This handoff asks your agent to perform installation. The guide itself has not changed your host settings. Review any host-level prompts your environment requires.

## Connect one local host

These are configuration recipes derived from the hosts' official documentation. Sherlock's host smoke results are tracked separately in [compatibility.md](compatibility.md). Use one host path, not all four. If `uv` is absent from the host's PATH, replace `uv` with the absolute path printed by `command -v uv`.

### Claude Code

From the working project where you want Sherlock available, with the variables above still set:

```sh
claude mcp add --transport stdio --scope local agent-sherlock -- uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" --profile personal serve
```

Open a new Claude Code session and check `/mcp`. The `local` scope ties this registration to the current project. Copy the five skill directories into that project's `.claude/skills/`, preserving any existing folders with the same name. [Claude Code MCP](https://code.claude.com/docs/en/mcp) and [skills](https://code.claude.com/docs/en/skills).

### Codex

```sh
codex mcp add agent-sherlock -- uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" --profile personal serve
```

Start a fresh local Codex session and inspect its MCP tools. Copy the five skill directories into the working project's `.agents/skills/`. A project-scoped MCP configuration is also possible in trusted `.codex/config.toml`; preserve existing entries. [Codex MCP](https://developers.openai.com/codex/mcp) and [skills](https://learn.chatgpt.com/docs/build-skills).

### Hermes

Merge this entry into the intended Hermes profile's `config.yaml`. Replace both example paths with absolute paths; do not replace the entire configuration.

```yaml
mcp_servers:
  agent-sherlock:
    command: uv
    args:
      - run
      - --locked
      - --project
      - /absolute/path/to/Agent Sherlock/public-facing/runtime
      - sherlock
      - --data-dir
      - /absolute/path/to/private/sherlock-data
      - --profile
      - personal
      - serve
```

Copy the five skill directories into the intended profile's skills directory, then use a new session or the host's documented reload path. Do not import an unrelated existing agent profile to install Sherlock. [Hermes MCP reference](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference) and [skills](https://hermes-agent.nousresearch.com/docs/guides/work-with-skills).

### OpenClaw

Current OpenClaw documentation describes an outbound MCP registry. This is separate from `openclaw mcp serve`, which exposes OpenClaw itself to another client. Replace the example paths before running:

```sh
openclaw mcp set agent-sherlock '{"command":"uv","args":["run","--locked","--project","/absolute/path/to/Agent Sherlock/public-facing/runtime","sherlock","--data-dir","/absolute/path/to/private/sherlock-data","--profile","personal","serve"]}'
openclaw mcp probe agent-sherlock --json
```

Copy the five skill directories into the intended agent workspace's `skills/`. Start a fresh session using a runtime/tool profile that exposes configured MCP tools. Older versions using a separate mcporter registry need their own verified setup; do not mix registry formats. [OpenClaw MCP](https://docs.openclaw.ai/cli/mcp) and [skills](https://docs.openclaw.ai/tools/skills).

## Verify from your chosen host

Ask the host to discover Sherlock's tools and call `sherlock_status`. In a dedicated test profile, create a fictional case with `case_create`, read it with `case_get`, add sourced fictional evidence and a finding, and retrieve it with `recall_search`. Confirm the same case is available after restarting that host. A host may prefix tool names; use the discovered schema rather than guessing the prefix.

Do not run `serve` as a background web server: it is a stdio process started by the MCP host and waits for protocol messages on stdin. It does not supply a browser sign-in page or public HTTP endpoint.

## Connect your own Slack workspace

Follow [slack.md](slack.md) to configure your own workspace and app credentials through your selected host. Resolve the workspace ID, app/bot identity, allowed channel IDs and senders, and the Sherlock profile before enabling access. An existing host's ability to support Slack does not prove your account is connected or authorized.

Verify local recall and an authorized test reply separately, including readback in the intended Slack destination. A standalone Slack bot is not included in this preview; this build uses the selected host's Slack handling.

Next: [daily recipes](daily-recipes.md), [Slack setup](slack.md), [CRM integrations](integrations.md), [permissions](permissions.md), [operations](operations.md), and [troubleshooting](troubleshooting.md).
