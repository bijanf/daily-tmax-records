"""Lake Urmia's water from Landsat: the September area of every year since 1986, and two pictures.

    data/urmia/scenes/<item>.json      per Landsat scene: footprint, valid pixels, water at three
                                        MNDWI thresholds (km2)
    data/urmia/area_september.csv      per year: the median over its accepted scenes (km2)
    data/urmia/picture_<year>.npz      water (median MNDWI > 0 over the year's scenes), the lake's
                                        full extent (JRC, any year 1984-2021) and the grid
    data/urmia/colour_<year>.npz       the September lake in true colour (red, green, blue surface
                                        reflectance on the same grid), for the reel   (--colour)
    data/urmia/level_insitu_daily.csv  the shore gauges' daily level 1965-2020 (Mendeley deposit)   (--gauge)

The MNDWI areas count wet salt crust and thin brine as water: in dry years they read up to 5-6
times the official open-water area (September 2025: 2,698 against 481 km2), so the reel shows the
true-colour pictures and the measured level, not these areas.

Landsat Collection 2 Level-2 surface reflectance (USGS), read from Microsoft's Planetary Computer
with its anonymous token (no account): scenes of WRS path 169 row 034 between 20 August and 10
October, up to four with the least cloud per year. Water = MNDWI = (green - SWIR1) / (green +
SWIR1) above 0 (checks -0.1, +0.1), on pixels inside the lake's full extent in JRC Global
Surface Water 1984-2021 (Pekel et al. 2016), clear of cloud, shadow, cirrus and snow (QA_PIXEL).
A scene's water area is its water share of the clear pixels times one fixed footprint (the median
of the Landsat 8/9 scenes), so a cloud or a stripe does not shrink the lake. Accepted: scenes
covering at least 85 % of that footprint (Landsat 7 after the 2003 scan-line failure: 60 %).
Known offsets (fact check of the method): Landsat 7 reads about 5 % above Landsat 8/9 in common
years; in dry years the threshold moves the area by about +9 % / -6 %.

    python -I src/get_urmia.py            # about 30 minutes for every year (scenes are cached)
"""

from __future__ import annotations

import datetime
import hashlib
import json
import sys
import time
import urllib.request
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.crs import CRS
from scipy import ndimage
from rasterio.env import Env
from rasterio.transform import Affine, from_origin
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import Window, from_bounds

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "urmia"
BOX = (44.9, 37.0, 46.0, 38.4)                      # W, S, E, N
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/landsat-c2-l2"
JRC = "https://storage.googleapis.com/global-surface-water/downloads2021/extent/extent_40E_40Nv1_4_2021.tif"
MENDELEY = ("https://data.mendeley.com/public-files/datasets/285n67m8zd/files/"
            "6971fa21-18d3-4107-9880-1660d9d1c07f/file_downloaded")
MENDELEY_SHA256 = "8a766ac5af2e2ea0a0cd7a244f7e9187d0032fd26ad5c127227d89790daf9775"
YEARS = (1986, 2026)
PICTURES = (1995, 2025)
THRESHOLDS = (-0.1, 0.0, 0.1)
PIXEL_KM2 = 0.0009                                  # a 30 m pixel
GRID = 0.0015                                       # deg: the pictures' grid, about 150 m
DECIMATE = 4                                        # the true-colour pictures read the 120 m overview
ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".TIF,.tif",
           GDAL_HTTP_MAX_RETRY="6", GDAL_HTTP_RETRY_DELAY="3")
_token = {"token": None, "expiry": 0.0}


def get(url: str, body: dict | None = None):
    last = None
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                         headers={"Content-Type": "application/json"}, method="POST" if body else "GET")
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except Exception as ex:                         # 429s and timeouts come in bursts: back off
            last = ex
            time.sleep(5 * 2 ** attempt)
    raise RuntimeError(f"no answer from {url}: {last!r}")


def signed(href: str) -> str:
    if not _token["token"] or _token["expiry"] - time.time() < 300:
        d = get(SAS)
        e = datetime.datetime.strptime(d["msft:expiry"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        _token.update(token=d["token"], expiry=e.timestamp())
    return "/vsicurl/" + href + "?" + _token["token"]


def scenes(year: int, path_row: str = "169034", n: int = 4, cloud: float = 60) -> list:
    d = get(STAC, {"collections": ["landsat-c2-l2"], "bbox": list(BOX), "limit": 300,
                   "datetime": f"{year}-08-20T00:00:00Z/{year}-10-10T23:59:59Z"})
    feats = [f for f in d.get("features", []) if f"_{path_row}_" in f["id"] and (f["properties"].get("eo:cloud_cover") or 0) <= cloud]
    return sorted(feats, key=lambda f: f["properties"].get("eo:cloud_cover") or 0)[:n]


def extent() -> tuple[np.ndarray, Affine]:
    """JRC's lake extent (any water 1984-2021) over the box, cached."""
    cache = DATA / "jrc_extent_box.npz"
    if cache.exists():
        z = np.load(cache)
        return z["ext"], Affine(*z["transform"])
    with Env(**ENV), rasterio.open("/vsicurl/" + JRC) as e:
        w = from_bounds(BOX[0] - 0.02, BOX[1] - 0.02, BOX[2] + 0.02, BOX[3] + 0.02, transform=e.transform)
        w = w.round_offsets().round_lengths()
        ext, t = e.read(1, window=w), e.window_transform(w)
    DATA.mkdir(parents=True, exist_ok=True)
    np.savez(cache, ext=ext, transform=np.array(tuple(t)[:6]))
    return ext, t


def on_grid(src: np.ndarray, src_t, src_crs, dst_t, dst_crs, shape, nodata=0) -> np.ndarray:
    dst = np.full(shape, nodata, dtype=src.dtype)
    reproject(source=src, destination=dst, src_transform=src_t, src_crs=src_crs, dst_transform=dst_t,
              dst_crs=dst_crs, resampling=Resampling.nearest, src_nodata=nodata, dst_nodata=nodata)
    return dst


def read(feat) -> tuple:
    """green, SWIR1, QA on the scene's own grid, cut to the box; with that grid."""
    a = feat["assets"]
    with Env(**ENV):
        with rasterio.open(signed(a["green"]["href"])) as g:
            b = transform_bounds(CRS.from_epsg(4326), g.crs, *BOX)
            win = from_bounds(*b, transform=g.transform).round_offsets(op="floor").round_lengths(op="ceil")
            win = win.intersection(Window(0, 0, g.width, g.height))
            t, crs, shape = g.window_transform(win), g.crs, (int(win.height), int(win.width))
            green = g.read(1, window=win)
        with rasterio.open(signed(a["swir16"]["href"])) as s:
            swir = s.read(1, window=win)
        with rasterio.open(signed(a["qa_pixel"]["href"])) as q:
            qa = q.read(1, window=win)
    return green, swir, qa, t, crs, shape


def mndwi_of(green, swir, qa, inside):
    bad = (qa & 0b111111) > 0                           # fill, dilated cloud, cirrus, cloud, shadow, snow
    ok = (green > 0) & (swir > 0) & inside
    G, S = green * 0.0000275 - 0.2, swir * 0.0000275 - 0.2
    den = np.where(G + S == 0, 1, G + S)
    m = np.where(ok & (G + S != 0), (G - S) / den, np.nan).astype(np.float32)
    return m, ok, ok & ~bad & np.isfinite(m)


def process(feat) -> dict:
    p = feat["properties"]
    green, swir, qa, t, crs, shape = read(feat)
    ext, ext_t = extent()
    inside = on_grid(ext, ext_t, CRS.from_epsg(4326), t, crs, shape) == 1
    m, ok, valid = mndwi_of(green.astype(np.float32), swir.astype(np.float32), qa, inside)
    out = dict(item=feat["id"], platform=p.get("platform"), datetime=p["datetime"],
               cloud_cover_scene=p.get("eo:cloud_cover"), footprint_km2=round(float(ok.sum()) * PIXEL_KM2, 1),
               valid_frac_of_footprint=round(float(valid.sum()) / max(int(ok.sum()), 1), 4))
    for thr in THRESHOLDS:
        out[f"water_valid_km2_thr{thr:+.1f}"] = round(float((valid & (m > thr)).sum()) * PIXEL_KM2, 1)
    return out


def table() -> pd.DataFrame:
    rows = []
    for f in sorted((DATA / "scenes").glob("*.json")):
        r = json.loads(f.read_text())
        if r.get("error"):
            continue
        d = pd.Timestamp(r["datetime"][:10])
        rows.append(dict(item=r["item"], date=d, year=d.year, platform=r["platform"], footprint=r["footprint_km2"],
                         valid=r["valid_frac_of_footprint"] * r["footprint_km2"],
                         **{f"w{thr:+.1f}": r[f"water_valid_km2_thr{thr:+.1f}"] for thr in THRESHOLDS}))
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    fixed = df[df.platform.isin(["landsat-8", "landsat-9"])].footprint.median()
    df["coverage"] = df.footprint / fixed
    for thr in THRESHOLDS:
        df[f"A{thr:+.1f}"] = df[f"w{thr:+.1f}"] / df.valid * fixed
    slc_off = (df.platform == "landsat-7") & (df.date >= pd.Timestamp("2003-06-01"))
    df["accepted"] = np.where(slc_off, df.coverage >= 0.6, df.coverage >= 0.85) & (df.valid > 0)
    df.attrs["fixed"] = float(fixed)
    return df


def annual(df: pd.DataFrame) -> pd.DataFrame:
    g = df[df.accepted].groupby("year")
    return pd.DataFrame({"n_scenes": g.size(), "area_km2": g["A+0.0"].median(), "low_km2": g["A+0.0"].min(),
                         "high_km2": g["A+0.0"].max(), "thr_minus": g["A-0.1"].median(), "thr_plus": g["A+0.1"].median(),
                         "platforms": g["platform"].agg(lambda s: "+".join(sorted(set(s))))})


def picture(year: int) -> None:
    """The year's water on a lon/lat grid: median MNDWI above 0 over its accepted path-169 scenes
    and the neighbouring path 168's (which covers the lake's south-east, outside path 169; the
    areas in area_september.csv stay on path 169 alone)."""
    df = table()
    feats = {f["id"]: f for f in scenes(year)}
    items = [i for i in df[(df.year == year) & df.accepted].item if i in feats]
    assert items, f"no accepted scene in {year}"
    east = scenes(year, "168034")
    feats.update({f["id"]: f for f in east})
    items += [f["id"] for f in east]
    w, s, e, n = BOX
    t = from_origin(w, n, GRID, GRID)
    shape = (int(round((n - s) / GRID)), int(round((e - w) / GRID)))
    stack = []
    ext, ext_t = extent()
    for i in items:
        green, swir, qa, st, crs, sshape = read(feats[i])
        inside = on_grid(ext, ext_t, CRS.from_epsg(4326), st, crs, sshape) == 1
        m, _, valid = mndwi_of(green.astype(np.float32), swir.astype(np.float32), qa, inside)
        m = np.where(valid, m, np.nan).astype(np.float32)
        stack.append(on_grid(m, st, crs, t, CRS.from_epsg(4326), shape, nodata=np.nan))
    med = np.nanmedian(np.stack(stack), axis=0)
    lake = on_grid(ext, ext_t, CRS.from_epsg(4326), t, CRS.from_epsg(4326), shape) == 1
    np.savez_compressed(DATA / f"picture_{year}.npz", water=med > 0, seen=np.isfinite(med), lake=lake,
                        transform=np.array(tuple(t)[:6]), items=np.array(items))
    print(f"picture {year}: {len(items)} scenes, water {np.nansum(med > 0) * GRID ** 2 * 111.32 ** 2 * np.cos(np.deg2rad(37.7)):.0f} km2 on the grid")


def rgb_on_grid(feat, t, shape) -> np.ndarray:
    """A scene's red, green and blue surface reflectance on the pictures' grid (NaN where unseen),
    read from the COG's overviews at about 120 m. Outside the lake (JRC's extent, two pixels wider)
    the pixels Landsat flags as dilated cloud, cirrus, cloud or cloud shadow (QA_PIXEL bits 1-4,
    read at 30 m) are dropped; inside it none are: bright salt can be flagged as cloud or snow."""
    out = np.full((3,) + shape, np.nan, np.float32)
    ext, ext_t = extent()
    with Env(**ENV):
        with rasterio.open(signed(feat["assets"]["qa_pixel"]["href"])) as q:
            b = transform_bounds(CRS.from_epsg(4326), q.crs, *BOX)
            win = from_bounds(*b, transform=q.transform).round_offsets(op="floor").round_lengths(op="ceil")
            win = win.intersection(Window(0, 0, q.width, q.height))
            h, w = int(win.height) // DECIMATE, int(win.width) // DECIMATE
            qa = q.read(1, window=win)[:h * DECIMATE, :w * DECIMATE]
            crs, st = q.crs, q.window_transform(win) * Affine.scale(win.width / w, win.height / h)
        cloudy = ((qa & 0b11110) > 0).reshape(h, DECIMATE, w, DECIMATE).any(axis=(1, 3))
        lake = ndimage.binary_dilation(on_grid(ext, ext_t, CRS.from_epsg(4326), st, crs, (h, w)) == 1, iterations=2)
        drop = cloudy & ~lake
        for k, band in enumerate(("red", "green", "blue")):
            with rasterio.open(signed(feat["assets"][band]["href"])) as src:
                dn = src.read(1, window=win, out_shape=(h, w), resampling=Resampling.average).astype(np.float32)
            sr = np.where((dn > 0) & ~drop, dn * 0.0000275 - 0.2, np.nan).astype(np.float32)
            reproject(source=sr, destination=out[k], src_transform=st, src_crs=crs, dst_transform=t,
                      dst_crs=CRS.from_epsg(4326), resampling=Resampling.bilinear, src_nodata=np.nan,
                      dst_nodata=np.nan)
    return out


def colour(year: int) -> None:
    """The year's September lake in true colour on the pictures' grid: per Landsat path the per-pixel
    median of its six least-cloudy scenes (no cloud mask: the median drops a cloud seen in fewer
    than half of them; with three, a pixel seen twice kept half of a cloud),
    path 169 over path 168 (the lake's south-east) over path 169's row 033 (the box's north-west corner)."""
    w, s, e, n = BOX
    t = from_origin(w, n, GRID, GRID)
    shape = (int(round((n - s) / GRID)), int(round((e - w) / GRID)))
    layers, items = [], []
    for path_row in ("169034", "168034", "169033"):
        feats = scenes(year, path_row, n=6)
        if feats:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)           # all-NaN pixels stay NaN
                layers.append(np.nanmedian(np.stack([rgb_on_grid(f, t, shape) for f in feats]), axis=0))
            items += [f["id"] for f in feats]
    if not layers:
        print(f"colour {year}: no scene", flush=True)
        return
    rgb = layers[0]
    for more in layers[1:]:
        rgb = np.where(np.isnan(rgb), more, rgb)
    np.savez_compressed(DATA / f"colour_{year}.npz", rgb=rgb.astype(np.float16), items=np.array(items),
                        transform=np.array(tuple(t)[:6]))
    print(f"colour {year}: {len(items)} scenes, unseen {100 * np.isnan(rgb[0]).mean():.1f} % of the box", flush=True)


def gauge() -> None:
    """The lake's level at its shore gauges, daily 1965 to January 2020, from the deposit of
    "Lake Urmia Restoration Success Story: A Natural Trend or a Planned Remedy?" (University of
    Tehran; Mendeley Data, doi:10.17632/285n67m8zd.2, CC BY 4.0), checked against its sha256."""
    xlsx = DATA / "mendeley_285n67m8zd_v2.xlsx"
    if not xlsx.exists():
        with urllib.request.urlopen(MENDELEY, timeout=120) as r:
            xlsx.write_bytes(r.read())
    assert hashlib.sha256(xlsx.read_bytes()).hexdigest() == MENDELEY_SHA256, "the deposit changed"
    import openpyxl
    ws = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)["Sheet1"]
    rows = [(r[4], r[5]) for r in ws.iter_rows(min_row=4, values_only=True)
            if isinstance(r[4], datetime.datetime) and r[5] is not None]   # columns E-F: "In Situ Observation"
    df = pd.DataFrame(rows, columns=["date", "level_m"]).sort_values("date")
    df.to_csv(DATA / "level_insitu_daily.csv", index=False)
    print(f"gauge: {len(df)} days, {df.date.min():%Y-%m-%d} to {df.date.max():%Y-%m-%d}")


def main() -> None:
    (DATA / "scenes").mkdir(parents=True, exist_ok=True)
    for year in range(YEARS[0], YEARS[1] + 1):
        for f in scenes(year):
            path = DATA / "scenes" / f"{f['id']}.json"
            if path.exists():
                continue
            try:
                r = process(f)
            except Exception as ex:                       # a scene that cannot be read is logged
                r = dict(item=f["id"], error=repr(ex)[:300])
            path.write_text(json.dumps(r, indent=1))
        print(year, "done", flush=True)
    df = table()
    annual(df).round(1).to_csv(DATA / "area_september.csv")
    print(f"fixed footprint {df.attrs['fixed']:.1f} km2; scenes {len(df)}, accepted {int(df.accepted.sum())}")
    for year in PICTURES:
        picture(year)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--pictures":
        for y in PICTURES:
            picture(y)
    elif len(sys.argv) > 1 and sys.argv[1] == "--gauge":
        gauge()
    elif len(sys.argv) > 1 and sys.argv[1] == "--colour":       # every year in true colour, three at a time
        years = [int(a) for a in sys.argv[2:]] or list(range(YEARS[0], YEARS[1] + 1))
        with ThreadPoolExecutor(3) as pool:
            list(pool.map(colour, years))
    elif len(sys.argv) > 1 and sys.argv[1] == "--scene":    # one scene, for checking against a cache
        feat = next(f for f in scenes(int(sys.argv[2])) if f["id"] == sys.argv[3])
        print(json.dumps(process(feat), indent=1))
    else:
        main()
