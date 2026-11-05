"""TEHRAN AND ISTANBUL, WINTER NO2 FROM SPACE: one map of Turkey and Iran, the two cities up close, one number.

The same satellite, the same method, the same winter (air_compare.py, region v1: Sentinel-5P TROPOMI OFFL NO2, qa >= 0.75,
footprints spread on a 0.02-degree grid, the NRTI granules only on days with no OFFL granule). Every number on screen comes
from compare_v1 (the pre-registered metric); the map and the close-ups are cut from the region field's cumulative maps
(Azar, Azar + Dey, the whole winter).

The look is the NO2 reel's glow (onebit_air): the NASA Blue Marble darkened to a neutral base (BASE_MIX, BASE_GAIN: land
relief and coasts visible, the orange not in the base), the NO2 added on top in onebit_air's ORANGE-to-HOT composite
(onebit_air.paint's formula), with its halo (BLOOM_K), clipped to the two countries' land. No opaque tint: low NO2 is nearly
transparent, high NO2 luminous. Turkey and Iran are lifted slightly over their neighbours (OWN_LIFT).

Deliberate differences from the reel's functions (onebit_air keeps its own scale, 2-60, and its glow is a method of its
AirFilm, so only its colours and halo constants are imported):
  - one scale here: 2-100 (1e15 molec/cm2), LINEAR (GAMMA 1.0): glow intensity proportional to the value, shared by the
    map, the close-ups and the bar;
  - the halo is divided by its plateau gain (1 + 0.9 BLOOM_K), so a core pixel of value v carries exactly intensity(v):
    the reel's own formula would clip Tehran's plateau (69-72) at the top of the glow.
The bar's swatches are the glow of a uniform field over one constant base: the median land base of Istanbul's close-up.
The colour check subtracts each pixel's own base, so it does not depend on that choice.

Frame clock (seconds; the score reads these through schedule()):
  STEP_A   0.8 - 2.3   Azar -> Azar + Dey (smooth crossfade of the cumulative fields; map and close-ups together)
  STEP_B   2.8 - 4.8   Azar + Dey -> the whole winter (the map and close-ups hold the winter from 4.8 s)
  WORD_SWITCH          the month word changes at the middle of each crossfade (آذر, آذر تا دی, آذر تا بهمن)
  17.0 - 17.5          the headline counter fades in and stays to the end; the push-in runs throughout

Layout (1080 x 1920): title 150-280; the map band 290-850; the close-ups 866-1246 (Istanbul left, Tehran right, the same
180 km square each: the two squares cannot be 480 px side by side inside x 150-930, so each is SQ = 380 px), each with its
day-mean on its name chip; the scale bar 1266; the changing word 1332 (the counter 1362 / 1432 from 17 s); the colour bar
1470-1486 with its numbers 1524, the unit line 1560, the sources line 1590 (inside the safe zone, bottom at 1600).
The bar's base is Istanbul's land median (the one base the colour check can hold for both close-ups).

    python -I src/onebit_compare.py              # the film (the driver renders the video)
    python -I src/onebit_compare.py --stills     # the stills at the times in STILLS
    python -I src/onebit_compare.py --check      # the colour check: each close-up's land box through the bar
    python -I src/onebit_compare.py --sbs        # the 23.5 s still beside the NO2 reel's 12 s frame (test image)
"""

from __future__ import annotations

import argparse
import io
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

import air  # noqa: E402
import air_grid  # noqa: E402
import onebit_air  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, SIZES, SOCIAL_CRF, fa  # noqa: E402

W, H = 1080, 1920
DURATION = 24.0                                  # s
# the clock: the crossfades of the cumulative fields (seconds), the counter (seconds)
STEP_A = (0.8, 2.3)                              # s: Azar -> Azar + Dey
STEP_B = (2.8, 4.8)                              # s: Azar + Dey -> the whole winter
T_MAP = STEP_B[1]                                # s: the winter is reached (the map and the close-ups hold it from here)
WORD_SWITCH = ((STEP_A[0] + STEP_A[1]) / 2, (STEP_B[0] + STEP_B[1]) / 2)   # s: the month word changes
T_HOLD = 17.0                                    # s: the counter appears
T_HOLD_FADE = 0.5                                # s: the counter's fade-in
STILLS = (0.0, 3.0, 8.0, 13.0, 18.0, 23.5)
VMIN, VMAX, GAMMA = 2.0, 100.0, 1.0             # 1e15 molec/cm2: one LINEAR scale for the map, the close-ups, the bar
TICKS = (25, 50, 75)                             # the bar's ticks (2 and 100 are its ends)
ORANGE, HOT = onebit_air.ORANGE, onebit_air.HOT
PAPER, SHADOW, AMBER = (tuple(int(q) for q in c) for c in (onebit_air.PAPER, onebit_air.SHADOW, onebit_air.AMBER))
BLOOM_K = onebit_air.BLOOM_K
BLOOM_SIGMA = onebit_air.BLOOM_PX / onebit_air.SS   # the reel's halo width, at the output size (1 px)
BASE_MIX, BASE_GREY, BASE_GAIN = 0.35, 0.65, 0.26  # the base: colour share, grey share, brightness (0.24-0.32 tried)
OWN_LIFT = 0.15                                  # Turkey and Iran lifted over their neighbours in the map base
PLATEAU_GAIN = 1.0 + 0.9 * BLOOM_K               # the halo of a uniform field, divided out (see the docstring)
COS0 = math.cos(math.radians(34.1))
CEN = (44.5, 34.1)                               # deg: the map's centre (lon, lat), at (540, CY)
CY = 563.0                                       # px: the map's centre height (the push-in pivot)
KX = 26.3                                        # px per degree of longitude (1000 px for Turkey and Iran)
ZOOM = 0.04                                      # the push-in: the scale at the end of the film is 1 + ZOOM
CITY = dict(istanbul=(28.98, 41.01), tehran=(51.39, 35.69))
NAME = dict(istanbul="استانبول", tehran="تهران")
TITLE = ("زمستان از فضا: تهران و استانبول", "دی‌اکسیدِ نیتروژنِ کدام بیشتر است؟")
HEADLINE = ("تهران: حدودِ ۵ برابرِ", "استانبول")  # the pre-registered rounding down of 5.82 (one constant, keep it)
SOURCES = "منبع: Sentinel-5P (ESA/Copernicus)؛ تصویر: NASA Blue Marble"
Y_TITLE = (196, 262)
SQ = 380                                         # px: a close-up's side
HALF_KM = 90.0                                   # km: a close-up's half side (a 180 km square, the same km per pixel)
SQ_X = dict(istanbul=150, tehran=550)            # px: the close-ups' left edges (Tehran's right edge at 930)
SQ_Y = 866                                       # px: their top edge
Y_SCALE, Y_WORD = 1266, 1332                     # px: the shared scale bar, the changing word
Y_CNT = (1342, 1412)                             # px: the counter's two baselines
Y_BAR, Y_BAR_NUM, Y_UNIT, Y_SOURCES = 1450, 1498, 1540, 1576
BAR_X = (150, 880)
MARGIN = 0.12                                    # deg: the Blue Marble tile's margin around a close-up
BOX_DEG = 0.15                                   # deg: the land box checked by --check (the metric's box)
TOL = 0.10                                       # the --check tolerance
DATA = air.DATA / "compare"
RFIELD = DATA / "region_winter_v1.npz"
BM_WORLD = DATA / "bluemarble_world.jpg"
NO2_REEL = OUT / "social" / "air_tehran_fa_voice_reel.mp4"   # read only: the test image's comparison frame
GIBS = ("https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0"
        "&LAYERS=BlueMarble_ShadedRelief_Bathymetry&STYLES=&CRS=EPSG:4326&FORMAT=image/jpeg")
WORLD = dict(lon0=10.0, lon1=80.0, lat0=-42.0, lat1=65.0, w=2400)


def smoothstep(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def font(path, px: int):
    from PIL import ImageFont
    return ImageFont.truetype(str(path), px)


def width(s: str, path, px) -> float:
    return font(path, px).getlength(s, direction="rtl", language="fa")


def text(im, x, y, s, path, px, anchor="ms", fill=PAPER, stroke=4):
    f = font(path, px)
    ImageDraw.Draw(im).text((x, y), s, font=f, fill=fill, anchor=anchor, direction="rtl", language="fa",
                            stroke_width=stroke, stroke_fill=SHADOW)
    return f.getlength(s, direction="rtl", language="fa")


def intensity(raw):
    """The one colour scale (the map, the close-ups and the bar): NO2 (1e15 molec/cm2) to 0-1, linear (GAMMA 1)."""
    return np.clip((np.asarray(raw, float) - VMIN) / (VMAX - VMIN), 0, 1) ** GAMMA


def dim_base(rgb: np.ndarray) -> np.ndarray:
    """The neutral dark base of the Blue Marble (colour and grey mixed, scaled down): float RGB 0-255."""
    grey = rgb.mean(axis=-1, keepdims=True)
    return np.clip((BASE_MIX * rgb + BASE_GREY * grey) * BASE_GAIN, 0, 255).astype(np.float32)


def luminance(a: np.ndarray) -> np.ndarray:
    """Rec. 601 luminance of float RGB."""
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def halo(i: np.ndarray, sigma: float) -> np.ndarray:
    """onebit_air's halo: i + BLOOM_K * (blurred i * 0.9), divided by its plateau gain, so a plateau keeps exactly i."""
    from scipy import ndimage
    bloom = ndimage.gaussian_filter(i, sigma) * 0.9
    return np.clip(i + BLOOM_K * bloom, 0, PLATEAU_GAIN) / PLATEAU_GAIN


def paint(base: np.ndarray, g: np.ndarray) -> np.ndarray:
    """onebit_air.draw_frame's composite: base + g * (orange + (hot - orange) * g), float RGB 0-255."""
    return base + g[..., None] * (ORANGE + (HOT - ORANGE) * g[..., None])


def to_rgb(a: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(a + 0.5, 0, 255).astype(np.uint8), "RGB")


def bar_x(v: float) -> float:
    """Output px of value v on the colour bar: linear in intensity, so the colour is linear along the bar."""
    return BAR_X[0] + float(intensity(v)) * (BAR_X[1] - BAR_X[0])


def fetch_bm(path: Path, lon0: float, lon1: float, lat0: float, lat1: float, w: int) -> Path:
    """NASA Blue Marble (shaded relief and bathymetry) for a box, from NASA GIBS (keyless WMS), cached in data/air/compare."""
    if path.exists():
        return path
    import urllib.request
    h = round(w * (lat1 - lat0) / (lon1 - lon0))
    url = f"{GIBS}&BBOX={lat0},{lon0},{lat1},{lon1}&WIDTH={w}&HEIGHT={h}"
    with urllib.request.urlopen(url, timeout=300) as r:
        im = Image.open(io.BytesIO(r.read())).convert("RGB")
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, quality=92)
    return path


def sample_bm(arr: np.ndarray, box: dict, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """The Blue Marble raster sampled at lon, lat (bilinear), RGB float."""
    from scipy import ndimage
    h, w = arr.shape[:2]
    dx, dy = (box["lon1"] - box["lon0"]) / w, (box["lat1"] - box["lat0"]) / h
    fi = (lon - box["lon0"]) / dx - 0.5
    fj = (box["lat1"] - lat) / dy - 0.5
    return np.stack([ndimage.map_coordinates(arr[..., k], [fj, fi], order=1, mode="nearest")
                     for k in range(3)], -1)


def sample_field(arr: np.ndarray, lon_g: np.ndarray, lat_g: np.ndarray, lon, lat) -> np.ndarray:
    """A cell field (lon and lat ascending, cell centres) sampled at lon, lat (bilinear); zero outside the grid."""
    from scipy import ndimage
    fi = (lon - lon_g[0]) / (lon_g[1] - lon_g[0])
    fj = (lat - lat_g[0]) / (lat_g[1] - lat_g[0])
    out = ndimage.map_coordinates(arr, [fj, fi], order=1, mode="constant", cval=0.0)
    inside = (fi > -0.5) & (fi < arr.shape[1] - 0.5) & (fj > -0.5) & (fj < arr.shape[0] - 0.5)
    return np.where(inside, out, 0.0)


def ascending(a: np.ndarray, lat: np.ndarray, axis: int):
    """Flip an array along its latitude axis when the latitudes descend."""
    if lat[0] > lat[-1]:
        return np.flip(a, axis=axis), lat[::-1]
    return a, lat


def water_mask(rgb: np.ndarray, opening: bool = True) -> np.ndarray:
    from scipy import ndimage
    water = (rgb[..., 2] > rgb[..., 0] + 25) & (rgb[..., 2] > rgb[..., 1] - 8)
    return ndimage.binary_opening(water, iterations=1) if opening else water


def day_means() -> dict:
    """The day-means on screen (compare_v1, the pre-registered metric): Tehran's and Istanbul's land, in 1e15 molec/cm2."""
    import json
    s = json.loads((DATA / "compare_v1.json").read_text(encoding="utf-8"))["summary"]["primary"]
    return {"tehran": float(s["tehran"]["day_mean"]), "istanbul": float(s["istanbul_land"]["day_mean"])}


def tile_lonlat(c: str):
    """The close-up's pixel centres (lon, lat) and its half sides (deg): a square of 2 * HALF_KM."""
    clon, clat = CITY[c]
    hl = HALF_KM / (111.32 * math.cos(math.radians(clat)))      # deg of longitude
    hb = HALF_KM / 111.32                                       # deg of latitude
    yy, xx = np.mgrid[0:SQ, 0:SQ].astype(np.float64)
    lon = clon + (xx + 0.5 - SQ / 2) / SQ * 2 * hl
    lat = clat - (yy + 0.5 - SQ / 2) / SQ * 2 * hb
    return lon, lat, hl, hb


class Film:
    """The film: draw(1, t) is the frame at t seconds, 1080 x 1920."""

    def __init__(self):
        self.checks()
        self.L = type("L", (), {"end": DURATION})()     # the length onebit.video reads
        z = np.load(RFIELD)
        lat_r = z["lat"]
        self.lon_r = z["lon"]
        self.inside, self.lat_r = ascending(z["inside"].astype(np.float32), lat_r, 0)
        self.fields = {}
        for k in ("azar", "azar_dey", "winter"):
            f, self.lat_r = ascending(z[k].astype(np.float32), lat_r, 0)
            self.fields[k] = f
        self.box = dict(lon0=WORLD["lon0"], lon1=WORLD["lon1"], lat0=WORLD["lat0"], lat1=WORLD["lat1"])
        self.bm = np.asarray(Image.open(fetch_bm(BM_WORLD, WORLD["lon0"], WORLD["lon1"], WORLD["lat0"], WORLD["lat1"],
                                                 WORLD["w"])).convert("RGB"), np.float32)
        self.lon_f, self.lat_f = self.frame_lonlat()
        self.base, self.water, self.inside_f = self.make_base()
        self.G = [self.make_map_glow(k) for k in ("azar", "azar_dey", "winter")]
        self.tile = {c: self.make_tile(c) for c in CITY}
        self.tg = {c: [self.make_tile_glow(c, k) for k in ("azar", "azar_dey", "winter")] for c in CITY}
        ist = self.tile["istanbul"]
        self.bar_base = np.median(ist["base"][ist["land"]], axis=0).astype(np.float32)   # the one base of the bar
        self.static = self.make_static()

    # ── checks ──

    def checks(self) -> None:
        assert VMIN == 2.0 and VMAX == 100.0 and GAMMA == 1.0
        assert 0 < STEP_A[0] < STEP_A[1] <= STEP_B[0] < STEP_B[1] <= T_HOLD < DURATION == 24.0
        assert STEP_A[1] <= STEP_B[0], "the crossfades do not overlap"
        for s in HEADLINE:
            assert width(s, FA_BOLD, 96) <= 860, ("headline line too wide", s)
        for s in TITLE:
            assert width(s, FA_BOLD, 58) <= 960, ("title line too wide", s)
        assert "۶" not in HEADLINE[0] and "۵" in HEADLINE[0], "the headline is the rounded-down 5"
        assert SQ_X["istanbul"] >= 150 and SQ_X["tehran"] + SQ <= 930 and SQ_X["istanbul"] + SQ < SQ_X["tehran"]
        assert abs(float(intensity(np.array([VMIN]))[0])) < 1e-12 and abs(float(intensity(np.array([VMAX]))[0]) - 1) < 1e-12
        assert abs(float(intensity(np.array([70.0]))[0]) - 68 / 98) < 1e-9, "linear: intensity is proportional to the value"
        assert abs(float(halo(np.ones((5, 5)), 1.0)[2, 2]) - 1.0) < 1e-9, "the plateau keeps its value"

    # ── geometry ──

    def frame_lonlat(self):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
        lon = CEN[0] + (xx + 0.5 - 540.0) / KX
        lat = CEN[1] - (yy + 0.5 - CY) * COS0 / KX
        return lon, lat

    def xy(self, lon: float, lat: float, s: float = 1.0):
        """The frame position of lon, lat under the push-in scale s (pivot (540, CY))."""
        x = 540.0 + (lon - CEN[0]) * KX
        y = CY - (lat - CEN[1]) * KX / COS0
        return 540.0 + (x - 540.0) * s, CY + (y - CY) * s

    # ── the layers ──

    def make_base(self):
        """The dark neutral base over the whole frame, the land relief kept, thin country outlines; Turkey and Iran lifted."""
        lon, lat = self.lon_f, self.lat_f
        rgb = sample_bm(self.bm, self.box, lon, lat)
        water = water_mask(rgb)
        inside_f = sample_field(self.inside, self.lon_r, self.lat_r, lon, lat)
        inside = inside_f > 0.5
        base = dim_base(rgb) * (1.0 + OWN_LIFT * np.clip(inside_f, 0, 1))[..., None].astype(np.float32)
        base = np.clip(base, 0, 255).astype(np.float32)
        im = to_rgb(base)
        d = ImageDraw.Draw(im)
        import shapefile
        shp = air_grid.NE / "ne_10m_admin_0_countries.shp"
        r = shapefile.Reader(str(shp))
        bbox = (lon.min(), lat.min(), lon.max(), lat.max())
        for sh, rec in zip(r.iterShapes(), r.iterRecords()):
            x0, y0, x1, y1 = sh.bbox
            if x1 < bbox[0] or x0 > bbox[2] or y1 < bbox[1] or y0 > bbox[3]:
                continue
            pts = np.asarray(sh.points, float)
            starts = list(sh.parts) + [len(pts)]
            own = rec["ADMIN"] in ("Turkey", "Iran")
            for a, b in zip(starts[:-1], starts[1:]):
                q = pts[a:b]
                px = 540.0 + (q[:, 0] - CEN[0]) * KX
                py = CY - (q[:, 1] - CEN[1]) * KX / COS0
                d.line(list(zip(px.tolist(), py.tolist())), fill=(214, 220, 228) if own else (84, 92, 102),
                       width=2 if own else 1, joint="curve")
        out = np.asarray(im, np.float32)
        return out, water, inside

    def make_map_glow(self, key: str) -> np.ndarray:
        """A field as the map's glow, 0-1: the one scale, the halo, over Turkey's and Iran's land only."""
        from scipy import ndimage
        i = intensity(sample_field(self.fields[key], self.lon_r, self.lat_r, self.lon_f, self.lat_f))
        keep = np.clip(ndimage.gaussian_filter((self.inside_f & ~self.water).astype(np.float32), 1.0), 0, 1)
        return (halo(i, BLOOM_SIGMA) * keep).astype(np.float32)

    def country_cover(self, lon0: float, lon1: float, lat0: float, lat1: float) -> np.ndarray:
        """The share of each close-up pixel that is Turkey or Iran (4x supersampled Natural Earth polygons, area-averaged)."""
        import shapefile
        n = SQ * 4
        im = Image.new("L", (n, n), 0)
        d = ImageDraw.Draw(im)
        r = shapefile.Reader(str(air_grid.NE / "ne_10m_admin_0_countries.shp"))
        for sh, rec in zip(r.iterShapes(), r.iterRecords()):
            if rec["ADMIN"] not in ("Turkey", "Iran"):
                continue
            pts = np.asarray(sh.points, float)
            starts = list(sh.parts) + [len(pts)]
            for a, b in zip(starts[:-1], starts[1:]):
                q = pts[a:b]
                px = (q[:, 0] - lon0) / (lon1 - lon0) * n
                py = (lat1 - q[:, 1]) / (lat1 - lat0) * n
                d.polygon(list(zip(px.tolist(), py.tolist())), fill=255)
        return np.asarray(im.resize((SQ, SQ), Image.BOX), np.float32) / 255.0

    def make_tile(self, c: str) -> dict:
        """One close-up: the Blue Marble on the dark neutral base (land and sea), the land share of each pixel, the coordinates."""
        from scipy import ndimage
        lon, lat, hl, hb = tile_lonlat(c)
        clon, clat = CITY[c]
        box = dict(lon0=clon - hl - MARGIN, lon1=clon + hl + MARGIN, lat0=clat - hb - MARGIN, lat1=clat + hb + MARGIN)
        path = fetch_bm(DATA / f"bluemarble_tile_{c}_v4.jpg", box["lon0"], box["lon1"], box["lat0"], box["lat1"], 1000)
        tile = np.asarray(Image.open(path).convert("RGB"), np.float32)
        rgb = sample_bm(tile, box, lon, lat)
        base = dim_base(rgb)
        water = water_mask(rgb, opening=False).astype(np.float32)
        wsoft = ndimage.gaussian_filter(water, 0.6)
        cov = self.country_cover(clon - hl, clon + hl, clat - hb, clat + hb) * np.clip(1 - wsoft, 0, 1)
        return dict(base=base, cov=cov.astype(np.float32), land=cov > 0.5, lon=lon, lat=lat)

    def make_tile_glow(self, c: str, key: str) -> np.ndarray:
        """One close-up's glow for one cumulative field, 0-1, over its land only."""
        tl = self.tile[c]
        i = intensity(sample_field(self.fields[key], self.lon_r, self.lat_r, tl["lon"], tl["lat"]))
        return (halo(i, BLOOM_SIGMA) * tl["cov"]).astype(np.float32)

    def make_static(self) -> Image.Image:
        """Title, colour bar with its numbers and unit line, the sources line, the close-up frames, names, the scale bar."""
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for s, y in zip(TITLE, Y_TITLE):
            text(im, 540, y, s, FA_BOLD, 58, stroke=5)
        x0, x1 = BAR_X
        d = ImageDraw.Draw(im)
        for xx in range(x0, x1 + 1):
            i = (xx - x0) / (x1 - x0)                      # linear in intensity, as bar_x() and the ticks
            v = VMIN + (VMAX - VMIN) * i ** (1 / GAMMA)
            col = np.clip(paint(self.bar_base, np.full((1, 1), i, np.float32))[0, 0] + 0.5, 0, 255)
            d.line([(xx, Y_BAR), (xx, Y_BAR + 16)], fill=tuple(int(q) for q in col) + (255,))
        d.rectangle([x0, Y_BAR, x1, Y_BAR + 16], outline=PAPER, width=2)
        for v in TICKS:
            xt = bar_x(v)
            d.line([(xt, Y_BAR + 16), (xt, Y_BAR + 24)], fill=PAPER, width=2)
            text(im, xt, Y_BAR_NUM, fa(v), FA_TEXT, 32, stroke=3)
        text(im, x0, Y_BAR_NUM, fa(int(VMIN)), FA_TEXT, 32, stroke=3)
        text(im, x1, Y_BAR_NUM, fa(int(VMAX)), FA_TEXT, 32, stroke=3)
        # the unit, with the exponent raised (the font has no superscript digits), as onebit_air
        px, pe = 30, 22
        fa_, fe_ = font(FA_TEXT, px), font(FA_TEXT, pe)
        A, N, E, C = "دی‌اکسیدِ نیتروژن، ", "۱۰", "۱۵", " مولکول بر سانتی‌مترِ مربع"
        wA, wN, wC = (fa_.getlength(t, direction="rtl", language="fa") for t in (A, N, C))
        wE = fe_.getlength(E, direction="rtl", language="fa")
        total = wA + wN + wE + wC
        x_r = 540 + total / 2
        assert x_r <= 930 and x_r - total >= 150, ("unit line", x_r, total)
        text(im, x_r - wA / 2, Y_UNIT, A, FA_TEXT, px, stroke=3)
        text(im, x_r - wA - wN / 2, Y_UNIT, N, FA_TEXT, px, stroke=3)
        text(im, x_r - wA - wN - wE / 2, Y_UNIT - 0.42 * px, E, FA_TEXT, pe, stroke=2)
        text(im, x_r - wA - wN - wE - wC / 2, Y_UNIT, C, FA_TEXT, px, stroke=3)
        text(im, 540, Y_SOURCES, SOURCES, FA_TEXT, 28, stroke=3)
        assert width(SOURCES, FA_TEXT, 28) <= 780, ("sources line too wide", width(SOURCES, FA_TEXT, 28))
        d = ImageDraw.Draw(im)
        means = day_means()
        for c in CITY:
            x0 = SQ_X[c]
            d.rectangle([x0 - 1, SQ_Y - 1, x0 + SQ, SQ_Y + SQ], outline=PAPER, width=2)
            f = font(FA_BOLD, 40)
            label = f"{NAME[c]} {fa(f'{means[c]:.1f}')}"
            tw = f.getlength(label, direction="rtl", language="fa")
            assert tw <= SQ - 28, ("name chip too wide", label, tw)
            lx, ly = x0 + 14, SQ_Y + 14
            d.rounded_rectangle([lx, ly, lx + tw + 24, ly + 52], radius=12, fill=(8, 10, 14, 215))
            text(im, lx + tw / 2 + 12, ly + 40, label, FA_BOLD, 40, stroke=3)
        px_km = SQ / (2 * HALF_KM)                        # px per km (the tiles' scale)
        bx0 = 540 - 5 * px_km
        d.line([(bx0, Y_SCALE), (bx0 + 10 * px_km, Y_SCALE)], fill=PAPER, width=4)
        d.line([(bx0, Y_SCALE - 8), (bx0, Y_SCALE + 8)], fill=PAPER, width=3)
        d.line([(bx0 + 10 * px_km, Y_SCALE - 8), (bx0 + 10 * px_km, Y_SCALE + 8)], fill=PAPER, width=3)
        text(im, bx0 + 10 * px_km + 20, Y_SCALE + 8, "۱۰ کیلومتر", FA_TEXT, 26, anchor="ls", stroke=3)
        return im

    # ── time ──

    def weights(self, t: float) -> tuple:
        """The cumulative fields at t: Azar, Azar + Dey, the whole winter (weights sum to 1)."""
        a = smoothstep((t - STEP_A[0]) / (STEP_A[1] - STEP_A[0]))
        b = smoothstep((t - STEP_B[0]) / (STEP_B[1] - STEP_B[0]))
        return 1 - a, a - b, b

    def word_at(self, t: float) -> str:
        N = air.JALALI_NAMES
        if t < WORD_SWITCH[0]:
            return f"{N[8]} {fa(1404)}"
        if t < WORD_SWITCH[1]:
            return f"{N[8]} تا {N[9]} {fa(1404)}"
        return f"{N[8]} تا {N[10]} {fa(1404)}"

    def schedule(self) -> dict:
        """The film's clock, for the score: the crossfades, the month changes, the counter, the stills."""
        return dict(step_a=STEP_A, step_b=STEP_B, build=(0.0, T_MAP), month_changes=WORD_SWITCH,
                    hold=T_HOLD, counter_fade=(T_HOLD, T_HOLD + T_HOLD_FADE), end=DURATION, stills=STILLS)

    # ── the frame ──

    def draw_frame(self, t: float) -> Image.Image:
        t = min(max(t, 0.0), DURATION)
        s = 1.0 + ZOOM * t / DURATION                  # the push-in
        w = self.weights(t)
        g = sum(wk * Gk for wk, Gk in zip(w, self.G))
        full = np.clip(paint(self.base, g) + 0.5, 0, 255).astype(np.uint8)
        im = Image.fromarray(full, "RGB").transform(
            (W, H), Image.AFFINE, (1 / s, 0, 540 - 540 / s, 0, 1 / s, CY - CY / s), resample=Image.BILINEAR)
        im = im.convert("RGBA")
        for c in CITY:
            gt = sum(wk * Gk for wk, Gk in zip(w, self.tg[c]))
            sq = paint(self.tile[c]["base"], gt)
            im.paste(to_rgb(sq), (SQ_X[c], SQ_Y))
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        for c in CITY:                                 # the leader lines, under the static layer
            x, y = self.xy(*CITY[c], s=s)
            d.line([(x, y), (SQ_X[c] + SQ / 2, SQ_Y - 2)], fill=PAPER[:3] + (170,), width=2)
        for c in CITY:
            x, y = self.xy(*CITY[c], s=s)
            d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=PAPER, outline=SHADOW, width=2)
            f = font(FA_BOLD, 34)
            tw = f.getlength(NAME[c], direction="rtl", language="fa")
            lx, ly = x + 16, y - 52
            d.rounded_rectangle([lx, ly, lx + tw + 22, ly + 46], radius=10, fill=(8, 10, 14, 215))
            text(ov, lx + tw / 2 + 11, ly + 36, NAME[c], FA_BOLD, 34, stroke=2)
        im.alpha_composite(ov)
        im.alpha_composite(self.static)
        if t < T_HOLD:
            text(im, 540, Y_WORD, self.word_at(t), FA_BOLD, 60)
        else:
            a = smoothstep((t - T_HOLD) / T_HOLD_FADE)
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            text(lay, 540, Y_CNT[0], HEADLINE[0], FA_BOLD, 96, fill=AMBER, stroke=6)
            text(lay, 540, Y_CNT[1], HEADLINE[1], FA_BOLD, 76, fill=AMBER, stroke=6)
            arr = np.asarray(lay).copy()
            arr[..., 3] = (arr[..., 3].astype(np.float32) * a).astype(np.uint8)
            im.alpha_composite(Image.fromarray(arr, "RGBA"))
        return im.convert("RGB")

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]) -> Image.Image:
        assert s == 1 and tuple(size) == (W, H), (s, size)
        return self.draw_frame(DURATION if not np.isfinite(t) else min(max(t, 0.0), DURATION))

    # ── the colour check ──

    def colour_check(self) -> bool:
        """Each close-up's land box (+-0.15 deg around the city centre) in the end frame, inverted pixel by pixel: each
        pixel's own base is subtracted, the glow increment is inverted through the composite (the nearest g of a 401-step
        grid, all three channels), divided by the land share, and the land mean is compared with the mean of the region
        field (winter) over the same land cells. Tolerance 10 %. Also the five-times measurement: the mean glow-only
        luminance of each box (frame minus its own base), and the ratio Tehran / Istanbul."""
        frame = np.asarray(self.draw_frame(DURATION), np.float64)
        z = np.load(RFIELD)
        lat_r, lon_r = z["lat"], z["lon"]
        grid = np.linspace(0.0, 1.0, 401)
        inc = paint(np.zeros(3), grid).astype(np.float64)              # (401, 3): the glow increment of each g
        ok_all = True
        glow_lum = {}
        for c in CITY:
            lon, lat, hl, hb = tile_lonlat(c)
            hx = int(round(BOX_DEG / (2 * hl / SQ)))
            hy = int(round(BOX_DEG / (2 * hb / SQ)))
            cy, cx = SQ // 2, SQ // 2
            sl = (slice(SQ_Y + cy - hy, SQ_Y + cy + hy), slice(SQ_X[c] + cx - hx, SQ_X[c] + cx + hx))
            sub = (slice(cy - hy, cy + hy), slice(cx - hx, cx + hx))
            tl = self.tile[c]
            landm = tl["land"][sub]
            cov = np.maximum(tl["cov"][sub], 1e-6).astype(np.float64)
            base = tl["base"][sub].astype(np.float64)
            p = frame[sl]
            dv = (p - base).reshape(-1, 3)                              # each pixel's own glow increment
            d2 = ((dv[:, None, :] - inc[None]) ** 2).sum(-1)
            g_hat = grid[d2.argmin(1)].reshape(landm.shape) / cov        # the intensity, the land share divided out
            g_hat = np.clip(g_hat, 0, 1)
            v_hat = VMIN + (VMAX - VMIN) * g_hat ** (1 / GAMMA)
            rendered = float(v_hat[landm].mean())
            lo, la = lon[sub].reshape(-1), lat[sub].reshape(-1)
            wf = sample_field(z["winter"].astype(np.float32), lon_r, lat_r, lo, la)
            inside = sample_field(z["inside"].astype(np.float32), lon_r, lat_r, lo, la) > 0.5
            sel = inside & landm.reshape(-1) & (wf > 0)
            expected = float(wf[sel].mean())
            dev = abs(rendered - expected) / expected
            good = dev <= TOL
            ok_all &= bool(good)
            glow_lum[c] = float(luminance(p - base)[landm].mean())
            centre = float(sample_field(z["winter"].astype(np.float32), lon_r, lat_r,
                                        np.array([CITY[c][0]]), np.array([CITY[c][1]]))[0])
            print(f"box {c}: rendered land mean {rendered:.1f}; region field {expected:.1f} on {int(sel.sum())} land cells "
                  f"(centre cell {centre:.1f}); deviation {100 * dev:.1f} % -> {'PASS' if good else 'FAIL'} "
                  f"({100 * TOL:.0f} % limit)", flush=True)
        ratio = glow_lum["tehran"] / glow_lum["istanbul"]
        print(f"five-times: glow-only luminance tehran {glow_lum['tehran']:.2f}, istanbul {glow_lum['istanbul']:.2f} "
              f"(levels); ratio {ratio:.2f}", flush=True)
        print("colour key:", "PASS" if ok_all else "FAIL", flush=True)
        return ok_all

def sbs(film: Film) -> Path:
    """The test image: the 23.5 s still beside the NO2 reel's 12 s frame (the reel is read, never written)."""
    with tempfile.TemporaryDirectory() as td:
        ref = Path(td) / "no2_12s.png"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", "12", "-i", str(NO2_REEL), "-frames:v", "1",
                        str(ref)], check=True)
        other = Image.open(ref).convert("RGB")
        this = film.draw(1, 23.5)
        out = Image.new("RGB", (2 * 540 + 40, 960 + 60), (12, 14, 18))
        out.paste(this.resize((540, 960), Image.LANCZOS), (0, 60))
        out.paste(other.resize((540, 960), Image.LANCZOS), (580, 60))
        d = ImageDraw.Draw(out)
        d.text((20, 18), "this film, 23.5 s", fill=(240, 240, 240))
        d.text((600, 18), "NO2 reel, 12 s", fill=(240, 240, 240))
        p = OUT / "social" / "compare_tehran_istanbul_fa_sidebyside.png"
        p.parent.mkdir(parents=True, exist_ok=True)
        out.save(p)
        return p


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true", help="stills only, no video")
    ap.add_argument("--check", action="store_true", help="the colour check: each close-up's land box through the bar")
    ap.add_argument("--sbs", action="store_true", help="the side-by-side test image (23.5 s beside the NO2 reel's 12 s)")
    args = ap.parse_args()
    film = Film()
    print("schedule", film.schedule(), flush=True)
    if args.check:
        film.colour_check()
        return
    if args.sbs:
        print("saved", sbs(film), flush=True)
        return
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / "compare_tehran_istanbul_fa"
    if args.stills:
        for t in STILLS:
            p = f"{base}_t{t:04.1f}.png"
            film.draw(1, t).save(p)
            print("saved", p, flush=True)
        return
    film.draw(1, 0.0).save(f"{base}_cover.png", optimize=True)
    import onebit
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
