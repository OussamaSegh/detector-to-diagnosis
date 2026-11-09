# SPDX-License-Identifier: MIT
"""The book's plotting style (docs/PLAN-interior-design.md, sections 3 and 4).

A figure script imports this module, draws, and calls save():

    import d2d
    fig, ax = d2d.figure(height=2.4)
    ax.plot(x, y, color=d2d.CAT[0], marker="o", label="trues")
    d2d.save(fig)

book/tools/figures.py runs the script as `python3 script.py OUT.(pdf|svg)` with D2D_PROFILE
(screen, boox or bw) and D2D_PART (the Part whose color is d2d.PART) in the environment.
Colors come from book/tools/palette.json, so the figures, the page and the checks agree.
Color never carries meaning alone: give every series a marker, a dash or a direct label.
"""
import colorsys
import glob
import json
import os
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, to_rgb  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
PALETTE = json.loads((ROOT / "book/tools/palette.json").read_text())
PROFILE = os.environ.get("D2D_PROFILE", "screen")
PART_ID = os.environ.get("D2D_PART", "0")
GRAY = PALETTE["profiles"][PROFILE]["gray"]
# The text width of the 8.5 x 11 in page, in inches; figures are drawn at this size.
TEXT_WIDTH = 6.65


def _gray(h):
    r, g, b = to_rgb("#" + h)
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    y = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    v = 12.92 * y if y <= 0.0031308 else 1.055 * y ** (1 / 2.4) - 0.055
    return "#{0:02X}{0:02X}{0:02X}".format(round(v * 255))


def color(h):
    """A palette hex value as a matplotlib color, in gray for the black ink profile."""
    h = h.lstrip("#")
    return _gray(h) if GRAY else "#" + h


def tint(c, amount):
    """c mixed with white: amount 0 is white, 1 is c."""
    r, g, b = to_rgb(c)
    return (1 - amount * (1 - r), 1 - amount * (1 - g), 1 - amount * (1 - b))


BASE = {k: color(v) for k, v in PALETTE["base"].items()}
INK, MUTED, RULE = BASE["ink"], BASE["muted"], BASE["rule"]
PART = color(PALETTE["parts"].get(PART_ID, PALETTE["parts"]["0"])[1])
SEM = {k: color(v) for k, v in PALETTE["semantic"].items()}
# Categorical colors (color-blind safe). In gray they differ by lightness only partly, so
# scripts also vary markers and dashes (MARKERS, DASHES), in the same order.
CAT = [color(h) for h in PALETTE["categorical"]]
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]
DASHES = ["-", "--", "-.", ":", (0, (5, 1, 1, 1)), (0, (1, 1)), (0, (8, 2)), (0, (3, 2, 1, 2))]
# Intensities (sinograms, images): perceptually uniform, monotone in gray.
CMAP = plt.get_cmap("gray_r") if GRAY else plt.get_cmap("viridis")
CMAP_PART = LinearSegmentedColormap.from_list("part", [tint(PART, 0.04), tint(PART, 0.5), PART,
                                                       tuple(0.45 * c for c in to_rgb(PART))])

BOOX = PROFILE == "boox"
FONT_PT = 8.6 if BOOX else 7.8
LINE_PT = 1.4 if BOOX else 1.1


def _fonts():
    for path in glob.glob("/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheros-*.otf") + \
            glob.glob("/usr/share/fonts/**/texgyreheros-*.otf", recursive=True):
        try:
            font_manager.fontManager.addfont(path)
        except Exception:  # noqa: BLE001 - a missing font falls back to DejaVu Sans
            pass


_fonts()
plt.rcParams.update({
    "font.family": ["TeX Gyre Heros", "DejaVu Sans"],
    "font.size": FONT_PT,
    "axes.titlesize": FONT_PT + 0.6,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.labelsize": FONT_PT,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK,
    "axes.linewidth": 0.7,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.prop_cycle": matplotlib.cycler(color=CAT[:6]),
    "axes.grid": True,
    "grid.color": tint(RULE, 0.55),
    "grid.linewidth": 0.5,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelcolor": INK,
    "ytick.labelcolor": INK,
    "xtick.labelsize": FONT_PT - 0.6,
    "ytick.labelsize": FONT_PT - 0.6,
    "legend.fontsize": FONT_PT - 0.6,
    "legend.frameon": False,
    "lines.linewidth": LINE_PT,
    "lines.markersize": 4.2,
    "patch.linewidth": 0.6,
    "text.color": INK,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.03,
    "svg.fonttype": "path",
    "pdf.fonttype": 42,
    "hatch.linewidth": 0.6,
    "svg.hashsalt": "d2d",
})


def figure(height=2.4, width=1.0, **kw):
    """A figure `width` of the text width wide and `height` inches high; plt.subplots(**kw)."""
    return plt.subplots(figsize=(TEXT_WIDTH * width, height), **kw)


def label(ax, x, y, text, c=None, **kw):
    """A direct label on a curve, in the curve's color (darkened for legibility)."""
    kw.setdefault("fontsize", FONT_PT - 0.4)
    kw.setdefault("fontweight", "bold")
    ax.text(x, y, text, color=c or INK, **kw)


def save(fig, dst=None):
    dst = dst or sys.argv[1]
    meta = {"Creator": "Detector to Diagnosis figure pipeline"}
    if dst.endswith(".pdf"):
        meta["CreationDate"] = None
    elif dst.endswith(".svg"):
        meta = {"Date": None}
    fig.savefig(dst, metadata=meta)
    plt.close(fig)


def part_hsv():
    return colorsys.rgb_to_hsv(*to_rgb(PART))
