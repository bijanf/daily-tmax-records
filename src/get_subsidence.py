"""SINKING GROUND: the inputs of subsidence.py and subsidence3d.py, keyless public downloads, into data/subsidence/.

    rate_A.tif            vertical land-subsidence rate 2014-2020, cm/yr (positive = down), 100 m, Sentinel-1
                          descending InSAR projected to vertical: Haghshenas Haghighi & Motagh 2024, Science Advances
                          10, eadk3039; Zenodo 10.5281/zenodo.10815578 (CC BY 4.0)
    payne/<region>_vU.geo.tif   the independent product: vertical velocity Oct 2014 - Dec 2022, mm/yr (negative =
                          down), ascending + descending decomposition: Payne et al. 2025, JGR Solid Earth 130,
                          e2024JB030367; Zenodo 10.5281/zenodo.13754200 (CC BY 4.0), three regions of vU.zip
    geob_adm2.geojson     Iran's counties (geoBoundaries IRN ADM2, OSM/Wambacher 2017, ODbL): the SW Tehran plain
    osm_karaj.json        the city of Karaj (OpenStreetMap via Nominatim, ODbL)
    ne_admin0/            Natural Earth 1:10m countries (public domain): Iran's outline on the map
    dem_iran.npy          Copernicus DEM GLO-90 (ESA; free licence), 40-67 E, 22-44 N, read at 0.02 deg from each
                          tile's overview (Planetary Computer, anonymous token); sea and missing tiles = 0
    dem_<tile>.npy        Copernicus DEM GLO-30 tiles N35E050, N36E050, N35E051, N36E051 (the Tehran-Karaj plain)
    tex_iran.jpg          Sentinel-2 cloudless 2016 by EOX (s2maps.eu; CC BY 4.0; contains modified Copernicus
                          Sentinel data 2016), 40-67 E, 22-44 N, four WMS requests (a side is capped at 4096 px)
    tex_karaj.jpg         the same, 50.20-51.90 E, 35.00-36.60 N, about 20 m a pixel

Files already fetched by the feasibility check (~/Documents/instagram_research/feasibility/feas_subsidence/dl) are
cloned when their MD5 matches; everything else is downloaded.

    python -I src/get_subsidence.py
"""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.env import Env

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "subsidence"
FEAS = Path.home() / "Documents" / "instagram_research" / "feasibility" / "feas_subsidence" / "dl"
RATE_A = ("https://zenodo.org/records/10815578/files/Iran_subsidence_rate_2014-2020_Sentinel-1_InSAR_desc_v1.0.0.tif"
          "?download=1", "c0a19300c161940dc2e6a8de267cef4f")
VU_ZIP = ("https://zenodo.org/records/13754200/files/vU.zip?download=1", "63fafbd6c4c671c629b46f9c34956415")
PAYNE = ("Qazvin_Western_Tehran_Plain_Zarand_Saveh_vU.geo.tif", "Rafsanjan_Bardsir_vU.geo.tif",
         "Qouchan_-_Shirvan_Esfarayen_Javin_Sabzevar_1_Sabzevar_2_Mashhad_Neyshabour_vU.geo.tif")
ADM2 = "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IRN/ADM2/geoBoundaries-IRN-ADM2.geojson"
OSM_KARAJ = "https://nominatim.openstreetmap.org/search?q=Karaj&countrycodes=ir&format=json&polygon_geojson=1&limit=1"
NE = ROOT / "data" / "grace" / "ne_10m_admin_0_countries"
NE_ZIP = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip"
TOKEN = "https://planetarycomputer.microsoft.com/api/sas/v1/token/cop-dem-glo-{}"
GLO = "https://elevationeuwest.blob.core.windows.net/copernicus-dem/COP{}_hh/Copernicus_DSM_COG_{}_{}_DEM.tif"
IRAN_BOX, IRAN_STEP = (40.0, 22.0, 67.0, 44.0), 0.02          # W, S, E, N (deg); the national mesh's spacing
KARAJ_BOX = (50.20, 35.00, 51.90, 36.60)
LOCAL_TILES = ("N35_00_E050_00", "N36_00_E050_00", "N35_00_E051_00", "N36_00_E051_00")
WMS = ("https://tiles.maps.eox.at/wms?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1&LAYERS=s2cloudless&STYLES="
       "&SRS=EPSG:4326&BBOX={},{},{},{}&WIDTH={}&HEIGHT={}&FORMAT=image/jpeg")
UA = {"User-Agent": "daily-tmax-records/subsidence (research reel)"}


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600) as r:
        return r.read()


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def clone(src: Path, dst: Path) -> bool:
    """A copy-on-write clone of a file the feasibility check fetched (macOS cp -c), else a plain copy."""
    if not src.exists():
        return False
    if subprocess.run(["/bin/cp", "-c", str(src), str(dst)], capture_output=True).returncode != 0:
        shutil.copyfile(src, dst)
    return True


def rate_a() -> None:
    dst = DATA / "rate_A.tif"
    if not dst.exists() and not clone(FEAS / "zenodo" / "Iran_subsidence_rate_2014-2020_Sentinel-1_InSAR_desc_v1.0.0.tif", dst):
        dst.write_bytes(get(RATE_A[0]))
    assert md5(dst) == RATE_A[1], "rate_A.tif: not the Zenodo v1.0.0 file"
    print("have", dst.name, flush=True)


def payne() -> None:
    out = DATA / "payne"
    out.mkdir(exist_ok=True)
    if all((out / f).exists() for f in PAYNE):
        print("have payne/", flush=True)
        return
    z = FEAS / "payne" / "vU.zip"
    if not z.exists():
        z = DATA / "vU.zip"
        z.write_bytes(get(VU_ZIP[0]))
    assert md5(z) == VU_ZIP[1], "vU.zip: not the Zenodo file"
    with zipfile.ZipFile(z) as zf:
        for name in zf.namelist():
            if Path(name).name in PAYNE:
                (out / Path(name).name).write_bytes(zf.read(name))
    assert all((out / f).exists() for f in PAYNE), "a Payne region is missing from vU.zip"
    print("have payne/", flush=True)


def boundaries() -> None:
    adm2 = DATA / "geob_adm2.geojson"
    if not adm2.exists() and not clone(FEAS / "geob" / "geoBoundaries-IRN-ADM2.geojson", adm2):
        adm2.write_bytes(get(ADM2))
    karaj = DATA / "osm_karaj.json"
    if not karaj.exists() and not clone(FEAS / "osm" / "nom_Karaj.json", karaj):
        karaj.write_bytes(get(OSM_KARAJ))
    k = json.loads(karaj.read_text())[0]
    assert k["geojson"]["type"] in ("Polygon", "MultiPolygon"), "Karaj: a boundary, not a point"
    if not (NE / "ne_10m_admin_0_countries.shp").exists():
        NE.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(get(NE_ZIP))) as zf:
            zf.extractall(NE)
    print("have geob_adm2.geojson, osm_karaj.json (", k["display_name"][:40], "), Natural Earth", flush=True)


def dem_iran() -> None:
    path = DATA / "dem_iran.npy"
    if path.exists():
        print("have", path.name, flush=True)
        return
    w, s, e, n = IRAN_BOX
    per = round(1 / IRAN_STEP)                                   # samples a degree
    out = np.zeros((round((n - s) * per), round((e - w) * per)), np.float32)
    token = json.loads(get(TOKEN.format(90)))["token"]
    missing = 0
    with Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="3", GDAL_HTTP_RETRY_DELAY="2"):
        for lat in range(int(s), int(n)):
            for lon in range(int(w), int(e)):
                tile = f"{'N' if lat >= 0 else 'S'}{abs(lat):02d}_00_E{lon:03d}_00"
                try:
                    with rasterio.open("/vsicurl/" + GLO.format(90, 30, tile) + "?" + token) as src:
                        a = src.read(1, out_shape=(per, per), resampling=rasterio.enums.Resampling.average)
                except rasterio.errors.RasterioIOError:
                    missing += 1                                 # open sea: no tile
                    continue
                r0 = round((n - lat - 1) * per)
                c0 = round((lon - w) * per)
                out[r0:r0 + per, c0:c0 + per] = a
            print(f"  DEM row {lat} N done ({missing} tiles missing so far)", flush=True)
    np.save(path, out)
    print("fetched", path.name, out.shape, f"{missing} sea tiles", flush=True)


def dem_local() -> None:
    token = None
    for t in LOCAL_TILES:
        path = DATA / f"dem_{t}.npy"
        if path.exists() or clone(ROOT / "data" / "tehranwater" / f"dem_{t}.npy", path):
            print("have", path.name, flush=True)
            continue
        token = token or json.loads(get(TOKEN.format(30)))["token"]
        with Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"), rasterio.open("/vsicurl/" + GLO.format(30, 10, t) + "?" + token) as s:
            np.save(path, s.read(1))
        print("fetched", path.name, flush=True)


def wms(box, name: str, side: int = 3800) -> None:
    """A texture from four WMS quadrants (NW, NE, SW, SE), each at most 3800 px on its longer side."""
    path = DATA / name
    if path.exists():
        print("have", name, flush=True)
        return
    w, s, e, n = box
    mx, my = (w + e) / 2, (s + n) / 2
    qw, qh = (e - w) / 2, (n - s) / 2
    if qw >= qh:
        pw, ph = side, round(side * qh / qw)
    else:
        pw, ph = round(side * qw / qh), side
    quads = ((w, my, mx, n), (mx, my, e, n), (w, s, mx, my), (mx, s, e, my))
    out = Image.new("RGB", (2 * pw, 2 * ph))
    for k, (a, b, c, d) in enumerate(quads):
        im = Image.open(io.BytesIO(get(WMS.format(a, b, c, d, pw, ph)))).convert("RGB")
        assert im.size == (pw, ph), ("the WMS returned an error tile", im.size)
        out.paste(im, ((k % 2) * pw, (k // 2) * ph))
    out.save(path, quality=92)
    print("fetched", name, out.size, flush=True)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    rate_a()
    payne()
    boundaries()
    dem_local()
    wms(KARAJ_BOX, "tex_karaj.jpg")
    wms(IRAN_BOX, "tex_iran.jpg")
    dem_iran()
    print("inputs in", DATA, flush=True)


if __name__ == "__main__":
    main()
