"""«۲ درجه گرم‌تر؛ برفِ البرز چه می‌شود؟» (twodeg_fa): part 2 of the El Niño explainer the owner asked for on 9 Nov
2026. Why 1.5-2 °C of global warming is a lot: ten thousand calm years, the jump of the last 150, where the extra heat
went, the extremes each degree brings, a year's rain in a day, and snow as Iran's natural dam. The frame of the
five-dam reel (onebit_slides, 106,677 views): a real named place in frame 0 and at the end (the Alborz above Tehran
under snow, Sentinel-2), one chart or picture per slide, the headline whole on the slide's first frame, one key phrase
in a red box, no narration (a light score).

Eight slides at 60 BPM, 47 s:
    hook      0-4.5 s     the Alborz and Tehran under snow, 26 Jan 2026 (Sentinel-2), a slow push in, the labels pop
    holocene  4.5-11      global temperature over 12,000 years: the 10,000-year band (century means, Kaufman 2020),
                          farming in the Zagros, Susa, Persepolis; the red line of the last 150 years draws in last
    modern    11-16.5     one bar a year since 1850 (HadCRUT5): 2024 at +1.55 °C, far above the 10,000-year band
    ocean     16.5-23     91 % of the extra heat went into the ocean (IPCC AR6 Table 7.1); 3.5 m of sea water hold as
                          much heat per degree as the whole atmosphere (computed); the deep keeps it for centuries
    extremes  23-28.5     a once-in-50-years heat (global land): 1, 4.8, 8.6, 13.9 times in 50 years (IPCC AR6 SPM.6)
    rain      28.5-34.5   a year's rain in a day or less: Jeddah (NCM), Dubai (WMO), Chabahar (IRIMO, as reported)
    snow      34.5-41     snow is the natural dam: the Alborz in winter and before the next winter (Sentinel-2);
                          snow-cover days at Iran's mountain stations (Sadeqi et al. 2024)
    end       41-47       the summary, the snow picture again, the question (a loop to frame 0)

Numbers: src/twodeg.py (data/twodeg/numbers.json); the rain examples, the ocean shares and the snow numbers are
constants with their sources below; every on-screen number is asserted.

    outputs/onebit/social/twodeg_fa_reel.mp4 (silent master), twodeg_fa_cover.png, _t<sec>.png (stills)

    python -I src/onebit_twodeg.py --stills
    python -I src/onebit_twodeg.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import onebit  # noqa: E402
import onebit_elnino26x as part1  # noqa: E402   (the ocean slide and the glyph guard, imported, not copied)
import twodeg as num  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, PIXEL, SIZES, SOCIAL_CRF, TEXT, Canvas, fa, title  # noqa: E402
from onebit_slides import COLOURS, LEFT, RIGHT, WIN, Slides  # noqa: E402

BASE = "twodeg_fa"
SCENES = ("hook", "holocene", "modern", "ocean", "extremes", "rain", "snow", "end")
SECONDS_OF = dict(hook=4.5, holocene=6.5, modern=5.5, ocean=6.5, extremes=5.5, rain=6.0, snow=6.5, end=6.0)
SECONDS = tuple(SECONDS_OF[k] for k in SCENES)
PACE = dict(bpm=60, bars=tuple(s / 4 for s in SECONDS))
END = sum(SECONDS)                                                # 47 s
COVER_T = 1.0                                                     # s: the cover, once both labels are on the picture
BARH, RULE_Y, SOURCE_Y = 64, 664, 1532
LABEL, UNIT, SOURCE = 48, 44, 42
MIDX = (LEFT + RIGHT) / 2
PAST = "#A3968A"
BAND = "#E3D7C3"                                                  # the 5-95 % band of the Holocene
HOT = "#A03129"
# holocene: time runs right to left, 12,000 years ago at the right, 2025 at the left
CH = (LEFT + 8, 760, RIGHT - 92, 1250)                            # x0, y0 (T_TOP), x1, y1 (T_BOT)
T_TOP, T_BOT = 2.2, -1.2
AGE_LEFT, AGE_RIGHT = -75.0, 12000.0                              # years BP (1950 = 0): 2025 CE to 12,000 BP
# years before present, approximate (Riehl et al. 2013: cultivation at Chogha Golan from about 11,700 years ago;
# Susa: from the late fifth millennium BCE; Persepolis: founded by Darius I in 518 BCE, both UNESCO)
MILESTONES = ((11700, "آغازِ کشت، زاگرس"), (6200, "شوش"), (2500, "تخت‌جمشید"))
BAND_T, MILE_T0, MILE_STEP, RED_T0, RED_T1 = 0.5, 1.1, 0.5, 2.6, 3.9   # s into the holocene slide
# modern: since 1850
C3 = (LEFT + 8, 760, RIGHT - 92, 1250)
C3_TOP, C3_BOT = 2.0, -0.5
# extremes: the unit chart, 50 squares a row
UNIT_ROWS = ((None, 1), (1.0, 4.8), (1.5, 8.6), (2.0, 13.9))      # (warming, times in 50 years)
UNIT_TOP, UNIT_PITCH = 760, 168
# rain: (place and month, amount mm, duration words, the place's mean year mm, mean shown as): Jeddah 24 Nov 2022 (Saudi
# NCM via Arab News, 08:00-14:00; WMO WWIS normal 1982-2011), Dubai airport 16 Apr 2024 (WMO; 1991-2020 normal about
# 80 mm), Chabahar 31 Dec 2021-1 Jan 2022 (IRIB News quoting the Sistan-Baluchestan met office; mean as reported there)
RAIN = (("جده، آذرِ ۱۴۰۱", 179.0, "در حدودِ ۶ ساعت", 55.6, "۵۶"), ("دبی، فروردینِ ۱۴۰۳", 142.0, "در یک روز", 80.0, "حدودِ ۸۰"),
        ("چابهار، دیِ ۱۴۰۰", 144.8, "در یک روز", 110.3, "۱۱۰"))
# the pictures (Sentinel-2 L2A true colour from src/get_alborzsnow.py): winter and the cloud-free composite of the
# passes of 18 Oct-2 Nov 2026 (26 Mehr-11 Aban 1405), before the November storm
SNOW_PIC = onebit.ROOT / "data" / "alborzsnow" / "tex_2026-01-26.jpg"
BARE_PIC = onebit.ROOT / "data" / "alborzsnow" / "tex_before.jpg"
SNOW_BOX = (50.55, 35.45, 52.45, 36.40)                           # W, S, E, N of the tex files (get_alborzsnow.BOX)
PLACES = (("تهران", 51.39, 35.69), ("دماوند", 52.11, 35.95))
HOOK_H, ZOOM = 660, 0.06                                          # px: the hook picture; its push-in over the slide
HOOK_CENTRE = (51.66, 35.86)                                      # lon, lat: the hook's crop holds Tehran and Damavand
# the ocean slide (part 1's drawing): the constants live in onebit_elnino26x


def fa_dec(x: float, digits: int = 1) -> str:
    return fa(f"{x:.{digits}f}").replace(".", "٫")


def words() -> dict:
    scene = dict(
        hook=("۲ درجه گرم‌تر؛ // برفِ البرز {چه می‌شود}؟", "البرز و تهران زیرِ برف، ۶ بهمنِ ۱۴۰۴"),
        holocene=("۱۰ هزار سال: // فقط حدودِ {نیم درجه} تغییر", "دمای کره‌ی زمین؛ میانگین‌های صدساله"),
        modern=("۲۰۲۴: {۱٫۵۵ درجه} // گرم‌تر از دورانِ پیش‌صنعتی", "میانگینِ کلِ کره‌ی زمین، نه فقط ایران"),
        ocean=("{۹۱٪} گرمای اضافه‌ی زمین را // اقیانوس‌ها جذب کرده‌اند", "ال‌نینوی امسال روی همین آبِ گرم است"),
        extremes=("گرمای «یک بار در ۵۰ سال»: // با ۲ درجه {۱۴ بار}", "خشکی‌های جهان؛ هر خانه یک سال"),
        rain=("بارانِ {یک سال} // در یک روز یا کمتر", "خاک فرصتِ جذب ندارد؛ آب سیل می‌شود"),
        snow=("برف، {سدِ طبیعی} ایران است", "مهم این است که بارش برف باشد، نه باران"),
        end=("۲ درجه یعنی: // گرمای بیشتر، بارانِ تندتر، {برفِ کمتر}", "تغییرِ کمِ میانگین، رخدادِ شدیدِ بیشتر"))
    source = dict(hook="Copernicus Sentinel-2 (26 Jan 2026)", holocene="Kaufman 2020 · HadCRUT5 · Riehl 2013",
                  modern="HadCRUT5 · WMO · Kaufman 2020", ocean="IPCC AR6, Table 7.1 · 3.5 m: computed",
                  extremes="IPCC AR6 WG1, SPM.6 (2021)", rain="NCM · WMO · IRIMO (reported) · IPCC",
                  snow="Sentinel-2 · Sadeqi et al. 2024", end="IPCC AR6 WG1 (2021)")
    w = dict(
        scenes=tuple(scene[k] for k in SCENES),
        follow="این را برای کسی بفرستید که می‌گوید ۲ درجه چیزی نیست",
        sources=tuple(source[k] for k in SCENES),
        ch_unit="محورِ افقی: سال پیش؛ دما نسبت به دورانِ پیش‌صنعتی",
        ch_key="سیاه: صدساله · قرمز: ده‌ساله · نقطه: یک سال",
        ch_years=((12000, "۱۲٬۰۰۰"), (9000, "۹٬۰۰۰"), (6000, "۶٬۰۰۰"), (3000, "۳٬۰۰۰"), (0, "امروز")),
        ch_lines=((1.5, "۱٫۵"), (2.0, "۲")),
        recent="۱۵۰ سالِ اخیر",
        band_label="بازه‌ی ۱۰ هزار سال (میانگینِ صدساله)",
        c3_unit="دمای سالانه‌ی کلِ زمین، از ۱۸۵۰؛ هر میله یک سال",
        c3_note="فقط ۲۰۲۴ از ۱٫۵ گذشت؛ روندِ بلندمدت حدودِ ۱٫۴",
        unit_rows=("دورانِ پیش‌صنعتی: ۱ بار", "با ۱ درجه: حدودِ ۵ بار", "با ۱٫۵ درجه: حدودِ ۹ بار",
                   "با ۲ درجه: حدودِ ۱۴ بار"),
        unit_note="قرمز: سالی با گرمای «یک بار در ۵۰ سال»",
        rain_year="میانگینِ یک سالِ کامل",
        rain_ar6="هر درجه گرمایش، بارانِ سنگین را حدودِ ۷٪ شدیدتر می‌کند",
        snow_pics=("۶ بهمنِ ۱۴۰۴: زمستان", "مهر و آبانِ ۱۴۰۵: پیش از برفِ زمستان"),
        snow_lines=("برف: آب را تا بهار و تابستان نگه می‌دارد", "باران: همان زمستان روان می‌شود و می‌رود"),
        snow_data="ایران، ۱۹۸۲ تا ۲۰۱۸، زمستان‌های گرم‌تر و کم‌بارش‌تر:",
        snow_data2="۹ ایستگاه از ۱۳: هر دهه ۳ تا ۱۵ روز پوششِ برفِ کمتر",
        question="وقتی بچه بودید // شهرتان چقدر // برف داشت؟",
    )
    p1 = part1.words()                                            # the ocean slide's labels, as in part 1
    for k in ("heat_title", "col_air", "col_sea", "col_eq", "col_deep"):
        w[k] = p1[k]
    flat = [x for v in w.values() for x in (v if isinstance(v, tuple) else (v,))]
    flat = [y for x in flat for y in (x if isinstance(x, tuple) else (x,)) if isinstance(y, str)]
    bad = [x for x in flat if part1.dotted_yeh(x)]
    assert not bad, bad
    return w


class TwoDegFilm(Slides):
    ocean_draw = part1.ElNino26xFilm.ocean                         # part 1's slide, borrowed

    def __init__(self, th: onebit.Theme, colour: dict):
        self.nums = json.loads((num.DATA / "numbers.json").read_text(encoding="utf-8"))
        self.check_data()
        self.words = words()
        self.setup(th, "fa", colour, self.words, PACE, "Warming.Earth")
        assert abs(self.starts[-1] - END) < 1e-9
        self.hook_at_once = True
        self.th = th
        self.snow_big = self.load(SNOW_PIC)
        self.pic_snow = self.fit(self.snow_big, RIGHT - LEFT, 270)
        self.pic_bare = self.fit(self.load(BARE_PIC), RIGHT - LEFT, 270)
        self.pic_end = self.fit(self.snow_big, RIGHT - LEFT, 380)

    def check_data(self):
        h, i, s = self.nums["holocene"], self.nums["instrumental"], self.nums["spm6"]
        assert h["span_10ka"] == 0.54 and h["at_12ka"] < -1.0
        assert i["y2024"] == 1.55 and i["first_year_above_1p5"] == 2024
        assert sum(1 for v in i["values"] if v > 1.5) == 1, "only 2024 above 1.5 (the screen says so)"
        assert [s["heat50"][str(k)] for k in (1.0, 1.5, 2.0)] == [4.8, 8.6, 13.9]
        assert [round(v) for _, v in UNIT_ROWS] == [1, 5, 9, 14]
        assert s["rain10"]["1.0"][1] == 6.7                 # ~7 % per degree (AR6: about 7 % per 1 °C)
        assert sum(v for _, v in part1.HEAT) == 100

    # ── pictures ──

    @staticmethod
    def load(path: Path) -> Image.Image:
        """The picture at a third of its size (still sharper than the screen), cropped to the box's middle 2:1."""
        im = Image.open(path).convert("RGB")
        return im.resize((im.width // 3, im.height // 3), Image.LANCZOS)

    @staticmethod
    def crop_box(w: int, h: int, W: int, H: int, zoom: float, centre) -> tuple:
        """The source box (x0, y0, x1, y1) and the scale of a W x H view pushed in by `zoom` around `centre` (lon,
        lat; None = the middle), kept inside the picture."""
        k = max(W / w, H / h) * zoom
        cw, ch = W / k, H / k
        if centre is None:
            cx, cy = w / 2, h / 2
        else:
            W_, S_, E_, N_ = SNOW_BOX
            cx = (centre[0] - W_) / (E_ - W_) * w
            cy = (N_ - centre[1]) / (N_ - S_) * h
        x0 = min(max(cx - cw / 2, 0.0), w - cw)
        y0 = min(max(cy - ch / 2, 0.0), h - ch)
        return (x0, y0, x0 + cw, y0 + ch), k

    def fit(self, im: Image.Image, W: int, H: int, zoom: float = 1.0, centre=None) -> Image.Image:
        """The picture filling W x H, pushed in by `zoom` around `centre`."""
        box, _ = self.crop_box(im.width, im.height, W, H, zoom, centre)
        return im.resize((W, H), Image.LANCZOS, box=box)

    def place_xy(self, lon: float, lat: float, W: int, H: int, zoom: float = 1.0, centre=None) -> tuple:
        """Where a place falls on a picture made by fit(W, H, zoom, centre) of the full box."""
        w, h = self.snow_big.size
        (x0, y0, _, _), k = self.crop_box(w, h, W, H, zoom, centre)
        W_, S_, E_, N_ = SNOW_BOX
        px = ((lon - W_) / (E_ - W_) * w - x0) * k
        py = ((N_ - lat) / (N_ - S_) * h - y0) * k
        return px, py

    def tag(self, c: Canvas, x: float, y: float, name: str, size: int = 32):
        """A place: a red dot and a paper tag, to the right of the dot unless that leaves the picture."""
        th = self.th
        tw = c.width(name, FA_BOLD, size, "rtl")
        c.fill(x - 5, y - 5, x + 5, y + 5, HOT)
        x0t, x1t = x + 10, x + 26 + tw
        if x1t > RIGHT - 8:
            x0t, x1t = x - 26 - tw, x - 10
        assert x0t > LEFT + 8, name
        c.frame(x0t, y - 22, x1t, y + 20, fill=th.paper)
        c.text(x1t - 8, y + 10, name, FA_BOLD, size, th.ink, "rs", "rtl")

    def picture(self, c: Canvas, im: Image.Image, y: float, label: str | None):
        th = self.th
        c.im.paste(im, (c.X(LEFT), c.Y(y)))
        c.frame(LEFT - 1, y - 1, RIGHT + 1, y + im.height + 1, colour=th.ink)
        if label:
            w = c.width(label, FA_BOLD, 34, "rtl")
            c.frame(RIGHT - w - 28, y + 10, RIGHT - 8, y + 56, fill=th.paper)
            c.text(RIGHT - 18, y + 44, label, FA_BOLD, 34, th.ink, "rs", "rtl")

    # ── time ──

    def appear(self, i: int) -> list:
        """Every headline whole on the first frame of its slide, as in the five-dam reel."""
        ws = [w for w, _ in onebit.words_of(self.S.scenes[i].title, self.th)]
        return [-1.0] * (len(ws) - ws.count("//"))

    # ── the frame ──

    def window(self, c: Canvas, i: int):
        th = self.th
        x, y, w, h = WIN
        c.frame(x, y, x + w, y + h, fill=th.paper)
        c.fill(x, y, x + w, y + BARH, th.ink)
        c.frame(x + 3, y + BARH + 3, x + w - 3, y + h - 3)
        if i == len(self.S.scenes) - 1:
            c.text(x + w - 14, y + BARH - 18, self.words["follow"], FA_TEXT, 34, th.title, "rs", "rtl")
            assert c.width(self.words["follow"], FA_TEXT, 34, "rtl") <= w - 28
        else:
            c.text(x + 14, y + BARH - 14, self.app, PIXEL, 48, th.title)
            if i > 0:
                c.text(x + w - 14, y + BARH - 14, f"[{i}/{len(self.S.scenes) - 2}]", PIXEL, 48, th.title, "rs")
        c.fill(x + 3, RULE_Y, x + w - 3, RULE_Y + 2, th.ink)

    def sources(self, c: Canvas, i: int):
        s = self.words["sources"][i]
        assert c.width(s, TEXT, SOURCE) <= RIGHT - LEFT, s
        c.text(RIGHT, SOURCE_Y, s, TEXT, SOURCE, self.th.head, "rs")

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]):
        c = Canvas(s, self.th, 1.0, (0.0, 0.0), size)
        c.pixels(0, 0, self.dots, self.th.dots)
        i = self.scene(t)
        dt = t - self.starts[i] if np.isfinite(t) else np.inf
        self.window(c, i)
        self.progress(c, t)
        at = self.appear(i)
        title(c, self.th, self.S.scenes[i], dt, self.lang, 1.0, LEFT, RIGHT, WIN[1] + BARH + 96, at,
              sizes=((68, 92), (60, 82)), motion=False, line_at=at[-1] + 0.6, small=LABEL)
        dict(hook=self.hook, holocene=self.holo, modern=self.modern, ocean=self.ocean, extremes=self.extremes,
             rain=self.rain, snow=self.snowpack, end=self.summary)[SCENES[i]](c, t, dt, i)
        self.sources(c, i)
        return c.im

    # ── hook: the Alborz under snow ──

    def hook(self, c: Canvas, t: float, dt: float, i: int):
        f = 1.0 if not np.isfinite(dt) else min(max(dt / SECONDS_OF["hook"], 0.0), 1.0)
        zoom = 1.0 + ZOOM * f
        im = self.fit(self.snow_big, RIGHT - LEFT, HOOK_H, zoom, HOOK_CENTRE)
        y = 700
        self.picture(c, im, y, None)
        for k, (name, lon, lat) in enumerate(PLACES):
            if np.isfinite(dt) and dt < 0.4 * (k + 1):
                continue
            px, py = self.place_xy(lon, lat, RIGHT - LEFT, HOOK_H, zoom, HOOK_CENTRE)
            assert 20 < px < RIGHT - LEFT - 20 and 20 < py < HOOK_H - 20, (name, px, py)
            self.tag(c, LEFT + px, y + py, name)

    # ── holocene: 12,000 years ──

    def hx(self, age: float) -> float:
        x0, _, x1, _ = CH
        return x0 + (age - AGE_LEFT) / (AGE_RIGHT - AGE_LEFT) * (x1 - x0)

    def hy(self, v: float) -> float:
        _, y0, _, y1 = CH
        return y1 - (min(max(v, T_BOT), T_TOP) - T_BOT) / (T_TOP - T_BOT) * (y1 - y0)

    def poly(self, c: Canvas, pts, colour, width):
        if len(pts) > 1:
            c.d.line([(c.X(x), c.Y(y)) for x, y in pts], fill=colour, width=max(1, round(width * c.k)), joint="curve")

    def holo(self, c: Canvas, t: float, dt: float, i: int):
        th = self.th
        x0, y0, x1, y1 = CH
        h, ins = self.nums["holocene"], self.nums["instrumental"]
        age, med, p5, p95 = (np.array(h[k]) for k in ("age", "median", "p5", "p95"))
        keep = age >= 100                                        # the 1900-2000 bin is left to the instrument line
        age, med, p5, p95 = age[keep], med[keep], p5[keep], p95[keep]
        on = lambda t0: (not np.isfinite(dt)) or dt >= t0  # noqa: E731
        # the 5-95 % band (clipped to the chart: the early Holocene's band runs far below it; said in the comment)
        top = [(self.hx(a), self.hy(v)) for a, v in zip(age, p95)]
        bot = [(self.hx(a), self.hy(v)) for a, v in zip(age, p5)]
        c.d.polygon([(c.X(x), c.Y(y)) for x, y in top + bot[::-1]], fill=BAND)
        for v in (-1, 0, 1):                                      # the grid and its labels
            yy = self.hy(v)
            for xx in np.arange(x0, x1, 14):
                c.fill(xx, yy - 1, min(xx + 6, x1), yy + 1, th.dots if v else PAST)
            c.text(RIGHT, yy + 15, ("+" if v > 0 else "") + fa(v) if v >= 0 else "−" + fa(-v), FA_TEXT, UNIT,
                   th.ink, "rs")
        for v, lab in self.words["ch_lines"]:                     # 1.5 and 2: dashed, in the hot colour
            yy = self.hy(v)
            for xx in np.arange(x0, x1, 20):
                c.fill(xx, yy - 1.5, min(xx + 10, x1), yy + 1.5, HOT)
            c.text(RIGHT, yy + 15, "+" + lab, FA_BOLD, UNIT, HOT, "rs")
        k10 = age <= 10000
        lo, hi = float(np.min(med[k10])), float(np.max(med[k10]))
        if on(BAND_T):                                            # the 10,000-year band of the median
            c.fill(self.hx(0), self.hy(hi), self.hx(10000), self.hy(lo), "#C9B48F")
            c.text(self.hx(5000), self.hy(hi) - 14, self.words["band_label"].split(" (")[0], FA_BOLD, 36, th.ink, "ms",
                   "rtl")
        self.poly(c, [(self.hx(a), self.hy(v)) for a, v in zip(age, med)], th.ink, 4)
        for k, (a, lab) in enumerate(MILESTONES):                 # the milestones, one by one, on paper tags
            if not on(MILE_T0 + MILE_STEP * k):
                continue
            xx = self.hx(a)
            w = c.width(lab, FA_BOLD, 32, "rtl")
            ylab = y1 - 14 - 46 * (k % 2)
            xl = xx - 14 - w / 2 if xx + w / 2 > x1 - 4 else min(max(xx, x0 + w / 2 + 6), x1 - w / 2 - 6)
            yv = float(np.interp(a, age[::-1], med[::-1]))
            for yy in np.arange(self.hy(yv) + 14, ylab - 40, 10):
                c.fill(xx - 1.5, yy, xx + 1.5, yy + 5, th.ink)
            c.frame(xl - w / 2 - 6, ylab - 36, xl + w / 2 + 6, ylab + 10, fill=th.paper)
            c.text(xl, ylab, lab, FA_BOLD, 32, th.ink, "ms", "rtl")
        years, vals = ins["years"], ins["values"]                 # the instrument era: 10-year means, then 2024
        smooth = [(y, float(np.mean(vals[max(0, k - 9):k + 1]))) for k, y in enumerate(years) if k >= 9]
        f = 1.0 if not np.isfinite(dt) else min(max((dt - RED_T0) / (RED_T1 - RED_T0), 0.0), 1.0)
        n = max(2, int(round(f * len(smooth)))) if f > 0 else 0
        if n:
            self.poly(c, [(self.hx(1950 - y), self.hy(v)) for y, v in smooth[:n]], HOT, 9)
            c.text(self.hx(1950 - 1990) + 26, self.hy(0.95), self.words["recent"], FA_BOLD, 34, HOT, "ls", "rtl")
        if f >= 1.0:
            y24 = ins["y2024"]
            c.fill(self.hx(1950 - 2024) - 7, self.hy(y24) - 7, self.hx(1950 - 2024) + 7, self.hy(y24) + 7, HOT)
            c.text(self.hx(1950 - 2024) + 18, self.hy(y24) - 14, f"۲۰۲۴: +{fa_dec(y24, 2)}", FA_BOLD, 40, HOT, "ls")
        c.fill(x0, y1, x1, y1 + 2, th.ink)
        for a, lab in self.words["ch_years"]:
            xx = self.hx(a)
            c.fill(xx - 1, y1, xx + 1, y1 + 12, th.ink)
            anchor = "ls" if a == 0 else ("rs" if a == 12000 else "ms")
            c.text(xx - (8 if a == 0 else 0), y1 + 52, lab, FA_TEXT, 34, th.ink, anchor)
        for k, key in enumerate(("ch_unit", "ch_key")):
            c.text(RIGHT, y1 + 108 + 48 * k, self.words[key], FA_TEXT, 36, th.ink, "rs", "rtl")
            assert c.width(self.words[key], FA_TEXT, 36, "rtl") <= RIGHT - LEFT

    # ── modern: since 1850 ──

    def modern(self, c: Canvas, t: float, dt: float, i: int):
        th = self.th
        x0, y0, x1, y1 = C3
        ins, h = self.nums["instrumental"], self.nums["holocene"]
        years, vals = ins["years"], ins["values"]
        n = len(years)
        X = lambda k: x1 - (k + 0.5) / n * (x1 - x0)  # noqa: E731   (1850 at the right, 2025 at the left)
        Y = lambda v: y1 - (min(max(v, C3_BOT), C3_TOP) - C3_BOT) / (C3_TOP - C3_BOT) * (y1 - y0)  # noqa: E731
        c.fill(x0, Y(h["max_10ka"]), x1, Y(h["min_10ka"]), "#E5D6BC")          # the 10,000-year band
        c.text(x1 - 10, Y(h["max_10ka"]) - 12, self.words["band_label"], FA_BOLD, 32, th.ink, "rs", "rtl")
        for v in (0, 1):
            yy = Y(v)
            for xx in np.arange(x0, x1, 14):
                c.fill(xx, yy - 1, min(xx + 6, x1), yy + 1, PAST if v == 0 else th.dots)
            c.text(RIGHT, yy + 15, ("+" if v else "") + fa(v), FA_TEXT, UNIT, th.ink, "rs")
        yy = Y(1.5)
        for xx in np.arange(x0, x1, 20):
            c.fill(xx, yy - 1.5, min(xx + 10, x1), yy + 1.5, HOT)
        c.text(RIGHT, yy + 15, "+۱٫۵", FA_BOLD, UNIT, HOT, "rs")
        grow = 1.0 if not np.isfinite(dt) else min(max((dt - 0.3) / 1.8, 0.0), 1.0)
        shown = int(round(grow * n))
        w = (x1 - x0) / n
        for k in range(shown):                                    # one bar a year, from 1850 on
            v = vals[k]
            col = HOT if v > h["max_10ka"] else PAST
            ya, yb = sorted((Y(0), Y(v)))
            c.fill(X(k) - w * 0.42, ya, X(k) + w * 0.42, yb, col)
        if shown == n:
            k24 = years.index(2024)
            c.text(X(k24) + 16, Y(ins["y2024"]) - 18, f"۲۰۲۴: +{fa_dec(ins['y2024'], 2)}", FA_BOLD, 48, HOT, "ls")
        c.fill(x0, y1, x1, y1 + 2, th.ink)
        for yv in (1850, 1900, 1950, 2000):
            k = years.index(yv)
            c.fill(X(k) - 1, y1, X(k) + 1, y1 + 12, th.ink)
            c.text(X(k), y1 + 52, fa(yv), FA_TEXT, 34, th.ink, "ms")
        for k, (key, font, col) in enumerate((("c3_unit", FA_TEXT, th.ink), ("c3_note", FA_BOLD, HOT))):
            c.text(RIGHT, y1 + 108 + 50 * k, self.words[key], font, 36, col, "rs", "rtl")
            assert c.width(self.words[key], font, 36, "rtl") <= RIGHT - LEFT

    # ── ocean: part 1's slide ──

    def ocean(self, c: Canvas, t: float, dt: float, i: int):
        self.ocean_draw(c, t, dt)

    # ── extremes: once in 50 years ──

    def extremes(self, c: Canvas, t: float, dt: float, i: int):
        th = self.th
        cell = (RIGHT - LEFT) / 25
        for r, ((gwl, times), lab) in enumerate(zip(UNIT_ROWS, self.words["unit_rows"])):
            top = UNIT_TOP + r * UNIT_PITCH
            on = (not np.isfinite(dt)) or dt >= 0.5 + 0.6 * r
            c.text(RIGHT, top + 36, lab, FA_BOLD, 38, HOT if r == 3 else th.ink, "rs", "rtl")
            hot = round(times) if on else 0
            idx = {int(round((k + 0.5) * 50 / max(times, 1e-9) - 0.5)) for k in range(hot)}
            assert len(idx) == hot
            for k in range(50):
                row, col = divmod(k, 25)
                x = RIGHT - (col + 1) * cell
                y = top + 54 + row * (cell + 4)
                c.fill(x + 3, y, x + cell - 3, y + cell - 4, HOT if k in idx else "#E2D8C8")
        c.text(RIGHT, UNIT_TOP + 4 * UNIT_PITCH + 30, self.words["unit_note"], FA_TEXT, 34, th.ink, "rs", "rtl")

    # ── rain: a year's rain in a day or less ──

    def rain(self, c: Canvas, t: float, dt: float, i: int):
        th = self.th
        top, pitch = 770, 196
        vmax = 185.0
        bw = RIGHT - LEFT
        for k, (place, mm, dur, mean, mean_txt) in enumerate(RAIN):
            y = top + k * pitch
            grow = 1.0 if not np.isfinite(dt) else min(max((dt - 0.5 - 0.5 * k) / 0.8, 0.0), 1.0)
            c.text(RIGHT, y, place, FA_BOLD, 40, th.ink, "rs", "rtl")
            yy = y + 18
            c.fill(RIGHT - mm * grow / vmax * bw, yy, RIGHT, yy + 54, "#2a78d6")
            c.frame(LEFT, yy, RIGHT, yy + 54, colour=th.ink)
            if grow >= 1.0:
                c.text(RIGHT - 16, yy + 40, f"{fa(round(mm))} میلی‌متر {dur}", FA_BOLD, 36, th.paper, "rs", "rtl")
            yy += 64
            c.fill(RIGHT - mean / vmax * bw, yy, RIGHT, yy + 46, "#C9BBA6")
            c.frame(LEFT, yy, RIGHT, yy + 46, colour=th.ink)
            lab = f"{self.words['rain_year']}: {mean_txt}"
            lw, barw = c.width(lab, FA_TEXT, 32, "rtl"), mean / vmax * bw
            xl = RIGHT - 16 if lw + 32 < barw else RIGHT - barw - 14     # inside the bar if it fits, else beside it
            assert xl - lw > LEFT + 10, place
            c.text(xl, yy + 34, lab, FA_TEXT, 32, th.ink, "rs", "rtl")
        c.text(MIDX, top + 3 * pitch + 40, self.words["rain_ar6"], FA_TEXT, 36, th.ink, "ms", "rtl")
        assert c.width(self.words["rain_ar6"], FA_TEXT, 36, "rtl") <= RIGHT - LEFT

    # ── snow: the natural dam ──

    def snowpack(self, c: Canvas, t: float, dt: float, i: int):
        th = self.th
        self.picture(c, self.pic_snow, 700, self.words["snow_pics"][0])
        if (not np.isfinite(dt)) or dt >= 0.6:
            self.picture(c, self.pic_bare, 990, self.words["snow_pics"][1])
        for k, line in enumerate(self.words["snow_lines"]):
            c.text(RIGHT, 1306 + 46 * k, line, FA_BOLD, 36, "#1c5cab" if k == 0 else HOT, "rs", "rtl")
        c.text(RIGHT, 1408, self.words["snow_data"], FA_TEXT, 32, th.ink, "rs", "rtl")
        c.text(RIGHT, 1452, self.words["snow_data2"], FA_BOLD, 32, th.ink, "rs", "rtl")
        assert 1452 + 12 < SOURCE_Y - 36

    # ── end: the summary, the picture, the question ──

    def summary(self, c: Canvas, t: float, dt: float, i: int):
        th = self.th
        self.picture(c, self.pic_end, 700, None)
        question = self.words["question"].split(" // ")
        c.frame(LEFT + 60, 1110, RIGHT - 60, 1460, fill=th.paper, colour=th.ink)
        for k, line in enumerate(question):
            c.text(MIDX, 1210 + 100 * k, line, FA_BOLD, 78, th.ink, "ms", "rtl")
            assert c.width(line, FA_BOLD, 78, "rtl") <= (RIGHT - 60) - (LEFT + 60) - 40, line


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="kahgel", choices=["kahgel"])
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--at", type=float, nargs="*")
    args = ap.parse_args()
    film = TwoDegFilm(onebit.THEMES[args.theme], COLOURS[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / BASE
    film.draw(1, COVER_T).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills or args.at:
        times = args.at or sorted({0.0} | {round(float(film.starts[i] + f * (film.starts[i + 1] - film.starts[i])), 2)
                                           for i in range(len(SECONDS)) for f in (0.35, 0.95)})
        if not args.at:
            for old in (OUT / "social").glob(f"{BASE}_t*.png"):
                old.unlink()
        for t in times:
            film.draw(1, t).save(f"{base}_t{t:05.2f}.png")
            print("saved", f"{base}_t{t:05.2f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
