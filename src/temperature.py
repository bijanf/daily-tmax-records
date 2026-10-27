"""HOW MUCH HAS IRAN WARMED? Iran's mean temperature against the world's land, one dataset.

Measured data only. CRU TS 4.10 monthly mean temperature (Harris et al. 2020, University of
East Anglia; 0.5 deg, from stations), data/water/cru_ts4.10.*.tmp.dat.nc (src/get_water.py).
Iran = the 621 cells of enso.iran_mask (Natural Earth 50 m), world land = every CRU cell with
data (land without Antarctica), both cos-latitude weighted: land against land, the same grid
and the same stations' method, so the ratio is like for like (an ocean-and-land index such as
HadCRUT warms less than land).

Numbers: annual means; change = mean 2016-2025 minus mean 1951-1980; trend 1975-2025 by least
squares with a moving-block bootstrap (blocks of 5 years, 10,000 draws) for its 95 % interval;
the meteorological seasons (Mar-May, Jun-Aug, Sep-Nov, Dec-Feb) and the spread over Iran's
cells, to see whether "3 to 5 degrees" holds anywhere. Also how many of Iran's ten warmest years
since 1951 fall after 2000.

    python -I src/temperature.py > outputs/temperature_iran_log.txt
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import xarray as xr  # noqa: E402

import enso  # noqa: E402  (its Iran mask, without shapely)

ROOT = Path(__file__).resolve().parents[1]
CRU = ROOT / "data" / "water"
THEN, NOW, TREND = (1951, 1980), (2016, 2025), (1975, 2025)
SEASONS = {"spring (Mar-May)": (3, 4, 5), "summer (Jun-Aug)": (6, 7, 8), "autumn (Sep-Nov)": (9, 10, 11),
           "winter (Dec-Feb)": (12, 1, 2)}
DRAWS, BLOCK, SEED = 10_000, 5, 20261027


@functools.cache
def tmp() -> xr.DataArray:
    files = sorted(CRU.glob("cru_ts4.10.*.tmp.dat.nc"))
    assert len(files) == 13, f"CRU TS 4.10 temperature: {len(files)} of 13 files (src/get_water.py)"
    return xr.concat([xr.open_dataset(f)["tmp"].load() for f in files], "time").sortby("time")


def weights(t: xr.DataArray, mask: xr.DataArray | None) -> xr.DataArray:
    w = np.cos(np.deg2rad(t.lat)) * xr.ones_like(t.isel(time=0))
    w = w.where(np.isfinite(t).all("time"))                # cells with every month: no coverage drift
    return w if mask is None else w.where(mask)


@functools.cache
def series() -> pd.DataFrame:
    """Annual means 1901-2025 (°C) for Iran and the world's land; and Iran by season."""
    t = tmp()
    lon, lat = np.meshgrid(t.lon.values, t.lat.values)
    iran = xr.DataArray(enso.iran_mask(lat, lon), dims=("lat", "lon"), coords=dict(lat=t.lat, lon=t.lon))
    assert int(iran.sum()) == 621
    out, n = {}, {}
    for name, mask in (("iran", iran), ("land", None)):
        w = weights(t, mask)
        n[name] = int(np.isfinite(w).sum())
        m = (t * w).sum(("lat", "lon")) / w.sum()
        out[name] = m.groupby("time.year").mean().to_series()
    df = pd.DataFrame(out)
    w = weights(t, iran)
    monthly = ((t * w).sum(("lat", "lon")) / w.sum()).to_series()
    for name, months in SEASONS.items():
        s = monthly[monthly.index.month.isin(months)]
        label = s.index.year + ((s.index.month == 12) & (months[0] == 12)).astype(int)
        g = s.groupby(label)
        df[name] = g.mean()[g.count() == 3]
    df.attrs["cells"] = n
    return df


def change(s: pd.Series) -> float:
    return float(s.loc[NOW[0]:NOW[1]].mean() - s.loc[THEN[0]:THEN[1]].mean())


def trend(s: pd.Series) -> tuple[float, float, float]:
    """°C per decade over TREND by least squares, with a moving-block bootstrap 95 % interval of
    the residuals."""
    y = s.loc[TREND[0]:TREND[1]]
    x = y.index.values.astype(float)
    b, a = np.polyfit(x, y.values, 1)
    fit = a + b * x
    res = y.values - fit
    rng = np.random.default_rng(SEED)
    n, slopes = len(res), []
    starts = np.arange(n - BLOCK + 1)
    for _ in range(DRAWS):
        idx = np.concatenate([np.arange(k, k + BLOCK) for k in rng.choice(starts, n // BLOCK + 1)])[:n]
        slopes.append(np.polyfit(x, fit + res[idx], 1)[0])
    lo, hi = np.percentile(slopes, [2.5, 97.5])
    return 10 * b, 10 * lo, 10 * hi


@functools.cache
def era5() -> pd.Series:
    """The check: ERA5 monthly 2 m temperature over the same Iran (data/snow, src/get_snow.py),
    annual means of complete years, °C."""
    files = sorted((ROOT / "data" / "snow").glob("era5_2m_temperature_*.nc"))
    t = xr.concat([xr.open_dataset(f)["t2m"].load() for f in files], "valid_time").sortby("valid_time")
    lon, lat = np.meshgrid(t.longitude.values, t.latitude.values)
    w = np.cos(np.deg2rad(lat)) * enso.iran_mask(lat, lon)
    s = pd.Series((t.values - 273.15).reshape(len(t), -1) @ w.ravel() / w.sum(), pd.DatetimeIndex(t.valid_time.values))
    n = s.groupby(s.index.year).count()
    return s.groupby(s.index.year).mean()[n == 12]


def cells() -> np.ndarray:
    """Change 1951-1980 -> 2016-2025 in each Iran cell (°C)."""
    t = tmp()
    lon, lat = np.meshgrid(t.lon.values, t.lat.values)
    inside = enso.iran_mask(lat, lon)
    a = t.groupby("time.year").mean()
    d = a.sel(year=slice(*NOW)).mean("year") - a.sel(year=slice(*THEN)).mean("year")
    return d.values[inside]


def main() -> None:
    df = series()
    print(f"CRU TS 4.10 mean temperature, {df.index[0]}-{df.index[-1]}; cells with every month: "
          f"world land {df.attrs['cells']['land']}, Iran {df.attrs['cells']['iran']}")
    for name in ("iran", "land"):
        s = df[name]
        b, lo, hi = trend(s)
        print(f"\n== {name}: {THEN[0]}-{THEN[1]} mean {s.loc[THEN[0]:THEN[1]].mean():.2f} °C, "
              f"{NOW[0]}-{NOW[1]} {s.loc[NOW[0]:NOW[1]].mean():.2f} °C: change {change(s):+.2f} °C")
        print(f"  trend {TREND[0]}-{TREND[1]}: {b:+.3f} °C/decade (95 % {lo:+.3f} to {hi:+.3f}), "
              f"= {5 * b:+.2f} °C in 50 years")
        warm = s.loc[1951:].sort_values(ascending=False)
        top = list(warm.index[:10])
        print(f"  ten warmest years since 1951: {top}; after 2000: {sum(y > 2000 for y in top)} of 10")
    ratio = change(df["iran"]) / change(df["land"])
    print(f"\nIran / world land change: {ratio:.2f}")
    e = era5()
    b, lo, hi = trend(e)
    top = list(e.loc[1951:].sort_values(ascending=False).index[:10])
    print(f"ERA5 check (Iran, {e.index[0]}-{e.index[-1]}): change {change(e):+.2f} °C, trend {b:+.3f} °C/decade "
          f"(95 % {lo:+.3f} to {hi:+.3f}); ten warmest since 1951 {top}, after 2000: {sum(y > 2000 for y in top)} of 10")
    print("\nIran by season (change 1951-1980 -> 2016-2025):")
    for name in SEASONS:
        print(f"  {name}: {change(df[name]):+.2f} °C")
    d = cells()
    print(f"\nIran's cells: change median {np.median(d):+.2f}, 5-95 % {np.percentile(d, 5):+.2f} to "
          f"{np.percentile(d, 95):+.2f}, max {d.max():+.2f} °C; cells >= 3 °C: {int((d >= 3).sum())} of {d.size}")


if __name__ == "__main__":
    main()
