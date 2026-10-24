"""Download the inputs of the snow-to-rain story: ERA5 monthly means over the highlands from
Turkey to the edge of Tibet.

    data/snow/era5_<var>_<y0>-<y1>.nc   ERA5 monthly means (Hersbach et al. 2020), every month
                                        from 1940 to the latest published one, 25-43 N, 26-80 E,
                                        0.25 deg: snowfall, total precipitation, 2 m temperature
    data/snow/era5_invariant.nc         land-sea mask and surface geopotential (terrain height)

ERA5 comes from the Copernicus Climate Data Store and needs a key in ~/.cdsapirc; months not
yet published are skipped.

    python -I src/get_snow.py
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNOW = ROOT / "data" / "snow"
AREA = [43, 26, 25, 80]                                   # N, W, S, E: to western Tibet (Ladakh, Aksai Chin)
ALL = [f"{m:02d}" for m in range(1, 13)]
VARS = ["snowfall", "total_precipitation", "2m_temperature"]
CHUNKS = ((1940, 1959), (1960, 1979), (1980, 1999), (2000, 2025))
DATASET = "reanalysis-era5-single-levels-monthly-means"


def retrieve(req: dict, path: Path) -> Path:
    import cdsapi

    if path.exists():
        return path
    req = {"product_type": ["monthly_averaged_reanalysis"], "time": ["00:00"], "area": AREA,
           "data_format": "netcdf", "download_format": "unarchived", **req}
    part = path.with_suffix(".nc.part")
    cdsapi.Client(quiet=True).retrieve(DATASET, req, str(part))
    part.rename(path)
    print("wrote", path.relative_to(ROOT), flush=True)
    return path


def era5(var: str, y0: int, y1: int, months=ALL) -> Path:
    return retrieve({"variable": [var], "year": [str(y) for y in range(y0, y1 + 1)], "month": list(months)},
                    SNOW / f"era5_{var}_{y0}-{y1}.nc")


def this_year(var: str) -> Path | None:
    """The current year's published months (ERA5 monthly means appear a few days after the month),
    fetched afresh on every run so that newly published months come in."""
    y = date.today().year
    (SNOW / f"era5_{var}_{y}-{y}.nc").unlink(missing_ok=True)
    months = [m for m in ALL if int(m) < date.today().month]
    for k in range(len(months), 0, -1):
        try:
            return era5(var, y, y, months[:k])
        except Exception as e:                            # the last month may not be out yet
            print(f"{var} {y} months {months[:k]}: {e}", flush=True)
    return None


def invariant() -> Path:
    return retrieve({"variable": ["land_sea_mask", "geopotential"], "year": ["2000"], "month": ["01"]},
                    SNOW / "era5_invariant.nc")


def main() -> None:
    SNOW.mkdir(parents=True, exist_ok=True)
    assert CHUNKS[-1][1] == date.today().year - 1, "add the finished year to CHUNKS"
    with ThreadPoolExecutor(8) as ex:
        jobs = [ex.submit(era5, v, a, b) for v in VARS for a, b in CHUNKS] + [ex.submit(invariant)]
        [j.result() for j in jobs]
        list(ex.map(this_year, VARS))


if __name__ == "__main__":
    main()
