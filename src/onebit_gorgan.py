"""THE GORGAN BAY FROM SPACE, 1986-2026: the bay's late-summer water in true colour every year, and the
Caspian Sea's level against 1374.

Measured data only, from gorgan.py (outputs/gorgan_log.txt) and get_gorgan.py:
- Pictures: Landsat (USGS) in true colour, per year the per-pixel median of the clear passes between 1 August
  and 30 September over path 163 row 034; 1995 is one pass (8 September). Where no pass sees a pixel clear,
  the bay is hatched (never filled); land and sea outside the bay are filled from the nearest year.
- Bay area: the wet share of the bay's clear pixels times the bay's area (588 km2), in whole km2 on screen.
  1992, 1993, 1997, 2002 and 2005 are shown as uncertain (gorgan.uncertain): their pictures stay.
- Caspian Sea: NASA GWM lake 270 (EGM2008), the Aug-Sep mean of each year against 1995 (1374). The gauge
  starts in 1372, the first Aug-Sep reading; before it the gauge is blank and says "satellite from 1371".
  2007 has no picture (no pass with half the bay clear) and is skipped.

A slide on the frame of onebit_slides: one window, one bold line per scene. The picture of the bay runs
across the window's text width, with its heading and year at the top, the area and a 10-km scale at the
bottom, and the places labelled with approximate positions (Wikipedia coordinates). Under it the gauge: the
Caspian's change against 1374 in metres, a line drawn year by year from 1372, with the current year's dot and
its value in words ("2.5 m lower"; no minus signs). Three scenes, 6 + 6 + 8 s at 60 BPM = 20 s, silent.

Time: frame 0 is 2026 (1405) with the whole question; the film rewinds to 1986 (1365) in 2 s, then plays
every year forward: 1987-2009 fast (the rise and the plateau), 2010-2025 slower (the decline). The bay has
visibly shrunk when the second line's number arrives (7.6 s, about 2015), 2025 (1404) comes before the last
scene, and 2026 (1405) comes after its line is whole (15.2 s).

    outputs/onebit/social/gorgan_khazar_fa_reel.mp4, _cover.png

    python -I src/onebit_gorgan.py
    python -I src/onebit_gorgan.py --stills
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import get_gorgan as gg  # noqa: E402
import gorgan  # noqa: E402
import onebit  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, SIZES, SOCIAL_CRF, Canvas, fa  # noqa: E402
from onebit_slides import COLOURS, LEFT, RIGHT, RULE, WIN, Slides  # noqa: E402

PACE = dict(bpm=60, bars=(1.5, 1.5, 2))          # 6 + 6 + 8 s = 20 s at 60 BPM
REWIND = (0.3, 2.3)                               # s: 2025 back to 1986 (Persian 1365), in 2 s
FORWARD = 2.8                                     # s: 1986 forward again, after a short hold
FAST, SLOW = 0.13, 0.388                          # s per year: 1987-2009 (the rise and the plateau), 2010-2025
SLOW_FROM = 2010                                  # the decline: Persian 1389 on
LAST = 3.2                                        # s into the last scene: 2026 (1405), after its line is whole
FADE = 0.12                                       # s: one year dissolves into the next (at most half a step)
STRETCH, GAMMA = 0.30, 1.3                        # reflectance shown as white; one stretch for every year
CROP = (882, 3235)                                # grid columns: lon 53.30-54.10 E
PIC_W = RIGHT - LEFT                              # px: the picture spans the text width (828)
PIC_H = round(PIC_W * (gg.NY * gg.DY * 111.32)
              / ((CROP[1] - CROP[0]) * gg.DX * 111.32 * np.cos(np.deg2rad(36.82))))   # its true shape: 517
PIC_Y = RULE + 24                                 # px: the picture's top, under the rule
PLOT = (344, 1170, 914, 1392)                     # px: the gauge's plot (x0, y0, x1, y1)
VMAX, VMIN = 0.2, -3.0                            # m: the plot's range (the 0 m reference 0.2 m below the top)
FIRST_READING = 1993                              # Gregorian: the first Aug-Sep mean (Persian 1372)
SOURCE, SOURCE_PX = 38, 30
MARK_PX = 34                                      # labels, axis and readouts: phone size
BASE_YEAR, NOW, LOW = 1995, 2026, 2025            # Gregorian: 1374, 1405, 1404 (the cover's west half)
# Places (lon, lat): the gulf's centroid, the barrier's centre (Wikipedia infobox), the two ports (city articles)
GULF = (53.880, 36.833)
SEA = (53.78, 36.990)
BARRIER = (53.75, 36.883)
TORKAMAN = (54.074, 36.901)
GAZ = (53.948, 36.774)

ZWNJ = "‌"
SCENES = (("خلیجِ گرگان {۴۰ سال} پیش // چه شکلی بود؟", ""),
          ("از ۱۳۷۴ تا ۱۴۰۵: // مساحتِ آب {حدودِ نصف} شد", ""),
          # the placeholder "۲٫۵ تا ۳ متر" set the upper bound with June 1995 against January 2026 (2.99 m), which
          # is not like for like. The same calendar month, 2026 against 1995 (ten months): 2.49 to 2.71 m.
          ("دریای خزر از ۱۳۷۴: // {۲٫۵ تا ۲٫۷ متر} پایین" + ZWNJ + "تر", ""))
SOURCES = ("منبع: تصاویرِ لندست (USGS)، اواخرِ تابستان",
           "تراز: آلتیمتریِ ماهواره" + ZWNJ + "ایِ ناسا؛ تغییر نسبت به ۱۳۷۴")


def words() -> dict:
    return dict(scenes=SCENES,
                follow="این را برای کسی بفرستید که میانکاله رفته",
                heading="خلیجِ گرگان: پهنه" + ZWNJ + "ی آبی",
                gauge="ترازِ دریای خزر نسبت به ۱۳۷۴ (متر)",
                places=(("خلیجِ گرگان", GULF, "c"), ("دریای خزر", SEA, "c"), ("میانکاله", BARRIER, "b"),
                        ("بندر ترکمن", TORKAMAN, "l"), ("بندر گز", GAZ, "l")),
                unit="کیلومترِ مربع", uncertain="نامطمئن", hatch="خط" + ZWNJ + "چین: دیده نشد",
                before="ماهواره از ۱۳۷۱", reference="۱۳۷۴", base="مبنا",
                below=" متر پایین" + ZWNJ + "تر", below_small="کمتر از ۰٫۱ متر پایین" + ZWNJ + "تر",
                scale="۱۰ کیلومتر", sources=SOURCES)


def pic_xy(lon: float, lat: float) -> tuple:
    """Screen position (px) of a lon/lat on the picture."""
    lon0, lon1 = gg.BOX[0] + CROP[0] * gg.DX, gg.BOX[0] + CROP[1] * gg.DX
    lat0, lat1 = gg.BOX[3], gg.BOX[3] - gg.NY * gg.DY
    return LEFT + (lon - lon0) / (lon1 - lon0) * PIC_W, PIC_Y + (lat0 - lat) / (lat0 - lat1) * PIC_H


def down(a: np.ndarray) -> np.ndarray:
    """An area mean of a 2-D array at the picture's size (box filter)."""
    im = Image.fromarray(np.ascontiguousarray(a, dtype=np.float32))
    return np.asarray(im.resize((PIC_W, PIC_H), Image.BOX), dtype=np.float32)


def pictures() -> tuple:
    """Per year the picture at the film's size (3 x H x W; NaN where never seen clear), the bay's mask at that
    size, and the share of the bay never seen clear."""
    R = gorgan.geometry()["R"][:, CROP[0]:CROP[1]].astype(np.float32)
    bay = down(R) >= 0.5
    pics = {}
    for y in gorgan.years():
        rgb = np.load(gg.DATA / f"{y}.npz")["rgb"][:, :, CROP[0]:CROP[1]].astype(np.float32)
        ok = np.isfinite(rgb).all(axis=0)
        frac = down(ok.astype(np.float32))
        pic = np.full((3, PIC_H, PIC_W), np.nan, np.float32)
        for b in range(3):
            s = down(np.where(ok, rgb[b], 0.0))
            with np.errstate(all="ignore"):
                pic[b] = np.where(frac >= 0.5, s / np.maximum(frac, 1e-6), np.nan)
        pics[y] = pic
    for y in sorted(pics):                                   # land and sea never seen: the nearest year's
        for d in (1, -1, 2, -2, 3, -3):
            if y + d not in pics:
                continue
            hole = np.isnan(pics[y][0]) & ~bay
            if not hole.any():
                break
            src = pics[y + d]
            fill = hole & np.isfinite(src[0])
            pics[y][:, fill] = src[:, fill]
    hatched = {y: float(np.isnan(pics[y][0]).mean()) for y in pics}     # the share of the picture never seen clear
    return pics, bay, hatched


def persian(year: int) -> int:
    return gorgan.persian(year)


class GorganFilm(Slides):
    def __init__(self, th: onebit.Theme, colour: dict):
        self.checks = gorgan.checks()                        # the published numbers; raises when one moves
        self.years = gorgan.years()
        assert self.years[0] == 1986 and self.years[-1] == 2026 and 2007 not in self.years, self.years
        self.level = {y: gorgan.caspian_change(y) for y in range(FIRST_READING, NOW + 1)}
        assert not any(np.isnan(self.level[y]) for y in range(FIRST_READING, NOW + 1)), "a gauge year is missing"
        self.label = {y: gorgan.on_screen(y) for y in self.years}
        self.pics, self.bay, self.hatched = pictures()
        self.photos = {y: self.photo(y, th) for y in self.years}
        self.hook_at_once = True
        self.setup(th, "fa", colour, words(), PACE, "Gorgan.Bay")
        dots = np.zeros((1920, 1080), bool)                  # the sources sit in the window
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        self.dots = dots
        self.layout()
        self.schedule()
        self.done = 0.6
        assert float(self.starts[1]) + self.later(1) < 8.0, "scene 2's number must land by 8 s"
        assert self.at[LOW] < float(self.starts[2]) - 0.3, "1404 must come before the last scene"

    # ── pictures ──

    def photo(self, year: int, th: onebit.Theme) -> Image.Image:
        """The year's bay at the picture's size; a chequer of ink where the bay was never seen clear."""
        pic = self.pics[year]
        v = np.clip(pic / STRETCH, 0, 1) ** (1 / GAMMA)
        field = np.array([int(th.field[k:k + 2], 16) / 255 for k in (1, 3, 5)], np.float32)[:, None, None]
        v = np.where(np.isnan(v), field, v)
        rgb = (np.moveaxis(v, 0, -1) * 255 + 0.5).astype(np.uint8)
        hole = np.isnan(pic[0])                              # never seen clear: in the bay, or outside the swath
        yy, xx = np.mgrid[0:PIC_H, 0:PIC_W]
        ink = np.array([int(th.ink[k:k + 2], 16) for k in (1, 3, 5)], np.uint8)
        rgb[((xx + yy) % 2 == 0) & hole] = ink
        return Image.fromarray(rgb)

    def layout(self):
        inner_bot = WIN[1] + WIN[3] - 24 - SOURCE * len(self.words["sources"])
        self.source_y = inner_bot + SOURCE - 8
        assert PIC_Y + PIC_H + 40 <= PLOT[1] - 20, "the picture and the gauge's heading do not fit"
        tick = onebit._font(FA_TEXT, MARK_PX).getlength(fa(3) + self.words["below"], direction="rtl")
        assert PLOT[0] - 12 - tick >= LEFT, f"the gauge's tick labels run into the margin ({tick:.0f} px)"

    def schedule(self):
        """Keyframes (time, year): 2026 at 0 s, the rewind to 1986, forward again, 2026 last."""
        upto = [y for y in self.years if y <= LOW]           # 1986..2025 without 2007
        back = upto[::-1]
        step = (REWIND[1] - REWIND[0]) / (len(back) - 1)
        keys = [(0.0, NOW)] + [(REWIND[0] + k * step, y) for k, y in enumerate(back)]
        t, self.at = FORWARD, {}
        for y in upto[1:]:                                    # 1987 ... 2025 (no 2007)
            keys.append((t, y))
            self.at[y] = t
            t += FAST if y < SLOW_FROM else SLOW
        assert abs(self.at[2015] - 7.6) < 0.1, f"2015 should be on screen at the second line's number: {self.at[2015]:.2f}"
        keys.append((float(self.starts[2]) + LAST, NOW))
        assert LAST >= self.later(2) + 1.0, "1405 must come after the last line is whole"
        self.at[NOW] = keys[-1][0]
        self.keys = keys

    # ── time ──

    def appear(self, i: int) -> list:
        """The part after the break comes in as one: a number never stands without its unit."""
        t = super().appear(i)
        ws = [w for w, _ in onebit.words_of(self.S.scenes[i].title, self.th)]
        if i > 0 and "//" in ws:
            first = ws.index("//")
            t = t[:first] + [self.later(i)] * (len(t) - first)
        return t

    def later(self, i: int) -> float:
        return 1.6                                            # once the first part is in (0.3-1.5 s)

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

    def label_box(self, c: Canvas, x: float, y: float, s: str, size: int, anchor: str = "l", bold: bool = True):
        """A label in a paper box: x is its left edge ('l'), its centre ('c') or its right edge ('r'); y the baseline."""
        font = FA_BOLD if bold else FA_TEXT
        w = c.width(s, font, size, "rtl")
        x0 = x if anchor == "l" else (x - w / 2 if anchor == "c" else x - w)
        c.frame(x0 - 12, y - size - 4, x0 + w + 12, y + 14, fill=self.th.field)
        c.text(x0 + w, y, s, font, size, self.th.ink, "rs", "rtl")

    def year_chip(self, c: Canvas, x: float, y: float, year: int, anchor: str):
        s = fa(year)
        w = c.width(s, FA_BOLD, 48, "rtl")
        x0 = x - w - 28 if anchor == "r" else x
        c.frame(x0, y, x0 + w + 28, y + 64, fill=self.th.field)
        c.text(x0 + w + 14, y + 50, s, FA_BOLD, 48, self.th.ink, "rs", "rtl")

    def picture(self, c: Canvas, t: float):
        x, y = LEFT, PIC_Y
        s = self.state(t)
        if s is None:                                          # the cover: the bay's west half 2025, east 1995
            west, east = self.photos[LOW], self.photos[BASE_YEAR]
            half = east.width // 2
            im = west.copy()
            im.paste(east.crop((half, 0, east.width, east.height)), (half, 0))
            c.im.paste(self.scaled(im, c), (c.X(x), c.Y(y)))
            c.fill(x + half - 2, y, x + half + 2, y + PIC_H, self.th.field)
            self.year_chip(c, x + 14, y + PIC_H - 78, persian(LOW), "l")          # clear of the heading
            self.label_box(c, x + 14, y + PIC_H - 92, self.words["hatch"], 30, "l", bold=False)
            self.year_chip(c, x + PIC_W - 14, y + 14, persian(BASE_YEAR), "r")
        else:
            a, b, w = s
            im = self.photos[a] if w == 0 else Image.blend(self.photos[a], self.photos[b], w)
            c.im.paste(self.scaled(im, c), (c.X(x), c.Y(y)))
            shown = b if w >= 0.5 else a
            self.year_chip(c, x + PIC_W - 14, y + 14, persian(shown), "r")
            self.readout(c, shown)
            self.places(c)
        self.label_box(c, x + 14, y + 46, self.words["heading"], MARK_PX, "l")
        self.scale(c)
        c.frame(x, y, x + PIC_W, y + PIC_H)

    def readout(self, c: Canvas, year: int):
        """The bay's area of the year in whole km2, or 'uncertain'; a hatch legend where the bay was not seen."""
        x, base = LEFT + 14, PIC_Y + PIC_H - 22
        lab = self.label[year]
        text = self.words["uncertain"] if lab == "uncertain" else f"{fa(lab)} {self.words['unit']}"
        self.label_box(c, x, base, text, MARK_PX, "l")
        if self.hatched[year] > 0.005:
            self.label_box(c, x, base - 52, self.words["hatch"], 30, "l", bold=False)

    def places(self, c: Canvas):
        for name, (lon, lat), anchor in self.words["places"]:
            px, py = pic_xy(lon, lat)
            if anchor == "l":                                   # a port: a dot, its name to the left
                c.frame(px - 5, py - 5, px + 5, py + 5, fill=self.th.ink)
                self.label_box(c, px - 18, py + 12, name, MARK_PX - 4, "r")
            elif anchor == "b":                                 # the barrier: a dot, its name above
                c.frame(px - 5, py - 5, px + 5, py + 5, fill=self.th.ink)
                self.label_box(c, px, py - 24, name, MARK_PX - 4, "c")
            else:
                self.label_box(c, px, py + 12, name, MARK_PX, "c")

    def scale(self, c: Canvas):
        km = 10.0 * PIC_W / ((CROP[1] - CROP[0]) * gg.DX * 111.32 * np.cos(np.deg2rad(36.82)))
        right, base = LEFT + PIC_W - 16, PIC_Y + PIC_H - 22
        c.fill(right - km, base - 6, right, base + 2, self.th.ink)
        self.label_box(c, right, base - 22, self.words["scale"], 30, "r", bold=False)

    def gauge(self, c: Canvas, t: float):
        th, col = self.th, self.colour
        x0, y0, x1, y1 = PLOT
        yv = lambda v: y0 + (VMAX - v) / (VMAX - VMIN) * (y1 - y0)      # metres to px
        xp = lambda p: x0 + (p - 1365) / 40 * (x1 - x0)                 # Persian year to px
        self.say(c, x1, PIC_Y + PIC_H + 40, self.words["gauge"], MARK_PX, True, th.ink, "rs")
        for m in (1, 2, 3):                                             # the scale, in words, no minus sign
            yy = yv(-m)
            for xx in np.arange(x0, x1, 16):
                c.fill(xx, yy - 1, xx + 8, yy + 1, col["line"])
            c.text(x0 - 12, yy + 12, fa(m) + self.words["below"], FA_TEXT, MARK_PX, th.ink, "rs", "rtl")
        zero = yv(0.0)                                                  # the 1374 reference, labelled
        for xx in np.arange(x0, x1, 14):
            c.fill(xx, zero - 2, xx + 8, zero + 2, th.ink)
        ref_w = c.width(self.words["reference"], FA_TEXT, 30, "rtl")
        c.text(x0 + 8 + ref_w, zero - 10, self.words["reference"], FA_TEXT, 30, th.ink, "rs", "rtl")
        for py in (1365, 1375, 1385, 1395, 1405):                       # the year axis (Persian years)
            c.fill(xp(py) - 1, y1, xp(py) + 1, y1 + 10, th.ink)
            c.text(xp(py), y1 + 44, fa(py), FA_TEXT, MARK_PX, th.ink, "ms", "rtl")
        s = self.state(t)
        if s is None:
            shown = LOW                                                 # the cover: 1404
        else:
            a, b, w = s
            shown = b if w >= 0.5 else a
        if shown < FIRST_READING:                                      # no reading yet: blank, and the satellite's start
            c.text(x0 + 16 + c.width(self.words["before"], FA_TEXT, MARK_PX, "rtl"), yv(-1.5), self.words["before"],
                   FA_TEXT, MARK_PX, th.ink, "rs", "rtl")
            return
        pts = [(xp(persian(y)), yv(self.level[y])) for y in range(FIRST_READING, shown + 1)]
        if len(pts) > 1:                                                # the line, year by year
            c.d.line([(c.X(px), c.Y(py)) for px, py in pts], fill=col["water"], width=max(2, round(5 * c.k)))
        dx, dy = pts[-1]
        r = 10 * c.k
        c.d.ellipse([c.X(dx) - r, c.Y(dy) - r, c.X(dx) + r, c.Y(dy) + r], fill=col["now"], outline=th.field,
                    width=max(1, round(2 * c.k)))
        v = self.level[shown]
        if shown == BASE_YEAR:
            val = self.words["base"]
        elif round(abs(v), 1) == 0:
            val = self.words["below_small"]
        else:
            val = fa(f"{abs(v):.1f}") + self.words["below"]
        self.label_box(c, x0 + 16, y1 - 18, f"{fa(persian(shown))}: {val}", 44, "l")   # the year and its value, in the empty corner

    def body(self, c: Canvas, t: float):
        self.picture(c, t)
        self.gauge(c, t)

    def sources(self, c: Canvas):
        for k, line in enumerate(self.words["sources"]):
            c.text(RIGHT, self.source_y + SOURCE * k, line, FA_TEXT, SOURCE_PX, self.th.head, "rs", "rtl")
            assert c.width(line, FA_TEXT, SOURCE_PX, "rtl") <= RIGHT - LEFT, line


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="khazar", choices=["khazar"], help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    args = ap.parse_args()
    film = GorganFilm(onebit.THEMES[args.theme], COLOURS[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"gorgan_{args.theme}_fa"
    for old in (OUT / "social").glob(f"{base.name}_t*.png"):
        old.unlink()                                          # no stale frames of an earlier cut
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (0.0, 1.3, 2.5, st[1] + film.later(1) + 1.2, film.at[LOW] + 0.05, st[2] + film.later(2) + 1.6,
                  film.at[NOW] + 0.5, st[-1] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
