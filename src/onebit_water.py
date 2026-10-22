"""SAME RAIN, HOTTER AIR: a region's water, dot by dot, as the world warms (Europe, Iran).

The water balance of each season: rain minus what the air pulls out of the ground
(Penman-Monteith potential evapotranspiration), from CRU TS; numbers in water.py. Europe:
summers (June to August), 1901-2025. Iran: water years (October to September), 1951-2025.
A still 1-bit desktop: two windows that never move, ink and one accent colour (or two colours
only, with --theme pink1, gelb1 or firuzeh), and the data stepping on the beat like an old
computer. On top the planet's temperature in chunky bars of five years each; below, the region
in Mercator (the map of the phone's maps app) as a halftone of square dots: a solid square
where the seasons of a ten-year window held less water than in 1951-1980, a hollow one where
more, the bigger the more litres. The bars stand up one per sixteenth note, then the ten-year
window jumps five years per beat and the map follows. A small box beside the map says it in
plain words: litres less water per m², then rain and evaporation, then the litres as 10-litre
buckets (a half-filled one for the rest). Five scenes, 18 bars of 112 BPM = 38.6 s, with
onebit_chip's 8-bit soundtrack: every bar and every step a note. The 20 s cut (--cut 20s): 9
bars of 108 BPM, everything stepping twice as fast, fewer words; the 25 s cut (--cut 25s): 10
bars of 96 BPM, calmer, with captions a fifth bigger. --lang fa: Persian, right to left, in
Vazirmatn with Persian digits.

    outputs/onebit/social/<region>_water_<theme>[_20s][_fa]_reel.mp4, _cover.png, _music.wav

    python -I src/onebit_water.py --theme gelb1                    # Europe, BVG.Gelb.1bit
    python -I src/onebit_water.py --theme gelb1 --cut 20s          # the 20 s cut
    python -I src/onebit_water.py --region iran --lang fa --theme firuzeh --cut 20s
    python -I src/onebit_water.py --stills                         # cover and seven frames, no video
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

import onebit  # noqa: E402
import water  # noqa: E402
from onebit import (FA_BOLD, FA_TEXT, FOLLOW, FULL, GROTESK, LEFT, MONO, OUT, PIXEL, SIZES, SOCIAL_CRF,  # noqa: E402
                    Canvas, Scene, Timeline, caption_band, fa)
from onebit_soil import SoilFilm  # noqa: E402

# the cuts: tempo, scene lengths (bars), beats before the bars rise and per bar, beats before the
# map walks and per step (and per bucket), beats before the first bucket, caption size
CUTS = {"long": dict(bpm=112, bars=(2, 3, 7, 3, 3), lead=2, rise=1 / 4, wait=1, step=1, drop=2, caption=1.0),
        "20s": dict(bpm=108, bars=(1.5, 1.5, 3, 1.5, 1.5), lead=1, rise=1 / 8, wait=0, step=1 / 2, drop=1, caption=1.0),
        "25s": dict(bpm=96, bars=(2, 2, 3, 1.5, 1.5), lead=1, rise=1 / 4, wait=1, step=1 / 2, drop=1, caption=1.2)}
# the map of each region: its frame (water.REGIONS), halftone pitch (CRU's 0.5 deg cells need
# wider dots over a small country), the litres of the four dot sizes, and how the "why" box
# counts: per cent, or litres when both rain and evaporation moved
MAPS = {"europe": dict(title="Europe.Water", os="EU.WATER.VS.PLANET", pitch=11, steps=(10, 25, 50, 75), why="%"),
        "iran": dict(title="Iran.Water", os="IR.WATER.VS.PLANET", pitch=20, steps=(25, 50, 100, 150), why="litres")}
SOURCES = "Data: CRU TS 4.10 (UEA) · HadCRUT5 (Met Office)"
GMT_WIN = (60, 628, 960, 300)       # x, y, w, h: both windows stand still all film long
MAP_WIN = (60, 944, 960, 612)
MAP_BOX = (390, 973, 620, 576)      # the region in Mercator, the map everyone knows, right of the box
STATS = (71, 1060, 300, 380)        # the plain-words box, left of the map (tall: the buckets)
PERIOD = 5                          # years per temperature bar; the map jumps as far per beat
HATCH = np.add.outer(np.arange(1000), np.arange(60)) // 2 % 2 == 0    # MacPaint-style diagonal fill
BUCKET = ["...#####...", "..#.....#..", ".#.......#.", "###########", "###########", ".#########.",
          ".#########.", ".#########.", "..#######..", "..#######..", "..#######..", "...#####..."]
HALF = ["...#####...", "..#.....#..", ".#.......#.", "###########", "#.........#", ".#.......#.",
        ".#.......#.", ".#########.", "..#######..", "..#######..", "..#######..", "...#####..."]
FOLLOW_FA = "برای داده‌های اقلیمی بیشتر، فالو کنید"


def captions(region: str, lang: str, cut: str, n: int, y0: int, y1: int, warm: float, loss: float) -> tuple:
    """(title, line) of the five scenes; {braces} mark the accent."""
    w, L = f"{warm:.1f}", f"{-loss:.0f}"
    if (region, lang) == ("europe", "en"):
        if cut == "long":
            return (("Where did Europe's {summer water} go?", f"{n} summers of rain and evaporation, {y0}–{y1}"),
                    (f"First, the planet: {{+{w} °C}}", "global temperature vs 1850–1900, average of 10 years"),
                    ("Summer water, {dot by dot}", "solid square: drier than in 1951–80 · hollow: wetter"),
                    ("Same rain. But {hotter air takes more water.}", "sun, heat and wind pull water out of soil and plants"),
                    (f"At +{w} °C, each m² is {{{L} litres drier}} every summer", FOLLOW["en"]))
        return (("Where did Europe's {summer water} go?", f"{n} summers of rain and evaporation"),
                (f"The planet: {{+{w} °C}}", "global temperature vs 1850–1900"),
                ("Summer water, {dot by dot}", "solid square: drier than 1951–80 · hollow: wetter"),
                ("Same rain. {Hotter air.}", "hot air pulls more water out of soil and plants"),
                (f"{{{L} litres less}} per m², every summer", FOLLOW["en"]))
    if (region, lang) == ("iran", "en"):
        if cut == "long":
            return (("Where did Iran's {water} go?", f"{n} water years of rain and evaporation, {y0}–{y1}"),
                    (f"First, the planet: {{+{w} °C}}", "global temperature vs 1850–1900, average of 10 years"),
                    ("Iran's water, {dot by dot}", "solid square: drier than in 1951–80 · hollow: wetter"),
                    ("Less rain. And {hotter air takes more water.}", "sun, heat and wind pull water out of soil and plants"),
                    (f"At +{w} °C, each m² of Iran is {{{L} litres drier}} every year", "Follow for more climate data in 1-bit"))
        return (("Where did Iran's {water} go?", f"{n} years of rain and evaporation"),
                (f"The planet: {{+{w} °C}}", "global temperature vs 1850–1900"),
                ("Iran's water, {dot by dot}", "solid square: drier than 1951–80 · hollow: wetter"),
                ("Less rain. {Hotter air.}", "hot air pulls more water out of soil and plants"),
                (f"{{{L} litres less}} per m², every year", "Follow for more climate data in 1-bit"))
    if (region, lang) == ("iran", "fa"):
        if cut == "long":
            return (("آبِ ایران {کجا رفت؟}", f"{fa(n)} سال آبی باران و تبخیر، {fa(y0)} تا {fa(y1)}"),
                    (f"اول، کرهٔ زمین: {{{fa(w)} درجه}} گرم‌تر", "دمای میانگین جهان نسبت به ۱۸۵۰ تا ۱۹۰۰، میانگین ده ساله"),
                    ("آبِ ایران، {نقطه به نقطه}", "مربع پر: کم‌آب‌تر از ۱۹۵۱ تا ۱۹۸۰ · مربع توخالی: پرآب‌تر"),
                    ("باران {کمتر}، تبخیر {بیشتر}", "هوای گرم‌تر آب بیشتری از خاک و گیاه بیرون می‌کشد"),
                    (f"{{{fa(L)} لیتر}} آب کمتر، هر سال، در هر متر مربعِ ایران", FOLLOW_FA))
        return (("آبِ ایران {کجا رفت؟}", f"{fa(n)} سال باران و تبخیر"),
                (f"زمین: {{{fa(w)} درجه}} گرم‌تر", "نسبت به ۱۸۵۰ تا ۱۹۰۰"),
                ("آبِ ایران، {نقطه به نقطه}", "مربع پر: کم‌آب‌تر · مربع توخالی: پرآب‌تر"),
                ("باران {کمتر}، تبخیر {بیشتر}", "هوای گرم‌تر آب بیشتری می‌کشد"),
                (f"هر سال {{{fa(L)} لیتر}} آب کمتر در هر متر مربع", FOLLOW_FA))
    raise ValueError(f"no words for {region} in {lang}")


class WaterFilm(SoilFilm):
    """Draws the film; exposes L, S, bpm, melody(), hits and drips for onebit_chip."""

    def __init__(self, d: dict, th: onebit.Theme, cut: str = "long", lang: str = "en"):
        self.d, self.th, self.cut, self.lang = d, th, cut, lang
        self.region = d["region"]
        self.map = MAPS[self.region]
        self.fa = lang == "fa"
        self.pace = CUTS[cut]
        self.bpm = self.pace["bpm"]
        self.beat = 60 / self.bpm
        y, D = d["years"], water.DECADE
        base, last = (y >= water.BASE[0]) & (y <= water.BASE[1]), slice(-D, None)
        eu = d["eu"]
        self.old = {k: v[base].mean() for k, v in eu.items()}
        self.new = {k: v[last].mean() for k, v in eu.items()}
        self.loss = self.new["balance"] - self.old["balance"]
        self.warm = d["gmt"][last].mean()
        full, rest = divmod(-self.loss, 10)                      # 10-litre buckets, and a half one
        self.icons = [BUCKET] * int(full) + ([HALF] if rest >= 2.5 else [])
        self.icons += [BUCKET] if rest >= 7.5 else []
        self.buckets = len(self.icons)
        words = captions(self.region, lang, cut, len(y), y[0], y[-1], self.warm, self.loss)
        scenes = tuple(Scene(b, FULL, title, line) for b, (title, line) in zip(self.pace["bars"], words))
        starts = np.cumsum([0.0] + [sc.bars * 4 * self.beat for sc in scenes])
        self.starts = starts
        self.L = Timeline(0, 0, 0, 0, 0, end=float(starts[-1]), camera=((0.0, FULL),),
                          scenes=tuple(float(t) for t in starts[:-1]))
        self.S = SimpleNamespace(scenes=scenes, os_name=self.map["os"], lang=lang, race=[])
        self.open = 0.0
        self.hits = [float(starts[4]) + 0.3]
        self.drips = [(float(starts[3]) + 0.5, float(starts[3]) + 2.0)]
        # temperature in five-year bars; the map's ten-year windows, five years apart
        self.period = (y - y[0]) // PERIOD
        n = int(self.period.max()) + 1
        self.bars = np.array([d["gmt"][self.period == p].mean() for p in range(n)])
        self.bar_years = y[0] + PERIOD * np.arange(n)
        keep = (d["ends"] - y[0] + 1) % PERIOD == 0
        self.ends = d["ends"][keep]                              # Europe 1910, 1915, ..., 2025; Iran 1960, ...
        self.win_area = d["win_eu"]["balance"][keep]             # the region's change, litres per m²
        import cartopy.crs as ccrs
        lon0, lon1, lat0, lat1 = water.REGIONS[self.region]["frame"]
        europe = self.region == "europe"
        self.val = self.layout(d["win_cells"][keep], MAP_WIN, self.map["pitch"], ccrs.Mercator(),
                               [lon0, lon1, 34.5 if europe else lat0, lat1], MAP_BOX, skip_top=europe)
        x, yy, w, h = STATS
        under = ((self.dot_xy[:, 0] + 7 > x) & (self.dot_xy[:, 0] - 7 < x + w)
                 & (self.dot_xy[:, 1] + 7 > yy) & (self.dot_xy[:, 1] - 7 < yy + h))
        if under.any():
            print(f"warning: {under.sum()} dots of the map under the label box")
        dots = np.zeros((1920 - 620, 1080), bool)
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        dots[1562 - 620:1620 - 620] = False
        self.dots = dots

    # ── words in two scripts ──

    def small(self, c: Canvas, x, y, s, size=30, colour=None, anchor="ls"):
        """A line of the pixel font, or of Vazirmatn right to left in Persian."""
        if self.fa:
            return c.text(x, y, fa(s), FA_TEXT, size - 2, colour, anchor, "rtl")
        return c.text(x, y, s, PIXEL, size, colour, anchor)

    def big(self, c: Canvas, x, y, s, size, colour=None, anchor="ls"):
        """Numbers in the grotesk, or in Vazirmatn with Persian digits."""
        return c.text(x, y, fa(s) if self.fa else s, FA_BOLD if self.fa else GROTESK, size, colour, anchor)

    def years(self, lo: int, hi: int) -> str:
        return f"{lo} تا {hi}" if self.fa else f"{lo}–{str(hi)[2:]}"

    # ── time: everything steps, nothing glides ──

    def bars_at(self, t: float) -> int:
        """How many temperature bars stand: one more per sixteenth note in scene 2."""
        n = len(self.bars)
        if not np.isfinite(t) or not self.starts[1] <= t < self.starts[2]:
            return n
        lead, rise = self.pace["lead"] * self.beat, self.pace["rise"] * self.beat
        return int(np.clip(np.floor((t - self.starts[1] - lead) / rise) + 1, 0, n))

    def window_at(self, t: float) -> int:
        """Which ten-year window the map shows: one step of five years per beat in scene 3."""
        n = len(self.ends) - 1
        if not np.isfinite(t) or not self.starts[2] <= t < self.starts[3]:
            return n
        wait, step = self.pace["wait"] * self.beat, self.pace["step"] * self.beat
        return int(np.clip(np.floor((t - self.starts[2] - wait) / step), 0, n))

    def calm(self, t: float) -> float:
        """1 in scene 2: every dot at rest while the planet has the stage."""
        return float(np.isfinite(t) and self.starts[1] <= t < self.starts[2])

    def melody(self):
        """(time, step, length, gain): each bar a note as high as the planet's temperature; each
        step of the map a note as low as the region's water; each bucket a falling note."""
        out = []
        b, P = self.beat, self.pace
        unit = self.map["steps"][-1] / 75                        # Europe 1: its dots' litres set the scale
        t0 = self.starts[1] + P["lead"] * b
        for k, g in enumerate(self.bars):
            out.append((t0 + k * P["rise"] * b, int(round(6 * max(g, 0))), 0.12, 0.35 + 0.25 * k / len(self.bars)))
        for k in range(1, len(self.ends)):
            v = self.win_area[k] / unit
            out.append((self.starts[2] + (P["wait"] + k * P["step"]) * b, 4 + int(round(v / 7)), 0.2,
                        min(0.7, 0.35 + abs(v) / 80)))
        for j in range(self.buckets):
            out.append((self.starts[4] + self.bucket_at(j), 4 - j, 0.2, 0.7))
        return out

    def bucket_at(self, j: int) -> float:
        """Seconds into scene 5 when bucket j drops in: one per step of the walk, two when many."""
        step = self.pace["step"] * (0.5 if self.buckets > 6 else 1)
        return (self.pace["drop"] + j * step) * self.beat

    # ── drawing ──

    def gmt_window(self, c: Canvas, t: float, k: int):
        th = self.th
        x0, y0, x1, y1 = c.window(*GMT_WIN, "Global.Temp")
        shown = self.bars_at(t)
        rising = np.isfinite(t) and self.starts[1] <= t < self.starts[2]
        hi = int(self.bar_years[max(shown, 1) - 1]) + PERIOD - 1 if rising else int(self.ends[k])
        lo = max(hi - water.DECADE + 1, int(self.bar_years[0]))
        n = len(self.bars)
        cx0, cx1 = x0 + 14, x1 - 14
        bw = (cx1 - cx0) / n
        floor = y1 - 46
        gmin = min(float(self.bars.min()), 0.0)
        scale = (floor - y0 - 20) / (1.6 - gmin)
        base = floor + gmin * scale
        for i in range(shown):
            xx = cx0 + i * bw
            top = base - self.bars[i] * scale
            inside = lo <= self.bar_years[i] and self.bar_years[i] + PERIOD - 1 <= hi
            a, b = min(top, base), max(top, base) + 1
            if th.mono and not inside:                           # two colours: the other bars are hatched
                c.pixels(xx + 2, a, HATCH[:int(np.ceil(b - a)), :int(bw - 6)], th.ink)
                c.frame(xx + 2, a, xx + bw - 4, b)
            else:
                c.fill(xx + 2, a, xx + bw - 4, b, th.hot if inside else th.ink)
        c.fill(cx0, base, cx1, base + 2, th.ink)
        first, last = f"{self.bar_years[0]}", f"{self.bar_years[-1] + PERIOD - 1}"
        if self.fa:
            self.big(c, cx0, floor + 38, first, 30, th.head)
            self.big(c, cx1, floor + 38, last, 30, th.head, "rs")
        else:
            c.text(cx0, floor + 38, first, size=34, colour=th.head)
            c.text(cx1, floor + 38, last, size=34, colour=th.head, anchor="rs")
        sel = (self.d["years"] >= lo) & (self.d["years"] <= hi)
        g = round(float(self.d["gmt"][sel].mean()), 1)
        self.big(c, x0 + 12, y0 + 96, (f"{g:+.1f}" if g else "0.0").replace("-", "−") + "°C", 100, th.hot)
        self.small(c, x0 + 16, y0 + 136, "زمین نسبت به ۱۸۵۰ تا ۱۹۰۰" if self.fa else "Earth vs 1850–1900")
        self.small(c, x0 + 16, y0 + 170, self.years(lo, hi), 34)

    def map_window(self, c: Canvas, k: int, calm: float, t: float = np.inf):
        th = self.th
        x0, y0, x1, y1 = c.window(*MAP_WIN, self.map["title"])
        v = self.val[k] * (1 - calm)
        step = np.digitize(np.abs(v), self.map["steps"])
        grow = (self.map["pitch"] - 3) / 8                       # Europe 1: one pixel per size step
        for x, y in self.other_xy:                               # the rest of the land, faint
            if th.mono:
                c.fill(x, y, x + 1, y + 1, th.ink)
            else:
                c.fill(x - 1, y - 1, x + 1, y + 1, th.levels[1])
        for (x, y), s, vv in zip(self.dot_xy, step, v):
            r = 1 + s * grow                                     # a 1 px gap at the most
            if s and vv > 0:                                     # wetter: a hollow square
                c.frame(x - r, y - r, x + r, y + r)
            else:
                c.fill(x - r, y - r, x + r, y + r, th.hot if s else th.ink)
        self.stats(c, t, k, calm)

    def stats(self, c: Canvas, t: float, k: int, calm: float):
        """The plain-words box: litres per m², then rain and evaporation, then buckets. In
        Persian everything sits on the right edge of the box."""
        th, F = self.th, self.fa
        x, y, w, h = STATS
        c.fill(x, y, x + w, y + h, th.paper)
        scene = self.scene(t) if np.isfinite(t) else 0
        if calm:
            return
        edge, anchor = (x + w - 8, "rs") if F else (x + 8, "ls")
        if scene == 3:
            rows = (("rain", "باران", "rain", False), ("evaporation", "تبخیر", "thirst", True))
            for j, (en, pe, key, accent) in enumerate(rows):
                change = self.new[key] - self.old[key]
                rel = self.new[key] / self.old[key] - 1
                if abs(rel) < 0.03:
                    label = "تقریباً همان" if F else "same"
                elif self.map["why"] == "%":
                    label = f"{100 * rel:+.0f} %"
                elif F:
                    label = f"{abs(change):.0f} لیتر {'بیشتر' if change > 0 else 'کمتر'}"
                else:
                    label = f"{abs(change):.0f} L {'more' if change > 0 else 'less'}"
                self.small(c, edge, y + 40 + j * 100, pe if F else en, 34, anchor=anchor)
                size = 44 if self.map["why"] == "litres" else 60
                if F:
                    lw = c.width(fa(label), FA_BOLD, size, "rtl")
                else:
                    lw = c.width(label, GROTESK, size)
                lx = edge - lw if F else edge
                if accent and th.mono:                           # inverse video instead of an accent colour
                    c.fill(lx - 4, y + 104 + j * 100 - size, lx + lw + 4, y + 106 + j * 100 + 0.14 * size, th.ink)
                colour = (th.field if th.mono else th.hot) if accent else th.ink
                if F:
                    c.text(edge, y + 96 + j * 100, fa(label), FA_BOLD, size, colour, "rs", "rtl")
                else:
                    c.text(edge, y + 96 + j * 100, label, GROTESK, size, colour)
            return
        litres = self.win_area[k]
        colour = th.hot if litres < 0 else th.ink
        less = litres < 0
        if F:
            nw = self.big(c, edge, y + 100, f"{abs(litres):.0f}", 110, colour, "rs")
            c.text(edge - nw - 12, y + 100, "لیتر", FA_BOLD, 44, colour, "rs", "rtl")
            self.small(c, edge, y + 134, f"آب {'کمتر' if less else 'بیشتر'} در هر متر مربع", anchor=anchor)
        else:
            nw = c.text(x + 4, y + 100, f"{abs(litres):.0f}", GROTESK, 110, colour)
            c.text(x + 12 + nw, y + 100, "litre" if round(abs(litres)) == 1 else "litres", GROTESK, 44, colour)
            c.text(x + 8, y + 134, f"{'less' if less else 'more'} water per m²", size=30)
        if scene == 4:
            dr = t - self.starts[4]
            per, cell, dx, dy = (3, 7, 92, 96) if self.buckets <= 6 else (4, 5, 70, 70)
            for j, icon in enumerate(self.icons):                # big buckets; from the right in Persian
                if dr >= self.bucket_at(j):
                    col = per - 1 - j % per if F else j % per
                    c.icon(x + 10 + col * dx, y + 160 + (j // per) * dy, icon, th.hot, cell=cell)
            return
        hi = int(self.ends[k])
        unit = water.REGIONS[self.region]["unit"]
        if F:
            self.small(c, edge, y + 166, f"سال‌های آبی {self.years(hi - 9, hi)}", anchor=anchor)
            self.small(c, edge, y + 198, "نسبت به ۱۹۵۱ تا ۱۹۸۰", anchor=anchor)
        else:
            c.text(x + 8, y + 166, f"{unit}{'s' if unit != 'summer' else ''} {hi - 9}–{str(hi)[2:]}", size=30)
            c.text(x + 8, y + 198, "vs 1951–80", size=30)

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]):
        c = Canvas(s, self.th, 1.0, (0.0, 0.0), size)
        c.pixels(0, 620, self.dots, self.th.dots)
        i = self.scene(t)
        dt = t - self.starts[i] if np.isfinite(t) else np.inf
        k = self.window_at(t)
        self.gmt_window(c, t, k)
        self.map_window(c, k, self.calm(t), t)
        c.text(LEFT, 1596, SOURCES, MONO, 20, self.th.head)
        caption_band(c, self.th, self.S.scenes, i, dt, self.S.os_name, self.lang, self.pace["caption"])
        return c.im


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="europe", choices=list(MAPS))
    ap.add_argument("--lang", default="en", choices=("en", "fa"))
    ap.add_argument("--theme", default="kanal", choices=list(onebit.THEMES), help="colour theme")
    ap.add_argument("--cut", default="long", choices=list(CUTS), help="long (38.6 s), 20s or 25s")
    ap.add_argument("--stills", action="store_true", help="cover and seven frames only, no video")
    args = ap.parse_args()
    film = WaterFilm(water.compute(args.region), onebit.THEMES[args.theme], args.cut, args.lang)
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    tag = ("" if args.cut == "long" else f"_{args.cut}") + ("" if args.lang == "en" else f"_{args.lang}")
    base = OUT / "social" / f"{args.region}_water_{args.theme}{tag}"
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (st[1] + 1.0, st[2] - 0.3, st[2] + 2, (st[2] + st[3]) / 2, st[3] + 1.5, st[4] + 0.8, st[5] - 0.2):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
        print("saved", f"{base}_t*.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="chip")


if __name__ == "__main__":
    main()
