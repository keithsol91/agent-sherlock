"""Exercise release boundaries using only synthetic, temporary file trees."""

from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from package_release import build_release, write_zip
from release_check import check_git_history, check_tree, is_allowed


class ReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"
        self.root.mkdir()

    def write(self, name: str, content: str = "example\n") -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def rules(self, *, links: bool = True) -> set[str]:
        return {finding.rule for finding in check_tree(self.root, require_complete=False, links=links)}

    def test_allowlist_uses_canonical_runtime_and_skills(self) -> None:
        for name in ["public-facing/runtime/pyproject.toml", "public-facing/runtime/uv.lock",
                     "public-facing/runtime/src/agent_sherlock/cli.py",
                     "public-facing/skills/agent-sherlock/SKILL.md",
                     "public-facing/documentation/quickstart.md", ".github/workflows/ci.yml"]:
            self.assertTrue(is_allowed(Path(name)), name)
        for name in ["FOR_Keith.md", "docs/GITHUB-PUBLICATION-BRIEF.md", "sherlock.py",
                     "public-facing/app/index.html", "public-facing/.vercel/project.json",
                     "brand/source/source.zip", "scripts/private_operations.py"]:
            self.assertFalse(is_allowed(Path(name)), name)

    def test_package_excludes_local_evidence_and_environment(self) -> None:
        self.write("README.md", "# Sherlock\n")
        self.write("public-facing/runtime/src/agent_sherlock/__init__.py", "")
        self.write("public-facing/skills/agent-sherlock/SKILL.md", "# Skill\n")
        for name in ["FOR_Keith.md", "public-facing/.vercel/project.json", ".env",
                     ".playwright-cli/page.yml", "output/playwright/screen.png",
                     "public-facing/runtime/.venv/private.py", "public-facing/runtime/src/__pycache__/x.pyc",
                     "docs/PRODUCT-POSITIONING.md", "public-facing/app/index.html"]:
            self.write(name)
        destination = Path(self.temp.name) / "release"
        hashes = build_release(self.root, destination, require_complete=False)
        self.assertEqual(set(hashes), {
            "README.md", "public-facing/runtime/src/agent_sherlock/__init__.py",
            "public-facing/skills/agent-sherlock/SKILL.md",
        })
        self.assertEqual(check_tree(destination, require_complete=False), [])

    def test_exact_tree_check_includes_hidden_and_disallowed_files(self) -> None:
        self.write("public-facing/.vercel/project.json", "{}")
        self.write("public-facing/runtime/.env.production", "value=example")
        self.write("public-facing/runtime/cases.sqlite3", "synthetic")
        self.assertIn("excluded-file", self.rules())
        self.assertIn("allowlist", self.rules())
        self.assertEqual(len(check_tree(self.root, require_complete=False)), 6)

    def test_private_token_is_rejected_without_echoing_it(self) -> None:
        token = "gh" + "p_" + "a" * 36
        self.write("README.md", "# Example\n" + token + "\n")
        findings = check_tree(self.root, require_complete=False)
        self.assertTrue(any(f.rule == "provider-token" for f in findings))
        self.assertFalse(any(token in str(f) for f in findings))
        self.assertIn("line 2", str(findings[0]))

    def test_common_credentials_and_machine_paths_are_rejected(self) -> None:
        values = {
            "private-key": "-----BEGIN " + "PRIVATE KEY-----",
            "aws-key": "AK" + "IA" + "A" * 16,
            "machine-path": "/Use" + "rs/example/private.txt",
            "deployment-id": "dp" + "l_" + "a" * 24,
            "credential-url": "https://example:" + "synthetic" + "@example.invalid/",
            "credential-assignment": 'api_key = "' + "a" * 28 + '"',
        }
        for rule, value in values.items():
            with self.subTest(rule=rule):
                self.write("README.md", value)
                self.assertIn(rule, self.rules())

    def test_documented_names_and_placeholder_config_do_not_trigger_secrets(self) -> None:
        self.write("README.md", '# Setup\nUse API_KEY from your environment.\napi_key = "YOUR_API_KEY"\n')
        self.assertEqual(self.rules(), set())

    def test_symlink_escape_is_never_copied(self) -> None:
        outside = Path(self.temp.name) / "outside.md"
        outside.write_text("not public", encoding="utf-8")
        (self.root / "README.md").symlink_to(outside)
        self.assertIn("symlink", self.rules())
        destination = Path(self.temp.name) / "release"
        with self.assertRaisesRegex(ValueError, "symbolic link"):
            build_release(self.root, destination, require_complete=False)
        self.assertFalse(destination.exists())

    def test_symlinked_allowed_directory_is_rejected(self) -> None:
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (self.root / "tests").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symbolic link"):
            build_release(self.root, Path(self.temp.name) / "release", require_complete=False)

    def test_missing_local_links_and_anchors_fail(self) -> None:
        self.write("README.md", "[missing](absent.md)\n[anchor](public-facing/index.html#absent)\n")
        self.write("public-facing/index.html", '<main id="main"></main>')
        self.assertEqual(self.rules(), {"local-link", "local-anchor"})

    def test_real_links_css_assets_and_markdown_anchors_pass(self) -> None:
        self.write("README.md", '# Sherlock\n[docs](public-facing/documentation/setup.md#start-here)\n[external](https://example.invalid/path)\n')
        self.write("public-facing/documentation/setup.md", "# Start here\n[home](../../README.md)\n")
        self.write("public-facing/index.html", '<a href="/docs.html#setup">Setup</a><link rel="stylesheet" href="styles.css">')
        self.write("public-facing/docs.html", '<main id="setup"></main>')
        self.write("public-facing/styles.css", 'body { background-image: url("assets/example.svg"); }')
        self.write("public-facing/assets/example.svg", '<svg xmlns="http://www.w3.org/2000/svg"></svg>')
        self.assertEqual(self.rules(), set())

    def test_documentation_code_blocks_are_not_link_targets(self) -> None:
        self.write("README.md", '# Example\n```markdown\n[illustration](missing.md)\n```\n')
        self.assertEqual(self.rules(), set())

    def test_link_path_cannot_escape_staged_tree(self) -> None:
        self.write("README.md", "[outside](../outside.md)")
        self.assertIn("local-link", self.rules())

    def test_missing_license_blocks_complete_release(self) -> None:
        self.write("README.md", "# Sherlock\n")
        findings = check_tree(self.root)
        self.assertTrue(any(f.path == "LICENSE" and f.rule == "required" for f in findings))

    def test_failed_scan_does_not_leave_partial_output(self) -> None:
        self.write("README.md", "[missing](missing.md)")
        destination = Path(self.temp.name) / "release"
        with self.assertRaisesRegex(ValueError, "Release checks failed"):
            build_release(self.root, destination, require_complete=False)
        self.assertFalse(destination.exists())

    def test_existing_destination_and_source_are_not_overwritten(self) -> None:
        self.write("README.md", "# Sherlock")
        destination = Path(self.temp.name) / "release"
        destination.mkdir()
        preserved = destination / "work.md"
        preserved.write_text("preserve", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "already exists"):
            build_release(self.root, destination, require_complete=False)
        self.assertEqual(preserved.read_text(), "preserve")
        with self.assertRaisesRegex(ValueError, "source tree"):
            build_release(self.root, self.root, require_complete=False)

    def test_hash_manifest_and_zip_are_reproducible(self) -> None:
        self.write("README.md", "# Sherlock\n")
        self.write(".gitignore", "dist/\n")
        first = Path(self.temp.name) / "release-one"
        second = Path(self.temp.name) / "release-two"
        one = build_release(self.root, first, require_complete=False)
        two = build_release(self.root, second, require_complete=False)
        self.assertEqual(one, two)
        self.assertEqual(one["README.md"], hashlib.sha256(b"# Sherlock\n").hexdigest())
        zip_one = Path(self.temp.name) / "one.zip"
        zip_two = Path(self.temp.name) / "two.zip"
        write_zip(first, zip_one)
        write_zip(second, zip_two)
        self.assertEqual(zip_one.read_bytes(), zip_two.read_bytes())
        with zipfile.ZipFile(zip_one) as archive:
            self.assertEqual(archive.namelist(), ["agent-sherlock/.gitignore", "agent-sherlock/README.md"])

    def git(self, *arguments: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.root), "-c", "core.hooksPath=/dev/null",
             "-c", "commit.gpgsign=false", "-c", "user.name=Release Test",
             "-c", "user.email=release-test@example.invalid", *arguments],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    @unittest.skipUnless(shutil.which("git"), "Git is optional for local release checks")
    def test_history_finds_deleted_secret_and_ignores_current_clean_content(self) -> None:
        self.git("init")
        token = "gh" + "p_" + "a" * 36
        self.write("README.md", token)
        self.git("add", "README.md")
        self.git("commit", "-m", "Synthetic test fixture")
        self.write("README.md", "# Clean current content\n")
        self.git("add", "README.md")
        self.git("commit", "-m", "Remove synthetic test fixture")
        findings = check_git_history(self.root)
        self.assertTrue(any(f.rule == "provider-token" for f in findings))
        self.assertFalse(any(token in str(f) for f in findings))

    @unittest.skipUnless(shutil.which("git"), "Git is optional for local release checks")
    def test_history_rejects_symlink_and_deleted_deployment_state(self) -> None:
        self.git("init")
        self.write("README.md", "# Sherlock\n")
        self.write("public-facing/.vercel/project.json", "{}")
        (self.root / "CONTRIBUTING.md").symlink_to("README.md")
        self.git("add", "README.md", "CONTRIBUTING.md", "public-facing/.vercel/project.json")
        self.git("commit", "-m", "Synthetic file-boundary fixture")
        self.git("rm", "CONTRIBUTING.md", "public-facing/.vercel/project.json")
        self.git("commit", "-m", "Remove file-boundary fixture")
        findings = check_git_history(self.root)
        self.assertEqual(sum(f.rule == "history-file" for f in findings), 2)

    @unittest.skipUnless(shutil.which("git"), "Git is optional for local release checks")
    def test_clean_history_passes(self) -> None:
        self.git("init")
        self.write("README.md", "# Sherlock\n")
        self.git("add", "README.md")
        self.git("commit", "-m", "Public source")
        self.assertEqual(check_git_history(self.root), [])


if __name__ == "__main__":
    unittest.main()
