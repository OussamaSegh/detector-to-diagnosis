"""Exercise 16.2: the change request rules of tools/check_changes.py, without git, plus two to add."""
import pathlib
import re

CR = pathlib.Path(__file__).with_name("CR-0010-coincidence-window-3ns.md")
FIELDS = ("Status", "Requested", "Source", "Decision", "Commits")
STATUSES = ("proposed", "approved", "rejected", "implemented")
SECTIONS = ("Description", "Reason", "Requirements", "Software items and safety class", "Risk", "SOUP",
            "Interfaces and data formats", "Documents", "Regulatory", "Verification", "Decision")
FIELD_ROW = re.compile(r"^\|\s*([A-Za-z]+)\s*\|\s*(.*?)\s*\|\s*$", re.M)
HEADING = re.compile(r"^#{2,3} (.+?)\s*$", re.M)
TEST_NAME = re.compile(r"\b([A-Z]\w+\.[A-Z]\w+)\b")
COMMIT = re.compile(r"\b[0-9a-f]{7,40}\b")


def load():
    return CR.read_text()


def sections(text):
    marks = list(HEADING.finditer(text))
    return {m.group(1): text[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)].strip()
            for i, m in enumerate(marks)}


def check(name, text, known):
    """Problems of a change request; known has the sets requirements, risk and tests."""
    m = re.match(r"# (CR-\d{4}): \S", text)
    if not m or not name.startswith(m.group(1) + "-"):
        return [f"{name}: the title must be '# CR-NNNN: ...' with the number of the file name"]
    errors = []
    fields = dict(FIELD_ROW.findall(text.split("\n## ", 1)[0]))
    for f in FIELDS:
        if not fields.get(f):
            errors.append(f"{name}: no field {f}")
    status = fields.get("Status", "")
    if status not in STATUSES:
        errors.append(f"{name}: status '{status}' is not one of {', '.join(STATUSES)}")
    body = sections(text)
    for s in SECTIONS:
        if not body.get(s):
            errors.append(f"{name}: section '{s}' is missing or empty")
    for rid in sorted(set(re.findall(r"SRS-[A-Z]+-\d{3}", text)) - known["requirements"]):
        errors.append(f"{name}: {rid} is not a requirement of the SRS")
    for hid in sorted(set(re.findall(r"\b(?:H|RC)-\d\d\b", text)) - known["risk"]):
        errors.append(f"{name}: {hid} is not in the risk file")
    if status in ("approved", "implemented", "rejected") and fields.get("Decision", "").startswith("pending"):
        errors.append(f"{name}: status {status}, but the decision is pending")
    # TODO(16.2): a change that is not implemented lists no commits (COMMIT), and every test that
    # the Verification section names (TEST_NAME) must exist, whatever the status.
    return errors
