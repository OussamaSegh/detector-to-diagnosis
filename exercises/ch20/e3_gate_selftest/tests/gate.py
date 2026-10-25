# SPDX-License-Identifier: MIT
"""The gate under study in Exercise 20.3 (given, do not change): a source-file check.

Every C++ file below ROOT/src (.cpp and .hpp) must
1. carry an "SPDX-License-Identifier:" comment in its first two lines, and
2. write each TODO with the issue that tracks it, as TODO(#123).

check(root) returns one problem per violation, as "<path>:<line>: <what>"; [] means pass.
"""
import pathlib
import re

TODO = re.compile(r"\bTODO\b(?!\(#\d+\))")


def check(root):
    problems = []
    for f in sorted(pathlib.Path(root, "src").rglob("*")):
        if f.suffix not in (".cpp", ".hpp") or not f.is_file():
            continue
        lines = f.read_text().splitlines()
        rel = f.relative_to(root).as_posix()
        if not any("SPDX-License-Identifier:" in line for line in lines[:2]):
            problems.append(f"{rel}:1: no SPDX-License-Identifier in the first two lines")
        for n, line in enumerate(lines, 1):
            if TODO.search(line):
                problems.append(f"{rel}:{n}: TODO without an issue number")
    return problems
