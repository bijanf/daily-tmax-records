"""WHERE THE STORM'S WATER GOES (the slide «rain» of the dams long cut): the real section along 51.42 E from the
Tochal ridge down to the Tehran plain, a reservoir behind its dam where the mountain ends, the city on the plain
and the ground under it. In the storm a sheet of flood water runs through the city and off the picture; the top
skin of the ground gets wet; after the storm part of that goes back to the air; the water table far below stays
where it was; and of ten drops, one reaches the reservoir. One of the four cross-sections of
src/onebit_sections.py; drawn with src/onebit_section.py (the kit) and src/onebit_scenery.py.

The picture says what the fact check of 9 Nov 2026 allows and no more (src/onebit_damsexplain2.py): the five lines
of words["rain_labels"]. The land's surface is the measured one (Copernicus GLO-30 along the meridian, a point a
kilometre, the corners rounded). The reservoir stands for the dams, which lie in valleys east and west of this
meridian; it, the buildings and the trees are far larger than life, and depths are not to scale: the break band
says so. The nine pale drops are not sorted into fates: the fact check gives no shares for them.

    python -I src/onebit_sections.py rain --sheet
"""

from __future__ import annotations

import functools
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image, ImageChops  # noqa: E402

import onebit_scenery as Y  # noqa: E402
import onebit_section as S  # noqa: E402

SECONDS = 26.0                                      # the slide's length in the voiced cut (damsexplain2v_fa)
CUE = dict(                                         # scene-local seconds, on the owner's words (piece v04)
    flood=(0.9, 2.1),                               # «این همه سیل… کجا رفت؟»: the sheet builds: start, length
    flood_label=5.0,                                # «سیل، وقتی بارون…» (5.04)
    skin=8.4,                                       # «جذب» (8.42): the top skin of the ground darkens
    skin_label=9.9,                                 # «بهش میگن سیل» (9.9–11.2): its words, once the first are read
    drain=(12.5, 2.5),                              # «اضافه بیاد… چند ساعته میاد و میره» (12.5–14.8): it runs off
    clear=(14.2, 2.2),                              # the storm ends as it goes: start, length
    air=15.3,                                       # «برآوردِ ما» (15.5): part goes back to the air
    deep=17.0,                                      # «آنالیزِ ما» (17.6): the water table has not moved
    drops=(19.3, 1.2),                              # «از هر ده قطره» (19.24–20.8): the ten appear one by one
    dam=20.4,                                       # the headline, in time to be read before the slide ends
    one=23.3,                                       # «یکی» (23.34): nine go pale
    fall=(24.0, 0.9),                               # «به سد میرسه» (24.2–24.9): the tenth falls into the reservoir
)
LAT = (35.95, 35.63)                                # the section's window: the Tochal ridge … the south of the city
Y_TOP, Y_LOW = 100.0, 452.0                         # where its highest and lowest points stand in the box
DAM_X, CREST, LEVEL, RISE = 452.0, 350.0, 362.0, 3.0   # the dam's water face, its crest, the lake, the tenth drop's rise
CITY_X = 530.0                                      # the city starts here, a stone's throw below the dam
SKIN, TABLE = 24.0, 706.0                           # the wet skin's depth; the water table, px
BREAK = (628.0, 644.0)                              # the break band: the depth below it is not to scale
GAP = (640.0, 668.0)                                # an open street in the city: the flood shows, the leader ends
DROPS = dict(x0=274.0, pitch=27.0, y=196.0, s=12.0, one=4)   # the row of ten; `one` is the drop over the lake


@functools.lru_cache(maxsize=2)
def land(w: int):
    """The surface per pixel column (x = -8 … w + 8): the measured section with its 1-km corners rounded."""
    surf0, _ = Y.section(w, Y_TOP, Y_LOW, *LAT)
    xs = np.arange(-8.0, w + 9.0)
    ys = np.array([surf0(float(min(max(x, 0.0), w))) for x in xs])
    ys = np.convolve(np.pad(ys, 5, mode="edge"), np.hanning(13)[1:-1] / np.hanning(13)[1:-1].sum(), mode="valid")
    return xs, ys


def surface(w: int):
    xs, ys = land(w)
    return lambda x: float(np.interp(x, xs, ys))


def bedrock(surf):
    """The top of the rock: at the surface under the mountain, diving under the alluvium of the plain."""
    return lambda x: surf(x) + 7.0 + 430.0 * min(max((x - 335.0) / 190.0, 0.0), 1.2) ** 1.15


def break_band(b: S.Box, y0: float, y1: float, a: float = 1.0, tooth: float = 12.0):
    """Two zigzag lines with paper between them: the ground between is left out."""
    xs = np.arange(-tooth, b.w + 2 * tooth, tooth)
    up = [(x, y0 + (4.0 if k % 2 else -4.0)) for k, x in enumerate(xs)]
    low = [(x, y1 + (4.0 if k % 2 else -4.0)) for k, x in enumerate(xs)]
    b.poly(up + low[::-1], S.rgba(S.PAPER, a))
    for pts in (up, low):
        b.line(pts, S.rgba(S.INK, 0.55 * a), 1.6)


def drop(b: S.Box, x: float, y: float, s: float, a: float = 1.0, pale: float = 0.0):
    """A raindrop s px in radius centred on (x, y): blue, or (pale 1) a pale outline of itself."""
    if a <= 0.01:
        return
    n = 22
    pts = [(x, y - 2.05 * s)]
    for k in range(n + 1):                                # the round belly, from the right shoulder to the left
        q = math.radians(-38.0 + 256.0 * k / n)
        pts.append((x + s * math.cos(q), y + 0.18 * s + s * math.sin(q)))
    fill = S.mix(S.WATER, (226, 234, 240), 0.86 * pale)
    b.poly(pts, S.rgba(fill, a * (1.0 - 0.45 * pale)))
    b.line(pts + [pts[0]], S.rgba(S.mix(S.WATER_DARK, (150, 168, 186), pale), a * (0.95 - 0.25 * pale)), 1.6)
    b.ellipse(x - 0.36 * s, y + 0.02 * s, 0.20 * s, 0.34 * s, S.rgba(S.WHITE, 0.62 * a * (1.0 - pale)))


def wisp(b: S.Box, x: float, y0: float, rise: float, u: float, a: float = 1.0):
    """Vapour leaving the ground at (x, y0): a wavy line that climbs `rise` px as u runs 0 → 1, with a head."""
    vis = a * min(1.0, u / 0.18) * min(1.0, (1.0 - u) / 0.30)
    if vis <= 0.02:
        return
    top = y0 - rise * (0.25 + 0.75 * u)
    n = 16
    pts = [(x + 5.0 * math.sin((y0 - (y0 + (top - y0) * k / n)) / 9.0 + 2.2 * u * math.pi),
            y0 + (top - y0) * k / n) for k in range(n + 1)]
    pts = pts[int(n * 0.45 * u):]                         # the tail lets go of the ground as it climbs
    for col, wd in ((S.rgba(S.WATER_DARK, 0.30 * vis), 6.0), (S.rgba((232, 244, 254), 0.96 * vis), 3.2)):
        b.line(pts, col, wd)
    hx, hy = pts[-1]
    b.poly([(hx, hy - 9.0), (hx - 6.5, hy + 2.0), (hx + 6.5, hy + 2.0)], S.rgba((232, 244, 254), 0.96 * vis))
    b.line([(hx - 6.5, hy + 2.0), (hx, hy - 9.0), (hx + 6.5, hy + 2.0)], S.rgba(S.WATER_DARK, 0.34 * vis), 1.3)


def sheet(b: S.Box, surf, d, tp: float, x0: float, part: str):
    """The flood on the plain right of x0: `d(x)` px of water over the land's top face. part "back": its surface
    behind the buildings; "front": the strip in front of them and the cut through the water, with the light on it."""
    xs = np.linspace(x0, b.w + 4.0, 110)
    dd = np.array([d(x) for x in xs])
    if dd.max() < 0.3:
        return
    wave = 1.0 + 0.16 * np.sin(xs / 21.0 - 3.4 * tp) + 0.08 * np.sin(xs / 8.3 - 6.1 * tp + 1.3)
    ys = np.array([surf(x) for x in xs])
    top = ys - dd * wave                                   # the water's surface at the cut
    a = float(min(1.0, dd.max() / 3.0))
    if part == "back":
        b.poly(list(zip(xs, top - TOP * np.minimum(1.0, dd / 2.0))) + list(zip(xs, top))[::-1],
               S.rgba(S.mix(S.WATER, S.WATER_LIGHT, 0.42), 0.94 * a))
        return
    b.poly(list(zip(xs, top - 0.46 * TOP * np.minimum(1.0, dd / 2.0))) + list(zip(xs, top))[::-1],
           S.rgba(S.mix(S.WATER, S.WATER_LIGHT, 0.42), 0.94 * a))
    b.poly(list(zip(xs, top)) + list(zip(xs, ys + 0.6))[::-1], S.rgba(S.WATER, 0.96 * a))
    b.line(list(zip(xs, top)), S.rgba((214, 234, 250), 0.9 * a), 1.5)
    span = b.w + 4.0 - x0
    for k in range(16):                                    # light running with the water
        u = (S.hash01(k, 71) + tp * (0.20 + 0.10 * S.hash01(k, 72))) % 1.0
        x = x0 + u * span
        j = int(min(len(xs) - 2, max(0, (x - x0) / span * (len(xs) - 1))))
        if dd[j] < 2.0:
            continue
        yy = top[j] - TOP * (0.08 + 0.80 * S.hash01(k, 73))
        ln = 9.0 + 12.0 * S.hash01(k, 74)
        slope = (ys[j + 1] - ys[j]) / (xs[j + 1] - xs[j])
        b.line([(x, yy), (x + ln, yy + slope * ln)], S.rgba(S.WHITE, 0.62 * a * min(1.0, u / 0.08, (1.0 - u) / 0.08)), 1.5)


TOP = 12.0                                          # px of the plain's top face behind the cut edge
WET = (0.78, 0.34)                                  # wet ground: how much of the damp picture, how much water tint


def scene(w: int, h: int, t: float, words: dict, tp: float | None = None, cue: dict = CUE) -> Image.Image:
    """The box at the scene's time t (inf: everything shown); `tp` is the running clock of rain, water and clouds."""
    tp = (t if np.isfinite(t) else 0.0) if tp is None else tp
    L = words["rain_labels"]
    b = S.Box(w, h, t)
    surf = surface(w)
    rock = bedrock(surf)
    g = S.ground("rain", w, h, surf, 9, rock=rock)

    clear = S.ramp(t, *cue["clear"])                      # 0 in the storm, 1 after it
    storm = 1.0 - clear
    Y.sky(b, Y_LOW + 20, storm=storm)
    Y.sun(b, 748, 56, 22, a=S.ramp(t, cue["clear"][0] + 0.6, cue["clear"][1]))
    Y.cloud(b, 118 + 2.0 * tp, 50, 320, 118, 1, storm=storm)
    Y.cloud(b, 426 + 2.6 * tp, 44, 340, 124, 2, storm=storm, a=1.0 - 0.12 * clear)
    Y.cloud(b, 712 + 3.0 * tp, 58, 300, 112, 3, storm=storm, a=storm)

    b.paste(g.dry, g.mask)
    x_toe = DAM_X + 0.74 * (surf(DAM_X + 46.0) + 3.0 - CREST)
    grow = S.ramp(t, *cue["flood"])
    gone = S.ramp(t, *cue["drain"])
    front = CITY_X - 90.0 + (w + 150.0 - CITY_X) * gone   # the sheet's upstream end, running off to the right

    def depth(x):                                         # the flood's depth on the plain, px
        if x < x_toe:
            return 0.0
        return 11.0 * grow * S.ease((x - x_toe - 12.0) / 70.0) * S.ease((x - front) / 90.0) * (1.0 - 0.55 * gone)

    # the wet skin of the ground, the water table far below it, the break band
    damp = S.fade(t, cue["skin"], dur=1.4)
    if damp > 0:
        def skin(x):
            return 12.0 + (SKIN - 12.0) * S.ease((x - DAM_X) / 60.0) + 1.6 * math.sin(x / 13.0) + 1.1 * math.sin(x / 4.7)
        m = ImageChops.subtract(b.below(lambda x: surf(x) + 1.0, n=320), b.below(lambda x: surf(x) + skin(x), n=320))
        b.paste(g.damp, m, alpha=WET[0] * damp)
        b.im.paste(S.WATER, (0, 0), m.point(lambda v: int(v * WET[1] * damp)))
    alluvium = ImageChops.subtract(g.mask, b.below(lambda x: rock(x) + 3.0 * math.sin(x / 23.0), n=420))
    S.water_table(b, g, TABLE, clip=alluvium)
    glow = S.fade(t, cue["deep"], cue["deep"] + 1.3, dur=0.7) if np.isfinite(t) else 0.0
    if glow > 0:                                          # the eye is led to the table: a light along it, then gone
        b.line([(474, TABLE), (w, TABLE)], S.rgba(S.WHITE, 0.85 * glow), 4.0)
    break_band(b, *BREAK)

    # the reservoir and its dam; the plain's top face; the city
    level = LEVEL - RISE * S.ramp(t, cue["fall"][0] + cue["fall"][1], 0.7)
    Y.pool(b, 300, DAM_X + 1, level, surf, tp=tp)
    Y.dam(b, DAM_X, CREST, surf(DAM_X + 46.0) + 3.0)
    face = S.mix((190, 178, 140), (150, 142, 122), max(damp, grow))
    Y.top_face(b, lambda x: surf(x) + 0.0, TOP * 1.0, x0=x_toe - 6.0, colour=face)
    sheet(b, surf, depth, tp, x_toe - 6.0, "back")
    base = lambda x: surf(x) - 0.5 * TOP                  # noqa: E731
    Y.buildings(b, CITY_X, GAP[0], base, 4, 40, 70)
    Y.buildings(b, GAP[1], 756, base, 9, 40, 70)
    Y.tree(b, 513, base(513) + 2, 40, 1)
    Y.grass(b, base, 756, w, 2)
    sheet(b, surf, depth, tp, x_toe - 6.0, "front")

    def floor(x):                                         # what a raindrop lands on
        if 300.0 < x < DAM_X and surf(x) > level:
            return level
        return surf(x) - (0.5 * TOP + depth(x) if x > x_toe else 0.0)

    Y.rain(b, tp, 1.0 - S.ramp(t, cue["clear"][0] - 0.8, 1.8), floor, top=62.0)

    a_air = S.fade(t, cue["air"], dur=0.8)                # vapour off the wet ground
    for k, x in enumerate(WISPS):
        wisp(b, x, base(x) - 2.0, 74.0 + 20.0 * S.hash01(k, 92), (tp / 2.9 + S.hash01(k, 91)) % 1.0, a_air)

    a_out = S.fade(t, cue["flood_label"], cue["drain"][0] + cue["drain"][1] - 0.5)
    if a_out > 0:                                         # the flood leaves the picture
        ya = base(792.0) - 30.0
        b.arrow(764, ya - 2.0, 822, ya + 1.0, S.rgba(S.WATER_DARK, a_out), 5.0, 15.0)

    D = DROPS                                             # ten drops; nine go pale, one falls into the reservoir
    pale = S.ramp(t, cue["one"], 0.6)
    lin = 1.0 if not np.isfinite(t) else min(max((t - cue["fall"][0]) / cue["fall"][1], 0.0), 1.0)
    x1, y_land = D["x0"] + D["pitch"] * D["one"], level - 1.18 * D["s"]
    for k in range(10):
        a = S.fade(t, cue["drops"][0] + cue["drops"][1] * (9 - k) / 10.0, dur=0.3)     # from the right, as one reads
        x, y = D["x0"] + D["pitch"] * k, D["y"] + 7.0 * (1.0 - a)
        if k != D["one"]:
            drop(b, x, y, D["s"], a, pale)
            continue
        yd = y + (y_land - y) * lin * lin                 # it falls as a drop does: faster and faster
        if lin > 0:                                       # the way it went stays drawn
            yy = D["y"] + 1.3 * D["s"]
            while yy < min(yd - 2.2 * D["s"], level - 16.0):
                b.ellipse(x1, yy, 1.9, 1.9, S.rgba(S.WATER, 0.85))
                yy += 9.0
        if lin < 1.0:
            drop(b, x, yd, D["s"], a)
        else:
            q = 1.0 if not np.isfinite(t) else min(1.0, (t - cue["fall"][0] - cue["fall"][1]) / 0.9)
            for j, r in enumerate((10.0 + 30.0 * q, 4.0 + 18.0 * q)):
                b.ellipse(x1, level + 0.5, r, 0.26 * r, None, outline=S.rgba(S.WHITE, 0.9 * (1.0 - q)), width=1.6)
            b.poly([(x1, level - 3.0), (x1 - 6.0, level - 14.0), (x1 + 6.0, level - 14.0)], S.rgba(S.WATER, 0.85))

    # the words (their leaders are drawn now, over the scenery)
    lines = (L[0].replace("؛ ", "؛\n", 1), L[1].replace(" خیس", "\nخیس", 1),
             L[3].replace(" زود", "\nزود", 1).replace(" (", "\n(", 1))
    assert [q.count("\n") for q in lines] == [1, 1, 2], lines
    xg = 0.5 * (GAP[0] + GAP[1])
    b.label(806, 190, lines[0], at=cue["flood_label"], until=cue["drain"][0] + cue["drain"][1] - 0.5, size=32,
            lead=(xg, base(xg) - 5.0))
    b.label(806, 538, lines[1], at=cue["skin_label"], size=30, lead=(700.0, surf(700.0) + 0.55 * SKIN))
    b.label(806, 300, L[2], at=cue["air"], size=28)
    b.label(806, 772, L[4], at=cue["deep"], size=28, colour=S.WATER_DARK)
    b.label(806, 140, lines[2], at=cue["dam"], size=36)
    return b.done()


WISPS = (512.0, 562.0, 608.0, 654.0, 694.0, 738.0, 790.0)   # where the vapour leaves the ground
