#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks the SOUP list against the pins in cmake/Dependencies.cmake (Chapter 14).

For every FetchContent dependency, docs/regulatory/soup-list.md must
- name its exact version and its pin (the git commit, or the archive's SHA-256), so that the
  list identifies the same bytes the build uses,
- for a shipped item (scope "required" in tools/make_sbom.py), record a known-anomaly review
  dated YYYY-MM-DD for the current MiniDAQ minor version: "| Last review | 2026-10-25, for
  MiniDAQ 0.3 ...". A new minor version therefore needs a new review before its release.

Usage: check_soup.py ROOT. Exit status 0 if the list matches the build, 1 otherwise.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_sbom import KNOWN, dependencies  # noqa: E402  (one parser for the SBOM and this check)

REVIEW = re.compile(r"^\|\s*Last review\s*\|\s*(\d{4}-\d{2}-\d{2}), for MiniDAQ (\d+\.\d+)\b", re.M)


def sections(text):
    """{heading of a '| Field | <name> |' table: table text} for the per-item tables."""
    out = {}
    for m in re.finditer(r"^\| Field \| (.+?) \|\n((?:\|.*\n)+)", text, re.M):
        out[m.group(1).strip()] = m.group(2)
    return out


def check(cmake_text, soup_text, minidaq_version):
    errors = []
    minor = ".".join(minidaq_version.split(".")[:2])
    items = sections(soup_text)
    for name, f in dependencies(cmake_text):
        pin = f.get("GIT_TAG") or f.get("URL_HASH", "=").split("=", 1)[1]
        version = f.get("version")
        if not pin or pin not in soup_text:
            errors.append(f"{name}: pin {pin or '(none)'} is not in the SOUP list")
        if not version or version not in soup_text:
            errors.append(f"{name}: version {version} is not in the SOUP list")
        if KNOWN.get(name, {}).get("scope") != "required":
            continue
        table = next((t for title, t in items.items() if pin and pin in t), None)
        if table is None:
            errors.append(f"{name}: shipped item without its own table ('| Field | {name} |')")
            continue
        m = REVIEW.search(table)
        if not m:
            errors.append(f"{name}: no dated known-anomaly review ('| Last review | YYYY-MM-DD, for MiniDAQ X.Y')")
        elif m.group(2) != minor:
            errors.append(f"{name}: last review was for MiniDAQ {m.group(2)}, this is {minor}: review again")
    return errors


def main(root):
    errors = check((root / "cmake/Dependencies.cmake").read_text(),
                   (root / "docs/regulatory/soup-list.md").read_text(),
                   (root / "VERSION").read_text().strip())
    for e in errors:
        print(e)
    print("SOUP list: " + ("ok" if not errors else f"{len(errors)} problem(s)"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(pathlib.Path(sys.argv[1]).resolve()))
