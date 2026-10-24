# SPDX-License-Identifier: MIT
"""Exercise 7.3 solution: compare two CycloneDX SBOMs, as a release reviewer
would: which components were added or removed, and which changed version,
license, scope or hash.

Usage: python3 sbom_diff.py OLD.cdx.json NEW.cdx.json
Exit status: 0 no change, 1 changes that need a SOUP review, 2 usage error.
"""
import json
import sys


def key(c):
    """A component's identity across versions: group and name, not bom-ref (which contains the version)."""
    return (c.get("group", ""), c["name"])


def licenses(c):
    out = set()
    for entry in c.get("licenses", []):
        lic = entry.get("license", {})
        out.add(lic.get("id") or lic.get("name") or entry.get("expression", "?"))
    return sorted(out)


def hashes(c):
    return sorted((h["alg"], h["content"]) for h in c.get("hashes", []))


# [snippet:diff]
def diff(old, new):
    """Returns a list of (kind, component name, detail) tuples, sorted."""
    a = {key(c): c for c in old.get("components", [])}
    b = {key(c): c for c in new.get("components", [])}
    changes = []
    for k in sorted(b.keys() - a.keys()):
        changes.append(("added", "/".join(filter(None, k)), b[k].get("version", "")))
    for k in sorted(a.keys() - b.keys()):
        changes.append(("removed", "/".join(filter(None, k)), a[k].get("version", "")))
    for k in sorted(a.keys() & b.keys()):
        name = "/".join(filter(None, k))
        before, after = a[k], b[k]
        for field, get in (("version", lambda c: c.get("version", "")), ("license", licenses),
                           ("scope", lambda c: c.get("scope", "required")), ("hash", hashes)):
            if get(before) != get(after):
                changes.append((field, name, f"{get(before)} -> {get(after)}"))
    return sorted(changes)
# [/snippet:diff]


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
