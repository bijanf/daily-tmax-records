"""THE KARUN'S TWO NUMBERS AGAINST A SECOND SATELLITE: the Gotvand lake's open water and the green land south of Ahvaz
in the late summers of 2023-2026 from Sentinel-2 (the clearest date of each) (ESA Copernicus, L2A, via Microsoft's Planetary Computer with its
anonymous token), on get_karun.py's own grids, polygons and tests, beside the Landsat numbers of the same summers.

An independent check of the film's two headline numbers: another satellite, another sensor, another processing chain
(not another kind of observation: both are optical pictures, so this checks the reading, not the idea).

Reflectance = (DN - 1000) / 10000 (processing baseline 04.00 and later). Clear = the scene classification is not
no-data, saturated, cloud, cirrus or snow, and not shadow unless the pixel is water by the test. The bands are
averaged into the 30-m grid cells (B03, B04, B08 from 10 m; B11 from 20 m). A date counts when at least 90 % of the
polygon is clear.

    data/karun/s2.csv     place, date, clear share, km2

    python -I src/karun_s2.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.crs import CRS
from rasterio.env import Env
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import from_bounds
from shapely.geometry import Polygon, shape
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
import get_damsrain as dr  # noqa: E402  (signed, ENV: the Sentinel-2 collection's token)
import get_karun as gk  # noqa: E402
import get_urmia as gu  # noqa: E402

YEARS = range(2023, 2027)
SCL_BAD = {0, 1, 8, 9, 10, 11}
SHADOW = 3


def dates(name: str, year: int) -> list:
    poly = Polygon(gk.PLACES[name]["poly"])
    d = gu.get(gu.STAC, {"collections": ["sentinel-2-l2a"], "bbox": list(poly.bounds), "limit": 300,
                         "datetime": f"{year}-{gk.SEASON[0]}T00:00:00Z/{year}-{gk.SEASON[1]}T23:59:59Z"})
    by = {}
    for f in d.get("features", []):
        by.setdefault(f["properties"]["datetime"][:10], []).append(f)
    out = []
    for day, fs in by.items():
        u = unary_union([shape(f["geometry"]) for f in fs])
        cloud = float(np.mean([f["properties"].get("eo:cloud_cover") or 0 for f in fs]))
        if u.intersection(poly).area / poly.area >= 0.999 and cloud <= 10:
            out.append((cloud, day, fs))
    return sorted(out, key=lambda x: x[0])[:1]


def band(feats: list, key: str, name: str, resampling) -> np.ndarray:
    t, shp = gk.grid(name)
    b = gk.PLACES[name]["box"]
    out = np.full(shp, np.nan, np.float32)
    for f in feats:
        with Env(**dr.ENV), rasterio.open(dr.signed(f["assets"][key]["href"])) as src:
            bb = transform_bounds(CRS.from_epsg(4326), src.crs, *b, densify_pts=21)
            win = from_bounds(*bb, transform=src.transform).round_offsets(op="floor").round_lengths(op="ceil")
            k = max(1, round(gk.M / abs(src.transform.a)))                # read near the grid's own 30 m (the file's overviews),
            shape_ = (max(1, int(win.height) // k), max(1, int(win.width) // k))   # not the 10-m pixels: a tenth of the download
            arr = src.read(1, window=win, boundless=True, fill_value=0, out_shape=shape_,
                           resampling=Resampling.nearest if key == "SCL" else Resampling.average).astype(np.float32)
            st, crs = src.window_transform(win) * rasterio.Affine.scale(win.width / shape_[1], win.height / shape_[0]), src.crs
        arr[arr == 0] = np.nan
        one = np.full(shp, np.nan, np.float32)
        reproject(source=arr, destination=one, src_transform=st, src_crs=crs, dst_transform=t, dst_crs=CRS.from_epsg(4326),
                  resampling=resampling, src_nodata=np.nan, dst_nodata=np.nan)
        out = np.where(np.isnan(out), one, out)
    return out


def measure(name: str, day: str, feats: list) -> dict:
    mk = gk.masks(name)
    poly, near = mk["poly"], mk["near"]
    base = min(float(f["properties"].get("s2:processing_baseline", "0") or 0) for f in feats)
    off = 1000.0 if base >= 4.0 else 0.0
    g, r, nir, sw = ((band(feats, k, name, Resampling.average) - off) / 10000.0 for k in ("B03", "B04", "B08", "B11"))
    scl = band(feats, "SCL", name, Resampling.nearest)
    g, r, nir, sw = (np.clip(x, 1e-4, None) for x in (g, r, nir, sw))
    valid = np.isfinite(g) & np.isfinite(r) & np.isfinite(nir) & np.isfinite(sw) & np.isfinite(scl)
    water = valid & ((g - sw) / (g + sw) > 0) & (sw < 0.15) & (nir < 0.12)
    green = valid & ((nir - r) / (nir + r) > 0.3) & ~water
    s = np.nan_to_num(scl, nan=0).astype(int)
    clear = valid & ~np.isin(s, list(SCL_BAD)) & ((s != SHADOW) | water)
    what = (water & near) if gk.PLACES[name]["what"] == "water" else green
    n_clear = int((clear & poly).sum())
    px = (gk.M / 1000.0) ** 2
    return dict(place=name, date=day, baseline=base, clear=round(n_clear / poly.sum(), 3),
                km2=round(float((what & clear & poly).sum() / max(n_clear, 1) * poly.sum() * px), 1))


def main() -> None:
    rows = []
    for name in gk.PLACES:
        for y in YEARS:
            for cloud, day, fs in dates(name, y):
                row = measure(name, day, fs)
                rows.append(row)
                print(row, flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(gk.OUT / "s2.csv", index=False)
    df["year"] = pd.to_datetime(df.date).dt.year
    s2 = df[df.clear >= 0.9].groupby(["place", "year"]).km2.median().rename("sentinel2")
    ls = pd.read_csv(gk.OUT / "summers.csv").set_index(["place", "year"]).km2.rename("landsat")
    both = pd.concat([ls, s2], axis=1).dropna()
    both["ratio"] = (both.sentinel2 / both.landsat).round(3)
    print(both.round(1).to_string())


if __name__ == "__main__":
    main()
