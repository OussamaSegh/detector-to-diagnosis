#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Sets the project's version in every place that carries it (roadmap 2.0.0, Theme D).

After release 0.3.0, 1.0.0 and others, a version was changed in VERSION but not in the Python
packages, or not at all after the tag, and CI turned red on docs.version or analysis.pytest.
This tool makes the change in one step:

- VERSION;
- analysis/pyproject.toml, minidaq_analysis.__version__ and recon/python/pyproject.toml, in
  the Python spelling (1.2.0-dev is 1.2.0.dev0);
- CHANGELOG.md gets an empty "## [Unreleased]" section if it has none.

Usage:
  post_release.py ROOT              after a release: the next patch -dev of the newest release
                                    record in docs/regulatory/releases/ (1.1.0 -> 1.1.1-dev)
  post_release.py ROOT VERSION      any version: 1.2.0-dev to start a minor version, 1.2.0 in
                                    the release commit
  post_release.py ROOT --check      only report places that disagree with VERSION

It never writes a SOUP review: a new minor version needs a real one (docs.soup fails until it is
dated for that version), so the tool only says so. Exit status 0 on success, 1 on a problem.
"""
import pathlib
import re
import sys

PLACES = [  # (file, pattern whose group 1 is the version)
    ("analysis/pyproject.toml", r'(?m)^version = "([^"]+)"'),
    ("analysis/src/minidaq_analysis/__init__.py", r'(?m)^__version__ = "([^"]+)"'),
    ("recon/python/pyproject.toml", r'(?m)^version = "([^"]+)"'),
]
VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)(-dev)?")


def key(v):
    return tuple(int(x) for x in v.split("."))


def python_version(version):
    """1.2.0-dev -> 1.2.0.dev0 (PEP 440); 1.2.0 -> 1.2.0."""
    m = VERSION_RE.fullmatch(version)
    if not m:
        raise ValueError(f"'{version}' is not X.Y.Z or X.Y.Z-dev")
    return f"{m.group(1)}.{m.group(2)}.{m.group(3)}" + (".dev0" if m.group(4) else "")


def next_dev(released):
    """The version after the newest release: its patch + 1, as -dev."""
    if not released:
        raise ValueError("no release record in docs/regulatory/releases/")
    major, minor, patch = key(max(released, key=key))
    return f"{major}.{minor}.{patch + 1}-dev"


def released_versions(root):
    return [p.stem for p in (root / "docs/regulatory/releases").glob("*.md")
            if re.fullmatch(r"\d+\.\d+\.\d+", p.stem)]


def disagreements(root, version):
    """[(file, found)] for each place whose version is not VERSION's."""
    want = python_version(version)
    out = []
    for rel, pattern in PLACES:
        m = re.search(pattern, (root / rel).read_text())
        found = m.group(1) if m else None
        if found != want:
            out.append((rel, found))
    return out


def with_unreleased(changelog):
    """CHANGELOG text with an empty [Unreleased] section above the first release section."""
    if re.search(r"(?m)^## \[Unreleased\]", changelog):
        return changelog
    m = re.search(r"(?m)^## \[", changelog)
    if not m:
        return changelog.rstrip("\n") + "\n\n## [Unreleased]\n"
    return changelog[:m.start()] + "## [Unreleased]\n\n" + changelog[m.start():]


def set_version(root, version):
    """Writes version everywhere; returns the notes for the person running it."""
    python_version(version)  # refuses a malformed version before anything is written
    old = (root / "VERSION").read_text().strip()
    (root / "VERSION").write_text(version + "\n")
    for rel, pattern in PLACES:
        path = root / rel
        text = path.read_text()
        m = re.search(pattern, text)
        if not m:
            raise ValueError(f"{rel}: no version line")
        path.write_text(text[:m.start(1)] + python_version(version) + text[m.end(1):])
    changelog = root / "CHANGELOG.md"
    changelog.write_text(with_unreleased(changelog.read_text()))
    notes = [f"VERSION {old} -> {version}; Python packages {python_version(version)}"]
    if VERSION_RE.fullmatch(old) and key(VERSION_RE.fullmatch(old).expand(r"\1.\2.\3"))[:2] != \
            key(VERSION_RE.fullmatch(version).expand(r"\1.\2.\3"))[:2]:
        notes.append("new minor version: docs/regulatory/soup-list.md needs a dated known-anomaly "
                     "review for it (docs.soup fails until then), and the internal audit is due "
                     "before its release checks (SDP section 8, item 9)")
    notes.append("re-run cmake in each build directory: cmake.consumer reads VERSION at configure time")
    return notes


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    root = pathlib.Path(argv[1]).resolve()
    arg = argv[2] if len(argv) > 2 else None
    try:
        if arg == "--check":
            version = (root / "VERSION").read_text().strip()
            bad = disagreements(root, version)
            for rel, found in bad:
                print(f"{rel}: {found}, VERSION {version} needs {python_version(version)}")
            print(f"version {version}: " + ("ok" if not bad else f"{len(bad)} place(s) disagree"))
            return 1 if bad else 0
        version = arg or next_dev(released_versions(root))
        for note in set_version(root, version):
            print(note)
    except ValueError as e:
        print(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
