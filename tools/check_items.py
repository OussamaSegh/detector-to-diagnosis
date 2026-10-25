#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks MiniDAQ's software item classification (Chapter 14).

docs/architecture/software-items.json lists the software items, the process each runs in, its
IEC 62304 safety class and the hazards it can contribute to. The rules checked here are the
mechanical part of the classification; the judgment (which hazards, how severe) is reviewed by
people.

1. A shipped item has class A, B or C and a rationale; an item that is not shipped has no
   class and says why it is not shipped.
2. An item's class is at least the class its worst hazard implies: a non-serious injury needs
   B, a serious injury or death needs C, no injury allows A.
3. Nothing segregates items that run in the same process, so each of them has the class of the
   highest item in that process.
4. The software system has the class of its highest item.
5. Every source file belongs to exactly one item (longest path prefix wins), so a new file
   cannot escape classification.
6. Every requirement in the SRS names an item of this list.

Usage: check_items.py ROOT. Exit status 0 if the classification follows the rules.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from trace_matrix import SRS, parse_srs  # noqa: E402

# [snippet:rules]
ORDER = {"A": 0, "B": 1, "C": 2}
IMPLIED = {"none": "A", "non-serious": "B", "serious": "C", "death": "C"}


def problems(doc):
    errors = []
    severity = {h["id"]: h["severity"] for h in doc["hazards"]}
    shipped = [i for i in doc["items"] if i["shipped"]]
    for i in doc["items"]:
        if not i["shipped"]:
            if i["class"] is not None or not i["rationale"].startswith("Not shipped"):
                errors.append(f"{i['id']}: an item that is not shipped has no class and says 'Not shipped: why'")
            continue
        if i["class"] not in ORDER or not i["rationale"].strip():
            errors.append(f"{i['id']}: a shipped item needs a class A, B or C and a rationale")
            continue
        for h in i["hazards"]:
            if h not in severity:
                errors.append(f"{i['id']}: unknown hazard {h}")
            elif ORDER[i["class"]] < ORDER[IMPLIED[severity[h]]]:
                errors.append(f"{i['id']}: class {i['class']}, but {h} ({severity[h]}) needs {IMPLIED[severity[h]]}")
    by_process = {}
    for i in shipped:
        if i["class"] in ORDER:
            by_process.setdefault(i["runs_in"], []).append(i)
    for process, items in by_process.items():
        top = max(items, key=lambda i: ORDER[i["class"]])
        for i in items:
            if ORDER[i["class"]] < ORDER[top["class"]]:
                errors.append(f"{i['id']}: class {i['class']} in process {process} with {top['id']} "
                              f"(class {top['class']}), and nothing segregates them")
    classes = [i["class"] for i in shipped if i["class"] in ORDER]
    if classes and doc["system"]["class"] != max(classes, key=ORDER.get):
        errors.append(f"system: class {doc['system']['class']}, but its highest item is {max(classes, key=ORDER.get)}")
    return errors
# [/snippet:rules]


def unclassified(root, doc):
    prefixes = [(p, i["id"]) for i in doc["items"] for p in i["paths"]]
    errors = []
    files = sorted(root.glob("minidaq/include/minidaq/**/*.hpp")) + sorted(root.glob("minidaq/src/**/*.cpp")) + \
        sorted(root.glob("minidaq/apps/*.cpp"))
    for f in files:
        rel = f.relative_to(root).as_posix()
        hits = [(p, i) for p, i in prefixes if rel.startswith(p)]
        if not hits:
            errors.append(f"{rel}: belongs to no software item")
            continue
        longest = max(len(p) for p, _ in hits)
        if len({i for p, i in hits if len(p) == longest}) > 1:
            errors.append(f"{rel}: belongs to more than one software item")
    return errors


def main(root):
    doc = json.loads((root / "docs/architecture/software-items.json").read_text())
    errors = problems(doc) + unclassified(root, doc)
    ids = {i["id"] for i in doc["items"]}
    reqs, _, _ = parse_srs((root / SRS).read_text())
    errors += [f"{rid}: item '{item}' is not a software item" for rid, (_, item, _) in reqs.items() if item not in ids]
    for e in errors:
        print(e)
    print("software items: " + ("ok" if not errors else f"{len(errors)} problem(s)"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(pathlib.Path(sys.argv[1]).resolve()))
