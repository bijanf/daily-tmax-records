"""SAME RAIN, THIRSTIER AIR: 125 summers of Europe's water, dot by dot, as the world warms.

The water balance of each summer (June to August), 1901-2025: rain minus what the air pulls
out of the ground (Penman-Monteith potential evapotranspiration), from CRU TS; numbers in
water.py. The temperature window maximises while its bars rise, one per year, then shrinks
back above the map. Europe is a halftone that goes both ways: a red dot where the summers of a ten-year
window held less water than in 1951-1980, a navy dot where more, the bigger the more mm.
A ten-year bracket walks along the bars from 1901-10 to the latest summers and the map
follows. A last window answers why: the rain bars stay put, the thirst bars grow. Five scenes,
18 bars of 112 BPM = 38.6 s, with onebit_chip's 8-bit soundtrack: the bars and the map play
the lead, drips under the rain, a rising whistle under the thirst. The camera does not move.

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
                    Timeline, caption_band, ease, prog, smooth)
from onebit_soil import SoilFilm  # noqa: E402

BPM = 112
BAR = 4 * 60 / BPM
SOURCES = "Data: CRU TS 4.10 (UEA, NCAS) · HadCRUT5 (Met Office, UEA)"
GMT_SMALL = (60, 628, 960, 330)     # x, y, w, h
GMT_BIG = (60, 628, 960, 924)       # maximised over the map while the bars rise
MAP_WIN = (60, 972, 960, 580)
WHY_WIN = (76, 1000, 928, 536)
PITCH = 11
STATS = (71, 1080, 300, 160)        # on open sea: the change in summer water, between Iceland and Iberia,
LEGEND = (71, 1468, 300, 80)        # and the dot sizes, below Gibraltar
STEPS = (10, 25, 50, 75)            # mm: the four dot sizes above "about the same"


class WaterFilm(SoilFilm):
    """Draws the film; exposes L, S, bpm, melody(), hits, drips and sweeps for onebit_chip."""

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
        thirst = d["slopes"]["thirst"][0]
        scenes = (
            Scene(2, FULL, "Where did Europe's {summer water} go?",
                  f"{len(y)} summers: rain minus what the air pulls out"),
            Scene(3, FULL, f"First, the planet: {{+{self.warm:.1f} °C}}",
                  "global temperature since 1850–1900, 10-year mean"),
            Scene(7, FULL, "Summer water, {dot by dot}", "red: less water than in 1951–80 · blue: more"),
            Scene(3, FULL, "Same rain. {Thirstier air.}",
                  f"the air pulls {thirst:+.0f} mm more per +1 °C of warming"),
            Scene(3, FULL, f"At +{self.warm:.1f} °C, each m² is {{{-self.loss:.0f} litres drier}} every summer",
                  FOLLOW["en"]),
        )
        starts = np.cumsum([0.0] + [sc.bars * BAR for sc in scenes])
        self.starts = starts
        self.L = Timeline(0, 0, 0, 0, 0, end=float(starts[-1]), camera=((0.0, FULL),),
                          scenes=tuple(float(t) for t in starts[:-1]))
        self.S = SimpleNamespace(scenes=scenes, os_name="EU.WATER.VS.PLANET", lang="en", race=[])
        self.open = 0.4
        self.hits = [float(starts[3])]
        self.rise = (starts[1] + 0.7, starts[1] + 4.6)          # the bars grow in the maximised window
        self.walk = (starts[2] + 0.8, starts[3] - 0.9)
        t3 = starts[3] + self.open
        self.drips = [(t3, t3 + 1.4)]                            # under the rain bars
        self.sweeps = [(t3 + 1.0, t3 + 2.6)]                     # under the thirst bars
        self.gy, self.gv = y, d["gmt"]
        self.ends = d["ends"]                                    # the walk starts at the first ten summers
        self.win_area = d["win_eu"]["balance"]                   # Europe's change, mm (the big number)
        self.val = self.layout(d["win_cells"], MAP_WIN, PITCH)
        for x, yy, w, h in (STATS, LEGEND):
            under = ((self.dot_xy[:, 0] + 6 > x) & (self.dot_xy[:, 0] - 6 < x + w)
                     & (self.dot_xy[:, 1] + 6 > yy) & (self.dot_xy[:, 1] - 6 < yy + h))
            if under.any():
                print(f"warning: {under.sum()} dots of Europe under the label box at {x}, {yy}")
        dots = np.zeros((1920 - 620, 1080), bool)
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        dots[1562 - 620:1644 - 620] = False
        self.dots = dots

    # ── time ──

    def big(self, t: float) -> float:
        """0: the temperature window above the map; 1: maximised."""
        if not np.isfinite(t) or t < self.starts[1] or t >= self.starts[2] + 0.5:
            return 0.0
        if t < self.starts[2]:
            return smooth(prog(t, self.starts[1], 0.5))
        return 1 - smooth(prog(t, self.starts[2], 0.5))

    def melody(self):
        """(time, step, length, gain): the rising bars climb the scale with the planet's
        temperature; on the walk, Europe's summer water sinks the line as it dries."""
        out = []
        n = len(self.gy)
        ts = np.arange(self.rise[0], self.rise[1], 1 / 120)
        bars = np.array([self.bars_at(t) for t in ts])
        for k, g in enumerate(self.gv):
            hit = np.flatnonzero(bars >= k + 1)
            if len(hit):
                out.append((ts[hit[0]], int(round(6 * max(g, 0))), 0.12, 0.35 + 0.25 * k / n))
        ts = np.arange(self.walk[0], self.walk[1], 1 / 120)
        idx = np.array([self.window_at(t) for t in ts])
        for k in range(1, len(self.ends)):
            hit = np.flatnonzero(idx >= k)
            if len(hit):
                v = self.win_area[k]
                out.append((ts[hit[0]], 4 + int(round(v / 7)), 0.14, min(0.7, 0.35 + abs(v) / 80)))
        return out

    # ── drawing ──

    def gmt_window(self, c: Canvas, t: float, k: float):
        th = self.th
        e = self.big(t)
        rect = tuple(a + (b - a) * e for a, b in zip(GMT_SMALL, GMT_BIG))
        x0, y0, x1, y1 = c.window(*rect, "Global.Temp · °C vs 1850–1900")
        n = self.bars_at(t)
        shown = int(np.floor(n))
        if np.isfinite(t) and self.starts[1] <= t < self.starts[2]:
            hi = int(self.gy[max(shown - 1, 0)])                # the newest bar while they rise
        else:
            hi = int(self.ends[int(round(k))])                  # the map's ten summers
        lo = max(hi - water.DECADE + 1, int(self.gy[0]))
        cx0, cx1 = x0 + 14, x1 - 14
        bw = (cx1 - cx0) / len(self.gy)
        floor = y1 - 50                                         # bottom of the coldest bar, above the years
        gmin = min(float(self.gv.min()), 0.0)
        scale = (floor - y0 - 24) / (1.65 - gmin)
        base = floor + gmin * scale                             # 0 °C: years below it hang down
        sel = (self.gy >= lo) & (self.gy <= hi) & (np.arange(len(self.gy)) < max(shown, 1))
        size = 100 + 50 * e
        number = f"+{self.gv[sel].mean():.1f}°C"
        ly, lx = base - 1.5 * scale, x0 + 12 + c.width(number, GROTESK, size) + 30
        for xx in np.arange(lx, cx1, 9):
            c.fill(xx, ly, xx + 4, ly + 2, th.head)
        c.text(lx, ly - 8, "+1.5 °C", size=28 + 6 * e, colour=th.head)
        for i in range(min(shown + 1, len(self.gy))):
            g = self.gv[i] * (1 if i < shown else n - shown)
            xx = cx0 + i * bw
            top = base - g * scale
            c.fill(xx, min(top, base), xx + bw - 2, max(top, base) + 1, th.hot if lo <= self.gy[i] <= hi else th.ink)
        c.fill(cx0, base, cx1, base + 1, th.ink)
        for yr, anchor in ((self.gy[0], "ls"), (1925, "ms"), (1950, "ms"), (1975, "ms"), (2000, "ms"),
                           (self.gy[-1], "rs")):
            xx = cx0 if anchor == "ls" else cx1 if anchor == "rs" else cx0 + (yr - self.gy[0] + 0.5) * bw
            c.text(xx, floor + 40, f"{yr}", size=34, colour=th.head, anchor=anchor)
        c.text(x0 + 12, y0 + 0.96 * size, number, GROTESK, size, th.hot)
        c.text(x0 + 16, y0 + 0.96 * size + 40, "planet, 10-year mean", size=30 + 6 * e)
        c.text(x0 + 16, y0 + 0.96 * size + 76 + 6 * e, f"{lo}–{str(hi)[2:]}" if hi > lo else f"{lo}", size=34 + 6 * e)

    def map_window(self, c: Canvas, k: float, calm: float):
        th = self.th
        x0, y0, x1, y1 = c.window(*MAP_WIN, "Europe.Water · rain − evaporation, Jun–Aug")
        i = int(np.floor(k))
        a = k - i
        v = ((1 - a) * self.val[i] + a * self.val[min(i + 1, len(self.val) - 1)]) * (1 - calm)
        step = np.digitize(np.abs(v), STEPS)
        for x, y in self.other_xy:
            c.fill(x - 1, y - 1, x + 1, y + 1, th.levels[1])
        for (x, y), s, vv in zip(self.dot_xy, step, v):
            c.fill(x - 1 - s, y - 1 - s, x + 1 + s, y + 1 + s, th.ink if s == 0 else th.hot if vv < 0 else th.cold)
        x, y, w, h = STATS
        c.fill(x, y, x + w, y + h, th.paper)
        if calm < 0.5:
            mm = np.interp(k, np.arange(len(self.win_area)), self.win_area)
            hi = int(self.ends[int(round(k))])
            nw = c.text(x + 4, y + 96, f"{mm:+.0f}".replace("-", "−"), GROTESK, 110, th.hot if mm < 0 else th.cold)
            c.text(x + 12 + nw, y + 96, "mm", GROTESK, 44, th.hot if mm < 0 else th.cold)
            c.text(x + 8, y + 128, "water per summer", size=30)
            c.text(x + 8, y + 156, f"{hi - 9}–{str(hi)[2:]} vs 1951–80", size=30)
        x, y, w, h = LEGEND
        c.fill(x, y, x + w, y + h, th.paper)
        c.text(x + 8, y + 28, "mm vs 1951–80:", size=28)
        for j, (s, label, colour) in enumerate(((4, "−75", th.hot), (2, "−25", th.hot), (0, "0", th.ink),
                                                (2, "+25", th.cold))):
            cx = x + 14 + j * 72
            c.fill(cx - 1 - s, y + 56 - s, cx + 1 + s, y + 58 + s, colour)
            c.text(cx + 12, y + 68, label, size=28)

    def why_window(self, c: Canvas, t: float):
        th = self.th
        t0, t1 = self.starts[3], self.starts[4]
        if not np.isfinite(t) or t < t0 or t >= t1 + self.open:
            return
        x, y, w, h = WHY_WIN
        if t < t0 + self.open:
            return c.opening(x, y, w, h, prog(t, t0, self.open))
        if t >= t1:
            return c.opening(x, y, w, h, 1 - prog(t, t1, self.open))
        x0, y0, x1, y1 = c.window(x, y, w, h, "Why.Dry · Europe, Jun–Aug, mm per summer")
        dt = t - t0 - self.open
        bx, bmax = x0 + 236, x1 - 120
        scale = (bmax - bx) / max(self.new["thirst"], self.old["thirst"])
        rows = (("rain", "", "rain", th.cold, 0.0, 34), ("thirst", "of the air", "thirst", th.hot, 0.9, 184))
        for label, sub, key, colour, delay, top in rows:
            p = ease(prog(dt, delay, 1.1))
            c.text(x0 + 16, y0 + top + 50, label, size=44)
            if sub:
                c.text(x0 + 16, y0 + top + 82, sub, size=28)
            for j, (val, solid) in enumerate(((self.old[key], False), (self.new[key], True))):
                yy = y0 + top + j * 44
                xe = bx + val * scale * p
                if solid:
                    c.fill(bx, yy, xe, yy + 34, colour)
                else:
                    c.frame(bx, yy, max(xe, bx + 2), yy + 34)
                if p > 0.95:
                    c.text(xe + 10, yy + 28, f"{val:.0f}", size=32)
        ly = y0 + 312
        c.frame(bx, ly - 18, bx + 26, ly + 2)
        c.text(bx + 34, ly, "1951–80", size=28)
        c.fill(bx + 180, ly - 18, bx + 206, ly + 2, th.ink)
        c.text(bx + 214, ly, f"{self.d['years'][-water.DECADE]}–{str(self.d['years'][-1])[2:]}", size=28)
        if dt > 2.2:
            q = ease(prog(dt, 2.2, 0.8))
            c.text(x0 + 16, y0 + 446, f"{self.loss * q:+.0f}".replace("-", "−") + " mm", GROTESK, 110, th.hot)
            c.text(x0 + 20, y0 + 486, f"rain − thirst: {-self.loss:.0f} litres less water per m²", size=30)

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]):
        c = Canvas(s, self.th, 1.0, (0.0, 0.0), size)
        c.pixels(0, 620, self.dots, self.th.dots)
        i = self.scene(t)
        dt = t - self.starts[i] if np.isfinite(t) else np.inf
        k = self.window_at(t)
        self.map_window(c, k, self.calm(t))
        self.gmt_window(c, t, k)
        self.why_window(c, t)
        c.text(LEFT, 1584, SOURCES, MONO, 20, self.th.head)
        c.text(LEFT, 1610, "Water: rain minus potential evaporation (Penman–Monteith), Jun–Aug.",
               MONO, 18, self.th.head)
        c.text(LEFT, 1634, f"Europe {water.BASE[0]}–{str(water.BASE[1])[2:]}: {self.old['rain']:.0f} mm rain, "
                           f"{self.old['thirst']:.0f} mm demand per summer.", MONO, 18, self.th.head)
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
        for t in (st[1] + 0.3, st[1] + 3.0, st[1] + 5.5, st[2] + 5, st[2] + 10, st[3] + 3.5, st[4] + 3):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
        print("saved", f"{base}_t*.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="chip")


if __name__ == "__main__":
    main()
