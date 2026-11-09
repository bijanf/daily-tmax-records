"""THE CROSS-SECTION KIT for the slide reels: a drawing box, ground materials with texture, the cut face of a
block of ground, and labels that fade in on cream pills with tidy leader lines (the look of a newsroom explainer).

- Shapes are drawn SS times larger and scaled down (anti-aliased). The box draws in "RGBA" mode: a fill with a
  fourth value blends with what is under it (a translucent polyline blends twice at its joints: fill polygons).
- Every frame is a pure function of its time: particles come from hash01, never from a random state.
- Textures (alluvium, topsoil, clay, rock) are made once per size and cached; a scene pastes them through masks,
  so a falling water table or a wetting front costs one mask per frame.
- Box.done() scales the picture down and draws the Persian labels at full resolution (crisp type).

The things that stand in the picture (sky, the Alborz, Tehran, wells, rain) are in src/onebit_scenery.py.
"""

from __future__ import annotations

import functools
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

SS = 3
FONTS = Path(__file__).resolve().parents[1] / "data" / "fonts" / "vazirmatn"
PAPER = (243, 236, 225)
INK = (46, 33, 24)
WHITE = (255, 255, 255)
GREY = (96, 104, 112)
SKY_TOP, SKY_LOW = (164, 205, 236), (239, 237, 226)
STORM_TOP, STORM_LOW = (110, 122, 140), (188, 194, 202)
WATER, WATER_LIGHT, WATER_DARK = (42, 120, 214), (150, 196, 232), (24, 84, 160)
GRASS, GRASS_DARK = (128, 152, 88), (94, 122, 70)
SAND, TOPSOIL, CLAY, ROCK = (220, 194, 146), (150, 104, 66), (152, 134, 120), (168, 154, 142)
PEBBLES = ((196, 170, 128), (176, 150, 112), (204, 186, 160), (160, 142, 122), (186, 160, 130), (148, 126, 100),
           (210, 200, 184), (172, 132, 102))
STEEL, STEEL_DARK, STEEL_LIGHT = (112, 120, 130), (66, 72, 82), (176, 184, 194)


def ease(p: float) -> float:
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


def ramp(t: float, t0: float, dur: float) -> float:
    """0 before t0, 1 after t0 + dur, eased; t = inf gives the end state."""
    if not np.isfinite(t):
        return 1.0
    return ease((t - t0) / max(dur, 1e-6))


def fade(t: float, at=None, until=None, dur: float = 0.4) -> float:
    """Visibility of something that appears at `at` and (optionally) leaves at `until`."""
    a = 1.0 if at is None else ramp(t, at, dur)
    if until is not None:
        a *= 0.0 if not np.isfinite(t) else 1.0 - ramp(t, until, dur)
    return a


def mix(a, b, p: float):
    p = min(max(p, 0.0), 1.0)
    return tuple(int(round(x + (y - x) * p)) for x, y in zip(a, b))


def hash01(k: int, salt: int = 0) -> float:
    v = math.sin(k * 12.9898 + salt * 78.233) * 43758.5453
    return v - math.floor(v)


def clock(t: float) -> float:
    return 0.0 if not np.isfinite(t) else t


def rgba(colour, a: float = 1.0):
    return tuple(colour[:3]) + (int(round(255 * min(max(a, 0.0), 1.0))),)


@functools.lru_cache(maxsize=32)
def font(bold: bool, size: int):
    return ImageFont.truetype(str(FONTS / ("Vazirmatn-Bold.ttf" if bold else "Vazirmatn-Medium.ttf")), size)


def text_width(text: str, size: float, bold: bool = True) -> float:
    return font(bold, int(round(size))).getlength(text, direction="rtl")


@functools.lru_cache(maxsize=8)
def corner_mask(w: int, h: int, radius: int) -> Image.Image:
    m = Image.new("L", (w * SS, h * SS), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius=radius * SS, fill=255)
    return m.resize((w, h), Image.LANCZOS)


class Box:
    """The drawing box: coordinates in final pixels, the image SS times larger. `t` is the scene's clock (labels
    fade by it); inf is the end state."""

    def __init__(self, w: int, h: int, t: float = np.inf, bg=PAPER):
        self.w, self.h, self.t = w, h, t
        self.im = Image.new("RGB", (w * SS, h * SS), bg)
        self.d = ImageDraw.Draw(self.im, "RGBA")
        self.labels: list = []

    # ── shapes ──
    def P(self, x, y):
        return (x * SS, y * SS)

    def poly(self, pts, fill):
        self.d.polygon([self.P(x, y) for x, y in pts], fill=fill)

    def line(self, pts, fill, width=2.0):
        self.d.line([self.P(x, y) for x, y in pts], fill=fill, width=max(1, int(round(width * SS))), joint="curve")

    def dashed(self, x0, x1, y, fill, width=2.0, dash=14, gap=9):
        """A dashed line from x0 to x1; y is a number or a function of x."""
        x = x0
        f = y if callable(y) else (lambda _x: y)
        while x < x1:
            xe = min(x + dash, x1)
            self.line([(x, f(x)), (xe, f(xe))], fill, width)
            x += dash + gap

    def rect(self, x0, y0, x1, y1, fill, radius=0.0, outline=None, width=1.0):
        box = [x0 * SS, y0 * SS, x1 * SS, y1 * SS]
        kw = dict(fill=fill, outline=outline, width=max(1, int(round(width * SS))))
        if radius:
            self.d.rounded_rectangle(box, radius=radius * SS, **kw)
        else:
            self.d.rectangle(box, **kw)

    def ellipse(self, cx, cy, rx, ry, fill, outline=None, width=1.0):
        self.d.ellipse([(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS], fill=fill, outline=outline,
                       width=max(1, int(round(width * SS))))

    def arrow(self, x0, y0, x1, y1, fill, width=4.0, head=14.0):
        a = math.atan2(y1 - y0, x1 - x0)
        self.line([(x0, y0), (x1 - 0.6 * head * math.cos(a), y1 - 0.6 * head * math.sin(a))], fill, width)
        self.poly([(x1, y1), (x1 - head * math.cos(a - 0.42), y1 - head * math.sin(a - 0.42)),
                   (x1 - head * math.cos(a + 0.42), y1 - head * math.sin(a + 0.42))], fill)

    def glow(self, cx, cy, r, colour, a=0.5, steps=22):
        """A soft disc: stacked translucent ellipses, brightest in the middle."""
        for k in range(steps):
            q = 1.0 - k / steps
            self.ellipse(cx, cy, r * q, r * q, rgba(colour, a / steps * 1.5))

    def vgradient(self, x0, y0, x1, y1, top, bottom):
        hh = max(1, int(round((y1 - y0) * SS)))
        ramp_ = np.linspace(0.0, 1.0, hh, dtype=np.float32)[:, None]
        col = np.array(top, np.float32)[None, :] * (1 - ramp_) + np.array(bottom, np.float32)[None, :] * ramp_
        strip = Image.fromarray(np.uint8(np.clip(col, 0, 255))[:, None, :]).resize(
            (max(1, int(round((x1 - x0) * SS))), hh), Image.NEAREST)
        self.im.paste(strip, (int(round(x0 * SS)), int(round(y0 * SS))))

    def paste(self, tex: Image.Image, mask: Image.Image | None = None, x=0.0, y=0.0, alpha: float = 1.0):
        """Paste an SS-scale image (RGB with an L mask, or RGBA) at (x, y); alpha fades it."""
        if tex.mode == "RGBA" and mask is None:
            mask = tex.getchannel("A")
        if mask is not None and alpha < 0.999:
            mask = mask.point(lambda v: int(v * alpha))
        elif mask is None and alpha < 0.999:
            mask = Image.new("L", tex.size, int(255 * alpha))
        self.im.paste(tex.convert("RGB") if tex.mode != "RGB" else tex, (int(round(x * SS)), int(round(y * SS))), mask)

    def mask(self, pts=None) -> Image.Image:
        """An empty L mask of the box's size (SS scale), or the polygon `pts` filled."""
        m = Image.new("L", self.im.size, 0)
        if pts is not None:
            ImageDraw.Draw(m).polygon([self.P(x, y) for x, y in pts], fill=255)
        return m

    def below(self, curve, clip: Image.Image | None = None, n: int = 160, wobble: float = 0.0) -> Image.Image:
        """The mask of everything below y = curve(x) (a number or a function), inside `clip`."""
        f = curve if callable(curve) else (lambda _x: curve)
        xs = np.linspace(0, self.w, n)
        pts = [(x, f(x) + (wobble * math.sin(x / 19.0) if wobble else 0.0)) for x in xs]
        m = self.mask(pts + [(self.w, self.h + 2), (0, self.h + 2)])
        return ImageChops.multiply(m, clip) if clip is not None else m

    # ── labels ──
    def label(self, x, y, text, at=None, until=None, colour=INK, size=34, bold=True, lead=None, anchor="rs",
              pill=True, rise=10.0):
        """A label on a cream pill: (x, y) is the baseline's right end ("rs", Persian) or left end ("ls") of its
        first line; "\n" in the text starts a new line (the lines are flush right, LINE * size apart). It fades
        in at `at` (rising `rise` px into place) and out at `until`; `lead` is the point it names (an L-shaped
        leader with a ring). Returns the pill's box (x0, y0, x1, y1), or None while hidden."""
        a = fade(self.t, at, until)
        if a <= 0.01:
            return None
        lines = text.split("\n")
        tw = max(text_width(q, size, bold) for q in lines)
        x1 = x if anchor == "rs" else x + tw
        yy = y + rise * (1.0 - a)
        box = (x1 - tw - 14, yy - 0.98 * size, x1 + 14, yy + (len(lines) - 1) * LINE * size + 0.36 * size)
        if lead is not None:
            self.leader(box, lead, a)
        self.labels.append(dict(text=text, colour=tuple(colour), size=int(round(size)), bold=bold, alpha=a,
                                pill=pill, box=box))
        return box

    def leader(self, box, target, a=1.0, colour=INK, width=2.2):
        x0, y0, x1, y1 = box
        tx, ty = target
        col = rgba(colour, 0.9 * a)
        if x0 + 16 <= tx <= x1 - 16:                      # straight down or up from the pill
            pts = [(tx, y1 if ty > y1 else y0), (tx, ty)]
        elif y0 + 6 <= ty <= y1 - 6:                      # straight out of its side
            pts = [(x0 if tx < x0 else x1, ty), (tx, ty)]
        else:                                             # out of the side, then down or up
            ym = (y0 + y1) / 2
            pts = [(x0 if tx < x0 else x1, ym), (tx, ym), (tx, ty)]
        for p, q in zip(pts[:-1], pts[1:]):
            self.line([p, q], col, width)
        self.ring(tx, ty, 6.0, a, colour)

    def ring(self, x, y, r=6.0, a=1.0, colour=INK):
        self.ellipse(x, y, r, r, rgba(WHITE, a), outline=rgba(colour, a), width=2.0)

    def done(self, radius=18) -> Image.Image:
        """The finished picture (RGB, w by h, rounded corners) with the labels drawn at full resolution."""
        im = self.im.resize((self.w, self.h), Image.LANCZOS)
        out = Image.new("RGBA", (self.w, self.h), PAPER + (255,))
        out.paste(im, (0, 0), corner_mask(self.w, self.h, radius))
        for L in self.labels:
            x0, y0, x1, y1 = L["box"]
            assert x0 >= 1 and x1 <= self.w - 1 and y0 >= 1 and y1 <= self.h - 1, (L["text"], L["box"])
            tile = _label_tile(L["text"], L["size"], L["bold"], L["colour"], L["pill"],
                               int(math.ceil(x1 - x0)), int(math.ceil(y1 - y0)))
            if L["alpha"] < 0.999:
                tile = tile.copy()
                tile.putalpha(tile.getchannel("A").point(lambda v, q=L["alpha"]: int(v * q)))
            ox, oy = int(round(x0)) - LABEL_PAD, int(round(y0)) - LABEL_PAD
            if ox < 0 or oy < 0:
                tile = tile.crop((max(0, -ox), max(0, -oy), tile.width, tile.height))
                ox, oy = max(0, ox), max(0, oy)
            out.alpha_composite(tile, (ox, oy))
        return out.convert("RGB")


LINE = 1.34                                           # line spacing of a label, in sizes
LABEL_PAD = 9                                         # room around a pill for its shadow, px


@functools.lru_cache(maxsize=96)
def _label_tile(text: str, size: int, bold: bool, colour: tuple, pill: bool, w: int, h: int) -> Image.Image:
    """A label's pill (soft shadow, thin outline) and its lines, as an RGBA tile LABEL_PAD larger all round."""
    pad = LABEL_PAD
    tw, th = w + 2 * pad, h + 2 * pad
    tile = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    if pill:
        ImageDraw.Draw(tile).rounded_rectangle([pad, pad + 3, tw - pad, th - pad + 3], radius=12, fill=INK + (58,))
        tile = tile.filter(ImageFilter.GaussianBlur(3.2))
        ImageDraw.Draw(tile).rounded_rectangle([pad, pad, tw - pad - 1, th - pad - 1], radius=12,
                                               fill=PAPER + (240,), outline=INK + (64,), width=1)
    d = ImageDraw.Draw(tile)
    for k, q in enumerate(text.split("\n")):
        d.text((pad + w - 14, pad + (0.98 + k * LINE) * size), q, font=font(bold, size), fill=tuple(colour) + (255,),
               anchor="rs", direction="rtl")
    return tile


# ── textures ──

def noise(shape, cell: float, seed: int, sx: float = 1.0, sy: float = 1.0) -> np.ndarray:
    """Smooth value noise in 0..1: a random grid with cells of about `cell` px (stretched by sx, sy), bicubic."""
    h, w = shape
    g = np.random.default_rng(seed).random((max(2, int(h / (cell * sy)) + 2), max(2, int(w / (cell * sx)) + 2)),
                                            dtype=np.float32)
    return np.clip(np.asarray(Image.fromarray(g).resize((w, h), Image.BICUBIC), dtype=np.float32), 0.0, 1.0)


def fbm(shape, cell: float, seed: int, octaves: int = 4, sx: float = 1.0, sy: float = 1.0) -> np.ndarray:
    out, amp, tot = np.zeros(shape, np.float32), 1.0, 0.0
    for o in range(octaves):
        out += amp * noise(shape, max(1.5, cell / 2 ** o), seed * 131 + o, sx, sy)
        tot += amp
        amp *= 0.5
    return out / tot


def _grain(h: int, w: int, rng, amount: float) -> np.ndarray:
    """Per-pixel grain at the final scale (it survives the scaling down), as a factor around 1."""
    g = 1.0 + amount * (rng.random((h, w), dtype=np.float32) * 2 - 1)
    return np.repeat(np.repeat(g, SS, 0), SS, 1)


def _pebbles(im: Image.Image, rng, n: int, small: float, big: float, bed: np.ndarray | None = None,
             palette=PEBBLES):
    """Stones with a shadow below and light from the upper left; `bed` (0..1) thins them out in fine beds."""
    d = ImageDraw.Draw(im, "RGBA")
    W, H = im.size
    for _ in range(n):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        if bed is not None and rng.random() > bed[min(H - 1, int(y)), min(W - 1, int(x))]:
            continue
        r = SS * min(big, small * math.exp(rng.exponential(0.6)))
        ry = r * rng.uniform(0.55, 0.85)
        c = palette[int(rng.integers(len(palette)))]
        d.ellipse([x - r, y - ry + 0.4 * r, x + r, y + ry + 0.4 * r], fill=(70, 46, 26, 64))
        d.ellipse([x - r, y - ry, x + r, y + ry], fill=c)
        d.ellipse([x - 0.6 * r, y - 0.66 * ry, x + 0.05 * r, y - 0.12 * ry], fill=(255, 250, 236, 76))


@functools.lru_cache(maxsize=24)
def material(name: str, w: int, h: int, seed: int = 0) -> Image.Image:
    """A full-box texture (SS scale): "alluvium" (sand and gravel in beds), "topsoil" (crumbs, flecks, a few
    stones), "clay" (laminated), "rock" (fractured). Do not draw on the result: it is cached."""
    W, H = w * SS, h * SS
    rng = np.random.default_rng(1000 + seed)
    if name == "alluvium":
        tone = 0.90 + 0.20 * fbm((H, W), 110 * SS, seed + 1, 4, sx=3.0)
        beds = 0.955 + 0.09 * noise((H, W), 22 * SS, seed + 2, sx=16.0)
        a = np.array(SAND, np.float32) * (tone * beds * _grain(h, w, rng, 0.045))[:, :, None]
        im = Image.fromarray(np.uint8(np.clip(a, 0, 255)))
        bed = np.clip(0.25 + 1.5 * (noise((H, W), 34 * SS, seed + 3, sx=9.0) - 0.3), 0.08, 1.0)
        _pebbles(im, rng, int(w * h / 150), 1.25, 7.0, bed)
        return im
    if name == "topsoil":
        crumb = 0.80 + 0.40 * fbm((H, W), 10 * SS, seed + 4, 3)
        a = np.array(TOPSOIL, np.float32) * (crumb * _grain(h, w, rng, 0.07))[:, :, None]
        im = Image.fromarray(np.uint8(np.clip(a, 0, 255)))
        d = ImageDraw.Draw(im, "RGBA")
        for _ in range(int(w * h / 260)):                 # dark organic flecks
            x, y, r = rng.uniform(0, W), rng.uniform(0, H), SS * rng.uniform(0.8, 2.4)
            d.ellipse([x - r * 1.5, y - r * 0.7, x + r * 1.5, y + r * 0.7], fill=(74, 46, 26, 110))
        _pebbles(im, rng, int(w * h / 900), 1.2, 4.5, None, ((188, 168, 140), (150, 132, 112), (206, 192, 170)))
        return im
    if name == "clay":
        lam = 0.86 + 0.28 * fbm((H, W), 6 * SS, seed + 5, 3, sx=18.0)
        a = np.array(CLAY, np.float32) * (lam * _grain(h, w, rng, 0.03))[:, :, None]
        im = Image.fromarray(np.uint8(np.clip(a, 0, 255)))
        d = ImageDraw.Draw(im, "RGBA")
        for y in range(0, H, 5 * SS):                     # thin laminae
            ph = rng.uniform(0, 6.28)
            d.line([(x, y + SS * 1.6 * math.sin(x / (70.0 * SS) + ph)) for x in range(0, W + 40, 40)],
                   fill=(92, 76, 66, 84), width=max(1, SS // 2))
        return im
    if name == "rock":
        tone = 0.86 + 0.28 * fbm((H, W), 70 * SS, seed + 6, 5, sx=1.5)
        dip = 0.42                                        # beds that dip to the right: sheared bands
        beds = noise((H + int(W * dip) + 1, W), 13 * SS, seed + 7, sx=22.0)
        rows = np.arange(H)[:, None] + (np.arange(W)[None, :] * dip).astype(int)
        beds = 0.93 + 0.14 * np.take_along_axis(beds, rows, axis=0)
        a = np.array(ROCK, np.float32) * (tone * beds * _grain(h, w, rng, 0.04))[:, :, None]
        im = Image.fromarray(np.uint8(np.clip(a, 0, 255)))
        d = ImageDraw.Draw(im, "RGBA")
        for _ in range(int(w * h / 5200)):                # fractures: short broken lines
            x, y, ang = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.5, 1.3) * (1 if rng.random() < 0.6 else -1)
            pts = [(x, y)]
            for _k in range(int(rng.integers(3, 7))):
                ang += rng.uniform(-0.5, 0.5)
                L = SS * rng.uniform(10, 26)
                pts.append((pts[-1][0] + L * math.cos(ang), pts[-1][1] + L * math.sin(ang)))
            d.line(pts, fill=(84, 70, 62, 104), width=max(1, SS // 2 + 1))
            d.line([(px + SS, py + SS) for px, py in pts], fill=(214, 208, 200, 60), width=max(1, SS // 2))
        return im
    raise KeyError(name)


def saturated(im: Image.Image) -> Image.Image:
    """The same ground with water in its pores: blue, and the stones and beds still show."""
    a = np.asarray(im, np.float32)
    k = np.clip(a.mean(axis=2, keepdims=True) / 186.0, 0.35, 1.5) ** 1.35
    out = np.array((34, 104, 190), np.float32) * k * 0.86 + a * 0.16
    return Image.fromarray(np.uint8(np.clip(out, 0, 255)))


def moist(im: Image.Image, k: float = 0.58) -> Image.Image:
    """Damp, not saturated: darker and a little cooler."""
    a = np.asarray(im, np.float32) * np.array((k, k * 1.0, k * 1.06), np.float32)
    return Image.fromarray(np.uint8(np.clip(a, 0, 255)))


# ── the block of ground ──

class Ground:
    """The static cut face of a block: `dry` and `wet` (saturated) pictures, `mask` of the block below its surface,
    `soil` mask of the topsoil, `clay` masks of the lenses (all SS scale), and the surface line `ys` per column."""

    def __init__(self, dry, wet, damp, mask, soil, clay, ys):
        self.dry, self.wet, self.damp, self.mask, self.soil, self.clay, self.ys = dry, wet, damp, mask, soil, clay, ys


_GROUNDS: dict = {}


def ground(key, w: int, h: int, surf, soil_px: float, clay=(), rock=None, seed: int = 7, shade: bool = True) -> Ground:
    """Build (once per `key`) the cut face under y = surf(x): topsoil `soil_px` thick, alluvium, clay lenses
    (yc, thick, xa, xb) where yc is a number or a function of x, and rock below y = rock(x) if given."""
    if key in _GROUNDS:
        return _GROUNDS[key]
    W, H = w * SS, h * SS
    xs = np.arange(W) / SS
    ys = np.array([surf(x) for x in xs], np.float32)
    im = material("alluvium", w, h, seed).copy()

    def region(top, bot=None):
        m = Image.new("L", (W, H), 0)
        pts = [(i, top[i] * SS) for i in range(0, W, 2)] + [(W - 1, top[-1] * SS)]
        low = ([(W - 1, H + 2), (0, H + 2)] if bot is None else
               [(W - 1, bot[-1] * SS)] + [(i, bot[i] * SS) for i in range(W - 1, -1, -2)])
        ImageDraw.Draw(m).polygon(pts + low, fill=255)
        return m

    if rock is not None:
        ry = np.array([rock(x) for x in xs], np.float32) + 3.0 * np.sin(xs / 23.0)
        m = region(ry)
        im.paste(material("rock", w, h, seed), (0, 0), m)
        ImageDraw.Draw(im, "RGBA").line([(i, ry[i] * SS) for i in range(0, W, 3)], fill=(60, 50, 44, 150), width=SS)
    lenses = []
    d = ImageDraw.Draw(im, "RGBA")
    for j, (yc, thick, xa, xb) in enumerate(clay):
        f = yc if callable(yc) else (lambda _x, v=yc: v)
        px = np.linspace(xa, xb, 90)
        taper = np.clip(1.0 - np.abs((px - (xa + xb) / 2) / ((xb - xa) / 2)) ** 2.6, 0.0, 1.0) ** 0.6
        mid = np.array([f(x) for x in px]) + 2.4 * np.sin(px / 37.0 + j)
        up = [(x * SS, (y - thick / 2 * q) * SS) for x, y, q in zip(px, mid, taper)]
        dn = [(x * SS, (y + thick / 2 * q + 1.6 * math.sin(x / 29.0)) * SS) for x, y, q in zip(px, mid, taper)]
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).polygon(up + dn[::-1], fill=255)
        im.paste(material("clay", w, h, seed + j), (0, 0), m)
        d = ImageDraw.Draw(im, "RGBA")
        d.line(up, fill=(84, 68, 56, 170), width=SS)
        d.line(dn, fill=(84, 68, 56, 120), width=SS)
        lenses.append(m)
    base = ys + soil_px + 1.8 * np.sin(xs / 17.0) + 1.2 * np.sin(xs / 5.3)
    soil = region(ys, base)
    im.paste(material("topsoil", w, h, seed), (0, 0), soil)
    ImageDraw.Draw(im, "RGBA").line([(i, base[i] * SS) for i in range(0, W, 3)], fill=(70, 46, 28, 110), width=SS)
    mask = region(ys)
    if shade:                                             # a soft shadow under the surface, darker with depth
        yy = (np.arange(H, dtype=np.float32) / SS)[:, None]
        depth = np.clip(yy - ys[None, :], 0.0, None)
        s = (1.0 - 0.17 * np.exp(-depth / 12.0)) * (1.0 - 0.10 * np.clip(depth / max(1.0, h * 0.7), 0, 1))
        s = s * (1.0 - 0.05 * ((xs[None, :] - w / 2) / (w / 2)) ** 2)
        im = Image.fromarray(np.uint8(np.clip(np.asarray(im, np.float32) * s[:, :, None], 0, 255)))
    g = Ground(im, saturated(im), moist(im), mask, soil, lenses, ys)
    _GROUNDS[key] = g
    return g


def mesh_warp(im: Image.Image, shift, nx: int = 48, ny: int = 40, resample=Image.BILINEAR) -> Image.Image:
    """Move the picture's pixels down by shift(x, y) final pixels, where (x, y) is the place in the RESULT (so the
    function answers: how far above me was the stuff that is now here?). A mesh of nx by ny cells, bilinear."""
    W, H = im.size
    gx = np.linspace(0, W, nx + 1)
    gy = np.linspace(0, H, ny + 1)
    src = np.array([[gy[j] - SS * shift(gx[i] / SS, gy[j] / SS) for i in range(nx + 1)] for j in range(ny + 1)])
    data = []
    for j in range(ny):
        for i in range(nx):
            box = (int(gx[i]), int(gy[j]), int(gx[i + 1]), int(gy[j + 1]))
            quad = (gx[i], src[j, i], gx[i], src[j + 1, i], gx[i + 1], src[j + 1, i + 1], gx[i + 1], src[j, i + 1])
            data.append((box, quad))
    return im.transform((W, H), Image.MESH, data, resample)


def water_table(b: Box, g: Ground, curve, alpha: float = 1.0, fringe: float = 9.0, clip: Image.Image | None = None,
                line=(206, 232, 252)):
    """Saturate the ground below y = curve(x) (a number or a function): the wet picture through a mask, a damp
    fringe above it and a light line on the table itself. `clip` (default: the whole block) limits it."""
    clip = g.mask if clip is None else clip
    f = curve if callable(curve) else (lambda _x: curve)
    if fringe:
        b.paste(g.damp, b.below(lambda x: f(x) - fringe, clip), alpha=0.30 * alpha)
    b.paste(g.wet, b.below(f, clip), alpha=alpha)
    m = Image.new("L", b.im.size, 0)
    ImageDraw.Draw(m).line([b.P(x, f(x)) for x in np.linspace(0, b.w, 160)], fill=int(215 * alpha),
                           width=int(2.2 * SS), joint="curve")
    b.im.paste(line, (0, 0), ImageChops.multiply(m, clip))
