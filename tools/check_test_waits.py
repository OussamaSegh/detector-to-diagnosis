#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks that every sleep in MiniDAQ's tests says why it is there (Chapter 16, CAPA-0001).

A test that sleeps for a fixed time and then asserts that something has happened fails on a
slow or busy machine although the code is right (problem reports MDQ-PR-010 and MDQ-PR-011).
Coding standard rule 5.5 therefore allows a sleep in a test only for one of four reasons, which
the line states in a comment "// sleep: <reason>":

- poll: inside a loop that ends when a condition holds or a deadline passes;
- minimum: the test needs at least this much time to pass, and more is still correct;
- device: it models a slow device, a slow consumer or work that takes time;
- hides only: it gives a wrong behavior the time to show, so a slow machine can only hide a
  failure, never cause one.

Waiting for a condition uses test_support::eventually (minidaq/tests/unit/eventually.hpp).

Usage: check_test_waits.py ROOT. Exit status 0 if every sleep is tagged.
"""
import pathlib
import re
import sys

SLEEP = re.compile(r"\bsleep_(?:for|until)\s*\(|\btime\.sleep\s*\(")
TAG = re.compile(r"(?://|#) sleep: (?:poll|minimum|device|hides only)\b")
HELPER = "minidaq/tests/unit/eventually.hpp"


def sources(root):
    yield from (root / "minidaq/tests").rglob("*.[ch]pp")
    for tests in sorted(root.glob("exercises/ch*/*/tests")):
        yield from tests.rglob("*.[ch]pp")
        yield from tests.rglob("*.py")


# [snippet:check]
def untagged(root):
    found = []
    for f in sorted(sources(root)):
        rel = f.relative_to(root).as_posix()
        if rel == HELPER:
            continue
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if SLEEP.search(line) and not TAG.search(line):
                found.append(f"{rel}:{n}: a sleep without '// sleep: poll|minimum|device|hides only'")
    return found
# [/snippet:check]


def main(root):
    found = untagged(root)
    for f in found:
        print(f)
    print("test sleeps: " + ("ok" if not found else f"{len(found)} untagged"))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(pathlib.Path(sys.argv[1]).resolve()))
