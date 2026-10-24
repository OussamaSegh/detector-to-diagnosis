# SPDX-License-Identifier: MIT
"""Exercise 6.3: a checker for architecture decision records (format: docs/adr/0001)."""
import pathlib


def lint_file(path):
    """Problems in one ADR, as human-readable strings (empty: fine)."""
    path = pathlib.Path(path)
    # TODO: file name, title line and its number, Date, Status, the four sections in order,
    # at least two options, Consequences with non-empty Positive and Negative.
    return []


def lint_dir(directory):
    """{file name: problems} for every ADR-like file, plus directory-wide problems
    (duplicate numbers, gaps, superseded-by targets) under the key '(directory)'."""
    directory = pathlib.Path(directory)
    # TODO
    return {p.name: lint_file(p) for p in sorted(directory.glob("[0-9]*.md"))}
