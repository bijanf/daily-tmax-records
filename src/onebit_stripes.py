"""HOW MUCH HAS IRAN WARMED? About 2 °C since 1951-1980, and its ten warmest years all after 2000.

Measured data only. Every number comes from temperature.py (outputs/temperature_iran_log.txt):
- Iran's annual mean temperature, CRU TS 4.10 (University of East Anglia; stations, 0.5 deg),
  621 cells inside Iran: 2016-2025 is 1.86 °C warmer than 1951-1980; ERA5 (Copernicus/ECMWF,
  a second estimate) gives 2.30 °C; Berkeley Earth 1.71 °C for 2014-2023 (fact check). The screen
  says "about 2 degrees", names both, and keeps the base (1951-1980, NASA GISS's too) in the
  colour bar's heading; against 1991-2020 it would be 0.7 (CRU) to 0.9 °C (ERA5): caption.
- Iran's ten warmest years since 1951 all came after 2000, in CRU TS and in ERA5.
- Not on screen, in the caption: the world's land in the same dataset warmed 1.30 °C (Iran about
  1.4 times as much; Berkeley Earth about 1.3); summer +2.2 °C in CRU and ERA5. Not claimed: that
  no part of Iran warmed 3 °C (CRU's largest cell +2.26, but 4 % of ERA5's cells reach +3).

A slow, still slide on the frame of onebit_slides: one window, one bold line per scene. Below it
75 stripes, one per year from 1951 (right) to 2025 (left), each coloured by how much warmer or
cooler that year was than the 1951-1980 mean, in 0.5 °C steps (a diverging ramp, blue - grey -
red, checked with the dataviz validator), and a stepped colour bar under them. On the cover the
stripes are empty; in the second scene they fill in three steps (1951-1980, 1981-2000,
2001-2025); in the third every stripe but the ten warmest goes. The cover (the grid's thumbnail)
shows the full stripes; the film opens on the empty frame. Three scenes, 2 + 3 + 3.5 bars
of 60 BPM = 34 s, a silent track (music is added in the app).

    outputs/onebit/social/iran_stripes_<theme>_fa_reel.mp4, _cover.png

    python -I src/onebit_stripes.py
    python -I src/onebit_stripes.py --stills
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

import onebit  # noqa: E402
import temperature  # noqa: E402
from onebit import FA_TEXT, OUT, SIZES, SOCIAL_CRF, Canvas, fa  # noqa: E402
from onebit_slides import COLOURS, LEFT, RIGHT, RULE, WIN, Slides  # noqa: E402

YEARS = (1951, 2025)
STEPS = (-1.75, -1.25, -0.75, -0.25, 0.25, 0.75, 1.25, 1.75)   # °C: the edges of the ramp's 9 classes
EXPECT = dict(cru=1.9, era5=2.3)                 # °C, rounded: the published reel
PACE = dict(bpm=60, bars=(2, 3, 3.5))
FILL = ((1951, 1980), (1981, 2000), (2001, 2025))  # the stripes come in, one group per beat
STRIPE, TALL = 11, 400                           # px: a year's width, the stripes' height
SOURCE, SOURCE_PX = 38, 28                   # line step and size of the sources


def words(cru: float, era: float) -> dict:
    return dict(scenes=(("ایران چقدر // {گرم‌تر} شده؟", ""),
                        ("۱۰ سالِ اخیر: // {حدود ۲ درجه} گرم‌تر", ""),
                        ("۱۰ سالِ گرم‌ترِ ایران: // {همه بعد از ۲۰۰۰}", "")),
                follow="برای داده‌های اقلیمی بیشتر، دنبال کنید",
                head="نسبت به میانگینِ ۱۹۵۱ تا ۱۹۸۰",
                ends=("۲ درجه سردتر", "تقریباً بی‌تغییر", "۲ درجه گرم‌تر"),
                sources=("منبع: دمای CRU TS 4.10 (دانشگاه ایست‌آنگلیا)",
                         "و ERA5 (کوپرنیکوس) · میانگینِ سالانه‌ی ایران",
                         f"۲۰۱۶ تا ۲۰۲۵: CRU {fa(f'{cru:.1f}')} و ERA5 {fa(f'{era:.1f}')} درجه گرم‌تر"))


class StripesFilm(Slides):
    def __init__(self, th: onebit.Theme, colour: dict):
        df = temperature.series()
        s = df["iran"].loc[YEARS[0]:YEARS[1]]
        assert len(s) == YEARS[1] - YEARS[0] + 1, "a year is missing"
        self.anom = s - s.loc[1951:1980].mean()
        cru, era = temperature.change(df["iran"]), temperature.change(temperature.era5())
        assert (round(cru, 1), round(era, 1)) == (EXPECT["cru"], EXPECT["era5"]), (cru, era)
        assert 1.5 <= cru <= 2.5 and 1.5 <= era <= 2.5, "'about 2 degrees' must hold for both"
        self.top = set(int(y) for y in s.sort_values(ascending=False).index[:10])
        era_top = temperature.era5().loc[1951:].sort_values(ascending=False).index[:10]
        assert min(self.top) > 2000 and min(era_top) > 2000, "the ten warmest years after 2000, in both"
        self.cls = {int(y): int(np.searchsorted(STEPS, a, side="right")) for y, a in self.anom.items()}
        self.setup(th, "fa", colour, words(cru, era), PACE, "Iran.Warming")
        dots = np.zeros((1920, 1080), bool)              # the sources sit in the window: dots all down
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        self.dots = dots
        self.layout()
        b = self.beat
        self.fill_at = [float(self.starts[1]) + (1 + k) * b for k in range(len(FILL))]
        self.fade_at = float(self.starts[2]) + b
        self.done = self.fill_at[-1] - float(self.starts[1]) + b
        assert self.fill_at[-1] + b < 15, "the number must land before 15 s"

    def layout(self):
        inner_top = RULE + 24
        inner_bot = WIN[1] + WIN[3] - 24 - SOURCE * len(self.words["sources"])
        self.source_y = inner_bot + SOURCE - 8
        n = YEARS[1] - YEARS[0] + 1
        width = n * STRIPE
        assert width <= RIGHT - LEFT, width
        block = TALL + 60 + 70 + 46 + 60                 # stripes, years, heading, bar, labels
        gap = (inner_bot - inner_top - block) / 3
        assert gap >= 20, "the picture does not fit the window"
        self.x_right = (LEFT + RIGHT + width) / 2         # 1951's stripe ends here
        self.y0 = inner_top + gap
        self.years_y = self.y0 + TALL + 44
        self.head_y = self.years_y + 70 + gap / 2
        self.bar_y = self.head_y + 24

    # ── time ──

    def later(self, i: int) -> float:
        """The number comes in one beat after the last stripes; in scene 3 one beat after the fade."""
        if i == 1:
            return self.fill_at[-1] - float(self.starts[1]) + self.beat
        if i == 2:
            return self.fade_at - float(self.starts[2]) + self.beat
        return super().later(i)

    def shown(self, year: int, t: float) -> str:
        """'empty', 'full' or 'faded' for a year's stripe at time t."""
        i = self.scene(t)
        if not np.isfinite(t):
            return "full"                             # the cover (the grid's thumbnail): the stripes
        if i == 0:
            return "empty"
        if i == 1:
            k = next(k for k, (a, b) in enumerate(FILL) if a <= year <= b)
            return "full" if t >= self.fill_at[k] else "empty"
        return "full" if (year in self.top or t < self.fade_at) else "empty"

    # ── drawing ──

    def stripes(self, c: Canvas, t: float):
        ramp, x1 = self.colour["ramp"], self.x_right
        for y, k in self.cls.items():
            right = x1 - (y - YEARS[0]) * STRIPE              # Persian: the earliest year on the right
            state = self.shown(y, t)
            if state == "full":
                c.fill(right - STRIPE, self.y0, right, self.y0 + TALL, ramp[k])
        c.frame(x1 - len(self.cls) * STRIPE - 2, self.y0 - 2, x1 + 2, self.y0 + TALL + 2)
        c.text(x1, self.years_y, fa(YEARS[0]), FA_TEXT, 34, self.th.ink, "rs", "rtl")
        c.text(x1 - len(self.cls) * STRIPE, self.years_y, fa(YEARS[1]), FA_TEXT, 34, self.th.ink, "ls", "rtl")

    def legend(self, c: Canvas):
        """The ramp as nine boxes, cold on the right as the stripes' first years, warm on the left."""
        mid = (LEFT + RIGHT) / 2
        self.say(c, mid, self.head_y, self.words["head"], 40, True, self.th.ink, "ms")
        box, h, n = 90, 46, len(self.colour["ramp"])
        for k, colour in enumerate(self.colour["ramp"]):
            x0 = mid + (n / 2 - 1 - k) * box                  # k = 0 (coldest) right-most
            c.fill(x0 + 1, self.bar_y, x0 + box - 1, self.bar_y + h, colour)
        for k, label in zip((0, n // 2, n - 1), self.words["ends"]):
            cx = mid + (n / 2 - 1 - k) * box + box / 2
            anchor = "rs" if k == 0 else "ls" if k == n - 1 else "ms"
            x = cx + box / 2 if k == 0 else cx - box / 2 if k == n - 1 else cx
            c.text(x, self.bar_y + h + 44, label, FA_TEXT, 32, self.th.ink, anchor, "rtl")

    def sources(self, c: Canvas):
        for k, line in enumerate(self.words["sources"]):
            c.text(RIGHT, self.source_y + SOURCE * k, line, FA_TEXT, SOURCE_PX, self.th.head, "rs", "rtl")
            assert c.width(line, FA_TEXT, SOURCE_PX, "rtl") <= RIGHT - LEFT, line

    def body(self, c: Canvas, t: float):
        self.stripes(c, t)
        self.legend(c)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="kahgel", choices=["kahgel"], help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    args = ap.parse_args()
    film = StripesFilm(onebit.THEMES[args.theme], COLOURS[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"iran_stripes_{args.theme}_fa"
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
