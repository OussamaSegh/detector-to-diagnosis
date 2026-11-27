#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The printed book's volumes (roadmap 3.0.0, Theme K).

The Third Edition is printed in two volumes, because one paperback holds at most 828 pages. The
EPUB, the screen PDF, the Boox PDF, the web edition and the solutions manual stay single. The
list of the book's files (book/book.txt) marks where each volume starts with a comment line

    #volume 2: From Data to Diagnosis

and the files before the first marker belong to volume 1, whose title is given by a marker at the
top in the same way. This tool reads that list for book/build.sh:

  volumes.py count LIST                 the number of volumes (1 when the list has no marker)
  volumes.py title LIST N               volume N's title
  volumes.py files LIST N               volume N's files, one per line, as the list names them
  volumes.py offset LIST N              the chapter number before volume N's first chapter
                                        (the largest chNN of the volumes before it), so LaTeX
                                        numbers volume 2's chapters as the single book does
  volumes.py ids LIST OUT               writes OUT: one "identifier<TAB>volume" line per
                                        identifier defined in the book's sources, for
                                        filters/volumes.lua, which names the other volume in a
                                        cross-reference to it
  volumes.py check LIST                 every file in exactly one volume, every volume titled
                                        and not empty

Exit status 0 on success, 1 on a problem, 2 on wrong usage.
"""
import pathlib
import re
import sys

MARKER = re.compile(r"#volume\s+(\d+):\s*(.+?)\s*")
DEFINED = re.compile(r"[{ ]#([A-Za-z][\w:.-]*)")
CHAPTER = re.compile(r"\bch(\d+)-[\w-]+\.md$")


def read(list_path):
    """[(number, title, [files])] in order. A list without markers is one untitled volume."""
    volumes = [[1, "", []]]
    for raw in pathlib.Path(list_path).read_text().splitlines():
        line = raw.strip()
        m = MARKER.fullmatch(line)
        if m:
            n = int(m.group(1))
            if volumes[-1][2] or n != volumes[-1][0]:
                volumes.append([n, m.group(2), []])
            else:
                volumes[-1][1] = m.group(2)
            continue
        if not line or line.startswith("#"):
            continue
        volumes[-1][2].append(line)
    return [tuple(v) for v in volumes]


def problems(volumes):
    out = []
    numbers = [n for n, _, _ in volumes]
    if numbers != list(range(1, len(volumes) + 1)):
        out.append(f"volumes are numbered {numbers}, not 1 to {len(volumes)} in order")
    seen = {}
    for n, title, files in volumes:
        if len(volumes) > 1 and not title:
            out.append(f"volume {n} has no title (#volume {n}: Title)")
        if not files:
            out.append(f"volume {n} has no files")
        for f in files:
            if f in seen:
                out.append(f"{f} is in volume {seen[f]} and volume {n}")
            seen[f] = n
    return out


def volume(volumes, n):
    for v in volumes:
        if v[0] == n:
            return v
    raise SystemExit(f"no volume {n}")


def offset(volumes, n):
    last = 0
    for number, _, files in volumes:
        if number >= n:
            break
        for f in files:
            m = CHAPTER.search(f)
            if m:
                last = max(last, int(m.group(1)))
    return last


def ids(volumes, root):
    found = {}
    for n, _, files in volumes:
        for f in files:
            for m in DEFINED.finditer((root / f).read_text()):
                found.setdefault(m.group(1), n)
    return found


def main(argv):
    if len(argv) < 3 or argv[1] not in ("count", "title", "files", "offset", "ids", "check"):
        print(__doc__.split("\n\n")[2], file=sys.stderr)
        return 2
    cmd, list_path = argv[1], pathlib.Path(argv[2])
    volumes = read(list_path)
    if cmd == "check":
        bad = problems(volumes)
        for p in bad:
            print(f"{list_path}: {p}")
        print(f"volumes: {len(volumes)}, {len(bad)} problem(s)")
        return 1 if bad else 0
    if cmd == "count":
        print(len(volumes))
        return 0
    if len(argv) != 4:
        return 2
    if cmd == "ids":
        found = ids(volumes, list_path.parent)
        pathlib.Path(argv[3]).write_text("".join(f"{k}\t{v}\n" for k, v in sorted(found.items())))
        return 0
    n = int(argv[3])
    if cmd == "title":
        print(volume(volumes, n)[1])
    elif cmd == "files":
        print("\n".join(volume(volumes, n)[2]))
    else:
        print(offset(volumes, n))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
