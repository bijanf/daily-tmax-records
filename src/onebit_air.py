"""WINTER NO2 OVER IRAN, FROM SPACE: the tropospheric NO2 column that Sentinel-5P sees over the whole country, the
winter of 1404 (Azar to Bahman) against the summer (Tir to Shahrivar 1405), the twelve Jalali months in between.

A static camera on Iran: a darkened hillshaded relief (Copernicus GLO-30 tiles on a 0.04-degree grid, coarse by
design), the border as a thin line, the NO2 field as the glow in one colour scale for every month.

Measured data only, from air.py (the granules of get_air.py, the full Iran box, valid pixels qa >= 0.75):
  the counter is the Tehran-Karaj box's month mean over the summer reference (Tir to Shahrivar 1405, pooled);
  the held counter is the same box's Azar-Bahman 1404 mean over that reference (asserted: 3.36, shown as x3).

    0.0 s         the Azar-Bahman 1404 field over Iran, the hook and the held counter
    1.0-9.46 s    the Jalali months Aban 1404 to Mehr 1405 at 1.3 months a second; the counter is that month
    9.46-10.06 s  the turn back to the Azar-Bahman field
    10.6-19.06 s  the months again, from Aban 1404 to Mehr 1405
    19.06-19.66 s the turn back; from about 20 s the Azar-Bahman field is held to the end, the counter held

Colour: one scale for all months (VMIN..VMAX, GAMMA), the same function for the glow and the legend.

    python -I src/onebit_air.py              # the film (the video is rendered by the driver)
    python -I src/onebit_air.py --stills     # the cover and the stills, no video
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

import air  # noqa: E402
import onebit  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, SIZES, SOCIAL_CRF, fa  # noqa: E402

W, H = air.W, air.H
DURATION = 24.0                                  # s
RATE = 1.3                                       # months a second
PASS_LEN = 11 / RATE                             # s: Aban 1404 to Mehr 1405 (twelve months, eleven steps)
DIAL_STARTS = (1.0, 10.6)                        # s: the months play twice, from Aban 1404 each time
TURN = 0.6                                       # s: back to the Azar-Bahman field after each pass
FADE = 0.4                                       # s: the glow comes in from the Azar-Bahman field at each start
TURNS = tuple(s + PASS_LEN for s in DIAL_STARTS) # s: the start of each turn (Mehr 1405 each time)
DIAL_END = TURNS[-1]                             # s: the end of the second pass (Mehr 1405)
HOLD = DIAL_END + TURN                           # s: the Azar-Bahman field is held from here to the end (about 20 s)
VMIN, VMAX, GAMMA = 2.0, 60.0, 0.5               # 1e15 molec/cm2: one scale for the map, the glow and the bar: sqrt((v-2)/58)
ORANGE = np.array([255, 120, 30], np.float32)
HOT = np.array([255, 214, 140], np.float32)
PAPER, SHADOW, AMBER = (250, 246, 238, 255), (8, 10, 14, 255), (255, 150, 60, 255)
MONTHS = air.DIAL_JK                             # Aban 1404 to Mehr 1405 (Jalali keys "YYYY-MM")
BLOOM_PX = 3.0                                   # px: the glow's halo at this scale
# the country view: Iran's grid on the frame, Iran's width about 980 px, Tehran in the upper middle
VIEW = dict(lon=53.65, lat=32.5, yA=700.0, km=1.945)
CITIES = (("تهران", 51.39, 35.69), ("مشهد", 59.61, 36.30), ("اصفهان", 51.67, 32.65), ("تبریز", 46.29, 38.08),
          ("شیراز", 52.53, 29.59), ("اهواز", 48.67, 31.32))
TITLE = ("زمستان، ایران از فضا:", "دی‌اکسیدِ نیتروژن کجا جمع می‌شود؟")
SOURCES = "منبع: Sentinel-5P (ESA/Copernicus)؛ ارتفاع: Copernicus DEM"
HOLD_WORD = "آذر تا بهمن ۱۴۰۴"
# the layout, in px (baselines unless stated)
Y_TITLE = (150, 225)
Y_COUNTER, Y_MONTH = 1290, 1378
COUNTER_PX = 180                                 # px: «تهران ×۳» on one line, inside x 150-930 (the buttons' column)
Y_BAR, Y_BAR_NUM, Y_SOURCES = 1424, 1476, 1565
BAR_X = (150, 880)                               # px: the colour bar's ends (the numbers stay inside x 930)
FA_MONTH_NAMES = air.JALALI_NAMES
GRID_LON0, GRID_LAT0, GRID_STEP = air.IRAN_GRID["lon0"], air.IRAN_GRID["lat0"], air.IRAN_GRID["step"]


def font(path, px: int):
    from PIL import ImageFont
    return ImageFont.truetype(str(path), px)


def pct(v: float) -> str:
    return "×" + fa(f"{v:.1f}")                  # one decimal: ×۴٫۲


def intensity(raw):
    """The one colour scale: NO2 (1e15 molec/cm2) to 0-1. The glow and the legend both use this."""
    return np.clip((np.asarray(raw, float) - VMIN) / (VMAX - VMIN), 0, 1) ** GAMMA


def smoothstep(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def text(im, x, y, s, path, px, anchor="ms", fill=PAPER, stroke=4):
    f = font(path, px)
    ImageDraw.Draw(im).text((x, y), s, font=f, fill=fill, anchor=anchor, direction="rtl", language="fa",
                            stroke_width=stroke, stroke_fill=SHADOW)
    return f.getlength(s, direction="rtl", language="fa")


class AirFilm:
    """The film: draw(1, t) is the frame at t seconds (t = inf: the end state)."""

    def __init__(self):
        m = air.monthly()
        self.table = m
        self.ratio = {jk: float(r) for jk, r in zip(m.jk, m.ratio)}
        self.winter = float(m.attrs["winter"])
        self.ref = float(m.attrs["ref"])
        self.fields, self.cover = air.iran_glow()
        rel = np.load(air.DATA / "iran_relief.npz")
        self.rel = {k: rel[k] for k in ("hs", "elev", "water", "inside", "border")}
        self.checks()
        self.L = type("L", (), {"end": DURATION})()
        self.dial_end = DIAL_END
        self.yy, self.xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.base = self.make_base()
        self.glow = {k: self.make_glow(k) for k in MONTHS + ["winter", "summer"]}
        self.static = self.make_static()
        self.assert_scale()

    # ── checks: every number on the screen ──

    def checks(self):
        m, r = self.table, self.ratio
        assert list(m.jk) == MONTHS, list(m.jk)
        assert (m.n_pix > 1000).all() and (m.n_days >= 5).all(), m[["jk", "n_pix", "n_days"]]
        summer = [r[jk] for jk in air.REF_JK]
        assert all(0.7 < v < 1.3 for v in summer), summer
        assert 3.20 <= self.winter <= 3.26, self.winter          # the Tehran-Karaj box, OFFL+NRTI: 3.23
        self.held = int(round(self.winter))
        assert self.held == 3, self.winter                       # the held counter: x3
        assert max(r, key=r.get) == "1404-09", r                 # Azar is the peak month (OFFL+NRTI: 3.63, Dey 3.59)
        assert r["1404-12"] < r["1404-09"] and r["1404-11"] < r["1404-09"], r
        # the share of Iran's land cells with no data, per month (after the NRTI fill); fails above 10 %
        land = self.rel["inside"] > 0.5
        self.empty_share = {}
        for k in air.DIAL_JK + ["winter", "summer"]:
            self.empty_share[k] = float((land & ~self.cover[k]).sum() / land.sum())
        print("share of Iran's land cells with no data, per month:")
        for k, v in self.empty_share.items():
            print(f"    {k}  {100 * v:5.1f} %")
        worst = max(self.empty_share, key=self.empty_share.get)
        assert self.empty_share[worst] <= 0.10, (worst, self.empty_share[worst])

    def assert_scale(self):
        """The country view and the close-up use one colour scale: the legend's ends are the scale's ends."""
        assert intensity(np.array([VMIN]))[0] == 0.0 and intensity(np.array([VMAX]))[0] == 1.0
        assert (VMIN, VMAX, GAMMA) == (2.0, 60.0, 0.5)
        # the legend's colour at any value is the glow's: one function, one scale
        for v in (2.0, 15.0, 30.0, 60.0):
            c = float(intensity(v))
            assert abs(c - np.sqrt((v - 2.0) / 58.0)) < 1e-9, (v, c)

    # ── geometry ──

    def lonlat(self):
        v = VIEW
        lon = v["lon"] + (self.xx + 0.5 - W / 2) * v["km"] / (111.32 * math.cos(math.radians(v["lat"])))
        lat = v["lat"] - (self.yy + 0.5 - v["yA"]) * v["km"] / 110.574
        return lon, lat

    def place(self, lon: float, lat: float) -> tuple:
        v = VIEW
        x = W / 2 + (lon - v["lon"]) * v["km"] ** -1 * 111.32 * math.cos(math.radians(v["lat"])) - 0.5
        y = v["yA"] - (lat - v["lat"]) * 110.574 / v["km"] - 0.5
        return x, y

    @staticmethod
    def sample(arr, lon, lat):
        from scipy import ndimage
        fi = (lon - GRID_LON0) / GRID_STEP - 0.5
        fj = (GRID_LAT0 - lat) / GRID_STEP - 0.5
        return ndimage.map_coordinates(arr, [fj, fi], order=1, mode="nearest")

    # ── layers ──

    def make_base(self) -> np.ndarray:
        """The relief of Iran, dimmed outside the country, the sea dark, the border as a thin line."""
        lon, lat = self.lonlat()
        from scipy import ndimage
        hs = self.sample(self.rel["hs"], lon, lat)
        el = self.sample(self.rel["elev"], lon, lat)
        ins = self.sample(self.rel["inside"], lon, lat)
        hs = hs * ins + ndimage.gaussian_filter(hs, 4) * (1 - ins)   # soft outside the country: no tile seams
        wat = self.sample(self.rel["water"], lon, lat)
        brd = np.clip(2.0 * self.sample(self.rel["border"], lon, lat), 0, 1)
        base = np.empty((H, W, 3), np.float32)
        base[:] = np.array([58, 70, 84], np.float32) * (0.16 + 0.95 * hs[..., None])
        base += (np.clip(el, 0, 3000)[..., None] / 3000.0) * np.array([10, 9, 6], np.float32)
        base *= (0.30 + 0.70 * ins)[..., None]
        base = base * (1 - wat[..., None]) + np.array([12, 18, 26], np.float32) * wat[..., None]
        base = base * (1 - 0.8 * brd[..., None]) + np.array([205, 212, 220], np.float32) * (0.8 * brd[..., None])
        return base

    def make_glow(self, key: str) -> np.ndarray:
        """A field as the glow, 0-1: the one colour scale, a soft halo of BLOOM_PX."""
        from scipy import ndimage
        lon, lat = self.lonlat()
        raw = self.sample(self.fields[key], lon, lat)
        i = intensity(raw)
        bloom = ndimage.gaussian_filter(i, BLOOM_PX) * 0.9
        return np.clip(0.85 * i + 0.6 * bloom, 0, 1).astype(np.float32)

    def make_static(self) -> Image.Image:
        """The title, the six city dots and labels, the colour bar with its two ends, the sources line."""
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for s, y in zip(TITLE, Y_TITLE):
            w = text(im, 540, y, s, FA_BOLD, 58, stroke=5)
            assert w <= 960, (s, w)
        for name, lon, lat in CITIES:
            x, y = self.place(lon, lat)
            x, y = int(round(x)), int(round(y))
            d = ImageDraw.Draw(im)
            d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=PAPER, outline=SHADOW, width=2)
            f = font(FA_BOLD, 34)
            tw = f.getlength(name, direction="rtl", language="fa")
            ox = x + 18 if x < 700 else x - 18 - tw
            d.rounded_rectangle([ox - 10, y - 26, ox + tw + 10, y + 12], radius=12, fill=(8, 10, 14, 200))
            text(im, ox, y + 2, name, FA_BOLD, 34, anchor="ls", stroke=3)
        d = ImageDraw.Draw(im)
        x0, x1 = BAR_X
        for xx in range(x0, x1):
            c = float(intensity(VMIN + (xx - x0) / (x1 - x0) * (VMAX - VMIN)))
            col = tuple(int(q) for q in ORANGE * (1 - c) + HOT * c) + (255,)
            d.line([(xx, Y_BAR), (xx, Y_BAR + 16)], fill=col)
        d.rectangle([x0, Y_BAR, x1, Y_BAR + 16], outline=PAPER, width=2)
        text(im, x0, Y_BAR_NUM, fa(int(VMIN)), FA_TEXT, 32, anchor="ms", stroke=3)
        text(im, x1, Y_BAR_NUM, fa(int(VMAX)), FA_TEXT, 32, anchor="ms", stroke=3)
        text(im, 540, Y_SOURCES, SOURCES, FA_TEXT, 28, stroke=3)
        return im

    # ── time ──

    def state(self, t: float):
        """(glow A, glow B, blend, counter value, month word, phase) at t seconds."""
        win = "winter"
        if not np.isfinite(t) or t < DIAL_STARTS[0] or t >= HOLD:
            return win, win, 0.0, self.winter, "hold", "hold"
        for s, e in zip(DIAL_STARTS, TURNS):
            if t < s:                                  # between the passes: the Azar-Bahman field
                return win, win, 0.0, self.winter, "hold", "hold"
            if t < e:                                  # a pass: the months, a fade in from the winter at its start
                p = min((t - s) * RATE, len(MONTHS) - 1)
                a = int(math.floor(p))
                b = min(a + 1, len(MONTHS) - 1)
                k = int(round(p))
                if t - s < FADE:
                    return win, MONTHS[0], smoothstep((t - s) / FADE), self.ratio[MONTHS[0]], MONTHS[0], "dial"
                return MONTHS[a], MONTHS[b], p - a, self.ratio[MONTHS[k]], MONTHS[k], "dial"
            if t < e + TURN:                           # the turn back to the Azar-Bahman field
                w = (t - e) / TURN
                last = MONTHS[-1]
                value = self.ratio[last] + (self.winter - self.ratio[last]) * smoothstep(w)
                return last, win, smoothstep(w), value, last, "turn"
        return win, win, 0.0, self.winter, "hold", "hold"

    def schedule(self) -> dict:
        """The film's clock, for the score: each month's tick (s, Jalali key), the turns (s), the hold (s)."""
        ticks = [(s + k / RATE, ym) for s in DIAL_STARTS for k, ym in enumerate(MONTHS)]
        return dict(ticks=ticks, turns=list(TURNS), hold=HOLD, end=DURATION)

    @staticmethod
    def month_word(key: str) -> str:
        y, m = int(key[:4]), int(key[5:])
        return f"{air.JALALI_NAMES[m - 1]} {fa(y)}"

    # ── frame ──

    def draw_frame(self, t: float) -> Image.Image:
        ga, gb, w, value, key, phase = self.state(t)
        g = (1 - w) * self.glow[ga] + w * self.glow[gb]
        img = self.base + g[..., None] * (ORANGE[None, None] + (HOT - ORANGE)[None, None] * g[..., None])
        im = Image.fromarray(np.clip(img + 0.5, 0, 255).astype(np.uint8)).convert("RGBA")
        im.alpha_composite(self.static)
        if phase == "hold":                          # the held Azar-Bahman field: x3 (the box ratio, rounded)
            s, word = "×" + fa(f"{self.held}"), HOLD_WORD
        elif phase == "dial":                        # a month: one decimal, its month word and year
            s, word = pct(value), self.month_word(key)
        else:                                        # the turn: Mehr to Azar-Bahman
            s = pct(value) if value < 2.5 else "×" + fa(f"{value:.0f}")
            word = self.month_word(key) if w < 0.5 else HOLD_WORD
        text(im, 540, Y_COUNTER, "تهران " + s, FA_BOLD, COUNTER_PX, anchor="ms", fill=AMBER, stroke=6)
        text(im, 540, Y_MONTH, word, FA_BOLD, 60, anchor="ms")
        return im.convert("RGB")

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]) -> Image.Image:
        assert s == 1 and tuple(size) == (W, H), (s, size)
        return self.draw_frame(0.0 if not np.isfinite(t) else t)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="tehran", choices=["tehran"], help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    args = ap.parse_args()
    film = AirFilm()
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"air_{args.theme}_fa"
    for old in (OUT / "social").glob(f"{base.name}_t*.png"):
        old.unlink()
    film.draw(1, 0.0).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        for t in (0.0, 2.54, 7.15, 7.92, 23.9):      # the hook, Dey (peak), Tir, Mordad, the hold
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
