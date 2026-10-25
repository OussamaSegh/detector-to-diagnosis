"""Exercise 16.1: map MiniDAQ's documents to the clauses of ISO 13485.

A mapping is {"clauses": {clause: {"evidence": [documents], "plan": "..."}}}. problems() returns
every rule the mapping breaks: an unknown clause or document, a design and development clause
(7.3.2 to 7.3.10) with neither evidence nor a plan, a document that no clause uses, and the
mistakes reviewers see most often.
"""
import json
import pathlib

DESIGN = ("7.3.2", "7.3.3", "7.3.4", "7.3.5", "7.3.6", "7.3.7", "7.3.8", "7.3.9", "7.3.10")
# Verification evidence is not validation evidence.
VERIFICATION = ("docs/regulatory/trace-matrix.md", "minidaq/tests/", "ci/run_all.sh")


# [snippet:problems]
def problems(mapping, clauses, documents):
    errors = []
    used = set()
    for clause, entry in mapping["clauses"].items():
        if clause not in clauses:
            errors.append(f"{clause}: not a clause of the list")
            continue
        for d in entry.get("evidence", []):
            if d not in documents:
                errors.append(f"{clause}: {d} is not a MiniDAQ document")
            used.add(d)
        if clause in DESIGN and not entry.get("evidence") and not entry.get("plan", "").strip():
            errors.append(f"{clause}: no evidence and no plan")
    for clause in DESIGN:
        if clause not in mapping["clauses"]:
            errors.append(f"{clause}: missing")
    for d in documents:
        if d not in used:
            errors.append(f"{d}: used by no clause")
    validation = mapping["clauses"].get("7.3.7", {}).get("evidence", [])
    for d in validation:
        if d in VERIFICATION:
            errors.append(f"7.3.7: {d} is verification evidence, not validation")
    return errors
# [/snippet:problems]


def load(path=None):
    path = path or pathlib.Path(__file__).resolve().parent / "mapping.json"
    return json.loads(pathlib.Path(path).read_text())
