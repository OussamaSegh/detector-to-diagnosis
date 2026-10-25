# SPDX-License-Identifier: MIT
"""Exercise 20.1 solution: the manifest of a release package and its check."""
from __future__ import annotations

import dataclasses
import hashlib
import pathlib
import re

NAME = "MANIFEST.sha256"
LINE = re.compile(r"^([0-9a-f]{64})  (\S.*)$")


@dataclasses.dataclass
class Report:
    changed: list[str]
    missing: list[str]
    added: list[str]

    @property
    def ok(self) -> bool:
        return not (self.changed or self.missing or self.added)


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _entries(top: pathlib.Path) -> tuple[list[str], list[str]]:
    """The regular files below top, and everything else that is not a directory (links)."""
    files, others = [], []
    for p in top.rglob("*"):
        rel = p.relative_to(top).as_posix()
        if p.is_symlink():
            others.append(rel)
        elif p.is_file() and rel != NAME:
            files.append(rel)
    return sorted(files), sorted(others)


# [snippet:write]
def write_manifest(top: pathlib.Path) -> list[str]:
    """Writes top/MANIFEST.sha256 for every regular file below top except itself; returns the
    paths."""
    files, _ = _entries(top)
    (top / NAME).write_text("".join(f"{sha256(top / f)}  {f}\n" for f in files))
    return files
# [/snippet:write]


def read_manifest(path: pathlib.Path) -> dict[str, str]:
    """Path to digest. Raises ValueError for a malformed line, an escaping path or a duplicate."""
    out: dict[str, str] = {}
    for n, line in enumerate(path.read_text().splitlines(), 1):
        m = LINE.match(line)
        if not m:
            raise ValueError(f"{path}:{n}: not '<sha256>  <path>'")
        digest, rel = m.groups()
        parts = pathlib.PurePosixPath(rel).parts
        if rel.startswith("/") or ".." in parts:
            raise ValueError(f"{path}:{n}: {rel} leaves the package")
        if rel in out:
            raise ValueError(f"{path}:{n}: {rel} listed twice")
        out[rel] = digest
    return out


# [snippet:verify]
def verify(top: pathlib.Path) -> Report:
    """Every difference between the files below top and its manifest."""
    listed = read_manifest(top / NAME)
    files, links = _entries(top)
    present = set(files)
    changed = sorted(f for f in present & listed.keys() if sha256(top / f) != listed[f])
    missing = sorted(listed.keys() - present)
    added = sorted((present - listed.keys()) | set(links))
    return Report(changed, missing, added)
# [/snippet:verify]
