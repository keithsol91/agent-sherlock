# Fix a setup problem

Start with the result printed by `sherlock setup`. It identifies the installed
locations, the local check result, and the steps left to finish in your agent.

| What happened | What to do |
| --- | --- |
| `uv: command not found` | Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then open a new terminal and try again. uv can install the Python version Sherlock needs. |
| `setup` is not a recognized command | Guided setup starts in release 0.2.1a1. If you have an earlier release, download the current release or use [manual installation](install.md#manual-installation). |
| The runtime folder cannot be found | Open the terminal in the checkout's top folder, which contains `README.md` and `public-facing/`, and run the command from there. |
| A dependency download or Python installation fails | Check the actual uv error and your network connection, then rerun setup. Adding account credentials will not fix this stage. |
| Setup reports an existing Sherlock entry or skill conflict | Compare the existing item with the planned installation. Setup preserves it. Keep it, or back it up and deliberately resolve the conflict before rerunning; `--yes` does not replace conflicting files. |
| The local save or recall check fails | Keep the setup result and follow the reported error. Setup must pass this check before changing your host settings. Rerun it after resolving the error. |
| Setup passed, but Sherlock is missing from my agent | Restart the agent and finish its trust or connection prompt. Check `/mcp` in Claude Code or the MCP tools in Codex. Confirm that you opened the project selected during project-scoped setup. |
| I selected another agent | Setup prepared the local files. Add the generated connection settings and skill paths using that agent's own instructions, then verify it there. |
| I downloaded the source again | An identical setup can be rerun safely. A changed runtime, Sherlock entry, or skill may need a deliberate upgrade; resolve any reported conflict before proceeding. |
| Slack or my CRM is not connected | Installation does not connect accounts. Continue with [Slack setup](slack.md) or [CRM integrations](integrations.md) when you are ready. |

## Check the installed service

Use the runtime path, data directory, profile, and Sherlock configuration path
printed by setup. Replace the example paths and profile below with those values:

```sh
uv run --locked --project "/absolute/path/to/installed/runtime" sherlock --data-dir "/absolute/path/to/private/sherlock-data" --profile default --config "/absolute/path/to/private/sherlock-data/default/config.json" doctor
```

Global options such as `--data-dir`, `--profile`, and `--config` go before
`doctor` or another subcommand. Include `--config` so the command checks the
same configuration as your agent. Use `sherlock --help` through the same launcher
to see available commands. For a manual installation, use the permanent source
path from [install.md](install.md#manual-installation).

A doctor result describes local configuration. It does not prove that your
agent accepted the connection or that a provider account works.

## Problems during use

| Symptom | Check and remedy |
| --- | --- |
| `sherlock` is not found | Use the documented `uv run --locked --project ... sherlock` launcher. Setup does not promise a global `sherlock` command. In manually configured desktop hosts, use the absolute uv executable path if PATH differs from your shell. |
| A path with spaces fails | Quote the entire path in shell commands; in JSON/YAML put it in one argument string. Do not split the project path into multiple args. |
| Startup dependency or Python error | Check the installed runtime path and actual uv error. Use the matching locked dependencies for that installation. |
| `serve` waits without a web page | This is expected for stdio. The MCP host starts the process and sends protocol requests. There is no HTTP/browser UI in that command. |
| Host reports no Sherlock tools | Verify the launcher, profile/config selection, host stderr, then restart/reload that host. Inspect tool discovery; do not confuse a skill appearing with an MCP connection working. |
| Skill missing | Check the skill destination in the setup summary and start a fresh agent session. For manual installation, copy all seven complete skill directories into the chosen host's skills location, preserving existing files. |
| Cases disappear between sessions | Compare the actual data directory and profile. The demo uses a separate profile. A new working directory should not require a new store when absolute startup settings are used. |
| Profile service is already running | This build allows one Sherlock server process per profile. Stop that process before another host starts the same profile or before backup/restore. This is not a shared multi-host daemon. |
| Configuration profile mismatch | Select the matching profile or correct the operator-owned config. MCP tool input cannot switch the process profile. |
| Research is empty | A prepared research plan is not evidence collection. Use host research tools or supplied sources, record observations, and inspect source states. Restricted or failed sources are not zero activity. |
| CRM is unavailable | Inspect `crm_status`, credential environment availability, selected account, required scopes, and mappings. Reconnect using that provider's own supported flow. Never paste tokens into a support issue. |
| Custom gateway tools are incompatible | Compare discovered schemas and response paths with the configured mapping. Report unsupported operations clearly; do not guess tool slugs or field names. |
| Proposal remains unapproved | The operator must use the local interactive `review` command for that exact proposal and profile. Chat approval alone does not write the approval store. |
| Write timed out or readback failed | Inspect `change_status`, run read-only `change_reconcile`, and preserve the proposal ID. Do not repeatedly issue the mutation to make the error disappear. |
| CRM record changed since proposal | Read it again and prepare a fresh proposal with the current state rather than silently overwriting someone else's edit. |
| Case revision conflict | Read the case's current revision, reconcile the intended edit, then submit the updated revision. |
| Count differs from expected | Verify case type, category, duplicate identity, result coverage, and missing history. Research accounts do not become recorded clients automatically. |
| Slack response lacks context | Test local recall first, then the host's authorized channel routing and profile binding. A public Slack example image is not workspace installation evidence. |

## Back up and restore

Stop the profile's Sherlock MCP process before `backup DESTINATION`; choose a
new private directory outside the active profile. To restore, inspect the backup
manifest and use an empty destination with the same profile name. Keep the
existing Sherlock configuration path printed by setup. The example below uses
the `default` profile and a new data root so existing data is preserved. Use your
backup's profile name for `--profile` and `--confirm`, and replace all example
paths. Do not run doctor in that recovery profile first: it would initialize a
database and make the destination nonempty.

```sh
SHERLOCK_RECOVERY_DATA="/absolute/path/to/new/private/sherlock-recovery"
uv run --locked --project "/absolute/path/to/installed/runtime" sherlock --data-dir "$SHERLOCK_RECOVERY_DATA" --profile default --config "/absolute/path/to/private/sherlock-data/default/config.json" restore "/absolute/path/to/private/sherlock-backup" --confirm default
```

Point the host at the recovery data directory, restart it, and verify the recovered cases and recall. Restoring an old backup can reintroduce evidence deleted after that backup; review the recovered state before reconnecting users. Restore deliberately skips old CRM proposals, so previously approved changes cannot be replayed from a backup. Backups do not revoke credentials or roll back external CRM mutations.

## Upgrade or remove Sherlock

Before an upgrade, record the installed version and locations, then back up the
data profile. Stop its MCP process and review the new version's release notes.
The guided installer preserves conflicting existing files; it is not an
automatic replacement for every upgrade. Use a new permanent install directory
or the release's migration instructions, review the changed host entry and
skills, and keep the existing data directory and profile. Run doctor and the
fictional demo, restart the host, and verify a representative existing case.
Do not assume a previous binary can read a newer database schema; use the
documented restore path with the matching version for a rollback.

To remove Sherlock from one agent, remove its named MCP registration and its
separate installed skill copies, then restart that agent. The printed runtime
path is inside a managed bundle that other agents may share. If an agent uses
skills directly from that bundle, leave those files in place too.

Delete the containing bundle only after confirming that no other agent uses its
runtime or skills. Keep your private case data, configuration, exports, and
backups; removing an agent connection does not require deleting them. Revoke
optional external provider credentials through their own account controls when
appropriate.

## Report a reproducible problem

Include the Sherlock version/commit, host/version, OS/Python/uv versions, operation, expected result, actual status/error, and minimal reproduction using fictional records when possible. Redact credentials, authorization links, account IDs, customer payloads, private paths, and full database/log files. Share exact tool names and structural response shapes only after removing private values. Use the repository's verified support/security destination when one is published.
