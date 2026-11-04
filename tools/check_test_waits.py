#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks that every sleep, clock read and thread start in MiniDAQ's tests says why it is safe
(Chapter 16, Chapter 32, CAPA-0001).

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

Since release 0.7.0 (MDQ-PR-047, MDQ-PR-048) two more kinds of line must say why they are safe,
in a comment on the line or on one of the two lines above it:

- a clock read ("// clock: <kind>"): deadline (a limit only a hang reaches, or how long a loop
  runs when any duration gives the same result), speed (asserts a speed; the test is a row of
  CAPA-0001's margin table), measure (the time is reported or compared with another time of the
  same run, not with a fixed limit), data (the time is input data, such as a timestamp) or
  minimum (asserts that at least this much time passed, which a slow machine cannot break);
- a thread start ("// threads: <kind>"): joined (what the test checks is complete when the
  threads are joined or their result is waited for, whatever order they ran in) or started (the
  test waits until each thread has started its work, with a latch, a barrier or eventually,
  before it relies on it; rule 5.6).

Usage: check_test_waits.py ROOT. Exit status 0 if every such line is tagged.
"""
import pathlib
import re
import sys

SLEEP = re.compile(r"\bsleep_(?:for|until)\s*\(|\btime\.sleep\s*\(")
TAG = re.compile(r"(?://|#) sleep: (?:poll|minimum|device|hides only)\b")
CLOCK = re.compile(r"\b(?:steady_clock|system_clock|high_resolution_clock|Clock)::now\(\)"
                   r"|\btime\.(?:perf_counter|monotonic|time)\(|\btimeit\.")
CLOCK_KINDS = "deadline|speed|measure|data|minimum"
CLOCK_TAG = re.compile(rf"(?://|#) clock: (?:{CLOCK_KINDS})\b")
THREAD = re.compile(r"\bstd::j?thread\s+\w+\s*[{(]|\bstd::j?thread\s*[{(]"
                    r"|\.emplace_back\(\s*\[|\bthreading\.Thread\(")
THREAD_TAG = re.compile(r"(?://|#) threads: (?:joined|started)\b")
HELPER = "minidaq/tests/unit/eventually.hpp"


def sources(root):
    for d in ("minidaq/tests", "recon/tests", "analysis/tests"):
        yield from (root / d).rglob("*.[ch]pp")
        yield from (root / d).rglob("*.py")
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
        lines = f.read_text().splitlines()
        for n, line in enumerate(lines, 1):
            if SLEEP.search(line) and not TAG.search(line):
                found.append(f"{rel}:{n}: a sleep without '// sleep: poll|minimum|device|hides only'")
            near = lines[max(0, n - 3):n]  # this line and the two above it
            if CLOCK.search(line) and not any(CLOCK_TAG.search(x) for x in near):
                found.append(f"{rel}:{n}: a clock read without '// clock: {CLOCK_KINDS}'")
            if THREAD.search(line) and not any(THREAD_TAG.search(x) for x in near):
                found.append(f"{rel}:{n}: a thread start without '// threads: joined|started'")
    return found
# [/snippet:check]


def main(root):
    found = untagged(root)
    for f in found:
        print(f)
    print("test waits, clocks and threads: " + ("ok" if not found else f"{len(found)} untagged"))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(pathlib.Path(sys.argv[1]).resolve()))
