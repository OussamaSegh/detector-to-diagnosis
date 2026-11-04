#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""How many lines clang-format would change if the whole tree were reformatted (Chapter 32).

For each style (the repository's .clang-format, and the same with Google's IncludeBlocks:
Regroup), formats every tracked C++ file in memory and counts the lines that differ, with
difflib. Nothing is written.

    format_cost.py [CLANG_FORMAT]      run from the repository root
"""
import difflib
import pathlib
import subprocess
import sys

TOOL = sys.argv[1] if len(sys.argv) > 1 else "clang-format-18"
BASE = pathlib.Path(".clang-format").read_text()
STYLES = {
    "repository (.clang-format, IncludeBlocks: Preserve)": BASE,
    "the same with IncludeBlocks: Regroup": BASE.replace("IncludeBlocks: Preserve",
                                                         "IncludeBlocks: Regroup"),
}


def style_arg(text):
    keys = [l for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    return "{" + ", ".join(keys) + "}"


files = subprocess.run(["git", "ls-files", "*.cpp", "*.hpp", "*.h", "*.cc"], check=True,
                       capture_output=True, text=True).stdout.split()
total = sum(len(pathlib.Path(f).read_text().splitlines()) for f in files)
version = subprocess.run([TOOL, "--version"], capture_output=True, text=True).stdout.strip()
print(f"# {version}; {len(files)} tracked C++ files, {total:,} lines\n")
print("| style | lines changed | files changed | share of lines |")
print("|---|---|---|---|")
for name, text in STYLES.items():
    lines = changed_files = 0
    for f in files:
        src = pathlib.Path(f).read_text()
        out = subprocess.run([TOOL, f"--style={style_arg(text)}", f"--assume-filename={f}"],
                             input=src, capture_output=True, text=True, check=True).stdout
        n = sum(1 for op in difflib.ndiff(src.splitlines(), out.splitlines()) if op[:1] == "-")
        lines += n
        changed_files += n > 0
    print(f"| {name} | {lines:,} | {changed_files} of {len(files)} | {100 * lines / total:.1f}% |")
