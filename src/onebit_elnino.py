"""EL NIÑO AND IRAN'S RAIN: El Niño autumns were mostly wetter; El Niño winters half and half.

Measured data only, no forecast. Every number comes from enso.py (outputs/enso_iran_log.txt):
- Iran's rain, CRU TS 4.10 (University of East Anglia), 621 cells inside Iran, 1951-2024. Autumn
  = October-December, winter = January-March (closest to Persian Mehr-Azar and Dey-Esfand;
  September-November and December-February agree: 21 of 25 and 14 of 25).
- El Niño = NOAA CPC's Oceanic Niño Index of that same season at least +0.5 °C (the value NOAA
  uses, applied to one season at a time): 26 autumns, of which 21 had more rain than the
  1951-2024 median (p = 0.001, permutation); 22 winters, of which 11 did (p = 0.31). CPC's RONI
  gives 20 of 25 and 11 of 21. Strong El Niños alone (ONI at least +1.5) are few: 4 of 6 autumns
  and 2 of 6 winters wetter (caption). Autumn brings 27 % of Iran's yearly rain, winter 46 %.
- "This year": CPC's ENSO discussion of 8 October 2026 (El Niño Advisory, Niño-3.4 +2.1 °C;
  "strong-to-very strong El Niño likely through January-March 2027"). The first line states that
  status; every number on screen is about past seasons, and the reel forecasts nothing.

A slow, still slide on the frame of onebit_slides. One window that never moves; its top holds
the scene's bold line. Below it two blocks of rain drops, one drop per El Niño season, earliest
on the right: autumn (26) and winter (22). On the cover all drops are pale; in the second scene
the autumn drops turn, a row per beat, solid where that autumn was wetter than usual and hollow
where it was drier; in the third the winter drops do the same. One bold line per scene, three
scenes, 2 + 3 + 3.5 bars of 60 BPM = 34 s, a silent track (music is added in the app).

    outputs/onebit/social/iran_elnino_<theme>_fa_reel.mp4, _cover.png

    python -I src/onebit_elnino.py              # Persian, Baran
    python -I src/onebit_elnino.py --stills
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

import enso  # noqa: E402
import onebit  # noqa: E402
from onebit import FA_TEXT, OUT, SIZES, SOCIAL_CRF, Canvas, fa  # noqa: E402
from onebit_slides import COLOURS, LEFT, RIGHT, RULE, WIN, Slides  # noqa: E402

# onebit_snow's rain drop, copied: importing that module loads cartopy before the netCDF files,
# and shapely first crashes the heap ("corrupted size vs. prev_size")
DROP = ["....#....", "....#....", "...###...", "..#####..", ".#######.", ".#######.", ".#######.",
        "..#####..", "...###..."]
AUTUMN, WINTER = "OND", "JFM"                     # the reel's seasons (enso.SEASONS)
EXPECT = {AUTUMN: (21, 26), WINTER: (11, 22)}     # wetter of all El Niño seasons: the published reel
SHARE = {AUTUMN: 27, WINTER: 46}                  # % of the year's rain: the published reel
PACE = dict(bpm=60, bars=(2, 3, 3.5))
CELL = 7                                          # px per sprite pixel: a drop is 63 px
PER_ROW = 9
PITCH, ROW = 80, 84                               # drop to drop in a row, row to row
YEAR = 28                                         # px of the first and last year beside each row
HEAD = 48                                         # px of a block's heading
SOURCE = 36                                       # line step of the sources (26 px type)


def words(autumn: dict, winter: dict) -> dict:
    a, w = autumn, winter
    # «ال‌نینوهای گذشته» would push the title down to 58 px; the past tense «آوردند» carries the past
    return dict(scenes=(("امسال ال‌نینوی قوی داریم. // ال‌نینوها {باران} آوردند؟", ""),
                        (f"پاییزهای ال‌نینو: // {{{fa(a['n_wetter'])} از {fa(len(a['years']))}}} پربارش‌تر", ""),
                        (f"زمستان‌های ال‌نینو: // {{{fa(w['n_wetter'])} از {fa(len(w['years']))}}}، نیمی بله و نیمی نه", "")),
                follow="برای داده‌های اقلیمی بیشتر، دنبال کنید",
                heads=(f"پاییز · {fa(SHARE[AUTUMN])}٪ از بارانِ سال", f"زمستان · {fa(SHARE[WINTER])}٪ از بارانِ سال"),
                legend=("پربارش‌تر از معمول", "کم‌بارش‌تر از معمول"),
                sources=("منبع: بارش CRU TS 4.10 (دانشگاه ایست‌آنگلیا) · شاخص ONI نوآ · ۱۹۵۱ تا ۲۰۲۴",
                         "ال‌نینو: ONI دست‌کم ۰٫۵ درجه · پاییز: اکتبر تا دسامبر · زمستان: ژانویه تا مارس"))


class ElNinoFilm(Slides):
    def __init__(self, th: onebit.Theme, colour: dict):
        self.res = {s: enso.result(s) for s in (AUTUMN, WINTER)}
        for s, r in self.res.items():
            got = (r["n_wetter"], len(r["years"]))
            assert got == EXPECT[s], f"{s}: the data now give {got}, the published reel {EXPECT[s]}"
        assert enso.THRESHOLD == 0.5, "the source line says ONI at least 0.5"
        annual = enso.iran_rain()[0].loc["1951":"2024"]
        annual = annual.groupby(annual.index.year).sum().mean()
        for s, r in self.res.items():
            assert round(100 * r["mean"] / annual) == SHARE[s], (s, 100 * r["mean"] / annual)
        self.setup(th, "fa", colour, words(self.res[AUTUMN], self.res[WINTER]), PACE, "ElNino.Iran")
        # the sources sit inside the window (below it, Instagram lays its caption over the frame),
        # so the dot grid runs on under the window
        dots = np.zeros((1920, 1080), bool)
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        self.dots = dots
        self.blocks = self.layout()
        b = self.beat
        # the rows of a block turn one per beat from beat 1 of its scene; its number one beat later
        self.turn_at = {s: [float(self.starts[i]) + (1 + k) * b for k in range(len(self.blocks[s]["rows"]))]
                        for i, s in ((1, AUTUMN), (2, WINTER))}
        self.done = self.turn_at[AUTUMN][-1] - float(self.starts[1]) + b
        assert self.turn_at[AUTUMN][-1] + b < 15, "the autumn number must land before 15 s"

    def layout(self) -> dict:
        """Two blocks under the rule, each a heading and rows of at most PER_ROW drops, spread
        evenly down the window with the legend under them."""
        inner_top, inner_bot = RULE + 24, WIN[1] + WIN[3] - 24 - SOURCE * len(self.words["sources"])
        self.source_y = inner_bot + SOURCE - 8           # first baseline of the sources, in the window
        heights, blocks = [], {}
        for s in (AUTUMN, WINTER):
            years = self.res[s]["years"]
            rows = [list(r) for r in np.array_split(years, int(np.ceil(len(years) / PER_ROW)))]
            blocks[s] = dict(rows=[[int(y) for y in r] for r in rows])
            heights.append(70 + ROW * len(rows))
        legend_h = 60
        gap = (inner_bot - inner_top - sum(heights) - legend_h) / 4
        assert gap >= 20, "the blocks do not fit the window"
        y = inner_top + gap
        for s, h in zip((AUTUMN, WINTER), heights):
            blocks[s]["head"] = y + HEAD
            blocks[s]["row_y"] = [y + 70 + ROW * k + ROW / 2 for k in range(len(blocks[s]["rows"]))]
            y += h + gap
        self.legend_y = y + 40
        return blocks

    # ── time ──

    def state(self, season: str, row: int, t: float) -> bool:
        """True once a row has turned."""
        i = self.scene(t)
        if not np.isfinite(t) or i == 0:
            return False
        if season == AUTUMN:
            return i > 1 or t >= self.turn_at[AUTUMN][row]
        return i > 2 or (i == 2 and t >= self.turn_at[WINTER][row])

    def later(self, i: int) -> float:
        """The number comes in one beat after the last row has turned."""
        if i in (1, 2):
            s = AUTUMN if i == 1 else WINTER
            return self.turn_at[s][-1] - float(self.starts[i]) + self.beat
        return super().later(i)

    # ── drawing ──

    def drop(self, c: Canvas, cx: float, cy: float, kind: str):
        """kind: 'open' (not yet turned: a pale drop), 'wet' (solid rain blue), 'dry' (hollow:
        the outline in ink)."""
        h, w = len(DROP), len(DROP[0])
        x0, y0 = cx - w * CELL / 2, cy - h * CELL / 2
        on = [[ch == "#" for ch in row] for row in DROP]
        for r in range(h):
            for q in range(w):
                if not on[r][q]:
                    continue
                a, b = x0 + q * CELL, y0 + r * CELL
                edge = any(not (0 <= r + dr < h and 0 <= q + dq < w and on[r + dr][q + dq])
                           for dr, dq in ((-1, 0), (1, 0), (0, -1), (0, 1)))
                if kind == "wet":
                    c.fill(a, b, a + CELL, b + CELL, self.colour["rain"])
                elif kind == "open":
                    c.fill(a, b, a + CELL, b + CELL, self.colour["land"])
                elif edge:
                    c.fill(a, b, a + CELL, b + CELL, self.th.ink)

    def block(self, c: Canvas, season: str, head: str, t: float):
        B, r = self.blocks[season], self.res[season]
        mid = (LEFT + RIGHT) / 2
        self.say(c, RIGHT, B["head"], head, HEAD, True, self.th.ink)
        for k, (years, cy) in enumerate(zip(B["rows"], B["row_y"])):
            turned = self.state(season, k, t)
            n = len(years)
            for j, y in enumerate(years):                 # Persian: the earliest year on the right
                cx = mid + ((n - 1) / 2 - j) * PITCH
                self.drop(c, cx, cy, ("wet" if r["wetter"][y] else "dry") if turned else "open")
            # the row's first year at its right end, its last year at its left end: the order reads
            half = len(DROP[0]) * CELL / 2 + 10
            first, last = fa(years[0]), fa(years[-1])
            right, left = mid + (n - 1) / 2 * PITCH + half, mid - (n - 1) / 2 * PITCH - half
            c.text(right, cy + YEAR / 3, first, FA_TEXT, YEAR, self.th.head, "ls")
            c.text(left, cy + YEAR / 3, last, FA_TEXT, YEAR, self.th.head, "rs")
            assert right + c.width(first, FA_TEXT, YEAR) <= RIGHT + 8 and left - c.width(last, FA_TEXT, YEAR) >= LEFT - 8, years

    def legend(self, c: Canvas):
        mid, y = (LEFT + RIGHT) / 2, self.legend_y
        for k, (kind, label) in enumerate(zip(("wet", "dry"), self.words["legend"])):
            x = mid + (1 - 2 * k) * 210                   # wet on the right (read first), dry on the left
            self.drop(c, x + 150, y - 14, kind)
            c.text(x + 100, y, label, FA_TEXT, 34, self.th.ink, "rs", "rtl")
            assert c.width(label, FA_TEXT, 34, "rtl") <= 300, label

    def sources(self, c: Canvas):
        """Inside the window, under the legend: clear of Instagram's caption over the frame's foot."""
        for k, line in enumerate(self.words["sources"]):
            c.text(RIGHT, self.source_y + SOURCE * k, line, FA_TEXT, 26, self.th.head, "rs", "rtl")
            assert c.width(line, FA_TEXT, 26, "rtl") <= RIGHT - LEFT, line

    def body(self, c: Canvas, t: float):
        self.block(c, AUTUMN, self.words["heads"][0], t)
        self.block(c, WINTER, self.words["heads"][1], t)
        self.legend(c)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="baran", choices=["baran"], help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    args = ap.parse_args()
    film = ElNinoFilm(onebit.THEMES[args.theme], COLOURS[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"iran_elnino_{args.theme}_fa"
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (st[0] + 4.0, st[1] + 2.5, st[1] + film.later(1) + 1.0, st[2] + film.later(2) + 1.0, st[-1] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
