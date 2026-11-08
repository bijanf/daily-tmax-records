"""EL NIÑO, VERSION B: THE SELF-DESCRIBING REEL OF THE NOAH'S-FLOOD HOOK, in the five-dam grammar (iran_elnino26s_fa).

Five bars of 60 BPM, 27.5 s: S1 0-4.5 s the hook (the tropical Pacific, the week's warm water, the ONI bar); S2
[1/3] 4.5-10.5 s the 26 autumns, one drop each; S3 [2/3] 10.5-16 s the Iran map and the autumn rain bar (74 mm
against the mean of 60); S4 [3/3] 16-21 s the 22 winters; S5 21-27.5 s the answer and the question. Measured data only,
no forecast. Every number comes from src/elnino26s.py (asserted there and read back from numbers.json here).

The Pacific (S1): the tropical Pacific from 120 E to 80 W, 30 S to 30 N, equirectangular, the Blue Marble darkened
and tinted where NOAA OISST v2.1's daily anomaly (vs 1991-2020), averaged over 17-23 October 2026, is at least +1.5 °C
(orange to red: the colours of src/elnino26_3d.py's WARM table; its alpha is raised to 0.5 at the threshold so the
edge reads). The Niño-3.4 box (5 N-5 S, 170 W-120 W) is outlined. The Iran map and its colour bar are onebit_elnino2's.

The engine: onebit_elnino2.py (the cream remake: the drops, the appear() whole-headline override, the honest map,
the colour of the map, the sprites) and onebit_slides.py (the window, the progress bar, the title), imported.

    outputs/onebit/social/elnino26s_fa_reel.mp4 (silent master), elnino26s_fa_cover.png (frame 0), _t<sec>.png (stills)

    python -I src/onebit_elnino26s.py              # the silent reel and the cover
    python -I src/onebit_elnino26s.py --stills     # the cover and the stills of the iterations
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import warnings  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from scipy import ndimage  # noqa: E402

import elnino26s as num  # noqa: E402
import enso  # noqa: E402
import onebit  # noqa: E402
import onebit_elnino2 as el2  # noqa: E402  (the drops, the map's colours, the sprites: imported, not copied)
from onebit import FA_BOLD, FA_TEXT, OUT, PIXEL, SIZES, SOCIAL_CRF, TEXT, Canvas, fa, title  # noqa: E402
from onebit_slides import COLOURS, LEFT, RIGHT, WIN, Slides  # noqa: E402

BASE = "elnino26s_fa"
AUTUMN, WINTER = "OND", "JFM"
PACE = dict(bpm=60, bars=(1.125, 1.5, 1.375, 1.25, 1.625))     # 4.5, 6, 5.5, 5, 6.5 s: 27.5 s
END = 27.5
BARH = 64                                          # px: the title bar of the window
RULE_Y = 664                                       # px: the rule under the headline (as onebit_elnino2)
SOURCE_Y = 1540                                    # px: the sources' baseline, clear of the bottom UI band
DROP_TOP = 748                                     # px: centre of the first row of drops
ROW_PITCH = 112
PER_ROW = {AUTUMN: 9, WINTER: 8}
CELL = el2.CELL
DROP = el2.DROP
WET_T0 = {AUTUMN: 1.0, WINTER: 0.8}                # s into a scene: the first drop turns
WET_SPAN = {AUTUMN: 3.6, WINTER: 3.2}              # s: the drops turn over this span
COUNT_T = {AUTUMN: 5.0, WINTER: 4.5}               # s into a scene: the count is written
# the Pacific: 120 E to 80 W (the box of elnino26s), its pixels on the film's map
PAC_BOX = (120.0, 280.0, -30.0, 30.0)
PAC_W, PAC_H = RIGHT - LEFT, 311                   # px: 828 wide, 160 deg at 5.175 px a degree
PAC_Y = 700                                        # px: the map's top
KEY_Y = 1040                                       # px: the colour key's top (the warm scale 1.5 to 5)
KEY_LO, KEY_HI = 1.5, 5.0                          # °C: the tint's scale (WARM's ends)
TINT_MIN_ALPHA = 0.5                               # the threshold edge: at 1.5 °C the tint is this opaque, not 0
WARM = np.array([(1.5, 255, 200, 70, 0.0), (2.0, 255, 170, 50, 0.55), (3.0, 250, 110, 35, 0.8),
                 (4.0, 235, 45, 45, 0.9), (5.0, 205, 20, 100, 0.95)])   # elnino26_3d.py's WARM, unchanged
OCEAN_DARK = np.array([8.0, 21.0, 38.0])           # the darkened ocean's colour, for the key's blend
BAR_SCALE = (0.0, 3.0)                             # °C: the ONI bar runs from 0 to 3
RAIN_MEAN_AT = 0.62                                # the autumn rain bar: the mean at 62 % of the width
MAP_H3 = 400                                       # px: the Iran map's height on S3
MAP_Y3 = 700
COLOUR3_Y = 1130                                   # px: the Iran colour bar's top on S3
BAR_Y, BAR_H = 1340, 44
UNIT = 44                                          # px: the unit and tick labels (floor 44)
SOURCE = 42                                        # px: the sources line (44 px does not fit its one line)
LABEL = 48                                         # px: the key and labels (floor 48)
GROW = 1.0                                         # s: a bar grows once, then holds
ONI_T0 = -1.0                                      # s: the ONI bar is full at frame 0 (the cover shows the answer)
RAIN_T0 = 10.5 + 0.3                               # s: the rain bar starts to grow (scene 3)
REVEAL_GAP = 0.2                                   # s: the answer appears this long after its verdict is typed
PAC_LABEL = "اقیانوسِ آرام"
NINO_LABEL = "ناحیه‌ی نینو ۳٫۴"
WET_LABEL = "میانگین ۶۰"

def fa_dec(x: float) -> str:
    """A decimal as Persian digits with the decimal separator «٫»."""
    return fa(f"{x:.1f}").replace(".", "٫")


def words(d: dict) -> dict:
    """The five scenes (bold line, key line), the lines of the answer, the sources and the legends. d: derived()."""
    a_n, a_m, w_n, w_m, pct = d["a_n"], d["a_m"], d["w_n"], d["w_m"], d["pct"]
    return dict(
        scenes=(("ال‌نینوی قوی آمده؛ // یعنی طوفانِ نوح؟", f"{PAC_LABEL}: یکی از قوی‌ترین‌ها از ۱۹۵۰"),
                (f"پاییز: {{{fa(a_n)} از {fa(a_m)}}} // ال‌نینو پرباران‌تر از معمول",
                 "اکتبر تا دسامبر؛ هر قطره یک پاییزِ ال‌نینو"),
                (f"پاییزِ ال‌نینو: {{{fa(pct)}٪}} میانگین",
                 f"{fa(a_m)} پاییزِ ال‌نینو در برابرِ همه‌ی {fa(d['n_all'])} پاییز"),
                (f"زمستان: {{{fa(w_n)} از {fa(w_m)}}} // نیمی پرباران‌تر، نیمی نه",
                 "ژانویه تا مارس؛ مثلِ شیر یا خط"),
                ("شانسِ پاییزِ پرباران بیشتر بوده؛ // نه طوفانِ نوح", "این پیش‌بینی نیست.")),
        note="درباره‌ی ال‌نینوهای ۱۹۵۱ تا ۲۰۲۴ است",
        recap=(f"پاییز: {fa(a_n)} از {fa(a_m)}", f"میانگینِ پاییز: {fa(pct - 100)}٪ بیشتر",
               f"زمستان: {fa(w_n)} از {fa(w_m)}؛ نیمی پرباران‌تر"),
        question="پاییزِ امسال // در شهرِ شما // چطور بوده؟",
        sources="ONI · OISST · CRU TS 4.10 · Blue Marble",
        legend=("توپُر: بیش از معمولِ ۱۹۵۱–۲۰۲۴", "خالی: کم‌بارش‌تر از معمول"),
        scale=("۱۰۰٪", "۱۱۰٪", "۱۲۰٪", "۱۳۰٪", "۱۴۰٪", "۱۵۰٪"),
        unit="درصدِ میانگینِ پاییزِ ۱۹۵۱–۲۰۲۴ (۱۰۰٪)",
        pac_key=("درجه‌ی سلسیوس گرم‌تر از معمول", "هفته‌ی ۲۵ مهر تا ۱ آبانِ ۱۴۰۵"),
        pac_ticks=("۱٫۵", "۲", "۳", "۴", "۵"),
        dam_marks=(("ال‌نینو", 0.5), ("قوی", 1.5)),
        dam_unit=("درجه گرم‌تر از معمول؛ شاخصِ ONI", "میانگینِ سه‌ماهه‌ی مرداد تا مهرِ ۱۴۰۵"),
        rain_unit="میلی‌متر بارانِ پاییز، کلِ ایران",
    )


class ElNino26sFilm(Slides):
    def __init__(self, th: onebit.Theme, colour: dict):
        self.nums = json.loads((num.DATA / "numbers.json").read_text(encoding="utf-8"))
        self.res = {s: enso.result(s) for s in (AUTUMN, WINTER)}
        self.check_data()
        self.words = words(self.derived())
        self.setup(th, "fa", colour, self.words, PACE, "ElNino.Iran")
        self.hook_at_once = True
        self.th = th
        self.comp = el2.composite()
        self.map_w, self.map_h = self.geometry3()
        self.iran = self.make_iran()
        self.pac = self.make_pacific()
        self.key_pac = self.make_key()
        self.sprites = {k: el2.ElNino2Film.sprite(self, k) for k in ("pale", "wet", "dry")}
        self.check_layout()

    def derived(self) -> dict:
        """The counts the words use, read from enso (asserted against numbers.json in check_data)."""
        a, w = self.res[AUTUMN], self.res[WINTER]
        return dict(a_n=a["n_wetter"], a_m=len(a["years"]), w_n=w["n_wetter"], w_m=len(w["years"]),
                    pct=self.nums["iran_pct_text"], n_all=self.nums["iran_n_all"])

    # ── checks: every number on screen is asserted here, against enso and numbers.json ──

    def check_data(self) -> None:
        n = self.nums
        a, w = self.res[AUTUMN], self.res[WINTER]
        assert (a["n_wetter"], len(a["years"])) == (21, 26) and (w["n_wetter"], len(w["years"])) == (11, 22)
        assert (n["iran_n_wetter"], len(n["iran_autumn_years"])) == (21, 26), "numbers.json and enso disagree"
        assert n["oni_shown"] == 2.5 and n["oni_rank"] == 1 and n["roni_rank"] == 2 and n["n_aso"] == 77
        assert n["iran_pct_text"] == 123 and round(n["iran_mm_el"]) == 74 and round(n["iran_mean74"]) == 60
        assert n["iran_wettest"] == 1982 and n["iran_wettest_mm"] == 114 and n["iran_wettest_is_el"]
        assert round(n["iran_yearly"]) == 226 and n["iran_share_pct"] == 27 and n["iran_n_all"] == 74
        assert n["iran_rand_ge"] == 0 and round(n["iran_rand_lo"]) == 90 and round(n["iran_rand_hi"]) == 111
        assert n["strong_autumn"] == 4 and n["strong_autumn_n"] == 6
        assert n["week"]["days"] == ["2026-10-17", "2026-10-23"] and n["week"]["tint_at"] == 1.5
        assert n["week"]["tinted_cells"] > 0
        assert fa(n["iran_n_all"]) == "۷۴" and fa(n["iran_pct_text"]) == "۱۲۳"
        assert abs(n["iran_mean74"] - 60.0) < 0.05 and abs(n["iran_mm_el"] - 73.9) < 0.05
        assert abs(n["oni"] - 2.46) < 1e-9 and n["iran_p_autumn"] == 0.001
        assert enso.THRESHOLD == 0.5

    def check_layout(self) -> None:
        for s in (AUTUMN, WINTER):
            n = len(self.res[s]["years"])
            rows = math.ceil(n / PER_ROW[s])
            assert DROP_TOP + ROW_PITCH * (rows - 1) + CELL * len(DROP) / 2 < 1200, s
        assert RULE_Y + 30 < DROP_TOP - CELL * len(DROP) / 2 + 20
        assert PAC_Y + PAC_H < KEY_Y - 10 and KEY_Y + 124 + 88 + 20 < BAR_Y - 60, "the key runs into the dam bar"
        assert MAP_Y3 + self.map_h < COLOUR3_Y - 20, "the Iran map runs into its colour bar"
        assert COLOUR3_Y + 124 + UNIT < BAR_Y - 40, "the colour bar's unit runs into the rain bar"

    # ── geometry ──

    def geometry3(self) -> tuple:
        w, e, s, n = el2.MAP_BOX
        km_w = (e - w) * math.cos(math.radians((s + n) / 2))
        return round(MAP_H3 * km_w / (n - s)), MAP_H3

    # ── the Pacific: the Blue Marble, darkened, tinted where the week's anomaly is at least +1.5 °C ──

    def make_pacific(self) -> Image.Image:
        g = num.week_grid()
        lat, lon, m = g["lat"], g["lon"], g["mean"]
        ocean = np.isfinite(m)
        idx = ndimage.distance_transform_edt(~ocean, return_distances=False, return_indices=True)
        filled = m[tuple(idx)]
        bm = num.blue_marble()
        base = Image.open(bm).convert("RGB").resize((PAC_W, PAC_H), Image.LANCZOS)
        base = np.asarray(base, float) * 0.42
        lon0, lon1, lat0, lat1 = PAC_BOX
        lon_d = lon0 + (np.arange(PAC_W) + 0.5) / PAC_W * (lon1 - lon0)
        lat_d = lat1 - (np.arange(PAC_H) + 0.5) / PAC_H * (lat1 - lat0)
        LON, LAT = np.meshgrid(lon_d, lat_d)
        dlat, dlon = lat[1] - lat[0], lon[1] - lon[0]
        iy = (LAT - lat[0]) / dlat
        ix = (LON - lon[0]) / dlon
        val = ndimage.map_coordinates(filled, [iy, ix], order=1, mode="nearest")
        wet = ndimage.map_coordinates(ocean.astype(float), [iy, ix], order=0, mode="nearest") > 0.5
        hot = wet & (val >= num.TINT_AT)
        rgb, alpha = self.warm(val)
        alpha = np.maximum(alpha, TINT_MIN_ALPHA)
        out = base.copy()
        out[hot] = (1 - alpha[hot][:, None]) * base[hot] + alpha[hot][:, None] * rgb[hot]
        # the Niño-3.4 box, thin, in paper
        bx0, bx1 = 190.0, 240.0
        by0, by1 = 5.0, -5.0
        X0, X1 = (bx0 - lon0) / (lon1 - lon0) * PAC_W, (bx1 - lon0) / (lon1 - lon0) * PAC_W
        Y0, Y1 = (lat1 - by0) / (lat1 - lat0) * PAC_H, (lat1 - by1) / (lat1 - lat0) * PAC_H
        self.nino_box = (LEFT + X0, LEFT + X1, PAC_Y + Y0, PAC_Y + Y1)
        im = Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8))
        arr = np.asarray(im).copy()
        for xx in range(int(round(X0)), int(round(X1)) + 1):
            for yy in (int(round(Y0)), int(round(Y1))):
                arr[yy, xx] = el2.MID
        for yy in range(int(round(Y0)), int(round(Y1)) + 1):
            for xx in (int(round(X0)), int(round(X1))):
                arr[yy, xx] = el2.MID
        self.week_anom = dict(val=val, hot=int(hot.sum()), total=PAC_W * PAC_H)
        return Image.fromarray(arr)

    def warm(self, v: np.ndarray) -> tuple:
        """The WARM table's colour and alpha at each value (clipped to the table's ends)."""
        x = np.clip(v, WARM[0, 0], WARM[-1, 0])
        rgb = np.stack([np.interp(x, WARM[:, 0], WARM[:, k]) for k in (1, 2, 3)], -1)
        alpha = np.interp(x, WARM[:, 0], WARM[:, 4])
        return rgb, alpha

    def make_key(self) -> Image.Image:
        """The warm key: the tint's colour over the darkened ocean at 1.5 to 5 °C, one strip."""
        n = 400
        v = np.linspace(KEY_LO, KEY_HI, n)
        rgb, alpha = self.warm(v)
        alpha = np.maximum(alpha, TINT_MIN_ALPHA)
        col = (1 - alpha[:, None]) * OCEAN_DARK[None, :] + alpha[:, None] * rgb
        return Image.fromarray(np.repeat(np.clip(col, 0, 255).astype(np.uint8)[None], 40, axis=0))

    # ── the Iran map: onebit_elnino2's honest map (the composite, the Blue Marble of Iran), smaller ──

    def make_iran(self) -> Image.Image:
        from scipy.ndimage import binary_erosion, binary_dilation, distance_transform_edt, map_coordinates
        w_, e_, s_, n_ = el2.MAP_BOX
        W, H = self.map_w, self.map_h
        bm = onebit.ROOT / "data" / "air" / "bluemarble_srb_iran.jpg"
        assert bm.exists(), bm
        step, lon0, lat0 = 0.005, 42.0, 45.5
        box = (round((w_ - lon0) / step), round((lat0 - n_) / step), round((e_ - lon0) / step),
               round((lat0 - s_) / step))
        base = Image.open(bm).convert("RGB").crop(box).resize((W, H), Image.LANCZOS)
        base = np.asarray(base, float) * 0.42
        lon_d = w_ + (np.arange(W) + 0.5) / W * (e_ - w_)
        lat_d = n_ - (np.arange(H) + 0.5) / H * (n_ - s_)
        LON, LAT = np.meshgrid(lon_d, lat_d)
        pct = self.comp["pct"]
        idx = distance_transform_edt(np.isnan(pct), return_distances=False, return_indices=True)
        filled = pct[tuple(idx)]
        lat_c, lon_c = self.comp["lat"], self.comp["lon"]
        dlat, dlon = lat_c[1] - lat_c[0], lon_c[1] - lon_c[0]
        iy = (lat_c[0] - LAT) / dlat if dlat < 0 else (LAT - lat_c[0]) / dlat
        ix = (LON - lon_c[0]) / dlon
        up = map_coordinates(filled, [iy, ix], order=1, mode="nearest")
        mask = enso.iran_mask(LAT, LON)
        edge = mask & ~binary_erosion(mask, iterations=1)
        rgb = el2.colour_of(up)
        out = base.copy()
        out[mask] = 0.12 * base[mask] + 0.88 * rgb[mask]
        out[binary_dilation(edge, iterations=2)] = np.array(el2.MID, float)
        return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8))

    # ── time ──

    def appear(self, i: int) -> list:
        """The whole headline in 1.6 s after the hook (the hook whole at frame 0), as in onebit_elnino2."""
        if i == 0:
            return super().appear(i)
        ws = [w for w, _ in onebit.words_of(self.S.scenes[i].title, self.th)]
        n = len(ws) - ws.count("//")
        return [0.3 + 1.6 * k / n for k in range(n)]

    def turn(self, season: str, k: int) -> float:
        return WET_T0[season] + k * WET_SPAN[season] / len(self.res[season]["years"])

    # ── drawing ──

    def window(self, c: Canvas, i: int):
        th = self.th
        x, y, w, h = WIN
        c.frame(x, y, x + w, y + h, fill=th.paper)
        c.fill(x, y, x + w, y + BARH, th.ink)
        c.frame(x + 3, y + BARH + 3, x + w - 3, y + h - 3)
        c.text(x + 14, y + BARH - 14, self.app, PIXEL, 48, th.title)
        if i in (1, 2, 3):
            c.text(x + w - 14, y + BARH - 14, f"[{i}/3]", PIXEL, 48, th.title, "rs")
        c.fill(x + 3, RULE_Y, x + w - 3, RULE_Y + 2, th.ink)

    def sources(self, c: Canvas):
        s = self.words["sources"]
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
              sizes=((68, 92), (64, 86)), motion=False, line_at=at[-1] + 0.6, small=LABEL)
        self.body(c, t)
        self.sources(c)
        return c.im

    def body(self, c: Canvas, t: float):
        i = self.scene(t)
        if i == 0:
            self.pacific(c, t)
        elif i in (1, 3):
            self.drops(c, t, i)
        elif i == 2:
            self.iran_scene(c, t)
        else:
            self.answer(c, t)

    # ── scene 1: the Pacific and the ONI bar ──

    def pacific(self, c: Canvas, t: float):
        th = self.th
        c.im.paste(self.pac, (LEFT, PAC_Y))
        c.frame(LEFT - 1, PAC_Y - 1, RIGHT + 1, PAC_Y + PAC_H + 1, colour=th.ink)
        x0, x1, y0, y1 = self.nino_box
        lw = c.width(NINO_LABEL, FA_TEXT, LABEL, "rtl")
        lx = min(max((x0 + x1) / 2, LEFT + lw / 2 + 8), RIGHT - lw / 2 - 8)
        c.frame(lx - lw / 2 - 8, y0 - 60, lx + lw / 2 + 8, y0 - 14, fill=th.paper)
        c.text(lx, y0 - 26, NINO_LABEL, FA_TEXT, LABEL, th.ink, "ms", "rtl")
        c.frame(RIGHT - c.width(PAC_LABEL, FA_TEXT, LABEL, "rtl") - 30, PAC_Y + PAC_H - 62,
                RIGHT - 8, PAC_Y + PAC_H - 12, fill=th.paper)
        c.text(RIGHT - 19, PAC_Y + PAC_H - 24, PAC_LABEL, FA_TEXT, LABEL, th.ink, "rs", "rtl")
        # the colour key: 1.5 to 5 °C, ticks, the unit and the week
        bx0, bx1, by = LEFT, RIGHT, KEY_Y
        c.im.paste(self.key_pac.resize((round(bx1 - bx0), 30), Image.BILINEAR), (c.X(bx0), c.Y(by)))
        c.frame(bx0, by, bx1, by + 30, colour=th.ink)
        for v, lab in zip((1.5, 2.0, 3.0, 4.0, 5.0), self.words["pac_ticks"]):
            xv = bx0 + (v - KEY_LO) / (KEY_HI - KEY_LO) * (bx1 - bx0)
            c.fill(xv - 1, by + 30, xv + 1, by + 40, th.ink)
            c.text(xv, by + 78, lab, FA_TEXT, UNIT, th.ink, "ms", "rtl")
        for k, line in enumerate(self.words["pac_key"]):
            c.text(RIGHT, by + 124 + 44 * k, line, FA_TEXT, UNIT, th.ink, "rs", "rtl")
            assert c.width(line, FA_TEXT, UNIT, "rtl") <= RIGHT - LEFT, line
        # the ONI bar: 2.5 against the marks of El Niño (0.5) and of a strong one (1.5)
        self.oni_bar(c, t)

    def oni_bar(self, c: Canvas, t: float):
        th = self.th
        lo, hi = BAR_SCALE
        xv = lambda v: LEFT + (v - lo) / (hi - lo) * (RIGHT - LEFT)
        p = 1.0 if not np.isfinite(t) else min(max((t - ONI_T0) / GROW, 0.0), 1.0)
        p = p * p * (3 - 2 * p)
        val = self.nums["oni"] * p
        c.fill(LEFT, BAR_Y, xv(val), BAR_Y + BAR_H, th.mark)
        c.frame(LEFT, BAR_Y, RIGHT, BAR_Y + BAR_H, colour=th.ink)
        for lab, v in self.words["dam_marks"]:
            x = xv(v)
            for yy in range(BAR_Y - 14, BAR_Y + BAR_H + 14, 10):
                c.fill(x - 2, yy, x + 2, yy + 6, th.ink)
            c.text(x, BAR_Y - 26, lab, FA_TEXT, LABEL, th.ink, "ms", "rtl")
        if p > 0.5:
            c.text(xv(val) + 14, BAR_Y + BAR_H - 6, fa_dec(self.nums["oni_shown"]), FA_BOLD, LABEL, th.ink, "ls")
        c.text(LEFT, BAR_Y - 26, fa(0), FA_TEXT, UNIT, th.ink, "ls")
        c.text(RIGHT, BAR_Y - 26, fa(int(hi)), FA_TEXT, UNIT, th.ink, "rs")
        for k, line in enumerate(self.words["dam_unit"]):
            c.text(RIGHT, BAR_Y + BAR_H + 56 + 44 * k, line, FA_TEXT, UNIT, th.ink, "rs", "rtl")
            assert c.width(line, FA_TEXT, UNIT, "rtl") <= RIGHT - LEFT, line

    # ── scene 2 and 4: the drops (onebit_elnino2's, with this film's timing) ──

    def drops(self, c: Canvas, t: float, i: int):
        th = self.th
        season = AUTUMN if i == 1 else WINTER
        r = self.res[season]
        flags = [bool(r["wetter"][y]) for y in r["years"]]
        n = len(flags)
        dt = t - self.starts[i] if np.isfinite(t) else np.inf
        per = PER_ROW[season]
        pitch = (RIGHT - LEFT) / per
        for k, wet in enumerate(flags):
            row, col = divmod(k, per)
            cx = RIGHT - pitch / 2 - col * pitch
            cy = DROP_TOP + row * ROW_PITCH
            turned = np.isfinite(dt) and dt >= self.turn(season, k)
            kind = ("wet" if wet else "dry") if turned else "pale"
            sp = self.sprites[kind]
            c.im.paste(sp, (c.X(cx - CELL * len(DROP) / 2), c.Y(cy - CELL * len(DROP) / 2)), sp)
        counted = np.isfinite(dt) and dt >= COUNT_T[season]
        c.text(540, 1196, f"{fa(sum(flags))} از {fa(n)}", FA_BOLD, 120, th.ink if counted else th.paper, "ms", "rtl")
        ly = 1282
        for k, (kind, lab) in enumerate((("wet", self.words["legend"][0]), ("dry", self.words["legend"][1]))):
            y = ly + k * 66
            sp = self.sprites[kind]
            c.im.paste(sp.resize((40, 40), Image.NEAREST), (c.X(RIGHT - 40), c.Y(y - 34)),
                       sp.resize((40, 40), Image.NEAREST))
            c.text(RIGHT - 60, y, lab, FA_TEXT, LABEL, th.ink, "rs", "rtl")

    # ── scene 3: the Iran map, its colour bar, the autumn rain bar ──

    def iran_scene(self, c: Canvas, t: float):
        th = self.th
        x0 = (1080 - self.map_w) // 2
        c.im.paste(self.iran, (x0, MAP_Y3))
        c.frame(x0 - 1, MAP_Y3 - 1, x0 + self.map_w + 1, MAP_Y3 + self.map_h + 1, colour=th.ink)
        bx0, bx1, by = LEFT + 40, RIGHT - 40, COLOUR3_Y
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
        c.text(540, by + 124, self.words["unit"], FA_TEXT, UNIT, th.ink, "ms", "rtl")
        assert c.width(self.words["unit"], FA_TEXT, UNIT, "rtl") <= RIGHT - LEFT
        self.rain_bar(c, t)

    def rain_bar(self, c: Canvas, t: float):
        th = self.th
        mean = self.nums["iran_mean74"]
        el = self.nums["iran_mm_el"]
        top = mean / RAIN_MEAN_AT                          # the scale's end: the mean sits at 70 % of the width
        xv = lambda v: LEFT + v / top * (RIGHT - LEFT)
        p = 1.0 if not np.isfinite(t) else min(max((t - RAIN_T0) / GROW, 0.0), 1.0)
        p = p * p * (3 - 2 * p)
        v = el * p
        y = BAR_Y
        c.fill(LEFT, y, xv(v), y + BAR_H, th.mark)
        c.frame(LEFT, y, RIGHT, y + BAR_H, colour=th.ink)
        xm = xv(mean)
        for yy in range(y - 12, y + BAR_H + 10, 12):
            c.fill(xm - 2, yy, xm + 2, yy + 7, th.ink)
        lab = fa(f"میانگین {round(mean)}")
        c.text(min(max(xm, LEFT + 150), RIGHT - 150), y - 22, lab, FA_TEXT, LABEL, th.ink, "ms", "rtl")
        if p > 0.5:
            c.text(xv(v) + 14, y + BAR_H - 6, fa(round(el)), FA_BOLD, LABEL, th.ink, "ls")
        c.text(LEFT, y - 22, fa(0), FA_TEXT, UNIT, th.ink, "ls")
        c.text(RIGHT, y - 22, fa(round(top)), FA_TEXT, UNIT, th.ink, "rs")
        c.text(RIGHT, y + BAR_H + 56, self.words["rain_unit"], FA_TEXT, UNIT, th.ink, "rs", "rtl")
        assert c.width(self.words["rain_unit"], FA_TEXT, UNIT, "rtl") <= RIGHT - LEFT

    # ── scene 5: the answer ──

    def answer(self, c: Canvas, t: float):
        """The answer waits until the verdict is typed: the note, the recap and the question appear together."""
        th = self.th
        dt = t - self.starts[4]
        rec = self.words["recap"]
        reveal = self.appear(4)[-1] + REVEAL_GAP
        shown = (not np.isfinite(dt)) or dt >= reveal
        question = self.words["question"].split(" // ")
        assert c.width(self.words["note"], FA_TEXT, LABEL, "rtl") <= RIGHT - LEFT
        for line in question:
            assert c.width(line, FA_BOLD, 72, "rtl") <= (RIGHT - 60) - (LEFT + 60) - 60, line
        if not shown:
            return
        c.text(RIGHT, 602, self.words["note"], FA_TEXT, LABEL, th.ink, "rs", "rtl")
        c.text(540, 860, rec[0], FA_BOLD, 96, th.ink, "ms", "rtl")
        def fit(line: str, size: int, limit: float) -> int:
            """The largest size from `size` down to 52 px at which a centred line stays inside `limit` px."""
            while c.width(line, FA_BOLD, size, "rtl") > limit and size > 52:
                size -= 2
            assert c.width(line, FA_BOLD, size, "rtl") <= limit, line
            return size
        # centred on x 540: the content edge is RIGHT, and below y 1000 nothing may come within 150 px of the edge (x 930)
        c.text(540, 960, rec[1], FA_BOLD, fit(rec[1], 72, 2 * (RIGHT - 540) - 20), th.ink, "ms", "rtl")
        c.text(540, 1070, rec[2], FA_BOLD, fit(rec[2], 64, 2 * (930 - 540) - 20), th.ink, "ms", "rtl")
        c.frame(LEFT + 60, 1160, RIGHT - 60, 1470, colour=th.ink)
        for k, line in enumerate(question):
            c.text(540, 1248 + 88 * k, line, FA_BOLD, 72, th.ink, "ms", "rtl")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="kahgel", choices=["kahgel"], help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and stills only, no video")
    args = ap.parse_args()
    film = ElNino26sFilm(onebit.THEMES[args.theme], COLOURS[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / BASE
    film.draw(1, 0.0).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        for t in (0.0, 3.0, 8.0, 13.0, 18.0, 24.0, 27.0):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
