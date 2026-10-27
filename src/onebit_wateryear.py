"""THE WATER YEAR 1404-1405: about normal rain for Iran, a sixth year below normal for Tehran.

Measured data only. Numbers from wateryear.py (outputs/wateryear_iran_log.txt) and, for the
official figures, the press reports of Iran's Meteorological Organization (fact check):
- Iran, water year 1404-1405 (1 Mehr 1404 to 31 Shahrivar 1405): official 233.6 mm against a
  long-term 231.9 mm (101 %, via Rokna); ERA5 October-September 101 %; CHIRPS v3.0 113 % of its own
  1370-1371 to 1399-1400 normal (CHIRPS reads 1.25-1.29 times the official totals). The screen
  says "about normal" and prints all three.
- Tehran province (Natural Earth's, current boundaries, Alborz apart): below normal in each of
  the six water years 1399-1400 to 1404-1405 in CHIRPS (82, 71, 92, 77, 47, 75 %) and in ERA5
  (October-September 2020-21 to 2025-26: 95, 79, 71, 96, 68, 68 %); official 1404-1405 to 19
  Mordad: 162 mm against 272 mm, about 60 %. The squares carry no per-year percentages: the
  products differ by up to 20 points in a year, all agree on the side of normal.
- Rain only: not dam storage, groundwater or consumption; a province mean is not the dams'
  catchment rain.

A slow, still slide on the frame of onebit_slides. One window, one bold line per scene. Below it
Iran's map with Tehran province in saffron, and under it six squares, one per water year from
1399-1400 (right) to 1404-1405 (left), solid where Tehran's rain was below normal in both CHIRPS
and ERA5. The first frame carries the whole question and the map; the squares fill in the third
scene, one after another. Three scenes, 1.5 + 2 + 2.5 bars of 60 BPM = 24 s (--cut 34s: 2 + 3 + 3.5
bars, the first version, "so slow"), a silent track (music in the app).

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

import iranmap  # noqa: E402
import onebit  # noqa: E402
import wateryear  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, SIZES, SOCIAL_CRF, Canvas, fa  # noqa: E402
from onebit_slides import COLOURS, LEFT, RIGHT, RULE, WIN, Slides  # noqa: E402

CUTS = {"24s": dict(bpm=60, bars=(1.5, 2, 2.5)),   # the default: "so slow" at 34 s (2026-10-27)
        "34s": dict(bpm=60, bars=(2, 3, 3.5))}
STEP = 0.5                                        # s between two squares filling
YEARS = tuple(range(1399, 1405))                 # water years 1399-1400 .. 1404-1405
EXPECT = {"iran": 113, "tehran": (82, 71, 92, 77, 47, 75)}   # CHIRPS % of normal: the published reel
OFFICIAL = dict(iran=101, tehran=60)              # % (press reports of IRIMO figures; fact check)
MAP_W = 600
SQ, SQ_GAP = 84, 34                               # the six squares
YEAR_PX, YEAR_LEAD = 32, 34
SOURCE, SOURCE_PX = 38, 30


def words() -> dict:
    return dict(scenes=(("سال آبی ۱۴۰۴–۱۴۰۵ // {چطور} گذشت؟", ""),
                        ("ایران: // بارش {حدودِ نرمال}", ""),
                        ("اما استان تهران: // {۶ سال} پشتِ سرِ هم زیرِ نرمال", "")),
                follow="برای داده‌های اقلیمی بیشتر، دنبال کنید",
                tehran="استان تهران", key="زیرِ نرمال در CHIRPS و ERA5",
                sources=("منبع: بارش CHIRPS v3 و ERA5؛ آمار رسمی: سازمان هواشناسی",
                         f"ایران ۱۴۰۴–۱۴۰۵: رسمی {fa(OFFICIAL['iran'])}٪ · ERA5 {fa(101)}٪ · CHIRPS {fa(EXPECT['iran'])}٪ نرمال",
                         f"تهران ۱۴۰۴–۱۴۰۵: رسمی حدود {fa(OFFICIAL['tehran'])}٪ · ERA5 {fa(68)}٪ · CHIRPS {fa(75)}٪"))


class WaterYearFilm(Slides):
    def __init__(self, th: onebit.Theme, colour: dict, cut: str = "24s"):
        pct = {}
        for region in ("iran", "tehran"):
            t = wateryear.table("rnl", region)
            normal = t.loc[wateryear.NORMAL[0]:wateryear.NORMAL[1], "year"].mean()
            pct[region] = {jy: 100 * t.loc[jy, "year"] / normal for jy in YEARS}
        assert round(pct["iran"][1404]) == EXPECT["iran"], pct["iran"][1404]
        assert tuple(round(pct["tehran"][jy]) for jy in YEARS) == EXPECT["tehran"], pct["tehran"]
        era = {r: wateryear.era5_oct_sep(r) for r in ("iran", "tehran")}
        era_pct = {r: 100 * era[r] / era[r].loc[1991:2020].mean() for r in era}
        assert round(era_pct["iran"].loc[2025]) == 101 and round(era_pct["tehran"].loc[2025]) == 68
        self.below = [pct["tehran"][jy] < 100 and era_pct["tehran"].loc[jy + 621] < 100     # water year 1399-1400 ~ ERA5 Oct 2020-Sep 2021
                      for jy in YEARS]
        assert all(self.below), "Tehran: below normal in every year, in both CHIRPS and ERA5"
        self.map = iranmap.Map(MAP_W)
        self.tehran_px = self.map.province("Tehran") & self.map.inside
        assert self.tehran_px.sum() > 200, "Tehran province too small to see"
        self.hook_at_once = True
        self.setup(th, "fa", colour, words(), CUTS[cut], "Iran.WaterYear")
        dots = np.zeros((1920, 1080), bool)               # the sources sit in the window
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        self.dots = dots
        self.layout()
        b = self.beat
        self.fill_at = [float(self.starts[2]) + b / 2 + k * STEP for k in range(len(YEARS))]   # one square at a time
        self.done = b
        assert float(self.starts[1]) + self.later(1) < 15

    def layout(self):
        inner_top = RULE + 24
        inner_bot = WIN[1] + WIN[3] - 24 - SOURCE * len(self.words["sources"])
        self.source_y = inner_bot + SOURCE - 8
        squares = 44 + SQ + 20 + 2 * YEAR_LEAD             # key, squares, two lines of years
        gap = (inner_bot - inner_top - self.map.h - squares) / 3
        assert gap >= 20, f"the picture does not fit the window ({gap:.0f})"
        self.map_at = ((LEFT + RIGHT - self.map.w) / 2, inner_top + gap)
        self.key_y = self.map_at[1] + self.map.h + gap + 30
        self.sq_top = self.key_y + 20
        self.years_y = self.sq_top + SQ + 40
        width = len(YEARS) * SQ + (len(YEARS) - 1) * SQ_GAP
        self.sq_right = (LEFT + RIGHT + width) / 2

    # ── time ──

    def later(self, i: int) -> float:
        if i == 2:
            return self.fill_at[-1] - float(self.starts[2]) + STEP
        return self.beat + 0.3

    def filled(self, t: float, k: int) -> bool:
        if not np.isfinite(t):
            return True                                   # the cover: the squares full
        return self.scene(t) == 2 and t >= self.fill_at[k]

    # ── drawing ──

    def iran(self, c: Canvas, t: float):
        th, col = self.th, self.colour
        x, y = self.map_at
        c.pixels(x, y, self.map.inside & ~self.tehran_px, col["land"])
        c.pixels(x, y, self.tehran_px, col["now"])
        c.pixels(x, y, self.map.border, th.ink)
        for name, lo, la in iranmap.CITIES:
            px, py = self.map.place(lo, la)
            px, py = x + px, y + py
            c.fill(px - 5, py - 5, px + 5, py + 5, th.ink)
            if name == "تهران":                           # the province, named beside its city
                name = self.words["tehran"]
            tw = c.width(name, FA_TEXT, 30, "rtl")
            c.frame(px + 12, py - 26, px + 12 + tw + 16, py + 12, fill=th.field)
            c.text(px + 20 + tw, py + 4, name, FA_TEXT, 30, th.ink, "rs", "rtl")

    def squares(self, c: Canvas, t: float):
        th, col = self.th, self.colour
        w = c.width(self.words["key"], FA_TEXT, 30, "rtl")
        c.fill(RIGHT - 30, self.key_y - 26, RIGHT, self.key_y + 4, col["now"])        # the key, read first
        c.text(RIGHT - 42, self.key_y, self.words["key"], FA_TEXT, 30, th.ink, "rs", "rtl")
        assert RIGHT - 42 - w > LEFT
        for k, jy in enumerate(YEARS):                   # Persian: the earliest year on the right
            right = self.sq_right - k * (SQ + SQ_GAP)
            box = (right - SQ, self.sq_top, right, self.sq_top + SQ)
            if self.filled(t, k) and self.below[k]:
                c.fill(*box, col["now"])
            c.frame(*box)
            cx = right - SQ / 2
            c.text(cx, self.years_y, fa(f"{jy}–"), FA_TEXT, YEAR_PX, th.ink, "ms", "rtl")
            c.text(cx, self.years_y + YEAR_LEAD, fa(f"{jy + 1}"), FA_TEXT, YEAR_PX, th.ink, "ms", "rtl")

    def sources(self, c: Canvas):
        for k, line in enumerate(self.words["sources"]):
            c.text(RIGHT, self.source_y + SOURCE * k, line, FA_TEXT, SOURCE_PX, self.th.head, "rs", "rtl")
            assert c.width(line, FA_TEXT, SOURCE_PX, "rtl") <= RIGHT - LEFT, line

    def body(self, c: Canvas, t: float):
        self.iran(c, t)
        self.squares(c, t)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="zafaran", choices=["zafaran"], help="colour theme")
    ap.add_argument("--cut", default="24s", choices=list(CUTS), help="24 s (default) or the slower 34 s")
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    args = ap.parse_args()
    film = WaterYearFilm(onebit.THEMES[args.theme], COLOURS[args.theme], args.cut)
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"iran_wateryear_{args.theme}_fa_{args.cut}"
    for old in (OUT / "social").glob(f"{base.name}_t*.png"):
        old.unlink()                                      # no stale frames of an earlier cut
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (st[0] + 0.0, st[1] + film.later(1) + 1.0, st[2] + film.later(2) + 1.0, st[-1] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
