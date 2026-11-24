"""Step 3: one late-summer (15 Jul - 15 Sep) composite per year on the box's 30-m grid.

Per year and path: up to 4 Tier-1 passes (Landsat 7 after 31 May 2003 left out; scene cloud <= 30 %),
those with scene cloud <= 5 % first, then the nearest to 15 August. Path 161 passes read row 039 and the
same overpass's row 038 (top strip). A pixel is clear when it has data in red and NIR and QA_PIXEL flags
none of fill, dilated cloud, cirrus, cloud, cloud shadow, snow (bits 0-5). NDVI = (NIR - red)/(NIR + red)
from surface reflectance (DN * 0.0000275 - 0.2). The year's NDVI is the per-pixel median over its clear
passes. Zone W of the box is measured from path 161, zone E from path 160 (geom.py).

    python -I s04_year.py 1987 2025 --rgb     # also keep the red/green/blue median for pictures
    python -I s04_year.py 1986 1987 ...       # areas only

Writes results/<year>.json (passes, per-pass and composite areas, coverage) and cache/ndvi_<year>.npz
(NDVI quantised down: q = floor((NDVI + 0.2) / 0.005), 0..240, 255 = not seen; a threshold t that is a
multiple of 0.005 is exactly q >= (t + 0.2) / 0.005, e.g. 0.20/0.25/0.30 -> 80/90/100), nobs; with --rgb
cache/rgb_<year>.npz (median surface reflectance * 10000 as uint16, 0 = none, per path).
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import rasterio
from rasterio.env import Env
from rasterio.transform import Affine
from rasterio.warp import Resampling, reproject
from rasterio.windows import from_bounds, Window

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ENV, SCALE, OFFSET, HERE, signed, slc_off, tier, path_row  # noqa: E402
from geom import T, SHAPE, UTM, PIX_KM2, masks  # noqa: E402

K = 4
THR = (0.15, 0.20, 0.25, 0.30)                   # 0.15: an extra, lower sensitivity check
QA_BAD = 0b111111
RES_DIR = HERE / "results"
CACHE = HERE / "cache"


def items(year: int) -> list:
    return json.loads((HERE / "stac" / f"{year}.json").read_text())


def choose(year: int, pr: str) -> list:
    c = [f for f in items(year) if path_row(f) == pr and tier(f) == "T1" and not slc_off(f)
         and (f["properties"].get("eo:cloud_cover") or 0) <= 30]
    mid = np.datetime64(f"{year}-08-15")
    c.sort(key=lambda f: ((f["properties"].get("eo:cloud_cover") or 0) > 5,
                          abs((np.datetime64(f["properties"]["datetime"][:10]) - mid).astype(int)),
                          f["id"]))
    return c[:K]


def bbox_of(mask: np.ndarray, pad: int = 2):
    rr = np.nonzero(mask.any(axis=1))[0]
    cc = np.nonzero(mask.any(axis=0))[0]
    r0, r1 = max(rr[0] - pad, 0), min(rr[-1] + 1 + pad, SHAPE[0])
    c0, c1 = max(cc[0] - pad, 0), min(cc[-1] + 1 + pad, SHAPE[1])
    return r0, r1, c0, c1


def read_sub(feat, assets, sub):
    """Assets of one scene copied onto the sub-grid rows r0:r1, cols c0:c1 of the box grid (0 = none)."""
    r0, r1, c0, c1 = sub
    st = T * Affine.translation(c0, r0)
    shape = (r1 - r0, c1 - c0)
    xmin, ymax = st * (0, 0)
    xmax, ymin = st * (shape[1], shape[0])
    out = {}
    with Env(**ENV):
        for name in assets:
            with rasterio.open(signed(feat["assets"][name]["href"])) as s:
                assert str(s.crs) == UTM, s.crs
                win = from_bounds(xmin - 60, ymin - 60, xmax + 60, ymax + 60, transform=s.transform)
                win = win.round_offsets(op="floor").round_lengths(op="ceil").intersection(Window(0, 0, s.width, s.height))
                arr = s.read(1, window=win)
                dst = np.zeros(shape, np.uint16)
                reproject(arr, dst, src_transform=s.window_transform(win), src_crs=s.crs, dst_transform=st,
                          dst_crs=s.crs, resampling=Resampling.nearest, src_nodata=0, dst_nodata=0)
                out[name] = dst
    return out


def read_pass(group, assets, sub):
    """A pass = row 039 (+ the same overpass's row 038 for path 161): 039 first, 038 where 039 has no data."""
    d = None
    for f in group:
        for attempt in range(3):
            try:
                x = read_sub(f, assets, sub)
                break
            except Exception as ex:                       # a dropped connection costs one try
                print(f"  retry {f['id']}: {ex!r}"[:200], flush=True)
                time.sleep(10)
        else:
            raise RuntimeError(f"cannot read {f['id']}")
        if d is None:
            d = x
        else:
            fill = d["red"] == 0
            for k in assets:
                d[k] = np.where(fill, x[k], d[k])
    return d


def ndvi_of(d):
    red = d["red"].astype(np.float32) * SCALE + OFFSET
    nir = d["nir08"].astype(np.float32) * SCALE + OFFSET
    clear = (d["red"] > 0) & (d["nir08"] > 0) & ((d["qa_pixel"] & QA_BAD) == 0)
    den = nir + red
    ok = clear & (den > 0)
    nd = np.full(red.shape, np.nan, np.float32)
    nd[ok] = (nir[ok] - red[ok]) / den[ok]
    return nd, d["red"] > 0


def path_composite(year: int, pr: str, zone: np.ndarray, region: np.ndarray, rgb: bool):
    """Median NDVI (and RGB) of the path's chosen passes over region's bbox; per-pass stats over zone."""
    feats = choose(year, pr)
    if not feats:
        return None
    sub = bbox_of(region)
    r0, r1, c0, c1 = sub
    zsub = zone[r0:r1, c0:c1]
    north = {f["properties"]["datetime"][:10]: f for f in items(year) if path_row(f) == "161038" and tier(f) == "T1"}
    assets = ["red", "nir08", "qa_pixel"] + (["green", "blue"] if rgb else [])
    groups = []
    for f in feats:
        g = [f]
        if pr == "161039":
            n = north.get(f["properties"]["datetime"][:10])
            if n is not None:
                g.append(n)
        groups.append(g)
    with ThreadPoolExecutor(4) as pool:
        data = list(pool.map(lambda g: read_pass(g, assets, sub), groups))
    nds, passes = [], []
    zpx = int(zsub.sum())
    for g, d in zip(groups, data):
        nd, has = ndvi_of(d)
        clear = np.isfinite(nd) & zsub
        cp = int(clear.sum())
        rec = dict(items=[f["id"] for f in g], date=g[0]["properties"]["datetime"][:10],
                   platform=g[0]["properties"]["platform"], scene_cloud=g[0]["properties"].get("eo:cloud_cover"),
                   zone_data_frac=round(float((has & zsub).sum()) / zpx, 5), zone_clear_frac=round(cp / zpx, 5))
        for t in THR:
            n = int((clear & (nd >= t)).sum())
            rec[f"veg_px_thr{t:.2f}"] = n
            rec[f"veg_km2_scaled_thr{t:.2f}"] = round(n / cp * zpx * PIX_KM2, 2) if cp else None
        dz = nd[clear & (nd < 0.15)]
        rec["desert_ndvi_median"] = round(float(np.median(dz)), 4) if dz.size else None
        passes.append(rec)
        nds.append(nd)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        stack = np.stack(nds)
        med = np.nanmedian(stack, axis=0)
        nobs = np.isfinite(stack).sum(axis=0).astype(np.uint8)
        del stack
        rgbm = None
        if rgb:
            rgbm = []
            for b in ("red", "green", "blue"):
                s = np.stack([np.where(np.isfinite(nd), d[b].astype(np.float32) * SCALE + OFFSET, np.nan)
                              for nd, d in zip(nds, data)])
                rgbm.append(np.nanmedian(s, axis=0))
                del s
            rgbm = np.stack(rgbm)
    return dict(sub=sub, med=med, nobs=nobs, rgb=rgbm, passes=passes)


def run(year: int, rgb: bool) -> None:
    out_json = RES_DIR / f"{year}.json"
    if out_json.exists() and not rgb:
        print(year, "cached", flush=True)
        return
    m = masks()
    t0 = time.time()
    full = np.full(SHAPE, np.nan, np.float32)
    nobs = np.zeros(SHAPE, np.uint8)
    res = dict(year=year, zones={})
    rgb_store = {}
    for zname, pr, zone, region in (("W", "161039", m["zw"], m["zw"]),
                                    ("E", "160039", m["ze"], m["in160"] if rgb else m["ze"])):
        pc = path_composite(year, pr, zone, region, rgb)
        if pc is None:
            res["zones"][zname] = dict(path_row=pr, passes=[], available=False)
            continue
        r0, r1, c0, c1 = pc["sub"]
        zsub = zone[r0:r1, c0:c1]
        tgt = full[r0:r1, c0:c1]
        tgt[zsub] = pc["med"][zsub]
        nobs[r0:r1, c0:c1][zsub] = pc["nobs"][zsub]
        zpx = int(zsub.sum())
        medz = pc["med"][zsub]
        seen = np.isfinite(medz)
        z = dict(path_row=pr, available=True, passes=pc["passes"], zone_px=zpx, zone_km2=round(zpx * PIX_KM2, 2),
                 unseen_px=int((~seen).sum()), unseen_frac=round(float((~seen).mean()), 6))
        for t in THR:
            n = int((medz >= t).sum())                    # NaN >= t is False
            z[f"veg_px_thr{t:.2f}"] = n
            z[f"veg_km2_thr{t:.2f}"] = round(n * PIX_KM2, 3)
        h, e = np.histogram(medz[seen], bins=np.arange(-0.2, 1.0001, 0.005))
        z["ndvi_mode"] = round(float(e[np.argmax(h)] + 0.0025), 4)
        z["desert_ndvi_median"] = round(float(np.median(medz[seen & (medz < 0.15)])), 4)
        res["zones"][zname] = z
        if rgb:
            rgb_store[zname] = (pc["sub"], pc["rgb"])
    q = np.full(SHAPE, 255, np.uint8)
    ok = np.isfinite(full)
    q[ok] = np.clip(np.floor((full[ok].astype(np.float64) + 0.2) / 0.005 + 1e-6), 0, 240).astype(np.uint8)
    CACHE.mkdir(exist_ok=True)
    np.savez_compressed(CACHE / f"ndvi_{year}.npz", q=q, nobs=nobs)
    if rgb:
        z = {}
        for zname, (sub, arr) in rgb_store.items():
            a = np.where(np.isfinite(arr), np.clip(arr, 0, 1) * 10000, 0).astype(np.uint16)
            z[f"rgb_{zname}"] = a
            z[f"sub_{zname}"] = np.array(sub)
        np.savez_compressed(CACHE / f"rgb_{year}.npz", **z)
    res["seconds"] = round(time.time() - t0, 1)
    RES_DIR.mkdir(exist_ok=True)
    out_json.write_text(json.dumps(res, indent=1))
    zs = res["zones"]
    msg = " | ".join(f"{k}: {len(v['passes'])} passes, unseen {v.get('unseen_frac')}, "
                     f"veg25 {v.get('veg_km2_thr0.25')} km2" for k, v in zs.items())
    print(year, msg, f"({res['seconds']} s)", flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    rgb = "--rgb" in args
    years = [int(a) for a in args if a.isdigit()]
    for y in years:
        run(y, rgb)
