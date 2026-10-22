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
for each of its two parts. Europe is soil.py's: the European countries of Natural Earth
inside 24.8 W-45 E, 34-71.5 N.

Check: ERA5 (Hersbach et al. 2020), 0.25 deg, 1940-2026, with the thirst computed here as the
reference evapotranspiration ET0 of FAO-56 (Allen et al. 1998, eq. 6) from monthly means of
2 m temperature and dewpoint, 10 m wind speed (to 2 m, eq. 47), net radiation and surface
pressure (soil heat flux 0; the saturation vapour pressure of the mean temperature puts ET0
somewhat low, a bias that drops out of the changes). From the 1960s on ERA5 and CRU TS agree
within about 10 mm per decade; in the 1940s and 1950s ERA5's rain is 20-35 mm per summer
below the stations', which would make those summers look as dry as today's. ERA5 has few
observations then and assimilates no rain gauges, so the reel uses CRU TS.

    outputs/water_log.txt       the numbers (printed)
    outputs/water_summers.csv   per summer: GMT, Europe's rain, thirst and balance (mm), CRU TS

Run with `python -I src/water.py > outputs/water_log.txt` after src/get_water.py.
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
SHORT = {"total_precipitation": "tp", "2m_temperature": "t2m", "2m_dewpoint_temperature": "d2m",
         "10m_wind_speed": "si10", "surface_net_solar_radiation": "ssr",
         "surface_net_thermal_radiation": "str", "surface_pressure": "sp"}


def era5(var: str, months=SEASON) -> xr.DataArray:
    files = sorted(WATER.glob(f"era5_{var}_*.nc"))
    v = xr.open_mfdataset(files, combine="nested", concat_dim="valid_time")[SHORT[var]].sortby("valid_time")
    # accumulations (rain, radiation) are stamped 06:00, the rest 00:00: align them on the day
    v = v.assign_coords(valid_time=v["valid_time"].dt.floor("D")).drop_vars(["expver", "number"], errors="ignore")
    return v.sel(valid_time=v["valid_time.month"].isin(months)).load()


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


def summers(months=SEASON):
    """(rain, thirst) in mm per season, as (year, lat, lon) arrays, and the coordinates."""
    tp = era5("total_precipitation", months)
    days = month_days(tp, "valid_time")
    tp = tp * 1000 * days
    t = era5("2m_temperature", months) - 273.15
    td = era5("2m_dewpoint_temperature", months) - 273.15
    rn = (era5("surface_net_solar_radiation", months) + era5("surface_net_thermal_radiation", months)) / 1e6
    e = et0(t, td, era5("10m_wind_speed", months), rn, era5("surface_pressure", months) / 1000) * days
    out = []
    for x in (tp, e):
        n = pd.Series(x["valid_time.year"].to_numpy()).value_counts()
        full = sorted(n.index[n == len(months)])
        out.append(x.groupby("valid_time.year").sum("valid_time").sel(year=full))
    rain, thirst = out
    return rain.to_numpy(), thirst.to_numpy(), rain["year"].to_numpy(), rain["latitude"].to_numpy(), \
        rain["longitude"].to_numpy()


def balance(rain, thirst, years, lat1, lon1) -> dict:
    """Europe's water balance per summer and per cell, its change against 1951-1980, and its
    link to global temperature, for (year, lat, lon) arrays of rain and thirst (mm)."""
    lat2, lon2 = np.meshgrid(lat1, lon1, indexing="ij")
    lat, lon = lat2.ravel(), lon2.ravel()
    r, e = rain.reshape(len(years), -1), thirst.reshape(len(years), -1)
    ok = np.isfinite(r).all(0) & np.isfinite(e).all(0) & soil.europe(lat, lon)
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
    return dict(years=years, gmt=t, gmt_months=months_last, lat=lat, lon=lon, w=w, rain=r, thirst=e,
                anom=anom, eu=eu, slopes=slopes, ends=ends, win_cells=win_cells,
                win_eu={k: np.convolve(v - v[base].mean(), kern, "valid") for k, v in eu.items()},
                win_gmt=np.convolve(t, kern, "valid"))


def compute() -> dict:
    """The record: CRU TS 4.10, rain (mm/month) and Penman-Monteith PET (mm/day), 1901-2025."""
    def load(var):
        v = xr.open_mfdataset(sorted(WATER.glob(f"cru_ts4.10.*.{var}.dat.nc")), combine="by_coords")[var]
        v = v.sel(lat=slice(34, 72), lon=slice(-25, 45))
        return v.sel(time=v["time.month"].isin(SEASON)).load()
    pre, pet = load("pre"), load("pet")
    pet = pet * month_days(pet, "time")
    rain, thirst = (x.groupby("time.year").sum("time", min_count=len(SEASON)) for x in (pre, pet))
    return balance(rain.to_numpy(), thirst.to_numpy(), rain["year"].to_numpy(), rain["lat"].to_numpy(),
                   rain["lon"].to_numpy())


def era5_check(months=SEASON) -> dict:
    """The same on ERA5 with FAO-56 ET0, 1940-2026."""
    return balance(*summers(months))


def report(d: dict, label: str) -> None:
    y = d["years"]
    base = (y >= BASE[0]) & (y <= BASE[1])
    last = slice(-DECADE, None)
    print(f"\n== {label}")
    print(f"cells {len(d['lat']):,}; summers {y[0]}-{y[-1]} ({len(y)}); GMT of {y[-1]}: {d['gmt_months']} months")
    for k in ("rain", "thirst", "balance"):
        v = d["eu"][k]
        s, ci = d["slopes"][k]
        print(f"{k:8s} {BASE[0]}-{BASE[1]}: {v[base].mean():6.0f} mm   {y[last][0]}-{y[-1]}: {v[last].mean():6.0f} mm"
              f"   change {v[last].mean() - v[base].mean():+5.0f} mm   per +1 C GMT {s:+5.0f} mm "
              f"[{ci[0]:+.0f}, {ci[1]:+.0f}]")
    a = d["win_cells"][-1]
    w = d["w"]
    print(f"last decade vs {BASE[0]}-{BASE[1]}: drier at {100 * w[a < 0].sum() / w.sum():.0f} % of Europe's "
          f"area; >= 25 mm drier {100 * w[a <= -25].sum() / w.sum():.0f} %, >= 50 mm {100 * w[a <= -50].sum() / w.sum():.0f} %, "
          f">= 25 mm wetter {100 * w[a >= 25].sum() / w.sum():.0f} %")
    b = d["eu"]["balance"] - d["eu"]["balance"][base].mean()
    top = np.argsort(b)[:6]
    print("driest summers (balance vs base): " + ", ".join(f"{y[i]} {b[i]:+.0f} mm" for i in top))
    k = np.arange(len(d["ends"]) - 1, -1, -DECADE)[::-1]
    print("decades (balance vs base): " + ", ".join(f"{e - DECADE + 1}-{str(e)[2:]} {v:+.0f} mm"
                                                   for e, v in zip(d["ends"][k], d["win_eu"]["balance"][k])))


def decades(runs: dict) -> None:
    """Each decade against 1951-1980, side by side: where the datasets part."""
    print("\n== decades against 1951-1980 (mm per summer): rain / thirst / balance")
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
    d = compute()
    report(d, "CRU TS 4.10, June-August, Penman-Monteith")
    OUT.mkdir(exist_ok=True)
    pd.DataFrame({"year": d["years"], "gmt_c": d["gmt"].round(3)} |
                 {f"{k}_mm": v.round(1) for k, v in d["eu"].items()}).to_csv(OUT / "water_summers.csv", index=False)
    e = era5_check()
    report(e, "check: ERA5, June-August, FAO-56 Penman-Monteith")
    decades({"CRU": d, "ERA5": e})


if __name__ == "__main__":
    main()
