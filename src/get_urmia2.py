"""LAKE URMIA, SECOND FILM (urmia2_fa): the ground around the lake and the lake's altimetry, keyless downloads.

    data/urmia2/ground.jpg   Sentinel-2 cloudless 2016 by EOX (s2maps.eu; CC BY 4.0; contains modified Copernicus
                             Sentinel data 2016), true colour, 43.8-47.0 E, 35.7-39.6 N at the film's picture pixel
                             (0.0018958 deg of longitude by 0.0015 deg of latitude: square on the ground at 37.7 N)
    data/urmia2/lake*.txt    NASA Global Water Monitor altimetry of Lake Urmia (south basin 000115, north basin
                             001829); column 15 is the height in the EGM2008 datum (m). Printed here as a cross-check
                             only (not on screen): the October-to-mid-November means of 2025 and 2026 and their difference.

    python -I src/get_urmia2.py
"""

from __future__ import annotations

import io
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "urmia2"
UA = {"User-Agent": "daily-tmax-records/urmia (research reel)"}
WMS = ("https://tiles.maps.eox.at/wms?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1&LAYERS=s2cloudless&STYLES="
       "&SRS=EPSG:4326&BBOX={},{},{},{}&WIDTH={}&HEIGHT={}&FORMAT=image/jpeg")
BOX = (43.8, 35.7, 47.0, 39.6)                       # W, S, E, N
DLON, DLAT = 0.0015 / 0.7919, 0.0015                 # cos(37.7 deg) = 0.79122; the film uses 0.0015 / cos(37.7 deg)
BASE = "https://earth.gsfc.nasa.gov/gwm/timeseries/"
SERIES = dict(south="lake000115.10d.2.txt", north="lake001829.27a.2.txt")


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
        return r.read()


def ground() -> None:
    import math
    from PIL import Image
    path = OUT / "ground.jpg"
    if path.exists():
        print("have", path.name)
        return
    dlon = 0.0015 / math.cos(math.radians(37.7))
    w, s, e, n = BOX
    wd, ht = round((e - w) / dlon), round((n - s) / DLAT)
    im = Image.open(io.BytesIO(get(WMS.format(w, s, e, n, wd, ht)))).convert("RGB")
    assert im.size == (wd, ht), ("the WMS returned an error tile", im.size)
    im.save(path, quality=93)
    print("saved", path.name, im.size, flush=True)


def series(name: str) -> dict:
    """date -> EGM2008 height (m) of the series, the rows with a real value."""
    path = OUT / SERIES[name]
    if not path.exists():
        path.write_bytes(get(BASE + SERIES[name]))
        print("saved", path.name, flush=True)
    out = {}
    for line in path.read_text(errors="replace").splitlines():
        p = line.split()
        if len(p) < 16 or not (p[2].isdigit() and len(p[2]) == 8):
            continue
        h = float(p[14])
        if h < 9000:
            out[date(int(p[2][:4]), int(p[2][4:6]), int(p[2][6:]))] = h
    return out


def mean(s: dict, a: date, b: date) -> tuple:
    v = [h for d, h in s.items() if a <= d <= b]
    assert v, (a, b)
    return sum(v) / len(v), len(v)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ground()
    for name in SERIES:
        s = series(name)
        m25, n25 = mean(s, date(2025, 10, 1), date(2025, 11, 15))
        m26, n26 = mean(s, date(2026, 10, 1), date(2026, 11, 15))
        print(f"{name}: {len(s)} values, last {max(s)}; 1 Oct-15 Nov 2025 {m25:.2f} m (n={n25}), 2026 {m26:.2f} m (n={n26}); "
              f"difference {m26 - m25:+.2f} m")
        if name == "north":
            a, b = s[date(2026, 6, 10)], s[date(2026, 10, 23)]
            print(f"north: 2026-06-10 {a:.2f} m, 2026-10-23 {b:.2f} m, October minus June {b - a:+.2f} m")


if __name__ == "__main__":
    sys.exit(main())
