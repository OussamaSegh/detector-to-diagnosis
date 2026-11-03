# SPDX-License-Identifier: MIT
"""Provenance: which data, which code and which environment produced a result.

A number in a report is evidence only if someone can tell, later, exactly what it was computed
from. This module writes two things:

- a dataset manifest: every input file with its size and SHA-256, so that a later analysis can
  prove it read the same bytes (``verify_manifest``), and a renamed or re-copied run can be
  recognized;
- an environment record: the package's version, the versions of Python and of each library that
  can change a number, the platform, the command, the time, and the git commit of the code when
  the code is in a git checkout.

This is what tools such as DVC automate. A run of a few files is well served by the manifest
alone; the manifest's own SHA-256 then names the dataset in one string.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import platform
import subprocess
import sys
from collections.abc import Iterable
from importlib import metadata
from typing import Any

from . import __version__

# The libraries whose versions can change a number in a report.
LIBRARIES = ("numpy", "scipy", "matplotlib")


def sha256_file(path: pathlib.Path, block: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(block):
            h.update(chunk)
    return h.hexdigest()


# [snippet:manifest]
def make_manifest(paths: Iterable[pathlib.Path], root: pathlib.Path) -> dict[str, Any]:
    """{"format", "files": [{"path" (relative to root), "bytes", "sha256"}], sorted by path}."""
    files = []
    for p in sorted(pathlib.Path(x) for x in paths):
        files.append({"path": p.resolve().relative_to(root.resolve()).as_posix(),
                      "bytes": p.stat().st_size, "sha256": sha256_file(p)})
    return {"format": "minidaq-analysis manifest 1", "files": files}


def manifest_id(manifest: dict[str, Any]) -> str:
    """SHA-256 of the manifest's canonical JSON: one string that names the dataset."""
    text = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify_manifest(manifest: dict[str, Any], root: pathlib.Path) -> list[str]:
    """The differences between the files under root and the manifest; empty if none."""
    problems = []
    for f in manifest["files"]:
        p = root / f["path"]
        if not p.is_file():
            problems.append(f"{f['path']}: missing")
        elif p.stat().st_size != f["bytes"]:
            problems.append(f"{f['path']}: {p.stat().st_size} bytes, manifest says {f['bytes']}")
        elif sha256_file(p) != f["sha256"]:
            problems.append(f"{f['path']}: SHA-256 differs")
    return problems
# [/snippet:manifest]


def git_commit(where: pathlib.Path) -> str | None:
    """The commit of the checkout that holds `where`, with "-dirty" if it has local changes;
    None outside a git checkout or without git."""
    try:
        commit = subprocess.run(["git", "-C", str(where), "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=True, timeout=10)
        dirty = subprocess.run(["git", "-C", str(where), "status", "--porcelain", "--", "."],
                               capture_output=True, text=True, check=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return commit.stdout.strip() + ("-dirty" if dirty.stdout.strip() else "")


def environment(argv: list[str] | None = None) -> dict[str, Any]:
    versions: dict[str, str | None] = {}
    for lib in LIBRARIES:
        try:
            versions[lib] = metadata.version(lib)
        except metadata.PackageNotFoundError:
            versions[lib] = None
    return {
        "package": "minidaq-analysis",
        "version": __version__,
        "code_commit": git_commit(pathlib.Path(__file__).resolve().parent),
        "python": platform.python_version(),
        "libraries": versions,
        "platform": platform.platform(),
        "command": list(sys.argv if argv is None else argv),
        "created_utc": datetime.datetime.now(datetime.UTC).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
    }
