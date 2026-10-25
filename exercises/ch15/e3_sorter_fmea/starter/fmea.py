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


def problems(fmea, reqs):
    errors = []
    covered = set()
    for row in fmea["rows"]:
        where = f"{row.get('function', '?')}: {row.get('failure_mode', '?')}"
        missing = [k for k in FIELDS if k not in row]
        if missing:
            errors.append(f"{where}: no {', '.join(missing)}")
            continue
        covered.add(row["function"])
    # TODO: empty fields, unknown functions, duplicates, the scale, hazards, controls, detection.
    for f in FUNCTIONS:
        if f not in covered:
            errors.append(f"function '{f}' has no failure mode")
    return errors


def load(path=None):
    path = path or pathlib.Path(__file__).resolve().parent / "fmea-sorter.json"
    return json.loads(pathlib.Path(path).read_text())
