"""TEHRAN AND ISTANBUL, WINTER NO2 FROM SPACE: the pre-registered comparison behind onebit_compare.py.

Sentinel-5P TROPOMI OFFL L2 NO2 (processor 02.09.01), the winter of 1404 (Azar to Bahman: 22 November 2025 to
19 February 2026), valid pixels only (qa_value >= 0.75). Each pixel is spread over its footprint on a 0.02-degree
lattice (16 sub-points per pixel, as air_grid.py); the cell values are the area-weighted NO2 columns in
1e15 molec/cm2 (mol/m2 x 6.02214e19 / 1e15). Each day is one valid day when its box holds at least 3 valid pixel
centres. The box is the centre +- 0.15 deg (the sensitivities: +- 0.25 deg; Istanbul also centred on its land maximum).

Metrics (preregistration.md, written before the full-window results):
  PRIMARY  day-mean: the mean over valid days of each day's box mean (every day weighs the same)
  ratio    Tehran / Istanbul, 90 % bootstrap over days (10,000 resamples, seed 1405)
  Istanbul land only: the cells whose land fraction (Natural Earth 10 m land, 5 x 5 sub-points) is at least 0.5;
  the Golden Horn and the Bosphorus are water and drop out; Tehran's box is all land.
  The pre-registered primary box kept the water cells (Istanbul 10.1 on 38 days, Tehran / Istanbul 7.14,
  90 % 5.64-9.28); removing them was a pre-registered check and is the headline, because it gives the lower ratio.

Inputs: data/air/compare/pix/<granule>.npz (per-pixel records within +-0.40 deg of each centre, written here or
seeded from the pre-registration's cache, see SEED). Outputs: data/air/compare/items.json, cells.npz,
compare_v1.json and compare_v1.log. Nothing outside data/air/compare is written.

    python -I src/air_compare.py              # all steps (reads the missing granules, 3 readers)
    python -I src/air_compare.py --offline    # cached granules only
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import air  # noqa: E402
import air_grid  # noqa: E402
import get_air  # noqa: E402
from air_grid import corners  # noqa: E402

COMP = air.DATA / "compare"
PIX = COMP / "pix"
ITEMS = COMP / "items.json"
CELLS = COMP / "cells.npz"
RESULT = COMP / "compare_v1.json"
LOG = COMP / "compare_v1.log"
SEED = Path(os.environ.get("AIR_COMPARE_SEED",      # optional: the pre-registration's per-pixel cache to copy from
                           Path(__file__).resolve().parents[1] / "data" / "air" / "compare" / "seed"))
CITY = {"tehran": (51.39, 35.69), "istanbul": (28.98, 41.01)}
STEP = 0.02                                       # deg: the lattice
PH = 0.40                                         # deg: a pixel is read when its centre lies within this of a centre
BOX, SENS = 0.15, 0.25                            # deg: the metric box and the wider sensitivity box
GRID_HALF = 0.45                                  # deg: the cell grid (covers the film's tiles and the +-0.35 search)
WINTER = ("2025-11-22", "2026-02-19")
MONTH_KEYS = ("1404-09", "1404-10", "1404-11")    # Azar, Dey, Bahman
WMIN = 0.05                                       # a cell has data above this weight (pixel units), as air_grid.py
SMOOTH = 1.0                                      # cells: the field's smoothing
BOOT_SEED = 1405
PRE = dict(tehran=(72.2, 61), istanbul_land=(12.4, 31), ratio=(5.82, (4.54, 7.68)))   # the verified headline values
PRE_PRIMARY = dict(istanbul_all_cells=(10.1, 38), ratio=(7.14, (5.64, 9.28)),
                   note="the pre-registered primary box kept the water cells; the headline uses the land-only box")
HORN = (28.955, 41.022, 29.015, 41.040)   # the Golden Horn (Haliç) burned in as water: W, S, E, N, its middle channel
LOGLINES: list = []


def say(*a) -> None:
    line = " ".join(str(x) for x in a)
    print(line, flush=True)
    LOGLINES.append(line)


# ── the granules: search (get_air's STAC search), read, cache ──

def search() -> list:
    """OFFL granules over both city boxes (+- 0.45 deg) in the winter window, as the scratch search."""
    rows = {}
    for c, (cx, cy) in CITY.items():
        bbox = [cx - PH - 0.05, cy - PH - 0.05, cx + PH + 0.05, cy + PH + 0.05]
        body = {"collections": ["sentinel-5p-l2-netcdf"], "bbox": bbox,
                "datetime": f"{WINTER[0]}T00:00:00Z/{WINTER[1]}T23:59:59Z", "limit": 500,
                "query": {"s5p:product_type": {"eq": "L2__NO2___"}}}
        page, feats = get_air.call(f"{get_air.STAC}/search", body), []
        for _ in range(100):
            feats += page.get("features", [])
            nxt = next((x for x in page.get("links", []) if x.get("rel") == "next"), None)
            if not nxt:
                break
            page = (get_air.call(nxt["href"], nxt.get("body")) if nxt.get("method") == "POST"
                    else get_air.call(nxt["href"]))
        for f in feats:
            if f["properties"].get("s5p:processing_mode") != "OFFL":
                continue
            rows.setdefault(f["id"], dict(id=f["id"], datetime=f["properties"]["datetime"], mode="OFFL",
                                          href=next(iter(f["assets"].values()))["href"]))
        say(f"search {c}: {len(feats)} granules, OFFL so far {len(rows)}")
    out = sorted(rows.values(), key=lambda r: r["datetime"])
    ITEMS.write_text(json.dumps(out))
    return out


def seed() -> int:
    """Copy the pre-registration's per-pixel cache for granules not yet here (it carries the same fields)."""
    n = 0
    src = SEED / "pix"
    if not src.is_dir():
        return 0
    PIX.mkdir(parents=True, exist_ok=True)
    for f in src.glob("*.npz"):
        dst = PIX / f.name
        if dst.exists():
            continue
        with np.load(f) as z:
            if "clat" in z.files:
                shutil.copy(f, dst)
                n += 1
    return n


def read_one(row: dict) -> dict:
    """One granule's pixels within PH of each centre, with the footprint corners (the scratch read_box rule)."""
    import h5py
    gid = row["id"]
    path = PIX / f"{gid}.npz"
    if path.exists():
        return dict(id=gid, status="cached")
    last = None
    for attempt in range(4):
        try:
            f = h5py.File(get_air.RangeFile(get_air.sas_url(row["href"])), "r")
            p = f["PRODUCT"]
            lat_all, lon_all = p["latitude"][0], p["longitude"][0]
            near = np.zeros(lat_all.shape[0], bool)
            for cx, cy in CITY.values():
                near |= ((np.abs(lat_all - cy) < PH + 0.1) & (np.abs(lon_all - cx) < PH + 0.1)).any(axis=1)
            rows = np.flatnonzero(near)
            PIX.mkdir(parents=True, exist_ok=True)
            if rows.size == 0:
                np.savez(path, n=np.array(0))
                return dict(id=gid, status="none")
            r0, r1 = int(rows.min()), int(rows.max()) + 1
            a0, a1 = max(r0 - 1, 0), min(lat_all.shape[0], r1 + 1)
            la = lat_all[a0:a1].astype(np.float64)
            lo = lon_all[a0:a1].astype(np.float64)
            raw = p["qa_value"][0, a0:a1, :]
            qa = np.where(raw == 255, np.nan, raw.astype(np.float64) * 0.01)
            no2 = p["nitrogendioxide_tropospheric_column"][0, a0:a1, :].astype(np.float64)
            amf = p["air_mass_factor_troposphere"][0, a0:a1, :].astype(np.float64)
            cf = p["SUPPORT_DATA/INPUT_DATA/cloud_fraction_crb"][0, a0:a1, :].astype(np.float64)
            snow = p["SUPPORT_DATA/INPUT_DATA/snow_ice_flag"][0, a0:a1, :].astype(np.float64)
            alb_w = p["SUPPORT_DATA/INPUT_DATA/surface_albedo_nitrogendioxide_window"][0, a0:a1, :].astype(np.float64)
            cla, clo = corners(la), corners(lo)
            C = {k: [] for k in ("lat", "lon", "clat", "clon", "qa", "no2", "amf", "cf", "snow", "alb_w", "city",
                                 "row", "col")}
            for ci, (cx, cy) in enumerate(CITY.values()):
                ii, jj = np.nonzero((np.abs(la - cy) < PH) & (np.abs(lo - cx) < PH))
                if ii.size == 0:
                    continue
                C["lat"].append(la[ii, jj])
                C["lon"].append(lo[ii, jj])
                C["clat"].append(np.stack([cla[ii, jj], cla[ii, jj + 1], cla[ii + 1, jj + 1], cla[ii + 1, jj]], -1))
                C["clon"].append(np.stack([clo[ii, jj], clo[ii, jj + 1], clo[ii + 1, jj + 1], clo[ii + 1, jj]], -1))
                for k, arr in (("qa", qa), ("no2", no2), ("amf", amf), ("cf", cf), ("snow", snow), ("alb_w", alb_w)):
                    C[k].append(arr[ii, jj])
                C["city"].append(np.full(ii.size, ci))
                C["row"].append(ii + a0)
                C["col"].append(jj)
            cat = {k: (np.concatenate(v) if v else np.zeros(0)) for k, v in C.items()}
            tmp = PIX / f"{gid}.part.npz"
            np.savez_compressed(tmp, n=np.array(cat["lat"].size), datetime=np.array(row["datetime"]),
                                mode=np.array("OFFL"), lat=cat["lat"], lon=cat["lon"], clat=cat["clat"].reshape(-1, 4),
                                clon=cat["clon"].reshape(-1, 4), qa=cat["qa"], no2=cat["no2"], amf=cat["amf"],
                                cf=cat["cf"], snow=cat["snow"], alb_w=cat["alb_w"], city=cat["city"].astype(int),
                                row=cat["row"].astype(int), col=cat["col"].astype(int))
            tmp.replace(path)
            return dict(id=gid, status="ok", n=int(cat["lat"].size))
        except Exception as ex:  # noqa: BLE001
            last = repr(ex)[:200]
            time.sleep(20 * (attempt + 1))
    return dict(id=gid, status="error", err=last)


def fetch(items: list, offline: bool) -> None:
    missing = [r for r in items if not (PIX / f"{r['id']}.npz").exists()]
    say(f"granules {len(items)}, cached {len(items) - len(missing)}, to read {len(missing)} (offline={offline})")
    if missing and offline:
        raise SystemExit(f"{len(missing)} granules not cached; run without --offline")
    stat: dict = {}
    if missing:
        with ProcessPoolExecutor(max_workers=3) as ex:
            for fu in as_completed([ex.submit(read_one, r) for r in missing]):
                res = fu.result()
                stat[res["status"]] = stat.get(res["status"], 0) + 1
                if res["status"] == "error":
                    say("ERROR", res)
    say("read status", stat)


# ── land and the cell grid ──

def lattice(cx: float, cy: float, half: float = GRID_HALF):
    """Cell edges on the 0.02-degree lattice, the cell centres ascending (the scratch mask rule)."""
    i0, i1 = int(np.floor((cx - half) / STEP)), int(np.ceil((cx + half) / STEP))
    j0, j1 = int(np.floor((cy - half) / STEP)), int(np.ceil((cy + half) / STEP))
    lon = (np.arange(i0, i1) + 0.5) * STEP
    lat = (np.arange(j0, j1) + 0.5) * STEP
    return lon, lat


def land_fraction(name: str) -> dict:
    """Land fraction of each cell from Natural Earth 10 m land (25 sub-points per cell)."""
    import geopandas as gpd
    from shapely import contains_xy
    shp = str(air_grid.NE / "ne_10m_land.shp")
    bbox = {"istanbul": (27.0, 39.5, 30.5, 42.5), "tehran": (50.0, 34.5, 52.5, 36.8)}[name]
    geom = gpd.read_file(shp, bbox=bbox).geometry.union_all()
    cx, cy = CITY[name]
    lon, lat = lattice(cx, cy)
    LO, LA = np.meshgrid(lon, lat)
    frac = np.zeros(LO.shape)
    s = (np.arange(5) + 0.5) / 5 - 0.5
    for a in s:
        for b in s:
            frac += contains_xy(geom, LO + a * STEP, LA + b * STEP)
    frac /= 25
    if name == "istanbul":                        # the Golden Horn burned in as water: the cells of the Haliç's
        h = (LO > HORN[0]) & (LO < HORN[2]) & (LA > HORN[1]) & (LA < HORN[3])     # middle channel (W, S, E, N)
        frac[h] = 0.0
    return dict(lon=lon, lat=lat, frac=frac)


def check_mask(name: str, m: dict) -> None:
    """Against the pre-registration's mask (same lattice and method, a different land file): the cells must agree."""
    ref = SEED / f"mask_{name}.npz"
    if not ref.exists():
        say(f"mask {name}: no pre-registration mask to compare")
        return
    z = np.load(ref)
    lon_ix = [int(np.argmin(np.abs(z["lon"] - x))) for x in m["lon"]]
    lat_ix = [int(np.argmin(np.abs(z["lat"] - y))) for y in m["lat"]]
    b = z["frac"][np.ix_(lat_ix, lon_ix)]
    a = m["frac"]
    diff = np.abs(a - b)
    say(f"mask {name}: cells {a.size}, land cells (frac>=0.5) {int((a >= 0.5).sum())} vs "
        f"{int((b >= 0.5).sum())} in the pre-registration, max |difference| {diff.max():.3f}, cells differing in "
        f"class {int(((a >= 0.5) != (b >= 0.5)).sum())}")


# ── the per-day cell sums and the pixel records ──

def build_cells(items: list) -> dict:
    lon_e, lat_e = {}, {}
    masks = {}
    for c, (cx, cy) in CITY.items():
        m = land_fraction(c)
        check_mask(c, m)
        masks[c] = m
        lon_e[c] = m["lon"][0] - STEP / 2
        lat_e[c] = m["lat"][0] - STEP / 2
    days = sorted({r["datetime"][:10] for r in items if air.jkey(r["datetime"][:10]) in air.WINTER_JK})
    day_i = {d: k for k, d in enumerate(days)}
    S = {c: np.zeros((len(days), masks[c]["lat"].size, masks[c]["lon"].size)) for c in CITY}
    W = {c: np.zeros((len(days), masks[c]["lat"].size, masks[c]["lon"].size)) for c in CITY}
    recs = {k: [] for k in ("city", "day", "lat", "lon", "valid", "no2c", "amf", "landc", "qa")}
    n_gran = 0
    for r in items:
        f = PIX / f"{r['id']}.npz"
        if not f.exists():
            say("missing", f.name)
            continue
        z = np.load(f)
        if int(z["n"]) == 0:
            continue
        day = str(z["datetime"])[:10]
        if day not in day_i:
            continue
        n_gran += 1
        k = day_i[day]
        for ci, c in enumerate(CITY):
            sel = z["city"] == ci
            if not sel.any():
                continue
            lat, lon = z["lat"][sel], z["lon"][sel]
            qa, no2 = z["qa"][sel], z["no2"][sel]
            valid = np.isfinite(no2) & (np.abs(no2) < get_air.FILL) & (qa >= air.QA_MIN)
            ny_c, nx_c = masks[c]["lat"].size, masks[c]["lon"].size
            ii = np.flatnonzero(valid)
            if ii.size:
                clat, clon = z["clat"][sel][ii], z["clon"][sel][ii]
                no2c = no2[ii] * air.K
                lat_s = sum(clat[:, q:q + 1] * W_SUB[q][None, :] for q in range(4))
                lon_s = sum(clon[:, q:q + 1] * W_SUB[q][None, :] for q in range(4))
                ix = np.floor((lon_s - lon_e[c]) / STEP).astype(np.int64)
                iy = np.floor((lat_s - lat_e[c]) / STEP).astype(np.int64)
                ok = (ix >= 0) & (ix < nx_c) & (iy >= 0) & (iy < ny_c)
                cell = (iy * nx_c + ix)[ok]
                val = np.broadcast_to((no2c / W_SUB[0].size)[:, None], lat_s.shape)[ok]
                S[c][k] += np.bincount(cell, weights=val, minlength=ny_c * nx_c).reshape(ny_c, nx_c)
                W[c][k] += np.bincount(cell, weights=np.full(cell.shape, 1.0 / W_SUB[0].size),
                                       minlength=ny_c * nx_c).reshape(ny_c, nx_c)
            ixc = np.floor((lon - lon_e[c]) / STEP).astype(int)
            iyc = np.floor((lat - lat_e[c]) / STEP).astype(int)
            inside = (ixc >= 0) & (ixc < nx_c) & (iyc >= 0) & (iyc < ny_c)
            landc = np.zeros(lon.size, bool)
            landc[inside] = masks[c]["frac"][iyc[inside], ixc[inside]] >= 0.5
            recs["city"].append(np.full(lon.size, ci))
            recs["day"].append(np.full(lon.size, k))
            recs["lat"].append(lat)
            recs["lon"].append(lon)
            recs["valid"].append(valid)
            recs["no2c"].append(np.where(valid, no2 * air.K, np.nan))
            recs["amf"].append(z["amf"][sel])
            recs["landc"].append(landc)
            recs["qa"].append(qa)
    say(f"granules with pixels in the window: {n_gran}; winter days: {len(days)}")
    cat = {k: np.concatenate(v) for k, v in recs.items()}
    return dict(days=np.array(days), S=S, W=W, masks=masks, pix=cat)


W_SUB = air_grid._subpoints()   # 16 sub-points per pixel (air_grid's footprint rule)


def day_table(data: dict, c: str, half: float, land: bool, centre: tuple | None = None) -> dict:
    """Per valid day: the box value (cell sums ratio) and the valid pixel count; the pooled mean over all days."""
    cx, cy = centre if centre else CITY[c]
    m = data["masks"][c]
    LO, LA = np.meshgrid(m["lon"], m["lat"])
    cellm = (np.abs(LO - cx) < half) & (np.abs(LA - cy) < half)
    if land:
        cellm &= m["frac"] >= 0.5
    p = data["pix"]
    ci = list(CITY).index(c)
    pm = (p["city"] == ci) & (np.abs(p["lon"] - cx) < half) & (np.abs(p["lat"] - cy) < half) & p["valid"]
    if land:
        pm &= p["landc"]
    nv = np.bincount(p["day"][pm], minlength=len(data["days"]))
    SS = data["S"][c][:, cellm].sum(1)
    WW = data["W"][c][:, cellm].sum(1)
    out = {}
    for k, d in enumerate(data["days"]):
        out[str(d)] = dict(val=float(SS[k] / WW[k]) if WW[k] > 0 else np.nan, nv=int(nv[k]))
    valid = {d: v["val"] for d, v in out.items() if v["nv"] >= 3 and np.isfinite(v["val"])}
    pooled = float(SS.sum() / WW.sum()) if WW.sum() > 0 else np.nan
    return dict(tab=out, valid=valid, pooled=pooled, n=len(valid),
                mean=float(np.mean(list(valid.values()))), median=float(np.median(list(valid.values()))))


def ratio_ci(a: dict, b: dict, n: int = 10000):
    """Tehran / Istanbul ratio of the day-means, 90 % bootstrap over days (fresh seed per call, as analyse.py)."""
    rng = np.random.default_rng(BOOT_SEED)
    A = np.array(list(a.values()))
    B = np.array(list(b.values()))
    ra = A[rng.integers(0, A.size, (n, A.size))].mean(1) / B[rng.integers(0, B.size, (n, B.size))].mean(1)
    return float(A.mean() / B.mean()), float(np.percentile(ra, 5)), float(np.percentile(ra, 95))


def field_of(S: np.ndarray, W: np.ndarray, cover_mask: np.ndarray) -> tuple:
    """The mean NO2 field (normalised convolution, SMOOTH cells) on the cell grid; zero where there is no data."""
    from scipy import ndimage
    have = W > WMIN
    mean = np.where(have, S / np.maximum(W, 1e-12), 0.0)
    hf = have.astype(np.float64)
    wgt = ndimage.gaussian_filter(hf, SMOOTH)
    sm = ndimage.gaussian_filter(mean, SMOOTH) / np.maximum(wgt, 1e-6)
    local = (wgt > 0.2) & cover_mask
    field = np.where(local, sm, 0.0)
    return field.astype(np.float32), local


def tile_fields(data: dict) -> dict:
    """Per city: the winter field and the three Jalali month fields (cell means, land only for Istanbul)."""
    out = {}
    days = data["days"]
    keys = {"winter": np.ones(len(days), bool)}
    for mk in MONTH_KEYS:
        keys[mk] = np.array([air.jkey(str(d)) == mk for d in days])
    for c in CITY:
        m = data["masks"][c]
        land = (m["frac"] >= 0.5) if c == "istanbul" else np.ones(m["frac"].shape, bool)
        out[c] = {}
        for name, sel in keys.items():
            S = data["S"][c][sel].sum(0) * land           # sea cells carry no land values into the smoothing
            W = data["W"][c][sel].sum(0) * land
            f, cov = field_of(S, W, land)
            out[c][name] = dict(field=f, cover=cov, n_days=int(sel.sum()))
    return out


def main() -> None:
    offline = "--offline" in sys.argv
    COMP.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    items = json.loads(ITEMS.read_text()) if (ITEMS.exists() and offline) else search()
    say(f"seeded from the pre-registration cache: {seed()} granules")
    fetch(items, offline)
    data = build_cells(items)
    say("grid (cells of 0.02 deg, +- %.2f deg around each centre): " % GRID_HALF
        + ", ".join(f"{c} {data['masks'][c]['lon'].size} x {data['masks'][c]['lat'].size}" for c in CITY))
    T = day_table(data, "tehran", BOX, False)
    I = day_table(data, "istanbul", BOX, True)
    Ia = day_table(data, "istanbul", BOX, False)
    say(f"tehran (box +-{BOX}, all cells): valid days {T['n']}, day-mean {T['mean']:.1f}, median {T['median']:.1f}, "
        f"pooled {T['pooled']:.1f}")
    say(f"istanbul land (box +-{BOX}): valid days {I['n']}, day-mean {I['mean']:.1f}, median {I['median']:.1f}, "
        f"pooled {I['pooled']:.1f}")
    say(f"istanbul all cells (box +-{BOX}): valid days {Ia['n']}, day-mean {Ia['mean']:.1f}")
    r, lo, hi = ratio_ci(T["valid"], I["valid"])
    say(f"RATIO tehran / istanbul land: {r:.2f} [90 %: {lo:.2f} - {hi:.2f}]")
    summary = dict(primary=dict(tehran=dict(days=T["n"], day_mean=T["mean"], median=T["median"], pooled=T["pooled"]),
                                istanbul_land=dict(days=I["n"], day_mean=I["mean"], median=I["median"],
                                                   pooled=I["pooled"]),
                                istanbul_all=dict(days=Ia["n"], day_mean=Ia["mean"]),
                                ratio=r, ci90=[lo, hi]))
    # the sensitivities
    sens = {}
    T25 = day_table(data, "tehran", SENS, True)
    I25 = day_table(data, "istanbul", SENS, True)
    rr = ratio_ci(T25["valid"], I25["valid"])
    sens["box_0.25_land"] = dict(tehran_days=T25["n"], tehran=T25["mean"], istanbul_days=I25["n"],
                                 istanbul=I25["mean"], ratio=rr[0], ci90=[rr[1], rr[2]])
    # Istanbul centred on its land maximum (cells within +-0.35 deg, weight at least half the land median)
    m = data["masks"]["istanbul"]
    LO, LA = np.meshgrid(m["lon"], m["lat"])
    cx, cy = CITY["istanbul"]
    Ssum = data["S"]["istanbul"].sum(0)
    Wsum = data["W"]["istanbul"].sum(0)
    inbox = (np.abs(LO - cx) < 0.35) & (np.abs(LA - cy) < 0.35) & (m["frac"] >= 0.5)
    wmed = np.median(Wsum[inbox])
    cand = inbox & (Wsum >= 0.5 * wmed)
    mean_cell = np.where(cand, Ssum / np.where(Wsum > 0, Wsum, 1), -np.inf)
    iy, ix = np.unravel_index(np.argmax(mean_cell), mean_cell.shape)
    mx, my = float(m["lon"][ix]), float(m["lat"][iy])
    IM = day_table(data, "istanbul", BOX, True, centre=(mx, my))
    rm = ratio_ci(T["valid"], IM["valid"])
    sens["istanbul_on_land_max"] = dict(centre=[round(mx, 2), round(my, 2)], istanbul_days=IM["n"],
                                        istanbul=IM["mean"], ratio=rm[0], ci90=[rm[1], rm[2]])
    say(f"istanbul land maximum cell: lon {mx:.2f} lat {my:.2f}; tehran / that box {rm[0]:.2f} "
        f"[{rm[1]:.2f} - {rm[2]:.2f}]")
    # the four low-AMF days: the top five Tehran days whose median AMF is below 0.8 of Tehran's median
    Tpix = data["pix"]
    tci = list(CITY).index("tehran")
    tb = (np.abs(Tpix["lon"] - CITY["tehran"][0]) < BOX) & (np.abs(Tpix["lat"] - CITY["tehran"][1]) < BOX)
    tsel = (Tpix["city"] == tci) & tb
    amf_ref = float(np.median(Tpix["amf"][tsel & Tpix["valid"]]))
    top5 = [d for d, _ in sorted(T["valid"].items(), key=lambda kv: -kv[1])[:5]]
    amf_ratio = {}
    for d in top5:
        k = list(map(str, data["days"])).index(d)
        msk = tsel & Tpix["valid"] & (Tpix["day"] == k)
        amf_ratio[d] = float(np.median(Tpix["amf"][msk]) / amf_ref) if msk.any() else float("nan")
    low = [d for d in top5 if amf_ratio[d] < 0.8]
    keep = {d: v for d, v in T["valid"].items() if d not in low}
    rl = ratio_ci(keep, I["valid"])
    rl3 = ratio_ci(keep, IM["valid"])
    sens["without_low_amf_days"] = dict(dropped=low, amf_ratio={d: round(v, 3) for d, v in amf_ratio.items()},
                                        tehran_days=len(keep), tehran=float(np.mean(list(keep.values()))),
                                        ratio=rl[0], ci90=[rl[1], rl[2]],
                                        ratio_vs_land_max=rl3[0], ci90_vs_land_max=[rl3[1], rl3[2]])
    say("sensitivities:", {k: (round(v["ratio"], 2), [round(x, 2) for x in v["ci90"]]) for k, v in sens.items()},
        "| without low-AMF days over the land-maximum box:", round(rl3[0], 2), [round(rl3[1], 2), round(rl3[2], 2)])
    say(f"top five Tehran days {top5}; AMF ratio {amf_ratio}; dropped {low}; ratio {rl[0]:.2f} "
        f"[{rl[1]:.2f} - {rl[2]:.2f}]")
    d22 = T["tab"].get("2025-11-22", {}).get("val", float("nan"))
    say(f"22 Nov 2025, Tehran box day value {d22:.1f} (granule audit: tehran_granules_audit.csv in the scratch folder)")
    # the monthly day-means (for the film's counter lines)
    months = {}
    for mk in MONTH_KEYS:
        sel = [d for d in T["valid"] if air.jkey(d) == mk]
        sel_i = [d for d in I["valid"] if air.jkey(d) == mk]
        months[mk] = dict(tehran_days=len(sel), tehran=float(np.mean([T["valid"][d] for d in sel])) if sel else None,
                          istanbul_days=len(sel_i),
                          istanbul=float(np.mean([I["valid"][d] for d in sel_i])) if sel_i else None)
        say(f"month {mk}: tehran {months[mk]['tehran']} ({months[mk]['tehran_days']} days), istanbul land "
            f"{months[mk]['istanbul']} ({months[mk]['istanbul_days']} days)")
    fields = tile_fields(data)
    save = {}
    for c in CITY:
        for name, v in fields[c].items():
            save[f"{c}_{name}_field"] = v["field"]
            save[f"{c}_{name}_cover"] = v["cover"]
            save[f"{c}_{name}_days"] = np.array(v["n_days"])
        save[f"{c}_land"] = data["masks"][c]["frac"].astype(np.float32)
        save[f"{c}_lon"] = data["masks"][c]["lon"]
        save[f"{c}_lat"] = data["masks"][c]["lat"]
        save[f"{c}_S"] = data["S"][c].sum(0).astype(np.float32)
        save[f"{c}_W"] = data["W"][c].sum(0).astype(np.float32)
    np.savez_compressed(CELLS, **save)
    checks = dict(
        tehran_days=T["n"] == PRE["tehran"][1], tehran_mean=round(T["mean"], 1) == PRE["tehran"][0],
        istanbul_land_days=I["n"] == PRE["istanbul_land"][1],
        istanbul_land_mean=round(I["mean"], 1) == PRE["istanbul_land"][0],
        ratio=round(r, 2) == PRE["ratio"][0], ci_lo=round(lo, 2) == PRE["ratio"][1][0],
        ci_hi=round(hi, 2) == PRE["ratio"][1][1])
    result = dict(expected=dict(tehran=PRE["tehran"], istanbul_land=PRE["istanbul_land"], ratio=PRE["ratio"]),
                  preregistered_primary_all_cells=PRE_PRIMARY, summary=summary, sensitivities=sens, months=months,
                  checks=checks, seconds=round(time.time() - t0))
    RESULT.write_text(json.dumps(result, indent=1, ensure_ascii=False, default=float))
    LOG.write_text("\n".join(LOGLINES) + "\n")
    say("checks", checks)
    say("saved", RESULT, CELLS, LOG)
    assert all(checks.values()), checks


# ── the regional winter field: Turkey and Iran on one 0.02-degree grid (region v1) ──
#
# Iran's part: the reel's per-granule cache (air_grid.FINE, pixels east of SPLIT, read only). Turkey's part: new reads
# (pixels west of SPLIT). A granule the Iran cache does not hold is read whole. The day rule is the reel's: the OFFL
# granules of a day; the NRTI granules only on a day with no OFFL granule over the region.

RDIR = COMP / "region"
RITEMS = COMP / "region_items.json"
RGRID = dict(lon0=25.5, lat0=43.0, step=STEP, nx=1900, ny=925)   # lon0: west edge; lat0: north edge of row 0
RBOX = (25.5, 24.5, 63.5, 43.0)                                  # W, S, E, N of the region
SPLIT = 43.0                                                     # the Iran cache holds the pixels east of this
RFIELD = COMP / "region_winter_v1.npz"
RLOG = COMP / "region_winter_v1.log"
RDAYS = COMP / "region_days_v1.json"
RLOGLINES: list = []
MODE_OF = {"OFFL": 0, "NRTI": 1}
CUM = {"azar": ("1404-09",), "azar_dey": ("1404-09", "1404-10"), "winter": ("1404-09", "1404-10", "1404-11")}


def rsay(*a) -> None:
    line = " ".join(str(x) for x in a)
    print(line, flush=True)
    RLOGLINES.append(line)


def search_region() -> list:
    """Every S5P NO2 granule over the region in the winter window (OFFL and NRTI), from the STAC search."""
    rows = {}
    body = {"collections": ["sentinel-5p-l2-netcdf"], "bbox": list(RBOX),
            "datetime": f"{WINTER[0]}T00:00:00Z/{WINTER[1]}T23:59:59Z", "limit": 500,
            "query": {"s5p:product_type": {"eq": "L2__NO2___"}}}
    page, feats = get_air.call(f"{get_air.STAC}/search", body), []
    for _ in range(100):
        feats += page.get("features", [])
        nxt = next((x for x in page.get("links", []) if x.get("rel") == "next"), None)
        if not nxt:
            break
        page = (get_air.call(nxt["href"], nxt.get("body")) if nxt.get("method") == "POST"
                else get_air.call(nxt["href"]))
    for f in feats:
        mode = f["properties"].get("s5p:processing_mode")
        if mode not in MODE_OF:
            continue
        rows.setdefault(f["id"], dict(id=f["id"], datetime=f["properties"]["datetime"], mode=mode,
                                      href=next(iter(f["assets"].values()))["href"]))
    out = sorted(rows.values(), key=lambda r: r["datetime"])
    RITEMS.write_text(json.dumps(out))
    rsay(f"region search: {len(feats)} granules, OFFL+NRTI {len(out)}, "
         f"OFFL {sum(r['mode'] == 'OFFL' for r in out)}, NRTI {sum(r['mode'] == 'NRTI' for r in out)}")
    return out


def select_region(rows: list) -> list:
    """Per day: its OFFL granules; the NRTI granules only where the day has no OFFL granule over the region."""
    by_day: dict = {}
    for r in rows:
        by_day.setdefault(r["datetime"][:10], []).append(r)
    out = []
    for d in sorted(by_day):
        g = by_day[d]
        off = [r for r in g if r["mode"] == "OFFL"]
        out += off if off else [r for r in g if r["mode"] == "NRTI"]
    return out


def read_region(row: dict) -> dict:
    """One granule's valid pixels (qa >= 0.75) with footprint corners: west of SPLIT when the Iran cache holds the
    granule, the whole region otherwise. Written to data/air/compare/region/<granule>.npz."""
    import h5py
    gid = row["id"]
    path = RDIR / f"{gid}.npz"
    if path.exists():
        return dict(id=gid, status="cached")
    full = not (air_grid.FINE / f"{gid}.npz").exists()
    W, S, N = RBOX[0], RBOX[1], RBOX[3]
    E = RBOX[2] if full else SPLIT
    last = None
    for attempt in range(4):
        try:
            f = h5py.File(get_air.RangeFile(get_air.sas_url(row["href"])), "r")
            p = f["PRODUCT"]
            lat, lon = p["latitude"][0], p["longitude"][0]
            inb = (lat > S) & (lat < N) & (lon > W) & (lon <= E)
            rows_ = np.flatnonzero(inb.any(axis=1))
            RDIR.mkdir(parents=True, exist_ok=True)
            if rows_.size == 0:
                np.savez(path, n=np.array(0), full=np.array(full))
                return dict(id=gid, status="none")
            r0, r1 = int(rows_.min()), int(rows_.max()) + 1
            a0, a1 = max(r0 - 1, 0), min(lat.shape[0], r1 + 1)
            la, lo = lat[a0:a1], lon[a0:a1]
            raw = p["qa_value"][0, a0:a1, :]
            qa = np.where(raw == 255, np.nan, raw.astype(np.float32) * 0.01)
            no2 = p["nitrogendioxide_tropospheric_column"][0, a0:a1, :].astype(np.float32)
            good = np.isfinite(no2) & (np.abs(no2) < get_air.FILL)
            valid = inb[a0:a1] & good & (qa >= get_air.QA_MIN)
            i, j = np.nonzero(valid)
            cla, clo = corners(la.astype(np.float64)), corners(lo.astype(np.float64))
            clat = np.stack([cla[i, j], cla[i, j + 1], cla[i + 1, j + 1], cla[i + 1, j]], -1).astype(np.float32)
            clon = np.stack([clo[i, j], clo[i, j + 1], clo[i + 1, j + 1], clo[i + 1, j]], -1).astype(np.float32)
            tmp = RDIR / f"{gid}.part.npz"
            np.savez(tmp, n=np.array(i.size), full=np.array(full), day=np.array(row["datetime"][:10]),
                     mode=np.array(row["mode"]), no2=no2[i, j], lat=la[i, j].astype(np.float64),
                     lon=lo[i, j].astype(np.float64), clat=clat, clon=clon)
            tmp.replace(path)
            return dict(id=gid, status="ok", n=int(i.size), full=full)
        except Exception as ex:  # noqa: BLE001
            last = repr(ex)[:200]
            time.sleep(20 * (attempt + 1))
    return dict(id=gid, status="error", err=last)


def fetch_region(rows: list) -> None:
    missing = [r for r in rows if not (RDIR / f"{r['id']}.npz").exists()]
    rsay(f"region granules {len(rows)}, cached {len(rows) - len(missing)}, to read {len(missing)}")
    stat: dict = {}
    if missing:
        with ProcessPoolExecutor(max_workers=3) as ex:
            for fu in as_completed([ex.submit(read_region, r) for r in missing]):
                res = fu.result()
                stat[res["status"]] = stat.get(res["status"], 0) + 1
                if res["status"] == "error":
                    rsay("ERROR", res)
    rsay("region read status", stat)


def region_pixels(row: dict):
    """The granule's pixels for the grid: the region file, plus the Iran cache's pixels east of SPLIT when the region
    file holds only the west part. Returns None for a granule with no valid pixel."""
    z = np.load(RDIR / f"{row['id']}.npz")
    if int(z["n"]) == 0:
        return None
    parts = [dict(no2=z["no2"], lat=z["lat"], lon=z["lon"], clat=z["clat"], clon=z["clon"])]
    if not bool(z["full"]):
        fz = np.load(air_grid.FINE / f"{row['id']}.npz")
        parts.append(dict(no2=fz["no2"], lat=fz["lat"].astype(np.float64), lon=fz["lon"].astype(np.float64),
                          clat=fz["clat"], clon=fz["clon"]))
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


def region_deposit(S: np.ndarray, Wt: np.ndarray, res: dict, wts: list) -> tuple:
    """Spread one granule's pixels on the region grid (air_grid's footprint rule); returns the flat cell index and the
    value and weight of each deposit, the same arrays for the full grid and for the city crops."""
    g = RGRID
    lat_s = sum(res["clat"][:, k:k + 1].astype(np.float64) * wts[k][None, :] for k in range(4))
    lon_s = sum(res["clon"][:, k:k + 1].astype(np.float64) * wts[k][None, :] for k in range(4))
    ix = np.floor((lon_s - g["lon0"]) / g["step"]).astype(np.int64)
    iy = np.floor((g["lat0"] - lat_s) / g["step"]).astype(np.int64)
    ok = (ix >= 0) & (ix < g["nx"]) & (iy >= 0) & (iy < g["ny"])
    val = np.broadcast_to((res["no2"].astype(np.float64) * air.K)[:, None], lat_s.shape)[ok] / wts[0].size
    unit = np.full(val.shape, 1.0 / wts[0].size)
    return ix[ok], iy[ok], val, unit


def city_crop(c: str) -> dict:
    """The city's crop of the region grid: cell index bounds (the window +- GRID_HALF) and the cell centres."""
    cx, cy = CITY[c]
    x0 = int(np.floor((cx - GRID_HALF - RGRID["lon0"]) / STEP))
    x1 = int(np.ceil((cx + GRID_HALF - RGRID["lon0"]) / STEP))
    y0 = int(np.floor((RGRID["lat0"] - (cy + GRID_HALF)) / STEP))
    y1 = int(np.ceil((RGRID["lat0"] - (cy - GRID_HALF)) / STEP))
    return dict(x0=x0, x1=x1, y0=y0, y1=y1, w=x1 - x0, h=y1 - y0)


def build_region() -> None:
    t0 = time.time()
    rows_all = json.loads(RITEMS.read_text())
    rows = select_region(rows_all)
    rsay(f"days with a granule: {len({r['datetime'][:10] for r in rows})}; granules used {len(rows)} "
         f"(OFFL {sum(r['mode'] == 'OFFL' for r in rows)}, NRTI {sum(r['mode'] == 'NRTI' for r in rows)})")
    fetch_region(rows)
    g = RGRID
    ncell = g["nx"] * g["ny"]
    S = np.zeros(ncell)
    Wt = np.zeros(ncell)
    wts = air_grid._subpoints()
    crop = {c: city_crop(c) for c in CITY}
    lnd = {c: land_fraction(c) for c in CITY}
    days = sorted({r["datetime"][:10] for r in rows if air.jkey(r["datetime"][:10]) in air.WINTER_JK})
    day_i = {d: k for k, d in enumerate(days)}
    # per city, per day, per granule mode (0 OFFL, 1 NRTI): crop sums, box sums and valid centres in the box
    CS = {c: np.zeros((2, len(days), crop[c]["h"], crop[c]["w"])) for c in CITY}
    CW = {c: np.zeros((2, len(days), crop[c]["h"], crop[c]["w"])) for c in CITY}
    NV = {c: np.zeros((2, len(days)), int) for c in CITY}
    NVL = {c: np.zeros((2, len(days)), int) for c in CITY}
    npx = 0
    Sg = {k: np.zeros(ncell) for k in CUM}
    Wg = {k: np.zeros(ncell) for k in CUM}
    for r in rows:
        res = region_pixels(r)
        if res is None:
            continue
        day = r["datetime"][:10]
        if day not in day_i:
            continue
        k, md = day_i[day], MODE_OF[r["mode"]]
        npx += res["no2"].size
        ix, iy, val, unit = region_deposit(S, Wt, res, wts)
        cell = iy * g["nx"] + ix
        S += np.bincount(cell, weights=val, minlength=ncell)
        Wt += np.bincount(cell, weights=unit, minlength=ncell)
        for c in CITY:
            cr = crop[c]
            sel = (ix >= cr["x0"]) & (ix < cr["x1"]) & (iy >= cr["y0"]) & (iy < cr["y1"])
            loc = (iy[sel] - cr["y0"]) * cr["w"] + (ix[sel] - cr["x0"])
            CS[c][md, k] += np.bincount(loc, weights=val[sel], minlength=cr["w"] * cr["h"]).reshape(cr["h"], cr["w"])
            CW[c][md, k] += np.bincount(loc, weights=unit[sel], minlength=cr["w"] * cr["h"]).reshape(cr["h"], cr["w"])
            # valid pixel centres in the metric box (+-BOX), and on land (the Istanbul metric)
            cx, cy = CITY[c]
            m = lnd[c]
            lon_e, lat_e = m["lon"][0] - STEP / 2, m["lat"][0] - STEP / 2
            inb = (np.abs(res["lon"] - cx) < BOX) & (np.abs(res["lat"] - cy) < BOX)
            ixc = np.floor((res["lon"] - lon_e) / STEP).astype(int)
            iyc = np.floor((res["lat"] - lat_e) / STEP).astype(int)
            inside = (ixc >= 0) & (ixc < m["lon"].size) & (iyc >= 0) & (iyc < m["lat"].size)
            landc = np.zeros(ixc.size, bool)
            landc[inside] = m["frac"][iyc[inside], ixc[inside]] >= 0.5
            NV[c][md, k] += int((inb).sum())
            NVL[c][md, k] += int((inb & landc).sum())
        for name, jks in CUM.items():
            if air.jkey(day) in jks:
                Sg[name] += np.bincount(cell, weights=val, minlength=ncell)
                Wg[name] += np.bincount(cell, weights=unit, minlength=ncell)
    rsay(f"pixels gridded {npx}; seconds {time.time() - t0:.0f}")
    # the box values per day: the cell sums of the metric box (all cells for Tehran, land cells for Istanbul)
    stats, byday = {}, {}
    for c in CITY:
        cr = crop[c]
        m = lnd[c]
        cx, cy = CITY[c]
        # the crop's cell centres from the region axes
        cl_lon = RGRID["lon0"] + (np.arange(cr["x0"], cr["x1"]) + 0.5) * STEP
        cl_lat = RGRID["lat0"] - (np.arange(cr["y0"], cr["y1"]) + 0.5) * STEP
        CLO, CLA = np.meshgrid(cl_lon, cl_lat)
        box = (np.abs(CLO - cx) < BOX) & (np.abs(CLA - cy) < BOX)
        if c == "istanbul":
            # land cells of the crop (the Natural Earth fraction on the same lattice, aligned by centre)
            fr = np.zeros(CLO.shape)
            # the mask's axes ascend (lattice); the crop's centres sit on the same 0.02-degree lattice
            ii = np.rint((CLO - m["lon"][0]) / STEP).astype(int)
            jj = np.rint((CLA - m["lat"][0]) / STEP).astype(int)
            okk = (ii >= 0) & (ii < m["lon"].size) & (jj >= 0) & (jj < m["lat"].size)
            fr[okk] = m["frac"][jj[okk], ii[okk]]
            box &= fr >= 0.5
        stats[c] = {}
        for md, mname in enumerate(("OFFL", "NRTI")):
            SS = CS[c][md][:, box].sum(1)
            WW = CW[c][md][:, box].sum(1)
            stats[c][mname] = dict(S=SS, W=WW, nv=NVL[c][md] if c == "istanbul" else NV[c][md])
        for k, d in enumerate(days):
            row = byday.setdefault(d, dict(day=d, jalali=air.jkey(d)))
            for mname in ("OFFL", "NRTI"):
                st = stats[c][mname]
                v = float(st["S"][k] / st["W"][k]) if st["W"][k] > 0 else None
                row[f"{c}_{mname}"] = v
                row[f"{c}_{mname}_nv"] = int(st["nv"][k])
    dayrows = [byday[d] for d in days]     # one row per day, both cities' keys
    # the fields: OFFL and NRTI-fill days together (the reel's rule), smoothed as the reel's cell fields
    inside = air_grid.burn(air_grid.ne_countries_polygons({"Iran", "Turkey"}, g), g) > 0
    save = dict(inside=inside.astype(np.uint8))
    lon_ax, lat_ax = air_grid.grid_axes(g)
    save["lon"], save["lat"] = lon_ax, lat_ax
    fields = {}
    for name in CUM:
        f, cov = air_grid.field_of(Sg[name].reshape(g["ny"], g["nx"]), Wg[name].reshape(g["ny"], g["nx"]), inside)
        fields[name] = (f, cov)
        save[name] = f
        save["cov_" + name] = cov
    # the per-day city crops (OFFL and NRTI-fill together) for the close-ups' running means
    for c in CITY:
        save[f"{c}_crop_S"] = (CS[c][0] + CS[c][1]).astype(np.float32)
        save[f"{c}_crop_W"] = (CW[c][0] + CW[c][1]).astype(np.float32)
        save[f"{c}_crop_lon"] = RGRID["lon0"] + (np.arange(crop[c]["x0"], crop[c]["x1"]) + 0.5) * STEP
        save[f"{c}_crop_lat"] = RGRID["lat0"] - (np.arange(crop[c]["y0"], crop[c]["y1"]) + 0.5) * STEP
    save["days"] = np.array(days)
    np.savez_compressed(RFIELD, **save)
    RDAYS.write_text(json.dumps(dict(days=dayrows, grid=RGRID, box=BOX), indent=1, ensure_ascii=False))
    # the checks: the metric as the pre-registration (OFFL granules only, Tehran all cells, Istanbul land)
    def core(c: str, mname: str, land: bool) -> tuple:
        vals = [r[f"{c}_{mname}"] for r in dayrows if r[f"{c}_{mname}"] is not None and r[f"{c}_{mname}_nv"] >= 3]
        return float(np.mean(vals)), len(vals)
    tm, tn = core("tehran", "OFFL", False)
    im, inn = core("istanbul", "OFFL", True)
    tmf, tnf = core("tehran", "NRTI", False)
    rsay(f"CHECK OFFL-only, Tehran core (box +-{BOX}): {tm:.1f} on {tn} valid days (pre-registration 72.2 on 61)")
    rsay(f"CHECK OFFL-only, Istanbul land core: {im:.1f} on {inn} valid days (pre-registration 12.4 on 31)")
    rsay(f"ratio of the OFFL day-means: {tm / im:.2f} (pre-registration 5.82)")
    # the field's own day-means (OFFL + NRTI-fill days)
    fm_t = [r["tehran_OFFL"] for r in dayrows if r["tehran_OFFL"] is not None and r["tehran_OFFL_nv"] >= 3]
    rsay(f"days in the region field: {len(days)}; Tehran day-means with NRTI-fill days, OFFL days only "
         f"{len(fm_t)}, NRTI-fill days {tmf:.1f} over {tnf} days")
    rsay(f"field max {float(fields['winter'][0].max()):.1f}; seconds {time.time() - t0:.0f}")
    RLOG.write_text("\n".join(RLOGLINES) + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "region":
        COMP.mkdir(parents=True, exist_ok=True)
        RDIR.mkdir(parents=True, exist_ok=True)
        if "--search" in sys.argv or not RITEMS.exists():
            search_region()
        fetch_region(select_region(json.loads(RITEMS.read_text())))
        build_region()
    else:
        main()
