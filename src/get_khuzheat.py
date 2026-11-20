"""Fetch and cache the inputs of the Khuzestan heat film (khuzheat_fa): the hourly reports of the Abadan and Ahvaz
stations, an independent reanalysis series at the same two points, and the satellite pictures of the two cities.

    data/khuzheat/isd/<station>_<year>.csv   NOAA ISD "global-hourly" (keyless, the noaa-global-hourly-pds bucket): every
                                             report of the station, with the maximum- and minimum-thermometer readings in
                                             the KA fields. ISD ends on 24 August 2025.
    data/khuzheat/era5/era5land_<name>.zip   ERA5-Land hourly 2 m temperature at the station's point, 1950 to now, from
                                             the Copernicus time-series service (needs the key in ~/.cdsapirc).
    data/khuzheat/scene_<name>.npz           each city as a 9:16 frame: the red, green and blue bands' reflectance on
                                             the clearest Sentinel-2 day of summer 2025 (Copernicus Sentinel data, read
                                             from the Planetary Computer, keyless), with scene_<name>.json naming the day.

    python -I src/get_khuzheat.py --isd        # about 110 files, 260 MB
    python -I src/get_khuzheat.py --era5       # two requests, a minute each
    python -I src/get_khuzheat.py --maps
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import get_khazar  # noqa: E402  (the 9:16 Web Mercator frame, the retrying fetch)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "khuzheat"
AGENT = {"User-Agent": "research-script/1.0"}
ISD = "https://noaa-global-hourly-pds.s3.amazonaws.com/{year}/{station}.csv"
ISD_LAST = 2025                                   # the archive's last year (it stops on 24 August 2025)
# name: the station's ISD id, the first year of its record, its point (lat, lon)
STATIONS = dict(abadan=dict(isd="40831099999", first=1943, lat=30.371, lon=48.228),
                ahvaz=dict(isd="40811099999", first=1973, lat=31.337, lon=48.762))
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-2-l2a"
SCENE_WINDOW = ("2025-06-10", "2025-08-31")       # the picture's day is looked for in this window
SCENE_PX = (1620, 2880)
# the pictures: each city as one 9:16 frame (W, S, E, N)
FRAMES = dict(abadan=get_khazar.frame(48.18, 48.38, 30.20), ahvaz=get_khazar.frame(48.57, 48.79, 31.17))


def _one(job) -> str:
    station, year = job
    path = DATA / "isd" / f"{station}_{year}.csv"
    if path.exists() and path.stat().st_size > 0:
        return ""
    try:
        req = urllib.request.Request(ISD.format(year=year, station=station), headers=AGENT)
        with urllib.request.urlopen(req, timeout=600) as r:
            body = r.read()
    except Exception as e:                        # a year the archive does not hold (the war years, some early ones)
        return f"{station} {year}: {type(e).__name__}"
    assert body[:9] == b'"STATION"', (station, year, body[:40])      # a CSV, not an error page
    path.write_bytes(body)
    return ""


def isd() -> None:
    (DATA / "isd").mkdir(parents=True, exist_ok=True)
    jobs = [(s["isd"], y) for s in STATIONS.values() for y in range(s["first"], ISD_LAST + 1)]
    with ThreadPoolExecutor(6) as ex:
        miss = [m for m in ex.map(_one, jobs) if m]
    print(f"{len(jobs) - len(miss)} files; not in the archive: {len(miss)}")


def era5land() -> None:
    import cdsapi
    (DATA / "era5").mkdir(parents=True, exist_ok=True)
    c = cdsapi.Client(quiet=True)
    for name, s in STATIONS.items():
        path = DATA / "era5" / f"era5land_{name}.zip"
        if not path.exists():
            c.retrieve("reanalysis-era5-land-timeseries",
                       {"variable": ["2m_temperature"], "location": {"longitude": s["lon"], "latitude": s["lat"]},
                        "date": ["1950-01-01/2026-10-31"], "data_format": "csv"}, str(path))
            print("saved", path.name)


def _call(url: str, body: dict | None = None):
    import json
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                 headers=dict(AGENT, **{"Content-Type": "application/json"}))
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def scenes() -> None:
    """Each city's frame from the clearest Sentinel-2 day of SCENE_WINDOW that covers the whole frame: the reflectance
    of the red, green and blue bands (10 m, warped to the Web Mercator frame) as whole ten-thousandths. The tiles' own
    ready picture is not used: it is white wherever the desert reflects more than about a third of the light."""
    import json
    import numpy as np
    import rasterio
    from rasterio.crs import CRS
    from rasterio.env import Env
    from rasterio.transform import from_bounds
    from rasterio.warp import Resampling, reproject, transform_bounds
    from rasterio.windows import Window, from_bounds as window_of
    from shapely.geometry import box as sbox, shape
    from shapely.ops import unary_union
    env = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF",
               GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2")
    mx, my = get_khazar.mx, get_khazar.my
    token = _call(SAS)["token"]
    for name, (w, s, e, n) in FRAMES.items():
        path = DATA / f"scene_{name}.npz"
        if path.exists():
            continue
        d = _call(STAC, {"collections": ["sentinel-2-l2a"], "bbox": [w, s, e, n], "limit": 300,
                         "datetime": f"{SCENE_WINDOW[0]}T00:00:00Z/{SCENE_WINDOW[1]}T23:59:59Z"})
        by = {}
        for f in d["features"]:
            by.setdefault(f["properties"]["datetime"][:10], []).append(f)
        whole = [(float(np.mean([f["properties"].get("eo:cloud_cover") or 0 for f in fs])), day, fs) for day, fs in by.items()
                 if unary_union([shape(f["geometry"]) for f in fs]).intersection(sbox(w, s, e, n)).area / sbox(w, s, e, n).area > 0.999]
        cloud, day, fs = min(whole, key=lambda x: (x[0], x[1]))
        b = (mx(w), my(s), mx(e), my(n))
        dst_t, dst_crs = from_bounds(*b, *SCENE_PX), CRS.from_epsg(3857)
        out = np.zeros((3, SCENE_PX[1], SCENE_PX[0]), np.float32)
        filled = np.zeros(out.shape[1:], bool)
        for f in fs:
            base = float(f["properties"].get("s2:processing_baseline") or 0)
            assert base >= 4.0, (f["id"], base)                 # from baseline 04.00 the numbers carry an offset of 1000
            one = np.zeros_like(out)
            for k, band in enumerate(("B04", "B03", "B02")):
                with Env(**env), rasterio.open(f["assets"][band]["href"] + "?" + token) as src:
                    bb = transform_bounds(dst_crs, src.crs, *b, densify_pts=21)
                    win = window_of(*bb, transform=src.transform).round_offsets(op="floor").round_lengths(op="ceil")
                    win = win.intersection(Window(0, 0, src.width, src.height))
                    if win.width < 1 or win.height < 1:
                        break
                    reproject(source=src.read(1, window=win).astype(np.float32), destination=one[k], src_transform=src.window_transform(win),
                              src_crs=src.crs, dst_transform=dst_t, dst_crs=dst_crs, resampling=Resampling.bilinear, src_nodata=0, dst_nodata=0)
            m = (one.min(0) > 0) & ~filled
            out[:, m] = one[:, m]
            filled |= m
        assert filled.mean() > 0.999, (name, day, float(filled.mean()))
        refl = np.clip(out - 1000.0, 0, 10000).astype(np.uint16)          # reflectance in ten-thousandths
        np.savez_compressed(path, rgb=np.moveaxis(refl, 0, -1))
        (DATA / f"scene_{name}.json").write_text(json.dumps(dict(day=day, cloud=round(cloud, 2), tiles=[f["id"] for f in fs])))
        print("saved", path.name, day, f"cloud {cloud:.2f} %")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--isd", action="store_true")
    ap.add_argument("--era5", action="store_true")
    ap.add_argument("--maps", action="store_true")
    a = ap.parse_args()
    if a.isd:
        isd()
    if a.era5:
        era5land()
    if a.maps:
        scenes()
    if not (a.isd or a.era5 or a.maps):
        print(__doc__)


if __name__ == "__main__":
    main()
