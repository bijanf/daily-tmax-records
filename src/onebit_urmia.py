"""LAKE URMIA, 40 YEARS FROM SPACE: the late-summer lake in true colour every year since 1986.

Measured data only. Pictures and levels from urmia.py (outputs/urmia_log.txt):
- Landsat (USGS) in true colour: per year the median of up to six least-cloudy scenes per path
  between 20 August and 10 October (29 Mordad to 18 Mehr); 1993 has none. White on the bed is
  salt crust or a thin film of brine over salt.
- The level: the in-situ September mean to 2019 (Mendeley deposit), later years from official
  statements (urmia.OFFICIAL: 1400, 1404, 1405): September 1995 1,277.89 m, early Mehr 1404
  1,269.50 m (8.4 m lower), 19 Mehr 1405 1,270.58 m (7.3 m below 1995, 1.1 m above 1404). For
  1399 and 1401-1403 no end-of-Shahrivar figure was found: the gauge holds the last measured
  year's level and its heading names that year («ترازِ آبِ ۱۴۰۰» over the picture of 1402).
- "Less than a tenth" (scene 2), fact check of 27 Oct 2026: the reported extent fell from about
  6,900 km2 (Khordad 1374) to 481 km2 (early Mehr 1404); open water in Landsat 1.6 % (MNDWI > 0
  and NIR < 0.10) to 8.2 % (NDWI > 0) of September 1995; the official volume from 32-36 to 0.24
  billion m3. Causes are in the caption, not on screen.

A slide on the frame of onebit_slides: one window, one bold line per scene. The picture on the
right (Persian reads it first), the level gauge on its left. The first frame carries the whole
question and the end state, the white lake of 1404 (the winners of the round-5 scouting open on
the end state, then rewind); the film rewinds to 1365 in 2 s (the first answer, the blue lake, by
2.3 s), then plays every year forward to 1404 (the years before 1374 quickly), the year on the
picture and the gauge falling with it; the last scene is 1405. The cover splits the lake down the
middle, its east half in 1374 and its west half in 1404. Three scenes, 1.5 + 1.5 + 2 bars of
60 BPM = 20 s, a silent track (music in the app).

    outputs/onebit/social/urmia_namak_fa_reel.mp4, _cover.png

    python -I src/onebit_urmia.py
    python -I src/onebit_urmia.py --stills
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import onebit  # noqa: E402
import urmia  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, SIZES, SOCIAL_CRF, Canvas, fa  # noqa: E402
from onebit_slides import COLOURS, LEFT, RIGHT, RULE, WIN, Slides  # noqa: E402

PACE = dict(bpm=60, bars=(1.5, 1.5, 2))
EXPECT = {1995: 1277.9, 2025: 1269.5, 2026: 1270.6}   # m, rounded: the published reel
REWIND = (0.3, 2.3)                               # s: 1404 back to 1365
FORWARD = 2.8                                     # s: 1365 forward again, after a short hold
FAST, SLOW = 0.15, 0.26                           # s per year going forward: before 1995, then 1995-2025
FADE = 0.12                                       # s: one year dissolves into the next (at most half a step)
STRETCH, GAMMA = 0.32, 1.3                        # reflectance shown as white; one stretch for every year
PIC_H = 790                                       # px: the picture's height (its width follows the lake)
TUBE = (300, 356)                                 # px: the gauge's tube, left and right
LEVELS = (1269.0, 1279.0)                         # m: the gauge's range
SOURCE, SOURCE_PX = 38, 30


def persian(year: int) -> int:
    return year - 621                              # 20 Aug-10 Oct of year Y lies in Persian year Y - 621


def words() -> dict:
    return dict(scenes=(("دریاچه‌ی ارومیه // {۴۰ سال} پیش چه شکلی بود؟", ""),
                        ("از ۱۳۷۴ تا ۱۴۰۴: // {کمتر از یک‌دهم} آب ماند", ""),
                        ("امسال بهتر شد، // اما هنوز {۷ متر} پایین‌تر از ۱۳۷۴", "")),
                follow="برای داده‌های اقلیمی بیشتر، دنبال کنید",
                gauge="ترازِ آبِ", unit="متر",
                sources=("منبع: تصاویرِ لندست (USGS)، اواخرِ مرداد تا اواسطِ مهر؛ سفید: نمک",
                         "تراز: اندازه‌گیریِ میدانی (Mendeley) تا ۱۳۹۸، سپس آمارِ رسمی",
                         "وسعتِ رسمی: خردادِ ۱۳۷۴ حدود ۶٬۹۰۰، مهرِ ۱۴۰۴: ۴۸۱ کیلومترِ مربع"))


class UrmiaFilm(Slides):
    def __init__(self, th: onebit.Theme, colour: dict):
        lv = urmia.levels()
        got = {y: round(float(lv.loc[y]), 1) for y in EXPECT}
        assert got == EXPECT, got
        assert lv.loc[1995] - lv.loc[2025] >= 8.0, "scene 2's gauge: about 8 m"
        assert round(lv.loc[1995] - lv.loc[2026]) == 7, "scene 3: 7 m below 1374"
        self.years = urmia.years()
        assert self.years[0] == 1986 and self.years[-1] == 2026 and 1993 not in self.years, self.years
        self.level = lv                                   # the gauge holds the last measured year's level,
        self.measured = {y: max(m for m in lv.index if m <= y) for y in self.years}   # its heading names it
        assert max(y - m for y, m in self.measured.items()) <= 3, self.measured
        self.photos = {y: self.photo(y, th) for y in self.years}
        self.pic_w = self.photos[1995].width
        self.hook_at_once = True
        self.setup(th, "fa", colour, words(), PACE, "Urmia.Lake")
        dots = np.zeros((1920, 1080), bool)               # the sources sit in the window
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        self.dots = dots
        self.layout()
        self.schedule()
        self.done = 0.6
        assert float(self.starts[1]) + self.later(1) < 15, "scene 2's number must land before 15 s"

    def photo(self, year: int, th) -> Image.Image:
        """The year's lake, one stretch for all years, squeezed from the lon/lat grid to its true shape."""
        rgb = urmia.colour(year)["rgb"]
        v = np.clip(rgb / STRETCH, 0, 1) ** (1 / GAMMA)
        field = np.array([int(th.field[k:k + 2], 16) / 255 for k in (1, 3, 5)])[:, None, None]
        v = np.where(np.isnan(v), field, v)                # unseen: the paper
        im = Image.fromarray((np.moveaxis(v, 0, -1) * 255 + 0.5).astype(np.uint8))
        h0, w0 = rgb.shape[1:]
        w = round(PIC_H * w0 * np.cos(np.deg2rad(37.7)) / h0)
        return im.resize((w, PIC_H), Image.LANCZOS)

    def layout(self):
        inner_top = RULE + 24
        inner_bot = WIN[1] + WIN[3] - 24 - SOURCE * len(self.words["sources"])
        self.source_y = inner_bot + SOURCE - 8
        gap = (inner_bot - inner_top - PIC_H) / 2
        assert gap >= 12, f"the picture does not fit the window ({gap:.0f})"
        self.pic = (RIGHT - self.pic_w, inner_top + gap)
        assert TUBE[1] + 70 <= self.pic[0], "the gauge runs into the picture"
        self.gauge_mid = (LEFT + TUBE[1]) / 2 + 20
        self.head_y = self.pic[1] + 34
        self.count_y = self.head_y + 76
        self.tube_top, self.tube_bot = self.count_y + 46, self.pic[1] + PIC_H - 6

    def schedule(self):
        """Keyframes (time, year): 1404 at 0 s, the rewind to 1365, forward again (the years before
        1995 fast), 1405 at the start of the last scene."""
        upto = [y for y in self.years if y <= 2025]
        back = upto[::-1][1:]                              # 2024 ... 1986
        step = (REWIND[1] - REWIND[0]) / len(back)
        keys = [(0.0, 2025)] + [(REWIND[0] + k * step, y) for k, y in enumerate(back)]
        t, self.at = FORWARD, {}
        for y in upto[1:]:                                 # 1987 ... 2025
            keys.append((t, y))
            self.at[y] = t
            t += FAST if y < 1995 else SLOW
        assert self.at[2025] < float(self.starts[2]), "the years run past the last scene"
        keys.append((float(self.starts[2]) + 0.3, 2026))
        self.at[2026] = keys[-1][0]
        self.keys = keys

    # ── time ──

    def later(self, i: int) -> float:
        return 1.6                                        # once the first part is in (0.3-1.5 s)

    def state(self, t: float):
        """(year, next year, blend 0-1), or None for the split (the cover)."""
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

    def chip(self, c: Canvas, x: float, y: float, s: str, anchor: str):
        """A year on the picture, in a paper box: anchor 'r' puts its right edge at x."""
        w = c.width(s, FA_BOLD, 48, "rtl")
        x0 = x - w - 28 if anchor == "r" else x
        c.frame(x0, y, x0 + w + 28, y + 64, fill=self.th.field)
        c.text(x0 + w + 14, y + 50, s, FA_BOLD, 48, self.th.ink, "rs", "rtl")

    def picture(self, c: Canvas, t: float):
        x, y = self.pic
        s = self.state(t)
        if s is None:                                     # the cover: east 1374, west 1404
            east, west = self.photos[1995], self.photos[2025]
            half = east.width // 2
            im = west.copy()
            im.paste(east.crop((half, 0, east.width, east.height)), (half, 0))
            c.im.paste(self.scaled(im, c), (c.X(x), c.Y(y)))
            c.fill(x + half - 2, y, x + half + 2, y + PIC_H, self.th.field)
            self.chip(c, x + self.pic_w - 14, y + 14, fa(persian(1995)), "r")
            self.chip(c, x + 14, y + 14, fa(persian(2025)), "l")
        else:
            a, b, w = s
            im = self.photos[a] if w == 0 else Image.blend(self.photos[a], self.photos[b], w)
            c.im.paste(self.scaled(im, c), (c.X(x), c.Y(y)))
            self.chip(c, x + self.pic_w - 14, y + 14, fa(persian(b if w >= 0.5 else a)), "r")
        c.frame(x, y, x + self.pic_w, y + PIC_H)

    def ly(self, level: float) -> float:
        lo, hi = LEVELS
        return self.tube_bot - (level - lo) / (hi - lo) * (self.tube_bot - self.tube_top)

    def gauge(self, c: Canvas, t: float):
        th, col = self.th, self.colour
        x0, x1 = TUBE
        s = self.state(t)
        if s is None:                                     # the cover: 1404's water, 1374's mark
            now, shown, past = float(self.level.loc[2025]), 2025, True
        else:
            a, b, w = s
            la, lb = (float(self.level.loc[self.measured[y]]) for y in (a, b))
            now = (1 - w) * la + w * lb                   # the water moves with the picture
            shown = self.measured[b if w >= 0.5 else a]   # the number is always a measured year's
            past = t >= self.at[1995]                     # 1374's mark from the forward pass on
        c.fill(x0, self.ly(now), x1, self.tube_bot, col["water"])
        c.frame(x0, self.tube_top, x1, self.tube_bot)
        for m in range(1270, 1279, 2):                    # the scale, left of the tube
            yy = self.ly(m)
            c.fill(x0 - 10, yy - 1, x0, yy + 1, th.ink)
            c.text(x0 - 16, yy + 10, fa(m), FA_TEXT, 30, th.ink, "rs", "rtl")
        if past:                                          # 1374's level stays as a dashed line
            yy = self.ly(float(self.level.loc[1995]))
            for xx in np.arange(x0 - 4, x1 + 8, 12):
                c.fill(xx, yy - 2, xx + 7, yy + 2, th.ink)
            c.text(x1 + 12, yy + 10, fa(persian(1995)), FA_TEXT, 28, th.ink, "ls", "rtl")
        self.say(c, self.gauge_mid, self.head_y, f"{self.words['gauge']} {fa(persian(shown))}", 36, True, th.ink, "ms")
        v = fa(f"{float(self.level.loc[shown]):.1f}")
        c.text(self.gauge_mid + 4, self.count_y, f"{v} {self.words['unit']}", FA_BOLD, 52, th.ink, "ms", "rtl")

    def sources(self, c: Canvas):
        for k, line in enumerate(self.words["sources"]):
            c.text(RIGHT, self.source_y + SOURCE * k, line, FA_TEXT, SOURCE_PX, self.th.head, "rs", "rtl")
            assert c.width(line, FA_TEXT, SOURCE_PX, "rtl") <= RIGHT - LEFT, line

    def body(self, c: Canvas, t: float):
        self.picture(c, t)
        self.gauge(c, t)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="namak", choices=["namak"], help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    args = ap.parse_args()
    film = UrmiaFilm(onebit.THEMES[args.theme], COLOURS[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"urmia_{args.theme}_fa"
    for old in (OUT / "social").glob(f"{base.name}_t*.png"):
        old.unlink()                                      # no stale frames of an earlier cut
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (0.0, 1.3, 2.5, film.at[1995] + 0.1, st[1] + film.later(1) + 1.0, film.at[2025] + 0.1,
                  st[2] + film.later(2) + 1.5, st[-1] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
