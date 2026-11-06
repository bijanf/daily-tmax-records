"""IRAN'S WATER, WEIGHED FROM SPACE: the inputs of grace.py, all keyless public downloads, into data/grace/.

    CSR RL06.3 mascons, all corrections (UT Austin; NASA open data; Save et al. 2016, data doi:10.15781/cgq9-nh24)
        and its land mask, 0.25 deg grid of 1-deg equal-area mascons, Apr 2002 onwards
    GSFC RL06 v2.0 mascons (NASA Goddard; Loomis et al. 2019, doi:10.1007/s00190-019-01252-y), 0.5 deg grid
    COST-G RL02 GravIS TWS (GFZ; CC BY 4.0; doi:10.5880/COST-G.GRAVIS_02_L3_TWS), 1 deg, combined spherical harmonics
    G-REALM lake 000270, the Caspian Sea's level from satellite altimetry (NASA/USDA; public), 10-day
    Natural Earth 10 m admin-0 countries (public domain)

The three gravity products use the same satellites (GRACE 2002-2017, GRACE-FO from 2018) and share the C20/C30
replacement, the GIA model and the de-aliasing: they are a check of the processing, not of the measurement.
A file that already exists is not fetched again; a newer release of a product carries a new name: update URLS.

    python -I src/get_grace.py
"""

from __future__ import annotations

import shutil

import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "grace"
URLS = {
    "CSR_GRACE_GRACE-FO_RL0603_Mascons_all-corrections.nc":
        "https://download.csr.utexas.edu/outgoing/grace/RL0603_mascons/CSR_GRACE_GRACE-FO_RL0603_Mascons_all-corrections.nc",
    "CSR_GRACE_GRACE-FO_RL06_Mascons_v02_LandMask.nc":
        "https://download.csr.utexas.edu/outgoing/grace/RL0603_mascons/CSR_GRACE_GRACE-FO_RL06_Mascons_v02_LandMask.nc",
    "GSFC.glb_.200204_202606_RL06v2.0_OBP-ICE6GD_HALFDEGREE.nc":
        "https://earth.gsfc.nasa.gov/sites/default/files/geo/GSFC.glb_.200204_202606_RL06v2.0_OBP-ICE6GD_HALFDEGREE.nc",
    "GRAVIS-3_COSTG_0200_TWS_GRID_GFZ_0001.nc":
        "https://isdc-data.gfz.de/grace/GravIS/COST-G/Level-3/TWS/GRAVIS-3_COSTG_0200_TWS_GRID_GFZ_0001.nc",
    "lake000270.10d.2.txt": "https://earth.gsfc.nasa.gov/gwm/timeseries/lake000270.10d.2.txt",
}
NE_ZIP = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip"


def fetch(url: str, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "daily-tmax-records/grace"})
    with urllib.request.urlopen(req, timeout=600) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
    tmp.rename(path)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    for name, url in URLS.items():
        path = DATA / name
        if path.exists() and path.stat().st_size > 0:
            print(f"have  {name} ({path.stat().st_size / 1e6:.0f} MB)", flush=True)
            continue
        print(f"fetch {name}", flush=True)
        fetch(url, path)
    shp = DATA / "ne_10m_admin_0_countries" / "ne_10m_admin_0_countries.shp"
    if not shp.exists():
        z = DATA / "ne_10m_admin_0_countries.zip"
        fetch(NE_ZIP, z)
        with zipfile.ZipFile(z) as zf:
            zf.extractall(DATA / "ne_10m_admin_0_countries")
        z.unlink()
    print("inputs in", DATA, flush=True)


if __name__ == "__main__":
    main()
