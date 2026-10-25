"""Exercise 16.3: answers to an auditor's questions, checked the way an auditor reads them."""
import json
import pathlib
import re

ANSWERS = pathlib.Path(__file__).with_name("answers.json")
MAX_WORDS = 80
# Words that turn an answer into an opinion. An auditor writes them down.
HEDGES = ("probably", "i think", "i believe", "maybe", "perhaps", "should", "might", "usually",
          "normally", "as far as i know", "i guess", "in principle")
TEST_NAME = re.compile(r"^[A-Z]\w+\.[A-Z]\w+$")


def load():
    return json.loads(ANSWERS.read_text())


def exists(evidence, files, tests):
    """A test name, a tracked file, or a directory (ending in '/') with tracked files."""
    if TEST_NAME.match(evidence):
        return evidence in tests
    if evidence.endswith("/"):
        return any(f.startswith(evidence) for f in files)
    return evidence in files


def problems(answers, questions, files, tests):
    errors = []
    ids = [q["id"] for q in questions]
    for qid in ids:
        if qid not in answers:
            errors.append(f"{qid}: not answered")
    for qid, a in answers.items():
        if qid not in ids:
            errors.append(f"{qid}: not a question")
            continue
        text = a.get("answer", "")
        words = len(text.split())
        if words == 0:
            errors.append(f"{qid}: empty answer")
        if words > MAX_WORDS:
            errors.append(f"{qid}: {words} words; answer the question, at most {MAX_WORDS}")
        lower = f" {text.lower()} "
        for h in HEDGES:
            if re.search(rf"\b{re.escape(h)}\b", lower):
                errors.append(f"{qid}: '{h}' is an opinion, not an answer")
        evidence = a.get("evidence", [])
        if not evidence:
            errors.append(f"{qid}: no evidence")
        if evidence and all(e.endswith("/") for e in evidence):
            errors.append(f"{qid}: only directories; point at a document, a record or a test")
        for e in evidence:
            if not exists(e, files, tests):
                errors.append(f"{qid}: evidence {e} does not exist")
    return errors
