"""Exercise 14.1: the mechanical rules of an IEC 62304 software item classification.

A classification document (JSON) lists hazards with the severity of their worst harm after
risk controls outside the software, and software items with the process they run in, their
safety class and the hazards they can contribute to. problems() returns every rule the
document breaks; an empty list means the classification is consistent, not that it is right.
"""
import json
import pathlib

ORDER = {"A": 0, "B": 1, "C": 2}
IMPLIED = {"none": "A", "non-serious": "B", "serious": "C", "death": "C"}


def problems(doc):
    errors = []
    severity = {h["id"]: h["severity"] for h in doc["hazards"]}
    for i in doc["items"]:
        if not i["shipped"]:
            continue
        if i["class"] not in ORDER:
            errors.append(f"{i['id']}: a shipped item needs class A, B or C and a rationale")
            continue
        for h in i["hazards"]:
            if h in severity and ORDER[i["class"]] < ORDER[IMPLIED[severity[h]]]:
                errors.append(f"{i['id']}: class {i['class']}, but {h} ({severity[h]}) needs {IMPLIED[severity[h]]}")
    # TODO: items in one process, and the system's class.
    return errors


def load(path):
    return json.loads(pathlib.Path(path).read_text())
