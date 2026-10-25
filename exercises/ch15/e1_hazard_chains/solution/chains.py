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


# [snippet:rate]
def acceptable(severity, probability):
    """The criterion of MiniDAQ's risk management plan: severity index + probability index <= 5."""
    return int(severity[1:]) + int(probability[1:]) <= 5
# [/snippet:rate]


def problems(doc):
    errors = []
    seen = set()
    for c in doc["chains"]:
        cid = c.get("id", "?")
        missing = [f for f in FIELDS if f not in c or c[f] is None or (isinstance(c[f], str) and not c[f].strip())]
        if missing:
            errors.append(f"{cid}: no {', '.join(missing)}")
            continue
        if cid in seen:
            errors.append(f"{cid}: defined twice")
        seen.add(cid)
        if c["category"] not in CATEGORIES:
            errors.append(f"{cid}: category '{c['category']}' is not one of {', '.join(CATEGORIES)}")
        # [snippet:chain]
        texts = [c["hazard"].strip().lower(), c["hazardous_situation"].strip().lower(), c["harm"].strip().lower()]
        if len(set(texts)) < 3:
            errors.append(f"{cid}: hazard, hazardous situation and harm are three different things")
        if c["severity"] not in SEVERITIES or c["probability"] not in PROBABILITIES:
            errors.append(f"{cid}: severity and probability must be on the scales S1-S4 and P1-P5")
            continue
        if c["acceptable"] is not acceptable(c["severity"], c["probability"]):
            errors.append(f"{cid}: {c['severity']}/{c['probability']} is "
                          f"{'' if acceptable(c['severity'], c['probability']) else 'not '}acceptable by the criterion")
        # [/snippet:chain]
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
