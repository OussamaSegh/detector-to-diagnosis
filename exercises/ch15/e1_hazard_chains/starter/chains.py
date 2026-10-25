"""Exercise 15.1: hazard chains and their rating.

A chain goes from a hazard (a potential source of harm) through a sequence of events to a
hazardous situation (someone exposed to the hazard) and to the harm. Each chain is rated
before risk control: the severity of the harm (S1 to S4) and the probability of the harm
(P1 to P5), with the software's own failure taken as certain. problems() returns every rule a
chain document breaks; missing_categories() the kinds of hazard it does not cover yet.
"""
import json
import pathlib

FIELDS = ("id", "category", "hazard", "sequence", "hazardous_situation", "harm", "severity",
          "probability", "acceptable")
SEVERITIES = ("S1", "S2", "S3", "S4")
PROBABILITIES = ("P1", "P2", "P3", "P4", "P5")
CATEGORIES = ("data loss", "timing", "file integrity", "identification", "quantitation", "control")
REQUIRED = ("data loss", "timing", "file integrity", "identification", "quantitation")


def acceptable(severity, probability):
    # TODO: this is not the criterion of MiniDAQ's risk management plan.
    return int(severity[1:]) * int(probability[1:]) <= 6


def problems(doc):
    errors = []
    for c in doc["chains"]:
        cid = c.get("id", "?")
        missing = [f for f in FIELDS if f not in c]
        if missing:
            errors.append(f"{cid}: no {', '.join(missing)}")
    # TODO: empty fields, duplicate IDs, categories, chains that are not chains, scales, ratings.
    return errors


def missing_categories(doc):
    found = {c.get("category") for c in doc["chains"]}
    return [k for k in REQUIRED if k not in found]


def load(path=None):
    path = path or pathlib.Path(__file__).resolve().parent / "hazards.json"
    return json.loads(pathlib.Path(path).read_text())


if __name__ == "__main__":
    d = load()
    for e in problems(d) + [f"no chain of category '{k}'" for k in missing_categories(d)]:
        print(e)
