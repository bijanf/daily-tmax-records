"""HEAT vs COLD: one reel, one comparison. Every daily record since 2020 is one pixel.

Two 1-bit windows side by side, heat records on the left and cold records on the right,
fill in the order the records were set while a clock runs from 1 January 2020 to the latest
data: heatwaves arrive as bursts of red pixels, and can be heard. A dashed line in each
window marks what a stable climate would give; heat runs far past it, cold stops short. A
result window then shows the ratio, and one sentence closes. No zoom: the data moves, the
camera does not. Four scenes, 20 bars of 128 BPM = 37.5 s, with onebit_audio's soundtrack.

    outputs/onebit/social/europe_race_<theme>_reel.mp4, _cover.png, _music.wav

    python -I src/onebit_race.py                 # TS.Pink (matte)
    python -I src/onebit_race.py --theme beton
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import findings  # noqa: E402
import onebit  # noqa: E402
from onebit import (BAR, FOLLOW, FULL, GROTESK, LEFT, MONO, OUT, RIGHT, SIZES, SOCIAL_CRF, Canvas, Scene,  # noqa: E402
                    Timeline, caption_band, ease, prog)

SOURCES = "Data: NOAA GHCN-Daily · DWD · SMHI · KNMI · GeoSphere · MeteoSwiss"
COLS, CELL, DOT = 72, 6, 5                      # pixel grid: columns, cell and dot size (logical px)
WIN = {"heat": (60, 790, 465, 690), "cold": (555, 790, 465, 690)}
RESULT = (585, 1150, 405, 250)                  # inside the cold window, where its pixels never reach
SPARK = 0.35                                    # seconds a new record stays white before it turns red or blue


def records(f: dict, reg: str = "Europe") -> dict:
    """Dates of every daily heat and cold record set since 2020 (current holders, ties to the
    first year), the number a stable climate gives, and the stations."""
    fy = f["final_year"]
    rows = f["region"] == reg
    w = f["window"][rows]
    md = pd.date_range("2001-01-01", "2001-12-31")
    out = {}
    for kind, years in (("heat", f["hi_year"][rows]), ("cold", f["lo_year"][rows])):
        st, day = np.nonzero((years >= 2020) & w)
        y = years[st, day]
        dates = pd.to_datetime({"year": y, "month": md.month[day], "day": md.day[day]})
        out[kind] = np.sort(dates.to_numpy())
    expected = float(f["idx"].loc[rows, "expected_2020s"].sum())
    last = max(out["heat"].max(), out["cold"].max())
    return dict(heat=out["heat"], cold=out["cold"], expected=expected, n=int(rows.sum()), fy=fy,
                start=np.datetime64("2020-01-01"), end=last)


class RaceFilm:
    """Draws the film; exposes L, S, open and events() for onebit_audio's story soundtrack."""

    def __init__(self, D: dict, th: onebit.Theme):
        self.D, self.th = D, th
        heat, cold = len(D["heat"]), len(D["cold"])
        self.ratio = heat / cold
        scenes = (
            Scene(2, FULL, "Which records is Europe breaking: {heat} or [cold?]",
                  f"{D['n']} weather stations with 100+ years of data"),
            Scene(10, FULL, "Every pixel is one {broken record}",
                  "red: hottest day ever for that date · blue: the coldest"),
            Scene(4, FULL, f"{{{self.ratio:.0f} heat records}} for every cold one",
                  f"{heat:,} heat · {cold:,} cold · a stable climate gives about 1 : 1"),
            Scene(4, FULL, "Europe is breaking {heat records,} not [cold ones.]", FOLLOW["en"]),
        )
        starts = np.cumsum([0.0] + [sc.bars * BAR for sc in scenes])
        self.L = Timeline(0, 0, 0, 0, 0, end=float(starts[-1]), camera=((0.0, FULL),),
                          scenes=tuple(float(t) for t in starts[:-1]))
        self.S = SimpleNamespace(scenes=scenes, os_name="EU.HEAT.VS.COLD", lang="en", race=[])
        self.open = 0.4
        self.race = (starts[1] + 0.3, starts[2] - 0.4)          # the clock runs inside the race scene
        self.reveal = float(starts[2])
        self.hits = [self.reveal]
        # cell index of every grid pixel (-1 between dots), shared by both windows
        rows = int(np.ceil(max(heat, cold) / COLS))
        idx = np.full((rows * CELL, COLS * CELL), -1)
        for r in range(rows):
            for col in range(COLS):
                idx[r * CELL:r * CELL + DOT, col * CELL:col * CELL + DOT] = r * COLS + col
        self.cells = idx
        dots = np.zeros((1920 - 620, 1080), bool)
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        self.dots = dots

    # ── time ──

    def clock(self, t: float) -> np.datetime64:
        """The date the race has reached at time t."""
        if not np.isfinite(t):
            return self.D["end"]
        p = float(np.clip((t - self.race[0]) / (self.race[1] - self.race[0]), 0, 1))
        span = (self.D["end"] - self.D["start"]).astype("timedelta64[s]").astype(float)
        return self.D["start"] + np.timedelta64(int(p * span), "s")

    def events(self):
        """(time, heat records, cold records) per day of the race, for the soundtrack."""
        days = np.union1d(self.D["heat"], self.D["cold"])
        span = (self.D["end"] - self.D["start"]).astype("timedelta64[s]").astype(float)
        out = []
        for day in days:
            frac = (day - self.D["start"]).astype("timedelta64[s]").astype(float) / span
            out.append((self.race[0] + frac * (self.race[1] - self.race[0]),
                        int(np.sum(self.D["heat"] == day)), int(np.sum(self.D["cold"] == day))))
        return out

    # ── drawing ──

    def window(self, c: Canvas, kind: str, now, before):
        th = self.th
        x, y, w, h = WIN[kind]
        colour = th.hot if kind == "heat" else th.cold
        x0, y0, x1, y1 = c.window(x, y, w, h, f"{kind.upper()}.Records")
        dates = self.D[kind]
        n = int(np.searchsorted(dates, now, side="right"))
        fresh = int(np.searchsorted(dates, before, side="right"))   # records older than SPARK
        c.text(x0 + 14, y0 + 104, f"{n:,}", GROTESK, 100, colour)
        c.text(x0 + 16, y0 + 144, f"{kind} records since 2020", size=30)
        gx, gy = x0 + (x1 - x0 - COLS * CELL) / 2, y0 + 172
        c.pixels(gx, gy, (self.cells >= 0) & (self.cells < fresh), colour)
        c.pixels(gx, gy, (self.cells >= fresh) & (self.cells < n), th.ink)       # just set: a white flash
        # what a stable climate gives: a dashed line after that many pixels
        ey = gy + self.D["expected"] / COLS * CELL
        for xx in np.arange(gx, gx + COLS * CELL, 10):
            c.fill(xx, ey, xx + 6, ey + 2, th.head)
        label = f"stable climate · {self.D['expected']:,.0f}"
        lw = c.width(label, size=28)
        c.fill(gx + COLS * CELL - lw - 8, ey - 34, gx + COLS * CELL + 2, ey - 2, th.paper)
        c.text(gx + COLS * CELL, ey - 8, label, size=28, colour=th.head, anchor="rs")

    def date_strip(self, c: Canvas, now):
        th = self.th
        day = pd.Timestamp(now)
        c.text(LEFT, 722, day.strftime("%d %b %Y").upper(), size=66, colour=th.head)
        years = range(2020, self.D["fy"] + 1)
        cw = (RIGHT - 560) / len(years)
        for i, yr in enumerate(years):
            cx = 560 + i * cw
            c.frame(cx, 654, cx + cw - 6, 726)
            frac = np.clip((day.year - yr) + day.dayofyear / 366, 0, 1)
            c.fill(cx + 3, 657, cx + 3 + (cw - 12) * frac, 723, th.ink)
            c.text(cx + (cw - 6) / 2, 766, f"{yr}", size=34, colour=th.head, anchor="ms")

    def result(self, c: Canvas, t: float):
        x, y, w, h = RESULT
        dt = t - self.reveal
        if dt < 0:
            return
        if dt < self.open:
            return c.opening(x, y, w, h, prog(dt, 0, self.open))
        x0, y0, x1, y1 = c.window(x, y, w, h, "Result.Ratio 1.1")
        mid = (x0 + x1) / 2
        k = round(self.ratio * ease(prog(dt, self.open, 1.2)))
        c.text(mid, y0 + 150, f"{k} : 1", GROTESK, 140, self.th.hot, anchor="ms")
        c.text(mid, y0 + 200, "heat : cold records", size=32, anchor="ms")

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]):
        c = Canvas(s, self.th, 1.0, (0.0, 0.0), size)
        c.pixels(0, 620, self.dots, self.th.dots)
        starts = self.L.scenes
        i = int(np.searchsorted(starts, t, side="right")) - 1 if np.isfinite(t) else 0
        dt = t - starts[i] if np.isfinite(t) else np.inf
        now = self.clock(t)
        self.date_strip(c, now)
        for kind in ("heat", "cold"):
            self.window(c, kind, now, self.clock(t - SPARK))
        self.result(c, t)
        c.text(LEFT, 1524, SOURCES, MONO, 20, self.th.head)
        c.text(LEFT, 1554, f"{self.D['n']} European stations, each with 100+ years of daily data.", MONO, 18,
               self.th.head)
        c.text(LEFT, 1582, "A record: the hottest (coldest) day ever measured on that calendar date.", MONO, 18,
               self.th.head)
        caption_band(c, self.th, self.S.scenes, i, dt, self.S.os_name)
        return c.im


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="pink", choices=list(onebit.THEMES), help="colour theme")
    args = ap.parse_args()
    film = RaceFilm(records(findings.compute()), onebit.THEMES[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"europe_race_{args.theme}"
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="music")


if __name__ == "__main__":
    main()
