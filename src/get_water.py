"""Download the inputs of the water-deficit story: CRU TS and ERA5 monthly means.

    data/water/era5_<var>_<y0>-<y1>.nc      ERA5 monthly means (Hersbach et al. 2020), 1940 to
                                             now, April to September, Europe 34-72 N, 25 W-45 E, 0.25 deg: rain
                                             and the inputs of FAO-56 Penman-Monteith (2 m
                                             temperature and dewpoint, 10 m wind speed, net solar
                                             and thermal radiation, surface pressure)
    data/water/era5_iran_<var>_<y0>-<y1>.nc  the same seven fields over Iran (24-41 N, 43-64 E),
                                             every month: the ERA5 check of the Iran story
    data/water/cru_ts4.10.<decade>.<pre|pet>.dat.nc
                                             CRU TS 4.10 (Harris et al. 2020) precipitation and
                                             Penman-Monteith potential evapotranspiration,
                                             1901-2025: the record of water.py

ERA5 comes from the Copernicus Climate Data Store and needs a key in ~/.cdsapirc; months not
yet published are skipped. CRU TS is a plain download from the University of East Anglia.

    python -I src/get_water.py
"""

from __future__ import annotations

import gzip
import shutil
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATER = ROOT / "data" / "water"
AREA = [72, -25, 34, 45]                                  # N, W, S, E
MONTHS = ["04", "05", "06", "07", "08", "09"]
ALL = [f"{m:02d}" for m in range(1, 13)]
IRAN = [41, 43, 24, 64]                                   # N, W, S, E
VARS = ["total_precipitation", "2m_temperature", "2m_dewpoint_temperature", "10m_wind_speed",
        "surface_net_solar_radiation", "surface_net_thermal_radiation", "surface_pressure"]
CRU = "https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.10/cruts.2604091129.v4.10"
DECADES = ["1901.1910", "1911.1920", "1921.1930", "1931.1940", "1941.1950", "1951.1960", "1961.1970",
           "1971.1980", "1981.1990", "1991.2000", "2001.2010", "2011.2020", "2021.2025"]


def era5(var: str, y0: int, y1: int, months=MONTHS, area=AREA, tag: str = "") -> Path:
    import cdsapi

    path = WATER / f"era5_{tag}{var}_{y0}-{y1}.nc"
    if path.exists():
        return path
    req = {"product_type": ["monthly_averaged_reanalysis"], "variable": [var],
           "year": [str(y) for y in range(y0, y1 + 1)], "month": list(months), "time": ["00:00"],
           "area": area, "data_format": "netcdf", "download_format": "unarchived"}
    part = path.with_suffix(".nc.part")
    cdsapi.Client(quiet=True).retrieve("reanalysis-era5-single-levels-monthly-means", req, str(part))
    part.rename(path)
    print("wrote", path.relative_to(ROOT), flush=True)
    return path


def this_year(var: str) -> Path | None:
    """The current year's published months (ERA5 monthly means appear a few days after the month)."""
    y = date.today().year
    months = [m for m in MONTHS if int(m) < date.today().month]
    for k in range(len(months), 0, -1):
        try:
            return era5(var, y, y, months[:k])
        except Exception as e:                            # the last month may not be out yet
            print(f"{var} {y} months {months[:k]}: {e}", flush=True)
    return None


def iran(var: str) -> list[Path]:
    """All months over Iran (the water year runs October to September), 1950 to the latest
    published month: the ERA5 check of the Iran story."""
    y = date.today().year
    out = [era5(var, 1950, y - 1, ALL, IRAN, "iran_")]
    months = [m for m in ALL if int(m) < date.today().month]
    for k in range(len(months), 0, -1):
        try:
            return out + [era5(var, y, y, months[:k], IRAN, "iran_")]
        except Exception as e:                            # the last month may not be out yet
            print(f"iran {var} {y} months {months[:k]}: {e}", flush=True)
    return out


def cru(decade: str, var: str) -> Path:
    path = WATER / f"cru_ts4.10.{decade}.{var}.dat.nc"
    if not path.exists():
        gz = path.with_suffix(".nc.gz")
        urllib.request.urlretrieve(f"{CRU}/{var}/{gz.name}", gz)
        with gzip.open(gz) as src, open(path, "wb") as dst:
            shutil.copyfileobj(src, dst)
        gz.unlink()
        print("wrote", path.relative_to(ROOT), flush=True)
    return path


def main() -> None:
    WATER.mkdir(parents=True, exist_ok=True)
    y1 = date.today().year - 1
    with ThreadPoolExecutor(8) as ex:
        jobs = [ex.submit(era5, v, a, b) for v in VARS for a, b in ((1940, 1949), (1950, y1))]
        jobs += [ex.submit(cru, d, v) for d in DECADES for v in ("pre", "pet")]
        [j.result() for j in jobs]
        list(ex.map(this_year, VARS))
        list(ex.map(iran, VARS))


if __name__ == "__main__":
    main()
