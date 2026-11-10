"""HOW DEEP A FEW DAYS OF RAIN WET THE SOIL (the slide «soil» of the dams long cut): a close look at the top 60 cm
of the ground in the rain, the wetting front that goes down and stops at about 25 cm, and then the camera pulls
back to two metres of ground with a person for scale: the wet layer is a thin skin, the soil under it is dry and
the groundwater is far below the picture. One of the four cross-sections of src/onebit_sections.py; drawn with
src/onebit_section.py (the kit) and src/onebit_scenery.py.

The picture says what the fact check of 9 Nov 2026 allows and no more (src/onebit_damsexplain2.py): the three
lines of words["soil_labels"] and the ruler's ticks (words["cm"], words["m"]). The soil profile is a generic one
(dark topsoil, lighter subsoil, the plain's sand and gravel below): no depth of a layer is a claim.

The ground is ONE world in metres, seen by a camera (px per metre, the surface's height in the box). It is kept
as three nested pictures of the same world at rising resolution (the whole block, the middle, the close view), so
the pull-back is a real zoom: no cross-fade between two different textures.

    python -I src/onebit_sections.py soil --sheet
"""

from __future__ import annotations

import functools
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image, ImageChops, ImageDraw  # noqa: E402

import onebit_scenery as Y  # noqa: E402
import onebit_section as S  # noqa: E402

SS = S.SS
SECONDS = 13.75                                     # the slide's length in the voiced cut (damsexplain2v_fa)
CUE = dict(                                         # scene-local seconds, on the owner's words (piece v05)
    front=(0.5, 5.5),                               # «هر میلی‌متر بارون فقط حدودِ نیم سانت … خیس کنه»: the front goes down
    label=6.1,                                      # «بارونِ این چند روز»: the wet layer's label
    clear=(6.3, 2.0),                               # the rain stops, the sky clears
    back=(7.2, 2.2),                                # «بیست سانتیِ اول»: the camera pulls back
    one=8.7,                                        # the one-metre tick comes into the picture
    dry=9.6,                                        # the camera has settled: the soil under the wet skin, its label
    deep=10.6,                                      # «پایین‌ترش که هنوز خشکِ خشک»: and the groundwater is far below
)
CAM = dict(cx=560.0, s=(880.0, 150.0), gy=(250.0, 470.0), top=(40.0, 14.0))   # close → wide: px per m, surface, top face
XW, DW = (-3.90, 1.95), (-0.06, 2.30)               # the world: metres across (0 under the label's leader), depth
LEVELS = ((XW[0], XW[1], DW[1], 300.0), (-1.75, 0.87, 1.45, 560.0), (-0.70, 0.36, 0.68, 1320.0))   # x0, x1, d1, px per m
FEATHER = 0.05                                      # m: a finer picture blends into the coarser one over this
PERSON_X, PERSON_M = -2.40, 1.75                    # where the person stands (m), how tall
RULER_X = 30.0                                      # the ruler's right edge in the box, px
WET, MOIST = (0.80, 0.38), 0.70                     # wet ground: how much of the damp picture and of the water tint;
#                                                     the damp picture's darkness (lighter than the rain slide's thin
#                                                     skin: here the wet soil fills a third of the picture)
TOP_DRY, TOP_WET = (190, 178, 140), (150, 142, 122)
SUBSOIL = (192, 154, 108)
STRAW = ((176, 160, 96), (150, 146, 84), (132, 138, 78), (112, 132, 72), (190, 170, 110))
LEAVES = ((196, 140, 60), (176, 108, 48), (150, 96, 52), (208, 168, 84), (166, 84, 44))


def relief(x):
    """The surface's own small ups and downs, m (down is positive), at x m."""
    return 0.006 * np.sin(x * 7.3) + 0.004 * np.sin(x * 19.1 + 1.0)


def horizons(x):
    """Depth of the topsoil's base and of the subsoil's base below the surface at x, m."""
    return (0.15 + 0.012 * np.sin(x * 9.0) + 0.007 * np.sin(x * 31.0 + 1.0),
            0.88 + 0.05 * np.sin(x * 2.1 + 0.5) + 0.02 * np.sin(x * 7.7))


def front_shape(x):
    """The wetting front is not a ruler: its depth at x as a factor around 1 (exactly 1 at the close view's ruler,
    so the front stops on the tick)."""
    f = lambda v: (0.05 * np.sin(v * 21.0 + 1.0) + 0.035 * np.sin(v * 57.0 + 2.2)     # noqa: E731
                   + 0.008 * np.sin(v * 131.0 + 0.7) + 0.004 * np.sin(v * 293.0 + 2.1))
    return 1.0 + f(x) - f((RULER_X - CAM["cx"]) / CAM["s"][0])


def camera(t: float, cue: dict):
    """(z, s, gy, top): the pull-back 0..1, px per metre, the surface's y in the box, the top face's depth in px."""
    z = S.ramp(t, *cue["back"])
    s = CAM["s"][0] * (CAM["s"][1] / CAM["s"][0]) ** z
    return z, s, CAM["gy"][0] + (CAM["gy"][1] - CAM["gy"][0]) * z, CAM["top"][0] + (CAM["top"][1] - CAM["top"][0]) * z


def _field(shape, x0: float, d0: float, ppm: float, cell: float, seed: int, sx: float = 1.0) -> np.ndarray:
    """World-anchored value noise in 0..1 for a picture whose corner is (x0, d0) m at ppm px per metre: a random
    lattice with cells of `cell` m (sx times longer across), the same lattice whatever the picture."""
    H, W = shape
    cx, cy = cell * sx, cell
    g = np.random.default_rng(seed).random((int((DW[1] - DW[0]) / cy) + 4, int((XW[1] - XW[0]) / cx) + 4),
                                           dtype=np.float32)
    box = ((x0 - XW[0]) / cx + 1.0, (d0 - DW[0]) / cy + 1.0, (x0 + W / ppm - XW[0]) / cx + 1.0,
           (d0 + H / ppm - DW[0]) / cy + 1.0)
    return np.clip(np.asarray(Image.fromarray(g).resize((W, H), Image.BICUBIC, box=box), np.float32), 0.0, 1.0)


def _fbm(shape, x0, d0, ppm, cell, seed, octaves, sx=1.0, gain=0.5) -> np.ndarray:
    out, amp, tot = np.zeros(shape, np.float32), 1.0, 0.0
    for o in range(octaves):
        if cell / 2 ** o * ppm >= 0.7:                 # finer than a pixel: it averages out
            out += amp * (_field(shape, x0, d0, ppm, cell / 2 ** o, seed * 131 + o, sx) - 0.5)
        tot += amp
        amp *= gain
    return 0.5 + out / tot


@functools.lru_cache(maxsize=1)
def stones() -> tuple:
    """Everything that lies in the ground, in metres: (kind, x, depth below the surface, radius, flatness, turn,
    colour, two phases). Kinds: 0 a stone, 1 a dark fleck, 2 gravel (thinned out in the fine beds), 3 a sand grain. One list
    for every picture of the world."""
    rng = np.random.default_rng(4107)
    out = []
    wide = XW[1] - XW[0]

    def add(n, d0, d1, small, big, sigma, palette, kind=0):
        for _ in range(int(n)):
            x = rng.uniform(XW[0], XW[1])
            lo, hi = (v(x) if callable(v) else v for v in (d0, d1))
            out.append((kind, x, rng.uniform(lo, hi), min(big, small * math.exp(rng.exponential(sigma))),
                        rng.uniform(0.52, 0.86), rng.uniform(-0.45, 0.45), palette[int(rng.integers(len(palette)))],
                        rng.uniform(0, 6.28), rng.uniform(0, 6.28)))

    soil_stones = ((188, 168, 140), (150, 132, 112), (206, 192, 170))
    base_a = lambda x: float(horizons(x)[0])            # noqa: E731
    base_b = lambda x: float(horizons(x)[1])            # noqa: E731
    add(wide * 0.15 * 1500, 0.004, base_a, 0.0016, 0.0050, 0.35, ((74, 46, 26),), kind=1)      # flecks in the topsoil
    add(wide * 0.15 * 22, 0.02, base_a, 0.0035, 0.011, 0.45, soil_stones)
    grains = ((232, 214, 178), (240, 228, 204), (206, 184, 146), (150, 120, 88), (124, 98, 72))
    add(wide * 0.15 * 1300, 0.004, base_a, 0.0008, 0.0018, 0.30, grains[:3], kind=3)           # sand grains
    add(wide * 0.73 * 2600, base_a, base_b, 0.0008, 0.0020, 0.30, grains, kind=3)
    add(wide * 0.73 * 300, base_a, base_b, 0.0016, 0.0040, 0.35, ((116, 84, 56),), kind=1)     # flecks in the subsoil
    add(wide * 0.73 * 420, base_a, base_b, 0.0020, 0.0050, 0.30, S.PEBBLES)                    # grit in the subsoil
    add(wide * 0.73 * 46, base_a, base_b, 0.0060, 0.026, 0.50, S.PEBBLES)
    add(wide * 1.42 * 150, base_b, DW[1] + 0.05, 0.0083, 0.047, 0.60, S.PEBBLES, kind=2)       # the plain's gravel
    return tuple(out)


@functools.lru_cache(maxsize=1)
def tufts() -> tuple:
    """The grass: (x m, how far back on the top face 0..1, blades), a blade = (dx m, height m, lean, colour, phase)."""
    rng = np.random.default_rng(977)
    out, x = [], XW[0]
    while x < XW[1]:
        if abs(x - PERSON_X) > 0.22:                  # nobody stands in a tuft
            blades = tuple((rng.uniform(-0.02, 0.02), rng.uniform(0.045, 0.125), rng.uniform(-0.5, 0.5),
                            STRAW[int(rng.integers(len(STRAW)))], rng.uniform(0, 6.28))
                           for _ in range(int(rng.integers(4, 8))))
            out.append((x, 0.0 if rng.random() < 0.6 else rng.uniform(0.25, 0.9), blades))
        x += rng.uniform(0.05, 0.12)
    return tuple(out)


def _smooth(p):
    p = np.clip(p, 0.0, 1.0)
    return p * p * (3.0 - 2.0 * p)


def _blob(X, Yc, r, flat, turn, p1, p2, n=14):
    """A pebble's outline: an ellipse r by r * flat, turned, a little out of round."""
    ca, sa, pts = math.cos(turn), math.sin(turn), []
    for j in range(n):
        th = 2.0 * math.pi * j / n
        q = 1.0 + 0.10 * math.sin(2.0 * th + p1) + 0.06 * math.sin(3.0 * th + p2)
        u, v = r * q * math.cos(th), r * flat * q * math.sin(th)
        pts.append((X + u * ca - v * sa, Yc + u * sa + v * ca))
    return pts


def _roots(d: ImageDraw.ImageDraw, x0: float, p2: float):
    """Fine roots under the grass at the cut face: pale threads that wander down and thin out."""
    for k, (x, back, _blades) in enumerate(tufts()):
        if back > 0.0:
            continue
        rng = np.random.default_rng(31000 + k)
        for _ in range(int(rng.integers(3, 6))):
            length, wd = rng.uniform(0.06, 0.28), rng.uniform(0.0012, 0.0024)
            px, pd, ang = x + rng.uniform(-0.015, 0.015), float(relief(x)), rng.uniform(-0.5, 0.5)
            steps = max(2, int(length / 0.012))
            for j in range(steps):
                ang = 0.82 * ang + rng.uniform(-0.38, 0.38)
                qx, qd = px + 0.012 * math.sin(ang), pd + 0.012 * math.cos(ang)
                wpx = wd * (1.0 - 0.75 * j / steps) * p2
                if wpx >= 0.45:
                    d.line([((px - x0) * p2, (pd - DW[0]) * p2), ((qx - x0) * p2, (qd - DW[0]) * p2)],
                           fill=(226, 208, 174, int(176 * min(1.0, wpx / 1.6))), width=max(1, int(round(wpx))))
                px, pd = qx, qd


@functools.lru_cache(maxsize=3)
def level(k: int) -> Image.Image:
    """Picture k of the world (RGB), from (LEVELS[k] x0, DW[0]) at about LEVELS[k]'s px per metre: drawn twice as
    large and scaled down. Do not draw on the result: it is cached."""
    x0, x1, d1, ppm = LEVELS[k]
    p2 = 2.0 * ppm
    W, H = 2 * int(round((x1 - x0) * ppm)), 2 * int(round((d1 - DW[0]) * ppm))
    shape = (H, W)
    xs = x0 + (np.arange(W, dtype=np.float32) + 0.5) / p2
    ds = DW[0] + (np.arange(H, dtype=np.float32) + 0.5) / p2
    dd = ds[:, None] - relief(xs)[None, :]                       # depth below the surface, m
    da, db = horizons(xs)
    wa = _smooth((da[None, :] - dd) / 0.02 + 0.5)                # topsoil
    wc = _smooth((dd - db[None, :]) / 0.08 + 0.5)                # the plain's sand and gravel
    wb = (1.0 - wa) * (1.0 - wc)                                 # subsoil
    tone = 0.90 + 0.20 * _fbm(shape, x0, DW[0], p2, 0.70, 11, 4, 3.0)
    crumb = _fbm(shape, x0, DW[0], p2, 0.045, 12, 6, gain=0.85) - 0.5   # structure at every scale of the zoom
    beds = _field(shape, x0, DW[0], p2, 0.147, 13, 16.0) - 0.5
    grain = np.random.default_rng(77 + k).random(shape, dtype=np.float32) - 0.5
    f = tone * (1.0 + (0.60 * wa + 0.34 * wb + 0.20 * wc) * crumb * 2.0 + (0.03 * wb + 0.09 * wc) * beds * 2.0
                + (0.07 * wa + 0.05 * wb + 0.045 * wc) * grain)
    f *= (1.0 - 0.10 * np.clip(dd / 1.6, 0.0, 1.0)) * (1.0 - 0.12 * wa * np.exp(-np.clip(dd, 0.0, None) / 0.035))
    col = (np.array(S.TOPSOIL, np.float32)[None, None, :] * wa[:, :, None]
           + np.array(SUBSOIL, np.float32)[None, None, :] * wb[:, :, None]
           + np.array(S.SAND, np.float32)[None, None, :] * wc[:, :, None]) * f[:, :, None]
    im = Image.fromarray(np.uint8(np.clip(col, 0, 255)))
    d = ImageDraw.Draw(im, "RGBA")
    bedmap = np.clip(0.25 + 1.5 * (_field((95, 234), XW[0], DW[0], 40.0, 0.23, 15, 9.0) - 0.3), 0.08, 1.0)
    for kind, x, dep, r, flat, turn, c, ph1, ph2 in stones():
        rp = r * p2
        if rp < (0.5 if kind in (1, 3) else 0.7) or not (x0 - 0.06 < x < x1 + 0.06):
            continue
        X, Yc = (x - x0) * p2, (float(relief(x)) + dep - DW[0]) * p2
        if Yc > H + rp:
            continue
        if kind == 2 and ph2 / 6.28 > bedmap[min(94, int((dep - DW[0]) * 40.0)), min(233, int((x - XW[0]) * 40.0))]:
            continue
        if kind == 1:
            d.ellipse([X - 1.5 * rp, Yc - 0.7 * rp, X + 1.5 * rp, Yc + 0.7 * rp], fill=tuple(c) + (110,))
        elif kind == 3:
            d.ellipse([X - rp, Yc - flat * rp, X + rp, Yc + flat * rp], fill=tuple(c) + (int(190 * min(1.0, rp / 1.4)),))
        elif rp < 2.6:
            d.ellipse([X - rp, Yc - flat * rp, X + rp, Yc + flat * rp], fill=c)
        else:
            d.polygon(_blob(X + 0.06 * rp, Yc + 0.36 * flat * rp, rp, flat, turn, ph1, ph2), fill=(70, 46, 26, 64))
            d.polygon(_blob(X, Yc, rp, flat, turn, ph1, ph2), fill=c)
            if rp > 9.0:
                d.line(_blob(X, Yc, rp, flat, turn, ph1, ph2) + _blob(X, Yc, rp, flat, turn, ph1, ph2)[:1],
                       fill=(70, 50, 34, 70), width=2)
            d.polygon(_blob(X - 0.24 * rp, Yc - 0.30 * flat * rp, 0.50 * rp, 0.62 * flat, turn, ph1, ph2),
                      fill=(255, 250, 236, 76))
    _roots(d, x0, p2)
    return im.resize((W // 2, H // 2), Image.LANCZOS)


@functools.lru_cache(maxsize=3)
def ground_view(w: int, h: int, s: float, gy: float):
    """The dry ground as the camera sees it: (picture at SS scale, the box row y_top it starts at). The coarse
    picture of the whole world first, the finer ones over it where they reach, their edges feathered. Do not draw
    on the result: it is cached (the camera stands still before and after the pull-back)."""
    cx = CAM["cx"]
    y_top = int(math.floor(gy - 0.03 * s)) - 2
    out = Image.new("RGB", (w * SS, (h - y_top) * SS), S.SAND)
    use = [1.0, S.ease((s / LEVELS[0][3] - 0.62) / 0.25), S.ease((s / LEVELS[1][3] - 0.62) / 0.25)]
    xa, xb, da, db = -cx / s, (w - cx) / s, (y_top - gy) / s, (h - gy) / s          # the view, m
    for k, (x0, x1, d1, _ppm) in enumerate(LEVELS):
        covers = x0 + FEATHER <= xa and xb <= x1 - FEATHER and db <= d1 - FEATHER
        if use[k] <= 0.0 or (k < 2 and use[k + 1] >= 1.0 and LEVELS[k + 1][0] + FEATHER <= xa
                             and xb <= LEVELS[k + 1][1] - FEATHER and db <= LEVELS[k + 1][2] - FEATHER):
            continue                                              # not needed, or hidden by the next finer one
        im = level(k)
        X0 = max(0, int(math.floor((cx + x0 * s) * SS)))          # the picture's place in the result, px
        X1 = min(w * SS, int(math.ceil((cx + x1 * s) * SS)))
        Y1 = min((h - y_top) * SS, int(math.ceil((gy + d1 * s - y_top) * SS)))
        if X1 - X0 < 2 or Y1 < 2:
            continue
        wx = lambda X: (X / SS - cx) / s                          # noqa: E731  result px -> m
        wd = lambda Yp: (Yp / SS + y_top - gy) / s                # noqa: E731
        ku, kv = im.width / (x1 - x0), im.height / (d1 - DW[0])
        box = (max(0.0, (wx(X0) - x0) * ku), max(0.0, (wd(0) - DW[0]) * kv),
               min(float(im.width), (wx(X1) - x0) * ku), min(float(im.height), (wd(Y1) - DW[0]) * kv))
        piece = im.resize((X1 - X0, Y1), Image.BICUBIC, box=box)
        if k == 0:
            out.paste(piece, (X0, 0))
            continue
        fx = wx(np.arange(X0, X1) + 0.5)
        fy = wd(np.arange(0, Y1) + 0.5)
        ax = np.clip((fx - x0) / FEATHER, 0.0, 1.0) * np.clip((x1 - fx) / FEATHER, 0.0, 1.0)
        ay = np.clip((d1 - fy) / FEATHER, 0.0, 1.0)
        m = np.ones((Y1, X1 - X0), np.float32) * use[k] if covers else use[k] * np.outer(ay, ax)
        out.paste(piece, (X0, 0), Image.fromarray(np.uint8(255 * m)))
    return out, y_top


def blade(b: S.Box, x: float, y: float, hgt: float, lean: float, wd: float, colour, a: float = 1.0):
    """A blade of dry grass from (x, y): `hgt` px long, leaning by `lean` rad, `wd` px wide at its foot."""
    tip = (x + hgt * math.sin(lean), y - hgt * math.cos(lean))
    mid = (x + 0.42 * hgt * math.sin(0.35 * lean), y - 0.5 * hgt * math.cos(0.35 * lean))
    left, right = [], []
    for j in range(7):
        u = j / 6.0
        px = (1 - u) ** 2 * x + 2 * u * (1 - u) * mid[0] + u * u * tip[0]
        py = (1 - u) ** 2 * y + 2 * u * (1 - u) * mid[1] + u * u * tip[1]
        hw = 0.5 * wd * (1.0 - u) ** 0.8
        left.append((px - hw, py))
        right.append((px + hw, py))
    b.poly(left + right[::-1], S.rgba(colour, a))


def grass(b: S.Box, X, s: float, gy: float, top: float, tp: float, back: bool):
    """The tufts on the top face (back=True: those standing behind the cut edge; False: those on the edge)."""
    for k, (x, q, blades) in enumerate(tufts()):
        if (q > 0.0) != back:
            continue
        sx = X(x)
        if not -30.0 < sx < b.w + 30.0:
            continue
        y0 = gy + float(relief(x)) * s - q * top
        size = 1.0 - 0.28 * q                              # those further back are a little smaller
        for j, (dx, hb, lean, colour, ph) in enumerate(blades):
            sway = 0.05 * math.sin(1.7 * tp + ph) + 0.03 * math.sin(2.9 * tp + 1.3 * ph)
            blade(b, sx + dx * s, y0 + 1.0, hb * s * size, lean + sway, max(1.3, 0.0075 * s * size), colour)


def leaves(b: S.Box, X, s: float, gy: float, top: float):
    """Fallen leaves on the top face: pointed, with a midrib and a stalk, lying flat, in autumn colours."""
    x, k = XW[0] + 0.2, 0
    while x < XW[1]:
        q, ln = 0.24 + 0.52 * S.hash01(k, 41), (0.046 + 0.026 * S.hash01(k, 42)) * s
        sx, sy = X(x), gy + float(relief(x)) * s - q * top
        if -60.0 < sx < b.w + 60.0 and abs(x - PERSON_X) > 0.3:
            turn = (S.hash01(k, 43) - 0.5) * 1.1 + (math.pi if S.hash01(k, 46) < 0.5 else 0.0)
            c = LEAVES[int(S.hash01(k, 44) * len(LEAVES)) % len(LEAVES)]
            ry = max(1.0, min(0.21 * ln, 0.30 * top))
            ca, sa = math.cos(turn), 0.36 * math.sin(turn)        # the top face is seen from the side: flattened
            at = lambda u, v: (sx + (u - 0.5) * ln * ca - v * math.sin(turn) * 0.5,      # noqa: E731
                               sy + (u - 0.5) * ln * sa + v * (0.55 + 0.45 * abs(math.cos(turn))))
            us = [j / 12.0 for j in range(13)]
            half = [ry * math.sin(math.pi * u) ** 0.8 * (1.22 - 0.55 * u) for u in us]   # fuller at the stalk's end
            up = [at(u, -hw) for u, hw in zip(us, half)]
            low = [at(u, hw) for u, hw in zip(us, half)]
            b.poly([(px + 1.2, py + 0.3 * ry + 0.8) for px, py in up + low[::-1]], S.rgba((60, 44, 28), 0.24))
            b.poly(up + low[::-1], c)
            b.poly(up + [at(u, 0.0) for u in us[::-1]], S.rgba(S.mix(c, S.WHITE, 0.5), 0.30))      # the lit half
            rib = S.rgba(S.mix(c, S.INK, 0.5), 0.85)
            b.line([at(-0.16, 0.0), at(0.97, 0.0)], rib, max(1.0, 0.022 * ln))
            if ln > 26.0:
                for u in (0.25, 0.42, 0.59, 0.75):
                    hw = 0.72 * ry * math.sin(math.pi * u) ** 0.8 * (1.22 - 0.55 * u)
                    b.line([at(u, 0.0), at(u + 0.10, -hw)], rib, 1.0)
                    b.line([at(u, 0.0), at(u + 0.10, hw)], rib, 1.0)
        x += 0.24 + 0.52 * S.hash01(k, 45)
        k += 1


def wet_zone(b: S.Box, s: float, gy: float, y_top: int, F: float, block: Image.Image):
    """The soil the rain has reached, from the surface down to the front at F m (uneven, soft): the wet look of
    the family (WET), a little weaker towards the front, where the soil is only damp."""
    cx, W = CAM["cx"], b.w * SS
    ya, yb = y_top, int(min(b.h, gy + (1.25 * F + 0.03) * s + 8.0))
    if F * s < 0.4 or yb <= ya:
        return
    xm = ((np.arange(W, dtype=np.float32) + 0.5) / SS - cx) / s                    # m
    top = (gy + relief(xm) * s) * SS                                               # the surface, SS px
    dep = np.maximum(F * front_shape(xm) * s * SS, 1.0)                            # the front below it, SS px
    rows = (np.arange(ya * SS, yb * SS, dtype=np.float32) + 0.5)[:, None]
    q = (rows - top[None, :]) / dep[None, :]                                       # 0 at the surface, 1 at the front
    soft = max(1.5, 0.022 * s) * SS / dep                                          # the front's blur, in q
    m = (q > 0.0) * _smooth((1.0 - q) / soft[None, :] + 0.5) * (1.0 - 0.30 * np.clip(q, 0.0, 1.0) ** 2)
    box = (0, ya * SS, W, yb * SS)
    mask = ImageChops.multiply(Image.fromarray(np.uint8(255.0 * m)), block.crop(box))
    b.im.paste(S.moist(b.im.crop(box), MOIST), (0, ya * SS), mask.point(lambda v: int(v * WET[0])))
    b.im.paste(S.WATER, box, mask.point(lambda v: int(v * WET[1])))


def trickle(b: S.Box, s: float, gy: float, F: float, tp: float, a: float):
    """Water on its way down through the wet soil: small light drops from the surface to the front."""
    if a <= 0.02 or F * s < 14.0:
        return
    cx, dens = CAM["cx"], 62.0
    k0, k1 = int(math.floor((-cx / s - XW[0]) * dens)) - 1, int(math.ceil(((b.w - cx) / s - XW[0]) * dens)) + 1
    rx, ry = max(1.0, 0.0017 * s), max(1.6, 0.0050 * s)
    for k in range(k0, k1):
        x = XW[0] + (k + S.hash01(k, 71)) / dens
        u = (tp / (1.5 + 1.3 * S.hash01(k, 72)) + S.hash01(k, 73)) % 1.0
        al = a * S.ease(u / 0.12) * S.ease((1.0 - u) / 0.30)
        if al <= 0.02:
            continue
        xx = x + 0.004 * math.sin(9.0 * u + 6.28 * S.hash01(k, 74))
        px = cx + xx * s
        py = gy + (float(relief(xx)) + F * float(front_shape(xx)) * (0.05 + 0.88 * u ** 0.85)) * s
        b.line([(px, py - 3.2 * ry), (px, py)], S.rgba((190, 222, 250), 0.30 * al), 1.4 * rx)
        b.ellipse(px, py, rx, ry, S.rgba((198, 228, 252), 0.85 * al))


def ruler(b: S.Box, s: float, y0: float, lit: dict, a5: float):
    """The ruler down the left edge from the surface at y0: a tick every 5 cm while they can be told apart (a5),
    a longer one every 25 cm; `lit` = {depth m: 0..1}: the ticks the water has reached turn blue."""
    b.rect(RULER_X - 22.0, y0, RULER_X, b.h + 6.0, S.rgba(S.PAPER, 0.95), outline=S.rgba(S.INK, 0.55), width=1.2)
    n = int((b.h - y0) / (0.05 * s)) + 1
    for k in range(1, n + 1):
        d, y = 0.05 * k, y0 + 0.05 * k * s
        if y > b.h - 2.0:
            break
        major = k % 5 == 0
        a = 1.0 if major else a5
        if a > 0.02:
            b.line([(RULER_X - (13.0 if major else 7.0), y), (RULER_X, y)], S.rgba(S.INK, 0.85 * a), 1.6 if major else 1.2)
    for d, q in lit.items():
        y = y0 + d * s
        if q["a"] > 0.02 and y < b.h - 2.0:
            col = S.mix(S.INK, S.WATER_DARK, q["lit"])
            b.line([(RULER_X - 15.0, y), (RULER_X + 14.0, y)], S.rgba(col, q["a"]), 2.4)
            if q["lit"] > 0.02:
                b.ellipse(RULER_X + 14.0, y, 5.0 * q["lit"], 5.0 * q["lit"], S.rgba(S.WATER, q["a"]))


HORIZON = 300                                       # the mountain sprite's own horizon row (it is made once)
TICK = 24                                           # the size of the ruler's numbers


def scene(w: int, h: int, t: float, words: dict, tp: float | None = None, cue: dict = CUE,
          wet_cm: float = 25) -> Image.Image:
    """The box at the scene's time t (inf: everything shown); `tp` is the running clock of the rain, the clouds
    and the grass; the front stops at `wet_cm`."""
    tp = (t if np.isfinite(t) else 0.0) if tp is None else tp
    L = words["soil_labels"]
    b = S.Box(w, h, t)
    _, s, gy, top = camera(t, cue)
    cx = CAM["cx"]
    X = lambda x: cx + x * s                                         # noqa: E731  m -> box px
    surf = lambda px: gy + float(relief((px - cx) / s)) * s          # noqa: E731  the cut edge at box x
    y_h = gy - top
    clear = S.ramp(t, *cue["clear"])
    storm = 1.0 - clear
    raining = 1.0 - S.ramp(t, cue["clear"][0] - 0.4, 1.3)
    soaked = S.ramp(t, 0.15, 1.0)                                    # the surface is wet at once

    Y.sky(b, y_h + 4.0, storm=storm)
    Y.sun(b, 84, 62, 22, a=S.ramp(t, cue["back"][0] + cue["back"][1] - 0.1, 1.2))   # once the person has passed it
    Y.cloud(b, 150 + 2.0 * tp, 54, 320, 118, 1, storm=storm, a=storm)
    Y.cloud(b, 470 + 2.6 * tp, 46, 340, 124, 2, storm=storm, a=1.0 - 0.12 * clear)
    Y.cloud(b, 740 + 3.0 * tp, 60, 300, 112, 3, storm=storm, a=storm)
    Y.cloud(b, 232 + 2.4 * tp, 96, 210, 80, 4, a=0.92 * clear)       # fair weather: a small one, clear of the sun
    b.paste(Y.alborz_sprite(w, HORIZON, -34.0, 66.0, 30.0, 3650.0), x=0, y=y_h - HORIZON, alpha=0.30 + 0.70 * clear)
    Y.city(b, y_h, 64, 0, 0.27, a=0.36 + 0.64 * clear)
    Y.top_face(b, surf, top, colour=S.mix(TOP_DRY, TOP_WET, soaked), n=140)

    gv, y_top = ground_view(w, h, round(s, 4), round(gy, 4))
    block = b.below(surf, n=220)
    b.im.paste(gv, (0, y_top * SS), block.crop((0, y_top * SS, w * SS, h * SS)))
    p = 1.0 if not np.isfinite(t) else min(max((t - cue["front"][0]) / cue["front"][1], 0.0), 1.0)
    F = 0.01 * wet_cm * (1.0 - (1.0 - p) ** 2)                       # the front's depth, m: fast, then slower
    wet_zone(b, s, gy, y_top, F, block)
    trickle(b, s, gy, F, tp, raining * S.ease((F * s - 14.0) / 30.0))
    xs = np.linspace(0.0, w, 140)
    for j in range(5):                                               # the edge's own shadow on the cut face
        b.line([(x, surf(x) + 1.0 + 1.6 * j) for x in xs], S.rgba((58, 38, 22), 0.13 * (1.0 - j / 5.0)), 2.4)
    if raining * soaked > 0.02:                                      # water standing on the soil while it rains
        b.line([(x, surf(x) - 0.8) for x in xs], S.rgba((214, 234, 250), 0.75 * raining * soaked), 2.0)

    grass(b, X, s, gy, top, tp, True)
    leaves(b, X, s, gy, top)
    xp = X(PERSON_X)
    if xp > -0.25 * PERSON_M * s:                                    # the camera's pull-back brings the person in
        Y.person(b, xp, surf(xp) - 0.45 * top, PERSON_M * s)
    grass(b, X, s, gy, top, tp, False)
    floor = lambda px: surf(px) - top * (0.06 + 0.86 * ((px * 0.6180339) % 1.0))     # noqa: E731
    Y.rain(b, tp, raining, floor, top=40.0)

    y0 = surf(RULER_X - 11.0)
    near = S.fade(t, None, cue["back"][0])                           # the close view's ticks
    reach = lambda d: S.ease((F - d + 0.012) / 0.012)                # noqa: E731  (the close view's front at the ruler)
    ruler(b, s, y0, {0.10: dict(a=near, lit=reach(0.10)), 0.25: dict(a=1.0, lit=reach(0.25)),
                     0.50: dict(a=near, lit=0.0), 1.00: dict(a=S.fade(t, cue["one"]), lit=0.0)},
          S.ease((s - 380.0) / 220.0))
    tick = lambda d: y0 + d * s + 0.31 * TICK                        # noqa: E731
    b.label(RULER_X + 36.0, tick(0.10), words["cm"](10), until=cue["back"][0], size=TICK, anchor="ls", rise=0.0)
    b.label(RULER_X + 36.0, tick(0.25), words["cm"](25), size=TICK, anchor="ls", rise=0.0)
    b.label(RULER_X + 36.0, tick(0.50), words["cm"](50), until=cue["back"][0], size=TICK, anchor="ls", rise=0.0)
    b.label(RULER_X + 36.0, tick(1.00), words["m"](1), at=cue["one"], size=TICK, anchor="ls", rise=0.0)

    a_deep = S.fade(t, cue["deep"])
    if a_deep > 0:                                                   # the groundwater: down there, out of the picture
        bob = 3.0 * math.sin(2.4 * tp)
        b.arrow(802, 716 + bob, 802, 790 + bob, S.rgba(S.WATER_DARK, a_deep), 5.0, 15.0)
    two = L[0].replace(": ", ":\n", 1)
    assert two.count("\n") == 1, two
    b.label(806, 92, two, at=cue["label"], size=36, lead=(cx, surf(cx) + 0.5 * 0.01 * wet_cm * s))
    b.label(806, 606, L[1], at=cue["dry"], size=32)
    b.label(772, 770, L[2], at=cue["deep"], size=30, colour=S.WATER_DARK)
    return b.done()
