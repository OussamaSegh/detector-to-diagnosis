#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks that software requirements are written in testable form (Chapter 14).

A requirement is one row of a Markdown table whose first cell is its ID:

    | SRS-SRT-001 | The sorter shall ... | sorter | T |

The checks are mechanical, so they catch the form of a bad requirement, not its content: a
reviewer still has to ask whether the requirement is right. Each requirement

- has an ID of the form SRS-AREA-nnn that no other requirement has,
- names its subject and says "shall" exactly once ("The sorter shall ...", or a condition
  first: "When ..., the sorter shall ..."), so it is one requirement and it is mandatory,
- avoids words that cannot be verified ("fast", "robust", "appropriate", "and/or", ...),
- gives a number with its unit, never a bare number of something measurable,
- names a verification method: T (test), A (analysis), I (inspection), D (demonstration)
  or M (measurement).

Usage: req_lint.py FILE.md [FILE.md ...]. Exit status 0 if every requirement passes.
"""
import pathlib
import re
import sys

# [snippet:rules]
ROW = re.compile(r"^\|\s*(SRS-[A-Z0-9-]*?)\s*\|\s*(.*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*$")
ID = re.compile(r"^SRS-[A-Z]{2,5}-\d{3}$")
SUBJECT = re.compile(r"^(?:(?:When|If|While|After|Before|Until|Unless|Where|For)\b[^.]*?,\s+)?[Tt]he\s[\w .,'/()-]+?\sshall\b")
VAGUE = [
    "fast", "quickly", "slow", "efficient", "efficiently", "robust", "robustly", "reliable",
    "reliably", "appropriate", "appropriately", "adequate", "adequately", "sufficient",
    "user-friendly", "easy", "easily", "flexible", "as soon as possible", "as needed",
    "if possible", "where possible", "normally", "usually", "etc", "and/or", "tbd",
    "high-performance", "real-time capable", "state of the art", "minimal", "optimal",
]
VAGUE_RE = re.compile(r"(?<![\w-])(" + "|".join(re.escape(w) for w in VAGUE) + r")(?![\w-])", re.I)
# A number of something measurable must carry its unit. Counts ("16 crystals", "2 boards"),
# versions ("1.3"), bit patterns and identifiers are written with the noun that follows them.
NUMBER = re.compile(r"(?<![\w.^/-])(\d+(?:[.,']\d+)*(?:\^\d+|/\d+)?)(?!\w|[.,]\d)(?:[\s-]*([^\s,;:)]+))?")
NAMED_BY = {"ieee", "iso", "iec", "rfc", "version", "versions", "schema", "api"}
UNITS = {
    "ps", "ns", "us", "µs", "ms", "s", "min", "h", "hz", "khz", "mhz", "kev", "mev", "mm", "cm",
    "m", "b", "bytes", "byte", "kib", "mib", "gib", "kb", "mb", "gb", "bit", "bits", "%",
    "words/s", "singles/s", "coincidences/s", "m/s", "k/s", "mbq", "bq", "degrees", "°",
}
COUNT_NOUNS = re.compile(r"^(?:[a-z][a-z-]*s|times|percent|of|to|and|or|per|in|out|bytes?|bit|"
                         r"block|board|crystal|word|single|record|packet|file|sector|ring|"
                         r"thread|stage|client|connection|digit|line|entry|bin|time|state|"
                         r"event|command|request|error|byte|second|minute)$")
METHODS = {"T", "A", "I", "D", "M"}
# [/snippet:rules]


def requirements(text):
    """(line number, id, text, item, methods) for every requirement row of a Markdown text."""
    out = []
    for n, line in enumerate(text.splitlines(), start=1):
        m = ROW.match(line)
        if m:
            out.append((n, m.group(1), m.group(2), m.group(3), m.group(4)))
    return out


def problems(req_id, req_text, methods):
    """Every reason why one requirement is not in testable form."""
    found = []
    if not ID.match(req_id):
        found.append("ID must look like SRS-AREA-nnn")
    plain = re.sub(r"`[^`]*`", "CODE", req_text)  # names in code spans are not prose
    plain = re.sub(r'"[^"]*"', "QUOTED", plain)  # nor are quoted values
    shalls = len(re.findall(r"\bshall\b", plain))
    if shalls != 1:
        found.append(f"says 'shall' {shalls} times; write one requirement per row")
    elif not SUBJECT.match(plain):
        found.append("must start with its subject: 'The <item> shall' or 'When ..., the <item> shall'")
    if re.search(r"\b(should|may|might|could|will)\b", plain):
        found.append("uses 'should', 'may', 'might', 'could' or 'will'; a requirement says 'shall'")
    for v in VAGUE_RE.findall(plain):
        found.append(f"vague word '{v}' cannot be verified")
    for m in NUMBER.finditer(plain):
        num, after = m.group(1), m.group(2)
        before = plain[: m.start()].split()
        if before and before[-1].lower() in NAMED_BY:
            continue  # part of a name: "IEEE 802.3", "schema version 1.3"
        unit = (after or "").strip(".").lower()
        if unit in UNITS or COUNT_NOUNS.match(unit) or unit.startswith(("%", "×", "x")):
            continue
        found.append(f"number {num} has no unit or counted noun")
    given = {m.strip() for m in methods.split(",") if m.strip()}
    if not given or not given <= METHODS:
        found.append("verification method must be one or more of T, A, I, D, M")
    return found


def lint(text):
    """(line, id, problem) for a whole document, including duplicate IDs."""
    out = []
    seen = {}
    for n, rid, rtext, _item, methods in requirements(text):
        if rid in seen:
            out.append((n, rid, f"duplicate ID (first on line {seen[rid]})"))
        seen.setdefault(rid, n)
        out.extend((n, rid, p) for p in problems(rid, rtext, methods))
    return out


def main(paths):
    total = 0
    bad = 0
    for p in paths:
        text = pathlib.Path(p).read_text()
        total += len(requirements(text))
        for n, rid, problem in lint(text):
            print(f"{p}:{n}: {rid}: {problem}")
            bad += 1
    print(f"{total} requirements, {bad} problem(s)")
    return 1 if bad or total == 0 else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
