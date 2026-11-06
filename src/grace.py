"""IRAN'S WATER, WEIGHED FROM SPACE: the change of the water stored in Iran's land (total water storage: groundwater,
soil water, snow, lakes and reservoirs together) from the GRACE and GRACE-FO gravity satellites, per Persian solar
year, against the mean of 1382-1384 (April 2003 to March 2006). The data of onebit_grace.py.

Inputs (src/get_grace.py, data/grace/): three solutions of the same satellites, CSR RL06.3 mascons (x 1.025: CSR
gives equivalent water height at 1025 kg/m3), GSFC RL06 v2.0 mascons, COST-G RL02 GravIS TWS (combined spherical
harmonics, filtered); the Caspian's level from altimetry (G-REALM 000270); Natural Earth 10 m countries.

Method (the feasibility check of 6 Nov 2026, ~/Documents/instagram_research/feasibility/feas_grace/README.md):
- Masks on each product's grid by sub-sampling each cell (pyshp + matplotlib.path, no shapely): Iran's share of the
  cell; the Caspian = cells in the Caspian's box outside Iran, Azerbaijan, Russia, Kazakhstan and Turkmenistan; the
  distance of each cell to the nearest Caspian water (great circle, R 6371 km).
- Iran's mean (area-weighted) per month in cm of water; the seasons removed (mean annual and semi-annual cycle fitted
  with a trend over the whole record); the months of GRACE's end and GRACE-FO's start (Jul 2017 to May 2018) missing.
- THE CASPIAN: the sea fell about 2 m since 2003-2005 (altimetry), and at GRACE's ~300 km resolution part of that
  loss leaks into northern Iran. The counter therefore uses Iran's land more than 200 km from the Caspian (85 % of
  Iran), its mean in cm applied to all of Iran's area ("interior"). The same numbers for all of Iran ("all") are
  in the log: they are larger by the leakage.
- A Persian year P holds the months whose solution date lies from 21 March of P + 621 to 20 March of P + 622 (the
  solutions are dated mid-month, so a March solution belongs to the year before); a year with fewer than 6 months is
  partial (shown as no data on the map, never counted).
- km3 = cm x Iran's area (this product's mask) x 1e-5; 1 km3 = 1 billion m3 («میلیارد مترمکعب»).
- The counter: per year the mean of the three products' interior values; its range: their smallest and largest.
- The map: GSFC (its Caspian sits in its own ocean-like mascons, so its Iran cells leak least), per cell with the
  seasons removed, the Persian year's mean against the cell's 1382-1384 mean; cells holding Caspian water are empty
  and filled from the nearest land cell for the picture; ~300 km resolution: the patches are not single aquifers.

    data/grace/grace_reel.npz     the counter table and the GSFC yearly maps for the film
    python -I src/grace.py > outputs/grace_log.txt
"""

from __future__ import annotations

import datetime as dt
import sys
import warnings
from pathlib import Path

import numpy as np
import shapefile
import xarray as xr
from matplotlib.path import Path as MPath

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "grace"
NE = DATA / "ne_10m_admin_0_countries" / "ne_10m_admin_0_countries"
R = 6371.0
WIN = (18.0, 52.0, 35.0, 75.0)                              # S, N, W, E: the region read from each product
PRODUCTS = {
    "csr": dict(file="CSR_GRACE_GRACE-FO_RL0603_Mascons_all-corrections.nc", var="lwe_thickness", fac=1.025,
                t0=dt.date(2002, 1, 1), nsub=4, name="CSR RL06.3 mascons"),
    "gsfc": dict(file="GSFC.glb_.200204_202606_RL06v2.0_OBP-ICE6GD_HALFDEGREE.nc", var="lwe_thickness", fac=1.0,
                 t0=dt.date(2002, 1, 1), nsub=6, name="GSFC RL06 v2.0 mascons"),
    "costg": dict(file="GRAVIS-3_COSTG_0200_TWS_GRID_GFZ_0001.nc", var="tws", fac=1.0,
                  t0=dt.date(2002, 4, 18), nsub=10, name="COST-G RL02 GravIS"),
}
BASE_YEARS = (1382, 1383, 1384)                            # April 2003 to March 2006
FULL_MONTHS = 6                                            # a year with fewer months is partial (seasons removed: 6 months give the year)
INTERIOR_KM = 200                                          # km from the Caspian: the leakage-safe part of Iran
CASPIAN_BOX = (36.4, 47.4, 46.4, 55.2)                     # S, N, W, E
NEIGHBOURS = ("IRN", "AZE", "RUS", "KAZ", "TKM")
MAP_PRODUCT = "gsfc"


def persian_year(d: dt.date) -> int:
    return d.year - 621 if (d.month, d.day) >= (3, 21) else d.year - 622


def polygons(reader, idx: int) -> list:
    shp = reader.shape(idx)
    pts = np.asarray(shp.points)
    parts = list(shp.parts) + [len(pts)]
    return [MPath(pts[parts[i]:parts[i + 1]]) for i in range(len(parts) - 1)]


def countries() -> dict:
    rc = shapefile.Reader(str(NE))
    fields = [f[0] for f in rc.fields[1:]]
    idx = {dict(zip(fields, r))["ADM0_A3"]: i for i, r in enumerate(rc.records())}
    return {k: polygons(rc, idx[k]) for k in NEIGHBOURS}


def share_inside(paths: list, lat: np.ndarray, lon: np.ndarray, nsub: int) -> np.ndarray:
    """The share of each cell (centres lat x lon) inside the polygons, from nsub x nsub points per cell."""
    dlat, dlon = abs(lat[1] - lat[0]), abs(lon[1] - lon[0])
    off = (np.arange(nsub) + 0.5) / nsub - 0.5
    LA, LO = np.meshgrid(lat, lon, indexing="ij")
    hits = np.zeros(LA.shape)
    for oy in off:
        for ox in off:
            p = np.column_stack([(LO + ox * dlon).ravel(), (LA + oy * dlat).ravel()])
            hit = np.zeros(len(p), bool)
            for pa in paths:
                bb = pa.get_extents()
                sel = (p[:, 0] >= bb.x0) & (p[:, 0] <= bb.x1) & (p[:, 1] >= bb.y0) & (p[:, 1] <= bb.y1)
                if sel.any():
                    hit[sel] |= pa.contains_points(p[sel])
            hits += hit.reshape(LA.shape)
    return hits / nsub ** 2


def cell_area(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    dlat, dlon = np.deg2rad(abs(lat[1] - lat[0])), np.deg2rad(abs(lon[1] - lon[0]))
    phi = np.deg2rad(lat)
    a = R ** 2 * dlon * (np.sin(phi + dlat / 2) - np.sin(phi - dlat / 2))
    return np.repeat(a[:, None], len(lon), axis=1)


def great_circle(lat1, lon1, lat2, lon2):
    p1, p2 = np.deg2rad(lat1), np.deg2rad(lat2)
    c = np.sin(p1) * np.sin(p2) + np.cos(p1) * np.cos(p2) * np.cos(np.deg2rad(lon2 - lon1))
    return R * np.arccos(np.clip(c, -1, 1))


def masks(lat: np.ndarray, lon: np.ndarray, nsub: int, polys: dict) -> dict:
    """Iran's share, the Caspian's share, the cell areas (km2) and each cell's distance to the Caspian (km)."""
    iran = share_inside(polys["IRN"], lat, lon, nsub)
    land = np.zeros_like(iran)
    for p in polys.values():
        land = np.maximum(land, share_inside(p, lat, lon, nsub))
    LA, LO = np.meshgrid(lat, lon, indexing="ij")
    s, n, w, e = CASPIAN_BOX
    casp = np.where((LA > s) & (LA < n) & (LO > w) & (LO < e), 1 - land, 0.0)
    casp[casp < 0.05] = 0
    fla, flo = np.arange(s + 0.05, n, 0.1), np.arange(w + 0.05, e, 0.1)     # the Caspian's water on a 0.1-deg grid
    FL, FO = np.meshgrid(fla, flo, indexing="ij")
    pts = np.column_stack([FO.ravel(), FL.ravel()])
    inland = np.zeros(len(pts), bool)
    for p in polys.values():
        for pa in p:
            inland |= pa.contains_points(pts)
    water = pts[~inland]
    dist = np.full(LA.shape, np.inf)
    for chunk in np.array_split(water, 20):
        dist = np.minimum(dist, great_circle(LA[..., None], LO[..., None], chunk[None, None, :, 1],
                                             chunk[None, None, :, 0]).min(axis=-1))
    return dict(iran=iran, casp=casp, area=cell_area(lat, lon), dist=dist)


def load(key: str, polys: dict) -> dict:
    """One product over the region: the field (months, lat, lon) in cm of fresh water, the dates and the masks."""
    p = PRODUCTS[key]
    ds = xr.open_dataset(DATA / p["file"], decode_times=False, engine="netcdf4")
    lat, lon = ds["lat"].values, ds["lon"].values
    jl = np.where((lat >= WIN[0]) & (lat <= WIN[1]))[0]
    il = np.where((lon >= WIN[2]) & (lon <= WIN[3]))[0]
    field = ds[p["var"]].isel(lat=jl, lon=il).values.astype(float) * p["fac"]
    dates = [p["t0"] + dt.timedelta(days=float(x)) for x in ds["time"].values.astype(float)]
    m = masks(lat[jl], lon[il], p["nsub"], polys)
    return dict(key=key, field=field, dates=dates, lat=lat[jl], lon=lon[il], **m)


def decimal_year(d: dt.date) -> float:
    y0, y1 = dt.date(d.year, 1, 1), dt.date(d.year + 1, 1, 1)
    return d.year + (d - y0).days / (y1 - y0).days


def design(t: np.ndarray) -> np.ndarray:
    w = 2 * np.pi * t
    return np.column_stack([np.ones_like(t), t - 2010.0, np.cos(w), np.sin(w), np.cos(2 * w), np.sin(2 * w)])


def deseason(t: np.ndarray, y: np.ndarray) -> np.ndarray:
    """y without its mean annual and semi-annual cycle (fitted with a trend over the whole record); y may be
    (months,) or (months, cells)."""
    X = design(t)
    Y = y.reshape(len(t), -1)
    out = np.full(Y.shape, np.nan)
    good = np.all(np.isfinite(Y), axis=0)
    beta, *_ = np.linalg.lstsq(X, Y[:, good], rcond=None)
    out[:, good] = Y[:, good] - X[:, 2:] @ beta[2:]
    return out.reshape(y.shape)


def trend(t: np.ndarray, y: np.ndarray) -> tuple:
    """The linear trend (per year) with the seasons fitted, and its standard error adjusted for lag-1 correlation."""
    X = design(t)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ beta
    n, k = X.shape
    se = np.sqrt((r @ r) / (n - k) * np.linalg.inv(X.T @ X)[1, 1])
    r1 = np.corrcoef(r[:-1], r[1:])[0, 1]
    neff = n * (1 - r1) / (1 + r1)
    return beta[1], se * np.sqrt((n - k) / max(neff - k, 2))


def mean_over(field: np.ndarray, w: np.ndarray) -> np.ndarray:
    w = np.where(np.isfinite(field[0]), w, 0.0)
    return np.nansum(field * w, axis=(1, 2)) / w.sum()


def series(d: dict) -> dict:
    """Iran's monthly mean (cm), seasons removed, for all of Iran and for the interior; and the areas (km2)."""
    t = np.array([decimal_year(x) for x in d["dates"]])
    w_all = d["iran"] * d["area"]
    w_int = w_all * (d["dist"] > INTERIOR_KM)
    out = dict(t=t, area=float(w_all.sum()), area_int=float(w_int.sum()))
    for name, w in (("all", w_all), ("int", w_int)):
        raw = mean_over(d["field"], w)
        out[name + "_raw"] = raw
        out[name] = deseason(t, raw)
    out["casp"] = deseason(t, mean_over(d["field"], d["casp"] * d["area"]))
    return out


def yearly(dates: list, values: np.ndarray, base: np.ndarray) -> dict:
    """Per Persian year: the mean of the months (values minus the base mean) and the month count."""
    py = np.array([persian_year(x) for x in dates])
    out = {}
    for y in range(min(py), max(py) + 1):
        sel = py == y
        out[y] = (np.nanmean(values[sel], axis=0) - base if sel.any() else np.nan, int(sel.sum()))
    return out


def caspian_level() -> tuple:
    """The Caspian's level (m) from G-REALM 000270: decimal years and heights (the file's 10-day product)."""
    t, h = [], []
    for line in open(DATA / "lake000270.10d.2.txt"):
        p = line.split()
        if len(p) < 6 or not (p[2].isdigit() and len(p[2]) == 8):
            continue
        try:
            v = float(p[5])
        except ValueError:
            continue
        if v > 900:
            continue
        d = dt.date(int(p[2][:4]), int(p[2][4:6]), int(p[2][6:8]))
        t.append(d)
        h.append(v)
    return t, np.array(h)


def main() -> None:
    polys = countries()
    runs, years = {}, None
    for key, p in PRODUCTS.items():
        d = load(key, polys)
        s = series(d)
        py = np.array([persian_year(x) for x in d["dates"]])
        base = np.isin(py, BASE_YEARS)
        rows = {}
        for name in ("all", "int"):
            km3 = s[name] * s["area"] * 1e-5                         # the interior's mean applied to all of Iran's area
            rows[name] = yearly(d["dates"], km3, np.nanmean(km3[base]))
        runs[key] = dict(d=d, s=s, rows=rows, base_n=int(base.sum()))
        years = sorted(rows["int"]) if years is None else sorted(set(years) & set(rows["int"]))
        print(f"{p['name']}: {len(d['dates'])} months, {d['dates'][0]} to {d['dates'][-1]}; Iran mask "
              f"{s['area'] / 1e6:.4f} million km2, interior (> {INTERIOR_KM} km from the Caspian) "
              f"{s['area_int'] / 1e6:.4f} ({100 * s['area_int'] / s['area']:.0f} %); base months {int(base.sum())}")
        for name in ("all", "int"):
            b, se = trend(s["t"], s[name + "_raw"])
            print(f"    trend {name:3s} {b:+.3f} +- {se:.3f} cm/yr = {b * s['area'] * 1e-5:+.1f} +- "
                  f"{se * s['area'] * 1e-5:.1f} km3/yr (whole record, seasons fitted)")
    print()
    print("per Persian year, km3 against 1382-1384 (interior applied to all of Iran; 'all' = all of Iran, with the "
          "Caspian's leakage); n = months")
    print("year   n(csr gsfc costg)  csr_int gsfc_int costg_int | mean  min  max | csr_all gsfc_all costg_all  flag")
    table = []
    for y in years:
        n = [runs[k]["rows"]["int"][y][1] for k in PRODUCTS]
        vi = [runs[k]["rows"]["int"][y][0] for k in PRODUCTS]
        va = [runs[k]["rows"]["all"][y][0] for k in PRODUCTS]
        partial = min(n) < FULL_MONTHS
        row = dict(year=y, n=n, int=vi, all=va, mean=float(np.mean(vi)), lo=float(min(vi)), hi=float(max(vi)),
                   partial=partial)
        table.append(row)
        print(f"{y}  {n[0]:3d} {n[1]:3d} {n[2]:3d}     " + " ".join(f"{v:+7.0f}" for v in vi)
              + f" | {row['mean']:+5.0f} {row['lo']:+5.0f} {row['hi']:+5.0f} | " + " ".join(f"{v:+7.0f}" for v in va)
              + ("   partial: not counted" if partial else ""))
    full = [r for r in table if not r["partial"]]
    last = full[-1]
    low = min(full, key=lambda r: r["mean"])
    print()
    print(f"last full year {last['year']}: {last['mean']:+.0f} km3 (products {last['lo']:+.0f} to {last['hi']:+.0f}); "
          f"all of Iran with leakage {min(last['all']):+.0f} to {max(last['all']):+.0f}")
    print(f"lowest year: {low['year']} {low['mean']:+.0f} km3")
    wet = [r for r in full if 1395 <= r["year"] <= 1400]
    print("the wet years' rebound: " + ", ".join(f"{r['year']} {r['mean']:+.0f}" for r in wet))
    # the Caspian, for the log: altimetry against GRACE's Caspian cells
    tc, hc = caspian_level()
    pyc = np.array([persian_year(x) for x in tc])
    h0 = hc[np.isin(pyc, BASE_YEARS)].mean()
    h1 = hc[pyc == last["year"]].mean()
    print(f"Caspian level (altimetry, G-REALM 000270): {last['year']} against 1382-1384 {h1 - h0:+.2f} m "
          f"(about {(h1 - h0) * 371000 * 1e-3:+.0f} km3 at 371,000 km2)")
    # comparisons
    renew, withdraw = 128.5, 93.0                                  # km3/yr: AQUASTAT via World Bank (fact check)
    print(f"comparisons: {-last['mean'] / renew:.2f} years of Iran's internal renewable water ({renew} km3/yr; "
          f"range {-last['hi'] / renew:.2f}-{-last['lo'] / renew:.2f}); {-last['mean'] / withdraw:.2f} years of "
          f"withdrawals ({withdraw} km3/yr)")
    # the map: GSFC, per cell, seasons removed, Persian-year means against 1382-1384
    d = runs[MAP_PRODUCT]["d"]
    t = runs[MAP_PRODUCT]["s"]["t"]
    cells = deseason(t, d["field"])
    py = np.array([persian_year(x) for x in d["dates"]])
    base_map = np.nanmean(cells[np.isin(py, BASE_YEARS)], axis=0)
    maps, counts = [], []
    for y in years:
        sel = py == y
        maps.append(np.nanmean(cells[sel], axis=0) - base_map if sel.sum() >= FULL_MONTHS else
                    np.full(base_map.shape, np.nan))
        counts.append(int(sel.sum()))
    maps = np.array(maps)
    maps[:, d["casp"] > 0.02] = np.nan                             # the Caspian's own cells: not Iran
    inside = d["iran"] > 0.5
    print(f"map ({PRODUCTS[MAP_PRODUCT]['name']}): Iran cells {int(inside.sum())}; "
          f"{last['year']} Iran-cell mean {np.nanmean(maps[years.index(last['year'])][inside]):+.1f} cm, "
          f"5th percentile {np.nanpercentile(maps[years.index(last['year'])][inside], 5):+.1f} cm, "
          f"95th {np.nanpercentile(maps[years.index(last['year'])][inside], 95):+.1f} cm")
    np.savez_compressed(DATA / "grace_reel.npz", years=np.array(years),
                        mean=np.array([r["mean"] for r in table]), lo=np.array([r["lo"] for r in table]),
                        hi=np.array([r["hi"] for r in table]), partial=np.array([r["partial"] for r in table]),
                        nmonths=np.array([r["n"] for r in table]), products=np.array([r["int"] for r in table]),
                        product_names=np.array(list(PRODUCTS)), maps=maps.astype(np.float32),
                        map_months=np.array(counts), lat=d["lat"], lon=d["lon"], iran=d["iran"].astype(np.float32),
                        casp=d["casp"].astype(np.float32), last=last["year"])
    print("saved", DATA / "grace_reel.npz")


if __name__ == "__main__":
    main()
    sys.stdout.flush()
