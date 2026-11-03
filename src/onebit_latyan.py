"""LATYAN DAM, 38 AUTUMNS FROM SPACE: the open water of the Latyan reservoir on the Jajrud river, one of the five
dams that supply Tehran, in one autumn Landsat pass a year, 1987-2026, and the storage figure that was
officially reported (outputs/latyan_log.txt).

Measured data only, from latyan.py (outputs/latyan_log.txt) and get_latyan.py:
- Landsat (USGS) in true colour: per year the autumn pass nearest 1 October (within 25 days) that sees the
  reservoir clear; 38 years have a frame (2003 and 2011 have none), of which 32 are shown (six are measured,
  not shown: striped Landsat 7 scenes and one cloudy Landsat 5 scene).
- The area of open water in that pass (km2): MNDWI > 0 and NIR < 0.10 on the clear pixels of the reservoir.
  One pass per year, so every year's number is one estimate.
- The usual area: the median of the 38 passes; 1404 (2025) and 1405 (2026) against it.
- The storage of the Latyan dam as reported for 1 Aban 1405 (23 October 2026): 21 million m3, against a
  long-term average of 42 (storage, not area).

A slide on the frame of onebit_slides: one window, one bold line per scene. The Latyan picture spans the
window, the gauge of its water sits under it. The first frame carries the whole hook with the autumn of 1405
(2026); the film jumps back to 1404 (2025) within 1 s, rewinds to 1366 (1987) and plays the autumns forward
from 6 s, so 1404 arrives before the last scene; 1405 comes in as the last scene begins. The cover splits
through the middle of the 2025 (1404) water: 1404 on the right, 1405 on the left. Three scenes, 1.5 + 1.5 + 2 bars of
60 BPM = 20 s, a silent track (the score: src/onebit_score_latyan.py).

    outputs/onebit/social/latyan_firuze_fa_reel.mp4, _cover.png

    python -I src/onebit_latyan.py
    python -I src/onebit_latyan.py --stills
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import get_latyan  # noqa: E402
import latyan  # noqa: E402
import onebit  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, SIZES, SOCIAL_CRF, Canvas, fa  # noqa: E402
from onebit_slides import COLOURS, LEFT, RIGHT, RULE, WIN, Slides  # noqa: E402

PACE = dict(bpm=60, bars=(1.5, 1.5, 2))
EXPECT = dict(median=(2.10, 2.12), near=5, total=38, smallest=2025,
              ratio_1404=(0.41, 0.43), ratio_1405=(0.65, 0.67), official=(21, 42, 10))
JUMP = 1.0                                        # s: 1405 gives way to 1404 (the big change lands by 2 s)
REWIND = (2.0, 4.0)                               # s: 1404 back to 1366 (1987), in two seconds
FORWARD = 6.0                                     # s: 1987 forward again, as scene 2 begins
STEP, SLOW, RECENT = 0.10, 0.17, 2015             # s per autumn going forward; slower from 2015 (the last decade)
FADE = 0.10                                       # s: one autumn dissolves into the next (at most half a step)
STRETCH, GAMMA = 0.30, 1.3                        # reflectance shown as white; one stretch for every year
PIC_W = WIN[2] - 6                                # px: the picture spans the window's inner width
BOX = (51.6100, 35.7830, 51.7000, 35.8170)        # W, S, E, N: the reservoir and its shore, in the picture
DAM = (51.6793, 35.7901)                          # lon, lat: the dam (the reservoir's southern end)
KM_MAX, TICKS = 3.0, (0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0)   # km2: the gauge's scale
BAR_H = 30                                        # px: the gauge's bar
SOURCE, SOURCE_PX = 38, 30
CHIP_H = 72                                       # px: a year box on the picture (phone floor: at least 70)


def persian(year: int) -> int:
    return year - 621                              # the autumn of Y lies in Persian year Y - 621


def words() -> dict:
    off = latyan.OFFICIAL["latyan"]
    total = len(latyan.all_years())
    return dict(
        scenes=(("کرج برگشت؛ // لتیان چه؟", ""),
                (f"پاییزِ ۱۴۰۴: // {{کوچک‌ترین}} در {fa(total)} پاییز", ""),
                ("امسال: {دو‌سومِ} معمول؛ // حجمِ آب: نصفِ میانگین", "")),
        follow="این را برای کسی بفرستید که آبِ تهران برایش مهم است",
        gauge="میانه‌ی ۳۸ پاییز", unit="کیلومترمربع", dam="سدِ لتیان", scale="۱ کیلومتر",
        store_value=off["value"], store="میلیون مترمکعب",
        store_line=f"سدِ لتیان، ۱ آبان ۱۴۰۵؛ پارسال {fa(off['last_year'])} میلیون مترمکعب",
        sources=("منبع: لندست (USGS)، هر سال گذرِ نزدیک به ۹ مهر؛ وسعت: برآورد",
                 "آمارِ سد: شرکتِ آبِ منطقه‌ای تهران، خبرگزاریِ مهر، ۴ آبان ۱۴۰۵"),
    )


def picture_size(box: tuple) -> tuple:
    """The picture at its true shape: the box's longitude squeezed by the cosine of its latitude."""
    w, s, e, n = box
    return PIC_W, round(PIC_W * (n - s) / ((e - w) * math.cos(math.radians((s + n) / 2))))


def crop(grid: np.ndarray, box: tuple) -> np.ndarray:
    """The part of the fixed grid inside the box (W, S, E, N); the last two axes are rows and columns."""
    w, s, e, n = box
    c0, c1 = round((w - get_latyan.GRID[0]) / get_latyan.RES), round((e - get_latyan.GRID[0]) / get_latyan.RES)
    r0, r1 = round((get_latyan.GRID[3] - n) / get_latyan.RES), round((get_latyan.GRID[3] - s) / get_latyan.RES)
    return grid[..., r0:r1, c0:c1]


class LatyanFilm(Slides):
    def __init__(self, th: onebit.Theme, colour: dict):
        self.years = latyan.years()
        self.all = latyan.all_years()
        assert self.years[0] == 1987 and self.years[-1] == 2026, self.years
        assert sorted(set(self.all) - set(self.years)) == sorted(latyan.NOT_SHOWN), "the years left out are NOT_SHOWN"
        assert sorted(latyan.NO_PASS) == [2003, 2011], "no frame: 2003 and 2011"
        self.area = {y: latyan.area(y) for y in self.all}
        self.med = latyan.median()
        assert len(self.all) == EXPECT["total"], len(self.all)
        assert EXPECT["median"][0] <= self.med < EXPECT["median"][1], self.med
        assert len(latyan.near_median()) == EXPECT["near"], latyan.near_median()
        a25, a26 = self.area[2025], self.area[2026]
        assert EXPECT["ratio_1404"][0] <= a25 / self.med < EXPECT["ratio_1404"][1], (a25, self.med)
        assert EXPECT["ratio_1405"][0] <= a26 / self.med <= EXPECT["ratio_1405"][1], (a26, self.med)
        assert a26 > a25, "scene 3: 1405 above 1404"
        assert sorted(self.all, key=self.area.get)[0] == EXPECT["smallest"], "1404 is the smallest of the 38"
        off = latyan.OFFICIAL["latyan"]
        assert latyan.jalali(off["date"]) == "1 Aban 1405", latyan.jalali(off["date"])
        assert (off["value"], off["long_term"], off["last_year"]) == EXPECT["official"], off
        assert off["long_term"] == 2 * off["value"], "scene 3: the volume is half the long-term average"
        self.pic_size = picture_size(BOX)
        self.photos = {y: self.photo(y, th) for y in self.years}
        self.split = self.lake_middle()
        self.hook_at_once = True
        self.setup(th, "fa", colour, words(), PACE, "Latyan.Dam")
        dots = np.zeros((1920, 1080), bool)               # the sources sit in the window
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        self.dots = dots
        self.layout()
        self.schedule()
        self.done = 0.6
        assert float(self.starts[1]) + self.later(1) < 8, "scene 2's number must land by about 8 s"

    def lake_middle(self) -> float:
        """Where the cover splits, as a share of the picture's width: through the middle of the 2025 (1404)
        water, so that both halves of the cover show water: 1404 right, 1405 left."""
        m = crop(latyan.water(2025), BOX) == 1
        return float((np.nonzero(m)[1].mean() + 0.5) / m.shape[1])

    def photo(self, year: int, th: onebit.Theme) -> Image.Image:
        """The year's pass over the reservoir and its shore, one stretch for all years."""
        rgb = crop(latyan.picture(year), BOX)
        v = np.clip(rgb / STRETCH, 0, 1) ** (1 / GAMMA)
        field = np.array([int(th.field[k:k + 2], 16) / 255 for k in (1, 3, 5)])[:, None, None]
        v = np.where(np.isnan(v), field, v)                # not clear: the paper
        im = Image.fromarray((np.moveaxis(v, 0, -1) * 255 + 0.5).astype(np.uint8))
        return im.resize(self.pic_size, Image.LANCZOS)

    def layout(self):
        self.pic = (WIN[0] + 3, RULE + 24)
        self.pic_bottom = self.pic[1] + self.pic_size[1]
        self.source_y = WIN[1] + WIN[3] - 24 - SOURCE * len(self.words["sources"]) + SOURCE + 6
        self.dam_xy = self.locate(DAM)
        self.mark_y = self.pic_bottom + 52               # the median mark's label
        self.bar_y = self.pic_bottom + 72                # the gauge bar: 0 km2 at the right, as in Persian
        self.tick_y = self.bar_y + BAR_H + 38
        self.val_y = self.tick_y + 60
        self.off_y = self.val_y + 60
        self.off_y2 = self.off_y + 36
        assert self.pic_bottom + 22 < self.mark_y - 22, "the picture runs into the gauge"
        assert self.off_y2 + 10 < self.source_y - 22, "the second counter runs into the sources"

    def locate(self, lon_lat: tuple) -> tuple:
        lon, lat = lon_lat
        w, s, e, n = BOX
        return (self.pic[0] + (lon - w) / (e - w) * self.pic_size[0],
                self.pic[1] + (n - lat) / (n - s) * self.pic_size[1])

    def km_x(self, km: float) -> float:
        return RIGHT - km / KM_MAX * (RIGHT - LEFT)

    def schedule(self):
        """Keyframes (time, year): 1405 at 0 s, 1404 at JUMP, the rewind to 1366, forward again from FORWARD
        (the last decade slower), 1405 as the last scene begins."""
        back = self.years[-2::-1]                          # 2025 ... 1987, the shown years
        step = (REWIND[1] - REWIND[0]) / (len(back) - 1)
        keys = [(0.0, self.years[-1]), (JUMP, self.years[-2])]
        keys += [(REWIND[0] + k * step, y) for k, y in enumerate(back)]
        t, self.at = FORWARD, {}
        for y in self.years[1:-1]:                         # 1988 ... 2025, shown years only
            keys.append((t, y))
            self.at[y] = t
            t += STEP if y < RECENT else SLOW
        self.at[1987] = REWIND[1]
        assert self.at[2025] < float(self.starts[2]) - 1.0, "1404 must arrive a second before the last scene"
        keys.append((float(self.starts[2]), 2026))
        self.at[2026] = keys[-1][0]
        self.keys = keys

    # ── time ──

    def later(self, i: int) -> float:
        return 1.6                                         # once the first part is in (0.3-1.5 s)

    def appear(self, i: int) -> list:
        """The part after the break comes in as one: a number never stands without its unit."""
        t = super().appear(i)
        ws = [w for w, _ in onebit.words_of(self.S.scenes[i].title, self.th)]
        if i > 0 and "//" in ws:
            first = ws.index("//")
            t = t[:first] + [self.later(i)] * (len(t) - first)
        return t

    def state(self, t: float):
        """(year, next year, blend 0-1), or None for the cover."""
        if not np.isfinite(t):
            return None
        k = max(i for i, (at, _) in enumerate(self.keys) if at <= max(t, 0.0))
        y = self.keys[k][1]
        if k + 1 < len(self.keys):
            nxt_at, nxt = self.keys[k + 1]
            fade = min(FADE, 0.5 * (nxt_at - self.keys[k][0]))
            a = (t - (nxt_at - fade)) / fade
            if a > 0:
                return y, nxt, min(a, 1.0)
        return y, y, 0.0

    # ── drawing ──

    def scaled(self, im: Image.Image, c: Canvas) -> Image.Image:
        return im if c.k == 1 else im.resize((round(im.width * c.k), round(im.height * c.k)), Image.LANCZOS)

    def chip(self, c: Canvas, x: float, y: float, s: str, right: bool = True):
        """A year on the picture, in a paper box: right puts its right edge at x, else its left edge."""
        w = c.width(s, FA_BOLD, 48, "rtl")
        x0 = x - w - 28 if right else x
        assert CHIP_H >= 70, "phone floor: a year box is at least 70 px tall"
        c.frame(x0, y, x0 + w + 28, y + CHIP_H, fill=self.th.field)
        c.text(x0 + w + 14, y + 53, s, FA_BOLD, 48, self.th.ink, "rs", "rtl")

    def picture(self, c: Canvas, t: float):
        x, y = self.pic
        w, h = self.pic_size
        s = self.state(t)
        if s is None:                                      # the cover: east 1404 (2025), west 1405 (2026)
            east, west = self.photos[2025], self.photos[2026]
            half = round(w * self.split)
            im = east.copy()
            im.paste(west.crop((0, 0, half, h)), (0, 0))
            c.im.paste(self.scaled(im, c), (c.X(x), c.Y(y)))
            c.fill(x + half - 2, y, x + half + 2, y + h, self.th.field)
            self.chip(c, x + w - 14, y + 14, fa(persian(2025)))
            self.chip(c, x + half - 14, y + 14, fa(persian(2026)))
        else:
            a, b, wt = s
            im = self.photos[a] if wt == 0 else Image.blend(self.photos[a], self.photos[b], wt)
            c.im.paste(self.scaled(im, c), (c.X(x), c.Y(y)))
            self.chip(c, x + w - 14, y + 14, fa(persian(b if wt >= 0.5 else a)))
        xd, yd = self.dam_xy                               # the dam: a dot and its name
        c.frame(xd - 6, yd - 6, xd + 6, yd + 6, fill=self.th.field)
        tw = c.width(self.words["dam"], FA_TEXT, 30, "rtl")
        c.frame(xd - 18 - tw - 20, yd - 72, xd - 18, yd - 30, fill=self.th.field)
        c.text(xd - 28, yd - 40, self.words["dam"], FA_TEXT, 30, self.th.ink, "rs", "rtl")
        km = w / ((BOX[2] - BOX[0]) * 111.32 * math.cos(math.radians((BOX[1] + BOX[3]) / 2)))   # px per km
        bx, by = x + 26, y + h - 46                        # a 1-km scale bar, bottom left, its label right of it
        tw = c.width(self.words["scale"], FA_TEXT, 30, "rtl")
        c.frame(bx - 14, by - 26, bx + km + 14 + tw + 14, by + 20, fill=self.th.field)
        c.fill(bx, by, bx + km, by + 8, self.th.ink)
        c.text(bx + km + 14 + tw, by + 8, self.words["scale"], FA_TEXT, 30, self.th.ink, "rs", "rtl")
        c.frame(x, y, x + w, y + h)

    def gauge(self, c: Canvas, t: float):
        th, col = self.th, self.colour
        s = self.state(t)
        year = 2026 if s is None else (s[1] if s[2] >= 0.5 else s[0])   # the year in the picture
        v = self.area[year]
        x0, x1 = self.km_x(v), RIGHT
        c.fill(x0, self.bar_y, x1, self.bar_y + BAR_H, col["water"])
        c.frame(LEFT, self.bar_y, RIGHT, self.bar_y + BAR_H, colour=th.ink)
        for k in TICKS:
            xx = self.km_x(k)
            c.fill(xx - 1, self.bar_y + BAR_H, xx + 1, self.bar_y + BAR_H + 8, th.ink)
            c.text(xx, self.tick_y, fa(f"{k:g}"), FA_TEXT, 30, th.ink, "ms", "rtl")
        xm = self.km_x(self.med)                           # the 38-year median: a dashed mark
        for yy in range(self.bar_y - 4, self.bar_y + BAR_H + 6, 12):
            c.fill(xm - 2, yy, xm + 2, yy + 7, th.ink)
        c.text(xm, self.mark_y, f"{self.words['gauge']}: {fa(f'{self.med:.2f}')}", FA_TEXT, 30, th.ink, "ms", "rtl")
        c.text(RIGHT, self.val_y, f"{fa(persian(year))}: {fa(f'{v:.2f}')} {self.words['unit']}", FA_BOLD, 52,
               th.ink, "rs", "rtl")                        # the value names its year (the cover is split)

    def official(self, c: Canvas):
        """The second counter of the last scene: the dam's storage as reported, and its date."""
        th = self.th
        c.text(RIGHT, self.off_y, f"{fa(self.words['store_value'])} {self.words['store']}", FA_BOLD, 52,
               th.mark, "rs", "rtl")
        c.text(RIGHT, self.off_y2, self.words["store_line"], FA_TEXT, 30, th.ink, "rs", "rtl")

    def sources(self, c: Canvas):
        for k, line in enumerate(self.words["sources"]):
            c.text(RIGHT, self.source_y + SOURCE * k, line, FA_TEXT, SOURCE_PX, self.th.head, "rs", "rtl")
            assert c.width(line, FA_TEXT, SOURCE_PX, "rtl") <= RIGHT - LEFT, line

    def body(self, c: Canvas, t: float):
        self.picture(c, t)
        self.gauge(c, t)
        if np.isfinite(t) and t >= self.at[2026]:        # the official storage of 1405 only with 1405's picture
            self.official(c)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="firuze", choices=["firuze"], help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    args = ap.parse_args()
    film = LatyanFilm(onebit.THEMES[args.theme], COLOURS[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"latyan_{args.theme}_fa"
    for old in (OUT / "social").glob(f"{base.name}_t*.png"):
        old.unlink()                                       # no stale frames of an earlier cut
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (0.0, 0.5, 1.5, 2.6, 4.6, st[1] + film.later(1) + 1.0, film.at[2025] + 0.05,
                  st[2] + 0.5, st[2] + film.later(2) + 1.0, st[-1] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
