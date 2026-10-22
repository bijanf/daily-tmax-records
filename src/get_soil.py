"""Download the inputs of the soil-drought story: ERA5-Land soil water and global temperature.

    data/soil/era5land_swvl<k>_<y0>-<y1>.nc   ERA5-Land monthly means (Muñoz-Sabater et al.
                                               2021), volumetric soil water of layer k
                                               (1: 0-7 cm, 2: 7-28 cm, 3: 28-100 cm), April to
                                               September, Europe 34-72 N, 25 W-45 E, 0.1 deg
    data/soil/hadcrut5_global_monthly.csv      HadCRUT5 analysis, global mean (Morice et al. 2021)
    data/soil/cpc_soilw_mon_v2.nc              NOAA CPC soil moisture v2, monthly, 0.5 deg, global
                                               (the check in soil.py)

ERA5-Land comes from the Copernicus Climate Data Store and needs a key in ~/.cdsapirc; months
not yet published are skipped. HadCRUT5 and CPC are plain downloads (Met Office, NOAA PSL).

    python -I src/get_soil.py
"""

from __future__ import annotations

import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOIL = ROOT / "data" / "soil"
AREA = [72, -25, 34, 45]                                  # N, W, S, E
MONTHS = ["04", "05", "06", "07", "08", "09"]
CHUNKS = [(1950, 1969), (1970, 1989), (1990, 2009), (2010, 2025)]
HADCRUT = ("https://www.metoffice.gov.uk/hadobs/hadcrut5/data/HadCRUT.5.1.0.0/analysis/diagnostics/"
           "HadCRUT.5.1.0.0.analysis.summary_series.global.monthly.csv")
CPC = "https://downloads.psl.noaa.gov/Datasets/cpcsoil/soilw.mon.mean.v2.nc"


def era5land(layer: int, y0: int, y1: int, months=MONTHS) -> Path:
    import cdsapi

    path = SOIL / f"era5land_swvl{layer}_{y0}-{y1}.nc"
    if path.exists():
        return path
    req = {"product_type": ["monthly_averaged_reanalysis"],
           "variable": [f"volumetric_soil_water_layer_{layer}"],
           "year": [str(y) for y in range(y0, y1 + 1)], "month": list(months), "time": ["00:00"],
           "area": AREA, "data_format": "netcdf", "download_format": "unarchived"}
    part = path.with_suffix(".nc.part")
    cdsapi.Client(quiet=True).retrieve("reanalysis-era5-land-monthly-means", req, str(part))
    part.rename(path)
    print("wrote", path.relative_to(ROOT), flush=True)
    return path


def this_year(layer: int) -> Path | None:
    """The current year's published months (ERA5-Land monthly means lag about two months)."""
    y = date.today().year
    months = [m for m in MONTHS if int(m) < date.today().month]
    for k in range(len(months), 0, -1):
        try:
            return era5land(layer, y, y, months[:k])
        except Exception as e:                            # the last month may not be out yet
            print(f"swvl{layer} {y} months {months[:k]}: {e}", flush=True)
    return None


def main() -> None:
    SOIL.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(HADCRUT, SOIL / "hadcrut5_global_monthly.csv")
    urllib.request.urlretrieve(CPC, SOIL / "cpc_soilw_mon_v2.nc")
    jobs = [(k, y0, y1) for k in (1, 2, 3) for y0, y1 in CHUNKS]
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda j: era5land(*j), jobs))
        list(ex.map(this_year, (1, 2, 3)))


if __name__ == "__main__":
    main()
