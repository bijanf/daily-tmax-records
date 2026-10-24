"""IRAN'S SNOW: 29 % less of it, nowhere more, in winters about 2 °C warmer.

Three facts, each from its own source, shown side by side and not as one chain (no study
attributes Iran's snow loss to people; part of it is the drought's lack of precipitation):
- Iran's snowfall, ERA5 (snow.py, land inside Iran's borders, water years October to
  September): 58 mm a year in 1951-1980, 41 mm in 2017-2026, 29 % less. In ERA5 about three
  quarters of it is a smaller snow share of the precipitation (19.9 -> 15.3 %), the rest less
  precipitation (-6 %; CRU TS: -13 %). Of the 1,182 cells that had at least 20 mm of snow a
  year, none gained; the median lost 35 %. The 1940s are left out: ERA5 is too dry then.
- Iran's winters (November-March) warmed between 1951-1980 and 2016-2025: +1.6 °C at the
  stations of CRU TS 4.10, +2.4 °C in ERA5 (snow.cru_winter, snow.series).
- Human-caused warming made Iran's five-year drought (to mid-2025, 60-month SPEI) about 50
  times more likely: probability ratio 53.7, 95 % range 9.7 to 815, "due to the planet warming
  by 1.3 °C"; water use and management lie outside the statistics. World Weather Attribution,
  21 November 2025, a rapid study from observations only:
  https://www.worldweatherattribution.org/human-induced-climate-change-compounded-by-socio-economic-water-stressors-increased-severity-of-5-year-drought-in-iran-and-euphrates-and-tigris-basin/

A slow, still 1-bit slide. One window that never moves; its top holds the scene's bold line and,
big enough for a phone, its small line. Below it a map of Iran (Mercator, its border dotted,
five cities tagged) and a row of ten big snowflakes for the snow of 1951-1980. First the map
shows where snow fell then; then, one every two beats, three flakes fade to dots, and the map
turns once: each snowy place darkens by how much of its snow is gone (under 25 %, 25-50 %,
over 50 %; legend under the map). Nothing else moves.

Four scenes, 10 bars of 60 BPM = 40 s, with onebit_atari's slow Atari tune: a plip and a falling
note for each flake that fades. Persian (--lang fa) mirrors the type and the row.

    outputs/onebit/social/iran_snow_<theme>[_fa]_reel.mp4, _cover.png, _music.wav

    python -I src/onebit_iran_snow.py --lang fa       # Kabud.1bit, Persian
    python -I src/onebit_iran_snow.py --lang fa --stills
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import xarray as xr  # noqa: E402
from scipy import ndimage  # noqa: E402

import onebit  # noqa: E402
import snow  # noqa: E402
from onebit import (FA_BOLD, FA_TEXT, FULL, GROTESK, MONO, OUT, PIXEL, SIZES, SOCIAL_CRF, TEXT, Canvas,  # noqa: E402
                    Scene, Timeline, fa, title, words_of)
from onebit_snow import FLAKE, highland_map, mercator_y  # noqa: E402

PACE = dict(bpm=60, bars=(2, 3, 2, 3), lead=2, per=2)   # beats before the fade, beats per flake
THEN, NOW, WARM = (1951, 1980), (2017, 2026), (2016, 2025)   # CRU TS 4.10 ends in 2025
DROUGHT = 50                                     # WWA 2025: probability ratio 53.7 (9.7-815)
SNOWY = 20.0                                     # mm a year in 1951-80: a place that had snow
CLASSES = (25, 50)                               # % lost: the map's three steps
EXTENT = (43.5, 63.8, 24.8, 40.2)                # W, E, S, N: Iran
CITIES = {"en": (("Tehran", 51.39, 35.69), ("Tabriz", 46.29, 38.08), ("Mashhad", 59.61, 36.30),
                 ("Isfahan", 51.67, 32.65), ("Shiraz", 52.53, 29.59)),
          "fa": (("تهران", 51.39, 35.69), ("تبریز", 46.29, 38.08), ("مشهد", 59.61, 36.30),
                 ("اصفهان", 51.67, 32.65), ("شیراز", 52.53, 29.59))}
WIN = (60, 196, 900, 1356)
BAR = 40
LEFT, RIGHT = 96, 924
RULE = 560
SMALL = 48                                       # px of the small line: readable on a phone
MAP_W = 620
MAP_H = round(MAP_W * (mercator_y(EXTENT[3]) - mercator_y(EXTENT[2])) / np.deg2rad(EXTENT[1] - EXTENT[0]))
MAP = ((LEFT + RIGHT - MAP_W) // 2, 584, MAP_W, MAP_H)
LEGEND = MAP[1] + MAP_H + 40                     # baseline of the legend's heading; its steps below
ROW, PITCH, CELL = 1356, 82, 7                   # the flakes: centre line, pitch, sprite pixel
FOOTER = 1592
SOURCE = "Data: ERA5 · CRU TS 4.10 · World Weather Attribution 2025"


def words(lang: str, lost: int, loss: float, cru: float, era: float) -> dict:
    warm = (cru + era) / 2
    if lang == "fa":
        return dict(scenes=(("برفِ ایران {کجا رفت؟}", f"برف در ایران، {fa(1951)} تا {fa(2026)}"),
                            (f"از هر ۱۰ دانهٔ برف، // {{{fa(lost)} دانه کم شده است}}", f"{fa(f'{100 * loss:.0f}%')} برفِ کمتر، و هیچ‌جا بیشتر نشده"),
                            (f"زمستان‌های ایران حالا // {{حدود {fa(f'{warm:.0f}')} درجه}} گرم‌تر است", f"ایستگاه‌ها {fa(f'{cru:.1f}')} و ERA5 {fa(f'{era:.1f}')} درجه"),
                            (f"خشکسالیِ ۵ سالهٔ ایران: // احتمالش {{حدود {fa(DROUGHT)} برابر}} شد", "به‌دلیلِ گرمایشِ انسان‌ساز (WWA)")),
                    follow="برای داده‌های اقلیمی بیشتر، فالو کنید",
                    snowy="جاهای برف‌گیر، ۱۹۵۱ تا ۱۹۸۰", head="برفِ کم‌شده",
                    steps=("زیر ۲۵٪", "۲۵ تا ۵۰٪", "بیش از ۵۰٪"))
    return dict(scenes=(("Where did {Iran's snow} go?", "snow in Iran, 1951–2026"),
                        (f"Of every 10 snowflakes, // {{{lost} are gone}}", f"{100 * loss:.0f} % less snow, and nowhere more"),
                        (f"Iran's winters are // {{about {warm:.0f} °C}} warmer", f"stations +{cru:.1f} °C, ERA5 +{era:.1f} °C"),
                        (f"Iran's 5-year drought: // about {{{DROUGHT}×}} more likely", "due to human-caused warming")),
                follow="Follow for more climate data in 1-bit",
                snowy="snowy places, 1951–80", head="snow lost",
                steps=("under 25 %", "25–50 %", "over 50 %"))


def screens(h: int, w: int) -> dict:
    """The map's patterns, ink on the field, light to dark: 2 x 2 dots every 8 px, every 4 px
    (rows staggered), diagonal hatch, solid."""
    yy, xx = np.mgrid[0:h, 0:w]
    return {"sparse": (yy % 8 < 2) & (xx % 8 < 2),
            "dots": (yy % 4 < 2) & ((xx + 2 * (yy // 4 % 2)) % 4 < 2),
            "hatch": (xx + yy) % 5 < 2,
            "solid": np.ones((h, w), bool)}


class IranSnowFilm:
    """Draws the film; exposes L, S, bpm, appear(), melody() and blips for onebit_atari."""

    def __init__(self, th: onebit.Theme, lang: str = "en"):
        self.th, self.lang, self.fa = th, lang, lang == "fa"
        s = snow.series(0.0, "Iran")
        then, now = s.loc[THEN[0]:THEN[1], "snow"], s.loc[NOW[0]:NOW[1], "snow"]
        assert len(then) == 30 and len(now) == 10, "complete water years only"
        self.loss = 1 - now.mean() / then.mean()               # 0.29
        self.lost = round(10 * self.loss)                      # of every 10 flakes: 3
        era = float(s.loc[WARM[0]:WARM[1], "cold_t2m"].mean() - s.loc[THEN[0]:THEN[1], "cold_t2m"].mean())   # 2.4 °C
        cru = snow.cru_winter("Iran", *THEN, *WARM)            # 1.6 °C
        assert round((cru + era) / 2) == 2, (cru, era)
        self.words = words(lang, self.lost, self.loss, cru, era)
        self.bpm = PACE["bpm"]
        self.beat = 60 / self.bpm
        scenes = tuple(Scene(b, FULL, t, line) for b, (t, line) in zip(PACE["bars"], self.words["scenes"]))
        self.check(scenes)
        starts = np.cumsum([0.0] + [sc.bars * 4 * self.beat for sc in scenes])
        self.starts = starts
        self.L = Timeline(0, 0, 0, 0, 0, end=float(starts[-1]), camera=((0.0, FULL),),
                          scenes=tuple(float(t) for t in starts[:-1]))
        self.S = SimpleNamespace(scenes=scenes, os_name="IRAN.SNOW", lang=lang, race=[])
        self.blips = [float(starts[1]) + (PACE["lead"] + k * PACE["per"]) * self.beat for k in range(self.lost)]
        self.done = self.blips[-1] - float(starts[1]) + 0.5   # s into the fade: the number, the map, the years
        assert self.blips[-1] < starts[2] - 2 * self.beat, "the fade must finish with time to read"
        self.maps()
        dots = np.zeros((1920, 1080), bool)
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        dots[FOOTER - 32:FOOTER + 16] = False
        self.dots = dots

    def check(self, scenes):
        """Every small line on one line at SMALL px."""
        path, way = (FA_TEXT, "rtl") if self.fa else (TEXT, None)
        font = onebit._font(path, SMALL)
        for sc in scenes:
            assert font.getlength(sc.line, direction=way) <= RIGHT - LEFT, sc.line

    def maps(self):
        """The map's two states: where snow fell in 1951-80, and how much of it is gone."""
        x, y, w, h = MAP
        land, borders, _, self.place, _, inside = highland_map(w, h, EXTENT, "Iran")
        sf = snow.water_years(snow.field("snowfall", "sf"))
        then = sf.sel(wy=slice(*THEN)).mean("wy")
        lost = 100 * (1 - sf.sel(wy=slice(*NOW)).mean("wy") / then)
        lon = EXTENT[0] + (np.arange(w) + 0.5) / w * (EXTENT[1] - EXTENT[0])
        y0, y1 = mercator_y(EXTENT[2]), mercator_y(EXTENT[3])
        lat = np.rad2deg(np.arctan(np.sinh(y1 - (np.arange(h) + 0.5) / h * (y1 - y0))))
        at = dict(latitude=xr.DataArray(lat, dims="latitude"), longitude=xr.DataArray(lon, dims="longitude"),
                  method="nearest")
        then_px, lost_px = then.interp(**at).values, lost.interp(**at).values
        edge = inside & ~ndimage.binary_erosion(inside, iterations=2)
        body = inside & ~edge
        snowy = body & (then_px >= SNOWY)
        self.pat = scr = screens(h, w)
        self.base = body & ~snowy & scr["sparse"]                # Iran without snow: in the dot colour
        self.before = snowy & scr["dots"]
        a, b = CLASSES
        self.after = snowy & np.where(lost_px < a, scr["dots"], np.where(lost_px < b, scr["hatch"], scr["solid"]))
        self.border = edge & ((np.add.outer(np.arange(h), np.arange(w))) % 2 == 0)
        gained = int((snowy & (lost_px < 0)).sum())
        assert gained == 0, f"{gained} map pixels gained snow: the line 'more nowhere' would be wrong"

    # ── time ──

    def scene(self, t: float) -> int:
        return int(np.searchsorted(self.starts[:-1], t, side="right")) - 1 if np.isfinite(t) else 0

    def turned(self, t: float) -> bool:
        """After the fade: today's years, today's map."""
        i = self.scene(t)
        return i > 1 or (i == 1 and t - self.starts[1] > self.done)

    def faded(self, t: float) -> int:
        i = self.scene(t)
        return 0 if i < 1 else self.lost if i > 1 else int(np.searchsorted(self.blips, t, side="right"))

    def appear(self, i: int) -> list:
        """Slow: a line comes in over 1.6 s; a line with a break shows its second part later: in
        the fade once the last flake has gone, in the other scenes two beats on."""
        ws = [w for w, _ in words_of(self.S.scenes[i].title, self.th)]
        n = len(ws) - ws.count("//")
        if "//" not in ws:
            return [0.3 + 1.6 * k / n for k in range(n)]
        first = ws.index("//")
        later = self.done if i == 1 else 2 * self.beat + 0.3
        return [0.3 + 1.2 * k / first for k in range(first)] + [later + 0.3 * k for k in range(n - first)]

    def melody(self):
        """A tune note each time a flake fades, falling to the tonic."""
        return [(t, self.lost - 1 - k, 1.6, 0.35) for k, t in enumerate(self.blips)]

    # ── drawing ──

    def say(self, c: Canvas, x, y, s, size=34, bold=False, colour=None, anchor=None):
        """A line in the film's script: Vazirmatn right to left in Persian, Inter otherwise."""
        if self.fa:
            return c.text(x, y, fa(s), FA_BOLD if bold else FA_TEXT, size, colour, anchor or "rs", "rtl")
        return c.text(x, y, s, onebit.BOLD if bold else TEXT, size, colour, anchor or "ls")

    def window(self, c: Canvas, i: int):
        th = self.th
        x, y, w, h = WIN
        c.frame(x, y, x + w, y + h, fill=th.paper)
        c.fill(x, y, x + w, y + BAR, th.ink)
        c.frame(x + 3, y + BAR + 3, x + w - 3, y + h - 3)
        last = i == len(self.S.scenes) - 1
        if last and self.fa:
            c.text(x + w - 12, y + BAR - 10, self.words["follow"], FA_TEXT, 28, th.title, "rs", "rtl")
        else:
            c.text(x + 12, y + BAR - 9, self.words["follow"] if last else "Iran.Snow", PIXEL, 32, th.title)
            if not last:
                c.text(x + w - 12, y + BAR - 9, f"[{i + 1:02d}/{len(self.S.scenes):02d}]", PIXEL, 32, th.title, "rs")
        c.fill(x + 3, RULE, x + w - 3, RULE + 2, th.ink)

    def map(self, c: Canvas, t: float):
        th = self.th
        x, y, w, h = MAP
        turned = self.turned(t)
        c.pixels(x, y, self.base, th.dots)
        c.pixels(x, y, self.after if turned else self.before, th.ink)
        c.pixels(x, y, self.border, th.ink)
        for name, lo, la in CITIES[self.lang]:            # small framed tags, readable over any screen
            px, py = self.place(lo, la)
            px, py = x + px, y + py
            c.fill(px - 5, py - 5, px + 5, py + 5, th.ink)
            tw = c.width(name, FA_TEXT if self.fa else TEXT, 30, "rtl" if self.fa else None)
            bx = px + 12
            c.frame(bx, py - 26, bx + tw + 16, py + 12, fill=th.field)
            if self.fa:
                c.text(bx + 8 + tw, py + 4, name, FA_TEXT, 30, th.ink, "rs", "rtl")
            else:
                c.text(bx + 8, py + 4, name, TEXT, 30, th.ink)
        self.legend(c, turned)

    def legend(self, c: Canvas, turned: bool):
        """Under the map, centred, in reading order: where snow fell before the turn; after it a
        heading and the three steps of loss."""
        th = self.th
        mid = (LEFT + RIGHT) / 2
        items = [("dots", self.words["snowy"])] if not turned else \
            [("dots", self.words["steps"][0]), ("hatch", self.words["steps"][1]), ("solid", self.words["steps"][2])]
        if turned:
            self.say(c, mid, LEGEND, self.words["head"], 36, True, th.ink, "ms")
        path, way, size, sw, gap = (FA_TEXT, "rtl", 32, 46, 30) if self.fa else (TEXT, None, 30, 46, 30)
        widths = [sw + 10 + c.width(fa(label) if self.fa else label, path, size, way) for _, label in items]
        total = sum(widths) + gap * (len(items) - 1)
        x = mid + total / 2 if self.fa else mid - total / 2     # Persian starts on the right
        y = LEGEND + 50
        for (pat, label), wd in zip(items, widths):
            sx = x - sw if self.fa else x                         # the swatch leads, the label follows
            c.frame(sx, y - 26, sx + sw, y + 6)
            c.pixels(sx + 1, y - 25, self.pat[pat][:30, :sw - 2], th.ink)
            if self.fa:
                c.text(sx - 10, y, fa(label), path, size, th.ink, "rs", "rtl")
                x -= wd + gap
            else:
                c.text(sx + sw + 10, y, label, path, size, th.ink)
                x += wd + gap
        assert total <= RIGHT - LEFT, total

    def flakes(self, c: Canvas, t: float):
        """Ten flakes; the last ones in reading order fade to a dotted ghost."""
        gone = self.faded(t)
        h, w = len(FLAKE), len(FLAKE[0])
        for k in range(10):
            j = 9 - k if self.fa else k                       # Persian reads the row from the right
            cx = (LEFT + RIGHT) / 2 + (j - 4.5) * PITCH
            x0, y0 = cx - w * CELL / 2, ROW - h * CELL / 2
            ghost = k >= 10 - gone
            for r, row in enumerate(FLAKE):
                for q, ch in enumerate(row):
                    if ch == "#" and (not ghost or (r + q) % 2 == 0):
                        a, b = x0 + q * CELL, y0 + r * CELL
                        if ghost:                             # a faded flake: one dot per pixel, its middle
                            c.fill(a + 2, b + 2, a + CELL - 2, b + CELL - 2, self.th.ink)
                        else:
                            c.fill(a, b, a + CELL, b + CELL, self.th.ink)

    def era(self, c: Canvas, t: float):
        y0, y1 = NOW if self.turned(t) else THEN
        if self.fa:
            c.text((LEFT + RIGHT) / 2, ROW + 112, f"{fa(y0)} تا {fa(y1)}", FA_BOLD, 52, self.th.ink, "ms", "rtl")
        else:
            c.text((LEFT + RIGHT) / 2, ROW + 112, f"{y0}–{y1}", GROTESK, 52, self.th.ink, "ms")

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]):
        c = Canvas(s, self.th, 1.0, (0.0, 0.0), size)
        c.pixels(0, 0, self.dots, self.th.dots)
        i = self.scene(t)
        dt = t - self.starts[i] if np.isfinite(t) else np.inf
        self.window(c, i)
        at = self.appear(i)
        title(c, self.th, self.S.scenes[i], dt, self.lang, 1.0, LEFT, RIGHT, WIN[1] + BAR + 96, at,
              motion=False, line_at=at[-1] + 0.6, small=SMALL)
        self.map(c, t)
        self.flakes(c, t)
        self.era(c, t)
        c.text(onebit.LEFT, FOOTER, SOURCE, MONO, 20, self.th.head)
        return c.im


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="kabud1", choices=list(onebit.THEMES), help="colour theme")
    ap.add_argument("--lang", default="fa", choices=("en", "fa"))
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    args = ap.parse_args()
    film = IranSnowFilm(onebit.THEMES[args.theme], args.lang)
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / (f"iran_snow_{args.theme}" + ("" if args.lang == "en" else f"_{args.lang}"))
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (st[1] + 3.0, st[1] + film.done + 2, st[2] + 4.0, st[3] + 4.0, st[4] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
        print("saved", f"{base}_t*.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="atari")


if __name__ == "__main__":
    main()
