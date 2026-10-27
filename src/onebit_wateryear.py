"""THE WATER YEAR 1404-1405: near normal for Iran, a sixth dry year in a row for Tehran.

Measured data only. Every number comes from wateryear.py (outputs/wateryear_iran_log.txt):
- CHIRPS v3.0 daily rain (Climate Hazards Center, UC Santa Barbara) summed over the Persian
  calendar's water years, 1 Mehr to 31 Shahrivar, over all of Iran and all of Tehran province;
  in % of the normal (the mean of 1370-1371 to 1399-1400).
- Iran: 1403-1404 was the driest water year since 1360-1361 (53 %), 1404-1405 came in at 113 %
  (ERA5, October-September: 64 % and 101 %). Tehran province: below normal six water years in a
  row, 1399-1400 to 1404-1405 (82, 71, 92, 77, 47, 75 %; ERA5 95, 79, 71, 96, 68, 68 %).
- Not on screen, in the caption: Mehr and Aban 1404 together were the driest start of a water
  year in the record (14 % of normal), Azar 1404 brought twice its normal.

A slow, still slide on the frame of onebit_slides. One window, one bold line per scene. Below it
two rows of six bars, Iran and Tehran province, one bar per water year from 1399-1400 (right)
to 1404-1405 (left), in % of normal, with the normal as a dotted line and each bar's value on
top. On the cover the bars are full (the grid's thumbnail); the film opens on empty frames, the
Iran bars come in in the second scene, Tehran's in the third. Three scenes, 2 + 3 + 3.5 bars of
60 BPM = 34 s, a silent track (music is added in the app).

    outputs/onebit/social/iran_wateryear_<theme>_fa_reel.mp4, _cover.png

    python -I src/onebit_wateryear.py
    python -I src/onebit_wateryear.py --stills
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

import onebit  # noqa: E402
import wateryear  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, SIZES, SOCIAL_CRF, Canvas, fa  # noqa: E402
from onebit_slides import COLOURS, LEFT, RIGHT, RULE, WIN, Slides  # noqa: E402

PACE = dict(bpm=60, bars=(2, 3, 3.5))
YEARS = tuple(range(1399, 1405))                 # water years 1399-1400 .. 1404-1405
EXPECT = {"iran": (67, 67, 92, 90, 53, 113), "tehran": (82, 71, 92, 77, 47, 75)}   # % of normal: the published reel
TOP = 140                                         # % at the top of a block's bars
TALL = 190                                        # px of 140 %
YEAR_PX, YEAR_LEAD = 32, 34                       # a water year in two lines under its bar
NORMAL_LABEL = 84                                 # px kept left of the bars for "نرمال"
SOURCE, SOURCE_PX = 38, 28


def label(jy: int) -> str:
    return fa(f"{jy}–{jy + 1}")


def words() -> dict:
    return dict(scenes=(("سال آبیِ ۱۴۰۴–۱۴۰۵ // {چطور} گذشت؟", ""),
                        ("ایران: // سالِ {نزدیکِ نرمال}", ""),
                        ("اما تهران: // {۶ سال} پشتِ سرِ هم کم‌باران", "")),
                follow="برای داده‌های اقلیمی بیشتر، دنبال کنید",
                heads=("ایران", "استان تهران"),
                sources=("منبع: بارش روزانه‌ی CHIRPS v3 (دانشگاه کالیفرنیا، سانتا باربارا)",
                         "سال آبی: ۱ مهر تا ۳۱ شهریور · نرمال: میانگینِ ۱۳۷۰ تا ۱۴۰۰",
                         "میانگینِ کلِ ایران و کلِ استان تهران · بررسی با ERA5"))


class WaterYearFilm(Slides):
    def __init__(self, th: onebit.Theme, colour: dict):
        self.pct = {}
        for region in ("iran", "tehran"):
            t = wateryear.table("rnl", region)
            normal = t.loc[wateryear.NORMAL[0]:wateryear.NORMAL[1], "year"].mean()
            self.pct[region] = {jy: 100 * t.loc[jy, "year"] / normal for jy in YEARS}
            got = tuple(int(round(self.pct[region][jy])) for jy in YEARS)
            assert got == EXPECT[region], (region, got)
        assert all(v < 100 for v in self.pct["tehran"].values()), "Tehran: six below normal"
        era = wateryear.era5_oct_sep("tehran")
        era_n = era.loc[1991:2020].mean()
        assert all(era.loc[y] < era_n for y in range(2020, 2026)), "ERA5 must agree: Tehran six below normal"
        self.setup(th, "fa", colour, words(), PACE, "Iran.WaterYear")
        dots = np.zeros((1920, 1080), bool)               # the sources sit in the window
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        self.dots = dots
        self.layout()
        b = self.beat
        self.fill_at = {"iran": float(self.starts[1]) + b, "tehran": float(self.starts[2]) + b}
        self.done = b
        assert self.fill_at["iran"] + b < 15

    def layout(self):
        inner_top = RULE + 24
        inner_bot = WIN[1] + WIN[3] - 24 - SOURCE * len(self.words["sources"])
        self.source_y = inner_bot + SOURCE - 8
        block = 50 + 46 + TALL + 30 + 2 * YEAR_LEAD          # heading, values, bars, two lines of years
        gap = (inner_bot - inner_top - 2 * block) / 3
        assert gap >= 20, f"the picture does not fit the window ({gap:.0f})"
        self.blocks = {}
        y = inner_top + gap
        for region in ("iran", "tehran"):
            head = y + 40
            base = head + 46 + 10 + TALL                   # the bars' foot
            self.blocks[region] = dict(head=head, base=base, years=base + 38)
            y += block + gap
        x0, x1 = LEFT + NORMAL_LABEL, RIGHT
        self.pitch = (x1 - x0) / len(YEARS)
        self.bar_w = self.pitch * 0.62
        self.x_right = x1

    # ── time ──

    def later(self, i: int) -> float:
        if i in (1, 2):
            region = "iran" if i == 1 else "tehran"
            return self.fill_at[region] - float(self.starts[i]) + self.beat
        return super().later(i)

    def full(self, region: str, t: float) -> bool:
        if not np.isfinite(t):
            return True                                   # the cover: both rows full
        i = self.scene(t)
        need = 1 if region == "iran" else 2
        return i > need or (i == need and t >= self.fill_at[region])

    # ── drawing ──

    def block(self, c: Canvas, region: str, head: str, t: float):
        th, col, B = self.th, self.colour, self.blocks[region]
        self.say(c, RIGHT, B["head"], head, 44, True, th.ink)
        y100 = B["base"] - 100 / TOP * TALL
        for x in np.arange(LEFT + NORMAL_LABEL, RIGHT, 12):          # the normal: a dotted line
            c.fill(x, y100 - 1, x + 6, y100 + 1, th.ink)
        c.text(LEFT + NORMAL_LABEL - 10, y100 + 10, "نرمال", FA_TEXT, 28, th.ink, "rs", "rtl")
        full = self.full(region, t)
        for k, jy in enumerate(YEARS):                   # Persian: the earliest year on the right
            cx = self.x_right - (k + 0.5) * self.pitch
            x0, x1 = cx - self.bar_w / 2, cx + self.bar_w / 2
            v = self.pct[region][jy]
            top = B["base"] - min(v, TOP) / TOP * TALL
            colour = col["now"] if jy == YEARS[-1] else col["bar"]
            if full:
                c.fill(x0, top, x1, B["base"], colour)
                c.text(cx, top - 12, fa(f"{v:.0f}%"), FA_BOLD, 34, th.ink, "ms", "rtl")
            else:
                c.frame(x0, B["base"] - TALL * 0.02, x1, B["base"])
            first, second = fa(f"{jy}–"), fa(f"{jy + 1}")          # 1404– over 1405: years in full
            c.text(cx, B["years"], first, FA_TEXT, YEAR_PX, th.ink, "ms", "rtl")
            c.text(cx, B["years"] + YEAR_LEAD, second, FA_TEXT, YEAR_PX, th.ink, "ms", "rtl")
            assert c.width(first, FA_TEXT, YEAR_PX, "rtl") <= self.pitch - 10, first
        c.fill(LEFT + NORMAL_LABEL, B["base"], RIGHT, B["base"] + 2, th.ink)

    def sources(self, c: Canvas):
        for k, line in enumerate(self.words["sources"]):
            c.text(RIGHT, self.source_y + SOURCE * k, line, FA_TEXT, SOURCE_PX, self.th.head, "rs", "rtl")
            assert c.width(line, FA_TEXT, SOURCE_PX, "rtl") <= RIGHT - LEFT, line

    def body(self, c: Canvas, t: float):
        self.block(c, "iran", self.words["heads"][0], t)
        self.block(c, "tehran", self.words["heads"][1], t)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="zafaran", choices=["zafaran"], help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    args = ap.parse_args()
    film = WaterYearFilm(onebit.THEMES[args.theme], COLOURS[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"iran_wateryear_{args.theme}_fa"
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (st[0] + 4.0, st[1] + film.later(1) + 1.0, st[2] + film.later(2) + 1.0, st[-1] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
