# SPDX-License-Identifier: MIT
"""Exercise 20.3 solution: a self-test for a gate.

A gate is a function check(root) -> list of problems. The self-test makes a correct tree, runs
the gate on it (the control: it must pass), plants one fault, runs the gate again and decides
whether the gate caught the fault for the planted reason.
"""
from __future__ import annotations

import dataclasses
import pathlib
import re
import tempfile
from typing import Callable

GOOD = {
    "src/a.cpp": "// SPDX-License-Identifier: MIT\n#include \"b.hpp\"\nint a() { return b(); }  // TODO(#12): inline\n",
    "src/b.hpp": "// SPDX-License-Identifier: MIT\n#pragma once\ninline int b() { return 1; }\n",
}


def make_tree(root: pathlib.Path) -> pathlib.Path:
    """A tree the gate must accept."""
    for rel, text in GOOD.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    return root


@dataclasses.dataclass
class Fault:
    name: str
    plant: Callable[[pathlib.Path], None]  # changes a correct tree
    expect: str  # pattern one of the gate's problems must match


def _edit(rel: str, old: str, new: str) -> Callable[[pathlib.Path], None]:
    def plant(root: pathlib.Path) -> None:
        text = (root / rel).read_text()
        assert text.count(old) == 1, f"{rel}: the fault's anchor must occur once"
        (root / rel).write_text(text.replace(old, new))
    return plant


# [snippet:faults]
FAULTS: list[Fault] = [
    Fault("cpp without header", _edit("src/a.cpp", "// SPDX-License-Identifier: MIT\n", ""),
          r"^src/a\.cpp:1: no SPDX"),
    Fault("hpp without header", _edit("src/b.hpp", "// SPDX-License-Identifier: MIT\n", ""),
          r"^src/b\.hpp:1: no SPDX"),
    Fault("header on line 3",
          _edit("src/b.hpp", "// SPDX-License-Identifier: MIT\n#pragma once\n",
                "#pragma once\n\n// SPDX-License-Identifier: MIT\n"),
          r"^src/b\.hpp:1: no SPDX"),
    Fault("TODO without issue", _edit("src/a.cpp", "TODO(#12)", "TODO"),
          r"^src/a\.cpp:3: TODO without"),
    Fault("TODO with a name, not an issue",
          _edit("src/b.hpp", "return 1; }", "return 1; }  // TODO(anna)"),
          r"^src/b\.hpp:3: TODO without"),
]
# [/snippet:faults]


def verdict(clean: list[str], problems: list[str], expect: str) -> str:
    """'caught', 'NOT CAUGHT', 'failed for another reason' or 'gate fails on correct code'."""
    if clean:
        return "gate fails on correct code"
    if not problems:
        return "NOT CAUGHT"
    if not any(re.search(expect, p) for p in problems):
        return "failed for another reason"
    return "caught"


def run(check: Callable[[pathlib.Path], list[str]], faults: list[Fault] = FAULTS) -> dict[str, str]:
    """The verdict for each fault, each in a fresh tree."""
    out = {}
    for fault in faults:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_tree(pathlib.Path(tmp))
            clean = check(root)
            fault.plant(root)
            out[fault.name] = verdict(clean, check(root), fault.expect)
    return out
