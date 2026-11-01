"""THE ZAYANDEH RUD IN ISFAHAN, 40 YEARS FROM SPACE: in which months the river still flows.

Measured data only, from zayandeh.py (outputs/zayandeh_log.txt) and get_zayandeh.py: Landsat
(USGS) over Isfahan's river reach, Si-o-se Pol in the middle; per Persian month "wet" when a clear
pass saw the river flowing (open water on at least 30 % of the channel), "dry" when every clear
pass saw it dry, "none" when no pass counted. The picture of each year is its late-summer
(20 Aug-10 Oct) true-colour median.

A slide on the frame of onebit_slides: one window, one bold line per scene. The picture on the
right (Persian reads it first), the "water calendar" on its left: one row per Persian year, 1365 at
the top, twelve squares each, Farvardin on the right; turquoise where the river was seen flowing,
sand where it was dry, empty where no pass counted. The first frame carries the whole question,
the dry river of 1404 and the whole calendar (the end state); the film rewinds to 1365 in 2 s,
then plays every year forward, the calendar growing row by row, the current row outlined; 1405 in
the last scene. Three scenes, 1.5 + 1.5 + 2 bars of 60 BPM = 20 s, a silent track.

    outputs/onebit/social/zayandeh_naqsh_fa_reel.mp4, _cover.png

    python -I src/onebit_zayandeh.py
    python -I src/onebit_zayandeh.py --stills
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import onebit  # noqa: E402
import zayandeh  # noqa: E402
from get_zayandeh import BOX  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, SIZES, SOCIAL_CRF, Canvas, fa  # noqa: E402
from onebit_slides import COLOURS, LEFT, RIGHT, RULE, WIN, Slides  # noqa: E402

PACE = dict(bpm=60, bars=(1.5, 1.5, 2))
REWIND = (0.3, 2.3)                               # s: 1404 back to 1365
FORWARD = 2.8                                     # s: 1365 forward again, after a short hold
STEP = 0.22                                       # s per year going forward
FADE = 0.10                                       # s: one year dissolves into the next (at most half a step)
STRETCH, GAMMA = 0.30, 1.3                        # reflectance shown as white; one stretch for every year
PIC_H = 790                                       # px: the picture's height
CELL, GAP = 19, 3                                 # px: a month's square and the gap between squares
ROW = 15                                          # px: a year's row pitch (12 px squares)
BRIDGE = (51.6675, 32.6445, "سی‌وسه‌پل")          # lon, lat, label on the picture
SOURCE, SOURCE_PX = 38, 30
COVER = 1995                                      # the cover's "before" half: 1374, full in 10 of its 11 months seen
# Scene 2 and 3: full months per year, asserted against the data in __init__ ("about 10", "about 2";
# outputs/zayandeh_log.txt: 1370-1379 10.2, 1400-1404 2.4).
EXPECT = {"1370s": (1370, 1379), "1400-1404": (1400, 1404)}


def persian(year: int) -> int:
    return year - 621                              # 20 Aug-10 Oct of year Y lies in Persian year Y - 621


def words() -> dict:
    return dict(scenes=(("زاینده‌رود در اصفهان // {چند ماه} از سال آب دارد؟", ""),
                        ("دهه‌ی ۱۳۷۰: // {حدودِ ۱۰ ماه} از سال", ""),
                        ("۱۴۰۰ تا ۱۴۰۴: // فقط {حدودِ ۲ ماه}", "")),
                follow="برای داده‌های اقلیمی بیشتر، دنبال کنید",
                seasons=("بهار", "تابستان", "پاییز", "زمستان"),
                key=(("full", "پرآب"), ("low", "کم‌آب"), ("dry", "خشک")),
                sources=("منبع: تصاویرِ لندست (USGS) · بسترِ رود: JRC",
                         "پرآب: ماهواره دستِ‌کم ۳۰٪ بستر را آب دید؛ کم‌آب: ۵ تا ۳۰٪"))


class ZayandehFilm(Slides):
    def __init__(self, th: onebit.Theme, colour: dict):
        self.years = zayandeh.years()
        assert self.years[0] <= 1987 and self.years[-1] == 2026, self.years
        self.rows = list(range(zayandeh.PERSIAN[0], zayandeh.PERSIAN[1] + 1))
        self.cal = {jy: zayandeh.months(jy) for jy in self.rows}
        full = {jy: zayandeh.counts(jy)[0] for jy in self.rows}
        self.decades = {k: float(np.mean([full[jy] for jy in range(a, b + 1)])) for k, (a, b) in EXPECT.items()}
        assert {k: round(v) for k, v in self.decades.items()} == {"1370s": 10, "1400-1404": 2}, self.decades
        self.photos = {y: self.photo(y, th) for y in self.years}
        self.pic_w = self.photos[self.years[-1]].width
        self.hook_at_once = True
        self.setup(th, "fa", colour, words(), PACE, "Zayandeh.Rud")
        dots = np.zeros((1920, 1080), bool)               # the sources sit in the window
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        self.dots = dots
        self.layout()
        self.schedule()
        self.done = 0.6
        assert float(self.starts[1]) + self.later(1) < 15, "scene 2's line must land before 15 s"

    def photo(self, year: int, th) -> Image.Image:
        """The year's reach, one stretch for all years, squeezed from the lon/lat grid to its true shape."""
        rgb = zayandeh.colour(year)
        v = np.clip(rgb / STRETCH, 0, 1) ** (1 / GAMMA)
        field = np.array([int(th.field[k:k + 2], 16) / 255 for k in (1, 3, 5)])[:, None, None]
        v = np.where(np.isnan(v), field, v)
        im = Image.fromarray((np.moveaxis(v, 0, -1) * 255 + 0.5).astype(np.uint8))
        h0, w0 = rgb.shape[1:]
        w = round(PIC_H * w0 * np.cos(np.deg2rad((BOX[1] + BOX[3]) / 2)) / h0)
        return im.resize((w, PIC_H), Image.LANCZOS)

    def layout(self):
        inner_top = RULE + 24
        inner_bot = WIN[1] + WIN[3] - 24 - SOURCE * len(self.words["sources"])
        self.source_y = inner_bot + SOURCE - 8
        gap = (inner_bot - inner_top - PIC_H) / 2
        assert gap >= 12, f"the picture does not fit the window ({gap:.0f})"
        self.pic = (RIGHT - self.pic_w, inner_top + gap)
        self.wall_right = self.pic[0] - 28
        self.wall_left = self.wall_right - 12 * CELL - 11 * GAP
        assert self.wall_left - 64 >= LEFT, "the calendar runs into the year labels"
        self.key_y = self.pic[1] + 30
        self.season_y = self.key_y + 46
        self.wall_top = self.season_y + 16
        assert self.wall_top + len(self.rows) * ROW <= self.pic[1] + PIC_H, "the calendar is taller than the picture"

    def schedule(self):
        """Keyframes (time, year): 1404 at 0 s, the rewind to 1365, forward again, 1405 last."""
        upto = [y for y in self.years if y <= 2025]
        back = upto[::-1][1:]
        step = (REWIND[1] - REWIND[0]) / len(back)
        keys = [(0.0, 2025)] + [(REWIND[0] + k * step, y) for k, y in enumerate(back)]
        t, self.at = FORWARD, {}
        for y in upto[1:]:
            keys.append((t, y))
            self.at[y] = t
            t += STEP
        assert self.at[2025] < float(self.starts[2]), "the years run past the last scene"
        keys.append((float(self.starts[2]) + 0.3, 2026))
        self.at[2026] = keys[-1][0]
        self.keys = keys

    # ── time ──

    def later(self, i: int) -> float:
        return 1.6                                        # once the first part is in (0.3-1.5 s)

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

    def shown_year(self, t: float) -> int:
        s = self.state(t)
        return 2025 if s is None else (s[1] if s[2] >= 0.5 else s[0])

    # ── drawing ──

    def scaled(self, im: Image.Image, c: Canvas) -> Image.Image:
        return im if c.k == 1 else im.resize((round(im.width * c.k), round(im.height * c.k)), Image.LANCZOS)

    def chip(self, c: Canvas, x: float, y: float, s: str, size: int = 48):
        """A label on the picture in a paper box, its right edge at x."""
        w = c.width(s, FA_BOLD, size, "rtl")
        c.frame(x - w - 28, y, x, y + size + 16, fill=self.th.field)
        c.text(x - 14, y + size + 2, s, FA_BOLD, size, self.th.ink, "rs", "rtl")

    def picture(self, c: Canvas, t: float):
        x, y = self.pic
        s = self.state(t)
        if s is None:                                     # the cover: east 1374 (a full river), west 1404
            east, west = self.photos[COVER], self.photos[2025]
            half = east.width // 2
            im = west.copy()
            im.paste(east.crop((half, 0, east.width, east.height)), (half, 0))
            c.im.paste(self.scaled(im, c), (c.X(x), c.Y(y)))
            c.fill(x + half - 2, y, x + half + 2, y + PIC_H, self.th.field)
            self.chip(c, x + self.pic_w - 14, y + 14, fa(persian(COVER)))
            self.chip(c, x + half - 14, y + 14, fa(persian(2025)))
        else:
            a, b, w = s
            im = self.photos[a] if w == 0 else Image.blend(self.photos[a], self.photos[b], w)
            c.im.paste(self.scaled(im, c), (c.X(x), c.Y(y)))
            self.chip(c, x + self.pic_w - 14, y + 14, fa(persian(b if w >= 0.5 else a)))
        lon, lat, name = BRIDGE                           # Si-o-se Pol, a dot and its name
        bx = x + (lon - BOX[0]) / (BOX[2] - BOX[0]) * self.pic_w
        by = y + (BOX[3] - lat) / (BOX[3] - BOX[1]) * PIC_H
        c.frame(bx - 6, by - 6, bx + 6, by + 6, fill=self.th.field)
        tw = c.width(name, FA_TEXT, 28, "rtl")
        c.frame(bx - 18 - tw - 20, by - 70, bx - 18, by - 30, fill=self.th.field)
        c.text(bx - 28, by - 40, name, FA_TEXT, 28, self.th.ink, "rs", "rtl")
        c.frame(x, y, x + self.pic_w, y + PIC_H)

    def wall(self, c: Canvas, t: float):
        th, col = self.th, self.colour
        upto = persian(self.shown_year(t))               # rows up to the year in the picture
        x = self.wall_right                               # the key, right to left
        for k, name in self.words["key"]:
            c.fill(x - 24, self.key_y - 22, x, self.key_y + 2, col[{"full": "water"}.get(k, k)])
            c.frame(x - 24, self.key_y - 22, x, self.key_y + 2, colour=col["line"])
            c.text(x - 34, self.key_y, name, FA_TEXT, 28, th.ink, "rs", "rtl")
            x -= 34 + c.width(name, FA_TEXT, 28, "rtl") + 30
        for k, name in enumerate(self.words["seasons"]):  # seasons over three squares each, right to left
            right = self.wall_right - k * 3 * (CELL + GAP)
            mid = right - (3 * CELL + 2 * GAP) / 2
            c.text(mid, self.season_y, name, FA_TEXT, 24, th.ink, "ms", "rtl")
        for r, jy in enumerate(self.rows):
            y0 = self.wall_top + r * ROW
            if jy % 5 == 0 or jy in (self.rows[0], self.rows[-1]):
                c.text(self.wall_left - 10, y0 + 12, fa(jy), FA_TEXT, 22, th.ink, "rs", "rtl")
            if jy > upto:
                continue
            for jm, state in enumerate(self.cal[jy]):    # Farvardin on the right
                right = self.wall_right - jm * (CELL + GAP)
                box = (right - CELL, y0, right, y0 + ROW - 3)
                if state == "full":
                    c.fill(*box, col["water"])
                elif state == "low":
                    c.fill(*box, col["low"])
                elif state == "dry":
                    c.fill(*box, col["dry"])
                    c.frame(*box, colour=col["line"])
            if jy == upto and np.isfinite(t):             # the row of the year in the picture
                c.frame(self.wall_left - 3, y0 - 2, self.wall_right + 3, y0 + ROW - 1)

    def sources(self, c: Canvas):
        for k, line in enumerate(self.words["sources"]):
            c.text(RIGHT, self.source_y + SOURCE * k, line, FA_TEXT, SOURCE_PX, self.th.head, "rs", "rtl")
            assert c.width(line, FA_TEXT, SOURCE_PX, "rtl") <= RIGHT - LEFT, line

    def body(self, c: Canvas, t: float):
        self.picture(c, t)
        self.wall(c, t)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="naqsh", choices=["naqsh"], help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    args = ap.parse_args()
    film = ZayandehFilm(onebit.THEMES[args.theme], COLOURS[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"zayandeh_{args.theme}_fa"
    for old in (OUT / "social").glob(f"{base.name}_t*.png"):
        old.unlink()                                      # no stale frames of an earlier cut
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (0.0, 1.3, 2.5, 5.0, st[1] + film.later(1) + 1.0, film.at[2025] + 0.05,
                  st[2] + film.later(2) + 1.5, st[-1] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
