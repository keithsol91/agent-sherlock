# Operate a local Sherlock profile

Use the variables from [install.md](install.md). Each host registration and operating command must select the same absolute data directory, profile, and optional private config. `SHERLOCK_DATA_DIR`, `SHERLOCK_PROFILE`, and `SHERLOCK_CONFIG` are environment alternatives. CLI arguments take precedence. The service is a host-started stdio process; this build does not run a hosted web application or scheduler.

## Inspect and restart

```sh
uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --version
uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" --profile personal doctor
uv run --locked --project "$SHERLOCK_ROOT/runtime" sherlock --data-dir "$SHERLOCK_DATA" --profile personal changes
```

Doctor checks local initialization without provider calls. `changes` lists pending local proposals; it does not send updates. From the host, `sherlock_status` identifies the bound profile and configured connection names, while `crm_status` actively contacts one selected connection.

Restart through the host that launched Sherlock. Configuration is loaded on process startup. Only one service may hold a profile at a time; close its first host before starting another host against that same profile. A new process should retrieve the same saved case when its profile/data settings match.

## Data lifecycle

| Action | Interface | Effect |
| --- | --- | --- |
| Save a case/evidence/finding | MCP case and evidence tools | Persists in the selected local profile. |
| Correct a finding | `finding_correct` | Preserves the correction reason and prior history. |
| Export cases | Operator CLI `export` | Writes JSON to stdout; redirect to an unused private file. |
| Back up | Operator CLI `backup DESTINATION` | Writes private data snapshots and an integrity manifest to a new directory. Stop the service first. |
| Restore | Operator CLI `restore SOURCE --confirm PROFILE` | Requires an empty matching profile and verified backup files; does not replay old CRM proposals. |
| Delete one case | Operator CLI `delete-case CASE_ID --confirm CASE_ID` | Deletes local case data; check retrieval/recall afterward. Other copies remain separate. |
| Disconnect CRM | Operator private config and provider controls | Restart after local config changes; revoke credentials separately when needed. |

See [troubleshooting.md](troubleshooting.md#back-up-and-restore) for a recovery command using a new data root. Do not run doctor in the empty recovery profile before restoring, because that initializes a case database. Preserve the original data until the restored case/recall readback passes.

Backups can contain deleted historical data and previously recorded proposal payloads. Restore deliberately leaves CRM proposal history/approvals out of the active store. Neither backup nor restore changes external CRM state or includes an external provider's own rollback mechanism. Keep credentials and private connector configuration separately under your own secret-management process.

## Recover an uncertain change

Inspect `change_status` using the original proposal ID. If it is interrupted, partial, or uncertain, call `change_reconcile`; that path reads the provider without repeating the mutation. A `verified` state means the requested values matched the readback. Partial/unknown remains unresolved and must not be summarized as saved.

If the desired change still needs to be made after reconciliation, reread the current record and prepare a new proposal for the actual remaining difference. Review it through the ordinary operator flow. Do not reset a proposal's state in the database or reuse old approval for different values.

## Upgrade and rollback

Record the running version/commit and back up before replacing a working checkout. Stop the service, review the release's migration notes, sync its committed lockfile with `uv sync --locked`, run its demo, and check the intended profile before reconnecting users. Host/model versions and provider mappings are part of the compatibility record.

Database compatibility must be verified for each release; do not assume an older executable can read a newer schema. For rollback, use the preserved source version and a matching backup restored into a new empty data root, then verify the recovered case and recall. Any CRM mutations that happened meanwhile must be reconciled separately.

## Local trust and support

The profile binding prevents an MCP caller from requesting another profile through Sherlock's tool arguments. It is not an operating-system security boundary against a host with unrestricted shell/filesystem access. Do not share one profile across mutually untrusted users or expose stdio through an unauthenticated remote bridge.

Retain a minimal record of version, host, profile alias, operation, tool status, and reproducible fixture steps when investigating failures. Do not attach case databases, CRM payloads, credentials, authentication links, or private environment files to public issues. See [troubleshooting.md](troubleshooting.md#report-a-reproducible-problem).
