# SPDX-License-Identifier: MIT
"""Exercise 20.3 starter: a self-test for a gate.

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


FAULTS: list[Fault] = [
    # TODO: one fault per way the gate can be wrong. Look at what the gate promises, file type by
    # file type and rule by rule, and at where its rules end.
]


def verdict(clean: list[str], problems: list[str], expect: str) -> str:
    """'caught', 'NOT CAUGHT', 'failed for another reason' or 'gate fails on correct code'."""
    raise NotImplementedError  # TODO


def run(check: Callable[[pathlib.Path], list[str]], faults: list[Fault] = FAULTS) -> dict[str, str]:
    """The verdict for each fault, each in a fresh tree."""
    raise NotImplementedError  # TODO
