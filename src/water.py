"""Europe's summer water deficit against global warming, 1901-2025 (CRU TS; ERA5 check).

Every land cell of Europe gets the water balance of its summer (June to August):

    rain     precipitation
    thirst   the air's demand: Penman-Monteith potential evapotranspiration
    balance  rain - thirst, mm per summer; below 0 the summer has a water deficit

The record is CRU TS 4.10 (Harris et al. 2020): station-based rain and Penman-Monteith
potential evapotranspiration at 0.5 deg, 1901-2025, the input of the SPEI drought index
(Vicente-Serrano et al. 2010). Changes are against 1951-1980, by cell and as Europe's
area-weighted mean. The link to warming is the least-squares slope on global temperature
(HadCRUT5 against 1850-1900) with a moving-block bootstrap, as in soil.py, for the balance and
for each of its two parts. Europe is soil.py's (the European countries of Natural Earth)
inside the frame of the reel's map, 11 W-42 E, 34-71.5 N: without Iceland and the land east
of 42 E.

Check: ERA5 (Hersbach et al. 2020), 0.25 deg, 1940-2026, with the thirst computed here as the
reference evapotranspiration ET0 of FAO-56 (Allen et al. 1998, eq. 6) from monthly means of
2 m temperature and dewpoint, 10 m wind speed (to 2 m, eq. 47), net radiation and surface
pressure (soil heat flux 0; the saturation vapour pressure of the mean temperature puts ET0
somewhat low, a bias that drops out of the changes). From the 1960s on ERA5 and CRU TS agree
within about 10 mm per decade; in the 1940s and 1950s ERA5's rain is 20-35 mm per summer
below the stations', which would make those summers look as dry as today's. ERA5 has few
observations then and assimilates no rain gauges, so the reel uses CRU TS.

Iran (--region iran): the water year October-September, from 1951, when CRU TS has stations
within reach of every cell of the country (before 1941 about three cells in four); the ERA5
check runs on ERA5 fields over Iran.

    outputs/water_log.txt            the numbers (printed)
    outputs/water_summers.csv        per summer: GMT, Europe's rain, thirst and balance (mm), CRU TS
    outputs/water_iran_years.csv     the same per water year for Iran

Run with `python -I src/water.py [--region iran] > outputs/water[_iran]_log.txt` after src/get_water.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import xarray as xr  # noqa: E402

import soil  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WATER = ROOT / "data" / "water"
OUT = ROOT / "outputs"
SEASON = (6, 7, 8)
BASE = soil.BASE
DECADE = soil.DECADE
# season: the months summed, or "water" for the water year October-September, named by the year
# it ends in (Iran's rain falls October to May); first: the first season with stations everywhere
# (CRU TS station counts: Iran from 1951); frame: lon0, lon1, lat0, lat1 of the reel's map
REGIONS = {
    "europe": dict(season=SEASON, first=1901, frame=(-11, 42, 34, 71.5), country=None, unit="summer"),
    "iran": dict(season="water", first=1951, frame=(43.5, 63.8, 24.8, 40.2), country="Iran", unit="water year"),
}
SHORT = {"total_precipitation": "tp", "2m_temperature": "t2m", "2m_dewpoint_temperature": "d2m",
         "10m_wind_speed": "si10", "surface_net_solar_radiation": "ssr",
         "surface_net_thermal_radiation": "str", "surface_pressure": "sp"}


def era5(var: str, tag: str = "") -> xr.DataArray:
    files = sorted(WATER.glob(f"era5_{tag}{var}_*.nc"))
    v = xr.open_mfdataset(files, combine="nested", concat_dim="valid_time")[SHORT[var]].sortby("valid_time")
    # accumulations (rain, radiation) are stamped 06:00, the rest 00:00: align them on the day
    v = v.assign_coords(valid_time=v["valid_time"].dt.floor("D")).drop_vars(["expver", "number"], errors="ignore")
    return v.load()


def inside(region: str, lat, lon) -> np.ndarray:
    """True on the land cells of a region inside its map frame: soil.py's Europe, or a country
    of Natural Earth (50m)."""
    R = REGIONS[region]
    x0, x1, y0, y1 = R["frame"]
    box = (lon > x0) & (lon < x1) & (lat > y0) & (lat < y1)
    if R["country"] is None:
        return box & soil.europe(lat, lon)
    import cartopy.io.shapereader as shpreader
    import shapely

    geom = next(r.geometry for r in shpreader.Reader(shpreader.natural_earth("50m", "cultural", "admin_0_countries"))
                .records() if r.attributes["NAME"] == R["country"])
    shapely.prepare(geom)
    return box & shapely.contains_xy(geom, lon, lat)


def seasons(x: xr.DataArray, dim: str, season) -> xr.DataArray:
    """Totals per season (the months of a tuple, or the water year); a cell missing a month is NaN
    and incomplete seasons are dropped."""
    t = pd.DatetimeIndex(x[dim].values)
    if season == "water":
        label, need = np.asarray(t.year + (t.month >= 10)), 12
    else:
        keep = np.isin(t.month, season)
        x, label, need = x.isel({dim: keep}), np.asarray(t.year[keep]), len(season)
    n = pd.Series(label).value_counts()
    full = sorted(n.index[n == need])
    year = xr.DataArray(label, dims=dim, coords={dim: x[dim]}, name="year")
    return x.groupby(year).sum(dim, min_count=need).sel(year=full)


def month_days(x: xr.DataArray, dim: str) -> xr.DataArray:
    return xr.DataArray(pd.DatetimeIndex(x[dim].values).days_in_month, dims=dim, coords={dim: x[dim]})


def es(t):
    """Saturation vapour pressure (kPa) at t (deg C), FAO-56 eq. 11."""
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))


def et0(t, td, wind10, rn, p):
    """FAO-56 Penman-Monteith reference evapotranspiration (mm/day) from daily means: t, td in
    deg C, wind at 10 m (m/s), net radiation (MJ/m2/day), pressure (kPa); G = 0."""
    u2 = wind10 * 4.87 / np.log(67.8 * 10 - 5.42)
    gamma = 0.000665 * p
    delta = 4098 * es(t) / (t + 237.3) ** 2
    vpd = np.maximum(es(t) - es(td), 0)
    return (0.408 * delta * rn + gamma * 900 / (t + 273) * u2 * vpd) / (delta + gamma * (1 + 0.34 * u2))


def era5_seasons(region: str = "europe"):
    """ERA5 (rain, thirst) in mm per season, thirst as FAO-56 ET0, as (year, lat, lon) arrays,
    and the coordinates."""
    tag = "" if region == "europe" else f"{region}_"
    tp = era5("total_precipitation", tag)
    days = month_days(tp, "valid_time")
    tp = tp * 1000 * days
    t = era5("2m_temperature", tag) - 273.15
    td = era5("2m_dewpoint_temperature", tag) - 273.15
    rn = (era5("surface_net_solar_radiation", tag) + era5("surface_net_thermal_radiation", tag)) / 1e6
    e = et0(t, td, era5("10m_wind_speed", tag), rn, era5("surface_pressure", tag) / 1000) * days
    rain, thirst = (seasons(x, "valid_time", REGIONS[region]["season"]) for x in (tp, e))
    return rain.to_numpy(), thirst.to_numpy(), rain["year"].to_numpy(), rain["latitude"].to_numpy(), \
        rain["longitude"].to_numpy()


def balance(rain, thirst, years, lat1, lon1, region: str = "europe") -> dict:
    """A region's water balance per season and per cell, its change against 1951-1980, and its
    link to global temperature, for (year, lat, lon) arrays of rain and thirst (mm)."""
    lat2, lon2 = np.meshgrid(lat1, lon1, indexing="ij")
    lat, lon = lat2.ravel(), lon2.ravel()
    r, e = rain.reshape(len(years), -1), thirst.reshape(len(years), -1)
    ok = np.isfinite(r).all(0) & np.isfinite(e).all(0) & inside(region, lat, lon)
    g, months_last = soil.gmt()
    months_last = months_last if years[-1] == g.index[-1] else 12
    keep = np.isin(years, g.index)
    years, r, e, lat, lon = years[keep], r[keep][:, ok], e[keep][:, ok], lat[ok], lon[ok]
    b = r - e
    base = (years >= BASE[0]) & (years <= BASE[1])
    anom = b - b[base].mean(0)                               # per cell, mm
    w = np.cos(np.radians(lat))
    eu = {k: x @ w / w.sum() for k, x in (("rain", r), ("thirst", e), ("balance", b))}
    t = g.loc[years].to_numpy()
    rng = np.random.default_rng(7)
    slopes = {k: (np.polyfit(t, v, 1)[0], np.percentile(soil.block_bootstrap(t, v, rng), [2.5, 97.5]))
              for k, v in eu.items()}
    ends = years[DECADE - 1:]
    kern = np.ones(DECADE) / DECADE
    win_cells = np.stack([anom[i:i + DECADE].mean(0) for i in range(len(ends))])   # mm, per cell
    return dict(region=region, years=years, gmt=t, gmt_months=months_last, lat=lat, lon=lon, w=w, rain=r, thirst=e,
                anom=anom, eu=eu, slopes=slopes, ends=ends, win_cells=win_cells,
                win_eu={k: np.convolve(v - v[base].mean(), kern, "valid") for k, v in eu.items()},
                win_gmt=np.convolve(t, kern, "valid"))


def compute(region: str = "europe") -> dict:
    """The record: CRU TS 4.10, rain (mm/month) and Penman-Monteith PET (mm/day), per season."""
    R = REGIONS[region]
    x0, x1, y0, y1 = R["frame"]

    def load(var):
        v = xr.open_mfdataset(sorted(WATER.glob(f"cru_ts4.10.*.{var}.dat.nc")), combine="by_coords")[var]
        return v.sel(lat=slice(y0 - 1, y1 + 1), lon=slice(x0 - 1, x1 + 1)).load()
    pre, pet = load("pre"), load("pet")
    pet = pet * month_days(pet, "time")
    rain, thirst = (seasons(x, "time", R["season"]) for x in (pre, pet))
    rain, thirst = (x.sel(year=x["year"] >= R["first"]) for x in (rain, thirst))
    return balance(rain.to_numpy(), thirst.to_numpy(), rain["year"].to_numpy(), rain["lat"].to_numpy(),
                   rain["lon"].to_numpy(), region)


def era5_check(region: str = "europe") -> dict:
    """The same on ERA5 with FAO-56 ET0, 1940 on (Iran: 1951 on)."""
    rain, thirst, years, lat, lon = era5_seasons(region)
    keep = years >= max(REGIONS[region]["first"], 1940)
    return balance(rain[keep], thirst[keep], years[keep], lat, lon, region)


def report(d: dict, label: str) -> None:
    y = d["years"]
    base = (y >= BASE[0]) & (y <= BASE[1])
    last = slice(-DECADE, None)
    print(f"\n== {label}")
    unit = REGIONS[d["region"]]["unit"]
    print(f"cells {len(d['lat']):,}; {unit}s {y[0]}-{y[-1]} ({len(y)}); GMT of {y[-1]}: {d['gmt_months']} months")
    for k in ("rain", "thirst", "balance"):
        v = d["eu"][k]
        s, ci = d["slopes"][k]
        print(f"{k:8s} {BASE[0]}-{BASE[1]}: {v[base].mean():6.0f} mm   {y[last][0]}-{y[-1]}: {v[last].mean():6.0f} mm"
              f"   change {v[last].mean() - v[base].mean():+5.0f} mm   per +1 C GMT {s:+5.0f} mm "
              f"[{ci[0]:+.0f}, {ci[1]:+.0f}]")
    a = d["win_cells"][-1]
    w = d["w"]
    print(f"last decade vs {BASE[0]}-{BASE[1]}: drier at {100 * w[a < 0].sum() / w.sum():.0f} % of the "
          f"area; >= 25 mm drier {100 * w[a <= -25].sum() / w.sum():.0f} %, >= 50 mm {100 * w[a <= -50].sum() / w.sum():.0f} %, "
          f">= 25 mm wetter {100 * w[a >= 25].sum() / w.sum():.0f} %")
    b = d["eu"]["balance"] - d["eu"]["balance"][base].mean()
    top = np.argsort(b)[:6]
    print(f"driest {unit}s (balance vs base): " + ", ".join(f"{y[i]} {b[i]:+.0f} mm" for i in top))
    k = np.arange(len(d["ends"]) - 1, -1, -DECADE)[::-1]
    print("decades (balance vs base): " + ", ".join(f"{e - DECADE + 1}-{str(e)[2:]} {v:+.0f} mm"
                                                   for e, v in zip(d["ends"][k], d["win_eu"]["balance"][k])))


def decades(runs: dict) -> None:
    """Each decade against 1951-1980, side by side: where the datasets part."""
    print("\n== decades against 1951-1980 (mm per season): rain / thirst / balance")
    for d0 in range(1900, 2030, 10):
        row = f"{d0}s"
        for name, d in runs.items():
            y = d["years"]
            base, m = (y >= BASE[0]) & (y <= BASE[1]), (y >= d0) & (y < d0 + 10)
            if m.sum() >= 5:
                row += f"   {name} " + " / ".join(f"{d['eu'][k][m].mean() - d['eu'][k][base].mean():+4.0f}"
                                               for k in ("rain", "thirst", "balance"))
        print(row)


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="europe", choices=list(REGIONS))
    region = ap.parse_args().region
    season = "June-August" if region == "europe" else "water year October-September"
    d = compute(region)
    report(d, f"CRU TS 4.10, {region}, {season}, Penman-Monteith")
    OUT.mkdir(exist_ok=True)
    name = "water_summers.csv" if region == "europe" else f"water_{region}_years.csv"
    pd.DataFrame({"year": d["years"], "gmt_c": d["gmt"].round(3)} |
                 {f"{k}_mm": v.round(1) for k, v in d["eu"].items()}).to_csv(OUT / name, index=False)
    if any(WATER.glob(f"era5_{'' if region == 'europe' else region + '_'}total_precipitation_*.nc")):
        e = era5_check(region)
        report(e, f"check: ERA5, {region}, {season}, FAO-56 Penman-Monteith")
        decades({"CRU": d, "ERA5": e})


if __name__ == "__main__":
    main()
