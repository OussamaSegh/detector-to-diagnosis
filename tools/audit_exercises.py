#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks the record of each audit exercise (roadmap 3.0.0, Theme Q; TL-70).

An audit exercise, marked (A) in the book, gives the reader a recorded agent change and asks
for the tests that reject it and accept the corrected change. Its directory is
exercises/chNN/audit-NAME:

    README.md               the goal and the acceptance
    change/SPEC.md          the task as the agent was given it
    change/TRANSCRIPT.md    the session, condensed
    change/agent.patch      the agent's diff, from change/before/ to tests/agent/
    change/before/          the files before the change
    tests/agent/            the files as the agent left them (what the tests run)
    tests/reference/        the corrected change
    tests/defects/          (Python) the corrected change with one defect each
    starter/  solution/     the reader's tests; solution/REPORT.md names the problem reports

The check makes sure the record is what it says it is:

- every part above exists;
- applying change/agent.patch to change/before/ gives exactly the files of tests/agent/, so
  the patch the reader studies is the change the tests run;
- every problem report the solution's report names exists in
  docs/regulatory/problem-reports.json, and it names at least one: the defects come from
  MiniDAQ's history, not from invention (the README does not name them: that would give the
  answer away);
- the chapter names the exercise's directory in an exercise marked (A).

    audit_exercises.py ROOT [DIR...]     (default: every exercises/ch*/audit-*)

Exit status 0 if every record is complete, 1 if not.
"""
import json
import pathlib
import re
import sys

PARTS = ("README.md", "change/SPEC.md", "change/TRANSCRIPT.md", "change/agent.patch",
         "change/before", "tests/agent", "tests/reference", "starter", "solution",
         "solution/REPORT.md")
PR = re.compile(r"MDQ-PR-\d{3}")
HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class PatchError(Exception):
    pass


def parse_patch(text):
    """[(path, [(old_start, [lines with their ' ', '-' or '+'])])] of a unified diff."""
    files, hunks, path = [], None, None
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("--- "):
            if i + 1 >= len(lines) or not lines[i + 1].startswith("+++ "):
                raise PatchError(f"line {i + 1}: '---' without '+++'")
            path = lines[i + 1][4:].split("\t")[0].strip()
            path = path[2:] if path.startswith("b/") else path
            hunks = []
            files.append((path, hunks))
            i += 2
            continue
        m = HUNK.match(line)
        if m:
            if hunks is None:
                raise PatchError(f"line {i + 1}: a hunk before any file")
            old_len = int(m.group(2)) if m.group(2) is not None else 1
            new_len = int(m.group(4)) if m.group(4) is not None else 1
            body, i = [], i + 1
            while (old_len > 0 or new_len > 0) and i < len(lines):
                b = lines[i]
                if b.startswith("\\"):  # "\ No newline at end of file"
                    i += 1
                    continue
                if b[:1] not in (" ", "-", "+"):
                    raise PatchError(f"line {i + 1}: not a line of a hunk")
                old_len -= b[0] in " -"
                new_len -= b[0] in " +"
                body.append(b)
                i += 1
            if old_len or new_len:
                raise PatchError(f"a hunk of {path} is shorter than its header says")
            hunks.append((int(m.group(1)), body))
            continue
        i += 1
    return files


def apply(old, hunks):
    """The text of `old` with the hunks applied; the context must match exactly."""
    src = old.splitlines(keepends=True)
    out, pos = [], 0
    for start, body in hunks:
        at = max(start - 1, 0)
        if at < pos:
            raise PatchError("hunks overlap or are out of order")
        out += src[pos:at]
        pos = at
        for b in body:
            kind, text = b[0], b[1:]
            if kind in " -":
                if pos >= len(src) or src[pos] != text:
                    raise PatchError(f"context does not match at line {pos + 1}")
                pos += 1
            if kind in " +":
                out.append(text)
    return "".join(out + src[pos:])


def chapter_file(root, chapter):
    for f in sorted((root / "book/src").glob(f"part*/{chapter}-*.md")):
        return f
    return None


def check(root, d):
    errors = []
    rel = d.relative_to(root).as_posix()
    for p in PARTS:
        if not (d / p).exists():
            errors.append(f"{rel}: {p} is missing")
    if errors:
        return errors
    try:
        for path, hunks in parse_patch((d / "change/agent.patch").read_text()):
            before = d / "change/before" / path
            got = apply(before.read_text() if before.exists() else "", hunks)
            agent = d / "tests/agent" / path
            if not agent.exists():
                errors.append(f"{rel}: the patch changes {path}, which tests/agent/ does not have")
            elif agent.read_text() != got:
                errors.append(f"{rel}: change/agent.patch applied to change/before/ is not "
                              f"tests/agent/{path}")
    except PatchError as e:
        errors.append(f"{rel}: change/agent.patch does not apply: {e}")
    named = set(PR.findall((d / "solution/REPORT.md").read_text()))
    known = {r["id"] for r in json.loads((root / "docs/regulatory/problem-reports.json")
                                         .read_text())["reports"]}
    if not named:
        errors.append(f"{rel}: solution/REPORT.md names no problem report (MDQ-PR-nnn) as the "
                      "defects' source")
    errors += [f"{rel}: solution/REPORT.md names {p}, which is not a problem report" for p in sorted(named - known)]
    book = chapter_file(root, d.parent.name)
    if book is None:
        errors.append(f"{rel}: no chapter file for {d.parent.name}")
    elif not re.search(r"\*\*Exercise \d+\.\d+ \(A\)[^\n]*(?:\n[^\n]+)*?" + re.escape(rel), book.read_text()):
        errors.append(f"{rel}: {book.relative_to(root).as_posix()} has no exercise marked (A) "
                      "that names this directory")
    return errors


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    root = pathlib.Path(argv[0]).resolve()
    dirs = [pathlib.Path(a).resolve() if pathlib.Path(a).is_absolute() else (root / a).resolve()
            for a in argv[1:]] or sorted(root.glob("exercises/ch*/audit-*"))
    errors = [e for d in dirs for e in check(root, d)]
    for e in errors:
        print(e)
    print(f"audit exercises: {len(dirs)} checked, " + ("ok" if not errors else f"{len(errors)} problem(s)"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
