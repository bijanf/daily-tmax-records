"""SAME RAIN, HOTTER AIR: 125 summers of Europe's water, dot by dot, as the world warms.

The water balance of each summer (June to August), 1901-2025: rain minus what the air pulls
out of the ground (Penman-Monteith potential evapotranspiration), from CRU TS; numbers in
water.py. A still 1-bit desktop: two windows that never move, ink and one accent colour, and
the data stepping on the beat like an old computer. On top the planet's temperature in 25
chunky bars of five years each; below, Europe in Mercator (the map of the phone's maps app) as a halftone of square dots: a solid red
square where the summers of a ten-year window held less water than in 1951-1980, a hollow
one where more, the bigger the more litres. The bars stand up one per sixteenth note, then
the ten-year window jumps five years per beat from 1901-10 to 2016-25 and the map follows.
A small box on the map says it in plain words: litres less water per m², then rain "same"
and evaporation "+12 %", then the litres as 10-litre buckets (a half-filled one for the rest). Five scenes, 18 bars of
112 BPM = 38.6 s, with onebit_chip's 8-bit soundtrack: every bar and every step a note.

    outputs/onebit/social/europe_water_<theme>_reel.mp4, _cover.png, _music.wav

    python -I src/onebit_water.py                 # Landwehr.Kanal
    python -I src/onebit_water.py --theme feld
    python -I src/onebit_water.py --stills        # cover and seven frames, no video
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
from onebit import (FOLLOW, FULL, GROTESK, LEFT, MONO, OUT, SIZES, SOCIAL_CRF, Canvas, Scene,  # noqa: E402
                    Timeline, caption_band)
from onebit_soil import SoilFilm  # noqa: E402

BPM = 112
BEAT = 60 / BPM
BAR = 4 * BEAT
SOURCES = "Data: CRU TS 4.10 (UEA) · HadCRUT5 (Met Office)"
GMT_WIN = (60, 628, 960, 300)       # x, y, w, h: both windows stand still all film long
MAP_WIN = (60, 944, 960, 612)
MAP_BOX = (390, 973, 620, 576)      # Europe in Mercator, the map everyone knows, right of the box
STATS = (71, 1090, 300, 210)        # the plain-words box, left of the map
PITCH = 11
STEPS = (10, 25, 50, 75)            # litres per m² (= mm): the four dot sizes above "about the same"
PERIOD = 5                          # years per temperature bar; the map jumps as far per beat
HATCH = np.add.outer(np.arange(400), np.arange(60)) // 2 % 2 == 0     # MacPaint-style diagonal fill
BUCKET = ["...#####...", "..#.....#..", ".#.......#.", "###########", "###########", ".#########.",
          ".#########.", ".#########.", "..#######..", "..#######..", "..#######..", "...#####..."]
HALF = ["...#####...", "..#.....#..", ".#.......#.", "###########", "#.........#", ".#.......#.",
        ".#.......#.", ".#########.", "..#######..", "..#######..", "..#######..", "...#####..."]


class WaterFilm(SoilFilm):
    """Draws the film; exposes L, S, bpm, melody(), hits and drips for onebit_chip."""

    bpm = BPM

    def __init__(self, d: dict, th: onebit.Theme):
        self.d, self.th = d, th
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
        scenes = (
            Scene(2, FULL, "Where did Europe's {summer water} go?",
                  f"{len(y)} summers of rain and evaporation, {y[0]}–{y[-1]}"),
            Scene(3, FULL, f"First, the planet: {{+{self.warm:.1f} °C}}",
                  "global temperature since 1850–1900, 10-year mean"),
            Scene(7, FULL, "Summer water, {dot by dot}", "solid square: drier than in 1951–80 · hollow: wetter"),
            Scene(3, FULL, "Same rain. But {hotter air takes more water.}",
                  "sun, heat and wind pull water out of soil and plants"),
            Scene(3, FULL, f"At +{self.warm:.1f} °C, each m² is {{{-self.loss:.0f} litres drier}} every summer",
                  FOLLOW["en"]),
        )
        starts = np.cumsum([0.0] + [sc.bars * BAR for sc in scenes])
        self.starts = starts
        self.L = Timeline(0, 0, 0, 0, 0, end=float(starts[-1]), camera=((0.0, FULL),),
                          scenes=tuple(float(t) for t in starts[:-1]))
        self.S = SimpleNamespace(scenes=scenes, os_name="EU.WATER.VS.PLANET", lang="en", race=[])
        self.open = 0.0
        self.hits = [float(starts[4]) + 0.3]
        self.drips = [(float(starts[3]) + 0.5, float(starts[3]) + 2.0)]
        # temperature in five-year bars; the map's ten-year windows, five years apart
        self.period = (y - y[0]) // PERIOD
        n = int(self.period.max()) + 1
        self.bars = np.array([d["gmt"][self.period == p].mean() for p in range(n)])
        self.bar_years = y[0] + PERIOD * np.arange(n)
        keep = (d["ends"] - y[0] + 1) % PERIOD == 0
        self.ends = d["ends"][keep]                              # 1910, 1915, ..., 2025
        self.win_area = d["win_eu"]["balance"][keep]             # Europe's change, litres per m²
        import cartopy.crs as ccrs
        self.val = self.layout(d["win_cells"][keep], MAP_WIN, PITCH, ccrs.Mercator(), list(water.FRAME) + [34.5, 71.5],
                               MAP_BOX)
        x, yy, w, h = STATS
        under = ((self.dot_xy[:, 0] + 7 > x) & (self.dot_xy[:, 0] - 7 < x + w)
                 & (self.dot_xy[:, 1] + 7 > yy) & (self.dot_xy[:, 1] - 7 < yy + h))
        if under.any():
            print(f"warning: {under.sum()} dots of Europe under the label box")
        dots = np.zeros((1920 - 620, 1080), bool)
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        dots[1562 - 620:1620 - 620] = False
        self.dots = dots

    # ── time: everything steps, nothing glides ──

    def bars_at(self, t: float) -> int:
        """How many temperature bars stand: one more per sixteenth note in scene 2."""
        n = len(self.bars)
        if not np.isfinite(t) or not self.starts[1] <= t < self.starts[2]:
            return n
        return int(np.clip(np.floor((t - self.starts[1] - 2 * BEAT) / (BEAT / 4)) + 1, 0, n))

    def window_at(self, t: float) -> int:
        """Which ten-summer window the map shows: one step of five years per beat in scene 3."""
        n = len(self.ends) - 1
        if not np.isfinite(t) or not self.starts[2] <= t < self.starts[3]:
            return n
        return int(np.clip(np.floor((t - self.starts[2]) / BEAT) - 1, 0, n))

    def calm(self, t: float) -> float:
        """1 in scene 2: every dot at rest while the planet has the stage."""
        return float(np.isfinite(t) and self.starts[1] <= t < self.starts[2])

    def melody(self):
        """(time, step, length, gain): each bar a note as high as the planet's temperature; each
        step of the map a note as low as Europe's summer water; each bucket a falling note."""
        out = []
        t0 = self.starts[1] + 2 * BEAT
        for k, g in enumerate(self.bars):
            out.append((t0 + k * BEAT / 4, int(round(6 * max(g, 0))), 0.12, 0.35 + 0.25 * k / len(self.bars)))
        for k in range(1, len(self.ends)):
            v = self.win_area[k]
            out.append((self.starts[2] + (k + 1) * BEAT, 4 + int(round(v / 7)), 0.2, min(0.7, 0.35 + abs(v) / 80)))
        for j in range(self.buckets):
            out.append((self.starts[4] + self.bucket_at(j), 4 - j, 0.2, 0.7))
        return out

    def bucket_at(self, j: int) -> float:
        """Seconds into scene 5 when bucket j drops in: one per beat."""
        return 2 * BEAT + j * BEAT

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
        c.text(cx0, floor + 38, f"{self.bar_years[0]}", size=34, colour=th.head)
        c.text(cx1, floor + 38, f"{self.bar_years[-1] + PERIOD - 1}", size=34, colour=th.head, anchor="rs")
        sel = (self.d["years"] >= lo) & (self.d["years"] <= hi)
        g = round(float(self.d["gmt"][sel].mean()), 1)
        c.text(x0 + 12, y0 + 96, (f"{g:+.1f}" if g else "0.0").replace("-", "−") + "°C", GROTESK, 100, th.hot)
        c.text(x0 + 16, y0 + 136, "global temperature", size=30)
        c.text(x0 + 16, y0 + 170, f"{lo}–{str(hi)[2:]}", size=34)

    def map_window(self, c: Canvas, k: int, calm: float, t: float = np.inf):
        th = self.th
        x0, y0, x1, y1 = c.window(*MAP_WIN, "Europe.Water")
        v = self.val[k] * (1 - calm)
        step = np.digitize(np.abs(v), STEPS)
        for x, y in self.other_xy:                               # the rest of the land, faint
            if th.mono:
                c.fill(x, y, x + 1, y + 1, th.ink)
            else:
                c.fill(x - 1, y - 1, x + 1, y + 1, th.levels[1])
        for (x, y), s, vv in zip(self.dot_xy, step, v):
            r = 1 + s                                            # 2 to 10 px: a 1 px gap at the most
            if s and vv > 0:                                     # wetter: a hollow square
                c.frame(x - r, y - r, x + r, y + r)
            else:
                c.fill(x - r, y - r, x + r, y + r, th.hot if s else th.ink)
        self.stats(c, t, k, calm)

    def stats(self, c: Canvas, t: float, k: int, calm: float):
        """The plain-words box: litres per m², then rain and evaporation, then buckets."""
        th = self.th
        x, y, w, h = STATS
        c.fill(x, y, x + w, y + h, th.paper)
        scene = self.scene(t) if np.isfinite(t) else 0
        if calm:
            return
        if scene == 3:
            rain = self.new["rain"] / self.old["rain"] - 1
            evap = self.new["thirst"] / self.old["thirst"] - 1
            c.text(x + 8, y + 40, "rain", size=34)
            c.text(x + 8, y + 96, "same" if abs(rain) < 0.03 else f"{100 * rain:+.0f} %", GROTESK, 60, th.ink)
            c.text(x + 8, y + 140, "evaporation", size=34)
            label = f"{100 * evap:+.0f} %"
            if th.mono:                                          # inverse video instead of an accent colour
                c.fill(x + 4, y + 148, x + 16 + c.width(label, GROTESK, 60), y + 210, th.ink)
            c.text(x + 8, y + 196, label, GROTESK, 60, th.field if th.mono else th.hot)
            return
        litres = self.win_area[k]
        colour = th.hot if litres < 0 else th.ink
        nw = c.text(x + 4, y + 100, f"{abs(litres):.0f}", GROTESK, 110, colour)
        c.text(x + 12 + nw, y + 100, "litre" if round(abs(litres)) == 1 else "litres", GROTESK, 44, colour)
        c.text(x + 8, y + 134, f"{'less' if litres < 0 else 'more'} water per m²", size=30)
        if scene == 4:
            dr = t - self.starts[4]
            for j, icon in enumerate(self.icons):
                if dr >= self.bucket_at(j):
                    c.icon(x + 10 + j * 56, y + 150, icon, th.hot, cell=4)
            return
        hi = int(self.ends[k])
        c.text(x + 8, y + 166, f"summer {hi - 9}–{str(hi)[2:]}", size=30)
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
        caption_band(c, self.th, self.S.scenes, i, dt, self.S.os_name)
        return c.im


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="kanal", choices=list(onebit.THEMES), help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and seven frames only, no video")
    args = ap.parse_args()
    film = WaterFilm(water.compute(), onebit.THEMES[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"europe_water_{args.theme}"
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (st[1] + 1.5, st[1] + 5.0, st[2] + 3, st[2] + 9, st[3] + 3, st[4] + 1.5, st[4] + 5):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
        print("saved", f"{base}_t*.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="chip")


if __name__ == "__main__":
    main()
