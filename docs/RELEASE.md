# Release verification

Release: **0.1.0a1**. The owner approved MIT licensing and public GitHub
publication on 6 September 2026. This document records verification and the
scope of that release.

## Distribution contract

The public source package retains this repository's layout, including
`public-facing/runtime`, `public-facing/skills`, and
`public-facing/documentation`. Build it with:

```sh
python3 scripts/package_release.py
python3 scripts/release_check.py dist/agent-sherlock
```

The builder copies only reviewed source categories, checks the copied tree, and
produces a ZIP and per-file SHA-256 manifest. Existing outputs are not replaced;
use `--output` with a new path when preparing another candidate. Review
[FILE-AUDIT.md](FILE-AUDIT.md) for inclusion and exclusion details.

## Verification status

| Check | Status |
| --- | --- |
| Five skill files: required frontmatter and naming | Passed locally |
| Skill scenario review: provenance, injected source instructions, missing tools, fictional counts, uncertain CRM writes | Reviewed; host execution tracked separately |
| Release packaging controls | 19 local tests passed; checked source package and first-commit Git history passed |
| Runtime, MCP protocol, data lifecycle, mock CRM | 95 tests and 9 subtests passed on the reviewed local candidate; includes 20 fictional personas across independent MCP processes |
| Fresh source install | Passed with Python 3.11.15, a fresh environment, and an empty dependency cache; 11 CLI operations plus MCP persistence verified |
| Actual GitHub ZIP install | Commit `078e31b`: all 109 files matched the reviewed package; fresh locked install, doctor, fictional demo, 19 MCP tools, and 13 operations including restart persistence passed |
| Named agent host | Claude Code 2.1.261 loaded the router and recall skills, saved a fictional case with sourced evidence, and retrieved it after a new host process; initial snapshot `6c5198a` |
| Live CRM account reads/writes and Slack delivery | Not verified by the fictional demo |
| GitHub workflow checks | [Run 34011393286](https://github.com/keithsol91/agent-sherlock/actions/runs/34011393286) passed for `39d8541`: Windows, macOS, and Linux on Python 3.11 and 3.13, plus the public distribution job |
| Software license | MIT for original code and skills, confirmed by the owner on 6 September 2026; artwork and third-party notices retain their stated scope |
| GitHub publication | Owner-authorized public repository and preview release; inspect the repository and release links for current availability |

Repository: [keithsol91/agent-sherlock](https://github.com/keithsol91/agent-sherlock).
Preview release: [v0.1.0a1](https://github.com/keithsol91/agent-sherlock/releases/tag/v0.1.0a1).
The actual GitHub README, quickstart anchor, and rendered installation guide
were inspected in an authenticated browser. The local website points to this
repository; those website edits have not been deployed.

The downloaded GitHub ZIP for full commit
`078e31bf627463ee181feaf756de5395d3565fa6` was 4,888,080 bytes with SHA-256
`6ee93cadaad337e879fc8bafd92ea163bb589463b5a2bc36bae3c0a157e9f835`.
Its source remained byte-identical after the acceptance run. Later changes to
this release record do not change the runtime tested in that archive. For the
latest commit, inspect [Release checks](https://github.com/keithsol91/agent-sherlock/actions/workflows/ci.yml).

The Claude Code check used only a temporary MCP configuration, project skill
folders, and fictional records. It did not alter global agent settings or test
CRM, web research, Slack delivery, or other agent hosts. Its first harness
disabled all setting sources and therefore hid project skills; enabling only
the isolated project source verified normal skill discovery in the second process.

The [compatibility record](../public-facing/documentation/compatibility.md)
distinguishes documented configuration, protocol tests, fixture workflows,
named-host tests, and live-provider tests. Do not collapse those states into a
universal “works with” claim.

## Maintainer release sequence

1. Run the locked runtime suite and the public packaging suite.
2. Build and inspect the exact clean distribution, including hidden files and
   all links. Install it in a fresh directory and use isolated fictional data.
3. Run doctor, demo, and a protocol-level case/evidence/recall lifecycle from the
   distribution. Confirm restart, export, correction, and deletion behavior.
4. Review the software license, third-party notices, and actual compatibility
   evidence. Update this record and README to match the results.
5. Inspect the exact Git tree and history, then run the repository CI. Public
   repository creation, visibility changes, deployment, and promotion require
   explicit owner approval.

Publishing a source repository does not itself deploy the website, publish a
package-registry release, connect provider accounts, or verify a human beta.
