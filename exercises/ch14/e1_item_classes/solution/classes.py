"""Exercise 14.1: the mechanical rules of an IEC 62304 software item classification.

A classification document (JSON) lists hazards with the severity of their worst harm after
risk controls outside the software, and software items with the process they run in, their
safety class and the hazards they can contribute to. problems() returns every rule the
document breaks; an empty list means the classification is consistent, not that it is right.
"""
import json
import pathlib

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
                errors.append(f"{i['id']}: not shipped, so no class and a rationale 'Not shipped: why'")
            continue
        if i["class"] not in ORDER or not i["rationale"].strip():
            errors.append(f"{i['id']}: a shipped item needs class A, B or C and a rationale")
            continue
        for h in i["hazards"]:
            if h not in severity:
                errors.append(f"{i['id']}: unknown hazard {h}")
            elif ORDER[i["class"]] < ORDER[IMPLIED[severity[h]]]:
                errors.append(f"{i['id']}: class {i['class']}, but {h} ({severity[h]}) needs {IMPLIED[severity[h]]}")
    # Nothing segregates items inside one process: they share the highest class there.
    by_process = {}
    for i in shipped:
        if i["class"] in ORDER:
            by_process.setdefault(i["runs_in"], []).append(i)
    for process, items in by_process.items():
        top = max(items, key=lambda i: ORDER[i["class"]])
        for i in items:
            if ORDER[i["class"]] < ORDER[top["class"]]:
                errors.append(f"{i['id']}: class {i['class']} in {process} with {top['id']} "
                              f"(class {top['class']}), and nothing segregates them")
    classes = [i["class"] for i in shipped if i["class"] in ORDER]
    if classes and doc["system"]["class"] != max(classes, key=ORDER.get):
        errors.append(f"system: class {doc['system']['class']}, but its highest item is "
                      f"{max(classes, key=ORDER.get)}")
    return errors
# [/snippet:rules]


def load(path):
    return json.loads(pathlib.Path(path).read_text())
