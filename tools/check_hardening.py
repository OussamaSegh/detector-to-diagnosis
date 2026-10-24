#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks that ELF executables carry the hardening that the build asked for
(Chapter 7, ADR 0008). A flag in a CMake file is a wish; this reads the binary.

Usage: tools/check_hardening.py BINARY...     exit status 0: all hardened, 1: not

Required for every binary: position-independent executable, full RELRO
(read-only relocations, bound at load time), non-executable stack, and on
x86-64 the CET properties (indirect-branch tracking and shadow stack).
Reported, not required: a stack canary and fortified calls, because a program
without arrays on the stack or without fortifiable calls legitimately has none.
"""
import re
import subprocess
import sys


def readelf(*args):
    return subprocess.run(["readelf", "-W", *args], capture_output=True, text=True, check=True).stdout


# [snippet:checks]
def properties(path):
    header = readelf("-h", path)
    dynamic = readelf("-d", path)
    segments = readelf("-l", path)
    notes = readelf("-n", path)
    symbols = readelf("--dyn-syms", path)
    stack = re.search(r"GNU_STACK\s+(?:\S+\s+){5}(\S+)", segments)
    props = {
        "pie": "DYN" in re.search(r"Type:\s+(\S+)", header).group(1) and "PIE" in dynamic,
        "relro": "GNU_RELRO" in segments,
        "bind_now": "BIND_NOW" in dynamic or re.search(r"FLAGS_1.*\bNOW\b", dynamic) is not None,
        "nx_stack": stack is not None and "E" not in stack.group(1),
        "canary": "__stack_chk_fail" in symbols,
        "fortify": re.search(r"__\w+_chk\b", symbols.replace("__stack_chk_fail", "")) is not None,
    }
    if "X86-64" in header or "x86-64" in header:
        props["cet_ibt"] = re.search(r"x86 feature:.*\bIBT\b", notes) is not None
        props["cet_shstk"] = re.search(r"x86 feature:.*\bSHSTK\b", notes) is not None
    return props
# [/snippet:checks]


REQUIRED = ("pie", "relro", "bind_now", "nx_stack", "cet_ibt", "cet_shstk")


def main(paths):
    if not paths:
        print(__doc__)
        return 2
    failed = False
    for path in paths:
        props = properties(path)
        missing = [k for k in REQUIRED if k in props and not props[k]]
        line = "  ".join(f"{k}={'yes' if v else 'no'}" for k, v in props.items())
        print(f"{'FAIL' if missing else 'ok  '} {path}: {line}")
        failed = failed or bool(missing)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
