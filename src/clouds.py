"""DO THE NEIGHBOURS STEAL IRAN'S RAIN? Iran's rain against its neighbours', year by year.

The claim ("ابردزدی", cloud theft): neighbours or rivals take the rain that would fall on
Iran (in July 2018 the head of Iran's Passive Defence Organisation said Israel and a
neighbour were stealing clouds and snow; Iran's Meteorological Organization answered that a
country cannot steal clouds). If rain were taken from Iran by a neighbour, the two would move
in opposite directions: a dry year in Iran a wet one next door. Measured data only:
- CRU TS 4.10 monthly precipitation (Harris et al. 2020, University of East Anglia; 0.5 deg,
  from stations), data/water/cru_ts4.10.*.pre.dat.nc (src/get_water.py).
- Countries: Natural Earth 50 m (enso.country_mask), cell centres, cos-latitude weights.
  The Arabian block is Saudi Arabia, Kuwait, the UAE, Oman, Qatar and Bahrain together.
- Water years October-September, named by September's year, 1952-2024 (73 years).

Numbers: each region's rain per water year in % of its own 1952-2024 mean; Pearson's r of
Iran's year-to-year rain with each neighbour's, raw and with both series detrended; the change
of each region's mean from 1952-1981 to 1995-2024; Iran's ten driest water years and in how
many of them each neighbour was below its own median. ERA5 monthly precipitation (data/snow,
1960-2024, the region the snow files cover) as a second estimate for Iran, Iraq, Afghanistan
and Turkmenistan. Correlation shows shared weather; it does not rule out a small local
effect of cloud seeding anywhere, and the reel does not claim that.

    python -I src/clouds.py > outputs/clouds_iran_log.txt
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import xarray as xr  # noqa: E402

import enso  # noqa: E402  (country masks without shapely)

ROOT = Path(__file__).resolve().parents[1]
YEARS = (1952, 2024)
EARLY, LATE = (1952, 1981), (1995, 2024)
REGIONS = {"Iran": ["Iran"], "Iraq": ["Iraq"], "Turkey": ["Turkey"], "Afghanistan": ["Afghanistan"],
           "Pakistan": ["Pakistan"], "Turkmenistan": ["Turkmenistan"], "Azerbaijan": ["Azerbaijan"],
           "Armenia": ["Armenia"],
           "Arabia": ["Saudi Arabia", "Kuwait", "United Arab Emirates", "Oman", "Qatar", "Bahrain"]}
ERA5_REGIONS = ("Iran", "Iraq", "Afghanistan", "Turkmenistan")   # inside the snow files' 25-43 N, 26-80 E


def water_years(monthly: pd.Series) -> pd.Series:
    """Oct-Sep totals named by September's year; complete years only."""
    label = monthly.index.year + (monthly.index.month >= 10)
    g = monthly.groupby(label)
    return g.sum()[g.count() == 12].loc[YEARS[0]:YEARS[1]]


@functools.cache
def cru() -> pd.DataFrame:
    """Water-year rain (mm) per region, CRU TS 4.10."""
    files = sorted((ROOT / "data" / "water").glob("cru_ts4.10.*.pre.dat.nc"))
    assert len(files) == 13
    pre = xr.concat([xr.open_dataset(f)["pre"].sel(lon=slice(25, 80), lat=slice(10, 45)).load() for f in files],
                    "time").sortby("time")
    lon, lat = np.meshgrid(pre.lon.values, pre.lat.values)
    out, cells = {}, {}
    for name, countries in REGIONS.items():
        m = enso.country_mask(countries, lat, lon)
        w = np.cos(np.deg2rad(lat[m]))                    # only the cells inside: the sea is NaN in CRU
        v = pre.values[:, m]
        assert np.isfinite(v).all(), f"{name}: a cell inside without data"
        cells[name] = int(m.sum())
        s = pd.Series(v @ w / w.sum(), pd.DatetimeIndex(pre.time.values))
        out[name] = water_years(s)
    df = pd.DataFrame(out)
    df.attrs["cells"] = cells
    assert cells["Iran"] == 621 and len(df) == YEARS[1] - YEARS[0] + 1
    return df


@functools.cache
def era5() -> pd.DataFrame:
    """Water-year rain (mm) from ERA5 monthly means (m/day x days), 1960 on: ERA5's rain before
    about 1960 is too dry (see reference notes)."""
    files = sorted((ROOT / "data" / "snow").glob("era5_total_precipitation_*.nc"))
    tp = xr.concat([xr.open_dataset(f)["tp"].load() for f in files], "valid_time").sortby("valid_time")
    t = pd.DatetimeIndex(tp.valid_time.values)
    mm = tp.values * 1000 * t.days_in_month.values[:, None, None]
    lon, lat = np.meshgrid(tp.longitude.values, tp.latitude.values)
    out = {}
    for name in ERA5_REGIONS:
        m = enso.country_mask(REGIONS[name], lat, lon)
        w = np.cos(np.deg2rad(lat[m]))
        s = pd.Series(mm[:, m] @ w / w.sum(), t)
        out[name] = water_years(s.loc["1959-10":])
    return pd.DataFrame(out).loc[1960:]


def pct(df: pd.DataFrame) -> pd.DataFrame:
    """Each region in % of its own mean over the years shown."""
    return 100 * df / df.mean()


def detrend(s: pd.Series) -> pd.Series:
    x = s.index.values.astype(float)
    return s - np.polyval(np.polyfit(x, s.values, 1), x)


def relations(df: pd.DataFrame) -> pd.DataFrame:
    """Per neighbour: r with Iran (raw, detrended), change early -> late, and Iran's ten driest
    years with the neighbour below its own median."""
    driest = df["Iran"].sort_values().index[:10]
    rows = []
    for name in df.columns:
        s = df[name]
        early, late = s.loc[EARLY[0]:EARLY[1]].mean(), s.loc[LATE[0]:LATE[1]].mean()
        rows.append(dict(region=name, r=float(np.corrcoef(df["Iran"], s)[0, 1]),
                         r_detrended=float(np.corrcoef(detrend(df["Iran"]), detrend(s))[0, 1]),
                         change_pct=float(100 * (late / early - 1)), early_mm=float(early), late_mm=float(late),
                         dry_with_iran=int((s.loc[driest] < s.median()).sum())))
    out = pd.DataFrame(rows).set_index("region")
    out.attrs["driest"] = [int(y) for y in driest]
    return out


def main() -> None:
    df = cru()
    rel = relations(df)
    print(f"CRU TS 4.10, water years Oct-Sep {YEARS[0]}-{YEARS[1]} ({len(df)}); cells: {df.attrs['cells']}")
    print(f"Iran's ten driest water years: {rel.attrs['driest']}")
    print(f"{'region':14s} {'r':>6s} {'r detr.':>8s} {'early mm':>9s} {'late mm':>8s} {'change':>8s} "
          f"{'dry with Iran (of 10)':>22s}")
    for name, r in rel.iterrows():
        print(f"{name:14s} {r.r:+6.2f} {r.r_detrended:+8.2f} {r.early_mm:9.1f} {r.late_mm:8.1f} "
              f"{r.change_pct:+7.1f}% {int(r.dry_with_iran):22d}")
    nb = rel.drop("Iran")
    print(f"\nneighbours with r < 0: {int((nb.r < 0).sum())} of {len(nb)}; mean r {nb.r.mean():+.2f}")
    e = era5()
    erel = relations(e)
    print(f"\nERA5 check, water years {e.index[0]}-{e.index[-1]} ({len(e)}): Iran's ten driest {erel.attrs['driest']}")
    for name, r in erel.iterrows():
        print(f"  {name:14s} r {r.r:+.2f} (detrended {r.r_detrended:+.2f}), change {r.change_pct:+.1f}%, "
              f"dry with Iran {int(r.dry_with_iran)} of 10")


if __name__ == "__main__":
    main()
