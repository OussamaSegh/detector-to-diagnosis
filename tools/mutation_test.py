#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Mutation testing for one MiniDAQ source file (Chapter 18).

A mutant is a copy of the code with one small change a programmer could have made by mistake:
`<` for `<=`, `&&` for `||`, `+` for `-`, a condition negated. The tests "kill" a mutant if they
fail on it. A mutant that survives is either equivalent to the original (no input can tell them
apart) or a gap in the tests: a mistake the tests would let through. Coverage asks whether a
line ran; mutation testing asks whether the tests would notice if it were wrong.

    tools/mutation_test.py FILE --build build/debug --target minidaq_unit_tests \
        --test 'build/debug/minidaq/tests/minidaq_unit_tests --gtest_filter=CoincidenceSorter.*'
        [--lines 120-240] [--only ror,lcr] [--list] [--out report.txt]

For each mutant: write it over FILE, rebuild TARGET, run TEST with a timeout, put FILE back.
A mutant that does not compile is not counted. FILE is restored however the run ends, but run
it on a clean working tree and check `git status` afterwards.

Operators, applied only to code (comments and string literals are skipped):
  ror  relational: < <= > >= == != replaced by their neighbor or opposite
  lcr  logical: && and || swapped
  aor  arithmetic: binary + and - swapped
  neg  an `if (...)` condition negated
Binary operators are recognized by the spaces around them, as clang-format writes them, which
keeps template brackets, `<<`, `->` and `#include <...>` out.
"""
import argparse
import hashlib
import os
import pathlib
import re
import signal
import subprocess
import sys
import time

# [snippet:operators]
ROR = {"<": ["<=", ">="], "<=": ["<", ">"], ">": [">=", "<="], ">=": [">", "<"],
       "==": ["!="], "!=": ["=="]}
LCR = {"&&": ["||"], "||": ["&&"]}
AOR = {"+": ["-"], "-": ["+"]}
BINARY = re.compile(r"(?<=\s)(<=|>=|==|!=|&&|\|\||<|>|\+|-)(?=\s)")
IF = re.compile(r"\bif \((?!constexpr)")
# [/snippet:operators]


def code_mask(text):
    """For each character of a C++ file, True if it is code (not a comment or a literal)."""
    mask = [True] * len(text)
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
        elif text[i] == '"' or (text[i] == "'" and not (i > 0 and text[i - 1].isalnum())):  # not 1'000
            q = text[i]
            j = i + 1
            while j < n and text[j] != q:
                j += 2 if text[j] == "\\" else 1
            j += 1
        elif text[i] == "#" and (i == 0 or text[i - 1] == "\n"):
            j = text.find("\n", i)  # preprocessor lines: #include <...>
            j = n if j < 0 else j
        else:
            i += 1
            continue
        for k in range(i, min(j, n)):
            mask[k] = False
        i = j
    return mask


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def column_of(text, pos):
    return pos - text.rfind("\n", 0, pos)


def find_if_end(text, open_paren):
    depth = 0
    for k in range(open_paren, len(text)):
        if text[k] == "(":
            depth += 1
        elif text[k] == ")":
            depth -= 1
            if depth == 0:
                return k
    return -1


# [snippet:mutants]
def mutants(text, ops, lines=None):
    """Every mutant of `text` as (line, column, operator, description, mutated text)."""
    mask = code_mask(text)
    out = []
    for m in BINARY.finditer(text):
        if not mask[m.start()]:
            continue
        line = line_of(text, m.start())
        if lines and not lines[0] <= line <= lines[1]:
            continue
        tok = m.group(1)
        for op, table in (("ror", ROR), ("lcr", LCR), ("aor", AOR)):
            if op in ops and tok in table:
                for repl in table[tok]:
                    mutated = text[:m.start()] + repl + text[m.end():]
                    out.append((line, column_of(text, m.start()), op, f"{tok} -> {repl}", mutated))
    if "neg" in ops:
        for m in IF.finditer(text):
            if not mask[m.start()]:
                continue
            line = line_of(text, m.start())
            if lines and not lines[0] <= line <= lines[1]:
                continue
            open_paren = m.end() - 1
            close = find_if_end(text, open_paren)
            if close < 0:
                continue
            cond = text[open_paren + 1:close]
            if ";" in cond:  # if with an initializer: negating it is not a simple mutation
                continue
            mutated = text[:open_paren + 1] + "!(" + cond + ")" + text[close:]
            out.append((line, column_of(text, m.start()), "neg", "if (c) -> if (!(c))", mutated))
    out.sort(key=lambda x: x[:4])
    return out
# [/snippet:mutants]


def run(cmd, timeout):
    """(exit status, output) of cmd, or (None, "timeout"). A mutant can make a test loop forever, so on
    a timeout the whole process group is killed: killing only the shell would leave the test running."""
    p = subprocess.Popen(cmd, shell=isinstance(cmd, str), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, start_new_session=True)
    try:
        out, _ = p.communicate(timeout=timeout)
        return p.returncode, out
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        p.communicate()
        return None, "timeout"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("file", type=pathlib.Path)
    ap.add_argument("--build", required=True, help="build directory")
    ap.add_argument("--target", required=True, nargs="+", help="CMake targets that contain the tests")
    ap.add_argument("--test", required=True, help="command that runs the tests (exit 0 = pass)")
    ap.add_argument("--lines", help="only lines A-B")
    ap.add_argument("--only", default="ror,lcr,aor,neg", help="operators to apply")
    ap.add_argument("--timeout", type=float, default=120.0, help="seconds per test run")
    ap.add_argument("--list", action="store_true", help="list the mutants and stop")
    ap.add_argument("--out", type=pathlib.Path, help="write the report here too")
    args = ap.parse_args()

    original = args.file.read_text()
    lines = tuple(int(x) for x in args.lines.split("-")) if args.lines else None
    ms = mutants(original, set(args.only.split(",")), lines)
    if args.list:
        for i, (line, col, op, desc, _) in enumerate(ms, 1):
            print(f"{i:4} {args.file}:{line}:{col} {op} {desc}")
        return 0

    build = ["cmake", "--build", args.build, "--target", *args.target]
    code, log = run(build, None)
    if code != 0:
        sys.exit("mutation_test: the original does not build:\n" + log[-2000:])
    code, log = run(args.test, args.timeout)
    if code != 0:
        sys.exit("mutation_test: the tests fail on the original code:\n" + log[-2000:])

    report = [f"# {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {args.file}, {len(ms)} mutants",
              f"# source sha256 {hashlib.sha256(original.encode()).hexdigest()}",
              f"# test: {args.test}"]
    counts = {"killed": 0, "survived": 0, "timeout": 0, "invalid": 0}
    try:
        for i, (line, col, op, desc, mutated) in enumerate(ms, 1):
            args.file.write_text(mutated)
            code, _ = run(build, None)
            if code != 0:
                status = "invalid"  # does not compile: not a mutant the tests need to kill
            else:
                code, _ = run(args.test, args.timeout)
                status = "timeout" if code is None else "survived" if code == 0 else "killed"
            counts[status] += 1
            entry = f"{status:<8} {args.file}:{line}:{col} {op} {desc}"
            report.append(entry)
            print(f"[{i}/{len(ms)}] {entry}", flush=True)
    finally:
        args.file.write_text(original)
        run(build, None)

    valid = counts["killed"] + counts["survived"] + counts["timeout"]
    score = 100.0 * (counts["killed"] + counts["timeout"]) / valid if valid else 0.0
    report.append(f"# killed {counts['killed']}, timeout {counts['timeout']}, survived {counts['survived']}, "
                  f"invalid {counts['invalid']}; mutation score {score:.1f}%")
    print(report[-1])
    if args.out:
        args.out.write_text("\n".join(report) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
