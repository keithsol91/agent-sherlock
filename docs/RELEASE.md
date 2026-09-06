# Release verification

Candidate: **0.1.0a1**. This document records verification, not public launch
approval. Update it from actual command results before promoting this build.

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
| Release packaging controls | Automated tests implemented; final candidate run pending |
| Runtime, MCP protocol, data lifecycle, mock CRM | Implementation and validation in progress |
| Fresh install from exact sanitized ZIP | Pending candidate completion |
| Named agent host installation | See the current compatibility record |
| Live CRM account reads/writes and Slack delivery | Not verified by the fictional demo |
| GitHub workflow checks | Prepared; no remote run recorded yet |
| Software license | Proposed MIT for original code and skills; public release requires owner confirmation |
| Public repository and public promotion | Pending owner approval |

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
