#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Builds the book's figures (book/docs/PLAN-interior-design.md, section 4).

A figure is a block in a chapter:

    ```{.figure src="book/figures/tikz/ch08-annihilation.tex" #fig:ch08-annihilation
        caption="..." alt="..." width="90%" inputs="measurements/ch12/sino"}
    ```

src is a TikZ picture (.tex) or a Python script (.py, using book/figures/lib/d2d.py). The
figure is built once per (source, inputs, shared style files, profile, Part, format) into
book/build/figures/<hash>.<pdf|svg>, so a warm build costs nothing.

    figures.py build SRC PROFILE PART FMT [INPUTS]   build one, print its path
    figures.py all [PROFILE...]                      build every figure of the book, in parallel
    figures.py check                                 the checks of section 4 (book.figures)
"""
import concurrent.futures
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
BOOK = HERE.parent
ROOT = BOOK.parent
OUT = BOOK / "build" / "figures"
SHARED = [BOOK / "figures/lib/d2d.py", BOOK / "figures/tikz/d2d-figure.tex",
          HERE / "palette.json", HERE / "palette.py", pathlib.Path(__file__)]
BLOCK = re.compile(r"^```\{\.figure ([^\n]*)\}\s*$", re.M)
ATTR = re.compile(r'([\w-]+)="((?:[^"\\]|\\.)*)"')

TIKZ_DOC = r"""\documentclass[border=2pt]{standalone}
\usepackage{fontspec}
\setmainfont{TeX Gyre Pagella}\setsansfont{TeX Gyre Heros}\setmonofont[Scale=0.92]{Inconsolata}
\usepackage{unicode-math}\setmathfont{TeX Gyre Pagella Math}
\usepackage{xcolor}
\usepackage{tikz}
\input{palette.tex}
\colorlet{partcolor}{d2dpart%(part)s}
\input{d2d-figure.tex}
\begin{document}
\input{%(src)s}
\end{document}
"""


def digest(src, profile, part, fmt, inputs):
    h = hashlib.sha1()
    for p in [ROOT / src] + SHARED:
        h.update(p.read_bytes())
    for inp in (inputs or "").split():
        p = ROOT / inp
        files = sorted(p.rglob("*")) if p.is_dir() else [p]
        for f in files:
            if f.is_file():
                h.update(str(f.relative_to(ROOT)).encode())
                h.update(f.read_bytes())
    h.update(f"{profile}|{part}|{fmt}".encode())
    return h.hexdigest()


def build(src, profile, part, fmt, inputs=""):
    """The path of the built figure; builds it if it is not in the cache."""
    OUT.mkdir(parents=True, exist_ok=True)
    key = digest(src, profile, part, fmt, inputs)
    dst = OUT / f"{key}.{fmt}"
    if dst.exists():
        return dst
    srcp = ROOT / src
    with tempfile.TemporaryDirectory(dir=OUT) as tmp:
        tmp = pathlib.Path(tmp)
        env = dict(os.environ, D2D_PROFILE=profile, D2D_PART=str(part),
                   PYTHONPATH=str(BOOK / "figures/lib"), MPLCONFIGDIR=str(tmp / "mpl"))
        if srcp.suffix == ".py":
            out = tmp / f"fig.{fmt}"
            r = subprocess.run([sys.executable, str(srcp), str(out)], cwd=ROOT, env=env,
                               capture_output=True, text=True)
            if r.returncode != 0 or not out.exists():
                raise RuntimeError(f"figures: {src} failed\n{r.stdout}{r.stderr}")
        elif srcp.suffix == ".tex":
            subprocess.run([sys.executable, str(HERE / "palette.py"), "tex", profile,
                            str(tmp / "palette.tex")], check=True)
            (tmp / "fig.tex").write_text(TIKZ_DOC % {"part": part, "src": srcp})
            env["TEXINPUTS"] = f"{BOOK / 'figures/tikz'}:"
            r = subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", "fig.tex"],
                               cwd=tmp, env=env, capture_output=True, text=True)
            if r.returncode != 0:
                log = (tmp / "fig.log").read_text(errors="replace")
                err = "\n".join(line for line in log.splitlines() if line.startswith("!") or line.startswith("l."))
                raise RuntimeError(f"figures: {src} failed\n{err}")
            out = tmp / "fig.pdf"
            if fmt == "svg":
                subprocess.run(["pdftocairo", "-svg", str(out), str(tmp / "fig.svg")], check=True)
                out = tmp / "fig.svg"
        else:
            raise RuntimeError(f"figures: {src}: unknown kind of source")
        if fmt == "svg":
            # EPUB 3 forbids an external DTD; matplotlib and cairo write none, but be sure.
            text = re.sub(r"<!DOCTYPE[^>]*>\s*", "", out.read_text(), count=1)
            out.write_text(text)
        shutil.move(str(out), dst)
    return dst


def blocks():
    """Every figure block of the book and the solutions: (file, attributes)."""
    out = []
    for lst in ("book.txt", "solutions.txt"):
        for line in (BOOK / lst).read_text().splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            md = BOOK / line.strip()
            for m in BLOCK.finditer(md.read_text()):
                attrs = dict(ATTR.findall(m.group(1)))
                ident = re.search(r"#([\w:-]+)", m.group(1))
                attrs["id"] = ident.group(1) if ident else ""
                out.append((md, attrs))
    return out


def chapter_part(md):
    n = re.search(r"ch(\d\d)", md.name)
    if not n:
        return "0"
    n = int(n.group(1))
    for part, last in ((1, 7), (2, 12), (3, 17), (4, 21), (5, 25), (6, 30), (7, 32), (8, 34), (9, 37)):
        if n <= last:
            return str(part)
    return "0"


def build_all(profiles):
    jobs = []
    for md, a in blocks():
        part = chapter_part(md)
        for profile in profiles:
            fmts = ["pdf", "svg"] if profile == "screen" else ["pdf"]
            for fmt in fmts:
                jobs.append((a["src"], profile, part, fmt, a.get("inputs", "")))
    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as ex:
        futs = {ex.submit(build, *j): j for j in jobs}
        bad = 0
        for f in concurrent.futures.as_completed(futs):
            try:
                f.result()
            except Exception as e:  # noqa: BLE001 - report every failing figure
                bad += 1
                print(e, file=sys.stderr)
    print(f"figures: {len(jobs)} built or cached, {bad} failed")
    return 1 if bad else 0


def check():
    """Every figure: an id, a caption, alt text of at least 40 characters that is not the
    caption, a source in the repository, referenced in its chapter's text; and the palette's
    contrast check."""
    problems = []
    seen = set()
    for md, a in blocks():
        where = f"{md.relative_to(ROOT)}: {a.get('id') or a.get('src')}"
        if not a.get("id"):
            problems.append(f"{where}: no id")
        elif a["id"] in seen:
            problems.append(f"{where}: id used twice")
        seen.add(a.get("id"))
        if not a.get("caption"):
            problems.append(f"{where}: no caption")
        alt = a.get("alt", "")
        if len(alt) < 40:
            problems.append(f"{where}: alt text missing or shorter than 40 characters")
        if alt and alt == a.get("caption"):
            problems.append(f"{where}: alt text repeats the caption")
        if not (ROOT / a.get("src", "")).is_file():
            problems.append(f"{where}: source {a.get('src')} not found")
        for inp in a.get("inputs", "").split():
            if not (ROOT / inp).exists():
                problems.append(f"{where}: input {inp} not found")
        if a.get("id") and f"@{a['id']}" not in md.read_text() and f"#{a['id']})" not in md.read_text():
            problems.append(f"{where}: not referenced in the text ([Figure](#{a['id']}))")
    r = subprocess.run([sys.executable, str(HERE / "palette.py"), "check"], capture_output=True, text=True)
    if r.returncode != 0:
        problems.append(r.stdout.strip())
    for p in problems:
        print("figures:", p)
    print(f"figures: {len(blocks())} figures, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    if cmd == ["build"]:
        print(build(*sys.argv[2:7]))
    elif cmd == ["all"]:
        sys.exit(build_all(sys.argv[2:] or ["screen", "boox", "bw"]))
    elif cmd == ["check"]:
        sys.exit(check())
    else:
        sys.exit(__doc__)
