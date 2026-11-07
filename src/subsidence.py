"""SINKING GROUND: the numbers and the clock of the reel «زیرِ پای کدام شهرها زمین پایین می‌رود؟».

The data: the vertical land-subsidence rate 2014-2020 over Iran from Sentinel-1 radar (Haghshenas Haghighi & Motagh
2024, Science Advances; 100 m; cm/yr, positive = down; only the pixels inside the authors' subsidence mask carry a
value), checked against the independent product of Payne et al. 2025 (JGR Solid Earth; Oct 2014 - Dec 2022, ascending
+ descending, mm/yr, negative = down). Inputs: src/get_subsidence.py (data/subsidence/).

On screen:
    the subsiding area        all of A's subsidence mask (the paper: "approximately 56,000 km2 (3.5%)"), on a sphere
    > 4x Tehran province      Tehran province 13,640 km2 (Statistical Yearbook of Iran 1395, table 1-4; not the
                              18,814 km2 of Tehran + Alborz)
    Karaj and SW Tehran:      the fastest ground: the maximum of the pixels sinking >= 1 cm/yr in the city of Karaj
    up to 15-20 cm/yr         (OSM) and in the six counties of the SW Tehran plain (geoBoundaries), in A and in B (like
                              for like): 14.8 to 20.3, so «up to 15 to 20»; the 95th percentiles are logged too
The labels: each sits on the rate-weighted centre of the pixels sinking >= 5 cm/yr within a radius of its town.

The clock: 26 s at 30 frames a second. Frame 0 = the end state (Iran with every subsiding pixel glowing, the hook, the
counter «؟»); the counter counts the area up (1.2-7.8 s) while the labels appear; the number lands at 7.8 s; the
camera dives to the Tehran-Karaj plain (8.6-13.0 s), the second number at 13.0 s, the cause at 17.6 s, out again,
the question at 23.4 s; the camera's path returns to frame 0 at 26 s (a loop).

    data/subsidence/timeline.json    every number, the labels and the camera for subsidence3d.py and the film
    python -I src/subsidence.py > outputs/subsidence_log.txt
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio import features, windows

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "subsidence"
R_KM = 6371.0088
TEHRAN_PROVINCE = 13640.0                                   # km2, Statistical Yearbook 1395, table 1-4
SW_TEHRAN = ("Shahriar", "Malard", "Qods", "Robatkarim", "Islamshahr", "Baharestan")
LON0, LAT0 = 53.5, 32.5                                     # the scene's origin (sinusoidal projection, km)
KARAJ_BOX = (50.20, 35.00, 51.90, 36.60)                    # the fine patch (get_subsidence.py)
IRAN_BOX, IRAN_STEP = (40.0, 22.0, 67.0, 44.0), 0.02
DURATION, FPS = 26.0, 30
COUNT, LAND, DIVE, CLOSE, BACK = 1.2, 7.8, 8.6, 13.0, 20.5   # s
BEATS = (7.8, 13.0, 17.6, 23.4)                             # s: area, Karaj, cause, question
EXPECT = dict(area_km2=(55500, 56500), gt10_km2=(2900, 3100), times_province=(4.0, 4.2),
              karaj_A_p95=(17, 19.5), karaj_A_max=(19.5, 21.5), karaj_B_p95=(14, 16.5), karaj_B_max=(16, 18),
              sw_A_p95=(13.5, 15.5), sw_A_max=(17.5, 19.5), sw_B_p95=(10.5, 12.5), sw_B_max=(14, 16))
# the national labels: (text, seed lon, lat, search radius km, side of the label: +1 right, -1 left, dy px)
NATIONAL = [("کرج و جنوب‌غربِ تهران", 51.05, 35.72, 30, -1, -26),
            ("دشتِ قم", 50.75, 34.75, 45, -1, 22),
            ("گنبدِ کاووس", 55.10, 37.25, 45, 1, -48),
            ("مشهد", 59.45, 36.40, 20, 1, -36),
            ("نیشابور", 58.80, 36.21, 30, -1, 30),
            ("اصفهان", 51.67, 32.65, 35, -1, 0),
            ("دشتِ بهرمان (رفسنجان)", 55.65, 30.87, 25, -1, -10),
            ("کرمان", 57.05, 30.28, 20, 1, 12),
            ("مرودشت", 52.80, 29.90, 35, -1, 10)]
# the local labels on the Tehran-Karaj plain: town centres (OpenStreetMap), (text, lon, lat)
LOCAL = [("کرج", 50.9905, 35.8225), ("شهریار", 51.0590, 35.6593), ("اسلامشهر", 51.2350, 35.5450),
         ("ملارد", 50.9760, 35.6660), ("تهران", 51.3896, 35.6893), ("هشتگرد", 50.6830, 35.9620)]
# the camera: (t s, focal lon, lat, km above sea; distance km; azimuth of the camera from the focal point (deg,
# compass: 180 = south of it); elevation (deg)); log-distance and the angles are interpolated (cubic Hermite)
CAMERA = [(0.0, 53.6, 32.0, 0.0, 5500.0, 180.0, 66.0),
          (COUNT, 53.6, 32.0, 0.0, 5450.0, 180.0, 66.0),
          (LAND, 53.5, 32.2, 0.0, 5000.0, 181.0, 64.0),
          (DIVE, 53.4, 32.3, 0.0, 4900.0, 181.0, 64.0),
          (11.6, 51.24, 35.55, 1.10, 320.0, 170.0, 72.0),
          (CLOSE, 51.25, 35.575, 1.10, 120.0, 170.0, 42.0),
          (17.6, 51.23, 35.585, 1.10, 112.0, 178.0, 40.0),
          (BACK, 51.21, 35.595, 1.10, 120.0, 186.0, 42.0),
          (DURATION, 53.6, 32.0, 0.0, 5500.0, 180.0, 66.0)]


def xy(lon, lat):
    """The scene's km: a sinusoidal projection about (LON0, LAT0)."""
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    return (lon - LON0) * 111.32 * np.cos(np.radians(lat)), (lat - LAT0) * 110.574


def pixel_km2(transform, rows) -> np.ndarray:
    """The area (km2) of one pixel in each row (a sphere)."""
    dx = math.radians(abs(transform.a))
    top = transform.f + np.asarray(rows) * transform.e
    return R_KM ** 2 * dx * np.abs(np.sin(np.radians(top)) - np.sin(np.radians(top + transform.e)))


def national(src) -> dict:
    """The subsiding area (all of the mask) and the area above 10 cm/yr, read in blocks of rows."""
    tot = gt1 = gt10 = 0.0
    vmax = 0.0
    for r0 in range(0, src.height, 1024):
        h = min(1024, src.height - r0)
        a = src.read(1, window=windows.Window(0, r0, src.width, h))
        pa = pixel_km2(src.transform, np.arange(r0, r0 + h))
        m = (a != src.nodata) & np.isfinite(a)
        tot += float((m.sum(axis=1) * pa).sum())
        gt1 += float(((m & (a >= 1)).sum(axis=1) * pa).sum())
        gt10 += float(((m & (a > 10)).sum(axis=1) * pa).sum())
        if m.any():
            vmax = max(vmax, float(a[m].max()))
    return dict(area_km2=tot, gt1_km2=gt1, gt10_km2=gt10, max_cm=vmax)


def region(path: Path, geoms, scale: float, nodata=None) -> dict:
    """p95 and max (cm/yr down) of the pixels sinking >= 1 cm/yr inside the geometries; scale turns the file's unit
    into cm/yr down (A: 1; B: -0.1, mm/yr up)."""
    with rasterio.open(path) as src:
        xs, ys = [], []
        for g in geoms:
            c = np.concatenate([np.asarray(r)[:, :2] for poly in (g["coordinates"] if g["type"] == "MultiPolygon"
                                                                   else [g["coordinates"]]) for r in poly])
            xs += [c[:, 0].min(), c[:, 0].max()]
            ys += [c[:, 1].min(), c[:, 1].max()]
        win = windows.from_bounds(min(xs), min(ys), max(xs), max(ys), src.transform).round_offsets().round_lengths()
        a = src.read(1, window=win, boundless=True, fill_value=np.nan).astype(float)
        nd = src.nodata if nodata is None else nodata
        if nd is not None:
            a[a == nd] = np.nan
        inside = features.geometry_mask(geoms, out_shape=a.shape, transform=src.window_transform(win), invert=True)
    v = a[inside & np.isfinite(a)] * scale
    v = v[v >= 1.0]
    return dict(n=int(v.size), p95=float(np.percentile(v, 95)), max=float(v.max()), median=float(np.median(v)))


def anchor(src, lon, lat, r_km) -> tuple:
    """The rate-weighted centre of the pixels sinking >= 5 cm/yr within r_km of (lon, lat), and their peak."""
    dlat, dlon = r_km / 110.574, r_km / (111.32 * math.cos(math.radians(lat)))
    win = windows.from_bounds(lon - dlon, lat - dlat, lon + dlon, lat + dlat, src.transform).round_offsets().round_lengths()
    a = src.read(1, window=win).astype(float)
    tr = src.window_transform(win)
    rows, cols = np.indices(a.shape)
    plon = tr.c + (cols + 0.5) * tr.a
    plat = tr.f + (rows + 0.5) * tr.e
    near = ((plon - lon) / dlon) ** 2 + ((plat - lat) / dlat) ** 2 <= 1
    m = near & (a != src.nodata) & (a >= 5)
    assert m.sum() > 20, ("no fast pixels near", lon, lat)
    w = a[m]
    return float((plon[m] * w).sum() / w.sum()), float((plat[m] * w).sum() / w.sum()), float(w.max()), int(m.sum())


def main() -> None:
    A = DATA / "rate_A.tif"
    with rasterio.open(A) as src:
        assert src.tags().get("UNITS") == "cm/year" and src.nodata == -999.0
        nat = national(src)
        labels = []
        for text, lon, lat, r, side, dy in NATIONAL:
            alon, alat, peak, n = anchor(src, lon, lat, r)
            labels.append(dict(text=text, lon=round(alon, 4), lat=round(alat, 4), side=side, dy=dy))
            print(f"label {text:>24}: centre {alon:.3f} E {alat:.3f} N, {n} pixels >= 5 cm/yr, peak {peak:.1f} cm/yr")
    print(f"national (A, 2014-2020): subsiding {nat['area_km2']:.0f} km2; >= 1 cm/yr {nat['gt1_km2']:.0f}; "
          f"> 10 cm/yr {nat['gt10_km2']:.0f}; max {nat['max_cm']:.1f} cm/yr")
    times = nat["area_km2"] / TEHRAN_PROVINCE
    print(f"{nat['area_km2']:.0f} / {TEHRAN_PROVINCE:.0f} km2 (Tehran province) = {times:.2f}")
    karaj = json.loads((DATA / "osm_karaj.json").read_text())[0]["geojson"]
    adm2 = json.loads((DATA / "geob_adm2.geojson").read_text())["features"]
    sw = [f["geometry"] for f in adm2 if f["properties"]["shapeName"] in SW_TEHRAN]
    assert len({f["properties"]["shapeName"] for f in adm2 if f["properties"]["shapeName"] in SW_TEHRAN}) == 6
    B = DATA / "payne" / "Qazvin_Western_Tehran_Plain_Zarand_Saveh_vU.geo.tif"
    st = {}
    for name, geoms in (("karaj", [karaj]), ("sw", sw)):
        st[name + "_A"] = region(A, geoms, 1.0)
        st[name + "_B"] = region(B, geoms, -0.1)
        for k in ("A", "B"):
            s = st[f"{name}_{k}"]
            print(f"{name:>5} {k}: {s['n']} pixels >= 1 cm/yr, median {s['median']:.1f}, p95 {s['p95']:.1f}, "
                  f"max {s['max']:.1f} cm/yr")
    peaks = [st[k]["max"] for k in st]                      # the fastest ground of each region in each product
    lo, hi = min(peaks), max(peaks)
    print(f"Karaj and the SW Tehran plain, the fastest ground (max of A and B in each): {lo:.1f} to {hi:.1f} cm/yr "
          f"-> on screen «up to 15 to 20»")
    v = dict(area_km2=nat["area_km2"], gt10_km2=nat["gt10_km2"], times_province=times,
             karaj_A_p95=st["karaj_A"]["p95"], karaj_A_max=st["karaj_A"]["max"], karaj_B_p95=st["karaj_B"]["p95"],
             karaj_B_max=st["karaj_B"]["max"], sw_A_p95=st["sw_A"]["p95"], sw_A_max=st["sw_A"]["max"],
             sw_B_p95=st["sw_B"]["p95"], sw_B_max=st["sw_B"]["max"])
    for k, (a, b) in EXPECT.items():
        assert a <= v[k] <= b, (k, v[k], (a, b))
    assert 14.5 <= lo <= 15.5 and 19.5 <= hi <= 20.5, "up to 15 to 20 holds: every peak rounds into it"
    shown_area = int(round(nat["area_km2"] / 1000) * 1000)    # the counter lands on a round thousand
    assert shown_area == 56000
    cam = []
    for t, lon, lat, z, dist, az, el in CAMERA:
        x, y = xy(lon, lat)
        cam.append(dict(t=t, focal=[float(x), float(y), z], dist=dist, az=az, el=el))
    for lab in labels:
        lab["x"], lab["y"] = (float(c) for c in xy(lab["lon"], lab["lat"]))
    local = []
    for text, lon, lat in LOCAL:
        x, y = xy(lon, lat)
        local.append(dict(text=text, lon=lon, lat=lat, x=float(x), y=float(y)))
    timeline = dict(duration=DURATION, fps=FPS, count=COUNT, land=LAND, dive=DIVE, close=CLOSE, back=BACK,
                    beats=list(BEATS), lon0=LON0, lat0=LAT0, karaj_box=KARAJ_BOX, iran_box=IRAN_BOX,
                    iran_step=IRAN_STEP, area_km2=nat["area_km2"], shown_area=shown_area, times_province=times,
                    gt10_km2=nat["gt10_km2"], shown_range=[15, 20], stats=st, labels=labels, local=local, camera=cam)
    (DATA / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1))
    print(f"on screen: {shown_area} km2 ({times:.1f}x Tehran province); Karaj and SW Tehran 15 to 20 cm/yr")
    print("saved", DATA / "timeline.json")


if __name__ == "__main__":
    main()
