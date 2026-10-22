"""DRY SOIL, WARM PLANET: Europe's summer soil drought, dot by dot, as the world warms.

Two 1-bit windows. On top the planet's temperature since 1950, one bar per year against
1850-1900 (HadCRUT5). Below, Europe as a halftone: one dot per 12-pixel patch of land (about
75 km), and the more summers out of ten had their soil drier than nine in ten summers of
1951-1980 there, the bigger and redder the dot (ERA5-Land, numbers in soil.py). The reel
opens on the latest ten summers; the map goes quiet while the temperature bars rise; then a
ten-year bracket walks along the bars from 1951-60 to the latest summers and the map follows.
A third window plots every summer's drought area against the global temperature. Five
scenes, 19 bars of 128 BPM = 35.6 s, with onebit_audio's soundtrack: a blip per year, higher
as the planet warms, louder the more of Europe was dry. No zoom: the data moves, the camera
does not.

    outputs/onebit/social/europe_soil_<theme>_reel.mp4, _cover.png, _music.wav

    python -I src/onebit_soil.py                 # Tempelhof.Feld
    python -I src/onebit_soil.py --theme beton
    python -I src/onebit_soil.py --stills        # cover and seven frames, no video
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from scipy import sparse  # noqa: E402

import onebit  # noqa: E402
import soil  # noqa: E402
from onebit import (BAR, FOLLOW, FPS, FULL, GROTESK, LEFT, MONO, OUT, SIZES, SOCIAL_CRF, Canvas, Scene,  # noqa: E402
                    Timeline, caption_band, ease, prog, smooth)

SOURCES = "Data: ERA5-Land (Copernicus, ECMWF) · HadCRUT5 (Met Office, UEA)"
GMT_WIN = (60, 628, 960, 236)       # x, y, w, h
MAP_WIN = (60, 878, 960, 676)
LINK_WIN = (76, 910, 928, 628)      # the result window, stacked over the map
STATS = (71, 1050, 270, 196)        # map labels on open sea: the share in drought, between Iceland and Iberia,
LEGEND = (71, 1463, 262, 80)        # and the dot sizes, below Gibraltar
EXTENT = [-25, 45, 34, 71.5]
PITCH = 12                          # halftone: one dot per PITCH x PITCH logical pixels
STEPS = 4                           # dot sizes above the stable-climate one
YEAR0 = 1950                        # first temperature bar
NAMED = (2018, 2026)                # summers named in the link plot: the driest, and this one


class SoilFilm:
    """Draws the film; exposes L, S, open, events() and hits for onebit_audio's story soundtrack."""

    def __init__(self, d: dict, th: onebit.Theme):
        self.d, self.th = d, th
        y, D = d["years"], soil.DECADE
        base = (y >= soil.BASE[0]) & (y <= soil.BASE[1])
        self.was, self.now = 100 * d["area"][base].mean(), 100 * d["area"][-D:].mean()
        self.warm, self.per, self.ci = d["gmt"][-D:].mean(), 100 * d["slope"], 100 * d["ci"]
        scenes = (
            Scene(2, FULL, "Is Europe's soil {drying out?}", f"summer soil water, {y[0]}–{y[-1]}"),
            Scene(3, FULL, f"First, the planet: {{+{self.warm:.1f} °C}}",
                  "global temperature since 1850–1900, 10-year mean"),
            Scene(8, FULL, "Europe's soil, {dot by dot}", "bigger, redder dot: more dry summers out of 10"),
            Scene(3, FULL, "Warmer world, {drier soil}",
                  f"+{self.per:.0f} % of Europe in soil drought per +1 °C of warming"),
            Scene(3, FULL, f"At +{self.warm:.1f} °C, soil drought is {{{self.now / self.was:.0f}× as common}}",
                  FOLLOW["en"]),
        )
        starts = np.cumsum([0.0] + [sc.bars * BAR for sc in scenes])
        self.starts = starts
        self.L = Timeline(0, 0, 0, 0, 0, end=float(starts[-1]), camera=((0.0, FULL),),
                          scenes=tuple(float(t) for t in starts[:-1]))
        self.S = SimpleNamespace(scenes=scenes, os_name="EU.SOIL.VS.PLANET", lang="en", race=[])
        self.open = 0.4
        self.hits = [float(starts[3])]
        self.rise = (starts[1] + 0.4, starts[1] + 4.0)          # the temperature bars grow
        self.walk = (starts[2] + 0.8, starts[3] - 0.9)          # the bracket walks 1951-60 -> latest
        # temperature bars and the ten-summer windows from 1951-60 on
        keep = y >= YEAR0
        self.gy, self.gv = y[keep], d["gmt"][keep]
        k0 = int(np.searchsorted(d["ends"], soil.BASE[0] + D - 1))
        self.ends, self.win_area = d["ends"][k0:], 100 * d["win_area"][k0:]
        self.layout(d["win_cells"][k0:])
        for x, y, w, h in (STATS, LEGEND):
            under = ((self.dot_xy[:, 0] + 6 > x) & (self.dot_xy[:, 0] - 6 < x + w)
                     & (self.dot_xy[:, 1] + 6 > y) & (self.dot_xy[:, 1] - 6 < y + h))
            if under.any():
                print(f"warning: {under.sum()} dots of Europe under the label box at {x}, {y}")
        dots = np.zeros((1920 - 620, 1080), bool)
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        dots[1562 - 620:1644 - 620] = False                     # a clear band under the footnotes
        self.dots = dots

    def layout(self, cells: np.ndarray):
        """The halftone: Europe's cells pooled into lattice dots (area-weighted share of the ten
        summers in drought, per window), and the rest of the land as faint dots."""
        x, y, w, h = MAP_WIN
        x0, y0 = x + 7, y + 29
        mw, mh = w - 14, h - 36
        land, xy = onebit.europe_raster(self.d["lon"], self.d["lat"], mw, mh, EXTENT)
        nx, ny = mw // PITCH, mh // PITCH
        i, j = np.floor(xy[:, 0] / PITCH).astype(int), np.floor(xy[:, 1] / PITCH).astype(int)
        inside = (i >= 0) & (i < nx) & (j >= 0) & (j < ny)
        keys, dot = np.unique((j * nx + i)[inside], return_inverse=True)
        m = sparse.csr_matrix((self.d["w"][inside], (dot, np.flatnonzero(inside))), shape=(len(keys), len(i)))
        m = sparse.diags(1 / np.asarray(m.sum(1)).ravel()) @ m
        self.frac = np.asarray((m @ cells.T).T) / soil.DECADE          # (window, dot)
        centre = lambda k: np.c_[k % nx, k // nx] * PITCH + PITCH / 2 + [x0, y0]  # noqa: E731
        self.dot_xy = centre(keys)
        jj, ii = np.mgrid[0:ny, 0:nx]
        other = land[jj * PITCH + PITCH // 2, ii * PITCH + PITCH // 2] & (jj >= ny // 8)   # no Greenland
        other = other.ravel()
        other[keys] = False
        self.other_xy = centre(np.flatnonzero(other))

    # ── time ──

    def scene(self, t: float) -> int:
        return int(np.searchsorted(self.starts[:-1], t, side="right")) - 1 if np.isfinite(t) else 0

    def window_at(self, t: float) -> float:
        """Which ten-summer window the map shows (fractional index into self.ends)."""
        n = len(self.ends) - 1
        if not np.isfinite(t) or not self.starts[2] <= t < self.starts[3]:
            return float(n)
        return n * smooth(prog(t, self.walk[0], self.walk[1] - self.walk[0]))

    def calm(self, t: float) -> float:
        """0: the map shows its window; 1: every dot at rest, while the planet has the stage."""
        if not np.isfinite(t) or t < self.starts[1] or t >= self.starts[3]:
            return 0.0
        if t < self.starts[2]:
            return ease(prog(t, self.starts[1], 1.0))
        return 1 - ease(prog(t, self.starts[2], 0.6))

    def bars_at(self, t: float) -> float:
        """How many temperature bars stand."""
        n = len(self.gy)
        if not np.isfinite(t) or not self.starts[1] <= t < self.starts[2]:
            return float(n)
        return n * ease(prog(t, self.rise[0], self.rise[1] - self.rise[0]))

    def events(self):
        """(time, dry, wet) per year for the soundtrack: the bars rise in pitch with the planet's
        temperature; on the walk, each summer that enters the window sounds louder the more of
        Europe was dry, a wet summer low."""
        ts = np.arange(round(self.L.end * FPS)) / FPS
        out = []
        rise = ts[(ts >= self.starts[1]) & (ts < self.starts[2])]
        bars = np.array([self.bars_at(t) for t in rise])
        for k, g in enumerate(self.gv):
            hit = np.flatnonzero(bars >= k + 1)
            if len(hit):
                out.append((rise[hit[0]], int(2 ** (3 * max(g, 0))), 0))
        walk = ts[(ts >= self.starts[2]) & (ts < self.starts[3])]
        idx = np.array([self.window_at(t) for t in walk])
        area = dict(zip(self.d["years"], 100 * self.d["area"]))
        for k, end in enumerate(self.ends[1:], 1):
            hit = np.flatnonzero(idx >= k)
            if len(hit):
                a = area[end]
                out.append((walk[hit[0]], int(5 * a) if a >= 15 else 0, int(a < 5)))
        return out

    # ── drawing ──

    def gmt_window(self, c: Canvas, t: float, k: float):
        th = self.th
        x0, y0, x1, y1 = c.window(*GMT_WIN, "Global.Temp · °C vs 1850–1900")
        n = self.bars_at(t)
        shown = int(np.floor(n))
        if np.isfinite(t) and self.starts[1] <= t < self.starts[2]:
            hi = int(self.gy[max(shown - 1, 0)])                # the newest bar while they rise
        else:
            hi = int(self.ends[int(round(k))])                  # the map's ten summers
        lo = max(hi - soil.DECADE + 1, int(self.gy[0]))
        cx0, cx1 = x0 + 372, x1 - 14
        bw = (cx1 - cx0) / len(self.gy)
        base, scale = y0 + 160, 95
        # +1.5 °C, dotted
        ly = base - 1.5 * scale
        for xx in np.arange(cx0, cx1, 9):
            c.fill(xx, ly, xx + 4, ly + 2, th.head)
        c.text(cx0 - 8, ly + 9, "1.5", size=28, colour=th.head, anchor="rs")
        for i in range(min(shown + 1, len(self.gy))):
            g = self.gv[i] * (1 if i < shown else n - shown)
            xx = cx0 + i * bw
            top = base - g * scale
            colour = th.hot if lo <= self.gy[i] <= hi else th.ink
            c.fill(xx, min(top, base), xx + bw - 2, max(top, base) + 1, colour)
        c.fill(cx0, base, cx1, base + 1, th.ink)
        c.text(cx0, base + 38, f"{self.gy[0]}", size=34, colour=th.head)
        c.text(cx0 + (1990 - self.gy[0] + 0.5) * bw, base + 38, "1990", size=34, colour=th.head, anchor="ms")
        c.text(cx1, base + 38, f"{self.gy[-1]}", size=34, colour=th.head, anchor="rs")
        # the ten-year mean under the bracket
        sel = (self.gy >= lo) & (self.gy <= hi) & (np.arange(len(self.gy)) < max(shown, 1))
        c.text(x0 + 12, y0 + 96, f"+{self.gv[sel].mean():.1f}°C", GROTESK, 100, th.hot)
        c.text(x0 + 16, y0 + 138, "planet, 10-year mean", size=30)
        c.text(x0 + 16, y0 + 172, f"{lo}–{str(hi)[2:]}", size=34)

    def map_window(self, c: Canvas, k: float, calm: float):
        th = self.th
        x0, y0, x1, y1 = c.window(*MAP_WIN, "Europe.Soil · summer, top metre")
        i = int(np.floor(k))
        a = k - i
        f = (1 - a) * self.frac[i] + a * self.frac[min(i + 1, len(self.frac) - 1)]
        step = np.clip(np.floor(((1 - calm) * f - 0.1) * 10 + 0.5), 0, STEPS).astype(int)
        for x, y in self.other_xy:
            c.fill(x - 1, y - 1, x + 1, y + 1, th.levels[1])
        for (x, y), s in zip(self.dot_xy, step):
            c.fill(x - 1 - s, y - 1 - s, x + 1 + s, y + 1 + s, th.hot if s else th.ink)
        # on open sea: the share of Europe in soil drought, and the dot sizes
        x, y, w, h = STATS
        c.fill(x, y, x + w, y + h, th.paper)
        if calm < 0.5:
            area = np.interp(k, np.arange(len(self.win_area)), self.win_area)
            hi = int(self.ends[int(round(k))])
            c.text(x + 4, y + 104, f"{area:.0f}%", GROTESK, 110, th.hot)
            c.text(x + 8, y + 144, "of Europe in drought", size=30)
            c.text(x + 8, y + 178, f"avg summer {hi - 9}–{str(hi)[2:]}", size=30)
        x, y, w, h = LEGEND
        c.fill(x, y, x + w, y + h, th.paper)
        c.text(x + 8, y + 30, "dry summers of 10:", size=28)
        for j, (s, label) in enumerate(((0, "1"), (2, "3"), (4, "5+"))):
            cx = x + 16 + j * 84
            c.fill(cx - 1 - s, y + 58 - s, cx + 1 + s, y + 60 + s, th.hot if s else th.ink)
            c.text(cx + 14, y + 70, label, size=30)

    def link_window(self, c: Canvas, t: float):
        th = self.th
        t0, t1 = self.starts[3], self.starts[4]
        if not np.isfinite(t) or t < t0 or t >= t1 + self.open:
            return
        x, y, w, h = LINK_WIN
        if t < t0 + self.open:
            return c.opening(x, y, w, h, prog(t, t0, self.open))
        if t >= t1:
            return c.opening(x, y, w, h, 1 - prog(t, t1, self.open))
        x0, y0, x1, y1 = c.window(x, y, w, h, "Link.Plot · one dot per summer")
        dt = t - t0 - self.open
        c.text(x0 + 16, y0 + 96, f"+{self.per:.0f}%", GROTESK, 100, th.hot)
        c.text(x0 + 20, y0 + 134, "of Europe in drought per +1 °C", size=30)
        c.text(x0 + 20, y0 + 166, f"95 % range: +{self.ci[0]:.0f} to +{self.ci[1]:.0f}", size=28)
        px0, px1, py0, py1 = x0 + 96, x1 - 34, y0 + 206, y1 - 78
        gx = lambda g: px0 + (g + 0.2) / 1.8 * (px1 - px0)  # noqa: E731
        gy = lambda a: py1 - a / 50 * (py1 - py0)  # noqa: E731
        c.fill(px0, py1, px1, py1 + 1, th.ink)
        c.fill(px0, py0, px0 + 1, py1, th.ink)
        for g in (0, 0.5, 1.0, 1.5):
            c.text(gx(g), py1 + 36, f"{g:g}", size=30, anchor="ms")
        c.text(px1, py1 + 68, "global temperature, °C", size=28, anchor="rs")
        for a in (0, 25, 50):
            c.text(px0 - 12, gy(a) + 10, f"{a}%", size=30, anchor="rs")
        years, area, gmt = self.d["years"], 100 * self.d["area"], self.d["gmt"]
        shown = int(len(years) * ease(prog(dt, 0, 1.6)))
        recent = years > years[-1] - soil.DECADE
        for i in range(shown):
            r = 4 if recent[i] else 3
            c.fill(gx(gmt[i]) - r, gy(area[i]) - r, gx(gmt[i]) + r, gy(area[i]) + r, th.hot if recent[i] else th.ink)
        line = ease(prog(dt, 1.7, 0.7))
        for g in np.linspace(gmt.min(), gmt.max(), 50)[:int(50 * line)]:
            a = 100 * (self.d["icept"] + self.d["slope"] * g)
            c.fill(gx(g) - 2, gy(a) - 2, gx(g) + 2, gy(a) + 2, th.hot)
        for yr in NAMED:
            i = int(np.flatnonzero(years == yr)[0])
            if i < shown:
                c.text(gx(gmt[i]) - 10, gy(area[i]) + 8, f"{yr}", size=30, anchor="rs")

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]):
        c = Canvas(s, self.th, 1.0, (0.0, 0.0), size)
        c.pixels(0, 620, self.dots, self.th.dots)
        i = self.scene(t)
        dt = t - self.starts[i] if np.isfinite(t) else np.inf
        k = self.window_at(t)
        self.gmt_window(c, t, k)
        self.map_window(c, k, self.calm(t))
        self.link_window(c, t)
        c.text(LEFT, 1584, SOURCES, MONO, 20, self.th.head)
        c.text(LEFT, 1610, f"Soil drought: summer (Jun–Aug) water in the top metre below its "
                           f"{soil.BASE[0]}–{str(soil.BASE[1])[2:]} 10th percentile.", MONO, 18, self.th.head)
        c.text(LEFT, 1634, f"A stable climate: {self.was:.0f} % of Europe in drought in an average summer.",
               MONO, 18, self.th.head)
        caption_band(c, self.th, self.S.scenes, i, dt, self.S.os_name)
        return c.im


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="feld", choices=list(onebit.THEMES), help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and seven frames only, no video")
    args = ap.parse_args()
    film = SoilFilm(soil.compute(), onebit.THEMES[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"europe_soil_{args.theme}"
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (st[1] + 0.5, st[1] + 2.5, st[2] + 0.3, st[2] + 5, st[2] + 10, st[3] + 3.5, st[4] + 3):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
        print("saved", f"{base}_t*.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="music")


if __name__ == "__main__":
    main()
