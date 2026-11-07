"""WHERE DID THE HAMOUN GO, the 3D inputs: the ground under the Hamoun pictures, a keyless public download into
data/hamoun/reel/.

    dem_pic.npy    Copernicus DEM GLO-30 (ESA; free licence), tiles N30-N31 x E060-E062, 1 arc-second, metres,
                   through Microsoft's Planetary Computer (anonymous token), averaged onto hamoun.py's picture grid
                   (get_hamoun.PIC_T: 60.69-62.31 E, 30.2504-31.85 N, 1080 x 1240 pixels of about 143 m), so the
                   mesh and every year's picture share one grid
    wide.jpg       Sentinel-2 cloudless 2016 by EOX (s2maps.eu; CC BY 4.0; contains modified Copernicus Sentinel data
                   2016), true colour, 58.70-64.30 E, 28.65-33.45 N (WIDE), one WMS request of 3800 x 3257 pixels
                   (about 150 m a pixel): the ground around the Landsat pictures (outside the lakes' box only), so the
                   3D view has real desert to its horizon instead of a flat colour

    python -I src/get_hamoun3d.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from rasterio.env import Env
from rasterio.warp import Resampling, reproject

sys.path.insert(0, str(Path(__file__).resolve().parent))
import get_hamoun as gh  # noqa: E402  (the picture grid only)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "hamoun" / "reel"
DEM_TOKEN = "https://planetarycomputer.microsoft.com/api/sas/v1/token/cop-dem-glo-30"
DEM = "https://elevationeuwest.blob.core.windows.net/copernicus-dem/COP30_hh/Copernicus_DSM_COG_10_{}_DEM.tif"
TILES = [f"N{la}_00_E0{lo}_00" for la in (30, 31) for lo in (60, 61, 62)]
UA = {"User-Agent": "daily-tmax-records/hamoun (research reel)"}
WIDE = (58.70, 28.65, 64.30, 33.45)                  # W, S, E, N of the surroundings
WMS = ("https://tiles.maps.eox.at/wms?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1&LAYERS=s2cloudless&STYLES="
       "&SRS=EPSG:4326&BBOX={},{},{},{}&WIDTH=3800&HEIGHT=3257&FORMAT=image/jpeg")


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
        return r.read()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    wide = OUT / "wide.jpg"
    if not wide.exists():
        import io
        from PIL import Image
        im = Image.open(io.BytesIO(get(WMS.format(*WIDE)))).convert("RGB")
        assert im.size == (3800, 3257), ("the WMS returned an error tile", im.size)
        im.save(wide, quality=92)
    print("have", wide.name)
    path = OUT / "dem_pic.npy"
    if path.exists():
        print("have", path.name)
        return
    token = json.loads(get(DEM_TOKEN))["token"]
    dst = np.zeros(gh.PIC_SHAPE, np.float64)
    cnt = np.zeros(gh.PIC_SHAPE, np.float64)
    with Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        for t in TILES:
            with rasterio.open("/vsicurl/" + DEM.format(t) + "?" + token) as s:
                a = s.read(1).astype(np.float32)
                part = np.full(gh.PIC_SHAPE, np.nan, np.float32)
                reproject(source=a, destination=part, src_transform=s.transform, src_crs=s.crs,
                          dst_transform=gh.PIC_T, dst_crs=gh.WGS, resampling=Resampling.average,
                          src_nodata=s.nodata, dst_nodata=np.nan)
                ok = np.isfinite(part)
                dst[ok] += part[ok]
                cnt[ok] += 1
                print(f"tile {t}: {a.shape}, {ok.mean() * 100:.1f} % of the picture grid, "
                      f"{np.nanmin(a):.0f}-{np.nanmax(a):.0f} m", flush=True)
    assert (cnt > 0).all(), ("pixels without a DEM value", int((cnt == 0).sum()))
    dem = (dst / cnt).astype(np.float32)
    np.save(path, dem)
    print(f"saved {path.name}: {dem.shape}, {dem.min():.0f}-{dem.max():.0f} m")


if __name__ == "__main__":
    main()
