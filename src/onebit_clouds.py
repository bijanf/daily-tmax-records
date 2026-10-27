"""DO THE NEIGHBOURS STEAL IRAN'S RAIN? Iran's rain rises and falls with its neighbours'.

Measured data only. Every number comes from clouds.py (outputs/clouds_iran_log.txt):
- CRU TS 4.10 precipitation (University of East Anglia; stations, 0.5 deg), water years
  October-September 1952-2024, each country in % of its own 1952-2024 mean.
- Iran and Iraq move together: r = 0.77 (0.75 with both detrended; ERA5 0.73). No neighbour
  moves against Iran (all eight r > 0).
- In Iran's ten driest water years, each neighbour was below its own median: Iraq and
  Afghanistan 10 of 10, Turkmenistan 9, Turkey 8, the Arabian block, Azerbaijan and Armenia 7,
  Pakistan 6 (chance alone: about 5). ERA5: Iraq 9, Afghanistan and Turkmenistan 10.
- Not on screen: how much Iran's rain fell (CRU -11.5 % from 1952-1981 to 1995-2024, ERA5 -0.5 %
  from the 1960s: the datasets disagree), and nothing about cloud seeding's local effects.

A slow, still slide on the frame of onebit_slides. One window, one bold line per scene. Below
it a line chart, 1952 (right) to 2024 (left), and a scoreboard of the eight neighbours, ten
squares each, one per dry Iran year. On the cover all is empty; in the second scene Iran's line
comes in, then Iraq's; in the third the squares fill, solid where that neighbour was dry too.
Three scenes, 2 + 3 + 3.5 bars of 60 BPM = 34 s, a silent track (music is added in the app).

    outputs/onebit/social/iran_clouds_<theme>_fa_reel.mp4, _cover.png

    python -I src/onebit_clouds.py
    python -I src/onebit_clouds.py --stills
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

import clouds  # noqa: E402
import onebit  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, SIZES, SOCIAL_CRF, Canvas, fa  # noqa: E402
from onebit_slides import COLOURS, LEFT, RIGHT, RULE, WIN, Slides  # noqa: E402

PACE = dict(bpm=60, bars=(2, 3, 3.5))
EXPECT_R = 0.77                                  # Iran-Iraq, CRU: the published reel
EXPECT_DRY = {"Iraq": 10, "Afghanistan": 10, "Turkmenistan": 9, "Turkey": 8, "Arabia": 7, "Azerbaijan": 7,
              "Armenia": 7, "Pakistan": 6}
NAMES = {"Iraq": "عراق", "Afghanistan": "افغانستان", "Turkmenistan": "ترکمنستان", "Turkey": "ترکیه",
         "Arabia": "شبه‌جزیره‌ی عربستان", "Azerbaijan": "جمهوری آذربایجان", "Armenia": "ارمنستان",
         "Pakistan": "پاکستان"}
LO, HI = 40, 160                                 # % of the mean: the chart's range
PLOT = 270                                       # px: the chart's height
LABEL = 96                                       # px kept left of the chart for the lines' names
YAXIS = 74                                       # px kept right of it for 150 / 100 / 50 %
SQ, GAP, ROW = 28, 10, 38                        # the scoreboard's squares
SOURCE, SOURCE_PX = 38, 28


def words() -> dict:
    return dict(scenes=(("همسایه‌ها {بارانِ ایران} را می‌دزدند؟", ""),
                        ("ایران و عراق: // {با هم} بالا و پایین می‌روند", ""),
                        ("سال‌های خشکِ ایران: // همسایه‌ها هم {خشک} بودند", "")),
                follow="برای داده‌های اقلیمی بیشتر، دنبال کنید",
                chart="بارشِ سالانه، درصدِ میانگینِ هر کشور",
                board="۱۰ سالِ خشکِ ایران", board_key="همسایه هم خشک بود",
                sources=("منبع: بارش CRU TS 4.10 (دانشگاه ایست‌آنگلیا)",
                         "سال‌های آبی (اکتبر تا سپتامبر) ۱۹۵۲ تا ۲۰۲۴",
                         "خشک: کمتر از میانه‌ی ۱۹۵۲ تا ۲۰۲۴ همان کشور"))


class CloudsFilm(Slides):
    def __init__(self, th: onebit.Theme, colour: dict):
        df = clouds.cru()
        rel = clouds.relations(df)
        assert round(rel.loc["Iraq", "r"], 2) == EXPECT_R, rel.loc["Iraq", "r"]
        assert (rel.drop("Iran").r > 0).all(), "a neighbour moves against Iran: the scene 2 line would be wrong"
        got = {k: int(rel.loc[k, "dry_with_iran"]) for k in EXPECT_DRY}
        assert got == EXPECT_DRY, got
        self.pct = clouds.pct(df)
        self.years = list(df.index)
        self.driest = sorted(rel.attrs["driest"])           # chronological, earliest on the right
        median = df.median()
        self.dry = {k: [bool(df.loc[y, k] < median[k]) for y in self.driest] for k in EXPECT_DRY}
        self.order = sorted(EXPECT_DRY, key=lambda k: (-got[k], -rel.loc[k, "r"]))
        self.setup(th, "fa", colour, words(), PACE, "Iran.Rain")
        dots = np.zeros((1920, 1080), bool)                 # the sources sit in the window
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        self.dots = dots
        self.layout()
        b = self.beat
        self.iran_at = float(self.starts[1]) + b
        self.iraq_at = float(self.starts[1]) + 2 * b
        self.board_at = float(self.starts[2]) + b
        self.done = self.iraq_at - float(self.starts[1]) + b
        assert self.iraq_at + b < 15, "the scene 2 line must land before 15 s"

    def layout(self):
        inner_top = RULE + 24
        inner_bot = WIN[1] + WIN[3] - 24 - SOURCE * len(self.words["sources"])
        self.source_y = inner_bot + SOURCE - 8
        chart = 44 + 30 + PLOT + 50                         # heading, legend, plot, years
        board = 44 + ROW * len(EXPECT_DRY)
        gap = (inner_bot - inner_top - chart - board) / 3
        assert gap >= 20, f"the picture does not fit the window ({gap:.0f})"
        y = inner_top + gap
        self.chart_head = y + 36
        self.legend_y = self.chart_head + 40
        self.plot = (LEFT + LABEL, self.legend_y + 24, RIGHT - YAXIS, self.legend_y + 24 + PLOT)
        self.years_y = self.plot[3] + 40
        y += chart + gap
        self.board_head = y + 36
        self.rows_y = [self.board_head + 24 + ROW * k + ROW / 2 for k in range(len(EXPECT_DRY))]

    # ── time ──

    def later(self, i: int) -> float:
        if i == 1:
            return self.iraq_at - float(self.starts[1]) + self.beat
        if i == 2:
            return self.board_at - float(self.starts[2]) + self.beat
        return super().later(i)

    def shown(self, what: str, t: float) -> bool:
        if not np.isfinite(t):
            return what != "board"                          # the cover shows both lines, the board empty
        i = self.scene(t)
        at = {"iran": self.iran_at, "iraq": self.iraq_at, "board": self.board_at}[what]
        return i > {"iran": 1, "iraq": 1, "board": 2}[what] or (t >= at and i >= {"iran": 1, "iraq": 1, "board": 2}[what])

    # ── drawing ──

    def xy(self, year: int, v: float) -> tuple[float, float]:
        x0, y0, x1, y1 = self.plot
        x = x1 - (year - self.years[0]) / (self.years[-1] - self.years[0]) * (x1 - x0)   # 1952 on the right
        return x, y1 - (np.clip(v, LO, HI) - LO) / (HI - LO) * (y1 - y0)

    def line(self, c: Canvas, name: str, colour: str, width: float = 5):
        pts = [self.xy(y, self.pct.loc[y, name]) for y in self.years]
        c.d.line([(c.X(x), c.Y(y)) for x, y in pts], fill=colour, width=max(1, round(width * c.k)), joint="curve")

    def chart(self, c: Canvas, t: float):
        th, col = self.th, self.colour
        x0, y0, x1, y1 = self.plot
        self.say(c, RIGHT, self.chart_head, self.words["chart"], 38, True, th.ink)
        for k, (key, name) in enumerate((("iran", "ایران"), ("iraq", "عراق"))):   # the legend, right to left
            x = RIGHT - k * 190
            c.fill(x - 46, self.legend_y - 13, x, self.legend_y - 7, col[key])
            c.text(x - 56, self.legend_y, name, FA_TEXT, 32, th.ink, "rs", "rtl")
        c.frame(x0, y0, x1, y1)
        _, ymid = self.xy(self.years[0], 100)               # the mean: a dotted hairline
        for x in np.arange(x0 + 4, x1 - 4, 12):
            c.fill(x, ymid - 1, x + 6, ymid + 1, th.ink)
        for v in (150, 100, 50):                            # the axis, right of the chart
            c.text(RIGHT, self.xy(self.years[0], v)[1] + 10, fa(f"{v}%"), FA_TEXT, 28, th.ink, "rs", "rtl")
        c.text(x1, self.years_y, fa(self.years[0]), FA_TEXT, 34, th.ink, "rs", "rtl")
        c.text(x0, self.years_y, fa(self.years[-1]), FA_TEXT, 34, th.ink, "ls", "rtl")
        ends = {}
        for key, name, region in (("iran", "ایران", "Iran"), ("iraq", "عراق", "Iraq")):
            if self.shown(key, t):
                self.line(c, region, col[key])
                ends[name] = self.xy(self.years[-1], self.pct.loc[self.years[-1], region])[1]
        if len(ends) == 2 and abs(ends["ایران"] - ends["عراق"]) < 34:   # the lines' names, apart
            mid = (ends["ایران"] + ends["عراق"]) / 2
            hi_name = "ایران" if ends["ایران"] <= ends["عراق"] else "عراق"
            ends = {hi_name: mid - 17, ("عراق" if hi_name == "ایران" else "ایران"): mid + 17}
        for name, y in ends.items():
            c.text(x0 - 10, y + 10, name, FA_TEXT, 28, th.ink, "rs", "rtl")

    def board(self, c: Canvas, t: float):
        th = self.th
        self.say(c, RIGHT, self.board_head, self.words["board"], 34, True, th.ink)
        w = c.width(self.words["board_key"], FA_TEXT, 30, "rtl")    # the key: a solid square, left
        c.fill(LEFT + w + 10, self.board_head - SQ + 4, LEFT + w + 10 + SQ, self.board_head + 4, th.ink)
        c.text(LEFT + w, self.board_head, self.words["board_key"], FA_TEXT, 30, th.ink, "rs", "rtl")   # square read first
        assert LEFT + SQ + 10 + w + 20 < RIGHT - c.width(self.words["board"], FA_BOLD, 34, "rtl"), "key and heading meet"
        full = self.shown("board", t)
        for key, y in zip(self.order, self.rows_y):
            c.text(RIGHT, y + 10, NAMES[key], FA_TEXT, 30, th.ink, "rs", "rtl")
            for j, dry in enumerate(self.dry[key]):         # earliest of the ten years on the right
                right = RIGHT - 300 - j * (SQ + GAP)
                box = (right - SQ, y - SQ / 2, right, y + SQ / 2)
                if full and dry:
                    c.fill(*box, th.ink)
                else:
                    c.frame(*box)
        assert RIGHT - 300 - 10 * (SQ + GAP) >= LEFT, "the scoreboard runs out of the window"

    def sources(self, c: Canvas):
        for k, line in enumerate(self.words["sources"]):
            c.text(RIGHT, self.source_y + SOURCE * k, line, FA_TEXT, SOURCE_PX, self.th.head, "rs", "rtl")
            assert c.width(line, FA_TEXT, SOURCE_PX, "rtl") <= RIGHT - LEFT, line

    def body(self, c: Canvas, t: float):
        self.chart(c, t)
        self.board(c, t)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="pesteh", choices=["pesteh"], help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    args = ap.parse_args()
    film = CloudsFilm(onebit.THEMES[args.theme], COLOURS[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"iran_clouds_{args.theme}_fa"
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (st[0] + 4.0, st[1] + 1.5, st[1] + film.later(1) + 1.0, st[2] + film.later(2) + 1.0, st[-1] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
