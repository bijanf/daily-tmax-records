"""HEAT'S TOLL: the heat deaths of Europe's cities in summer 2026, one square per hundred people.

The numbers are published estimates, not ours. Imperial College London and the London School
of Hygiene & Tropical Medicine (Barnes et al., Nature Health, October 2026) take the observed
temperatures of 854 cities in the EU-27, the UK, Norway and Switzerland (173 million people,
about 40 % of their population), run them through city- and age-specific temperature-mortality
curves, and compare with the same summer in a climate without human-made warming. June to
August 2026: 50,391 heat deaths, 32,619 (65 %) of them added by the warming. The countries come
from RTE's report of the study (23 October 2026). Summer 2022 in the same cities: about 29,000
(German press report of the study, 23 October 2026); RTE: 2026 is more than 70 % above 2022, and
the warming's share alone exceeds all of 2022. Model estimates for cities only: the true toll is
higher.

A still 1-bit desktop: two windows that never move. On top 504 squares, one per hundred people:
a hollow square for a death, a solid one for a death the warming added. Below, the count, then
the five countries hit hardest, then all of 2022 against the warming's share of 2026. Five
scenes, 11 bars of 96 BPM = 27.5 s, with onebit_bell's bells and clock: each row of squares a
bell, a toll when the squares turn solid and when the warming's share passes 2022. The last
scene holds the answer for three bars while the music comes home to A minor and goes quiet.

    outputs/onebit/social/eu_heat_toll_<theme>_reel.mp4, _cover.png, _music.wav

    python -I src/onebit_heat.py                  # Ziegel.1bit, 27.5 s
    python -I src/onebit_heat.py --stills         # cover and seven frames, no video
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

import onebit  # noqa: E402
from onebit import (FULL, GROTESK, LEFT, MONO, OUT, PIXEL, SIZES, SOCIAL_CRF, Canvas, Scene, Timeline,  # noqa: E402
                    caption_band)

# the published estimates (see the docstring for the sources)
TOTAL, WARMING, Y2022 = 50_391, 32_619, 29_000
COUNTRIES = (("Italy", 13_303), ("France", 7_268), ("Spain", 6_824), ("Germany", 6_340), ("UK", 4_354))
HOME = "Germany"                    # the account's country: its name in inverse video
PER = 100                           # people per square
COLS, ROWS = 28, 18                 # 504 squares
SQUARES, SOLID = round(TOTAL / PER), round(WARMING / PER)
assert SQUARES == COLS * ROWS

# tempo, scene lengths (bars), beats before the rows fill and per row, before the squares turn
# solid and per row, before the countries and per country, caption size
PACE = dict(bpm=96, bars=(2, 2, 2, 2, 3), lead=1, row=1 / 4, wait=1, turn=1 / 4, country=1, caption=1.2)
SCENES = (("How many people did {this summer's heat} kill?", "an estimate for 854 European cities"),
          ("{50,391} deaths in one summer", "each square: 100 people"),
          ("{2 in 3} from human-made warming", "solid square: deaths the warming added"),
          ("Hit hardest: {Italy}", "estimated heat deaths, June–August 2026"),
          ("Warming's share alone: {more than all of 2022}", "Follow for more climate data in 1-bit"))
SOURCES = "Estimates: Imperial College London · LSHTM (Nature Health, 2026)"
TOLL_WIN = (60, 628, 960, 630)      # x, y, w, h: both windows stand still all film long
COUNT_WIN = (60, 1272, 960, 290)
PITCH, SQ, STROKE = 32, 24, 3       # the squares: grid pitch, side, outline of a hollow one
GRID = (92, 666)                    # top-left square
HATCH = np.add.outer(np.arange(80), np.arange(1200)) // 3 % 2 == 0      # MacPaint-style diagonal fill


class HeatFilm:
    """Draws the film; exposes L, S, bpm, melody() and hits for onebit_bell."""

    def __init__(self, th: onebit.Theme):
        self.th = th
        self.bpm = PACE["bpm"]
        self.beat = 60 / self.bpm
        scenes = tuple(Scene(b, FULL, title, line) for b, (title, line) in zip(PACE["bars"], SCENES))
        starts = np.cumsum([0.0] + [sc.bars * 4 * self.beat for sc in scenes])
        self.starts = starts
        self.L = Timeline(0, 0, 0, 0, 0, end=float(starts[-1]), camera=((0.0, FULL),),
                          scenes=tuple(float(t) for t in starts[:-1]))
        self.S = SimpleNamespace(scenes=scenes, os_name="EU.HEAT.TOLL", lang="en", race=[])
        b = self.beat
        self.hits = [float(starts[2]) + PACE["wait"] * b, float(starts[4]) + 2 * b]
        dots = np.zeros((1920 - 620, 1080), bool)
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        dots[1562 - 620:1620 - 620] = False
        self.dots = dots

    # ── time: everything steps, nothing glides ──

    def scene(self, t: float) -> int:
        return int(np.searchsorted(self.starts[:-1], t, side="right")) - 1 if np.isfinite(t) else 0

    def steps(self, t: float, i: int, lead: float, per: float, n: int) -> int:
        """How many steps of scene i have happened at t: the first after `lead` beats, then one
        every `per` beats; all n outside the scene."""
        if not np.isfinite(t) or self.scene(t) != i:
            return n
        k = np.floor((t - self.starts[i] - lead * self.beat) / (per * self.beat)) + 1
        return int(np.clip(k, 0, n))

    def rows_at(self, t: float) -> int:
        """Rows of squares standing: one more per sixteenth note in scene 2."""
        return self.steps(t, 1, PACE["lead"], PACE["row"], ROWS)

    def solid_at(self, t: float) -> int:
        """Solid squares: none while the rows fill, then a row more per sixteenth in scene 3."""
        if np.isfinite(t) and self.scene(t) == 1:
            return 0
        return min(SOLID, COLS * self.steps(t, 2, PACE["wait"], PACE["turn"], -(-SOLID // COLS)))

    def melody(self):
        """(time, step, length, gain): each row a bell climbing the scale, each solid row one
        falling, each country a bell the lower the more deaths, then 2022 and 2026."""
        out, b, st = [], self.beat, self.starts
        for k in range(ROWS):
            out.append((st[1] + (PACE["lead"] + k * PACE["row"]) * b, k // 2, 0.6, 0.22))
        for k in range(-(-SOLID // COLS)):
            out.append((st[2] + (PACE["wait"] + k * PACE["turn"]) * b, 7 - k, 0.8, 0.32))
        top = COUNTRIES[0][1]
        for j, (_, n) in enumerate(COUNTRIES):
            out.append((st[3] + (PACE["lead"] + j * PACE["country"]) * b, int(round(6 - 6 * n / top)), 1.5, 0.55))
        out += [(st[4] + 1 * b, 2, 1.5, 0.45), (st[4] + 2 * b, 0, 2.0, 0.6)]
        return out

    # ── drawing ──

    def square(self, c: Canvas, x, y, solid: bool):
        th = self.th
        c.fill(x, y, x + SQ, y + SQ, th.ink)
        if not solid:
            c.fill(x + STROKE, y + STROKE, x + SQ - STROKE, y + SQ - STROKE, th.paper)

    def toll_window(self, c: Canvas, t: float):
        c.window(*TOLL_WIN, "Heat.Toll")
        rows, solid = self.rows_at(t), self.solid_at(t)
        for k in range(rows * COLS):
            r, q = divmod(k, COLS)
            self.square(c, GRID[0] + q * PITCH, GRID[1] + r * PITCH, k < solid)

    def legend(self, c: Canvas, x, y, solid: bool):
        """What a square means, in the corner of the count window."""
        self.square(c, x, y - SQ + 4, False)
        c.text(x + SQ + 12, y, "100 people", size=32)
        if solid:
            self.square(c, x, y + 44 - SQ + 4, True)
            c.text(x + SQ + 12, y + 44, "100 added by warming", size=32)

    def count_window(self, c: Canvas, t: float):
        th = self.th
        x0, y0, x1, y1 = c.window(*COUNT_WIN, "Count")
        i = self.scene(t)
        if i in (0, 1, 2):
            if i == 2:
                n = WARMING if self.solid_at(t) == SOLID else self.solid_at(t) * PER
                label, sub = "deaths the warming added", "65 % · two in every three"
            else:
                rows = self.rows_at(t)
                n = TOTAL if rows == ROWS else rows * COLS * PER
                label, sub = "estimated heat deaths", "854 cities · June–August 2026"
            c.text(x0 + 14, y0 + 116, f"{n:,}", GROTESK, 110, th.ink)
            c.text(x0 + 20, y0 + 168, label, size=34)
            c.text(x0 + 20, y0 + 206, sub, size=30)
            self.legend(c, x1 - 330, y0 + 60, i != 1)
            return
        if i == 3:                                       # the five countries, one per beat
            shown = self.steps(t, 3, PACE["lead"], PACE["country"], len(COUNTRIES))
            top, bx, wmax = COUNTRIES[0][1], x0 + 200, 520
            for j, (name, n) in enumerate(COUNTRIES[:shown]):
                y = y0 + 44 + j * 48
                if name == HOME:
                    c.chip(x0 + 14, y, name, 34, fg=th.field, bg=th.ink, pad=4)
                else:
                    c.text(x0 + 18, y, name, size=34)
                w = wmax * n / top
                c.fill(bx, y - 28, bx + w, y + 2, th.ink)
                c.text(bx + w + 14, y + 2, f"{n:,}", GROTESK, 40, th.ink)
            return
        shown = self.steps(t, 4, 1, 1, 2)                # 2022, then the warming's share of 2026
        scale = 600 / WARMING
        rows = (("summer 2022 · all heat deaths", Y2022, True, f"about {Y2022:,}"),
                ("summer 2026 · added by warming alone", WARMING, False, f"{WARMING:,}"))
        for j, (label, n, hatched, number) in enumerate(rows[:shown]):
            y = y0 + 40 + j * 116
            c.text(x0 + 18, y, label, size=32)
            w, a, b = scale * n, y + 14, y + 64
            if hatched:
                c.pixels(x0 + 18, a, HATCH[:b - a, :int(w)], th.ink)
                c.frame(x0 + 18, a, x0 + 18 + w, b)
            else:
                c.fill(x0 + 18, a, x0 + 18 + w, b, th.ink)
            c.text(x0 + 18 + w + 14, b - 6, number, GROTESK, 44, th.ink)

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]):
        c = Canvas(s, self.th, 1.0, (0.0, 0.0), size)
        c.pixels(0, 620, self.dots, self.th.dots)
        i = self.scene(t)
        dt = t - self.starts[i] if np.isfinite(t) else np.inf
        self.toll_window(c, t)
        self.count_window(c, t)
        c.text(LEFT, 1596, SOURCES, MONO, 20, self.th.head)
        caption_band(c, self.th, self.S.scenes, i, dt, self.S.os_name, "en", PACE["caption"])
        return c.im


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="ziegel1", choices=list(onebit.THEMES), help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and seven frames only, no video")
    args = ap.parse_args()
    film = HeatFilm(onebit.THEMES[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"eu_heat_toll_{args.theme}"
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (st[1] + 1.2, st[1] + 2.0, st[2] + 1.6, st[2] + 4.0, st[3] + 2.5, st[4] + 2.0, st[5] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
        print("saved", f"{base}_t*.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="bell")


if __name__ == "__main__":
    main()
