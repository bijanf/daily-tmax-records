"""THE KARUN REEL, the ground between the whole globe and the first place (the Gotvand lake), the map between the two
places, and the river's line: keyless public downloads into data/karun/zoom/.

    g.jpg, r.jpg, m.jpg, n.jpg   Sentinel-2 cloudless 2016 by EOX (s2maps.eu; CC BY 4.0; contains modified Copernicus
                                 Sentinel data 2016), EPSG:4326, nested boxes centred on the Gotvand frame (the levels
                                 of get_hoor_zoom.py: the whole Earth, 1.5 km, 300 m, 75 m)
    card.jpg                     the same mosaic over the river from above the Gotvand lake to the Persian Gulf
                                 (CARD_BOX, the frame of the map between the two places), about 170 m a pixel
    river.json                   the Karun's course as longitude/latitude lists, from OpenStreetMap (the ways named
                                 Karun between Karun-3 and the Arvand, joined end to end; (c) OpenStreetMap
                                 contributors, ODbL), fetched once through the Overpass API
    levels.json                  each picture's box and size

Natural Earth's 10 m rivers have the Karkheh and the Arvand but not the Karun, hence OpenStreetMap for the line.

    python -I src/get_karun_zoom.py
"""

from __future__ import annotations

import json
import math
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import get_hoor_zoom as hz0  # noqa: E402  (fetch: the map service in bands)
import get_karun as gk  # noqa: E402

OUT = gk.OUT / "zoom"
W_, S_, E_, N_ = gk.PLACES["gotvand"]["box"]
LON0, LAT0 = (W_ + E_) / 2, (S_ + N_) / 2                                        # the first place's centre
KM_LAT = 111.32
KM_LON = KM_LAT * math.cos(math.radians(LAT0))
NESTED = dict(r=(21.0, 24.0, 1.5), m=(3.6, 5.4, 0.3), n=(0.9, 1.35, 0.075))      # half-width, half-height (deg), km a pixel
CARD_BOX = (47.705, 29.92, 49.845, 33.16)                                        # W, S, E, N: the map between the places
CARD_PX = (1200, 2133)
OVERPASS = "https://overpass-api.de/api/interpreter"
QUERY = '[out:json][timeout:90];way["waterway"="river"]["name"~"کارون|Karun"](29.9,47.7,33.3,50.6);out geom;'
UA = {"User-Agent": "reel-map-fetch/1.0"}


def river() -> list:
    """The Karun's course, upstream to downstream: the ways joined at shared end points, starting at the easternmost."""
    raw = OUT / "osm_karun.json"
    if not raw.exists():
        req = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({"data": QUERY}).encode(), headers=UA)
        with urllib.request.urlopen(req, timeout=180) as r:
            raw.write_bytes(r.read())
    ways = [[(round(p["lon"], 5), round(p["lat"], 5)) for p in e["geometry"]] for e in json.loads(raw.read_text())["elements"]
            if e["type"] == "way" and "بازفت" not in e["tags"].get("name", "") and len(e.get("geometry", [])) > 1]
    ways = [w for w in ways if max(p[0] for p in w) < 50.2]                       # from Karun-3 down
    best = {}                                                                     # two ways drawn over one stretch: keep the finer
    for w in ways:
        key = frozenset([(round(w[0][0], 3), round(w[0][1], 3)), (round(w[-1][0], 3), round(w[-1][1], 3))])
        if key not in best or len(w) > len(best[key]):
            best[key] = w
    ways = list(best.values())
    start = max(ways, key=lambda w: w[0][0])
    line, left = list(start), [w for w in ways if w is not start]
    while left:
        end = line[-1]
        d = [(min(math.dist(end, w[0]), math.dist(end, w[-1])), i) for i, w in enumerate(left)]
        gap, i = min(d)
        if gap > 0.02:                                                            # nothing joins within about 2 km: the end
            break
        w = left.pop(i)
        if math.dist(end, w[-1]) < math.dist(end, w[0]):
            w = w[::-1]
        line += w[1:]
    return line


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    levels = {}
    g_src = gk.ROOT / "data" / "hoor" / "zoom" / "g.jpg"                          # the whole Earth is the same picture
    if not (OUT / "g.jpg").exists():
        if g_src.exists():
            shutil.copy(g_src, OUT / "g.jpg")
        else:
            hz0.fetch((-180.0, -90.0, 180.0, 90.0), 4096, 2048).save(OUT / "g.jpg", quality=93, subsampling=0)
    levels["g"] = dict(box=[-180.0, -90.0, 180.0, 90.0], size=[4096, 2048])
    plan = {}
    for name, (dx, dy, km) in NESTED.items():
        box = (LON0 - dx, LAT0 - dy, LON0 + dx, LAT0 + dy)
        plan[name] = (box, round(2 * dx * KM_LON / km), round(2 * dy * KM_LAT / km))
    plan["card"] = (CARD_BOX, *CARD_PX)
    for name, (box, w, h) in plan.items():
        path = OUT / f"{name}.jpg"
        if not path.exists():
            hz0.fetch(box, w, h).save(path, quality=93, subsampling=0)
            print("saved", path.name, (w, h), flush=True)
        else:
            assert Image.open(path).size == (w, h), (name, Image.open(path).size, (w, h))
            print("have", path.name, (w, h))
        levels[name] = dict(box=[round(v, 6) for v in box], size=[w, h])
    (OUT / "levels.json").write_text(json.dumps(levels, indent=1))
    line = river()
    (OUT / "river.json").write_text(json.dumps(line))
    print(f"river: {len(line)} points from {line[0]} to {line[-1]}")


if __name__ == "__main__":
    main()
