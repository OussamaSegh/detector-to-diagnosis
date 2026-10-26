#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks that the version in VERSION says what the build is (Chapter 21, MDQ-PR-024).

The version goes into every program (minidaq_server's hello, its crash report, the list-mode
files' "software" field), so a build of main that says "0.3.0" claims to be the release. The
rules:

- X.Y.Z without a suffix only in the release commit, whose subject starts "Release X.Y.Z", or
  in a working tree that is changing VERSION for one;
- otherwise X.Y.Z-dev, later than the newest release recorded in docs/regulatory/releases/.

Usage: check_version.py ROOT. Exit status 0 if VERSION follows the rules. Outside a git checkout
(a source archive) only the second rule is checked.
"""
import pathlib
import re
import subprocess
import sys

RELEASES = pathlib.Path("docs/regulatory/releases")


def key(v):
    return tuple(int(x) for x in v.split("."))


# [snippet:problems]
def problems(version, subject, released, changing):
    """version: VERSION's text; subject: the commit's subject, None outside git; released: the
    versions with a release record; changing: True if the working tree changes VERSION."""
    m = re.fullmatch(r"(\d+\.\d+\.\d+)(-dev)?", version)
    if not m:
        return [f"VERSION '{version}' is not X.Y.Z or X.Y.Z-dev"]
    number, dev = m.group(1), m.group(2)
    newest = max(released, key=key, default=None)
    if dev:
        if newest and key(number) <= key(newest):
            return [f"VERSION {version} is not later than the newest release, {newest}: "
                    f"the commit after a release sets the next -dev version"]
        return []
    if subject is None or changing or subject.startswith(f"Release {number}"):
        return []
    return [f"VERSION says {number}, a release, but this commit is not its release commit "
            f"('{subject}'): the commit after a release sets the next -dev version"]
# [/snippet:problems]


def git(root, *args):
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def main(root):
    version = (root / "VERSION").read_text().strip()
    released = [p.stem for p in (root / RELEASES).glob("*.md") if re.fullmatch(r"\d+\.\d+\.\d+", p.stem)]
    code, subject = git(root, "log", "-1", "--format=%s")
    changing = git(root, "diff", "--quiet", "HEAD", "--", "VERSION")[0] == 1 if code == 0 else False
    errors = problems(version, subject if code == 0 else None, released, changing)
    for e in errors:
        print(e)
    print(f"version {version}: " + ("ok" if not errors else f"{len(errors)} problem(s)"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(pathlib.Path(sys.argv[1]).resolve()))
