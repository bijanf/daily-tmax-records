"""ALPINE GLACIERS: how much thinner they are than in 1976, year by year.

Dussaillant et al. (2025), "Annual mass change of the world's glaciers from 1976 to 2024 by
temporal downscaling of satellite data with in situ observations", Earth System Science Data,
with its dataset of annual mass change for every glacier (WGMS Fluctuations of Glaciers
2025-01): data/glacier/CEU_gla_MEAN-CAL-mass-change-series_obs_unobs.csv (Central Europe,
RGI region 11) and its total error, copied from the dataset's individual-glacier time series.
Annual specific mass balance in metres of water equivalent, per glacier, observed or estimated
for unobserved glaciers from their neighbours and calibrated to geodetic elevation change.

The Alps are the region's glaciers north of 44 N, the Maritime Alps included (south of it lie the
Pyrenees, the Apennines and the Dinaric mountains); the regional
balance is the area-weighted mean (RGI 6.0 areas). Ice thickness: water equivalent divided by
the density used to turn elevation change into mass (850 kg/m3) or by that of pure ice (900);
both give more than 30 m since 1976.

    python -I src/glacier.py
"""

from __future__ import annotations

import functools
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "glacier"
SERIES = DATA / "CEU_gla_MEAN-CAL-mass-change-series_obs_unobs.csv"
ERROR = DATA / "CEU_gla_mean-cal-mass-change_TOTAL-ERROR_obs_unobs.csv"
ALPS = 44.0                                     # deg N: south of it, the Pyrenees, Apennines, Dinarides
FIRST, LAST = 1976, 2024                         # the paper's period


@functools.lru_cache(maxsize=2)
def table(path: Path = SERIES) -> pd.DataFrame:
    t = pd.read_csv(path)
    return t[t["CenLat"] >= ALPS]


@functools.lru_cache(maxsize=1)
def balance() -> pd.DataFrame:
    """Year -> area-weighted mean mass balance of the Alpine glaciers (m w.e.), its error (the
    glaciers' errors area-weighted, i.e. taken as fully correlated between glaciers), the
    cumulative balance since 1976 and its error with the years taken as independent: a lower
    bound; were a bias the same every year, the errors would add up (about 25 m w.e.)."""
    years = [str(y) for y in range(FIRST, LAST + 1)]
    t, e = table(SERIES), table(ERROR)
    assert (t["RGIId"].values == e["RGIId"].values).all(), "series and errors list the same glaciers"
    w = t["Area"] / t["Area"].sum()
    out = pd.DataFrame({"mb": t[years].mul(w, axis=0).sum(), "err": e[years].mul(w, axis=0).sum()})
    out.index = out.index.astype(int)
    out["cum"] = out["mb"].cumsum()
    out["cum_err"] = np.sqrt((out["err"] ** 2).cumsum())
    return out


def main() -> None:
    b = balance()
    t = table()
    print(f"{len(t)} glaciers, {t['Area'].sum():.0f} km2")
    print(f"1976-2024: {b['cum'].iloc[-1]:.1f} +- {b['cum_err'].iloc[-1]:.1f} m w.e.; "
          f"ice {-b['cum'].iloc[-1] / 0.85:.1f} m (850 kg/m3), {-b['cum'].iloc[-1] / 0.90:.1f} m (900)")
    last10 = b.loc[2015:2024, "mb"].sum()
    print(f"2015-2024: {last10:.1f} m w.e. = {100 * last10 / b['cum'].iloc[-1]:.0f} % of the loss since 1976")
    print("most negative years:", b["mb"].nsmallest(5).round(2).to_dict())
    print("years with a gain since 1990:", list(b.loc[1990:].index[b.loc[1990:, "mb"] > 0]))


if __name__ == "__main__":
    main()
