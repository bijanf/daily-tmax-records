"""GORGAN BAY FROM LANDSAT: the late-summer water of the bay and its true-colour picture, 1986-2026,
and the Caspian Sea's level from altimetry.

Measured data only:
- Landsat Collection 2 Level-2 surface reflectance (USGS), read from Microsoft's Planetary Computer with
  its anonymous token (the helpers of get_urmia.py), WRS-2 path 163 row 034, 1 August to 30 September
  of each year, on one fixed 30-m grid (0.00034 x 0.00027 deg, about 30 m square at 36.8 N).
- The bay's region (R): JRC Global Surface Water's extent (any water 1984-2021, Pekel et al. 2016) south
  of the barrier's sea-side edge, 53.33-54.10 E and north of 36.78 N. The edge comes from the
  wet-frequency composites of 1995, 2010 and 2025 on a 0.001-deg grid (20 Aug - 10 Oct, path 163 row
  034, eight least cloudy scenes): per longitude, the scan runs south from 36.95 N until three rows in
  a row carry no water in at least half of the clear passes; the edge is the median over the three years,
  smoothed over 2 km. The sea (SEA) is the JRC water north of that edge.
- The Caspian Sea's level: NASA's Global Water Monitor lake 270 (multi-mission altimetry, EGM2008 mean
  sea level; the 10-day series from 1992), downloaded as data/gorgan/caspian_nasa270.txt.

Rules, per year: a scene's clear pixels are those with no fill, dilated cloud, cirrus, cloud or shadow
(QA_PIXEL bits 1-4). A pass counts when at least half of the bay (area-weighted) is clear. Landsat 7
after its scan-line failure (31 May 2003) is left out when another pass counts that year. The picture is
the per-pixel median of the counted passes' reflectance (NaN where no pass is clear). Water = MNDWI > 0
and NIR08 < 0.10 on clear pixels; a pixel is wet when at least half of its clear passes say so. The bay's
area is the wet share of the bay's clear pixels times the bay's area, so cloud does not shrink it.
1995 is one pass only, 8 September 1995 (98 % of the bay clear): the 24 September 1995 scene is Tier 2 and
reads 281 km2 against 559-563 km2 for the three Tier-1 passes; the 7 and 23 August passes have 54 % and 86 %
of the bay clear. Years with one pass, two passes that disagree on the wet rule, striped Landsat 7 only, or
more than a tenth of the bay never clear are flagged in frames.csv: their pictures are shown, their areas
are uncertain. 2007 has no pass with half the bay clear and is left out.

One difference from the feasibility run that the barrier edge came from: its cached JRC extent covered only
53.38-54.12 E, so its lake mask was cropped, and its 1995-08-23 pass read 78 % clear of the lake (here 49.9 %
on the full box, so it is left out). The 1995 composite then has three passes, not four; the edge moves by at
most one 0.001-deg step, the bay by 21 pixels (0.02 km2). Every frame of 1986-2026 except 1995 is identical to
the frames of the fact check of 1 Nov 2026 (its bay areas agree to 0.1 km2).

    python -I src/get_gorgan.py                  # every year (about 30 minutes; the scenes are not cached)
    python -I src/get_gorgan.py 1986 1995        # some years (the tables are rebuilt from all rows)
    python -I src/get_gorgan.py --tables         # frames.csv and scenes.csv from the stored rows

Outputs (data/gorgan/): <year>.npz (rgb, wet, wetfreq, seen, clear_n, items, dates, platforms, transform),
rows/<year>.json (the year's summary and passes), frames.csv, scenes.csv, geometry.npz,
barrier/composite_<year>.npz and barrier/scenes/<item>.npz (cached), caspian_nasa270.txt.
"""

from __future__ import annotations

import csv
import json
import sys
import time
import urllib.request
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.env import Env
from rasterio.transform import Affine, from_origin
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import Window, from_bounds
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from get_urmia import ENV, STAC, get, signed, slc_off  # noqa: E402  (keyless Landsat helpers)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "gorgan"
WGS = CRS.from_epsg(4326)
JRC = "https://storage.googleapis.com/global-surface-water/downloads2021/extent/extent_50E_40Nv1_4_2021.tif"
NASA = "https://earth.gsfc.nasa.gov/gwm/timeseries/lake000270.10d.2.txt"
SCALE, OFFSET = 0.0000275, -0.2                     # Collection 2 surface reflectance
BANDS = ("red", "green", "blue", "nir08", "swir16")
YEARS = list(range(1986, 2027))
BOX = (53.00, 36.62, 54.40, 37.02)                  # W, S, E, N: the frames' grid
DX, DY = 0.00034, 0.00027                           # deg: 30.3 m E-W and 30.0 m N-S at 36.8 N
NX, NY = round((BOX[2] - BOX[0]) / DX), round((BOX[3] - BOX[1]) / DY)
T = from_origin(BOX[0], BOX[3], DX, DY)
LON = BOX[0] + (np.arange(NX) + 0.5) * DX
LAT = BOX[3] - (np.arange(NY) + 0.5) * DY
ROW_KM2 = (DX * 111.32 * np.cos(np.deg2rad(LAT))) * (DY * 111.32)
FEAS = (52.60, 36.70, 54.10, 36.95)                 # W, S, E, N: the barrier's composites
GRID = 0.001                                        # deg: about 100 m
EDGE_N = 36.95                                      # the barrier scan starts here (north of the bay)
COL_LO, COL_HI, LON_MAX, SOUTH_CUT = 53.33, 53.95, 54.10, 36.78
CLEAR_SHARE = 0.5                                   # share of the bay clear: a pass counts
SEARCH_CLOUD = 90                                   # scene cloud cover allowed in the frames' search
SINGLE = {1995: "LT05_L2SP_163034_19950908_02_T1"}  # the one pass used for the year (see the docstring)
VARIANTS = {"base": "wet_base", "thr_minus0.1": "wet_thr_minus0_1", "thr_plus0.1": "wet_thr_plus0_1",
            "noNIR": "wet_noNIR"}                    # sensitivity name -> per-scene key


def jrc_extent(box, name: str):
    """JRC's extent (any water 1984-2021) over a box, 0.02 deg wider on each side, cached in data/gorgan."""
    cache = DATA / f"{name}.npz"
    if cache.exists():
        z = np.load(cache)
        return z["ext"], Affine(*z["transform"])
    w_, s_, e_, n_ = box
    with Env(**ENV), rasterio.open("/vsicurl/" + JRC) as e:
        w = from_bounds(w_ - 0.02, s_ - 0.02, e_ + 0.02, n_ + 0.02, transform=e.transform)
        w = w.round_offsets().round_lengths()
        ext, t = e.read(1, window=w), e.window_transform(w)
    DATA.mkdir(parents=True, exist_ok=True)
    np.savez(cache, ext=ext, transform=np.array(tuple(t)[:6]))
    return ext, t


def on_grid(src: np.ndarray, src_t, dst_t, shape) -> np.ndarray:
    """Nearest-neighbour resampling of a lon/lat raster onto another lon/lat grid (0 outside)."""
    dst = np.full(shape, 0, dtype=src.dtype)
    reproject(source=src, destination=dst, src_transform=src_t, src_crs=WGS, dst_transform=dst_t,
              dst_crs=WGS, resampling=Resampling.nearest, src_nodata=0, dst_nodata=0)
    return dst


# ── the barrier's edge: 0.001-deg composites of three years ──

def feas_search(year: int) -> list:
    """The eight least cloudy scenes of path 163 row 034 over the barrier box, 20 Aug - 10 Oct (cloud <= 60 %)."""
    d = get(STAC, {"collections": ["landsat-c2-l2"], "bbox": list(FEAS), "limit": 300,
                   "datetime": f"{year}-08-20T00:00:00Z/{year}-10-10T23:59:59Z"})
    feats = [f for f in d.get("features", []) if "_163034_" in f["id"]
             and (f["properties"].get("eo:cloud_cover") or 0) <= 60]
    feats = sorted(feats, key=lambda f: f["properties"].get("eo:cloud_cover") or 0)[:8]
    return sorted(feats, key=lambda f: f["properties"]["datetime"])


def feas_arrays(feat) -> dict:
    """One scene on the barrier grid: true colour and the clear masks (120-m overview, QA pooled to 120 m)."""
    cache = DATA / "barrier" / "scenes" / f"{feat['id']}.npz"
    if cache.exists():
        z = np.load(cache)
        return {k: z[k] for k in z.files}
    W, S, E, N = FEAS
    fT = from_origin(W, N, GRID, GRID)
    fshape = (round((N - S) / GRID), round((E - W) / GRID))
    a = feat["assets"]
    with Env(**ENV):
        with rasterio.open(signed(a["qa_pixel"]["href"])) as q:
            b = transform_bounds(WGS, q.crs, W, S, E, N)
            win = from_bounds(*b, transform=q.transform).round_offsets(op="floor").round_lengths(op="ceil")
            win = win.intersection(Window(0, 0, q.width, q.height))
            h, w = int(win.height) // 4, int(win.width) // 4
            win = Window(win.col_off, win.row_off, w * 4, h * 4)
            qa = q.read(1, window=win)
            crs, st = q.crs, q.window_transform(win) * Affine.scale(4)
        dn = {}
        for band in BANDS:
            with rasterio.open(signed(a[band]["href"])) as src:
                dn[band] = src.read(1, window=win, out_shape=(h, w), resampling=Resampling.average).astype(np.float32)
    cloudy = ((qa & 0b11110) > 0).reshape(h, 4, w, 4).any(axis=(1, 3))
    valid = np.all([dn[k] > 0 for k in dn], axis=0)
    valid = ndimage.binary_erosion(valid, iterations=1)
    clear = valid & ~cloudy
    sr = {k: dn[k] * SCALE + OFFSET for k in dn}

    def to_grid(arr, method, nodata):
        dst = np.full(fshape, nodata, dtype=np.float32)
        reproject(source=arr.astype(np.float32), destination=dst, src_transform=st, src_crs=crs,
                  dst_transform=fT, dst_crs=WGS, resampling=method, src_nodata=nodata, dst_nodata=nodata)
        return dst

    rgb = ("red", "green", "blue")
    out = dict(
        rgb_all=np.stack([to_grid(np.where(valid, sr[k], np.nan), Resampling.bilinear, np.nan) for k in rgb]),
        rgb_clr=np.stack([to_grid(np.where(clear, sr[k], np.nan), Resampling.bilinear, np.nan) for k in rgb]),
        nir_clr=to_grid(np.where(clear, sr["nir08"], np.nan), Resampling.bilinear, np.nan),
        swir_clr=to_grid(np.where(clear, sr["swir16"], np.nan), Resampling.bilinear, np.nan),
        clear=to_grid(clear.astype(np.float32), Resampling.nearest, 0) > 0.5,
        valid=to_grid(valid.astype(np.float32), Resampling.nearest, 0) > 0.5,
    )
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, **out)
    return out


def barrier_composite(year: int, lake: np.ndarray) -> tuple:
    """The year's barrier composite: median true colour (filled where no clear pass sees the land) and the
    wet frequency of the clear passes that half-see the bay (rounded share, as the fact check ran it)."""
    ds, wets = [], []
    for f in feas_search(year):
        d = feas_arrays(f)
        G, Sw, Nr = d["rgb_clr"][1], d["swir_clr"], d["nir_clr"]
        ok = np.isfinite(G) & np.isfinite(Sw) & np.isfinite(Nr) & (G + Sw != 0)
        mndwi = np.where(ok, (G - Sw) / np.where(G + Sw == 0, 1, G + Sw), np.nan)
        wet = ok & (mndwi > 0) & (Nr < 0.10)
        share = (d["clear"] & lake).sum() / max(lake.sum(), 1)
        if round(float(share), 3) >= CLEAR_SHARE:
            ds.append(d)
            wets.append(wet)
    if not ds:
        raise RuntimeError(f"barrier {year}: no scene with half of the lake clear")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        rgb = np.nanmedian(np.stack([d["rgb_clr"] for d in ds]), axis=0)
        fb = np.nanmedian(np.stack([d["rgb_all"] for d in ds]), axis=0)
    rgb = np.where(np.isfinite(rgb), rgb, fb)
    clrcnt = np.sum([d["clear"] for d in ds], axis=0)
    wetfreq = np.sum(wets, axis=0) / np.maximum(clrcnt, 1)
    return rgb.astype(np.float16), wetfreq.astype(np.float16), len(ds)


def barrier_lake() -> np.ndarray:
    """JRC's water on the barrier grid (0.001 deg)."""
    W, S, E, N = FEAS
    ext, ext_t = jrc_extent(FEAS, "jrc_extent_barrier")
    shape = (round((N - S) / GRID), round((E - W) / GRID))
    return on_grid(ext, ext_t, from_origin(W, N, GRID, GRID), shape) == 1


def barrier_edge(years=(1995, 2010, 2025)) -> tuple:
    """The sea-side edge of the barrier, latitude per longitude on the 0.001-deg grid (NaN west of 53.33 E)."""
    cache_dir = DATA / "barrier"
    lake = barrier_lake()
    est, lon_f = [], None
    for y in years:
        path = cache_dir / f"composite_{y}.npz"
        if not path.exists():
            cache_dir.mkdir(parents=True, exist_ok=True)
            rgb, wetfreq, n = barrier_composite(y, lake)
            np.savez_compressed(path, rgb=rgb, wetfreq=wetfreq, lake=lake, scenes=n)
            print(f"barrier composite {y}: {n} scenes", flush=True)
        z = np.load(path)
        wf = z["wetfreq"].astype(float)
        rv = np.isfinite(z["rgb"]).all(axis=0)
        H, WD = wf.shape
        lon_f = FEAS[0] + (np.arange(WD) + 0.5) * GRID
        out = np.full(WD, np.nan)
        for j in np.where((lon_f >= COL_LO) & (lon_f <= COL_HI))[0]:
            col = wf[:, j] >= 0.5
            if not col[0:3].any() or not rv[0:3, j].all():
                continue
            r = 0
            while r < H - 3 and (col[r] or col[r + 1] or col[r + 2]):
                r += 1
            out[j] = EDGE_N - r * GRID
        est.append(out)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        edge = np.nanmedian(np.array(est), axis=0)
    ok = np.isfinite(edge)
    idx = np.arange(len(edge))
    ef = np.interp(idx, idx[ok], edge[ok])
    ef = ndimage.median_filter(ef, size=21, mode="nearest")
    ef[lon_f > COL_HI] = ef[lon_f <= COL_HI][-1]
    ef[lon_f < COL_LO] = np.nan
    return lon_f, ef


def geometry() -> dict:
    """The bay (R) and the sea (SEA) on the 30-m grid, with their areas (km2)."""
    path = DATA / "geometry.npz"
    if not path.exists():
        lon_f, ef = barrier_edge()
        ok = np.isfinite(ef)
        ed = np.interp(LON, lon_f[ok], ef[ok])
        ed[LON < COL_LO] = np.nan
        ext, ext_t = jrc_extent(BOX, "jrc_extent_frames")
        lake = on_grid(ext, ext_t, T, (NY, NX)) == 1
        inside = np.isfinite(ed)[None, :] & (LON[None, :] >= COL_LO) & (LON[None, :] <= LON_MAX)
        south = LAT[:, None] < ed[None, :]
        R = lake & inside & south & (LAT[:, None] > SOUTH_CUT)
        SEA = lake & inside & ~south
        np.savez_compressed(path, R=R, SEA=SEA, lake=lake, edge=ed, lon=LON, lat=LAT,
                            transform=np.array(tuple(T)[:6]))
    z = np.load(path)
    R, SEA = z["R"], z["SEA"]
    geo = dict(R=R, SEA=SEA, RA=R * ROW_KM2[:, None], SEAA=SEA * ROW_KM2[:, None])
    geo["R_area"] = float(geo["RA"].sum())
    geo["SEA_area"] = float(geo["SEAA"].sum())
    print(f"grid {NX} x {NY} px; JRC water in the box {float((z['lake'] * ROW_KM2[:, None]).sum()):.1f} km2; "
          f"bay R {geo['R_area']:.1f} km2 ({int(R.sum())} px); sea strip {geo['SEA_area']:.1f} km2", flush=True)
    return geo


# ── the frames: Landsat passes on the 30-m grid ──

def search(year: int) -> list:
    body = {"collections": ["landsat-c2-l2"], "bbox": list(BOX), "limit": 500,
            "datetime": f"{year}-08-01T00:00:00Z/{year}-09-30T23:59:59Z"}
    allf = get(STAC, body).get("features", [])
    if len(allf) >= 500:
        print(f"WARNING {year}: STAC page full, paging needed", flush=True)
    feats = [f for f in allf if "_163034_" in f["id"] and (f["properties"].get("eo:cloud_cover") or 0) <= SEARCH_CLOUD]
    return sorted(feats, key=lambda f: f["properties"]["datetime"])


def scene_arrays(feat) -> dict:
    """True colour and wet flags of one scene on the bay grid (NaN outside its footprint)."""
    a = feat["assets"]
    W, S, E, N = BOX
    with Env(**ENV):
        with rasterio.open(signed(a["qa_pixel"]["href"])) as q:
            b = transform_bounds(WGS, q.crs, W, S, E, N)
            win = from_bounds(*b, transform=q.transform).round_offsets(op="floor").round_lengths(op="ceil")
            win = win.intersection(Window(0, 0, q.width, q.height))
            st, crs = q.window_transform(win), q.crs
            qa = q.read(1, window=win).astype(np.float32)
        dn = {}
        for band in BANDS:
            with rasterio.open(signed(a[band]["href"])) as src:
                arr = src.read(1, window=win).astype(np.float32)
            dn[band] = arr[: qa.shape[0], : qa.shape[1]]

    def to_grid(arr):
        dst = np.full((NY, NX), np.nan, np.float32)
        reproject(source=arr, destination=dst, src_transform=st, src_crs=crs, dst_transform=T, dst_crs=WGS,
                  src_nodata=np.nan, dst_nodata=np.nan, resampling=Resampling.nearest)
        return dst

    qg = to_grid(qa)
    covered = np.isfinite(qg)
    qi = np.where(covered, qg, 1).astype(np.uint16)          # outside the footprint counts as fill
    refl = {}
    for band in BANDS:
        sr = np.where(dn[band] == 0, np.nan, dn[band] * SCALE + OFFSET).astype(np.float32)
        refl[band] = to_grid(sr)
    valid = covered & ((qi & 1) == 0)
    for band in BANDS:
        valid &= np.isfinite(refl[band])
    clear = valid & ((qi & 0b11110) == 0)
    G, Sw, Nir = refl["green"], refl["swir16"], refl["nir08"]
    with np.errstate(all="ignore"):
        mndwi = (G - Sw) / (G + Sw)
    ok = clear & np.isfinite(mndwi)
    return dict(
        rgb=np.stack([np.where(clear, refl[b], np.nan) for b in ("red", "green", "blue")]).astype(np.float16),
        clear=clear,
        wet_base=ok & (mndwi > 0) & (Nir < 0.10),
        wet_thr_minus0_1=ok & (mndwi > -0.1) & (Nir < 0.10),
        wet_thr_plus0_1=ok & (mndwi > 0.1) & (Nir < 0.10),
        wet_noNIR=ok & (mndwi > 0),
    )


def read_one(f):
    err = None
    for attempt in range(3):
        try:
            return scene_arrays(f), None
        except Exception as ex:                          # network hiccups: retry, then log
            err = repr(ex)[:200]
            time.sleep(8 * (attempt + 1))
    return None, err


def run_year(year: int, geo: dict) -> tuple:
    t0 = time.time()
    feats = search(year)
    with ThreadPoolExecutor(4) as pool:
        res = list(pool.map(read_one, feats))
    scenes = []
    for f, (r, err) in zip(feats, res):
        p = f["properties"]
        row = dict(year=year, item=f["id"], date=p["datetime"][:10], platform=p.get("platform"),
                   scene_cloud=p.get("eo:cloud_cover"), striped_L7=bool(slc_off(f)), accepted=False,
                   reason="", bay_clear_share=None, scene_bay_km2=None)
        if r is None:
            row["reason"] = f"read error: {err}"
        else:
            share = float(np.sum(geo["RA"] * r["clear"])) / geo["R_area"]
            row["bay_clear_share"] = round(share, 3)
            if share < CLEAR_SHARE:
                row["reason"] = "bay mostly cloud or no data"
            else:
                row["accepted"] = True
                den = float(np.sum(geo["RA"] * r["clear"]))
                row["scene_bay_km2"] = round(float(np.sum(geo["RA"] * r["wet_base"])) / den * geo["R_area"], 1)
        scenes.append((row, r))
    acc = [(row, r) for row, r in scenes if row["accepted"]]
    if any(not row["striped_L7"] for row, _ in acc):
        for row, _ in acc:
            if row["striped_L7"]:
                row["accepted"], row["reason"] = False, "striped L7 left out: other passes exist"
        acc = [(row, r) for row, r in acc if not row["striped_L7"]]
    else:
        for row, _ in acc:
            if row["striped_L7"]:
                row["reason"] = "only striped L7 passes: kept, flagged"
    if year in SINGLE:
        for row, _ in acc:
            if row["item"] == SINGLE[year]:
                row["reason"] = "the one pass used for this year (98 % of the bay clear)"
            else:
                row["accepted"], row["reason"] = False, f"left out: {year} uses one pass only"
        acc = [(row, r) for row, r in acc if row["item"] == SINGLE[year]]
    summary = dict(year=year, n_considered=len(feats), n_accepted=len(acc),
                   seconds=round(time.time() - t0, 1))
    if not acc:
        summary["note"] = "no accepted pass"
        return summary, [row for row, _ in scenes]
    used = [r for _, r in acc]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        med = np.nanmedian(np.stack([r["rgb"] for r in used]).astype(np.float32), axis=0)
    clear_n = np.sum(np.stack([r["clear"] for r in used]), axis=0, dtype=np.int32)
    seen = clear_n > 0
    freq = {}
    for v, key in VARIANTS.items():
        cnt = np.sum(np.stack([r[key] for r in used]), axis=0, dtype=np.int32)
        freq[v] = np.where(seen, cnt / np.maximum(clear_n, 1), np.nan).astype(np.float32)
    wet = {v: freq[v] >= 0.5 for v in VARIANTS}
    RA, SEAA = geo["RA"], geo["SEAA"]
    seen_area = float(np.sum(RA * seen))
    summary.update(
        items_used=";".join(row["item"] for row, _ in acc),
        dates_used=";".join(row["date"] for row, _ in acc),
        platforms_used="+".join(sorted(set(row["platform"] for row, _ in acc))),
        only_striped_L7=all(row["striped_L7"] for row, _ in acc),
        unseen_share_bay_pct=round(100 * (1 - seen_area / geo["R_area"]), 2),
        bay_wet_km2=round(float(np.sum(RA * wet["base"])) / seen_area * geo["R_area"], 1),
        bay_wet_raw_km2=round(float(np.sum(RA * wet["base"])), 1),
        bay_wet_thr_minus0_1_km2=round(float(np.sum(RA * wet["thr_minus0.1"])) / seen_area * geo["R_area"], 1),
        bay_wet_thr_plus0_1_km2=round(float(np.sum(RA * wet["thr_plus0.1"])) / seen_area * geo["R_area"], 1),
        bay_wet_noNIR_km2=round(float(np.sum(RA * wet["noNIR"])) / seen_area * geo["R_area"], 1),
        sea_strip_wet_km2=round(float(np.sum(SEAA * wet["base"])) / max(float(np.sum(SEAA * seen)), 1e-9)
                                * geo["SEA_area"], 1),
        scene_km2_median=round(float(np.median([row["scene_bay_km2"] for row, _ in acc])), 1),
        scene_km2_min=round(float(min(row["scene_bay_km2"] for row, _ in acc)), 1),
        scene_km2_max=round(float(max(row["scene_bay_km2"] for row, _ in acc)), 1),
        R_area_km2=round(geo["R_area"], 1),
    )
    DATA.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(DATA / f"{year}.npz", rgb=med.astype(np.float16), wet=wet["base"],
                        wetfreq=freq["base"].astype(np.float16), seen=seen,
                        clear_n=np.clip(clear_n, 0, 255).astype(np.uint8),
                        items=np.array([row["item"] for row, _ in acc]),
                        dates=np.array([row["date"] for row, _ in acc]),
                        platforms=np.array([row["platform"] for row, _ in acc]),
                        transform=np.array(tuple(T)[:6]))
    summary["seconds"] = round(time.time() - t0, 1)
    return summary, [row for row, _ in scenes]


# ── the Caspian Sea's level ──

def caspian_file() -> Path:
    """NASA GWM lake 270 as downloaded (the 10-day series, EGM2008 mean sea level), kept as it came."""
    path = DATA / "caspian_nasa270.txt"
    if not path.exists():
        DATA.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(NASA, timeout=120) as r:
            text = r.read()
        assert b"Caspian" in text[:4000], "not the Caspian series"
        path.write_bytes(text)
        print(f"downloaded {NASA} ({len(text)} bytes)", flush=True)
    return path


# ── tables ──

def status_of(s: dict | None) -> tuple:
    """used / flag / left out, with the reasons (as the fact check's analysis labelled them)."""
    if s is None or s.get("n_accepted", 0) == 0:
        why = ("no Landsat pass on path 163 row 034 in 1 Aug-30 Sep" if (s is None or s.get("n_considered", 0) == 0)
               else "no pass with half of the bay clear (striped-L7 rule applied)")
        return "left out", why
    flags = []
    if s.get("only_striped_L7"):
        flags.append("only striped L7 (SLC-off stripes)")
    if s["unseen_share_bay_pct"] > 10:
        flags.append(f"{s['unseen_share_bay_pct']:.0f} % of the bay never clear")
    if s["n_accepted"] == 1:
        flags.append("single pass (scene noise)")
    if s["n_accepted"] == 2:
        flags.append("two passes: wet rule-dependent (>= 0.5 vs > 0.5 differs)")
    return ("flag" if flags else "used"), "; ".join(flags)


def write_tables() -> None:
    rows = [json.loads(f.read_text()) for f in sorted((DATA / "rows").glob("*.json"))]
    summ = {r["summary"]["year"]: r["summary"] for r in rows}
    scenes = [s for r in rows for s in r["scenes"]]
    cols = ["year", "status", "reason", "n_considered", "n_accepted", "items_used", "dates_used", "platforms_used",
            "unseen_share_bay_pct", "bay_wet_km2", "bay_wet_raw_km2", "bay_wet_thr_minus0_1_km2",
            "bay_wet_thr_plus0_1_km2", "bay_wet_noNIR_km2", "sea_strip_wet_km2", "scene_km2_median",
            "scene_km2_min", "scene_km2_max", "R_area_km2"]
    with open(DATA / "frames.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for y in YEARS:
            st, why = status_of(summ.get(y))
            w.writerow(dict(summ.get(y, {"year": y}), year=y, status=st, reason=why))
    keys = ["year", "item", "date", "platform", "scene_cloud", "striped_L7", "bay_clear_share", "accepted",
            "reason", "scene_bay_km2"]
    with open(DATA / "scenes.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for s in sorted(scenes, key=lambda s: (s["year"], s["date"])):
            w.writerow(s)
    print(f"frames.csv: {len(summ)} years with a row; scenes.csv: {len(scenes)} passes", flush=True)


def main(years: list) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    geo = geometry()
    caspian_file()
    (DATA / "rows").mkdir(parents=True, exist_ok=True)
    for y in years:
        summary, scenes = run_year(y, geo)
        (DATA / "rows" / f"{y}.json").write_text(json.dumps(dict(summary=summary, scenes=scenes), default=float))
        print(json.dumps({k: v for k, v in summary.items() if k not in ("items_used", "dates_used")}),
              flush=True)
    write_tables()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--tables":
        write_tables()
    else:
        args = sys.argv[1:]
        main(YEARS if not args else [int(a) for a in args])
