#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Builds the book's figures (book/docs/PLAN-interior-design.md, section 4).

A figure is a block in a chapter:

    ```{.figure src="book/figures/tikz/ch08-annihilation.tex" #fig:ch08-annihilation
        caption="..." alt="..." width="90%" inputs="measurements/ch12/sino"}
    ```

src is a TikZ picture (.tex), a Python script (.py, using book/figures/lib/d2d.py), or a photo
(.jpg or .png under book/figures/photos/, with its credit in credits.json: roadmap 2.3.0,
Theme I, and CR-0039). The
figure is built once per (source, inputs, shared style files, profile, Part, format) into
book/build/figures/<hash>.<pdf|svg>, so a warm build costs nothing.

    figures.py build SRC PROFILE PART FMT [INPUTS]   build one, print its path
    figures.py all [PROFILE...]                      build every figure of the book, in parallel
    figures.py check                                 the checks of section 4 (book.figures)
    figures.py credits [--write]                     the photo credits page, from credits.json
"""
import base64
import concurrent.futures
import datetime
import hashlib
import io
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
PHOTOS = BOOK / "figures" / "photos"
CREDITS = PHOTOS / "credits.json"
CREDITS_PAGE = BOOK / "src" / "back" / "photo-credits.md"
PHOTO_SUFFIXES = (".jpg", ".jpeg", ".png")
# The photo policy (docs/ROADMAP-2.3.0-illustrations.md, section 3): public domain, CC0 or CC BY,
# never BY-SA, NC, ND, GFDL-only or a product photo. The value is the label a caption cites.
LICENSES = {"PD": "public domain", "CC0-1.0": "CC0 1.0", "CC-BY-3.0": "CC BY 3.0", "CC-BY-4.0": "CC BY 4.0"}
CREDIT_FIELDS = ("file", "title", "source", "author", "license", "license_url", "read_on", "read_by",
                 "sha256", "changes")
# Metadata a photo must not carry: EXIF (GPS, camera serial), XMP, IPTC, comments, PNG text.
FORBIDDEN_INFO = ("exif", "xmp", "XML:com.adobe.xmp", "photoshop", "iptc", "comment")
ALLOWED_INFO = ("dpi", "gamma", "icc_profile", "transparency", "progressive", "progression", "jfif",
                "jfif_version", "jfif_unit", "jfif_density", "adobe", "adobe_transform", "srgb",
                "chromaticity", "interlace", "aspect", "loop", "background", "duration")
PRINT_PPI = 300
TEXT_WIDTH_IN = 6.65  # the text width of the 8.5 x 11 in page (book/figures/lib/d2d.py)
EPUB_LONG_PX = 1600
EPUB_MAX_BYTES = 400_000
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
        if srcp.suffix.lower() in PHOTO_SUFFIXES:
            out = tmp / f"fig.{fmt}"
            build_photo(srcp, profile, fmt, out)
        elif srcp.suffix == ".py":
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


def build_photo(srcp, profile, fmt, out):
    """A photo for one profile: gray with its contrast stretched for black ink (bw); a PDF at
    300 ppi for LaTeX; for the EPUB an SVG that holds a JPEG of at most 1600 px on its long
    side, so that every format of a figure goes through the same path."""
    from PIL import Image, ImageOps

    img = Image.open(srcp)
    img = ImageOps.exif_transpose(img).convert("RGB")
    if profile == "bw":
        img = ImageOps.autocontrast(ImageOps.grayscale(img), cutoff=1).convert("RGB")
    if fmt == "pdf":
        img.save(out, "PDF", resolution=PRINT_PPI)
        return
    if max(img.size) > EPUB_LONG_PX:
        img.thumbnail((EPUB_LONG_PX, EPUB_LONG_PX), Image.LANCZOS)
    for quality in (85, 75, 65, 55):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality, optimize=True)
        if buf.tell() <= EPUB_MAX_BYTES:
            break
    w, h = img.size
    data = base64.b64encode(buf.getvalue()).decode()
    out.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                   f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
                   f'<image width="{w}" height="{h}" xlink:href="data:image/jpeg;base64,{data}"/></svg>\n')


def load_credits(path=CREDITS):
    if not path.is_file():
        return []
    return json.loads(path.read_text())["photos"]


def credit_line(c):
    """The short credit a caption ends with."""
    return f"Photo: {c['author']}, {LICENSES.get(c['license'], c['license'])}."


def photo_problems(photos_dir, credits, figure_blocks):
    """The photo policy's checks. photos_dir holds the photos, credits is the list of
    credits.json, figure_blocks the (where, attributes) of the figures whose source is a photo."""
    from PIL import Image

    problems = []
    by_file = {}
    for c in credits:
        name = c.get("file", "?")
        if name in by_file:
            problems.append(f"credits: {name} has two entries")
        by_file[name] = c
        for f in CREDIT_FIELDS:
            if not str(c.get(f, "")).strip():
                problems.append(f"credits: {name}: no {f}")
        if c.get("license") not in LICENSES:
            problems.append(f"credits: {name}: license {c.get('license')!r} is not allowed "
                            f"(only {', '.join(LICENSES)})")
        try:
            datetime.date.fromisoformat(str(c.get("read_on", "")))
        except ValueError:
            problems.append(f"credits: {name}: read_on is not a date (YYYY-MM-DD)")
        for f in ("source", "license_url"):
            if c.get(f) and not str(c[f]).startswith("https://"):
                problems.append(f"credits: {name}: {f} is not an https URL")
        p = photos_dir / name
        if not p.is_file():
            problems.append(f"credits: {name}: no such file in {photos_dir.name}/")
            continue
        if hashlib.sha256(p.read_bytes()).hexdigest() != c.get("sha256"):
            problems.append(f"credits: {name}: the SHA-256 does not match the file")
        with Image.open(p) as img:
            left = [k for k in img.info if k in FORBIDDEN_INFO or k not in ALLOWED_INFO]
            if len(img.getexif()) or left:
                problems.append(f"{name}: metadata left in the file ({', '.join(sorted(left)) or 'EXIF'}): strip it")
            c["_px"] = img.size
    if photos_dir.is_dir():
        for p in sorted(photos_dir.iterdir()):
            if p.suffix.lower() in PHOTO_SUFFIXES and p.name not in by_file:
                problems.append(f"{p.name}: no entry in credits.json")
    for where, a in figure_blocks:
        name = pathlib.Path(a.get("src", "")).name
        c = by_file.get(name)
        if c is None:
            problems.append(f"{where}: photo {name} has no credit")
            continue
        if not a.get("caption", "").rstrip().endswith(credit_line(c)):
            problems.append(f"{where}: the caption must end with the credit \"{credit_line(c)}\"")
        width = float(a.get("width", "100%").rstrip("%")) / 100
        need = round(PRINT_PPI * TEXT_WIDTH_IN * width)
        if "_px" in c and c["_px"][0] < need:
            problems.append(f"{where}: {name} is {c['_px'][0]} px wide; {need} px are needed for "
                            f"{PRINT_PPI} ppi at {a.get('width', '100%')}")
    return problems


def credits_page(credits):
    """book/src/back/photo-credits.md, generated from credits.json."""
    lines = ["# Photo credits {.unnumbered}", "",
             "The photos in this book are by the people named below, under the licenses named; "
             "they are not under the book's own terms (book/LICENSE). A photo marked as changed "
             "was cropped, retouched or turned gray for print.", ""]
    for c in sorted(credits, key=lambda c: c["file"]):
        lines.append(f"- **{c['title']}.** {c['author']}, {LICENSES.get(c['license'], c['license'])} "
                     f"(<{c['license_url']}>). Source: <{c['source']}>. Changes: {c['changes']}.")
    return "\n".join(lines) + "\n"


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
    if md.parent.name == "appendix":
        return "A"
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
    photo_blocks = [(f"{md.relative_to(ROOT)}: {a.get('id')}", a) for md, a in blocks()
                    if pathlib.Path(a.get("src", "")).suffix.lower() in PHOTO_SUFFIXES]
    for md, a in blocks():
        src = pathlib.Path(a.get("src", ""))
        if src.suffix.lower() in PHOTO_SUFFIXES and (ROOT / src).parent != PHOTOS:
            problems.append(f"{md.relative_to(ROOT)}: {a.get('id')}: a photo must be under book/figures/photos/")
    credits = load_credits()
    problems += photo_problems(PHOTOS, credits, photo_blocks)
    if credits:
        if not CREDITS_PAGE.is_file() or CREDITS_PAGE.read_text() != credits_page(credits):
            problems.append("book/src/back/photo-credits.md is not current: figures.py credits --write")
        if "src/back/photo-credits.md" not in (BOOK / "book.txt").read_text():
            problems.append("book/book.txt does not include src/back/photo-credits.md")
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
    elif cmd == ["credits"]:
        page = credits_page(load_credits())
        if sys.argv[2:3] == ["--write"]:
            CREDITS_PAGE.parent.mkdir(parents=True, exist_ok=True)
            CREDITS_PAGE.write_text(page)
        else:
            print(page, end="")
    else:
        sys.exit(__doc__)
