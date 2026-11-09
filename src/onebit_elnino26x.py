"""EL NIÑO EXPLAINER, PART 1 (elnino26x_fa): the narrated El Niño reel of 8 Nov 2026 (elnino26s_fa, the owner's own
voice) with the explanation the owner asked for on 9 Nov: what El Niño is, how strong this one is, why a handful of
strong events cannot tell Iran's future, and where the heat of global warming goes. The frame of the five-dam reel
(onebit_slides; 106,677 views on 9 Nov 2026), one picture or chart per scene, one key phrase in a red box.

Ten scenes at 60 BPM, 67 s. The five scenes of the narrated reel keep their length, their pictures and the owner's
voice (src/elnino26x_voice.py: n1..n5); the five new ones carry no voice (the light score plays alone):
    S1   0-7 s        the hook (n1): this week's Pacific, warm water tinted, and the ONI bar
    S2   7-12.5 s     what El Niño is: the same week a year ago and now, against 1991-2020 (NOAA PSL)
    S3   12.5-19      how warm: NOAA's weekly classic Niño-3.4 since 1981, 2026 over 1982, 1997, 2015, 2023; NOAA's
                      official relative index (RONI) puts Aug-Oct 2026 second after 1997 (said on screen)
    S4   19-26.75     the 26 El Niño autumns, 21 wetter (n2)
    S5   26.75-30.75  El Niño autumns at 123 % of the mean (n3)
    S6   30.75-38.75  the 22 winters, 11 wetter (n4)
    S7   38.75-45.25  the six strong El Niño autumns (ONI of Oct-Dec at least 1.5): 67 % to 191 % of the mean
    S8   45.25-51.75  why so warm: classic against relative index, Aug-Oct of 1997, 2015, 2026; the gap (-0.03,
                      +0.22, +0.49 °C) is the warmer tropical ocean that the relative index removes
    S9   51.75-58.25  where the heat went: 91 % into the ocean (IPCC AR6 Table 7.1); 3.5 m of sea water hold as much
                      heat per degree as the whole atmosphere (computed); whether warming strengthens El Niño itself
                      is still debated (said on screen)
    S10  58.25-67 s   the verdict and the question (n5)

Numbers: src/elnino26x.py (data/enso/elnino26x/numbers.json) for the new scenes, src/elnino26s.py
(data/enso/elnino26s/numbers.json) and src/enso.py for the narrated ones; every on-screen number is asserted.

    outputs/onebit/social/elnino26x_fa_reel.mp4 (silent master), elnino26x_fa_cover.png, _t<sec>.png (stills)

    python -I src/onebit_elnino26x.py --stills
    python -I src/onebit_elnino26x.py
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from scipy import ndimage  # noqa: E402

import elnino26s as num26  # noqa: E402
import elnino26x as num  # noqa: E402
import enso  # noqa: E402
import onebit  # noqa: E402
import onebit_elnino2 as el2  # noqa: E402
import onebit_elnino26s as s26  # noqa: E402  (the narrated reel's constants and pictures, imported, not copied)
from onebit import FA_BOLD, FA_TEXT, OUT, PIXEL, SIZES, SOCIAL_CRF, TEXT, Canvas, fa, title  # noqa: E402
from onebit_slides import COLOURS, LEFT, RIGHT, WIN, Slides  # noqa: E402

BASE = "elnino26x_fa"
AUTUMN, WINTER = s26.AUTUMN, s26.WINTER
# the posted cut (review of 9 Nov: the index-gap and ocean-heat slides are left out of part 1; the ocean slide is in
# part 2, the gap is in the caption); the voiced scenes keep their length from elnino26s
SCENES = ("hook", "what", "record", "autumn", "iran", "winter", "strong", "answer")
SECONDS_OF = dict(hook=7.0, what=5.5, record=6.5, autumn=7.75, iran=4.0, winter=8.0, strong=6.5, gap=6.5, ocean=6.5,
                  answer=9.75)                                   # the answer: +1 s so the last chord rings out
VOICE_OF = dict(hook="n1", autumn="n2", iran="n3", winter="n4", answer="n5")
SECONDS = tuple(SECONDS_OF[k] for k in SCENES)
PACE = dict(bpm=60, bars=tuple(s / 4 for s in SECONDS))
END = sum(SECONDS)                                               # 55 s
VOICED = {i: VOICE_OF[k] for i, k in enumerate(SCENES) if k in VOICE_OF}   # scene -> the owner's piece
COVER_T = 2.0                                                    # s: the cover frame (the hook whole, the bar grown)
BARH, RULE_Y = s26.BARH, s26.RULE_Y
SOURCE_Y = s26.SOURCE_Y - 8                                      # the descenders clear the window's inner frame
LABEL, UNIT, SOURCE = s26.LABEL, s26.UNIT, s26.SOURCE
INK2 = "#8C7B6B"                                                  # the past years' lines: a warm grey on the paper
WET, DRY, MID = el2.WET, el2.DRY, el2.MID
# S2: the two weeks, one above the other, cooler blue and warmer red on the darkened Blue Marble
AB_LAT = 25.0                                                     # the maps run 25 S to 25 N
AB_W, AB_H = RIGHT - LEFT, round((RIGHT - LEFT) * 50 / 160)       # 828 x 259 px
AB_Y = (712, 1026)                                                # the maps' tops
AB_KEY_Y = 1330                                                   # the key's top
AB_MAX = 3.0                                                      # °C: the tint is full at +-3
AB_MIN = 1.0                                                      # °C: within +-1 no tint (near the usual)
# a diverging ramp on the dark ocean: (°C, R, G, B); the alpha grows with the size of the anomaly
AB_RAMP = np.array([(-3.0, 70, 150, 245), (-1.5, 45, 115, 215), (-0.5, 40, 90, 170), (0.5, 235, 140, 50),
                    (1.5, 240, 95, 40), (3.0, 215, 30, 60), (5.0, 200, 20, 110)])
# S3: the weekly chart
CH = (LEFT + 8, 724, RIGHT - 78, 1262)                            # x0, y0 (CH_MAX), x1, y1 (0 °C): the plot box
CH_MAX = 4.0                                                      # °C: headroom over 2026's +3.4 for its label
CH_DAYS = 213                                                     # 1 June to 31 December
MONTHS = (("تیر", 21), ("مرداد", 52), ("شهریور", 83), ("مهر", 114), ("آبان", 144), ("آذر", 174), ("دی", 204))
#                                                                   1st of each Persian month, days after 1 June (1405)
DRAW_T0, DRAW_T1 = 1.0, 3.6                                       # s into S3: the 2026 line draws in
PAST = "#A3968A"                                                  # the past years' lines and labels
MIDX = (LEFT + RIGHT) / 2                                         # 510: the column's centre
# S7: the six strong autumns
ST = (LEFT + 24, 760, RIGHT - 24, 1240)                           # x0, y0 (200 %), x1, y1 (0 %)
ST_MAX = 200.0
ST_T0, ST_STEP = 0.9, 0.42                                        # s into S7: the first bar, then one every 0.42 s
# S8: where the heat went
HEAT = (("اقیانوس", 91), ("خشکی", 5), ("یخ", 3), ("هوا", 1))     # IPCC AR6 WGI, 1971-2018, % of the heat gained
HEAT_Y, HEAT_H = 772, 96
COL_Y0, COL_Y1 = 1020, 1350                                       # the heat-capacity comparison


def fa_dec(x: float, digits: int = 1) -> str:
    return fa(f"{x:.{digits}f}").replace(".", "٫")


NONJOIN = set("اآأإدذرزژوؤ \u200c\u200d")


def dotted_yeh(text: str) -> bool:
    """A joined final ی with a kasra after it: Vazirmatn (raqm) draws it as the Arabic yeh with two dots."""
    return any(text[k] == "ی" and text[k + 1] == "\u0650" and text[k - 1] not in NONJOIN
               for k in range(1, len(text) - 1))


def words() -> dict:
    """The scenes (bold line, small line), the follow line, the sources of each scene, the labels."""
    scene = dict(
        hook=("ال‌نینوی قوی آمده؛ // یعنی {طوفانِ نوح} در ایران؟", "یکی از قوی‌ترین ال‌نینوها از ۱۹۵۰"),
        what=("ال‌نینو یعنی چه؟ // اقیانوسِ آرام {گرم‌تر از معمول}", "مرکز و شرقِ آرامِ استوایی؛ هر ۲ تا ۷ سال"),
        record=("ال‌نینوی امسال: // {گرم‌ترین} آب از ۱۹۸۱ تاکنون", "شاخصِ رسمی NOAA، اوت تا اکتبر: دوم"),
        autumn=("پاییز: {۲۱ از ۲۶} ال‌نینو // پرباران‌تر از معمول", "اکتبر تا دسامبر؛ هر قطره یک پاییزِ ال‌نینو"),
        iran=("پاییزِ ال‌نینو: {۱۲۳٪} میانگین", "۲۶ پاییزِ ال‌نینو در برابرِ همه‌ی ۷۴ پاییز"),
        winter=("زمستان: {۱۱ از ۲۲} // نیمی پرباران‌تر، نیمی نه", "ژانویه تا مارس؛ مثلِ شیر یا خط"),
        strong=("پاییزِ ال‌نینوی قوی فقط {۶ بار؛} // بارانِ ایران هر بار فرق کرد", "از ۱۹۵۱ فقط ۶ نمونه؛ برای آمار کافی نیست"),
        gap=("چرا این‌قدر گرم؟ // بخشی از آن: {گرمای کلِ گرمسیر}", "فاصله‌ی دو شاخص در ۲۰۲۶: نیم درجه"),
        ocean=("{۹۱٪} گرمای اضافه‌ی زمین را // اقیانوس‌ها جذب کرده‌اند", "اثرِ گرمایش بر خودِ ال‌نینو هنوز روشن نیست"),
        answer=("شانسِ پاییزِ پرباران بیشتر بوده؛ // نه طوفانِ نوح", "این پیش‌بینی نیست"))
    source = dict(hook="NOAA OISST · ONI · NASA Blue Marble", what="NOAA OISST v2.1 (PSL) · Blue Marble",
                  record="NOAA CPC (Niño-3.4, RONI) · WMO", autumn="NOAA ONI · CRU TS 4.10",
                  iran="NOAA ONI · CRU TS 4.10", winter="NOAA ONI · CRU TS 4.10", strong="NOAA ONI · CRU TS 4.10",
                  gap="NOAA CPC: ONI, RONI (ERSSTv6)", ocean="IPCC AR6, Table 7.1 · 3.5 m: computed",
                  answer="NOAA ONI · CRU TS 4.10")
    w = dict(
        scenes=tuple(scene[k] for k in SCENES),
        follow="این را برای کسی بفرستید که از طوفانِ نوح می‌ترسد",
        sources=tuple(source[k] for k in SCENES),
        # hook
        pac_key=("درجه‌ی سلسیوس گرم‌تر از معمول", "هفته‌ی ۱۰ تا ۱۶ آبانِ ۱۴۰۵"),
        pac_ticks=("۱٫۵", "۲", "۳", "۴", "۵"),
        dam_marks=(("ال‌نینو", 0.5), ("قوی", 1.5)),
        dam_unit=("درجه گرم‌تر از معمول؛ شاخص کلاسیک ONI", "میانگین سه‌ماهه‌ی اوت تا اکتبر ۲۰۲۶"),
        # what
        ab_labels=("یک سال پیش: ۱۰ تا ۱۶ آبان ۱۴۰۴", "امسال: ۱۰ تا ۱۶ آبان ۱۴۰۵"),
        ab_key=("سردتر از معمول", "نزدیکِ معمول", "گرم‌تر از معمول"),
        ab_places=("آسیا و استرالیا", "آمریکای جنوبی"),
        # record
        ch_unit="نینو ۳٫۴ (کلاسیک، هفتگی): درجه گرم‌تر از معمول",
        ch_wmo="WMO: احتمالاً تا دسامبر قوی‌ترینِ ثبت‌شده",
        ch_prev="رکوردِ قبلی، ۲۰۱۵",
        ch_legend="خاکستری: ۱۹۸۲، ۱۹۹۷، ۲۰۱۵، ۲۰۲۳ · قرمز: ۲۰۲۶",
        # autumn, iran, winter (the narrated reel's)
        legend=("توپُر: پرباران‌تر از معمولِ ۱۹۵۱–۲۰۲۴", "خالی: کم‌باران‌تر از معمول"),
        scale=("۱۰۰٪", "۱۱۰٪", "۱۲۰٪", "۱۳۰٪", "۱۴۰٪", "۱۵۰٪"),
        unit="درصدِ میانگینِ پاییزِ ۱۹۵۱–۲۰۲۴ (۱۰۰٪)",
        rain_unit="میلی‌متر بارانِ پاییز، کلِ ایران",
        # strong
        st_unit="بارانِ پاییزِ ایران (اکتبر تا دسامبر)، درصدِ میانگین",
        st_mean="خط‌چین: میانگینِ ۱۹۵۱–۲۰۲۴، یعنی ۶۰ میلی‌متر",
        # gap (not in the posted cut)
        gap_legend=("قرمز: شاخصِ کلاسیک (ONI)، با گرمای کلِ گرمسیر", "خاکستری: شاخصِ رسمی NOAA، منهای گرمای کلِ گرمسیر"),
        gap_unit="مرداد تا مهر؛ درجه گرم‌تر از معمول در نینو ۳٫۴",
        gap_word="فاصله",
        # ocean (part 2 borrows it)
        heat_title="گرمای اضافه‌ی زمین کجا رفت؟ ۱۹۷۱ تا ۲۰۱۸",
        col_air=("همه‌ی هوای", "کره‌ی زمین"),
        col_sea=("فقط ۳٫۵ متر", "از آبِ اقیانوس‌ها"),
        col_eq="برای یک درجه گرم شدن، یک اندازه انرژی می‌خواهند",
        col_deep="این گرما آهسته به عمق می‌رود و قرن‌ها می‌ماند",
        # answer (the narrated reel's)
        note="درباره‌ی ال‌نینوهای ۱۹۵۱ تا ۲۰۲۴ است",
        recap=("پاییز: ۲۱ از ۲۶", "میانگینِ پاییز: ۲۳٪ بیشتر", "زمستان: ۱۱ از ۲۲؛ نیمی پرباران‌تر"),
        question="پاییزِ امسال // در شهرِ شما // چطور بوده؟",
    )
    flat = [x for v in w.values() for x in (v if isinstance(v, tuple) else (v,))]
    flat = [y for x in flat for y in (x if isinstance(x, tuple) else (x,)) if isinstance(y, str)]
    bad = [x for x in flat if dotted_yeh(x)]
    assert not bad, bad
    return w


class ElNino26xFilm(Slides):
    warm = s26.ElNino26sFilm.warm                    # the warm table (the narrated reel's), borrowed

    def __init__(self, th: onebit.Theme, colour: dict):
        self.nums = json.loads((num.DATA / "numbers.json").read_text(encoding="utf-8"))
        self.n26 = json.loads((num26.DATA / "numbers.json").read_text(encoding="utf-8"))
        self.res = {s: enso.result(s) for s in (AUTUMN, WINTER)}
        self.check_data()
        self.words = words()
        self.setup(th, "fa", colour, self.words, PACE, "ElNino.Iran")
        assert abs(self.starts[-1] - END) < 1e-9 and len(self.starts) == len(SECONDS) + 1
        self.hook_at_once = True
        self.th = th
        self.comp = el2.composite()
        self.map_w, self.map_h = s26.ElNino26sFilm.geometry3(self)
        self.iran = s26.ElNino26sFilm.make_iran(self)
        self.weeks = {k: num.oisst91(k) for k in num.PSL_WEEKS}      # against 1991-2020 (NOAA PSL)
        self.bm = Image.open(num26.blue_marble()).convert("RGB")
        self.pac = self.make_pacific(self.weeks["now"])
        self.key_pac = s26.ElNino26sFilm.make_key(self)
        self.ab = {k: self.make_anomaly(self.weeks[k]) for k in ("ago", "now")}
        self.ab_key = self.make_ab_key()
        self.sprites = {k: el2.ElNino2Film.sprite(self, k) for k in ("pale", "wet", "dry")}
        self.check_layout()

    # ── checks ──

    def check_data(self) -> None:
        n, o = self.nums, self.n26
        a, w = self.res[AUTUMN], self.res[WINTER]
        assert (a["n_wetter"], len(a["years"])) == (21, 26) and (w["n_wetter"], len(w["years"])) == (11, 22)
        assert o["iran_pct_text"] == 123 and round(o["iran_mm_el"]) == 74 and round(o["iran_mean74"]) == 60
        assert o["oni_shown"] == 2.5 and o["oni_rank"] == 1 and o["roni_rank"] == 2
        assert n["weekly"]["record_n34"]["year"] == 2026 and n["weekly"]["record_n34"]["value"] == 3.4
        assert n["weekly"]["record_n34"]["second"]["year"] == 2015 and n["weekly"]["record_n34"]["second"]["value"] == 3.0
        assert n["weekly"]["first_week"] == "02SEP1981"
        assert n["roni"]["aso_rank"] == 2 and tuple(n["roni"]["aso_first"]) == (1997, 2.07)
        assert [(s["year"], s["pct"]) for s in n["strong"]] == [list(x) for x in num.EXPECT["strong"]] or \
            [(s["year"], s["pct"]) for s in n["strong"]] == list(num.EXPECT["strong"])
        assert n["strong_n"] == 6 and n["strong_wetter"] == 4 and n["autumn_mean74"] == 60.0
        assert sum(v for _, v in HEAT) == 100

    def check_layout(self) -> None:
        assert AB_Y[0] + AB_H + 30 < AB_Y[1] and AB_Y[1] + AB_H + 40 < AB_KEY_Y
        assert AB_KEY_Y + 30 + 60 < SOURCE_Y - 40
        assert CH[3] + 90 < SOURCE_Y - 60
        assert COL_Y1 + 80 < SOURCE_Y
        for s in self.words["sources"]:
            assert onebit._font(TEXT, SOURCE).getlength(s) <= RIGHT - LEFT, s

    # ── pictures ──

    def bm_crop(self, lat_max: float, w: int, h: int) -> np.ndarray:
        """The Blue Marble of the box (120 E to 80 W) between lat_max S and N, resized, darkened."""
        lon0, lon1, lat0, lat1 = s26.PAC_BOX
        H = self.bm.height
        y0 = round((lat1 - lat_max) / (lat1 - lat0) * H)
        y1 = round((lat1 + lat_max) / (lat1 - lat0) * H)
        im = self.bm.crop((0, y0, self.bm.width, y1)).resize((w, h), Image.LANCZOS)
        return np.asarray(im, float) * 0.42

    def sample(self, g: dict, lat_max: float, w: int, h: int) -> tuple:
        """The week's mean anomaly at each pixel (nearest ocean cell filled into the land), and the ocean mask."""
        lat, lon, m = g["lat"], g["lon"], g["mean"]
        ocean = np.isfinite(m)
        idx = ndimage.distance_transform_edt(~ocean, return_distances=False, return_indices=True)
        filled = m[tuple(idx)]
        lon0, lon1, _, _ = s26.PAC_BOX
        lon_d = lon0 + (np.arange(w) + 0.5) / w * (lon1 - lon0)
        lat_d = lat_max - (np.arange(h) + 0.5) / h * (2 * lat_max)
        LON, LAT = np.meshgrid(lon_d, lat_d)
        iy = (LAT - lat[0]) / (lat[1] - lat[0])
        ix = (LON - lon[0]) / (lon[1] - lon[0])
        val = ndimage.map_coordinates(filled, [iy, ix], order=1, mode="nearest")
        wet = ndimage.map_coordinates(ocean.astype(float), [iy, ix], order=0, mode="nearest") > 0.5
        return val, wet

    def make_pacific(self, g: dict) -> Image.Image:
        """S1: the week's Pacific, tinted where the anomaly is at least +1.5 °C (the narrated reel's look), the
        Niño-3.4 box outlined."""
        W, H = s26.PAC_W, s26.PAC_H
        base = self.bm_crop(30.0, W, H)
        val, wet = self.sample(g, 30.0, W, H)
        hot = wet & (val >= s26.KEY_LO)
        rgb, alpha = self.warm(val)
        alpha = np.maximum(alpha, s26.TINT_MIN_ALPHA)
        out = base.copy()
        out[hot] = (1 - alpha[hot][:, None]) * base[hot] + alpha[hot][:, None] * rgb[hot]
        lon0, lon1, lat0, lat1 = s26.PAC_BOX
        X0, X1 = (190.0 - lon0) / (lon1 - lon0) * W, (240.0 - lon0) / (lon1 - lon0) * W
        Y0, Y1 = (lat1 - 5.0) / (lat1 - lat0) * H, (lat1 + 5.0) / (lat1 - lat0) * H
        self.nino_box = (LEFT + X0, LEFT + X1, s26.PAC_Y + Y0, s26.PAC_Y + Y1)
        arr = np.clip(out + 0.5, 0, 255).astype(np.uint8)
        for xx in range(int(round(X0)), int(round(X1)) + 1):
            for yy in (int(round(Y0)), int(round(Y1))):
                arr[yy, xx] = MID
        for yy in range(int(round(Y0)), int(round(Y1)) + 1):
            for xx in (int(round(X0)), int(round(X1))):
                arr[yy, xx] = MID
        return Image.fromarray(arr)

    def ab_colour(self, v: np.ndarray) -> tuple:
        """S2: AB_RAMP's colour at each anomaly; no tint within +-AB_MIN (the usual); the tint grows to full at
        +-AB_MAX, so a small anomaly is a faint wash and a big one is solid."""
        x = np.clip(v, AB_RAMP[0, 0], AB_RAMP[-1, 0])
        rgb = np.stack([np.interp(x, AB_RAMP[:, 0], AB_RAMP[:, k]) for k in (1, 2, 3)], -1)
        f = np.clip((np.abs(v) - AB_MIN) / (AB_MAX - AB_MIN), 0, 1)
        alpha = 0.55 + 0.4 * f
        return rgb, np.where(np.abs(v) < AB_MIN, 0.0, alpha)

    def make_anomaly(self, g: dict) -> Image.Image:
        base = self.bm_crop(AB_LAT, AB_W, AB_H)
        val, wet = self.sample(g, AB_LAT, AB_W, AB_H)
        rgb, alpha = self.ab_colour(val)
        alpha = np.where(wet, alpha, 0.0)
        out = (1 - alpha[..., None]) * base + alpha[..., None] * rgb
        return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8))

    def make_ab_key(self) -> Image.Image:
        n = 600
        v = np.linspace(-AB_MAX, AB_MAX, n)
        rgb, alpha = self.ab_colour(v[None, :])
        dark = s26.OCEAN_DARK[None, None, :]
        col = (1 - alpha[..., None]) * dark + alpha[..., None] * rgb
        return Image.fromarray(np.repeat(np.clip(col, 0, 255).astype(np.uint8), 30, axis=0))

    # ── time ──

    def appear(self, i: int) -> list:
        """Every headline whole on the first frame of its slide, as in the five-dam reel (onebit_tehran5)."""
        ws = [w for w, _ in onebit.words_of(self.S.scenes[i].title, self.th)]
        return [-1.0] * (len(ws) - ws.count("//"))

    def turn(self, season: str, k: int) -> float:
        return s26.WET_T0[season] + k * s26.WET_SPAN[season] / len(self.res[season]["years"])

    # ── the frame ──

    def window(self, c: Canvas, i: int):
        th = self.th
        x, y, w, h = WIN
        c.frame(x, y, x + w, y + h, fill=th.paper)
        c.fill(x, y, x + w, y + BARH, th.ink)
        c.frame(x + 3, y + BARH + 3, x + w - 3, y + h - 3)
        last = i == len(self.S.scenes) - 1
        if last:
            c.text(x + w - 14, y + BARH - 18, self.words["follow"], FA_TEXT, 34, th.title, "rs", "rtl")
            assert c.width(self.words["follow"], FA_TEXT, 34, "rtl") <= w - 28
        else:
            c.text(x + 14, y + BARH - 14, self.app, PIXEL, 48, th.title)
            if i > 0:
                c.text(x + w - 14, y + BARH - 14, f"[{i}/{len(self.S.scenes) - 2}]", PIXEL, 48, th.title, "rs")
                assert len(self.S.scenes) - 2 >= i
        c.fill(x + 3, RULE_Y, x + w - 3, RULE_Y + 2, th.ink)

    def sources(self, c: Canvas, i: int):
        s = self.words["sources"][i]
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
        dict(hook=self.pacific, what=self.what, record=self.record, autumn=self.autumn, iran=self.iran_scene,
             winter=self.winter, strong=self.strong, gap=self.gap, ocean=self.ocean,
             answer=self.answer)[SCENES[i]](c, t, dt)
        self.sources(c, i)
        return c.im

    # ── S1: the hook ──

    def pacific(self, c: Canvas, t: float, dt: float):
        th = self.th
        c.im.paste(self.pac, (LEFT, s26.PAC_Y))
        c.frame(LEFT - 1, s26.PAC_Y - 1, RIGHT + 1, s26.PAC_Y + s26.PAC_H + 1, colour=th.ink)
        x0, x1, y0, _ = self.nino_box
        lw = c.width(s26.NINO_LABEL, FA_TEXT, LABEL, "rtl")
        lx = min(max((x0 + x1) / 2, LEFT + lw / 2 + 8), RIGHT - lw / 2 - 8)
        c.frame(lx - lw / 2 - 8, y0 - 60, lx + lw / 2 + 8, y0 - 14, fill=th.paper)
        c.text(lx, y0 - 26, s26.NINO_LABEL, FA_TEXT, LABEL, th.ink, "ms", "rtl")
        pw = c.width(s26.PAC_LABEL, FA_TEXT, LABEL, "rtl")
        c.frame(RIGHT - pw - 30, s26.PAC_Y + s26.PAC_H - 62, RIGHT - 8, s26.PAC_Y + s26.PAC_H - 12, fill=th.paper)
        c.text(RIGHT - 19, s26.PAC_Y + s26.PAC_H - 24, s26.PAC_LABEL, FA_TEXT, LABEL, th.ink, "rs", "rtl")
        by = s26.KEY_Y
        c.im.paste(self.key_pac.resize((RIGHT - LEFT, 30), Image.BILINEAR), (c.X(LEFT), c.Y(by)))
        c.frame(LEFT, by, RIGHT, by + 30, colour=th.ink)
        for v, lab in zip((1.5, 2.0, 3.0, 4.0, 5.0), self.words["pac_ticks"]):
            xv = LEFT + (v - s26.KEY_LO) / (s26.KEY_HI - s26.KEY_LO) * (RIGHT - LEFT)
            c.fill(xv - 1, by + 30, xv + 1, by + 40, th.ink)
            anchor = "ls" if v == 1.5 else ("rs" if v == 5.0 else "ms")
            c.text(xv, by + 78, lab, FA_TEXT, UNIT, th.ink, anchor, "rtl")
        for k, line in enumerate(self.words["pac_key"]):
            c.text(RIGHT, by + 124 + 44 * k, line, FA_TEXT, UNIT, th.ink, "rs", "rtl")
        self.oni_bar(c, t)

    def oni_bar(self, c: Canvas, t: float):
        """The classic ONI of Aug-Oct 2026 as a bar that fills from the right (Persian reading order); it grows from
        the El Niño mark (0.5) to its value between 0.2 and 1.8 s, so the hook moves from frame 0."""
        th = self.th
        lo, hi = s26.BAR_SCALE
        y, bh = s26.BAR_Y, s26.BAR_H
        xv = lambda v: RIGHT - (v - lo) / (hi - lo) * (RIGHT - LEFT)  # noqa: E731
        p = 1.0 if not np.isfinite(t) else min(max((t - 0.2) / 1.6, 0.0), 1.0)
        p = p * p * (3 - 2 * p)
        val = 0.5 + (self.n26["oni"] - 0.5) * p
        c.fill(xv(val), y, RIGHT, y + bh, th.mark)
        c.frame(LEFT, y, RIGHT, y + bh, colour=th.ink)
        for lab, v in self.words["dam_marks"]:
            x = xv(v)
            for yy in range(y - 14, y + bh + 8, 10):
                c.fill(x - 2, yy, x + 2, yy + 6, th.ink)
            c.text(x, y - 26, lab, FA_TEXT, LABEL, th.ink, "ms", "rtl")
        if p >= 1.0:
            c.text(xv(val) - 14, y + bh - 6, fa_dec(self.n26["oni_shown"]), FA_BOLD, LABEL, th.ink, "rs")
        c.text(RIGHT, y - 26, fa(0), FA_TEXT, UNIT, th.ink, "rs")
        c.text(LEFT, y - 26, fa(int(hi)), FA_TEXT, UNIT, th.ink, "ls")
        for k, line in enumerate(self.words["dam_unit"]):
            c.text(RIGHT, y + bh + 48 + 52 * k, line, FA_TEXT, UNIT, th.ink, "rs", "rtl")
            assert c.width(line, FA_TEXT, UNIT, "rtl") <= RIGHT - LEFT, line

    # ── S2: what El Niño is ──

    def what(self, c: Canvas, t: float, dt: float):
        th = self.th
        for k, (tag, y) in enumerate((("ago", AB_Y[0]), ("now", AB_Y[1]))):
            c.im.paste(self.ab[tag], (c.X(LEFT), c.Y(y)))
            c.frame(LEFT - 1, y - 1, RIGHT + 1, y + AB_H + 1, colour=th.ink)
            bx0 = LEFT + (190.0 - 120.0) / 160.0 * AB_W           # the Niño-3.4 box (170 W-120 W, 5 S-5 N), in paper
            bx1 = LEFT + (240.0 - 120.0) / 160.0 * AB_W
            by0 = y + (AB_LAT - 5.0) / (2 * AB_LAT) * AB_H
            by1 = y + (AB_LAT + 5.0) / (2 * AB_LAT) * AB_H
            c.frame(bx0, by0, bx1, by1, colour="#F4EFE4")
            lab = self.words["ab_labels"][k]
            lw = c.width(lab, FA_BOLD, 40, "rtl")
            c.frame(RIGHT - lw - 30, y + 10, RIGHT - 8, y + 62, fill=th.paper)
            c.text(RIGHT - 19, y + 50, lab, FA_BOLD, 40, th.ink, "rs", "rtl")
            if tag == "now":                                    # where the map's edges are
                west, east = self.words["ab_places"]
                for s, x, anchor in ((west, LEFT + 10, "ls"), (east, RIGHT - 10, "rs")):
                    w = c.width(s, FA_TEXT, 30, "rtl")
                    xa = x if anchor == "ls" else x - w
                    c.frame(xa - 6, y + AB_H - 50, xa + w + 6, y + AB_H - 10, fill=th.paper)
                    c.text(x, y + AB_H - 20, s, FA_TEXT, 30, th.ink, anchor, "rtl")
        by = AB_KEY_Y
        c.im.paste(self.ab_key.resize((RIGHT - LEFT, 30), Image.BILINEAR), (c.X(LEFT), c.Y(by)))
        c.frame(LEFT, by, RIGHT, by + 30, colour=th.ink)
        cold, usual, warm = self.words["ab_key"]
        mid = LEFT + (RIGHT - LEFT) / 2                      # the dark band (-1 to +1 °C) is centred on the key
        size = 38
        c.text(LEFT, by + 72, cold, FA_TEXT, size, th.ink, "ls", "rtl")
        c.text(mid, by + 72, usual, FA_TEXT, size, th.ink, "ms", "rtl")
        c.text(RIGHT, by + 72, warm, FA_TEXT, size, th.ink, "rs", "rtl")
        wc, wu, ww = (c.width(s, FA_TEXT, size, "rtl") for s in (cold, usual, warm))
        assert LEFT + wc + 30 < mid - wu / 2 and mid + wu / 2 + 30 < RIGHT - ww, "the key's labels touch"

    # ── S3: the weekly record ──

    def cx(self, day: float) -> float:
        """Days after 1 June -> x: the months run right to left (Persian reading order)."""
        x0, _, x1, _ = CH
        return x1 - day / CH_DAYS * (x1 - x0)

    def cy(self, v: float) -> float:
        _, y0, _, y1 = CH
        return y1 - max(0.0, v) / CH_MAX * (y1 - y0)

    def line(self, c: Canvas, pts: list, colour: str, width: float):
        d = c.d
        xy = [(c.X(self.cx(day)), c.Y(self.cy(v))) for day, v in pts]
        if len(xy) > 1:
            d.line(xy, fill=colour, width=max(1, round(width * c.k)), joint="curve")

    def record(self, c: Canvas, t: float, dt: float):
        th = self.th
        x0, y0, x1, y1 = CH
        for v in (1, 2, 3):                                       # the grid
            yy = self.cy(v)
            for xx in np.arange(x0, x1, 14):
                c.fill(xx, yy - 1, min(xx + 6, x1), yy + 1, th.dots)
            c.text(RIGHT, yy + 15, f"+{fa(v)}", FA_TEXT, UNIT, th.ink, "rs")
        c.text(RIGHT, y1 + 15, fa(0), FA_TEXT, UNIT, th.ink, "rs")
        c.fill(x0, y1, x1, y1 + 2, th.ink)
        ticks = [day for _, day in MONTHS] + [CH_DAYS]
        for k, (name, day) in enumerate(MONTHS):                  # the months: a tick at the 1st, the name in between
            xx = self.cx(day)
            c.fill(xx - 1, y1, xx + 1, y1 + 12, th.ink)
            xa, xb = self.cx(ticks[k + 1]), xx
            if xb - xa >= c.width(name, FA_TEXT, 32, "rtl") + 8:
                c.text((xa + xb) / 2, y1 + 50, name, FA_TEXT, 32, th.ink, "ms", "rtl")
        for k, (key, font, col) in enumerate((("ch_legend", FA_TEXT, th.ink), ("ch_unit", FA_TEXT, th.ink),
                                               ("ch_wmo", FA_BOLD, th.mark))):
            line = self.words[key]
            c.text(RIGHT, y1 + 108 + 50 * k, line, font, 36, col, "rs", "rtl")
            assert c.width(line, font, 36, "rtl") <= RIGHT - LEFT, line
        prev = self.nums["weekly"]["record_n34"]["second"]["value"]   # 2015's +3.0: the record before this year
        yp = self.cy(prev)
        for xx in np.arange(x0, x1, 18):
            c.fill(xx, yp - 1.5, min(xx + 10, x1), yp + 1.5, PAST)
        c.text(x1, yp - 14, f"{self.words['ch_prev']}: {fa_dec(prev)}", FA_TEXT, 34, th.ink, "rs", "rtl")
        paths = {int(y): p for y, p in self.nums["paths"].items()}
        for y in (1982, 1997, 2015, 2023):                       # the past years, whole from the start
            self.line(c, [q for q in paths[y] if q[0] <= CH_DAYS], PAST, 2.5)
        p = paths[2026]                                           # 2026 draws in, red
        f = 1.0 if not np.isfinite(dt) else min(max((dt - DRAW_T0) / (DRAW_T1 - DRAW_T0), 0.0), 1.0)
        if f <= 0:
            return
        last_day = p[-1][0]
        upto = f * last_day
        shown = [q for q in p if q[0] <= upto]
        if len(shown) < len(p) and shown:
            nxt = p[len(shown)]
            a = (upto - shown[-1][0]) / max(1e-9, nxt[0] - shown[-1][0])
            shown = shown + [(upto, shown[-1][1] + a * (nxt[1] - shown[-1][1]))]
        self.line(c, shown, th.mark, 7)
        if shown:
            hx, hy = self.cx(shown[-1][0]), self.cy(shown[-1][1])
            c.fill(hx - 8, hy - 8, hx + 8, hy + 8, th.mark)
        if f >= 1.0:
            day, v = max(p, key=lambda q: q[1])
            s = f"۲۰۲۶: +{fa_dec(v)}"
            w = c.width(s, FA_BOLD, 52)
            xl = min(max(self.cx(day) - w / 2, x0 + 4), x1 - w - 16)
            top = self.cy(v) - 96
            assert top > RULE_Y + 12, "the 2026 label runs into the rule"
            c.frame(xl - 12, top, xl + w + 12, top + 62, fill=th.mark, colour=th.mark)
            c.text(xl, top + 48, s, FA_BOLD, 52, th.paper, "ls")

    # ── S4-S6: the narrated reel's drops and map ──

    def drops(self, c: Canvas, dt: float, season: str):
        th = self.th
        r = self.res[season]
        flags = [bool(r["wetter"][y]) for y in r["years"]]
        n = len(flags)
        per = s26.PER_ROW[season]
        pitch = (RIGHT - LEFT) / per
        CELL, DROP = s26.CELL, s26.DROP
        for k, wet in enumerate(flags):
            row, col = divmod(k, per)
            x = RIGHT - pitch / 2 - col * pitch
            y = s26.DROP_TOP + row * s26.ROW_PITCH
            turned = np.isfinite(dt) and dt >= self.turn(season, k) or not np.isfinite(dt)
            sp = self.sprites[("wet" if wet else "dry") if turned else "pale"]
            c.im.paste(sp, (c.X(x - CELL * len(DROP) / 2), c.Y(y - CELL * len(DROP) / 2)), sp)
        counted = (not np.isfinite(dt)) or dt >= s26.COUNT_T[season]
        c.text(MIDX, 1196, f"{fa(sum(flags))} از {fa(n)}", FA_BOLD, 120, th.ink if counted else th.paper, "ms", "rtl")
        for k, (kind, lab) in enumerate((("wet", self.words["legend"][0]), ("dry", self.words["legend"][1]))):
            y = 1282 + k * 66
            sp = self.sprites[kind].resize((40, 40), Image.NEAREST)
            c.im.paste(sp, (c.X(RIGHT - 40), c.Y(y - 34)), sp)
            c.text(RIGHT - 60, y, lab, FA_TEXT, LABEL, th.ink, "rs", "rtl")

    def autumn(self, c: Canvas, t: float, dt: float):
        self.drops(c, dt, AUTUMN)

    def winter(self, c: Canvas, t: float, dt: float):
        self.drops(c, dt, WINTER)

    def iran_scene(self, c: Canvas, t: float, dt: float):
        th = self.th
        x0 = (1080 - self.map_w) // 2
        c.im.paste(self.iran, (x0, s26.MAP_Y3))
        c.frame(x0 - 1, s26.MAP_Y3 - 1, x0 + self.map_w + 1, s26.MAP_Y3 + self.map_h + 1, colour=th.ink)
        bx0, bx1, by = LEFT + 40, RIGHT - 40, s26.COLOUR3_Y
        n = 200
        for k in range(n):
            pct = el2.LO + (el2.HI - el2.LO) * (k + 0.5) / n
            rgb = el2.colour_of(np.array([pct]))[0].astype(int)
            c.fill(bx0 + (bx1 - bx0) * k / n, by, bx0 + (bx1 - bx0) * (k + 1) / n, by + 30, "#%02x%02x%02x" % tuple(rgb))
        c.frame(bx0, by, bx1, by + 30, colour=th.ink)
        for v, lab in zip((100, 110, 120, 130, 140, 150), self.words["scale"]):
            xv = bx0 + (v - el2.LO) / (el2.HI - el2.LO) * (bx1 - bx0)
            c.fill(xv - 1, by + 30, xv + 1, by + 40, th.ink)
            c.text(xv, by + 78, lab, FA_TEXT, UNIT, th.ink, "ms", "rtl")
        c.text(MIDX, by + 124, self.words["unit"], FA_TEXT, UNIT, th.ink, "ms", "rtl")
        mean, el = self.n26["iran_mean74"], self.n26["iran_mm_el"]
        top = mean / s26.RAIN_MEAN_AT
        xv = lambda v: RIGHT - v / top * (RIGHT - LEFT)  # noqa: E731   (0 at the right: Persian reading order)
        p = 1.0 if not np.isfinite(dt) else min(max((dt - s26.RAIN_OFF) / s26.GROW, 0.0), 1.0)
        p = p * p * (3 - 2 * p)
        y, bh = s26.BAR_Y, s26.BAR_H
        c.fill(xv(el * p), y, RIGHT, y + bh, th.mark)
        c.frame(LEFT, y, RIGHT, y + bh, colour=th.ink)
        xm = xv(mean)
        for yy in range(y - 4, y + bh + 10, 12):
            c.fill(xm - 2, yy, xm + 2, yy + 7, th.ink)
        c.text(min(max(xm, LEFT + 150), RIGHT - 150), y - 22, fa(f"میانگین {round(mean)}"), FA_TEXT, LABEL, th.ink,
               "ms", "rtl")
        if p > 0.5:
            c.text(xv(el * p) - 14, y + bh - 6, fa(round(el)), FA_BOLD, LABEL, th.ink, "rs")
        c.text(RIGHT, y - 22, fa(0), FA_TEXT, UNIT, th.ink, "rs")
        c.text(RIGHT, y + bh + 56, self.words["rain_unit"], FA_TEXT, UNIT, th.ink, "rs", "rtl")

    # ── S7: the six strong autumns ──

    def strong(self, c: Canvas, t: float, dt: float):
        th = self.th
        x0, y0, x1, y1 = ST
        bars = self.nums["strong"]                              # 1965 ... 2023, then this year's open slot
        n = len(bars) + 1
        slot = (x1 - x0) / n
        ybar = lambda v: y1 - v / ST_MAX * (y1 - y0)  # noqa: E731
        for k, b in enumerate(bars):                            # right to left: 1965 at the right
            xr = x1 - k * slot
            xa, xb = xr - slot * 0.82, xr - slot * 0.18
            f = 1.0 if not np.isfinite(dt) else min(max((dt - ST_T0 - k * ST_STEP) / 0.35, 0.0), 1.0)
            if f > 0:
                top = ybar(b["pct"] * f)
                col = WET if b["pct"] > 110 else DRY if b["pct"] < 90 else (176, 166, 152)   # near the mean: grey
                c.fill(xa, top, xb, y1, "#%02x%02x%02x" % tuple(col))
                if f >= 1.0:
                    c.text((xa + xb) / 2, top - 16, fa(f"{b['pct']}٪"), FA_BOLD, 44, th.ink, "ms", "rtl")
            c.text((xa + xb) / 2, y1 + 54, fa(b["year"]), FA_BOLD, 40, th.ink, "ms")
        xr = x1 - len(bars) * slot                              # this year's slot: dashed, a question
        xa, xb = xr - slot * 0.82, xr - slot * 0.18
        for yy in np.arange(ybar(ST_MAX), y1 - 4, 12):
            c.fill(xa, yy, xa + 3, yy + 6, th.mark)
            c.fill(xb - 3, yy, xb, yy + 6, th.mark)
        c.text((xa + xb) / 2, ybar(ST_MAX * 0.75) + 20, "؟", FA_BOLD, 72, th.mark, "ms", "rtl")
        c.text((xa + xb) / 2, y1 + 54, fa(2026), FA_BOLD, 40, th.mark, "ms")
        c.fill(x0, y1, x1, y1 + 2, th.ink)
        ym = ybar(100)
        for xx in np.arange(x0, x1, 16):
            c.fill(xx, ym - 1.5, min(xx + 9, x1), ym + 1.5, th.ink)
        c.text(RIGHT, y1 + 120, self.words["st_unit"], FA_TEXT, 40, th.ink, "rs", "rtl")
        c.text(RIGHT, y1 + 172, self.words["st_mean"], FA_TEXT, 40, th.ink, "rs", "rtl")

    # ── S8: classic against relative index ──

    def gap(self, c: Canvas, t: float, dt: float):
        th = self.th
        pairs = self.nums["pairs"]
        x0, y0, x1, y1 = LEFT + 20, 790, RIGHT - 20, 1200
        vmax = 2.8
        Y = lambda v: y1 - v / vmax * (y1 - y0)  # noqa: E731
        years = ("1997", "2015", "2026")                      # right to left: 1997 at the right
        slot = (x1 - x0) / 3
        grow = 1.0 if not np.isfinite(dt) else min(max((dt - 0.6) / 0.9, 0.0), 1.0)
        for k, y in enumerate(years):
            xr = x1 - k * slot
            bw = slot * 0.30
            xa_c, xb_c = xr - slot * 0.5 + 6, xr - slot * 0.5 + 6 + bw      # classic: the right bar of the pair
            xa_c, xb_c = xr - slot * 0.18 - bw, xr - slot * 0.18
            xa_r, xb_r = xa_c - bw - 10, xa_c - 10                          # relative: to its left
            on, ro = pairs[y]["oni"] * grow, pairs[y]["roni"] * grow
            c.fill(xa_c, Y(on), xb_c, y1, th.mark)
            c.fill(xa_r, Y(ro), xb_r, y1, PAST)
            if grow >= 1.0:
                c.text((xa_c + xb_c) / 2, Y(on) - 14, fa_dec(pairs[y]["oni"], 2), FA_BOLD, 36, th.mark, "ms")
                c.text((xa_r + xb_r) / 2, Y(ro) - 14, fa_dec(pairs[y]["roni"], 2), FA_BOLD, 36, th.ink, "ms")
                g = pairs[y]["gap"]
                lab = f"{self.words['gap_word']}: " + ("تقریباً صفر" if abs(g) < 0.05 else f"{fa_dec(g, 2)} درجه")
                c.text((xa_r + xb_c) / 2, y1 + 104, lab, FA_BOLD, 36, th.mark if g > 0.3 else th.ink, "ms", "rtl")
            c.text((xa_r + xb_c) / 2, y1 + 54, fa(int(y)), FA_BOLD, 44, th.ink, "ms")
        c.fill(x0, y1, x1, y1 + 2, th.ink)
        for k, line in enumerate(self.words["gap_legend"]):
            c.text(RIGHT, y1 + 170 + 46 * k, line, FA_TEXT, 36, th.mark if k == 0 else th.ink, "rs", "rtl")
            assert c.width(line, FA_TEXT, 36, "rtl") <= RIGHT - LEFT, line
        c.text(RIGHT, y1 + 170 + 46 * 2, self.words["gap_unit"], FA_TEXT, 36, th.ink, "rs", "rtl")

    # ── S9: where the heat went ──

    def ocean(self, c: Canvas, t: float, dt: float):
        th = self.th
        c.text(RIGHT, HEAT_Y - 24, self.words["heat_title"], FA_BOLD, 44, th.ink, "rs", "rtl")
        x = RIGHT                                               # the 100 % bar, right to left
        cols = ("#2a78d6", "#B89B72", "#9FC4E0", "#E2D8C8")
        f = 1.0 if not np.isfinite(dt) else min(max((dt - 0.8) / 1.0, 0.0), 1.0)
        f = f * f * (3 - 2 * f)
        for (name, pct), col in zip(HEAT, cols):
            w = (RIGHT - LEFT) * pct / 100 * f
            c.fill(x - w, HEAT_Y, x, HEAT_Y + HEAT_H, col)
            x -= w
        c.frame(LEFT, HEAT_Y, RIGHT, HEAT_Y + HEAT_H, colour=th.ink)
        if f >= 1.0:
            c.text(RIGHT - 24, HEAT_Y + 66, fa("اقیانوس ۹۱٪"), FA_BOLD, 56, th.paper, "rs", "rtl")
            small = "خشکی ۵٪ · یخ ۳٪ · هوا ۱٪"
            c.text(LEFT, HEAT_Y + HEAT_H + 52, fa(small), FA_TEXT, 40, th.ink, "ls", "rtl")
        # the heat-capacity comparison: the whole air above the land and sea, against 3.5 m of sea water
        if np.isfinite(dt) and dt < 2.6:
            return
        top, bot = COL_Y0, COL_Y1 - 60
        ax0, ax1 = RIGHT - 300, RIGHT - 140                     # the air: a tall column, at the right
        sx0, sx1 = LEFT + 100, LEFT + 340                       # the sea: a thin slab, at the left
        c.fill(ax0, top, ax1, bot, "#D6E4EE")
        c.frame(ax0, top, ax1, bot, colour=th.ink)
        c.fill(sx0, bot - 22, sx1, bot, "#2a78d6")
        c.frame(sx0, bot - 22, sx1, bot, colour=th.ink)
        for k, line in enumerate(self.words["col_air"]):
            c.text((ax0 + ax1) / 2, bot + 50 + 44 * k, line, FA_BOLD, 38, th.ink, "ms", "rtl")
        for k, line in enumerate(self.words["col_sea"]):
            c.text((sx0 + sx1) / 2, bot + 50 + 44 * k, line, FA_BOLD, 38, th.ink, "ms", "rtl")
        assert (sx0 + sx1) / 2 + c.width(self.words["col_sea"][1], FA_BOLD, 38, "rtl") / 2 + 30 < \
            (ax0 + ax1) / 2 - c.width(self.words["col_air"][1], FA_BOLD, 38, "rtl") / 2, "the two labels touch"
        c.text(560, (top + bot) / 2 + 30, "=", FA_BOLD, 110, th.mark, "ms")
        c.text(MIDX, top - 24, self.words["col_eq"], FA_TEXT, 38, th.ink, "ms", "rtl")
        c.text(MIDX, bot + 160, self.words["col_deep"], FA_TEXT, 38, th.ink, "ms", "rtl")

    # ── S9: the answer (the narrated reel's) ──

    def answer(self, c: Canvas, t: float, dt: float):
        th = self.th
        i = len(self.S.scenes) - 1
        rec = self.words["recap"]
        reveal = self.appear(i)[-1] + s26.REVEAL_GAP
        if np.isfinite(dt) and dt < reveal:
            return
        question = self.words["question"].split(" // ")
        c.text(RIGHT, 602, self.words["note"], FA_TEXT, LABEL, th.ink, "rs", "rtl")
        c.text(MIDX, 860, rec[0], FA_BOLD, 96, th.ink, "ms", "rtl")

        def fit(line: str, size: int, limit: float) -> int:
            while c.width(line, FA_BOLD, size, "rtl") > limit and size > 52:
                size -= 2
            return size
        c.text(MIDX, 960, rec[1], FA_BOLD, fit(rec[1], 72, 2 * (RIGHT - MIDX) - 20), th.ink, "ms", "rtl")
        c.text(MIDX, 1070, rec[2], FA_BOLD, fit(rec[2], 64, 2 * (RIGHT - MIDX) - 20), th.ink, "ms", "rtl")
        c.frame(LEFT + 60, 1160, RIGHT - 60, 1470, colour=th.ink)
        for k, line in enumerate(question):
            c.text(MIDX, 1248 + 88 * k, line, FA_BOLD, 72, th.ink, "ms", "rtl")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="kahgel", choices=["kahgel"], help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and stills only, no video")
    ap.add_argument("--at", type=float, nargs="*", help="stills at these times only")
    args = ap.parse_args()
    film = ElNino26xFilm(onebit.THEMES[args.theme], COLOURS[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / BASE
    film.draw(1, COVER_T).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills or args.at:
        times = args.at or sorted({0.0} | {round(float(film.starts[i] + f * (film.starts[i + 1] - film.starts[i])), 2)
                                           for i in range(len(SECONDS)) for f in (0.35, 0.95)})
        for old in (OUT / "social").glob(f"{BASE}_t*.png"):
            old.unlink()
        for t in times:
            film.draw(1, t).save(f"{base}_t{t:05.2f}.png")
            print("saved", f"{base}_t{t:05.2f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
