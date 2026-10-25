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
enough for a phone, its small line. Below it a map of Iran (Mercator, border dotted, four cities
tagged), a colour bar, and a row of ten snowflakes, a rounded picture of the snow of 1951-1980.
First the map shows where snow fell then; then, one every two beats, three flakes fade, and the
map turns once: each snowy place takes the colour of how much of its snow is gone (under 25 %,
25-50 %, over 50 %). One bold line per scene, nothing else to read but the map; the periods
stand in the source lines. Three scenes, 10 bars of 60 BPM = 40 s, with onebit_atari's slow tune: a
plip and a falling note for each flake that fades. Persian (--lang fa, the default) mirrors the
type, the bar and the row. Themes: kashi in full colour (COLOURS), the 1-bit themes in patterns.

    outputs/onebit/social/iran_snow_<theme>[_fa]_reel.mp4, _cover.png, _music.wav

    python -I src/onebit_snowloss.py --region iran --theme kashi --no-music      # Persian, colour
    python -I src/onebit_snowloss.py --region alps --theme flieder --no-music    # German, lilac
    python -I src/onebit_snowloss.py --region alps --theme flieder --stills
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

THEN, NOW, WARM = (1951, 1980), (2017, 2026), (2016, 2025)   # CRU TS 4.10 ends in 2025
SNOWY = 20.0                                     # mm a year in 1951-80: a place that had snow
CLASSES = (25, 50)                               # % lost: the map's three steps
# name: a Natural Earth country or range (snow.shape); data: the get_snow.py download; extent:
# W, E, S, N of the map; pace: tempo, scene lengths (bars), beats before the fade and per flake;
# expect: the published numbers (% less snow; °C stations, ERA5): the film stops if the data
# no longer give them; nowhere_more: the caption says no snowy place gained, so the film asserts it; era: the map's
# empty top corner that holds the years (Turkmenistan for Iran, the Jura for the Alps)
REGIONS = {
    "iran": dict(name="Iran", data="snow", extent=(43.5, 63.8, 24.8, 40.2), map_w=760, langs=("fa", "en"),
                 pace=dict(bpm=60, bars=(3, 4, 3), lead=3, per=3), app="Iran.Snow", borders=False, era="right",
                 expect=(29, 1.6, 2.4),
                 nowhere_more=True,
                 cities={"en": (("Tehran", 51.39, 35.69), ("Tabriz", 46.29, 38.08), ("Mashhad", 59.61, 36.30),
                                ("Shiraz", 52.53, 29.59)),
                         "fa": (("تهران", 51.39, 35.69), ("تبریز", 46.29, 38.08), ("مشهد", 59.61, 36.30),
                                ("شیراز", 52.53, 29.59))}),
    "alps": dict(name="ALPS", data="snow_alps", extent=(4.6, 17.0, 43.3, 48.6), map_w=828, langs=("de",),
                 pace=dict(bpm=60, bars=(2.5, 3.5, 2), lead=2, per=2.5), app="Alpen.Schnee", borders=True, era="left",
                 expect=(21, 2.1, 2.7),
                 nowhere_more=False,
                 cities={"de": (("Zürich", 8.54, 47.37), ("Innsbruck", 11.39, 47.27), ("Mailand", 9.19, 45.46),
                                ("Grenoble", 5.72, 45.19))}),
}
WIN = (60, 196, 900, 1356)
BAR = 40
LEFT, RIGHT = 96, 924
RULE = 560
SMALL = 48                                       # px of the small line: readable on a phone
BOX_H = 46                                       # height of the colour bar
PITCH, CELL = 78, 6                              # the flakes: pitch, sprite pixel
BELOW = 44 + 178 + 27                            # map foot to the colour bar's heading, the flakes, their foot
FOOTER = 1592
PROGRESS = 10                                    # height of the progress bar over the window
# themes in full colour (by their key), checked with the dataviz validator: the loss is an
# ordinal ramp of one hue (light end at least 2:1 on the field), snow a colour apart from it,
# and the land without snow a cool grey, so that even the lightest step stands apart from it
COLOURS = {"kashi": dict(land="#E2E5E7", snow="#5B9BC8", ramp=("#E39A63", "#C7612F", "#93351F")),
           "flieder": dict(land="#E3E1E8", snow="#6F8FD8", ramp=("#A98BD4", "#7E52B8", "#4B2280"))}


def span(years, lang: str = "fa") -> str:
    """A period in full years, one format everywhere: «۱۹۵۱ تا ۱۹۸۰», 1951–1980."""
    return f"{fa(years[0])} تا {fa(years[1])}" if lang == "fa" else f"{years[0]}–{years[1]}"


def decimal(v: float) -> str:
    """One decimal with a German decimal comma: 2,1."""
    return f"{v:.1f}".replace(".", ",")


def seasons(years) -> str:
    """Winters named by their March, written as seasons: (2016, 2025) -> 2015/16–2024/25."""
    return f"{years[0] - 1}/{str(years[0])[2:]}–{years[1] - 1}/{str(years[1])[2:]}"


def words(region: str, lang: str, lost: float, cru: float, era: float) -> dict:
    pct = f"{100 * lost:.0f}"
    if (region, lang) == ("alps", "de"):
        nb = "\u00a0"                                    # no-break space: a number keeps its unit
        return dict(scenes=(("Wie viel Schnee {fehlt den Alpen?}", ""),
                            (f"Schneefall in den Alpen: // {{{pct}{nb}% weniger}}", ""),
                            (f"Winter (Nov–März): // {{{decimal(cru)} bis {decimal(era)}{nb}°C}} wärmer", "")),
                    follow="Folge mir für mehr Klimadaten",
                    snowy="Gebiete mit Schneefall, 1951–1980", head="Schneeverlust gegenüber 1951–1980",
                    steps=(f"unter 25{nb}%", f"25–50{nb}%", f"über 50{nb}%"),
                    sources=("Daten: ERA5 monatlich (Copernicus/ECMWF) · CRU TS 4.10 (Univ. of East Anglia)",
                             f"Schnee {span(THEN, 'de')} → {span(NOW, 'de')} · Winter {seasons(THEN)} → {seasons(WARM)}"))
    assert (region, lang) in (("iran", "fa"), ("iran", "en")), (region, lang)
    if lang == "fa":
        return dict(scenes=(("برفِ ایران {چقدر کم شده؟}", ""),
                            (f"بارشِ برفِ ایران // {{{fa(pct)}٪ کم شده است}}", ""),
                            (f"در همین سال‌ها، زمستان‌ها // {{{fa(f'{cru:.1f}')} تا {fa(f'{era:.1f}')} درجه}} گرم‌تر شده‌اند", "")),
                    follow="برای داده‌های اقلیمی بیشتر، فالو کنید",
                    snowy="مناطقِ برفی، ۱۹۵۱ تا ۱۹۸۰", head="کاهشِ برف نسبت به ۱۹۵۱ تا ۱۹۸۰",
                    steps=("زیر ۲۵٪", "۲۵ تا ۵۰٪", "بیش از ۵۰٪"),
                    sources=("منبع: ERA5 ماهانه (کوپرنیکوس / ECMWF) و CRU TS 4.10 (دانشگاه ایست‌آنگلیا)",
                             f"برف: سال‌های آبی {span(THEN)} و {span(NOW)} · زمستان: {span(THEN)} و {span(WARM)}"))
    return dict(scenes=(("How much has {Iran's snow} shrunk?", ""),
                        (f"Snowfall in Iran // {{is down {pct} %}}", ""),
                        (f"Over the same years, winters // {{warmed {cru:.1f} to {era:.1f} °C}}", "")),
                follow="Follow for more climate data in 1-bit",
                snowy="snowy places, 1951–1980", head="snow lost since 1951–1980",
                steps=("under 25 %", "25–50 %", "over 50 %"),
                sources=("Data: ERA5 monthly (Copernicus / ECMWF), CRU TS 4.10 (Univ. of East Anglia)",
                         f"Snow (water years) {span(THEN, 'en')} vs {span(NOW, 'en')} · winters {span(THEN, 'en')} vs {span(WARM, 'en')}"))


def screens(h: int, w: int) -> dict:
    """The map's patterns, ink on the field, light to dark: 2 x 2 dots every 8 px, every 4 px
    (rows staggered), diagonal hatch, solid."""
    yy, xx = np.mgrid[0:h, 0:w]
    return {"sparse": (yy % 8 < 2) & (xx % 8 < 2),
            "dots": (yy % 4 < 2) & ((xx + 2 * (yy // 4 % 2)) % 4 < 2),
            "hatch": (xx + yy) % 5 < 2,
            "solid": np.ones((h, w), bool)}


class SnowLossFilm:
    """Draws the film; exposes L, S, bpm, appear(), melody() and blips for onebit_atari."""

    def __init__(self, th: onebit.Theme, region: str = "iran", lang: str = "fa", colour: dict | None = None):
        """colour: a COLOURS entry for full colour; None draws a 1-bit theme in patterns."""
        self.th, self.lang, self.fa, self.colour = th, lang, lang == "fa", colour
        R = self.R = REGIONS[region]
        self.extent, self.cities, self.pace, self.app = R["extent"], R["cities"][lang], R["pace"], R["app"]
        snow.use(R["data"])
        s = snow.series(0.0, R["name"])
        then, now = s.loc[THEN[0]:THEN[1], "snow"], s.loc[NOW[0]:NOW[1], "snow"]
        assert len(then) == 30 and len(now) == 10, "complete water years only"
        self.loss = 1 - now.mean() / then.mean()               # 0.29
        self.lost = round(10 * self.loss)                      # of every 10 flakes: 3
        era = float(s.loc[WARM[0]:WARM[1], "cold_t2m"].mean() - s.loc[THEN[0]:THEN[1], "cold_t2m"].mean())   # 2.4 °C
        cru = snow.cru_winter(R["name"], *THEN, *WARM)         # 1.6 °C
        got = (round(100 * self.loss), round(cru, 1), round(era, 1))
        assert got == R["expect"], f"the data now give {got}, the published reel {R['expect']}: check before rendering"
        assert self.lost >= 1, "no flake to fade"
        self.warming = (cru, era)                              # °C: stations, ERA5
        self.words = words(region, lang, self.loss, cru, era)
        self.bpm = self.pace["bpm"]
        self.beat = 60 / self.bpm
        # the map block (map, colour bar, flakes) centred between the rule and the window's foot
        w = R["map_w"]
        h = round(w * (mercator_y(self.extent[3]) - mercator_y(self.extent[2]))
                  / np.deg2rad(self.extent[1] - self.extent[0]))
        room = WIN[1] + WIN[3] - 32 - (RULE + 24)          # 32 px above the window's foot
        assert h + BELOW <= room, "the map block does not fit the window"
        top = RULE + 24 + (room - (h + BELOW)) // 2
        self.map_box = ((LEFT + RIGHT - w) // 2, top, w, h)
        self.legend_y = top + h + 44                       # baseline of the colour bar's heading
        self.row = self.legend_y + 178                     # centre line of the flakes
        self.era_at = (self.map_box[0] + (w - 6 if R["era"] == "right" else 6), top + 64)   # the years
        scenes = tuple(Scene(b, FULL, t, line) for b, (t, line) in zip(self.pace["bars"], self.words["scenes"]))
        self.check(scenes)
        starts = np.cumsum([0.0] + [sc.bars * 4 * self.beat for sc in scenes])
        self.starts = starts
        self.L = Timeline(0, 0, 0, 0, 0, end=float(starts[-1]), camera=((0.0, FULL),),
                          scenes=tuple(float(t) for t in starts[:-1]))
        self.S = SimpleNamespace(scenes=scenes, os_name=self.app.upper(), lang=lang, race=[])
        self.blips = [float(starts[1]) + (self.pace["lead"] + k * self.pace["per"]) * self.beat
                      for k in range(self.lost)]
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
        x, y, w, h = self.map_box
        _, borders, _, self.place, _, inside = highland_map(w, h, self.extent, self.R["name"])
        sf = snow.water_years(snow.field("snowfall", "sf"))
        then = sf.sel(wy=slice(*THEN)).mean("wy")
        lost = 100 * (1 - sf.sel(wy=slice(*NOW)).mean("wy") / then)
        lon = self.extent[0] + (np.arange(w) + 0.5) / w * (self.extent[1] - self.extent[0])
        y0, y1 = mercator_y(self.extent[2]), mercator_y(self.extent[3])
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
        self.base = self.land & scr["sparse"]                    # 1-bit: land without snow in the dot colour
        self.before = snowy & scr["dots"]
        self.after = snowy & np.where(lost_px < a, scr["dots"], np.where(lost_px < b, scr["hatch"], scr["solid"]))
        dotted = (np.add.outer(np.arange(h), np.arange(w))) % 2 == 0
        self.border = edge & dotted
        if self.R["borders"]:                             # the countries' borders inside the range, dotted
            self.border |= borders & body & dotted
        assert np.isfinite(lost_px[snowy]).all(), "a snowy place without a change would be drawn as land"
        self.gained = int((snowy & (lost_px < 0)).sum())   # map pixels: the caption must say so
        if self.R["nowhere_more"]:
            assert self.gained == 0, f"{self.gained} map pixels gained snow: the caption would be wrong"

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
            c.text(x + 12, y + BAR - 9, self.words["follow"] if last else self.app, PIXEL, 32, th.title)
            if not last:
                c.text(x + w - 12, y + BAR - 9, f"[{i + 1:02d}/{len(self.S.scenes):02d}]", PIXEL, 32, th.title, "rs")
        c.fill(x + 3, RULE, x + w - 3, RULE + 2, th.ink)

    def map(self, c: Canvas, t: float):
        th = self.th
        x, y, w, h = self.map_box
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
        for name, lo, la in self.cities:                  # small framed tags, readable over any screen
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
            self.say(c, mid, self.legend_y, self.words["head"], 44, True, th.ink, "ms")
        box, top = 240, self.legend_y + 20
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
            x0, y0 = cx - w * CELL / 2, self.row - h * CELL / 2
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

    def progress(self, c: Canvas, t: float):
        """Above the window, one segment per scene, as in a story: the scenes before are full, the
        scene playing fills as it plays, so a viewer sees there is more to come; on the cover all
        are empty. Persian fills from the right."""
        n, gap = len(self.S.scenes), 12
        x0, x1, y = WIN[0], WIN[0] + WIN[2], WIN[1] - 34
        seg = (x1 - x0 - gap * (n - 1)) / n
        i = self.scene(t)
        track = self.colour["land"] if self.colour else self.th.dots
        for k in range(n):
            if not np.isfinite(t) or k > i:
                frac = 0.0
            elif k < i:
                frac = 1.0
            else:
                frac = (t - self.starts[k]) / (self.starts[k + 1] - self.starts[k])
            a = x1 - (k + 1) * seg - k * gap if self.fa else x0 + k * (seg + gap)
            c.fill(a, y, a + seg, y + PROGRESS, track)
            done = seg * min(1.0, frac)
            if self.fa:
                c.fill(a + seg - done, y, a + seg, y + PROGRESS, self.th.mark)
            else:
                c.fill(a, y, a + done, y + PROGRESS, self.th.mark)

    def era(self, c: Canvas, t: float):
        y0, y1 = NOW if self.turned(t) else THEN
        if self.fa:
            c.text(*self.era_at, f"{fa(y0)} تا {fa(y1)}", FA_BOLD, 56, self.th.ink, "rs", "rtl")
        else:
            c.text(*self.era_at, f"{y0}–{y1}", GROTESK, 56, self.th.ink, "rs" if self.R["era"] == "right" else "ls")

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]):
        c = Canvas(s, self.th, 1.0, (0.0, 0.0), size)
        c.pixels(0, 0, self.dots, self.th.dots)
        i = self.scene(t)
        dt = t - self.starts[i] if np.isfinite(t) else np.inf
        self.window(c, i)
        self.progress(c, t)
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
                c.text(WIN[0], FOOTER + 34 * k, line, TEXT, 22, self.th.head)
            assert c.width(line, FA_TEXT if self.fa else TEXT, 26 if self.fa else 22,
                           "rtl" if self.fa else None) <= WIN[2], line
        return c.im


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="iran", choices=list(REGIONS))
    ap.add_argument("--theme", default="kashi", choices=list(onebit.THEMES), help="colour theme")
    ap.add_argument("--lang", choices=("en", "fa", "de"), help="default: the region's first language")
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    ap.add_argument("--no-music", action="store_true", help="a silent audio track: music is added in the app")
    args = ap.parse_args()
    lang = args.lang or REGIONS[args.region]["langs"][0]
    if lang not in REGIONS[args.region]["langs"]:
        ap.error(f"{args.region} comes in {', '.join(REGIONS[args.region]['langs'])}")
    film = SnowLossFilm(onebit.THEMES[args.theme], args.region, lang, COLOURS.get(args.theme))
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / (f"{args.region}_snow_{args.theme}" + ("" if lang == "en" else f"_{lang}"))
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (st[1] + 3.0, st[1] + film.done + 2, st[2] + 4.0, st[-1] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
        print("saved", f"{base}_t*.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent" if args.no_music else "atari")


if __name__ == "__main__":
    main()
