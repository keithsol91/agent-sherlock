# Release verification

Release: **0.2.0a1**. The owner approved publishing this update on 6 September
2026. Original code and skills retain the approved MIT license; artwork, fonts,
and third-party marks retain the scope in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

Repository: [keithsol91/agent-sherlock](https://github.com/keithsol91/agent-sherlock).
Preview: [v0.2.0a1](https://github.com/keithsol91/agent-sherlock/releases/tag/v0.2.0a1).
The earlier [v0.1.0a1 release](https://github.com/keithsol91/agent-sherlock/releases/tag/v0.1.0a1)
retains its original tag and artifacts.

## Current verification

| Check | Evidence |
| --- | --- |
| Runtime, MCP, profile isolation, CRM fixtures, and relationship reviews | 167 tests passed locally on macOS/Python 3.12.13 before publication preparation |
| Packaging controls | 31 tests passed, including existing-output and symlink protection, reservation races, failure cleanup, and reproducibility |
| Clean source distribution | 121 allowlisted files; exact-tree, local-link, ZIP, manifest, and canonical-source comparisons passed |
| Seven portable skills | Frontmatter validated; copied skill folders retain their bundled guides and fictional examples with no missing local references |
| Fresh install and local workflows | Locked fresh-environment installation, doctor, fictional demo, relationship import/evaluation, and new-process persistence passed in the local readiness audit |
| Credential handling | Synthetic tests cover full and bare Bearer values, header casing/whitespace, nested result redaction, and rejection without persisting or sending credential-bearing proposals |
| Live CRM, Slack delivery, and relationship source collection | Not verified by these fictional/local checks; each installer configures and verifies their own accounts |

The [Release checks workflow](https://github.com/keithsol91/agent-sherlock/actions/workflows/ci.yml)
records results for each exact commit: Windows, macOS, and Linux on Python 3.11
and 3.13, plus the public distribution job. Inspect that commit's result when
evaluating an archive; local results alone do not establish cross-platform success.
Published release notes identify the final checked commit and its verification.

The three readiness fixes prevent configured credentials from surviving as bare
Bearer values, protect all three packaging output paths, and explain host/model
processing of relationship data. A separate portability fix bundles the two new
skills' guides inside their installable folders. All examples and regression
records are fictional.

## Upgrade from 0.1.0a1

Stop the profile service and create a backup with the previous runtime before
starting this release against existing data. The cases database migrates from
schema 1 to schema 2 transactionally. An older runtime cannot read schema 2;
rollback needs the matching old runtime and a pre-upgrade backup. See
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
