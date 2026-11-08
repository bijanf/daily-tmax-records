"""HAMOUN, VERSION 2: «هامون هر بهار چقدر آب داشت؟» Forty springs of the Hamoun lakes, 1366-1405 (1987-2026), as
one big bar chart against their own mean, in the frame of the slide reels (onebit_slides: the frame of the five-dam
reel, 47,500 views without narration). The user's direction (8 Nov 2026): the chart big, no comparison with Tehran,
a line for the lakes' mean, the springs one by one; a light background, no narration.

Every number comes from data/hamoun/reel/timeline.json (src/hamounreel.py, fact-checked for the first Hamoun reel):
the late-spring open water of the whole Hamoun (both sides of the border) in km2, one value a spring, 1381 without a
trusted number. The mean is the mean of the 39 measured springs, computed and asserted here; so are the counts on
screen: 12 of 12 springs of 1367-1378 above it, 5 of the 26 measured springs of 1379-1405 above it, 10 springs under
100 km2 (all from 1379 on), 1405 about a third of it. The picture inset is each spring's Landsat picture (the first
reel's, data/hamoun/reel/tex_<year>.jpg) with its measured water outlined; a spring without a clean picture keeps its
number, its picture is the last clean one, grey, with a note.

Five scenes, 1 + 1.1 + 2.5 + 1.5 + 1.4 bars of 60 BPM = 30 s, a light setar score (onebit_score_hamoun2_light.py):
    0-4 s        the hook, whole in frame 0 with 1405; 1.0-2.2 s the bars go, newest first; from 2.4 s 1366 on
    4-8.4 s      1367-1378 (0.45 s a spring)
    8.4-18.4 s   1379-1405 (0.36 s a spring); the eras bracketed once 1405 is in
    18.4-24.4 s  the chart alone: the ten near-dry springs ringed
    24.4-30 s    1405 against the mean; the end is frame 0 again (a loop)

    python -I src/onebit_hamoun2.py --stills
    python -I src/onebit_hamoun2.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageOps  # noqa: E402

import onebit  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, SIZES, SOCIAL_CRF, Canvas, fa  # noqa: E402
from onebit_slides import LEFT, RIGHT, Slides  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data" / "hamoun" / "reel"
THEME = "kahgel"
WET, DRY, GAPC = "#1c5cab", "#B5763A", "#9A8F80"     # above the mean, below it, no number
PACE = dict(bpm=60, bars=(1, 1.1, 2.5, 1.5, 2, 2, 1.4))
DURATION = 46.0
REWIND = (1.0, 2.2)                                  # s: the bars go, newest first
T0, STEP1 = 2.4, 0.45                                # 1366 at 2.4 s; 1366-1378 every 0.45 s
T13, STEP2 = 8.4, 0.36                               # 1379 at 8.4 s; 1379-1405 every 0.36 s
GROW = 0.25                                          # s: a bar grows from 0 to its value
T_ERAS, T_DRY, T_WHY, T_WHERE, T_NOW = 18.0, 18.4, 24.4, 32.4, 40.4   # s: brackets, rings, why, where, 1405
NEAR_DRY = 100.0                                     # km2: «تقریباً بی‌آب»
# the layout, inside the window of onebit_slides
FIELD = (LEFT, 740, RIGHT, 1400)                     # x0, y top (the largest spring), x1, y base
INSET = (LEFT, 600, 380)                             # x, y, side: the spring's picture, over the low recent bars
PIC_SQ = (150, 175, 810, 835)                        # the square of the picture grid (px) that holds the lakes
VALUE_Y, RATIO_Y = 668, 716                          # the value line and its ratio line (right-aligned)
AXIS_Y, LEGEND_Y = 1442, 1500
CHIP_H = 72


def words() -> dict:
    return dict(
        scenes=(("هامون هر بهار // {چقدر آب} داشت؟", ""),
                ("۱۳۶۷ تا ۱۳۷۸: // هر ۱۲ بهار {بالای میانگین}", ""),
                ("از ۱۳۷۹: // فقط ۵ بار {بالای میانگین}", ""),
                ("و {۱۰ بهار} // تقریباً بی‌آب", ""),
                ("چرا؟ بارش {کمی} کم شد؛ // آبِ هامون {خیلی بیشتر}", "با بارشِ مشابه، آبِ کمتری به هامون رسید"),
                ("آب کجا رفت؟ // سدها و آبیاری، {در دو سوی مرز}", "خشکسالی شروع کرد؛ برداشتِ آب ادامه داد"),
                ("امسال: حدودِ {یک‌سومِ} میانگین", "شما هامونِ پُر را دیده‌اید؟")),
        follow="این را برای کسی بفرستید که هامون را می‌شناسد",
        unit="کیلومترمربع", held="تصویرِ صافی از این بهار نیست؛", held2="عدد از همین بهار است",
        gap="عددِ مطمئنی نیست", gap_pic="تصویرِ صافی و عددِ مطمئنی", gap_pic2="از این بهار نیست", legend=("بالای میانگین", "زیرِ میانگین"), mean="میانگینِ ۳۹ بهار",
        eras=("۱۲ از ۱۲ بالای میانگین", "۵ از ۲۶ بالای میانگین"), dry="تقریباً بی‌آب",
        rain_item="بارشِ زمستان (مهر تا فروردین)، کوه‌های بالادست", lake_item="آبِ هامون، اواخرِ بهار",
        before="۱۳۶۶ تا ۱۳۷۸", after="۱۳۷۹ تا ۱۴۰۴", wet="در زمستان‌های پرباران هم: حدودِ ۴۰٪ قبل",
        two="دو داده‌ی بارش: CRU و ERA5",
        # scene 6, fact-checked 8 Nov 2026 (Whitney 2006 USGS SIR 2006-5182; the 1973 treaty; Akbari et al. 2022 JGLR;
        # Modaresi Rad et al. 2022 STOTEN; Anadolu Agency 24 Mar 2021): (when, where, what)
        rows=(("۱۳۳۲", "افغانستان", "سدِ کجکی روی هیرمند"),
              ("۱۳۵۱", "ایران و افغانستان", "سهمِ ایران از هیرمند: حدودِ ۸۲۰ میلیون مترمکعب در سال"),
              ("۱۳۶۲", "ایران", "مخازنِ چاه‌نیمه در سیستان؛ چهارمی در ۱۳۸۷"),
              ("۱۳۶۹ تا ۱۳۹۰", "افغانستان", "زمینِ آبی بینِ سدِ کجکی و مرز: ۶۲٪ بیشتر"),
              ("۱۴۰۰", "افغانستان", "سدِ کمال‌خان روی هیرمند")),
        study=("پژوهش (Modaresi Rad و همکاران، ۲۰۲۲):", "بدونِ برداشتِ رو به افزایشِ آب در حوضه،",
               "هامون در ۲۰۱۰ تا ۲۰۱۹ حدودِ ۲٫۵ برابر بزرگ‌تر می‌بود"),
        sources=("منبع: لندست ۴، ۵، ۷، ۸ و ۹ (USGS)؛ آبِ باز در اواخرِ بهار، کلِ هامون",
                 "سنجیده با JRC؛ بارش: CRU TS 4.10 و ERA5؛ ۱۳۸۱ بی‌عدد"),
    )


def shown(v: float) -> str:
    """To the nearest 10 from 100 km2 (the first reel's rule), half up, with «٬»."""
    n = int(np.floor(v / 10 + 0.5)) * 10 if v >= 100 else int(np.floor(v + 0.5))
    return fa(f"{n:,}").replace(",", "٬")


def dec(x: float) -> str:
    return fa(f"{x:.1f}").replace(".", "٫")


def bars_above(k: int) -> bool:
    """Is spring k (0 = 1366) above the mean of the measured springs? (for the score's notes)"""
    bars = json.loads((DATA / "timeline.json").read_text())["bars"]
    v = np.array([b["km2"] if b["km2"] is not None else np.nan for b in bars], float)
    return bool(v[k] > np.nanmean(v))


def ease(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def spring_t(k: int) -> float:
    """When spring k (0 = 1366) comes in."""
    return T0 + STEP1 * k if k <= 12 else T13 + STEP2 * (k - 13)


class Hamoun2(Slides):
    def __init__(self, th: onebit.Theme, colour: dict):
        tl = json.loads((DATA / "timeline.json").read_text())
        self.bars = tl["bars"]
        assert len(self.bars) == 40 and self.bars[0]["year"] == 1987 and self.bars[-1]["year"] == 2026
        self.pics = set(tl["pictures"])
        self.T = tl["pic_transform"]
        self.outlines = json.loads((DATA / "outlines.json").read_text())
        v = np.array([b["km2"] if b["km2"] is not None else np.nan for b in self.bars], float)
        self.v = v
        self.mean = float(np.nanmean(v))
        self.vmax = float(np.nanmax(v))
        yrs = np.array([b["year"] for b in self.bars])
        assert np.isfinite(v).sum() == 39 and [b["year"] for b in self.bars if b["km2"] is None] == [2002]
        assert 1560 < self.mean < 1570, self.mean
        era1 = (yrs >= 1988) & (yrs <= 1999)
        era2 = (yrs >= 2000) & np.isfinite(v)
        assert era1.sum() == 12 and (v[era1] > self.mean).all()
        assert era2.sum() == 26 and int((v[era2] > self.mean).sum()) == 5
        assert int((v < NEAR_DRY).sum()) == 10 and all(yrs[v < NEAR_DRY] >= 2000)
        assert 0.33 <= v[-1] / self.mean <= 0.38, v[-1] / self.mean          # «حدودِ یک‌سومِ میانگین»
        assert spring_t(12) < 8.4 <= spring_t(13) and spring_t(39) < T_ERAS
        rain = json.loads((DATA.parent / "reel2" / "rain.json").read_text())   # src/hamoun_rain.py
        self.rain = rain
        assert (rain["n_early"], rain["n_late"]) == (13, 25) and 0.25 <= rain["lake_share"] <= 0.27
        assert 0.91 <= rain["cru"]["rain_share"] <= 0.93 and 0.76 <= rain["era5"]["rain_share"] <= 0.78
        assert all(0.35 <= rain[k]["wet_share"] <= 0.45 for k in ("cru", "era5"))
        self.hook_at_once = True
        self.setup(th, "fa", colour, words(), PACE, "Hamoun.Lakes")
        assert abs(self.starts[-1] - DURATION) < 1e-9 and np.allclose(self.starts[:-1], (0, 4, 8.4, 18.4, 24.4, 32.4, 40.4))
        self.done = 0.6
        self.cache = {}
        x, y, side = INSET                                 # the inset sits over the low recent bars
        under = [k for k in range(40) if self.slot(k)[0] < x + side and np.isfinite(v[k])]
        assert all(self.ybar(v[k]) > y + side + 12 for k in under), "a bar runs into the picture"

    # ── geometry ──
    def slot(self, k: int) -> tuple:
        """(x left, x right) of bar k: the springs run right to left (1366 at the right, 1405 at the left)."""
        x0, _, x1, _ = FIELD
        s = (x1 - x0) / 40
        xr = x1 - k * s
        return xr - s * 0.84, xr - s * 0.16

    def ybar(self, v: float) -> float:
        _, yt, _, yb = FIELD
        return yb - (yb - yt) * v / self.vmax

    # ── the clock ──
    def state(self, t: float):
        """(the spring on screen, bars shown up to, growth of the last, all bars at once 0-1)."""
        if not np.isfinite(t) or t < REWIND[0] or t >= T_NOW:
            return 39, 39, 1.0, 1.0
        if t < REWIND[1]:
            u = (t - REWIND[0]) / (REWIND[1] - REWIND[0])
            return 39, int(39 - 40 * u), 1.0, 0.0
        if t < T0:
            return 0, -1, 0.0, 0.0
        k = max(i for i in range(40) if spring_t(i) <= t)
        return k, k, ease((t - spring_t(k)) / GROW), 0.0

    # ── drawing ──
    def to_inset(self, lon: float, lat: float) -> tuple:
        a, _, c, _, e, f = self.T
        x0, y0, x1, y1 = PIC_SQ
        side = INSET[2]
        px, py = (lon - c) / a, (lat - f) / e
        return (px - x0) * side / (x1 - x0), (py - y0) * side / (y1 - y0)

    def picture(self, year: int) -> Image.Image:
        if year in self.cache:
            return self.cache[year]
        held = year not in self.pics
        src = year if not held else max(y for y in self.pics if y < year)
        side = INSET[2]
        im = Image.open(DATA / f"tex_{src}.jpg").convert("RGB").crop(PIC_SQ).resize((side, side), Image.LANCZOS)
        if held:
            im = Image.blend(im, ImageOps.grayscale(im).convert("RGB"), 0.9)
        else:
            d = ImageDraw.Draw(im)
            for line in self.outlines.get(str(year), []):
                pts = [self.to_inset(lo, la) for lo, la in line]
                if len(pts) > 2:
                    d.line(pts + [pts[0]], fill=WET, width=2)
        self.cache[year] = im
        return im

    def scaled(self, im: Image.Image, c: Canvas) -> Image.Image:
        return im if c.k == 1 else im.resize((round(im.width * c.k), round(im.height * c.k)), Image.LANCZOS)

    def inset(self, c: Canvas, k: int):
        th = self.th
        x, y, side = INSET
        year = self.bars[k]["year"]
        c.im.paste(self.scaled(self.picture(year), c), (c.X(x), c.Y(y)))
        c.frame(x, y, x + side, y + side)
        s = fa(self.bars[k]["label"])
        w = c.width(s, FA_BOLD, 48, "rtl")
        c.frame(x + side - 14 - w - 28, y + 14, x + side - 14, y + 14 + CHIP_H, fill=th.field)
        c.text(x + side - 28, y + 14 + 53, s, FA_BOLD, 48, th.ink, "rs", "rtl")
        if year not in self.pics:                          # no clean picture (1381: no number either)
            one, two = (("held", "held2") if self.bars[k]["km2"] is not None else ("gap_pic", "gap_pic2"))
            c.frame(x + 10, y + side - 84, x + side - 10, y + side - 10, fill=th.field)
            c.text(x + side - 22, y + side - 52, self.words[one], FA_TEXT, 24, th.ink, "rs", "rtl")
            c.text(x + side - 22, y + side - 22, self.words[two], FA_TEXT, 24, th.ink, "rs", "rtl")

    def value(self, c: Canvas, k: int):
        th = self.th
        b = self.bars[k]
        if b["km2"] is None:
            c.text(RIGHT, VALUE_Y, self.words["gap"], FA_BOLD, 48, th.ink, "rs", "rtl")
            return
        v = b["km2"]
        c.text(RIGHT, VALUE_Y, f"{shown(v)} {self.words['unit']}", FA_BOLD, 52, th.ink, "rs", "rtl")
        r = v / self.mean
        line = (self.words["dry"] if v < NEAR_DRY else f"{dec(r)} برابرِ میانگین" if r >= 1.15
                else "نزدیکِ میانگین" if r >= 0.85 else f"{fa(round(100 * r))}٪ میانگین")
        c.text(RIGHT, RATIO_Y, line, FA_BOLD, 34, th.mark, "rs", "rtl")

    def chart(self, c: Canvas, t: float, cur: int, upto: int, grow: float, all_: float):
        th = self.th
        x0, _, x1, yb = FIELD
        for k, b in enumerate(self.bars):
            xa, xb = self.slot(k)
            if b["km2"] is None:
                if k <= upto or all_ > 0:                  # no number: a dashed outline to the axis
                    top = self.ybar(self.mean * 0.2)
                    for yy in np.arange(top, yb - 4, 10):
                        c.fill(xa, yy, xa + 2, yy + 5, GAPC)
                        c.fill(xb - 2, yy, xb, yy + 5, GAPC)
                continue
            f = 1.0 if (all_ > 0 or k < upto) else grow if k == upto else 0.0
            if f <= 0:
                continue
            top = min(self.ybar(b["km2"] * f), yb - 3)
            c.fill(xa, top, xb, yb, WET if b["km2"] > self.mean else DRY)
            if k == cur and np.isfinite(t) and REWIND[1] <= t < T_ERAS:
                c.frame(xa - 3, top - 3, xb + 3, yb, colour=th.ink)
        c.fill(x0, yb, x1, yb + 2, th.ink)                 # the axis
        ym = self.ybar(self.mean)                          # the mean: a dashed line
        for xx in np.arange(x0, x1, 16):
            c.fill(xx, ym - 1.5, min(xx + 9, x1), ym + 1.5, th.ink)
        for k in (0, 10, 20, 30, 39):                      # the years under the axis
            xa, xb = self.slot(k)
            c.text((xa + xb) / 2, AXIS_Y, fa(self.bars[k]["label"]), FA_TEXT, 28, th.ink, "ms", "rtl")

    def legend(self, c: Canvas):
        th = self.th
        x = RIGHT
        for s, col in zip(self.words["legend"], (WET, DRY)):
            c.fill(x - 26, LEGEND_Y - 22, x, LEGEND_Y - 2, col)
            c.text(x - 36, LEGEND_Y, s, FA_TEXT, 28, th.ink, "rs", "rtl")
            x -= 36 + c.width(s, FA_TEXT, 28, "rtl") + 34
        for xx in range(int(x - 34), int(x), 12):          # the mean's swatch: dashed
            c.fill(xx, LEGEND_Y - 13, xx + 7, LEGEND_Y - 10, th.ink)
        s = f"{self.words['mean']}: {shown(self.mean)}"
        c.text(x - 44, LEGEND_Y, s, FA_TEXT, 28, th.ink, "rs", "rtl")
        assert x - 44 - c.width(s, FA_TEXT, 28, "rtl") >= LEFT, "the legend runs out of the window"

    def eras(self, c: Canvas, t: float):
        th = self.th
        if not (np.isfinite(t) and T_ERAS <= t < T_WHY):
            return
        _, yt, _, _ = FIELD
        later = self.v[13:][np.isfinite(self.v[13:])].max()
        for (k0, k1), s in zip(((1, 12), (13, 39)), self.words["eras"]):
            xa, _ = self.slot(k1)
            _, xb = self.slot(k0)
            y = yt - 26 if k0 == 1 else self.ybar(later) - 60
            c.fill(xa, y, xb, y + 3, th.ink)
            c.fill(xa, y, xa + 3, y + 16, th.ink)
            c.fill(xb - 3, y, xb, y + 16, th.ink)
            c.text((xa + xb) / 2, y - 12, s, FA_BOLD, 32, th.mark, "ms", "rtl")

    def rings(self, c: Canvas, t: float):
        th = self.th
        if not (np.isfinite(t) and T_DRY <= t < T_WHY):
            return
        yb = FIELD[3]
        for k, b in enumerate(self.bars):
            if b["km2"] is not None and b["km2"] < NEAR_DRY:
                xa, xb = self.slot(k)
                cx, cy = (xa + xb) / 2, yb - 22
                k_ = c.k
                ImageDraw.Draw(c.im).ellipse([c.X(cx - 14), c.Y(cy - 14), c.X(cx + 14), c.Y(cy + 14)],
                                             outline=th.mark, width=max(1, round(3 * k_)))

    def why(self, c: Canvas):
        """Scene 5: the rain and the lake, the later period as a share of the earlier (100 %), as bars."""
        th, r = self.th, self.rain
        L = 500                                             # px for 100 %: room left of it for the label
        lo, hi = sorted((r["era5"]["rain_share"], r["cru"]["rain_share"]))
        items = ((self.words["rain_item"], (lo, hi), WET, f"{fa(round(100 * lo))} تا {fa(round(100 * hi))}٪"),
                 (self.words["lake_item"], (r["lake_share"],) * 2, DRY, f"{fa(round(100 * r['lake_share']))}٪"))
        y = 650
        for label, (a, b), col, val in items:
            c.text(RIGHT, y, label, FA_BOLD, 36, th.ink, "rs", "rtl")
            for k, (period, frac) in enumerate(((self.words["before"], 1.0), (self.words["after"], None))):
                yy = y + 30 + k * 86
                c.text(RIGHT, yy + 44, period, FA_TEXT, 28, th.ink, "rs", "rtl")
                x1 = RIGHT - 150
                if frac == 1.0:
                    c.fill(x1 - L, yy + 8, x1, yy + 58, "#CFC4B3")
                    c.text(x1 - L + 12, yy + 46, "۱۰۰٪", FA_BOLD, 32, th.ink, "ls", "rtl")
                else:
                    c.fill(x1 - L * a, yy + 8, x1, yy + 58, col)
                    if b > a:                               # the range of the two datasets: hatched
                        for xx in np.arange(x1 - L * b, x1 - L * a, 10):
                            c.fill(xx, yy + 8, xx + 5, yy + 58, col)
                    c.text(x1 - L * b - 14, yy + 46, val, FA_BOLD, 36, th.mark, "rs", "rtl")
                    assert x1 - L * b - 14 - c.width(val, FA_BOLD, 36, "rtl") >= LEFT, val
            y += 300
        c.text(RIGHT, y + 10, self.words["wet"], FA_BOLD, 34, th.mark, "rs", "rtl")
        c.text(RIGHT, y + 64, self.words["two"], FA_TEXT, 28, th.ink, "rs", "rtl")

    def where(self, c: Canvas):
        """Scene 6: where the water went: the dams, the treaty, the reservoirs and the irrigation on both sides of
        the border, in time order, and the one study that puts a number on the human share."""
        th = self.th
        y = 640
        for when, side, what in self.words["rows"]:
            c.text(RIGHT, y, when, FA_BOLD, 40, th.mark, "rs", "rtl")
            w = c.width(when, FA_BOLD, 40, "rtl")
            c.text(RIGHT - w - 22, y, f"· {side}", FA_TEXT, 30, th.ink, "rs", "rtl")
            c.text(RIGHT, y + 46, what, FA_TEXT, 32, th.ink, "rs", "rtl")
            assert c.width(what, FA_TEXT, 32, "rtl") <= RIGHT - LEFT, what
            y += 112
        y0 = y + 6
        c.frame(LEFT, y0, RIGHT, y0 + 178, fill=th.field)
        for k, line in enumerate(self.words["study"]):
            c.text(RIGHT - 20, y0 + 52 + 52 * k, line, FA_BOLD if k == 2 else FA_TEXT, 32 if k else 28,
                   th.mark if k == 2 else th.ink, "rs", "rtl")
            assert c.width(line, FA_TEXT, 32, "rtl") <= RIGHT - LEFT - 40, line
        assert y0 + 178 < 1530, "the study box runs out of the window"

    def body(self, c: Canvas, t: float):
        if np.isfinite(t) and T_WHY <= t < T_WHERE:
            self.why(c)
            return
        if np.isfinite(t) and T_WHERE <= t < T_NOW:
            self.where(c)
            return
        cur, upto, grow, all_ = self.state(t)
        alone = np.isfinite(t) and T_DRY <= t < T_WHY       # scene 4: the chart alone
        self.chart(c, t, cur, upto, grow, all_)
        self.eras(c, t)
        self.rings(c, t)
        if not alone and (not np.isfinite(t) or t < REWIND[1] or t >= T0):
            self.inset(c, cur)
            self.value(c, cur)
        self.legend(c)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true")
    args = ap.parse_args()
    film = Hamoun2(onebit.THEMES[THEME], {"land": "#E2D8C8"})
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / "hamoun2_fa"
    for old in (OUT / "social").glob(f"{base.name}_t*.png"):
        old.unlink()
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    if args.stills:
        for t in (0.0, 1.6, 9.0, 19.5, 27.5, 30.0, 35.0, 42.0, 45.9):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png", flush=True)
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
