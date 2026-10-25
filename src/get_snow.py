"""Download the inputs of the snow-to-rain story: ERA5 monthly means over the highlands from
Turkey to the edge of Tibet.

    data/snow/era5_<var>_<y0>-<y1>.nc   ERA5 monthly means (Hersbach et al. 2020), every month
                                        from 1940 to the latest published one, 25-43 N, 26-80 E,
                                        0.25 deg: snowfall, total precipitation, 2 m temperature
    data/snow/era5_invariant.nc         land-sea mask and surface geopotential (terrain height)
    data/snow_alps/...                  the same over the Alps, 43.3-48.6 N, 4.5-17 E (--region alps)
    data/snow_alps_land/...             ERA5-Land over the Alps, 0.1 deg, from 1950, with the snowpack
                                        (snow water equivalent) (--region alps_land)

ERA5 comes from the Copernicus Climate Data Store and needs a key in ~/.cdsapirc; months not
yet published are skipped.

    python -I src/get_snow.py
    python -I src/get_snow.py --region alps
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import numpy as np
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# N, W, S, E and the folder: Turkey to western Tibet (Ladakh, Aksai Chin), and the Alps
REGIONS = {"asia": ([43, 26, 25, 80], ROOT / "data" / "snow"),
           "alps": ([48.6, 4.5, 43.3, 17.0], ROOT / "data" / "snow_alps"),
           "alps_land": ([48.6, 4.5, 43.3, 17.0], ROOT / "data" / "snow_alps_land")}
# ERA5-Land (0.1 deg, from 1950; a land model on ERA5's weather, with the snowpack): its own
# dataset, variables and first year
LAND = dict(dataset="reanalysis-era5-land-monthly-means", first=1950,
            vars=["snowfall", "total_precipitation", "2m_temperature", "snow_depth_water_equivalent"])
AREA, SNOW = REGIONS["asia"]
ALL = [f"{m:02d}" for m in range(1, 13)]
VARS = ["snowfall", "total_precipitation", "2m_temperature"]
CHUNKS = ((1940, 1959), (1960, 1979), (1980, 1999), (2000, 2025))
DATASET = "reanalysis-era5-single-levels-monthly-means"


def retrieve(req: dict, path: Path, fresh: bool = False) -> Path:
    """Download once (fresh: again, replacing the file only once the new one is complete)."""
    import cdsapi

    if path.exists() and not fresh:
        return path
    req = {"product_type": ["monthly_averaged_reanalysis"], "time": ["00:00"], "area": AREA,
           "data_format": "netcdf", "download_format": "unarchived", **req}
    part = path.with_suffix(".nc.part")
    cdsapi.Client(quiet=True).retrieve(DATASET, req, str(part))
    part.rename(path)
    print("wrote", path.relative_to(ROOT), flush=True)
    return path


def era5(var: str, y0: int, y1: int, months=ALL, fresh: bool = False) -> Path:
    return retrieve({"variable": [var], "year": [str(y) for y in range(y0, y1 + 1)], "month": list(months)},
                    SNOW / f"era5_{var}_{y0}-{y1}.nc", fresh)


def this_year(var: str) -> Path | None:
    """The current year's published months (ERA5 monthly means appear a few days after the month),
    fetched afresh on every run so that newly published months come in; the old file stays until
    a new one is complete."""
    y = date.today().year
    months = [m for m in ALL if int(m) < date.today().month]
    for k in range(len(months), 0, -1):
        try:
            return era5(var, y, y, months[:k], fresh=True)
        except Exception as e:                            # the last month may not be out yet
            print(f"{var} {y} months {months[:k]}: {e}", flush=True)
    return None


def invariant() -> Path:
    path = retrieve({"variable": ["land_sea_mask", "geopotential"], "year": ["2000"], "month": ["01"]},
                    SNOW / "era5_invariant.nc")
    return unzipped(path)


def unzipped(path: Path) -> Path:
    """CDS sometimes answers with a zip of one netCDF per variable (ERA5-Land's invariants) even
    when asked for an unarchived file: merge them into one netCDF in its place."""
    import tempfile
    import zipfile

    import xarray as xr

    if not zipfile.is_zipfile(path):
        return path
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(path) as z:
        z.extractall(tmp)
        parts = []
        for f in sorted(Path(tmp).glob("*.nc")):                  # each its own time stamp: drop it
            d = xr.open_dataset(f)
            for dim in ("time", "valid_time"):
                if dim in d.dims:
                    d = d.isel({dim: 0}, drop=True)
            parts.append(d.load())
        merged = xr.merge(parts, join="exact").expand_dims(valid_time=[np.datetime64("2000-01-01", "ns")])
    assert all(int(merged[v].isnull().sum()) == 0 for v in merged.data_vars), "an empty invariant"
    merged.to_netcdf(path.with_suffix(".nc.part"))
    path.with_suffix(".nc.part").rename(path)
    print("merged", path.name, flush=True)
    return path


def main() -> None:
    import argparse

    global AREA, SNOW
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="asia", choices=list(REGIONS))
    region = ap.parse_args().region
    AREA, SNOW = REGIONS[region]
    SNOW.mkdir(parents=True, exist_ok=True)
    if region.endswith("_land"):
        global DATASET, VARS, CHUNKS
        DATASET, VARS = LAND["dataset"], LAND["vars"]
        CHUNKS = ((LAND["first"], 1969), (1970, 1989), (1990, 2009), (2010, 2025))
    assert CHUNKS[-1][1] == date.today().year - 1, "add the finished year to CHUNKS"
    with ThreadPoolExecutor(8) as ex:
        jobs = [ex.submit(era5, v, a, b) for v in VARS for a, b in CHUNKS] + [ex.submit(invariant)]
        [j.result() for j in jobs]
        list(ex.map(this_year, VARS))


if __name__ == "__main__":
    main()
