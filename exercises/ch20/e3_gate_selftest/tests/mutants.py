# SPDX-License-Identifier: MIT
"""Broken versions of the gate. A self-test that reports every fault as caught with one of these
has not tested the gate: each must leave at least one fault 'NOT CAUGHT' or worse."""
import pathlib
import re

import gate


def always_passes(root):
    return []


def always_fails(root):
    return ["src/a.cpp:1: no SPDX-License-Identifier in the first two lines"]


def ignores_headers(root):
    return [p for p in gate.check(root) if ".hpp:" not in p]


def header_anywhere(root):
    problems = [p for p in gate.check(root) if "SPDX" not in p]
    for f in sorted(pathlib.Path(root, "src").rglob("*")):
        if f.suffix in (".cpp", ".hpp") and "SPDX-License-Identifier:" not in f.read_text():
            problems.append(f"{f.relative_to(root).as_posix()}:1: no SPDX-License-Identifier in the first two lines")
    return problems


def vague(root):
    return ["something is wrong"] if gate.check(root) else []


def todo_blind(root):
    return [p for p in gate.check(root) if "TODO" not in p]


def any_number_will_do(root):
    loose = re.compile(r"\bTODO\b(?!\(#?\w*\))")
    out = [p for p in gate.check(root) if "TODO" not in p]
    for f in sorted(pathlib.Path(root, "src").rglob("*")):
        if f.suffix in (".cpp", ".hpp"):
            for n, line in enumerate(f.read_text().splitlines(), 1):
                if loose.search(line):
                    out.append(f"{f.relative_to(root).as_posix()}:{n}: TODO without an issue number")
    return out


MUTANTS = [always_passes, always_fails, ignores_headers, header_anywhere, vague, todo_blind, any_number_will_do]
