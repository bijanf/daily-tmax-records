"""THE LATYAN RESERVOIR FROM SPACE: the open water of the Latyan reservoir on the Jajrud river, one of the five
dams that supply Tehran, in one autumn Landsat pass a year, 1987-2026.

Measured data only, from Landsat Collection 2 Level-2 (USGS, via Microsoft's Planetary Computer with its
anonymous token: the helpers of get_urmia.py) and JRC Global Surface Water (extent of any water 1984-2021).
The reservoir: JRC's extent opened with a disk of 3 pixels (about 90 m, which cuts thin shore fringes), and
the piece that holds the dam point (51.6793 E, 35.7901 N). Open water = MNDWI > 0 and NIR < 0.10 on clear
pixels. Area = water / clear pixels x the reservoir's pixels (30 m, 0.0009 km2 each).

A pass is accepted when the whole reservoir lies in the scene and at least 85 % of it is clear of cloud,
cloud shadow, cirrus and snow (60 % for Landsat 7 after its scan-line corrector failed on 31 May 2003). One
pass per year: the nearest to 1 October within 25 days, preferring a pass with at least 99 % of the reservoir
clear, then one without stripe gaps over the reservoir (at least 99.5 % of it with data), however near the
striped pass is. Passes listed in EXCLUDE are left out of every count, with the reason given there.

    data/latyan/roi.npz              the reservoir on JRC's grid: mask, transform, bounds (W, S, E, N)
    data/latyan/scenes/<item>.json   per Landsat pass over the dam point: date, platform, coverage, clear and
                                     valid shares, water and area (km2) on the pass's own grid
    data/latyan/<year>.npz           the chosen pass on one fixed 1-arc-second grid (EPSG:4326): surface
                                     reflectance (NaN where not clear); water (1), land (0) and not clear (255)
                                     inside the reservoir, 255 outside it; the reservoir mask; the area on this grid
    data/latyan/frames.csv           one row per year with a frame

    python -I src/get_latyan.py                      # every year (scenes are cached)
    python -I src/get_latyan.py --years 2025 2026    # scan some years only
    python -I src/get_latyan.py --frames             # choose the frames again from the cached scenes
"""

from __future__ import annotations

import functools
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.crs import CRS
from rasterio.env import Env
from rasterio.transform import Affine
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import Window, from_bounds
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from get_urmia import ENV, STAC, get, signed, slc_off  # noqa: E402  (keyless Landsat helpers)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "latyan"
DAM = (51.6793, 35.7901)                             # lon, lat: the Latyan dam (on the Jajrud river)
SEARCH = [51.50, 35.70, 51.85, 35.92]                # W, S, E, N: the STAC search box
JRC = "https://storage.googleapis.com/global-surface-water/downloads2021/extent/extent_50E_40Nv1_4_2021.tif"
JRC_WINDOW = (51.50, 35.70, 51.85, 35.92)            # W, S, E, N read from JRC's tile
OPEN = 3                                             # px of JRC's 30-m grid: radius of the opening disk
GRID = (51.600, 35.770, 51.712, 35.832)              # W, S, E, N: the fixed grid of the frames
RES = 1 / 3600                                       # deg: one arc-second
GRID_T = Affine(RES, 0, GRID[0], 0, -RES, GRID[3])
SHAPE = (round((GRID[3] - GRID[1]) / RES), round((GRID[2] - GRID[0]) / RES))
YEARS = (1987, 2026)
WINDOW = 25                                          # days either side of 1 October
PREFER = 0.99                                        # share of the reservoir clear: a pass with it is preferred
ACCEPT = (0.85, 0.60)                                # share clear to accept; Landsat 7 after 31 May 2003
GAP_FREE = 0.995                                     # share of the reservoir with data: fewer gaps preferred
EXCLUDE = {                                          # item -> reason: anomalous passes, left out of every count
    "LT05_L2SP_164035_19950915_02_T2":
        "Tier 2: 0.00 km2 inside the outline, sixteen days before 2.64 km2 on 1 October 1995 (a Tier-1 pass); "
        "its water lies 1.8 km east and 1.1 km north of the reservoir's centre, outside the outline: the pass is "
        "misregistered (as the Tier-2 passes at Karaj were); no drawdown explains it",
    "LT05_L2SP_164035_19951017_02_T2":
        "Tier 2: no open water anywhere in the reservoir's window (0.00 km2), sixteen days after 2.64 km2 on "
        "1 October 1995 (a Tier-1 pass); no drawdown explains it",
    "LT05_L2SP_164035_19960917_02_T2":
        "Tier 2: 1.03 km2 against 2.62 km2 on 3 October 1996 (a Tier-1 pass, sixteen days later); its water's "
        "centre lies 0.95 km west and 0.15 km north of the reservoir's centre: misregistered, as the Tier-2 passes "
        "at Karaj were; no drawdown explains it",
}
SCALE, OFFSET = 0.0000275, -0.2                      # Collection 2 surface reflectance
QA_BAD = 0b111111                                    # fill, dilated cloud, cirrus, cloud, cloud shadow, snow
PIX_KM2 = 0.0009                                     # Landsat's 30-m pixel
CELL_KM2 = (RES * 111320 * math.cos(math.radians(35.80))) * (RES * 110574) / 1e6   # a cell of the fixed grid


def covers(geom: dict, lon: float, lat: float) -> bool:
    """Whether a GeoJSON footprint (Polygon or MultiPolygon) contains the point (even-odd rule)."""
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        inside = False
        for (x1, y1), (x2, y2) in zip(poly[0], poly[0][1:]):
            if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
                inside = not inside
        if inside:
            return True
    return False


def disk(r: int) -> np.ndarray:
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


@functools.cache
def reservoir() -> tuple:
    """The reservoir on JRC's grid: (mask, transform, bounds W S E N), cached in data/latyan/roi.npz."""
    cache = DATA / "roi.npz"
    if not cache.exists():
        with Env(**ENV), rasterio.open("/vsicurl/" + JRC) as src:
            win = from_bounds(*JRC_WINDOW, transform=src.transform).round_offsets(op="floor").round_lengths(op="ceil")
            ext, t = src.read(1, window=win), src.window_transform(win)
        opened = ndimage.binary_opening(ext == 1, structure=disk(OPEN))
        lab, _ = ndimage.label(opened, structure=np.ones((3, 3)))
        ys, xs = np.nonzero(opened)
        lon, lat = t.c + (xs + 0.5) * t.a, t.f + (ys + 0.5) * t.e
        k = int(np.argmin(((lon - DAM[0]) * math.cos(math.radians(DAM[1]))) ** 2 + (lat - DAM[1]) ** 2))
        mask = lab == lab[ys[k], xs[k]]
        rr, cc = np.nonzero(mask)
        bounds = (t.c + cc.min() * t.a, t.f + (rr.max() + 1) * t.e, t.c + (cc.max() + 1) * t.a, t.f + rr.min() * t.e)
        DATA.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, mask=mask, transform=np.array(tuple(t)[:6]), bounds=np.array(bounds))
    z = np.load(cache)
    return z["mask"], Affine(*z["transform"]), tuple(float(b) for b in z["bounds"])


def search(year: int) -> list:
    """The Landsat passes of 1 September to 15 November that cover the dam point."""
    d = get(STAC, {"collections": ["landsat-c2-l2"], "bbox": SEARCH, "limit": 300,
                   "datetime": f"{year}-09-01T00:00:00Z/{year}-11-15T23:59:59Z"})
    feats = d.get("features", [])
    assert len(feats) < 300, f"{year}: the search hit its limit"
    return [f for f in feats if covers(f["geometry"], *DAM)]


def window(src, bounds: tuple):
    """The window of a scene that holds the lon/lat bounds, and whether all of it lies in the scene."""
    b = transform_bounds(CRS.from_epsg(4326), src.crs, *bounds)
    want = from_bounds(*b, transform=src.transform).round_offsets(op="floor").round_lengths(op="ceil")
    clip = want.intersection(Window(0, 0, src.width, src.height))
    return clip, abs(clip.width - want.width) < 0.5 and abs(clip.height - want.height) < 0.5


def scan(feat: dict) -> dict:
    """One pass over the reservoir on the pass's own grid: coverage, clear and valid shares, water, area."""
    p, a = feat["properties"], feat["assets"]
    out = dict(item=feat["id"], year=int(p["datetime"][:4]), date=p["datetime"][:10], platform=p.get("platform"),
               path_row=feat["id"].split("_")[2], cloud_scene=p.get("eo:cloud_cover"), slc_off=bool(slc_off(feat)))
    roi, t_roi, bounds = reservoir()
    with Env(**ENV):
        with rasterio.open(signed(a["green"]["href"])) as g:
            crs = g.crs
            win, out["coverage_ok"] = window(g, bounds)
            out["coverage_ok"] = bool(out["coverage_ok"])
            if win.width <= 0 or win.height <= 0:
                return out
            wt = g.window_transform(win)
            green = g.read(1, window=win)
        bands = {}
        for key, asset in (("swir", "swir16"), ("nir", "nir08"), ("qa", "qa_pixel")):
            with rasterio.open(signed(a[asset]["href"])) as ds:
                bands[key] = ds.read(1, window=win)
    inside = np.zeros(green.shape, np.uint8)
    reproject(source=roi.astype(np.uint8), destination=inside, src_transform=t_roi, src_crs=CRS.from_epsg(4326),
              dst_transform=wt, dst_crs=crs, resampling=Resampling.nearest)
    inside = inside == 1
    roi_px = int(inside.sum())
    out["roi_px"] = roi_px
    if roi_px == 0:
        return out
    G, S, N = (x.astype(np.float32) * SCALE + OFFSET for x in (green, bands["swir"], bands["nir"]))
    valid = (green > 0) & (bands["swir"] > 0) & (bands["nir"] > 0)
    clear = valid & ((bands["qa"] & QA_BAD) == 0) & inside
    den = G + S
    water = clear & ((G - S) / np.where(den == 0, 1, den) > 0) & (N < 0.10)
    clear_px, water_px = int(clear.sum()), int(water.sum())
    out.update(valid_share=round(float((valid & inside).sum()) / roi_px, 4),
               clear_share=round(clear_px / roi_px, 4), clear_px=clear_px, water_px=water_px,
               area_km2=round(water_px / clear_px * roi_px * PIX_KM2, 4) if clear_px else None)
    limit = ACCEPT[1] if out["slc_off"] else ACCEPT[0]
    out["accepted"] = bool(out["coverage_ok"] and out["clear_share"] >= limit and out["area_km2"] is not None)
    return out


def scene_json(feat: dict) -> dict:
    """The scan of one pass, cached in data/latyan/scenes; a pass that failed to read is tried again."""
    path = DATA / "scenes" / f"{feat['id']}.json"
    if path.exists():
        r = json.loads(path.read_text())
        if "error" not in r:
            return r
    for attempt in range(3):
        try:
            r = scan(feat)
            break
        except Exception as ex:                                    # a dropped connection costs one try
            r = dict(item=feat["id"], error=repr(ex)[:300])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(r))
    return r


def table() -> pd.DataFrame:
    """Every scanned pass that covers the dam point, from the cache (no network), with its day count from 1 October."""
    rows = [json.loads(f.read_text()) for f in sorted((DATA / "scenes").glob("*.json"))]
    df = pd.DataFrame([r for r in rows if "error" not in r])
    when = pd.to_datetime(df["date"])
    df["dt"] = (when - pd.to_datetime(df["year"].astype(str) + "-10-01")).dt.days
    df["accepted"] = df["accepted"].fillna(False).astype(bool)
    return df


def choose(df: pd.DataFrame) -> pd.DataFrame:
    """One pass per year, by the rule of the module docstring."""
    c = df[df["accepted"] & (df["dt"].abs() <= WINDOW) & ~df["item"].isin(EXCLUDE)].copy()
    c["clear_ok"] = c["clear_share"] >= PREFER
    c["gap_free"] = c["valid_share"] >= GAP_FREE
    c["adt"] = c["dt"].abs()
    c = c.sort_values(["year", "clear_ok", "gap_free", "adt", "date"],
                      ascending=[True, False, False, True, True])
    return c.groupby("year").head(1).reset_index(drop=True)


def to_grid(arr: np.ndarray, t, crs) -> np.ndarray:
    dst = np.zeros(SHAPE, dtype=arr.dtype)
    reproject(source=arr, destination=dst, src_transform=t, src_crs=crs, src_nodata=0, dst_transform=GRID_T,
              dst_crs=CRS.from_epsg(4326), dst_nodata=0, resampling=Resampling.nearest)
    return dst


def frame(feat: dict, roi_grid: np.ndarray) -> dict:
    """The pass on the fixed grid: surface reflectance, water, land, not clear, and the area on this grid."""
    a = feat["assets"]
    names = {"red": "red", "green": "green", "blue": "blue", "swir": "swir16", "nir": "nir08", "qa": "qa_pixel"}
    with Env(**ENV):
        with rasterio.open(signed(a["green"]["href"])) as g:
            crs = g.crs
            clip, _ = window(g, GRID)
            wt = g.window_transform(clip)
            raw = {"green": g.read(1, window=clip)}
        for key in ("red", "blue", "swir", "nir", "qa"):
            with rasterio.open(signed(a[names[key]]["href"])) as ds:
                raw[key] = ds.read(1, window=clip)
    grid = {k: to_grid(v, wt, crs) for k, v in raw.items()}
    sr = {k: grid[k].astype(np.float32) * SCALE + OFFSET for k in ("red", "green", "blue", "swir", "nir")}
    valid = (grid["green"] > 0) & (grid["swir"] > 0) & (grid["nir"] > 0)
    seen = valid & ((grid["qa"] & QA_BAD) == 0)           # every clear pixel: the picture shows the land too
    clear = seen & roi_grid                               # the reservoir's clear pixels: the area
    den = sr["green"] + sr["swir"]
    water = clear & ((sr["green"] - sr["swir"]) / np.where(den == 0, 1, den) > 0) & (sr["nir"] < 0.10)
    roi_px, clear_px = int(roi_grid.sum()), int(clear.sum())
    rgb = np.stack([sr["red"], sr["green"], sr["blue"]]).astype(np.float16)
    rgb[:, ~seen] = np.nan
    water_u8 = np.full(SHAPE, 255, np.uint8)
    water_u8[clear] = 0
    water_u8[water] = 1
    return dict(rgb=rgb, water=water_u8, roi=roi_grid, valid_share=float((valid & roi_grid).sum()) / roi_px,
                area_km2_grid=float(water.sum()) / clear_px * roi_px * CELL_KM2 if clear_px else float("nan"))


def grid_roi() -> np.ndarray:
    mask, t, _ = reservoir()
    out = np.zeros(SHAPE, np.uint8)
    reproject(source=mask.astype(np.uint8), destination=out, src_transform=t, src_crs=CRS.from_epsg(4326),
              dst_transform=GRID_T, dst_crs=CRS.from_epsg(4326), resampling=Resampling.nearest)
    return out == 1


def build_frames(picked: pd.DataFrame) -> pd.DataFrame:
    roi_grid = grid_roi()
    feats = {}
    for y in sorted(picked["year"].unique()):
        feats.update({f["id"]: f for f in search(int(y))})

    def one(row):
        f = frame(feats[row["item"]], roi_grid)
        np.savez_compressed(DATA / f"{int(row['year'])}.npz", rgb=f["rgb"], water=f["water"], roi=f["roi"],
                            item=np.array(row["item"]), date=np.array(row["date"]), platform=np.array(row["platform"]),
                            clear_share=np.array(row["clear_share"]), area_km2=np.array(row["area_km2"]),
                            area_km2_grid=np.array(f["area_km2_grid"]), valid_share_grid=np.array(f["valid_share"]),
                            transform=np.array(tuple(GRID_T)[:6]), crs=np.array("EPSG:4326"))
        return f["area_km2_grid"]

    with ThreadPoolExecutor(4) as pool:
        grid_areas = list(pool.map(one, [r for _, r in picked.iterrows()]))
    out = picked.copy()
    out["area_km2_grid"] = np.round(grid_areas, 4)
    out["days_from_1Oct"] = out["dt"]
    return out[["year", "date", "platform", "item", "clear_share", "valid_share", "area_km2", "area_km2_grid",
                "days_from_1Oct", "slc_off"]]


def main(argv: list) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "scenes").mkdir(parents=True, exist_ok=True)
    mask, _, bounds = reservoir()
    print(f"reservoir: {int(mask.sum())} JRC cells, bounds W {bounds[0]:.5f} S {bounds[1]:.5f} "
          f"E {bounds[2]:.5f} N {bounds[3]:.5f}", flush=True)
    if "--frames" not in argv:
        years = [int(a) for a in argv[argv.index("--years") + 1:]] if "--years" in argv else list(range(YEARS[0], YEARS[1] + 1))
        feats = []
        with ThreadPoolExecutor(4) as pool:
            for feats_y in pool.map(search, years):
                feats.extend(feats_y)
        with ThreadPoolExecutor(4) as pool:
            rows = list(pool.map(scene_json, feats))
        print(f"scanned {len(rows)} passes over the dam point ({sum(bool(r.get('accepted')) for r in rows)} accepted, "
              f"{sum('error' in r for r in rows)} failed to read)", flush=True)
    df = table()
    print(f"scenes covering the dam point (cache): {len(df)}; accepted: {int(df['accepted'].sum())}", flush=True)
    picked = choose(df)
    have = set(picked["year"].astype(int))
    missing = [y for y in range(YEARS[0], YEARS[1] + 1) if y not in have]
    print(f"frames: {len(picked)} years; no frame: {missing}", flush=True)
    frames = build_frames(picked)
    frames.to_csv(DATA / "frames.csv", index=False, float_format="%.4f")
    for old in DATA.glob("*.npz"):
        if old.stem.isdigit() and int(old.stem) not in have:
            old.unlink()                                       # no stale frame of an earlier rule
    for _, r in frames.iterrows():
        print(f"{int(r['year'])} {r['date']} {r['platform']} clear {r['clear_share']:.4f} "
              f"area {r['area_km2']:.4f} grid {r['area_km2_grid']:.4f} d {int(r['days_from_1Oct']):+d}"
              f"{' SLC' if r['slc_off'] else ''}", flush=True)
    print("frames written to", DATA / "frames.csv", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
