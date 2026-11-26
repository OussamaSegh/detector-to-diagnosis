#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Evidence names no absolute path of the machine that wrote it (CAPA-0008).

The repository is public, and the privacy rule (CLAUDE.md) forbids an absolute path of the
machine in anything committed. Evidence is written by many programs (CTest, Google Benchmark,
the end-to-end run, the soak), each of which prints the directories it was given; two problem
reports corrected one generator each (MDQ-PR-101, MDQ-PR-103) and the rest kept writing them
(MDQ-PR-106). So the paths are removed where all evidence passes: when it is copied into the
repository, and a check over the whole of it keeps them out.

    tools/evidence_paths.py check ROOT            (every tracked file under measurements/, docs/)
    tools/evidence_paths.py fix DIR...            (rewrite the files under each DIR in place)

A path that names the machine or its user is one under a home directory (/home/NAME,
/Users/NAME, /root) or under an agent's scratch directory (/tmp/claude-N/...). `fix` writes
the home directory as `~` and the scratch directory as `$SCRATCH`, and keeps the rest of the
path, so the evidence still says which build or output a line came from. A temporary
directory such as /tmp/tmp.XXXX names nothing and is kept. Binary files are left alone.
Exit status of check: 0 if no file names such a path, 1 if one does.
"""
import pathlib
import re
import subprocess
import sys

AREAS = ("measurements", "docs")
SCRATCH = re.compile(r"/tmp/claude-\d+(?:/-[^/\s\"'`]+/[0-9a-f]{8}-[0-9a-f-]{27}/scratchpad)?(?![\w-])")
HOME = re.compile(r"(?<![\w.~$}/])(?:/home/[\w.-]+|/Users/[\w.-]+|/root)(?=/|\b)")


def clean(text):
    """The text with each machine path rewritten; the rest of each path kept."""
    return HOME.sub("~", SCRATCH.sub("$SCRATCH", text))


def found(text):
    return [m.group(0) for pattern in (SCRATCH, HOME) for m in pattern.finditer(text)]


def read(path):
    try:
        with open(path, encoding="utf-8", newline="") as f:
            return f.read()
    except (UnicodeDecodeError, IsADirectoryError):
        return None


def check(root):
    files = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--", *AREAS],
                           capture_output=True, text=True, check=True).stdout.split("\0")
    problems = []
    for rel in filter(None, files):
        text = read(root / rel)
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for p in found(line):
                problems.append(f"{rel}:{n}: names {p}, a path of the machine that wrote it")
    return problems


def fix(directory):
    changed = 0
    for path in sorted(p for p in pathlib.Path(directory).rglob("*") if p.is_file()):
        text = read(path)
        if text is not None and found(text):
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(clean(text))
            changed += 1
    return changed


def main(argv):
    if len(argv) >= 2 and argv[0] == "check" and len(argv) == 2:
        problems = check(pathlib.Path(argv[1]))
        for p in problems:
            print(p)
        print(f"evidence paths: {len(problems)} problem(s)")
        return 1 if problems else 0
    if len(argv) >= 2 and argv[0] == "fix":
        for d in argv[1:]:
            print(f"{d}: {fix(d)} file(s) rewritten")
        return 0
    print(__doc__.strip().splitlines()[0], file=sys.stderr)
    print("usage: evidence_paths.py check ROOT | fix DIR...", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
