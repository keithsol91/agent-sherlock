#!/usr/bin/env python3
"""Offline checks for the exact public release tree; Python 3.10+, no packages.

This catches common mistakes, not every possible secret or licensing problem.
It deliberately does not fetch links or inspect adjacent private projects.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit


ROOT_FILES = frozenset({
    ".gitignore", "AGENTS.md", "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md",
    "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "CHANGELOG.md",
})
PUBLIC_DOCS = frozenset({
    "FILE-AUDIT.md", "RELEASE.md",
})
DESIGN_FILES = frozenset({
    "AGENT-INSTRUCTIONS.md", "DESIGN-SYSTEM.md", "CHANGELOG.md",
    "asset-registry.json", "tokens/tokens.json", "tokens/contrast-report.json",
    "styles/fonts.css", "styles/tokens.css", "styles/components.css",
    "fonts/Fraunces-variable.ttf", "fonts/Fraunces-OFL.txt",
    "fonts/Inter-variable.ttf", "fonts/Inter-OFL.txt", "fonts/README.md",
    "reference/approved-homepage.png", "docs/components.md",
    "docs/implementation.md", "docs/page-patterns.md", "docs/prompt-kit.md",
    "docs/asset-specification.md", "docs/release-checklist.md",
    "scripts/validate_package.py",
})
TREE_SUFFIXES = {
    ".github": {".yml", ".yaml", ".md"},
    ".devcontainer": {".json", ".md"},
    "tests": {".py", ".json"},
    "public-facing/skills": {".md", ".json", ".txt", ".py"},
    "public-facing/documentation": {".md", ".json", ".png", ".svg"},
    "public-facing/assets": {".html", ".css", ".js", ".svg", ".png", ".webp", ".ico", ".ttf", ".woff2", ".txt"},
    "public-facing/examples": {".html", ".css", ".js", ".json", ".md"},
    "public-facing/runtime/src": {".py", ".json", ".md"},
    "public-facing/runtime/tests": {".py", ".json"},
}
RUNTIME_FILES = frozenset({"pyproject.toml", "uv.lock", "README.md", ".python-version", ".gitignore"})
WEB_FILES = frozenset({"index.html", "docs.html", "styles.css", "slack-gallery.js", "README.md", ".gitignore"})
RELEASE_SCRIPTS = frozenset({"package_release.py", "release_check.py"})
FORBIDDEN_COMPONENTS = frozenset({
    ".vercel", ".env", ".venv", "venv", "node_modules", "__pycache__", ".git",
    ".playwright-cli", "archive", "output", "brand", ".hermes", ".ssh",
    "case-data", ".sherlock", "sherlock-data", "runtime-state", ".pytest_cache",
    ".ruff_cache", ".mypy_cache", "dist", "build", ".cache",
})
FORBIDDEN_SUFFIXES = frozenset({".db", ".sqlite", ".sqlite3", ".log", ".pem", ".key", ".p12", ".pfx", ".pyc", ".zip", ".tar", ".gz"})
TEXT_SUFFIXES = frozenset({".py", ".md", ".json", ".yml", ".yaml", ".html", ".css", ".js", ".svg", ".txt", ".toml", ".lock"})
REQUIRED_FILES = frozenset({
    "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md",
    "CONTRIBUTING.md", "SECURITY.md", ".gitignore",
    "CODE_OF_CONDUCT.md", "CHANGELOG.md", "AGENTS.md", "docs/FILE-AUDIT.md", "docs/RELEASE.md",
    "scripts/release_check.py", "scripts/package_release.py", "public-facing/index.html",
    "public-facing/runtime/pyproject.toml", "public-facing/runtime/uv.lock",
    "public-facing/runtime/src/agent_sherlock/__main__.py",
    "public-facing/runtime/src/agent_sherlock/cli.py",
    "public-facing/runtime/src/agent_sherlock/server.py",
    "public-facing/skills/agent-sherlock/SKILL.md",
    "public-facing/skills/sherlock-account-context/SKILL.md",
    "public-facing/skills/sherlock-competitor-research/SKILL.md",
    "public-facing/skills/sherlock-case-files/SKILL.md",
    "public-facing/skills/sherlock-recall/SKILL.md",
    "public-facing/documentation/install.md", "public-facing/documentation/permissions.md",
    "public-facing/documentation/troubleshooting.md", "public-facing/documentation/compatibility.md",
})
PATTERNS = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("provider-token", re.compile(r"\b(?:sk-(?:proj-|ant-api\d+-)?[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|xox[baprs]-[A-Za-z0-9-]{20,})\b")),
    ("aws-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("machine-path", re.compile(r"(?:/Users/|/home/)[A-Za-z0-9_.-]+/|[A-Z]:\\Users\\[A-Za-z0-9_.-]+\\")),
    ("deployment-id", re.compile(r"\b(?:dpl|prj)_[A-Za-z0-9]{16,}\b")),
    ("credential-url", re.compile(r"https?://[^\s/@:]+:[^\s/@]+@")),
    ("credential-assignment", re.compile(r'''(?im)(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*["']?\s*[:=]\s*["']([A-Za-z0-9_+/=-]{20,})["']''')),
)


@dataclass(frozen=True)
class Finding:
    path: str
    rule: str
    detail: str

    def __str__(self) -> str:
        return f"{self.path}: {self.rule}: {self.detail}"


def is_allowed(relative: Path) -> bool:
    """An explicit publication manifest. New top-level areas are excluded."""
    value = relative.as_posix()
    if value in ROOT_FILES:
        return True
    if len(relative.parts) == 2 and relative.parts[0] == "docs":
        return relative.name in PUBLIC_DOCS
    if len(relative.parts) == 2 and relative.parts[0] == "scripts":
        return relative.name in RELEASE_SCRIPTS
    if len(relative.parts) == 2 and relative.parts[0] == "public-facing":
        return relative.name in WEB_FILES
    if relative.parent.as_posix() == "public-facing/runtime":
        return relative.name in RUNTIME_FILES
    if value.startswith("design/agent-sherlock/"):
        return value.removeprefix("design/agent-sherlock/") in DESIGN_FILES
    return any(value.startswith(prefix + "/") and relative.suffix.lower() in suffixes
               for prefix, suffixes in TREE_SUFFIXES.items())


def forbidden_path(relative: Path) -> str | None:
    if any(part in FORBIDDEN_COMPONENTS for part in relative.parts):
        return "private, generated, dependency, or deployment directory"
    if relative.name.startswith(".env") and relative.name != ".env.example":
        return "environment file"
    if relative.suffix.lower() in FORBIDDEN_SUFFIXES:
        return "runtime, credential, compiled, or archive file"
    if relative.name == "FOR_Keith.md":
        return "owner-only handoff"
    return None


def files_under(root: Path) -> list[Path]:
    """Return hidden entries too; callers reject all symbolic links."""
    return sorted((path for path in root.rglob("*") if path.is_file() or path.is_symlink()), key=lambda p: p.as_posix())


def source_files(root: Path) -> list[Path]:
    """Select reviewed categories, never publish an arbitrary repository copy."""
    import os

    selected = []
    for directory, subdirs, names in os.walk(root, followlinks=False):
        base = Path(directory)
        subdirs[:] = [name for name in subdirs if name not in FORBIDDEN_COMPONENTS]
        # Include symlinked directories as candidates so package validation can
        # reject them; never follow them to read their contents.
        for name in names + [name for name in subdirs if (base / name).is_symlink()]:
            path = base / name
            relative = path.relative_to(root)
            allowed_directory = any(prefix == relative.as_posix() or prefix.startswith(relative.as_posix() + "/")
                                    for prefix in TREE_SUFFIXES)
            if (is_allowed(relative) or (path.is_symlink() and allowed_directory)) and not forbidden_path(relative):
                selected.append(path)
    return sorted(selected, key=lambda path: path.as_posix())


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.targets: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if value is not None and name in {"href", "src", "poster"}:
                self.targets.append(value)
            if value is not None and (name == "id" or (tag == "a" and name == "name")):
                self.ids.add(value)


def strip_fences(content: str) -> str:
    return re.sub(r"(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$", "", content)


def markdown_ids(content: str) -> set[str]:
    result: set[str] = set()
    for heading in re.findall(r"(?m)^#{1,6}\s+(.+?)\s*#*\s*$", strip_fences(content)):
        slug = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        unique = slug
        count = 0
        while unique in result:
            count += 1
            unique = f"{slug}-{count}"
        result.add(unique)
    return result


def links_in(path: Path, content: str) -> list[str]:
    if path.suffix == ".html":
        parser = Links()
        parser.feed(content)
        return parser.targets
    if path.suffix == ".md":
        text = strip_fences(content)
        inline = re.findall(r"!?\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+[\"'][^\n]*?[\"'])?\s*\)", text)
        definitions = re.findall(r"(?m)^\s*\[[^\]]+\]:\s*(<[^>]+>|\S+)", text)
        return [value.strip("<>") for value in inline + definitions]
    if path.suffix == ".css":
        return [match[1] for match in re.findall(r"url\(\s*(['\"]?)(.*?)\1\s*\)", content)]
    return []


def check_links(root: Path, path: Path, content: str) -> list[Finding]:
    findings = []
    relative = path.relative_to(root).as_posix()
    for link in links_in(path, content):
        if not link or link.startswith(("//", "{{", "${")):
            continue
        try:
            parsed = urlsplit(link)
        except ValueError:
            findings.append(Finding(relative, "local-link", "malformed link target"))
            continue
        if parsed.scheme or parsed.netloc:
            continue
        decoded = unquote(parsed.path)
        if decoded.startswith("/") and relative.startswith("public-facing/"):
            target = root / "public-facing" / decoded.lstrip("/")
        elif decoded.startswith("/"):
            target = root / decoded.lstrip("/")
        else:
            target = path.parent / decoded if decoded else path
        target = target.resolve()
        if not target.is_relative_to(root.resolve()):
            findings.append(Finding(relative, "local-link", f"link escapes release tree: {link}"))
            continue
        if not target.exists():
            findings.append(Finding(relative, "local-link", f"missing target: {link}"))
            continue
        if target.is_dir():
            index = target / "index.html"
            if index.exists():
                target = index
        if parsed.fragment and target.is_file() and target.suffix in {".html", ".md"}:
            text = target.read_text(encoding="utf-8")
            if target.suffix == ".html":
                parser = Links()
                parser.feed(text)
                ids = parser.ids
            else:
                ids = markdown_ids(text)
            if unquote(parsed.fragment) not in ids:
                findings.append(Finding(relative, "local-anchor", f"missing anchor: {link}"))
    return findings


def check_tree(root: Path, *, require_complete: bool = True, links: bool = True) -> list[Finding]:
    """Inspect every file in a staged tree, without printing matched secrets."""
    findings: list[Finding] = []
    if not root.is_dir():
        return [Finding(".", "tree", "release directory does not exist")]
    if require_complete:
        for name in sorted(REQUIRED_FILES):
            if not (root / name).is_file():
                findings.append(Finding(name, "required", "missing required release file"))
    for path in files_under(root):
        relative = path.relative_to(root)
        name = relative.as_posix()
        if path.is_symlink():
            findings.append(Finding(name, "symlink", "symbolic links are not permitted in a public package"))
            continue
        blocked = forbidden_path(relative)
        if blocked:
            findings.append(Finding(name, "excluded-file", blocked))
        if not is_allowed(relative):
            findings.append(Finding(name, "allowlist", "file is outside the explicit publication manifest"))
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in ROOT_FILES:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(Finding(name, "text-encoding", "expected UTF-8 text"))
            continue
        for rule, pattern in PATTERNS:
            match = pattern.search(content)
            if match:
                line = content.count("\n", 0, match.start()) + 1
                findings.append(Finding(name, rule, f"possible sensitive content on line {line}; value withheld"))
        if links:
            findings.extend(check_links(root, path, content))
    return findings


def check_git_history(repository: Path) -> list[Finding]:
    """Read reachable committed blobs directly, without checkout or execution.

    All local branches and tags are scanned. Unreachable objects, remote-only
    refs, hosting metadata, and provider state are outside this local check.
    """
    def git(*arguments: str, input_data: bytes | None = None) -> bytes:
        result = subprocess.run(
            ["git", "--no-replace-objects", "-C", str(repository), *arguments],
            input=input_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, timeout=60,
        )
        if result.returncode:
            # Git diagnostics may contain local paths or URL credentials.
            raise ValueError("Git history command failed; confirm this is a readable Git repository")
        return result.stdout

    findings: list[Finding] = []
    try:
        git("rev-parse", "--git-dir")
        commits = git("rev-list", "--all").decode("ascii").splitlines()
        if not commits:
            return [Finding("git-history", "history", "repository has no commits to inspect")]
        seen_paths: set[tuple[str, str]] = set()
        seen_blobs: set[str] = set()
        for revision in commits:
            # A tree can contain a symbolic link or submodule even when its
            # blob bytes are harmless. Inspect modes and paths, never extract.
            entries = git("ls-tree", "-r", "-z", "--full-tree", revision).split(b"\0")
            for entry in entries:
                if not entry:
                    continue
                metadata, raw_name = entry.split(b"\t", 1)
                mode, kind, object_id = metadata.decode("ascii").split()
                name = raw_name.decode("utf-8", errors="replace")
                relative = Path(name)
                identity = (mode, name)
                label = f"git:{revision[:12]}:{name}"
                if identity not in seen_paths:
                    seen_paths.add(identity)
                    if mode in {"120000", "160000"}:
                        findings.append(Finding(label, "history-file", "symbolic link or submodule exists in history"))
                    blocked = forbidden_path(relative)
                    if blocked or not is_allowed(relative):
                        findings.append(Finding(label, "history-file", blocked or "file is outside the publication manifest"))
                if kind != "blob" or object_id in seen_blobs:
                    continue
                seen_blobs.add(object_id)
                size = int(git("cat-file", "-s", object_id))
                if size > 16 * 1024 * 1024:
                    findings.append(Finding(label, "history-size", "blob exceeds 16 MB; separate review required"))
                    continue
                raw = git("cat-file", "blob", object_id)
                if b"\0" in raw:
                    continue
                try:
                    content = raw.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                for rule, pattern in PATTERNS:
                    if pattern.search(content):
                        findings.append(Finding(label, rule, "possible sensitive content in committed blob; value withheld"))
            message = git("cat-file", "commit", revision).decode("utf-8", errors="replace")
            for rule, pattern in PATTERNS:
                if pattern.search(message):
                    findings.append(Finding(f"git:{revision[:12]}", rule, "possible sensitive content in commit metadata; value withheld"))
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        detail = str(error) if isinstance(error, ValueError) else "Git history unavailable or command timed out"
        findings.append(Finding("git-history", "history", detail))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--no-links", action="store_true", help="Only check file boundaries and sensitive text")
    parser.add_argument("--git-history", type=Path, metavar="PATH", help="Also scan all local branches/tags in a Git repository, without checking out files")
    args = parser.parse_args(argv)
    findings = check_tree(args.root.resolve(), links=not args.no_links)
    if args.git_history:
        findings.extend(check_git_history(args.git_history))
    for finding in findings:
        print(f"FAIL {finding}")
    if findings:
        print(f"Release check failed: {len(findings)} finding(s).")
        return 1
    print(f"Release check passed: {len(files_under(args.root))} files, including hidden files; local links checked: {not args.no_links}.")
    if args.git_history:
        print("Git history check passed for reachable commits and blobs across local branches and tags.")
    print("Offline heuristic check only: external links, image pixels, and ownership require separate review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
