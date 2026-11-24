"""The measuring box, the 30-m grid and the two path zones.

Box (lon/lat): 55.10-56.45 E, 30.15-31.03 N, minus its north-east corner east of 56.15 E and north of
30.60 N (the Zarand plain's orchard belt, a different basin, enters there).
Grid: UTM 40N (EPSG:32640, the CRS of every path 160/161 row 039 scene), 30 m, pixel corners on the
Landsat Collection 2 lattice (15 m mod 30 m), so scene pixels copy one-to-one onto it.
Zones: W = inside every Tier-1, non-SLC-off path 161 row 039 footprint of 15 Jul - 15 Sep 1986-2025,
shrunk by 0.01 deg, or inside every such path 161 row 038 footprint (same overpass, the next scene
north; it fills the box's top strip), shrunk alike; E = the rest of the box, which must lie inside
every path 160 row 039 footprint (shrunk by 0.01 deg). Path 161 measures zone W, path 160 zone E.
"""
from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import shapely
from pyproj import Transformer
from rasterio.features import geometry_mask
from rasterio.transform import Affine
from rasterio.warp import transform_bounds
from shapely.geometry import shape, box as sbox
from shapely.ops import transform as stransform

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HERE, WGS, slc_off, tier, path_row  # noqa: E402

BOX = (55.10, 30.15, 56.45, 31.03)                      # W S E N
NE_CUT = (56.15, 30.60)                                  # excluded: lon > 56.15 and lat > 30.60
UTM = "EPSG:32640"
RES = 30.0
WINDOW = ("07-15", "09-15")
PIX_KM2 = 0.0009


def _grid():
    xmin, ymin, xmax, ymax = transform_bounds(WGS, UTM, *BOX, densify_pts=101)
    x0 = np.floor((xmin - 15) / 30) * 30 + 15
    y1 = np.ceil((ymax - 15) / 30) * 30 + 15
    x1 = np.ceil((xmax - 15) / 30) * 30 + 15
    y0 = np.floor((ymin - 15) / 30) * 30 + 15
    T = Affine(RES, 0, x0, 0, -RES, y1)
    shape_ = (int(round((y1 - y0) / RES)), int(round((x1 - x0) / RES)))
    return T, shape_


T, SHAPE = _grid()
_to_ll = Transformer.from_crs(UTM, "EPSG:4326", always_xy=True)
_to_utm = Transformer.from_crs("EPSG:4326", UTM, always_xy=True)


def candidates() -> list:
    """Every cached STAC item (s03_inventory.py) usable for measurement: Tier 1, not Landsat 7 SLC-off."""
    out = []
    for f in sorted((HERE / "stac").glob("*.json")):
        for it in json.loads(f.read_text()):
            if tier(it) == "T1" and not slc_off(it):
                out.append(it)
    return out


@lru_cache(None)
def masks() -> dict:
    cache = HERE / "cache" / "geom.npz"
    if cache.exists():
        z = np.load(cache)
        return {k: z[k] for k in z.files}
    rows, cols = np.mgrid[0:SHAPE[0], 0:SHAPE[1]]
    x, y = T * (cols + 0.5, rows + 0.5)
    lon, lat = _to_ll.transform(x, y)
    inbox = (lon >= BOX[0]) & (lon <= BOX[2]) & (lat >= BOX[1]) & (lat <= BOX[3]) & \
        ~((lon > NE_CUT[0]) & (lat > NE_CUT[1]))
    feats = candidates()
    p161 = [shape(f["geometry"]) for f in feats if path_row(f) == "161039"]
    p161n = [shape(f["geometry"]) for f in feats if path_row(f) == "161038"]
    p160 = [shape(f["geometry"]) for f in feats if path_row(f) == "160039"]
    w_ll = shapely.union(shapely.intersection_all(p161).buffer(-0.01), shapely.intersection_all(p161n).buffer(-0.01))
    e_ll = shapely.intersection_all(p160).buffer(-0.01)
    proj = lambda g: stransform(lambda a, b: _to_utm.transform(a, b), g)
    zw = geometry_mask([proj(w_ll)], SHAPE, T, invert=True) & inbox
    in160 = geometry_mask([proj(e_ll)], SHAPE, T, invert=True)
    ze = inbox & ~zw & in160
    uncovered = inbox & ~zw & ~in160
    out = dict(inbox=inbox, zw=zw, ze=ze, uncovered=uncovered, in160=in160 & inbox,
               lon=lon.astype(np.float32), lat=lat.astype(np.float32))
    cache.parent.mkdir(exist_ok=True)
    np.savez_compressed(cache, **out)
    return out


if __name__ == "__main__":
    m = masks()
    print("grid", SHAPE, T)
    for k in ("inbox", "zw", "ze", "uncovered"):
        print(k, int(m[k].sum()), "px", round(m[k].sum() * PIX_KM2, 1), "km2")
