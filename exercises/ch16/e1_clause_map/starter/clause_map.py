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


def problems(mapping, clauses, documents):
    errors = []
    for clause, entry in mapping["clauses"].items():
        for d in entry.get("evidence", []):
            if d not in documents:
                errors.append(f"{clause}: {d} is not a MiniDAQ document")
    # TODO: unknown clauses, empty and missing design clauses, unused documents, validation.
    return errors


def load(path=None):
    path = path or pathlib.Path(__file__).resolve().parent / "mapping.json"
    return json.loads(pathlib.Path(path).read_text())
