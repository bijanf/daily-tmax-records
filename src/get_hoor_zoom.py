"""HOOR AL-AZIM, THE OPENING ZOOM: the Earth and the ground between the whole globe and the marsh, keyless public
downloads into data/hoor/zoom/.

The owner on the first cut (15 Nov 2026): «معلوم نیست هورالعظیم کجاست؛ باید از کره‌ی زمین اولش زوم کنی آدم بفهمه»
(it is not clear where Hoor al-Azim is; zoom in from the globe at the start). The zoom needs one product at every
scale, so that the tone does not change on the way down:

    g.jpg, r.jpg, m.jpg, n.jpg   Sentinel-2 cloudless 2016 by EOX (s2maps.eu; CC BY 4.0; contains modified Copernicus
                                 Sentinel data 2016), true colour, EPSG:4326, boxes centred on the film's frame
                                 (47.715 E, 31.41 N):
                                 g  the whole Earth, 4096 x 2048 (about 9.8 km a pixel at the equator)
                                 r  the region, 42 x 48 degrees at about 1.5 km (Iran, Iraq, the Persian Gulf; the frame of the rest at
                                    that scale fits inside it, corners included)
                                 m  7.2 x 10.8 degrees at about 300 m
                                 n  1.8 x 2.7 degrees at about 75 m (the ground around the Landsat picture)
    levels.json                  each picture's box (W, S, E, N) and size

The countries' outlines come from Natural Earth's 10 m admin-0 polygons, which get_hoor.py already keeps in
data/hoor/ne (Iran and Iraq only are drawn).

    python -I src/get_hoor_zoom.py
"""

from __future__ import annotations

import io
import json
import math
import sys
import urllib.request
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import get_hoor as gh  # noqa: E402

OUT = gh.OUT / "zoom"
UA = {"User-Agent": "daily-tmax-records/hoor (research reel)"}
WMS = ("https://tiles.maps.eox.at/wms?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1&LAYERS=s2cloudless&STYLES="
       "&SRS=EPSG:4326&BBOX={},{},{},{}&WIDTH={}&HEIGHT={}&FORMAT=image/jpeg")
LON0, LAT0 = (gh.BOX[0] + gh.BOX[2]) / 2, (gh.BOX[1] + gh.BOX[3]) / 2          # the frame's centre
KM_LAT = 111.32                                                                  # km a degree of latitude (the film's grid)
KM_LON = KM_LAT * math.cos(math.radians(LAT0))                                   # km a degree of longitude at the centre
# name: half-width (deg of longitude), half-height (deg of latitude), km a pixel
NESTED = dict(r=(21.0, 24.0, 1.5), m=(3.6, 5.4, 0.3), n=(0.9, 1.35, 0.075))
CHUNK = 2000                                                                     # rows a request (the map service's comfort)


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
        return r.read()


def fetch(box: tuple, w: int, h: int) -> Image.Image:
    """One box as one picture, asked for in horizontal bands of at most CHUNK rows."""
    west, south, east, north = box
    out = Image.new("RGB", (w, h))
    y = 0
    while y < h:
        rows = min(CHUNK, h - y)
        n = north - (north - south) * y / h
        s = north - (north - south) * (y + rows) / h
        part = Image.open(io.BytesIO(get(WMS.format(west, s, east, n, w, rows)))).convert("RGB")
        assert part.size == (w, rows), part.size
        out.paste(part, (0, y))
        y += rows
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    levels = {}
    plan = dict(g=((-180.0, -90.0, 180.0, 90.0), 4096, 2048))
    for name, (dx, dy, km) in NESTED.items():
        box = (LON0 - dx, LAT0 - dy, LON0 + dx, LAT0 + dy)
        plan[name] = (box, round(2 * dx * KM_LON / km), round(2 * dy * KM_LAT / km))
    for name, (box, w, h) in plan.items():
        path = OUT / f"{name}.jpg"
        if not path.exists():
            fetch(box, w, h).save(path, quality=93, subsampling=0)
            print("saved", path.name, (w, h), flush=True)
        else:
            assert Image.open(path).size == (w, h), (name, Image.open(path).size, (w, h))
            print("have", path.name, (w, h))
        levels[name] = dict(box=[round(v, 6) for v in box], size=[w, h])
    (OUT / "levels.json").write_text(json.dumps(levels, indent=1))


if __name__ == "__main__":
    main()
