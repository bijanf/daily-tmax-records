"""THE ZAYANDEH RUD AT SI-O-SE POL, 1370-1405 FROM SPACE: in which months water still reaches
the middle of Isfahan.

Measured data only, from zayandeh.py (outputs/zayandeh_log.txt) and get_zayandeh.py: Landsat
(USGS) over about 6 km of the river's bed around Si-o-se Pol. Per Persian month "full" when a
clear pass saw open water on at least 30 % of the reach, "low" at 5-30 %, "dry" under 5 %, "no
data" when no pass counted (clouds; Landsat 7's striped years are left out), nothing for the
months of 1405 still to come. The picture of each year is its late-summer (20 Aug-10 Oct)
true-colour median.

A slide on the frame of onebit_slides: one window, one bold line per scene. The picture on the
right (Persian reads it first), the "water calendar" on its left: one row per Persian year, 1370 at
the top, twelve squares each, Farvardin on the right. The first frame carries the whole question,
the dry river of 1404 and the whole calendar (the end state); the film rewinds to 1370 in 2 s,
then plays every year forward, the calendar growing row by row, the current row outlined: the
steady 1370s fast, the change slower, so that the dry 1404 stands under the last scene's line;
1405 comes last. Three scenes, 1.5 + 1.5 + 2 bars of 60 BPM = 20 s, a silent track.

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
REWIND = (0.3, 2.3)                               # s: 1404 back to 1370
FORWARD = 2.8                                     # s: 1370 forward again, after a short hold
FAST, SLOW = 0.10, 0.33                           # s per year going forward: the steady years to 1378, then
STEADY = 1378                                     # the change (Urmia's retention fell while nothing changed)
LAST = 3.2                                        # s into the last scene: 1405, after its line is whole
FADE = 0.10                                       # s: one year dissolves into the next (at most half a step)
STRETCH, GAMMA = 0.30, 1.3                        # reflectance shown as white; one stretch for every year
PIC_H = 790                                       # px: the picture's height
CELL, GAP, ROW = 17, 3, 18                        # px: a month's square, the gap, a year's row pitch
KEY_PX, SEASON_PX, YEAR_PX, BRIDGE_PX = 30, 30, 34, 30   # phone floors: labels >= 28-30, year axis >= 34
BRIDGE = (51.6675, 32.6445, "سی‌وسه‌پل")          # lon, lat, label on the picture
SOURCE, SOURCE_PX = 38, 30
COVER = 1995                                      # the cover's "before" half: 1374, full in 10 of its 11 months seen
# Scene 2 and 3: full months per year, asserted against the data in __init__ ("about 10", "about 2";
# outputs/zayandeh_log.txt: 1370-1379 10.2, 1400-1404 2.4).
EXPECT = {"1370s": (1370, 1379), "1400-1404": (1400, 1404)}


def persian(year: int) -> int:
    return year - 621                              # 20 Aug-10 Oct of year Y lies in Persian year Y - 621


def words() -> dict:
    return dict(scenes=(("زاینده‌رود در کدام ماه‌ها // به {اصفهان} می‌رسد؟", ""),
                        ("دهه‌ی ۱۳۷۰: // {حدودِ ۱۰ ماه} از ۱۲", ""),
                        ("۱۴۰۰ تا ۱۴۰۴: // {حدودِ ۲ ماه} از ۱۲", "")),
                follow="این را برای یک اصفهانی بفرستید",
                ends=("فروردین", "اسفند"),
                key=(("full", "پرآب"), ("low", "کم‌آب"), ("dry", "خشک"), ("none", "بدونِ داده")),
                sources=("منبع: لندست (USGS)؛ ۶ کیلومتر از بستر پیرامونِ سی‌وسه‌پل (JRC)",
                         "پرآب: دستِ‌کم یک بار آب در ۳۰٪ بسترِ دیده‌شده؛ کم‌آب: ۵ تا ۳۰٪"))


class ZayandehFilm(Slides):
    def __init__(self, th: onebit.Theme, colour: dict):
        self.years = zayandeh.years()
        assert self.years[0] == 1991 and self.years[-1] == 2026, self.years
        self.rows = list(range(zayandeh.PERSIAN[0], zayandeh.PERSIAN[1] + 1))
        self.cal = {jy: zayandeh.months(jy) for jy in self.rows}
        self.decades = {k: zayandeh.decade(a, b) for k, (a, b) in EXPECT.items()}
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
        assert float(self.starts[1]) + self.later(1) < 8, "scene 2's number must land by 8 s"

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
        self.wall_right = self.pic[0] - 26
        self.wall_left = self.wall_right - 12 * CELL - 11 * GAP
        assert self.wall_left - 10 - 80 >= LEFT, "the calendar runs into the year labels"
        self.key_y = (self.pic[1] + 30, self.pic[1] + 72)  # two rows of the key (baselines)
        self.season_y = self.pic[1] + 116
        self.wall_top = self.season_y + 14
        assert self.wall_top + len(self.rows) * ROW <= self.pic[1] + PIC_H, "the calendar is taller than the picture"

    def schedule(self):
        """Keyframes (time, year): 1404 at 0 s, the rewind to 1370, forward again, 1405 last."""
        upto = [y for y in self.years if y <= 2025]
        back = upto[::-1][1:]
        step = (REWIND[1] - REWIND[0]) / len(back)
        keys = [(0.0, 2025)] + [(REWIND[0] + k * step, y) for k, y in enumerate(back)]
        t, self.at = FORWARD, {}
        for y in upto[1:]:
            keys.append((t, y))
            self.at[y] = t
            t += FAST if persian(y) < STEADY else SLOW
        assert self.at[2025] < float(self.starts[2]), "the years run past the last scene"
        keys.append((float(self.starts[2]) + LAST, 2026))
        assert LAST >= self.later(2) + 1.0, "1405 must come after the last line is whole"
        self.at[2026] = keys[-1][0]
        self.keys = keys

    # ── time ──

    def later(self, i: int) -> float:
        return 1.6                                        # once the first part is in (0.3-1.5 s)

    def appear(self, i: int) -> list:
        """The part after the break comes in as one: a number never stands without its "of 12"."""
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
        tw = c.width(name, FA_TEXT, BRIDGE_PX, "rtl")
        c.frame(bx - 18 - tw - 20, by - 72, bx - 18, by - 30, fill=self.th.field)
        c.text(bx - 28, by - 40, name, FA_TEXT, BRIDGE_PX, self.th.ink, "rs", "rtl")
        c.frame(x, y, x + self.pic_w, y + PIC_H)

    def square(self, c: Canvas, box, state: str):
        col = self.colour
        if state == "full":
            c.fill(*box, col["water"])
        elif state == "low":
            c.fill(*box, col["low"])
        elif state == "dry":
            c.fill(*box, col["dry"])
            c.frame(*box, colour=col["line"])
        elif state == "none":                             # no counted pass: an empty square
            c.frame(*box, colour=col["line"])

    def wall(self, c: Canvas, t: float):
        th = self.th
        upto = persian(self.shown_year(t))               # rows up to the year in the picture
        key = self.words["key"]                           # the key in two rows, right to left
        for row, items in enumerate((key[:2], key[2:])):
            x, base = self.wall_right, self.key_y[row]
            for k, name in items:
                self.square(c, (x - 26, base - 24, x, base + 2), k)
                c.text(x - 36, base, name, FA_TEXT, KEY_PX, th.ink, "rs", "rtl")
                x -= 36 + c.width(name, FA_TEXT, KEY_PX, "rtl") + 34
        first, last = self.words["ends"]                  # the year runs from Farvardin (right) to Esfand
        c.text(self.wall_right, self.season_y, first, FA_TEXT, SEASON_PX, th.ink, "rs", "rtl")
        c.text(self.wall_left + c.width(last, FA_TEXT, SEASON_PX, "rtl"), self.season_y, last, FA_TEXT,
               SEASON_PX, th.ink, "rs", "rtl")
        for r, jy in enumerate(self.rows):
            y0 = self.wall_top + r * ROW
            if jy % 5 == 0:
                c.text(self.wall_left - 10, y0 + 20, fa(jy), FA_TEXT, YEAR_PX, th.ink, "rs", "rtl")
            if jy > upto:
                continue
            for jm, state in enumerate(self.cal[jy]):    # Farvardin on the right
                right = self.wall_right - jm * (CELL + GAP)
                self.square(c, (right - CELL, y0, right, y0 + ROW - 3), state)
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
                  st[2] + film.later(2) + 1.0, film.at[2026] + 0.5, st[-1] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
