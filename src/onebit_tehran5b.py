"""THE TEHRAN DAMS, FOLLOW-UP (tehran5b_fa, 25 s): the newest official figures, in the look of the five-dam reel
(theme kahgel, the cream window, the title bar "Tehran.Dams" with its counter [k/3]).

Five bars of 60 BPM: S1 0-4 s the hook (the five 1405 lakes, as the viral reel's hook; whole at frame 0, which is the
cover); S2 [1/3] 4-9.5 s the share of the five dams' capacity (one bar to 340 of 1,930 million m3, the band of 800-850
that the stable state needs); S3 [2/3] 9.5-15 s the water year's start (450), 1 Aban (359) and 16 Aban (340), three
bars on one scale, the earliest on the right (Persian time runs right to left); S4 [3/3] 15-20 s the rain of Tehran to
mid-Aban (16 mm against the expected 38.9), one bar and one dashed mark; S5 20-25 s the answer and the question.

The figures and their sources: src/tehran5b.py (asserted there). The five lakes: the pictures and the box of each dam
are onebit_tehran5's (the Landsat autumn passes of 1405, read from src/tehran5.py's modules). The window, the
headlines, the bars and the drops-free layout follow onebit_elnino26s.py and onebit_slides.py (imported).

    outputs/onebit/social/tehran5b_fa_reel.mp4 (silent master), tehran5b_fa_cover.png (frame 0), _t<sec>.png (stills)

    python -I src/onebit_tehran5b.py              # the silent reel and the cover
    python -I src/onebit_tehran5b.py --stills     # the cover and the stills of the iterations
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import onebit  # noqa: E402
import onebit_tehran5 as t5  # noqa: E402  (the five lakes: pictures, boxes, photo(), the hook's highlight: imported)
import tehran5  # noqa: E402
import tehran5b  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, PIXEL, SIZES, SOCIAL_CRF, Canvas, fa, title  # noqa: E402
from onebit_slides import COLOURS, LEFT, RIGHT, WIN, Slides  # noqa: E402

BASE = "tehran5b_fa"
PACE = dict(bpm=60, bars=(1.0, 1.375, 1.375, 1.25, 1.25))      # 4, 5.5, 5.5, 5, 5 s: 25 s
STARTS = (0.0, 4.0, 9.5, 15.0, 20.0, 25.0)                     # s: the scenes (the film's clock)
END = 25.0
ORDER = t5.ORDER                                               # worst to best against the average (the five-dam reel)
ENG = "Tehran.Dams"
BAR = 40                                                       # px: the window's title bar (Slides)
HEAD_Y = WIN[1] + BAR + 96                                     # px: the first baseline of the headline (332)
RULE_Y = 650                                                   # px: the rule under the key lines
KEY_Y = 520                                                    # px: the first baseline of a key line (two lines fit)
KEY_GAP = 60                                                   # px: between the key lines and their wrapped lines (48 px type)
HEAD = ((68, 92), (64, 86))                                    # the headline: full size, and the smaller fallback
SMALL = 48                                                     # px: key lines and labels (floor 48)
UNIT = 48                                                      # px: ticks, units and the scale (floor 48)
SOURCE = 40                                                    # px: the sources line (the 40-px floor, so it clears the border)
SOURCE_Y = 1590                                                # px: the sources' baseline, clear of the window border (1552)
STRIP_TOP, STRIP_BOTTOM = 668, 1210                            # px: the five lakes' area in S2 (its foot: the scale bar)
STRIP_BOTTOM_HOOK = 1450                                       # px: the hook's lakes take the empty cream below them
STRIP_FOOT = 64                                                # px: the lakes stop this far above the foot
PIC_X, PIC_W = WIN[0] + 3, WIN[2] - 6
NAMES_H, ROW_GAP, GAP_X = 64, 12, 36                           # px: a name under its lake, the rows, the lakes
HL_STEP = 0.6                                                  # s: the hook's highlight steps across the five lakes
GROW = 1.0                                                     # s: a bar grows once, then holds
BLUE = "#1c5cab"                                               # kahgel's water (as the five-dam reel)
BAR_Y, BAR_H = 1300, 44                                        # px: the storage bar (S2), the rain bar (S4) at 900
RAIN_Y, RAIN_H = 880, 80
AVG_AT = 0.70                                                  # the average (or the expected) sits at 70 % of the width
COL_BASE = 1240                                                # px: the baseline of the three columns (S3)
COL_K = 520 / 450                                              # px per million m3 for S3 (450 is 520 px tall)
COL_W = 200                                                    # px: a column's width
COL_X = (RIGHT - 100, (LEFT + RIGHT) / 2, LEFT + 100)          # the columns' centres: the earliest on the right
BAND = (tehran5b.NEED[0], tehran5b.NEED[1])                    # million m3: the stable state's band (800-850)
RAIN_TOP = tehran5b.DIDBAN["rain_expected"] / AVG_AT           # the scale's end for the rain bar
BAND_MIN = 40                                                  # px: the stable state's band is drawn at least this wide
LABEL = {"karaj": "سدِ امیرکبیر"}                               # the name under a lake (Karaj is the Amir Kabir dam)


def words() -> dict:
    """The five scenes (bold line, key line; S5's lines are drawn in body()), the follow line, the sources."""
    return dict(
        scenes=(("با این باران‌ها، // سدهای تهران پر می‌شوند؟", "تازه‌ترین آمارِ رسمی: ۱۶ آبان ۱۴۰۵"),
                ("پنج سد: {۱۸٪} پر", "حدودِ ۳۴۰ از جمعِ ظرفیتِ ۱٬۹۳۰ (حسابِ ما)"),
                ("آغازِ سالِ آبی: {۴۵۰}", "حالا حدودِ ۳۴۰؛ هنوز کم می‌شود"),
                ("بارانِ تهران: {۱۶} از ۳۸٫۹ میلی‌متر", "تا نیمه‌ی آبان؛ کمتر از نصفِ معمول"),
                ("چند روز باران پرشان نمی‌کند", "")),
        follow="این را برای کسی بفرستید که در تهران زندگی می‌کند",
        sources="دیدبان ایران · آبفا · مهر · لندست",
        s5_small=("بارانِ همین روزها هنوز در آمارِ رسمی نیست",),
        question="برفِ البرز // به میانگین می‌رسد؟",
        question_ref="میانگینِ بلندمدت",
        bar_end="جمعِ ظرفیت (حسابِ ما): ۱٬۹۳۰",
        unit="میلیون مترمکعب",
        columns=(("آغازِ سالِ", "آبی"), ("۱ آبان", ""), ("۱۶ آبان", "")),
        rain_mark="معمول ۳۸٫۹",
        rain_unit="میلی‌متر",
    )


def fa_dec(x: float) -> str:
    """A decimal as Persian digits with «٫»."""
    return fa(f"{x:.1f}").replace(".", "٫")


def smooth(p: float) -> float:
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


class Tehran5bFilm(Slides):
    photo = t5.Tehran5Film.photo                            # the lakes' pictures: onebit_tehran5's, unchanged

    def __init__(self, th: onebit.Theme, colour: dict):
        tehran5b.check()
        self.d = {d["key"]: d for d in tehran5.DAMS}
        t5.Tehran5Film.check_data(self)                     # the five dams' data checks (the five-dam reel's)
        self.check_layout_numbers()
        self.words = words()
        self.setup(th, "fa", colour, self.words, PACE, ENG)
        self.hook_at_once = True
        self.th = th
        self.km = {}
        for key in ORDER:                                   # the box of each lake in km (its true shape)
            w, s, e, n = t5.BOXES[key]
            mid = math.radians((s + n) / 2)
            self.km[key] = ((e - w) * 111.32 * math.cos(mid), (n - s) * 111.32)
        probe = Canvas(1, th, 1.0, (0.0, 0.0), SIZES["reel"])
        self.name_w = {key: probe.width(self.label(key), FA_TEXT, SMALL, "rtl") for key in ORDER}
        self.geo_hook = self.make_geo(STRIP_BOTTOM_HOOK)          # S1: the lakes take the cream below them
        self.geo_small = self.make_geo(STRIP_BOTTOM)              # S2: the lakes above the storage bar
        self.check_words()

    def label(self, key: str) -> str:
        return LABEL.get(key, self.d[key]["label"])

    def make_geo(self, bottom: float) -> dict:
        """The pictures of the five lakes at the largest scale that fits the area ending at bottom."""
        k = self.fit_rows(bottom)
        thumbs = {}
        for key in ORDER:
            w_km, h_km = self.km[key]
            thumbs[key] = self.photo(key, 2026, t5.BOXES[key], round(w_km * k), round(h_km * k), self.th)
        return dict(k=k, thumbs=thumbs, xy=self.rows_layout(k, bottom), bottom=bottom)

    # ── checks: every number on screen is asserted here ──

    def check_layout_numbers(self) -> None:
        """The five dams' storage on screen: 1405 and the average, as the five-dam reel had them."""
        assert sum(d["value"] for d in tehran5.DAMS) == tehran5.TOTAL["value"] == 359

    def check_words(self) -> None:
        sc = self.words["scenes"]
        assert len(sc) == 5 and len(PACE["bars"]) == 5
        assert sc[0][0] == "با این باران‌ها، // سدهای تهران پر می‌شوند؟"
        assert sc[1][0] == f"پنج سد: {{{fa(18)}٪}} پر"
        assert sc[2][0] == f"آغازِ سالِ آبی: {{{fa(450)}}}"
        assert sc[1][1] == f"حدودِ {fa(340)} از جمعِ ظرفیتِ {fa_thousands(1930)} (حسابِ ما)"
        assert sc[3][0] == f"بارانِ تهران: {{{fa(16)}}} از {fa_dec(38.9)} میلی‌متر"
        assert fa_thousands(tehran5b.TOTAL_CAPACITY) == "۱٬۹۳۰"
        assert fa(tehran5b.DIDBAN["share_pct"]) == "۱۸"
        assert fa(tehran5b.DIDBAN["rain_now"]) == "۱۶"
        assert fa_dec(tehran5b.DIDBAN["rain_expected"]) == "۳۸٫۹"
        assert self.words["s5_small"] and all(self.words["s5_small"])
        assert "ذوب" not in " ".join(self.words["s5_small"]), "no snowmelt claim without a source"
        assert self.words["columns"][0] == ("آغازِ سالِ", "آبی")

    # ── pictures: the five lakes in two rows at one scale (the hook's, with the names at 48 px) ──

    def check(self, scenes):
        """The base class checks each scene's key line on one line; here the key lines are wrapped (key_lines)."""

    def scaled(self, im: Image.Image, c: Canvas) -> Image.Image:
        return im if c.k == 1 else im.resize((round(im.width * c.k), round(im.height * c.k)), Image.LANCZOS)

    def slot(self, key: str, k: float) -> float:
        """The width (px) a lake takes in its row: its box at k px per km, or its name with a gap, if wider."""
        return max(self.km[key][0] * k, self.name_w[key] + 24)

    def fit_rows(self, bottom: float = STRIP_BOTTOM) -> float:
        """The largest px/km at which both rows fit the lakes' area: each row's width (a lake's slot is its box or its
        name, whichever is wider), and the height of the two rows with a name under each (checked in steps of 0.5)."""
        k = 200.0
        while True:
            rows = [(row, sum(self.slot(key, k) for key in row) + GAP_X * (len(row) - 1),
                     max(self.km[key][1] * k for key in row)) for row in t5.LAKE_ROWS]
            width_ok = all(total <= PIC_W - 16 for _, total, _ in rows)
            height_ok = sum(h + NAMES_H for _, _, h in rows) + ROW_GAP <= bottom - STRIP_TOP - STRIP_FOOT
            if width_ok and height_ok:
                return k
            k -= 0.5

    def rows_layout(self, k: float, bottom: float = STRIP_BOTTOM) -> dict:
        """Each lake's box (x, y, w, h), and its name's centre x and baseline, in the lakes' area."""
        rows = []
        for row in t5.LAKE_ROWS:
            slots = [self.slot(key, k) for key in row]
            h = max(self.km[key][1] * k for key in row)
            rows.append((row, slots, h, sum(slots) + GAP_X * (len(row) - 1)))
        block = sum(h + NAMES_H for _, _, h, _ in rows) + ROW_GAP
        top = STRIP_TOP + (bottom - STRIP_TOP - STRIP_FOOT - block) / 2
        out = {}
        for row, slots, h, total in rows:
            x = PIC_X + (PIC_W - total) / 2
            for key, sw in zip(row, slots):
                wk, hk = self.km[key][0] * k, self.km[key][1] * k
                cx = x + sw / 2
                out[key] = (cx - wk / 2, top + (h - hk) / 2, wk, hk, cx, top + h + 46)
                x += sw + GAP_X
            top += h + NAMES_H + ROW_GAP
        return out

    def strip(self, c: Canvas, t: float, geo: dict):
        """The five 1405 lakes, all five from the start, each named under it; the hook's highlight steps across them
        (HL_STEP each, none from 5 x HL_STEP on), and a 5-km scale bar with the 1405 chip."""
        hl = int(t // HL_STEP) if np.isfinite(t) and t < HL_STEP * len(ORDER) else None
        for j, key in enumerate(ORDER):
            x, y, w, h, cx, name_y = geo["xy"][key]
            c.im.paste(self.scaled(geo["thumbs"][key], c), (c.X(x), c.Y(y)))
            if hl == j:
                c.frame(x - 8, y - 8, x + w + 8, y + h + 8, colour=self.th.ink)
                c.frame(x - 7, y - 7, x + w + 7, y + h + 7, colour=self.th.ink)
            name = self.label(key)
            assert c.width(name, FA_TEXT, SMALL, "rtl") <= self.slot(key, geo["k"]) + 1, name   # its name fits its slot
            c.text(cx, name_y, name, FA_TEXT, SMALL, self.th.ink, "ms", "rtl")
        bx, by = PIC_X + 22, geo["bottom"] - 40
        label = fa("۵ کیلومتر")
        lw = c.width(label, FA_TEXT, UNIT, "rtl")
        c.frame(bx - 14, by - 26, bx + 5 * geo["k"] + 14 + lw + 14, by + 20, fill=self.th.field)
        c.fill(bx, by, bx + 5 * geo["k"], by + 8, self.th.ink)
        c.text(bx + 5 * geo["k"] + 14 + lw, by + 8, label, FA_TEXT, UNIT, self.th.ink, "rs", "rtl")
        # the pictures' date on the scale-bar row, right side: Landsat passes of 5-6 Mehr 1405 (not the 16 Aban figures)
        when = fa(f"مهر {t5.persian(2026)}")
        ww = c.width(when, FA_BOLD, UNIT, "rtl")
        rx = PIC_X + PIC_W - 14
        c.frame(rx - ww - 28, by - 26, rx, by + 20, fill=self.th.field)
        c.text(rx - 14, by + 8, when, FA_BOLD, UNIT, self.th.ink, "rs", "rtl")
        assert rx - ww - 28 > bx + 5 * geo["k"] + 14 + lw + 14 + 20, "the date chip must not touch the scale bar"
        c.frame(PIC_X, STRIP_TOP, PIC_X + PIC_W, geo["bottom"], colour=self.th.ink)

    def chip(self, c: Canvas, x: float, y: float, s: str):
        """A year in a paper box on the picture, its right edge at x (as onebit_tehran5's chip)."""
        w = c.width(s, FA_BOLD, SMALL, "rtl")
        x0 = x - w - 28
        c.frame(x0, y, x0 + w + 28, y + 72, fill=self.th.field)
        c.text(x0 + w + 14, y + 53, s, FA_BOLD, SMALL, self.th.ink, "rs", "rtl")

    # ── time ──

    def appear(self, i: int) -> list:
        """The hook whole at frame 0; every other headline's words within 1.8 s, so its key line lands by 2.4 s."""
        ws = [w for w, _ in onebit.words_of(self.S.scenes[i].title, self.th)]
        n = len(ws) - ws.count("//")
        if i == 0:
            return [-1.0] * n
        return [0.2 + 1.6 * k / n for k in range(n)]

    # ── text helpers ──

    def wrap(self, c: Canvas, s: str, path, px: int, maxw: float) -> list:
        """The words of s, greedily set in lines no wider than maxw (Persian, right to left)."""
        lines, cur = [], ""
        for w in s.split(" "):
            t = f"{cur} {w}".strip()
            if c.width(t, path, px, "rtl") <= maxw or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def key_lines(self, c: Canvas, s: str, y: float = KEY_Y, at: float = np.inf):
        lines = [part for piece in s.split(" // ") for part in self.wrap(c, piece, FA_TEXT, SMALL, RIGHT - LEFT)]
        for k, line in enumerate(lines):
            c.text(RIGHT, y + KEY_GAP * k, line, FA_TEXT, SMALL, self.th.ink, "rs", "rtl")

    def sources(self, c: Canvas):
        s = self.words["sources"]
        assert c.width(s, FA_TEXT, SOURCE, "rtl") <= 870, s
        c.text(RIGHT, SOURCE_Y, s, FA_TEXT, SOURCE, self.th.head, "rs", "rtl")

    def window(self, c: Canvas, i: int):
        th = self.th
        x, y, w, h = WIN
        c.frame(x, y, x + w, y + h, fill=th.paper)
        c.fill(x, y, x + w, y + BAR, th.ink)
        c.frame(x + 3, y + BAR + 3, x + w - 3, y + h - 3)
        c.text(x + 12, y + BAR - 9, ENG, PIXEL, 32, th.title)
        if 1 <= i <= 3:
            c.text(x + w - 12, y + BAR - 9, f"[{i}/3]", PIXEL, 32, th.title, "rs")
        c.fill(x + 3, RULE_Y, x + w - 3, RULE_Y + 2, th.ink)

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]):
        c = Canvas(s, self.th, 1.0, (0.0, 0.0), size)
        c.pixels(0, 0, self.dots, self.th.dots)
        i = self.scene(t)
        dt = t - self.starts[i] if np.isfinite(t) else np.inf
        self.window(c, i)
        self.progress(c, t)
        at = self.appear(i)
        title(c, self.th, self.S.scenes[i], np.inf if not np.isfinite(dt) else dt, self.lang, 1.0, LEFT, RIGHT,
              HEAD_Y, at, sizes=HEAD, motion=False, line_at=np.inf, small=SMALL)
        if not np.isfinite(dt) or dt >= at[-1] + 0.6:
            if i < 4:
                self.key_lines(c, self.words["scenes"][i][1])
        self.body(c, t)
        self.sources(c)
        return c.im

    def body(self, c: Canvas, t: float):
        i = self.scene(t)
        if i == 0:
            self.strip(c, t, self.geo_hook)
        elif i == 1:
            self.strip(c, np.inf, self.geo_small)
            self.storage_bar(c, t)
        elif i == 2:
            self.columns(c, t)
        elif i == 3:
            self.rain_bar(c, t)
        else:
            self.answer(c, t)

    # ── scene 2: one bar, full length 1,930, to 340, with the band of the stable state ──

    def x_storage(self, v: float) -> float:
        return LEFT + v / tehran5b.TOTAL_CAPACITY * (RIGHT - LEFT)

    def storage_bar(self, c: Canvas, t: float):
        th = self.th
        t0 = self.starts[1] + 0.4
        p = 1.0 if not np.isfinite(t) else smooth((t - t0) / GROW)
        v = tehran5b.NOW * p
        xv = self.x_storage(v)
        c.fill(LEFT, BAR_Y, xv, BAR_Y + BAR_H, BLUE)
        c.frame(LEFT, BAR_Y, RIGHT, BAR_Y + BAR_H, colour=th.ink)
        lo, hi = self.x_storage(BAND[0]), self.x_storage(BAND[1])
        if hi - lo < BAND_MIN:                                          # drawn at least BAND_MIN px wide, centred
            mid = (lo + hi) / 2
            lo, hi = mid - BAND_MIN / 2, mid + BAND_MIN / 2
        c.fill(lo, BAR_Y - 12, hi, BAR_Y + BAR_H + 12, th.mark)        # the band: the stable state, in the mark colour
        lab = f"{fa(BAND[0])} تا {fa(BAND[1])}"
        assert lab == "۸۰۰ تا ۸۵۰", lab
        lab = f"لازم برای پایداری: {lab}"            # what the band is: the spokesman's «عبور از شرایط پایدار»
        lw = c.width(lab, FA_TEXT, SMALL, "rtl")
        cx = min(max((lo + hi) / 2, LEFT + lw / 2), RIGHT - lw / 2)
        c.text(cx, BAR_Y - 22, lab, FA_TEXT, SMALL, th.ink, "ms", "rtl")
        if p > 0.5:
            c.text(xv + 14, BAR_Y + BAR_H - 6, fa(tehran5b.NOW), FA_BOLD, SMALL, th.ink, "ls", "rtl")
        c.text(LEFT, BAR_Y + BAR_H + 56, fa(0), FA_TEXT, UNIT, th.ink, "ls")
        unit = self.words["unit"]
        c.text(510, BAR_Y + BAR_H + 56, unit, FA_TEXT, UNIT, th.ink, "ms", "rtl")
        c.text(RIGHT, BAR_Y + BAR_H + 112, self.words["bar_end"], FA_TEXT, UNIT, th.ink, "rs", "rtl")
        assert c.width(unit, FA_TEXT, UNIT, "rtl") + 2 * 120 < RIGHT - LEFT
        assert fa_thousands(tehran5b.TOTAL_CAPACITY) in self.words["bar_end"]

    # ── scene 3: three columns on one scale, the earliest on the right ──

    def columns(self, c: Canvas, t: float):
        th = self.th
        c.fill(LEFT, COL_BASE, RIGHT, COL_BASE + 2, th.ink)
        values = (tehran5b.WATER_YEAR_START, tehran5.TOTAL["value"], tehran5b.NOW)
        starts = (self.starts[2] + 0.4, self.starts[2] + 1.6, self.starts[2] + 2.8)
        for cx, v, t0, lab in zip(COL_X, values, starts, self.words["columns"]):
            p = 1.0 if not np.isfinite(t) else smooth((t - t0) / GROW)
            top = COL_BASE - v * COL_K * p
            c.fill(cx - COL_W / 2, top, cx + COL_W / 2, COL_BASE, BLUE)
            if p >= 1.0:
                c.frame(cx - COL_W / 2, top, cx + COL_W / 2, COL_BASE, colour=th.ink)
            if p > 0.5:
                c.text(cx, top - 14, fa(v), FA_BOLD, SMALL, th.ink, "ms", "rtl")
            for k, part in enumerate(lab):
                if part:
                    c.text(cx, COL_BASE + 56 + 54 * k, part, FA_TEXT, SMALL, th.ink, "ms", "rtl")
        c.text(510, 1420, self.words["unit"], FA_TEXT, UNIT, th.ink, "ms", "rtl")

    # ── scene 4: one bar to 16 against the dashed expected rain ──

    def rain_bar(self, c: Canvas, t: float):
        th = self.th
        mean = tehran5b.RAIN_EXPECTED
        now = tehran5b.RAIN_NOW
        xv = lambda v: LEFT + v / RAIN_TOP * (RIGHT - LEFT)
        t0 = self.starts[3] + 0.4
        p = 1.0 if not np.isfinite(t) else smooth((t - t0) / GROW)
        v = now * p
        y = RAIN_Y
        c.fill(LEFT, y, xv(v), y + RAIN_H, BLUE)
        c.frame(LEFT, y, RIGHT, y + RAIN_H, colour=th.ink)
        xm = xv(mean)
        for yy in range(y - 30, y + RAIN_H + 30, 14):
            c.fill(xm - 2, yy, xm + 2, yy + 8, th.ink)
        lab = self.words["rain_mark"]
        lw = c.width(lab, FA_TEXT, SMALL, "rtl")
        c.text(min(max(xm, LEFT + lw / 2), RIGHT - lw / 2), y - 40, lab, FA_TEXT, SMALL, th.ink, "ms", "rtl")
        if p > 0.5:
            c.text(xv(v) + 14, y + RAIN_H - 8, fa(round(now)), FA_BOLD, SMALL, th.ink, "ls")
        c.text(LEFT, y + RAIN_H + 56, fa(0), FA_TEXT, UNIT, th.ink, "ls")
        c.text(RIGHT, y + RAIN_H + 56, self.words["rain_unit"], FA_TEXT, UNIT, th.ink, "rs", "rtl")

    # ── scene 5: the answer and the question ──

    def answer(self, c: Canvas, t: float):
        th = self.th
        dt = t - self.starts[4] if np.isfinite(t) else np.inf
        (small,) = self.words["s5_small"]
        t_a, t_q = 1.4, 3.0
        if not np.isfinite(dt) or dt >= t_a:
            for k, line in enumerate(self.wrap(c, small, FA_TEXT, SMALL, RIGHT - LEFT)):
                c.text(RIGHT, 700 + KEY_GAP * k, line, FA_TEXT, SMALL, th.ink, "rs", "rtl")
        if not np.isfinite(dt) or dt >= t_q:
            box_top = 860
            c.frame(LEFT + 60, box_top, RIGHT - 60, box_top + 300, colour=th.ink)
            for k, line in enumerate(self.words["question"].split(" // ")):
                assert c.width(line, FA_BOLD, 72, "rtl") <= (RIGHT - 60) - (LEFT + 60) - 60, line
                c.text(510, box_top + 110 + 92 * k, line, FA_BOLD, 72, th.ink, "ms", "rtl")
            c.text(510, box_top + 262, self.words["question_ref"], FA_TEXT, SMALL, th.ink, "ms", "rtl")


def fa_thousands(n: int) -> str:
    return tehran5b.fa_thousands(n)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="kahgel", choices=["kahgel"], help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and stills only, no video")
    args = ap.parse_args()
    film = Tehran5bFilm(onebit.THEMES[args.theme], COLOURS[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / BASE
    film.draw(1, 0.0).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        for t in (0.0, 3.0, 7.0, 12.0, 13.5, 17.0, 22.0, 24.5):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
