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
    """TODO(16.3): every question answered with a short answer, no hedges, and evidence that exists."""
    return [f"{q['id']}: not answered" for q in questions if q["id"] not in answers]
