"""WINTER NO2 OVER IRAN, FROM SPACE: the tropospheric NO2 column that Sentinel-5P sees over the whole country, the
winter of 1404 (Azar to Bahman) against the summer (Tir to Shahrivar 1405), the twelve Jalali months in between.

A static camera on Iran, drawn at 2x (2160 x 3840) and downscaled with Lanczos to 1080 x 1920:
  the relief: a hillshade of about 1 km (air_grid.py: Copernicus GLO-30, GLO-90 where GLO-30 has no tile), low sun
  from the north-west at 20 degrees, vertical exaggeration 2; muted earth tones, dimmer outside Iran and the sea dark;
  the coast (Natural Earth 10 m coastline), the borders (Natural Earth 10 m boundary lines; Iran's outline bright),
  drawn as vectors at the render scale.
  the NO2 field: the oversampled fields of air_grid.py (each TROPOMI pixel spread over its footprint on a 0.02-degree
  grid, all overlapping orbits, qa >= 0.75, OFFL with the NRTI fill), one colour scale for all months, a narrow halo.

Measured data only (air.py, air_grid.py): the counter is the Tehran-Karaj box's month mean over the summer reference
(Tir to Shahrivar 1405, pooled), the area-weighted mean of the oversampled cells; the held counter is the same box's
Azar-Bahman 1404 mean over that reference (asserted: x3).

    0.0 s         the Azar-Bahman 1404 field over Iran, the hook and the held counter
    1.0-9.46 s    the Jalali months Aban 1404 to Mehr 1405 at 1.3 months a second; the counter is that month
    9.46-10.06 s  the turn back to the Azar-Bahman field
    10.6-19.06 s  the months again, from Aban 1404 to Mehr 1405
    19.06-19.66 s the turn back; from about 20 s the Azar-Bahman field is held to the end, the counter held

Colour: one scale for all months (VMIN..VMAX, GAMMA), the same function for the glow and the legend.

    python -I src/onebit_air.py              # the film (the video is rendered by the driver)
    python -I src/onebit_air.py --stills     # the cover and the stills, no video
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

import air  # noqa: E402
import air_grid  # noqa: E402
import onebit  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, SIZES, SOCIAL_CRF, fa  # noqa: E402

W, H = air.W, air.H                              # the output: 1080 x 1920
SS = 2                                           # the render scale: drawn at 2x, then downscaled (Lanczos)
WR, HR = W * SS, H * SS
DURATION = 24.0                                  # s
RATE = 1.3                                       # months a second
PASS_LEN = 11 / RATE                             # s: Aban 1404 to Mehr 1405 (twelve months, eleven steps)
DIAL_STARTS = (1.0, 10.6)                        # s: the months play twice, from Aban 1404 each time
TURN = 0.6                                       # s: back to the Azar-Bahman field after each pass
FADE = 0.4                                       # s: the glow comes in from the Azar-Bahman field at each start
TURNS = tuple(s + PASS_LEN for s in DIAL_STARTS) # s: the start of each turn (Mehr 1405 each time)
DIAL_END = TURNS[-1]                             # s: the end of the second pass (Mehr 1405)
HOLD = DIAL_END + TURN                           # s: the Azar-Bahman field is held from here to the end (about 20 s)
VMIN, VMAX, GAMMA = 2.0, 60.0, 0.5               # 1e15 molec/cm2: one scale for the map, the glow and the bar: sqrt((v-2)/58)
ORANGE = np.array([255, 120, 30], np.float32)
HOT = np.array([255, 214, 140], np.float32)
EARTH = np.array([66, 76, 90], np.float32)       # cool dark slate: the orange glow stands off it
SEA = np.array([6, 10, 18], np.float32)          # the sea: darker than any land, so coasts read
OUT_LAND = np.array([34, 38, 45], np.float32)    # land outside Iran: flat dark grey, clearly not sea
PAPER, SHADOW, AMBER = (250, 246, 238, 255), (8, 10, 14, 255), (255, 150, 60, 255)
MONTHS = air.DIAL_JK                             # Aban 1404 to Mehr 1405 (Jalali keys "YYYY-MM")
BLOOM_PX = 2.0                                   # render px: the halo's width (a narrow halo, not a blur)
BLOOM_K = 0.35                                   # the halo's share of the glow (the core carries the glow)
# the country view: Iran's width about 980 output px, Tehran in the upper middle (output px; km per output px)
VIEW = dict(lon=53.65, lat=32.5, yA=700.0, km=1.945)
URMIA_LABEL = (45.32, 37.42)                    # lon, lat: the grey name of Lake Urmia (the lake is under the winter glow)
CITIES = (("تهران", 51.39, 35.69), ("مشهد", 59.61, 36.30), ("اصفهان", 51.67, 32.65), ("تبریز", 46.29, 38.08),
          ("شیراز", 52.53, 29.59), ("اهواز", 48.67, 31.32))
TITLE = ("زمستان، ایران از فضا:", "دی‌اکسیدِ نیتروژن کجا جمع می‌شود؟")
# two runs, drawn right to left: the English runs in one string reorder under bidi, so each label is its own run
SOURCES = ("منبع: Sentinel-5P (ESA/Copernicus)", "تصویرِ زمین: NASA Blue Marble")
BM = dict(lon0=42.0, lat0=45.5, step=0.005, nx=4700, ny=7000)   # the Blue Marble crop, the whole frame (north edge lat0)
DUSK = 0.36                                      # the base brightness: the Earth at dusk, the glow is the light
HOLD_WORD = "آذر تا بهمن ۱۴۰۴"
# the layout, in output px (baselines unless stated); drawn at SS times these
Y_TITLE = (180, 255)                             # the title's top at about y 135, clear of Reels' top overlay
Y_COUNTER, Y_MONTH = 1290, 1378
COUNTER_PX = 170                                 # px: «تهران ×۴٫۲» (the widest) on one line, inside x 150-930 (counter_ok)
Y_BAR, Y_BAR_NUM, Y_UNIT, Y_SOURCES = 1418, 1466, 1514, 1566
BAR_X = (150, 880)                               # px: the colour bar's ends (the numbers stay inside x 930)
BAR_TICKS = (10, 30)                             # 1e15 molec/cm2: labelled between the ends (2 and 60)
NATURAL = air_grid.NE


def font(path, px: int):
    from PIL import ImageFont
    return ImageFont.truetype(str(path), px)


def pct(v: float) -> str:
    return "×" + fa(f"{v:.1f}")                  # one decimal: ×۴٫۲


def intensity(raw):
    """The one colour scale: NO2 (1e15 molec/cm2) to 0-1. The glow and the legend both use this."""
    return np.clip((np.asarray(raw, float) - VMIN) / (VMAX - VMIN), 0, 1) ** GAMMA



def ensure_bluemarble() -> Path:
    """NASA Blue Marble, shaded relief and bathymetry (public domain), cropped to Iran from NASA GIBS (keyless WMS)."""
    path = air.DATA / "bluemarble_srb_iran.jpg"
    if not path.exists():                                   # two halves (the service caps the image size), stitched
        import io
        import urllib.request
        half = BM["ny"] // 2
        out = Image.new("RGB", (BM["nx"], BM["ny"]))
        for k in range(2):
            north = BM["lat0"] - k * half * BM["step"]
            south = north - half * BM["step"]
            url = ("https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap"
                   "&VERSION=1.3.0&LAYERS=BlueMarble_ShadedRelief_Bathymetry&STYLES=&CRS=EPSG:4326"
                   f"&BBOX={south},{BM['lon0']},{north},{BM['lon0'] + BM['nx'] * BM['step']}"
                   f"&WIDTH={BM['nx']}&HEIGHT={half}&FORMAT=image/jpeg")
            with urllib.request.urlopen(url, timeout=180) as r:
                out.paste(Image.open(io.BytesIO(r.read())).convert("RGB"), (0, k * half))
        out.save(path, quality=92)
    return path

def bar_x(v: float) -> float:
    """Output px of value v on the colour bar: the bar is linear in intensity(v), so the colour is linear along it."""
    return BAR_X[0] + float(intensity(v)) * (BAR_X[1] - BAR_X[0])


def counter_half_width(s: str) -> float:
    """Half the width (output px) of the counter «تهران <s>» with its stroke."""
    f = font(FA_BOLD, COUNTER_PX * SS)
    return f.getlength("تهران " + s, direction="rtl", language="fa") / SS / 2 + 6


def counter_ok(s: str) -> None:
    """The counter must stay inside x 150-930 (the buttons' column; nothing below y 1000 reaches within 150 px of the edge)."""
    hw = counter_half_width(s)
    assert 540 - hw >= 150 and 540 + hw <= 930, ("counter too wide", s, round(2 * hw, 1))


def smoothstep(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def text(im, x, y, s, path, px, anchor="ms", fill=PAPER, stroke=4):
    """Text in output px (drawn at the render scale)."""
    f = font(path, px * SS)
    ImageDraw.Draw(im).text((x * SS, y * SS), s, font=f, fill=fill, anchor=anchor, direction="rtl", language="fa",
                            stroke_width=stroke * SS, stroke_fill=SHADOW)
    return f.getlength(s, direction="rtl", language="fa")


def _lines(path, bbox, only=None) -> list:
    """Polylines (lon, lat arrays) of a Natural Earth line or polygon layer inside bbox (W, S, E, N)."""
    import shapefile
    r = shapefile.Reader(str(path))
    out = []
    for sh, rec in zip(r.iterShapes(), r.iterRecords() if only else [None] * len(r)):
        if only is not None and rec["ADMIN"] != only:
            continue
        x0, y0, x1, y1 = sh.bbox
        if x1 < bbox[0] or x0 > bbox[2] or y1 < bbox[1] or y0 > bbox[3]:
            continue
        pts = np.asarray(sh.points, float)
        starts = list(sh.parts) + [len(pts)]
        out += [pts[a:b] for a, b in zip(starts[:-1], starts[1:])]
    return out


class AirFilm:
    """The film: draw(1, t) is the frame at t seconds (t = inf: the end state), 1080 x 1920."""

    def __init__(self):
        # the fine fields (air_grid.py, 0.02 degree, oversampled) when they exist; else the coarse ones (air.py, 0.04)
        self.fine = air_grid.GLOW_PATH.exists() and air_grid.BOX_PATH.exists()
        if self.fine:
            box = air_grid.load_box()
            self.table = _table(box)
            self.winter = float(box["winter"])
            self.ref = float(box["ref"])
            self.fields, self.cover, self.iran_grid = air_grid.load_glow()
            self.grid = air_grid.GRID
        else:
            self.table = air.monthly()
            self.winter = float(self.table.attrs["winter"])
            self.ref = float(self.table.attrs["ref"])
            self.fields, self.cover = air.iran_glow()
            self.grid = air.IRAN_GRID
            self.iran_grid = np.load(air.DATA / "iran_relief.npz")["inside"] > 0.5
        print("NO2 fields:", "FINE " + air_grid.GLOW_PATH.name + " (0.02 deg, oversampled)" if self.fine
              else "COARSE iran_glow.npz (0.04 deg; " + air_grid.GLOW_PATH.name + " not built)",
              flush=True)
        self.ratio = {jk: float(r) for jk, r in zip(self.table.jk, self.table.ratio)}
        self.rel = air_grid.load_relief()
        self.checks()
        self.L = type("L", (), {"end": DURATION})()
        self.dial_end = DIAL_END
        self.km = VIEW["km"] / SS                 # km per render px
        self.LON, self.LAT = self.lonlat()
        self.base = self.make_base()
        self.glow = {k: self.make_glow(k) for k in MONTHS + ["winter", "summer"]}
        self.static = self.make_static()
        self.assert_scale()

    # ── checks: every number on the screen ──

    def checks(self):
        m, r = self.table, self.ratio
        assert list(m.jk) == MONTHS, list(m.jk)
        assert (m.n_pix > 1000).all() and (m.n_days >= 5).all(), m[["jk", "n_pix", "n_days"]]
        summer = [r[jk] for jk in air.REF_JK]
        assert all(0.7 < v < 1.3 for v in summer), summer
        assert 3.20 <= self.winter <= 3.26, self.winter          # the Tehran-Karaj box (OFFL+NRTI): 3.23, shown as x3
        self.held = int(round(self.winter))
        assert self.held == 3, self.winter                       # the held counter: x3
        for v in r.values():                                     # every counter string the film can show fits the margin:
            counter_ok(pct(v))                                   # a month (one decimal), and the turns and the hold (x3)
        for v in list(r.values()) + [self.winter]:
            counter_ok("×" + fa(f"{v:.0f}"))
        counter_ok("×" + fa(f"{self.held}"))
        assert max(r, key=r.get) == "1404-09", r                 # Azar is the peak month
        assert r["1404-12"] < r["1404-09"] and r["1404-11"] < r["1404-09"], r
        # the share of Iran's land cells with no data, per month; fails above 10 %
        land = self.iran_grid
        self.empty_share = {}
        for k in air.DIAL_JK + ["winter", "summer"]:
            self.empty_share[k] = float((land & ~self.cover[k]).sum() / land.sum())
        print("share of Iran's land cells with no data, per month:")
        for k, v in self.empty_share.items():
            print(f"    {k}  {100 * v:5.1f} %")
        worst = max(self.empty_share, key=self.empty_share.get)
        assert self.empty_share[worst] <= 0.10, (worst, self.empty_share[worst])

    def assert_scale(self):
        """The country view and the close-up use one colour scale: the legend's ends are the scale's ends."""
        assert intensity(np.array([VMIN]))[0] == 0.0 and intensity(np.array([VMAX]))[0] == 1.0
        assert (VMIN, VMAX, GAMMA) == (2.0, 60.0, 0.5)
        # the legend's colour at any value is the glow's: one function, one scale
        for v in (2.0, 15.0, 30.0, 60.0):
            c = float(intensity(v))
            assert abs(c - np.sqrt((v - 2.0) / 58.0)) < 1e-9, (v, c)
        for v in BAR_TICKS:                                       # the bar's position of v is its colour's intensity
            c = (bar_x(v) - BAR_X[0]) / (BAR_X[1] - BAR_X[0])
            assert abs(c - float(intensity(v))) < 1e-9 and abs(VMIN + (VMAX - VMIN) * c ** (1 / GAMMA) - v) < 1e-9, v

    # ── geometry (render px) ──

    def lonlat(self):
        v = VIEW
        yy, xx = np.mgrid[0:HR, 0:WR].astype(np.float64)
        lon = v["lon"] + (xx + 0.5 - WR / 2) * self.km / (111.32 * math.cos(math.radians(v["lat"])))
        lat = v["lat"] - (yy + 0.5 - v["yA"] * SS) * self.km / 110.574
        return lon.astype(np.float32), lat.astype(np.float32)

    def place(self, lon, lat) -> tuple:
        v = VIEW
        k = self.km
        x = WR / 2 + (np.asarray(lon, float) - v["lon"]) * 111.32 * math.cos(math.radians(v["lat"])) / k - 0.5
        y = v["yA"] * SS - (np.asarray(lat, float) - v["lat"]) * 110.574 / k - 0.5
        return x, y

    @staticmethod
    def sample(arr, g: dict, lon, lat):
        from scipy import ndimage
        fi = (lon - g["lon0"]) / g["step"] - 0.5
        fj = (g["lat0"] - lat) / g["step"] - 0.5
        return ndimage.map_coordinates(arr, [fj, fi], order=1, mode="nearest")

    # ── layers ──

    def make_base(self) -> np.ndarray:
        """NASA Blue Marble (shaded relief and bathymetry, ~500 m) as the real Earth, darkened like dusk so the NO2
        glow stands off it; Iran a little brighter than its neighbours; Iran's outline as one thin line. The water
        mask comes from the image itself (blue-dominant pixels: the Caspian, the Gulf, Lake Urmia), so the glow is
        clipped at the real coast."""
        from scipy import ndimage
        lon, lat = self.LON, self.LAT
        bm = np.asarray(Image.open(ensure_bluemarble()).convert("RGB"), np.float32)
        rgb = np.stack([self.sample(bm[..., k], BM, lon, lat) for k in range(3)], -1)
        water = (rgb[..., 2] > rgb[..., 0] + 25) & (rgb[..., 2] > rgb[..., 1] - 8)
        water = ndimage.binary_opening(water, iterations=2)
        ins = self.sample(np.asarray(self.rel["iran"], np.float32), air_grid.REL, lon, lat)
        grey = rgb.mean(axis=-1, keepdims=True)
        dusk = (0.72 * rgb + 0.28 * grey) * DUSK                       # darker and a little desaturated
        base = dusk * (0.82 + 0.30 * ins[..., None])                    # Iran a little brighter
        self.iran_land = np.clip(ins * (1 - water), 0, 1).astype(np.float32)   # the glow is clipped to it
        base = np.clip(base, 0, 255).astype(np.uint8)
        im = Image.fromarray(base, "RGB")
        d = ImageDraw.Draw(im)
        bbox = (self.LON.min(), self.LAT.min(), self.LON.max(), self.LAT.max())
        for ln in _lines(NATURAL / "ne_10m_admin_0_countries.shp", bbox, only="Iran"):
            d.line([tuple(p) for p in np.column_stack(self.place(ln[:, 0], ln[:, 1])).tolist()], fill=(214, 220, 228),
                   width=2 * SS, joint="curve")
        return np.asarray(im, np.float32)

    def make_glow(self, key: str) -> np.ndarray:
        """A field as the glow, 0-1: the one colour scale, a narrow halo of BLOOM_PX."""
        from scipy import ndimage
        raw = self.sample(self.fields[key], self.grid, self.LON, self.LAT)
        i = intensity(raw)
        bloom = ndimage.gaussian_filter(i, BLOOM_PX) * 0.9
        keep = np.clip(ndimage.gaussian_filter(self.iran_land, 1.0), 0, 1)   # only over Iran's land, a 1-px feather
        return (np.clip(1.0 * i + BLOOM_K * bloom, 0, 1) * keep).astype(np.float32)

    def make_static(self) -> Image.Image:
        """The title, the six city dots and labels, the colour bar with its two ends, the sources line (render px)."""
        im = Image.new("RGBA", (WR, HR), (0, 0, 0, 0))
        for s, y in zip(TITLE, Y_TITLE):
            w = text(im, 540, y, s, FA_BOLD, 58, stroke=5)
            assert w <= 960 * SS, (s, w)
        for name, lon, lat in CITIES:
            x, y = self.place(lon, lat)
            x, y = float(x), float(y)
            d = ImageDraw.Draw(im)
            r = 9 * SS
            d.ellipse([x - r, y - r, x + r, y + r], fill=PAPER, outline=SHADOW, width=2 * SS)
            f = font(FA_BOLD, 34 * SS)
            tw = f.getlength(name, direction="rtl", language="fa")
            left = x + 18 * SS if x < 700 * SS else x - 18 * SS - tw
            d.rounded_rectangle([left - 10 * SS, y - 26 * SS, left + tw + 10 * SS, y + 12 * SS], radius=12 * SS,
                                fill=(8, 10, 14, 200))
            ImageDraw.Draw(im).text((left, y + 2 * SS), name, font=f, fill=PAPER, anchor="ls", direction="rtl",
                                    language="fa", stroke_width=3 * SS, stroke_fill=SHADOW)
        d = ImageDraw.Draw(im)
        x0, x1 = BAR_X[0] * SS, BAR_X[1] * SS
        for xx in range(x0, x1):                      # x is the intensity (the square-root stretch), the colour its glow colour
            c = (xx - x0) / (x1 - x0)
            col = tuple(int(q) for q in ORANGE * (1 - c) + HOT * c) + (255,)
            d.line([(xx, Y_BAR * SS), (xx, (Y_BAR + 16) * SS)], fill=col)
        d.rectangle([x0, Y_BAR * SS, x1, (Y_BAR + 16) * SS], outline=PAPER, width=2 * SS)
        for v in BAR_TICKS:                           # the ticks at the stretched positions, the same function as the glow
            xt = bar_x(v) * SS
            d.line([(xt, (Y_BAR + 16) * SS), (xt, (Y_BAR + 24) * SS)], fill=PAPER, width=2 * SS)
            text(im, bar_x(v), Y_BAR_NUM, fa(v), FA_TEXT, 32, anchor="ms", stroke=3)
        text(im, BAR_X[0], Y_BAR_NUM, fa(int(VMIN)), FA_TEXT, 32, anchor="ms", stroke=3)
        text(im, BAR_X[1], Y_BAR_NUM, fa(int(VMAX)), FA_TEXT, 32, anchor="ms", stroke=3)
        # the unit, under the numbers: «دی‌اکسیدِ نیتروژن، ۱۰¹⁵ مولکول بر سانتی‌مترِ مربع» (the exponent drawn small and
        # raised: the font has no superscript digits); right to left: the name, the number (left to right), the unit
        px, pe = 30, 20
        fa_, fe_ = font(FA_TEXT, px * SS), font(FA_TEXT, pe * SS)
        A, N, E, C = "دی‌اکسیدِ نیتروژن، ", "۱۰", "۱۵", " مولکول بر سانتی‌مترِ مربع"
        wA, wN, wC = (fa_.getlength(t, direction="rtl", language="fa") / SS for t in (A, N, C))
        wE = fe_.getlength(E, direction="rtl", language="fa") / SS
        total = wA + wN + wE + wC
        x_r = 540 + total / 2
        assert x_r <= 930 and x_r - total >= 60, ("unit line", x_r, total)
        text(im, x_r - wA / 2, Y_UNIT, A, FA_TEXT, px, stroke=3)
        text(im, x_r - wA - wE - wN / 2, Y_UNIT, N, FA_TEXT, px, stroke=3)
        text(im, x_r - wA - wE / 2, Y_UNIT - 0.42 * px, E, FA_TEXT, pe, stroke=2)
        text(im, x_r - wA - wN - wE - wC / 2, Y_UNIT, C, FA_TEXT, px, stroke=3)
        gap = 36                                       # output px between the two runs
        f_src = font(FA_TEXT, 28 * SS)
        w_src = [f_src.getlength(t, direction="rtl", language="fa") / SS for t in SOURCES]
        x_right = min(540 + (w_src[0] + gap + w_src[1]) / 2, 926)   # the first run on the right (x <= 926: clear of the
        # 150-px edge zone below y 1000), the second to its left; the block is shifted left if it would reach further
        assert x_right - (w_src[0] + gap + w_src[1]) >= 60, "sources line too wide"
        text(im, x_right - w_src[0] / 2, Y_SOURCES, SOURCES[0], FA_TEXT, 28, stroke=3)
        text(im, x_right - w_src[0] - gap - w_src[1] / 2, Y_SOURCES, SOURCES[1], FA_TEXT, 28, stroke=3)
        # the Urmia label: the lake is under the winter glow in the cold months; a small grey name beside it
        lx, ly = self.place(*URMIA_LABEL)
        text(im, float(lx) / SS, float(ly) / SS, "دریاچه ارومیه", FA_TEXT, 26, anchor="ms", fill=(170, 176, 186, 255), stroke=3)
        return im

    # ── time ──

    def state(self, t: float):
        """(glow A, glow B, blend, counter value, month word, phase) at t seconds."""
        win = "winter"
        if not np.isfinite(t) or t < DIAL_STARTS[0] or t >= HOLD:
            return win, win, 0.0, self.winter, "hold", "hold"
        for s, e in zip(DIAL_STARTS, TURNS):
            if t < s:                                  # between the passes: the Azar-Bahman field
                return win, win, 0.0, self.winter, "hold", "hold"
            if t < e:                                  # a pass: the months, a fade in from the winter at its start
                p = min((t - s) * RATE, len(MONTHS) - 1)
                a = int(math.floor(p))
                b = min(a + 1, len(MONTHS) - 1)
                k = int(round(p))
                if t - s < FADE:
                    return win, MONTHS[0], smoothstep((t - s) / FADE), self.ratio[MONTHS[0]], MONTHS[0], "dial"
                return MONTHS[a], MONTHS[b], p - a, self.ratio[MONTHS[k]], MONTHS[k], "dial"
            if t < e + TURN:                           # the turn back to the Azar-Bahman field
                w = (t - e) / TURN
                last = MONTHS[-1]
                value = self.ratio[last] + (self.winter - self.ratio[last]) * smoothstep(w)
                return last, win, smoothstep(w), value, last, "turn"
        return win, win, 0.0, self.winter, "hold", "hold"

    def schedule(self) -> dict:
        """The film's clock, for the score: each month's tick (s, Jalali key), the turns (s), the hold (s)."""
        ticks = [(s + k / RATE, ym) for s in DIAL_STARTS for k, ym in enumerate(MONTHS)]
        return dict(ticks=ticks, turns=list(TURNS), hold=HOLD, end=DURATION)

    @staticmethod
    def month_word(key: str) -> str:
        y, m = int(key[:4]), int(key[5:])
        return f"{air.JALALI_NAMES[m - 1]} {fa(y)}"

    # ── frame ──

    def draw_frame(self, t: float) -> Image.Image:
        """The frame at render scale (WR x HR)."""
        ga, gb, w, value, key, phase = self.state(t)
        g = (1 - w) * self.glow[ga] + w * self.glow[gb]
        img = self.base + g[..., None] * (ORANGE[None, None] + (HOT - ORANGE)[None, None] * g[..., None])
        im = Image.fromarray(np.clip(img + 0.5, 0, 255).astype(np.uint8)).convert("RGBA")
        im.alpha_composite(self.static)
        if phase == "hold":                          # the held Azar-Bahman field: x3 (the box ratio, rounded)
            s, word = "×" + fa(f"{self.held}"), HOLD_WORD
        elif phase == "dial":                        # a month: one decimal, its month word and year
            s, word = pct(value), self.month_word(key)
        else:                                        # the turn: Mehr to Azar-Bahman
            s = pct(value) if value < 2.5 else "×" + fa(f"{value:.0f}")
            word = self.month_word(key) if w < 0.5 else HOLD_WORD
        counter_ok(s)                                # the counter is the cell-sum value of the box (air_grid.box_table), rounded
        text(im, 540, Y_COUNTER, "تهران " + s, FA_BOLD, COUNTER_PX, anchor="ms", fill=AMBER, stroke=6)
        text(im, 540, Y_MONTH, word, FA_BOLD, 60, anchor="ms")
        return im.convert("RGB")

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]) -> Image.Image:
        """The frame at t (s): size (1080, 1920) downscaled from the render (Lanczos), or the render size itself."""
        assert s == 1 and tuple(size) in ((W, H), (WR, HR)), (s, size)
        frame = self.draw_frame(0.0 if not np.isfinite(t) else t)
        return frame if tuple(size) == (WR, HR) else frame.resize((W, H), Image.LANCZOS)


def _table(box: dict):
    import pandas as pd
    t = pd.DataFrame(box["rows"])
    t.attrs["ref"] = float(box["ref"])
    t.attrs["winter"] = float(box["winter"])
    return t


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="tehran", choices=["tehran"], help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    args = ap.parse_args()
    film = AirFilm()
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"air_{args.theme}_fa"
    for old in (OUT / "social").glob(f"{base.name}_t*.png"):
        old.unlink()
    film.draw(1, 0.0).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        for t in (0.0, 1.77, 2.54, 7.15, 7.92, 23.9):   # the hook, Azar, Dey (peak), Tir, Mordad, the hold
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
