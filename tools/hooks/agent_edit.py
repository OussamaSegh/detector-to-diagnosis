#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The agent's hook after each edit (roadmap 2.2.0, Theme P2; CR-0036).

`.claude/settings.json` runs it after every Edit or Write. It reads the hook's JSON on stdin
(`tool_input.file_path`) and, when the file is a C++ file of the repository (`.cpp`, `.hpp`,
`.h`, `.cc`), formats it in place with clang-format and the repository's `.clang-format`
(coding standard, rule 1.4), so that the agent reads back what the pre-commit hook and CI will
accept. Every other file is left as it is. It never blocks: a missing clang-format is reported
on stderr with exit status 1, which the agent sees and goes on.

    agent_edit.py [--root DIR]      (the hook: JSON on stdin)
"""
import json
import os
import pathlib
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
    r = subprocess.run([tool, "-i", "--style=file", str(p)], cwd=root, capture_output=True,
                       text=True)
    if r.returncode != 0:
        print(f"agent_edit.py: clang-format failed on {p.relative_to(root)}: {r.stderr.strip()}",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
