#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks the formatting of the C++ lines a change touches (Chapter 32, SRS-BLD-004).

Runs `git clang-format --diff` with the repository's .clang-format on the lines that differ, and
fails if clang-format would change any of them. Lines the change does not touch are not checked:
the code written before .clang-format existed is formatted as it is edited (ADR 0027).

    check_format.py --staged          the lines staged for the next commit (the pre-commit hook)
    check_format.py BASE [HEAD]       the lines that differ between two commits (CI: the push or
                                      the pull request), or between BASE and the working tree

Exit status 0 if every touched line is formatted, 1 if not (the diff that would fix them is
printed: apply it with `git clang-format` and the same arguments), 2 if the check cannot run.
"""
import shutil
import subprocess
import sys

EXTENSIONS = "c,cc,cpp,cxx,h,hh,hpp,hxx"
# Files under these paths are someone else's code, or are written to show a style that is not
# ours; their formatting is not checked.
EXCLUDED = ("third_party/", "tools/sbom/schemas/")
CLEAN = ("no modified files to format", "clang-format did not modify any files")


def changed_files(args):
    """The C++ files the diff of these arguments touches, outside the excluded paths."""
    if args == ["--staged"]:
        cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
    else:
        cmd = ["git", "diff", "--name-only", "--diff-filter=ACMR", *args]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.split()
    ext = tuple("." + e for e in EXTENSIONS.split(","))
    return [f for f in out if f.endswith(ext) and not f.startswith(EXCLUDED)]


def check(args, binary="clang-format"):
    """(ok, text): whether the touched lines are formatted, and the diff that would fix them."""
    files = changed_files(args)
    if not files:
        return True, ""
    cmd = ["git", "clang-format", "--binary", binary, "--extensions", EXTENSIONS, "--diff"]
    cmd += args + ["--", *files]
    r = subprocess.run(cmd, capture_output=True, text=True)
    text = r.stdout.strip()
    if r.returncode not in (0, 1) or r.stderr.strip():
        raise RuntimeError(f"git clang-format failed ({r.returncode}): {r.stderr.strip()}")
    if not text or text in CLEAN:
        return True, ""
    return False, text


def main(argv):
    args = argv[1:]
    if not args or args[0] in ("-h", "--help") or len(args) > 2:
        print(__doc__, file=sys.stderr)
        return 2
    binary = shutil.which("clang-format")
    if binary is None or shutil.which("git-clang-format") is None:
        print("clang-format and git-clang-format are needed (tool TL-37)", file=sys.stderr)
        return 2
    try:
        ok, text = check(args, binary)
    except (RuntimeError, subprocess.CalledProcessError) as e:
        print(e, file=sys.stderr)
        return 2
    if ok:
        print("format: every touched line is formatted")
        return 0
    print(text)
    print(f"format: touched lines need formatting; run: git clang-format {' '.join(args)}",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
