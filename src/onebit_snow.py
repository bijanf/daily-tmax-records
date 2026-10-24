"""SNOW BECOMES RAIN: the highlands from Turkey to the edge of Tibet get more of their water as
rain and less as snow (snow.py: ERA5, every water year since 1940).

A slow, still 1-bit slide. One window that never moves; its top holds the scene's bold line.
Below it a map of the highlands (Mercator, the land above 1,000 m in stipple, borders dotted)
and a mountain of 100 pixel icons, one for every 100 litres of water that fall on it: rows of
1, 3, 5 ... 19, snowflakes on top as its snow cap, raindrops below. Then the snow cap of the
first decades; then, one flake a beat, the flakes at the snowline turn into drops until the
mountain holds today's share, and the snowline has climbed. Nothing else moves.

Four scenes, 9 bars of 60 BPM = 36 s, with onebit_atari's slow Atari tune: a plip for each
flake that turns, the tune falling a step each time. Persian (--lang fa) mirrors the type.

    outputs/onebit/social/snow_rain_<theme>[_fa]_reel.mp4, _cover.png, _music.wav

    python -I src/onebit_snow.py                  # Schnee.1bit, English
    python -I src/onebit_snow.py --lang fa
    python -I src/onebit_snow.py --stills         # cover and frames, no video
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
from onebit import (FA_BOLD, FULL, GROTESK, MONO, OUT, PIXEL, SIZES, SOCIAL_CRF, Canvas,  # noqa: E402
                    Scene, Timeline, fa, title, words_of)

# tempo, scene lengths (bars), beats before the melt, beats per flake
PACE = dict(bpm=60, bars=(2, 2, 3, 2), lead=2, per=1)
# water years compared: ERA5's 1940s are too dry (precipitation 18 % below 1951-80 over the
# highlands, CRU TS: 2 %), which inflates their snow share, so "then" starts in 1951
THEN, NOW = (1951, 1980), (2017, 2026)
WIN = (60, 196, 900, 1356)                       # the one window, clear of the app's buttons
BAR = 40
LEFT, RIGHT = 96, 924
RULE = 556
EXTENT = (26, 75, 25, 43)                        # W, E, S, N: Turkey to the edge of Tibet
MAP = (90, 576, 840, 374)                        # x, y, w, h of the map inside the window (Mercator)
PEAK, PITCH, RISE, CELL = (510, 1030), 44, 48, 4  # the mountain's top icon (centre), icon pitch across
                                                   # and down, sprite pixel
LABELS = {"en": (("Turkey", 33, 39.5), ("Iran", 54, 32.5), ("Tibet", 72.5, 35.5)),
          "fa": (("ترکیه", 33, 39.5), ("ایران", 54, 32.5), ("تبت", 72.5, 35.5))}
FOOTER = 1592
SOURCE = "Data: ERA5 (Copernicus/ECMWF), land above 1,000 m, 1951-2026"
FLAKE = ["....#....", ".#..#..#.", "..#.#.#..", "...###...", "#########", "...###...", "..#.#.#..",
         ".#..#..#.", "....#...."]
DROP = ["....#....", "....#....", "...###...", "..#####..", ".#######.", ".#######.", ".#######.",
        "..#####..", "...###..."]


def mountain() -> list:
    """Centres of the 100 icons, in the order the snow covers them: rows of 1, 3, 5 ... 19 from
    the top, each row from its middle out, so the snow cap stays even and melts from its edges."""
    out = []
    for r in range(10):
        for k in sorted(range(-r, r + 1), key=lambda k: (abs(k), k)):
            out.append((PEAK[0] + k * PITCH, PEAK[1] + r * RISE))
    return out


def mercator_y(lat):
    return np.log(np.tan(np.pi / 4 + np.deg2rad(lat) / 2))


def highland_map(w: int, h: int, extent=EXTENT, region: str | None = None) -> tuple:
    """Masks of the map (h x w logical pixels, Mercator over extent): land, borders, and the land
    standing above 1,000 m (ERA5's terrain), a function placing (lon, lat) on the map, the terrain
    height (m), and where the region lies (None without one)."""
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1], projection=ccrs.Mercator())
    ax.set_extent(extent, crs=ccrs.PlateCarree())
    ax.spines["geo"].set_visible(False)
    ax.add_feature(cfeature.NaturalEarthFeature("physical", "land", "50m"), facecolor="black",
                   edgecolor="none", antialiased=False)
    fig.canvas.draw()
    land = np.asarray(fig.canvas.buffer_rgba())[..., 0] < 128
    inside = None
    if region:
        import cartopy.io.shapereader as shp
        rec = shp.Reader(shp.natural_earth("50m", "cultural", "admin_0_countries")).records()
        ax.clear()
        ax.set_extent(extent, crs=ccrs.PlateCarree())
        ax.spines["geo"].set_visible(False)
        ax.add_geometries([next(r.geometry for r in rec if r.attributes["ADMIN"] == region)], ccrs.PlateCarree(),
                          facecolor="black", edgecolor="none", antialiased=False)
        fig.canvas.draw()
        inside = np.asarray(fig.canvas.buffer_rgba())[..., 0] < 128
    ax.clear()
    ax.set_extent(extent, crs=ccrs.PlateCarree())
    ax.spines["geo"].set_visible(False)
    ax.add_feature(cfeature.NaturalEarthFeature("cultural", "admin_0_boundary_lines_land", "50m"),
                   facecolor="none", edgecolor="black", linewidth=0.8, antialiased=False)
    fig.canvas.draw()
    borders = np.asarray(fig.canvas.buffer_rgba())[..., 0] < 128
    plt.close(fig)
    # terrain: each map pixel takes the height of the ERA5 cell it falls in
    _, _, height = snow.masks()
    lon = extent[0] + (np.arange(w) + 0.5) / w * (extent[1] - extent[0])
    y0, y1 = mercator_y(extent[2]), mercator_y(extent[3])
    lat = np.rad2deg(np.arctan(np.sinh(y1 - (np.arange(h) + 0.5) / h * (y1 - y0))))
    z = height.interp(latitude=xr.DataArray(lat, dims="latitude"), longitude=xr.DataArray(lon, dims="longitude"),
                      method="nearest").values
    high = land & (z >= snow.HIGH)

    def place(lo, la):
        return (lo - extent[0]) / (extent[1] - extent[0]) * w, (y1 - mercator_y(la)) / (y1 - y0) * h

    return land, borders, high, place, z, inside


def words(lang: str, then: int, now: int) -> dict:
    lost = then - now
    if lang == "fa":
        return dict(scenes=(("آیا برفِ ما {دارد باران می‌شود؟}", "ارتفاعاتِ ترکیه تا لبهٔ تبت"),
                            (f"آن روزها از هر ۱۰۰ لیتر، // {{{fa(then)} لیتر}} برف بود", "هر شکل: ۱ لیتر باران یا برف"),
                            (f"این روزها از هر ۱۰۰ لیتر، // {{{fa(now)} لیتر}} برف است", "کلاهِ برف دارد کوچک‌تر می‌شود"),
                            (f"{{{fa(lost)} لیتر از هر ۱۰۰}} // حالا به‌جای برف، باران می‌بارد", "برای داده‌های اقلیمی بیشتر، فالو کنید")),
                    app="Snow.Line", source=SOURCE)
    return dict(scenes=(("Is our snow {turning into rain?}", "the highlands from Turkey to the edge of Tibet"),
                        (f"Then, of every 100 litres, // {{{then}}} fell as snow", "each icon: 1 litre of rain or snow"),
                        (f"Now, of every 100 litres, // {{{now}}} fall as snow", "the snow cap is shrinking"),
                        (f"{{{lost} of every 100}} litres now fall as rain, not snow", "Follow for more climate data in 1-bit")),
                app="Snow.Line", source=SOURCE)


class SnowFilm:
    """Draws the film; exposes L, S, bpm, appear(), melody() and blips for onebit_atari."""

    def __init__(self, th: onebit.Theme, lang: str = "en", then: int | None = None, now: int | None = None):
        self.th, self.lang, self.fa = th, lang, lang == "fa"
        if then is None:
            # the average water year's snow share, 36.6 and 31.5 %: rounded, 37 and 32 keep the
            # true difference (5.0); the shares of the periods' totals (36.7, 31.4) would round to 6
            s = snow.series()
            then, now = (round(s.loc[a:b, "share"].mean()) for a, b in (THEN, NOW))
        self.then, self.now = then, now
        self.words = words(lang, then, now)
        self.bpm = PACE["bpm"]
        self.beat = 60 / self.bpm
        scenes = tuple(Scene(b, FULL, t, line) for b, (t, line) in zip(PACE["bars"], self.words["scenes"]))
        starts = np.cumsum([0.0] + [sc.bars * 4 * self.beat for sc in scenes])
        self.starts = starts
        self.L = Timeline(0, 0, 0, 0, 0, end=float(starts[-1]), camera=((0.0, FULL),),
                          scenes=tuple(float(t) for t in starts[:-1]))
        self.S = SimpleNamespace(scenes=scenes, os_name="SNOW.LINE", lang=lang, race=[])
        self.icons = mountain()
        # the map in two regular dot screens of 2 x 2 dots (they survive the platforms'
        # compression): the highlands dense (a dot every 4 px, rows staggered), the lowland land
        # sparse (every 8 px), the sea empty; borders dotted, with the screen cleared beside them
        w, h = MAP[2], MAP[3]
        land, borders, high, self.place, _, _ = highland_map(w, h)
        yy, xx = np.mgrid[0:h, 0:w]
        dense = (yy % 4 < 2) & ((xx + 2 * (yy // 4 % 2)) % 4 < 2)
        sparse = (yy % 8 < 2) & (xx % 8 < 2)
        clear = ndimage.binary_dilation(borders, iterations=2)
        self.stipple = np.where(high, dense, land & sparse) & ~clear
        self.borders = borders & ((xx + yy) % 3 == 0)
        self.blips = [float(starts[2]) + (PACE["lead"] + k * PACE["per"]) * self.beat for k in range(then - now)]
        assert self.blips[-1] < starts[3] - self.beat, "the melt must finish before the last scene"
        self.done = self.blips[-1] - float(starts[2]) + 0.5      # s into the melt: today's number and years
        dots = np.zeros((1920, 1080), bool)
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        dots[FOOTER - 32:FOOTER + 16] = False
        self.dots = dots

    # ── time ──

    def scene(self, t: float) -> int:
        return int(np.searchsorted(self.starts[:-1], t, side="right")) - 1 if np.isfinite(t) else 0

    def flakes(self, t: float) -> int:
        """Snowflakes on the mountain: the first decades' share until the melt, one fewer a beat in
        it, today's share after it."""
        i = self.scene(t)
        if i < 2:
            return self.then
        return self.then - int(np.searchsorted(self.blips, t, side="right")) if i == 2 else self.now

    def appear(self, i: int) -> list:
        """Slow: the line comes in over 1.6 s; in the melt, the part after the line break (today's
        number) only once the last flake has turned."""
        ws = [w for w, _ in words_of(self.S.scenes[i].title, self.th)]
        n = len(ws) - ws.count("//")
        if i != 2:
            return [0.3 + 1.6 * k / n for k in range(n)]
        first = ws.index("//")
        return [0.3 + 1.2 * k / first for k in range(first)] + [self.done + 0.3 * k for k in range(n - first)]

    def melody(self):
        """A tune note each time a flake turns, falling a step each time."""
        return [(t, len(self.blips) - 1 - k, 1.6, 0.35) for k, t in enumerate(self.blips)]   # ends on the tonic

    # ── drawing ──

    def icon(self, c: Canvas, cx, cy, rows, ink):
        h, w = len(rows), len(rows[0])
        c.icon(cx - w * CELL / 2, cy - h * CELL / 2, rows, ink, cell=CELL)

    def window(self, c: Canvas, i: int):
        th = self.th
        x, y, w, h = WIN
        c.frame(x, y, x + w, y + h, fill=th.paper)
        c.fill(x, y, x + w, y + BAR, th.ink)
        c.frame(x + 3, y + BAR + 3, x + w - 3, y + h - 3)
        last = i == len(self.S.scenes) - 1
        c.text(x + 12, y + BAR - 9, self.words["app"], PIXEL, 32, th.title)
        c.text(x + w - 12, y + BAR - 9, f"[{i + 1:02d}/{len(self.S.scenes):02d}]", PIXEL, 32, th.title, "rs")
        c.fill(x + 3, RULE, x + w - 3, RULE + 2, th.ink)

    def map(self, c: Canvas):
        x, y, w, h = MAP
        c.pixels(x, y, self.stipple, self.th.ink)
        c.pixels(x, y, self.borders, self.th.ink)
        for name, lo, la in LABELS[self.lang]:
            px, py = self.place(lo, la)
            if self.fa:
                tw = c.width(name, FA_BOLD, 34, "rtl")
                c.fill(x + px - tw / 2 - 8, y + py - 32, x + px + tw / 2 + 8, y + py + 12, self.th.ink)
                c.text(x + px, y + py, name, FA_BOLD, 34, self.th.field, "ms", "rtl")
            else:
                tw = c.width(name, PIXEL, 36)
                c.fill(x + px - tw / 2 - 6, y + py - 26, x + px + tw / 2 + 6, y + py + 8, self.th.ink)
                c.text(x + px, y + py, name, PIXEL, 36, self.th.field, "ms")

    def era(self, c: Canvas, t: float):
        """The water years the mountain shows, in its top corner: today's once the melt is over,
        with today's number."""
        i = self.scene(t)
        y0, y1 = THEN if i < 2 or (i == 2 and t - self.starts[2] <= self.done) else NOW
        label = f"{y0}–{y1}" if not self.fa else f"{fa(y0)} تا {fa(y1)}"
        if self.fa:
            c.text(RIGHT, PEAK[1] + 20, label, FA_BOLD, 54, self.th.ink, "rs", "rtl")
        else:
            c.text(LEFT, PEAK[1] + 20, label, GROTESK, 54, self.th.ink)

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]):
        c = Canvas(s, self.th, 1.0, (0.0, 0.0), size)
        c.pixels(0, 0, self.dots, self.th.dots)
        i = self.scene(t)
        dt = t - self.starts[i] if np.isfinite(t) else np.inf
        self.window(c, i)
        at = self.appear(i)
        title(c, self.th, self.S.scenes[i], dt, self.lang, 1.0, LEFT, RIGHT, WIN[1] + BAR + 96, at,
              motion=False, line_at=at[0 if i == 2 else -1] + 0.6)       # the melt's small line runs under it
        self.map(c)
        n = self.flakes(t)
        for k, (x, y) in enumerate(self.icons):
            self.icon(c, x, y, FLAKE if k < n else DROP, self.th.ink)
        self.era(c, t)
        c.text(onebit.LEFT, FOOTER, self.words["source"], MONO, 20, self.th.head)
        return c.im


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="schnee1", choices=list(onebit.THEMES), help="colour theme")
    ap.add_argument("--lang", default="en", choices=("en", "fa"))
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    ap.add_argument("--fake", nargs=2, type=int, help="snow shares then and now, before the data is in")
    args = ap.parse_args()
    film = SnowFilm(onebit.THEMES[args.theme], args.lang, *(args.fake or (None, None)))
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / (f"snow_rain_{args.theme}" + ("" if args.lang == "en" else f"_{args.lang}"))
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (st[1] + 3.0, st[2] + 1.0, st[2] + 6.5, st[3] - 0.1, st[4] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
        print("saved", f"{base}_t*.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="atari")


if __name__ == "__main__":
    main()
