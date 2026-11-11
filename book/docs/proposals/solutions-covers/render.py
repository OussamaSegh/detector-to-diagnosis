#!/usr/bin/env python3
"""Three front-cover proposals for the solutions manual. Not used by book/build.sh.

The live solutions cover is Inverse, drawn by book/tools/cover_art.py and
book/assets/cover.tex. These files are the record of the three options. The trim
is 8.5 x 11 in, including an Amazon thumbnail. Type sits at least 0.58 in inside.

    python3 book/docs/proposals/solutions-covers/render.py

Writes inverse.png, band.png, key.png, plate.png (the live book cover, for the
comparison), contact-full.png and contact-thumb.png.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "book" / "tools"))
import cover_art  # noqa: E402  the book's phantom and MLEM, not its cover

HERE = Path(__file__).resolve().parent
DPI = 160
W, H = round(8.5 * DPI), round(11 * DPI)
SAFE = 0.58 * DPI

GAR = "/usr/share/fonts/opentype/ebgaramond/EBGaramond12-Regular.otf"
GAR_IT = "/usr/share/fonts/opentype/ebgaramond/EBGaramond12-Italic.otf"
GAR_BOLD = "/usr/share/fonts/opentype/ebgaramond/EBGaramond12-Bold.otf"
INT = "/usr/share/fonts/truetype/macos/Inter-Regular.ttf"
INT_MED = "/usr/share/fonts/truetype/macos/Inter-Medium.ttf"

PAPER = (246, 241, 231)
INK = (22, 20, 18)
CREAM = (245, 239, 228)
TEAL = (15, 118, 110)       # Part I
ROSE = (159, 18, 57)        # Part III
VIOLET = (76, 29, 122)      # Solutions, darkened so cream clears 4.5:1
MUTE = (90, 78, 66)

AUTHOR = "Oussama Seghaier"
COMPANION = "Companion to Detector to Diagnosis"


def px(inches: float) -> int:
    return int(round(inches * DPI))


def font(path: str, pt: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, max(1, round(pt * DPI / 72)))


def fit(path: str, text: str, width: float, lo: float, hi: float) -> ImageFont.FreeTypeFont:
    """Largest point size in [lo, hi] at which text is no wider than width."""
    best = lo
    while hi - lo > 0.4:
        mid = (lo + hi) / 2
        if font(path, mid).getlength(text) <= width:
            best = mid
            lo = mid
        else:
            hi = mid
    return font(path, best)


def tracked(draw, xy, text, face, fill, tracking: float) -> float:
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=face, fill=fill)
        x += face.getlength(ch) + tracking
    return x


def text_width(face, text, tracking=0.0) -> float:
    return face.getlength(text) + tracking * max(0, len(text) - 1)


def luminance(rgb) -> float:
    def f(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (f(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def plate_image(recon, stops, size) -> Image.Image:
    """The book's reconstruction, cropped as on the live Plate cover, recolored."""
    v = cover_art.plate_tone(recon)
    n = v.shape[0]
    m = int(round(n * 0.14))
    crop = v[m:n - m, m:n - m]
    hexstops = [(a, "{:02X}{:02X}{:02X}".format(*c)) for a, c in stops]
    rgb = cover_art.colormap(hexstops, crop)
    im = Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8), mode="RGB")
    return im.resize(size, Image.Resampling.LANCZOS)


PLATE_STOPS = [
    (0.00, (8, 10, 14)),
    (0.08, (12, 16, 28)),
    (0.22, (36, 24, 72)),
    (0.40, (14, 78, 84)),
    (0.58, (168, 122, 58)),
    (0.78, (236, 214, 176)),
    (1.00, (252, 246, 234)),
]
# A print on paper: the bore stays paper, the cortex goes to teal and ink.
PRINT_STOPS = [
    (0.00, PAPER),
    (0.20, (232, 224, 208)),
    (0.42, (168, 196, 188)),
    (0.62, TEAL),
    (0.82, (24, 72, 68)),
    (1.00, INK),
]


def draw_name(draw, x, y, fill, manual_fill, measure, solutions_max: float = 108) -> int:
    """SOLUTIONS over MANUAL, the largest pair that fits the measure. Returns the y under it."""
    solutions = fit(GAR_BOLD, "SOLUTIONS", measure, 54, solutions_max)
    manual = fit(GAR, "MANUAL", measure * 0.72, 28, solutions_max * 0.56)
    draw.text((x, y), "SOLUTIONS", font=solutions, fill=fill)
    y2 = y + solutions.size + px(0.02)
    draw.text((x, y2), "MANUAL", font=manual, fill=manual_fill)
    return y2 + manual.size + px(0.06)


def draw_series(draw, x, y, ink, accent) -> int:
    """The series title, secondary to SOLUTIONS. Returns the y under it."""
    face = font(GAR, 26)
    ital = font(GAR_IT, 26)
    draw.text((x, y), "Detector", font=face, fill=ink)
    w = face.getlength("Detector ")
    draw.text((x + w, y), "to", font=ital, fill=accent)
    w += ital.getlength("to ")
    draw.text((x + w, y), "Diagnosis", font=face, fill=ink)
    return y + face.size + px(0.04)


def draw_companion(draw, x, y, fill) -> int:
    face = font(INT, 15)
    draw.text((x, y), COMPANION, font=face, fill=fill)
    return y + face.size + px(0.02)


def draw_author(draw, fill, y=None):
    face = font(INT, 15)
    tw = face.getlength(AUTHOR)
    if y is None:
        y = H - SAFE - face.size
    draw.text((W - SAFE - tw, y), AUTHOR, font=face, fill=fill)


def rule(draw, y, color, x0=None, x1=None, weight=1.75):
    draw.line([(0 if x0 is None else x0, y), (W if x1 is None else x1, y)],
              fill=color, width=max(2, round(weight * DPI / 72)))


def inverse(recon) -> Image.Image:
    """The Plate grid on paper. Teal stands in for the book's gold."""
    im = Image.new("RGB", (W, H), PAPER)
    picture = plate_image(recon, PRINT_STOPS, (W, H - px(4.15)))
    im.paste(picture, (0, 0))
    d = ImageDraw.Draw(im)
    y = H - px(4.15)
    rule(d, y, TEAL)
    y += px(0.28)
    y = draw_name(d, SAFE, y, INK, TEAL, W - 2 * SAFE)
    y = draw_companion(d, SAFE, y + px(0.06), MUTE)
    draw_series(d, SAFE, y + px(0.08), INK, TEAL)
    draw_author(d, INK)
    return im


def band(recon) -> Image.Image:
    """The same photograph, with a rose band where the book has its ink band."""
    im = Image.new("RGB", (W, H), ROSE)
    picture = plate_image(recon, PLATE_STOPS, (W, H - px(4.05)))
    im.paste(picture, (0, 0))
    d = ImageDraw.Draw(im)
    y = H - px(4.05)
    rule(d, y, (255, 236, 214), weight=2.25)
    y += px(0.22)
    y = draw_name(d, SAFE, y, CREAM, (255, 228, 196), W - 2 * SAFE)
    y = draw_companion(d, SAFE, y + px(0.04), (255, 228, 206))
    # The series title sits on the same line as the author, so the band stays one shout.
    face = font(GAR, 20)
    ital = font(GAR_IT, 20)
    d.text((SAFE, H - SAFE - face.size), "Detector", font=face, fill=CREAM)
    w = face.getlength("Detector ")
    d.text((SAFE + w, H - SAFE - ital.size), "to", font=ital, fill=(255, 214, 170))
    w += ital.getlength("to ")
    d.text((SAFE + w, H - SAFE - face.size), "Diagnosis", font=face, fill=CREAM)
    draw_author(d, CREAM)
    return im


def _marks(recon):
    """Three real places in the cropped slice: cortex, ventricle, striatum. Row, col in 0..1."""
    v = cover_art.plate_tone(recon)
    n = v.shape[0]
    m = int(round(n * 0.14))
    crop = v[m:n - m, m:n - m]
    h, w = crop.shape
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = (h - 1) / 2, (w - 1) / 2
    r = np.hypot((yy - cy) / (h / 2), (xx - cx) / (w / 2))
    cortex = crop.copy()
    cortex[(r < 0.62) | (r > 0.92)] = 0
    ventricle = crop.copy()
    ventricle[r > 0.28] = 1
    striatum = crop.copy()
    striatum[(r < 0.22) | (r > 0.55) | (xx > cx)] = 0
    picks = [cortex.argmax(), ventricle.argmin(), striatum.argmax()]
    out = []
    for flat in picks:
        row, col = divmod(int(flat), w)
        out.append((col / (w - 1), row / (h - 1)))
    return out


def key(recon) -> Image.Image:
    """The slice as a worked figure: paper, a frame, and violet answer marks."""
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    kicker = font(INT_MED, 12)
    tracked(d, (SAFE, px(0.48)), "ANSWER KEY", kicker, VIOLET, px(0.045))
    y = draw_series(d, SAFE, px(0.82), INK, VIOLET)
    rule(d, y + px(0.02), VIOLET, SAFE, SAFE + px(1.55))

    side = px(5.05)
    x0 = (W - side) // 2
    y0 = px(2.20)
    picture = plate_image(recon, PRINT_STOPS, (side, side))
    im.paste(picture, (x0, y0))
    d = ImageDraw.Draw(im)
    frame = max(2, round(1.5 * DPI / 72))
    d.rectangle([x0, y0, x0 + side, y0 + side], outline=INK, width=frame)

    labels = ("cortex", "ventricle", "striatum")
    face = font(INT_MED, 13)
    num = font(INT_MED, 15)
    radius = px(0.16)
    for i, ((u, v), label) in enumerate(zip(_marks(recon), labels), start=1):
        cx = x0 + int(u * side)
        cy = y0 + int(v * side)
        # Park the number just outside the activity so the mark reads as a note.
        ox = px(0.38) if u < 0.5 else -px(0.38)
        oy = -px(0.34) if v > 0.45 else px(0.28)
        nx, ny = cx + ox, cy + oy
        d.line([(cx, cy), (nx, ny)], fill=VIOLET, width=max(2, round(1.5 * DPI / 72)))
        d.ellipse([nx - radius, ny - radius, nx + radius, ny + radius], fill=VIOLET)
        glyph = str(i)
        gw = num.getlength(glyph)
        gb = num.getbbox(glyph)
        d.text((nx - gw / 2, ny - (gb[3] - gb[1]) / 2 - gb[1]), glyph, font=num, fill=CREAM)
        tw = face.getlength(label)
        lx = nx - tw - px(0.10) if u > 0.5 else nx + radius + px(0.08)
        d.text((lx, ny - face.size / 2), label, font=face, fill=VIOLET)

    foot = H - px(3.35)
    d.rectangle([0, foot, W, H], fill=VIOLET)
    rule(d, foot, CREAM, weight=2)
    y = foot + px(0.20)
    y = draw_name(d, SAFE, y, CREAM, (232, 220, 245), W - 2 * SAFE, solutions_max=86)
    draw_companion(d, SAFE, y + px(0.02), CREAM)
    draw_author(d, CREAM)
    return im


def live_plate() -> Image.Image:
    """The book cover as cover.tex sets it, scaled to this sheet."""
    assets = ROOT / "book" / "assets"
    with tempfile.TemporaryDirectory() as tmp:
        cmd = (
            f"\\def\\nlfvolume{{book}}\\def\\nlfauthor{{{AUTHOR}}}"
            f"\\def\\nlfassets{{{assets}}}\\input{{{assets / 'cover.tex'}}}"
        )
        subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error",
             "-output-directory", tmp, "-jobname", "plate", cmd],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        png = Path(tmp) / "plate.png"
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(DPI), "-singlefile", str(Path(tmp) / "plate.pdf"),
             str(png.with_suffix(""))],
            check=True,
        )
        im = Image.open(png).convert("RGB")
        return im.resize((W, H), Image.Resampling.LANCZOS)


def contact(covers: list[tuple[str, Image.Image]], width: int | None) -> Image.Image:
    gap = 28 if width is None else 16
    label_h = 54 if width is None else 36
    pad = 28 if width is None else 16
    tiles = []
    for _name, im in covers:
        if width is None:
            tiles.append(im)
        else:
            tiles.append(im.resize((width, round(im.height * width / im.width)), Image.Resampling.LANCZOS))
    tw, th = tiles[0].size
    sheet = Image.new("RGB", (pad * 2 + tw * len(tiles) + gap * (len(tiles) - 1),
                              pad * 2 + th + label_h), (236, 232, 224))
    d = ImageDraw.Draw(sheet)
    face = font(INT_MED, 13 if width else 16)
    for i, ((name, _), tile) in enumerate(zip(covers, tiles)):
        x = pad + i * (tw + gap)
        sheet.paste(tile, (x, pad))
        d.text((x, pad + th + 8), name, font=face, fill=INK)
    return sheet


def main() -> None:
    print("scan...")
    _truth, _sino, recon = cover_art.scan(n=200, n_angles=180, counts=2.0e7, iters=22)
    print("covers...")
    made = {
        "inverse": inverse(recon),
        "band": band(recon),
        "key": key(recon),
    }
    print("live plate...")
    plate = live_plate()
    made["plate"] = plate
    for name, im in made.items():
        im.save(HERE / f"{name}.png", optimize=True)
        print(f"wrote {name}.png {im.size}")
    order = [("Plate", plate), ("Inverse", made["inverse"]),
             ("Band", made["band"]), ("Key", made["key"])]
    contact(order, None).save(HERE / "contact-full.png", optimize=True)
    contact(order, 160).save(HERE / "contact-thumb.png", optimize=True)
    pairs = [
        ("SOLUTIONS on paper", INK, PAPER),
        ("MANUAL on paper", TEAL, PAPER),
        ("SOLUTIONS on rose", CREAM, ROSE),
        ("series title on rose", CREAM, ROSE),
        ("SOLUTIONS on violet", CREAM, VIOLET),
        ("marks on paper", VIOLET, PAPER),
        ("companion on paper", MUTE, PAPER),
    ]
    for name, fg, bg in pairs:
        ratio = contrast(fg, bg)
        print(f"contrast {name}: {ratio:.2f}")
        if ratio < 4.5:
            raise SystemExit(f"{name} is below 4.5:1")


if __name__ == "__main__":
    main()
