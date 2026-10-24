#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks MiniDAQ's layering (Chapter 6): every #include must go from a layer to
one it may depend on (docs/architecture/layers.json). An architecture rule
that is not checked by a machine erodes one convenient include at a time.

Usage: tools/check_layers.py [repo-root]     exit status 0: clean, 1: violations
"""
import json
import pathlib
import re
import sys

INCLUDE = re.compile(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]', re.M)


def module_of(path: pathlib.Path, root: pathlib.Path):
    rel = path.relative_to(root).as_posix()
    for prefix in ("minidaq/include/minidaq/", "minidaq/src/"):
        if rel.startswith(prefix):
            return rel[len(prefix):].rsplit(".", 1)[0]
    if rel.startswith("minidaq/apps/"):
        return "apps/" + path.stem
    return None


def layer_of(module, layers):
    best, best_len = None, -1
    for layer, prefixes in layers.items():
        for p in prefixes:
            if module.startswith(p) and len(p) > best_len:
                best, best_len = layer, len(p)
    return best


def check(root: pathlib.Path):
    spec = json.loads((root / "docs/architecture/layers.json").read_text())
    layers, allowed = spec["layers"], spec["may_include"]
    forbidden = spec.get("forbidden_external", {})
    files = sorted(
        p for d in ("minidaq/include", "minidaq/src", "minidaq/apps")
        for p in (root / d).rglob("*") if p.suffix in (".hpp", ".cpp", ".h"))
    problems = []
    for f in files:
        mod = module_of(f, root)
        layer = layer_of(mod, layers)
        if layer is None:
            problems.append(f"{f.relative_to(root)}: module '{mod}' is in no layer")
            continue
        for inc in INCLUDE.findall(f.read_text()):
            if inc.startswith("minidaq/"):
                target = inc[len("minidaq/"):].rsplit(".", 1)[0]
                tlayer = layer_of(target, layers)
                if tlayer is None:
                    problems.append(f"{f.relative_to(root)}: includes {inc}, which is in no layer")
                elif tlayer not in allowed[layer]:
                    problems.append(f"{f.relative_to(root)}: {layer} may not include {tlayer} ({inc})")
            else:
                for bad in forbidden.get(layer, []):
                    if inc.startswith(bad):
                        problems.append(f"{f.relative_to(root)}: {layer} may not include <{inc}>")
    return files, problems


def main(argv):
    root = pathlib.Path(argv[1] if len(argv) > 1 else pathlib.Path(__file__).resolve().parent.parent)
    files, problems = check(root.resolve())
    for p in problems:
        print(p)
    print(f"check_layers: {len(files)} files, {len(problems)} violation(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
