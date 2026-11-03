"""THE FIVE TEHRAN DAMS FROM SPACE: one autumn Landsat pass of each reservoir in 1404 (2025) and 1405 (2026), and
the storage the Tehran Regional Water Company reported for 1 Aban 1405 (23 October 2026), against the long-term
average of each dam. Three scenes of 2 bars at 60 BPM = 24 s, a silent track (the score: src/onebit_score_tehran5.py).

The order is from the worst to the best against the average: Mamlu (30 %), Lar (37 %), Latyan (50 %), Taleqan
(68 %), Karaj (119 %). Each dam has one bar of 60 BPM (4 s): its picture at its true shape in the same box, with
its own 1-km scale, 1404 for the first 1.2 s and then 1405; below it the dam's storage as a horizontal bar against
the dashed long-term average, moving from its 1404 value to its 1405 value when the picture flips. Scene 3 ends
on the five 1405 volumes stacked against the dashed total average (548) with a faint mark at the year before (217).

Measured: the pictures, from Landsat (USGS): get_mamlu.py, get_taleqan.py (data/mamlu, data/taleqan), and the
modules of the Lar, Karaj and Latyan reels (lar.py, karaj.py, latyan.py: their pictures and boxes). Official: the
storage figures (src/tehran5.py), the only volumes on screen. No area of a reservoir is printed on the reel.

    outputs/onebit/social/tehran5_kahgel_fa_reel.mp4, _cover.png

    python -I src/onebit_tehran5.py
    python -I src/onebit_tehran5.py --stills
"""

from __future__ import annotations

import argparse
import math
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import get_karaj  # noqa: E402
import get_lar  # noqa: E402
import get_latyan  # noqa: E402
import get_mamlu  # noqa: E402
import get_taleqan  # noqa: E402
import karaj  # noqa: E402
import lar  # noqa: E402
import latyan  # noqa: E402
import mamlu  # noqa: E402
import onebit  # noqa: E402
import onebit_karaj  # noqa: E402
import onebit_latyan  # noqa: E402
import onebit_lar  # noqa: E402
import tehran5  # noqa: E402
import taleqan  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, PIXEL, SIZES, SOCIAL_CRF, Canvas, fa  # noqa: E402
from onebit_slides import BAR, COLOURS, LEFT, RIGHT, RULE, WIN, Slides  # noqa: E402

PACE = dict(bpm=60, bars=(2, 2, 2))               # 8 s a scene: 24 s
ORDER = ("mamlu", "lar", "latyan", "taleqan", "karaj")   # worst to best against the long-term average
SEG = 4.0                                         # s: one dam, one bar of 60 BPM
FLIP = 1.2                                        # s into a dam's bar: 1404 gives way to 1405
MOVE = 0.4                                        # s: the bar moves from the 1404 value to the 1405 value
STACK = 20.0                                      # s: the five 1405 volumes are stacked (scene 3's second part)
LATER_STACK = STACK - 16.0                         # s into scene 3 (later(2)): the total lands with the stack
MODS = dict(mamlu=mamlu, lar=lar, latyan=latyan, taleqan=taleqan, karaj=karaj)
GETS = dict(mamlu=get_mamlu, lar=get_lar, latyan=get_latyan, taleqan=get_taleqan, karaj=get_karaj)
# the picture box of each dam: W, S, E, N, the reservoir and its shore (the Lar, Karaj and Latyan reels' own boxes)
BOXES = dict(mamlu=(51.7452, 35.5768, 51.8125, 35.6553), taleqan=(50.6220, 36.1600, 50.7455, 36.1950),
             lar=onebit_lar.BOX, latyan=onebit_latyan.BOX, karaj=onebit_karaj.BOX)
PIC_X, PIC_Y = WIN[0] + 3, RULE + 24              # the one picture box, the same for every dam
PIC_W, PIC_H = WIN[2] - 6, 620                    # px
STRETCH, GAMMA = 0.30, 1.3                        # reflectance shown as white; one stretch for every year and dam
CHIP_H = 72                                       # px: a year box on the picture (phone floor: at least 70)
AVG_AT = 0.70                                     # each dam's bar is scaled so its long-term average sits at 70 % of the width
BAR_Y, BAR_H = 1272, 44                           # px: the dam's volume bar
VALUE_Y = 1424                                    # px: the line under the volume bar
BLUE = "#1c5cab"                                  # kahgel's ramp: the water (the colour of the bars)
SOURCE_Y, SOURCE_GAP, SOURCE_PX = 1496, 38, 30
STK_BASE, STK_X0, STK_X1, STK_SCALE = 1196, 300, 520, 1.0    # the stacked column: base, its edges, px per million m3
STK_LABEL_X = 572                                 # px: the labels of the three small blocks


def persian(year: int) -> int:
    return year - 621                              # the autumn of Y lies in Persian year Y - 621


def half_up(x: float, places: int) -> str:
    """A number as the press writes it (half up, not the float's own rounding)."""
    return str(Decimal(str(x)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP))


def words() -> dict:
    return dict(
        scenes=(("پنج سدِ تهران از فضا: // کدام {بالای میانگین} است؟", ""),
                ("حجمِ آب در ۱ آبان ۱۴۰۵، // نسبت به میانگینِ بلندمدت", ""),
                ("{فقط کرج} بالای میانگین؛ // مجموعِ پنج سد: ۳۵۹؛ میانگین ۵۴۸", "")),
        follow="این را برای کسی بفرستید که در تهران زندگی می‌کند",
        sources=("منبع: لندست (USGS)، گذرِ نزدیک به ۹ مهر",
                 "حجم: شرکتِ آبِ منطقه‌ای تهران، خبرگزاریِ مهر، ۴ آبان ۱۴۰۵"),
    )


def fit(box: tuple, w_max: float, h_max: float) -> tuple:
    """The picture's size at its true shape inside a w_max x h_max box: one scale (px per km) on both axes, the
    longitude squeezed by the cosine of the latitude. Returns (width px, height px, px per km)."""
    w, s, e, n = box
    km_w = (e - w) * 111.32 * math.cos(math.radians((s + n) / 2))
    km_h = (n - s) * 111.32
    k = min(w_max / km_w, h_max / km_h)
    return round(km_w * k), round(km_h * k), k


def crop(key: str, arr: np.ndarray, box: tuple) -> np.ndarray:
    """The part of the dam's fixed grid inside the box (W, S, E, N); the last two axes are rows and columns."""
    g = GETS[key]
    w, s, e, n = box
    c0, c1 = round((w - g.GRID[0]) / g.RES), round((e - g.GRID[0]) / g.RES)
    r0, r1 = round((g.GRID[3] - n) / g.RES), round((g.GRID[3] - s) / g.RES)
    return arr[..., r0:r1, c0:c1]


def inside(box: tuple, grid: tuple, lon_lat: tuple) -> bool:
    w, s, e, n = box
    return w < lon_lat[0] < e and s < lon_lat[1] < n and grid[0] <= w and grid[1] <= s and e <= grid[2] \
        and n <= grid[3]


class Tehran5Film(Slides):
    def __init__(self, th: onebit.Theme, colour: dict):
        tehran5.check()
        self.d = {d["key"]: d for d in tehran5.DAMS}
        self.check_data()
        self.setup(th, "fa", colour, words(), PACE, "Tehran.Dams")
        self.hook_at_once = True
        self.th = th
        self.pic, self.geo, self.thumb, self.km = {}, {}, {}, {}
        self.strip_w, self.strip_h = PIC_W / len(ORDER) - 14, 330   # the strip's slot for one thumbnail
        for key in ORDER:
            self.build(key, th)
        self.layout()
        self.check_volume()
        # the strip: one scale (px per km) for all five, the largest that lets every thumbnail fit its slot
        self.strip_k = min(min(self.strip_w / self.km[key][0], self.strip_h / self.km[key][1]) for key in ORDER)
        for key in ORDER:
            w_km, h_km = self.km[key]
            self.thumb[key] = self.photo(key, 2026, BOXES[key], round(w_km * self.strip_k),
                                         round(h_km * self.strip_k), th)

    # ── checks: every number on screen is asserted here ──

    def check_volume(self) -> None:
        """Each dam's bar: its average at AVG_AT of the width; the 1405 value and the 1404 value on it; the lines."""
        for key in ORDER:
            d = self.d[key]
            assert abs(self.vx(d["long_term"], d["long_term"]) - (RIGHT - AVG_AT * (RIGHT - LEFT))) < 1e-9, key
            for v in (d["value"], d["last_year"]):
                assert LEFT - 1 <= self.vx(v, d["long_term"]) <= RIGHT + 1, (key, v)
            line = self.value_line(key, 2026)
            assert line.startswith(f"{d['name']}: ") and line.endswith(f"میانگین {fa(d['long_term'])}"), line
        k = self.d["karaj"]
        assert k["value"] / k["long_term"] > 1 and self.vx(k["value"], k["long_term"]) < RIGHT - AVG_AT * (RIGHT - LEFT), \
            "Karaj's 1405 bar crosses the average and stays inside the bar"
        assert self.vx(k["value"], k["long_term"]) >= LEFT, "Karaj's bar stays inside the window"
        assert self.value_line("mamlu", 2026) == "ماملو: ۲۸ میلیون مترمکعب؛ میانگین ۹۲"
        assert self.value_line("taleqan", 2026) == "طالقان: ۱۵۸ میلیون مترمکعب؛ میانگین ۲۳۲"

    def check_data(self) -> None:
        for key in ORDER:
            mod, g, box = MODS[key], GETS[key], BOXES[key]
            mod.checks()
            assert 2025 in mod.years() and 2026 in mod.years(), (key, "1404 and 1405 must be shown")
            assert inside(box, g.GRID, g.DAM), (key, "the dam point lies in its box, the box in the grid")
            d = self.d[key]
        ratio = {d["key"]: round(100 * tehran5.share(d)) for d in tehran5.DAMS}
        assert ratio == {"mamlu": 30, "lar": 37, "latyan": 50, "taleqan": 68, "karaj": 119}, ratio
        assert round(100 * tehran5.TOTAL["value"] / tehran5.TOTAL["long_term"], 1) == 65.5
        # Mamlu: the first reservoir autumn is 2008 (the first pass above 1 km2); Taleqan's is 2006
        first = {k: min(y for y in MODS[k].all_years() if MODS[k].area(y) > 1.0) for k in ("mamlu", "taleqan")}
        assert first == {"mamlu": 2008, "taleqan": 2006}, first
        # the two passes of each dam, as the captions state them (area in km2, half up)
        assert half_up(mamlu.area(2025), 3) == "1.690" and half_up(mamlu.area(2026), 3) == "1.895"
        assert half_up(taleqan.area(2025), 3) == "7.537" and half_up(taleqan.area(2026), 3) == "7.487"
        assert mamlu.frames().loc[2025, "item"] == "LC08_L2SP_164035_20251003_02_T1"
        assert mamlu.frames().loc[2026, "item"] == "LC09_L2SP_164035_20260928_02_T1"
        assert taleqan.frames().loc[2025, "item"] == "LC09_L2SP_165035_20251002_02_T1"
        assert taleqan.frames().loc[2026, "item"] == "LC08_L2SP_165035_20260927_02_T1"

    # ── pictures ──

    def build(self, key: str, th: onebit.Theme) -> None:
        """The dam's 1404 and 1405 pictures in the one box, at true shape, and its thumbnail for the cover."""
        box = BOXES[key]
        w, h, k = fit(box, PIC_W, PIC_H)
        ox, oy = (PIC_W - w) // 2, (PIC_H - h) // 2
        self.geo[key] = dict(w=w, h=h, k=k, ox=ox, oy=oy)
        for year in (2025, 2026):
            full = Image.new("RGB", (PIC_W, PIC_H), th.field)
            full.paste(self.photo(key, year, box, w, h, th), (ox, oy))
            self.pic[(key, year)] = full
        w_, s_, e_, n_ = box
        mid = math.radians((s_ + n_) / 2)
        self.km[key] = ((e_ - w_) * 111.32 * math.cos(mid), (n_ - s_) * 111.32)   # the box in km

    def photo(self, key: str, year: int, box: tuple, w: int, h: int, th: onebit.Theme) -> Image.Image:
        """The year's pass over the box, one stretch for all dams and years; not clear: the paper."""
        rgb = crop(key, MODS[key].picture(year), box)
        v = np.clip(rgb / STRETCH, 0, 1) ** (1 / GAMMA)
        field = np.array([int(th.field[i:i + 2], 16) / 255 for i in (1, 3, 5)])[:, None, None]
        v = np.where(np.isnan(v), field, v)
        im = Image.fromarray((np.moveaxis(v, 0, -1) * 255 + 0.5).astype(np.uint8))
        return im.resize((w, h), Image.LANCZOS)

    def locate(self, key: str, lon_lat: tuple) -> tuple:
        """The screen position (px) of a lon/lat point in the dam's picture."""
        w, s, e, n = BOXES[key]
        g = self.geo[key]
        return (PIC_X + g["ox"] + (lon_lat[0] - w) / (e - w) * g["w"],
                PIC_Y + g["oy"] + (n - lon_lat[1]) / (n - s) * g["h"])

    def layout(self) -> None:
        self.src_y = SOURCE_Y
        self.pic_bottom = PIC_Y + PIC_H
        assert self.pic_bottom + 24 < BAR_Y - 30, "the picture runs into the volume bar's label"
        assert VALUE_Y + 16 < self.src_y - SOURCE_PX, "the value line runs into the sources"

    # ── texts ──

    def value_line(self, key: str, year: int) -> str:
        """The dam's own numbers for the year: «ماملو: ۲۸ میلیون مترمکعب؛ میانگین ۹۲»."""
        d = self.d[key]
        v = d["value"] if year == 2026 else d["last_year"]
        return f"{d['name']}: {fa(v)} میلیون مترمکعب؛ میانگین {fa(d['long_term'])}"

    def clamp(self, c: Canvas, x: float, s: str, size: int = 30) -> float:
        w = c.width(s, FA_TEXT, size, "rtl")
        return min(max(x, LEFT + w / 2), RIGHT - w / 2)

    # ── time ──

    def later(self, i: int) -> float:
        return LATER_STACK if i == 2 else 1.6              # scene 3's total lands with the stack at 20 s

    def sources(self, c: Canvas):
        for k, line in enumerate(self.words["sources"]):
            assert c.width(line, FA_TEXT, SOURCE_PX, "rtl") <= RIGHT - LEFT, line
            c.text(RIGHT, self.src_y + SOURCE_GAP * k, line, FA_TEXT, SOURCE_PX, self.th.head, "rs", "rtl")

    def window(self, c: Canvas, i: int):
        """The shared window, with the follow line at 30 px in its title bar (the frame's line is 28 px)."""
        th = self.th
        x, y, w, h = WIN
        c.frame(x, y, x + w, y + h, fill=th.paper)
        c.fill(x, y, x + w, y + BAR, th.ink)
        c.frame(x + 3, y + BAR + 3, x + w - 3, y + h - 3)
        last = i == len(self.S.scenes) - 1
        if last:
            c.text(x + w - 12, y + BAR - 9, self.words["follow"], FA_TEXT, 30, th.title, "rs", "rtl")
            assert c.width(self.words["follow"], FA_TEXT, 30, "rtl") <= w - 24
        else:
            c.text(x + 12, y + BAR - 9, self.app, PIXEL, 32, th.title)
            c.text(x + w - 12, y + BAR - 9, f"[{i + 1:02d}/{len(self.S.scenes):02d}]", PIXEL, 32, th.title, "rs")
        c.fill(x + 3, RULE, x + w - 3, RULE + 2, th.ink)

    # ── drawing ──

    def scaled(self, im: Image.Image, c: Canvas) -> Image.Image:
        return im if c.k == 1 else im.resize((round(im.width * c.k), round(im.height * c.k)), Image.LANCZOS)

    def chip(self, c: Canvas, x: float, y: float, s: str):
        """A year on the picture, in a paper box, its right edge at x."""
        w = c.width(s, FA_BOLD, 48, "rtl")
        x0 = x - w - 28
        assert CHIP_H >= 70, "phone floor: a year box is at least 70 px tall"
        c.frame(x0, y, x0 + w + 28, y + CHIP_H, fill=self.th.field)
        c.text(x0 + w + 14, y + 53, s, FA_BOLD, 48, self.th.ink, "rs", "rtl")

    def dam(self, c: Canvas, t: float, k: int):
        """Scene 1-3's dam bar: the picture (1404, then 1405), the dam's name, its scale, and its volume bar."""
        key = ORDER[k]
        d = self.d[key]
        t0 = SEG * k
        year = 2025 if t - t0 < FLIP else 2026
        c.im.paste(self.scaled(self.pic[(key, year)], c), (c.X(PIC_X), c.Y(PIC_Y)))
        self.chip(c, PIC_X + PIC_W - 14, PIC_Y + 14, fa(persian(year)))
        xd, yd = self.locate(key, GETS[key].DAM)
        c.fill(xd - 6, yd - 6, xd + 6, yd + 6, self.th.ink)
        tw = c.width(d["label"], FA_TEXT, 30, "rtl")
        bw = tw + 28
        x0 = xd + 20 if xd + 20 + bw < PIC_X + PIC_W - 10 else xd - 20 - bw
        y0 = yd - 62
        c.frame(x0, y0, x0 + bw, y0 + 44, fill=self.th.field)
        c.text(x0 + bw - 14, y0 + 33, d["label"], FA_TEXT, 30, self.th.ink, "rs", "rtl")
        g = self.geo[key]
        bx, by = PIC_X + 26, PIC_Y + PIC_H - 46            # the 1-km scale, bottom left, its label right of it
        label = fa("۱ کیلومتر")
        tw = c.width(label, FA_TEXT, 30, "rtl")
        c.frame(bx - 14, by - 26, bx + g["k"] + 14 + tw + 14, by + 20, fill=self.th.field)
        c.fill(bx, by, bx + g["k"], by + 8, self.th.ink)
        c.text(bx + g["k"] + 14 + tw, by + 8, label, FA_TEXT, 30, self.th.ink, "rs", "rtl")
        c.frame(PIC_X, PIC_Y, PIC_X + PIC_W, PIC_Y + PIC_H)
        self.volume(c, t, t0, key, d)

    def vx(self, v: float, avg: float) -> float:
        """The x of a volume on a dam's own bar: its long-term average sits at AVG_AT of the width, 0 at the right."""
        return RIGHT - v / (avg / AVG_AT) * (RIGHT - LEFT)

    def volume(self, c: Canvas, t: float, t0: float, key: str, d: dict):
        """The dam's storage as a horizontal bar: the dashed long-term average, a faint mark for the year before,
        the bar moving from the 1404 value to the 1405 value at the flip, and the dam's own numbers."""
        th = self.th
        v0, v1, avg = d["last_year"], d["value"], d["long_term"]
        p = 0.0 if not np.isfinite(t) else min(max((t - t0 - FLIP) / MOVE, 0.0), 1.0)
        p = p * p * (3 - 2 * p)                           # smooth
        v = v0 + (v1 - v0) * p
        colour = th.mark if tehran5.share(d) > 1 else BLUE
        c.fill(self.vx(v, avg), BAR_Y, RIGHT, BAR_Y + BAR_H, colour)
        c.frame(LEFT, BAR_Y, RIGHT, BAR_Y + BAR_H, colour=th.ink)
        xm = self.vx(avg, avg)                            # the dam's long-term average: dashed, with its value
        for yy in range(BAR_Y - 10, BAR_Y + BAR_H + 10, 12):
            c.fill(xm - 2, yy, xm + 2, yy + 7, th.ink)
        lab_avg = fa(f"میانگین: {avg}")
        c.text(self.clamp(c, xm, lab_avg), BAR_Y - 20, lab_avg, FA_TEXT, 30, th.ink, "ms", "rtl")
        xo = self.vx(v0, avg)                             # a year earlier: a faint mark on the bar
        c.fill(xo - 2, BAR_Y - 8, xo + 2, BAR_Y + BAR_H + 8, th.dots)
        lab = fa(f"۱۴۰۴: {v0}")
        c.text(self.clamp(c, xo, lab), BAR_Y + BAR_H + 34, lab, FA_TEXT, 30, th.ink, "ms", "rtl")
        line = self.value_line(key, 2026 if t - t0 >= FLIP else 2025)
        c.text(RIGHT, VALUE_Y, line, FA_BOLD, 40, th.ink, "rs", "rtl")
        assert c.width(line, FA_BOLD, 40, "rtl") <= RIGHT - LEFT, line

    def cover(self, c: Canvas):
        """The five 1405 pictures in a strip at one scale (one px per km for all five), each named under it, and
        one scale bar for the strip."""
        cell = PIC_W / len(ORDER)
        base_y = PIC_Y + 60 + self.strip_h                # the strip's bottom line; thumbnails sit on it
        for k, key in enumerate(ORDER):
            im = self.thumb[key]
            x0 = PIC_X + k * cell + (cell - im.width) / 2
            y0 = base_y - im.height
            c.im.paste(self.scaled(im, c), (c.X(x0), c.Y(y0)))
            name = self.d[key]["label"]
            tw = c.width(name, FA_TEXT, 30, "rtl")
            c.text(PIC_X + (k + 0.5) * cell, base_y + 56, name, FA_TEXT, 30, self.th.ink, "ms", "rtl")
            assert tw <= cell - 8, name
        bx, by = PIC_X + 26, base_y + 120                # one 5-km scale bar, left, its label right of it
        label = fa("۵ کیلومتر")
        lw = c.width(label, FA_TEXT, 30, "rtl")
        assert 0 < 5 * self.strip_k < PIC_W - lw - 60
        c.frame(bx - 14, by - 26, bx + 5 * self.strip_k + 14 + lw + 14, by + 20, fill=self.th.field)
        c.fill(bx, by, bx + 5 * self.strip_k, by + 8, self.th.ink)
        c.text(bx + 5 * self.strip_k + 14 + lw, by + 8, label, FA_TEXT, 30, self.th.ink, "rs", "rtl")
        self.chip(c, PIC_X + PIC_W - 14, PIC_Y + 14, fa(persian(2026)))

    def stack(self, c: Canvas, t: float):
        """The five 1405 volumes stacked from the base (the Karaj block in the accent), the dashed total average
        (548) and a faint mark at the year before (217); the three small blocks are labelled to the side."""
        th = self.th
        grow = 1.0 if not np.isfinite(t) else min(max((t - STACK) / 0.4, 0.0), 1.0)
        grow = grow * grow * (3 - 2 * grow)
        yv = lambda v: STK_BASE - v * STK_SCALE          # noqa: E731  (px of a volume, up from the base)
        cum = 0.0
        blocks = []
        for key in ORDER:
            d = self.d[key]
            top, bot = yv((cum + d["value"]) * grow), yv(cum * grow)   # the stack grows as one column
            blocks.append((key, d, top, bot))
            cum += d["value"]
        for key, d, top, bot in blocks:
            colour = th.mark if tehran5.share(d) > 1 else BLUE
            c.fill(STK_X0, top, STK_X1, bot, colour)
            c.frame(STK_X0, top, STK_X1, bot, colour=th.field)     # a paper line between the blocks
        c.frame(STK_X0, yv(tehran5.TOTAL["value"] * grow), STK_X1, STK_BASE, colour=th.ink)
        c.fill(STK_X0 - 40, STK_BASE, STK_X1 + 40, STK_BASE + 3, th.ink)
        ya = yv(tehran5.TOTAL["long_term"])
        yo = yv(tehran5.TOTAL["last_year"])
        for xx in range(STK_X0 - 20, STK_X1 + 20, 12):
            c.fill(xx, ya - 2, xx + 7, ya + 2, th.ink)
            c.fill(xx, yo - 1, xx + 7, yo + 1, th.dots)
        for s, y in (("میانگینِ بلندمدت", ya + 10), (fa(f"۱۴۰۴: {tehran5.TOTAL['last_year']}"), yo + 10)):
            c.text(STK_X1 + 16 + c.width(s, FA_TEXT, 30, "rtl"), y, s, FA_TEXT, 30, th.ink, "rs", "rtl")
        for key, d, top, bot in blocks:                  # the labels: inside the big blocks, beside the small ones
            mid = (top + bot) / 2
            s = f"{d['name']} {fa(d['value'])}"
            if d["value"] * STK_SCALE >= 60:            # a big block: its label inside it
                c.text((STK_X0 + STK_X1) / 2, mid + 12, s, FA_BOLD, 36, th.field, "ms", "rtl")
            else:                                        # a small block: its label to the side, on a leader
                ly = {"mamlu": 1186, "lar": 1146, "latyan": 1106}[key]
                c.text(STK_LABEL_X + c.width(s, FA_TEXT, 30, "rtl"), ly, s, FA_TEXT, 30, th.ink, "rs", "rtl")
                c.d.line([(c.X(STK_X1), c.Y(mid)), (c.X(STK_LABEL_X - 6), c.Y(ly - 10))], fill=th.ink,
                         width=max(1, round(2 * c.k)))
        assert all(c.width(f"{d['name']} {fa(d['value'])}", FA_BOLD, 36, "rtl") < STK_X1 - STK_X0 - 10
                   for key, d, top, bot in blocks if d["value"] * STK_SCALE >= 60)
        total = fa(f"مجموع: {tehran5.TOTAL['value']} میلیون مترمکعب؛ پارسال {tehran5.TOTAL['last_year']}")
        c.text(RIGHT, VALUE_Y, total, FA_BOLD, 40, th.ink, "rs", "rtl")
        assert c.width(total, FA_BOLD, 40, "rtl") <= RIGHT - LEFT, total

    def body(self, c: Canvas, t: float):
        if not np.isfinite(t):
            self.cover(c)
            return
        if t >= STACK:
            self.stack(c, t)
            return
        k = min(int(t // SEG), len(ORDER) - 1)
        self.dam(c, t, k)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="kahgel", choices=["kahgel"], help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    args = ap.parse_args()
    film = Tehran5Film(onebit.THEMES[args.theme], COLOURS[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"tehran5_{args.theme}_fa"
    for old in (OUT / "social").glob(f"{base.name}_t*.png"):
        old.unlink()                                       # no stale frames of an earlier cut
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        times = [0.0]
        for k in range(len(ORDER)):
            times += [SEG * k + 0.6, SEG * k + 2.4]        # before and after the flip
        times += [STACK + 0.5, 23.9]
        for t in times:
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
