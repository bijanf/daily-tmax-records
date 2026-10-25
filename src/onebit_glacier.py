"""ALPENGLETSCHER: about 31 m of ice lost from 1976 to 2024, almost half of it in 2015-2024.

glacier.py: the area-weighted mean mass balance of the 3,892 Alpine glaciers in Dussaillant et
al. (2025): -27.8 +- 3.6 m water equivalent from 1976 to 2024, 46 % of it in 2015-2024. Drawn
as ice thickness at the density of pure ice (900 kg/m3: 31 m; at 850 kg/m3, the density used to
turn elevation change into mass, 33 m): "rund 31 Meter", the footer naming the density.

A slow, still slide on the Slides frame. Under the title a block of ice with the 1976 surface
dashed above it; a slanted cut through its foot says the ice goes on below (how thick the glaciers
still are is not shown). In the second scene the surface sinks year by year (gaining in the few good
years), the ice above it turning lilac, and once it reaches 2024 a ten-storey house (3 m a
floor) stands in the gap for scale. In the third scene the last ten years' slice turns dark.
Three scenes, 8 bars of 60 BPM = 32 s.

    outputs/onebit/social/alps_glacier_<theme>_de_reel.mp4, _cover.png

    python -I src/onebit_glacier.py --no-music
    python -I src/onebit_glacier.py --stills
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

import glacier  # noqa: E402
import onebit  # noqa: E402
from onebit import GROTESK, OUT, SIZES, SOCIAL_CRF, TEXT, Canvas  # noqa: E402
from onebit_slides import COLOURS, LEFT, RIGHT, RULE, WIN, Slides  # noqa: E402

ICE = 0.9                                         # m of ice per m of water equivalent / 0.9 (900 kg/m3)
LAST10 = (2015, 2024)
EXPECT = dict(ice=31, last10=46)                  # the published numbers: m, %
PACE = dict(bpm=60, bars=(2.5, 3.5, 2), lead=1, steps=9.0)   # beats before the sinking; its length (s)
SCALE = 18                                        # px per m of ice
FLOOR = 3                                         # m a storey


def words(ice: float, glaciers: int) -> dict:
    nb = "\u00a0"
    return dict(scenes=(("Wie viel Eis fehlt den // {Alpengletschern?}", ""),
                        (f"Von 1976 bis 2024: // {{rund {ice:.0f}{nb}Meter Eis weg}}", ""),
                        (f"Fast die Hälfte davon // {{allein {LAST10[0]}–{LAST10[1]}}}", "")),
                follow="Folge mir für mehr Klimadaten",
                head="Mittlerer Verlust an Eisdicke",
                surface="Oberfläche 1976", now="Oberfläche 2024", house="10 Stockwerke",
                sources=(f"Daten: Dussaillant et al. 2025, ESSD (WGMS) · {glaciers:,} Gletscher der Alpen".replace(",", "."),
                         "Massenbilanz 1976–2024, Flächenmittel, in Eis umgerechnet (Dichte 900 kg/m³)"))


class GlacierFilm(Slides):
    """Draws the film; exposes L, S, bpm and appear() for onebit.video."""

    def __init__(self, th: onebit.Theme, colour: dict):
        b = glacier.balance()
        # m of ice lost, from the 1976 surface (0) to the end of each year 1976-2024
        self.levels = [0.0] + list(-b["cum"].values / ICE)
        self.labels = [int(b.index[0])] + [int(y) for y in b.index]   # the year shown with each level
        self.ice = -b["cum"] / ICE
        total = float(self.ice.iloc[-1])
        last10 = 100 * float(b.loc[LAST10[0]:LAST10[1], "mb"].sum() / b["cum"].iloc[-1])
        got = dict(ice=int(round(total)), last10=int(round(last10)))
        assert got == EXPECT, f"the data now give {got}, the published reel {EXPECT}: check before rendering"
        assert 40 <= last10 < 50, "the title says almost half"
        self.setup(th, "de", colour, words(total, len(glacier.table())), PACE, "Alpen.Gletscher")
        t0 = float(self.starts[1]) + PACE["lead"] * self.beat
        n = len(self.levels)
        self.steps = [t0 + PACE["steps"] * k / (n - 1) for k in range(n)]   # one per level
        self.done = self.steps[-1] - float(self.starts[1]) + 0.5
        assert self.steps[-1] < self.starts[2] - 2 * self.beat, "the sinking must end with time to read"
        self.surface = RULE + 24 + 230                     # y of the 1976 surface
        self.base = WIN[1] + WIN[3] - 40                   # the drawn ice ends here: it goes on below
        assert self.y(self.labels[-1]) < self.base - 80, "some ice must be left to see"

    def later(self, i: int) -> float:
        """The second scene's number once the surface has reached 2024."""
        return self.done if i == 1 else super().later(i)

    def level_at(self, t: float) -> int:
        """Which level the surface stands at: 0 (1976) before the sinking, the last after it."""
        i = self.scene(t)
        if i < 1:
            return 0
        if i > 1:
            return len(self.levels) - 1
        return max(0, int(np.searchsorted(self.steps, t, side="right")) - 1)

    def y(self, year: int) -> float:
        """The surface at the end of that year on screen."""
        return self.surface + float(self.ice.loc[year]) * SCALE

    def body(self, c: Canvas, t: float):
        th, col = self.th, self.colour
        i = self.scene(t)
        k = self.level_at(t)
        year = self.labels[k]
        mid = (LEFT + RIGHT) / 2
        x0, x1 = LEFT + 30, LEFT + 370                     # the ice
        self.say(c, mid, self.surface - 170, self.words["head"], 40, True, th.ink, "ms")
        c.text(x1, self.surface - 70, str(year), GROTESK, 72, th.ink, "rs")
        # the ice, its lost part and, in the last scene, the last ten years' slice
        top = self.surface + self.levels[k] * SCALE
        c.fill(x0, self.surface, x1, top, col["ramp"][0])
        if i == 2:
            a, b = self.y(LAST10[0] - 1), self.y(LAST10[1])
            c.fill(x0, a, x1, b, col["ramp"][2])
            c.text((x0 + x1) / 2, (a + b) / 2 + 12, f"{LAST10[0]}–{LAST10[1]}", TEXT, 36, th.field, "ms")
        c.fill(x0, top, x1, self.base - 12, col["snow"])
        for k in range(0, x1 - x0, 24):                    # a ragged foot: the ice goes on below
            c.fill(x0 + k, self.base - 12, x0 + k + 12, self.base, col["snow"])
        self.cut(c, x0, x1, self.base - 70)
        # the 1976 surface, dashed
        for x in range(int(x0) - 20, int(x1) + 20, 16):
            c.fill(x, self.surface - 2, x + 9, self.surface + 1, th.ink)
        c.text(x0 - 20, self.surface - 14, self.words["surface"], TEXT, 32, th.ink)
        # the house, once the surface has reached 2024: ten floors of 3 m on the surface of 2024,
        # with that surface dashed from the ice to the house
        if self.settled(t):
            ground = self.y(self.labels[-1])
            for x in range(int(x1), int(x1) + 50 + 150, 16):
                c.fill(x, ground - 1, x + 9, ground + 2, th.ink)
            c.text(x1 + 50, ground + 40, self.words["now"], TEXT, 32, th.ink)
            self.house(c, x1 + 50, ground)

    def cut(self, c: Canvas, x0: float, x1: float, y: float):
        """A slanted gap across the ice, as on a broken axis: not to scale, the ice goes on."""
        w, h = int(x1 - x0) + 24, 48
        xs, ys = np.meshgrid(np.arange(w), np.arange(h))
        mid = h / 2 - 0.08 * (xs - w / 2)
        c.pixels(x0 - 12, y - h / 2, np.abs(ys - mid) < 5, self.th.field)

    def house(self, c: Canvas, x: float, ground: float):
        th = self.th
        w, fh = 150, FLOOR * SCALE
        c.frame(x, ground - 10 * fh, x + w, ground, fill=th.paper)
        for k in range(10):                                # floors and two windows each
            y = ground - (k + 1) * fh
            c.fill(x, y, x + w, y + 2, th.ink)
            for wx in (x + 28, x + w - 58):
                c.fill(wx, y + 18, wx + 30, y + fh - 14, th.ink)
        c.text(x + w + 14, ground - 5 * fh + 12, self.words["house"], TEXT, 34, th.ink)
        assert x + w + 14 + c.width(self.words["house"], TEXT, 34) <= RIGHT, "the house's label leaves the window"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="flieder", choices=list(COLOURS), help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    ap.add_argument("--no-music", action="store_true", help="a silent audio track: music is added in the app")
    args = ap.parse_args()
    assert args.stills or args.no_music, "no soundtrack for this film yet: use --no-music, music is added in the app"
    film = GlacierFilm(onebit.THEMES[args.theme], COLOURS[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"alps_glacier_{args.theme}_de"
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (st[1] + 4.0, st[1] + film.done + 1.5, st[2] + 4.0, st[-1] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
        print("saved", f"{base}_t*.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
