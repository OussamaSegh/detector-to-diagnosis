"""Exercise 14.5: check a release record before a release is made.

A release record (Markdown) states what is released, the result and evidence of every
verification of the development plan, the known anomalies, the SOUP review, how the release
was built and where it is archived. check() returns every reason why the record does not yet
allow the release; an empty list means it is complete, not that the release is good.
"""
import json
import pathlib
import re

SECTIONS = ["Release", "Verification", "Known anomalies", "SOUP review", "Build", "Archive"]
REQUIRED_CHECKS = [
    "build debug", "build clang-release", "build gcc-cxx23", "build hardened", "build asan-ubsan", "build tsan",
    "tests debug", "tests clang-release", "tests gcc-cxx23", "tests hardened", "tests asan-ubsan", "tests tsan",
    "static analysis", "fuzzing", "performance", "trace matrix",
]


def sections(text):
    """{heading: body} for every '## heading' of the record."""
    parts = re.split(r"^## +(.+?)\s*$", text, flags=re.M)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


# [snippet:check]
def check(text, root):
    root = pathlib.Path(root)
    errors = []
    s = sections(text)
    for name in SECTIONS:
        if not s.get(name, "").strip():
            errors.append(f"section '{name}' is missing or empty")
    m = re.search(r"MiniDAQ (\d+\.\d+\.\d+), commit ([0-9a-f]{40}), tag (\S+)", s.get("Release", ""))
    if not m:
        errors.append("Release: write 'MiniDAQ X.Y.Z, commit <40 hex digits>, tag <tag>'")
    elif m.group(3) != f"book-v{m.group(1)}":
        errors.append(f"Release: tag {m.group(3)} does not match version {m.group(1)}")
    rows = {}
    for line in s.get("Verification", "").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0] not in ("Check", "") and not set(cells[0]) <= set("-"):
            rows[cells[0]] = cells[1:]
    for name in REQUIRED_CHECKS:
        if name not in rows:
            errors.append(f"Verification: no row for '{name}'")
            continue
        result, evidence = rows[name]
        if result != "pass":
            errors.append(f"Verification: '{name}' is '{result}', not 'pass'")
        if not evidence or not (root / evidence.strip("`")).is_file():
            errors.append(f"Verification: evidence for '{name}' ({evidence or 'none'}) is not a file")
    reports = json.loads((root / "problem-reports.json").read_text())["reports"]
    for r in reports:
        if r["status"] == "open" and r["id"] not in s.get("Known anomalies", ""):
            errors.append(f"Known anomalies: open report {r['id']} is not listed")
    if not re.search(r"\d{4}-\d{2}-\d{2}", s.get("SOUP review", "")):
        errors.append("SOUP review: no date")
    if "cmake --preset" not in s.get("Build", "") or "```" not in s.get("Build", ""):
        errors.append("Build: give the exact commands in a code block")
    return errors
# [/snippet:check]
