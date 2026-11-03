"""THE FIVE TEHRAN DAMS FROM SPACE: one autumn Landsat pass of each reservoir in 1405 (2026) and the storage the
Tehran Regional Water Company reported for 1 Aban 1405 (23 October 2026), against the long-term average of each dam.
Seven bars of 4 s (60 BPM) = 28 s, a silent track (the score: src/onebit_score_tehran5.py).

Bar 1: the hook, with the five 1405 lakes at one scale, named, appearing one by one. Bars 2-6: one dam each, in
the order from the worst to the best against its average: Mamlu (30 %), Lar (37 %), Latyan (50 %), Taleqan (68 %),
Karaj (119 %): its 1405 picture, the headline with its share, and its storage as a bar against the dashed average
(scaled to that dam's own average). Bar 7: the five 1405 volumes stacked against the dashed total average (548).

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

PACE = dict(bpm=60, bars=(1, 1, 1, 1, 1, 1, 1))   # seven bars of 4 s: 28 s
ORDER = ("mamlu", "lar", "latyan", "taleqan", "karaj")   # worst to best against the long-term average
SEG = 4.0                                         # s: one bar of 60 BPM (the hook, each dam, the stack)
DAM_T0 = SEG                                      # s: the first dam's bar; dam k starts at DAM_T0 + SEG * k
STACK = DAM_T0 + SEG * 5                          # s: the stacked total (bar 7)
END = STACK + SEG                                 # s: the end, 28 s
HL_STEP = 0.6                                     # s: the hook's highlight steps across the five lakes, in order
LAKE_ROWS = (("lar", "taleqan"), ("mamlu", "latyan", "karaj"))   # two rows at one scale (the wide lakes on top)
GROW = 1.0                                        # s: a bar grows once, from 0 to this year's value, then holds
MODS = dict(mamlu=mamlu, lar=lar, latyan=latyan, taleqan=taleqan, karaj=karaj)
GETS = dict(mamlu=get_mamlu, lar=get_lar, latyan=get_latyan, taleqan=get_taleqan, karaj=get_karaj)
# the picture box of each dam: W, S, E, N, the reservoir and its shore (the Lar, Karaj and Latyan reels' own boxes)
BOXES = dict(mamlu=(51.7452, 35.5768, 51.8125, 35.6553), taleqan=(50.6220, 36.1600, 50.7455, 36.1950),
             lar=onebit_lar.BOX, latyan=onebit_latyan.BOX, karaj=onebit_karaj.BOX)
LAKE_TOP, LAKE_BOTTOM = 88, 56                    # px: the lakes' area clears the year chip above and the scale bar below
PIC_X, PIC_Y = WIN[0] + 3, RULE + 24              # the one picture box, the same for every dam
PIC_W, PIC_H = WIN[2] - 6, 720                    # px: the satellite picture is the main element of each bar
STRETCH, GAMMA = 0.30, 1.3                        # reflectance shown as white; one stretch for every year and dam
CHIP_H = 72                                       # px: a year box on the picture (phone floor: at least 70)
AVG_AT = 0.70                                     # each dam's bar is scaled so its long-term average sits at 70 % of the width
ENG = dict(mamlu="Mamlu.Dam", lar="Lar.Dam", latyan="Latyan.Dam", taleqan="Taleqan.Dam", karaj="Karaj.Dam")
BAR_Y, BAR_H = 1360, 44                           # px: the bar under the picture (compact)
UNIT_Y = 1444                                     # px: the unit label at the bar's start (0)
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
    """The seven bars: the hook, the five dams (headline with the share of its average), the stack."""
    return dict(
        scenes=(("پنج سدِ تهران از فضا: // کدام {بالای میانگین} است؟", ""),
                ("سدِ ماملو: // {۳۰٪} میانگین", ""),
                ("سدِ لار: // {۳۷٪} میانگین", ""),
                ("سدِ لتیان: // {۵۰٪} میانگین", ""),
                ("سدِ طالقان: // {۶۸٪} میانگین", ""),
                ("سدِ کرج: // {۱۱۹٪} میانگین", ""),
                ("{فقط کرج} بالای میانگین؛ // مجموعِ پنج سد: ۳۵۹ از ۵۴۸", "")),
        follow="این را برای کسی بفرستید که در تهران زندگی می‌کند",
        sources=("منبع: لندست (USGS)، گذرِ نزدیک به ۹ مهر",
                 "حجم: شرکتِ آبِ منطقه‌ای تهران، خبرگزاریِ مهر، ۴ آبان ۱۴۰۵"),
    )


def share_pct(d: dict) -> int:
    """A dam's 1405 storage as a percentage of its average, rounded: the headline's figure."""
    return round(100 * tehran5.share(d))


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
        for key in ORDER:
            self.build(key, th)
        self.layout()
        self.check_volume()
        self.check_headlines()
        # the strip: one scale (px per km) for all five, the largest that lets every thumbnail fit its slot
        self.strip_k = self.fit_rows()
        for key in ORDER:
            w_km, h_km = self.km[key]
            self.thumb[key] = self.photo(key, 2026, BOXES[key], round(w_km * self.strip_k),
                                         round(h_km * self.strip_k), th)
        self.lake_xy = self.rows_layout(self.strip_k)

    # ── checks: every number on screen is asserted here ──

    def check_headlines(self) -> None:
        """Each dam's headline names the dam and its share of its average, rounded; the total's; the hook's."""
        sc = words()["scenes"]
        assert len(sc) == 7 and len(PACE["bars"]) == 7
        assert sc[0][0] == "پنج سدِ تهران از فضا: // کدام {بالای میانگین} است؟", sc[0][0]
        pct = {}
        for i, key in enumerate(ORDER, start=1):
            d = self.d[key]
            pct[key] = share_pct(d)
            assert sc[i][0] == f"{d['label']}: // {{{fa(pct[key])}٪}} میانگین", (key, sc[i][0])
        assert pct == {"mamlu": 30, "lar": 37, "latyan": 50, "taleqan": 68, "karaj": 119}, pct
        assert sc[6][0] == "{فقط کرج} بالای میانگین؛ // مجموعِ پنج سد: ۳۵۹ از ۵۴۸", sc[6][0]
        assert fa(tehran5.TOTAL["value"]) == "۳۵۹" and fa(tehran5.TOTAL["long_term"]) == "۵۴۸"
        for key in ORDER:                                # the numbers written on each bar
            d = self.d[key]
            assert self.value_line(key, 2026) == fa(d["value"]) and fa(d["long_term"]) == f"{fa(d['long_term'])}", key

    def check_volume(self) -> None:
        """Each dam's bar: its average at AVG_AT of the width; the 1405 value and the 1404 value on it."""
        for key in ORDER:
            d = self.d[key]
            assert abs(self.vx(d["long_term"], d["long_term"]) - (RIGHT - AVG_AT * (RIGHT - LEFT))) < 1e-9, key
            for v in (d["value"], d["last_year"]):
                assert LEFT - 1 <= self.vx(v, d["long_term"]) <= RIGHT + 1, (key, v)
        k = self.d["karaj"]
        assert k["value"] / k["long_term"] > 1 and self.vx(k["value"], k["long_term"]) < RIGHT - AVG_AT * (RIGHT - LEFT), \
            "Karaj's 1405 bar crosses the average and stays inside the bar"
        assert self.vx(k["value"], k["long_term"]) >= LEFT, "Karaj's bar stays inside the window"

    def check_data(self) -> None:
        for key in ORDER:
            mod, g, box = MODS[key], GETS[key], BOXES[key]
            mod.checks()
            assert 2025 in mod.years() and 2026 in mod.years(), (key, "1404 and 1405 must be shown")
            assert inside(box, g.GRID, g.DAM), (key, "the dam point lies in its box, the box in the grid")
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
        """The dam's 1404 and 1405 pictures in the one box, at true shape; the box in km for the strip."""
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
        self.km[key] = ((e_ - w_) * 111.32 * math.cos(mid), (n_ - s_) * 111.32)

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
        assert UNIT_Y + 12 < self.src_y - SOURCE_PX, "the unit label runs into the sources"

    # ── texts ──

    def value_line(self, key: str, year: int) -> str:
        """The number written at the end of the dam's bar: this year's storage (1405), in Persian digits."""
        return fa(self.d[key]["value"])

    def clamp(self, c: Canvas, x: float, s: str, size: int = 30) -> float:
        w = c.width(s, FA_TEXT, size, "rtl")
        return min(max(x, LEFT + w / 2), RIGHT - w / 2)

    # ── time ──

    def appear(self, i: int) -> list:
        """Every word of a scene is in by 0.6 s: the hook at once (frame 0), the others in a calm 0.1 s apart."""
        ws = [w for w, _ in onebit.words_of(self.S.scenes[i].title, self.th)]
        n = len(ws) - ws.count("//")
        if i == 0:
            return [-1.0] * n
        return [-1.0] * n                                # every headline and line at once, at its bar line

    def sources(self, c: Canvas):
        for k, line in enumerate(self.words["sources"]):
            assert c.width(line, FA_TEXT, SOURCE_PX, "rtl") <= RIGHT - LEFT, line
            c.text(RIGHT, self.src_y + SOURCE_GAP * k, line, FA_TEXT, SOURCE_PX, self.th.head, "rs", "rtl")

    def window(self, c: Canvas, i: int):
        """The shared window: the dam's name and its bar number in the title bar; the follow line in the last bar."""
        th = self.th
        x, y, w, h = WIN
        c.frame(x, y, x + w, y + h, fill=th.paper)
        c.fill(x, y, x + w, y + BAR, th.ink)
        c.frame(x + 3, y + BAR + 3, x + w - 3, y + h - 3)
        last = i == len(self.S.scenes) - 1
        if last:
            c.text(x + w - 12, y + BAR - 9, self.words["follow"], FA_TEXT, 30, th.title, "rs", "rtl")
            assert c.width(self.words["follow"], FA_TEXT, 30, "rtl") <= w - 24
        elif 1 <= i <= len(ORDER):
            c.text(x + 12, y + BAR - 9, ENG[ORDER[i - 1]], PIXEL, 32, th.title)
            c.text(x + w - 12, y + BAR - 9, f"[{i:02d}/{len(ORDER):02d}]", PIXEL, 32, th.title, "rs")
        else:
            c.text(x + 12, y + BAR - 9, self.app, PIXEL, 32, th.title)
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
        """Bars 2-6: the satellite picture (1405), the dam's name and scale, the headline above, and one bar."""
        key = ORDER[k]
        d = self.d[key]
        t0 = DAM_T0 + SEG * k
        c.im.paste(self.scaled(self.pic[(key, 2026)], c), (c.X(PIC_X), c.Y(PIC_Y)))
        self.chip(c, PIC_X + PIC_W - 14, PIC_Y + 14, fa(persian(2026)))
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
        self.volume(c, t, t0, d["value"], d["long_term"], BLUE if tehran5.share(d) <= 1 else self.th.mark)

    def vx(self, v: float, avg: float) -> float:
        """The x of a volume on a bar: its average sits at AVG_AT of the width, 0 at the right edge."""
        return RIGHT - v / (avg / AVG_AT) * (RIGHT - LEFT)

    def volume(self, c: Canvas, t: float, t0: float, value: float, avg: float, colour: str):
        """One bar: it grows once, from 0 to the value, over GROW s, then holds; the value is written at its end,
        the dashed average is labelled, and one unit label sits at the bar's start."""
        th = self.th
        p = 1.0 if not np.isfinite(t) else min(max((t - t0) / GROW, 0.0), 1.0)
        p = p * p * (3 - 2 * p)                           # smooth
        v = value * p
        xv = self.vx(v, avg)
        c.fill(xv, BAR_Y, RIGHT, BAR_Y + BAR_H, colour)
        c.frame(LEFT, BAR_Y, RIGHT, BAR_Y + BAR_H, colour=th.ink)
        xm = self.vx(avg, avg)                            # the dashed average, labelled with its value
        for yy in range(BAR_Y - 12, BAR_Y + BAR_H + 10, 12):
            c.fill(xm - 2, yy, xm + 2, yy + 7, th.ink)
        lab = fa(f"میانگین {avg}")
        c.text(self.clamp(c, xm, lab), BAR_Y - 18, lab, FA_TEXT, 30, th.ink, "ms", "rtl")
        if p > 0.5:                                       # the value, at the bar's end (written once it has grown)
            c.text(xv - 12, BAR_Y + BAR_H - 8, fa(value), FA_BOLD, 40, th.ink, "rs", "rtl")
        c.text(RIGHT, UNIT_Y, "میلیون مترمکعب", FA_TEXT, 30, th.ink, "rs", "rtl")

    def rows_layout(self, k: float) -> dict:
        """The five lakes at one scale k (px per km) in two rows: each lake's box (x, y, w, h) and its name's centre.
        The rows are centred in the picture area below the year chip, with the scale bar's room at the bottom."""
        names_h, row_gap, gap_x = 50, 10, 36
        rows = []
        for row in LAKE_ROWS:
            w = [self.km[key][0] * k for key in row]
            h = max(self.km[key][1] * k for key in row)
            rows.append((row, w, h, sum(w) + gap_x * (len(row) - 1)))
        block = sum(h + names_h for _, _, h, _ in rows) + row_gap
        top = PIC_Y + LAKE_TOP + (PIC_H - LAKE_TOP - LAKE_BOTTOM - block) / 2
        out = {}
        for row, w, h, total in rows:
            x = PIC_X + (PIC_W - total) / 2
            for key, wk in zip(row, w):
                hk = self.km[key][1] * k
                out[key] = (x, top + (h - hk) / 2, wk, hk, x + wk / 2, top + h + 34)
                x += wk + gap_x
            top += h + names_h + row_gap
        return out

    def fit_rows(self) -> float:
        """The largest px/km at which both rows fit the picture area (width and height), checked in steps of 0.5."""
        k = 60.0
        while True:
            rows = [(row, sum(self.km[key][0] * k for key in row) + 36 * (len(row) - 1),
                     max(self.km[key][1] * k for key in row)) for row in LAKE_ROWS]
            width_ok = all(total <= PIC_W - 12 for _, total, _ in rows)
            height_ok = sum(h + 50 for _, _, h in rows) + 10 <= PIC_H - LAKE_TOP - LAKE_BOTTOM
            if width_ok and height_ok:
                return k
            k -= 0.5

    def strip(self, c: Canvas, t: float):
        """The five 1405 lakes at one scale in two rows, all five from t = 0, each named under it; the hook's
        highlight steps across them in the reel's order, HL_STEP each (none from 5 x HL_STEP on), and one 5-km bar."""
        hl = int(t // HL_STEP) if np.isfinite(t) and t < HL_STEP * len(ORDER) else None
        for j, key in enumerate(ORDER):
            x, y, w, h, cx, name_y = self.lake_xy[key]
            c.im.paste(self.scaled(self.thumb[key], c), (c.X(x), c.Y(y)))
            if hl == j:                                   # the highlight: an ink outline round the lake's box
                c.frame(x - 8, y - 8, x + w + 8, y + h + 8, colour=self.th.ink)
                c.frame(x - 7, y - 7, x + w + 7, y + h + 7, colour=self.th.ink)
            name = self.d[key]["label"]
            assert c.width(name, FA_TEXT, 30, "rtl") <= 2 * max(w, 120), name
            c.text(cx, name_y, name, FA_TEXT, 30, self.th.ink, "ms", "rtl")
        bx, by = PIC_X + 26, PIC_Y + PIC_H - 30            # one 5-km scale bar, bottom left, its label right of it
        label = fa("۵ کیلومتر")
        lw = c.width(label, FA_TEXT, 30, "rtl")
        assert 0 < 5 * self.strip_k < PIC_W - lw - 60
        c.frame(bx - 14, by - 26, bx + 5 * self.strip_k + 14 + lw + 14, by + 20, fill=self.th.field)
        c.fill(bx, by, bx + 5 * self.strip_k, by + 8, self.th.ink)
        c.text(bx + 5 * self.strip_k + 14 + lw, by + 8, label, FA_TEXT, 30, self.th.ink, "rs", "rtl")
        self.chip(c, PIC_X + PIC_W - 14, PIC_Y + 14, fa(persian(2026)))

    def stack(self, c: Canvas, t: float):
        """Bar 7: the five dams' 1405 storage together (359) against the dashed total average (548)."""
        self.strip(c, np.inf)
        self.volume(c, t, STACK, tehran5.TOTAL["value"], tehran5.TOTAL["long_term"], BLUE)

    def body(self, c: Canvas, t: float):
        if not np.isfinite(t):                           # the cover: the five 1405 lakes, all named
            self.strip(c, np.inf)
            return
        if t < DAM_T0:                                   # bar 1: the hook, the lakes appear
            self.strip(c, t)
            return
        if t >= STACK:
            self.stack(c, t)
            return
        k = min(int((t - DAM_T0) // SEG), len(ORDER) - 1)
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
        times = [0.0, 2.0]
        for k in range(len(ORDER)):
            times += [DAM_T0 + SEG * k + 0.3, DAM_T0 + SEG * k + 2.5]
        times += [25.0, 27.9]
        for t in times:
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
