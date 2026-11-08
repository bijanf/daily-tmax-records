"""THE FIRST SNOW ON THE ALBORZ ABOVE TEHRAN'S DAMS: the data of the post-storm reel («باران سدها را پر کرد؟»).

The central Alborz from the Taleqan reservoir to Damavand (BOX), with the five dams that supply Tehran: the ground
(Copernicus DEM GLO-30, averaged to 3 arc-seconds) and Sentinel-2 L2A true colour of one clear pass before the storm
of 14-17 Aban 1405 (5-8 Nov 2026) and of the first clear pass after it (ESA Copernicus, via Microsoft's Planetary
Computer with its anonymous token). Snow, on 20-m bands averaged onto a 0.0005-degree grid: NDSI = (B03 - B11) /
(B03 + B11) > 0.4 and B08 > 0.11 (the MODIS/Sentinel-2 snow test), on cells that SCL does not call cloud, cirrus or
no data; the area is counted above 2,000 m. Reflectance = (DN - 1000) / 10000 for processing baseline 04.00 and later.

    data/alborzsnow/dem.npy               the ground (m) on the 3-arc-second grid of BOX, north up
    data/alborzsnow/tex_<date>.jpg        the true colour (TCI) mosaic of the pass on the 0.00025-degree grid
    data/alborzsnow/snow_<date>.npz       snow (bool), cloud (bool), valid (bool) on the 0.0005-degree grid
    data/alborzsnow/passes.json           per pass: date, items, clear share, snow area above 2,000 m (km2)

    python -I src/get_alborzsnow.py --date 2026-10-28      # one pass (the date in UTC)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from PIL import Image
from rasterio.crs import CRS
from rasterio.env import Env
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import from_bounds

sys.path.insert(0, str(Path(__file__).resolve().parent))

import get_damsrain as R  # noqa: E402
import get_subsidence as G  # noqa: E402
import get_urmia as U  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "alborzsnow"
BOX = (50.55, 35.45, 52.45, 36.40)                 # W, S, E, N: Taleqan to Damavand, Mamlu at the south edge
DEM_STEP, TEX_STEP, SNOW_STEP = 1 / 1200, 0.00025, 0.0005   # deg
TILES = [f"N{la}_00_E{lo:03d}_00" for la in (35, 36) for lo in (50, 51, 52)]
WGS = CRS.from_epsg(4326)
SNOW_MIN_M = 2000.0
SCL_BAD = {0, 1, 8, 9, 10}                         # no data, saturated, cloud medium/high, cirrus (snow 11 is kept)


def grid(step: float) -> tuple:
    w, s, e, n = BOX
    shape = (round((n - s) / step), round((e - w) / step))
    return Affine(step, 0, w, 0, -step, n), shape


def dem() -> np.ndarray:
    path = DATA / "dem.npy"
    if path.exists():
        return np.load(path)
    t, shape = grid(DEM_STEP)
    out = np.full(shape, np.nan, np.float32)
    token = None
    for tile in TILES:
        npy = G.DATA / f"dem_{tile}.npy"
        if not npy.exists():
            token = token or json.loads(G.get(G.TOKEN.format(30)))["token"]
            with Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"), \
                    rasterio.open("/vsicurl/" + G.GLO.format(30, 10, tile) + "?" + token) as src:
                np.save(npy, src.read(1))
            print("fetched", npy.name, flush=True)
        a = np.load(npy).astype(np.float32)
        la, lo = int(tile[1:3]), int(tile[8:11])
        ts = Affine(1 / a.shape[1], 0, lo, 0, -1 / a.shape[0], la + 1)
        part = np.full(shape, np.nan, np.float32)
        reproject(source=a, destination=part, src_transform=ts, src_crs=WGS, dst_transform=t, dst_crs=WGS,
                  resampling=Resampling.average, src_nodata=np.nan, dst_nodata=np.nan)
        out = np.where(np.isfinite(part), part, out)
    assert np.isfinite(out).all(), "a hole in the DEM"
    np.save(path, out)
    print("saved dem.npy", out.shape, f"{np.nanmin(out):.0f}-{np.nanmax(out):.0f} m", flush=True)
    return out


def items(date: str) -> list:
    d = U.get(U.STAC, {"collections": ["sentinel-2-l2a"], "bbox": list(BOX), "limit": 50,
                       "datetime": f"{date}T00:00:00Z/{date}T23:59:59Z"})
    return d.get("features", [])


def onto(feat: dict, key: str, t: Affine, shape: tuple, resampling, bands=1, dtype=np.float32) -> np.ndarray:
    """An asset of one item on our grid (0 = no data), read at about the grid's resolution."""
    out = np.zeros((bands,) + shape, dtype)
    with Env(**R.ENV), rasterio.open(R.signed(feat["assets"][key]["href"])) as src:
        b = transform_bounds(WGS, src.crs, *BOX, densify_pts=21)
        win = from_bounds(*b, transform=src.transform).round_offsets(op="floor").round_lengths(op="ceil")
        win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
        f = max(1, int(abs(t.a) * 111000 * math.cos(math.radians(36)) / src.res[0] / 1.5))   # decimate to ~grid
        arr = src.read(list(range(1, bands + 1)), window=win, out_shape=(bands, int(win.height // f), int(win.width // f)),
                       resampling=Resampling.average if resampling == Resampling.average else Resampling.nearest)
        wt = src.window_transform(win) * Affine.scale(win.width / arr.shape[2], win.height / arr.shape[1])
        reproject(source=arr, destination=out, src_transform=wt, src_crs=src.crs, dst_transform=t, dst_crs=WGS,
                  resampling=resampling, src_nodata=0, dst_nodata=0)
    return out if bands > 1 else out[0]


def one_pass(date: str) -> dict:
    feats = items(date)
    assert feats, f"no Sentinel-2 pass on {date}"
    tt, ts = grid(TEX_STEP)
    st, ss = grid(SNOW_STEP)
    tex = np.zeros((3,) + ts, np.uint8)
    b = {k: np.zeros(ss, np.float32) for k in ("B03", "B08", "B11", "SCL")}
    base = {}
    for f in feats:
        print("  ", f["id"], f["properties"].get("eo:cloud_cover"), flush=True)
        v = onto(f, "visual", tt, ts, Resampling.average, bands=3, dtype=np.uint8)
        hole = tex.sum(0) == 0
        tex[:, hole] = v[:, hole]
        off = 1000.0 if float(f["properties"].get("s2:processing_baseline", "0") or 0) >= 4.0 else 0.0
        base[f["id"]] = off
        for k in b:
            a = onto(f, k, st, ss, Resampling.nearest if k == "SCL" else Resampling.average)
            if k != "SCL":
                a = np.where(a > 0, (a - off) / 10000.0, 0)
            gap = b[k] == 0
            b[k][gap] = a[gap]
    Image.fromarray(np.moveaxis(tex, 0, -1)).save(DATA / f"tex_{date}.jpg", quality=92)
    valid = (b["SCL"] > 0) & (b["B03"] != 0) & (b["B11"] != 0)
    cloud = valid & np.isin(b["SCL"].astype(int), list(SCL_BAD))
    with np.errstate(invalid="ignore", divide="ignore"):
        ndsi = (b["B03"] - b["B11"]) / (b["B03"] + b["B11"])
    snow = valid & ~cloud & (ndsi > 0.4) & (b["B08"] > 0.11)
    np.savez_compressed(DATA / f"snow_{date}.npz", snow=snow, cloud=cloud, valid=valid)
    h = dem()
    hz = np.full(ss, np.nan, np.float32)
    reproject(source=h, destination=hz, src_transform=grid(DEM_STEP)[0], src_crs=WGS, dst_transform=st, dst_crs=WGS,
              resampling=Resampling.bilinear)
    lat = BOX[3] - (np.arange(ss[0]) + 0.5) * SNOW_STEP
    cell = (SNOW_STEP * 111320 * np.cos(np.radians(lat)))[:, None] * (SNOW_STEP * 110574) / 1e6 * np.ones(ss)
    high = hz >= SNOW_MIN_M
    rec = dict(date=date, items=sorted(base), clear_share_high=round(float((valid & ~cloud & high).sum() / max(1, (valid & high).sum())), 3),
               snow_km2_high=round(float(cell[snow & high].sum()), 1), cloud_km2_high=round(float(cell[cloud & high].sum()), 1),
               high_km2=round(float(cell[high].sum()), 1))
    log = DATA / "passes.json"
    old = json.loads(log.read_text()) if log.exists() else {}
    old[date] = rec
    log.write_text(json.dumps(old, indent=1))
    return rec


def scl(date: str) -> np.ndarray:
    """SCL of the pass on the snow grid (cached as scl_<date>.npy)."""
    path = DATA / f"scl_{date}.npy"
    if path.exists():
        return np.load(path)
    st, ss = grid(SNOW_STEP)
    out = np.zeros(ss, np.float32)
    for f in items(date):
        a = onto(f, "SCL", st, ss, Resampling.nearest)
        gap = out == 0
        out[gap] = a[gap]
    np.save(path, out.astype(np.uint8))
    return out.astype(np.uint8)


def composite(dates: list, name: str) -> dict:
    """A cloud-free texture and snow map from several passes: each cell from the first pass in `dates` (the order
    given: the nearest to the storm first) where SCL calls it clear (not no data, saturated, cloud shadow, cloud,
    cirrus), cloud masks grown by 2 cells (about 100 m) for the fuzzy edges. Writes tex_<name>.jpg, snow_<name>.npz
    and the share of the area each pass gives."""
    from scipy import ndimage
    tt, ts = grid(TEX_STEP)
    st, ss = grid(SNOW_STEP)
    tex = np.zeros(ts + (3,), np.uint8)
    snow = np.zeros(ss, bool)
    filled = np.zeros(ss, bool)
    share = {}
    for d in dates:
        s = scl(d)
        bad = np.isin(s, [0, 1, 3, 8, 9, 10])
        bad = ndimage.binary_dilation(bad, iterations=2)
        ok = ~bad & ~filled
        t = np.asarray(Image.open(DATA / f"tex_{d}.jpg").convert("RGB"))
        okt = np.repeat(np.repeat(ok, 2, 0), 2, 1)[:ts[0], :ts[1]]
        tex[okt] = t[okt]
        z = np.load(DATA / f"snow_{d}.npz")
        snow[ok] = z["snow"][ok]
        filled |= ok
        share[d] = round(float(ok.mean()), 3)
    left = ~filled                                    # cloudy in every pass: the first pass as it is
    lt = np.repeat(np.repeat(left, 2, 0), 2, 1)[:ts[0], :ts[1]]
    tex[lt] = np.asarray(Image.open(DATA / f"tex_{dates[0]}.jpg").convert("RGB"))[lt]
    share["cloudy_in_all"] = round(float(left.mean()), 4)
    Image.fromarray(tex).save(DATA / f"tex_{name}.jpg", quality=92)
    np.savez_compressed(DATA / f"snow_{name}.npz", snow=snow, cloud=left, valid=np.ones(ss, bool))
    h = dem()
    hz = np.full(ss, np.nan, np.float32)
    reproject(source=h, destination=hz, src_transform=grid(DEM_STEP)[0], src_crs=WGS, dst_transform=st, dst_crs=WGS,
              resampling=Resampling.bilinear)
    lat = BOX[3] - (np.arange(ss[0]) + 0.5) * SNOW_STEP
    cell = (SNOW_STEP * 111320 * np.cos(np.radians(lat)))[:, None] * (SNOW_STEP * 110574) / 1e6 * np.ones(ss)
    high = hz >= SNOW_MIN_M
    rec = dict(name=name, dates=dates, share=share, snow_km2_high=round(float(cell[snow & high].sum()), 1),
               cloudy_in_all_km2_high=round(float(cell[left & high].sum()), 1))
    log = DATA / "passes.json"
    old = json.loads(log.read_text()) if log.exists() else {}
    old[name] = rec
    log.write_text(json.dumps(old, indent=1))
    return rec


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", help="the pass's date (UTC), YYYY-MM-DD")
    ap.add_argument("--composite", help="comma-separated dates, nearest to the storm first (fetched already)")
    ap.add_argument("--name", default="before")
    args = ap.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    dem()
    if args.composite:
        print(json.dumps(composite(args.composite.split(","), args.name), indent=1))
    else:
        print(json.dumps(one_pass(args.date), indent=1))


if __name__ == "__main__":
    main()
