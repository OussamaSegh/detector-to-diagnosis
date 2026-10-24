#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise 7.1 acceptance: clang-tidy with the repository's .clang-tidy
reports nothing for the variant's sources.

Usage: tidy_clean.py starter|solution     exit 0 clean, 1 findings, 77 no clang-tidy
"""
import os
import pathlib
import shutil
import subprocess
import sys

exercise = pathlib.Path(__file__).resolve().parent.parent
repo = exercise.parents[2]
variant = exercise / sys.argv[1]
tidy = shutil.which(os.environ.get("CLANG_TIDY", "clang-tidy-18")) or shutil.which("clang-tidy")
if tidy is None:
    print("clang-tidy not found: skipped")
    sys.exit(77)
# clang-tidy finds the repository's .clang-tidy by walking up from the source file.
r = subprocess.run([tidy, "--quiet", f"--header-filter={variant}/.*", str(variant / "legacy_tool.cpp"), "--",
                    "-std=c++20", f"-I{variant}", f"-I{repo / 'minidaq/include'}"],
                   capture_output=True, text=True)
findings = sorted({line for line in r.stdout.splitlines() if "warning:" in line or "error:" in line})
for f in findings:
    print(f.replace(str(repo) + "/", ""))
print(f"{len(findings)} finding(s) in {sys.argv[1]}")
sys.exit(1 if findings or r.returncode != 0 else 0)
