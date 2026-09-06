"""Exercise release boundaries using only synthetic, temporary file trees."""

from __future__ import annotations

import hashlib
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import package_release as packaging
from package_release import build_release, write_zip
from release_check import REQUIRED_FILES, check_git_history, check_tree, is_allowed


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

    def complete_fixture(self) -> None:
        """Satisfy the current manifest without copying any real project data."""
        for name in REQUIRED_FILES:
            content = "{}\n" if name.endswith(".json") else "# Public test fixture\n"
            self.write(name, content)

    def output_paths(self, basename: str) -> dict[str, Path]:
        output = Path(self.temp.name) / basename
        return {"directory": output, "manifest": output.with_name(output.name + "-sha256.json"),
                "zip": output.with_name(output.name + ".zip")}

    def run_main(self, output: Path) -> int:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return packaging.main(["--source", str(self.root), "--output", str(output)])

    def assert_absent(self, path: Path) -> None:
        self.assertFalse(path.exists() or path.is_symlink(), str(path))

    def seed_collision(self, path: Path, kind: str) -> tuple[Path, bytes]:
        payload = b"Existing public test file; preserve unchanged.\n"
        if kind == "file":
            path.write_bytes(payload)
            return path, payload
        if kind == "directory":
            path.mkdir()
            sentinel = path / "unrelated.txt"
            sentinel.write_bytes(payload)
            return sentinel, payload
        referent = path.with_name(path.name + "-referent")
        if kind == "live-symlink":
            referent.write_bytes(payload)
        path.symlink_to(referent)
        return referent, payload

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

    def test_main_preserves_every_existing_output_kind(self) -> None:
        self.complete_fixture()
        for role in ("directory", "manifest", "zip"):
            for kind in ("file", "directory", "live-symlink", "dangling-symlink"):
                with self.subTest(role=role, kind=kind):
                    paths = self.output_paths(f"existing-{role}-{kind}")
                    collision = paths[role]
                    referent, payload = self.seed_collision(collision, kind)
                    before = collision.lstat()
                    self.assertEqual(self.run_main(paths["directory"]), 1)
                    after = collision.lstat()
                    self.assertEqual((before.st_dev, before.st_ino, before.st_mode),
                                     (after.st_dev, after.st_ino, after.st_mode))
                    if kind == "dangling-symlink":
                        self.assertTrue(collision.is_symlink())
                        self.assert_absent(referent)
                    else:
                        self.assertEqual(referent.read_bytes(), payload)
                    for other_role, other in paths.items():
                        if other_role != role:
                            self.assert_absent(other)

    def test_main_rejects_racing_output_creation_after_preflight(self) -> None:
        self.complete_fixture()
        stage_release = packaging._staged_release
        for role in ("directory", "manifest", "zip"):
            for kind in ("file", "dangling-symlink"):
                with self.subTest(role=role, kind=kind):
                    paths = self.output_paths(f"racing-{role}-{kind}")
                    collision = paths[role]
                    seeded = []

                    @contextmanager
                    def raced_stage(*args, **kwargs):
                        with stage_release(*args, **kwargs) as result:
                            seeded.append(self.seed_collision(collision, kind))
                            yield result

                    with patch.object(packaging, "_staged_release", raced_stage):
                        self.assertEqual(self.run_main(paths["directory"]), 1)
                    referent, payload = seeded[0]
                    if kind == "dangling-symlink":
                        self.assertTrue(collision.is_symlink())
                        self.assert_absent(referent)
                    else:
                        self.assertEqual(collision.read_bytes(), payload)
                    for other_role, other in paths.items():
                        if other_role != role:
                            self.assert_absent(other)

    def test_main_copy_failure_removes_owned_partial_outputs(self) -> None:
        self.complete_fixture()
        paths = self.output_paths("failed-copy")
        sentinel = Path(self.temp.name) / "unrelated.txt"
        sentinel.write_text("preserve", encoding="utf-8")
        copy_staged = packaging._copy_staged
        observed_reservation = []

        def failed_copy(source, output, *args, **kwargs):
            observed_reservation.append(all(path.exists() for path in paths.values()))
            output.write(b"partial copied content")
            raise OSError("Injected copy failure")

        def fail_reserved_copy(staged, destination, created):
            with patch.object(packaging.shutil, "copyfileobj", failed_copy):
                copy_staged(staged, destination, created)

        with patch.object(packaging, "_copy_staged", fail_reserved_copy):
            self.assertEqual(self.run_main(paths["directory"]), 1)
        self.assertEqual(observed_reservation, [True])
        for path in paths.values():
            self.assert_absent(path)
        self.assertEqual(sentinel.read_text(), "preserve")

    def test_main_manifest_failure_removes_owned_partial_outputs(self) -> None:
        self.complete_fixture()
        paths = self.output_paths("failed-manifest")
        original_open = packaging._CreatedPaths.open

        class FailedManifest:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.stream.close()

            def write(self, value):
                self.stream.write(value[:4])
                raise OSError("Injected manifest failure")

        def fail_manifest(created, path):
            stream = original_open(created, path)
            return FailedManifest(stream) if path == paths["manifest"] else stream

        with patch.object(packaging._CreatedPaths, "open", fail_manifest):
            self.assertEqual(self.run_main(paths["directory"]), 1)
        for path in paths.values():
            self.assert_absent(path)

    def test_main_zip_failure_removes_owned_partial_outputs(self) -> None:
        self.complete_fixture()
        paths = self.output_paths("failed-zip")

        def failed_zip(root, stream):
            stream.write(b"partial archive")
            raise OSError("Injected ZIP failure")

        with patch.object(packaging, "write_zip", failed_zip):
            self.assertEqual(self.run_main(paths["directory"]), 1)
        for path in paths.values():
            self.assert_absent(path)

    def test_rollback_preserves_replaced_reserved_file(self) -> None:
        self.complete_fixture()
        paths = self.output_paths("replaced-manifest")
        displaced = paths["manifest"].with_name("displaced-owned-manifest")
        cleanup = packaging._CreatedPaths.cleanup

        def replace_then_clean(created):
            # Rollback runs after reserved handles close. Replacing here also
            # exercises Windows, where an open file cannot be renamed.
            # Keep the original inode alive so this deterministically tests
            # replacement identity rather than filesystem inode reuse.
            paths["manifest"].rename(displaced)
            paths["manifest"].write_bytes(b"another process owns this")
            cleanup(created)

        with patch.object(packaging, "write_zip", side_effect=OSError("Injected ZIP failure")), \
                patch.object(packaging._CreatedPaths, "cleanup", replace_then_clean):
            self.assertEqual(self.run_main(paths["directory"]), 1)
        self.assertEqual(paths["manifest"].read_bytes(), b"another process owns this")
        self.assert_absent(paths["directory"])
        self.assert_absent(paths["zip"])

    def test_rollback_preserves_unrelated_child_in_reserved_directory(self) -> None:
        self.complete_fixture()
        paths = self.output_paths("unrelated-child")
        copy_staged = packaging._copy_staged

        def add_child_then_fail(staged, destination, created):
            copy_staged(staged, destination, created)
            (destination / "unrelated.txt").write_bytes(b"another process owns this")
            raise OSError("Injected failure with unrelated child")

        with patch.object(packaging, "_copy_staged", add_child_then_fail):
            self.assertEqual(self.run_main(paths["directory"]), 1)
        self.assertEqual(list(paths["directory"].iterdir()), [paths["directory"] / "unrelated.txt"])
        self.assertEqual((paths["directory"] / "unrelated.txt").read_bytes(), b"another process owns this")
        self.assert_absent(paths["manifest"])
        self.assert_absent(paths["zip"])

    def test_rollback_does_not_follow_replaced_directory_symlink(self) -> None:
        self.complete_fixture()
        paths = self.output_paths("replaced-directory")
        displaced = Path(self.temp.name) / "displaced-owned-directory"
        foreign = Path(self.temp.name) / "foreign-directory"
        foreign.mkdir()
        (foreign / "README.md").write_bytes(b"preserve foreign content")
        copy_staged = packaging._copy_staged

        def replace_then_fail(staged, destination, created):
            copy_staged(staged, destination, created)
            destination.rename(displaced)
            destination.symlink_to(foreign, target_is_directory=True)
            raise OSError("Injected failure after parent replacement")

        with patch.object(packaging, "_copy_staged", replace_then_fail):
            self.assertEqual(self.run_main(paths["directory"]), 1)
        self.assertTrue(paths["directory"].is_symlink())
        self.assertEqual((foreign / "README.md").read_bytes(), b"preserve foreign content")
        self.assert_absent(paths["manifest"])
        self.assert_absent(paths["zip"])

    def test_direct_write_zip_rejects_existing_targets(self) -> None:
        self.write("README.md", "# Public fixture\n")
        for kind in ("file", "directory", "live-symlink", "dangling-symlink"):
            with self.subTest(kind=kind):
                target = Path(self.temp.name) / f"existing-{kind}.zip"
                referent, payload = self.seed_collision(target, kind)
                with self.assertRaises(OSError):
                    write_zip(self.root, target)
                if kind == "dangling-symlink":
                    self.assertTrue(target.is_symlink())
                    self.assert_absent(referent)
                else:
                    self.assertEqual(referent.read_bytes(), payload)

    def test_direct_write_zip_failure_removes_partial_archive(self) -> None:
        self.write("README.md", "# Public fixture\n")
        target = Path(self.temp.name) / "failed-direct.zip"
        with patch.object(packaging.zipfile.ZipFile, "writestr", side_effect=OSError("Injected ZIP write failure")):
            with self.assertRaises(OSError):
                write_zip(self.root, target)
        self.assert_absent(target)

    def test_direct_write_zip_string_and_pathlike_targets_are_exclusive(self) -> None:
        self.write("README.md", "# Public fixture\n")

        class ArchivePath:
            def __init__(self, path):
                self.path = path

            def __fspath__(self):
                return str(self.path)

        for convert in (str, ArchivePath):
            for kind in ("file", "dangling-symlink"):
                with self.subTest(path_type=convert.__name__, kind=kind):
                    target = Path(self.temp.name) / f"typed-{convert.__name__}-{kind}.zip"
                    referent, payload = self.seed_collision(target, kind)
                    with self.assertRaises(OSError):
                        write_zip(self.root, convert(target))
                    if kind == "dangling-symlink":
                        self.assertTrue(target.is_symlink())
                        self.assert_absent(referent)
                    else:
                        self.assertEqual(target.read_bytes(), payload)

    def test_full_main_archives_and_manifests_are_reproducible(self) -> None:
        self.complete_fixture()
        first = self.output_paths("complete-one")
        second = self.output_paths("complete-two")
        self.assertEqual(self.run_main(first["directory"]), 0)
        self.assertEqual(self.run_main(second["directory"]), 0)
        self.assertEqual(first["zip"].read_bytes(), second["zip"].read_bytes())
        self.assertEqual(first["manifest"].read_bytes(), second["manifest"].read_bytes())
        manifest = json.loads(first["manifest"].read_text())
        self.assertEqual(set(manifest), REQUIRED_FILES)
        with zipfile.ZipFile(first["zip"]) as archive:
            archived = {name.removeprefix("agent-sherlock/"): archive.read(name)
                        for name in archive.namelist()}
        self.assertEqual(set(archived), REQUIRED_FILES)
        for name, data in archived.items():
            self.assertEqual(manifest[name], hashlib.sha256(data).hexdigest())
            self.assertEqual(data, (first["directory"] / name).read_bytes())
            self.assertEqual(data, (self.root / name).read_bytes())

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
