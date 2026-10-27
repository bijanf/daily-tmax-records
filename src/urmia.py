"""LAKE URMIA FROM SPACE: the September water area of every year since 1986, in % of 1995.

Measured data only, from get_urmia.py (Landsat Collection 2 Level-2, USGS, via Microsoft's
Planetary Computer; MNDWI water inside JRC Global Surface Water's lake extent; one fixed path-169
footprint; median of up to four September-window scenes a year). 1995 is the record's largest
September lake (5,382 km2), 2025 its smallest (2,698 km2, half of 1995), 2026 the latest (3,268
km2). Checks: the MNDWI threshold at -0.1 and +0.1, and the sensor offset (Landsat 7 reads about
5 % above Landsat 8/9 in common years). The pictures (both Landsat paths 168 and 169) show the
water of September 1995 and 2025 over the lake's extent.

    python -I src/urmia.py > outputs/urmia_log.txt
"""

from __future__ import annotations

import functools
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "urmia"
TOP, LOW, NOW = 1995, 2025, 2026


@functools.cache
def series() -> pd.DataFrame:
    a = pd.read_csv(DATA / "area_september.csv", index_col="year")
    a["pct"] = 100 * a["area_km2"] / a.loc[TOP, "area_km2"]
    return a


def picture(year: int) -> dict:
    z = np.load(DATA / f"picture_{year}.npz")
    return dict(water=z["water"], seen=z["seen"], lake=z["lake"], items=list(z["items"]))


def main() -> None:
    a = series()
    print(f"Landsat September water area, {a.index[0]}-{a.index[-1]} ({len(a)} years; no scene in "
          f"{sorted(set(range(a.index[0], a.index[-1] + 1)) - set(a.index))})")
    print(f"largest {a.area_km2.idxmax()} ({a.area_km2.max():.0f} km2), smallest {a.area_km2.idxmin()} "
          f"({a.area_km2.min():.0f} km2)")
    for y in (TOP, LOW, NOW):
        r = a.loc[y]
        print(f"  {y}: {r.area_km2:.0f} km2 ({r.pct:.0f} % of {TOP}); thresholds -0.1/+0.1: {r.thr_minus:.0f}/"
              f"{r.thr_plus:.0f} km2 ({100 * r.thr_minus / a.loc[TOP, 'thr_minus']:.0f}/"
              f"{100 * r.thr_plus / a.loc[TOP, 'thr_plus']:.0f} %); {int(r.n_scenes)} scenes {r.platforms}")
    k = np.cos(np.deg2rad(37.7)) * (111.32 * 0.0015) ** 2
    for y in (TOP, LOW):
        p = picture(y)
        print(f"picture {y}: {len(p['items'])} scenes, water {p['water'].sum() * k:.0f} km2 on the grid, lake extent "
              f"unseen {100 * (p['lake'] & ~p['seen']).sum() / p['lake'].sum():.1f} %")


if __name__ == "__main__":
    main()
