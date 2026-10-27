"""DO THE NEIGHBOURS STEAL IRAN'S RAIN? Iran's rain rises and falls with its neighbours'.

Measured data only. Every number comes from clouds.py (outputs/clouds_iran_log.txt):
- CRU TS 4.10 precipitation (University of East Anglia; stations, 0.5 deg), water years
  October-September named by the year they end, 1952-2025, each country in % of its own mean.
- Iran and Iraq usually move together: r = 0.77 (0.75 detrended; ERA5 0.74, GPCC 0.69 in the
  fact check; about 60 % of the year-to-year swings shared). No neighbour moves against Iran
  over 1952-2025 (all eight r > 0; over 1995-2024 alone Azerbaijan is slightly negative).
- In Iran's ten driest water years each neighbour was below its own median in 6 to 10: Iraq and
  Afghanistan 10, Turkmenistan 9, Turkey and the six GCC states 8, Azerbaijan and Armenia 7,
  Pakistan 6; ERA5 Iraq 9, Afghanistan and Turkmenistan 10. The rows illustrate the correlation:
  they are about what r alone predicts, not a second test, and four rows alone are near chance.
- Not on screen: how much Iran's rain fell (CRU and ERA5 disagree: about -12 % against -2 %),
  and nothing about cloud seeding's local effects, snow cover, dams or rivers.

A slide on the frame of onebit_slides. One window, one bold line per scene. Below it a line
chart, 1952 (right) to 2025 (left), and a scoreboard of the seven land neighbours and the six
GCC states across the Gulf, ten squares each, one per dry Iran year (first and last year under
it). The first frame carries the whole question; both lines draw in during the first scene, the
year under their front; the board fills row by row in the third, solid where that neighbour was
below its own median too. The cover shows both lines and the empty board. Three scenes,
1.5 + 1.5 + 2 bars of 60 BPM = 20 s (--cut 34s: 2 + 3 + 3.5 bars, "so slow"), a silent track
(music is added in the app).

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

CUTS = {"20s": dict(bpm=60, bars=(1.5, 1.5, 2)),   # the default: 34 s still slides were "so slow"
        "34s": dict(bpm=60, bars=(2, 3, 3.5))}
DRAW = (-1.0, 4.8)                               # s: both lines draw in, 1952 to 2025, year at the front (frame 0: to 1964)
ROW_STEP = 0.3                                   # s between two rows of the board filling
EXPECT_R = 0.77                                  # Iran-Iraq, CRU: the published reel
EXPECT_DRY = {"Iraq": 10, "Afghanistan": 10, "Turkmenistan": 9, "Turkey": 8, "Arabia": 8, "Azerbaijan": 7,
              "Armenia": 7, "Pakistan": 6}
NAMES = {"Iraq": "عراق", "Afghanistan": "افغانستان", "Turkmenistan": "ترکمنستان", "Turkey": "ترکیه",
         "Arabia": "شورای همکاری خلیج فارس", "Azerbaijan": "جمهوری آذربایجان", "Armenia": "ارمنستان",
         "Pakistan": "پاکستان"}
LO, HI = 40, 160                                 # % of the mean: the chart's range
PLOT = 255                                       # px: the chart's height
LABEL = 96                                       # px kept left of the chart for the lines' names
YAXIS = 74                                       # px kept right of it for 150 / 100 / 50 %
SQ, GAP, ROW = 28, 10, 37                        # the scoreboard's squares
NAME_W = 336                                     # px kept right of the squares for the names
SOURCE, SOURCE_PX = 38, 30


def words() -> dict:
    return dict(scenes=(("همسایه‌ها {بارانِ ایران} را می‌دزدند؟", ""),
                        ("ایران و عراق: // معمولاً {با هم} بالا و پایین می‌روند", ""),
                        ("سال‌های خشکِ ایران: // همسایه‌ها هم اغلب {کم‌باران} بودند", "")),
                follow="برای داده‌های اقلیمی بیشتر، دنبال کنید",
                chart="بارشِ سالانه، درصدِ میانگینِ هر کشور",
                board="۱۰ سالِ خشکِ ایران", board_key="همسایه هم کم‌باران بود",
                sources=("منبع: بارش CRU TS 4.10 (دانشگاه ایست‌آنگلیا)",
                         "سال آبی: اکتبر تا سپتامبر، به نامِ سالِ پایانی؛ ۱۹۵۲ تا ۲۰۲۵",
                         "کم‌باران: زیرِ میانه‌ی ۱۹۵۲ تا ۲۰۲۵ همان کشور"))


class CloudsFilm(Slides):
    def __init__(self, th: onebit.Theme, colour: dict, cut: str = "20s"):
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
        self.hook_at_once = True                          # the first frame carries the whole question
        self.setup(th, "fa", colour, words(), CUTS[cut], "Iran.Rain")
        dots = np.zeros((1920, 1080), bool)                 # the sources sit in the window
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        self.dots = dots
        self.layout()
        n = self.years[-1] - self.years[0]
        self.draw_at = {y: DRAW[0] + (y - self.years[0]) / n * (DRAW[1] - DRAW[0]) for y in self.years}
        assert DRAW[1] < float(self.starts[1]), "the lines must be in before scene 2"
        self.board_at = [float(self.starts[2]) + 0.3 + k * ROW_STEP for k in range(len(EXPECT_DRY))]   # row by row
        self.done = 0.6
        assert float(self.starts[1]) + self.later(1) < 15, "the scene 2 line must land before 15 s"

    def layout(self):
        inner_top = RULE + 24
        inner_bot = WIN[1] + WIN[3] - 24 - SOURCE * len(self.words["sources"])
        self.source_y = inner_bot + SOURCE - 8
        chart = 44 + 30 + PLOT + 50                         # heading, legend, plot, years
        board = 44 + ROW * len(EXPECT_DRY) + 40              # rows and the years under them
        gap = (inner_bot - inner_top - chart - board) / 3
        assert gap >= 20, f"the picture does not fit the window ({gap:.0f})"
        y = inner_top + gap
        self.chart_head = y + 36
        self.legend_y = self.chart_head + 48            # clear of the heading's kasra
        self.plot = (LEFT + LABEL, self.legend_y + 20, RIGHT - YAXIS, self.legend_y + 20 + PLOT)
        self.years_y = self.plot[3] + 40
        y += chart + gap
        self.board_head = y + 36
        self.rows_y = [self.board_head + 24 + ROW * k + ROW / 2 for k in range(len(EXPECT_DRY))]

    # ── time ──

    def later(self, i: int) -> float:
        """The part after the break: once the first part is in (0.3-1.5 s); in scene 3 once the board is."""
        if i == 2:
            return max(self.board_at[-1] - float(self.starts[2]) + 0.3, 1.6)
        return 1.6

    def drawn(self, t: float) -> list:
        """The years of the lines drawn at time t: all but while they draw in, in the first scene."""
        if not np.isfinite(t) or self.scene(t) > 0:
            return self.years                               # the cover: both lines whole
        return [y for y in self.years if t >= self.draw_at[y]]

    def row_full(self, k: int, t: float) -> bool:
        if not np.isfinite(t):
            return False                                    # the cover: the board still empty
        return self.scene(t) == 2 and t >= self.board_at[k]

    # ── drawing ──

    def xy(self, year: int, v: float) -> tuple[float, float]:
        x0, y0, x1, y1 = self.plot
        x = x1 - (year - self.years[0]) / (self.years[-1] - self.years[0]) * (x1 - x0)   # 1952 on the right
        return x, y1 - (np.clip(v, LO, HI) - LO) / (HI - LO) * (y1 - y0)

    def line(self, c: Canvas, name: str, colour: str, years: list, width: float = 5):
        """A line with a 2 px ring in the paper colour, so where the two cross both stay visible."""
        if len(years) < 2:
            return
        pts = [(c.X(x), c.Y(y)) for x, y in (self.xy(y, self.pct.loc[y, name]) for y in years)]
        c.d.line(pts, fill=self.th.field, width=max(1, round((width + 4) * c.k)), joint="curve")
        c.d.line(pts, fill=colour, width=max(1, round(width * c.k)), joint="curve")

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
        years = self.drawn(t)
        for key, region in (("iran", "Iran"), ("iraq", "Iraq")):
            self.line(c, region, col[key], years)
        if len(years) < len(self.years):                    # drawing in: the year rides under the front
            y = years[-1] if years else self.years[0]
            w = c.width(fa(y), FA_BOLD, 40, "rtl")
            cx = min(max(self.xy(y, 100)[0], x0 + w / 2), x1 - w / 2)
            c.text(cx, self.years_y, fa(y), FA_BOLD, 40, th.ink, "ms", "rtl")
            if cx + w / 2 < x1 - c.width(fa(self.years[0]), FA_TEXT, 34, "rtl") - 16:
                c.text(x1, self.years_y, fa(self.years[0]), FA_TEXT, 34, th.ink, "rs", "rtl")
            return
        c.text(x1, self.years_y, fa(self.years[0]), FA_TEXT, 34, th.ink, "rs", "rtl")
        c.text(x0, self.years_y, fa(self.years[-1]), FA_TEXT, 34, th.ink, "ls", "rtl")
        ends = {}
        for key, name, region in (("iran", "ایران", "Iran"), ("iraq", "عراق", "Iraq")):
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
        for k, (key, y) in enumerate(zip(self.order, self.rows_y)):
            full = self.row_full(k, t)
            c.text(RIGHT, y + 10, NAMES[key], FA_TEXT, 30, th.ink, "rs", "rtl")
            for j, dry in enumerate(self.dry[key]):         # earliest of the ten years on the right
                right = RIGHT - NAME_W - j * (SQ + GAP)
                box = (right - SQ, y - SQ / 2, right, y + SQ / 2)
                if full and dry:
                    c.fill(*box, th.ink)
                else:
                    c.frame(*box)
        assert RIGHT - NAME_W - 10 * (SQ + GAP) >= LEFT, "the scoreboard runs out of the window"
        widest = max(c.width(n, FA_TEXT, 30, "rtl") for n in NAMES.values())
        assert widest + 12 <= NAME_W, f"a name runs into the squares ({widest:.0f} px)"
        first_x = RIGHT - NAME_W - SQ / 2                   # the first and the last of the ten years
        last_x = RIGHT - NAME_W - 9 * (SQ + GAP) - SQ / 2
        y = self.rows_y[-1] + SQ / 2 + 34
        c.text(first_x, y, fa(self.driest[0]), FA_TEXT, 28, th.ink, "ms", "rtl")
        c.text(last_x, y, fa(self.driest[-1]), FA_TEXT, 28, th.ink, "ms", "rtl")

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
    ap.add_argument("--cut", default="20s", choices=list(CUTS), help="20 s (default) or the slower 34 s")
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    args = ap.parse_args()
    film = CloudsFilm(onebit.THEMES[args.theme], COLOURS[args.theme], args.cut)
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"iran_clouds_{args.theme}_fa_{args.cut}"
    for old in (OUT / "social").glob(f"{base.name}_t*.png"):
        old.unlink()                                      # no stale frames of an earlier cut
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (0.0, 2.5, st[1] + film.later(1) + 1.5, st[2] + 1.2, st[2] + film.later(2) + 1.5, st[-1] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
