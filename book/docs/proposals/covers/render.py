#!/usr/bin/env python3
"""Five front-cover proposals. Not used by book/build.sh.

The front panel is the 8.5 x 11 in trim. Type sits at least 0.55 in inside the
trim, inside KDP's 0.375 in safe zone. For a 749-page interior on white paper
the spine is 1.6867 in and the full wrap is 18.937 x 11.250 in; these files
are the front panel a reader sees, including the Amazon thumbnail.

    python3 book/docs/proposals/covers/render.py
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "book" / "tools"))
import cover_art  # noqa: E402  the book's own phantom and MLEM, not its cover

HERE = Path(__file__).resolve().parent
DPI = 200
W, H = round(8.5 * DPI), round(11 * DPI)
SAFE = 0.58 * DPI

GAR = "/usr/share/fonts/opentype/ebgaramond/EBGaramond12-Regular.otf"
GAR_IT = "/usr/share/fonts/opentype/ebgaramond/EBGaramond12-Italic.otf"
INT = "/usr/share/fonts/truetype/macos/Inter-Regular.ttf"
INT_MED = "/usr/share/fonts/truetype/macos/Inter-Medium.ttf"

TITLE_A = "Detector"
TITLE_TO = "to"
TITLE_B = "Diagnosis"
SUBTITLE = "Building regulated\nmedical imaging software\nin modern C++"
AUTHOR = "Oussama Seghaier"
KICKER = "PET DATA ACQUISITION"


def px(inches):
    return inches * DPI


def font(path, pt):
    return ImageFont.truetype(path, max(1, round(pt * DPI / 72)))


def tracked(draw, xy, text, face, fill, tracking):
    """Draw text with extra pixels between glyphs. Returns the end x."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=face, fill=fill)
        x += face.getlength(ch) + tracking
    return x


def text_width(face, text, tracking=0):
    return face.getlength(text) + tracking * max(0, len(text) - 1)


def wrap_lines(text):
    return text.split("\n")


class Cover:
    def __init__(self, rgb):
        self.im = Image.new("RGB", (W, H), rgb)
        self.draw = ImageDraw.Draw(self.im)

    def paste(self, image, xy):
        self.im.paste(image, xy)
        self.draw = ImageDraw.Draw(self.im)

    def save(self, path):
        self.im.save(path, optimize=True)


def annular(cx, cy, r0, r1, a0_deg, a1_deg, steps=6):
    """Polygon of an annular sector. Angles are degrees, 0 at east, positive CCW
    with y up. Pixel y is down, so the sine is subtracted."""
    pts = []
    for i in range(steps + 1):
        a = math.radians(a0_deg + (a1_deg - a0_deg) * i / steps)
        pts.append((cx + r1 * math.cos(a), cy - r1 * math.sin(a)))
    for i in range(steps + 1):
        a = math.radians(a1_deg - (a1_deg - a0_deg) * i / steps)
        pts.append((cx + r0 * math.cos(a), cy - r0 * math.sin(a)))
    return pts


def load_scan():
    cache = Path("/tmp/d2d-cover-scan.npz")
    if cache.exists():
        z = np.load(cache)
        return z["truth"], z["sino"], z["recon"]
    truth, sino, recon = cover_art.scan(n=200, n_angles=180, counts=2.0e7, iters=22)
    np.savez_compressed(cache, truth=truth, sino=sino, recon=recon)
    return truth, sino, recon


def colormap(img, stops):
    v = np.clip(img, 0, 1)
    xs = np.array([s[0] for s in stops])
    cs = np.array([[c[0], c[1], c[2]] for _, c in stops], dtype=np.float64)
    out = np.stack([np.interp(v, xs, cs[:, k]) for k in range(3)], axis=-1)
    return out.astype(np.uint8)


PLATE_STOPS = [
    (0.00, (8, 10, 14)),
    (0.08, (12, 16, 28)),
    (0.22, (36, 24, 72)),
    (0.40, (14, 78, 84)),
    (0.58, (168, 122, 58)),
    (0.78, (236, 214, 176)),
    (1.00, (252, 246, 234)),
]


def brain_rgb(img, gamma=0.92):
    v = np.clip(img, 0, 1) ** gamma
    # Lift the cortex and keep the bore black.
    v = np.clip((v - 0.08) / 0.85, 0, 1)
    return colormap(v, PLATE_STOPS)


def sample_lors(img, n, rng):
    """Lines of response through the activity, in a unit square centered on the image,
    coordinates in [-1, 1], y up, matching cover_art.events."""
    p = np.clip(img, 0, None).ravel() ** 1.6
    idx = rng.choice(p.size, size=n, p=p / p.sum())
    h = img.shape[0]
    ys = (1 - (idx // h + rng.random(n)) / h) * 2 - 1
    xs = ((idx % h + rng.random(n)) / h) * 2 - 1
    out = []
    for x, y in zip(xs, ys):
        phi = rng.random() * math.pi
        dx, dy = math.cos(phi), math.sin(phi)
        b = x * dx + y * dy
        c = x * x + y * y - 1.0
        disc = b * b - c
        if disc <= 0:
            continue
        s = math.sqrt(disc)
        t0, t1 = -b + s, -b - s
        out.append((x + t0 * dx, y + t0 * dy, x + t1 * dx, y + t1 * dy))
    return out


def draw_ring(base, cx, cy, r_in, r_out, n, color, edge, gap=1.15):
    """Detector blocks on a transparent layer, then alpha-composited."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    step = 360 / n
    for i in range(n):
        a0 = -90 + i * step + gap / 2
        a1 = -90 + (i + 1) * step - gap / 2
        d.polygon(annular(cx, cy, r_in, r_out, a0, a1), fill=color + (255,))
        # A brighter inner face.
        d.polygon(annular(cx, cy, r_in, r_in + (r_out - r_in) * 0.16, a0, a1, steps=4),
                  fill=edge + (255,))
    return Image.alpha_composite(base.convert("RGBA"), layer).convert("RGB")


def kicker(draw, x, y, fill, tracking=1.6):
    face = font(INT_MED, 11)
    tracked(draw, (x, y), KICKER, face, fill, tracking)
    return y + face.size + 10


def subtitle(draw, x, y, fill, pt=15.5, leading=1.28):
    face = font(INT, pt)
    for line in wrap_lines(SUBTITLE):
        draw.text((x, y), line, font=face, fill=fill)
        y += face.size * leading
    return y


def author(draw, x, y, fill, pt=16):
    face = font(INT, pt)
    draw.text((x, y), AUTHOR, font=face, fill=fill)


def title_stack(draw, x, y, cream, accent, pt=72, gap=-6):
    """Detector / to Diagnosis. Returns y under the second line."""
    display = font(GAR, pt)
    italic = font(GAR_IT, pt)
    draw.text((x, y), TITLE_A, font=display, fill=cream)
    y += display.size + gap
    draw.text((x, y), TITLE_TO + " ", font=italic, fill=accent)
    to_w = italic.getlength(TITLE_TO + " ")
    draw.text((x + to_w, y), TITLE_B, font=display, fill=cream)
    return y + display.size


# ---------------------------------------------------------------------------------------------
# The five fronts.


def meridian(truth):
    """A single detector ring, brass on ink."""
    c = Cover((14, 16, 15))
    # A quiet lift toward the bore, so the ring is not floating on a flat void.
    glow = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([px(1.15), px(3.55), px(7.35), px(9.75)], fill=28)
    glow = glow.filter(ImageFilter.GaussianBlur(70))
    base = c.im.convert("RGB")
    arr = np.asarray(base).astype(np.int16)
    g = np.asarray(glow).astype(np.int16)
    arr += g[..., None] // 3
    c.im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    cx, cy = px(4.25), px(6.70)
    r_in = px(2.35)
    c.im = draw_ring(c.im, cx, cy, r_in, px(2.82), 60, (186, 148, 84), (244, 224, 180), gap=1.2)
    # Chords that meet the crystal face, few enough to stay lines.
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    rng = np.random.default_rng(7)
    lors = sample_lors(truth, 18, rng)
    for x0, y0, x1, y1 in lors:
        od.line([(cx + x0 * r_in, cy - y0 * r_in), (cx + x1 * r_in, cy - y1 * r_in)],
                fill=(236, 216, 170, 110), width=2)
    c.im = Image.alpha_composite(c.im.convert("RGBA"), overlay).convert("RGB")
    c.draw = ImageDraw.Draw(c.im)
    cream, brass, mute = (243, 237, 226), (212, 176, 112), (186, 176, 158)
    y = kicker(c.draw, SAFE, px(0.62), brass)
    y = title_stack(c.draw, SAFE, y + 6, cream, brass, pt=64, gap=-2)
    c.draw.line([(SAFE, y + 16), (SAFE + px(1.55), y + 16)], fill=brass, width=3)
    subtitle(c.draw, SAFE, y + 28, mute, pt=15)
    author(c.draw, SAFE, H - SAFE - font(INT, 16).size, cream, pt=16)
    return c


def chords(truth):
    """The brain drawn as lines of response inside a whole ring, above the type."""
    c = Cover((7, 9, 14))
    band_h = round(px(3.05))
    r_in = px(2.02)
    cx = px(4.25)
    cy = (H - band_h) - r_in - px(0.22) - (px(2.22) - r_in)
    # A faint slice under the lines, so the density has a head to gather in.
    rgb = brain_rgb(truth, gamma=1.05)
    disc = Image.fromarray(rgb).resize((round(r_in * 1.42), round(r_in * 1.42)), Image.Resampling.LANCZOS)
    mask = Image.new("L", disc.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, disc.size[0] - 1, disc.size[1] - 1], fill=150)
    c.im.paste(disc, (round(cx - disc.size[0] / 2), round(cy - disc.size[1] / 2)), mask)
    rng = np.random.default_rng(11)
    lors = sample_lors(truth, 260, rng)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x0, y0, x1, y1 in lors:
        d.line([(cx + x0 * r_in, cy - y0 * r_in), (cx + x1 * r_in, cy - y1 * r_in)],
               fill=(255, 244, 224, 46), width=1)
    for x0, y0, x1, y1 in lors[::7]:
        d.line([(cx + x0 * r_in, cy - y0 * r_in), (cx + x1 * r_in, cy - y1 * r_in)],
               fill=(255, 248, 230, 160), width=2)
    c.im = Image.alpha_composite(c.im.convert("RGBA"), layer).convert("RGB")
    c.im = draw_ring(c.im, cx, cy, r_in, px(2.22), 64, (214, 200, 170), (248, 240, 220), gap=1.5)
    c.paste(Image.new("RGB", (W, band_h), (9, 11, 16)), (0, H - band_h))
    cream, gold, mute = (246, 240, 230), (214, 176, 104), (176, 170, 158)
    y = kicker(c.draw, SAFE, H - band_h + px(0.32), gold)
    y = title_stack(c.draw, SAFE, y + 2, cream, gold, pt=56, gap=-4)
    subtitle(c.draw, SAFE, y + 12, mute, pt=14.5)
    face = font(INT, 15)
    author(c.draw, W - SAFE - face.getlength(AUTHOR), H - px(0.40) - face.size, cream, 15)
    return c


def plate(recon):
    """The reconstruction, full width, with the type in an ink band."""
    rgb = brain_rgb(recon, gamma=0.82)
    img = Image.fromarray(rgb, mode="RGB")
    band_h = round(px(3.45))
    img_h = H - band_h
    n = rgb.shape[0]
    m = int(n * 0.14)
    framed = img.crop((m, m, n - m, n - m)).resize((W, img_h), Image.Resampling.LANCZOS)
    c = Cover((16, 14, 12))
    c.paste(framed, (0, 0))
    c.paste(Image.new("RGB", (W, band_h), (16, 14, 12)), (0, img_h))
    c.draw.line([(0, img_h), (W, img_h)], fill=(196, 154, 84), width=4)
    cream, gold, mute = (245, 239, 228), (212, 170, 96), (186, 176, 160)
    y = kicker(c.draw, SAFE, img_h + px(0.26), gold)
    y = title_stack(c.draw, SAFE, y + 2, cream, gold, pt=54, gap=-4)
    subtitle(c.draw, SAFE, y + 14, mute, pt=14.5)
    face = font(INT, 15)
    author(c.draw, W - SAFE - face.getlength(AUTHOR), H - px(0.38) - face.size, cream, 15)
    return c


def cadence(sino):
    """Projections drawn as a family of signals on warm paper. No filled slab."""
    paper = (246, 241, 232)
    ink = (22, 24, 26)
    teal = (14, 94, 84)
    c = Cover(paper)
    y = kicker(c.draw, SAFE, px(0.58), teal, tracking=1.8)
    y = title_stack(c.draw, SAFE, y + 6, ink, teal, pt=68, gap=-2)
    c.draw.line([(SAFE, y + 16), (SAFE + px(1.7), y + 16)], fill=teal, width=3)
    subtitle(c.draw, SAFE, y + 30, (70, 74, 70), pt=15.5)

    def trace(values, y_mid, amp, color, width):
        v = np.convolve(values, np.ones(11) / 11, mode="same")
        v = (v - v.min()) / (np.percentile(v, 98) - v.min() + 1e-9)
        v = np.clip(v, 0, 1)
        xs = np.linspace(SAFE, W - SAFE, v.size)
        pts = [(float(x), float(y_mid - (s - 0.35) * amp)) for x, s in zip(xs, v)]
        c.draw.line(pts, fill=color, width=width, joint="curve")

    # Five real projection angles, stacked like a recording, one of them the voice.
    angles = (12, 40, 78, 110, 150)
    top = px(6.15)
    step = px(0.72)
    for i, a in enumerate(angles):
        trace(sino[a], top + i * step, px(0.85), (168, 186, 178), 2)
    trace(sino[78], top + 2 * step, px(1.15), teal, 4)
    author(c.draw, SAFE, H - SAFE - font(INT, 16).size, ink, 16)
    return c


def letter():
    """The title is the whole cover."""
    teal = (12, 74, 68)
    cream = (246, 241, 230)
    gold = (224, 186, 112)
    c = Cover(teal)
    # Find the largest size at which "Diagnosis" fits the measure.
    measure = W - 2 * SAFE
    pt = 130
    while text_width(font(GAR, pt), TITLE_B) > measure and pt > 40:
        pt -= 1
    y = px(2.15)
    y = kicker(c.draw, SAFE, y, gold, tracking=2.0)
    display = font(GAR, pt * 0.72)
    huge = font(GAR, pt)
    italic = font(GAR_IT, pt * 0.42)
    c.draw.text((SAFE, y + 10), TITLE_A, font=display, fill=cream)
    y += display.size + 8
    # "to" as tracked small caps, the Atlas kicker's cousin, between the two words.
    tw = text_width(italic, TITLE_TO, tracking=6)
    tracked(c.draw, (SAFE, y), TITLE_TO, italic, gold, 6)
    c.draw.line([(SAFE + tw + 16, y + italic.size * 0.72), (SAFE + px(2.4), y + italic.size * 0.72)],
                fill=gold, width=2)
    y += italic.size + 6
    c.draw.text((SAFE, y), TITLE_B, font=huge, fill=cream)
    y += huge.size + 18
    subtitle(c.draw, SAFE, y, (214, 206, 190), pt=16)
    rule_y = H - SAFE - font(INT, 18).size - px(0.28)
    c.draw.line([(SAFE, rule_y), (W - SAFE, rule_y)], fill=gold, width=2)
    author(c.draw, SAFE, H - SAFE - font(INT, 18).size, cream, 18)
    return c


def contact(paths):
    """All five fronts, small, in a row, with their names."""
    thumb_w = 220
    names = ["Meridian", "Chords", "Plate", "Cadence", "Letter"]
    thumbs = []
    for p in paths:
        im = Image.open(p)
        th = round(thumb_w * im.size[1] / im.size[0])
        thumbs.append(im.resize((thumb_w, th), Image.Resampling.LANCZOS))
    gap, label_h, margin = 18, 36, 24
    sheet_w = margin * 2 + thumb_w * 5 + gap * 4
    sheet_h = margin + thumbs[0].size[1] + label_h + margin
    sheet = Image.new("RGB", (sheet_w, sheet_h), (244, 241, 234))
    d = ImageDraw.Draw(sheet)
    face = font(INT_MED, 11)
    # font() scales by the cover DPI. For a small sheet, use a fixed pixel size.
    face = ImageFont.truetype(INT_MED, 15)
    x = margin
    for im, name in zip(thumbs, names):
        sheet.paste(im, (x, margin))
        d.text((x, margin + im.size[1] + 8), name, font=face, fill=(30, 32, 30))
        x += thumb_w + gap
    sheet.save(HERE / "contact.png", optimize=True)


def main():
    truth, sino, recon = load_scan()
    jobs = [
        ("meridian.png", lambda: meridian(truth)),
        ("chords.png", lambda: chords(truth)),
        ("plate.png", lambda: plate(recon)),
        ("cadence.png", lambda: cadence(sino)),
        ("letter.png", letter),
    ]
    paths = []
    for name, fn in jobs:
        print("drawing", name, flush=True)
        cover = fn()
        path = HERE / name
        cover.save(path)
        paths.append(path)
        print(" ", path, cover.im.size)
    contact(paths)
    print("wrote", HERE / "contact.png")


if __name__ == "__main__":
    main()
