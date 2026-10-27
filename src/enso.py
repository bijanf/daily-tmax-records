"""EL NIÑO AND IRAN'S RAIN: is an El Niño autumn or winter wetter in Iran than other years?

Measured data only, no forecast. Sources:
- Oceanic Niño Index (ONI), NOAA Climate Prediction Center, 3-month running mean of the Niño-3.4
  sea-surface temperature anomaly (ERSSTv5), from 1950:
  https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt (fetched into data/enso/).
- Rain: CRU TS 4.10 monthly precipitation (Harris et al. 2020, University of East Anglia; 0.5 deg,
  from stations), data/water/cru_ts4.10.*.pre.dat.nc (src/get_water.py).

Iran = CRU cells whose centres lie in Natural Earth's 50 m Iran polygon (621 cells), cos-latitude
weights. A season is El Niño when the ONI of that same 3-month season is at least +1.0 °C, La Niña
at most -1.0 °C, neutral otherwise (+-0.5 and +-1.5 as checks). "Wetter" = Iran's rain that season
above the 1951-2024 median of the same season. Seasons 1951-2024. The design was fixed before the
numbers were seen, for September-November and December-February (named by its January);
October-December and January-March were added before they were computed, because Persian autumn
(Mehr-Azar, 23 Sep-21 Dec) and winter (Dey-Esfand, 22 Dec-20 Mar) are closer to them: the reel
says پاییز and زمستان only if both definitions agree, else it names the months.

Tests: permutation of the season labels (10,000 shuffles, two-sided) for El Niño minus neutral
mean rain, and Spearman's rank correlation of the ONI with the rain. Small samples (about ten El
Niño seasons each), no correction across the seasons and thresholds: read as suggestive.

    python -I src/enso.py > outputs/enso_iran_log.txt
"""

from __future__ import annotations

import functools
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import xarray as xr  # noqa: E402
from scipy import stats  # noqa: E402

import water  # noqa: E402  (its Iran mask, loaded after the netCDF files: shapely first crashes the heap)

ROOT = Path(__file__).resolve().parents[1]
ONI_FILE = ROOT / "data" / "enso" / "oni.ascii.txt"
ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
CRU = ROOT / "data" / "water"
YEARS = (1951, 2024)
THRESHOLD = 1.0                                  # °C: El Niño at or above, La Niña at or below minus
CHECKS = (0.5, 1.5)
# season: its months and its ONI label; a season that starts in December is named by its January
SEASONS = {"SON": (9, 10, 11), "OND": (10, 11, 12), "DJF": (12, 1, 2), "JFM": (1, 2, 3)}
SHUFFLES, SEED = 10_000, 20261027
BOX = (43.0, 65.0, 24.0, 41.0)                  # W, E, S, N read from CRU; the polygon decides


def oni() -> pd.DataFrame:
    """The ONI table: season label, year, value (°C); downloaded once."""
    if not ONI_FILE.exists():
        ONI_FILE.parent.mkdir(parents=True, exist_ok=True)
        part = ONI_FILE.with_suffix(".part")
        urllib.request.urlretrieve(ONI_URL, part)
        part.rename(ONI_FILE)
    rows = [(p[0], int(p[1]), float(p[3])) for p in (line.split() for line in ONI_FILE.read_text().splitlines())
            if len(p) == 4 and p[1].isdigit()]
    df = pd.DataFrame(rows, columns=["season", "year", "oni"])
    assert not df.duplicated(["season", "year"]).any()
    return df


@functools.cache
def iran_rain() -> tuple[pd.Series, xr.DataArray]:
    """Iran's monthly rain (mm, cos-lat mean of the cells inside Iran) and the cells themselves."""
    files = sorted(CRU.glob("cru_ts4.10.*.pre.dat.nc"))
    assert len(files) == 13, f"CRU TS 4.10 precipitation: {len(files)} of 13 files (src/get_water.py)"
    pre = xr.concat([xr.open_dataset(f)["pre"].sel(lon=slice(BOX[0], BOX[1]), lat=slice(BOX[2], BOX[3])).load()
                     for f in files], "time").sortby("time")
    lon, lat = np.meshgrid(pre.lon.values, pre.lat.values)
    inside = xr.DataArray(water.inside("iran", lat, lon), dims=("lat", "lon"), coords=dict(lat=pre.lat, lon=pre.lon))
    cells = pre.where(inside)
    assert int(inside.sum()) == 621 and np.isfinite(cells.values[:, inside.values]).all()
    w = np.cos(np.deg2rad(pre.lat)) * inside
    mean = (cells * w).sum(("lat", "lon")) / w.sum()
    return mean.to_series(), cells


def seasonal(monthly: pd.Series, season: str) -> pd.Series:
    """Sum of the season's three months per year, YEARS only, each season complete."""
    months = SEASONS[season]
    s = monthly[monthly.index.month.isin(months)]
    label = s.index.year + ((s.index.month == 12) & (months[0] == 12)).astype(int)
    g = s.groupby(label)
    out = g.sum()[g.count() == 3]
    out = out.loc[YEARS[0]:YEARS[1]]
    assert len(out) == YEARS[1] - YEARS[0] + 1, season
    return out


def classes(o: pd.Series, threshold: float) -> pd.Series:
    o = o.round(2)
    return pd.Series(np.where(o >= threshold, "El Niño", np.where(o <= -threshold, "La Niña", "neutral")), o.index)


def shuffle_p(rain: pd.Series, cls: pd.Series, rng) -> float:
    """Two-sided permutation p of the El Niño minus neutral difference of mean rain."""
    r, c = rain.values, cls.values
    obs = r[c == "El Niño"].mean() - r[c == "neutral"].mean()
    perm = np.argsort(rng.random((SHUFFLES, len(c))), axis=1)
    cp = c[perm]
    en, ne = (cp == "El Niño"), (cp == "neutral")
    d = (en * r).sum(1) / en.sum(1) - (ne * r).sum(1) / ne.sum(1)
    return (1 + np.sum(np.abs(d) >= abs(obs) - 1e-12)) / (SHUFFLES + 1)


@functools.cache
def result(season: str, threshold: float = THRESHOLD) -> dict:
    """Everything the reel shows for one season, and what the caption needs."""
    monthly, _ = iran_rain()
    rain = seasonal(monthly, season)
    o = oni().query("season == @season").set_index("year")["oni"].loc[rain.index]
    assert len(o) == len(rain)
    cls = classes(o, threshold)
    median = float(rain.median())
    en = cls == "El Niño"
    years = [int(y) for y in rain.index[en]]
    wetter = {y: bool(rain[y] > median) for y in years}
    pct = 100 * (rain / rain.mean() - 1)
    rho, rho_p = stats.spearmanr(o, rain)
    return dict(season=season, threshold=threshold, n=len(rain), mean=float(rain.mean()), median=median,
                years=years, wetter=wetter, n_wetter=sum(wetter.values()),
                oni={y: float(o[y]) for y in years},
                pct={k: float(pct[cls == k].mean()) for k in ("El Niño", "neutral", "La Niña")},
                count={k: int((cls == k).sum()) for k in ("El Niño", "neutral", "La Niña")},
                mm_en=float(rain[en].mean()), mm_neutral=float(rain[cls == "neutral"].mean()),
                p=shuffle_p(rain, cls, np.random.default_rng(SEED)), rho=float(rho), rho_p=float(rho_p),
                rain={int(y): float(v) for y, v in rain.items()})


def main() -> None:
    monthly, cells = iran_rain()
    print(f"Iran: {int(np.isfinite(cells.isel(time=0)).sum())} CRU TS 4.10 cells, months "
          f"{monthly.index[0]:%Y-%m} to {monthly.index[-1]:%Y-%m}; ONI {ONI_FILE.name}, last row "
          f"{oni().iloc[-1].season} {oni().iloc[-1].year} = {oni().iloc[-1].oni:+.2f}")
    annual = monthly.loc[f"{YEARS[0]}":f"{YEARS[1]}"].groupby(monthly.loc[f"{YEARS[0]}":f"{YEARS[1]}"].index.year).sum()
    print(f"Iran's mean annual rain {YEARS[0]}-{YEARS[1]}: {annual.mean():.1f} mm")
    for season in SEASONS:
        r = result(season)
        print(f"\n== {season} {YEARS[0]}-{YEARS[1]}: mean {r['mean']:.1f} mm "
              f"({100 * r['mean'] / annual.mean():.0f} % of the year), median {r['median']:.1f} mm")
        print(f"  El Niño seasons (ONI >= {THRESHOLD}): {r['count']['El Niño']}, neutral {r['count']['neutral']}, "
              f"La Niña {r['count']['La Niña']}")
        print("  " + ", ".join(f"{y} ({r['oni'][y]:+.1f}, {r['rain'][y]:.0f} mm, {'wetter' if r['wetter'][y] else 'drier'})"
                               for y in r["years"]))
        print(f"  wetter than the median: {r['n_wetter']} of {len(r['years'])}")
        print(f"  mean rain vs the season's mean: El Niño {r['pct']['El Niño']:+.1f} %, neutral {r['pct']['neutral']:+.1f} %, "
              f"La Niña {r['pct']['La Niña']:+.1f} %; El Niño {r['mm_en']:.1f} mm vs neutral {r['mm_neutral']:.1f} mm")
        print(f"  permutation p (El Niño minus neutral, two-sided) {r['p']:.3f}; Spearman rho {r['rho']:+.2f} (p {r['rho_p']:.4f})")
        for t in CHECKS:
            c = result(season, t)
            print(f"  check ONI +-{t}: {c['n_wetter']} of {len(c['years'])} wetter, El Niño {c['pct']['El Niño']:+.1f} % "
                  f"vs neutral {c['pct']['neutral']:+.1f} %, p {c['p']:.3f}")


if __name__ == "__main__":
    main()
