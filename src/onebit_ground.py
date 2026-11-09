"""CROSS-SECTIONS UNDER TEHRAN for the slide reels (block diagrams in the style of newsroom explainers): where a
storm's water goes, how deep it wets the soil, the falling water table, and the sinking ground.

Shapes are drawn SS times larger and scaled down (anti-aliased). Every frame is a pure function of its time
(stills and video match; particles come from a fixed hash, not a random state). A scene returns a Box: the
picture and its labels; the film draws the Persian labels at full resolution on cream pills (crisp text).
"""

from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

SS = 3
PAPER = (243, 236, 225)
SKY_TOP, SKY_LOW = (196, 222, 238), (236, 238, 232)
GRASS = (122, 150, 92)
SOIL_DRY, SOIL_WET = (170, 120, 76), (92, 60, 38)
TOPFACE = (200, 168, 120)
SAND, SAND_DOT = (222, 196, 148), (196, 166, 116)
WET_SAND, WET_DOT = (108, 158, 206), (78, 128, 182)
CLAY, CLAY_LINE = (148, 128, 112), (112, 94, 80)
ROCK = (132, 126, 120)
WATER, WATER_LIGHT, WATER_DARK = (42, 120, 214), (150, 196, 232), (24, 84, 160)
RAIN = (78, 124, 180)
CLOUD, CLOUD_DARK = (240, 242, 246), (166, 176, 190)
CITY, CITY_SIDE, CITY_WIN = (92, 84, 78), (70, 63, 58), (232, 218, 168)
STEEL, STEEL_DARK = (110, 118, 128), (70, 76, 86)
INK = (46, 33, 24)
WHITE = (255, 255, 255)
DEPTH = (18, -12)                                         # the block's top face: right and up


def ease(p: float) -> float:
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


def ramp(t: float, t0: float, dur: float) -> float:
    """0 before t0, 1 after t0 + dur, eased; t = inf gives the end state."""
    if not np.isfinite(t):
        return 1.0
    return ease((t - t0) / max(dur, 1e-6))


def mix(a, b, p: float):
    p = min(max(p, 0.0), 1.0)
    return tuple(int(round(x + (y - x) * p)) for x, y in zip(a, b))


def hash01(k: int, salt: int = 0) -> float:
    v = math.sin(k * 12.9898 + salt * 78.233) * 43758.5453
    return v - math.floor(v)


def clock(t: float) -> float:
    return 0.0 if not np.isfinite(t) else t


class Box:
    def __init__(self, w: int, h: int, bg=PAPER):
        self.w, self.h = w, h
        self.im = Image.new("RGB", (w * SS, h * SS), bg)
        self.d = ImageDraw.Draw(self.im)
        self.labels: list = []

    def P(self, x, y):
        return (x * SS, y * SS)

    def poly(self, pts, fill):
        self.d.polygon([self.P(x, y) for x, y in pts], fill=fill)

    def line(self, pts, fill, width=2.0):
        self.d.line([self.P(x, y) for x, y in pts], fill=fill, width=max(1, int(round(width * SS))), joint="curve")

    def dashed(self, x0, x1, y, fill, width=2.0, dash=14, gap=9):
        x = x0
        while x < x1:
            self.line([(x, y), (min(x + dash, x1), y)], fill, width)
            x += dash + gap

    def rect(self, x0, y0, x1, y1, fill, radius=0.0):
        box = [x0 * SS, y0 * SS, x1 * SS, y1 * SS]
        if radius:
            self.d.rounded_rectangle(box, radius=radius * SS, fill=fill)
        else:
            self.d.rectangle(box, fill=fill)

    def ellipse(self, cx, cy, rx, ry, fill):
        self.d.ellipse([(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS], fill=fill)

    def arrow(self, x0, y0, x1, y1, fill, width=4.0, head=14.0):
        self.line([(x0, y0), (x1, y1)], fill, width)
        a = math.atan2(y1 - y0, x1 - x0)
        for s in (-1, 1):
            self.line([(x1, y1), (x1 - head * math.cos(a + s * 0.45), y1 - head * math.sin(a + s * 0.45))], fill, width)

    def vgradient(self, x0, y0, x1, y1, top, bottom):
        for k in range(int(y0 * SS), int(y1 * SS)):
            p = (k - y0 * SS) / max(1.0, (y1 - y0) * SS)
            self.d.line([(x0 * SS, k), (x1 * SS, k)], fill=mix(top, bottom, p))

    def label(self, x, y, text, colour=INK, size=34, bold=True, lead=None, anchor="rs"):
        """A label for the film: (x, y) is the baseline end (right edge, RTL); lead is the point it names."""
        if lead is not None:
            self.line([(x - 6, y - 0.3 * size), lead], INK, 1.8)
            self.ellipse(lead[0], lead[1], 4.5, 4.5, INK)
        self.labels.append(dict(x=x, y=y, text=text, colour=colour, size=size, bold=bold, anchor=anchor))

    def done(self, radius=18) -> Image.Image:
        im = self.im.resize((self.w, self.h), Image.LANCZOS)
        mask = Image.new("L", (self.w * SS, self.h * SS), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, self.w * SS - 1, self.h * SS - 1], radius=radius * SS, fill=255)
        mask = mask.resize((self.w, self.h), Image.LANCZOS)
        out = Image.new("RGB", (self.w, self.h), PAPER)
        out.paste(im, (0, 0), mask)
        return out


# ── pieces ──

def sky(b: Box, y1: float, dark: float = 0.0):
    b.vgradient(0, 0, b.w, y1, mix(SKY_TOP, (150, 160, 172), dark), mix(SKY_LOW, (196, 200, 204), dark))


def cloud(b: Box, cx, cy, s, dark=0.0):
    col = mix(CLOUD, CLOUD_DARK, dark)
    for dx, dy, r in ((-1.15, 0.25, 0.6), (-0.4, -0.25, 0.85), (0.45, -0.05, 0.75), (1.15, 0.28, 0.55)):
        b.ellipse(cx + dx * s, cy + dy * s, r * s * 1.15, r * s * 0.82, col)
    b.rect(cx - 1.7 * s, cy + 0.05 * s, cx + 1.7 * s, cy + 0.62 * s, col, radius=0.3 * s)


def rain(b: Box, t, x0, x1, ytop, ground, n=150, speed=950.0, alpha=1.0, seed=1):
    if alpha <= 0.02:
        return
    col = mix(SKY_LOW, RAIN, alpha)
    for k in range(n):
        x = x0 + hash01(k, seed) * (x1 - x0)
        span = ground(x) - ytop
        if span <= 4:
            continue
        y = ytop + ((hash01(k, seed + 7) * span + speed * clock(t)) % span)
        L = 15 + 10 * hash01(k, seed + 3)
        b.line([(x, y), (x - 0.22 * L, y - L)], col, 2.0)


def top_face(b: Box, pts, colour=TOPFACE):
    """The block's top: the surface line and its copy shifted by DEPTH."""
    dx, dy = DEPTH
    back = [(x + dx, y + dy) for x, y in pts[::-1]]
    b.poly(pts + back, colour)
    b.line([(x + dx, y + dy) for x, y in pts], mix(colour, INK, 0.25), 1.4)


def strata(b: Box, surf, xs, soil_px, wet_px, table_y, clay=(), squeeze=0.0, bottom=None, dot_seed=7):
    """The cut face under surf: wet topsoil (wet_px), dry topsoil (to soil_px), sand and gravel with dots, clay
    lenses (thinner as `squeeze` goes 0 → 1), the saturated zone in blue below table_y, rock at the bottom."""
    w = b.w
    bottom = b.h if bottom is None else bottom
    top = [(x, surf(x)) for x in xs]
    ymin = min(y for _, y in top)
    b.poly(top + [(w, bottom), (0, bottom)], SAND)
    if table_y is not None and table_y < bottom:
        b.rect(0, table_y, w, bottom, WET_SAND)
    rng = np.random.default_rng(dot_seed)
    for _ in range(int(w * (bottom - ymin) / 230)):
        x, y = rng.uniform(0, w), rng.uniform(ymin, bottom)
        if y > surf(x) + soil_px + 3:
            r = rng.uniform(1.5, 3.3)
            wet = table_y is not None and y > table_y
            b.ellipse(x, y, r, r * 0.8, WET_DOT if wet else SAND_DOT)
    for (yc, thick, xa, xb) in clay:
        th = thick * (1.0 - 0.5 * squeeze)
        up = [(x, yc - th / 2 + 2.2 * math.sin(x / 37.0)) for x in np.linspace(xa, xb, 70)]
        dn = [(x, yc + th / 2 + 2.2 * math.sin(x / 41.0)) for x in np.linspace(xb, xa, 70)]
        b.poly(up + dn, CLAY)
        for j in range(1, 4):
            yy = yc - th / 2 + j * th / 4
            b.line([(x, yy + 1.4 * math.sin(x / 29.0 + j)) for x in np.linspace(xa + 6, xb - 6, 50)], CLAY_LINE, 1.1)
    if table_y is not None and table_y < bottom:
        b.line([(x, table_y + 1.6 * math.sin(x / 23.0)) for x in np.linspace(0, w, 140)], WATER_DARK, 2.6)
    soil = [(x, surf(x) + soil_px) for x in xs[::-1]]
    b.poly(top + soil, SOIL_DRY)
    if wet_px > 0.6:
        wet = [(x, surf(x) + min(wet_px, soil_px) + 1.5 * math.sin(x / 17.0)) for x in xs[::-1]]
        b.poly(top + wet, SOIL_WET)
    top_face(b, top)


def buildings(b: Box, x0, x1, base_of, sink=0.0, seed=3, scale=1.0):
    x, k = x0, 0
    while x < x1 - 18 * scale:
        bw = (24 + 16 * hash01(k, seed)) * scale
        bh = (38 + 64 * hash01(k, seed + 1)) * scale
        base = base_of(x + bw / 2) + sink
        dx, dy = DEPTH[0] * 0.6 * scale, DEPTH[1] * 0.6 * scale
        b.poly([(x + bw, base - bh), (x + bw + dx, base - bh + dy), (x + bw + dx, base + dy), (x + bw, base)], CITY_SIDE)
        b.poly([(x, base - bh), (x + dx, base - bh + dy), (x + bw + dx, base - bh + dy), (x + bw, base - bh)], (120, 110, 102))
        b.rect(x, base - bh, x + bw, base, CITY)
        for wy in np.arange(base - bh + 7 * scale, base - 7 * scale, 12 * scale):
            for wx in np.arange(x + 4 * scale, x + bw - 5 * scale, 8 * scale):
                b.rect(wx, wy, wx + 3.5 * scale, wy + 5.5 * scale, CITY_WIN)
        x += bw + 7 * scale
        k += 1


def well(b: Box, x, ground_y, bottom_y, t=np.inf, pumping=0.0, stick_out=0.0):
    head = ground_y - stick_out
    b.rect(x - 4.5, head - 16, x + 4.5, bottom_y, STEEL)
    b.rect(x - 4.5, head - 16, x - 1.5, bottom_y, STEEL_DARK)
    b.rect(x - 12, head - 26, x + 12, head - 15, STEEL_DARK, radius=2)
    if pumping > 0 and np.isfinite(t):
        L = max(10.0, bottom_y - ground_y)
        for j in range(5):
            y = bottom_y - ((t * 140 + j * L / 5) % L)
            b.ellipse(x, y, 2.8, 3.6, mix(STEEL, WATER, pumping))


def person(b: Box, x, ground_y, height_px, colour=INK):
    """A standing silhouette for scale (head, torso, arms, legs as rounded shapes) on ground_y."""
    hp = height_px
    if hp < 4:
        return
    head = hp * 0.065
    b.ellipse(x, ground_y - hp + head, head, head * 1.1, colour)
    sh, hip = ground_y - hp * 0.80, ground_y - hp * 0.47
    b.rect(x - hp * 0.085, sh, x + hp * 0.085, hip, colour, radius=hp * 0.04)
    for side in (-1, 1):
        b.poly([(x + side * hp * 0.075, sh + hp * 0.01), (x + side * hp * 0.115, sh + hp * 0.01),
                (x + side * hp * 0.13, hip + hp * 0.02), (x + side * hp * 0.095, hip + hp * 0.02)], colour)
        b.poly([(x + side * hp * 0.012, hip - hp * 0.01), (x + side * hp * 0.078, hip - hp * 0.01),
                (x + side * hp * 0.07, ground_y), (x + side * hp * 0.018, ground_y)], colour)


# ── 1. where the storm's water goes ──

def scene_rain(w: int, h: int, t: float, words: dict, tp=None) -> Box:
    tp = t if tp is None else tp                          # particles keep real time when the story is stretched
    b = Box(w, h)
    plain = 0.40 * h

    def surf(x):
        p = min(max(x / (0.52 * w), 0.0), 1.0)
        return (plain - 0.27 * h) + 0.27 * h * (0.5 - 0.5 * math.cos(math.pi * p))

    storm = 1.0 - ramp(t, 7.0, 1.2)                      # rain on until ~7 s
    sky(b, plain + 10, dark=0.35 * storm)
    cloud(b, 0.26 * w, 0.075 * h, 44, dark=0.55 * storm)
    cloud(b, 0.66 * w, 0.06 * h, 52, dark=0.55 * storm)
    if storm < 0.5:                                      # the sun after the storm
        b.ellipse(0.88 * w, 0.08 * h, 24, 24, mix(SKY_LOW, (246, 196, 80), 1 - 2 * storm))
    rain(b, tp, 0.04 * w, 0.96 * w, 0.12 * h, surf, alpha=storm)
    xs = np.linspace(0, w, 160)
    soil_px = 0.07 * h
    wet = soil_px * 0.42 * ramp(t, 1.5, 4.0)
    table = 0.84 * h
    strata(b, surf, xs, soil_px, wet, table, clay=((0.66 * h, 15, 0.45 * w, 0.97 * w),))
    # the reservoir: a lake behind a dam wall high in the mountain valley
    dx = 0.17 * w
    lake_y = surf(dx) - 3
    fill = 2.0 * ramp(t, 8.6, 1.4)
    b.poly([(0.05 * w, lake_y - fill), (dx, lake_y - fill), (dx - 4, lake_y + 22), (0.07 * w, lake_y + 14)], WATER)
    b.poly([(dx, lake_y - 14), (dx + 10, lake_y - 14), (dx + 16, lake_y + 26), (dx - 2, lake_y + 26)], (150, 150, 146))
    # the flood: a sheet of water over the slope and the streets, then it drains off the right edge
    sheet = ramp(t, 1.2, 1.6) * (1.0 - ramp(t, 5.0, 2.6))
    if sheet > 0.02:
        x0 = 0.24 * w
        pts_top = [(x, surf(x) - 7 * sheet) for x in np.linspace(x0, w, 90)]
        pts_bot = [(x, surf(x) + 1) for x in np.linspace(w, x0, 90)]
        b.poly(pts_top + pts_bot, mix(SKY_LOW, WATER, 0.9 * sheet))
        for k in range(18):                              # ripples running downstream
            s = (hash01(k, 11) + 0.45 * clock(tp)) % 1.0
            x = x0 + s * (w - x0)
            b.line([(x - 16, surf(x - 16) - 4 * sheet), (x, surf(x) - 4 * sheet)], mix(WATER, WHITE, 0.6), 2.0)
        b.arrow(0.90 * w, plain - 34, 0.99 * w, plain - 34, mix(SKY_LOW, WATER_DARK, sheet), 4.0, 12)
    # back to the air: wavy lines once the sun is out
    ev = ramp(t, 7.6, 1.0)
    if ev > 0.02 and np.isfinite(tp):
        for k in range(5):
            x = 0.56 * w + k * 0.075 * w
            y0 = surf(x) - 14 - ((tp * 26 + k * 13) % 46)
            b.line([(x + 4 * math.sin((y0 - yy) / 6.0), yy) for yy in np.arange(y0, y0 - 36, -2)],
                   mix(SKY_LOW, (110, 120, 132), ev), 2.6)
    # the stream into the dam
    if ramp(t, 8.4, 0.6) > 0.02:
        b.arrow(0.02 * w, surf(0.02 * w) + 6, 0.07 * w, lake_y - 4, WATER_DARK, 3.4, 10)
    buildings(b, 0.58 * w, 0.97 * w, surf)
    L = words["rain_labels"]
    if ramp(t, 2.0, 0.3) > 0.5 and sheet > 0.3:
        b.label(0.97 * w, 0.205 * h, L[0], colour=WATER_DARK, lead=(0.40 * w, surf(0.40 * w) - 6))
    if ramp(t, 4.6, 0.3) > 0.5:
        b.label(0.97 * w, plain + soil_px + 56, L[1], lead=(0.36 * w, surf(0.36 * w) + wet * 0.6))
    if ramp(t, 8.0, 0.3) > 0.5:
        b.label(0.97 * w, 0.205 * h, L[2], colour=(96, 104, 112), size=32, bold=False)
    if ramp(t, 9.2, 0.3) > 0.5:
        b.label(0.97 * w, 0.29 * h, L[3], colour=WATER_DARK, size=32, lead=(0.12 * w, lake_y - 6))
    if ramp(t, 10.4, 0.3) > 0.5:
        b.label(0.97 * w, table + 52, L[4], colour=WATER_DARK)
    return b


# ── 2. how deep a storm wets the soil ──

def scene_soil(w: int, h: int, t: float, words: dict, wet_cm: float, tp=None) -> Box:
    """A soil column under a person: the storm wets the top `wet_cm`; the camera pulls back from the top 0.6 m to
    2.2 m, and the person (1.75 m) shows the scale; the water table is only an arrow (its depth varies, no number)."""
    tp = t if tp is None else tp
    b = Box(w, h)
    z = ramp(t, 4.2, 2.2)
    shown = 0.6 + (2.0 - 0.6) * z                         # metres below ground in view
    gy = 0.13 * h + 0.37 * h * z                          # the ground line moves down to make room for the person
    k = (h - gy) / shown
    sky(b, gy + 8)
    rain(b, tp, 0.02 * w, 0.98 * w, 0.0, lambda x: gy, n=80, alpha=1.0 - ramp(t, 3.2, 0.6), seed=5)
    wet_m = wet_cm / 100 * ramp(t, 0.4, 2.6)
    xs = np.linspace(0, w, 60)
    strata(b, lambda x: gy, xs, soil_px=h - gy + 10, wet_px=wet_m * k, table_y=None, dot_seed=9)
    for x in np.arange(6, w, 9):
        b.line([(x, gy), (x + 3, gy - 7 - 4 * hash01(int(x), 4))], GRASS, 1.6)
    if z > 0.5:                                           # 1.75 m tall, on the same scale as the soil below
        person(b, 0.24 * w, gy, 1.75 * k * ramp(t, 5.9, 0.6))
    ticks = (0.1, 0.3, 0.5) if z < 0.5 else (0.25, 1.0, 2.0)
    for m in ticks:
        y = gy + m * k
        if y < h - 6:
            b.line([(12, y), (40, y)], INK, 2.2)
            txt = words["cm"](m * 100) if m < 0.99 else words["m"](m)
            b.labels.append(dict(x=46, y=y + 12, text=txt, colour=INK, size=28, bold=False, anchor="ls"))
    L = words["soil_labels"]
    if ramp(t, 2.8, 0.3) > 0.5:
        b.label(0.97 * w, gy + wet_m * k + 58, L[0], lead=(0.62 * w, gy + wet_m * k * 0.5))
    if z > 0.97:
        b.label(0.97 * w, gy + 1.2 * k, L[1], colour=(112, 82, 50))
        b.arrow(0.62 * w, h - 70, 0.62 * w, h - 12, WATER_DARK, 4.0, 14)
        b.label(0.58 * w, h - 30, L[2], colour=WATER_DARK, size=32)
    return b


# ── 3. the falling water table ──

def scene_ground(w: int, h: int, t: float, words: dict, years: tuple, tp=None) -> Box:
    """The water table falls from y_then to y_now while the year runs; the depth above it is not to scale (a break
    band says so); the storm's water stays in the top of the soil."""
    b = Box(w, h)
    gy = 0.20 * h

    def surf(x):
        return gy + 5 * math.sin(x / 95.0)

    sky(b, gy + 8)
    p = ramp(t, 0.8, 5.6)
    y_then, y_now = 0.42 * h, 0.80 * h
    table = y_then + (y_now - y_then) * p
    xs = np.linspace(0, w, 120)
    strata(b, surf, xs, 0.04 * h, 0.012 * h * ramp(t, 7.0, 1.0), table,
           clay=((0.58 * h, 12, 0.04 * w, 0.42 * w), (0.69 * h, 10, 0.54 * w, 0.96 * w)))
    yb = 0.31 * h                                         # the break band: the depth here is not drawn to scale
    zig = [(x, yb + 5 * (1 if int(x / 14) % 2 else -1)) for x in np.arange(0, w + 14, 14)]
    b.poly(zig + [(x, y + 14) for x, y in zig[::-1]], PAPER)
    b.line(zig, INK, 1.4)
    b.line([(x, y + 14) for x, y in zig], INK, 1.4)
    buildings(b, 0.40 * w, 0.62 * w, surf, scale=0.8)
    for kk, x in enumerate((0.10 * w, 0.27 * w, 0.71 * w, 0.86 * w)):
        well(b, x, surf(x), min(h - 6, table + 34 + 10 * kk), t=t if tp is None else tp, pumping=1.0 if p < 1 else 0.5)
    b.dashed(0, w, y_then, WHITE, 2.2)
    if p > 0.05:
        b.arrow(0.62 * w, y_then + 6, 0.62 * w, table - 6, INK, 3.4, 12)
    year = round(years[0] + (years[1] - years[0]) * p)
    b.labels.append(dict(x=0.97 * w, y=0.12 * h, text=words["fa_digits"](year), colour=INK, size=58, bold=True,
                         anchor="rs"))
    L = words["ground_labels"]
    b.label(0.97 * w, y_then - 12, L[0], colour=(60, 70, 82), size=30, bold=False)
    if p >= 1.0:
        b.label(0.97 * w, (y_then + y_now) / 2 + 16, L[1], size=40)
    if ramp(t, 6.8, 0.3) > 0.5:
        b.label(0.97 * w, gy + 0.04 * h + 38, L[2], size=32, lead=(0.33 * w, surf(0.33 * w) + 0.01 * h))
    if ramp(t, 7.6, 0.3) > 0.5:
        b.label(0.97 * w, y_now + 112, L[3], colour=WATER_DARK, size=30)
    return b


# ── 4. the sinking ground ──

def scene_sink(w: int, h: int, t: float, words: dict) -> Box:
    b = Box(w, h)
    s = ramp(t, 0.8, 6.0)
    gy = 0.26 * h
    drop = 46 * s                                         # exaggerated, labelled as such

    def bowl(x):
        return math.exp(-((x - 0.52 * w) / (0.30 * w)) ** 2)

    def surf(x):
        return gy + drop * bowl(x)

    sky(b, gy + drop + 8)
    xs = np.linspace(0, w, 160)
    strata(b, surf, xs, 0.04 * h, 0, 0.86 * h,
           clay=((0.47 * h + 0.6 * drop, 30, 0.04 * w, 0.97 * w), (0.66 * h + 0.35 * drop, 26, 0.03 * w, 0.95 * w)),
           squeeze=s)
    b.dashed(0, w, gy, INK, 2.0)                          # where the ground was
    buildings(b, 0.33 * w, 0.72 * w, surf, scale=0.95)
    xc = 0.24 * w
    well(b, xc, surf(xc), 0.88 * h, stick_out=drop * bowl(xc))
    if surf(0.80 * w) - gy > 10:                         # only once the ground has sunk under it
        b.arrow(0.80 * w, gy + 2, 0.80 * w, surf(0.80 * w) - 2, INK, 3.0, 10)
    L = words["sink_labels"]
    if s >= 1.0:
        b.label(0.97 * w, 0.12 * h, L[0], size=38, lead=(xc + 12, surf(xc) - drop * bowl(xc) - 18))
        b.label(0.97 * w, gy - 14, L[1], colour=(70, 70, 70), size=30, bold=False)
        b.label(0.97 * w, 0.47 * h + 0.6 * drop + 64, L[2], colour=INK, size=34)
    return b
