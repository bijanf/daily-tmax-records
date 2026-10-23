"""HEAT'S TOLL: the heat deaths of Europe's cities in summer 2026, one square per hundred deaths.

The numbers are published estimates, not ours. Imperial College London and the London School
of Hygiene & Tropical Medicine take the observed temperatures of 854 cities in the EU-27, the
UK, Norway and Switzerland, run them through city- and age-specific temperature-mortality
curves, and compare with the same summer in a climate without human-made warming. Sources:

- Summer 2026 (June to August): 50,391 heat-related excess deaths, "around two thirds"
  attributable to human-induced climate change. Barnes et al., "Heat-related urban mortality
  attributable to human-induced climate change in Europe in summer 2026", Grantham Institute
  report, 23 October 2026, accepted in Nature Health,
  https://spiral.imperial.ac.uk/handle/10044/1/147042
- The attributable count (32,619, 65 %) and the countries (Italy 13,303, France 7,268,
  Spain 6,824, Germany 6,340, UK 4,354): the study as reported by RTÉ News (Ireland),
  23 October 2026, https://www.rte.ie/news/environment/2026/1023/1596522-heat-related-deaths-europe/
- Summer 2022 in the same cities with the same method: 29,480 (95 % range 26,643–32,006),
  the highest of 2000-2025. Barnes et al., "Heat-related urban mortality attributable to
  human-induced climate change in Europe from 2000 to 2025", Nature Health (2026),
  doi:10.1038/s44360-026-00209-8

Model estimates for cities only, not counted deaths. Estimates of 2022 for all of Europe are
larger, so the comparison holds only within these 854 cities.

A still 1-bit desktop: two windows that never move. On top 504 squares, one per hundred deaths
(rounded): hollow for a death, solid for a death the warming added. Below, the count, then the
five countries with the most deaths, then all of summer 2022 against the warming's share of
2026. The first scene shows the finished picture under the question, so the last frame loops
into the first. Five scenes, 11 bars of 96 BPM = 27.5 s, with onebit_bell's bells and clock:
each row of squares a bell, a toll when the squares first turn solid and when the warming's
share passes 2022. The last scene holds the answer for three bars while the music comes home
to A minor and fades.

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
from onebit import (FULL, GROTESK, LEFT, MONO, OUT, SIZES, SOCIAL_CRF, Canvas, Scene, Timeline,  # noqa: E402
                    caption_band)

# the published estimates (see the docstring for the sources)
TOTAL, WARMING, Y2022, CITIES = 50_391, 32_619, 29_480, 854
COUNTRIES = (("Italy", 13_303), ("France", 7_268), ("Spain", 6_824), ("Germany", 6_340), ("UK", 4_354))
SHARE = round(100 * WARMING / TOTAL)            # 65 %: a little under two in three
PER = 100                                       # deaths per square
COLS, ROWS = 28, 18                             # 504 squares
SQUARES, SOLID = round(TOTAL / PER), round(WARMING / PER)
assert SQUARES == COLS * ROWS and WARMING > Y2022

# tempo, scene lengths (bars), beats before the rows fill and per row, before the squares turn
# solid and per row, before the countries and per country, caption size
PACE = dict(bpm=96, bars=(2, 2, 2, 2, 3), lead=1, row=1 / 4, wait=1, turn=1 / 4, country=1, caption=1.2)
SCENES = (("How many people did {this summer’s heat} kill?", f"a model estimate for {CITIES} European cities"),
          (f"An estimated {{{TOTAL:,}}} heat deaths", f"each square: {PER} deaths (rounded)"),
          ("{Almost 2 in 3} deaths from human-made warming", f"solid square: {PER} deaths added by warming"),
          ("Most deaths: {Italy}", "estimated heat deaths, June–August 2026"),
          ("Warming alone: more than {all of summer 2022}", "Follow for more climate data in 1-bit"))
SOURCES = "Estimates: Barnes et al., Imperial College London · LSHTM, 2026"
TOLL_WIN = (60, 628, 900, 594)      # x, y, w, h: both windows stand still all film long, clear of
COUNT_WIN = (60, 1236, 900, 290)    # the app's buttons on the right and its caption at the bottom
FOOTER = 1560                       # baseline of the source line
PITCH, SQ, STROKE = 30, 23, 3       # the squares: grid pitch, side, outline of a hollow one
GRID = (93, 669)                    # top-left square: the grid centred in the toll window
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
        dots[FOOTER - 34 - 620:FOOTER + 24 - 620] = False
        self.dots = dots

    # ── time: everything steps, nothing glides ──
    # Scenes are counted from 0 in the code: 0 the question, 1 the count, 2 the warming's share,
    # 3 the countries, 4 summer 2022 against 2026.

    def scene(self, t: float) -> int:
        return int(np.searchsorted(self.starts[:-1], t, side="right")) - 1 if np.isfinite(t) else 0

    def steps(self, t: float, i: int, lead: float, per: float, n: int) -> int:
        """How many steps of scene i have happened at t: the first after `lead` beats, then one
        every `per` beats. Outside scene i all n: every other scene shows the finished picture,
        the question included."""
        if not np.isfinite(t) or self.scene(t) != i:
            return n
        k = np.floor((t - self.starts[i] - lead * self.beat) / (per * self.beat)) + 1
        return int(np.clip(k, 0, n))

    def rows_at(self, t: float) -> int:
        """Rows of squares standing: one more per sixteenth note in scene 1."""
        return self.steps(t, 1, PACE["lead"], PACE["row"], ROWS)

    def solid_at(self, t: float) -> int:
        """Solid squares: none while the rows fill (scene 1), then a row more per sixteenth note
        in scene 2."""
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
        c.text(x + SQ + 12, y, f"{PER} deaths", size=36)
        if solid:
            self.square(c, x, y + 46 - SQ + 4, True)
            c.text(x + SQ + 12, y + 46, f"{PER} added by warming", size=36)

    def count_window(self, c: Canvas, t: float):
        th = self.th
        x0, y0, x1, y1 = c.window(*COUNT_WIN, "Count")
        i = self.scene(t)
        if i in (0, 1, 2):
            if i == 2:
                n = WARMING if self.solid_at(t) == SOLID else self.solid_at(t) * PER
                label, sub = "deaths added by warming", f"{SHARE} % · almost two in three"
            else:
                rows = self.rows_at(t)
                n = TOTAL if rows == ROWS else rows * COLS * PER
                label, sub = "estimated heat deaths", f"{CITIES} cities · June to August 2026"
            c.text(x0 + 14, y0 + 116, f"{n:,}", GROTESK, 110, th.ink)
            c.text(x0 + 20, y0 + 170, label, size=40)
            c.text(x0 + 20, y0 + 214, sub, size=36)
            self.legend(c, x1 - 390, y0 + 60, i != 1)
            return
        if i == 3:                                       # the five countries, one per beat
            shown = self.steps(t, 3, PACE["lead"], PACE["country"], len(COUNTRIES))
            top, bx, wmax = COUNTRIES[0][1], x0 + 200, 480
            for j, (name, n) in enumerate(COUNTRIES[:shown]):
                y = y0 + 44 + j * 48
                c.text(x0 + 18, y, name, size=38)
                w = wmax * n / top
                c.fill(bx, y - 28, bx + w, y + 2, th.ink)
                c.text(bx + w + 14, y + 2, f"{n:,}", GROTESK, 40, th.ink)
            return
        shown = self.steps(t, 4, 1, 1, 2)                # 2022, then the warming's share of 2026
        scale = 560 / WARMING
        rows = (("summer 2022 · all heat deaths, same cities", Y2022, True),
                ("summer 2026 · added by warming alone", WARMING, False))
        for j, (label, n, hatched) in enumerate(rows[:shown]):
            y = y0 + 40 + j * 116
            c.text(x0 + 18, y, label, size=36)
            w, a, b = scale * n, y + 14, y + 64
            if hatched:
                c.pixels(x0 + 18, a, HATCH[:b - a, :int(w)], th.ink)
                c.frame(x0 + 18, a, x0 + 18 + w, b)
            else:
                c.fill(x0 + 18, a, x0 + 18 + w, b, th.ink)
            c.text(x0 + 18 + w + 14, b - 6, f"{n:,}", GROTESK, 44, th.ink)

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]):
        c = Canvas(s, self.th, 1.0, (0.0, 0.0), size)
        c.pixels(0, 620, self.dots, self.th.dots)
        i = self.scene(t)
        dt = t - self.starts[i] if np.isfinite(t) else np.inf
        self.toll_window(c, t)
        self.count_window(c, t)
        c.text(LEFT, FOOTER, SOURCES, MONO, 22, self.th.head)
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
        for t in (st[1] + 1.2, st[1] + 4.0, st[2] + 1.6, st[2] + 4.0, st[3] + 4.0, st[4] + 2.0, st[5] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
        print("saved", f"{base}_t*.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="bell")


if __name__ == "__main__":
    main()
