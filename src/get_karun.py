"""THE KARUN FROM SPACE, two places on one river (Khuzestan): what stands along it in late summer, 1987-1994 against
2013-2026, measured at 30 m from Landsat, and one true-colour picture of each place for 1990 (1369) and 2026 (1405).

The owner's question (15 Nov 2026): a before/after of the Karun "like the Hamoun". The river itself shows none: its
late-summer water surface through Ahvaz is nearly the same in 1990 and 2026 (research/feasibility/feas_karun). What
changed along it, and what this file measures:

    gotvand   the lake behind the Gotvand dam (the dam at about 48.94 E, 32.27 N): open water inside LAKE_POLY
    fields    the plain along the river south of Ahvaz: green land (NDVI > 0.3, not water) inside FIELDS_POLY, which
              leaves out the Shadegan marsh's edge (south-east) and the reed strip on the frame's western edge

Measured data only: Landsat Collection 2 Level-2 surface reflectance (USGS) from Microsoft's Planetary Computer with
its anonymous token (get_urmia.py's helpers); JRC Global Surface Water occurrence (Pekel et al. 2016) to keep the
lake's water near water that the JRC ever saw (mountain shadow passes a water test; it lies far from the lake).

WHEN: late summer, 20 August to 5 October (29 Mordad to 13 Mehr): no rain since spring, so what is green is watered;
the reservoirs are near their yearly low. Path 165 sees both places in one pass (rows 038 and 039, seconds apart).

PIXELS (on each place's longitude/latitude grid at about 30 m, nearest neighbour; a zero is "no data"). Clear: valid
and no QA_PIXEL bit for dilated cloud, cirrus, cloud or shadow, or water by the test. Open water: MNDWI > 0 and
SWIR1 < 0.15 and NIR < 0.12. Green: NDVI > 0.3 and not water.

A PASS counts when at least 90 % of the place's polygon is clear; its area is the share of the clear pixels times
the polygon's area. A summer's number is the median of its counted passes (at most three, the least cloudy).
Striped Landsat 7 (after 31 May 2003) is not used: 2003-2012 have no usable pass here (no Landsat 5 in the archive).

    data/karun/passes.csv        one row per pass and place
    data/karun/summers.csv       one row per summer and place: the median, how many passes
    data/karun/<place>_<year>.npz  the picture of 1990 and 2026: rgb (reflectance, the median of the summer's clear
                                 passes, 30 m), the mask of what was measured (water or green share, 30 m)
    data/karun/<place>_grid.npz  the polygon's mask on the grid

    python -I src/get_karun.py [--workers 6]
"""

from __future__ import annotations

import argparse
import sys
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
OUT = ROOT / "data" / "karun"
OCC = "https://storage.googleapis.com/global-surface-water/downloads2021/occurrence/occurrence_40E_40Nv1_4_2021.tif"
SEASON = ("08-20", "10-05")
YEARS = tuple(range(1987, 1995)) + tuple(range(2013, 2027))
PICTURES = (1990, 2026)                              # 1369 and 1405
M = 30.0                                             # metres a grid pixel
# each place: the film's frame (W, S, E, N; 9:16 on the ground), the polygon measured, what is measured
PLACES = dict(
    gotvand=dict(box=(48.82, 31.749, 49.42, 32.651), what="water",
                 poly=[(48.92, 32.46), (49.36, 32.46), (49.36, 32.08), (48.92, 32.08)]),
    fields=dict(box=(48.17, 30.547, 48.73, 31.40), what="green",
                poly=[(48.17, 31.25), (48.66, 31.25), (48.66, 30.905), (48.47, 30.905), (48.47, 30.84), (48.20, 30.84),
                      (48.20, 30.97), (48.17, 30.97)]),
)


def grid(name: str):
    w, s, e, n = PLACES[name]["box"]
    lat = 0.5 * (s + n)
    dlat = M / 111_320.0
    dlon = M / (111_320.0 * np.cos(np.radians(lat)))
    return Affine(dlon, 0, w, 0, -dlat, n), (int(round((n - s) / dlat)), int(round((e - w) / dlon)))


def search(name: str, year: int) -> list:
    b = PLACES[name]["box"]
    d = gu.get(gu.STAC, {"collections": ["landsat-c2-l2"], "bbox": list(b), "limit": 300,
                         "datetime": f"{year}-{SEASON[0]}T00:00:00Z/{year}-{SEASON[1]}T23:59:59Z"})
    want = Polygon(PLACES[name]["poly"])
    passes = {}
    for f in d.get("features", []):
        p = f["properties"]
        if p.get("platform") == "landsat-7" and p["datetime"][:10] >= "2003-05-31":
            continue
        passes.setdefault((p["datetime"][:10], p["platform"], p.get("landsat:wrs_path")), []).append(f)
    out = []
    for key, fs in passes.items():
        fs = [f for f in fs if shape(f["geometry"]).intersection(sbox(*b)).area / sbox(*b).area > 0.02]
        if not fs:
            continue
        u = unary_union([shape(f["geometry"]) for f in fs])
        cloud = float(np.mean([f["properties"].get("eo:cloud_cover") or 0 for f in fs]))
        if u.intersection(want).area / want.area >= 0.999 and cloud <= 40:   # the polygon wholly inside the pass
            fs.sort(key=lambda f: -shape(f["geometry"]).intersection(sbox(*b)).area)
            out.append(dict(date=key[0], platform=key[1], cloud=cloud, frame=u.intersection(sbox(*b)).area / sbox(*b).area,
                            ids=[f["id"] for f in fs], feats=fs))
    return sorted(out, key=lambda x: (x["cloud"], -x["frame"]))


def read(name: str, feats: list) -> dict:
    t, shp = grid(name)
    b = PLACES[name]["box"]
    out = {}
    for feat in feats:
        with Env(**gu.ENV):
            for band in ("red", "green", "blue", "nir08", "swir16", "qa_pixel"):
                with rasterio.open(gu.signed(feat["assets"][band]["href"])) as src:
                    bb = transform_bounds(CRS.from_epsg(4326), src.crs, *b)
                    win = from_bounds(*bb, transform=src.transform).round_offsets(op="floor").round_lengths(op="ceil")
                    win = win.intersection(Window(0, 0, src.width, src.height))
                    a = src.read(1, window=win)
                    st = src.window_transform(win)
                    if band == "qa_pixel":
                        dst = np.zeros(shp, np.uint16)
                        reproject(a, dst, src_transform=st, src_crs=src.crs, dst_transform=t, dst_crs=CRS.from_epsg(4326),
                                  resampling=Resampling.nearest, src_nodata=0, dst_nodata=0)
                        hole = out[band] == 0 if band in out else None
                    else:
                        sr = np.where(a > 0, a.astype(np.float32) * 0.0000275 - 0.2, np.nan).astype(np.float32)
                        dst = np.full(shp, np.nan, np.float32)
                        reproject(sr, dst, src_transform=st, src_crs=src.crs, dst_transform=t, dst_crs=CRS.from_epsg(4326),
                                  resampling=Resampling.nearest, src_nodata=np.nan, dst_nodata=np.nan)
                        hole = ~np.isfinite(out[band]) if band in out else None
                    out[band] = dst if hole is None else np.where(hole, dst, out[band])
    return out


def masks(name: str) -> dict:
    path = OUT / f"{name}_grid.npz"
    if path.exists():
        z = np.load(path)
        return dict(poly=z["poly"], near=z["near"])
    t, shp = grid(name)
    poly = rasterize([(Polygon(PLACES[name]["poly"]), 1)], out_shape=shp, transform=t).astype(bool)
    near = np.ones(shp, bool)
    if PLACES[name]["what"] == "water":                # water counts only near water the JRC ever saw (not shadow)
        b = PLACES[name]["box"]
        with Env(**gu.ENV), rasterio.open("/vsicurl/" + OCC) as e:
            win = from_bounds(*b, transform=e.transform).round_offsets().round_lengths()
            occ, et = e.read(1, window=win), e.window_transform(win)
        o = np.zeros(shp, np.uint8)
        reproject(((occ > 0) & (occ <= 100)).astype(np.uint8), o, src_transform=et, src_crs=CRS.from_epsg(4326),
                  dst_transform=t, dst_crs=CRS.from_epsg(4326), resampling=Resampling.nearest)
        near = ndimage.binary_dilation(o.astype(bool), iterations=20)       # 600 m: a lake above its old shore still counts
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, poly=poly, near=near, transform=np.array(tuple(t)[:6]))
    print(f"{name}: polygon {poly.sum() * (M / 1000) ** 2:.0f} km2", flush=True)
    return dict(poly=poly, near=near)


def measure(name: str, pas: dict, keep: bool) -> dict:
    mk = masks(name)
    poly, near = mk["poly"], mk["near"]
    d = read(name, pas["feats"])
    g, r, nir, sw = (np.clip(d[k], 1e-4, None) for k in ("green", "red", "nir08", "swir16"))
    valid = np.isfinite(d["green"]) & np.isfinite(d["red"]) & np.isfinite(d["nir08"]) & np.isfinite(d["swir16"])
    mndwi = (g - sw) / (g + sw)
    ndvi = (nir - r) / (nir + r)
    water = valid & (mndwi > 0) & (sw < 0.15) & (nir < 0.12)
    green = valid & (ndvi > 0.3) & ~water
    clear = valid & (((d["qa_pixel"] & 0b11110) == 0) | water)
    what = (water & near) if PLACES[name]["what"] == "water" else green
    px = (M / 1000.0) ** 2
    n_clear = int((clear & poly).sum())
    share = n_clear / poly.sum()
    area = float((what & clear & poly).sum() / max(n_clear, 1) * poly.sum() * px)
    row = dict(place=name, date=pas["date"], platform=pas["platform"], cloud=round(pas["cloud"], 1), clear=round(share, 3),
               frame=round(pas["frame"], 3), km2=round(area, 1), ids=";".join(pas["ids"]))
    if keep:
        rgb = np.stack([d["red"], d["green"], d["blue"]])
        rgb[:, ~clear] = np.nan
        row["_rgb"] = rgb.astype(np.float32)
        row["_what"] = np.where(clear, what, np.nan).astype(np.float32)
    return row


def work(name: str, year: int, pas: dict):
    try:
        return name, year, measure(name, pas, year in PICTURES)
    except Exception as ex:                          # a scene that cannot be read is logged and skipped
        return name, year, dict(date=pas["date"], error=repr(ex)[:200])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-passes", type=int, default=3)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for name in PLACES:
        masks(name)
    cache = OUT / "passes.csv"
    old = pd.read_csv(cache) if cache.exists() else pd.DataFrame(columns=["place", "date"])
    seen = set(zip(old["place"], old["date"].astype(str)))
    jobs = []
    for name in PLACES:
        for y in YEARS:
            need_pic = y in PICTURES and not (OUT / f"{name}_{y}.npz").exists()
            for pas in search(name, y)[: a.max_passes]:
                if need_pic or (name, pas["date"]) not in seen:
                    jobs.append((name, y, pas))
    print(len(jobs), "passes to read", flush=True)
    rows = old.to_dict("records")
    stack = {}
    with ProcessPoolExecutor(a.workers) as ex:
        futs = [ex.submit(work, *j) for j in jobs]
        for f in as_completed(futs):
            name, y, row = f.result()
            if "error" in row:
                print(name, y, row["date"], "FAILED", row["error"], flush=True)
                continue
            rgb, what = row.pop("_rgb", None), row.pop("_what", None)
            row["year"] = y
            if (name, row["date"]) not in seen:
                rows.append(row)
            if rgb is not None and row["clear"] >= 0.9:
                stack.setdefault((name, y), []).append((row["date"], rgb, what))
            print(name, y, row["date"], row["platform"], "clear", row["clear"], "frame", row["frame"], "km2", row["km2"], flush=True)
            pd.DataFrame(rows).sort_values(["place", "date"]).to_csv(cache, index=False)
    for (name, y), items in stack.items():           # the picture: the median of the summer's clear passes, band by band
        rgb = np.nanmedian(np.stack([i[1] for i in items]), axis=0)
        what = np.nanmean(np.stack([i[2] for i in items]), axis=0)
        np.savez_compressed(OUT / f"{name}_{y}.npz", rgb=rgb.astype(np.float32), what=what.astype(np.float32),
                            dates=np.array([i[0] for i in items]))
        print(f"picture {name} {y}: {len(items)} passes, {np.isnan(rgb[0]).mean() * 100:.2f} % never clear", flush=True)
    df = pd.DataFrame(rows)
    acc = df[df.clear >= 0.9]
    sm = acc.groupby(["place", "year"]).agg(n=("date", "size"), km2=("km2", "median"), lo=("km2", "min"), hi=("km2", "max"))
    sm.to_csv(OUT / "summers.csv")
    print(sm.round(1).to_string())


if __name__ == "__main__":
    main()
