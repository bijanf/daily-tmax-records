"""The oversampled NO2 fields and the relief of the winter NO2 film (onebit_air.py).

NO2: every valid Sentinel-5P pixel over Iran (OFFL, and the NRTI granules that fill the days with no OFFL granule:
data/air/nrti_fill.json; qa >= 0.75, as air.py) is spread over its footprint on the 0.02-degree grid GRID. The four
corners of a pixel are rebuilt from the granule's pixel centres (the mean of the 2 x 2 centres around each corner).
check_corners compares them with the file's latitude_bounds and longitude_bounds: median about 5 m (4.8 and 4.9 m
on two granules, 23 Oct 2025 and 25 Apr 2026), 99th percentile about 43 m. Each pixel gets 4 x 4 sub-points in its footprint, each deposits 1/16 of the pixel's weight and NO2 in its
cell, and overlapping orbits add up: a cell holds the area-weighted mean of every pixel that covers it.
The box ratio of the film is the same cell sums over the Tehran-Karaj box. The counter on screen is that cell-sum
value (3.22, shown rounded), not a mean of the rendered glow: averaging the glow over the same box gives about 3.29,
because the glow is smoothed and clipped at the coast. The city ratios (CITIES, box_table) use the same cell sums.

Relief (REL, 0.01 degree, about 1 km): Copernicus GLO-30 tiles read at 0.01 degree from their overviews, hillshaded
at vertical exaggeration VE (sun azimuth 315, altitude 20). Land, sea and Iran come from Natural Earth 10 m
(data/air/natural_earth: ne_10m_land, ne_10m_admin_0_countries, Natural Earth 5.1.1).

    python -I src/air_grid.py relief    # the relief (4 readers to the Planetary Computer)
    python -I src/air_grid.py fields    # the granules (4 readers), the fields and the box table
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))

import air  # noqa: E402
import get_air  # noqa: E402

DATA = air.DATA
NE = DATA / "natural_earth"
GLOW_PATH = DATA / "iran_glow_v4.npz"
FINE = DATA / "fine"                                         # per-granule cache of the footprint inputs
REL_PATH = DATA / "relief_v4.npz"
BOX_PATH = DATA / "iran_box_v4.json"
GRID = dict(lon0=43.0, lat0=40.2, step=0.02, nx=1050, ny=770)     # lat0: the north edge of row 0
REL = dict(lon0=42.5, lat0=45.5, step=0.01, nx=2250, ny=3600)
SUB = 4                                                          # sub-points per pixel side
SMOOTH, SMOOTH_WIDE = 1.0, 3.0                                   # cells (2.2 km and 6.6 km)
WMIN = 0.05                                                      # a cell has data above this weight (pixel units)
NEAR_CELLS = 8                                                   # about 16 km around a cell with data
VE = 2.0                                                         # vertical exaggeration of the hillshade
SUN = (315.0, 20.0)                                              # azimuth and altitude of the low sun, degrees
DEM = {"30": "https://planetarycomputer.microsoft.com/api/sas/v1/token/cop-dem-glo-30",
       "90": "https://planetarycomputer.microsoft.com/api/sas/v1/token/cop-dem-glo-90"}
BOX_TK = air.TEHRAN_KARAJ
CITY_HALF = 0.15                                                # deg: the city box is the centre +- 0.15 deg
# city centres (decimal degrees, lon, lat; approximate city centres): the ratio of each city box, winter over summer
CITIES = {"تهران": (51.39, 35.69), "کرج": (50.94, 35.84), "قم": (50.88, 34.64), "مشهد": (59.61, 36.30),
          "اصفهان": (51.67, 32.65), "تبریز": (46.29, 38.08), "شیراز": (52.53, 29.59), "اهواز": (48.67, 31.32),
          "کرمانشاه": (47.07, 34.31), "ارومیه": (45.08, 37.55)}


def grid_axes(g: dict) -> tuple:
    lon = g["lon0"] + (np.arange(g["nx"]) + 0.5) * g["step"]
    lat = g["lat0"] - (np.arange(g["ny"]) + 0.5) * g["step"]
    return lon, lat


# ── vector layers and rasters ──

def _polygons(shape) -> list:
    """GeoJSON-like polygons of a pyshp polygon: a clockwise ring starts a polygon, a counter-clockwise ring is a hole."""
    pts = np.asarray(shape.points, float)
    starts = list(shape.parts) + [len(pts)]
    out = []
    for a, b in zip(starts[:-1], starts[1:]):
        ring = pts[a:b]
        x, y = ring[:, 0], ring[:, 1]
        area = 0.5 * np.sum(x[:-1] * y[1:] - x[1:] * y[:-1])
        if area < 0 or not out:
            out.append([ring.tolist()])
        else:
            out[-1].append(ring.tolist())
    return [{"type": "Polygon", "coordinates": p} for p in out]


def ne_polygons(name: str, g: dict) -> list:
    import shapefile
    r = shapefile.Reader(str(NE / name))
    w, e = g["lon0"], g["lon0"] + g["nx"] * g["step"]
    s, n = g["lat0"] - g["ny"] * g["step"], g["lat0"]
    out = []
    for sh in r.iterShapes():
        x0, y0, x1, y1 = sh.bbox
        if x1 < w or x0 > e or y1 < s or y0 > n:
            continue
        out += _polygons(sh)
    return out


def ne_countries_polygons(names: set, g: dict) -> list:
    import shapefile
    r = shapefile.Reader(str(NE / "ne_10m_admin_0_countries.shp"))
    out = []
    for sh, rec in zip(r.iterShapes(), r.iterRecords()):
        if rec["ADMIN"] in names:
            out += _polygons(sh)
    return out


def burn(polys: list, g: dict) -> np.ndarray:
    from rasterio.features import rasterize
    from rasterio.transform import from_origin
    tr = from_origin(g["lon0"], g["lat0"], g["step"], g["step"])
    if not polys:
        return np.zeros((g["ny"], g["nx"]), np.uint8)
    return rasterize([(p, 1) for p in polys], out_shape=(g["ny"], g["nx"]), transform=tr, fill=0, dtype="uint8")


# ── relief ──

def _tile(job: tuple, toks: dict):
    """One 1-degree tile at 0.01 degree: GLO-30 where the tile exists, else GLO-90 (about 900 m, the tile GLO-30 lacks);
    None where neither has a tile (sea)."""
    import rasterio
    from rasterio.enums import Resampling
    la0, lo0 = job
    cands = [("COP30_hh", f"Copernicus_DSM_COG_10_N{la0:02d}_00_E{lo0:03d}_00_DEM", toks["30"]),
             ("COP90_hh", f"Copernicus_DSM_COG_30_N{la0:02d}_00_E{lo0:03d}_00_DEM", toks["90"])]
    for folder, tile, tok in cands:
        url = f"https://elevationeuwest.blob.core.windows.net/copernicus-dem/{folder}/{tile}.tif?{tok}"
        for attempt in range(4):
            try:
                with rasterio.open("/vsicurl/" + url) as src:
                    a = src.read(1, out_shape=(100, 100), resampling=Resampling.average).astype(np.float32)
                a[a < -1000] = np.nan
                return job, a, folder
            except Exception as ex:  # noqa: BLE001
                if "404" in str(ex) or "does not exist" in str(ex).lower():
                    break
                time.sleep(15 * (attempt + 1))
        else:
            raise RuntimeError(f"tile {job} {folder} failed")
    return job, None, "sea"


def hillshade(elev: np.ndarray, g: dict, ve: float = VE, sun: tuple = SUN) -> np.ndarray:
    """Hillshade in 0-1 of the elevation grid (metres), the cells of step g['step'] degrees, rows north to south."""
    lat = g["lat0"] - (np.arange(g["ny"]) + 0.5) * g["step"]
    dy = g["step"] * 110574.0
    dx = (g["step"] * 111320.0 * np.cos(np.radians(lat)))[:, None]
    z = elev.astype(np.float64) * ve
    gx = np.gradient(z, axis=1) / dx                  # east
    gn = -np.gradient(z, axis=0) / dy                 # north (rows run south)
    az, alt = np.radians(sun[0]), np.radians(sun[1])
    lx, ly, lz = np.sin(az) * np.cos(alt), np.cos(az) * np.cos(alt), np.sin(alt)
    shade = (lz - gx * lx - gn * ly) / np.sqrt(1.0 + gx * gx + gn * gn)
    return np.clip(shade, 0.0, 1.0).astype(np.float32)


def relief(path: Path = REL_PATH) -> None:
    import rasterio  # noqa: F401  (GDAL drivers loaded before the threads start)
    toks = {k: json.loads(urllib.request.urlopen(url, timeout=120).read())["token"] for k, url in DEM.items()}
    G = np.full((REL["ny"], REL["nx"]), np.nan, np.float32)
    jobs = [(la0, lo0) for la0 in range(9, 45) for lo0 in range(42, 65)]
    n_tiles, n_from = 0, {}
    with ThreadPoolExecutor(4) as ex:
        for job, a, folder in ex.map(lambda j: _tile(j, toks), jobs):
            n_from[folder] = n_from.get(folder, 0) + 1
            if a is None:
                continue
            la0, lo0 = job
            r0 = int(round((REL["lat0"] - (la0 + 1)) / REL["step"]))
            c0 = int(round((lo0 - REL["lon0"]) / REL["step"]))
            gr0, gr1 = max(r0, 0), min(r0 + 100, REL["ny"])
            gc0, gc1 = max(c0, 0), min(c0 + 100, REL["nx"])
            G[gr0:gr1, gc0:gc1] = a[gr0 - r0:gr1 - r0, gc0 - c0:gc1 - c0]
            n_tiles += 1
    print("tiles with data:", n_tiles, "of", len(jobs), "by folder:", n_from, flush=True)
    land = burn(ne_polygons("ne_10m_land.shp", REL), REL)
    iran = burn(ne_countries_polygons({"Iran"}, REL), REL)
    elev = np.where((land > 0) & np.isfinite(G), G, 0.0).astype(np.float32)
    hs = hillshade(elev, REL)
    print("land cells", int(land.sum()), "Iran cells", int(iran.sum()), "inside Iran with no elevation",
          int(((iran > 0) & ~np.isfinite(G)).sum()), flush=True)
    assert ((iran > 0) & (land == 0)).sum() < 0.002 * iran.sum()
    np.savez_compressed(path, hs=hs, elev=elev, land=land, iran=iran)
    print("saved", path, flush=True)


# ── NO2 ──

def corners(a: np.ndarray) -> np.ndarray:
    """Pixel corners, shape (rows + 1, cols + 1): the mean of the 2 x 2 centres around each corner (edges extrapolated)."""
    ap = np.pad(a, 1, mode="edge")
    ap[0, :] = 2 * ap[1, :] - ap[2, :]
    ap[-1, :] = 2 * ap[-2, :] - ap[-3, :]
    ap[:, 0] = 2 * ap[:, 1] - ap[:, 2]
    ap[:, -1] = 2 * ap[:, -2] - ap[:, -3]
    return 0.25 * (ap[:-1, :-1] + ap[1:, :-1] + ap[:-1, 1:] + ap[1:, 1:])


def granule(row: dict):
    """One granule's valid pixels over Iran, as the cache (get_air.py), with their corners rebuilt from the centres.
    Returns None for a granule without a cache entry (it does not reach Iran)."""
    import h5py
    npz = get_air.GRANULES / f"{row['id']}.npz"
    if not npz.exists():
        return None
    fine = FINE / f"{row['id']}.npz"                             # resumable: one cache file per granule
    if fine.exists():
        z = np.load(fine)
        return dict(id=row["id"], day=str(z["day"]), no2=z["no2"], clat=z["clat"], clon=z["clon"],
                    lat=z["lat"], lon=z["lon"], n_box=int(z["n_box"]))
    W, S, E, N = get_air.IRAN
    last = None
    for attempt in range(4):
        try:
            f = h5py.File(get_air.RangeFile(get_air.sas_url(row["href"])), "r")
            p = f["PRODUCT"]
            lat, lon = p["latitude"][0], p["longitude"][0]
            inb = (lat > S) & (lat < N) & (lon > W) & (lon < E)
            rows = np.flatnonzero(inb.any(axis=1))
            r0, r1 = int(rows.min()), int(rows.max()) + 1
            a0, a1 = max(r0 - 1, 0), min(lat.shape[0], r1 + 1)
            la, lo = lat[a0:a1], lon[a0:a1]
            raw = p["qa_value"][0, a0:a1, :]
            qa = np.where(raw == 255, np.nan, raw.astype(np.float32) * 0.01)
            no2 = p["nitrogendioxide_tropospheric_column"][0, a0:a1, :].astype(np.float32)
            good = np.isfinite(no2) & (np.abs(no2) < get_air.FILL)
            valid = inb[a0:a1] & good & (qa >= get_air.QA_MIN)
            break
        except Exception as ex:  # noqa: BLE001
            last = repr(ex)[:200]
            time.sleep(20)
    else:
        raise RuntimeError(f"{row['id']}: {last}")
    i, j = np.nonzero(valid)
    out = dict(id=row["id"], day=row["datetime"][:10], lat=la[i, j], lon=lo[i, j], no2=no2[i, j])
    z = np.load(npz)
    same = (z["lat"].shape == out["lat"].shape and np.array_equal(z["lat"], out["lat"])
            and np.array_equal(z["lon"], out["lon"]) and np.array_equal(z["no2"], out["no2"]))
    out["cache_match"] = bool(same)            # the fresh read is what is gridded; a mismatch is counted and logged
    if not same:
        print(f"note: {row['id']}: the fresh read ({out['lat'].size} px) differs from the cache ({z['lat'].size} px);"
              " the fresh read is used", flush=True)
    cla, clo = corners(la.astype(np.float64)), corners(lo.astype(np.float64))
    out["clat"] = np.stack([cla[i, j], cla[i, j + 1], cla[i + 1, j + 1], cla[i + 1, j]], -1).astype(np.float32)
    out["clon"] = np.stack([clo[i, j], clo[i, j + 1], clo[i + 1, j + 1], clo[i + 1, j]], -1).astype(np.float32)
    box = (out["lon"] > BOX_TK[0]) & (out["lon"] < BOX_TK[2]) & (out["lat"] > BOX_TK[1]) & (out["lat"] < BOX_TK[3])
    out["n_box"] = int(box.sum())
    FINE.mkdir(parents=True, exist_ok=True)
    tmp = FINE / f"{row['id']}.part.npz"
    np.savez(tmp, day=out["day"], no2=out["no2"], clat=out["clat"], clon=out["clon"], lat=out["lat"], lon=out["lon"],
             n_box=out["n_box"])
    tmp.replace(fine)
    return out


def check_corners(row: dict) -> dict:
    """The rebuilt corners against the file's latitude_bounds and longitude_bounds, on one granule's rows."""
    import h5py
    f = h5py.File(get_air.RangeFile(get_air.sas_url(row["href"])), "r")
    g = f["PRODUCT/SUPPORT_DATA/GEOLOCATIONS"]
    lat, lon = f["PRODUCT/latitude"][0], f["PRODUCT/longitude"][0]
    W, S, E, N = get_air.IRAN
    rows = np.flatnonzero(((lat > S) & (lat < N) & (lon > W) & (lon < E)).any(axis=1))
    r0, r1 = int(rows.min()), int(rows.max()) + 1
    a0, a1 = max(r0 - 1, 0), min(lat.shape[0], r1 + 1)
    cla, clo = corners(lat[a0:a1].astype(np.float64)), corners(lon[a0:a1].astype(np.float64))
    sl = (slice(2, -2, 3), slice(2, -2, 3))
    ii, jj = np.arange(a1 - a0)[sl[0]], np.arange(lat.shape[1])[sl[1]]
    ii, jj = ii[ii < a1 - a0 - 1], jj[jj < lat.shape[1] - 1]
    bl = g["latitude_bounds"][0, a0:a1, :, :][np.ix_(ii, jj)]
    bo = g["longitude_bounds"][0, a0:a1, :, :][np.ix_(ii, jj)]
    mine_la = np.stack([cla[np.ix_(ii, jj)], cla[np.ix_(ii, jj + 1)], cla[np.ix_(ii + 1, jj + 1)],
                        cla[np.ix_(ii + 1, jj)]], -1)
    mine_lo = np.stack([clo[np.ix_(ii, jj)], clo[np.ix_(ii, jj + 1)], clo[np.ix_(ii + 1, jj + 1)],
                        clo[np.ix_(ii + 1, jj)]], -1)
    # match each file corner to the nearest rebuilt corner (the file's corner order is not the same)
    dev = []
    for k in range(4):
        d = np.stack([np.hypot(bl[..., k] - mine_la[..., m], bo[..., k] - mine_lo[..., m]) for m in range(4)], -1)
        dev.append(d.min(-1))
    dev = np.concatenate([d.ravel() for d in dev]) * 111000.0
    return dict(id=row["id"], median_m=float(np.median(dev)), p99_m=float(np.percentile(dev, 99)),
                max_m=float(dev.max()), n=int(dev.size))


def _subpoints():
    u = (np.arange(SUB) + 0.5) / SUB
    U, V = np.meshgrid(u, u)
    U, V = U.ravel(), V.ravel()
    return [(1 - U) * (1 - V), U * (1 - V), U * V, (1 - U) * V]


def _deposit(acc: dict, res: dict, wts: list) -> None:
    """Spread one granule's pixels onto the grid: each pixel's sub-points deposit 1/SUB^2 of its weight and NO2."""
    jk = air.jkey(res["day"])
    if jk not in air.DIAL_JK:
        return
    keys = [k for k in (jk, "winter" if jk in air.WINTER_JK else None, "summer" if jk in air.REF_JK else None) if k]
    n = res["no2"].size
    if n == 0:
        return
    lat_s = sum(res["clat"][:, k:k + 1].astype(np.float64) * wts[k][None, :] for k in range(4))
    lon_s = sum(res["clon"][:, k:k + 1].astype(np.float64) * wts[k][None, :] for k in range(4))
    g = GRID
    ix = np.floor((lon_s - g["lon0"]) / g["step"]).astype(np.int64)
    iy = np.floor((g["lat0"] - lat_s) / g["step"]).astype(np.int64)
    ok = (ix >= 0) & (ix < g["nx"]) & (iy >= 0) & (iy < g["ny"])
    cell = (iy * g["nx"] + ix)[ok]
    val = np.broadcast_to((res["no2"].astype(np.float64) * air.K)[:, None], lat_s.shape)[ok] / wts[0].size
    unit = np.full(cell.shape, 1.0 / wts[0].size)
    ncell = g["nx"] * g["ny"]
    for k in keys:
        a = acc[k]
        a["S"] += np.bincount(cell, weights=val, minlength=ncell)
        a["W"] += np.bincount(cell, weights=unit, minlength=ncell)
    acc[jk]["n_box"] += res["n_box"]
    if res["n_box"]:
        acc[jk]["days"].add(res["day"])


def build_fields(workers: int = 4) -> None:
    rows = json.loads((DATA / "items_window.json").read_text())
    nrti = set(json.loads((DATA / "nrti_fill.json").read_text())["granules"])
    rows = [dict(r, mode="OFFL") if r["id"] in nrti else r for r in rows]
    todo = [r for r in rows if r["mode"] == "OFFL" and (get_air.GRANULES / f"{r['id']}.npz").exists()]
    print("granules to read:", len(todo), flush=True)
    ncell = GRID["nx"] * GRID["ny"]
    keys = list(air.DIAL_JK) + ["winter", "summer"]
    acc = {k: dict(S=np.zeros(ncell), W=np.zeros(ncell), n_box=0, days=set()) for k in keys}
    wts = _subpoints()
    failed, t0 = [], time.time()
    checks = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(granule, r): r for r in todo}
        for k, fu in enumerate(as_completed(futs), 1):
            try:
                res = fu.result()
            except Exception as err:  # noqa: BLE001
                failed.append(str(err)[:200])
                continue
            if res is not None:
                _deposit(acc, res, wts)
            if k % 100 == 0:
                print(f"{k}/{len(todo)} in {time.time() - t0:.0f} s", flush=True)
    print("failed granules:", len(failed), failed[:3], flush=True)
    assert not failed, failed[:3]
    # the rebuilt corners against the file's bounds, on one granule per season
    for r in (todo[0], todo[len(todo) // 2]):
        checks.append(check_corners(r))
    print("corner check:", checks, flush=True)
    fields, cover = {}, {}
    inside = burn(ne_countries_polygons({"Iran"}, GRID), GRID) > 0
    save = {}
    for key, a in acc.items():
        f, c = field_of(a["S"].reshape(GRID["ny"], GRID["nx"]), a["W"].reshape(GRID["ny"], GRID["nx"]), inside)
        fields[key], cover[key] = f, c
        save[key] = f
        save["cov_" + key] = c
    save["iran"] = inside.astype(np.uint8)
    np.savez_compressed(GLOW_PATH, **save)
    box = box_table(acc)
    BOX_PATH.write_text(json.dumps(box, indent=1, ensure_ascii=False))
    print("saved", GLOW_PATH, BOX_PATH, flush=True)


def field_of(S: np.ndarray, W: np.ndarray, inside: np.ndarray) -> tuple:
    """The mean NO2 field on the grid (1e15 molec/cm2): the cells with weight above WMIN, smoothed by normalised
    convolution at SMOOTH cells (wider where a month is sparse), zero outside Iran and where there is no data."""
    have = W > WMIN
    mean = np.where(have, S / np.maximum(W, 1e-12), 0.0)
    hf = have.astype(np.float64)
    wgt = ndimage.gaussian_filter(hf, SMOOTH)
    sm = ndimage.gaussian_filter(mean, SMOOTH) / np.maximum(wgt, 1e-6)
    wgt_w = ndimage.gaussian_filter(hf, SMOOTH_WIDE)
    sm_w = ndimage.gaussian_filter(mean, SMOOTH_WIDE) / np.maximum(wgt_w, 1e-9)
    local = wgt > 0.2
    near = ndimage.binary_dilation(have, iterations=NEAR_CELLS)
    cv = (local | near) & inside
    field = np.where(cv, np.where(local, sm, sm_w), 0.0)
    return field.astype(np.float32), cv


def box_table(acc: dict) -> dict:
    """The Tehran-Karaj box from the cell sums (cells whose centre lies in the box), per dial month: the area-weighted
    mean, the valid pixels with centres in the box and the days; the summer reference (pooled) and the winter ratio."""
    lon, lat = grid_axes(GRID)
    LO, LA = np.meshgrid(lon, lat)
    m = ((LO > BOX_TK[0]) & (LO < BOX_TK[2]) & (LA > BOX_TK[1]) & (LA < BOX_TK[3])).ravel()

    def mean_of(keys):
        s = sum(acc[k]["S"] for k in keys)[m].sum()
        w = sum(acc[k]["W"] for k in keys)[m].sum()
        return float(s / w), float(w)

    ref, ref_w = mean_of(air.REF_JK)
    rows = []
    for jk in air.DIAL_JK:
        pm, wsum = mean_of([jk])
        rows.append(dict(jk=jk, pix_mean=pm, box_weight=wsum, n_pix=acc[jk]["n_box"],
                         n_days=len(acc[jk]["days"]), ratio=pm / ref))
    winter, _ = mean_of(air.WINTER_JK)
    return dict(rows=rows, ref=ref, winter=winter / ref, ref_weight=ref_w, cities=city_table(acc))


def city_table(acc: dict) -> dict:
    """The ratio of each city box (centre +- CITY_HALF deg, cells whose centre lies in it): Azar-Bahman 1404 over the
    summer reference, from the same cell sums. A city with fewer than 100 cells or weight under 50 is left out."""
    lon, lat = grid_axes(GRID)
    LO, LA = np.meshgrid(lon, lat)
    def sums(keys):
        return sum(acc[k]["S"] for k in keys), sum(acc[k]["W"] for k in keys)
    sw, ww = sums(air.WINTER_JK)
    sr, wr = sums(air.REF_JK)
    out = {}
    for name, (clo, cla) in CITIES.items():
        m = ((np.abs(LO - clo) < CITY_HALF) & (np.abs(LA - cla) < CITY_HALF)).ravel()
        if m.sum() < 100 or ww[m].sum() < 50 or wr[m].sum() < 50:
            continue
        cw, cr = sw[m].sum() / ww[m].sum(), sr[m].sum() / wr[m].sum()
        out[name] = dict(lon=clo, lat=cla, winter=float(cw), summer=float(cr), ratio=float(cw / cr),
                         cells=int(m.sum()))
    return out


# ── reading the film's inputs ──

def load_glow() -> tuple:
    z = np.load(GLOW_PATH)
    keys = [k for k in z.files if not k.startswith("cov_") and k != "iran"]
    return {k: z[k] for k in keys}, {k: z["cov_" + k] for k in keys}, z["iran"] > 0


def load_box() -> dict:
    return json.loads(BOX_PATH.read_text())


def load_relief() -> dict:
    z = np.load(REL_PATH)
    return {k: z[k] for k in z.files}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "relief":
        relief()
    elif cmd == "fields":
        build_fields()
    else:
        sys.exit("usage: air_grid.py relief | fields")
