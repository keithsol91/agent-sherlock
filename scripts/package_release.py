#!/usr/bin/env python3
"""Build and validate a clean, allowlisted public release without publishing it."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

from release_check import check_tree, files_under, source_files


def build_release(source: Path, destination: Path, *, require_complete: bool = True) -> dict[str, str]:
    source = source.resolve()
    destination = destination.absolute()
    if destination.is_symlink():
        raise ValueError("Release destination must not be a symbolic link")
    if destination.resolve() == source or source.is_relative_to(destination.resolve()):
        raise ValueError("Release destination must not replace the source tree or one of its parents")
    if destination.exists():
        raise ValueError("Destination already exists; choose a fresh output directory")
    selected = source_files(source)
    for path in selected:
        if path.is_symlink() or not path.resolve().is_relative_to(source):
            raise ValueError(f"Source contains a symbolic link: {path.relative_to(source)}")
        # A selected file beneath a symlinked directory is also forbidden.
        if any(parent.is_symlink() for parent in path.parents if parent != source and parent.is_relative_to(source)):
            raise ValueError(f"Source contains a symbolic-link ancestor: {path.relative_to(source)}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sherlock-release-", dir=destination.parent) as temp:
        staged = Path(temp) / "agent-sherlock"
        staged.mkdir()
        for path in selected:
            target = staged / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            target.chmod(0o644)
        findings = check_tree(staged, require_complete=require_complete)
        if findings:
            raise ValueError("Release checks failed:\n" + "\n".join(str(finding) for finding in findings))
        hashes = {path.relative_to(staged).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in files_under(staged)}
        shutil.move(str(staged), str(destination))
    return hashes


def write_zip(root: Path, target: Path) -> None:
    """Stable paths, timestamps, permissions, and ordering yield reproducible ZIPs."""
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files_under(root):
            name = "agent-sherlock/" + path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, help="Fresh output directory (default: source/dist/agent-sherlock)")
    args = parser.parse_args(argv)
    output = args.output or args.source / "dist" / "agent-sherlock"
    try:
        hashes = build_release(args.source, output)
        manifest = output.parent / (output.name + "-sha256.json")
        manifest.write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        archive = output.parent / (output.name + ".zip")
        write_zip(output, archive)
    except (OSError, ValueError) as error:
        print(f"Release packaging failed: {error}", file=sys.stderr)
        return 1
    print(f"Prepared {len(hashes)} checked files in {output}")
    print(f"Archive: {archive}")
    print(f"SHA-256 manifest: {manifest}")
    print("Nothing was committed, pushed, published, or connected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
