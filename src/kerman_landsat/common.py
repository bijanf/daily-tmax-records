"""The Landsat measurement of the Rafsanjan plain's orchards for the Kerman reel (kerman_fa), written as a
feasibility check on 23 Nov 2026 and kept as it ran (run_all.sh, steps s01..s12, then s13_stage.py for the film).

Keyless Landsat Collection 2 Level-2 access (Microsoft Planetary Computer), as in the
project's src/get_urmia.py: STAC search + anonymous SAS token, windowed COG reads over HTTP.
A generic User-Agent is sent; nothing personal goes into any request."""

from __future__ import annotations

import datetime
import json
import time
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.env import Env
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import Window, from_bounds

HERE = Path(__file__).resolve().parents[2] / "data" / "kerman" / "landsat"   # the data and outputs; the code is in src/kerman_landsat
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/landsat-c2-l2"
UA = "landsat-feasibility-script/1.0"
ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".TIF,.tif",
           GDAL_HTTP_MAX_RETRY="6", GDAL_HTTP_RETRY_DELAY="3", GDAL_HTTP_USERAGENT=UA)
SCALE, OFFSET = 0.0000275, -0.2          # Collection 2 surface reflectance
WGS = CRS.from_epsg(4326)
_token = {"token": None, "expiry": 0.0}


def get(url: str, body: dict | None = None):
    last = None
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                         headers={"Content-Type": "application/json", "User-Agent": UA},
                                         method="POST" if body else "GET")
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except Exception as ex:
            last = ex
            time.sleep(5 * 2 ** attempt)
    raise RuntimeError(f"no answer from {url}: {last!r}")


def signed(href: str) -> str:
    if not _token["token"] or _token["expiry"] - time.time() < 300:
        d = get(SAS)
        e = datetime.datetime.strptime(d["msft:expiry"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        _token.update(token=d["token"], expiry=e.timestamp())
    return "/vsicurl/" + href + "?" + _token["token"]


def search(bbox, start: str, end: str, extra: dict | None = None) -> list:
    """All landsat-c2-l2 items intersecting bbox between two dates (follows pagination)."""
    body = {"collections": ["landsat-c2-l2"], "bbox": list(bbox), "limit": 500,
            "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z"}
    if extra:
        body.update(extra)
    d = get(STAC, body)
    feats = list(d.get("features", []))
    nxt = [l for l in d.get("links", []) if l.get("rel") == "next"]
    while nxt:
        l = nxt[0]
        d = get(l["href"], l.get("body")) if l.get("method", "GET") == "POST" else get(l["href"])
        feats += d.get("features", [])
        nxt = [l for l in d.get("links", []) if l.get("rel") == "next"]
    return feats


def slc_off(feat) -> bool:
    p = feat["properties"]
    return p.get("platform") == "landsat-7" and p["datetime"][:10] >= "2003-05-31"


def tier(feat) -> str:
    return feat["id"].split("_")[-1]                 # T1 / T2 / RT


def path_row(feat) -> str:
    return feat["id"].split("_")[2]


def to_grid(arr, src_t, src_crs, dst_t, dst_crs, shape, method=Resampling.nearest, nodata=0):
    dst = np.full(shape, nodata, dtype=arr.dtype)
    reproject(source=arr, destination=dst, src_transform=src_t, src_crs=src_crs, dst_transform=dst_t,
              dst_crs=dst_crs, resampling=method, src_nodata=nodata, dst_nodata=nodata)
    return dst


def read_window(feat, assets, bounds_ll, decimate: int = 1, dst=None):
    """Read the named assets over a lon/lat box from one scene's COGs.
    Returns dict asset -> array (uint16 DN, 0 = fill), plus the window transform and crs.
    If dst=(transform, crs, shape) is given, every band is reprojected (nearest) onto that grid."""
    a = feat["assets"]
    out = {}
    with Env(**ENV):
        with rasterio.open(signed(a[assets[0]]["href"])) as s0:
            b = transform_bounds(WGS, s0.crs, *bounds_ll)
            win = from_bounds(*b, transform=s0.transform).round_offsets(op="floor").round_lengths(op="ceil")
            win = win.intersection(Window(0, 0, s0.width, s0.height))
            crs = s0.crs
            if decimate > 1:
                h, w = int(win.height) // decimate, int(win.width) // decimate
                win = Window(win.col_off, win.row_off, w * decimate, h * decimate)
                t = s0.window_transform(win) * rasterio.Affine.scale(decimate)
                shape = (h, w)
            else:
                t = s0.window_transform(win)
                shape = (int(win.height), int(win.width))
        for name in assets:
            with rasterio.open(signed(a[name]["href"])) as s:
                if decimate > 1 and name != "qa_pixel":
                    out[name] = s.read(1, window=win, out_shape=shape, resampling=Resampling.average)
                elif decimate > 1:
                    out[name] = s.read(1, window=win, out_shape=shape, resampling=Resampling.nearest)
                else:
                    out[name] = s.read(1, window=win)
    if dst is not None:
        dt, dcrs, dshape = dst
        out = {k: to_grid(v, t, crs, dt, dcrs, dshape) for k, v in out.items()}
        t, crs = dt, dcrs
    return out, t, crs
