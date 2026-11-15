#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks the book's cross references (roadmap 2.0.0, Theme A).

Chapters were added and renumbered while the first edition was written, so a "Chapter 21" or an
"Exercise 18.5" in the text could point to nothing. This check reads the book's and the
solutions' Markdown and reports:

- a "Chapter N" outside the chapters that exist;
- a "Part X" outside the Parts that exist;
- an "Exercise N.M" that chapter N does not define ("**Exercise N.M (E|M|H): ...**"), or
  one marked other than E, M or H (with ", extra"), the marks How to use this book explains;
- an exercise defined in a chapter whose number is not N, or whose starter directory
  (`exercises/chNN/eM_...`) does not exist or does not start with eM_;
- a heading of the solutions manual's chapter NN for an exercise of another chapter.

Ranges and lists are read too: "Exercises 5.1 to 5.3", "Chapters 18, 19 and 21".

Usage: xrefs.py ROOT. Exit status 0 if every reference resolves.
"""
import pathlib
import re
import sys

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
LIST = r"((?:\d+(?:\.\d+)?)(?:(?:,? and |, | to |-| or |, or )(?:\d+(?:\.\d+)?))*)"
CHAPTER_REF = re.compile(r"\bChapters? " + LIST)
EXERCISE_REF = re.compile(r"\bExercises? " + LIST)
PART_REF = re.compile(r"\bParts? ((?:[IVX]+)(?:(?:,? and |, | to )(?:[IVX]+))*)\b")
DEFINITION = re.compile(r"^\*\*Exercise (\d+)\.(\d+) \([EMH][,)]", re.M)
STARTER = re.compile(r"\*Starter:\*\s*`(exercises/[^`]+)`")


def numbers(span):
    """'5.1 to 5.3' -> ['5.1', '5.2', '5.3']; '18, 19 and 21' -> ['18', '19', '21']."""
    items = re.findall(r"\d+(?:\.\d+)?", span)
    out = []
    for i, item in enumerate(items):
        out.append(item)
        sep = span.split(item, 1)[1] if i + 1 < len(items) else ""
        if i + 1 < len(items) and re.match(r"\s*(to|-)\s*", sep):
            a, b = item, items[i + 1]
            if "." in a and "." in b and a.split(".")[0] == b.split(".")[0]:
                c = a.split(".")[0]
                out += [f"{c}.{k}" for k in range(int(a.split(".")[1]) + 1, int(b.split(".")[1]))]
            elif "." not in a and "." not in b:
                out += [str(k) for k in range(int(a) + 1, int(b))]
    return out


def strip_code(text):
    """The text without fenced code blocks and inline code, where numbers are not references.
    A fenced block leaves its line breaks, so the line numbers of the report stay the file's."""
    text = re.sub(r"^(```|~~~).*?^\1", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.M | re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def chapters(root):
    """{chapter number: path} of the book's chapters."""
    out = {}
    for p in sorted((root / "book/src").glob("part*/ch*.md")):
        m = re.match(r"ch(\d+)-", p.name)
        if m:
            out[int(m.group(1))] = p
    return out


def check(root):
    errors = []
    chs = chapters(root)
    parts = {ROMAN[int(p.name[4:]) - 1] for p in (root / "book/src").glob("part*") if p.name[4:].isdigit()}
    defined = set()
    for n, path in chs.items():
        text = path.read_text()
        for m in DEFINITION.finditer(text):
            c, e = int(m.group(1)), int(m.group(2))
            where = f"{path.relative_to(root)}"
            if c != n:
                errors.append(f"{where}: Exercise {c}.{e} is defined in Chapter {n}")
            defined.add(f"{c}.{e}")
            para = text[m.start():text.find("\n\n", m.start())]
            s = STARTER.search(para)
            if s:
                starter = s.group(1).rstrip("/")
                directory = "/".join(starter.split("/")[:3])
                if not re.fullmatch(rf"exercises/ch{c:02d}/e{e}_[a-z0-9_]+", directory):
                    errors.append(f"{where}: Exercise {c}.{e}'s starter is {starter}")
                elif not (root / starter).exists():
                    errors.append(f"{where}: Exercise {c}.{e}'s starter {starter} does not exist")
        for m in re.finditer(r"^\*\*Exercise (\d+\.\d+) \(([^)]*)\)", text, re.M):
            if not re.fullmatch(r"[EMH](, extra)?", m.group(2)):
                errors.append(f"{path.relative_to(root)}: Exercise {m.group(1)} is marked "
                              f"({m.group(2)}), not E, M or H")
    files = sorted((root / "book/src").rglob("*.md")) + sorted((root / "book/solutions").glob("*.md"))
    for path in files:
        text = strip_code(path.read_text())
        where = str(path.relative_to(root))
        # Lines are joined within a paragraph, so a "Chapter" at the end of a line and its number
        # on the next are read too (review of 1.2.0); one character for one keeps the offsets.
        flat = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

        def line_of(m):
            return text.count("\n", 0, m.start()) + 1
        for m in CHAPTER_REF.finditer(flat):
            for x in numbers(m.group(1)):
                if "." in x or int(x) not in chs:
                    errors.append(f"{where}:{line_of(m)}: Chapter {x} does not exist")
        for m in EXERCISE_REF.finditer(flat):
            for x in numbers(m.group(1)):
                if x not in defined:
                    errors.append(f"{where}:{line_of(m)}: Exercise {x} is not defined")
        for m in PART_REF.finditer(flat):
            for x in re.findall(r"[IVX]+", m.group(1)):
                if x not in parts:
                    errors.append(f"{where}:{line_of(m)}: Part {x} does not exist")
        sm = re.fullmatch(r"ch(\d+)\.md", path.name)
        if path.parent.name == "solutions" and sm:
            for h in re.finditer(r"^#+ .*?Exercise (\d+)\.(\d+)", text, re.M):
                if int(h.group(1)) != int(sm.group(1)):
                    errors.append(f"{where}: heading for Exercise {h.group(1)}.{h.group(2)}")
    return errors


def main(root):
    errors = check(root)
    for e in errors:
        print(e)
    print("cross references: " + ("ok" if not errors else f"{len(errors)} problem(s)"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(pathlib.Path(sys.argv[1]).resolve()))
