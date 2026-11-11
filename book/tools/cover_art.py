# SPDX-License-Identifier: MIT
"""Raster artwork of the covers (book/assets/cover.tex): the Plate design.

A brain phantom (an FDG-like axial slice) is forward projected into a sinogram, given Poisson
noise and reconstructed with MLEM. The book's front is that reconstruction, edge to edge, above
an ink band; the solutions manual is the Inverse design, the same slice printed in teal and ink
on paper above a paper band. cover.tex sets the type. Each back is the field its spine uses
(ink for the book, paper for the solutions), with the four steps of the pipeline.

    python3 book/tools/cover_art.py [--out book/assets] [--dpi 300]

writes cover-front-<volume>.jpg and cover-back-<volume>.jpg for volume = book and solutions.
The output is deterministic (fixed seeds) and is committed, so building the book needs only
XeLaTeX. Needs numpy, scipy and Pillow (the versions of analysis/requirements.lock).

The field is flat, the same color cover.tex paints the spine, so the back panel meets the spine
without a seam. Positions are in inches on the trimmed panel (origin at its lower left corner);
the constants marked "shared with cover.tex" must match the ones there. The solutions band is
taller than the book's, so SOLUTIONS and MANUAL fit.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

TRIM_W, TRIM_H, BLEED = 8.5, 11.0, 0.125

# Shared with cover.tex. BAND is the book's ink band; SOLUTIONS_BAND is the Inverse paper band.
# The back panels sit above the barcode area (x 6.25..8.25, y 0.25..1.45), which cover.tex
# leaves empty.
BAND = 3.45
SOLUTIONS_BAND = 4.15
IMAGE_SPAN = 0.86                       # half side of a panel image, over the panel ring radius
PANEL_Y, PANEL_S = 2.55, 1.42          # back panels: bottom edge and side
PANEL_X = (0.75, 2.62, 4.49, 6.36)     # back panels: left edges

# The book's plate: ink, gold, and the reconstruction's colors.
_PLATE = {
    "bg_top": "100E0C", "bg_bottom": "100E0C",
    "gold": "C49A54", "cream": "F5EFE4",
    # The stops of the Plate proposal: black ground, violet, teal, gold, cream.
    "cmap": [(0.00, "080A0E"), (0.08, "0C101C"), (0.22, "241848"), (0.40, "0E4E54"),
             (0.58, "A87A3A"), (0.78, "ECD6B0"), (1.00, "FCF6EA")],
}
# Inverse: paper ground, Part I teal, ink. The same lightness ordering the KDP black-ink
# profile keeps, so the slice and the type still separate in gray.
_INVERSE = {
    "bg_top": "F6F1E7", "bg_bottom": "F6F1E7",
    "gold": "0F766E", "cream": "161412", "on_paper": True,
    "cmap": [(0.00, "F6F1E7"), (0.20, "E8E0D0"), (0.42, "A8C4BC"), (0.62, "0F766E"),
             (0.82, "184844"), (1.00, "161412")],
}
PALETTES = {"book": _PLATE, "solutions": _INVERSE}
BANDS = {"book": BAND, "solutions": SOLUTIONS_BAND}


def rgb(hexstr: str) -> np.ndarray:
    return np.array([int(hexstr[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64) / 255.0


def colormap(stops, v: np.ndarray) -> np.ndarray:
    """Maps values in [0, 1] to RGB by linear interpolation between the stops."""
    v = np.clip(v, 0.0, 1.0)
    xs = np.array([s[0] for s in stops])
    cs = np.array([rgb(s[1]) for s in stops])
    return np.stack([np.interp(v, xs, cs[:, k]) for k in range(3)], axis=-1)


def smoothstep(e0: float, e1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------------------------
# The simulated scan.

def phantom(n: int) -> np.ndarray:
    """An FDG-like axial brain slice at the level of the basal ganglia, on an n x n grid spanning
    [-1, 1]^2 (front at the top): a folded cortical ribbon, white matter, the deep gray nuclei
    and cold ventricles."""
    y, x = np.mgrid[1:-1:n * 1j, -1:1:n * 1j]
    rng = np.random.default_rng(1)

    def ellipse(cx, cy, a, b, deg=0.0):
        t = math.radians(deg)
        u = (x - cx) * math.cos(t) + (y - cy) * math.sin(t)
        w = -(x - cx) * math.sin(t) + (y - cy) * math.cos(t)
        return (u / a) ** 2 + (w / b) ** 2

    def field(sigma):
        f = ndimage.gaussian_filter(rng.standard_normal((n, n)), sigma * n)
        return f / f.std()

    th = np.arctan2(y, x)
    # The outline: an ellipse, a little wider at the back, with a wavy surface.
    outline = 1 + 0.035 * np.sin(23 * th) + 0.02 * np.sin(31 * th + 1.3) - 0.04 * np.sin(th)
    rho = np.sqrt(ellipse(0, 0, 0.74, 0.90)) / outline
    brain = rho <= 1.0
    img = np.where(brain, 0.36, 0.0)                      # white matter
    # The cortical ribbon, folded: its inner edge moves with smooth noise.
    folds = 0.73 + 0.07 * field(0.035) + 0.03 * np.sin(18 * th)
    gray = brain & (rho > folds)
    img[gray] = 1.0
    sulci = brain & (rho > 0.80) & (np.abs(field(0.02)) < 0.16)
    img[sulci] = 0.42
    img[gray] *= 1 + 0.12 * smoothstep(-0.35, -0.75, y[gray])   # visual cortex
    img[brain & (np.abs(x - 0.01 * y) < 0.022) & (np.abs(y) > 0.42)] = 0.12   # fissure
    for s in (-1, 1):
        img[ellipse(0.25 * s, 0.08, 0.13, 0.22, -18 * s) <= 1] = 0.62         # internal capsule
        img[ellipse(0.17 * s, 0.22, 0.065, 0.13, 22 * s) <= 1] = 1.10         # caudate
        img[ellipse(0.29 * s, 0.01, 0.08, 0.18, -14 * s) <= 1] = 1.12         # putamen
        img[ellipse(0.085 * s, -0.17, 0.10, 0.13, -10 * s) <= 1] = 1.02       # thalamus
        img[ellipse(0.07 * s, 0.17, 0.035, 0.16, 20 * s) <= 1] = 0.05         # ventricles
        img[ellipse(0.43 * s, 0.02, 0.03, 0.18, -8 * s) <= 1] = 0.80          # insula
    scalp = (np.sqrt(ellipse(0, 0, 0.82, 0.98)) / outline <= 1.0) & ~brain
    img[scalp] = 0.05
    return ndimage.gaussian_filter(img, 0.9)


def project(img: np.ndarray, angles: np.ndarray) -> np.ndarray:
    """Parallel-beam projections: rotate and sum the columns (a matched pair with backproject)."""
    return np.stack([ndimage.rotate(img, a, reshape=False, order=1).sum(axis=0) for a in angles])


def backproject(sino: np.ndarray, angles: np.ndarray) -> np.ndarray:
    n = sino.shape[1]
    out = np.zeros((n, n))
    for row, a in zip(sino, angles):
        out += ndimage.rotate(np.tile(row, (n, 1)), -a, reshape=False, order=1)
    return out


def scan(n: int = 192, n_angles: int = 160, counts: float = 1.5e7, iters: int = 24):
    """Returns (phantom, noisy sinogram, MLEM image), all normalized to a maximum of 1."""
    truth = phantom(n)
    angles = np.linspace(0.0, 180.0, n_angles, endpoint=False)
    ideal = project(truth, angles)
    rng = np.random.default_rng(62304)
    sino = rng.poisson(ideal * counts / ideal.sum()).astype(np.float64)
    mask = np.hypot(*np.mgrid[-1:1:n * 1j, -1:1:n * 1j]) <= 0.98
    sens = backproject(np.ones_like(sino), angles)
    est = mask.astype(np.float64)
    for _ in range(iters):
        ratio = sino / np.maximum(project(est, angles), 1e-9)
        est = est * backproject(ratio, angles) / np.maximum(sens, 1e-9) * mask
    est = ndimage.gaussian_filter(est, 1.0)
    return truth / truth.max(), sino / sino.max(), est / np.percentile(est[mask], 99.95)


# ---------------------------------------------------------------------------------------------
# Drawing helpers on float RGB canvases (H x W x 3, values in [0, 1]).

class Canvas:
    def __init__(self, w_in: float, h_in: float, dpi: int, pal: dict, y0_in: float = 0.0):
        """A panel w_in x h_in in; y0_in is the height of its bottom edge on the sheet, so that
        the background gradient runs over the whole sheet height (trim plus both bleeds)."""
        self.dpi, self.pal = dpi, pal
        self.w, self.h = round(w_in * dpi), round(h_in * dpi)
        sheet_h = TRIM_H + 2 * BLEED
        ys = (np.arange(self.h)[::-1] + 0.5) / dpi + y0_in        # height on the sheet
        t = (ys / sheet_h)[:, None, None]
        top, bottom = rgb(pal["bg_top"]), rgb(pal["bg_bottom"])
        self.px = np.broadcast_to(bottom + (top - bottom) * t, (self.h, self.w, 3)).copy()

    def grid(self, ox: float, oy: float):
        """Pixel-center coordinates in inches relative to (ox, oy) on the panel (y up)."""
        xs = (np.arange(self.w) + 0.5) / self.dpi - ox
        ys = (self.h - np.arange(self.h) - 0.5) / self.dpi - oy
        return np.meshgrid(xs, ys)

    def add(self, color: np.ndarray, alpha: np.ndarray):
        """Additive light: color * alpha added to the canvas."""
        self.px += alpha[..., None] * color

    def over(self, color: np.ndarray, alpha: np.ndarray):
        a = np.clip(alpha, 0, 1)[..., None]
        self.px = self.px * (1 - a) + color * a

    def lines(self, segs, width_in: float, ss: int = 3) -> np.ndarray:
        """Anti-aliased coverage of line segments ((x0, y0, x1, y1) in panel inches)."""
        img = Image.new("L", (self.w * ss, self.h * ss), 0)
        d = ImageDraw.Draw(img)
        k = self.dpi * ss
        wpx = max(1, round(width_in * k))
        for x0, y0, x1, y1 in segs:
            d.line([(x0 * k, (self.h / self.dpi - y0) * k), (x1 * k, (self.h / self.dpi - y1) * k)],
                   fill=255, width=wpx)
        img = img.resize((self.w, self.h), Image.Resampling.LANCZOS)
        return np.asarray(img, dtype=np.float64) / 255.0

    def save(self, path: Path):
        out = (np.clip(self.px, 0, 1) * 255 + 0.5).astype(np.uint8)
        Image.fromarray(out).save(path, quality=90, subsampling=0, dpi=(self.dpi, self.dpi),
                                  optimize=True)


def place(canvas: Canvas, cx: float, cy: float, rgb_img: np.ndarray, alpha: np.ndarray, size_in: float):
    """Pastes an image (with alpha) centered at (cx, cy), resized to size_in inches square."""
    n = round(size_in * canvas.dpi)
    def rs(a):
        return np.asarray(Image.fromarray((np.clip(a, 0, 1) * 65535).astype(np.uint16) if a.ndim == 2
                                          else (np.clip(a, 0, 1) * 255).astype(np.uint8))
                          .resize((n, n), Image.Resampling.BICUBIC), dtype=np.float64)
    img = np.stack([rs(rgb_img[..., k]) / 65535.0 for k in range(3)], axis=-1)
    al = rs(alpha) / 65535.0
    x0 = round(cx * canvas.dpi) - n // 2
    y0 = canvas.h - round(cy * canvas.dpi) - n // 2
    sub = canvas.px[y0:y0 + n, x0:x0 + n]
    a = np.clip(al, 0, 1)[..., None]
    canvas.px[y0:y0 + n, x0:x0 + n] = sub * (1 - a) + img * a


def gold_ring(canvas: Canvas, cx, cy, r_in, r_out, pal, n_blocks=28, lit=None):
    """A detector ring in the plate's gold, with a few crystals lit in cream."""
    X, Y = canvas.grid(cx, cy)
    r = np.hypot(X, Y)
    th = np.mod(np.arctan2(Y, X), 2 * np.pi)
    sector = 2 * np.pi / n_blocks
    local = th / sector - np.floor(th / sector)
    radial = (r - r_in) / (r_out - r_in)
    gap = 0.10
    block = (radial >= 0) & (radial <= 1) & (local > gap / 2) & (local < 1 - gap / 2)
    shade = 0.55 + 0.45 * np.clip(1 - radial, 0, 1)
    canvas.over(rgb(pal["gold"]) * shade[..., None], block.astype(np.float64) * 0.92)
    if lit:
        hits = np.zeros(block.shape)
        for ang, strength in lit:
            cell = block & (np.abs(np.arctan2(np.sin(th - ang), np.cos(th - ang))) < sector * 0.28)
            cell = cell & (radial < 0.55)
            hits = np.maximum(hits, cell * strength)
        if pal.get("on_paper"):
            canvas.over(rgb("0B3D3A"), hits)
        else:
            canvas.add(rgb(pal["cream"]), hits * 0.85)


def events(img: np.ndarray, n_events: int, r_in: float, rng) -> list:
    """Annihilations sampled from the activity image: each gives a line of response between the
    two points where the photons reach the ring's inner face. Returns (x0, y0, x1, y1, a0, a1)
    relative to the ring center, the image spanning [-0.86 r_in, 0.86 r_in]."""
    n = img.shape[0]
    p = np.clip(img, 0, None).ravel() ** 1.5
    idx = rng.choice(p.size, size=n_events, p=p / p.sum())
    half = IMAGE_SPAN * r_in
    ys = (1 - (idx // n + rng.random(n_events)) / n * 2) * half
    xs = ((idx % n + rng.random(n_events)) / n * 2 - 1) * half
    out = []
    for x, y in zip(xs, ys):
        phi = rng.random() * math.pi
        dx, dy = math.cos(phi), math.sin(phi)
        b = x * dx + y * dy
        c = x * x + y * y - r_in * r_in
        s = math.sqrt(b * b - c)
        t0, t1 = -b + s, -b - s
        p0 = (x + t0 * dx, y + t0 * dy)
        p1 = (x + t1 * dx, y + t1 * dy)
        out.append((*p0, *p1, math.atan2(p0[1], p0[0]) % (2 * math.pi),
                    math.atan2(p1[1], p1[0]) % (2 * math.pi)))
    return out


def plate_tone(img: np.ndarray, gamma: float = 0.92) -> np.ndarray:
    """The Plate proposal's curve: lift the cortex, keep the bore black."""
    v = np.clip(img, 0, 1) ** gamma
    return np.clip((v - 0.08) / 0.85, 0, 1)


def disc_image(img: np.ndarray, pal, gamma: float = 0.92):
    """The reconstructed image colored with the palette, and its alpha (activity and a disc)."""
    v = plate_tone(img, gamma)
    col = colormap(pal["cmap"], v)
    n = img.shape[0]
    rr = np.hypot(*np.mgrid[-1:1:n * 1j, -1:1:n * 1j])
    alpha = smoothstep(0.03, 0.22, v) * smoothstep(1.0, 0.9, rr)
    return col, alpha


# ---------------------------------------------------------------------------------------------

def front(pal, data, dpi: int, path: Path, band: float = BAND):
    """The reconstruction, full bleed, with a flat band along the bottom of the trim."""
    _, _, recon = data
    w_px = round((TRIM_W + 2 * BLEED) * dpi)
    h_px = round((TRIM_H + 2 * BLEED) * dpi)
    band_px = round((BLEED + band) * dpi)
    n = recon.shape[0]
    m = int(round(n * 0.14))
    crop = plate_tone(recon[m:n - m, m:n - m])
    colored = colormap(pal["cmap"], crop)
    image = Image.fromarray((np.clip(colored, 0, 1) * 255 + 0.5).astype(np.uint8), mode="RGB")
    image = image.resize((w_px, h_px - band_px), Image.Resampling.LANCZOS)
    ink = tuple(int(pal["bg_bottom"][i:i + 2], 16) for i in (0, 2, 4))
    canvas = Image.new("RGB", (w_px, h_px), ink)
    canvas.paste(image, (0, 0))
    canvas.save(path, quality=92, subsampling=0, dpi=(dpi, dpi), optimize=True)


def back(pal, data, dpi: int, path: Path):
    """Ink field (it meets the spine) and the four steps, in the plate colors."""
    truth, sino, recon = data
    # Bleed on the left; the right edge is the spine.
    c = Canvas(BLEED + TRIM_W, TRIM_H + 2 * BLEED, dpi, pal)
    rng = np.random.default_rng(14971)
    evs = events(truth, 80, 0.50, rng)
    cy = BLEED + PANEL_Y + PANEL_S / 2
    centers = [BLEED + x + PANEL_S / 2 for x in PANEL_X]
    rr_in, rr_out = 0.50, 0.62
    # 1 singles: the ring, a few crystals lit.
    lit = [(rng.random() * 2 * math.pi, 0.9) for _ in range(8)]
    gold_ring(c, centers[0], cy, rr_in, rr_out, pal, lit=lit)
    # 2 coincidences: lines of response across the bore.
    segs = [(centers[1] + e[0], cy + e[1], centers[1] + e[2], cy + e[3]) for e in evs[:36]]
    cov = c.lines(segs, 0.007)
    if pal.get("on_paper"):
        c.over(rgb(pal["gold"]), cov * 0.9)
    else:
        c.add(rgb(pal["cream"]), cov * 0.55 + ndimage.gaussian_filter(cov, dpi * 0.012) * 0.45)
    gold_ring(c, centers[1], cy, rr_in, rr_out, pal)
    # 3 sinogram.
    cols = np.flatnonzero(sino.max(axis=0) > 0.02)
    s = np.clip(sino[:, cols[0]:cols[-1] + 1], 0, 1) ** 0.8
    s = np.asarray(Image.fromarray((s * 65535).astype(np.uint16)).resize((s.shape[1], s.shape[1])),
                   dtype=np.float64) / 65535.0
    place(c, centers[2], cy, colormap(pal["cmap"], s), np.ones_like(s) * 0.98, PANEL_S - 0.12)
    # 4 the reconstruction.
    col, alpha = disc_image(recon, pal)
    place(c, centers[3], cy, col, alpha, PANEL_S - 0.08)
    c.save(path)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "assets")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--volume", choices=["book", "solutions", "both"], default="both")
    args = ap.parse_args()
    # The same scan the Plate proposal was drawn from.
    data = scan(n=200, n_angles=180, counts=2.0e7, iters=22)
    for vol in (["book", "solutions"] if args.volume == "both" else [args.volume]):
        pal = PALETTES[vol]
        front(pal, data, args.dpi, args.out / f"cover-front-{vol}.jpg", BANDS[vol])
        back(pal, data, args.dpi, args.out / f"cover-back-{vol}.jpg")
        print(f"wrote {args.out}/cover-front-{vol}.jpg and cover-back-{vol}.jpg")


if __name__ == "__main__":
    main()
