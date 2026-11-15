"""HOOR AL-AZIM / HAWIZEH FROM SPACE (on the Iran-Iraq border): the late-spring open water of every year 1986-2026
from Landsat, measured at 30 m, and one true-colour picture a year for a phone. A sibling of get_hamoun.py, simpler.

Measured data only. Landsat Collection 2 Level-2 surface reflectance (USGS) from Microsoft's Planetary Computer with
its anonymous token (the helpers of get_urmia.py); JRC Global Surface Water occurrence 1984-2021 (Pekel et al. 2016,
v1.4; storage.googleapis.com); Natural Earth 10 m admin-0 countries (naciscdn.org) for the Iran / Iraq split.

THE MARSH (the region the areas count): JRC's occurrence > 0 inside a hand polygon around the Hawizeh / Hoor al-Azim
block (MARSH_POLY: the vegetated basin between the Tigris canals in the west and the Karkheh floodplain in the
north-east, 30.98-31.86 N), opened with a disk of 2 pixels (cuts canals narrower than about 120 m), its largest piece.

WHEN: late spring, 15 April to 15 June (26 Farvardin to 25 Khordad: all in the Persian spring), when the spring
flood has arrived and before the summer heat. Any pass whose scenes cover the frame and average <= 40 % cloud.

PIXELS (on the frame's longitude/latitude grid at about 30 m, nearest neighbour from the scene's own grid; a zero is
"no data", so Landsat 7's stripes after 31 May 2003 are simply not seen). Clear: valid and no QA_PIXEL bit for
dilated cloud, cirrus, cloud or shadow, or water by the test whatever the bits say. Open water: MNDWI > 0 and
SWIR1 < 0.15 (the Hamoun rule: turbid flood water still absorbs SWIR1; damp salt and mud do not). Reeds: NDVI > 0.3.

AREA OF A PASS: the marsh is cut into 0.05-degree tiles split by the border; a tile's water = its water share of its
clear pixels x its area (a tile under 20 % clear takes the pass's overall share), summed for Iran, Iraq and the whole.
Accepted: at least 85 % of the marsh clear (Landsat 7 after the stripes: 60 %). A spring's number is the median of its
accepted passes. Each year's picture is its clearest unstriped pass (none: the year keeps its number, no picture).

    data/hoor/passes.csv        one row per pass read: date, satellite, clear share, water, reeds (Iran, Iraq, all)
    data/hoor/springs.csv       one row per spring: the median of the accepted passes, how many
    data/hoor/pic_<year>.npz    the picture pass: rgb (reflectance, 3 x H x W at 60 m), water share (H x W, 60 m)
    data/hoor/marsh.npz         the marsh mask and the Iran mask on the 30-m grid; the grid

    python -I src/get_hoor.py [--workers 6]
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.request
import zipfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from affine import Affine
from rasterio.crs import CRS
from rasterio.env import Env
from rasterio.features import rasterize
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import Window, from_bounds
from scipy import ndimage
from shapely.geometry import Polygon, box as sbox, shape
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
import get_urmia as gu  # noqa: E402  (get, signed, ENV, STAC)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "hoor"
BOX = (47.38, 30.92, 48.05, 31.90)                   # W, S, E, N: the film's frame (about 64 x 109 km)
DLAT = 30 / 111_320.0
DLON = 30 / (111_320.0 * np.cos(np.radians(31.41)))   # square 30-m pixels at the frame's middle latitude
MARSH_POLY = [(47.42, 31.86), (47.97, 31.86), (48.02, 31.40), (48.02, 30.99), (47.50, 30.98), (47.42, 31.40)]
OCC = "https://storage.googleapis.com/global-surface-water/downloads2021/occurrence/occurrence_40E_40Nv1_4_2021.tif"
NE_URL = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip"
UA = {"User-Agent": "daily-tmax-records/hoor (research reel)"}
YEARS = range(1986, 2027)
SEASON = ("04-15", "06-15")
PIC = 2                                              # picture pixels = PIC x PIC grid pixels (60 m)
TILE = 0.05


def grid():
    w, s, e, n = BOX
    shp = (int(round((n - s) / DLAT)), int(round((e - w) / DLON)))
    return Affine(DLON, 0, w, 0, -DLAT, n), shp


def striped(p: dict) -> bool:
    return p.get("platform") == "landsat-7" and p["datetime"][:10] >= "2003-05-31"


def search(year: int) -> list:
    d = gu.get(gu.STAC, {"collections": ["landsat-c2-l2"], "bbox": list(BOX), "limit": 300,
                         "datetime": f"{year}-{SEASON[0]}T00:00:00Z/{year}-{SEASON[1]}T23:59:59Z"})
    want = sbox(*BOX)
    passes = {}
    for f in d.get("features", []):
        p = f["properties"]
        passes.setdefault((p["datetime"][:10], p["platform"], p.get("landsat:wrs_path")), []).append(f)
    out = []
    for key, fs in passes.items():
        fs = [f for f in fs if shape(f["geometry"]).intersection(want).area / want.area > 0.02]
        if not fs:
            continue
        cover = unary_union([shape(f["geometry"]) for f in fs]).intersection(want).area / want.area
        cloud = float(np.mean([f["properties"].get("eo:cloud_cover") or 0 for f in fs]))
        if cover >= 0.995 and cloud <= 40:
            fs.sort(key=lambda f: -shape(f["geometry"]).intersection(want).area)
            out.append(dict(date=key[0], platform=key[1], cloud=cloud, ids=[f["id"] for f in fs], feats=fs))
    return sorted(out, key=lambda x: x["cloud"])


def read(feats: list) -> dict:
    """The pass's bands on the frame's grid (reflectance, NaN = not seen) and its QA; a later scene fills holes."""
    t, shp = grid()
    out = {}
    names = ("red", "green", "blue", "nir08", "swir16", "qa_pixel")
    for feat in feats:
        with Env(**gu.ENV):
            for name in names:
                with rasterio.open(gu.signed(feat["assets"][name]["href"])) as src:
                    bb = transform_bounds(CRS.from_epsg(4326), src.crs, *BOX)
                    win = from_bounds(*bb, transform=src.transform).round_offsets(op="floor").round_lengths(op="ceil")
                    win = win.intersection(Window(0, 0, src.width, src.height))
                    a = src.read(1, window=win)
                    st = src.window_transform(win)
                    if name == "qa_pixel":
                        dst = np.zeros(shp, np.uint16)
                        reproject(a, dst, src_transform=st, src_crs=src.crs, dst_transform=t, dst_crs=CRS.from_epsg(4326),
                                  resampling=Resampling.nearest, src_nodata=0, dst_nodata=0)
                        hole = out[name] == 0 if name in out else None
                    else:
                        sr = np.where(a > 0, a.astype(np.float32) * 0.0000275 - 0.2, np.nan).astype(np.float32)
                        dst = np.full(shp, np.nan, np.float32)
                        reproject(sr, dst, src_transform=st, src_crs=src.crs, dst_transform=t, dst_crs=CRS.from_epsg(4326),
                                  resampling=Resampling.nearest, src_nodata=np.nan, dst_nodata=np.nan)
                        hole = ~np.isfinite(out[name]) if name in out else None
                    out[name] = dst if hole is None else np.where(hole, dst, out[name])
    return out


def masks() -> dict:
    path = OUT / "marsh.npz"
    if path.exists():
        z = np.load(path)
        return dict(marsh=z["marsh"], iran=z["iran"])
    t, shp = grid()
    with Env(**gu.ENV), rasterio.open("/vsicurl/" + OCC) as e:
        win = from_bounds(*BOX, transform=e.transform).round_offsets().round_lengths()
        occ, et = e.read(1, window=win), e.window_transform(win)
    o = np.zeros(shp, np.uint8)
    reproject(((occ > 0) & (occ <= 100)).astype(np.uint8), o, src_transform=et, src_crs=CRS.from_epsg(4326),
              dst_transform=t, dst_crs=CRS.from_epsg(4326), resampling=Resampling.nearest)
    poly = rasterize([(Polygon(MARSH_POLY), 1)], out_shape=shp, transform=t).astype(bool)
    m = ndimage.binary_opening(o.astype(bool) & poly, structure=ndimage.generate_binary_structure(2, 1), iterations=2)
    lab, k = ndimage.label(m, structure=np.ones((3, 3)))
    sizes = ndimage.sum(m, lab, range(1, k + 1))
    marsh = lab == 1 + int(np.argmax(sizes))
    raw = urllib.request.urlopen(urllib.request.Request(NE_URL, headers=UA), timeout=300).read()
    ne = OUT / "ne"
    ne.mkdir(parents=True, exist_ok=True)
    zipfile.ZipFile(io.BytesIO(raw)).extractall(ne)
    import shapefile
    r = shapefile.Reader(str(ne / "ne_10m_admin_0_countries.shp"))
    fields = [f[0] for f in r.fields[1:]]
    geoms = [s.shape.__geo_interface__ for s in r.iterShapeRecords() if dict(zip(fields, s.record))["ADM0_A3"] == "IRN"]
    iran = rasterize([(g, 1) for g in geoms], out_shape=shp, transform=t).astype(bool)
    np.savez_compressed(path, marsh=marsh, iran=iran, transform=np.array(tuple(t)[:6]))
    px = 0.03 ** 2
    print(f"marsh: {marsh.sum() * px:.0f} km2 ({(marsh & iran).sum() * px:.0f} Iran, {(marsh & ~iran).sum() * px:.0f} Iraq)", flush=True)
    return dict(marsh=marsh, iran=iran)


def tiles(marsh: np.ndarray, iran: np.ndarray) -> np.ndarray:
    """Strata: 0.05-degree tiles split by the border (an integer label per marsh pixel, 0 outside)."""
    t, shp = grid()
    cols = (np.arange(shp[1]) * DLON / TILE).astype(int)
    rows = (np.arange(shp[0]) * DLAT / TILE).astype(int)
    lab = (rows[:, None] * 1000 + cols[None, :]) * 2 + iran.astype(int) + 1
    return np.where(marsh, lab, 0)


def measure(pas: dict) -> dict:
    mk = masks()
    marsh, iran = mk["marsh"], mk["iran"]
    d = read(pas["feats"])
    g, r, nir, sw = (np.clip(d[k], 1e-4, None) for k in ("green", "red", "nir08", "swir16"))
    valid = np.isfinite(d["green"]) & np.isfinite(d["red"]) & np.isfinite(d["nir08"]) & np.isfinite(d["swir16"])
    mndwi = (g - sw) / (g + sw)
    ndvi = (nir - r) / (nir + r)
    water = valid & (mndwi > 0) & (sw < 0.15)
    reeds = valid & (ndvi > 0.3) & ~water
    clear = valid & (((d["qa_pixel"] & 0b11110) == 0) | water)
    px = 0.03 ** 2
    lab = tiles(marsh, iran)
    ids = np.unique(lab[lab > 0])
    n_all = ndimage.sum(np.ones_like(lab), lab, ids)
    n_clear = ndimage.sum(clear, lab, ids)
    n_w = ndimage.sum(water & clear, lab, ids)
    n_r = ndimage.sum(reeds & clear, lab, ids)
    share_c = (clear & marsh).sum() / marsh.sum()
    overall_w = n_w.sum() / max(n_clear.sum(), 1)
    overall_r = n_r.sum() / max(n_clear.sum(), 1)
    ok = n_clear >= 0.2 * n_all
    sw_ = np.where(ok, n_w / np.maximum(n_clear, 1), overall_w)
    sr_ = np.where(ok, n_r / np.maximum(n_clear, 1), overall_r)
    is_iran = (ids % 2) == 0
    row = dict(date=pas["date"], platform=pas["platform"], cloud=round(pas["cloud"], 1), striped=striped(pas["feats"][0]["properties"]),
               clear=round(float(share_c), 3), ids=";".join(pas["ids"]))
    for name, sel in (("all", np.ones_like(is_iran)), ("iran", is_iran), ("iraq", ~is_iran)):
        row[f"water_{name}"] = round(float((sw_ * n_all)[sel].sum() * px), 1)
        row[f"reeds_{name}"] = round(float((sr_ * n_all)[sel].sum() * px), 1)
    rgb = np.stack([d["red"], d["green"], d["blue"]])
    H, W = (s // PIC for s in marsh.shape)
    rgb = np.nanmean(rgb[:, :H * PIC, :W * PIC].reshape(3, H, PIC, W, PIC), axis=(2, 4))
    wat = np.where(clear, water, np.nan)[:H * PIC, :W * PIC].reshape(H, PIC, W, PIC)
    row["_pic"] = dict(rgb=rgb.astype(np.float32), water=np.nanmean(wat, axis=(1, 3)).astype(np.float32))
    return row


def work(year: int, pas: dict):
    try:
        return year, measure(pas)
    except Exception as ex:                          # a scene that cannot be read is logged and skipped
        return year, dict(date=pas["date"], error=repr(ex)[:200])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-passes", type=int, default=4)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    masks()
    cache = OUT / "passes.csv"
    old = pd.read_csv(cache) if cache.exists() else pd.DataFrame(columns=["date"])
    seen = set(old["date"].astype(str))
    jobs = []
    for y in YEARS:
        for pas in search(y)[: a.max_passes]:
            if pas["date"] not in seen:
                jobs.append((y, pas))
    print(len(jobs), "passes to read", flush=True)
    rows = old.to_dict("records")
    pics = {}
    with ProcessPoolExecutor(a.workers) as ex:
        futs = [ex.submit(work, y, p) for y, p in jobs]
        for f in as_completed(futs):
            y, row = f.result()
            if "error" in row:
                print(y, row["date"], "FAILED", row["error"], flush=True)
                continue
            pic = row.pop("_pic")
            row["year"] = y
            rows.append(row)
            if not row["striped"] and row["clear"] >= 0.85:
                prev = pics.get(y)
                if prev is None or row["clear"] > prev[0]:
                    pics[y] = (row["clear"], row["date"], pic)
            print(y, row["date"], row["platform"], "clear", row["clear"], "water", row["water_all"],
                  f"(Iran {row['water_iran']}, Iraq {row['water_iraq']})", flush=True)
            pd.DataFrame(rows).sort_values("date").to_csv(cache, index=False)
    for y, (c, date, pic) in pics.items():
        path = OUT / f"pic_{y}.npz"
        if path.exists():
            z = np.load(path)
            if float(z["clear"]) >= c:
                continue
        np.savez_compressed(path, rgb=pic["rgb"], water=pic["water"], date=date, clear=c)
    df = pd.DataFrame(rows)
    df["year"] = pd.to_datetime(df["date"]).dt.year
    acc = df[(df.clear >= np.where(df.striped, 0.60, 0.85))]
    sp = acc.groupby("year").agg(n=("date", "size"), water_all=("water_all", "median"), water_iran=("water_iran", "median"),
                                 water_iraq=("water_iraq", "median"), reeds_all=("reeds_all", "median"),
                                 striped_only=("striped", "all"))
    sp.to_csv(OUT / "springs.csv")
    print(sp.round(1).to_string())


if __name__ == "__main__":
    main()
