"""1-bit desktop style: one colour field, dot grid, dithered clouds, Lisa-style windows.

The look follows the retro-terminal pages of typesafe.ai: Floyd–Steinberg stipple on a colour
field, windows with black title bars, pixel type for the windows (VT323), code labels
(JetBrains Mono) and one big grotesk headline (Inter Display). A `Story` holds every word and
number of a poster; `Desktop` lays it out the same way for every story (headline, map, station
grid, records race, one widget, a badge) and animates it along a `Timeline`: a loader, windows
that open and fill one after another, and a camera that moves in on them.
Every station keeps its own mark: a dot on the map, a cell in the grid.

Two cuts of the animation:

    CLASSIC  32 s, reading pace, ends on a slow close-up of the widget
    SOCIAL   30 s loop for Instagram reels: opens on the finished poster, switches
             the screen off like an old monitor, builds the desk at double speed, then the
             camera visits every window and returns to the full poster, so the last frame is
             the first. Dots are 2 x 2 pixels and nothing shimmers, so the stipple survives
             the platforms' compression.
    story    for a Story with scenes: one message at a time for people scrolling on a phone.
             The top of the 9:16 frame is a caption band (one bold line typed in word by
             word, one small line); below it the camera rests on one box per scene (the
             headline, the race with one row in focus, the widget) for two to four bars.

Themes recolour the whole scene:

    pink    TS.Pink       the typesafe.ai palette
    violet  Violet.Hour   the sky over the Spree after sunset
    orange  BSR.Orange    the street sweepers' orange
    berlin  BVG.Gelb      U-Bahn yellow, black station signs, the red of the city flag
    xberg   SO36.Nacht    Kreuzberg at night: asphalt, a neon Späti sign, spray paint
    sand    Streusand     Brandenburg's sand, "the sandbox of the Holy Roman Empire"
    uv      Schwarzlicht  black light on the dance floor: ultraviolet, neon mint and magenta
    beton   Beton         Berlin concrete, black type, signal red
    nacht   Berlin.Nacht  the city at night: near black, signal-red heat, ice-blue cold
    feld    Tempelhof.Feld  the old airfield in a dry August: straw grass, rust-red earth
    kanal   Landwehr.Kanal  the canal in Kreuzberg: grey-green water, rust, a navy barge
    pink1   TS.Pink.1bit    true 1-bit: the typesafe.ai pink and black, nothing else
    gelb1   BVG.Gelb.1bit   true 1-bit: U-Bahn yellow and black, nothing else
    firuzeh Firuzeh.1bit    true 1-bit: Persian turquoise (firuzeh) and black
"""

from __future__ import annotations

import base64
import functools
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from scipy import ndimage  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "onebit"
FONTS = ROOT / "data" / "fonts"
PIXEL = FONTS / "vt323" / "VT323-Regular.ttf"
MONO = FONTS / "jetbrains-mono" / "JetBrainsMono-Medium.ttf"
GROTESK = FONTS / "inter" / "ttf" / "InterDisplay-SemiBold.ttf"
TEXT = FONTS / "inter" / "ttf" / "Inter-Medium.ttf"
BOLD = FONTS / "inter" / "ttf" / "InterDisplay-Bold.ttf"
FA_BOLD = FONTS / "vazirmatn" / "Vazirmatn-Bold.ttf"      # Persian captions (lang "fa")
FA_TEXT = FONTS / "vazirmatn" / "Vazirmatn-Medium.ttf"
FOLLOW = {"en": "Follow for more of Europe's extremes in 1-bit",     # last line of every reel
          "fa": "برای داده‌های بیشتر از اقلیم اروپا، فالو کنید"}
FA_MONTHS = {1: "ژانویه", 2: "فوریه", 3: "مارس", 4: "آوریل", 5: "مه", 6: "ژوئن", 7: "ژوئیه", 8: "اوت",
             9: "سپتامبر", 10: "اکتبر", 11: "نوامبر", 12: "دسامبر"}

W, H = 1080, 1350           # logical poster = classic video size; the poster PNG is drawn at 2x
SIZES = {"poster": (W, H), "reel": (1080, 1920), "feed": (1080, 1350)}
FPS = 30
CRF, WEB_CRF, SOCIAL_CRF = 18, 25, 16   # x264 quality: full, calm web cut, platform upload
LEFT, RIGHT = 64, 1016
SIGNATURE = "Bijan Fallah"
EXTENT = [-11, 58, 35.5, 70.5]
OPEN = 0.4                  # zoom rectangles of an opening window
SWITCH_OFF = 0.5            # the screen switching off between the intro and the loader
BPM = 128
BAR = 4 * 60 / BPM          # scenes and the soundtrack count in bars
CAPTION = 600               # story cut: height of the caption band at the top of the reel
VISUAL = (0, 640, 1080, 1000)   # story cut: where the camera puts its box, above the app's overlay


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
    cold: str            # chip of a period on the left of 1 : 1 (cold, wet)
    hot: str             # chip of the 2020s
    levels: tuple        # station grid classes, light to dark
    accent: str = ""     # 2020s squares on the map; default: the field
    title: str = ""      # type in the big title bars; default: paper
    dots: str = ""       # dot grid; default: ink
    town: str = "Berlin"
    mono: bool = False   # two colours only (field and ink): accents become inverse video

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
    "sand": Theme("Streusand", field="#E2BC72", ink="#2A1B0D", head="#3A2613", paper="#FFFAF0",
                  light="#F1E3C6", track="#D9C49C", cold="#285899", hot="#A63A12",
                  levels=("#F1E3C6", "#C49A5E", "#7B4D24", "#2A1B0D"), accent="#C9471A"),
    "uv": Theme("Schwarzlicht", field="#12081F", ink="#CFB8FF", head="#F1EAFF", paper="#1C1030",
                light="#281A42", track="#47366B", cold="#4FB3FF", hot="#FF2BD6",
                levels=("#33264D", "#5E4A8C", "#9A80D9", "#CFB8FF"), accent="#3DFFB0", dots="#3A2A5C"),
    "nacht": Theme("Berlin.Nacht", field="#0B0B0D", ink="#E9E9EC", head="#F5F5F7", paper="#141417",
                   light="#1E1E22", track="#3A3A40", cold="#3FA9FF", hot="#FF3B30",
                   levels=("#2A2A30", "#55555E", "#9A9AA5", "#E9E9EC"), accent="#FF3B30", dots="#26262C"),
    "beton": Theme("Beton", field="#B9B8B2", ink="#141414", head="#161616", paper="#F2F1EC",
                   light="#D8D7D1", track="#C6C5BE", cold="#2A5AA6", hot="#D7191C",
                   levels=("#E3E2DC", "#9C9B95", "#4B4A46", "#141414"), accent="#D7191C"),
    "feld": Theme("Tempelhof.Feld", field="#BDB487", ink="#1C1A12", head="#1F1C12", paper="#F7F4E6",
                  light="#E6E0C6", track="#CEC7A6", cold="#2C5A86", hot="#A8361D",
                  levels=("#E6E0C6", "#A79F78", "#59523A", "#1C1A12"), accent="#A8361D"),
    "pink1": Theme("TS.Pink.1bit", field="#F386A1", ink="#1E1E1E", head="#1E1E1E", paper="#F386A1",
                   light="#F386A1", track="#1E1E1E", cold="#1E1E1E", hot="#1E1E1E",
                   levels=("#F386A1", "#1E1E1E", "#1E1E1E", "#1E1E1E"), title="#F386A1", mono=True),
    "gelb1": Theme("BVG.Gelb.1bit", field="#F7D117", ink="#111111", head="#111111", paper="#F7D117",
                   light="#F7D117", track="#111111", cold="#111111", hot="#111111",
                   levels=("#F7D117", "#111111", "#111111", "#111111"), title="#F7D117", mono=True),
    "firuzeh": Theme("Firuzeh.1bit", field="#4AAFA5", ink="#141414", head="#141414", paper="#4AAFA5",
                     light="#4AAFA5", track="#141414", cold="#141414", hot="#141414",
                     levels=("#4AAFA5", "#141414", "#141414", "#141414"), title="#4AAFA5", mono=True,
                     town="Tehran"),
    "kanal": Theme("Landwehr.Kanal", field="#8FA8A6", ink="#121A1A", head="#122020", paper="#F4F6F3",
                   light="#DCE3E0", track="#C2CDC9", cold="#22507E", hot="#A3312A",
                   levels=("#DCE3E0", "#8FA19D", "#46524F", "#121A1A"), accent="#A3312A"),
}

# pixel icons of the badge, one character per 2 x 2 logical pixels
ICONS = {
    "thermometer": ["..###..", "..#.#..", "..#.#..", "..#.#..", "..###..", "..###..", "..###..",
                    "..###..", ".#####.", "#######", "#######", "#######", ".#####."],
    "drop": ["....#....", "....#....", "...###...", "...###...", "..#####..", "..#####..",
             ".#######.", ".#.#####.", ".#.#####.", ".##.####.", "..#####..", "...###..."],
    "bolt": ["....###", "...###.", "...##..", "..###..", "..##...", ".######", "....##.", "...##..",
             "...#...", "..##...", "..#....", ".#.....", "#......"],
}

# ── layout (logical pixels, x, y, w, h unless noted) ─────────────────────────

FULL = (0, 0, W, H)
HEADLINE = (40, 40, 1000, 370)
BIG_NUMBER = (40, 95, 640, 250)     # the big headline number, for the story cut's camera
DESK = (LEFT, 424, RIGHT, 1212)     # x0, y0, x1, y1
MAP = (84, 462, 524, 424)
GRID = (628, 446, 368, 456)
RACE = (148, 920, 646, 270)
WIDGET = (816, 950, 180, 124)
BADGE = (LEFT, 1236, 286, 92)
BALLS = [(0.97, 0.80, 0.20), (0.03, 0.96, 0.17), (0.60, 1.06, 0.20)]


@dataclass(frozen=True)
class Timeline:
    """When each window opens (seconds), how fast it fills (pace 1 = the classic reading pace)
    and where the camera looks: keyframes (t, box) in poster coordinates. The camera glides from
    one box to the next and rests where neighbouring keyframes share a box. With an intro, the
    video opens on the finished poster and switches the screen off before the loader; a camera
    that ends on the full poster then closes the loop on that same frame."""
    desk: float
    map: float
    grid: float
    race: float
    widget: float
    end: float
    camera: tuple
    pace: float = 1.0
    intro: float = 0.0
    scenes: tuple = ()           # story cut: start of every scene (s)


CLASSIC = Timeline(1.8, 5.5, 11.5, 16.8, 22.5, end=32, camera=((25.5, FULL), (29.5, WIDGET)))
SOCIAL = Timeline(3.0, 4.6, 7.3, 10.0, 12.9, end=30, pace=0.55, intro=1.0, camera=(
    (14.2, FULL), (15.1, MAP), (17.4, MAP), (18.3, GRID), (20.6, GRID), (21.5, RACE), (23.8, RACE),
    (24.7, WIDGET), (27.4, WIDGET), (28.6, FULL)))


@dataclass
class Race:
    """One row of the records race: a period and its two record counts."""
    label: str
    chip: str                    # theme role of the label chip: "cold", "hot" or "ink"
    a: float                     # right of 1 : 1 (heat or dry records; or the recent value)
    b: float                     # left (cold or wet records; or the base value)
    ghost: float | None = None   # second ratio, drawn as a hollow square
    unit: str | None = None      # set: the row shows "b → a unit" (a change), not "a : b" records
    digits: int = 1


@dataclass
class Scene:
    """One beat of the story cut: the camera rests on one box while the caption says one thing."""
    bars: float                  # length, in bars of BPM
    box: tuple                   # what the camera shows (poster coordinates)
    title: str                   # one bold line; {braces} mark the words in the accent colour
    line: str = ""               # one small line under it
    focus: int | None = None     # race row to frame and replay
    count: bool = False          # replay the headline count
    sound: str = ""              # a texture under the scene in the soundtrack: "rain"


@dataclass
class Story:
    """Every word and number of one poster; the layout and the motion are shared."""
    os_name: str                 # tab of the desk
    app: str                     # badge and loader title
    lead: str                    # left of the dotted leader line
    tail: str                    # right of it
    big: float                   # headline number, counted up
    big_fmt: str                 # e.g. "{} : 1"
    stats: list                  # [(number, label)]: two stat blocks right of the headline
    note: str                    # footnote typed under the headline
    secret: str                  # hidden as base64 on the left edge
    final_year: int
    stations: pd.DataFrame       # lat, lon; year (map era); cls (grid class 0-3, -1 no data); hit
    map_title: str
    grid_title: str
    grid_chip: str
    grid_labels: tuple           # under the four steps of the ramp
    race_left: str
    race_right: str
    race: list                   # [Race]
    widget_title: str
    widget_line: str
    widget_n: int
    widget_words: tuple          # two short lines next to the number
    notes: list                  # four lines of footnotes
    loader_line: str
    icon: str = "thermometer"
    race_legend: tuple | None = None   # (hollow, filled) labels in the race title bar
    race_title: str = "Records.Race"
    race_center: str = "1 : 1"
    big_digits: int = 0          # decimals of the headline number
    scenes: tuple = ()           # [Scene]: the story cut for reels
    lang: str = "en"             # language of the scenes; "fa" sets the captions right to left
    cut: str = ""                # name of the cut, in the file names ("one": one message per scene)


def europe_raster(lon, lat, w: int, h: int, extent=EXTENT, proj=None):
    """Land mask of Europe (w x h px, Lambert conformal unless a cartopy projection is given)
    and the pixel position of each station."""
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    import matplotlib.pyplot as plt

    proj = proj or ccrs.LambertConformal(central_longitude=22, central_latitude=53, standard_parallels=(40, 64))
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1], projection=proj)
    ax.set_extent(extent, crs=ccrs.PlateCarree())
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


def blocks(a: np.ndarray, dot: int, shape) -> np.ndarray:
    """Every cell of a coarse array as a dot x dot block, cropped to shape."""
    if dot == 1:
        return a
    return np.kron(a, np.ones((dot, dot), a.dtype))[:shape[0], :shape[1]]


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


def fa(text) -> str:
    """Persian digits, with ٬ for thousands, ٫ for decimals and ٪ for per cent."""
    text = re.sub(r"(?<=\d),(?=\d)", "٬", str(text))
    text = re.sub(r"(?<=\d)\.(?=\d)", "٫", text)
    return text.translate(str.maketrans("0123456789%", "۰۱۲۳۴۵۶۷۸۹٪"))


def prog(t: float, t0: float, dur: float) -> float:
    return float(np.clip((t - t0) / dur, 0, 1))


def ease(p: float) -> float:
    return 1 - (1 - p) ** 3


def smooth(p: float) -> float:
    return p * p * (3 - 2 * p)


def glide(a0, z0, a1, z1, e):
    """View between two views (top-left corner a, zoom z) for 0 <= e <= 1: a zoom about the one
    point that sits at the same place on screen in both views, so the camera never swerves."""
    z = z0 ** (1 - e) * z1 ** e
    if abs(z1 - z0) < 1e-9:
        return a0 + (a1 - a0) * e, z
    p = (z1 * a1 - z0 * a0) / (z1 - z0)
    return p - (p - a0) * z0 / z, z


class Canvas:
    """Pillow image addressed in poster coordinates (logical pixels); one logical pixel is
    s x s output pixels at zoom 1. The view draws everything `zoom` times larger with the
    logical point `at` in the top-left corner, so the camera moves without losing sharpness."""

    def __init__(self, s: int, th: Theme, zoom: float = 1.0, at=(0.0, 0.0), size=(W, H)):
        self.s, self.th = s, th
        self.k, (self.ox, self.oy) = s * zoom, at
        self.im = Image.new("RGB", (size[0] * s, size[1] * s), th.field)
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

    def text(self, x, y, s, path=PIXEL, size=22, colour=None, anchor="ls", direction=None):
        """direction "rtl" for Persian (shaped by raqm); returns the width in logical pixels."""
        self.d.text(((x - self.ox) * self.k, (y - self.oy) * self.k), s, font=self.font(path, size),
                    fill=colour or self.th.ink, anchor=anchor, direction=direction)
        return self.width(s, path, size, direction)

    def width(self, s, path=PIXEL, size=22, direction=None) -> float:
        return self.font(path, size).getlength(s, direction=direction) / self.k

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

    def icon(self, x, y, rows, colour=None, cell=2):
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch == "#":
                    self.fill(x + i * cell, y + j * cell, x + (i + 1) * cell, y + (j + 1) * cell, colour or self.th.ink)

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


class Desktop:
    def __init__(self, story: Story, th: Theme, timeline: Timeline = CLASSIC, shimmer: bool = True,
                 dot: int = 1):
        """dot: side of one stipple dot in logical pixels (2 survives video compression)."""
        self.S, self.th, self.L, self.shimmer, self.dot = story, th, timeline, shimmer, dot
        self.open = max(0.25, OPEN * timeline.pace)
        self.rest = self.count = self.focus = None
        self._clouds, self._still = None, None
        st = story.stations
        x0, y0, x1, y1 = DESK
        self.dw, self.dh = x1 - x0, y1 - y0
        cw, ch = -(-self.dw // dot), -(-self.dh // dot)
        self.desk_rand = blocks(np.random.default_rng(1).random((ch, cw)), dot, (self.dh, self.dw))
        self.desk_grid = np.zeros((self.dh, self.dw), bool)
        step, off = (6, 3) if dot == 1 else (4 * dot, 2 * dot)
        for j in range(dot):
            for i in range(dot):
                self.desk_grid[off + j::step, off + i::step] = True
        # map: land mask and stations, inside the map window below two lines of text
        mx, my, mw, mh = MAP
        self.map_box = (mx + 8, my + 90, mw - 16, mh - 98)
        _, _, bw, bh = self.map_box
        inside = st[(st["lon"] >= EXTENT[0]) & (st["lon"] <= EXTENT[1]) & (st["lat"] >= EXTENT[2])
                    & st["year"].notna()]
        land, xy = europe_raster(inside["lon"], inside["lat"], bw, bh)
        dist_in = ndimage.distance_transform_edt(land)
        dist_out = ndimage.distance_transform_edt(~land)
        dens = np.where(land, 0.07 + 0.43 * (1 - np.exp(-dist_in / 30)), 0.08 * np.exp(-dist_out / 3))
        self.land = blocks(dither(dens[::dot, ::dot]), dot, land.shape)
        self.land_rand = blocks(np.random.default_rng(2).random(dens[::dot, ::dot].shape), dot, land.shape)
        self.map_st = inside.assign(x=xy[:, 0], y=xy[:, 1]).sort_values("year")
        # grid: stations north to south
        self.grid_st = st.sort_values("lat", ascending=False)
        self.b64 = base64.b64encode(story.secret.encode()).decode()

    def d(self, seconds: float) -> float:
        """A duration of the classic cut, at this timeline's pace."""
        return seconds * self.L.pace

    # ── camera ──

    def view(self, box, size):
        """Top-left corner and zoom that centre a box (poster coordinates) in the frame, or in
        the story cut's visual zone below its captions."""
        ow, oh = size
        zx, zy, zw, zh = VISUAL if self.L.scenes and size == SIZES["reel"] else (0, 0, ow, oh)
        x, y, w, h = box
        z = min(zw / w, zh / h) * (1 if w >= 0.85 * W else 0.9)    # the whole poster fills the frame
        return np.array([x + w / 2 - (zx + zw / 2) / z, y + h / 2 - (zy + zh / 2) / z]), z

    def camera(self, t: float, size):
        """Top-left corner, zoom, and the box the camera rests on (None while moving)."""
        keys = self.L.camera if np.isfinite(t) else ((0, FULL),)
        if t <= keys[0][0]:
            return (*self.view(keys[0][1], size), keys[0][1])
        for (t0, b0), (t1, b1) in zip(keys, keys[1:]):
            if t <= t1:
                if b0 == b1:
                    return (*self.view(b0, size), b0)
                (a0, z0), (a1, z1) = self.view(b0, size), self.view(b1, size)
                return (*glide(a0, z0, a1, z1, smooth(prog(t, t0, t1 - t0))), None)
        return (*self.view(keys[-1][1], size), keys[-1][1])

    # ── pieces ──

    def background(self, c: Canvas, t: float):
        """Dot grid on the whole desk; dithered clouds that shimmer as the light turns."""
        x0, y0, x1, y1 = DESK
        if t < self.L.desk:
            return
        c.pixels(x0, y0, self.desk_grid, self.th.dots)
        light = 2.2 + 0.2 * np.sin(2 * np.pi * t / 10) if np.isfinite(t) and self.shimmer else 2.2
        if self._clouds is None or self._clouds[0] != light:
            coarse = dither(spheres(-(-self.dw // self.dot), -(-self.dh // self.dot), BALLS, light))
            self._clouds = (light, blocks(coarse, self.dot, (self.dh, self.dw)))
        reveal = self.desk_rand < ease(prog(t, self.L.desk, self.d(1.8)))
        c.pixels(x0, y0, self._clouds[1] & reveal, self.th.ink)
        c.frame(x0, y0, x1, y1)
        c.chip(x0 + 1, y0 + 19, self.S.os_name, size=22, fg=self.th.field, pad=4)

    def headline(self, c: Canvas, t: float):
        S, HEAD, INK, L = self.S, self.th.head, self.th.ink, self.L
        for x, y, dx, dy in ((LEFT, 34, 1, 1), (RIGHT, 34, -1, 1), (LEFT, 392, 1, -1), (RIGHT, 392, -1, -1)):
            c.fill(min(x, x + 12 * dx), y if dy > 0 else y - 1, max(x, x + 12 * dx), (y + 1) if dy > 0 else y, INK)
            c.fill(x if dx > 0 else x - 1, min(y, y + 12 * dy), (x + 1) if dx > 0 else x, max(y, y + 12 * dy), INK)
        if t < L.desk:
            return
        w0, w1 = c.width(S.lead, TEXT, 24), c.width(S.tail, TEXT, 24)
        c.text(LEFT, 70, S.lead, TEXT, 24, HEAD)
        c.text(RIGHT, 70, S.tail, TEXT, 24, HEAD, anchor="rs")
        dots = "." * int((RIGHT - LEFT - w0 - w1 - 24) / c.width(".", TEXT, 24))
        c.text(LEFT + w0 + 12, 70, dots, TEXT, 24, HEAD)

        p = self.count if self.count is not None else ease(prog(t, L.desk, self.d(2.5)))
        x = LEFT - 8
        size = 300
        big = round(S.big * p, S.big_digits) if S.big_digits else round(S.big * p)
        for ch in S.big_fmt.format(big):
            c.text(x, 330, ch, GROTESK, size, HEAD)
            x += c.width(ch, GROTESK, size) - 0.045 * size
        # the numbers behind the headline, as stacked stat blocks
        for (n, label, *digits), base in zip(S.stats, (190, 300)):
            k = digits[0] if digits else 0
            c.text(RIGHT, base, f"{n * p:,.{k}f}", GROTESK, 76, HEAD, anchor="rs")
            c.text(RIGHT, base + 34, label, TEXT, 21, HEAD, anchor="rs")
        k = int(len(S.note) * prog(t, L.desk + self.d(0.8), self.d(2.4)))
        w = c.text(LEFT, 374, S.note[:k], MONO, 16, HEAD)
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
        t0 = self.L.map
        if t < t0:
            return
        if t < t0 + self.open:
            return c.opening(x, y, w, h, prog(t, t0, self.open))
        fy = self.S.final_year
        x0, y0, x1, y1 = c.window(x, y, w, h, "Europe.Map")
        c.text(x0 + 8, y0 + 24, self.S.map_title, size=22)
        mx, my, mw, mh = self.map_box
        st = self.map_st
        groups = [(f"2020–{str(fy)[2:]}", st["year"] >= 2020), ("2000–19", st["year"].between(2000, 2019)),
                  ("<2000", st["year"] < 2000)]
        lx = x0 + 8
        for i, (label, m) in enumerate(groups):
            self.marker(c, lx + 5, y0 + 46, i)
            lx += 16 + c.text(lx + 16, y0 + 52, f"{label} {int(m.sum())}", size=22) + 22
        reveal = self.land_rand < ease(prog(t, t0 + self.open, self.d(1.2)))
        c.pixels(mx, my, self.land & reveal, self.th.ink)
        # stations appear in the order of their year: the recent ones come last
        shown = int(len(st) * prog(t, t0 + self.d(1.0), self.d(4.0)))
        for (_, s) in st.iloc[:shown].iterrows():
            kind = 0 if s["year"] >= 2020 else 1 if s["year"] >= 2000 else 2
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
        t0 = self.L.grid
        if t < t0:
            return
        if t < t0 + self.open:
            return c.opening(x, y, w, h, prog(t, t0, self.open))
        st = self.grid_st
        x0, y0, x1, y1 = c.window(x, y, w, h, "Station.Grid")
        c.text(x0 + 8, y0 + 24, self.S.grid_title, size=22)
        shown = int(len(st) * ease(prog(t, t0 + self.d(0.6), self.d(3.5))))
        # denominator: stations with data for the question (class -1 = none, an empty cell)
        cw = c.chip(x0 + 8, y0 + 60, f"{int(st['hit'].iloc[:shown].sum())} / {int((st['cls'] >= 0).sum())}",
                    size=36, pad=4)
        c.text(x0 + 8 + cw + 10, y0 + 60, self.S.grid_chip, size=22)
        cols, cell = 12, 27
        gx, gy = x0 + (x1 - x0 - cols * cell) / 2, y0 + 78
        rows = int(np.ceil(len(st) / cols))
        for k in range(rows * cols):
            cx, cy = gx + (k % cols) * cell, gy + (k // cols) * cell
            c.frame(cx, cy, cx + cell + 1, cy + cell + 1)
            if k < shown and st["cls"].iloc[k] >= 0:
                c.fill(cx + 5, cy + 5, cx + cell - 4, cy + cell - 4, self.th.levels[int(st["cls"].iloc[k])])
        # stepped ramp, like the site's NO / 50:50 / YES bar
        ry = gy + rows * cell + 12
        sw = (x1 - x0 - 16) / len(self.th.levels)
        for i, (grey, lab) in enumerate(zip(self.th.levels, self.S.grid_labels)):
            c.fill(x0 + 8 + i * sw, ry, x0 + 8 + (i + 1) * sw, ry + 14, grey)
            c.text(x0 + 8 + i * sw + 2, ry + 32, lab, size=20)
        c.frame(x0 + 8, ry, x1 - 8, ry + 14)

    def race_window(self, c: Canvas, t: float):
        x, y, w, h = RACE
        t0 = self.L.race
        if t < t0:
            return
        if t < t0 + self.open:
            return c.opening(x, y, w, h, prog(t, t0, self.open))
        x0, y0, x1, y1 = c.window(x, y, w, h, self.S.race_title)
        th = self.th
        if self.S.race_legend:
            # hollow and filled square, in the title bar
            lx = x + w - 8
            for label, filled in ((self.S.race_legend[1], True), (self.S.race_legend[0], False)):
                lx -= c.width(label, size=20)
                c.text(lx, y + 17, label, size=20, colour=th.title)
                lx -= 14
                if filled:
                    c.fill(lx, y + 7, lx + 9, y + 16, th.title)
                else:
                    c.frame(lx, y + 7, lx + 9, y + 16, colour=th.title)
                lx -= 14
        # log axis of the ratio, 1/8 to 32; each square sits on its hairline
        ax0, ax1 = x0 + 14, x1 - 14
        pos = lambda r: ax0 + (np.log2(np.clip(r, 1 / 8, 32)) + 3) / 8 * (ax1 - ax0)  # noqa: E731
        one, step = pos(1), 38
        c.text(ax0, y0 + 22, self.S.race_left, size=20, colour=th.head)
        c.text(ax1, y0 + 22, self.S.race_right, size=20, colour=th.head, anchor="rs")
        c.text(one, y0 + 22, self.S.race_center, size=20, anchor="ms")
        for yy in range(int(y0 + 30), int(y0 + 58 + 4 * step + 12), 4):
            c.fill(one, yy, one + 1, yy + 2, th.head)
        for i, row in enumerate(self.S.race):
            r = row.a / max(row.b, 0.25)
            by = y0 + 52 + i * step
            c.chip(ax0, by, row.label, size=22, bg=getattr(th, row.chip))
            focused = self.focus is not None and self.focus[0] == i
            p = self.focus[1] if focused else smooth(prog(t, t0 + self.d(0.8 + 0.5 * i), self.d(1.6)))
            if focused:
                for k in range(2):
                    c.frame(ax0 - 9 + k, by - 25 + k, ax1 + 9 - k, by + 19 - k, colour=th.hot)
            rr = 2 ** (np.log2(r) * p)
            c.text(ax0 + 116, by, f"{rr:.1f}x", size=24)
            if row.unit is None:
                right = f"{round(row.a * p):,} : {round(row.b * p):,}"
            else:   # the value moves from before to now; "→" is not in the pixel font
                k = row.digits
                right = f"{row.b:.{k}f} » {row.b + (row.a - row.b) * p:.{k}f}{row.unit}"
            c.text(ax1, by, right, size=22, anchor="rs")
            c.fill(ax0, by + 12, ax1, by + 13, th.ink)
            if row.ghost is not None:
                gx = pos(2 ** (np.log2(row.ghost) * p))
                c.frame(gx - 4, by + 3, gx + 5, by + 12, fill=th.paper)
            sx = pos(rr)
            c.fill(sx - 4, by + 3, sx + 5, by + 12, th.ink)
        # fine dotted floor, as in the site's race window
        fy0 = y0 + 52 + 4 * step + 20
        floor = np.zeros((int(y1 - 2 - fy0), int(x1 - x0 - 4)), bool)
        floor[1::3, 1::3] = True
        c.pixels(x0 + 2, fy0, floor, th.track)

    def widget(self, c: Canvas, t: float):
        x, y, w, h = WIDGET
        t0 = self.L.widget
        if t < t0:
            return
        if t < t0 + self.open:
            return c.opening(x, y, w, h, prog(t, t0, self.open))
        S = self.S
        x0, y0, x1, y1 = c.window(x, y, w, h, S.widget_title, body=self.th.field, title_colour=self.th.field)
        c.text(x0 + 6, y0 + 24, S.widget_line, size=22)
        n = round(S.widget_n * ease(prog(t, t0 + self.open, self.d(1.2))))
        cw = c.chip(x0 + 6, y0 + 62, f"{n}", size=40, pad=4)
        c.text(x0 + 6 + cw + 6, y0 + 52, S.widget_words[0], size=20)
        tw = c.text(x0 + 6 + cw + 6, y0 + 68, S.widget_words[1], size=20)
        if np.isfinite(t) and self.rest == WIDGET and int(t * 2) % 2 == 0:
            cx = x0 + 6 + cw + 6 + tw + 2
            c.fill(cx, y0 + 55, cx + 6, y0 + 69, self.th.ink)

    def badge(self, c: Canvas, t: float):
        x, y, w, h = BADGE
        th = self.th
        x0, y0, x1, y1 = c.window(x, y, w, h, self.S.app, body=th.field, title_colour=th.field)
        c.icon(x0 + 8, y0 + 8, ICONS[self.S.icon])
        lines = [f"Version 1.0 · {th.name}", f"©{self.S.final_year} {SIGNATURE}.", f"Made in {th.town}. With Data."]
        for i, line in enumerate(lines):
            c.text(x0 + 30, y0 + 20 + i * 19, line, size=21)
        for i, line in enumerate(self.S.notes):
            c.text(x + w + 22, y + 20 + i * 21, line, MONO, 12.5, th.head)

    def loader(self, c: Canvas, t: float):
        """Pre-loader window of the video, as on the site."""
        w, h = 380, 150
        x, y = (W - w) / 2, (H - h) / 2
        x0, y0, x1, y1 = c.window(x, y, w, h, self.S.app, body=self.th.light)
        start = self.L.intro + (SWITCH_OFF if self.L.intro else 0)
        p = ease(prog(t, start + 0.2, self.L.desk - start - 0.4))
        c.text(x0 + 10, y0 + 26, "Loading ...", size=24)
        c.text(x0 + 10, y0 + 50, self.S.loader_line, size=22)
        c.text(x1 - 10, y0 + 50, f"{round(100 * p)} %", size=22, anchor="rs")
        bx0, bx1 = x0 + 10, x1 - 10
        n = 24
        cw = (bx1 - bx0) / n
        for k in range(n):
            c.frame(bx0 + k * cw, y0 + 68, bx0 + (k + 1) * cw + 1, y0 + 90)
            if k < round(n * p):
                c.fill(bx0 + k * cw + 3, y0 + 71, bx0 + (k + 1) * cw - 2, y0 + 87, self.th.ink)

    def switch_off(self, s: int, p: float, size) -> Image.Image:
        """An old monitor switching off: the finished frame squeezes into a line, the line into a dot."""
        if self._still is None or self._still[0] != (s, size):
            self._still = ((s, size), self.draw(s, np.inf, size))
        im = self._still[1]
        w, h = im.size
        out = Image.new("RGB", (w, h), self.th.field)
        if p < 0.6:
            nh = max(2 * s, round(h * (1 - smooth(p / 0.6)) ** 2))
            out.paste(im.resize((w, nh), Image.BILINEAR), (0, (h - nh) // 2))
        else:
            nw = round(w * (1 - smooth((p - 0.6) / 0.4)))
            if nw > 0:
                ImageDraw.Draw(out).rectangle([(w - nw) // 2, h // 2 - s, (w + nw) // 2, h // 2 + s], fill=self.th.ink)
        return out

    def draw(self, s: int, t: float = np.inf, size=(W, H)) -> Image.Image:
        L = self.L
        if L.scenes:
            return self.story_frame(s, t, size)
        if np.isfinite(t) and L.intro:
            if t < L.intro or (t >= L.camera[-1][0] and L.camera[-1][1] == FULL):
                t = np.inf      # the finished poster: the first and the last frames of the loop
            elif t < L.intro + SWITCH_OFF:
                return self.switch_off(s, prog(t, L.intro, SWITCH_OFF), size)
        at, zoom, self.rest = self.camera(t, size)
        c = Canvas(s, self.th, zoom, tuple(at), size)
        if t < L.desk:
            self.loader(c, t)
            return c.im
        return self.scene(c, t)

    def story_frame(self, s: int, t: float, size) -> Image.Image:
        """A frame of the story cut: the finished poster under the camera, one caption above."""
        starts = self.L.scenes
        i = int(np.searchsorted(starts, t, side="right")) - 1 if np.isfinite(t) else 0
        dt = t - starts[i] if np.isfinite(t) else np.inf
        sc = self.S.scenes[i]
        self.count = ease(prog(dt, 0.4, 1.6)) if sc.count else None
        self.focus = (sc.focus, smooth(prog(dt, 0.6, 1.4))) if sc.focus is not None else None
        at, zoom, self.rest = self.camera(t, size)
        c = Canvas(s, self.th, zoom, tuple(at), size)
        self.scene(c, np.inf)
        if size == SIZES["reel"]:
            self.caption(c, i, dt)
        self.count = self.focus = None
        return c.im

    def caption(self, c: Canvas, i: int, dt: float):
        caption_band(c, self.th, self.S.scenes, i, dt, self.S.os_name, self.S.lang)

    def still(self, s: int, box, size) -> Image.Image:
        """The finished poster seen through a camera resting on one box (a carousel slide)."""
        at, zoom = self.view(box, size)
        self.rest = None
        return self.scene(Canvas(s, self.th, zoom, tuple(at), size), np.inf)

    def scene(self, c: Canvas, t: float) -> Image.Image:
        self.background(c, t)
        self.headline(c, t)
        self.map_window(c, t)
        self.grid_window(c, t)
        self.race_window(c, t)
        self.widget(c, t)
        self.badge(c, t)
        return c.im


def caption_band(c: Canvas, th: Theme, scenes, i: int, dt: float, label: str, lang: str = "en"):
    """Caption band of the story cut: scene counter, one bold line typed in word by word
    ({braces} in the hot colour, [brackets] in the cold one), one small line once the bold one is complete. Persian
    runs right to left from the right margin."""
    s, d = c.s, c.d
    sc = scenes[i]
    rtl = lang == "fa"
    bold, text, way = (FA_BOLD, FA_TEXT, "rtl") if rtl else (BOLD, TEXT, None)
    start = RIGHT if rtl else LEFT
    d.rectangle([0, 0, c.im.width, CAPTION * s], fill=th.field)
    d.rectangle([LEFT * s, CAPTION * s, RIGHT * s, (CAPTION + 1) * s], fill=th.ink)
    d.text((start * s, 262 * s), f"[{i + 1:02d}/{len(scenes):02d}] {label}", font=_font(MONO, 22 * s),
           fill=th.head, anchor="rs" if rtl else "ls")
    # {braces}: accent in the hot colour; [brackets]: in the cold colour
    words = [(w, {"{": th.hot, "[": th.cold}.get(part[0])) for part in re.split(r"(\{[^}]*\}|\[[^]]*\])", sc.title)
             if part for w in part.strip("{}[]").split()]
    shown = int(np.ceil(len(words) * prog(dt, 0.15, 0.6))) if np.isfinite(dt) else len(words)
    # two lines at full size; a longer title is set smaller rather than run into the small line
    sizes = ((70, 96), (58, 80)) if rtl else ((76, 86), (62, 70))
    for px, lead in sizes:
        big = _font(bold, px * s)
        places, x, y, space = [], start, 350, big.getlength(" ") / s
        for w, _ in words:
            wl = big.getlength(w, direction=way) / s
            if w[0] in ":;,.!?؟،":    # punctuation after an accent phrase sticks to it
                x += space if rtl else -space
            elif (x < start and x - wl < LEFT) if rtl else (x > start and x + wl > RIGHT):
                x, y = start, y + lead
            places.append((x - wl if rtl else x, y))
            x = x - wl - space if rtl else x + wl + space
        if y <= 350 + lead:
            break
    # the title grows while it is read, about its first corner, and each word pops in
    grow = 0.85 + 0.15 * ease(prog(dt, 0.0, 3.0)) if np.isfinite(dt) else 1.0
    top = 350 - px
    for k, ((w, accent), (x, y)) in enumerate(zip(words, places)):
        if k >= shown:
            continue
        pop = 0.6 + 0.4 * ease(prog(dt, 0.15 + 0.6 * k / len(words), 0.25)) if np.isfinite(dt) else 1.0
        mid = start + (x + big.getlength(w, direction=way) / s / 2 - start) * grow
        size = max(8, round(px * grow * pop * s))
        base = (top + (y - top) * grow) * s
        if accent and th.mono:
            # two colours only: the accent is inverse video, a box of ink under field-coloured type
            half = (_font(bold, size).getlength(w, direction=way) + space * grow * s) / 2
            d.rectangle([mid * s - half, base - 0.84 * size, mid * s + half, base + 0.26 * size], fill=th.ink)
            accent = th.field
        d.text((mid * s, base), w, font=_font(bold, size), fill=accent or th.head, anchor="ms", direction=way)
    y = top + (places[-1][1] - top) * grow
    if sc.line and dt > 0.9:
        d.text((start * s, (y + (72 if rtl else 66)) * s), sc.line, font=_font(text, 34 * s), fill=th.head,
               anchor="rs" if rtl else "ls", direction=way)


def video(desk: Desktop, path: Path, crf: int = CRF, size=(W, H), audio: str | None = None) -> None:
    """H.264 in BT.709 (what phones assume). audio: None, "silent" (an empty track), "music"
    (onebit_audio's techno) or "chip" (onebit_chip's 8-bit tune), timed to the film; the WAV
    is kept beside the video."""
    ow, oh = size
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ow}x{oh}",
           "-r", str(FPS), "-i", "-"]
    if audio == "silent":
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    elif audio in ("music", "chip"):
        import onebit_audio
        import onebit_chip
        engine = onebit_chip if audio == "chip" else onebit_audio
        wav = engine.write(desk, path.with_name(path.stem.removesuffix("_reel") + "_music.wav"))
        cmd += ["-i", str(wav)]
        print("saved", wav)
    if audio:
        cmd += ["-shortest", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx264",
            "-preset", "slow", "-crf", str(crf), "-profile:v", "high", "-colorspace", "bt709",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-movflags", "+faststart", str(path)]
    with subprocess.Popen(cmd, stdin=subprocess.PIPE) as ff:
        for k in range(round(desk.L.end * FPS)):
            ff.stdin.write(desk.draw(1, k / FPS, size).tobytes())
        ff.stdin.close()
    print("saved", path)


def render(story: Story, keys, stem: str, default: str, with_video: bool, web: bool = False,
           social: bool = False) -> None:
    """Poster (and videos) of a story in each theme; the default theme gets no suffix. The web
    video drops the shimmer: still dither compresses to a fraction of the size. Social writes
    the looping cut as an Instagram reel (9:16) with its techno soundtrack and cover, and a 4:5
    carousel."""
    OUT.mkdir(parents=True, exist_ok=True)
    for key in THEMES if "all" in keys else keys:
        th = THEMES[key]
        name = stem + ("" if key == default else f"_{key}")
        if story.lang == "en":      # the poster and its videos carry no captions: one language is enough
            desk = Desktop(story, th)
            desk.draw(2).save(OUT / f"{name}.png", optimize=True)
            print("saved", OUT / f"{name}.png")
            if with_video:
                video(desk, OUT / f"{name}.mp4")
            if web:
                desk.shimmer = False
                video(desk, OUT / f"{name}_web.mp4", WEB_CRF)
        if social:
            (OUT / "social").mkdir(exist_ok=True)
            tag = (f"_{story.cut}" if story.cut else "") + ("" if story.lang == "en" else f"_{story.lang}")
            base = OUT / "social" / f"{stem}_{key}{tag}"
            loop = Desktop(story, th, storyline(story) if story.scenes else SOCIAL, shimmer=False, dot=2)
            loop.draw(1, np.inf, SIZES["reel"]).save(f"{base}_cover.png", optimize=True)
            video(loop, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="music")
            if story.lang == "en" and not story.cut:
                carousel(loop, base)


def storyline(story: Story, move: float = 0.9, push: float = 0.92) -> Timeline:
    """The story cut of a story: its scenes back to back. The camera glides to each scene's box
    and keeps pushing in slowly while the scene lasts; the last scene pulls back out to its box,
    the first frame, so a looping reel has no seam."""
    starts = np.cumsum([0.0] + [sc.bars * BAR for sc in story.scenes])
    keys, last = [], len(story.scenes) - 1
    for i, sc in enumerate(story.scenes):
        near = _closer(sc.box, push)
        a, b = (near, sc.box) if i == last else (sc.box, near)
        keys += [(float(starts[i]) + (move if i else 0.0), a), (float(starts[i + 1]), b)]
    return Timeline(0, 0, 0, 0, 0, end=float(starts[-1]), camera=tuple(keys),
                    scenes=tuple(float(t) for t in starts[:-1]))


def _closer(box, f: float):
    """The same box, f times its size about its centre."""
    x, y, w, h = box
    return (x + w * (1 - f) / 2, y + h * (1 - f) / 2, w * f, h * f)


@functools.lru_cache(maxsize=1024)
def _font(path: Path, px: int):
    return ImageFont.truetype(str(path), px)


def carousel(desk: Desktop, base: Path) -> None:
    """An Instagram carousel: five 4:5 slides, the full poster and the camera's four stops."""
    for i, box in enumerate((FULL, MAP, GRID, RACE, WIDGET), 1):
        desk.still(1, box, SIZES["feed"]).save(f"{base}_slide{i}.png", optimize=True)
    print("saved", f"{base}_slide1-5.png")
