# Troubleshooting and recovery

Start with the same source path, data directory, profile, and optional config as your MCP host. Run `sherlock --help` and the affected subcommand's help through the source launcher in [install.md](install.md). Global options go before the subcommand.

```sh
uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" --profile personal doctor
```

A doctor result describes local setup. It is not a test of every provider credential, live workflow, or host configuration.

| Symptom | Check and remedy |
| --- | --- |
| `uv` or `sherlock` is not found | Install uv; use the documented `uv run --locked --project ... sherlock` launcher. In desktop hosts use the absolute uv executable path if PATH differs from your shell. There is no assumed global Sherlock install. |
| A path with spaces fails | Quote the entire path in shell commands; in JSON/YAML put it in one argument string. Do not split the project path into multiple args. |
| Startup dependency or Python error | Verify Python 3.11+ and run the checkout's frozen dependency sync. Review the actual install error rather than adding unknown provider keys. |
| `serve` waits without a web page | This is expected for stdio. The MCP host starts the process and sends protocol requests. There is no HTTP/browser UI in that command. |
| Host reports no Sherlock tools | Verify the launcher, profile/config selection, host stderr, then restart/reload that host. Inspect tool discovery; do not confuse a skill appearing with an MCP connection working. |
| Skill missing | Copy all five complete skill directories into the chosen host's supported skills location; check for a same-name collision and start a fresh session. |
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

Stop the profile's Sherlock MCP process before `backup DESTINATION`; choose a new private directory outside the active profile. To restore, inspect the backup manifest and use an empty destination with the same profile name. The example below uses a new data root so existing data is preserved. Do not run doctor in that recovery profile first: it would initialize a database and make the destination nonempty.

```sh
SHERLOCK_RECOVERY_DATA="/absolute/path/to/new/private/sherlock-recovery"
uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_RECOVERY_DATA" --profile personal restore "/absolute/path/to/private/sherlock-backup" --confirm personal
```

Point the host at the recovery data directory, restart it, and verify the recovered cases and recall. Restoring an old backup can reintroduce evidence deleted after that backup; review the recovered state before reconnecting users. Restore deliberately skips old CRM proposals, so previously approved changes cannot be replayed from a backup. Backups do not revoke credentials or roll back external CRM mutations.

## Upgrade or remove Sherlock

Before changing a working checkout, record its version and back up the data profile. Stop its MCP process, review the new version's migration/release notes, sync the new locked dependencies, run doctor and the fictional demo, and restart the host. Verify a representative existing case. Do not assume a previous binary can safely read a newer database schema; use the documented restore path with the matching version for a rollback.

To remove Sherlock, remove only its named MCP registration and its five installed skill folders from the selected host, then restart it. Decide separately whether to keep or delete local data, exports, and backups. Revoke optional external provider credentials through their own account controls when appropriate.

## Report a reproducible problem

Include the Sherlock version/commit, host/version, OS/Python/uv versions, operation, expected result, actual status/error, and minimal reproduction using fictional records when possible. Redact credentials, authorization links, account IDs, customer payloads, private paths, and full database/log files. Share exact tool names and structural response shapes only after removing private values. Use the repository's verified support/security destination when one is published.
