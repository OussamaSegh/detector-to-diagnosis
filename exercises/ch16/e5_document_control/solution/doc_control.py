"""Exercise 16.5: document control between two releases, without git."""
import re

VERSION = re.compile(r"^Version (\d+)\b", re.M)
HISTORY_HEADING = re.compile(r"^## (?:\d+\. )?(?:Changes|Document history)\b.*$", re.M)
HISTORY_ROW = re.compile(r"^\|\s*(\d+)\s*\|.*$", re.M)


def version(text):
    """The version stated in the first six lines, or None."""
    m = VERSION.search("\n".join(text.splitlines()[:6]))
    return int(m.group(1)) if m else None


def history(text):
    """The history table's rows, as {version: the whole row}; {} if there is no table."""
    h = HISTORY_HEADING.search(text)
    if not h:
        return {}
    table = text[h.end():].split("\n## ", 1)[0]
    return {int(m.group(1)): m.group(0).strip() for m in HISTORY_ROW.finditer(table)}


def problems(old, new):
    """Compare two releases of the controlled documents: {path: text} before and after."""
    errors = []
    for path in sorted(set(old) - set(new)):
        errors.append(f"{path}: withdrawn without a record; keep it with its last version marked obsolete")
    for path in sorted(new):
        text = new[path]
        v, rows = version(text), history(text)
        if v is None:
            errors.append(f"{path}: no version")
            continue
        if list(rows) != list(range(1, len(rows) + 1)):
            errors.append(f"{path}: history versions {list(rows)} are not 1, 2, 3, ...")
        if not rows or max(rows) != v:
            errors.append(f"{path}: version {v} is not the last row of its history")
        if path not in old:
            if v != 1:
                errors.append(f"{path}: a new document starts at version 1, not {v}")
            continue
        before = old[path]
        ov = version(before)
        if text == before:
            continue
        if ov is None:
            continue  # first controlled release of an old document: only its own rules apply
        if v == ov:
            errors.append(f"{path}: changed but still version {v}")
        elif v < ov:
            errors.append(f"{path}: version went down from {ov} to {v}")
        for n, row in history(before).items():
            if rows.get(n) != row:
                errors.append(f"{path}: history row {n} was changed or removed; history is appended, never rewritten")
    return errors
