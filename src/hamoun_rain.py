"""WHY DID HAMOUN SHRINK? The rain against the lake: the winter precipitation (October to April) over the
highlands that feed the Hamoun lakes (the upper Helmand, Arghandab, Farah and Khash basins: the box 61.5-68.5 E,
31.5-35.0 N, an approximation of the catchment) against the lakes' late-spring open water (data/hamoun/reel/
timeline.json), the springs of 1366-1378 (1987-1999) against those of 1379-1404 (2000-2025).

Two precipitation datasets, so that the result does not hang on one:
- CRU TS 4.10 (University of East Anglia; stations interpolated, 0.5 deg; few stations in Afghanistan):
  data/water/cru_ts4.10.*.pre.dat.nc (src/get_water.py).
- ERA5 monthly means of total precipitation (ECMWF reanalysis, 0.25 deg): data/hamoun/reel2/era5_helmand.nc,
  fetched here from the Copernicus Climate Data Store when missing (needs ~/.cdsapirc).
Each spring's precipitation is the cos-latitude weighted box mean, summed over October of the year before to April.

Writes data/hamoun/reel2/rain.json: per dataset the two periods' means and the later as a share of the earlier; the
lake's two means and share; the wet winters (precipitation at or above the earlier period's median, per dataset): the
lake's mean in each period and the share; Spearman's rho between precipitation and the lake over all springs.

    python -I src/hamoun_rain.py
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "hamoun" / "reel2"
BOX = (61.5, 68.5, 31.5, 35.0)                      # W, E, S, N
ERA5 = OUT / "era5_helmand.nc"


def fetch_era5() -> None:
    import cdsapi
    cdsapi.Client(quiet=True).retrieve("reanalysis-era5-single-levels-monthly-means", {
        "product_type": ["monthly_averaged_reanalysis"], "variable": ["total_precipitation"],
        "year": [str(y) for y in range(1985, 2027)], "month": [f"{m:02d}" for m in range(1, 13)], "time": ["00:00"],
        "area": [BOX[3], BOX[0], BOX[2], BOX[1]], "data_format": "netcdf", "download_format": "unarchived"}, str(ERA5))


def monthly_cru() -> pd.Series:
    fs = sorted(f for f in glob.glob(str(ROOT / "data" / "water" / "cru_ts4.10.*.pre.dat.nc"))
                if int(Path(f).name.split(".")[2]) >= 1981)
    ds = xr.open_mfdataset(fs, engine="netcdf4", combine="by_coords").sel(
        lon=slice(BOX[0], BOX[1]), lat=slice(BOX[2], BOX[3])).load()
    return ds["pre"].weighted(np.cos(np.radians(ds.lat))).mean(("lat", "lon")).to_series()


def monthly_era5() -> pd.Series:
    if not ERA5.exists():
        fetch_era5()
    ds = xr.open_dataset(ERA5, engine="netcdf4")
    tp = ds["tp"].weighted(np.cos(np.radians(ds.latitude))).mean(("latitude", "longitude"))
    idx = pd.to_datetime(tp["valid_time"].values)
    return pd.Series(tp.values * 1000 * idx.days_in_month, index=idx)     # m a day (monthly mean) -> mm a month


def winters(p: pd.Series) -> dict:
    out = {}
    for y in range(1987, 2027):
        s = p[(p.index >= f"{y - 1}-10-01") & (p.index < f"{y}-05-01")]
        if len(s) == 7 and np.isfinite(s).all():
            out[y] = float(s.sum())
    return out


def main() -> None:
    bars = json.loads((ROOT / "data" / "hamoun" / "reel" / "timeline.json").read_text())["bars"]
    area = {b["year"]: b["km2"] for b in bars if b["km2"] is not None}
    res = dict(box=BOX, early=(1987, 1999), late=(2000, 2025), season="Oct-Apr")
    for name, p in (("cru", monthly_cru()), ("era5", monthly_era5())):
        w = winters(p)
        ys = [y for y in range(1987, 2026) if y in w and y in area]
        P = np.array([w[y] for y in ys])
        A = np.array([area[y] for y in ys])
        early = np.array([y <= 1999 for y in ys])
        med = float(np.median(P[early]))
        wet_e, wet_l = A[early & (P >= med)], A[~early & (P >= med)]
        res[name] = dict(n=len(ys), rain_early=float(P[early].mean()), rain_late=float(P[~early].mean()),
                         rain_share=float(P[~early].mean() / P[early].mean()),
                         wet_median=med, wet_n=(int(len(wet_e)), int(len(wet_l))),
                         wet_lake=(float(wet_e.mean()), float(wet_l.mean())),
                         wet_share=float(wet_l.mean() / wet_e.mean()), rho=float(spearmanr(P, A).statistic))
        res["lake_early"], res["lake_late"] = float(A[early].mean()), float(A[~early].mean())
        res["lake_share"] = res["lake_late"] / res["lake_early"]
        res["n_early"], res["n_late"] = int(early.sum()), int((~early).sum())
    # what the reel says, asserted
    assert res["n_early"] == 13 and res["n_late"] == 25, (res["n_early"], res["n_late"])
    assert 0.25 <= res["lake_share"] <= 0.27, res["lake_share"]                   # «۷۴٪ کمتر»
    assert 0.91 <= res["cru"]["rain_share"] <= 0.93 and 0.77 <= res["era5"]["rain_share"] <= 0.79
    assert 0.35 <= res["cru"]["wet_share"] <= 0.45 and 0.35 <= res["era5"]["wet_share"] <= 0.45   # «حدودِ ۴۰٪»
    (OUT / "rain.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
