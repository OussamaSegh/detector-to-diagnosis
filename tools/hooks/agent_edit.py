#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The agent's hook after each edit (roadmap 2.2.0, Theme P2; CR-0036).

`.claude/settings.json` runs it after every Edit or Write. It reads the hook's JSON on stdin
(`tool_input.file_path`) and, when the file is a C++ file of the repository (`.cpp`, `.hpp`,
`.h`, `.cc`), formats in place, with clang-format and the repository's `.clang-format` (coding
standard, rule 1.4), the lines that differ from HEAD (`git diff -U0 HEAD`), so that the agent
reads back what the pre-commit hook and CI will accept (tools/check_format.py judges the same
lines). A file git does not track is new and formatted whole. The lines the edit did not touch
keep their authors' style (ADR 0027): a one-line edit of a file written before `.clang-format`
gives a one-line diff (roadmap 2.3.0, Theme H; MDQ-PR-102). Every other file is left as it is.
It never blocks: a missing clang-format is reported on stderr with exit status 1, which the
agent sees and goes on.

    agent_edit.py [--root DIR]      (the hook: JSON on stdin)
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

CPP = (".cpp", ".hpp", ".h", ".cc")


def formatter():
    return shutil.which("clang-format-18") or shutil.which("clang-format")


def target(event, root):
    """The repository's C++ file the event edited, or None."""
    path = event.get("tool_input", {}).get("file_path", "")
    if not path:
        return None
    p = pathlib.Path(path)
    p = (p if p.is_absolute() else root / p).resolve()
    if p.suffix not in CPP or not p.is_file() or root not in p.parents:
        return None
    return p


HUNK = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@.*")


def changed_lines(p, root):
    """The line ranges (first, last) of p that differ from HEAD; None when git does not track p,
    which is then new and formatted whole."""
    rel = str(p.relative_to(root))
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "--", rel], cwd=root,
                             capture_output=True, text=True)
    head = subprocess.run(["git", "cat-file", "-e", f"HEAD:{rel}"], cwd=root,
                          capture_output=True, text=True)
    if tracked.returncode != 0 or head.returncode != 0:
        return None
    diff = subprocess.run(["git", "diff", "-U0", "--no-color", "--no-ext-diff", "HEAD", "--", rel],
                          cwd=root, capture_output=True, text=True, check=True).stdout
    ranges = []
    for line in diff.splitlines():
        m = HUNK.fullmatch(line)
        if m:
            first, count = int(m.group(1)), int(m.group(2) or "1")
            if count > 0:
                ranges.append((first, first + count - 1))
    return ranges


def main(argv):
    root = pathlib.Path(argv[argv.index("--root") + 1] if "--root" in argv
                        else os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    p = target(event, root)
    if p is None:
        return 0
    tool = formatter()
    if tool is None:
        print("agent_edit.py: clang-format is not installed; the file is not formatted",
              file=sys.stderr)
        return 1
    try:
        ranges = changed_lines(p, root)
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"agent_edit.py: git could not diff {p.relative_to(root)}: {e}; "
              "the file is not formatted", file=sys.stderr)
        return 1
    if ranges == []:
        return 0
    lines = [f"--lines={a}:{b}" for a, b in ranges or []]
    r = subprocess.run([tool, "-i", "--style=file", *lines, str(p)], cwd=root,
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"agent_edit.py: clang-format failed on {p.relative_to(root)}: {r.stderr.strip()}",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
