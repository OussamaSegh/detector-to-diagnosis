# SPDX-License-Identifier: MIT
"""Exercise 37.2: check that a context file names paths and tests that exist (solution)."""
import pathlib
import re

SPAN = re.compile(r"`([^`\n]+)`")
FENCE = re.compile(r"^\s*(```|~~~)")
TEST = re.compile(r"\bctest\b[^\n`]*?\s-R\s+'?\"?([\w./-]+)")
ADD_TEST = re.compile(r"add_test\(\s*NAME\s+([\w./-]+)")
PLACEHOLDER = re.compile(r"NN|X\.Y\.Z|<[^>/]+>|\*")


def _clean(word):
    word = word.strip().strip(".,;:()[]'\"")
    word = re.sub(r":\d+(-\d+)?$", "", word)
    return word.rstrip("/")


def references(text, tops):
    """[(line, path)] for every word of a code span or fenced block under a top-level entry."""
    found, fenced = [], False
    for n, line in enumerate(text.splitlines(), start=1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        words = line.split() if fenced else [w for s in SPAN.findall(line) for w in s.split()]
        for word in words:
            if "://" in word:
                continue
            path = _clean(word)
            if path and path.split("/")[0] in tops:
                found.append((n, path))
    return found


def _pattern(path):
    """A regular expression for a path with placeholders, or None for a plain path."""
    if not PLACEHOLDER.search(path):
        return None
    out = ""
    for part in re.split(r"(NN|X\.Y\.Z|<[^>/]+>|\*)", path):
        if part == "NN":
            out += r"\d\d"
        elif part == "X.Y.Z":
            out += r"\d+\.\d+\.\d+"
        elif part == "*" or part.startswith("<"):
            out += r"[^/]+"
        else:
            out += re.escape(part)
    return re.compile(out + r"/?$")


def _tests(root):
    names = set()
    for p in root.rglob("CMakeLists.txt"):
        names |= set(ADD_TEST.findall(p.read_text(errors="replace")))
    return names


def problems(text, root):
    """[(line, message)] for every path that does not exist and every test that is not defined."""
    root = pathlib.Path(root)
    tops = {p.name for p in root.iterdir()}
    every = None
    found = []
    for n, path in references(text, tops):
        pattern = _pattern(path)
        if pattern is None:
            if not (root / path).exists():
                found.append((n, f"{path} does not exist"))
            continue
        if every is None:
            every = [p.relative_to(root).as_posix() for p in root.rglob("*")]
        if not any(pattern.match(p) for p in every):
            found.append((n, f"nothing matches {path}"))
    tests = None
    for n, line in enumerate(text.splitlines(), start=1):
        for name in TEST.findall(line):
            tests = _tests(root) if tests is None else tests
            if name not in tests:
                found.append((n, f"no test named {name}"))
    return found
