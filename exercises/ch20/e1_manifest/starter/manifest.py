# SPDX-License-Identifier: MIT
"""Exercise 20.1 starter: the manifest of a release package and its check."""
from __future__ import annotations

import dataclasses
import hashlib
import pathlib

NAME = "MANIFEST.sha256"


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


def write_manifest(top: pathlib.Path) -> list[str]:
    """Writes top/MANIFEST.sha256 for every regular file below top except itself; returns the paths."""
    raise NotImplementedError  # TODO


def read_manifest(path: pathlib.Path) -> dict[str, str]:
    """Path to digest. Raises ValueError for a malformed line, an escaping path or a duplicate."""
    raise NotImplementedError  # TODO


def verify(top: pathlib.Path) -> Report:
    """Every difference between the files below top and its manifest."""
    raise NotImplementedError  # TODO
