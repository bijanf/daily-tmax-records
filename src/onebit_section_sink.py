"""PUMPED CLAY COMPACTS: THE GROUND SINKS (the slide «sink» of the dams long cut): the place of the water-table
slide (the Alborz and the city on the horizon, apartment blocks, trees, a pumping well) on two thick clay beds.
The water table falls past the beds, the beds give up their water and get thinner, and everything above them sinks
into a wide shallow bowl. The well's casing stands in the ground below the beds, so it stays, and its bare pipe
shows; a dashed line stays where the ground was. One of the four cross-sections of src/onebit_sections.py; drawn
with src/onebit_section.py (the kit) and src/onebit_scenery.py.

The picture says what the fact check of 9 Nov 2026 allows and no more (src/onebit_damsexplain2.py): the three
lines of words["sink_labels"], one of which says that the sinking is drawn larger than life. Buildings and trees
go down upright and whole; nothing breaks, nothing rises again and no water comes back. Depths are not to scale.

    python -I src/onebit_sections.py sink --sheet
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import onebit_scenery as Y  # noqa: E402
import onebit_section as S  # noqa: E402

SS = S.SS
SECONDS = 26.25                                     # the slide's length in the voiced cut (damsexplain2v_fa)
CUE = dict(                                         # scene-local seconds, on the owner's words (piece v09)
    clay=(1.5, 2.6),                                # «لایه‌های رسی»: the beds are picked out, then the light fades
    table=(2.4, 7.0),                               # «می‌کشیم بیرون»: the water table falls past the beds
    drain=(3.2, 8.0),                               # the beds give up their water
    sink=(3.9, 7.6),                                # «زمین هم نشست پیدا می‌کنه … داره پایین می‌ره»
    old=6.2,                                        # «این هم که شما دیدید»: the label of the old ground
    deep=8.5,                                       # «سالی بیش از ۲۵ سانتی‌متر»: an arrow from the old ground down
    pipe=11.8,                                      # «همه چی ثبت شده»: the bare pipe
    lasting=13.7,                                   # «بیشترِ این نشست هم دیگه برگشتنی نیست»
)
GY, FAR = 250.0, 14.0                               # the old ground; the land's far edge lies FAR px above it
DROP, MID, WIDE = 46.0, 414.0, 250.0                # the bowl: its depth (larger than life), middle and width, px
UPPER, LOWER = (392.0, 448.0), (545.0, 593.0)       # the clay beds at rest: top and base
SHARE = 0.56                                        # the upper bed's share of the sinking
BEDS = ((420.0, 56.0, 14.0, 814.0), (569.0, 48.0, 10.0, 818.0))    # for S.ground: middle, thickness, from, to
TABLE, CONE = (372.0, 730.0), (8.0, 16.0)           # the water table before and after; its cone at the well
WELL_X, WELL_FOOT = 360.0, 780.0
ARROW_X = 412.0
TOP = (190, 178, 140)                               # the land's surface
BLOCKS = (24.0, 300.0, 3)                           # the apartment blocks: from, to, seed
TREES = ((452, 56, 3), (522, 62, 1), (716, 60, 2), (786, 52, 4))
TURF = ((6, 22, 1), (384, 430, 2), (474, 500, 3), (548, 690, 4), (740, 764, 5), (806, 826, 6))


def bowl(x):
    return np.exp(-((x - MID) / WIDE) ** 2)


def glide(p: float, a: float = 0.10, b: float = 0.30) -> float:
    """0..1 at an even speed, with a soft start (the first `a` of the way) and a soft stop (the last `b`)."""
    p = min(max(p, 0.0), 1.0)
    if p < a:
        s = p * p / (2 * a)
    elif p <= 1 - b:
        s = a / 2 + (p - a)
    else:
        s = a / 2 + (1 - a - b) + b / 2 - (1 - p) ** 2 / (2 * b)
    return s / (1 - (a + b) / 2)


def lift(x, y, sunk: float):
    """How far above the place (x, y) of the picture its ground lay at rest: the whole drop above the upper bed,
    less and less through each bed as it is pressed, nothing below the lower one."""
    d = DROP * sunk * bowl(x)
    d2 = (1.0 - SHARE) * d
    (u0, u1), (l0, l1) = UPPER, LOWER
    if y >= l1:
        return 0.0
    if y >= l0 + d2:
        return y - l0 - (y - l0 - d2) * (l1 - l0) / (l1 - l0 - d2)
    if y >= u1 + d2:
        return d2
    if y >= u0 + d:
        return y - u0 - (y - u0 - d) * (u1 - u0) / (u1 - u0 - (d - d2))
    return d


def flat(x):
    return GY


def land(b: S.Box, g, table, wet: float, glow: float, sunk: float) -> Image.Image:
    """The cut face, put together as it lay at rest (dry ground, water below the table, the beds still wet by
    `wet` and picked out by `glow`) and then pressed: every piece moved down by lift()."""
    r = S.Box(b.w, b.h, b.t)
    r.paste(g.dry, g.mask)
    if wet > 0.01:
        for m in g.clay:
            r.paste(g.wet, m, alpha=wet)
    S.water_table(r, g, table)
    if glow > 0.01:
        for m in g.clay:
            r.im.paste((255, 246, 222), (0, 0), m.point(lambda v: int(v * 0.36 * glow)))
    if sunk > 1e-4:
        y0, y1 = int(GY) - 2, int(LOWER[1]) + 10
        strip = r.im.crop((0, y0 * SS, b.w * SS, y1 * SS))
        strip = S.mesh_warp(strip, lambda x, y: lift(x, y + y0, sunk), nx=46, ny=(y1 - y0) // 5)
        r.im.paste(strip, (0, y0 * SS))
    return r.im


def seep(b: S.Box, tp: float, a: float, sunk: float):
    """Drops leaving the undersides of the beds while they drain."""
    if a <= 0.01:
        return
    for k in range(72):
        x = 34.0 + 760.0 * S.hash01(k, 31)
        if abs(x - WELL_X) < 14.0:
            continue
        u = (tp / (2.0 + 1.6 * S.hash01(k, 32)) + S.hash01(k, 33)) % 1.0
        y0 = UPPER[1] + (1.0 - SHARE) * DROP * sunk * float(bowl(x)) if k % 2 else LOWER[1]
        y = y0 + 3.0 + 44.0 * u ** 1.3
        q = a * S.ease(u / 0.15) * S.ease((1.0 - u) / 0.35)
        b.ellipse(x, y, 2.5, 3.6, S.rgba(S.WATER_LIGHT, 0.94 * q), outline=S.rgba(S.WATER_DARK, 0.5 * q), width=0.8)
        b.ellipse(x - 0.7, y - 1.1, 0.9, 1.2, S.rgba(S.WHITE, 0.85 * q))


def inflow(b: S.Box, tp: float, y_water: float):
    """Groundwater moving into the well's screen."""
    for k in range(14):
        side = 1.0 if k % 2 else -1.0
        u = (tp / (1.7 + S.hash01(k, 41)) + S.hash01(k, 42)) % 1.0
        y = WELL_FOOT - 5.0 - 28.0 * S.hash01(k, 43)
        if y < y_water + 5.0:
            continue
        x = WELL_X + side * (9.0 + 112.0 * (1.0 - u) ** 1.25)
        q = S.ease(u / 0.2) * S.ease((1.0 - u) / 0.12)
        b.line([(x, y), (x + side * 8.0, y)], S.rgba((226, 240, 252), 0.8 * q), 1.5)


def scene(w: int, h: int, t: float, words: dict, tp: float | None = None, cue: dict = CUE) -> Image.Image:
    """The box at the scene's time t (inf: everything shown); `tp` is the running clock of the pump and the sky."""
    tp = (t if np.isfinite(t) else 0.0) if tp is None else tp
    L = words["sink_labels"]
    b = S.Box(w, h, t)
    g = S.ground("sink", w, h, flat, 14, clay=BEDS)
    sunk = 1.0 if not np.isfinite(t) else glide((t - cue["sink"][0]) / cue["sink"][1])
    fall = S.ramp(t, *cue["table"])
    wet = 1.0 - S.ramp(t, *cue["drain"])
    glow = S.fade(t, cue["clay"][0], cue["clay"][1], dur=0.7)
    surf = lambda x: GY + DROP * sunk * float(bowl(x))                       # noqa: E731
    table = lambda x: (TABLE[0] + (TABLE[1] - TABLE[0]) * fall               # noqa: E731
                       + (CONE[0] + (CONE[1] - CONE[0]) * fall) * np.exp(-((x - WELL_X) / 52.0) ** 2))
    xs = np.linspace(0.0, w, 150)
    front = [(x, surf(x)) for x in xs]

    Y.sky(b, GY)
    Y.cloud(b, 232 + 2.4 * tp, 50, 230, 86, 1)
    Y.cloud(b, 52 + 1.6 * tp, 96, 160, 60, 2, a=0.85)
    Y.cloud(b, 668 + 1.3 * tp, 82, 190, 70, 3, a=0.9)
    Y.alborz(b, GY - FAR)
    Y.city(b, GY - FAR + 2, 80, 0, 0.27)
    b.poly([(0, GY - FAR), (w, GY - FAR)] + front[::-1], TOP)               # the land, lying lower in the bowl
    b.line([(0, GY - FAR), (w, GY - FAR)], S.rgba(S.mix(TOP, S.WHITE, 0.45), 0.9), 1.4)
    for j in range(6):                                                       # a soft shade where it lies low
        band = [(x, y - 2.6 * j) for x, y in front]
        back = [(x, max(y - 2.6 * (j + 1), GY - FAR)) for x, y in front]
        b.poly(band + back[::-1], S.rgba(S.INK, 0.075 * sunk * (1.0 - j / 6.0)))

    b.im.paste(land(b, g, table, wet, glow, sunk), (0, 0), b.below(surf, n=200))
    b.line(front, S.rgba(S.mix(TOP, S.INK, 0.55), 0.9), 1.6)
    busy = S.ramp(t, cue["drain"][0], 0.8) * (1.0 - S.ramp(t, cue["drain"][0] + cue["drain"][1] - 1.2, 1.8))
    seep(b, tp, busy if np.isfinite(t) else 0.0, sunk)
    inflow(b, tp, float(table(WELL_X)))

    Y.buildings(b, BLOCKS[0], BLOCKS[1], lambda x: surf(x) - 7.0, BLOCKS[2], 56, 112)
    for x, hh, seed in TREES:
        Y.tree(b, x, surf(x) - 4.0, hh, seed)
    for x0, x1, seed in TURF:
        Y.grass(b, surf, x0, x1, seed)
    a_old = S.fade(t, cue["sink"][0], dur=0.6)
    if a_old > 0:                                                            # where the ground was
        b.dashed(0, w, GY, S.rgba(S.PAPER, 0.85 * a_old), 5.4)
        b.dashed(0, w, GY, S.rgba(S.INK, 0.9 * a_old), 2.4)
    a_deep, gap = S.fade(t, cue["deep"]), surf(ARROW_X) - GY
    if a_deep > 0 and gap > 20.0:                                            # how far it has gone down
        bob = 1.5 * math.sin(2.4 * tp)
        b.arrow(ARROW_X, GY + 5.0 + bob, ARROW_X, GY + gap - 4.0 + bob, S.rgba(S.INK, a_deep), 3.6, 12.0)
    well_y = surf(WELL_X)
    Y.well(b, WELL_X, well_y, WELL_FOOT, float(table(WELL_X)), tp, 1.0, y_head=GY, wd=12.0, side=-1)

    old = L[1].replace(" (", "\n(", 1)
    last = L[2].replace(" برگشت", "\nبرگشت", 1)
    assert old.count("\n") == 1 and last.count("\n") == 1, (old, last)
    b.label(806, 128, old, at=cue["old"], size=28, lead=(640.0, GY))
    box = b.label(716, 62, L[0], at=cue["pipe"], size=30)
    if box is not None:                                                      # down beside the wellhead, then in
        a = S.fade(t, cue["pipe"])
        xk, yk, col = WELL_X + 28.0, 0.5 * (GY + well_y) + 2.0, S.rgba(S.INK, 0.9 * a)
        b.line([(xk, box[3]), (xk, yk)], col, 2.2)
        b.line([(xk, yk), (WELL_X + 11.0, yk)], col, 2.2)
        b.ring(WELL_X + 10.5, yk, 6.0, a)
    b.label(806, 643, last, at=cue["lasting"], size=38)
    return b.done()
