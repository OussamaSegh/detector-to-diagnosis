#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reports the known vulnerabilities of every package pinned in a Python lock file (SOUP list,
section 2; the SOUP review of release 0.7.0).

The vulnerability scan of CI matches the SBOM, which lists the shipped software only. The tools'
Python packages (analysis/requirements.lock) are pinned too, and a pin does not age well: at the
review for 0.7.0, two of them had published vulnerabilities that nothing reported. This tool asks
the Python Package Index, whose JSON interface lists the advisories (from the OSV database) that
affect each released version.

    lock_audit.py LOCKFILE            every pin; exit 1 if any has a known vulnerability
    lock_audit.py LOCKFILE --json     the same as one JSON object, for a record

Exit status 0 if no pinned version has a known vulnerability, 1 if one has, 2 if the index cannot
be read (an audit that did not run is not a clean audit).
"""
import json
import re
import sys
import urllib.error
import urllib.request

PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;\\#]+)")
INDEX = "https://pypi.org/pypi/{name}/{version}/json"


def pins(text):
    """(name, version) of every exact pin in a requirements file, in its order."""
    return [m.groups() for line in text.splitlines() if (m := PIN.match(line.strip()))]


def fetch_from_index(name, version):
    """The index's JSON record of one released version."""
    url = INDEX.format(name=name, version=version)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def audit(text, fetch=fetch_from_index):
    """{name==version: [(advisory id, fixed in)]} for every pin; raises if a record lacks the
    vulnerabilities field, since an empty answer must mean "none known", not "not asked"."""
    found = {}
    for name, version in pins(text):
        record = fetch(name, version)
        if "vulnerabilities" not in record:
            raise RuntimeError(f"{name}=={version}: the index gave no vulnerability field")
        found[f"{name}=={version}"] = [
            (v.get("id", "?"), ", ".join(v.get("fixed_in") or []) or "no fix")
            for v in record["vulnerabilities"]
        ]
    return found


def main(argv):
    if len(argv) not in (2, 3) or (len(argv) == 3 and argv[2] != "--json"):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        with open(argv[1], encoding="utf-8") as f:
            found = audit(f.read())
    except (OSError, urllib.error.URLError, RuntimeError, ValueError) as e:
        print(f"lock audit could not run: {e}", file=sys.stderr)
        return 2
    affected = {k: v for k, v in found.items() if v}
    if len(argv) == 3:
        print(json.dumps({"lock": argv[1], "packages": len(found), "affected": affected}, indent=2))
    else:
        for pin, advisories in affected.items():
            fixes = sorted({fix for _, fix in advisories})
            print(f"{pin}: {len(advisories)} known vulnerabilities, fixed in {'; '.join(fixes)}")
            for advisory, fix in advisories:
                print(f"  {advisory} (fixed in {fix})")
        print(f"lock audit: {len(found)} packages, {len(affected)} with known vulnerabilities")
    return 1 if affected else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
