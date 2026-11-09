# SPDX-License-Identifier: MIT
"""Raster artwork of the covers (book/assets/cover.tex): a PET scan simulated end to end.

A brain phantom (an FDG-like axial slice) is forward projected into a sinogram, given Poisson
noise and reconstructed with MLEM. The front artwork is a detector ring with the reconstructed
image inside it and lines of response running through it; the back artwork shows the four steps
of the pipeline (singles, coincidences, sinogram, image) as small panels.

    python3 book/tools/cover_art.py [--out book/assets] [--dpi 300]

writes cover-front-<volume>.jpg and cover-back-<volume>.jpg for volume = book and solutions.
The output is deterministic (fixed seeds) and is committed, so building the book needs only
XeLaTeX. Needs numpy, scipy and Pillow (the versions of analysis/requirements.lock).

The background is the same vertical gradient that cover.tex draws on the spine, from BG_TOP at
the top of the sheet to BG_BOTTOM at its bottom, so the panels meet the spine without a seam.
Positions are in inches on the trimmed panel (origin at its lower left corner); the constants
marked "shared with cover.tex" must match the ones there.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

TRIM_W, TRIM_H, BLEED = 8.5, 11.0, 0.125

# Shared with cover.tex: the front ring and the back panels.
RING_CX, RING_CY = 5.55, 4.05          # center of the ring on the front panel
RING_R_IN, RING_R_OUT = 2.86, 3.38     # inner face and outer edge of the detector blocks
IMAGE_SPAN = 0.86                       # half side of the image in the bore, over RING_R_IN
PANEL_Y, PANEL_S = 2.55, 1.42          # back panels: bottom edge and side
PANEL_X = (0.75, 2.62, 4.49, 6.36)     # back panels: left edges

PALETTES = {
    "book": {
        "bg_top": "050816", "bg_bottom": "1A0B3A", "glow": "6D28D9",
        "ring": ["22D3EE", "3B82F6", "8B5CF6", "EC4899", "F59E0B"],
        "lor": "FDE68A",
        "cmap": [(0.00, "0B0B26"), (0.18, "2E1065"), (0.38, "7C3AED"), (0.58, "DB2777"),
                 (0.76, "F97316"), (0.90, "FACC15"), (1.00, "FFFBEB")],
    },
    "solutions": {
        "bg_top": "03141A", "bg_bottom": "07322F", "glow": "0D9488",
        "ring": ["2DD4BF", "22C55E", "A3E635", "FACC15", "38BDF8"],
        "lor": "FEF3C7",
        "cmap": [(0.00, "042024"), (0.18, "134E4A"), (0.38, "0F766E"), (0.58, "14B8A6"),
                 (0.76, "84CC16"), (0.90, "FACC15"), (1.00, "FEFCE8")],
    },
}


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


def ring(canvas: Canvas, cx, cy, r_in, r_out, n_blocks, pal, lit=None, glow=1.0, crystals=8):
    """A PET detector ring of n_blocks blocks of crystals x crystals crystals, colored by angle.
    lit: list of (angle in rad, strength) crystals hit by photons, drawn as bright cells."""
    X, Y = canvas.grid(cx, cy)
    r = np.hypot(X, Y)
    th = np.mod(np.arctan2(Y, X), 2 * np.pi)
    sector = 2 * np.pi / n_blocks
    k = np.floor(th / sector)
    local = th / sector - k                               # 0..1 across the block
    gap = 0.07
    radial = (r - r_in) / (r_out - r_in)                  # 0..1 through the block's depth
    inside = (radial >= 0) & (radial <= 1)
    block = inside & (local > gap / 2) & (local < 1 - gap / 2)
    # Color by angle: blend through the ring stops and back.
    stops = [rgb(c) for c in pal["ring"]]
    t = (k + 0.5) / n_blocks * len(stops)
    i0 = np.floor(t).astype(int) % len(stops)
    i1 = (i0 + 1) % len(stops)
    f = (t - np.floor(t))[..., None]
    col = np.stack(stops)[i0] * (1 - f) + np.stack(stops)[i1] * f
    # Crystal grid: dark lines between the crystals, and a lit inner face.
    u = (local - gap / 2) / (1 - gap)
    cu = np.abs(np.mod(u * crystals + 0.5, 1) - 0.5)
    cr = np.abs(np.mod(radial * crystals + 0.5, 1) - 0.5)
    line = np.minimum(cu, cr)
    shade = 0.62 + 0.38 * smoothstep(0.03, 0.16, line)
    shade = shade * (0.55 + 0.45 * np.clip(1 - radial, 0, 1) ** 0.6)
    face = (radial < 0.06).astype(np.float64)
    blk = block.astype(np.float64)
    # Soft halo of the ring.
    halo = ndimage.gaussian_filter(blk, canvas.dpi * 0.10)
    canvas.add(col * 0.9, halo * 0.55 * glow)
    canvas.over(col * shade[..., None] + face[..., None] * 0.35, blk * 0.96)
    if lit:
        # The crystal on the inner face where each photon stopped, all in one mask.
        hits = np.zeros_like(blk)
        for ang, strength in lit:
            kk = math.floor(ang / sector) % n_blocks
            uu = (ang / sector - math.floor(ang / sector) - gap / 2) / (1 - gap) * crystals
            ci = min(crystals - 1, max(0, int(uu)))
            cell = block & (k == kk) & (np.floor(u * crystals) == ci) & (radial * crystals < 2)
            hits = np.maximum(hits, cell * strength)
        canvas.add(rgb("FFFFFF"), hits * 0.75)
        canvas.add(rgb(pal["lor"]), ndimage.gaussian_filter(hits, canvas.dpi * 0.05) * 1.6)
    return block


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


def disc_image(img: np.ndarray, pal, gamma: float = 1.15):
    """The reconstructed image colored with the palette, and its alpha (activity and a disc)."""
    v = np.clip(img, 0, 1) ** gamma
    col = colormap(pal["cmap"], v)
    n = img.shape[0]
    rr = np.hypot(*np.mgrid[-1:1:n * 1j, -1:1:n * 1j])
    alpha = smoothstep(0.03, 0.22, v) * smoothstep(1.0, 0.9, rr)
    return col, alpha


# ---------------------------------------------------------------------------------------------

def front(pal, data, dpi: int, path: Path):
    truth, sino, recon = data
    c = Canvas(TRIM_W + 2 * BLEED, TRIM_H + 2 * BLEED, dpi, pal)
    cx, cy = RING_CX + BLEED, RING_CY + BLEED
    X, Y = c.grid(cx, cy)
    r = np.hypot(X, Y)
    # A wide glow behind the ring and a brighter core behind the image.
    c.add(rgb(pal["glow"]), 0.42 * np.exp(-(r / 2.6) ** 2))
    c.add(rgb(pal["glow"]), 0.30 * np.exp(-(r / 1.3) ** 2))
    # Faint rings of the gantry.
    for rad, a in ((RING_R_OUT + 0.16, 0.22), (RING_R_OUT + 0.30, 0.10)):
        c.add(rgb(pal["ring"][0]), a * np.exp(-((r - rad) / 0.008) ** 2))
    rng = np.random.default_rng(13485)
    evs = events(truth, 900, RING_R_IN, rng)
    # Lines of response: dense and faint across the bore, fading out over the lower right
    # where the image has formed; a few bright ones with a halo.
    direction = (-X * 0.70 + Y * 0.71)                    # toward the upper left
    raw = smoothstep(-1.6, 1.2, direction) * (r < RING_R_IN)
    faint = c.lines([(cx + e[0], cy + e[1], cx + e[2], cy + e[3]) for e in evs[:700]], 0.004)
    c.add(rgb(pal["lor"]), faint * 0.22 * (0.25 + 0.75 * raw))
    bright = evs[700:711]
    cov = c.lines([(cx + e[0], cy + e[1], cx + e[2], cy + e[3]) for e in bright], 0.009)
    c.add(rgb(pal["lor"]), ndimage.gaussian_filter(cov, dpi * 0.018) * 1.4 * (0.35 + 0.65 * raw))
    c.add(rgb(pal["lor"]), cov * 0.85 * (0.35 + 0.65 * raw))
    # The reconstructed image, revealed toward the lower right.
    col, alpha = disc_image(recon, pal)
    size = 2 * IMAGE_SPAN * RING_R_IN
    n = round(size * dpi)
    reveal = smoothstep(-0.9, 0.9, -direction)
    x0 = round(cx * dpi) - n // 2
    y0 = c.h - round(cy * dpi) - n // 2
    rv = reveal[y0:y0 + n, x0:x0 + n]
    big = np.asarray(Image.fromarray((np.clip(recon, 0, 1) * 65535).astype(np.uint16))
                     .resize((n, n), Image.Resampling.BICUBIC), dtype=np.float64) / 65535.0
    col, alpha = disc_image(big, pal)
    a = np.clip(alpha * (0.18 + 0.82 * rv), 0, 1)[..., None]
    sub = c.px[y0:y0 + n, x0:x0 + n]
    c.px[y0:y0 + n, x0:x0 + n] = sub * (1 - a) + col * a + col * a * 0.25 * rv[..., None]
    lit = [(e[4], 1.0) for e in bright] + [(e[5], 1.0) for e in bright]
    ring(c, cx, cy, RING_R_IN, RING_R_OUT, 48, pal, lit=lit)
    c.save(path)


def back(pal, data, dpi: int, path: Path):
    truth, sino, recon = data
    # The back panel: bleed on the left, the spine on the right.
    c = Canvas(BLEED + TRIM_W, TRIM_H + 2 * BLEED, dpi, pal)
    X, Y = c.grid(BLEED + 3.6, BLEED + 8.0)
    # A glow behind the blurb, gone before the spine so that the two meet without a seam.
    c.add(rgb(pal["glow"]), 0.20 * np.exp(-((X / 4.0) ** 2 + (Y / 2.8) ** 2))
          * smoothstep(8.4 - 3.6, 6.0 - 3.6, X))
    rng = np.random.default_rng(14971)
    evs = events(truth, 400, 0.5, rng)
    cy = BLEED + PANEL_Y + PANEL_S / 2
    centers = [BLEED + x + PANEL_S / 2 for x in PANEL_X]
    # Frames of the panels.
    for x in centers:
        X, Y = c.grid(x, cy)
        box = smoothstep(PANEL_S / 2 + 0.004, PANEL_S / 2 - 0.004, np.maximum(np.abs(X), np.abs(Y)))
        c.over(rgb(pal["bg_top"]) * 0.6, box * 0.65)
        edge = np.exp(-((np.maximum(np.abs(X), np.abs(Y)) - PANEL_S / 2) / 0.004) ** 2)
        c.add(rgb(pal["ring"][0]), edge * 0.35)
    rr_in, rr_out = 0.52, 0.64
    # 1 singles: the ring with crystals lit at random.
    lit = [(rng.random() * 2 * math.pi, 0.8) for _ in range(26)]
    ring(c, centers[0], cy, rr_in, rr_out, 24, pal, lit=lit, glow=0.6, crystals=4)
    # 2 coincidences: lines of response between pairs.
    segs = [(centers[1] + e[0], cy + e[1], centers[1] + e[2], cy + e[3]) for e in evs[:60]]
    cov = c.lines(segs, 0.006)
    c.add(rgb(pal["lor"]), cov * 0.55 + ndimage.gaussian_filter(cov, dpi * 0.01) * 0.6)
    lit2 = [(e[4], 0.6) for e in evs[:60]] + [(e[5], 0.6) for e in evs[:60]]
    ring(c, centers[1], cy, rr_in, rr_out, 24, pal, lit=lit2[:40], glow=0.6, crystals=4)
    # 3 sinogram: angle down, radial position across.
    cols = np.flatnonzero(sino.max(axis=0) > 0.02)
    s = np.clip(sino[:, cols[0]:cols[-1] + 1], 0, 1) ** 0.8
    s = np.asarray(Image.fromarray((s * 65535).astype(np.uint16)).resize((s.shape[1], s.shape[1])),
                   dtype=np.float64) / 65535.0
    place(c, centers[2], cy, colormap(pal["cmap"], s), np.ones_like(s) * 0.97, PANEL_S - 0.16)
    # 4 image.
    col, alpha = disc_image(recon, pal)
    place(c, centers[3], cy, col, alpha, PANEL_S - 0.10)
    c.save(path)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "assets")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--volume", choices=["book", "solutions", "both"], default="both")
    args = ap.parse_args()
    data = scan()
    for vol in (["book", "solutions"] if args.volume == "both" else [args.volume]):
        pal = PALETTES[vol]
        front(pal, data, args.dpi, args.out / f"cover-front-{vol}.jpg")
        back(pal, data, args.dpi, args.out / f"cover-back-{vol}.jpg")
        print(f"wrote {args.out}/cover-front-{vol}.jpg and cover-back-{vol}.jpg")


if __name__ == "__main__":
    main()
