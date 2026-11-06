"""THE LOST WATER OVER TEHRAN: the numbers and the clock of the reel «آبی که ایران از دست داد، روی تهران».

The volume: Iran's total stored water (groundwater, soil water, snow, lakes and reservoirs together) from GRACE and
GRACE-FO, src/grace.py (data/grace/grace_reel.npz): per Persian year the mean of three solutions (CSR, GSFC,
COST-G), each on Iran's land more than 200 km from the Caspian applied to all of Iran's area (the Caspian's own
fall leaks into the coast at GRACE's ~300 km resolution), against 1382-1384. Both ends are three-year windows, as
the fact check asked (a single dry year is not the headline): the start 1382-1384 is zero by definition, the end
is the mean of 1402, 1403 and 1404. 1396 has 4 months (GRACE ended in June 2017, GRACE-FO began in June 2018): no
value; 1405 is partial and left out.

The picture: that volume as a layer of one thickness over the city of Tehran (OpenStreetMap relation 6663864,
«شهر تهران»; area on a sphere of radius 6371.0088 km), thickness = volume / area; Milad Tower 435 m to the tip
(51.3753 E, 35.7448 N). The layer is a comparison of scale, not a flood: the caption says so.

The clock: 26 s at 30 frames a second. The end state at 0 s (the layer at its final thickness, the question, the
counter hidden), the layer drains (1.6-2.4 s) and rises again step by step through the years (2.4-8.4 s), the
number lands at 8.4 s; then three text beats (8.4, 15.0, 19.0 s) and the closing question (23.4 s); the camera's
path returns to its first frame at 26 s (a seamless loop).

    data/tehranwater/timeline.json    steps, camera keys and every number for tehranwater3d.py and the film
    python -I src/tehranwater.py > outputs/tehranwater_log.txt
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "tehranwater"
GRACE = ROOT / "data" / "grace" / "grace_reel.npz"
R_KM = 6371.0088
MILAD = dict(lon=51.3753, lat=35.7448, tip_m=435.0)
BASE = (1382, 1383, 1384)
END = (1402, 1403, 1404)
RENEWABLE = 128.5                                     # km3 a year: Iran's internal renewable water (FAO AQUASTAT)
DURATION, FPS = 26.0, 30
HOLD, DRAIN, RISE, LAND = 0.0, 1.6, 2.4, 8.4         # s: end state, drain, rise, the number lands
BEATS = (8.4, 15.0, 19.0, 23.4)                       # s: number, years of renewable water, groundwater, question
EXPECT = dict(end_km3=(375, 385), lo_km3=(350, 365), hi_km3=(400, 415), area_km2=(620, 640),
              years_renewable=(2.85, 3.05))
# the camera, in km from Milad Tower's foot (east, north, up): position and point looked at, at times (s)
CAMERA = [(0.0, (-5.0, -24.0, 3.6), (0.5, 3.0, 0.4)),
          (2.4, (-3.0, -13.0, 1.8), (0.0, 1.0, 0.35)),
          (8.4, (-1.3, -4.2, 0.42), (0.0, 0.6, 0.15)),
          (13.4, (1.8, -5.6, 0.75), (0.0, 1.0, 0.15)),
          (18.4, (4.0, -11.0, 2.2), (0.5, 2.0, 0.4)),
          (23.4, (-3.5, -20.0, 3.2), (0.5, 3.0, 0.4)),
          (26.0, (-5.0, -24.0, 3.6), (0.5, 3.0, 0.4))]


def ring() -> np.ndarray:
    d = json.loads((DATA / "tehran_osm.json").read_text())
    d = d if isinstance(d, list) else [d]
    assert d[0]["osm_id"] == 6663864 and d[0]["geojson"]["type"] == "Polygon", "the city of Tehran, one polygon"
    return np.array(d[0]["geojson"]["coordinates"][0])


def area_km2(r: np.ndarray) -> float:
    """The area of a lon/lat ring on a sphere (km2)."""
    s = 0.0
    for (x1, y1), (x2, y2) in zip(r, r[1:]):
        s += math.radians(x2 - x1) * (2 + math.sin(math.radians(y1)) + math.sin(math.radians(y2)))
    return abs(s) * R_KM ** 2 / 2


def steps() -> list:
    """The counter's steps: (label, km3 lost, the products' range): the base window, the single years, the end."""
    z = np.load(GRACE)
    years = [int(y) for y in z["years"]]
    mean, prods, partial = z["mean"], z["products"], z["partial"]
    by = {y: (float(-mean[k]), [float(-v) for v in prods[k]], bool(partial[k])) for k, y in enumerate(years)}
    base = float(np.mean([by[y][0] for y in BASE]))
    assert abs(base) < 1.0, ("1382-1384 is the reference: its mean is zero", base)
    out = [dict(label="۱۳۸۲ تا ۱۳۸۴", years=list(BASE), km3=0.0, lo=0.0, hi=0.0)]
    for y in range(BASE[-1] + 1, END[0]):
        v, p, part = by[y]
        if part:
            continue                                          # 1396: no value
        out.append(dict(label=str(y), years=[y], km3=v, lo=min(p), hi=max(p)))
    per = np.array([by[y][1] for y in END])                   # years x products
    prod_end = per.mean(axis=0)
    out.append(dict(label="۱۴۰۲ تا ۱۴۰۴", years=list(END), km3=float(np.mean([by[y][0] for y in END])),
                    lo=float(prod_end.min()), hi=float(prod_end.max())))
    return out


def main() -> None:
    r = ring()
    area = area_km2(r)
    st = steps()
    end = st[-1]
    depth = lambda km3: km3 * 1e9 / (area * 1e6)             # m
    yrs = end["km3"] / RENEWABLE
    print(f"Tehran (OSM 6663864): {len(r)} points, area {area:.1f} km2 (sphere R {R_KM} km)")
    print(f"end window {end['label']}: {end['km3']:.1f} km3 lost (products {end['lo']:.1f} to {end['hi']:.1f})")
    print(f"depth over Tehran: {depth(end['km3']):.0f} m (range {depth(end['lo']):.0f} to {depth(end['hi']):.0f}); "
          f"Milad Tower {MILAD['tip_m']:.0f} m")
    print(f"years of Iran's renewable water ({RENEWABLE} km3/yr): {yrs:.2f} "
          f"(range {end['lo'] / RENEWABLE:.2f} to {end['hi'] / RENEWABLE:.2f})")
    print("steps (label, km3, depth m):")
    for s in st:
        print(f"    {s['label']:>14}  {s['km3']:6.1f}  {depth(s['km3']):5.0f}")
    cross = next(s for s in st if depth(s["km3"]) > MILAD["tip_m"])
    print(f"the layer first stands above Milad's tip in {cross['label']} ({depth(cross['km3']):.0f} m)")
    for k, (lo, hi) in EXPECT.items():
        v = {"end_km3": end["km3"], "lo_km3": end["lo"], "hi_km3": end["hi"], "area_km2": area,
             "years_renewable": yrs}[k]
        assert lo <= v <= hi, (k, v, (lo, hi))
    assert depth(end["lo"]) > MILAD["tip_m"], "above Milad Tower even at the products' lowest"
    shown_km3 = int(round(end["km3"] / 10) * 10)              # the counter lands on a round ten
    shown_m = int(round(depth(end["km3"]) / 10) * 10)
    t_step = (LAND - RISE) / (len(st) - 1)
    timeline = dict(duration=DURATION, fps=FPS, hold=HOLD, drain=DRAIN, rise=RISE, land=LAND, beats=list(BEATS),
                    t_step=t_step, area_km2=area, milad=MILAD, steps=[dict(s, depth_m=depth(s["km3"])) for s in st],
                    shown_km3=shown_km3, shown_m=shown_m, years_renewable=yrs, camera=CAMERA, cross=cross["label"],
                    bbox=[51.00, 35.35, 51.85, 36.10])
    (DATA / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1))
    print(f"on screen: {shown_km3} billion m3, {shown_m} m; a step every {t_step:.3f} s")
    print("saved", DATA / "timeline.json")


if __name__ == "__main__":
    main()
