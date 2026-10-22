"""Europe's summer soil drought against global warming (ERA5-Land soil water, HadCRUT5).

Every 0.1 deg land cell of Europe gets the water in its top metre of soil in each summer
(June to August, mean of the monthly means): the volumetric water of ERA5-Land's layers 1-3
(0-7, 7-28, 28-100 cm) weighted by their depth. A summer is a soil drought where it is drier
than nine of the ten summers 1951-1980 at that cell, i.e. below the cell's 10th percentile of
that period. A stable climate puts 10 % of Europe in soil drought in an average summer.

    area     share of Europe's land (by area) in soil drought, per summer
    decade   the same, averaged over ten summers, and each cell's count of drought summers
    GMT      global mean surface temperature, annual, against 1850-1900 (HadCRUT5 analysis);
             the current year is the mean of its published months

The link to warming is the least-squares slope of the area on GMT; its 95 % interval comes
from a moving-block bootstrap of the summers (blocks of five, 10 000 draws), so runs of dry
and wet years stay together.

Europe: the land of the countries Natural Earth assigns to Europe inside 24.8 W-45 E,
34-71.5 N (Russia is cut at 45 E; the Azores and Svalbard fall outside), without cells whose
soil water barely varies (glaciers: fewer than 25 distinct summers in 1951-1980).

    outputs/soil_log.txt       the numbers (printed)
    outputs/soil_summers.csv   per summer: GMT, share of Europe in soil drought

Checks in the log: the 20th percentile, April to September, and the NOAA CPC soil moisture
model instead of ERA5-Land.

Run with `python -I src/soil.py > outputs/soil_log.txt` after src/get_soil.py.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
SOIL = ROOT / "data" / "soil"
OUT = ROOT / "outputs"
DEPTH = {1: 7, 2: 21, 3: 72}             # cm of each ERA5-Land layer in the top metre
SEASON = (6, 7, 8)
BASE = (1951, 1980)
Q = 0.10
DECADE = 10
BLOCK, DRAWS = 5, 10_000


def gmt() -> tuple[pd.Series, int]:
    """Annual global mean temperature against 1850-1900 and the number of months of the last year."""
    m = pd.read_csv(SOIL / "hadcrut5_global_monthly.csv")
    t = pd.to_datetime(m["Time"])
    s = pd.Series(m["Anomaly (deg C)"].to_numpy(), index=t)
    s = s - s["1850":"1900"].mean()
    year = s.groupby(s.index.year)
    return year.mean(), int(year.size().iloc[-1])


def root_zone(months=SEASON) -> xr.DataArray:
    """Water in the top metre (m3/m3), per year, mean of the given months."""
    theta = 0
    for k, cm in DEPTH.items():
        files = sorted(SOIL.glob(f"era5land_swvl{k}_*.nc"))
        v = xr.open_mfdataset(files, combine="nested", concat_dim="valid_time")[f"swvl{k}"]
        v = v.sortby("valid_time")
        v = v.sel(valid_time=v["valid_time.month"].isin(months))
        theta = theta + v * cm / sum(DEPTH.values())
    n = pd.Series(theta["valid_time.year"].to_numpy()).value_counts()
    full = sorted(n.index[n == len(months)])
    return theta.groupby("valid_time.year").mean("valid_time").sel(year=full).load()


def europe(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """True on the cells inside a European country (Natural Earth 50m), see the module note."""
    import cartopy.io.shapereader as shpreader
    import shapely
    from shapely.ops import unary_union

    shapes = shpreader.Reader(shpreader.natural_earth("50m", "cultural", "admin_0_countries"))
    geoms = [r.geometry for r in shapes.records() if r.attributes["CONTINENT"] == "Europe"]
    eu = unary_union(geoms)
    shapely.prepare(eu)
    return shapely.contains_xy(eu, lon, lat) & (lat < 71.5) & (lon > -24.8) & (lon < 45)


def block_bootstrap(x: np.ndarray, y: np.ndarray, rng) -> np.ndarray:
    """Least-squares slopes of y on x for moving-block resamples of the pairs."""
    n = len(x)
    starts = np.arange(n - BLOCK + 1)
    k = -(-n // BLOCK)
    out = np.empty(DRAWS)
    for i in range(DRAWS):
        idx = (rng.choice(starts, k)[:, None] + np.arange(BLOCK)).ravel()[:n]
        out[i] = np.polyfit(x[idx], y[idx], 1)[0]
    return out


def compute(months=SEASON, q: float = Q) -> dict:
    """The statistics on ERA5-Land."""
    theta = root_zone(months)
    return droughts(theta.to_numpy(), theta["year"].to_numpy(), theta["latitude"].to_numpy(),
                    theta["longitude"].to_numpy(), months, q)


def cpc(months=SEASON, q: float = Q) -> dict:
    """The same statistics on an independent model: NOAA CPC soil moisture (Fan & van den
    Dool 2004), a one-layer bucket of up to 760 mm driven by observed rain and temperature, 0.5 deg."""
    v = xr.open_dataset(SOIL / "cpc_soilw_mon_v2.nc")["soilw"]
    v = v.assign_coords(lon=((v["lon"] + 180) % 360) - 180).sortby("lon").sel(lat=slice(72, 34), lon=slice(-25, 45))
    v = v.sel(time=v["time.month"].isin(months))
    by_year = v.groupby("time.year")
    full = by_year.count("time").max(("lat", "lon")) == len(months)
    v = by_year.mean("time").sel(year=full["year"][full]).load()
    return droughts(v.to_numpy(), v["year"].to_numpy(), v["lat"].to_numpy(), v["lon"].to_numpy(), months, q)


def droughts(theta: np.ndarray, years: np.ndarray, lat1: np.ndarray, lon1: np.ndarray, months, q) -> dict:
    """Soil drought per cell and summer, Europe's share in drought, and its link to GMT, for a
    (year, lat, lon) array of seasonal soil water."""
    lat2, lon2 = np.meshgrid(lat1, lon1, indexing="ij")
    a = theta.reshape(len(years), -1)
    lat, lon = lat2.ravel(), lon2.ravel()
    base = (years >= BASE[0]) & (years <= BASE[1])
    ok = np.isfinite(a).all(0) & europe(lat, lon)
    varies = 1 + (np.diff(np.sort(a[base][:, ok], 0), axis=0) > 0).sum(0) >= 25
    ok[np.flatnonzero(ok)[~varies]] = False
    a, lat, lon = a[:, ok], lat[ok], lon[ok]
    thr = np.quantile(a[base], q, axis=0)
    dry = a < thr
    w = np.cos(np.radians(lat))
    area = dry @ w / w.sum()
    g, months_last = gmt()
    years = years[np.isin(years, g.index)]
    dry, a, area = dry[:len(years)], a[:len(years)], area[:len(years)]
    t = g.loc[years].to_numpy()
    slope, icept = np.polyfit(t, area, 1)
    boot = block_bootstrap(t, area, np.random.default_rng(7))
    # ten-summer windows ending in each year
    ends = years[DECADE - 1:]
    kern = np.ones(DECADE)
    win_area = np.convolve(area, kern, "valid") / DECADE
    win_gmt = np.convolve(t, kern, "valid") / DECADE
    win_cells = np.stack([dry[i:i + DECADE].sum(0) for i in range(len(ends))])   # drought summers per cell
    return dict(years=years, gmt=t, gmt_months=months_last, area=area, dry=dry, theta=a, thr=thr,
                lat=lat, lon=lon, w=w, slope=slope, icept=icept, ci=np.percentile(boot, [2.5, 97.5]),
                p_flat=float(np.mean(boot <= 0)), ends=ends, win_area=win_area, win_gmt=win_gmt,
                win_cells=win_cells, months=months, q=q)


def report(d: dict, label: str) -> None:
    y, area, t = d["years"], d["area"], d["gmt"]
    base = (y >= BASE[0]) & (y <= BASE[1])
    last = slice(-DECADE, None)
    print(f"\n== {label}")
    print(f"cells {len(d['lat']):,}; summers {y[0]}-{y[-1]} ({len(y)}); GMT of {y[-1]}: "
          f"{d['gmt_months']} months")
    print(f"area in soil drought, {BASE[0]}-{BASE[1]}: {100 * area[base].mean():.1f} % (by construction ~"
          f"{100 * d['q']:.0f} %); GMT {t[base].mean():+.2f} C")
    print(f"area in soil drought, {y[last][0]}-{y[-1]}: {100 * area[last].mean():.1f} %; GMT "
          f"{t[last].mean():+.2f} C; ratio {area[last].mean() / area[base].mean():.2f}")
    print(f"slope: {100 * d['slope']:+.1f} %-points of Europe per +1 C GMT, 95 % CI "
          f"[{100 * d['ci'][0]:+.1f}, {100 * d['ci'][1]:+.1f}], share of draws <= 0: {d['p_flat']:.4f}")
    print(f"fit at +0.3 C: {100 * (d['icept'] + 0.3 * d['slope']):.1f} %; at +1.3 C: "
          f"{100 * (d['icept'] + 1.3 * d['slope']):.1f} %")
    for lo, hi in ((-1, 0.5), (0.5, 1.0), (1.0, 9)):
        m = (t >= lo) & (t < hi)
        print(f"  GMT {lo:+.1f} to {hi:+.1f} C: {m.sum():2d} summers, mean area {100 * area[m].mean():.1f} %")
    top = np.argsort(area)[::-1][:8]
    print("driest summers: " + ", ".join(f"{y[i]} {100 * area[i]:.0f} %" for i in top))
    k = np.arange(len(d["ends"]) - 1, -1, -DECADE)[::-1]      # decades ending in the last summer
    print("decades: " + ", ".join(f"{e - DECADE + 1}-{str(e)[2:]} {100 * v:.1f} % ({g:+.2f} C)"
                                  for e, v, g in zip(d["ends"][k], d["win_area"][k], d["win_gmt"][k])))
    cells = d["win_cells"][-1]
    w = d["w"]
    print(f"last window: area where >= 3 of 10 summers were droughts {100 * w[cells >= 3].sum() / w.sum():.1f} %, "
          f">= 5: {100 * w[cells >= 5].sum() / w.sum():.1f} %, none: {100 * w[cells == 0].sum() / w.sum():.1f} %")


def main() -> None:
    d = compute()
    report(d, "June-August, below the 1951-1980 10th percentile")
    OUT.mkdir(exist_ok=True)
    pd.DataFrame({"year": d["years"], "gmt_c": d["gmt"].round(3), "area_pct": (100 * d["area"]).round(2)}
                 ).to_csv(OUT / "soil_summers.csv", index=False)
    report(compute(q=0.20), "check: June-August, below the 20th percentile")
    report(compute(months=(4, 5, 6, 7, 8, 9)), "check: April-September")
    report(cpc(), "check: NOAA CPC soil moisture, June-August, 10th percentile")


if __name__ == "__main__":
    main()
