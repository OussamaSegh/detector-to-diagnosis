"""Exercise 15.3: the mechanical rules of a software FMEA of the coincidence sorter.

An FMEA row is one failure mode of one function: what fails, its effect on the data and the
hazard it can lead to, its cause in the software, its severity, how the failure would be
detected, and the requirements that control it. A failure mode that no existing requirement
controls proposes a new one ("NEW: <the requirement>"). problems() returns every rule the
document breaks; an empty list means the FMEA is well formed, not that it is complete.
"""
import json
import pathlib
import re

# The sorter's functions, in its order of operations (coincidence_sorter.hpp), and around it.
FUNCTIONS = ("energy gate", "order check", "windowing", "multiples resolution", "geometry selection",
             "delayed window", "end of run", "accounting", "configuration")
AT_LEAST_TWO = ("order check", "windowing")
FIELDS = ("function", "failure_mode", "effect", "cause", "severity", "detection", "controls")
SEVERITIES = ("S1", "S2", "S3", "S4")
HAZARD = re.compile(r"\bH-\d\d\b")
REQ_ROW = re.compile(r"^\|\s*(SRS-[A-Z]+-\d{3})\s*\|", re.M)


def requirement_ids(srs_text):
    return set(REQ_ROW.findall(srs_text))


# [snippet:rules]
def problems(fmea, reqs):
    errors = []
    count = {f: 0 for f in FUNCTIONS}
    modes = set()
    for row in fmea["rows"]:
        where = f"{row.get('function', '?')}: {row.get('failure_mode', '?')}"
        missing = [k for k in FIELDS if not row.get(k)]
        if missing:
            errors.append(f"{where}: no {', '.join(missing)}")
            continue
        if row["function"] not in count:
            errors.append(f"{where}: '{row['function']}' is not a function of the sorter")
            continue
        count[row["function"]] += 1
        key = (row["function"], row["failure_mode"].strip().lower())
        if key in modes:
            errors.append(f"{where}: the same failure mode twice")
        modes.add(key)
        if row["severity"] not in SEVERITIES:
            errors.append(f"{where}: severity {row['severity']} is not on the scale S1-S4")
        if not HAZARD.search(row["effect"]):
            errors.append(f"{where}: the effect names no hazard (H-nn) of the hazard analysis")
        new = [c for c in row["controls"] if c.startswith("NEW:")]
        for c in row["controls"]:
            if c.startswith("NEW:"):
                if len(c[4:].split()) < 8 or " shall " not in f" {c[4:]} ":
                    errors.append(f"{where}: a new control is a requirement with 'shall', of 8 words or more")
            elif c not in reqs:
                errors.append(f"{where}: {c} is not a requirement")
        if row["detection"].strip().lower().startswith(("none", "not detected")) and not new:
            errors.append(f"{where}: an undetected failure needs a new control")
    for f, n in count.items():
        if n < (2 if f in AT_LEAST_TWO else 1):
            errors.append(f"function '{f}' has {n} failure mode(s)")
    return errors
# [/snippet:rules]


def load(path=None):
    path = path or pathlib.Path(__file__).resolve().parent / "fmea-sorter.json"
    return json.loads(pathlib.Path(path).read_text())
