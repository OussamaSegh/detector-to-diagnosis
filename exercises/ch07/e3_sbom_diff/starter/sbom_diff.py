# SPDX-License-Identifier: MIT
"""Exercise 7.3: compare two CycloneDX SBOMs, as a release reviewer would:
which components were added or removed, and which changed version, license,
scope or hash.

Usage: python3 sbom_diff.py OLD.cdx.json NEW.cdx.json
Exit status: 0 no change, 1 changes that need a SOUP review, 2 usage error.
"""
import json
import sys


def diff(old, new):
    """Returns a sorted list of (kind, component name, detail) tuples.

    kind is one of "added", "removed", "version", "license", "scope", "hash".
    A component is identified by group and name ("google/googletest"): its
    bom-ref contains the version, so it changes on every upgrade.
    """
    # TODO
    return []


def main(argv):
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[1]) as f1, open(argv[2]) as f2:
        changes = diff(json.load(f1), json.load(f2))
    for kind, name, detail in changes:
        print(f"{kind:8} {name}: {detail}")
    return 1 if changes else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
