"""Helpers to load cached composites and render quick-look PNGs (inspection only)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HERE  # noqa: E402
from geom import T, SHAPE, masks  # noqa: E402
from pyproj import Transformer

CACHE = HERE / "cache"
_to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32640", always_xy=True)


def ndvi(year: int) -> np.ndarray:
    """The cached median NDVI at the centre of its 0.005 bin, so `ndvi >= t` for t a multiple of 0.005
    is exactly the float test of s04_year.py."""
    q = np.load(CACHE / f"ndvi_{year}.npz")["q"]
    out = np.where(q == 255, np.nan, (q.astype(np.float32) + 0.5) * 0.005 - 0.2)
    return out


def rgb(year: int, feather_px: int = 100) -> np.ndarray:
    """Full-grid median RGB reflectance (3, H, W), path 161 in zone W, path 160 in zone E, blended
    linearly over feather_px pixels west of zone E where path 160 also has data."""
    from scipy import ndimage
    z = np.load(CACHE / f"rgb_{year}.npz")
    m = masks()
    out = np.full((3,) + SHAPE, np.nan, np.float32)
    lay = {}
    for k in ("W", "E"):
        if f"rgb_{k}" not in z:
            continue
        r0, r1, c0, c1 = z[f"sub_{k}"]
        a = z[f"rgb_{k}"].astype(np.float32) / 10000
        a[a == 0] = np.nan
        full = np.full((3,) + SHAPE, np.nan, np.float32)
        full[:, r0:r1, c0:c1] = a
        lay[k] = full
    if "W" in lay and "E" in lay:
        d = ndimage.distance_transform_edt(~m["ze"])          # px from zone E
        w = np.clip(1 - d / feather_px, 0, 1).astype(np.float32)
        w = np.where(np.isnan(lay["E"][0]), 0, w)
        w = np.where(np.isnan(lay["W"][0]), 1, w)
        out = np.where(w[None] > 0, np.nan_to_num(lay["E"]) * w + np.nan_to_num(lay["W"]) * (1 - w), lay["W"])
        out = np.where(np.isnan(lay["W"]) & np.isnan(lay["E"]), np.nan, out)
    else:
        out = lay.get("W", lay.get("E"))
    return out


def rc(lon: float, lat: float):
    x, y = _to_utm.transform(lon, lat)
    c, r = ~T * (x, y)
    return int(r), int(c)


def crop_ll(arr, w, s, e, n):
    r0, c0 = rc(w, n)
    r1, c1 = rc(e, s)
    r0, r1 = max(min(r0, r1), 0), min(max(r0, r1), SHAPE[0])
    c0, c1 = max(min(c0, c1), 0), min(max(c0, c1), SHAPE[1])
    return arr[..., r0:r1, c0:c1]


def stretch(rgbarr, lo, hi, gamma=1.0):
    x = (rgbarr - np.asarray(lo)[:, None, None]) / (np.asarray(hi) - np.asarray(lo))[:, None, None]
    x = np.clip(x, 0, 1) ** (1 / gamma)
    return np.nan_to_num(x.transpose(1, 2, 0), nan=0)
