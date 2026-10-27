"""Lake Urmia's water from Landsat: the September area of every year since 1986, and two pictures.

    data/urmia/scenes/<item>.json      per Landsat scene: footprint, valid pixels, water at three
                                        MNDWI thresholds (km2)
    data/urmia/area_september.csv      per year: the median over its accepted scenes (km2)
    data/urmia/picture_<year>.npz      water (median MNDWI > 0 over the year's scenes), the lake's
                                        full extent (JRC, any year 1984-2021) and the grid, for the reel

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
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.crs import CRS
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
YEARS = (1986, 2026)
PICTURES = (1995, 2025)
THRESHOLDS = (-0.1, 0.0, 0.1)
PIXEL_KM2 = 0.0009                                  # a 30 m pixel
GRID = 0.0015                                       # deg: the pictures' grid, about 150 m
ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".TIF,.tif",
           GDAL_HTTP_MAX_RETRY="6", GDAL_HTTP_RETRY_DELAY="3")
_token = {"token": None, "expiry": 0.0}


def get(url: str, body: dict | None = None):
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                         headers={"Content-Type": "application/json"}, method="POST" if body else "GET")
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except Exception:
            time.sleep(3 + 3 * attempt)
    raise RuntimeError(f"no answer from {url}")


def signed(href: str) -> str:
    if not _token["token"] or _token["expiry"] - time.time() < 300:
        d = get(SAS)
        e = datetime.datetime.strptime(d["msft:expiry"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        _token.update(token=d["token"], expiry=e.timestamp())
    return "/vsicurl/" + href + "?" + _token["token"]


def scenes(year: int, path_row: str = "169034") -> list:
    d = get(STAC, {"collections": ["landsat-c2-l2"], "bbox": list(BOX), "limit": 300,
                   "datetime": f"{year}-08-20T00:00:00Z/{year}-10-10T23:59:59Z"})
    feats = [f for f in d.get("features", []) if f"_{path_row}_" in f["id"] and (f["properties"].get("eo:cloud_cover") or 0) <= 60]
    return sorted(feats, key=lambda f: f["properties"].get("eo:cloud_cover") or 0)[:4]


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
    elif len(sys.argv) > 1 and sys.argv[1] == "--scene":    # one scene, for checking against a cache
        feat = next(f for f in scenes(int(sys.argv[2])) if f["id"] == sys.argv[3])
        print(json.dumps(process(feat), indent=1))
    else:
        main()
