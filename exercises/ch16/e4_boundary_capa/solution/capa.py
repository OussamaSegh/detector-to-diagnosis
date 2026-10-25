"""Exercise 16.4: the CAPA rules of tools/check_capa.py, plus the two that make a CAPA checkable."""
import pathlib
import re

RECORD = pathlib.Path(__file__).with_name("CAPA-0003-boundary-inputs.md")
DUE = re.compile(r"^(?:\d{4}-\d{2}-\d{2}|release \d+\.\d+\.\d+)\b")
CHECK_NAME = re.compile(r"\b[A-Z]\w+\.[A-Z]\w+\b|\b(?:docs|tests|tools)\.\w+|`[\w./-]+`")
VAGUE = re.compile(r"\b(improve[sd]?|better|awareness|more careful(ly)?|as expected)\b", re.I)
FIELDS = ("Status", "Opened", "Source", "Owner", "Effectiveness check")
STATUSES = ("open", "implemented", "closed")
SECTIONS = ("Problem", "Investigation", "Root cause", "Correction", "Corrective action", "Preventive action",
            "Verification of the actions", "Effectiveness check", "Closure")
FIELD_ROW = re.compile(r"^\|\s*([A-Za-z ]+?)\s*\|\s*(.*?)\s*\|\s*$", re.M)
HEADING = re.compile(r"^## (.+?)\s*$", re.M)
PATH = re.compile(r"`([\w./-]+/[\w./-]*|[\w-]+\.(?:md|json|py|cpp|hpp|sh|yml|txt|cmake))`")
BLAME = re.compile(r"\b(human|operator|developer|user) error\b|\bcareless(ness)?\b|\binattention\b", re.I)


def load():
    return RECORD.read_text()


def sections(text):
    marks = list(HEADING.finditer(text))
    return {m.group(1): text[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)].strip()
            for i, m in enumerate(marks)}


def files_named(text, files):
    """The repository files (or directories, ending in '/') that a section names in backticks."""
    return [p for p in PATH.findall(text) if p in files or (p.endswith("/") and any(f.startswith(p) for f in files))]


def check(name, text, reports, files):
    m = re.match(r"# (CAPA-\d{4}): \S", text)
    if not m or not name.startswith(m.group(1) + "-"):
        return [f"{name}: the title must be '# CAPA-NNNN: ...' with the number of the file name"]
    capa = m.group(1)
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
        if s != "Closure" and not body.get(s):
            errors.append(f"{name}: section '{s}' is missing or empty")
    named = set(re.findall(r"MDQ-PR-\d{3}", fields.get("Source", "")))
    for rid in sorted(named):
        if rid not in reports:
            errors.append(f"{name}: {rid} is not a problem report")
        elif reports[rid].get("capa") != capa:
            errors.append(f"{name}: {rid} does not name {capa} in its field 'capa'")
    for rid, r in sorted(reports.items()):
        if r.get("capa") == capa and rid not in named:
            errors.append(f"{name}: {rid} names {capa}, but the CAPA's source does not name it")
    if BLAME.search(body.get("Root cause", "")):
        errors.append(f"{name}: the root cause blames a person; ask why the process let the error through")
    if not files_named(body.get("Corrective action", ""), files):
        errors.append(f"{name}: the corrective action names no file of the repository that it changes")
    preventive = body.get("Preventive action", "")
    if not preventive.lower().startswith("none") and not files_named(preventive, files):
        errors.append(f"{name}: the preventive action names no file of the repository, and is not 'none'")
    check_ = body.get("Effectiveness check", "")
    for key in ("Criterion:", "Due:"):
        if key not in check_:
            errors.append(f"{name}: the effectiveness check has no '{key}' line")
    # [snippet:rules]
    # The two rules of the exercise: a CAPA whose check cannot fail cannot be closed honestly.
    due = re.search(r"^Due:\s*(.*)$", check_, re.M)
    for when, value in (("field", fields.get("Effectiveness check", "")), ("Due: line", due.group(1) if due else "")):
        if value and not DUE.match(value):
            errors.append(f"{name}: effectiveness check {when} '{value}' is not a date (YYYY-MM-DD) or 'release X.Y.Z'")
    criterion = re.search(r"^Criterion:\s*(.*(?:\n(?!Due:|Result:).+)*)", check_, re.M)
    text_ = criterion.group(1) if criterion else ""
    if criterion and not (re.search(r"\d", text_) or CHECK_NAME.search(text_)):
        errors.append(f"{name}: the criterion names no number and no test or check, so nothing can show it failed")
    if criterion and VAGUE.search(text_):
        errors.append(f"{name}: the criterion says '{VAGUE.search(text_).group(0)}', which no check can measure")
    # [/snippet:rules]
    result = re.search(r"^Result:\s*(.*)$", check_, re.M)
    if status == "closed":
        if not result or not result.group(1) or result.group(1).startswith("filled in"):
            errors.append(f"{name}: closed without the result of its effectiveness check")
        if not body.get("Closure"):
            errors.append(f"{name}: closed without a closure record")
    return errors


