"""THE LOST WATER OVER TEHRAN: the inputs of tehranwater.py and tehranwater3d.py, keyless public downloads, into
data/tehranwater/.

    tehran_osm.json        the city of Tehran's boundary, OpenStreetMap relation 6663864 («شهر تهران»), through
                           Nominatim's lookup (ODbL; one request, with this project's User-Agent)
    dem_<tile>.npy         Copernicus DEM GLO-30 (ESA; free licence), tiles N35E051 and N36E051, 1 arc-second, metres,
                           through Microsoft's Planetary Computer (anonymous token)
    texture.jpg            Sentinel-2 cloudless 2016 by EOX (s2maps.eu; CC BY 4.0; contains modified Copernicus
                           Sentinel data 2016), true colour, 51.00-51.85 E, 35.35-36.10 N, stitched from four WMS
                           requests (the service caps a side at 4096 px), about 10 m a pixel

    python -I src/get_tehranwater.py
"""

from __future__ import annotations

import io
import json
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.env import Env

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "tehranwater"
BBOX = (51.00, 35.35, 51.85, 36.10)                       # W, S, E, N of the scene
OSM = "https://nominatim.openstreetmap.org/lookup?osm_ids=R6663864&format=json&polygon_geojson=1"
DEM_TOKEN = "https://planetarycomputer.microsoft.com/api/sas/v1/token/cop-dem-glo-30"
DEM = "https://elevationeuwest.blob.core.windows.net/copernicus-dem/COP30_hh/Copernicus_DSM_COG_10_{}_DEM.tif"
TILES = ("N35_00_E051_00", "N36_00_E051_00")
WMS = ("https://tiles.maps.eox.at/wms?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1&LAYERS=s2cloudless&STYLES="
       "&SRS=EPSG:4326&BBOX={},{},{},{}&WIDTH=3800&HEIGHT=4000&FORMAT=image/jpeg")
UA = {"User-Agent": "daily-tmax-records/tehranwater (research reel)"}


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
        return r.read()


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    osm = DATA / "tehran_osm.json"
    if not osm.exists():
        osm.write_bytes(get(OSM))
    print("have", osm.name, flush=True)
    token = None
    for t in TILES:
        path = DATA / f"dem_{t}.npy"
        if path.exists():
            print("have", path.name, flush=True)
            continue
        token = token or json.loads(get(DEM_TOKEN))["token"]
        with Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"), rasterio.open("/vsicurl/" + DEM.format(t) + "?" + token) as s:
            np.save(path, s.read(1))
        print("fetched", path.name, flush=True)
    tex = DATA / "texture.jpg"
    if not tex.exists():
        w, s, e, n = BBOX
        mx, my = (w + e) / 2, (s + n) / 2
        quads = ((w, my, mx, n), (mx, my, e, n), (w, s, mx, my), (mx, s, e, my))   # NW, NE, SW, SE
        out = Image.new("RGB", (7600, 8000))
        for k, (a, b, c, d) in enumerate(quads):
            im = Image.open(io.BytesIO(get(WMS.format(a, b, c, d)))).convert("RGB")
            assert im.size == (3800, 4000), ("the WMS returned an error tile", im.size)
            out.paste(im, ((k % 2) * 3800, (k // 2) * 4000))
        out.save(tex, quality=92)
    print("have", tex.name, "; inputs in", DATA, flush=True)


if __name__ == "__main__":
    main()
