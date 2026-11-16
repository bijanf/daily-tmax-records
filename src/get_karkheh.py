"""THE KARKHEH FILM, its data («سدِ کرخه پر شد؟»): keyless public downloads into data/karkheh/ (git-ignored).

A post of 15 Nov 2026 said the Karkheh dam "filled", over two satellite pictures (10 Nov 2025 and 10 Nov 2026). This
file measures the reservoir on those days and on others, and fetches what the film shows downstream.

THE LAKE. Sentinel-2 L2A (ESA Copernicus; Microsoft's Planetary Computer with its anonymous token), read with the
Karun film's reader (karun_s2.band: inside each file, the 10-m bands averaged to 30 m, the 20-m bands as they are) on
a 30-m lon/lat grid. Open water = MNDWI > 0 and SWIR1 < 0.15 and NIR < 0.12 (the Karun film's test), counted in the
lake zone: within 600 m of water that JRC's Global Surface Water ever saw (1984-2021), so mountain shadow is not water.
The count is direct (no scaling by a clear share); the clear share is taken over the lake zone itself, and a pass with
less than 0.98 of the zone clear is a lower bound.

    lake.csv              label, date, cloud, zone_clear, km2 (the strict test), km2_loose (without the NIR test)
                          two passes near 10 November of 2017-2026, the full lake of May 2019, every pass of autumn 2026
    frame_<day>.npz       rgb (reflectance), water, loose on the film's frame (FRAME: 9:16 on the ground) for DAYS
    card.jpg, card.json   Sentinel-2 cloudless 2016 by EOX (CC BY 4.0) from above the dam to below the marsh
    osm_karkheh.json, river.json   the Karkheh's course from OpenStreetMap ((c) contributors, ODbL), dam to marsh
    border.json           the Iran-Iraq border inside the map (Natural Earth 10 m)
    dust_<day>.jpg        MODIS true colour (NASA GIBS / Worldview) of two days of May 2022: a wall of dust in Iraq
                          at the border (Aqua, 16 May), and the haze over Khuzestan a day later (Terra, 17 May)

    python -I src/get_karkheh.py            # the pictures, the map, the river, the border, the dust day
    python -I src/get_karkheh.py --series   # lake.csv (about 25 minutes)
"""

from __future__ import annotations

import io
import json
import math
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from rasterio.warp import Resampling
from shapely.geometry import LineString, MultiLineString, Polygon, box as sbox, shape
from shapely.ops import linemerge, unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
import get_hoor_zoom as hz0  # noqa: E402  (fetch: the EOX map service in bands)
import get_karun as gk  # noqa: E402
import get_urmia as gu  # noqa: E402
import karun_s2 as ks  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "karkheh"
ZONE_BOX = (47.60, 32.44, 48.22, 33.04)              # W, S, E, N: the lake above the dam, for the count
FRAME = (47.8235, 32.290, 48.1905, 32.840)           # the film's frame: 34.4 x 61.2 km; the lake above the tag, the dam at 0.64 of its height
DAM = (48.130, 32.490)                               # the Karkheh dam
DAYS = ("2026-11-10", "2025-11-10", "2019-05-11")    # now, a year before (the post's two days), the full lake
CARD_BOX = (46.98, 30.70, 48.64, 33.204)             # the map: 9:16 on the ground, the river's whole course from the dam to the marsh inside it
CARD_PX = (1200, 2133)
MARSH_AT = (47.92, 31.62)                            # where the river's line ends for the film: the marsh's Iranian side
DUST = (("Aqua", "2022-05-16"), ("Terra", "2022-05-17"))   # 26 and 27 Ordibehesht 1401: a wall of dust in Iraq at the border, a day later haze over Khuzestan
DUST_BOX = (43.5, 26.4, 51.0, 37.66)
GIBS = ("https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1"
        "&LAYERS=MODIS_{}_CorrectedReflectance_TrueColor&STYLES=&SRS=EPSG:4326&BBOX={},{},{},{}&WIDTH={}&HEIGHT={}"
        "&FORMAT=image/jpeg&TIME={}")
OVERPASS = "https://overpass-api.de/api/interpreter"
QUERY = '[out:json][timeout:90];way["waterway"="river"]["name"~"کرخه|Karkheh"](30.8,47.0,33.6,48.7);out geom;'
UA = {"User-Agent": "reel-map-fetch/1.0"}
NE = ROOT / "data" / "hoor" / "ne" / "ne_10m_admin_0_countries.shp"   # Natural Earth, kept by get_hoor.py

# the reader of karun_s2.py works on get_karun's places: the film's two boxes are registered there, cached here
gk.OUT = OUT
for _name, _b in (("kzone", ZONE_BOX), ("kframe", FRAME)):
    gk.PLACES[_name] = dict(box=_b, what="water", poly=[(_b[0], _b[3]), (_b[2], _b[3]), (_b[2], _b[1]), (_b[0], _b[1])])


def passes(name: str, start: str, end: str) -> list:
    """The days on which Sentinel-2 covers the whole box: (day, mean cloud of the tiles, the tiles)."""
    poly = Polygon(gk.PLACES[name]["poly"])
    d = gu.get(gu.STAC, {"collections": ["sentinel-2-l2a"], "bbox": list(poly.bounds), "limit": 500,
                         "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z"})
    by = {}
    for f in d.get("features", []):
        by.setdefault(f["properties"]["datetime"][:10], []).append(f)
    out = []
    for day, fs in sorted(by.items()):
        u = unary_union([shape(f["geometry"]) for f in fs])
        if u.intersection(poly).area / poly.area >= 0.999:
            out.append((day, float(np.mean([f["properties"].get("eo:cloud_cover") or 0 for f in fs])), fs))
    return out


def read(name: str, fs: list, colour: bool = False) -> dict:
    """One day on the place's grid: the water by both tests, the clear pixels, and the true colour if asked."""
    base = min(float(f["properties"].get("s2:processing_baseline", "0") or 0) for f in fs)
    off = 1000.0 if base >= 4.0 else 0.0
    keys = ("B03", "B08", "B11") + (("B04", "B02") if colour else ())
    b = {k: (ks.band(fs, k, name, Resampling.average) - off) / 10000.0 for k in keys}
    scl = ks.band(fs, "SCL", name, Resampling.nearest)
    g, nir, sw = (np.clip(b[k], 1e-4, None) for k in ("B03", "B08", "B11"))
    ok = np.isfinite(g) & np.isfinite(nir) & np.isfinite(sw) & np.isfinite(scl)
    loose = ok & ((g - sw) / (g + sw) > 0) & (sw < 0.15)
    water = loose & (nir < 0.12)
    s = np.nan_to_num(scl, nan=0).astype(int)
    clear = ok & ~np.isin(s, [0, 1, 8, 9, 10, 11]) & ((s != 3) | water)
    out = dict(water=water, loose=loose, clear=clear)
    if colour:
        out["rgb"] = np.dstack([b["B04"], b["B03"], b["B02"]]).astype(np.float32)
    return out


def _one(job):
    label, day, cloud, fs = job
    mk = gk.masks("kzone")
    zone = mk["near"] & mk["poly"]
    r = read("kzone", fs)
    px = (gk.M / 1000.0) ** 2
    return dict(label=label, date=day, cloud=round(cloud, 1), zone_clear=round(float((r["clear"] & zone).sum() / zone.sum()), 3),
                km2=round(float((r["water"] & zone).sum() * px), 1), km2_loose=round(float((r["loose"] & zone).sum() * px), 1))


def series() -> None:
    gk.masks("kzone")
    near = lambda c, target, n: sorted([x for x in c if x[1] <= 30],   # noqa: E731
                                       key=lambda x: abs((date.fromisoformat(x[0]) - date.fromisoformat(target)).days))[:n]
    jobs = []
    for y in range(2017, 2027):
        jobs += [(f"Nov {y}", *p) for p in near(passes("kzone", f"{y}-10-28", f"{y}-11-22"), f"{y}-11-10", 2)]
    jobs += [("full 2019", *p) for p in near(passes("kzone", "2019-04-15", "2019-06-05"), "2019-05-11", 2)]
    jobs += [("autumn 2026", *p) for p in passes("kzone", "2026-09-20", "2026-11-16") if p[1] <= 30 and not any(j[1] == p[0] for j in jobs)]
    with ProcessPoolExecutor(5) as ex:
        rows = list(ex.map(_one, jobs))
    df = pd.DataFrame(rows).sort_values(["date"])
    df.to_csv(OUT / "lake.csv", index=False)
    print(df.to_string(index=False))


def _frame(day: str):
    p = passes("kframe", day, day)
    assert p, day
    r = read("kframe", p[0][2], colour=True)
    np.savez_compressed(OUT / f"frame_{day}.npz", rgb=r["rgb"], water=r["water"], loose=r["loose"])
    return day, len(p[0][2]), round(float(r["water"].sum() * (gk.M / 1000.0) ** 2), 1)


def frames() -> None:
    gk.masks("kframe")
    todo = [d for d in DAYS if not (OUT / f"frame_{d}.npz").exists()]
    with ProcessPoolExecutor(3) as ex:
        for r in ex.map(_frame, todo):
            print("frame", r, flush=True)


def river() -> list:
    """The Karkheh from the dam to the marsh: the ways named Karkheh joined end to end, upstream to downstream."""
    raw = OUT / "osm_karkheh.json"
    if not raw.exists():
        req = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({"data": QUERY}).encode(), headers=UA)
        with urllib.request.urlopen(req, timeout=180) as r:
            raw.write_bytes(r.read())
    ways = [[(round(p["lon"], 5), round(p["lat"], 5)) for p in e["geometry"]] for e in json.loads(raw.read_text())["elements"]
            if e["type"] == "way" and len(e.get("geometry", [])) > 1]
    best = {}
    for w in ways:                                      # two ways drawn over one stretch: keep the finer
        key = frozenset([(round(w[0][0], 3), round(w[0][1], 3)), (round(w[-1][0], 3), round(w[-1][1], 3))])
        if key not in best or len(w) > len(best[key]):
            best[key] = w
    ways = list(best.values())
    start = max(ways, key=lambda w: max(w[0][1], w[-1][1]))          # the northernmost end is upstream
    line = list(start) if start[0][1] >= start[-1][1] else list(start[::-1])
    left = [w for w in ways if w is not start]
    while left:
        end = line[-1]
        gap, i = min((min(math.dist(end, w[0]), math.dist(end, w[-1])), i) for i, w in enumerate(left))
        if gap > 0.03:
            print(f"river: {len(left)} way(s) not joined; the nearest is {gap:.3f} degrees from the line's end {end}")
            break
        w = left.pop(i)
        line += (w if math.dist(end, w[0]) <= math.dist(end, w[-1]) else w[::-1])[1:]
    km = lambda a, b: math.hypot((a[0] - b[0]) * 94.5, (a[1] - b[1]) * 111.32)   # noqa: E731
    i_dam = int(np.argmin([km(p, DAM) for p in line]))
    i_end = int(np.argmin([km(p, MARSH_AT) for p in line]))
    assert km(line[i_dam], DAM) < 3.0, ("the line does not pass the dam", km(line[i_dam], DAM))
    assert i_end > i_dam and km(line[i_end], MARSH_AT) < 15.0, ("the line does not reach the marsh", i_dam, i_end, km(line[i_end], MARSH_AT))
    part = line[i_dam:i_end + 1]
    length = sum(km(a, b) for a, b in zip(part[:-1], part[1:]))
    print(f"river: {len(line)} points joined; dam to marsh {len(part)} points, {length:.0f} km along the river; "
          f"nearest to the dam {km(line[i_dam], DAM):.2f} km, to the marsh point {km(line[i_end], MARSH_AT):.1f} km")
    return part


def border(area: tuple = CARD_BOX, pair: tuple = ("IRN", "IRQ")) -> list:
    """The border of two countries inside a box, as lon/lat lists (Natural Earth 10 m admin 0)."""
    import shapefile
    r = shapefile.Reader(str(NE))
    fields = [f[0] for f in r.fields[1:]]
    g = {}
    for s in r.iterShapeRecords():
        a3 = dict(zip(fields, s.record))["ADM0_A3"]
        if a3 in pair:
            g[a3] = shape(s.shape.__geo_interface__)
    shared = g[pair[0]].boundary.intersection(g[pair[1]].boundary.buffer(0.002)).intersection(sbox(*area).buffer(0.3))
    merged = linemerge(shared) if isinstance(shared, MultiLineString) else shared
    lines = [merged] if isinstance(merged, LineString) else [l for l in getattr(merged, "geoms", []) if isinstance(l, LineString)]
    out = [[(round(x, 5), round(y, 5)) for x, y in l.coords] for l in lines if l.length > 0.02]
    print(f"border: {len(out)} piece(s), {sum(len(l) for l in out)} points")
    assert out
    return out


def card() -> None:
    if not (OUT / "card.jpg").exists():
        hz0.fetch(CARD_BOX, *CARD_PX).save(OUT / "card.jpg", quality=93, subsampling=0)
    (OUT / "card.json").write_text(json.dumps(dict(box=CARD_BOX, px=CARD_PX)))
    (OUT / "river.json").write_text(json.dumps(river()))
    (OUT / "border.json").write_text(json.dumps(border()))


def dust() -> None:
    w, s, e, n = DUST_BOX
    for sat, day in DUST:
        path = OUT / f"dust_{day}.jpg"
        if path.exists():
            continue
        req = urllib.request.Request(GIBS.format(sat, w, s, e, n, 1080, 1920, day), headers=UA)
        with urllib.request.urlopen(req, timeout=180) as r:
            im = Image.open(io.BytesIO(r.read())).convert("RGB")
        assert im.size == (1080, 1920), im.size
        im.save(path, quality=93)
        print("saved", path.name, sat)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if "--series" in sys.argv:
        series()
        return
    card()
    dust()
    frames()


if __name__ == "__main__":
    main()
