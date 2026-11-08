"""THE ALBORZ'S EARLY-NOVEMBER SNOW, EVERY YEAR SINCE 2000: the climatology the post-storm reel compares 2026 with.

MODIS Terra 8-day maximum snow extent (MOD10A2 v6.1, 500 m; NASA NSIDC DAAC, via Microsoft's Planetary Computer with
its anonymous token): a cell is snow (value 200) if MODIS saw snow on it on any clear day of the 8 days, cloud (50)
if it never saw it clear. Terra only, so that every year from 2000 is measured by the same instrument. The region:
get_alborzsnow.BOX (the central Alborz from Taleqan to Damavand, with Tehran's five dams), cells above 2,000 m
(Copernicus DEM, data/alborzsnow/dem.npy), on a 0.005-degree grid (about 500 m). The 8-day periods start on day 305
(1-8 November in a common year, 31 Oct-7 Nov in a leap year) and day 313 (9-16 November): the first two of November.

    data/alborzsnow/modis.csv     year, period start day, snow km2 and cloud km2 above 2,000 m, the item

    python -I src/get_alborzsnow_modis.py                # 2000 to the newest period available
"""

from __future__ import annotations

import datetime
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from affine import Affine
from rasterio.crs import CRS
from rasterio.env import Env
from rasterio.warp import Resampling, reproject

sys.path.insert(0, str(Path(__file__).resolve().parent))

import get_alborzsnow as A  # noqa: E402
import get_urmia as U  # noqa: E402

COLL = "modis-10A2-061"
STEP = 0.005
DAYS = (305, 313)


def signed(href: str) -> str:
    """The asset's URL signed by the Planetary Computer (its sign endpoint: the token of the asset's own container)."""
    import urllib.parse
    return "/vsicurl/" + U.get("https://planetarycomputer.microsoft.com/api/sas/v1/sign?href="
                               + urllib.parse.quote(href, safe=""))["href"]


def item(year: int, doy: int):
    day = datetime.date(year, 1, 1) + datetime.timedelta(doy - 1)
    d = U.get(U.STAC, {"collections": [COLL], "bbox": list(A.BOX), "limit": 10,
                       "datetime": f"{day.isoformat()}T00:00:00Z/{day.isoformat()}T23:59:59Z"})
    fs = [f for f in d.get("features", []) if f["id"].startswith(f"MOD10A2.A{year}{doy:03d}.")]
    return fs[0] if fs else None


def main() -> None:
    w, s, e, n = A.BOX
    t = Affine(STEP, 0, w, 0, -STEP, n)
    shape = (round((n - s) / STEP), round((e - w) / STEP))
    h = np.load(A.DATA / "dem.npy")
    hz = np.full(shape, np.nan, np.float32)
    reproject(source=h, destination=hz, src_transform=A.grid(A.DEM_STEP)[0], src_crs=A.WGS, dst_transform=t,
              dst_crs=A.WGS, resampling=Resampling.average)
    high = hz >= A.SNOW_MIN_M
    lat = n - (np.arange(shape[0]) + 0.5) * STEP
    cell = (STEP * 111320 * np.cos(np.radians(lat)))[:, None] * (STEP * 110574) / 1e6 * np.ones(shape)
    out = A.DATA / "modis.csv"
    old = pd.read_csv(out) if out.exists() else pd.DataFrame(columns=["year", "doy"])
    have = set(zip(old["year"], old["doy"]))
    rows = []
    for year in range(2000, datetime.date.today().year + 1):
        for doy in DAYS:
            if (year, doy) in have:
                continue
            f = item(year, doy)
            if f is None:
                print(f"{year} day {doy}: no item (yet)")
                continue
            mx = np.zeros(shape, np.uint8)
            with Env(**A.R.ENV), rasterio.open(signed(f["assets"]["Maximum_Snow_Extent"]["href"])) as src:
                reproject(source=rasterio.band(src, 1), destination=mx, dst_transform=t, dst_crs=A.WGS,
                          resampling=Resampling.nearest)
            snow, cloud = (mx == 200) & high, (mx == 50) & high
            rows.append(dict(year=year, doy=doy, snow_km2=round(float(cell[snow].sum()), 1),
                             cloud_km2=round(float(cell[cloud].sum()), 1), high_km2=round(float(cell[high].sum()), 1),
                             item=f["id"]))
            print(rows[-1], flush=True)
    df = pd.concat([old, pd.DataFrame(rows)], ignore_index=True).sort_values(["doy", "year"])
    df.to_csv(out, index=False)
    print("saved", out, len(df), "rows")


if __name__ == "__main__":
    main()
