"""The data of the Hormuz NO2 film: tropospheric NO2 over the Persian Gulf, the Strait of Hormuz and the Gulf of Oman
from the Sentinel-5P OFFL orbits that get_hormuz.py caches, and what the film says with it.

The comparison. Ship traffic through the Strait of Hormuz collapsed on 1 March 2026 (IMF PortWatch); a memorandum
followed on 17 June. The film sets the days 1 March to 17 June 2026 against the same days of 2025: the mean NO2 of
six ports and industrial centres inside the Persian Gulf (boxes of +-0.2 degree) against three places on the Gulf of
Oman, outside the strait, which the closure did not shut in. Beside it: the same change in every part of the year
(before, during, after), the two months before the event (what the two years, and the two processor versions,
differ by on their own), and the same window of 2023 and 2024 (what a normal year does). film() asserts every
sentence of the film against these numbers. The share of ships cannot be separated from ports, oil and gas, and
the film says so; a measure of the shipping lane against the sea around it was tried and dropped (it held only in
the Gulf of Oman, and only in March and April).

Fields: every valid pixel (qa_value >= 0.75) is spread over its footprint on the 0.025-degree grid GRID. The four
corners of a pixel are rebuilt from the pixel centres (the rule of air_grid.corners: the mean of the 2 x 2 centres
around each corner; checked there against the file's own bounds, median about 5 m). Each pixel gets SUB x SUB
sub-points in its footprint, each deposits 1/SUB^2 of the pixel's weight and NO2 in its cell; overlapping orbits add
up, so a cell holds the area-weighted mean of every pixel that covered it. Per calendar month or per part of the year
(PARTS): data/hormuz/fields/<key>.npz with the sums S and the weights W, in 1e15 molecules per cm2.

    python -I src/hormuz.py fields 2026-j01 2025-j01    # single parts (or calendar months: 2026-04)
    python -I src/hormuz.py fields 2025 2026            # the calendar months March to November of these years
    python -I src/hormuz.py film                        # the film's numbers, pictures and words: outputs/onebit/hormuz/
    python -I src/hormuz.py draft                       # the same without the checks that need the winter and 2023-24
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import get_hormuz  # noqa: E402

DATA = get_hormuz.DATA
FIELDS = DATA / "fields"
GRID = dict(lon0=47.0, lat0=31.0, step=0.025, nx=580, ny=380)     # lat0: the north edge of row 0
MONTHS = (3, 4, 5, 6, 7, 8, 9, 10, 11)                           # the window of a year
LAST_DAY = {11: 7}                                               # month -> last day used (every year alike)
FIRST_DAY = {8: 12}                                              # month -> first day used: the archive has no OFFL orbit of
                                                                 # 3 July to 11 August 2025, so August starts on its 12th day
                                                                 # in every year (and July is not among the common months)
# The parts of the year the film compares, as the Persian months that the viewer knows (first and last day, month-day).
# The cuts follow the calendar of events, not the data: 1 March 2026 (10 Esfand 1404) is the first day of the collapse
# of the ship count, 17 June 2026 (27 Khordad 1405) the day of the memorandum. Tir and Mordad are short: the archive
# holds no OFFL orbit of 3 July to 11 August 2025, so both years are cut to the days that 2025 has.
PARTS = {"j10": ("01-01", "01-20"), "j11": ("01-21", "02-28"),      # Dey (from its 11th day); Bahman with Esfand's first nine days
         "j12": ("03-01", "03-20"), "j01": ("03-21", "04-20"), "j02": ("04-21", "05-21"), "j03": ("05-22", "06-17"),
         "j04": ("06-18", "07-02"), "j05": ("08-12", "08-22"), "j06": ("08-23", "09-22"), "j07": ("09-23", "10-22"),
         "j08": ("10-23", "11-07")}
BEFORE = ("j10", "j11")                                          # 1 January to 28 February: before the event
CLOSURE = ("j12", "j01", "j02", "j03")                           # 1 March to 17 June
AFTER = ("j04", "j05", "j06", "j07", "j08")                      # 18 June to 7 November
SUB = 4                                                          # sub-points per pixel side
K = 6.02214e19 / 1e15                                            # mol m-2 -> 1e15 molecules cm-2


def window(year: int, months=MONTHS) -> list:
    return [f"{year}-{m:02d}" for m in months]


def closure(year: int) -> list:
    return [f"{year}-{k}" for k in CLOSURE]


def span(key: str) -> tuple:
    """(first day, last day) of a field's key, as dates: a calendar month ("2026-04") or a part ("2026-j01")."""
    y, tag = int(key[:4]), key[5:]
    if tag in PARTS:
        a, b = PARTS[tag]
        return f"{y}-{a}", f"{y}-{b}"
    m = int(tag)
    return f"{y}-{m:02d}-{FIRST_DAY.get(m, 1):02d}", f"{y}-{m:02d}-{LAST_DAY.get(m, 31):02d}"


def corners(a: np.ndarray) -> np.ndarray:
    """Pixel corners, shape (rows + 1, cols + 1): the mean of the 2 x 2 centres around each corner (edges
    extrapolated). The same rule as air_grid.corners."""
    ap = np.pad(a, 1, mode="edge")
    ap[0, :] = 2 * ap[1, :] - ap[2, :]
    ap[-1, :] = 2 * ap[-2, :] - ap[-3, :]
    ap[:, 0] = 2 * ap[:, 1] - ap[:, 2]
    ap[:, -1] = 2 * ap[:, -2] - ap[:, -3]
    return 0.25 * (ap[:-1, :-1] + ap[1:, :-1] + ap[:-1, 1:] + ap[1:, 1:])


def subpoints() -> list:
    u = (np.arange(SUB) + 0.5) / SUB
    U, V = np.meshgrid(u, u)
    U, V = U.ravel(), V.ravel()
    return [(1 - U) * (1 - V), U * (1 - V), U * V, (1 - U) * V]


def deposit(S: np.ndarray, W: np.ndarray, lat: np.ndarray, lon: np.ndarray, no2: np.ndarray, wts: list) -> int:
    """Spread one orbit's valid pixels onto the grid (S, W: flat sums and weights of one month)."""
    if lat.shape[0] < 3 or lat.shape[1] < 3:
        return 0
    i, j = np.nonzero(np.isfinite(no2))
    if i.size == 0:
        return 0
    cla, clo = corners(lat.astype(np.float64)), corners(lon.astype(np.float64))
    quad = ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))
    lat_s = sum(cla[q][:, None] * wts[k][None, :] for k, q in enumerate(quad))
    lon_s = sum(clo[q][:, None] * wts[k][None, :] for k, q in enumerate(quad))
    g = GRID
    ix = np.floor((lon_s - g["lon0"]) / g["step"]).astype(np.int64)
    iy = np.floor((g["lat0"] - lat_s) / g["step"]).astype(np.int64)
    ok = (ix >= 0) & (ix < g["nx"]) & (iy >= 0) & (iy < g["ny"])
    cell = (iy * g["nx"] + ix)[ok]
    n = wts[0].size
    val = np.broadcast_to((no2[i, j].astype(np.float64) * K)[:, None], lat_s.shape)[ok] / n
    ncell = g["nx"] * g["ny"]
    S += np.bincount(cell, weights=val, minlength=ncell)
    W += np.bincount(cell, weights=np.full(cell.shape, 1.0 / n), minlength=ncell)
    return int(i.size)


def month_rows(ym: str) -> list:
    first, last = span(ym)
    months = sorted({first[:7], last[:7]})
    return [r for m in months for r in get_hormuz.month_items(m) if first <= r["datetime"][:10] <= last]


def build_month(ym: str, partial: bool = False):
    """The sums and weights of one calendar month, from the cached orbits. A missing orbit is an error, unless
    partial: then the month is skipped (None)."""
    rows = month_rows(ym)
    missing = [r["id"] for r in rows if not (get_hormuz.GRANULES / f"{r['id']}.json").exists()]
    if missing and partial:
        return None
    assert not missing, f"{ym}: {len(missing)} orbits not cached, e.g. {missing[0]}"
    g, wts = GRID, subpoints()
    ncell = g["nx"] * g["ny"]
    S, W = np.zeros(ncell), np.zeros(ncell)
    orbits = pixels = 0
    versions, days = collections.Counter(), set()
    for r in rows:
        meta = json.loads((get_hormuz.GRANULES / f"{r['id']}.json").read_text())
        versions[meta.get("version")] += 1
        if not meta.get("n_valid"):
            continue
        z = np.load(get_hormuz.GRANULES / f"{r['id']}.npz")
        pixels += deposit(S, W, z["lat"], z["lon"], z["no2"], wts)
        orbits += 1
        days.add(r["datetime"][:10])
    FIELDS.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(FIELDS / f"{ym}.npz", S=S.reshape(g["ny"], g["nx"]).astype(np.float32),
                        W=W.reshape(g["ny"], g["nx"]).astype(np.float32))
    info = dict(month=ym, orbits=orbits, days=len(days), pixels=pixels, versions=dict(versions))
    (FIELDS / f"{ym}.json").write_text(json.dumps(info))
    return info


def load(ym: str) -> tuple:
    z = np.load(FIELDS / f"{ym}.npz")
    return z["S"].astype(np.float64), z["W"].astype(np.float64)


def have(ym: str) -> bool:
    return (FIELDS / f"{ym}.npz").exists()


def mean_field(yms, wmin: float = 2.0) -> np.ndarray:
    """The area-weighted mean NO2 of some months (NaN where fewer than wmin pixel-weights fell)."""
    S = W = 0.0
    for ym in yms:
        s, w = load(ym)
        S, W = S + s, W + w
    return np.where(W >= wmin, S / np.maximum(W, 1e-9), np.nan)


def axes() -> tuple:
    g = GRID
    lon = g["lon0"] + (np.arange(g["nx"]) + 0.5) * g["step"]
    lat = g["lat0"] - (np.arange(g["ny"]) + 0.5) * g["step"]
    return lon, lat


# ── the seas, the coast and the inventory's lane ──

SIGMA_KM = 15.0                                   # the inventory is smoothed over this length before its ridge is followed
# the three stretches of sea: their box (W, S, E, N) and the least distance from land of a cell that counts (km)
REGIONS = dict(strait=dict(box=(55.9, 25.9, 57.1, 27.0), coast=8.0),
               gulf=dict(box=(48.0, 24.0, 56.2, 30.5), coast=25.0),
               oman=dict(box=(56.9, 21.5, 61.5, 26.0), coast=25.0))
_CACHE: dict = {}


def cell_km() -> tuple:
    return 111.0 * GRID["step"], 111.0 * GRID["step"] * np.cos(np.deg2rad(26.0))


def land_mask() -> np.ndarray:
    """True on land (Natural Earth 10 m), on GRID."""
    if "land" not in _CACHE:
        import shapefile
        from rasterio.features import rasterize
        from rasterio.transform import from_origin
        g = GRID
        w, e = g["lon0"], g["lon0"] + g["nx"] * g["step"]
        s, n = g["lat0"] - g["ny"] * g["step"], g["lat0"]
        polys = []
        for sh in shapefile.Reader(str(DATA / "ne" / "ne_10m_land.shp")).iterShapes():
            x0, y0, x1, y1 = sh.bbox
            if x1 < w or x0 > e or y1 < s or y0 > n:
                continue
            pts = np.asarray(sh.points, float)
            starts = list(sh.parts) + [len(pts)]
            rings = []
            for a, b in zip(starts[:-1], starts[1:]):
                ring = pts[a:b]
                x, y = ring[:, 0], ring[:, 1]
                if 0.5 * np.sum(x[:-1] * y[1:] - x[1:] * y[:-1]) < 0 or not rings:      # clockwise: a new polygon
                    rings.append([ring.tolist()])
                else:
                    rings[-1].append(ring.tolist())                                      # a hole
            polys += [{"type": "Polygon", "coordinates": r} for r in rings]
        tr = from_origin(g["lon0"], g["lat0"], g["step"], g["step"])
        _CACHE["land"] = rasterize([(q, 1) for q in polys], out_shape=(g["ny"], g["nx"]), transform=tr, fill=0,
                                   dtype="uint8").astype(bool)
    return _CACHE["land"]


def coast_km() -> np.ndarray:
    """Distance of every cell from the nearest land cell, km."""
    if "coast" not in _CACHE:
        from scipy import ndimage
        _CACHE["coast"] = ndimage.distance_transform_edt(~land_mask(), sampling=cell_km())
    return _CACHE["coast"]


def inventory() -> dict:
    """EDGAR v8.1, 2022, on GRID: the NOx of ships, t per km2 and year, and the same smoothed (for the lane's line)."""
    if "inv" not in _CACHE:
        from scipy import ndimage
        z = np.load(DATA / "edgar_nox_2022.npz")
        lon, lat = axes()
        ii = np.clip(np.round((lat - z["lat"][0]) / 0.1).astype(int), 0, len(z["lat"]) - 1)
        jj = np.clip(np.round((lon - z["lon"][0]) / 0.1).astype(int), 0, len(z["lon"]) - 1)
        area = (11.1 * 11.1 * np.cos(np.deg2rad(z["lat"])))[:, None]
        ship = (z["ship"] / area)[np.ix_(ii, jj)]
        ky, kx = cell_km()
        _CACHE["inv"] = dict(ship=ship, ship_s=ndimage.gaussian_filter(ship, (SIGMA_KM / ky, SIGMA_KM / kx)))
    return _CACHE["inv"]


def region(name: str) -> dict:
    """The cells of one stretch of sea: its water, away from land by the stretch's least distance."""
    key = "region_" + name
    if key not in _CACHE:
        r = REGIONS[name]
        lon, lat = axes()
        LON, LAT = np.meshgrid(lon, lat)
        W, S, E, N = r["box"]
        _CACHE[key] = dict(water=(~land_mask()) & (coast_km() >= r["coast"]) & (LON > W) & (LON < E) & (LAT > S) & (LAT < N))
    return _CACHE[key]


# ── the pictures: NO2 as a glow over NASA Blue Marble, Web Mercator ──

V0, V1 = 1.0, 3.0                                 # 1e15 molecules per cm2: the glow starts at V0 and is full at V1
                                                  # (set for the sea, where the film's numbers are: the cities stand above it)
RAMP = ((0.0, (150, 30, 10)), (0.35, (235, 95, 15)), (0.7, (255, 190, 60)), (1.0, (255, 250, 225)))   # ember to white
BASE_DIM = 0.55                                   # the base map is darkened under the glow
GRAIN_CELLS = 1.4                                 # the field is smoothed over this many cells (3.5 km) before it is drawn


def filled(F: np.ndarray) -> np.ndarray:
    """A field with its empty cells taken from the nearest cell that has data, then smoothed for drawing."""
    from scipy import ndimage
    bad = ~np.isfinite(F)
    if bad.any():
        idx = ndimage.distance_transform_edt(bad, return_distances=False, return_indices=True)
        F = F[tuple(idx)]
    return ndimage.gaussian_filter(F, GRAIN_CELLS)


def sample(F: np.ndarray, box: tuple, px: tuple) -> np.ndarray:
    """A field on GRID drawn on a Web Mercator picture of px pixels over box (W, S, E, N)."""
    from scipy import ndimage
    import get_khazar
    W, S, E, N = box
    g = GRID
    assert g["lon0"] <= W and E <= g["lon0"] + g["nx"] * g["step"] and g["lat0"] - g["ny"] * g["step"] <= S and N <= g["lat0"], box
    xs = W + (np.arange(px[0]) + 0.5) / px[0] * (E - W)
    my = get_khazar.my(N) - (np.arange(px[1]) + 0.5) / px[1] * (get_khazar.my(N) - get_khazar.my(S))
    ys = np.array([get_khazar.lat_of(v) for v in my])
    RR, CC = np.meshgrid((g["lat0"] - ys) / g["step"] - 0.5, (xs - g["lon0"]) / g["step"] - 0.5, indexing="ij")
    return ndimage.map_coordinates(F, [RR, CC], order=1, mode="nearest")


def ramp(t: np.ndarray) -> np.ndarray:
    pos = np.array([q[0] for q in RAMP])
    return np.stack([np.interp(t, pos, np.array([q[1][k] for q in RAMP], float)) for k in range(3)], -1)


def picture(F: np.ndarray, name: str, px: tuple):
    """The glow of a field over the darkened base map of a frame ("east" or "gulf"): a PIL image."""
    from PIL import Image
    box = get_hormuz.EAST if name == "east" else get_hormuz.GULF
    base = Image.open(DATA / f"base_{name}.jpg").convert("RGB").resize(px, Image.LANCZOS)
    t = np.clip((sample(filled(F), box, px) - V0) / (V1 - V0), 0, 1)
    alpha = (np.clip(t * 1.6, 0, 1) ** 0.8 * 0.92)[..., None]
    im = np.asarray(base, float) * BASE_DIM * (1 - alpha) + ramp(t) * alpha
    return Image.fromarray(np.clip(im, 0, 255).astype(np.uint8))


def lane_path() -> list:
    """The main lane as a line (lon, lat), from inside the Gulf through the strait into the Gulf of Oman: the ridge of
    the inventory's ship NOx, followed column by column from the strait (56.55 E) to both sides, then smoothed."""
    from scipy import ndimage
    inv = inventory()
    lon, lat = axes()
    field = np.where(land_mask(), 0.0, inv["ship_s"])
    j0 = int(np.argmin(np.abs(lon - 56.55)))
    win = (lat > 26.35) & (lat < 26.8)
    i0 = int(np.flatnonzero(win)[np.argmax(field[win, j0])])
    step = 4                                                  # columns per step (0.1 degree)
    reach = 9                                                 # the ridge may move this many cells (0.225 degree) a step

    def walk(j_end: int, sign: int) -> list:
        out, i, j = [], i0, j0
        while (j + sign * step - j_end) * sign <= 0:
            j += sign * step
            a, b = max(0, i - reach), min(len(lat), i + reach + 1)
            i = a + int(np.argmax(field[a:b, j]))
            out.append((float(lon[j]), float(lat[i])))
        return out

    east = walk(int(np.argmin(np.abs(lon - 60.9))), +1)
    west = walk(int(np.argmin(np.abs(lon - 54.3))), -1)
    pts = np.array(west[::-1] + [(float(lon[j0]), float(lat[i0]))] + east)
    pts[:, 1] = ndimage.uniform_filter1d(pts[:, 1], 3, mode="nearest")
    return [[round(float(x), 3), round(float(y), 3)] for x, y in pts]


# ── the film: numbers, pictures, words, clock ──

ROOT = get_hormuz.ROOT
BUILD = ROOT / "outputs" / "onebit" / "hormuz"
THEN, NOW = 2025, 2026                            # the two years whose windows are compared
EVENT = "2026-03-01"                              # the first day of the collapse in the ship count (20 ships, then 4)
SITE_DEG = 0.2                                    # a place is the box of its centre +- this many degrees
FPS = 30
# ports, cities and plants (lon, lat): inside the strait, and just outside it on the Gulf of Oman
SITES = dict(asaluyeh=(52.61, 27.48), ras_laffan=(51.55, 25.92), jubail=(49.62, 27.02), dubai=(55.27, 25.20),
             bandar=(56.27, 27.19), kuwait=(47.98, 29.37), fujairah=(56.35, 25.13), sohar=(56.63, 24.47),
             muscat=(58.40, 23.60))
INSIDE = ("asaluyeh", "ras_laffan", "jubail", "dubai", "bandar", "kuwait")
# where each name stands from its dot on the panel (pixels): above it, unless a neighbour's name is there
SITE_AT = dict(asaluyeh=(70, -62), ras_laffan=(-165, -44), jubail=(0, -62), dubai=(0, -62), bandar=(0, 62), kuwait=(0, -62))
OUTSIDE = ("fujairah", "sohar", "muscat")
PLACES = dict(SITES, strait=(56.47, 26.62), e_iran=(59.3, 26.95), lane=(58.55, 25.38),
              g_iran=(53.6, 29.25), g_saudi=(48.9, 25.75), g_uae=(54.6, 24.5), g_gulf=(51.35, 27.05), g_strait=(56.45, 26.6))


def ships() -> dict:
    """IMF PortWatch's daily transit calls of the strait (AIS): the days of the closure window in both years, and
    weekly means from a year before the event to the end of that window, for the card."""
    import pandas as pd
    d = pd.read_csv(DATA / "portwatch_hormuz_daily.csv", parse_dates=["date"]).set_index("date")["n_total"]
    assert d.index.is_monotonic_increasing and not d.index.duplicated().any()
    a, b = PARTS[CLOSURE[0]][0], PARTS[CLOSURE[-1]][1]
    assert f"{NOW}-{a}" == EVENT and d.index[-1] >= pd.Timestamp(f"{NOW}-{b}"), (a, d.index[-1])
    then, now = float(d[f"{THEN}-{a}":f"{THEN}-{b}"].mean()), float(d[f"{NOW}-{a}":f"{NOW}-{b}"].mean())
    three = float(np.mean([d[f"{y}-{a}":f"{y}-{b}"].mean() for y in (2023, 2024, 2025)]))
    ev = pd.Timestamp(EVENT)

    def weeks(year: int) -> list:                                  # the window's weeks, counted from its first day
        w = d[f"{year}-{a}":f"{year}-{b}"]
        return [round(float(v), 1) for v in w.groupby((w.index - w.index[0]).days // 7).mean().values]

    after = (f"{PARTS[AFTER[0]][0]}", f"{PARTS[AFTER[-1]][1]}")       # 18 June to 7 November: the count stays low
    out = dict(then=then, now=now, three=three, fewer=1 - now / then, fewer_three=1 - now / three,
               day_before=int(d[ev - pd.Timedelta(days=2)]), day_after=int(d[ev + pd.Timedelta(days=1)]),
               weeks_then=weeks(THEN), weeks_now=weeks(NOW), first=f"{NOW}-{a}", last=f"{NOW}-{b}",
               after_then=float(d[f"{THEN}-{after[0]}":f"{THEN}-{after[1]}"].mean()),
               after_now=float(d[f"{NOW}-{after[0]}":f"{NOW}-{after[1]}"].mean()))
    assert len(out["weeks_then"]) == len(out["weeks_now"]) == 16, (len(out["weeks_then"]), len(out["weeks_now"]))
    assert 80 < then < 105 and 3 < now < 10 and 0.94 < out["fewer"] < 0.96, out            # «۹۵٪ کمتر», 97 and 5 a day
    assert 0.90 < out["fewer_three"] < 0.97 and out["day_before"] > 50 and out["day_after"] < 10, out
    return out


def site_mask(key: str) -> np.ndarray:
    lon, lat = axes()
    x, y = SITES[key]
    return (np.abs(lat - y) < SITE_DEG)[:, None] & (np.abs(lon - x) < SITE_DEG)[None, :]


def mean_over(keys, mask: np.ndarray) -> float:
    return float(np.nanmean(mean_field(keys, wmin=0.5)[mask]))


def measures() -> dict:
    """What the film says with numbers.
    closure: the window from the event to the memorandum (1 March to 17 June) in every year at hand: the mean NO2 over
      each stretch of sea (its cells away from land), of each place's box, of the places inside and outside the strait.
    parts: the change from THEN to NOW of each part of the year that both years have (before, during, after).
    before: the same change over 1 January to 28 February, when nothing had happened yet: what the two years (and the
      two processor versions, 2.8.0 and 2.9.1) differ by on their own.
    normal: the change of the closure window from one earlier year to the next: what a normal year does."""
    seas = {k: region(k)["water"] for k in REGIONS}
    sites = {k: site_mask(k) for k in SITES}
    years = [y for y in (2023, 2024, THEN, NOW) if all(have(k) for k in closure(y))]
    assert THEN in years and NOW in years, years
    group = lambda keys, names: float(np.mean([mean_over(keys, sites[k]) for k in names]))   # noqa: E731
    cl = dict(seas={k: {y: mean_over(closure(y), m) for y in years} for k, m in seas.items()},
              sites={k: {y: mean_over(closure(y), m) for y in years} for k, m in sites.items()},
              inside={y: group(closure(y), INSIDE) for y in years}, outside={y: group(closure(y), OUTSIDE) for y in years})
    ch = lambda d: d[NOW] / d[THEN] - 1                                               # noqa: E731
    out = dict(years=years, closure=cl,
               change=dict(seas={k: ch(v) for k, v in cl["seas"].items()}, sites={k: ch(v) for k, v in cl["sites"].items()},
                           inside=ch(cl["inside"]), outside=ch(cl["outside"])))
    parts = []
    for k in BEFORE + CLOSURE + AFTER:
        a, b = [f"{THEN}-{k}"], [f"{NOW}-{k}"]
        if have(a[0]) and have(b[0]):
            parts.append(dict(key=k, when="before" if k in BEFORE else "closure" if k in CLOSURE else "after",
                              gulf=mean_over(b, seas["gulf"]) / mean_over(a, seas["gulf"]) - 1,
                              strait=mean_over(b, seas["strait"]) / mean_over(a, seas["strait"]) - 1,
                              oman=mean_over(b, seas["oman"]) / mean_over(a, seas["oman"]) - 1,
                              inside=group(b, INSIDE) / group(a, INSIDE) - 1, outside=group(b, OUTSIDE) / group(a, OUTSIDE) - 1))
    out["parts"] = parts
    if all(have(f"{y}-{k}") for y in (THEN, NOW) for k in BEFORE):
        a, b = [f"{THEN}-{k}" for k in BEFORE], [f"{NOW}-{k}" for k in BEFORE]
        out["before"] = dict(seas={k: mean_over(b, m) / mean_over(a, m) - 1 for k, m in seas.items()},
                             inside=group(b, INSIDE) / group(a, INSIDE) - 1, outside=group(b, OUTSIDE) / group(a, OUTSIDE) - 1)
    earlier = [y for y in years if y < NOW]
    # the places inside the Gulf over the places on the Gulf of Oman: of the whole window in every year, and of each
    # of its parts (what the weather and the processor do to both groups alike drops out of this ratio)
    out["ratio"] = {y: cl["inside"][y] / cl["outside"][y] for y in years}
    out["ratio_parts"] = {k: {y: group([f"{y}-{k}"], INSIDE) / group([f"{y}-{k}"], OUTSIDE) for y in years} for k in CLOSURE}
    out["three"] = dict(inside=cl["inside"][NOW] / float(np.mean([cl["inside"][y] for y in earlier])) - 1,
                        outside=cl["outside"][NOW] / float(np.mean([cl["outside"][y] for y in earlier])) - 1,
                        ratio=out["ratio"][NOW] / float(np.mean([out["ratio"][y] for y in earlier])) - 1) if len(earlier) == 3 else None
    out["normal"] = [dict(years=[y0, y1], seas={k: cl["seas"][k][y1] / cl["seas"][k][y0] - 1 for k in seas},
                          inside=cl["inside"][y1] / cl["inside"][y0] - 1, outside=cl["outside"][y1] / cl["outside"][y0] - 1)
                     for y0, y1 in zip(earlier[:-1], earlier[1:])]
    return out


def report(m: dict) -> None:
    pc = lambda x: f"{100 * x:+4.0f} %"                                               # noqa: E731
    print(f"\nclosure window ({PARTS[CLOSURE[0]][0]} to {PARTS[CLOSURE[-1]][1]}), years {m['years']}, {THEN} -> {NOW}:")
    for k in REGIONS:
        print(f"  sea  {k:10s} " + "  ".join(f"{y}: {v:5.2f}" for y, v in m["closure"]["seas"][k].items()) + f"   {pc(m['change']['seas'][k])}")
    for k in SITES:
        print(f"  site {k:10s} " + "  ".join(f"{y}: {v:5.2f}" for y, v in m["closure"]["sites"][k].items()) + f"   {pc(m['change']['sites'][k])}")
    print(f"  inside the strait {pc(m['change']['inside'])}; outside it {pc(m['change']['outside'])}")
    print("parts (change of the Gulf's sea | inside places | outside places | the sea outside):")
    for q in m["parts"]:
        print(f"  {q['key']:5s} {q['when']:8s} {pc(q['gulf'])} | {pc(q['inside'])} | {pc(q['outside'])} | {pc(q['oman'])}")
    if "before" in m:
        print("before the event (1 Jan to 28 Feb):", {k: pc(v) for k, v in m["before"]["seas"].items()},
              "inside", pc(m["before"]["inside"]), "outside", pc(m["before"]["outside"]))
    for q in m["normal"]:
        print(f"normal years {q['years']}:", {k: pc(v) for k, v in q["seas"].items()}, "inside", pc(q["inside"]), "outside", pc(q["outside"]))
    print("inside over outside, the whole window:", {y: round(v, 2) for y, v in m["ratio"].items()},
          "| by part:", {k: [round(v, 2) for v in d.values()] for k, d in m["ratio_parts"].items()})
    if m["three"]:
        print("against the mean of the three earlier years: inside", pc(m["three"]["inside"]), "outside", pc(m["three"]["outside"]), "ratio", pc(m["three"]["ratio"]))


def pictures() -> dict:
    """The film's pictures: the strait and the Gulf of Oman (a 9:16 frame) and the whole Gulf (a wide panel), each as
    the mean of the closure window (1 March to 17 June) of the earlier and of the later year."""
    BUILD.mkdir(parents=True, exist_ok=True)
    for tag, year in (("then", THEN), ("now", NOW)):
        F = mean_field(closure(year))
        picture(F, "east", (1620, 2880)).save(BUILD / f"e_{tag}.jpg", quality=92, subsampling=0)
        picture(F, "gulf", (1620, 1440)).save(BUILD / f"g_{tag}.jpg", quality=92, subsampling=0)
    return dict(east=dict(box=list(get_hormuz.EAST), then="e_then.jpg", now="e_now.jpg"),
                gulf=dict(box=list(get_hormuz.GULF), then="g_then.jpg", now="g_now.jpg"))


def pct(x: float) -> str:
    from onebit import fa
    return fa(f"{round(100 * abs(x))}٪")


def about(x: float) -> str:
    """A share to the nearest five per cent, as the headlines say it («حدودِ ۳۰٪»)."""
    from onebit import fa
    return fa(f"{5 * round(100 * abs(x) / 5)}٪")


FA_PART = dict(j10="دی", j11="بهمن", j12="اسفند", j01="فروردین", j02="اردیبهشت", j03="خرداد", j04="تیر",
               j05="مرداد", j06="شهریور", j07="مهر", j08="آبان")
TICKS = ("j10", "j12", "j03", "j06", "j08")                       # the parts whose month is written under the chart


def words_of(sh: dict, m: dict) -> dict:
    from onebit import fa
    import air
    assert air.jalali(EVENT) == (1404, 12, 10) and air.jalali(f"{NOW}-{PARTS['j03'][1]}") == (1405, 3, 27)   # «۱۰ اسفند تا ۲۷ خرداد»
    span_fa = f"{fa(10)} اسفند تا {fa(27)} خرداد"
    ch = m["change"]
    fa_name = dict(asaluyeh="عسلویه", ras_laffan="رأس لفان", jubail="جبیل", dubai="دبی", bandar="بندرعباس", kuwait="کویت")
    W = dict(
        hook=f"آلاینده‌ی هوا روی خلیجِ فارس: // {{حدودِ {about(ch['inside'])} کمتر}} از پارسال",
        tag_then="پارسال", tag_now="امسال",
        bar_title="دی‌اکسیدِ نیتروژن در هوا", bar_low=f"کم: {fa(f'{V0:g}')}", bar_high=f"زیاد: {fa(f'{V1:g}')}",
        bar_unit="×۱۰¹⁵ مولکول بر سانتی‌مترمربع",
        head_b="این رنگ: دی‌اکسیدِ نیتروژن، // از {کشتی‌ها، نفت و گاز و شهرها}",
        g_iran="ایران", g_saudi="عربستان", g_uae="امارات", g_gulf="خلیجِ فارس", g_strait="تنگه‌ی هرمز",
        head_c=f"از {span_fa} // کشتی‌های ثبت‌شده در هرمز: {{{pct(sh['fewer'])} کمتر}}",
        lane="مسیرِ کشتی‌ها", bandar="بندرعباس", strait="تنگه‌ی هرمز", e_iran="ایران",
        c_unit="کشتی در روز", c_then=f"پارسال: {fa(round(sh['then']))}", c_now=f"امسال: {fa(round(sh['now']))}",
        c_note="کشتی‌های بی‌فرستنده شمرده نمی‌شوند", c_from=f"{fa(10)} اسفند", c_to=f"{fa(27)} خرداد",
        head_e="در خلیجِ فارس: کمتر؛ // در دریای عمان: {تقریباً همان}",
        head_f=f"بعد از {fa(27)} خرداد؟ // {{اختلاف با پارسال کمتر شد}}",
        f_title="شش جای خلیجِ فارس، نسبت به پارسال", f_key=span_fa,
        head_h="جنوبی‌ها: بهارِ امسال // {هوا پاک‌تر بود؟}", follow="برای یک جنوبی بفرستید",
        src_a=f"Sentinel-5P، ESA؛ {span_fa}، هر دو سال // عدد: میانگینِ شش بندر و مرکزِ صنعتی",
        src_b="نقشه: Blue Marble، ناسا // رنگ: ستونِ دی‌اکسیدِ نیتروژن در پایینِ جو",
        src_c="شمارش با فرستنده‌ی AIS: IMF PortWatch // مسیرِ تقریبیِ کشتی‌ها: فهرستِ انتشارِ EDGAR، ۲۰۲۲",
        src_e="میانگینِ کادرِ ۴۰ کیلومتریِ هر جا، همان روزهای پارسال // دریای عمان: فجیره، صحار، مسقط",
        src_f="سنجش روی همین داده‌ی ماهواره // تیر و مرداد: فقط روزهایی که هر دو سال داده دارند",
        src_h="منابع و روش در کامنتِ اول")
    for k in INSIDE:
        W[f"s_{k}"] = f"{fa_name[k]}: {pct(ch['sites'][k])} کمتر"          # in words: a minus sign beside Persian digits reads badly
    for k in TICKS:
        W[f"t_{k}"] = FA_PART[k]
    low = min((q for q in m["parts"] if q["when"] == "closure"), key=lambda q: q["inside"])
    W["f_low"] = f"بیشترین کاهش: {pct(low['inside'])}"                       # the deepest column of the closure, named as that
    return W


def clock_of() -> dict:
    a = (0.0, 7.4)
    b = (a[1], a[1] + 7.0)
    c = (b[1], b[1] + 9.4)
    e = (c[1], c[1] + 7.8)
    f = (e[1], e[1] + 8.0)
    h = (f[1], f[1] + 5.0)
    out = (h[1], h[1] + 0.8)
    return dict(a=a, b=b, c=c, e=e, f=f, h=h, out=out,
                a_go=(0.0, 1.7), a_back=(3.0, 4.2), bar_a=1.9, names_b=b[0] + 0.6,
                lane=(c[0] + 0.3, c[0] + 1.7), names_c=c[0] + 0.5, lane_chip=c[0] + 1.5,
                card_c=(c[0] + 1.2, c[1] - 0.15), weeks=(c[0] + 1.6, c[0] + 3.8), c_wipe=(c[0] + 3.0, c[0] + 4.4),
                c_vals=c[0] + 4.1, c_note=c[0] + 4.8,
                sites=[round(e[0] + 0.8 + 0.5 * j, 2) for j in range(len(INSIDE))],
                card_f=(f[0] + 0.3, f[1] - 0.15), parts=(f[0] + 0.8, f[0] + 3.4), f_key=f[0] + 3.6, follow=h[0] + 1.2)


def reading(Wd: dict, C: dict) -> None:
    """The owner's reading rule (src/onebit_reading.py) on every scene, asserted: a scene lasts at least 1 s plus its
    words at 2.5 a second (headline, small line and sentences in full, labels at half) and 3 s after its last string."""
    import onebit_reading as rd
    wt = lambda xs: sum(rd.weight(x) for x in xs)    # noqa: E731
    plan = [("hook", C["a"], [Wd["hook"]], [Wd["tag_then"], Wd["tag_now"], Wd["bar_title"], Wd["bar_low"], Wd["bar_high"], Wd["bar_unit"]], C["bar_a"]),
            ("what", C["b"], [Wd["head_b"]], [Wd["g_iran"], Wd["g_saudi"], Wd["g_uae"], Wd["g_gulf"], Wd["g_strait"]], C["names_b"] + 1.2),
            ("ships", C["c"], [Wd["head_c"], Wd["c_note"]], [Wd["lane"], Wd["bandar"], Wd["strait"], Wd["c_unit"], Wd["c_then"], Wd["c_now"], Wd["c_from"], Wd["c_to"]], C["c_note"]),
            ("sites", C["e"], [Wd["head_e"]], [Wd[f"s_{k}"] for k in INSIDE], C["sites"][-1] + 0.3),
            ("after", C["f"], [Wd["head_f"]], [Wd["f_title"], Wd["f_key"], Wd["f_low"]] + [Wd[f"t_{k}"] for k in TICKS], C["f_key"]),
            ("close", C["h"], [Wd["head_h"], Wd["follow"]], [], C["follow"])]
    print("\nreading (seconds the rule needs, seconds given):")
    short, total = [], 0.0
    for name, (a, b), full, half, last in plan:
        w = wt(full) + rd.LABELS * wt(half)
        total += w
        need = max(rd.SETTLE + w / rd.WPS, last - a + rd.HOLD)
        print(f"  {name:6s} {wt(full):4.1f} + {wt(half):4.1f}/2 words -> {need:4.1f} s needed, {b - a:4.1f} s given")
        if b - a + 0.051 < need:
            short.append((name, round(need, 2), round(b - a, 2)))
    print(f"  weighted words in the film: {total:.0f}")
    assert not short, short


def film(final: bool = True) -> dict:
    """Write outputs/onebit/hormuz/film.json and the pictures. final: the winter before the event and two earlier
    springs must be there, and every sentence of the film is asserted against them."""
    sh, m = ships(), measures()
    report(m)
    ch, parts = m["change"], {q["key"]: q for q in m["parts"]}
    # during the closure: less over the Gulf's sea and at every place inside the strait, in each of its four parts
    assert -0.36 < ch["seas"]["gulf"] < -0.22 and ch["inside"] < -0.2, ch
    assert all(ch["sites"][k] < -0.1 for k in INSIDE), ch["sites"]
    assert all(parts[k]["gulf"] < -0.15 and parts[k]["inside"] < -0.15 for k in CLOSURE), parts
    assert abs(ch["outside"]) < 0.1, ch                                            # «در دریای عمان: تقریباً همان»
    assert about(ch["inside"]) == about(0.30), ch["inside"]                        # «حدودِ ۳۰٪ کمتر»
    if final:
        assert set(BEFORE + CLOSURE + AFTER) == set(parts), sorted(parts)
        assert len(m["years"]) == 4 and "before" in m, m["years"]
        # the two years do not differ like this before the event, and normal years do not either
        assert abs(m["before"]["inside"] - m["before"]["outside"]) < 0.08, m["before"]   # before the event the two move together
        assert all(abs(q["inside"]) < 0.15 for q in m["normal"]), m["normal"]         # a normal year moves the six places by less
        # against the places on the Gulf of Oman, the six places stand lower than in any of the three earlier years:
        # in the whole window by a quarter at the least, and in each of its four parts
        low = min(m["ratio"][y] for y in m["years"] if y < NOW)
        assert m["ratio"][NOW] < 0.76 * low, m["ratio"]
        assert all(d[NOW] < 0.85 * min(v for y, v in d.items() if y < NOW) for d in m["ratio_parts"].values()), m["ratio_parts"]
        assert -0.30 < m["three"]["inside"] < -0.20 and -0.36 < m["three"]["ratio"] < -0.28, m["three"]   # the first comment's numbers
        # after the memorandum the six places differ less from last year than in any part of the closure («اختلاف کمتر شد»)
        assert max(abs(parts[k]["inside"]) for k in AFTER) < min(abs(parts[k]["inside"]) for k in CLOSURE), parts
    Wd, C = words_of(sh, m), clock_of()
    reading(Wd, C)
    pics = pictures()
    chart = [dict(key=q["key"], when=q["when"], value=round(100 * q["inside"], 1)) for q in m["parts"]]
    F = dict(fps=FPS, size=[1080, 1920], cover_t=0.85, end=C["out"][1], clock=C, words=Wd,
             places={k: list(v) for k, v in PLACES.items()}, inside=list(INSIDE), site_at={k: list(SITE_AT[k]) for k in INSIDE},
             colours=dict(gold="#F6C445", ink="#1d140c", paper="#FBF7F0", then="#F39C2B", now="#2C6FB7", rest="#9a948b"),
             lane=lane_path(), ships=dict(then=sh["weeks_then"], now=sh["weeks_now"]),
             chart=dict(parts=chart, ticks=[[q["key"] for q in m["parts"]].index(k) for k in TICKS if k in parts], tick_keys=[k for k in TICKS if k in parts],
                        low=min((k for k, q in enumerate(chart) if q["when"] == "closure"), key=lambda k: chart[k]["value"])),
             scale=dict(v0=V0, v1=V1, ramp=[[q[0], list(q[1])] for q in RAMP]),
             numbers=dict(ships=sh, **{k: v for k, v in m.items()}), **pics)
    (BUILD / "film.json").write_text(json.dumps(F, ensure_ascii=False, indent=1))
    print(f"\nships a day {sh['then']:.1f} -> {sh['now']:.1f} ({100 * sh['fewer']:.1f} % fewer; three earlier years {sh['three']:.1f}); "
          f"after the window {sh['after_then']:.1f} -> {sh['after_now']:.1f}")
    print(f"saved {BUILD / 'film.json'} | end {F['end']:.1f} s")
    return F


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] in ("film", "draft"):
        film(final=sys.argv[1] == "film")
        return
    if len(sys.argv) >= 3 and sys.argv[1] in ("fields", "partial"):
        yms = [ym for a in sys.argv[2:] for ym in (window(int(a)) if len(a) == 4 else [a])]
        for ym in yms:
            info = build_month(ym, partial=sys.argv[1] == "partial")
            print(ym, "not complete yet" if info is None else
                  f"orbits {info['orbits']}, days {info['days']}, versions {info['versions']}", flush=True)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
