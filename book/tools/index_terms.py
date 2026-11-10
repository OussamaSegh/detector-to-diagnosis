#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks the book's index terms (book/index-terms.txt, used by book/filters/index-terms.lua).

Every line is PHRASE | KEY or a comment; no phrase is listed twice; every phrase occurs in the
text of at least one chapter or the appendix, so that no entry of the list is dead; and the
index has at least MIN_ENTRIES distinct keys (the 1.0.0 review found 32).

Usage: index_terms.py ROOT. Exit status 0 if the list is consistent.
"""
import pathlib
import re
import sys

TERMS = pathlib.Path("book/index-terms.txt")
MIN_ENTRIES = 300


def phrases(text):
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        phrase, sep, key = s.partition("|")
        out.append((n, phrase.strip(), key.strip() if sep else phrase.strip()))
    return out


def found(phrase, text):
    if phrase.startswith("`"):
        return phrase in text
    words = [re.escape(w) for w in phrase.lower().split()]
    words[-1] += "(?:e?s)?"
    return re.search(r"(?<![\w-])" + r"\s+".join(words) + r"(?![\w-])", text) is not None


def main(root):
    entries = phrases((root / TERMS).read_text())
    chapters = sorted((root / "book/src").glob("part*/ch*.md")) + sorted((root / "book/src/appendix").glob("*.md"))
    text = "\n".join(p.read_text() for p in chapters)
    lower = text.lower()
    errors = []
    seen = {}
    for n, phrase, key in entries:
        if not phrase or not key:
            errors.append(f"line {n}: empty phrase or key")
            continue
        if phrase in seen:
            errors.append(f"line {n}: '{phrase}' is listed already on line {seen[phrase]}")
        seen[phrase] = n
        if not found(phrase, text if phrase.startswith("`") else lower):
            errors.append(f"line {n}: '{phrase}' occurs in no chapter")
    keys = {k.split("!")[0] for _, _, k in entries}
    if len(keys) < MIN_ENTRIES:
        errors.append(f"only {len(keys)} main entries, fewer than {MIN_ENTRIES}")
    for e in errors:
        print(e)
    print(f"index terms: {len(entries)} phrases, {len(keys)} main entries, "
          + ("ok" if not errors else f"{len(errors)} problem(s)"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(pathlib.Path(sys.argv[1]).resolve()))
