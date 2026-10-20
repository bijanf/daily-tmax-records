"""Europe's heat extremes as a 1-bit desktop: one colour field, dot grid, dithered clouds, windows.

The style follows the retro-terminal look of typesafe.ai: Floyd–Steinberg stipple on a colour
field, Lisa-style windows with black title bars, pixel type for the windows (VT323), code labels
(JetBrains Mono) and one big grotesk headline (Inter Display). Every station keeps its own
mark: a dot on the map, a cell in the grid. Themes recolour the whole scene:

    pink    TS.Pink      the typesafe.ai palette
    violet  Violet.Hour  the sky over the Spree after sunset
    orange  BSR.Orange   the street sweepers' orange
    berlin  BVG.Gelb     U-Bahn yellow, black station signs, the red of the city flag
    xberg   SO36.Nacht   Kreuzberg at night: asphalt, a neon Späti sign, spray paint

    outputs/onebit/europe_extremes[_<theme>].png    2160 x 2700 poster (no suffix for pink)
    outputs/onebit/europe_extremes[_<theme>].mp4    1080 x 1350, 30 fps: the poster assembling itself

    python -I src/plot_onebit.py                        # pink poster and animation
    python -I src/plot_onebit.py --theme berlin xberg   # chosen themes
    python -I src/plot_onebit.py --theme all --no-video # every theme, posters only
"""

from __future__ import annotations

import argparse
import base64
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from scipy import ndimage  # noqa: E402

import findings  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "onebit"
FONTS = ROOT / "data" / "fonts"
PIXEL = FONTS / "vt323" / "VT323-Regular.ttf"
MONO = FONTS / "jetbrains-mono" / "JetBrainsMono-Medium.ttf"
GROTESK = FONTS / "inter" / "ttf" / "InterDisplay-SemiBold.ttf"
TEXT = FONTS / "inter" / "ttf" / "Inter-Medium.ttf"

W, H = 1080, 1350           # logical canvas = video size; the poster is drawn at 2x
FPS, SECONDS = 30, 32
LEFT, RIGHT = 64, 1016

# station grid: heat:cold ratio of 2020-latest, upper bound of each class (colours per theme)
BOUNDS = (10, 20, 50, np.inf)


@dataclass(frozen=True)
class Theme:
    """Every colour role of the scene: one field, one ink, one accent."""
    name: str            # shown in the badge
    field: str           # page and desk; type of the small title bars
    ink: str             # lines, window type, dots and stipple
    head: str            # headline and notes
    paper: str           # window bodies
    light: str           # loader body
    track: str           # dotted floor of the race window
    cold: str            # chip of a period with more cold records
    hot: str             # chip of the 2020s
    levels: tuple        # station grid, from few to many heat records per cold record
    accent: str = ""     # 2020s squares on the map; default: the field
    title: str = ""      # type in the big title bars; default: paper
    dots: str = ""       # dot grid; default: ink
    town: str = "Berlin"

    def __post_init__(self):
        for role, default in (("accent", self.field), ("title", self.paper), ("dots", self.ink)):
            if not getattr(self, role):
                object.__setattr__(self, role, default)


THEMES = {
    "pink": Theme("TS.Pink", field="#F386A1", ink="#1E1E1E", head="#3D3D3D", paper="#FEFEFE",
                  light="#DEDEDE", track="#C4C4C4", cold="#285899", hot="#922239",
                  levels=("#DEDEDE", "#8E8E8E", "#474747", "#1E1E1E")),
    "violet": Theme("Violet.Hour", field="#9F8AF5", ink="#180F33", head="#2A1E57", paper="#FBFAFF",
                    light="#E3DDFA", track="#C6BCEB", cold="#2B4BB0", hot="#A3124F",
                    levels=("#E3DDFA", "#9C8FCB", "#4A3E7D", "#180F33")),
    "orange": Theme("BSR.Orange", field="#FF7A1F", ink="#1C1410", head="#2B1C12", paper="#FFFBF6",
                    light="#F2E4D7", track="#D8C4B1", cold="#1F5DA6", hot="#8C1C13",
                    levels=("#F2E4D7", "#B49985", "#5E4637", "#1C1410")),
    "berlin": Theme("BVG.Gelb", field="#F7D117", ink="#111111", head="#111111", paper="#FFFFFF",
                    light="#EEEEEE", track="#CCCCCC", cold="#0A5CA8", hot="#E2001A",
                    levels=("#E6E6E6", "#999999", "#4D4D4D", "#111111"), title="#F7D117"),
    "xberg": Theme("SO36.Nacht", field="#141218", ink="#E3FF4A", head="#F3F0E8", paper="#1D1A22",
                   light="#29252F", track="#4A4552", cold="#3FA9FF", hot="#FF3D81",
                   levels=("#38333F", "#6C6578", "#B4ADC0", "#E3FF4A"), accent="#FF3D81",
                   dots="#4A4552", town="X-berg"),
}

SOURCES = "Data: NOAA GHCN-Daily · DWD · SMHI · KNMI · GeoSphere · MeteoSwiss"
SIGNATURE = "Bijan Fallah"
EXTENT = [-11, 58, 35.5, 70.5]

# timeline of the animation (seconds): each window opens, fills, then rests long enough to be
# read; the video ends on a slow close-up of the Hottest.Day widget. The poster is t = inf.
T_DESK, T_MAP, T_GRID, T_RACE, T_WIDGET, T_ZOOM = 1.8, 5.5, 11.5, 16.8, 22.5, 25.5
OPEN = 0.4                  # zoom rectangles of an opening window
ZOOM, ZOOM_TIME = 5.0, 4.0  # close-up magnification and how long the camera takes to get there


def summarize(f: dict) -> dict:
    """Numbers behind the poster, Europe only: decades, stations, hottest days."""
    fy = f["final_year"]
    rows = f["region"] == "Europe"
    w = f["window"][rows]
    h20 = ((f["hi_year"][rows] >= 2020) & w).sum(axis=1)
    c20 = ((f["lo_year"][rows] >= 2020) & w).sum(axis=1)
    st = f["idx"].loc[rows, ["name", "country", "lat", "lon"]].copy()
    st["heat"], st["cold"] = h20, c20
    st["ratio"] = np.where(c20 > 0, h20 / np.maximum(c20, 1), np.inf)
    st["hot_year"] = f["hot"].loc[st.index, "year"]
    st["hot_date"] = f["hot"].loc[st.index, "date"]

    periods = [("1880–1989", 1880, 1989), ("1990s", 1990, 1999), ("2000s", 2000, 2009),
               ("2010s", 2010, 2019), ("2020s", 2020, fy)]
    race = [(label, *findings.record_counts(f, "Europe", y0, y1)) for label, y0, y1 in periods]

    latest = st[st["hot_year"] == fy]
    day, n_day = latest["hot_date"].value_counts().index[0], int(latest["hot_date"].value_counts().iloc[0])
    sig = findings.significance(f)
    return dict(fy=fy, st=st, race=race, day=pd.Timestamp(day), n_day=n_day, n_latest=len(latest),
                heat=sig["heat"], cold=sig["cold"], ratio=sig["observed"],
                p=max(sig["n_exceed"], 1) / sig["n_draw"], more_heat=sig["more_heat"])


def europe_raster(lon, lat, w: int, h: int):
    """Land mask of Europe (w x h px, Lambert conformal) and the pixel position of each station."""
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    import matplotlib.pyplot as plt

    proj = ccrs.LambertConformal(central_longitude=22, central_latitude=53, standard_parallels=(40, 64))
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1], projection=proj)
    ax.set_extent(EXTENT, crs=ccrs.PlateCarree())
    ax.spines["geo"].set_visible(False)
    ax.add_feature(cfeature.NaturalEarthFeature("physical", "land", "50m"), facecolor="black",
                   edgecolor="none", antialiased=False)
    fig.canvas.draw()
    land = np.asarray(fig.canvas.buffer_rgba())[..., 0] < 128
    xy = ax.transData.transform(proj.transform_points(ccrs.PlateCarree(), np.asarray(lon),
                                                      np.asarray(lat))[:, :2])
    plt.close(fig)
    xy[:, 1] = h - xy[:, 1]
    return land, xy


def dither(density: np.ndarray) -> np.ndarray:
    """Floyd–Steinberg 1-bit dither; True where a black dot falls."""
    grey = np.uint8(255 * (1 - np.clip(density, 0, 1)))
    return ~np.asarray(Image.fromarray(grey).convert("1"))


def spheres(w: int, h: int, balls, light: float) -> np.ndarray:
    """Density of lit spheres with a sparse spray around them, the dithered 'clouds'."""
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    lx, ly = np.cos(light), np.sin(light)
    out = np.zeros((h, w))
    for cx, cy, r in balls:
        dx, dy = (xx - cx * w) / (r * w), (yy - cy * h) / (r * w)
        rho2 = dx ** 2 + dy ** 2
        z = np.sqrt(np.clip(1 - rho2, 0, 1))
        lit = np.clip(0.55 + 0.45 * (dx * lx + dy * ly) - 0.35 * z, 0, 1)
        out = np.maximum(out, np.where(rho2 < 1, 0.18 + 0.8 * lit * (0.4 + 0.6 * np.sqrt(rho2)),
                                       0.07 * np.exp(-(np.sqrt(rho2) - 1) / 0.12)))
    return out


def prog(t: float, t0: float, dur: float) -> float:
    return float(np.clip((t - t0) / dur, 0, 1))


def ease(p: float) -> float:
    return 1 - (1 - p) ** 3


def smooth(p: float) -> float:
    return p * p * (3 - 2 * p)


class Canvas:
    """Pillow image addressed in logical pixels; one logical pixel = s x s output pixels.

    A close-up draws everything `zoom` times larger with the logical point `at` in the top-left
    corner, so the camera can move in without losing sharpness."""

    def __init__(self, s: int, th: Theme, zoom: float = 1.0, at=(0.0, 0.0)):
        self.s, self.th = s, th
        self.k, (self.ox, self.oy) = s * zoom, at
        self.im = Image.new("RGB", (W * s, H * s), th.field)
        self.d = ImageDraw.Draw(self.im)
        self._fonts: dict = {}

    def font(self, path: Path, size: float):
        key = (path, size)
        if key not in self._fonts:
            self._fonts[key] = ImageFont.truetype(str(path), max(1, round(size * self.k)))
        return self._fonts[key]

    def X(self, v) -> int:
        return int(np.floor((v - self.ox) * self.k + 0.5))

    def Y(self, v) -> int:
        return int(np.floor((v - self.oy) * self.k + 0.5))

    def fill(self, x0, y0, x1, y1, colour):
        if x1 > x0 and y1 > y0:
            a, b = self.X(x0), self.Y(y0)
            self.d.rectangle([a, b, max(self.X(x1), a + 1) - 1, max(self.Y(y1), b + 1) - 1], fill=colour)

    def frame(self, x0, y0, x1, y1, colour=None, fill=None):
        """Rectangle with a one-pixel outline, pixel-exact at any scale."""
        if fill:
            self.fill(x0, y0, x1, y1, fill)
        for box in ((x0, y0, x1, y0 + 1), (x0, y1 - 1, x1, y1), (x0, y0, x0 + 1, y1), (x1 - 1, y0, x1, y1)):
            self.fill(*box, colour or self.th.ink)

    def text(self, x, y, s, path=PIXEL, size=22, colour=None, anchor="ls"):
        self.d.text(((x - self.ox) * self.k, (y - self.oy) * self.k), s, font=self.font(path, size),
                    fill=colour or self.th.ink, anchor=anchor)
        return self.width(s, path, size)

    def width(self, s, path=PIXEL, size=22) -> float:
        return self.font(path, size).getlength(s) / self.k

    def chip(self, x, y, s, size=22, fg=None, bg=None, pad=3, path=PIXEL):
        """Inverse label: text on a solid box; (x, y) is the baseline start. Returns the box width."""
        w = self.width(s, path, size)
        self.fill(x, y - 0.72 * size - pad + 1, x + w + 2 * pad, y + 0.2 * size + pad - 1, bg or self.th.ink)
        self.text(x + pad, y, s, path, size, fg or self.th.paper)
        return w + 2 * pad

    def pixels(self, x0, y0, mask: np.ndarray, colour):
        """Paste a boolean mask (logical pixels) in one colour, scaled up without smoothing."""
        h, w = mask.shape
        # only the part inside the view
        xa, ya = max(0, int(np.floor(self.ox - x0))), max(0, int(np.floor(self.oy - y0)))
        xb = min(w, int(np.ceil(self.ox + self.im.width / self.k - x0)))
        yb = min(h, int(np.ceil(self.oy + self.im.height / self.k - y0)))
        if xb <= xa or yb <= ya:
            return
        a, b = self.X(x0 + xa), self.Y(y0 + ya)
        m = Image.fromarray(np.uint8(mask[ya:yb, xa:xb]) * 255).resize(
            (self.X(x0 + xb) - a, self.Y(y0 + yb) - b), Image.NEAREST)
        self.im.paste(colour, (a, b), m)

    def window(self, x, y, w, h, title, body=None, title_colour=None, bar=22):
        """Lisa-style window: black title bar, double outline. Returns the content box."""
        self.frame(x, y, x + w, y + h, fill=body or self.th.paper)
        self.fill(x, y, x + w, y + bar, self.th.ink)
        self.text(x + 4, y + bar - 5, title, size=22, colour=title_colour or self.th.title)
        self.frame(x + 3, y + bar + 3, x + w - 3, y + h - 3)
        return x + 3, y + bar + 3, x + w - 3, y + h - 3

    def opening(self, x, y, w, h, p):
        """Classic zoom rectangles while a window opens (0 < p < 1)."""
        cx, cy = x + w / 2, y + h / 2
        for k in range(3):
            q = np.clip(p - 0.18 * k, 0.05, 1)
            hw, hh = w / 2 * q, h / 2 * q
            self.frame(cx - hw, cy - hh, cx + hw, cy + hh)


# ── layout (logical pixels) ──────────────────────────────────────────────────

DESK = (LEFT, 424, RIGHT, 1212)
MAP = (84, 462, 524, 424)
GRID = (628, 446, 368, 456)
RACE = (148, 920, 646, 270)
WIDGET = (816, 950, 180, 124)
BADGE = (LEFT, 1236, 286, 92)
BALLS = [(0.97, 0.80, 0.20), (0.03, 0.96, 0.17), (0.60, 1.06, 0.20)]


class Poster:
    def __init__(self, D: dict, th: Theme):
        self.D, self.th = D, th
        st = D["st"]
        x0, y0, x1, y1 = DESK
        self.dw, self.dh = x1 - x0, y1 - y0
        self.desk_rand = np.random.default_rng(1).random((self.dh, self.dw))
        # map: land mask and stations, inside the map window below two lines of text
        mx, my, mw, mh = MAP
        self.map_box = (mx + 8, my + 90, mw - 16, mh - 98)
        _, _, bw, bh = self.map_box
        inside = st[(st["lon"] >= EXTENT[0]) & (st["lon"] <= EXTENT[1]) & (st["lat"] >= EXTENT[2])]
        land, xy = europe_raster(inside["lon"], inside["lat"], bw, bh)
        dist_in = ndimage.distance_transform_edt(land)
        dist_out = ndimage.distance_transform_edt(~land)
        dens = np.where(land, 0.07 + 0.43 * (1 - np.exp(-dist_in / 30)), 0.08 * np.exp(-dist_out / 3))
        self.land = dither(dens)
        self.land_rand = np.random.default_rng(2).random(self.land.shape)
        self.map_st = inside.assign(x=xy[:, 0], y=xy[:, 1]).sort_values("hot_year")
        # grid: stations north to south
        self.grid_st = st.sort_values("lat", ascending=False)
        b64 = (f"heat={D['heat']} cold={D['cold']} ratio={D['ratio']:.1f} stations={len(st)} "
               f"p<{D['p']:.0e} ")
        self.b64 = base64.b64encode(b64.encode()).decode()

    # ── pieces ──

    def background(self, c: Canvas, t: float):
        """Dot grid on the whole desk; dithered clouds that shimmer as the light turns."""
        x0, y0, x1, y1 = DESK
        if t < T_DESK:
            return
        grid = np.zeros((self.dh, self.dw), bool)
        grid[3::6, 3::6] = True
        c.pixels(x0, y0, grid, self.th.dots)
        light = 2.2 + 0.2 * np.sin(2 * np.pi * t / 10) if np.isfinite(t) else 2.2
        clouds = dither(spheres(self.dw, self.dh, BALLS, light))
        c.pixels(x0, y0, clouds & (self.desk_rand < ease(prog(t, T_DESK, 1.8))), self.th.ink)
        c.frame(x0, y0, x1, y1)
        c.chip(x0 + 1, y0 + 19, "EU.TMAX.OS1", size=22, fg=self.th.field, pad=4)

    def headline(self, c: Canvas, t: float):
        D, HEAD, INK = self.D, self.th.head, self.th.ink
        for x, y, dx, dy in ((LEFT, 34, 1, 1), (RIGHT, 34, -1, 1), (LEFT, 392, 1, -1), (RIGHT, 392, -1, -1)):
            c.fill(min(x, x + 12 * dx), y if dy > 0 else y - 1, max(x, x + 12 * dx), (y + 1) if dy > 0 else y, INK)
            c.fill(x if dx > 0 else x - 1, min(y, y + 12 * dy), (x + 1) if dx > 0 else x, max(y, y + 12 * dy), INK)
        if t < T_DESK:
            return
        lead = f"Europe 2020–{D['fy']}"
        tail = "Heat records per cold record"
        w0, w1 = c.width(lead, TEXT, 24), c.width(tail, TEXT, 24)
        c.text(LEFT, 70, lead, TEXT, 24, HEAD)
        c.text(RIGHT, 70, tail, TEXT, 24, HEAD, anchor="rs")
        dots = "." * int((RIGHT - LEFT - w0 - w1 - 24) / c.width(".", TEXT, 24))
        c.text(LEFT + w0 + 12, 70, dots, TEXT, 24, HEAD)

        p = ease(prog(t, T_DESK, 2.5))
        x = LEFT - 8
        size = 300
        for ch in f"{round(D['ratio'] * p)} : 1":
            c.text(x, 330, ch, GROTESK, size, HEAD)
            x += c.width(ch, GROTESK, size) - 0.045 * size
        # the two counts behind the ratio, as stacked stat blocks
        for (n, label), base in zip(((D["heat"], "heat records"), (D["cold"], "cold records")), (190, 300)):
            c.text(RIGHT, base, f"{round(n * p):,}", GROTESK, 76, HEAD, anchor="rs")
            c.text(RIGHT, base + 34, label, TEXT, 21, HEAD, anchor="rs")
        note = (f"*{len(D['st'])} stations, each with >100 years of daily data · year-shuffle test "
                f"p < {D['p']:.0e}".replace("e-0", "e-"))
        k = int(len(note) * prog(t, T_DESK + 0.8, 2.4))
        w = c.text(LEFT, 374, note[:k], MONO, 16, HEAD)
        if not np.isfinite(t) or int(t * 2) % 2 == 0:
            c.fill(LEFT + w + 3, 360, LEFT + w + 13, 378, HEAD)
        # base64 of the numbers, running up the left edge
        strip = Image.new("RGBA", (round(340 * c.k), round(16 * c.k)), (0, 0, 0, 0))
        ImageDraw.Draw(strip).text((0, 0), self.b64[:56], font=c.font(MONO, 11), fill=HEAD)
        strip = strip.rotate(90, expand=True)
        c.im.paste(strip, (c.X(30), c.Y(48)), strip)
        c.text(24, 404, "[B.64]", MONO, 10, HEAD)

    def map_window(self, c: Canvas, t: float):
        x, y, w, h = MAP
        if t < T_MAP:
            return
        if t < T_MAP + OPEN:
            return c.opening(x, y, w, h, prog(t, T_MAP, OPEN))
        D = self.D
        x0, y0, x1, y1 = c.window(x, y, w, h, "Europe.Map")
        c.text(x0 + 8, y0 + 24, "year of each station's hottest day ever", size=22)
        mx, my, mw, mh = self.map_box
        st = self.map_st
        groups = [("2020–" + str(D["fy"])[2:], st["hot_year"] >= 2020), ("2000–19", st["hot_year"].between(2000, 2019)),
                  ("<2000", st["hot_year"] < 2000)]
        lx = x0 + 8
        for i, (label, m) in enumerate(groups):
            self.marker(c, lx + 5, y0 + 46, i)
            lx += 16 + c.text(lx + 16, y0 + 52, f"{label} {int(m.sum())}", size=22) + 22
        c.pixels(mx, my, self.land & (self.land_rand < ease(prog(t, T_MAP + OPEN, 1.2))), self.th.ink)
        # stations appear in the order of their hottest year: the recent ones come last
        shown = int(len(st) * prog(t, T_MAP + 1.0, 4.0))
        for (_, s) in st.iloc[:shown].iterrows():
            kind = 0 if s["hot_year"] >= 2020 else 1 if s["hot_year"] >= 2000 else 2
            self.marker(c, mx + s["x"], my + s["y"], kind)

    @staticmethod
    def marker(c: Canvas, x, y, kind):
        """0: accent square (2020s), 1: hollow square (2000-2019), 2: dot (before 2000)."""
        x, y = round(x), round(y)
        r = (3, 2, 1)[kind]
        c.fill(x - r - 1, y - r - 1, x + r + 2, y + r + 2, c.th.paper)
        if kind == 0:
            c.frame(x - r, y - r, x + r + 1, y + r + 1, fill=c.th.accent)
        elif kind == 1:
            c.frame(x - r, y - r, x + r + 1, y + r + 1)
        else:
            c.fill(x - r, y - r, x + r + 1, y + r + 1, c.th.ink)

    def grid_window(self, c: Canvas, t: float):
        x, y, w, h = GRID
        if t < T_GRID:
            return
        if t < T_GRID + OPEN:
            return c.opening(x, y, w, h, prog(t, T_GRID, OPEN))
        st = self.grid_st
        x0, y0, x1, y1 = c.window(x, y, w, h, "Station.Grid")
        c.text(x0 + 8, y0 + 24, "heat : cold records per station", size=22)
        shown = int(len(st) * ease(prog(t, T_GRID + 0.6, 3.5)))
        n_more = int((st["heat"].iloc[:shown] > st["cold"].iloc[:shown]).sum())
        cw = c.chip(x0 + 8, y0 + 60, f"{n_more} / {len(st)}", size=36, pad=4)
        c.text(x0 + 8 + cw + 10, y0 + 60, "HEAT > COLD", size=22)
        cols, cell = 12, 27
        gx, gy = x0 + (x1 - x0 - cols * cell) / 2, y0 + 78
        rows = int(np.ceil(len(st) / cols))
        for k in range(rows * cols):
            cx, cy = gx + (k % cols) * cell, gy + (k // cols) * cell
            c.frame(cx, cy, cx + cell + 1, cy + cell + 1)
            if k < shown:
                ratio = st["ratio"].iloc[k]
                grey = next(g for top, g in zip(BOUNDS, self.th.levels) if ratio < top or top == np.inf)
                c.fill(cx + 5, cy + 5, cx + cell - 4, cy + cell - 4, grey)
        # stepped ramp, like the site's NO / 50:50 / YES bar
        ry = gy + rows * cell + 12
        sw = (x1 - x0 - 16) / len(BOUNDS)
        labels = ["<10:1", "10–20", "20–50", "≥50:1"]
        for i, (grey, lab) in enumerate(zip(self.th.levels, labels)):
            c.fill(x0 + 8 + i * sw, ry, x0 + 8 + (i + 1) * sw, ry + 14, grey)
            c.text(x0 + 8 + i * sw + 2, ry + 32, lab, size=20)
        c.frame(x0 + 8, ry, x1 - 8, ry + 14)

    def race_window(self, c: Canvas, t: float):
        x, y, w, h = RACE
        if t < T_RACE:
            return
        if t < T_RACE + OPEN:
            return c.opening(x, y, w, h, prog(t, T_RACE, OPEN))
        x0, y0, x1, y1 = c.window(x, y, w, h, "Records.Race")
        th = self.th
        # log axis of the heat:cold ratio, 1/8 to 32; each square sits on its hairline
        ax0, ax1 = x0 + 14, x1 - 14
        pos = lambda r: ax0 + (np.log2(r) + 3) / 8 * (ax1 - ax0)  # noqa: E731
        one, step = pos(1), 38
        c.text(ax0, y0 + 22, "< more cold records", size=20, colour=th.head)
        c.text(ax1, y0 + 22, "more heat records >", size=20, colour=th.head, anchor="rs")
        c.text(one, y0 + 22, "1 : 1", size=20, anchor="ms")
        for yy in range(int(y0 + 30), int(y0 + 58 + 4 * step + 12), 4):
            c.fill(one, yy, one + 1, yy + 2, th.head)
        for i, (label, heat, cold) in enumerate(self.D["race"]):
            r = heat / cold
            by = y0 + 52 + i * step
            bg = th.cold if r < 1 else th.hot if label == "2020s" else th.ink
            c.chip(ax0, by, label, size=22, bg=bg)
            p = smooth(prog(t, T_RACE + 0.8 + 0.5 * i, 1.6))
            rr = 2 ** (np.log2(r) * p)
            c.text(ax0 + 116, by, f"{rr:.1f}x", size=24)
            c.text(ax1, by, f"{round(heat * p):,} : {round(cold * p):,}", size=22, anchor="rs")
            c.fill(ax0, by + 12, ax1, by + 13, th.ink)
            sx = pos(rr)
            c.fill(sx - 4, by + 3, sx + 5, by + 12, th.ink)
        # fine dotted floor, as in the site's race window
        fy0 = y0 + 52 + 4 * step + 20
        floor = np.zeros((int(y1 - 2 - fy0), int(x1 - x0 - 4)), bool)
        floor[1::3, 1::3] = True
        c.pixels(x0 + 2, fy0, floor, th.track)

    def widget(self, c: Canvas, t: float):
        x, y, w, h = WIDGET
        if t < T_WIDGET:
            return
        if t < T_WIDGET + OPEN:
            return c.opening(x, y, w, h, prog(t, T_WIDGET, OPEN))
        D = self.D
        x0, y0, x1, y1 = c.window(x, y, w, h, "Hottest.Day 1.1", body=self.th.field, title_colour=self.th.field)
        c.text(x0 + 6, y0 + 24, D["day"].strftime("%a, %b %d, %Y"), size=22)
        n = round(D["n_day"] * ease(prog(t, T_WIDGET + OPEN, 1.2)))
        cw = c.chip(x0 + 6, y0 + 62, f"{n}", size=40, pad=4)
        c.text(x0 + 6 + cw + 6, y0 + 52, "stations", size=20)
        tw = c.text(x0 + 6 + cw + 6, y0 + 68, "all-time high", size=20)
        if np.isfinite(t) and t > T_ZOOM and int(t * 2) % 2 == 0:
            cx = x0 + 6 + cw + 6 + tw + 2
            c.fill(cx, y0 + 55, cx + 6, y0 + 69, self.th.ink)

    def badge(self, c: Canvas, t: float):
        x, y, w, h = BADGE
        th = self.th
        x0, y0, x1, y1 = c.window(x, y, w, h, "EU.TMAX 1.1", body=th.field, title_colour=th.field)
        # pixel thermometer
        tx, ty = x0 + 10, y0 + 8
        c.frame(tx + 3, ty, tx + 10, ty + 26)
        c.fill(tx + 5, ty + 8, tx + 8, ty + 26, th.ink)
        c.frame(tx, ty + 24, tx + 13, ty + 37, fill=th.ink)
        lines = [f"Version 1.0 · {th.name}", f"©{self.D['fy']} {SIGNATURE}.", f"Made in {th.town}. With Data."]
        for i, line in enumerate(lines):
            c.text(x0 + 30, y0 + 20 + i * 19, line, size=21)
        notes = ["Heat record: the hottest day ever measured on that calendar date.",
                 "Cold record: the coldest daily maximum. p: 200,000 year shuffles.",
                 f"{len(self.D['st'])} stations, each >100 years of daily TMAX. Izaña not mapped.",
                 SOURCES]
        for i, line in enumerate(notes):
            c.text(x + w + 22, y + 20 + i * 21, line, MONO, 12.5, th.head)

    def loader(self, c: Canvas, t: float):
        """Pre-loader window of the video, as on the site."""
        w, h = 380, 150
        x, y = (W - w) / 2, (H - h) / 2
        x0, y0, x1, y1 = c.window(x, y, w, h, "EU.TMAX 1.1", body=self.th.light)
        p = ease(prog(t, 0.2, 1.4))
        c.text(x0 + 10, y0 + 26, "Loading ...", size=24)
        c.text(x0 + 10, y0 + 50, f"{len(self.D['st'])} stations, records, copy", size=22)
        c.text(x1 - 10, y0 + 50, f"{round(100 * p)} %", size=22, anchor="rs")
        bx0, bx1 = x0 + 10, x1 - 10
        n = 24
        cw = (bx1 - bx0) / n
        for k in range(n):
            c.frame(bx0 + k * cw, y0 + 68, bx0 + (k + 1) * cw + 1, y0 + 90)
            if k < round(n * p):
                c.fill(bx0 + k * cw + 3, y0 + 71, bx0 + (k + 1) * cw - 2, y0 + 87, self.th.ink)

    def draw(self, s: int, t: float = np.inf) -> Image.Image:
        zoom, at = 1.0, (0.0, 0.0)
        if np.isfinite(t) and t > T_ZOOM:
            # the widget centre glides to the frame centre while the zoom grows geometrically
            e = smooth(prog(t, T_ZOOM, ZOOM_TIME))
            x, y, w, h = WIDGET
            px, py = x + w / 2, y + h / 2
            zoom = ZOOM ** e
            at = (px - (px + (W / 2 - px) * e) / zoom, py - (py + (H / 2 - py) * e) / zoom)
        c = Canvas(s, self.th, zoom, at)
        if t < T_DESK:
            self.loader(c, t)
            return c.im
        self.background(c, t)
        self.headline(c, t)
        self.map_window(c, t)
        self.grid_window(c, t)
        self.race_window(c, t)
        self.widget(c, t)
        self.badge(c, t)
        return c.im


def video(p: Poster, path: Path) -> None:
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)]
    with subprocess.Popen(cmd, stdin=subprocess.PIPE) as ff:
        for k in range(FPS * SECONDS):
            ff.stdin.write(p.draw(1, k / FPS).tobytes())
        ff.stdin.close()
    print("saved", path)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", nargs="+", default=["pink"], choices=[*THEMES, "all"], help="colour themes")
    ap.add_argument("--no-video", action="store_true", help="posters only")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    D = summarize(findings.compute())
    for key in THEMES if "all" in args.theme else args.theme:
        p = Poster(D, THEMES[key])
        stem = "europe_extremes" + ("" if key == "pink" else f"_{key}")
        p.draw(2).save(OUT / f"{stem}.png", optimize=True)
        print("saved", OUT / f"{stem}.png")
        if not args.no_video:
            video(p, OUT / f"{stem}.mp4")


if __name__ == "__main__":
    main()
