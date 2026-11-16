#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks the SOUP list against the pins in cmake/Dependencies.cmake (Chapter 14).

For every FetchContent dependency, docs/regulatory/soup-list.md must
- name its exact version and its pin (the git commit, or the archive's SHA-256), so that the
  list identifies the same bytes the build uses,
- for a shipped item (scope "required" in tools/make_sbom.py), record a known-anomaly review
  dated YYYY-MM-DD for the current MiniDAQ minor version: "| Last review | 2026-10-25, for
  MiniDAQ 0.3 ...". A new minor version therefore needs a new review before its release.

Every item of section 1 (the shipped software, platform libraries included) must also say when
its supplier stops supporting it (Chapter 40, the maintenance plan): "| Support ends | ..." with
a date YYYY-MM-DD or "no announced end". A date before the end of the support period that the
maintenance plan promises after the item's last review (SUPPORT_MONTHS) needs a row
"| End-of-support plan | ..." that says what MiniDAQ does about it.

Usage: check_soup.py ROOT. Exit status 0 if the list matches the build, 1 otherwise.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_sbom import KNOWN, dependencies  # noqa: E402  (one parser for the SBOM and this check)

SUPPORT_MONTHS = 24  # docs/regulatory/maintenance-plan.md, section 3
SUPPORT = re.compile(r"^\|\s*Support ends\s*\|\s*(.+?)\s*\|\s*$", re.M)
REVIEW = re.compile(r"^\|\s*Last review\s*\|\s*(\d{4}-\d{2}-\d{2}), for MiniDAQ (\d+\.\d+)\b", re.M)


def sections(text):
    """{heading of a '| Field | <name> |' table: table text} for the per-item tables."""
    out = {}
    for m in re.finditer(r"^\| Field \| (.+?) \|\n((?:\|.*\n)+)", text, re.M):
        out[m.group(1).strip()] = m.group(2)
    return out


def shipped_tables(text):
    """{name: table} of the per-item tables in section 1, the shipped software."""
    start = text.find("## 1.")
    end = text.find("## 2.", start)
    return sections(text[start:end] if start >= 0 else "")


def months_later(date, months):
    """The ISO date `months` calendar months after `date`, on the same day (the 28th at most)."""
    y, m, d = (int(x) for x in date.split("-"))
    m += months
    y, m = y + (m - 1) // 12, (m - 1) % 12 + 1
    return f"{y:04d}-{m:02d}-{min(d, 28):02d}"


# [snippet:support]
def support_problems(name, table):
    """An item names its end of support; one that ends within the support period MiniDAQ
    promises after the item's last review has a plan for it."""
    m = SUPPORT.search(table)
    if not m:
        return [f"{name}: no '| Support ends | YYYY-MM-DD or no announced end |' row"]
    ends = re.match(r"(\d{4}-\d{2}-\d{2})", m.group(1))
    if not ends:
        if m.group(1).startswith("no announced end"):
            return []
        return [f"{name}: 'Support ends' begins with a date YYYY-MM-DD or 'no announced end'"]
    review = re.search(r"^\|\s*Last review\s*\|\s*(\d{4}-\d{2}-\d{2})", table, re.M)
    if not review:
        return [f"{name}: support ends {ends.group(1)}, and no dated review to measure it from"]
    horizon = months_later(review.group(1), SUPPORT_MONTHS)
    if ends.group(1) < horizon and not re.search(r"^\|\s*End-of-support plan\s*\|\s*\S", table, re.M):
        return [f"{name}: support ends {ends.group(1)}, before {horizon} ({SUPPORT_MONTHS} months "
                "after its last review): add an 'End-of-support plan' row"]
    return []
# [/snippet:support]


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
    for name, table in shipped_tables(soup_text).items():
        errors += support_problems(name, table)
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
