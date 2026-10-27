"""LAKE URMIA FROM SPACE: its September water halved from 1995 to 2025; this year a little more.

Measured data only. Every number comes from urmia.py (outputs/urmia_log.txt), from Landsat
(get_urmia.py): the lake's September water area on one fixed footprint, 1986-2026, in % of 1995
(the record's largest: 5,382 km2). 2025 = 50 % (48-55 % over the MNDWI thresholds), the smallest;
2026 = 61 % (59-64 %). The two pictures are the September water of 1995 (Shahrivar 1374) and 2025
(Shahrivar 1404) from Landsat paths 168 and 169, over the lake's full extent in JRC Global
Surface Water 1984-2021 (its outline is drawn as the old shore). Causes are in the caption
(peer-reviewed studies; most give water use the larger share), not on screen.

A slow, still slide on the frame of onebit_slides. One window, one bold line per scene. The two
pictures side by side, 1995 on the right, and under them one bar per September since 1986 in %
of 1995. The first frame carries the whole question and both pictures. Three scenes, 2 + 3 + 3.5
bars of 60 BPM = 34 s, a silent track (music in the app).

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
from scipy import ndimage  # noqa: E402

import onebit  # noqa: E402
import urmia  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, SIZES, SOCIAL_CRF, Canvas, fa  # noqa: E402
from onebit_slides import COLOURS, LEFT, RIGHT, RULE, WIN, Slides  # noqa: E402

PACE = dict(bpm=60, bars=(2, 3, 3.5))
EXPECT = {1995: 100, 2025: 50, 2026: 61}          # % of 1995: the published reel
PIC_W, PIC_GAP = 290, 36                           # px: each picture's width, between them
BARS_H = 90                                      # px of 100 %
SOURCE, SOURCE_PX = 38, 30


def persian(year: int) -> int:
    return year - 621                              # September of year Y is Shahrivar of Y - 621


def words() -> dict:
    return dict(scenes=(("دریاچه‌ی ارومیه // {چه شد}؟", ""),
                        ("در ۳۰ سال: // آبش {نصف} شد", ""),
                        ("امسال کمی بهتر: // هنوز {حدود ۴۰٪} کمتر", "")),
                follow="برای داده‌های اقلیمی بیشتر، دنبال کنید",
                key=("آب", "بسترِ بی‌آب"), bars="آبِ شهریور، درصدِ ۱۳۷۴",
                sources=("منبع: تصاویرِ ماهواره‌ی لندست (USGS) · مرزِ دریاچه: JRC",
                         "مساحتِ آب در شهریورِ هر سال؛ ۱۳۷۴ = ۵٬۳۸۲ کیلومترِ مربع",
                         "۱۴۰۴: ۵۰٪ · ۱۴۰۵: ۶۱٪ (با آستانه‌های دیگر ۴۸ تا ۵۵٪ و ۵۹ تا ۶۴٪)"))


class UrmiaFilm(Slides):
    def __init__(self, th: onebit.Theme, colour: dict):
        a = urmia.series()
        got = {y: int(round(a.loc[y, "pct"])) for y in EXPECT}
        assert got == EXPECT, got
        assert a.area_km2.idxmax() == 1995 and a.area_km2.idxmin() == 2025, "the record's largest and smallest"
        self.pct = a["pct"]
        self.years = (int(a.index[0]), int(a.index[-1]))
        self.pics = {y: self.raster(y, colour, th) for y in (1995, 2025)}
        self.hook_at_once = True
        self.setup(th, "fa", colour, words(), PACE, "Urmia.Lake")
        dots = np.zeros((1920, 1080), bool)               # the sources sit in the window
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        self.dots = dots
        self.layout()
        b = self.beat
        self.done = b
        assert float(self.starts[1]) + self.later(1) + 1.5 < 15

    def raster(self, year: int, colour: dict, th) -> dict:
        """The picture as masks at its drawn size: water, bed (the extent without water), shore."""
        p = urmia.picture(year)
        h0, w0 = p["water"].shape
        w = PIC_W
        h = round(h0 * w / (w0 * np.cos(np.deg2rad(37.7))))   # lon/lat grid, squeezed to true shape
        def fit(m):
            return np.asarray(Image.fromarray(m.astype(np.uint8) * 255).resize((w, h), Image.BILINEAR)) > 127
        lake, water = fit(p["lake"]), fit(p["water"])
        shore = lake & ~ndimage.binary_erosion(lake, iterations=2)
        return dict(water=water & lake, bed=lake & ~water, shore=shore, w=w, h=h)

    def layout(self):
        inner_top = RULE + 24
        inner_bot = WIN[1] + WIN[3] - 24 - SOURCE * len(self.words["sources"])
        self.source_y = inner_bot + SOURCE - 8
        h = self.pics[1995]["h"]
        block = 40 + h + 44 + 40 + 44 + BARS_H + 40       # key, pictures, labels, bar heading, values, bars, years
        gap = (inner_bot - inner_top - block) / 3
        assert gap >= 16, f"the picture does not fit the window ({gap:.0f})"
        self.key_y = inner_top + gap + 30
        self.pic_y = self.key_y + 16
        mid = (LEFT + RIGHT) / 2
        self.pic_x = {1995: mid + PIC_GAP / 2, 2025: mid - PIC_GAP / 2 - PIC_W}   # 1995 on the right
        self.label_y = self.pic_y + h + 40
        self.bars_head = self.label_y + gap + 40
        self.bars_base = self.bars_head + 44 + BARS_H
        self.years_y = self.bars_base + 36

    # ── time ──

    def later(self, i: int) -> float:
        return self.beat + 0.3

    # ── drawing ──

    def pictures(self, c: Canvas):
        th, col = self.th, self.colour
        for y, x in self.pic_x.items():
            r = self.pics[y]
            c.pixels(x, self.pic_y, r["bed"], col["bed"])
            c.pixels(x, self.pic_y, r["water"], col["water"])
            c.pixels(x, self.pic_y, r["shore"], th.ink)
            c.text(x + PIC_W / 2, self.label_y, f"شهریور {fa(persian(y))}", FA_BOLD, 40, th.ink, "ms", "rtl")
        x = RIGHT                                          # the key, right to left
        for (name, k) in zip(self.words["key"], ("water", "bed")):
            c.fill(x - 30, self.key_y - 26, x, self.key_y + 2, col[k])
            if k == "bed":
                c.frame(x - 30, self.key_y - 26, x, self.key_y + 2)
            c.text(x - 42, self.key_y, name, FA_TEXT, 32, th.ink, "rs", "rtl")
            x -= 42 + c.width(name, FA_TEXT, 32, "rtl") + 40

    def bars(self, c: Canvas, t: float):
        th, col = self.th, self.colour
        i = self.scene(t) if np.isfinite(t) else 2
        self.say(c, RIGHT, self.bars_head, self.words["bars"], 32, True, th.ink)
        y0, y1 = self.years
        n = y1 - y0 + 1
        pitch = (RIGHT - LEFT) / n
        show = {1995: True, 2025: i >= 1, 2026: i >= 2}
        for k, y in enumerate(range(y0, y1 + 1)):
            if y not in self.pct.index:
                continue                                   # 1993: no usable scene
            right = RIGHT - k * pitch
            top = self.bars_base - self.pct.loc[y] / 100 * BARS_H
            colour = th.ink if y == 1995 else col["water"] if y in (2025, 2026) and show[y] else col["bar"]
            c.fill(right - pitch + 2, top, right - 2, self.bars_base, colour)
            if y in show and show[y] and not (y == 2025 and i >= 2):
                c.text(right - pitch / 2, top - 10, fa(f"{self.pct.loc[y]:.0f}٪"), FA_BOLD, 30, th.ink, "ms", "rtl")
        c.fill(LEFT, self.bars_base, RIGHT, self.bars_base + 2, th.ink)
        c.text(RIGHT, self.years_y, fa(persian(y0)), FA_TEXT, 30, th.ink, "rs", "rtl")
        c.text(LEFT, self.years_y, fa(persian(y1)), FA_TEXT, 30, th.ink, "ls", "rtl")

    def sources(self, c: Canvas):
        for k, line in enumerate(self.words["sources"]):
            c.text(RIGHT, self.source_y + SOURCE * k, line, FA_TEXT, SOURCE_PX, self.th.head, "rs", "rtl")
            assert c.width(line, FA_TEXT, SOURCE_PX, "rtl") <= RIGHT - LEFT, line

    def body(self, c: Canvas, t: float):
        self.pictures(c)
        self.bars(c, t)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="namak", choices=["namak"], help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    args = ap.parse_args()
    film = UrmiaFilm(onebit.THEMES[args.theme], COLOURS[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"urmia_{args.theme}_fa"
    for old in (OUT / "social").glob(f"{base.name}_t*.png"):
        old.unlink()
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (st[0] + 0.0, st[1] + film.later(1) + 1.5, st[2] + film.later(2) + 1.5, st[-1] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
