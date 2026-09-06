#!/usr/bin/env python3
"""Build and validate a clean, allowlisted public release without publishing it."""

from __future__ import annotations

import argparse
from contextlib import contextmanager, ExitStack
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from typing import BinaryIO, Iterator
import zipfile

from release_check import check_tree, files_under, source_files


class _CreatedPaths:
    """Track ownership so rollback never removes a pre-existing replacement."""

    def __init__(self) -> None:
        self.paths: dict[Path, tuple[int, int, int]] = {}

    @staticmethod
    def identity(info: os.stat_result) -> tuple[int, int, int]:
        return info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode)

    def matches(self, path: Path) -> bool:
        try:
            return self.identity(path.lstat()) == self.paths[path]
        except OSError:
            return False

    def mkdir(self, path: Path) -> None:
        path.mkdir()
        self.paths[path] = self.identity(path.lstat())

    def open(self, path: Path) -> BinaryIO:
        stream = path.open("xb")
        self.paths[path] = self.identity(os.fstat(stream.fileno()))
        return stream

    def cleanup(self) -> None:
        for path in reversed(self.paths):
            # A replaced parent must not redirect cleanup through a symlink.
            if any(parent in self.paths and not self.matches(parent) for parent in path.parents):
                continue
            if not self.matches(path):
                continue
            try:
                if stat.S_ISDIR(self.paths[path][2]):
                    path.rmdir()  # Preserve unrelated children created by another process.
                else:
                    path.unlink()
            except OSError:
                # A concurrent change or filesystem error must not widen cleanup.
                pass


def _check_destinations(source: Path, destination: Path, siblings: tuple[Path, ...] = ()) -> None:
    if destination.is_symlink():
        raise ValueError("Release destination must not be a symbolic link")
    if destination.resolve() == source or source.is_relative_to(destination.resolve()):
        raise ValueError("Release destination must not replace the source tree or one of its parents")
    for path in (destination, *siblings):
        if path.exists() or path.is_symlink():
            raise ValueError(f"Destination already exists: {path}; choose fresh output paths")


@contextmanager
def _staged_release(source: Path, parent: Path, *, require_complete: bool) -> Iterator[tuple[Path, dict[str, str]]]:
    selected = source_files(source)
    for path in selected:
        if path.is_symlink() or not path.resolve().is_relative_to(source):
            raise ValueError(f"Source contains a symbolic link: {path.relative_to(source)}")
        # A selected file beneath a symlinked directory is also forbidden.
        if any(parent.is_symlink() for parent in path.parents if parent != source and parent.is_relative_to(source)):
            raise ValueError(f"Source contains a symbolic-link ancestor: {path.relative_to(source)}")
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sherlock-release-", dir=parent) as temp:
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
        yield staged, hashes


@contextmanager
def _reserve_outputs(destination: Path, siblings: tuple[Path, ...] = ()) -> Iterator[tuple[_CreatedPaths, dict[Path, BinaryIO]]]:
    created = _CreatedPaths()
    try:
        with ExitStack() as stack:
            # These operations, not the earlier existence checks, prevent races.
            created.mkdir(destination)
            streams = {path: stack.enter_context(created.open(path)) for path in siblings}
            yield created, streams
    except BaseException:
        # Close all held files before rollback, including on Windows.
        created.cleanup()
        raise


def _copy_staged(staged: Path, destination: Path, created: _CreatedPaths) -> None:
    for path in files_under(staged):
        relative = path.relative_to(staged)
        parent = destination
        for part in relative.parts[:-1]:
            parent = parent / part
            if parent not in created.paths:
                created.mkdir(parent)
        target = destination / relative
        with path.open("rb") as source, created.open(target) as output:
            shutil.copyfileobj(source, output)
            if hasattr(os, "fchmod"):
                os.fchmod(output.fileno(), 0o644)


def build_release(source: Path, destination: Path, *, require_complete: bool = True) -> dict[str, str]:
    source = source.resolve()
    destination = destination.absolute()
    _check_destinations(source, destination)
    with _staged_release(source, destination.parent, require_complete=require_complete) as (staged, hashes):
        with _reserve_outputs(destination) as (created, _):
            _copy_staged(staged, destination, created)
    return hashes


def write_zip(root: Path, target: Path | str | BinaryIO) -> None:
    """Stable paths, timestamps, permissions, and ordering yield reproducible ZIPs."""
    created = _CreatedPaths()
    try:
        with ExitStack() as stack:
            path = Path(target) if isinstance(target, (str, os.PathLike)) else None
            stream = stack.enter_context(created.open(path)) if path is not None else target
            with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for path in files_under(root):
                    name = "agent-sherlock/" + path.relative_to(root).as_posix()
                    info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, path.read_bytes())
    except BaseException:
        created.cleanup()
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, help="Fresh output directory (default: source/dist/agent-sherlock)")
    args = parser.parse_args(argv)
    output = (args.output or args.source / "dist" / "agent-sherlock").absolute()
    manifest = output.parent / (output.name + "-sha256.json")
    archive = output.parent / (output.name + ".zip")
    try:
        source = args.source.resolve()
        _check_destinations(source, output, (manifest, archive))
        with _staged_release(source, output.parent, require_complete=True) as (staged, hashes):
            with _reserve_outputs(output, (manifest, archive)) as (created, streams):
                _copy_staged(staged, output, created)
                streams[manifest].write((json.dumps(hashes, indent=2, sort_keys=True) + "\n").encode("utf-8"))
                write_zip(staged, streams[archive])
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
