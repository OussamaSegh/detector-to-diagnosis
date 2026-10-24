# SPDX-License-Identifier: MIT
"""Exercise 6.3: a checker for architecture decision records (format: docs/adr/0001)."""
import datetime
import pathlib
import re

NAME = re.compile(r"^(\d{4})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
TITLE = re.compile(r"^# (\d{4})\. \S")
DATE = re.compile(r"^Date: (\d{4}-\d{2}-\d{2})\s*$", re.M)
STATUS = re.compile(r"^Status: (.+?)\s*$", re.M)
STATUSES = {"Proposed", "Accepted", "Rejected", "Deprecated"}
SUPERSEDED = re.compile(r"^Superseded by (\d{4})$")
SECTIONS = ["Context", "Options", "Decision", "Consequences"]


def _sections(text, level):
    """{heading: body} for headings of the given level ('##' or '###'), in order."""
    out = {}
    parts = re.split(rf"^{level} (.+?)\s*$", text, flags=re.M)
    for i in range(1, len(parts), 2):
        out[parts[i]] = parts[i + 1]
    return out


def _options(body):
    numbered = re.findall(r"^\d+\.\s+\S", body, flags=re.M)
    subsections = re.findall(r"^### \S", body, flags=re.M)
    return max(len(numbered), len(subsections))


# [snippet:lint_file]
def lint_file(path):
    """Problems in one ADR, as human-readable strings (empty: fine).
    Superseded-by targets are checked by lint_dir, which sees the other files."""
    path = pathlib.Path(path)
    problems = []
    m = NAME.match(path.name)
    if not m:
        problems.append("file name must look like 0001-short-title.md")
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    t = TITLE.match(lines[0]) if lines else None
    if not t:
        problems.append("first line must be '# NNNN. Title'")
    elif m and t.group(1) != m.group(1):
        problems.append(f"title number {t.group(1)} does not match file number {m.group(1)}")
    d = DATE.search(text)
    if not d:
        problems.append("missing 'Date: YYYY-MM-DD' line")
    else:
        try:
            datetime.date.fromisoformat(d.group(1))
        except ValueError:
            problems.append(f"invalid date {d.group(1)}")
    s = STATUS.search(text)
    if not s:
        problems.append("missing 'Status:' line")
    elif s.group(1) not in STATUSES and not SUPERSEDED.match(s.group(1)):
        problems.append(f"unknown status '{s.group(1)}'")
    sections = _sections(text, "##")
    present = [h for h in sections if h in SECTIONS]
    for h in SECTIONS:
        if h not in sections:
            problems.append(f"missing section '## {h}'")
        elif not sections[h].strip():
            problems.append(f"section '## {h}' is empty")
    if present != [h for h in SECTIONS if h in present]:
        problems.append("sections must be in the order " + ", ".join(SECTIONS))
    if "Options" in sections and _options(sections["Options"]) < 2:
        problems.append("'## Options' must list at least two options")
    if "Consequences" in sections:
        sub = _sections(sections["Consequences"], "###")
        for h in ("Positive", "Negative"):
            if h not in sub:
                problems.append(f"'## Consequences' needs a '### {h}' subsection")
            elif not sub[h].strip():
                problems.append(f"'### {h}' is empty")
    return problems
# [/snippet:lint_file]


def lint_dir(directory):
    """{file name: problems} for every ADR-like file (name starting with a digit),
    plus directory-wide problems under the key '(directory)'."""
    directory = pathlib.Path(directory)
    files = sorted(p for p in directory.glob("*.md") if p.name[:1].isdigit())
    result = {p.name: lint_file(p) for p in files}
    numbers = []
    for p in files:
        m = NAME.match(p.name)
        if m:
            numbers.append(m.group(1))
    general = []
    duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
    if duplicates:
        general.append("duplicate numbers: " + ", ".join(duplicates))
    want = [f"{i:04d}" for i in range(1, len(set(numbers)) + 1)]
    if sorted(set(numbers)) != want:
        general.append("numbers must run from 0001 without gaps")
    for p in files:
        s = STATUS.search(p.read_text(encoding="utf-8"))
        sup = SUPERSEDED.match(s.group(1)) if s else None
        if sup and sup.group(1) not in numbers:
            result[p.name].append(f"superseded by {sup.group(1)}, which does not exist")
    if general:
        result["(directory)"] = general
    return result
