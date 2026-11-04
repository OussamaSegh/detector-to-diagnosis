#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks CMakePresets.json (Chapter 32, SRS-BLD-002).

Every configure preset that is not hidden must have a build preset, a test preset and a workflow
preset of the same name, and the workflow must configure, build and test with those three, in
that order: then `cmake --workflow --preset NAME` is the whole gate of one configuration, the
same on a laptop and in CI. Every preset that the CI workflow's matrix names must exist.

Usage: check_presets.py ROOT. Exit status 0 if the presets are consistent.
"""
import json
import pathlib
import re
import sys


def check(presets, ci_text):
    errors = []
    configure = [p["name"] for p in presets["configurePresets"] if not p.get("hidden")]
    for kind in ("buildPresets", "testPresets", "workflowPresets"):
        have = {p["name"] for p in presets.get(kind, []) if not p.get("hidden")}
        for name in configure:
            if name not in have:
                errors.append(f"configure preset {name} has no entry in {kind}")
    by_kind = {k: {p["name"]: p for p in presets.get(k, [])} for k in ("buildPresets", "testPresets")}
    for w in presets.get("workflowPresets", []):
        steps = [(s["type"], s["name"]) for s in w.get("steps", [])]
        want = [("configure", w["name"]), ("build", w["name"]), ("test", w["name"])]
        if steps != want:
            errors.append(f"workflow {w['name']}: steps {steps}, expected {want}")
        for kind, key in (("buildPresets", "build"), ("testPresets", "test")):
            p = by_kind[kind].get(w["name"])
            if p is not None and p.get("configurePreset") != w["name"]:
                errors.append(f"{key} preset {w['name']} configures {p.get('configurePreset')}")
    for m in re.finditer(r"preset:\s*\[([^\]]*)\]", ci_text):
        for name in (x.strip() for x in m.group(1).split(",")):
            if name and name not in configure:
                errors.append(f"the CI matrix names preset {name}, which does not exist")
    return errors


def main(argv):
    root = pathlib.Path(argv[1])
    presets = json.loads((root / "CMakePresets.json").read_text())
    ci = (root / ".github/workflows/ci.yml").read_text()
    errors = check(presets, ci)
    for e in errors:
        print(e, file=sys.stderr)
    n = len([p for p in presets["configurePresets"] if not p.get("hidden")])
    print(f"presets: {n} configurations, {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
