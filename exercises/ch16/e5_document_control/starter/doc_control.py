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
    """Compare two releases of the controlled documents: {path: text} before and after.

    TODO(16.5): the rules of the README. This draft only checks that each document has a version.
    """
    return [f"{p}: no version" for p in sorted(new) if version(new[p]) is None]
