# Public file audit

Sherlock's public package is assembled from an explicit manifest in
[`scripts/release_check.py`](../scripts/release_check.py). Packaging checks the
actual staged files before producing an archive. New files outside the listed
categories are excluded until the manifest changes.

The release surface is the MCP runtime, seven Markdown skills, installation and
workflow documentation, and the supporting website and design sources. The
runtime installs from its local checkout. Provider connections and host-agent
compatibility have their own configuration and verification boundaries; the
presence of a logo or a skill does not establish a working integration.

## Included categories

| Category | Release treatment |
| --- | --- |
| Root README, license, notices, contribution, security, conduct, changelog, agent instructions, and ignore file | Public newcomer and contributor documents; each filename is explicitly listed. A complete package requires a license. |
| `.github/` and `.devcontainer/` | Text workflow, template, and development-environment configuration only; hidden files receive the same content checks as visible files. |
| `public-facing/runtime/` | Explicit package metadata, dependency lock, README, Python sources, and tests. Installed dependencies and runtime databases are excluded. |
| `public-facing/skills/` | Public skill instructions and supporting text/code fixtures. Current skills cover orientation, competitor research, account context, case files, recall, dormant relationships, and pitched-contact moves. |
| `public-facing/documentation/` | Public installation, daily-use, permission, and troubleshooting guides. |
| `public-facing/` website | Explicit top-level HTML/CSS/JavaScript files, assets, and fictional example renderers. Browser-app drafts are excluded. |
| `public-facing/assets/examples/` | Authored fictional Slack conversations and screenshots. These illustrate an answer format and do not prove a live Slack integration. |
| Font files | Original Fraunces and Inter files retain their respective SIL Open Font License notices in both consumed and design-source locations. |
| Sherlock and third-party imagery | Existing artwork and identification assets retain the scope and attribution described in [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md). Third-party marks are not covered by Sherlock's software license. |
| `design/agent-sherlock/` | Selected design instructions, tokens, CSS, font files/notices, component guidance, validator, and the approved reference image. The image is a design reference, not a product screenshot. |
| Root `scripts/` and `tests/` | Only the two public release scripts and Python/JSON test files; operational scripts are not an allowed category. |
| Root `docs/` | Only this audit, the release record, and [`PUBLIC_ASSET_MANIFEST.json`](PUBLIC_ASSET_MANIFEST.json). The manifest pins every shipped binary asset to a reviewed SHA-256 value. Working notes are not shipped. |

## Excluded categories

The manifest excludes the owner handoff, old product/planning and deployment
verification notes, source-design ZIP/PDF downloads, the archived visual concept,
browser automation logs/snapshots, local QA output, provider deployment metadata,
virtual environments, build caches, databases, log files, and credential files.
The packaged source contains no synchronization path to a private agent profile.

Do not upload an unfiltered ZIP of the development workspace. Use the generated
release directory or archive. A `.gitignore` alone is not the publication boundary.

## Repeatable verification

From the project root:

```sh
python3 -m unittest discover -s tests -p 'test_release.py' -v
python3 scripts/package_release.py
python3 scripts/release_check.py dist/agent-sherlock
```

Packaging produces `dist/agent-sherlock/`, a reproducible ZIP, and a separate
SHA-256 manifest. It neither creates a Git repository nor publishes anything.
Choose a fresh directory with `--output dist/another-release` for another build;
the script refuses to overwrite an existing destination.

The automated checks cover:

- Every file in the staged tree, including hidden files, against the publication manifest.
- Common token, private-key, credential-URL, machine-path, deployment-ID, JWT, and generic credential-assignment patterns; every matching value is withheld from reports.
- Every shipped binary asset against the reviewed SHA-256 manifest, plus basic scans for serialized private keys and common provider tokens in binary data.
- Symbolic links, environment files, database/log archives, and dependency/runtime directories.
- Local Markdown and HTML destinations and anchors, plus CSS asset paths, while ignoring fenced documentation examples and external URLs.
- Required release files and atomic staging: a failed scan leaves no partial release directory.
- Archive ordering, timestamps, permissions, and hashes for reproducible output.

The release tests exercise synthetic credential patterns, hidden deployment
state, symlink escapes, missing assets and anchors, unwanted draft files,
incomplete releases, existing-destination protection, and archive reproducibility.
Runtime functional tests are separate and must also pass; see the
[release instructions](RELEASE.md).

Once a local public-review Git repository exists, also inspect its history:

```sh
python3 scripts/release_check.py dist/agent-sherlock --git-history PATH_TO_PUBLIC_REVIEW_REPOSITORY
```

This reads committed blobs and file modes across local branches and tags
without checking out historical files, executing them, or following symlinks.
It catches sensitive text and excluded files that were deleted in a later
commit. Commit metadata receives the same sensitive-text checks.

## Limits

This is an offline heuristic scan, not a guarantee that arbitrary sensitive
content will be recognized. It does not verify remote links, inspect image
pixels semantically, or establish artwork ownership. Binary scanning detects
only the listed byte patterns; the SHA-256 manifest makes asset review explicit
but does not prove what an image depicts. History
checks require the explicit `--git-history` option and cover locally reachable
commits, not remote-only refs or unreachable objects. The release package is
assembled from reviewed source files without copying repository history.
Reusing a repository with existing history requires the history check and
review of any findings before publication.

The commands above describe reproducible checks. Current runtime, host, provider,
publication, and release-verification evidence belongs in the
[release record](RELEASE.md); this document does not imply those checks passed.
