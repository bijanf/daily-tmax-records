"""THE HAMOUN LAKES FROM SPACE (Sistan, on the Iran-Afghanistan border): the late-spring water of every
year 1985-2026 from Landsat, measured at 30 m, and one true-colour picture a year for a phone.

Measured data only. Landsat Collection 2 Level-2 surface reflectance (USGS), read from Microsoft's Planetary
Computer with its anonymous token (no account; the helpers of get_urmia.py); JRC Global Surface Water
(Pekel et al. 2016, v1.4, 1984-2021): the extent of any water (storage.googleapis.com) and the Monthly Water
History (the JRC open-data server jeodpp.jrc.ec.europa.eu, keyless); the Natural Earth 10 m admin-0
countries (naciscdn.org) for the Iran / Afghanistan split.

THE LAKES (the region the areas count). JRC's extent of any water 1984-2021 on its 0.00025-degree grid,
opened with a disk of 3 pixels (about 80 m: cuts river channels and canals narrower than about 160 m), its
largest connected piece (Hamoun-e Puzak, Hamoun-e Sabari and Hamoun-e Hirmand with the Puzak delta, about
4,300 km2), grown back by 4 pixels inside the extent (the shore fringe returns, the channels do not). This
leaves out the Chah-nimeh reservoirs (filled from the Sistan river; not part of the Hamoun), the Helmand,
Farah Rud and Harut Rud channels and small ponds. Water outside the lakes is not counted.

WHEN. Late spring: 1 May to 15 June (11 Ordibehesht to 25 Khordad), when the spring flood has arrived and
before the summer's heat and 120-day wind dry the shallow lakes. A year with fewer than 2 accepted passes in
that window is widened to 15 April - 30 June (recorded in the table: window "wide").

ONE PATH SEES IT ALL. WRS-2 path 157 rows 038 and 039, taken in the same pass (seconds apart), together cover
all of the lakes; the areas use only these passes, so no area joins two dates. A pass is the two rows of
one date and satellite, mosaicked on one fixed 30-m UTM 41N grid (EPSG:32641, aligned to Landsat's): row 038
where it has data, else row 039. Passes whose two scenes average more than 60 % scene cloud are not read.

PIXELS. Valid: all of green, red, NIR, SWIR1 have data and QA_PIXEL's fill bit is clear (Landsat 7 after its
scan-line corrector failed on 31 May 2003 leaves stripe gaps: not valid). Clear: valid and none of the
QA_PIXEL bits for dilated cloud, cirrus, cloud, cloud shadow or snow is set, or water-like whatever the bits
say: SWIR1 < 0.10 and MNDWI > 0.3 (QA_PIXEL flags the Hamoun's very turbid flood water as cloud and shadow:
about 150 km2 of the lakes on the cloud-free 29 May 2020; no cloud, bright land or salt has a SWIR1 that
low; logged per pass as "rescued"). Surface reflectance = DN x 0.0000275 - 0.2; below 0.0001 (dark water
over-corrected) it is set to 0.0001 before the indices.

WATER RULES (all computed on every clear pixel; the calibration against JRC picks one, see hamoun.py):
    mndwi0        MNDWI > 0              MNDWI = (green - SWIR1) / (green + SWIR1)
    mndwi01       MNDWI > 0.1
    mndwi0_nir10  MNDWI > 0 and NIR < 0.10
    mndwi0_nir15  MNDWI > 0 and NIR < 0.15
    ndwi0         NDWI > 0               NDWI = (green - NIR) / (green + NIR)
    mndwi0_swir10 MNDWI > 0 and SWIR1 < 0.10
    mndwi0_swir15 MNDWI > 0 and SWIR1 < 0.15
The last two were added after the first look at the 30-m pixels: the Hamoun's flood water is often very
turbid (green, red and NIR reflectance 0.2-0.3, so NIR caps and NDWI miss it, and so does JRC in places),
but it still absorbs SWIR1 (0.03-0.09); damp salt and mud on a drying bed pass MNDWI > 0 (and > 0.1) but keep
SWIR1 near 0.18-0.30. A SWIR1 cap separates the two where an NIR cap cannot.
Also counted: green plants, NDVI = (NIR - red) / (NIR + red) > 0.3 (reedbeds and fields), and MNDWI > 0 with
NDVI > 0.2 (water with plants in it, counted as water by MNDWI).

AREA OF A PASS (km2). The lakes are cut into strata: 0.1 x 0.1 degree tiles, each split by the Natural Earth
border into its Iran and Afghanistan parts. A stratum's area = its water share of its clear pixels x its
pixels x 0.0009 km2; a stratum with less than 20 % of its pixels clear takes the pass's overall water share
(so a cloud or a stripe does not shrink the lake, and a cloud over a dry part does not lend it the wet
part's share). The pass's area is the sum; Iran and Afghanistan are the sums of their strata.

ACCEPTED PASS: at least 97 % of the lakes valid and 85 % clear (Landsat 7 after 31 May 2003: 65 % valid,
60 % clear); strata with less than 20 % clear hold at most 5 % of the lakes; registered: its SWIR1 over a
land window (Zabol, Zahak, Kuh-e Khwaja: 61.38-61.78 E, 30.84-31.12 N) is shifted by at most 1 pixel (30 m)
in each direction from the reference pass (Landsat 8, 1 June 2021, Tier 1), by phase correlation of the
gradient images (measurable when half the window is clear and the correlation peak is at least 20 times its
noise; a Tier-1 pass whose shift cannot be measured is kept); a Tier-2 pass (geometry not assured: the
Tier-2 trap of Karaj and Latyan) at most 0.5 pixel, and its shift must be measurable. Passes in EXCLUDE are left out of every count, with the reason there.
THE YEAR'S AREA: the median over its accepted passes in its window (per rule; the low and high pass too).

JRC CHECK (calibration, years up to 2021). For each pass, JRC's Monthly Water History of the pass's month on
the same 30-m grid (nearest): on the pixels that are clear in the pass and observed by JRC that month, JRC's
water and each rule's water, both scaled to the lakes with the same strata. Stored per stratum, with the
pixels on which a rule and JRC agree on water (commission and omission follow).

PICTURES (true colour, --colour). One fixed EPSG:4326 grid for a 1080-pixel-wide phone picture of the whole
system: 60.69-62.31 E, 30.2504-31.85 N, 0.0015 deg east-west by 0.00129 deg north-south (about 143 m by
143 m: the pixels are square on the ground; no aspect correction is needed), 1080 x 1240 pixels. Red, green
and blue surface reflectance are read from the COGs' 120-m overview (average) with QA_PIXEL at 30 m pooled
over the 4 x 4 blocks (a block with any dilated cloud, cirrus, cloud or shadow is cloudy, unless it is
water-like at 120 m: SWIR1 < 0.10 and MNDWI > 0.3, read from the same overview), only where all
three bands have data, two overview pixels in from a whole scene's edge (one from a stripe gap's edge on
Landsat 7 after 31 May 2003), then bilinear to the grid. Each pass is matched in tone to the year's clearest
whole pass (per band, least-squares gain and offset over the land both see cloud-free: the dates differ in
haze and sun; without it the median changes tone wherever a pass has a gap and draws stripes). Per year:
the accepted path-157 passes of its window (at most 6, the clearest over the lakes), each pass's two rows
mosaicked; layer 1 (strict) = the per-pixel median over the whole passes (not Landsat 7 after 31 May 2003)
of their cloud-free values, where all of them see; layer 2 (loose) = the median over all of them incl. the
striped ones, where any sees; inside the lakes (grown by 2 picture pixels), where no pass is cloud-free but
at least 3 see, the median of all their values (salt and bright mud can be flagged as cloud in every pass:
a real cloud does not stay over one place in three passes), or where exactly 2 see and their values agree
within 0.04 reflectance in every band (a cloud does not look the same in two passes days apart); otherwise
the lake stays unseen. Then, for
the land only (never inside the lakes, where a different date would draw a seam in the water), the
neighbouring paths' scenes (158/038, 158/039, 156/038, 156/039: Tier 1, at most 60 % cloud, the 4 least
cloudy each) fill what path 157 does not see. hamoun.py joins the layers with matched tones.

    data/hamoun/roi.npz              the lakes and strata on JRC's grid; the 30-m UTM grid; the picture grid
    data/hamoun/stac/<year>.json     the STAC items of 15 April - 30 June over the picture box
    data/hamoun/jrc/<yyyy_mm>.npz    JRC's monthly water on the 30-m grid (0 no data, 1 not water, 2 water)
    data/hamoun/reference.npz        the reference pass's SWIR1 over the registration window
    data/hamoun/scenes/<pass>.json   per pass: its scenes, shares, shift, the QA cloud and snow flags on the
                                     lakes, and per stratum the pixel counts
    data/hamoun/maps/<pass>.npz      per pass on the picture grid, percent (255 none): seen, clear, each
                                     rule's water of the clear, JRC's water of the observed, green plants
    data/hamoun/colour_<year>.npz    the year's true-colour layers on the picture grid   (--colour)
    data/hamoun/area_spring.csv      per year: window, passes, the median area per rule, Iran/Afghanistan

    python -I src/get_hamoun.py                        # scan every year, then the pictures (cached; about
                                                       # 35 min for the 183 passes and 20 for the pictures)
    python -I src/get_hamoun.py --years 2020 2021      # some years only
    python -I src/get_hamoun.py --colour [years]       # the pictures only (needs the scans)
"""

from __future__ import annotations

import functools
import json
import math
import sys
import time
import urllib.request
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio import features
from rasterio.crs import CRS
from rasterio.env import Env
from rasterio.transform import Affine
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import Window, from_bounds
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from get_urmia import ENV, STAC, get, signed, slc_off  # noqa: E402  (keyless Landsat helpers)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "hamoun"
WGS, UTM = CRS.from_epsg(4326), CRS.from_epsg(32641)
YEARS = (1985, 2026)
WINDOW = ("05-01", "06-15")                          # late spring
WIDE = ("04-15", "06-30")                            # for a year with too few accepted passes
MIN_PASSES = 2
PATH, ROWS = "157", ("038", "039")
FILLS = ("158038", "158039", "156038", "156039")     # the picture's land outside path 157
MAX_CLOUD = 60                                       # % scene cloud (mean of a pass's two scenes)
BOX = (60.69, 30.2504, 62.31, 31.85)                 # W, S, E, N: the picture
DLON, DLAT = 0.0015, 0.00129
PIC_T = Affine(DLON, 0, BOX[0], 0, -DLAT, BOX[3])
PIC_SHAPE = (1240, 1080)
JRC_EXTENT = "https://storage.googleapis.com/global-surface-water/downloads2021/extent/extent_60E_40Nv1_4_2021.tif"
JRC_MONTHLY = ("https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GSWE/MonthlyHistory/LATEST/tiles/"
               "{y}/{y}_{m:02d}/{prefix}0000160000-0000960000.tif")     # the 60-70 E, 30-40 N chunk
JRC_LAST = 2021
NE_URL = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip"
OPEN, REGROW = 3, 4                                  # JRC pixels: the opening disk, the regrowth
TILE = 0.1                                           # deg: the strata
COUNTRY = {"IRN": 1, "AFG": 2}
MIN_CLEAR_STRATUM = 0.20
ACCEPT = dict(valid=(0.97, 0.65), clear=(0.85, 0.60), unseen_strata=0.05)   # (whole, Landsat 7 SLC-off)
MAX_SHIFT = (1.0, 0.5)                               # pixels: Tier 1, Tier 2
MIN_PEAK = 20                                        # a measurable shift: correlation peak / its noise
MIN_REG_CLEAR = 0.5                                  # ... and half the registration window clear
REG_BOX = (61.38, 30.84, 61.78, 31.12)               # W, S, E, N: the registration window (land)
REFERENCE = "P157_20210601_LC08"
EXCLUDE: dict[str, str] = {}                         # pass -> reason: left out of every count
RULES = ("mndwi0", "mndwi01", "mndwi0_nir10", "mndwi0_nir15", "ndwi0", "mndwi0_swir10", "mndwi0_swir15")
RULE_TEXT = {"mndwi0": "MNDWI > 0", "mndwi01": "MNDWI > 0.1", "mndwi0_nir10": "MNDWI > 0 and NIR < 0.10",
             "mndwi0_nir15": "MNDWI > 0 and NIR < 0.15", "ndwi0": "NDWI > 0",
             "mndwi0_swir10": "MNDWI > 0 and SWIR1 < 0.10", "mndwi0_swir15": "MNDWI > 0 and SWIR1 < 0.15"}
SCAN_VERSION = 2                                     # a cached scan of an older version is read again
COLUMNS = (["roi", "valid", "clear"] + [f"w_{r}" for r in RULES] + ["veg", "vegwater", "n_co", "jrc_w"]
           + [f"co_{r}" for r in RULES] + [f"both_{r}" for r in RULES])
MAPS = ("seen", "clear") + RULES + ("veg", "jrc")
SCALE, OFFSET = 0.0000275, -0.2
PIX_KM2 = 0.0009
DEC = 4                                              # the pictures read the 120-m overview
AGG = 5                                              # 30-m pixels per side of a map block (150 m)
N_COLOUR = 6
AGREE = 0.04                                         # reflectance: two flagged passes that look alike see ground
QA_CLEAR = 0b111110                                  # dilated cloud, cirrus, cloud, shadow, snow
QA_CLOUD = 0b11110                                   # the pictures: dilated cloud, cirrus, cloud, shadow
WATERLIKE = (0.10, 0.3)                              # SWIR1 below, MNDWI above: water even when QA flags it


def disk(r: int) -> np.ndarray:
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


# ----------------------------------------------------------------------------------------------- grids

def _countries(t: Affine, shape: tuple) -> np.ndarray:
    """Natural Earth 10 m admin-0 on a lon/lat grid: 1 Iran, 2 Afghanistan, 0 other."""
    import shapefile                                   # pyshp: no shapely in this process
    z = DATA / "ne" / "ne_10m_admin_0_countries.zip"
    if not z.exists():
        z.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(NE_URL, timeout=120) as r:
            z.write_bytes(r.read())
    shapes = []
    with shapefile.Reader(str(z)) as rd:
        for sr in rd.iterShapeRecords():
            code = COUNTRY.get(sr.record.as_dict()["ADM0_A3"])
            if code:
                shapes.append((sr.shape.__geo_interface__, code))
    return features.rasterize(shapes, out_shape=shape, transform=t, fill=0, dtype="uint8")


@functools.cache
def grids() -> dict:
    """The lakes, their strata and the grids, cached in data/hamoun/roi.npz (see the module docstring)."""
    cache = DATA / "roi.npz"
    if not cache.exists():
        with Env(**ENV), rasterio.open("/vsicurl/" + JRC_EXTENT) as src:
            win = from_bounds(*BOX, transform=src.transform).round_offsets(op="floor").round_lengths(op="ceil")
            ext, jt = src.read(1, window=win) == 1, src.window_transform(win)
        opened = ndimage.binary_opening(ext, structure=disk(OPEN))
        lab, n = ndimage.label(opened, structure=np.ones((3, 3)))
        sizes = ndimage.sum(opened, lab, index=np.arange(1, n + 1))
        main = lab == 1 + int(np.argmax(sizes))
        lakes = ext & ndimage.binary_dilation(main, structure=disk(REGROW))
        rr, cc = np.nonzero(lakes)
        r0, r1, c0, c1 = rr.min() - 40, rr.max() + 41, cc.min() - 40, cc.max() + 41
        lakes, ext = lakes[r0:r1, c0:c1], ext[r0:r1, c0:c1]
        jt = jt * Affine.translation(c0, r0)
        lon = jt.c + (np.arange(lakes.shape[1]) + 0.5) * jt.a
        lat = jt.f + (np.arange(lakes.shape[0]) + 0.5) * jt.e
        ix = np.floor((lon - 60.9) / TILE).astype(int)
        iy = np.floor((lat - 30.4) / TILE).astype(int)
        country = _countries(jt, lakes.shape)
        strata = ((iy[:, None] * 100 + ix[None, :]) * 4 + country).astype(np.int32) + 1
        strata[~lakes] = 0
        bounds = (jt.c, jt.f + lakes.shape[0] * jt.e, jt.c + lakes.shape[1] * jt.a, jt.f)   # W S E N
        xb = transform_bounds(WGS, UTM, *bounds)
        x0, x1 = math.floor((xb[0] - 15) / 30) * 30 + 15, math.ceil((xb[2] - 15) / 30) * 30 + 15
        y0, y1 = math.floor((xb[1] - 15) / 30) * 30 + 15, math.ceil((xb[3] - 15) / 30) * 30 + 15
        w, h = (x1 - x0) // 30, (y1 - y0) // 30
        w, h = w + (-w) % AGG, h + (-h) % AGG
        at = Affine(30, 0, x0, 0, -30, y1)
        a_strata = np.zeros((h, w), np.int32)
        reproject(source=strata, destination=a_strata, src_transform=jt, src_crs=WGS, dst_transform=at,
                  dst_crs=UTM, resampling=Resampling.nearest, src_nodata=0, dst_nodata=0)
        pic_lakes = np.zeros(PIC_SHAPE, np.uint8)
        reproject(source=lakes.astype(np.uint8), destination=pic_lakes, src_transform=jt, src_crs=WGS,
                  dst_transform=PIC_T, dst_crs=WGS, resampling=Resampling.max)
        pic_ext = np.zeros(PIC_SHAPE, np.uint8)
        reproject(source=ext.astype(np.uint8), destination=pic_ext, src_transform=jt, src_crs=WGS,
                  dst_transform=PIC_T, dst_crs=WGS, resampling=Resampling.max)
        pic_country = _countries(PIC_T, PIC_SHAPE)
        DATA.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, lakes=lakes, extent=ext, strata=strata, jrc_transform=np.array(tuple(jt)[:6]),
                            area_strata=a_strata, area_transform=np.array(tuple(at)[:6]), pic_lakes=pic_lakes == 1,
                            pic_extent=pic_ext == 1, pic_country=pic_country, pic_transform=np.array(tuple(PIC_T)[:6]))
    z = np.load(cache)
    a_strata = z["area_strata"]
    ids = np.unique(a_strata[a_strata > 0])
    flat = np.flatnonzero(a_strata.ravel() > 0)
    return dict(lakes=z["lakes"], extent=z["extent"], strata=z["strata"], jrc_t=Affine(*z["jrc_transform"]),
                area_strata=a_strata, area_t=Affine(*z["area_transform"]), area_shape=a_strata.shape,
                ids=ids, flat=flat, sidx=np.searchsorted(ids, a_strata.ravel()[flat]),
                pic_lakes=z["pic_lakes"], pic_extent=z["pic_extent"], pic_country=z["pic_country"])


def stratum_country(sid: int) -> int:
    return (int(sid) - 1) % 4


def area_lonlat() -> tuple:
    g = grids()
    h, w = g["area_shape"]
    t = g["area_t"]
    return transform_bounds(UTM, WGS, t.c, t.f + h * t.e, t.c + w * t.a, t.f)


# ------------------------------------------------------------------------------------------- catalogue

def search(year: int) -> list:
    """The STAC items of 15 April - 30 June over the picture box, cached."""
    cache = DATA / "stac" / f"{year}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    d = get(STAC, {"collections": ["landsat-c2-l2"], "bbox": list(BOX), "limit": 300,
                   "datetime": f"{year}-{WIDE[0]}T00:00:00Z/{year}-{WIDE[1]}T23:59:59Z"})
    feats = d.get("features", [])
    assert len(feats) < 300, f"{year}: the search hit its limit"
    keep = [dict(id=f["id"], properties={k: f["properties"].get(k) for k in
                                         ("datetime", "platform", "eo:cloud_cover", "landsat:collection_category")},
                 assets={k: {"href": v["href"]} for k, v in f["assets"].items()
                         if k in ("red", "green", "blue", "nir08", "swir16", "qa_pixel")})
            for f in feats]
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(keep))
    return keep


def in_window(date: str, window: tuple) -> bool:
    return f"{date[:4]}-{window[0]}" <= date[:10] <= f"{date[:4]}-{window[1]}"


def passes(year: int, window: tuple = WIDE) -> list:
    """Path 157's passes in the window: {name, date, platform, feats {row: item}}."""
    out = {}
    for f in search(year):
        _, _, pr, day = f["id"].split("_")[:4]
        if pr[:3] != PATH or pr[3:] not in ROWS:
            continue
        date = f"{day[:4]}-{day[4:6]}-{day[6:]}"
        if not in_window(date, window):
            continue
        name = f"P{PATH}_{day}_{f['id'][:4]}"
        p = out.setdefault(name, dict(name=name, date=date, platform=f["properties"]["platform"], feats={}))
        p["feats"][pr[3:]] = f
    return sorted(out.values(), key=lambda p: p["date"])


def pass_cloud(p: dict) -> float:
    return float(np.mean([f["properties"].get("eo:cloud_cover") or 0 for f in p["feats"].values()]))


def tier(p: dict) -> str:
    return "T2" if any(f["id"].endswith("_T2") for f in p["feats"].values()) else "T1"


def pass_slc_off(p: dict) -> bool:
    return any(slc_off(f) for f in p["feats"].values())


# ------------------------------------------------------------------------------------------------ JRC

def jrc_month(y: int, m: int) -> np.ndarray | None:
    """JRC's Monthly Water History of one month on the 30-m grid, cached (None after 2021)."""
    if y > JRC_LAST:
        return None
    cache = DATA / "jrc" / f"{y}_{m:02d}.npz"
    if not cache.exists():
        g = grids()
        prefix = "" if y == 2021 else f"{y}_{m:02d}-"            # the 2021 files have no prefix
        with Env(**ENV), rasterio.open("/vsicurl/" + JRC_MONTHLY.format(y=y, m=m, prefix=prefix)) as src:
            w, s, e, n = area_lonlat()
            win = from_bounds(w - 0.01, s - 0.01, e + 0.01, n + 0.01, transform=src.transform)
            win = win.round_offsets(op="floor").round_lengths(op="ceil")
            a, t = src.read(1, window=win), src.window_transform(win)
        dst = np.zeros(g["area_shape"], np.uint8)
        reproject(source=a, destination=dst, src_transform=t, src_crs=WGS, dst_transform=g["area_t"], dst_crs=UTM,
                  resampling=Resampling.nearest, src_nodata=255, dst_nodata=255)
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, code=dst)
    return np.load(cache)["code"]


# ------------------------------------------------------------------------------------------ 30-m scan

def read_band(href: str) -> tuple:
    """One band on the 30-m grid (0 where the scene has no data), and whether it had to be resampled."""
    g = grids()
    h, w = g["area_shape"]
    at = g["area_t"]
    out = np.zeros((h, w), np.uint16)
    misaligned = False
    with Env(**ENV), rasterio.open(signed(href)) as src:
        st = src.transform
        aligned = (src.crs == UTM and st.a == 30 and st.e == -30 and (st.c - at.c) % 30 == 0
                   and (st.f - at.f) % 30 == 0)
        if aligned:
            col, row = int((at.c - st.c) // 30), int((st.f - at.f) // 30)
            win = Window(col, row, w, h).intersection(Window(0, 0, src.width, src.height))
            if win.width > 0 and win.height > 0:
                a = src.read(1, window=win)
                r0, c0 = int(win.row_off) - row, int(win.col_off) - col
                out[r0:r0 + a.shape[0], c0:c0 + a.shape[1]] = a
        else:                                              # not on the grid: nearest, noted in the scan
            b = transform_bounds(UTM, src.crs, at.c, at.f - h * 30, at.c + w * 30, at.f)
            win = from_bounds(*b, transform=src.transform).round_offsets(op="floor").round_lengths(op="ceil")
            win = win.intersection(Window(0, 0, src.width, src.height))
            a = src.read(1, window=win)
            reproject(source=a, destination=out, src_transform=src.window_transform(win), src_crs=src.crs,
                      dst_transform=at, dst_crs=UTM, resampling=Resampling.nearest, src_nodata=0, dst_nodata=0)
            misaligned = True
    return out, misaligned


def read_pass(p: dict) -> tuple:
    """The pass's bands on the 30-m grid: row 038 where it has data, else row 039."""
    keys = ("green", "red", "nir08", "swir16", "qa_pixel")
    jobs = [(row, k, p["feats"][row]["assets"][k]["href"]) for row in ROWS if row in p["feats"] for k in keys]
    with ThreadPoolExecutor(len(jobs)) as pool:
        arrs = list(pool.map(lambda j: read_band(j[2]), jobs))
    by = {(j[0], j[1]): a for j, (a, _) in zip(jobs, arrs)}
    misaligned = any(m for _, m in arrs)
    out, valid = None, None
    for row in ROWS:
        if row not in p["feats"]:
            continue
        b = {k: by[(row, k)] for k in keys}
        v = (b["green"] > 0) & (b["red"] > 0) & (b["nir08"] > 0) & (b["swir16"] > 0) & ((b["qa_pixel"] & 1) == 0)
        if out is None:
            out, valid = b, v
        else:
            take = v & ~valid
            for k in keys:
                out[k][take] = b[k][take]
            valid |= v
    return out, valid, misaligned


def reflect(dn: np.ndarray) -> np.ndarray:
    return np.maximum(dn.astype(np.float32) * SCALE + OFFSET, 0.0001)


def waterlike(G, S) -> np.ndarray:
    """Unmistakable water, whatever QA_PIXEL says: SWIR1 below 0.10 and MNDWI above 0.3 (no cloud, bright
    land or salt has both; very turbid water, which QA_PIXEL flags as cloud or shadow, has)."""
    return (S < WATERLIKE[0]) & ((G - S) / (G + S) > WATERLIKE[1])


def classify(G, R, N, S) -> tuple:
    mndwi = (G - S) / (G + S)
    ndwi = (G - N) / (G + N)
    ndvi = (N - R) / (N + R)
    m0 = mndwi > 0
    rules = {"mndwi0": m0, "mndwi01": mndwi > 0.1, "mndwi0_nir10": m0 & (N < 0.10),
             "mndwi0_nir15": m0 & (N < 0.15), "ndwi0": ndwi > 0,
             "mndwi0_swir10": m0 & (S < 0.10), "mndwi0_swir15": m0 & (S < 0.15)}
    return rules, ndvi > 0.3, m0 & (ndvi > 0.2)


def phase_shift(ref: np.ndarray, img: np.ndarray) -> tuple:
    """(dx, dy, peak): how far img is shifted from ref in pixels (east, south), by phase correlation of the
    gradient images; peak = the correlation peak over its background's standard deviation."""
    def prep(a):
        a = np.where(np.isfinite(a), a, np.nanmedian(a))
        gy, gx = np.gradient(a)
        g = np.hypot(gx, gy)
        g = (g - g.mean()) / (g.std() + 1e-9)
        return g * np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    A, B = np.fft.fft2(prep(ref)), np.fft.fft2(prep(img))
    r = B * np.conj(A)
    c = np.fft.ifft2(r / (np.abs(r) + 1e-12)).real
    py, px = np.unravel_index(int(np.argmax(c)), c.shape)
    h, w = c.shape

    def sub(cm, c0, cp):
        d = cm - 2 * c0 + cp
        return 0.0 if d == 0 else 0.5 * (cm - cp) / d
    dy = py + sub(c[(py - 1) % h, px], c[py, px], c[(py + 1) % h, px])
    dx = px + sub(c[py, (px - 1) % w], c[py, px], c[py, (px + 1) % w])
    dy = dy - h if dy > h / 2 else dy
    dx = dx - w if dx > w / 2 else dx
    peak = float(c[py, px] / (np.std(c) + 1e-12))
    return float(dx), float(dy), peak


def reg_slice() -> tuple:
    g = grids()
    at = g["area_t"]
    x0, y0, x1, y1 = transform_bounds(WGS, UTM, *REG_BOX)
    c0, c1 = int((x0 - at.c) // 30), int((x1 - at.c) // 30)
    r0, r1 = int((at.f - y1) // 30), int((at.f - y0) // 30)
    return slice(r0, r1), slice(c0, c1)


def reference() -> np.ndarray:
    cache = DATA / "reference.npz"
    if not cache.exists():
        year = int(REFERENCE.split("_")[1][:4])
        p = next(q for q in passes(year) if q["name"] == REFERENCE)
        b, valid, _ = read_pass(p)
        clear = valid & ((b["qa_pixel"] & QA_CLEAR) == 0)
        rs, cs = reg_slice()
        swir = np.where(clear, reflect(b["swir16"]), np.nan)[rs, cs]
        np.savez_compressed(cache, swir=swir.astype(np.float32))
    return np.load(cache)["swir"]


def block_share(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    """Share num/den over AGG x AGG blocks of the 30-m grid, NaN where den is 0."""
    h, w = num.shape
    n = num.reshape(h // AGG, AGG, w // AGG, AGG).sum(axis=(1, 3), dtype=np.float32)
    d = den.reshape(h // AGG, AGG, w // AGG, AGG).sum(axis=(1, 3), dtype=np.float32)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(d > 0, n / d, np.nan).astype(np.float32)


def to_picture(share: np.ndarray) -> np.ndarray:
    g = grids()
    dst = np.full(PIC_SHAPE, np.nan, np.float32)
    reproject(source=share, destination=dst, src_transform=g["area_t"] * Affine.scale(AGG), src_crs=UTM,
              dst_transform=PIC_T, dst_crs=WGS, resampling=Resampling.bilinear, src_nodata=np.nan, dst_nodata=np.nan)
    return dst


def scan(p: dict) -> dict:
    """One pass at 30 m: shares, the registration shift, per stratum the counts, and the maps."""
    g = grids()
    b, valid, misaligned = read_pass(p)
    G, R, N, S = (reflect(b[k]) for k in ("green", "red", "nir08", "swir16"))
    flagged = (b["qa_pixel"] & QA_CLEAR) > 0
    rescued = valid & flagged & waterlike(G, S)              # turbid water flagged as cloud: clear water
    clear = valid & (~flagged | rescued)
    rules, veg, vegwater = classify(G, R, N, S)
    rules = {k: v & clear for k, v in rules.items()}
    veg, vegwater = veg & clear, vegwater & clear
    y, m = int(p["date"][:4]), int(p["date"][5:7])
    jrc = jrc_month(y, m)
    obs = clear & (jrc >= 1) & (jrc <= 2) if jrc is not None else np.zeros_like(clear)
    jw = obs & (jrc == 2) if jrc is not None else np.zeros_like(clear)
    flat, sidx, K = g["flat"], g["sidx"], len(g["ids"])

    def count(a):
        return np.bincount(sidx, weights=a.ravel()[flat], minlength=K).astype(np.int64)
    cols = {"roi": np.bincount(sidx, minlength=K), "valid": count(valid), "clear": count(clear)}
    for r in RULES:
        cols[f"w_{r}"] = count(rules[r])
    cols.update(veg=count(veg), vegwater=count(vegwater), n_co=count(obs), jrc_w=count(jw))
    for r in RULES:
        cols[f"co_{r}"] = count(rules[r] & obs)
        cols[f"both_{r}"] = count(rules[r] & jw)
    roi_px = int(cols["roi"].sum())
    rs, cs = reg_slice()
    reg_clear = float(clear[rs, cs].mean())
    dx, dy, peak = phase_shift(reference(), np.where(clear, S, np.nan)[rs, cs]) if reg_clear >= MIN_REG_CLEAR \
        else (np.nan, np.nan, 0.0)
    qa = b["qa_pixel"].ravel()[flat]
    feats = list(p["feats"].values())
    out = dict(name=p["name"], date=p["date"], platform=p["platform"], items=[f["id"] for f in feats],
               rows=sorted(p["feats"]), tier=tier(p), slc_off=pass_slc_off(p),
               cloud_scene=[f["properties"].get("eo:cloud_cover") for f in feats],
               valid_share=round(int(cols["valid"].sum()) / roi_px, 4),
               clear_share=round(int(cols["clear"].sum()) / roi_px, 4),
               jrc_month=f"{y}_{m:02d}" if jrc is not None else None,
               jrc_observed_share=round(int(cols["n_co"].sum()) / roi_px, 4),
               shift_px=[round(dx, 2), round(dy, 2)], shift_peak=round(peak, 1), reg_clear=round(reg_clear, 3),
               qa_cloud_share=round(float(((qa & 0b1000) > 0).mean()), 4),     # QA_PIXEL cloud bit, on the lakes
               qa_snow_share=round(float(((qa & 0b100000) > 0).mean()), 4),    # snow bit (bright salt is flagged)
               rescued_share=round(float(rescued.ravel()[flat].mean()), 4),   # flagged, but water-like
               version=SCAN_VERSION,
               misaligned=bool(misaligned), columns=list(COLUMNS),
               strata={str(int(sid)): [int(cols[c][k]) for c in COLUMNS] for k, sid in enumerate(g["ids"])})
    maps = {"seen": block_share(valid, np.ones_like(valid)), "clear": block_share(clear, valid)}
    for r in RULES:
        maps[r] = block_share(rules[r], clear)
    maps["veg"] = block_share(veg, clear)
    maps["jrc"] = block_share(jw, obs)
    pic = {}
    for k in MAPS:
        a = to_picture(maps[k])
        pic[k] = np.where(np.isfinite(a), np.clip(np.round(100 * a), 0, 100), 255).astype(np.uint8)
    (DATA / "maps").mkdir(parents=True, exist_ok=True)
    np.savez_compressed(DATA / "maps" / f"{p['name']}.npz", **pic)
    return out


def scan_cached(p: dict) -> dict:
    path = DATA / "scenes" / f"{p['name']}.json"
    if path.exists():
        r = json.loads(path.read_text())
        if "error" not in r and r.get("version") == SCAN_VERSION:
            return r
    for attempt in range(3):
        try:
            r = scan(p)
            break
        except Exception as ex:                                # a dropped connection costs one try
            r = dict(name=p["name"], date=p["date"], error=repr(ex)[:300])
            time.sleep(10)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(r))
    return r


# ------------------------------------------------------------------------------------- areas (no network)

def pass_area(r: dict, num: str, den: str) -> dict:
    """The stratified area (km2) of one pass: total, Iran, Afghanistan; and the unseen strata's share."""
    cols = r["columns"]
    a = np.array(list(r["strata"].values()), dtype=np.float64)
    sid = np.array([int(k) for k in r["strata"]])
    roi, nn, dd = a[:, cols.index("roi")], a[:, cols.index(num)], a[:, cols.index(den)]
    seen = dd >= MIN_CLEAR_STRATUM * roi
    overall = nn.sum() / dd.sum() if dd.sum() else np.nan
    with np.errstate(invalid="ignore", divide="ignore"):
        share = np.where(seen, nn / np.where(dd == 0, 1, dd), overall)
    area = share * roi * PIX_KM2
    c = np.array([stratum_country(s) for s in sid])
    return dict(total=float(area.sum()), iran=float(area[c == 1].sum()), afghanistan=float(area[c == 2].sum()),
                unseen=float(roi[~seen].sum() / roi.sum()))


def accept(r: dict) -> tuple[bool, str]:
    if "error" in r:
        return False, "could not be read: " + r["error"][:80]
    if r["name"] in EXCLUDE:
        return False, EXCLUDE[r["name"]]
    k = 1 if r["slc_off"] else 0
    why = []
    if r["valid_share"] < ACCEPT["valid"][k]:
        why.append(f"{100 * r['valid_share']:.1f} % of the lakes valid (rows {'+'.join(r['rows'])})")
    if r["clear_share"] < ACCEPT["clear"][k]:
        why.append(f"{100 * r['clear_share']:.1f} % of the lakes clear")
    if pass_area(r, "w_mndwi0", "clear")["unseen"] > ACCEPT["unseen_strata"]:
        why.append("too many strata under cloud")
    lim = MAX_SHIFT[1] if r["tier"] == "T2" else MAX_SHIFT[0]
    dx, dy = r["shift_px"]
    if r["shift_peak"] < MIN_PEAK:
        if r["tier"] == "T2":
            why.append(f"Tier 2 and its registration cannot be measured (peak {r['shift_peak']})")
    elif max(abs(dx), abs(dy)) > lim:
        why.append(f"{r['tier']}: shifted {30 * dx:+.0f} m east, {-30 * dy:+.0f} m north of the reference pass")
    return (not why), "; ".join(why)


def table() -> pd.DataFrame:
    """Every scanned pass from the cache, with its areas and whether it is accepted, and the year's window."""
    rows = []
    for f in sorted((DATA / "scenes").glob("*.json")):
        r = json.loads(f.read_text())
        if "error" not in r and r.get("version") != SCAN_VERSION:
            continue                                         # a scan of an older rule set, not read again
        ok, why = accept(r)
        row = dict(name=r["name"], date=r["date"], year=int(r["date"][:4]), accepted=ok, reason=why)
        if "error" not in r:
            row.update(platform=r["platform"], tier=r["tier"], slc_off=r["slc_off"], rows="+".join(r["rows"]),
                       cloud_scene=float(np.mean([c or 0 for c in r["cloud_scene"]])), valid=r["valid_share"],
                       clear=r["clear_share"], shift_x=r["shift_px"][0], shift_y=r["shift_px"][1],
                       shift_peak=r["shift_peak"], jrc_month=r["jrc_month"], jrc_obs=r["jrc_observed_share"],
                       rescued=r["rescued_share"], qa_cloud=r["qa_cloud_share"], qa_snow=r["qa_snow_share"])
            for rule in RULES:
                a = pass_area(r, f"w_{rule}", "clear")
                row[rule] = a["total"]
                row[f"{rule}_iran"], row[f"{rule}_afg"] = a["iran"], a["afghanistan"]
                if r["jrc_month"]:
                    row[f"{rule}_co"] = pass_area(r, f"co_{rule}", "n_co")["total"]
                    cols = r["columns"]
                    s = np.array(list(r["strata"].values()), dtype=np.float64)
                    co, both, jw = (s[:, cols.index(c)].sum() for c in (f"co_{rule}", f"both_{rule}", "jrc_w"))
                    row[f"{rule}_commission"] = (co - both) * PIX_KM2      # on the pixels both see
                    row[f"{rule}_omission"] = (jw - both) * PIX_KM2
                    row[f"{rule}_both"] = both * PIX_KM2
            row["veg"] = pass_area(r, "veg", "clear")["total"]
            row["vegwater"] = pass_area(r, "vegwater", "clear")["total"]
            if r["jrc_month"]:
                j = pass_area(r, "jrc_w", "n_co")
                row.update(jrc=j["total"], jrc_iran=j["iran"], jrc_afg=j["afghanistan"])
        rows.append(row)
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    df["in_window"] = [in_window(d, WINDOW) for d in df["date"]]
    n = df[df.accepted & df.in_window].groupby("year").size()
    df["window"] = ["default" if n.get(y, 0) >= MIN_PASSES else "wide" for y in df.year]
    df["counts"] = df.accepted & (df.in_window | (df.window == "wide"))
    return df


def annual(df: pd.DataFrame) -> pd.DataFrame:
    g = df[df.counts].groupby("year")
    out = pd.DataFrame({"window": g["window"].first(), "n_passes": g.size(),
                        "platforms": g["platform"].agg(lambda s: "+".join(sorted({p.replace("landsat-", "L") for p in s}))),
                        "dates": g["date"].agg(lambda s: " ".join(d[5:] for d in s))})
    for rule in RULES:
        out[rule] = g[rule].median()
        out[f"{rule}_low"], out[f"{rule}_high"] = g[rule].min(), g[rule].max()
        out[f"{rule}_iran"], out[f"{rule}_afg"] = g[f"{rule}_iran"].median(), g[f"{rule}_afg"].median()
    out["veg"] = g["veg"].median()
    out["vegwater"] = g["vegwater"].median()
    return out


# ------------------------------------------------------------------------------------------- pictures

def rgb_scene(feat: dict) -> tuple:
    """A scene's red, green, blue surface reflectance on the picture grid (NaN where unseen): all its
    pixels, and those not flagged as dilated cloud, cirrus, cloud or shadow (see the module docstring)."""
    with Env(**ENV):
        with rasterio.open(signed(feat["assets"]["qa_pixel"]["href"])) as q:
            b = transform_bounds(WGS, q.crs, *BOX)
            win = from_bounds(*b, transform=q.transform).round_offsets(op="floor").round_lengths(op="ceil")
            win = win.intersection(Window(0, 0, q.width, q.height))
            h, w = int(win.height) // DEC, int(win.width) // DEC
            win = Window(win.col_off, win.row_off, w * DEC, h * DEC)
            qa = q.read(1, window=win)
            crs, st = q.crs, q.window_transform(win) * Affine.scale(DEC)
        dn = []
        for band in ("red", "green", "blue", "swir16"):
            with rasterio.open(signed(feat["assets"][band]["href"])) as src:
                dn.append(src.read(1, window=win, out_shape=(h, w), resampling=Resampling.average).astype(np.float32))
    dn = np.stack(dn)
    sw = np.maximum(dn[3] * SCALE + OFFSET, 0.0001)
    gr = np.maximum(dn[1] * SCALE + OFFSET, 0.0001)
    cloudy = ((qa & QA_CLOUD) > 0).reshape(h, DEC, w, DEC).any(axis=(1, 3)) & ~waterlike(gr, sw)
    dn = dn[:3]
    valid = (dn > 0).all(axis=0)
    valid = ndimage.binary_erosion(valid, iterations=1 if slc_off(feat) else 2)   # no pixel half in a gap
    sr = dn * SCALE + OFFSET
    out = np.full((2, 3) + PIC_SHAPE, np.nan, np.float32)
    for j, keep in enumerate((valid, valid & ~cloudy)):
        for k in range(3):
            reproject(source=np.where(keep, sr[k], np.nan).astype(np.float32), destination=out[j, k],
                      src_transform=st, src_crs=crs, dst_transform=PIC_T, dst_crs=WGS,
                      resampling=Resampling.bilinear, src_nodata=np.nan, dst_nodata=np.nan)
    return out[0], out[1]


def rgb_pass(p: dict) -> tuple:
    """A pass on the picture grid: row 038 where it sees, else row 039."""
    every = clear = None
    for row in ROWS:
        if row not in p["feats"]:
            continue
        e, c = rgb_scene(p["feats"][row])
        if every is None:
            every, clear = e, c
        else:
            take = np.isnan(every[0]) & ~np.isnan(e[0])
            every[:, take], clear[:, take] = e[:, take], c[:, take]
    return every, clear


def _median(stack: list) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)              # all-NaN pixels stay NaN
        return np.nanmedian(np.stack(stack), axis=0)


def colour(year: int, df: pd.DataFrame | None = None) -> None:
    """The year's true-colour layers on the picture grid (see the module docstring)."""
    df = table() if df is None else df
    use = df[(df.year == year) & df.counts].sort_values("clear", ascending=False).head(N_COLOUR)
    if use.empty:
        print(f"colour {year}: no accepted pass", flush=True)
        return
    window = use["window"].iloc[0]
    win = WINDOW if window == "default" else WIDE
    by = {p["name"]: p for p in passes(year)}
    chosen = [by[n] for n in use["name"]]
    lake = ndimage.binary_dilation(grids()["pic_lakes"], iterations=2)
    with ThreadPoolExecutor(3) as pool:
        pairs = list(pool.map(rgb_pass, chosen))
    whole = [k for k, p in enumerate(chosen) if not pass_slc_off(p)]
    ref = pairs[whole[0] if whole else 0][1]                         # the clearest whole pass
    land = ~ndimage.binary_dilation(grids()["pic_lakes"], iterations=6)
    for k, (e, c) in enumerate(pairs):                              # each pass in the reference's tones
        over = np.isfinite(ref[0]) & np.isfinite(c[0]) & land
        if c is ref or over.sum() < 10000:
            continue
        for b in range(3):
            x, y = c[b][over].astype(np.float64), ref[b][over].astype(np.float64)
            gain, offset = np.linalg.lstsq(np.vstack([x, np.ones_like(x)]).T, y, rcond=None)[0]
            e[b], c[b] = gain * e[b] + offset, gain * c[b] + offset

    def layer(ks: list, strict: bool) -> np.ndarray:
        every = [pairs[k][0] for k in ks]
        clear = _median([pairs[k][1] for k in ks])
        seen = np.stack([~np.isnan(e[0]) for e in every]).sum(axis=0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            st = np.stack(every)
            spread = (np.nanmax(st, axis=0) - np.nanmin(st, axis=0)).max(axis=0)
        fall = np.isnan(clear[0]) & lake & ((seen >= 3) | ((seen == 2) & (spread < AGREE)))
        clear[:, fall] = _median(every)[:, fall]
        if strict:
            clear[:, seen < len(ks)] = np.nan                      # no edge where the median's set changes
        return clear
    strict = [layer(whole, True)] if whole else []
    loose = [layer(list(range(len(chosen))), False)]
    fills, items = [], [i for p in chosen for i in (f["id"] for f in p["feats"].values())]
    for pr in FILLS:
        feats = [f for f in search(year) if f["id"].split("_")[2] == pr and f["id"].endswith("_T1")
                 and in_window(f["properties"]["datetime"], win) and (f["properties"].get("eo:cloud_cover") or 0) <= MAX_CLOUD]
        feats = sorted(feats, key=lambda f: f["properties"].get("eo:cloud_cover") or 0)[:4]
        if not feats:
            continue
        with ThreadPoolExecutor(4) as pool:
            got = list(pool.map(rgb_scene, feats))
        f_layer = _median([c for _, c in got])
        f_layer[:, lake] = np.nan                                   # never inside the lakes
        if np.isfinite(f_layer[0]).any():
            fills.append(f_layer)
            items += [f["id"] for f in feats]
    np.savez_compressed(DATA / f"colour_{year}.npz", strict=np.array(strict, dtype=np.float16).reshape(-1, 3, *PIC_SHAPE),
                        loose=np.array(loose, dtype=np.float16), fills=np.array(fills, dtype=np.float16).reshape(-1, 3, *PIC_SHAPE),
                        passes=np.array([p["name"] for p in chosen]), items=np.array(items), window=np.array(window),
                        transform=np.array(tuple(PIC_T)[:6]))
    first = strict[0] if strict else loose[0]
    print(f"colour {year}: {len(chosen)} passes ({len(whole)} whole), {len(fills)} fill layers; lake unseen "
          f"{100 * np.isnan(loose[0][0])[grids()['pic_lakes']].mean():.2f} %; box unseen in the first layer "
          f"{100 * np.isnan(first[0]).mean():.1f} %", flush=True)


# ------------------------------------------------------------------------------------------------ main

def scan_year(year: int) -> list:
    todo = [p for p in passes(year, WINDOW) if pass_cloud(p) <= MAX_CLOUD]
    rows = [scan_cached(p) for p in todo]
    if sum(accept(r)[0] for r in rows) < MIN_PASSES:                 # widen the window
        more = [p for p in passes(year, WIDE) if not in_window(p["date"], WINDOW) and pass_cloud(p) <= MAX_CLOUD]
        rows += [scan_cached(p) for p in more]
    print(f"{year}: {len(rows)} passes scanned, {sum(accept(r)[0] for r in rows)} accepted", flush=True)
    return rows


def main(argv: list) -> None:
    t0 = time.time()
    DATA.mkdir(parents=True, exist_ok=True)
    g = grids()
    print(f"lakes: {int(g['lakes'].sum())} JRC cells; 30-m grid {g['area_shape']}; {len(g['ids'])} strata; "
          f"{len(g['flat']) * PIX_KM2:.0f} km2 on the 30-m grid", flush=True)
    years = [int(a) for a in argv[argv.index("--years") + 1:] if a.isdigit()] if "--years" in argv else \
        list(range(YEARS[0], YEARS[1] + 1))
    if "--colour" in argv:
        years = [int(a) for a in argv[argv.index("--colour") + 1:] if a.isdigit()] or list(range(YEARS[0], YEARS[1] + 1))
    else:
        with ThreadPoolExecutor(6) as pool:
            list(pool.map(search, years))
        months = sorted({(y, m) for y in years if y <= JRC_LAST for m in (5, 6)})
        with ThreadPoolExecutor(4) as pool:
            list(pool.map(lambda ym: jrc_month(*ym), months))
        print(f"JRC months cached: {len(months)} ({time.time() - t0:.0f} s)", flush=True)
        reference()
        with ThreadPoolExecutor(3) as pool:
            list(pool.map(scan_year, years))
        df = table()
        annual(df).round(1).to_csv(DATA / "area_spring.csv")
        print(f"scans done ({time.time() - t0:.0f} s): {len(df)} passes, {int(df.counts.sum())} counted", flush=True)
    df = table()

    def patient(year: int) -> None:
        for attempt in range(3):
            try:
                return colour(year, df)
            except Exception as ex:
                print(f"colour {year}: try {attempt + 1} failed: {ex!r}"[:300], flush=True)
                time.sleep(20)
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(patient, years))
    print(f"done in {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
