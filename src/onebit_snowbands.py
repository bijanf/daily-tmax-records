"""WO SCHWINDET DER SCHNEE: the Alps' spring snowpack by height, 1951-1980 against 2017-2026.

The snow on the ground in March and April (ERA5-Land snow water equivalent, mean of the two
months, 0.1 deg; snow.spring_bands) in the Alps (Natural Earth's outline), in four bands of the
grid cells' mean height, without the 45 cells still under snow in September, mostly the model's
glaciers: below
1,000 m it fell 71 %, at 1,000-1,500 m 43 %, at 1,500-2,000 m 21 %, above 2,000 m 12 %; below
1,500 m as a whole by about half (49.5 %). The lower, the larger the share lost: that order holds
for every baseline, month and band edge tried (30 variants: above 2,000 m -0.5 to -19 %); the
change above 2,000 m alone is not significant (Welch's t-test on the annual band means, 30
springs against 10: p 0.23). ERA5-Land runs a land model on ERA5's weather: sharper than ERA5, not
independent of it, and too snowy high up (Monteiro and Morin 2023).

A slow, still slide on the Slides frame. Under the title a mountain of four bars, the highest
band narrowest; each bar is the band's snow of 1951-1980. Then, one band a beat and a half from
the bottom up, each bar keeps only its middle, the share of snow still there, the rest turns
lilac, and the change stands in it. Three scenes, 8 bars of 60 BPM = 32 s.

    outputs/onebit/social/alps_bands_<theme>_de_reel.mp4, _cover.png

    python -I src/onebit_snowbands.py --no-music
    python -I src/onebit_snowbands.py --stills
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

import onebit  # noqa: E402
import snow  # noqa: E402
from onebit import GROTESK, OUT, SIZES, SOCIAL_CRF, Canvas  # noqa: E402
from onebit_slides import COLOURS, LEFT, RIGHT, RULE, WIN, Slides, span  # noqa: E402

THEN, NOW = (1951, 1980), (2017, 2026)
BANDS = ((2000, 5000), (1500, 2000), (1000, 1500), (0, 1000))   # top of the mountain first
LOW = (0, 1500)                                                  # the title's "below 1,500 m"
EXPECT = dict(bands=(-12, -21, -43, -71), low=-49)               # the published numbers (%)
PACE = dict(bpm=60, bars=(2.5, 3.5, 2), lead=1.5, per=1.5)       # beats before the first band, per band
WIDTHS = (420, 560, 700, 840)                                    # the bars, top to bottom
BAR_H, GAP = 168, 22


def label(lo: int, hi: int) -> str:
    if lo == 0:
        return f"unter {hi:,} m".replace(",", ".")
    if hi >= 5000:
        return f"über {lo:,} m".replace(",", ".")
    return f"{lo:,}–{hi:,} m".replace(",", ".")


def words() -> dict:
    nb = "\u00a0"
    return dict(scenes=(("Wo schwindet der // {Schnee in den Alpen?}", ""),
                        (f"Unter 1.500{nb}Metern: // {{rund die Hälfte weg}}", "Blau: bleibt · Lila: fehlt"),
                        ("Je tiefer, // {desto mehr fehlt}", "")),
                follow="Folge mir für mehr Klimadaten",
                head="Schnee am Boden im März und April",
                sources=("Daten: ERA5-Land, Monatsmittel, 0,1° (Copernicus/ECMWF) · Umriss: Natural Earth",
                         f"Wasser im Schnee, März–April: {span(NOW, 'de')} gegenüber {span(THEN, 'de')} · ohne Gletscher"))


class SnowBandsFilm(Slides):
    """Draws the film; exposes L, S, bpm and appear() for onebit.video."""

    def __init__(self, th: onebit.Theme, colour: dict):
        snow.use("snow_alps_land")
        b = snow.spring_bands("ALPS", BANDS, THEN, NOW)
        low = float(snow.spring_bands("ALPS", (LOW,), THEN, NOW)["change"].iloc[0])
        got = dict(bands=tuple(int(round(v)) for v in b["change"]), low=int(round(low)))
        assert got == EXPECT, f"the data now give {got}, the published reel {EXPECT}: check before rendering"
        assert -55 < low < -45, "the title says about half"
        assert (np.diff(b["change"].values) < 0).all(), "scene 3 says the lower, the more is missing"
        self.bands = b
        self.setup(th, "de", colour, words(), PACE, "Alpen.Schnee")
        self.turns = [float(self.starts[1]) + (PACE["lead"] + k * PACE["per"]) * self.beat for k in range(len(BANDS))]
        assert self.turns[-1] < self.starts[2] - 2 * self.beat, "the bands must have turned with time to read"
        self.done = self.turns[-1] - float(self.starts[1]) + 0.5
        height = len(BANDS) * BAR_H + (len(BANDS) - 1) * GAP
        room = WIN[1] + WIN[3] - 32 - (RULE + 24)
        self.top = RULE + 24 + (room - (height + 150)) // 2 + 100     # the heading and years above

    def later(self, i: int) -> float:
        """The second scene's second part once the bands below 1,500 m have turned (the first two:
        bands turn from the bottom), before most viewers have gone."""
        low = sum(1 for lo, hi in BANDS if hi <= LOW[1])
        return self.turns[low - 1] - float(self.starts[1]) + 0.5 if i == 1 else super().later(i)

    def turned(self, t: float) -> int:
        """How many bands have turned so far, from the bottom of the mountain."""
        i = self.scene(t)
        return 0 if i < 1 else len(BANDS) if i > 1 else int(np.searchsorted(self.turns, t, side="right"))

    def body(self, c: Canvas, t: float):
        th, col = self.th, self.colour
        mid = (LEFT + RIGHT) / 2
        n = self.turned(t)
        self.say(c, mid, self.top - 66, self.words["head"], 44, True, th.ink, "ms")
        years = f"{span(THEN, 'de')} → {span(NOW, 'de')}" if n else span(THEN, "de")   # from the first turn on
        c.text(mid, self.top - 18, years, GROTESK, 40, th.ink, "ms")
        for k, (_, row) in enumerate(self.bands.iterrows()):
            w = WIDTHS[k]
            x0, y0 = mid - w / 2, self.top + 12 + k * (BAR_H + GAP)
            down = len(BANDS) - 1 - k < n                 # bands turn from the bottom up
            c.fill(x0, y0, x0 + w, y0 + BAR_H, col["ramp"][0] if down else col["snow"])
            if down:                                      # the snow still there, in the middle
                keep = w * row["now"] / row["then"]
                c.fill(mid - keep / 2, y0, mid + keep / 2, y0 + BAR_H, col["snow"])
            self.say(c, mid, y0 + 66, label(int(row["lo"]), int(row["hi"])), 42, True, th.ink, "ms")
            if down:
                self.say(c, mid, y0 + 134, f"{row['change']:.0f} %".replace("-", "−"), 54, True, th.ink, "ms")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="flieder", choices=list(COLOURS), help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    ap.add_argument("--no-music", action="store_true", help="a silent audio track: music is added in the app")
    args = ap.parse_args()
    assert args.stills or args.no_music, "no soundtrack for this film yet: use --no-music, music is added in the app"
    film = SnowBandsFilm(onebit.THEMES[args.theme], COLOURS[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"alps_bands_{args.theme}_de"
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (st[1] + 2.0, st[1] + film.done + 1.5, st[2] + 4.0, st[-1] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
        print("saved", f"{base}_t*.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
