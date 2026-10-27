"""THE WATER YEAR 1404-1405: how much rain Iran got from 1 Mehr 1404 to 31 Shahrivar 1405.

Measured data only. CHIRPS v3.0 daily rain over Iran and Tehran province (get_chirps.py; Climate
Hazards Center, UC Santa Barbara; 0.05 deg, stations blended with satellite estimates), summed
over the Persian calendar's months: a water year runs from 1 Mehr to 31 Shahrivar (1 Mehr 1404
= 23 September 2025). The calendar is the arithmetic of the jalaali algorithm (Borkowski 1996, as
in jalaali-js), which matches Iran's official calendar for these years (checked: 1 Farvardin 1404
= 21 March 2025, 1 Farvardin 1405 = 21 March 2026, 1 Mehr 1404 = 23 September 2025).

Normal = the mean of the water years 1370-1371 to 1399-1400 (about 1991-2020, the WMO normal).
Ranks run over every complete water year in CHIRPS, 1360-1361 to 1404-1405 (45), 1 = driest.
Checks: CHIRPS "sat" (the days split by IMERG instead of ERA5; the months are the same sums),
and ERA5 monthly means (data/snow) for October-September, the Gregorian approximation, which
ERA5 can rank over 1960-61 to 2025-26 (its August and September 2026 are still preliminary).

    python -I src/wateryear.py > outputs/wateryear_iran_log.txt
"""

from __future__ import annotations

import functools
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CHIRPS = ROOT / "data" / "chirps" / "chirps_iran_daily.csv"
NOW = 1404                                       # the water year 1404-1405
NORMAL = (1370, 1399)                            # water years 1370-71 to 1399-1400
MONTHS = ("مهر", "آبان", "آذر", "دی", "بهمن", "اسفند", "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور")
BREAKS = (-61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210, 1635, 2060, 2097, 2192, 2262, 2324, 2394, 2456, 3178)


def _div(a: int, b: int) -> int:
    return int(a / b)


def _mod(a: int, b: int) -> int:
    return a - _div(a, b) * b


def farvardin1(jy: int) -> date:
    """The Gregorian date of 1 Farvardin of the Persian year jy (jalaali-js, jalCal)."""
    gy, leap_j, jp, jump = jy + 621, -14, BREAKS[0], 0
    for jm in BREAKS[1:]:
        jump = jm - jp
        if jy < jm:
            break
        leap_j += _div(jump, 33) * 8 + _div(_mod(jump, 33), 4)
        jp = jm
    n = jy - jp
    leap_j += _div(n, 33) * 8 + _div(_mod(n, 33) + 3, 4)
    if _mod(jump, 33) == 4 and jump - n == 4:
        leap_j += 1
    leap_g = _div(gy, 4) - _div((_div(gy, 100) + 1) * 3, 4) - 150
    return date(gy, 3, 20 + leap_j - leap_g)


def months(jy: int) -> list[tuple[date, date]]:
    """The twelve months of the water year jy-(jy+1), Mehr to Shahrivar: (first day, day after)."""
    starts = [farvardin1(jy) + timedelta(days=186 + 30 * k) for k in range(6)]      # Mehr..Esfand
    starts += [farvardin1(jy + 1) + timedelta(days=31 * k) for k in range(6)]       # Farvardin..Shahrivar
    return list(zip(starts, starts[1:] + [farvardin1(jy + 1) + timedelta(days=186)]))


@functools.cache
def daily(product: str = "rnl") -> pd.DataFrame:
    d = pd.read_csv(CHIRPS, parse_dates=["date"])
    return d[d["product"] == product].set_index("date").drop(columns="product").sort_index()


@functools.cache
def table(product: str = "rnl", region: str = "iran") -> pd.DataFrame:
    """mm per Persian month (columns Mehr..Shahrivar) and the year's total, every complete water
    year in the data (rows: the water year's first Persian year)."""
    s = daily(product)[region]
    first = s.index[0].date()
    rows = {}
    for jy in range(1350, 1450):
        ms = months(jy)
        if ms[0][0] < first:
            continue
        if ms[-1][1] - timedelta(days=1) > s.index[-1].date():
            break
        vals = []
        for a, b in ms:
            part = s.loc[pd.Timestamp(a):pd.Timestamp(b) - pd.Timedelta(days=1)]
            assert len(part) == (b - a).days, (jy, a)
            vals.append(float(part.sum()))
        rows[jy] = vals
    t = pd.DataFrame.from_dict(rows, orient="index", columns=MONTHS)
    t["year"] = t.sum(axis=1)
    return t


def report(t: pd.DataFrame, label: str) -> dict:
    """The water year NOW and the one before against the normal; a series that starts later (CHIRPS
    sat, 1998) uses the normal's years it has, and says so."""
    base = t.loc[NORMAL[0]:NORMAL[1]]
    if label.startswith("Iran, CHIRPS rnl") or label.startswith("Tehran"):
        assert len(base) == NORMAL[1] - NORMAL[0] + 1, "the normal needs all 30 water years"
    normal = base.mean()
    rank = t.rank(method="min")                       # 1 = driest
    now, before = t.loc[NOW], t.loc[NOW - 1]
    print(f"\n== {label}: water years {t.index[0]}-{t.index[0] + 1} to {t.index[-1]}-{t.index[-1] + 1} ({len(t)})")
    print(f"  normal ({base.index[0]}-{base.index[0] + 1} to {base.index[-1]}-{base.index[-1] + 1}, {len(base)} years): "
          f"{normal['year']:.1f} mm")
    print(f"  {NOW}-{NOW + 1}: {now['year']:.1f} mm = {100 * now['year'] / normal['year']:.0f} % of normal, "
          f"rank {int(rank.loc[NOW, 'year'])} of {len(t)} (1 = driest)")
    print(f"  {NOW - 1}-{NOW}: {before['year']:.1f} mm = {100 * before['year'] / normal['year']:.0f} % of normal, "
          f"rank {int(rank.loc[NOW - 1, 'year'])} of {len(t)}")
    for m in MONTHS:
        print(f"    {m:9s} {now[m]:6.1f} mm, normal {normal[m]:5.1f}, {100 * now[m] / normal[m]:4.0f} %, "
              f"rank {int(rank.loc[NOW, m]):2d} of {len(t)}")
    autumn = list(MONTHS[:3])
    a = t[autumn].sum(axis=1)
    print(f"  autumn Mehr-Azar {NOW}: {a.loc[NOW]:.1f} mm = {100 * a.loc[NOW] / a.loc[NORMAL[0]:NORMAL[1]].mean():.0f} % "
          f"of normal, rank {int(a.rank(method='min').loc[NOW])} of {len(t)}")
    ma = t[["مهر", "آبان"]].sum(axis=1)
    print(f"  Mehr+Aban {NOW}: {ma.loc[NOW]:.1f} mm = {100 * ma.loc[NOW] / ma.loc[NORMAL[0]:NORMAL[1]].mean():.0f} % of "
          f"normal, rank {int(ma.rank(method='min').loc[NOW])} of {len(t)}")
    return dict(normal=normal, now=now, before=before, rank=rank, n=len(t))


@functools.cache
def era5_oct_sep(region: str = "iran") -> pd.Series:
    """ERA5 rain per October-September (named by its October year), 1960-61 on, over Iran or
    Tehran province."""
    import xarray as xr
    import enso
    import get_chirps
    files = sorted((ROOT / "data" / "snow").glob("era5_total_precipitation_*.nc"))
    tp = xr.concat([xr.open_dataset(f)["tp"].load() for f in files], "valid_time").sortby("valid_time")
    t = pd.DatetimeIndex(tp.valid_time.values)
    mm = tp.values * 1000 * t.days_in_month.values[:, None, None]
    lon, lat = np.meshgrid(tp.longitude.values, tp.latitude.values)
    m = enso.iran_mask(lat, lon) if region == "iran" else get_chirps.province("Tehran", lat, lon)
    w = np.cos(np.deg2rad(lat[m]))
    s = pd.Series(mm[:, m] @ w / w.sum(), t).loc["1960-10":]
    label = s.index.year - (s.index.month < 10)
    g = s.groupby(label)
    return g.sum()[g.count() == 12]


def main() -> None:
    for jy, want in ((1404, date(2025, 3, 21)), (1405, date(2026, 3, 21))):
        assert farvardin1(jy) == want, (jy, farvardin1(jy))
    assert months(1404)[0][0] == date(2025, 9, 23)
    print(f"CHIRPS v3.0 daily, {CHIRPS.name}: rnl {daily('rnl').index[0]:%Y-%m-%d} to {daily('rnl').index[-1]:%Y-%m-%d}")
    print(f"water year {NOW}-{NOW + 1}: {months(NOW)[0][0]} to {months(NOW)[-1][1] - timedelta(days=1)}")
    report(table("rnl", "iran"), "Iran, CHIRPS rnl")
    report(table("sat", "iran"), "Iran, CHIRPS sat (check)")
    report(table("rnl", "tehran"), "Tehran province, CHIRPS rnl")
    for region in ("iran", "tehran"):
        e = era5_oct_sep(region)
        normal = e.loc[1991:2020].mean()
        r = e.rank(method="min")
        print(f"\n== ERA5 check, {region}, October-September {e.index[0]}-{e.index[0] + 1} to "
              f"{e.index[-1]}-{e.index[-1] + 1} ({len(e)})")
        for y in (2024, 2025):
            print(f"  {y}-{y + 1}: {e.loc[y]:.1f} mm = {100 * e.loc[y] / normal:.0f} % of 1991-2020, rank {int(r.loc[y])} of {len(e)}")


if __name__ == "__main__":
    main()
