# Release verification

Release: **0.2.1a1**. The owner approved publishing this update on 6 September
2026. Original code and skills retain the approved MIT license; artwork, fonts,
and third-party marks retain the scope in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

Repository: [keithsol91/agent-sherlock](https://github.com/keithsol91/agent-sherlock).
Preview: [v0.2.1a1](https://github.com/keithsol91/agent-sherlock/releases/tag/v0.2.1a1).
The earlier [v0.2.0a1](https://github.com/keithsol91/agent-sherlock/releases/tag/v0.2.0a1)
and [v0.1.0a1](https://github.com/keithsol91/agent-sherlock/releases/tag/v0.1.0a1)
releases retain their original tags and artifacts.

## Current verification

| Check | Evidence |
| --- | --- |
| Runtime, MCP, installer, profile isolation, CRM fixtures, and relationship reviews | 256 tests and 9 subtests passed locally on macOS/Python 3.12.13 before publication preparation |
| Packaging controls | 35 tests passed, including credential scanning, reviewed binary hashes, existing-output and symlink protection, reservation races, failure cleanup, and reproducibility |
| Clean source distribution | 128 allowlisted files; exact-tree, local-link, ZIP, manifest, canonical-source, archive-path, and CRC comparisons passed |
| Seven portable skills | Frontmatter validated; copied skill folders retain their bundled guides and fictional examples with no missing local references |
| Guided local setup | A disposable managed installation preserved host settings, installed all seven skills, passed MCP save/recall after restart, survived moving the original download, and produced an identical safe rerun |
| Credential and asset handling | Synthetic tests cover current token forms, credential assignments and URLs, full and bare Bearer values, redaction/rejection, reviewed binary hashes, and reports that never reveal matched values |
| Homepage relationship section | Desktop and mobile layouts, keyboard link access, local assets, Slack example controls, and zero browser console errors were verified before release preparation |
| Live CRM, Slack delivery, and relationship source collection | Not verified by these fictional/local checks; each installer configures and verifies their own accounts |

The [Release checks workflow](https://github.com/keithsol91/agent-sherlock/actions/workflows/ci.yml)
records results for each exact commit: Windows, macOS, and Linux on Python 3.11
and 3.13, plus the public distribution job. Inspect that commit's result when
evaluating an archive; local results alone do not establish cross-platform success.
Published release notes identify the final checked commit and its verification.

This release adds `sherlock setup` for Claude Code, Codex, and manual agent
hosts. It installs a managed local copy, all seven skills, and a private profile;
passes an isolated fictional MCP persistence check before registering the host;
preserves unrelated settings; and stops on conflicting Sherlock files or
settings. It does not request provider credentials, connect accounts, enable
writes, or bypass a host's trust prompt.

The release scanner also pins every shipped binary asset to a reviewed SHA-256
digest, recognizes additional credential forms, reports every match without its
value, and keeps the existing exact-tree and Git-history checks. The homepage
now explains the two relationship-recovery paths using the verified runtime
rules and owner-review boundary. All examples and regression records are fictional.

## Upgrade and data compatibility

Release 0.2.1a1 uses the same schema 2 store as 0.2.0a1. Before upgrading an
existing managed or manual installation, stop the profile service, create a
backup, and review the new release paths. The guided installer preserves a
different existing Sherlock installation as a conflict; it does not silently
replace it.

Users upgrading directly from 0.1.0a1 must create a backup with that previous
runtime before starting this release against existing data. The cases database
migrates from schema 1 to schema 2 transactionally. An older runtime cannot read
schema 2; rollback needs the matching old runtime and a pre-upgrade backup. See
[operations](../public-facing/documentation/operations.md#upgrade-and-rollback)
and [relationship storage](../public-facing/documentation/relationships.md#storage-and-upgrades).

## Earlier host evidence

Claude Code 2.1.261 loaded the router and recall skills and saved/retrieved a
fictional case with evidence across a new host process using 0.1.0a1 snapshot
`6c5198a`. A fresh GitHub source download at `078e31b` also passed installation,
doctor/demo, 19-tool discovery, and 13 case/evidence/recall operations including
restart persistence. These are historical checks of the named earlier build;
they do not certify every host or the new relationship workflows inside a host.

The [compatibility record](../public-facing/documentation/compatibility.md)
separates documented setup, protocol tests, fixture workflows, named-host tests,
and live-provider tests. Temporary validation used fictional profiles and did
not change global agent settings or connect provider accounts.

## Build the exact distribution

```sh
python3 -m unittest discover -s tests -v
python3 scripts/package_release.py
python3 scripts/release_check.py dist/agent-sherlock
```

The builder keeps `public-facing/runtime`, `public-facing/skills`, and
`public-facing/documentation` in their repository layout. It copies only
allowlisted sources and emits a ZIP and per-file SHA-256 manifest. The output
directory, ZIP, and manifest must all be fresh; existing files or symlinks are
rejected. Use `--output` with a new path for another build. See
[FILE-AUDIT.md](FILE-AUDIT.md) for the inclusion boundary and scanner limits.

Before publication, run the locked runtime suite, review the exact tree and Git
history, verify the archive from a fresh environment, and require the repository
CI to pass. Public publication and live provider connections require owner
authorization. This GitHub release does not deploy the website, publish to a
package registry, install a standalone Slack bot, or establish live integrations.
