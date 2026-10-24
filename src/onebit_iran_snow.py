"""IRAN'S SNOW: 29 % less of it, and no snowy place got more; winters 1.6 to 2.4 °C warmer.

Measured data only, no causes claimed. Each number has its source on screen and in the caption:
- Snowfall in Iran, ERA5 monthly means (snow.py; doi:10.24381/cds.f17050d7, Hersbach et al.
  2020): land inside Iran's borders, water years October to September (a water year is named
  by its September: 1951 = October 1950 to September 1951), cos-latitude weights. 1951-1980:
  58 mm a year, 2017-2026: 41 mm, 29 % less. About 80 % of it is a smaller snow share of the
  precipitation (19.9 -> 15.3 %), the rest less precipitation (-6 %; CRU TS: -13 %). Of the
  1,182 cells with at least 20 mm of snow a year in 1951-80 none gained (median -35 %); 22 of the
  low-snow cells below that did, which is why the screen says "no snowy place". The 1940s are
  left out (ERA5 is inhomogeneous then). The last months of 2026 are preliminary ERA5T.
- Iran's winters (November-March), 1951-1980 against 2016-2025: +1.6 °C in CRU TS 4.10 (gridded
  from stations, University of East Anglia), +2.4 °C in ERA5 (snow.cru_winter, snow.series). The
  screen gives the range, "over the same years", without claiming it as the cause.

A slow, still slide. One window that never moves; its top holds the scene's bold line and, big
enough for a phone, its small line. Below it a map of Iran (Mercator, border dotted, five cities
tagged), a colour bar, and a row of ten snowflakes, a rounded picture of the snow of 1951-1980.
First the map shows where snow fell then; then, one every two beats, three flakes fade, and the
map turns once: each snowy place takes the colour of how much of its snow is gone (under 25 %,
25-50 %, over 50 %). Three scenes, 7 bars of 60 BPM = 28 s, with onebit_atari's slow Atari tune: a
plip and a falling note for each flake that fades. Persian (--lang fa, the default) mirrors the
type, the bar and the row. Themes: kashi in full colour (COLOURS), the 1-bit themes in patterns.

    outputs/onebit/social/iran_snow_<theme>[_fa]_reel.mp4, _cover.png, _music.wav

    python -I src/onebit_iran_snow.py --theme kashi            # colour, Persian
    python -I src/onebit_iran_snow.py --theme kashi --stills
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
from onebit import (FA_BOLD, FA_TEXT, FULL, GROTESK, OUT, PIXEL, SIZES, SOCIAL_CRF, TEXT, Canvas,  # noqa: E402
                    Scene, Timeline, fa, title, words_of)
from onebit_snow import FLAKE, highland_map, mercator_y  # noqa: E402

PACE = dict(bpm=60, bars=(2, 3, 2), lead=2, per=2)   # beats before the fade, beats per flake
THEN, NOW, WARM = (1951, 1980), (2017, 2026), (2016, 2025)   # CRU TS 4.10 ends in 2025
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
MAP_W = 760
MAP_H = round(MAP_W * (mercator_y(EXTENT[3]) - mercator_y(EXTENT[2])) / np.deg2rad(EXTENT[1] - EXTENT[0]))
MAP = ((LEFT + RIGHT - MAP_W) // 2, 584, MAP_W, MAP_H)
LEGEND = MAP[1] + MAP_H + 44                     # baseline of the colour bar's heading; the bar below
BOX_H = 46                                       # height of the colour bar
ROW, PITCH, CELL = LEGEND + 178, 78, 6          # the flakes: centre line, pitch, sprite pixel
ERA = (MAP[0] + MAP_W - 6, MAP[1] + 64)          # the years: in the map's empty corner over Turkmenistan
FOOTER = 1592
# themes in full colour (by their key), checked with the dataviz validator: the loss is an
# ordinal ramp of one warm hue (light end 2.06:1 on the cream), snow a soft blue, and the land
# without snow a cool grey, so that even the lightest step stands apart from it
COLOURS = {"kashi": dict(land="#E2E5E7", snow="#5B9BC8", ramp=("#E39A63", "#C7612F", "#93351F"))}


def words(lang: str, lost: float, cru: float, era: float) -> dict:
    pct = f"{100 * lost:.0f}"
    if lang == "fa":
        return dict(scenes=(("برفِ ایران {چقدر کم شده؟}", ""),
                            (f"بارشِ برفِ ایران // {{{fa(pct)}٪ کم شده است}}", "و در هیچ منطقهٔ برفی، برف بیشتر نشده"),
                            (f"در همین سال‌ها، زمستان‌ها // {{{fa(f'{cru:.1f}')} تا {fa(f'{era:.1f}')} درجه}} گرم‌تر شده‌اند",
                             f"زمستان‌های {fa(1951)} تا {fa(80)} در برابر {fa(2016)} تا {fa(25)}")),
                    follow="برای داده‌های اقلیمی بیشتر، فالو کنید",
                    snowy="مناطقِ برفی، ۱۹۵۱ تا ۱۹۸۰", head="کاهشِ برفِ هر جا نسبت به ۱۹۵۱ تا ۱۹۸۰",
                    steps=("زیر ۲۵٪", "۲۵ تا ۵۰٪", "بیش از ۵۰٪"),
                    sources=("منبع: ERA5 ماهانه (کوپرنیکوس / ECMWF) و CRU TS 4.10 (دانشگاه ایست‌آنگلیا)",
                             "محاسبهٔ ما · سال آبی: اکتبر تا سپتامبر"))
    return dict(scenes=(("How much has {Iran's snow} shrunk?", ""),
                        (f"Snowfall in Iran // {{is down {pct} %}}", "and no snowy place got more"),
                        (f"Over the same years, winters // {{warmed {cru:.1f} to {era:.1f} °C}}", "Nov–Mar, 1951–80 vs 2016–25")),
                follow="Follow for more climate data in 1-bit",
                snowy="snowy places, 1951–80", head="snow lost per place, vs 1951–80",
                steps=("under 25 %", "25–50 %", "over 50 %"),
                sources=("Data: ERA5 monthly (Copernicus / ECMWF), CRU TS 4.10 (Univ. of East Anglia)",
                         "Our calculation · water year: October to September"))


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

    def __init__(self, th: onebit.Theme, lang: str = "en", colour: dict | None = None):
        """colour: a COLOURS entry for full colour; None draws a 1-bit theme in patterns."""
        self.th, self.lang, self.fa, self.colour = th, lang, lang == "fa", colour
        s = snow.series(0.0, "Iran")
        then, now = s.loc[THEN[0]:THEN[1], "snow"], s.loc[NOW[0]:NOW[1], "snow"]
        assert len(then) == 30 and len(now) == 10, "complete water years only"
        self.loss = 1 - now.mean() / then.mean()               # 0.29
        self.lost = round(10 * self.loss)                      # of every 10 flakes: 3
        era = float(s.loc[WARM[0]:WARM[1], "cold_t2m"].mean() - s.loc[THEN[0]:THEN[1], "cold_t2m"].mean())   # 2.4 °C
        cru = snow.cru_winter("Iran", *THEN, *WARM)            # 1.6 °C
        assert round((cru + era) / 2) == 2, (cru, era)
        self.words = words(lang, self.loss, cru, era)
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
        dots[FOOTER - 36:FOOTER + 50] = False
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
        _, _, _, self.place, _, inside = highland_map(w, h, EXTENT, "Iran")
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
        a, b = CLASSES
        self.land, self.snowy = body & ~snowy, snowy
        self.steps = (snowy & (lost_px < a), snowy & (lost_px >= a) & (lost_px < b), snowy & (lost_px >= b))
        self.base = self.land & scr["sparse"]                    # 1-bit: Iran without snow in the dot colour
        self.before = snowy & scr["dots"]
        self.after = snowy & np.where(lost_px < a, scr["dots"], np.where(lost_px < b, scr["hatch"], scr["solid"]))
        self.border = edge & ((np.add.outer(np.arange(h), np.arange(w))) % 2 == 0)
        assert np.isfinite(lost_px[snowy]).all(), "a snowy place without a change would be drawn as land"
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
        if self.colour:                                   # solid fills: land, snow, then the ramp of loss
            col = self.colour
            c.pixels(x, y, self.land, col["land"])
            if turned:
                for mask, colour in zip(self.steps, col["ramp"]):
                    c.pixels(x, y, mask, colour)
            else:
                c.pixels(x, y, self.snowy, col["snow"])
        else:
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
        """A stepped colour bar under the map, in reading order: before the turn one box (where
        snow fell), after it a heading and three boxes of loss, each labelled underneath."""
        th = self.th
        mid = (LEFT + RIGHT) / 2
        items = [("dots", self.words["snowy"])] if not turned else \
            [("dots", self.words["steps"][0]), ("hatch", self.words["steps"][1]), ("solid", self.words["steps"][2])]
        if turned:
            self.say(c, mid, LEGEND, self.words["head"], 44, True, th.ink, "ms")
        box, top = 240, LEGEND + 20
        n = len(items)
        for k, (pat, label) in enumerate(items):
            j = n - 1 - k if self.fa else k                   # Persian reads the bar from the right
            x0 = mid + (j - n / 2) * box
            if self.colour:                               # solid boxes with a 2 px gap between them
                fill = self.colour["snow"] if n == 1 else self.colour["ramp"][k]
                c.fill(x0 + 1, top, x0 + box - 1, top + BOX_H, fill)
            else:
                c.pixels(x0 + 2, top + 2, self.pat[pat][:BOX_H - 4, :box - 4], th.ink)
                c.frame(x0, top, x0 + box, top + BOX_H)
            cx = x0 + box / 2
            label = fa(label) if self.fa else label
            path, way = (FA_TEXT, "rtl") if self.fa else (TEXT, None)
            size = 40 if n > 1 else 36
            assert c.width(label, path, size, way) <= (box - 8 if n > 1 else RIGHT - LEFT), label
            c.text(cx, top + BOX_H + 48, label, path, size, th.ink, "ms", way)

    def flakes(self, c: Canvas, t: float):
        """Ten flakes; the last ones in reading order fade to a dotted ghost."""
        gone = self.faded(t)
        h, w = len(FLAKE), len(FLAKE[0])
        for k in range(10):
            j = 9 - k if self.fa else k                       # Persian reads the row from the right
            cx = (LEFT + RIGHT) / 2 + (j - 4.5) * PITCH
            x0, y0 = cx - w * CELL / 2, ROW - h * CELL / 2
            ghost = k >= 10 - gone
            ink = self.colour["snow"] if self.colour else self.th.ink
            for r, row in enumerate(FLAKE):
                for q, ch in enumerate(row):
                    if ch == "#" and (not ghost or (r + q) % 2 == 0):
                        a, b = x0 + q * CELL, y0 + r * CELL
                        if ghost:                             # a faded flake: one dot per pixel, its middle
                            c.fill(a + 2, b + 2, a + CELL - 2, b + CELL - 2, ink)
                        else:
                            c.fill(a, b, a + CELL, b + CELL, ink)

    def era(self, c: Canvas, t: float):
        y0, y1 = NOW if self.turned(t) else THEN
        if self.fa:
            c.text(*ERA, f"{fa(y0)} تا {fa(y1)}", FA_BOLD, 56, self.th.ink, "rs", "rtl")
        else:
            c.text(*ERA, f"{y0}–{y1}", GROTESK, 56, self.th.ink, "rs")

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
        for k, line in enumerate(self.words["sources"]):         # under the window, inside its width
            if self.fa:
                c.text(WIN[0] + WIN[2], FOOTER + 34 * k, line, FA_TEXT, 26, self.th.head, "rs", "rtl")
            else:
                c.text(WIN[0], FOOTER + 34 * k, line, TEXT, 24, self.th.head)
            assert c.width(line, FA_TEXT if self.fa else TEXT, 26 if self.fa else 24,
                           "rtl" if self.fa else None) <= WIN[2], line
        return c.im


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="kabud1", choices=list(onebit.THEMES), help="colour theme")
    ap.add_argument("--lang", default="fa", choices=("en", "fa"))
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    args = ap.parse_args()
    film = IranSnowFilm(onebit.THEMES[args.theme], args.lang, COLOURS.get(args.theme))
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / (f"iran_snow_{args.theme}" + ("" if args.lang == "en" else f"_{args.lang}"))
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (st[1] + 3.0, st[1] + film.done + 2, st[2] + 4.0, st[-1] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
        print("saved", f"{base}_t*.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="atari")


if __name__ == "__main__":
    main()
