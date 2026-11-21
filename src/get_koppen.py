"""Fetch and cache the inputs of the Köppen film (koppen_fa): the 1-km Köppen-Geiger maps of Beck et al. (2023) for
the recent and the future climate of Iran, their confidence layers, and Iran's province outlines.

    data/koppen/koppen_geiger_tif.zip   the maps as GeoTIFFs (figshare 21789074, version 2; 130.6 MB; CC BY 4.0)
    data/koppen/koppen_geiger_nc.zip    the same maps as netCDF with a confidence layer (kg_confidence: the share of the
                                        ensemble members that gave the cell's class; 755.3 MB)
    data/koppen/tif/<period>[_<ssp>].tif and nc/<period>[_<ssp>].nc   the 1-km files of the periods the film uses
    data/koppen/ne/                     Natural Earth 10 m admin-1 (public domain): Iran's 31 provinces

Beck, H. E., T. R. McVicar, N. Vergopolan, A. Berg, N. J. Lutsko, A. Dufour, Z. Zeng, X. Jiang, A. I. J. M. van Dijk and
D. G. Miralles (2023). High-resolution (1 km) Köppen-Geiger maps for 1901-2099 based on constrained CMIP6 projections.
Scientific Data 10, 724, doi:10.1038/s41597-023-02549-6. Licence CC BY 4.0 (figshare record and gloh2o.org/koppen).

    python -I src/get_koppen.py
"""

from __future__ import annotations

import hashlib
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "koppen"
AGENT = {"User-Agent": "research-script/1.0"}
FILES = dict(tif=("https://ndownloader.figshare.com/files/61012822", "koppen_geiger_tif.zip", "7fc2f5a15d4f5fe0ce59c9a9b502aa09"),
             nc=("https://ndownloader.figshare.com/files/61012825", "koppen_geiger_nc.zip", "9f143e1c5e1b4d1bd8b419b5a070939f"))
NE = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip"
# the periods the film uses: the recent climate and the end of the century under three scenarios (and two for the checks)
PERIODS = ("1961_1990", "1991_2020", "2041_2070/ssp245", "2071_2099/ssp126", "2071_2099/ssp245", "2071_2099/ssp370", "2071_2099/ssp585")


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(url: str, path: Path) -> None:
    req = urllib.request.Request(url, headers=AGENT)
    with urllib.request.urlopen(req, timeout=3000) as r, open(path.with_suffix(".part"), "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
    path.with_suffix(".part").rename(path)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    for kind, (url, name, digest) in FILES.items():
        path = DATA / name
        if not path.exists() or md5(path) != digest:
            fetch(url, path)
        assert md5(path) == digest, (name, "checksum")
        z = zipfile.ZipFile(path)
        (DATA / kind).mkdir(exist_ok=True)
        for p in PERIODS:
            out = DATA / kind / f"{p.replace('/', '_')}.{kind}"
            if not out.exists():
                out.write_bytes(z.read(f"{p}/koppen_geiger_0p00833333.{kind}"))
        if kind == "tif" and not (DATA / "legend.txt").exists():
            (DATA / "legend.txt").write_bytes(z.read("legend.txt"))
    ne = DATA / "ne" / "ne_10m_admin_1_states_provinces.zip"
    if not ne.exists():
        ne.parent.mkdir(exist_ok=True)
        fetch(NE, ne)
        zipfile.ZipFile(ne).extractall(DATA / "ne")
    print("ready:", sorted(p.name for p in (DATA / "tif").glob("*.tif")))


if __name__ == "__main__":
    main()
