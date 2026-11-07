"""HAMOUN, MORE THAN FIVE TEHRANS: the numbers, the pictures and the clock of the 3D reel «هامون بیش از پنج برابرِ
تهران بود؛ بهارِ امسال، حدودِ یک تهران».

The numbers: the open water of the Hamoun lakes in spring (Landsat path 157, 1 May - 15 June, widened to 15 April -
20 June where needed: every counted pass lies between 26 Farvardin and 31 Khordad), every year 1987-2026 (1366-1405),
from src/hamoun.py (rule MNDWI > 0 and SWIR1 < 0.15, calibrated against JRC's Monthly Water History;
data/hamoun/area_spring.csv). The lakes = JRC's extent of any water 1984-2021, its main body, 4,267 km2, on both
sides of the border together (the reel says «در دو سوی مرز»). "The full lake" is the class of springs within 5 % of
the wettest (1991, 1992, 1993, 1998: 4,071-4,184 km2; JRC's own count of the same passes 3,802-4,042): on screen
"about 4,000 km2". For scale: the city of Tehran (22 districts), 630.7 km2 (OpenStreetMap relation 6663864, the
area on a sphere, src/tehranwater.py; the municipality's figure 615.6 km2; Persian sources often quote about 730,
Wikipedia 750): the full lake is more than five of it on every one of these figures and on JRC's count (the reel
says «بیش از پنج برابر»), and spring 2026 about one (0.74-0.91).

The pictures: each year's true colour (hamoun.colour, one fixed stretch for every year, hamoun.display) and its water
share per pixel inside the lakes (hamoun.water_map, the median over the year's counted passes), on hamoun.py's
picture grid (about 143 m). Years whose picture is not clean (hamoun.NO_PICTURE: Landsat 7 stripes, clouds, black
spots, a ghost of two floods, a blend of two shorelines) keep their measured area on the counter and in the bars;
the picture holds the last clean year, veiled and without its water outline, with a note. A spring without a number the
method check trusts (GAPS: 2002, whose only pass in the default window, 13 June, saw 0 km2 while April's two saw
the flood pulse) shows no number and no bar; the bars start at 1987 (1366: 1985 and 1986 have no usable scene).
The picture of a held spring lies under a veil (60 %) so it is not read as that spring.

The clock: 26 s at 30 frames a second, set by the narration's seven lines (onebit_score_hamoun). The end state at
0 s (spring 1405 with the city of Tehran drawn to scale beside its water, the shore of the full lake of spring 1371
as a line, the hook, the counter at 1405's value); a rewind (1.6-2.8 s); run A, 1366-1372, one spring every
0.25 s, landing on the hero frame 1372 (1993) at 4.3 s, which holds to 5.9 s with Tehran drawn to scale on it (card
C1, then from 5.9 s «in the wet springs, about 4,000 km2»); run A2, 1373-1377, every 0.28 s; from 7.5 s (1379's
zero) the card «then it rose and fell; at times nearly without water»; run B, 1378-1395, every 0.23 s; run C, the last ten springs 1396-1405, every
0.5 s (11.45-15.95 s, card C2: five of them under 100 km2 in late spring); then 1405 holds: the seasonal floods
(16.0 s), card C3 «about one Tehran» with the outline (20.3 s), the question C4 (23.85 s); the camera returns to its
first frame at 26 s.

    data/hamoun/reel/timeline.json             steps, cards, camera keys, outlines and every number
    data/hamoun/reel/tex_<year>.jpg            the year's true colour (8-bit, the fixed stretch)
    data/hamoun/reel/water_<year>.png          the year's water share inside the lakes (0-255)
    data/hamoun/reel/outlines.json             each clean spring's water outline (share 0.5, lon/lat)
    data/hamoun/reel/lakes.png                 the lakes' mask on the picture grid
    python -I src/hamounreel.py > outputs/hamounreel_log.txt
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import get_hamoun as gh  # noqa: E402
import hamoun  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "hamoun"
OUT = DATA / "reel"
TEHRAN = ROOT / "data" / "tehranwater"
FIRST, LAST = 1987, 2026
FULL_YEAR = 1992                                  # the wettest spring: its shore is the line of "the full lake"
TEHRAN_OFFICIAL = 615.6                           # km2: the municipality's figure for the 22 districts
DURATION, FPS = 26.0, 30
REWIND, RUN_A = 1.6, 2.8                          # s: the rewind starts; run A's first spring (1987)
RUNS = (("A", 1987, 1993, 2.8, 0.25), ("A2", 1994, 1998, 5.9, 0.28), ("B", 1999, 2016, 7.3, 0.23),
        ("C", 2017, 2026, 11.45, 0.50))
GAPS = {2002: "its only pass in the default window (13 June) saw 0 km2, April's two (18 and 26 April) the flood "
              "pulse (182 and 308): no late-spring number"}
EMPTY = {1985: "no Landsat scene of the lakes after 26 March", 1986: "no clear pass"}      # slots in the bars
HERO = 1993                                       # the full lake's frame (the method check: 1993, 1992, 1998, 1991)
CARDS = ((0.0, "hook"), (4.3, "c1"), (5.9, "c1b"), (7.5, "low"), (11.45, "c2"), (16.0, "flood"), (20.3, "c3"),
         (23.85, "c4"))
TEHRAN_SHOWN = ((0.0, 1.9), (4.4, 5.9), (20.3, 26.0))   # s: when the outline of Tehran is on the ground
NEARLY_DRY = 100                                  # km2
EXPECT = dict(full_lo=(4000, 4100), full_hi=(4150, 4220), y2026=(540, 580), tehran=(620, 640),
              times_tehran=(6.0, 7.0), dry_last10=(5, 5), measured_last10=(10, 10))
TEHRAN_QUOTED = (615.6, 630.7, 730.0, 750.0)      # km2: municipality, OSM, Persian press, Wikipedia
PLACES = dict(zabol=(61.4986, 31.0287), khwaja=(61.2458, 30.9476),    # Zabol city centre; Kuh-e Khwaja's top (DEM)
              chahnimeh=(61.620, 30.790))                            # Chah-nimeh reservoirs, west lobe (not lakes)
TEHRAN_AT = (61.695, 31.424)                      # the city of Tehran drawn to scale (its centroid): on the full lake
                                                  # of 1371 (Sabari-Puzak), beside the water of 1405
# the camera: (time s, point looked at in km from the picture's south-west corner, azimuth of the view in degrees
# from north, elevation of the view in degrees below the horizontal, distance km). Frame 0 looks north at 1405's
# water with Tehran beside it; for the full lake the camera swings round to look east (the lakes' long axis across
# the screen), and swings back during the last ten springs; hamoun3d interpolates these numbers (a closed path).
VIEWS = ((0.0, (80.0, 130.0), 0.0, 68.0, 185.0),
         (1.6, (80.0, 128.0), 8.0, 67.0, 192.0),
         (4.3, (96.0, 110.0), 90.0, 62.0, 230.0),
         (5.9, (95.0, 109.0), 92.0, 62.0, 226.0),
         (11.45, (93.0, 110.0), 82.0, 63.0, 232.0),
         (16.0, (80.0, 127.0), 14.0, 67.0, 195.0),
         (20.3, (80.0, 129.0), 3.0, 68.0, 188.0),
         (26.0, (80.0, 130.0), 0.0, 68.0, 185.0))


def solar(y: int) -> int:
    """The Persian solar year of spring (15 April - 20 June) of Gregorian year y."""
    return y - 621


def areas() -> pd.Series:
    a = pd.read_csv(DATA / "area_spring.csv", index_col="year")[hamoun.RULE]
    return a.loc[FIRST:LAST]


def views() -> list:
    return [[t, fx, fy, az, el, dist] for t, (fx, fy), az, el, dist in VIEWS]


def contour_lines(share: np.ndarray, level: float = 0.5, min_pts: int = 40) -> list:
    """The shore at a water share, as lon/lat polylines (the picture grid's pixel centres), small pieces left out."""
    import contourpy
    from scipy import ndimage
    z = ndimage.gaussian_filter(np.nan_to_num(share, nan=0.0), 1.0)
    lines = contourpy.contour_generator(z=z).lines(level)
    t = gh.PIC_T
    out = []
    for ln in lines:
        if len(ln) < min_pts:
            continue
        cols, rows = ln[:, 0], ln[:, 1]
        lon = t.c + (cols + 0.5) * t.a
        lat = t.f + (rows + 0.5) * t.e
        out.append(np.round(np.c_[lon, lat][::2], 5).tolist())
    return out


def tehran_shape() -> tuple:
    """The city of Tehran's outline moved to TEHRAN_AT at true size (km offsets from its centroid, on a sphere's
    local scale at each latitude), and its area from tehranwater's timeline."""
    d = json.loads((TEHRAN / "tehran_osm.json").read_text())
    ring = np.array((d if isinstance(d, list) else [d])[0]["geojson"]["coordinates"][0])
    lat0 = ring[:, 1].mean()
    kx0, ky = 111.32 * math.cos(math.radians(lat0)), 110.574
    x, y = (ring[:, 0] - ring[:, 0].mean()) * kx0, (ring[:, 1] - lat0) * ky
    kx1 = 111.32 * math.cos(math.radians(TEHRAN_AT[1]))
    lon, lat = TEHRAN_AT[0] + x / kx1, TEHRAN_AT[1] + y / ky
    area = json.loads((TEHRAN / "timeline.json").read_text())["area_km2"]
    return np.round(np.c_[lon, lat], 5).tolist(), area


def on_water(poly: list, year: int) -> float:
    """The share of the outline's area on the year's water (pixels with water share >= 0.5)."""
    from matplotlib.path import Path as MPath
    t = gh.PIC_T
    yy, xx = np.mgrid[0:gh.PIC_SHAPE[0], 0:gh.PIC_SHAPE[1]]
    lon, lat = t.c + (xx + 0.5) * t.a, t.f + (yy + 0.5) * t.e
    inside = MPath(np.array(poly)).contains_points(np.c_[lon.ravel(), lat.ravel()]).reshape(lon.shape)
    w = np.nan_to_num(np.where(hamoun.lakes(), hamoun.water_map(year), 0.0)) >= 0.5
    return float(w[inside].mean())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    a = areas()
    pics = set(hamoun.years())
    assert list(a.index) == list(range(FIRST, LAST + 1)), "every spring 1987-2026 has an area"
    full = a[a >= 0.95 * a.max()]
    lk = hamoun.lakes_km2()
    poly, tehran_km2 = tehran_shape()
    last10 = a.loc[LAST - 9:LAST]
    dry10 = sorted(int(y) for y in last10[last10 < NEARLY_DRY].index)
    df = hamoun.passes()
    used = df[df.counts & (df.year >= FIRST)]
    md = used.date.str[5:]
    print(__doc__.split("\n\n")[0].replace("\n", " "))
    print(f"\nthe lakes: {lk['total']:,.0f} km2 (by the Natural Earth border: {lk['iran']:,.0f} and {lk['afghanistan']:,.0f})")
    print(f"counted passes {FIRST}-{LAST}: {len(used)}, dated {md.min()} to {md.max()} (spring: 26 Farvardin = 15 April "
          f"to 31 Khordad = 20/21 June)")
    assert md.min() >= "04-15" and md.max() <= "06-20", "every counted pass in the Persian spring"
    print(f"the full lake (within 5 % of the wettest): " + ", ".join(f"{y} {v:,.0f}" for y, v in full.items()))
    for name, ar in (("OSM", tehran_km2), ("municipality", TEHRAN_OFFICIAL)):
        print(f"the city of Tehran ({name}) {ar:.1f} km2: the full lake {full.min() / ar:.2f} to {full.max() / ar:.2f} "
              f"Tehrans (JRC's count 3,802-4,042: {3802 / ar:.2f} to {4042 / ar:.2f}); 2026 {a.loc[2026] / ar:.2f}")
    print(f"2026: {a.loc[2026]:,.0f} km2 = {100 * a.loc[2026] / a.max():.1f} % of {a.idxmax()} "
          f"({100 * a.loc[2026] / full.min():.1f} % of {full.idxmin()}; one seventh = 14.3 %)")
    print(f"the last 10 springs ({LAST - 9}-{LAST}): {len(last10)} measured, {len(dry10)} under {NEARLY_DRY} km2: {dry10}")
    for k, (lo, hi) in EXPECT.items():
        v = {"full_lo": full.min(), "full_hi": full.max(), "y2026": a.loc[2026], "tehran": tehran_km2,
             "times_tehran": full.min() / tehran_km2, "dry_last10": len(dry10), "measured_last10": len(last10)}[k]
        assert lo <= v <= hi, (k, v, (lo, hi))
    for ar in TEHRAN_QUOTED:
        print(f"  Tehran at {ar:.1f} km2: the full lake {full.min() / ar:.2f}-{full.max() / ar:.2f}, JRC's count "
              f"{3802 / ar:.2f}-{4042 / ar:.2f}; 2026 {a.loc[2026] / ar:.2f}")
    assert min(full.min(), 3802) / max(TEHRAN_QUOTED) > 5.0, "more than five Tehrans on every figure"
    assert 0.7 <= a.loc[2026] / max(TEHRAN_QUOTED) and a.loc[2026] / min(TEHRAN_QUOTED) <= 1.1, "about one Tehran"
    assert 0.12 <= a.loc[2026] / full.min() <= 0.16, "about one seventh of the full lake"

    for y in sorted(pics):                                       # the pictures and the water
        tex, wat = OUT / f"tex_{y}.jpg", OUT / f"water_{y}.png"
        if tex.exists() and wat.exists() and "--pictures" not in sys.argv:
            continue
        Image.fromarray(hamoun.display(hamoun.colour(y)["rgb"])).save(tex, quality=94)
        share = np.where(hamoun.lakes(), hamoun.water_map(y), 0.0)
        Image.fromarray((255 * np.clip(np.nan_to_num(share), 0, 1)).astype(np.uint8)).save(wat)
        print(f"  picture {y}: saved {tex.name}, {wat.name}", flush=True)
    shore = contour_lines(np.where(hamoun.lakes(), hamoun.water_map(FULL_YEAR), 0.0))
    Image.fromarray((255 * hamoun.lakes()).astype(np.uint8)).save(OUT / "lakes.png")   # the lakes' mask, for 3D
    outlines = {}                                                # each clean spring's measured water, its outline
    for y in sorted(pics):
        share = np.asarray(Image.open(OUT / f"water_{y}.png"), np.float32) / 255.0
        outlines[str(y)] = contour_lines(share, 0.5, min_pts=12)
    (OUT / "outlines.json").write_text(json.dumps(outlines))
    print(f"water outlines (share 0.5) of {len(outlines)} springs: "
          f"{sum(len(p) for v in outlines.values() for p in v):,} points")
    print(f"the shore of {FULL_YEAR} (water share 0.5): {len(shore)} lines, {sum(len(s) for s in shore)} points")
    print(f"the outline of Tehran at {TEHRAN_AT}: {100 * on_water(poly, FULL_YEAR):.0f} % on the water of {FULL_YEAR}, "
          f"{100 * on_water(poly, HERO):.0f} % on {HERO}'s (the hero), {100 * on_water(poly, LAST):.0f} % on {LAST}'s")

    runs = []
    print("\nruns (Gregorian, solar, km2, on screen, picture, shown at s):")
    for name, y0, y1, t0, dt in RUNS:
        steps = []
        for k, y in enumerate(range(y0, y1 + 1)):
            gap = y in GAPS
            steps.append(dict(year=y, label=str(solar(y)), km2=None if gap else float(a.loc[y]), picture=y in pics,
                              t=round(t0 + k * dt, 3), gap=gap,
                              shown=None if gap else (int(round(a.loc[y] / 10) * 10) if a.loc[y] >= 100 else int(round(a.loc[y])))))
            s = steps[-1]
            print(f"  {name:2s} {y}  {s['label']}  {'GAP' if gap else format(s['km2'], '7.1f'):>7}  "
                  f"{'-' if gap else s['shown']:>5}  {'picture' if s['picture'] else 'NO PICTURE (held, dimmed)':26s} {s['t']:6.2f}")
        runs.append(dict(name=name, t0=t0, dt=dt, steps=steps))
    for r0, r1 in zip(runs, runs[1:]):
        assert r0["steps"][-1]["t"] < r1["t0"], (r0["name"], r1["name"])
    land = runs[-1]["steps"][-1]["t"]
    print(f"1405 lands at {land:.2f} s and holds to {DURATION:.0f} s")
    timeline = dict(duration=DURATION, fps=FPS, rewind=REWIND, run_a=RUN_A, runs=runs, land=land, cards=CARDS,
                    tehran_shown=TEHRAN_SHOWN, first=FIRST, last=LAST,
                    bars=[dict(year=y, label=str(solar(y)), km2=None if y in GAPS else float(a.loc[y]))
                          for y in range(FIRST, LAST + 1)], gaps={str(k): v for k, v in GAPS.items()},
                    empty={str(k): v for k, v in EMPTY.items()}, hero=HERO,
                    pictures=sorted(pics), no_picture={str(k): v for k, v in hamoun.NO_PICTURE.items() if FIRST <= k <= LAST},
                    full_year=FULL_YEAR, full_years=[int(y) for y in full.index], full_lo=float(full.min()),
                    full_hi=float(full.max()), full_shown=4000, tehran_km2=tehran_km2, tehran_official=TEHRAN_OFFICIAL,
                    shown_2026=int(round(a.loc[2026] / 10) * 10), pct_2026=float(100 * a.loc[2026] / a.max()),
                    dry_last10=dry10, nearly_dry=NEARLY_DRY, lakes_km2=lk, shore=shore, tehran=poly,
                    tehran_at=TEHRAN_AT, places=PLACES, views=views(),
                    pic_transform=list(tuple(gh.PIC_T)[:6]), pic_shape=list(gh.PIC_SHAPE))
    (OUT / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1))
    print("saved", OUT / "timeline.json")


if __name__ == "__main__":
    main()
