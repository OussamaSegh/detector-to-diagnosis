#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks that the book and the exercises show only the current interfaces (CR-0030).

    tools/check_interfaces.py ROOT

A reader copies what the book shows. After control API 3.0 and acquisition configuration schema
2.0, a listing with a request of another API version, a request without "api", or a 1.x
acquisition configuration teaches something the server refuses. This check reads every
Markdown page of the book (book/src) and every file of the exercises and fails for each:

- a request (a JSON object with "cmd") whose "api" is older than 3.x, and a request line of
  a transcript ("-> {...}") without "api";
- an acquisition configuration (a JSON object with "schema_version" that is not a hardware
  description or a calibration table) whose schema_version is older than 2.x.

A version newer than the current one is not an old interface: a listing may show how a server
refuses a client from the future.

A passage that shows an old form on purpose, to say what changed, marks its code block with
the attribute `.old-interface`; the check skips such blocks and nothing else.
"""
import pathlib
import re
import sys

API = 3
SCHEMA = 2
REQUEST_API = re.compile(r'"api"\s*:\s*"(\d+)\.\d+"')
SCHEMA_VERSION = re.compile(r'"schema_version"\s*[:,]\s*"(\d+)\.\d+"')
NOT_ACQUISITION = re.compile(r'"(backend|boards|coefficients|crystals|procedure)"')
FENCE = re.compile(r"^(```+|~~~+)(.*)$")
TEXT_SUFFIXES = {".md", ".py", ".cpp", ".hpp", ".json", ".txt", ".sh", ".cmake"}


def blocks(path, text):
    """[(first line number, text)] of the parts of a file to check: the code blocks of a Markdown
    page that are not marked .old-interface, or the whole of any other file."""
    if path.suffix != ".md":
        return [(1, text)]
    out, current, start, fence, skip = [], None, 0, "", False
    for n, line in enumerate(text.splitlines(), 1):
        m = FENCE.match(line.strip())
        if current is None:
            if m:
                fence, start, current, skip = m.group(1), n + 1, [], ".old-interface" in m.group(2)
        elif line.strip() == fence:
            if not skip:
                out.append((start, "\n".join(current)))
            current = None
        else:
            current.append(line)
    return out


def objects(text):
    """[(offset, text)] of the outermost {...} of a text, braces inside strings ignored."""
    out, depth, start, i, n = [], 0, 0, 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n and text[j] not in '"\n':
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            continue
        if c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}" and depth:
            depth -= 1
            if depth == 0:
                out.append((start, text[start:i + 1]))
        i += 1
    if depth:
        out.append((start, text[start:]))
    return out


def problems_in(path, text):
    found = []
    for first, block in blocks(path, text):
        for offset, obj in objects(block):
            line = first + block.count("\n", 0, offset)
            if '"cmd"' in obj:
                m = REQUEST_API.search(obj)
                if m and int(m.group(1)) < API:
                    found.append((line, f"a request of API {m.group(1)}.x; the server speaks {API}.0"))
            m = SCHEMA_VERSION.search(obj)
            if m and int(m.group(1)) < SCHEMA and not NOT_ACQUISITION.search(obj):
                found.append((line, f"an acquisition configuration of schema {m.group(1)}.x; "
                                    f"convert it with tools/migrate_config.py"))
        if path.suffix == ".md":
            for k, row in enumerate(block.splitlines()):
                if row.lstrip().startswith("-> {") and '"api"' not in row:
                    found.append((first + k, 'a request without "api"; every request of 3.0 names it'))
    return sorted(set(found))


def files(root):
    yield from sorted((root / "book/src").rglob("*.md"))
    for p in sorted((root / "exercises").rglob("*")):
        if p.is_file() and p.suffix in TEXT_SUFFIXES and "__pycache__" not in p.parts:
            yield p


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    root = pathlib.Path(argv[1])
    count = 0
    for p in files(root):
        for line, what in problems_in(p, p.read_text(errors="replace")):
            print(f"{p.relative_to(root)}:{line}: {what}")
            count += 1
    print(f"interfaces in the book and the exercises: {count} problem(s)")
    return 1 if count else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
