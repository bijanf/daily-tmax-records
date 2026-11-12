"""HAMOUN FROM SPACE, THIRD FILM: the ground around the Landsat pictures and the lines drawn on it, a keyless
public download into data/hamoun/reel3/.

The film's camera moves between three views that share one map projection: longitude and latitude as straight
axes, with hamoun.py's picture pixel (get_hamoun.DLON by DLAT degrees: square on the ground at 31 N) as the unit.
A view is a centre and a scale (frame pixels per picture pixel); the three ground pictures below are the same
product at three pixel sizes, so the camera can travel from one to the next without a change of tone.

    near.jpg, mid.jpg, wide.jpg   Sentinel-2 cloudless 2016 by EOX (s2maps.eu; CC BY 4.0; contains modified
                                  Copernicus Sentinel data 2016), true colour, one WMS request each:
                                  near  60.39-62.61 E, 29.14-32.50 N at the picture's own pixel (about 143 m)
                                  mid   58.80-64.20 E, 27.20-34.80 N at 2.5 picture pixels (about 360 m)
                                  wide  57.60-71.40 E, 22.60-41.40 N at 6 picture pixels (about 860 m)
    ne/*.zip                      Natural Earth 10 m (public domain; naciscdn.org): the land boundary lines, the
                                  countries, the river centre lines
    lines.json                    the Iran-Afghanistan, Iran-Pakistan and Afghanistan-Pakistan boundaries and the
                                  Helmand river (its main stem from the Hindu Kush to the Hamoun) as lon/lat lists
    dust_20230922_<sensor>.jpg    the dust storm of 22 September 2023 (31 Shahrivar 1402) in true colour, three
                                  passes of one day from NASA GIBS (Corrected Reflectance, keyless WMS), 59.9-63.6 E,
                                  27.7-33.2 N at about 240 m: MODIS on Terra (05:35 UTC = 09:05 in Iran), VIIRS on
                                  Suomi NPP (08:36 UTC = 12:06) and VIIRS on NOAA-20 (09:30 UTC = 13:00); the times
                                  are the granules' start times from NASA's CMR (MOD021KM, VNP02MOD, VJ102MOD at
                                  61.5 E, 30.5 N). NASA's Earth Observatory showed this day (image of the day,
                                  28 Sep 2023, "Dusty Skies in Southern Asia"): "The dust appears to emanate from the
                                  ephemeral Hamun wetlands"

    python -I src/get_hamoun3.py
"""

from __future__ import annotations

import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import get_hamoun as gh  # noqa: E402  (the picture grid only)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "hamoun" / "reel3"
NE = OUT / "ne"
UA = {"User-Agent": "daily-tmax-records/hamoun (research reel)"}
WMS = ("https://tiles.maps.eox.at/wms?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1&LAYERS=s2cloudless&STYLES="
       "&SRS=EPSG:4326&BBOX={},{},{},{}&WIDTH={}&HEIGHT={}&FORMAT=image/jpeg")
# name: (W, S, E, N, picture pixels per ground-picture pixel)
GROUND = dict(near=(60.39, 29.141, 62.61, 32.495, 1.0),
              mid=(58.80, 27.20, 64.20, 34.80, 2.5),
              wide=(57.60, 22.60, 71.40, 41.40, 6.0))
NE_URL = "https://naciscdn.org/naturalearth/10m/{}/{}.zip"
NE_FILES = dict(ne_10m_admin_0_boundary_lines_land="cultural", ne_10m_admin_0_countries="cultural",
                ne_10m_rivers_lake_centerlines="physical")
REGION = (56.0, 22.0, 72.0, 42.0)                    # W, S, E, N: lines outside are dropped
GIBS = ("https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1"
        "&LAYERS={}_CorrectedReflectance_TrueColor&STYLES=&SRS=EPSG:4326&BBOX={},{},{},{}&WIDTH={}&HEIGHT={}"
        "&FORMAT=image/jpeg&TIME={}")
DUST_DAY = "2023-09-22"
DUST_BOX = (59.9, 27.7, 63.6, 33.2)                  # W, S, E, N
DUST_PASSES = (("MODIS_Terra", "05:35"), ("VIIRS_SNPP", "08:36"), ("VIIRS_NOAA20", "09:30"))   # sensor, UTC


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
        return r.read()


def size(name: str) -> tuple:
    w, s, e, n, k = GROUND[name]
    return round((e - w) / (gh.DLON * k)), round((n - s) / (gh.DLAT * k))


def ground() -> None:
    from PIL import Image
    for name, (w, s, e, n, _k) in GROUND.items():
        path = OUT / f"{name}.jpg"
        if path.exists():
            print("have", path.name)
            continue
        wd, ht = size(name)
        im = Image.open(io.BytesIO(get(WMS.format(w, s, e, n, wd, ht)))).convert("RGB")
        assert im.size == (wd, ht), ("the WMS returned an error tile", name, im.size)
        im.save(path, quality=93)
        print("saved", path.name, im.size, flush=True)


def dust() -> None:
    from PIL import Image
    w, s, e, n = DUST_BOX
    wd, ht = round((e - w) / 0.0025), round((n - s) / 0.00215)
    for sensor, _utc in DUST_PASSES:
        path = OUT / f"dust_{DUST_DAY.replace('-', '')}_{sensor}.jpg"
        if path.exists():
            print("have", path.name)
            continue
        im = Image.open(io.BytesIO(get(GIBS.format(sensor, w, s, e, n, wd, ht, DUST_DAY)))).convert("RGB")
        assert im.size == (wd, ht), (sensor, im.size)
        im.save(path, quality=93)
        print("saved", path.name, im.size, flush=True)


def natural_earth() -> None:
    NE.mkdir(parents=True, exist_ok=True)
    for stem, kind in NE_FILES.items():
        path = NE / f"{stem}.zip"
        if not path.exists():
            path.write_bytes(get(NE_URL.format(kind, stem)))
            print("saved", path.name, flush=True)
        with zipfile.ZipFile(path) as z:
            assert any(n.endswith(".shp") for n in z.namelist()), stem


def _inside(pts: list) -> list:
    w, s, e, n = REGION
    return [[round(x, 5), round(y, 5)] for x, y in pts if w <= x <= e and s <= y <= n]


def lines() -> None:
    import geopandas as gpd
    from shapely.geometry import LineString, MultiLineString
    from shapely.ops import linemerge

    def parts(geom) -> list:
        if geom is None or geom.is_empty:
            return []
        g = linemerge(geom) if isinstance(geom, MultiLineString) else geom
        return [list(p.coords) for p in (g.geoms if isinstance(g, MultiLineString) else [g]) if isinstance(p, LineString)]

    land = gpd.read_file(f"zip://{NE / 'ne_10m_admin_0_countries.zip'}")
    name = "ADMIN"
    shp = {c: land.loc[land[name] == c].geometry.union_all() for c in ("Iran", "Afghanistan", "Pakistan")}
    for c, g in shp.items():
        assert g is not None and not g.is_empty, c
    out = {}
    for a, b in (("Iran", "Afghanistan"), ("Iran", "Pakistan"), ("Afghanistan", "Pakistan")):
        shared = shp[a].boundary.intersection(shp[b].boundary)
        segs = [s for s in (_inside(p) for p in parts(shared)) if len(s) > 1]
        assert segs, (a, b)
        out[f"{a}-{b}"] = segs
        print(f"border {a}-{b}: {len(segs)} pieces, {sum(len(s) for s in segs)} points")
    riv = gpd.read_file(f"zip://{NE / 'ne_10m_rivers_lake_centerlines.zip'}")
    col = "name" if "name" in riv.columns else "name_en"
    hel = riv.loc[riv[col].fillna("").str.contains("Helmand|Hilmand|Hirmand", case=False)]
    assert len(hel), sorted(set(riv[col].dropna()))[:40]
    segs = []
    for geom in hel.geometry:
        segs += [s for s in (_inside(p) for p in parts(geom)) if len(s) > 1]
    out["Helmand"] = segs
    print(f"Helmand: {len(hel)} features, {len(segs)} pieces, {sum(len(s) for s in segs)} points; names "
          f"{sorted(set(hel[col]))}")
    near = riv.cx[59.0:69.5, 29.0:35.5]
    print("rivers in the region:", sorted(set(near[col].dropna())))
    (OUT / "lines.json").write_text(json.dumps(out))
    print("saved lines.json")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ground()
    dust()
    natural_earth()
    lines()


if __name__ == "__main__":
    main()
