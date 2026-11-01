"""The Zayandeh Rud through Isfahan from Landsat: in which months water was seen flowing, every
year since 1986, and the late-summer picture of the city's river reach.

    data/zayandeh/channel.npz          the river channel on the 30-m grid: JRC Global Surface
                                        Water's extent (any water 1984-2021), its largest piece
    data/zayandeh/scenes/<item>.json   per Landsat pass over the box: date, platform, path/row, the
                                        share of the channel seen clear, and the share of that
                                        which is open water
    data/zayandeh/calendar.csv         per Persian year and month: the passes that count, how many
                                        saw the river flowing, and the largest open-water share
    data/zayandeh/colour_<year>.npz    the late-summer (20 Aug-10 Oct) true-colour picture

Landsat Collection 2 Level-2 (USGS) from Microsoft's Planetary Computer with its anonymous token
(the helpers of get_urmia.py), paths 164 and 163, row 037, both covering the whole box. Open water
= MNDWI > 0 and NIR < 0.10 (the rule that matched JRC's monthly maps at Lake Urmia, fact check of
27 Oct 2026). A pass counts when at least CLEAR of the channel is in the scene and clear of cloud,
shadow and cirrus (QA_PIXEL); it saw the river FLOWING when at least FLOW of the clear channel is
open water (pools behind the weirs and bridges stay below that: see the histogram in the log).
The pictures leave out Landsat 7 after its scan-line failure (its gaps stripe a 150-m river).

    python -I src/get_zayandeh.py                    # every year (passes are cached)
    python -I src/get_zayandeh.py --years 1995 2025  # some years only
"""

from __future__ import annotations

import json
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.crs import CRS
from rasterio.env import Env
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import Window, from_bounds
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from get_urmia import ENV, STAC, get, signed, slc_off  # noqa: E402  (keyless Landsat helpers)
from wateryear import farvardin1  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "zayandeh"
BOX = (51.630, 32.585, 51.715, 32.705)              # W, S, E, N: Isfahan's river, Si-o-se Pol mid-box
GRID = 0.0003                                       # deg, about 30 m (Landsat's own resolution)
YEARS = (1986, 2026)
PATH_ROWS = ("164037", "163037")
JRC = "https://storage.googleapis.com/global-surface-water/downloads2021/extent/extent_50E_40Nv1_4_2021.tif"
CLEAR = 0.50                                        # share of the channel in the scene and clear: a pass counts
FLOW = 0.30                                         # share of the clear channel that is open water: flowing
WINDOW = ("08-20", "10-10")                         # the pictures: late summer, as at Lake Urmia
SCALE, OFFSET = 0.0000275, -0.2                     # Collection 2 surface reflectance


def grid():
    w, s, e, n = BOX
    return from_origin(w, n, GRID, GRID), (int(round((n - s) / GRID)), int(round((e - w) / GRID)))


def channel() -> np.ndarray:
    """The river channel: JRC's extent (any water 1984-2021) on the grid, its largest connected piece."""
    cache = DATA / "channel.npz"
    if cache.exists():
        return np.load(cache)["channel"]
    t, shape = grid()
    with Env(**ENV), rasterio.open("/vsicurl/" + JRC) as src:
        win = from_bounds(BOX[0] - 0.01, BOX[1] - 0.01, BOX[2] + 0.01, BOX[3] + 0.01,
                          transform=src.transform).round_offsets().round_lengths()
        ext, et = src.read(1, window=win), src.window_transform(win)
    out = np.zeros(shape, np.uint8)
    reproject((ext == 1).astype(np.uint8), out, src_transform=et, src_crs=CRS.from_epsg(4326), dst_transform=t,
              dst_crs=CRS.from_epsg(4326), resampling=Resampling.max)       # any water in the cell
    lab, n = ndimage.label(out == 1, structure=np.ones((3, 3)))
    sizes = ndimage.sum(np.ones(shape), lab, range(1, n + 1))
    ch = lab == 1 + int(np.argmax(sizes))
    DATA.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, channel=ch)
    return ch


def search(year: int, cloud: float = 60) -> list:
    d = get(STAC, {"collections": ["landsat-c2-l2"], "bbox": list(BOX), "limit": 400,
                   "datetime": f"{year}-01-01T00:00:00Z/{year}-12-31T23:59:59Z"})
    return [f for f in d.get("features", []) if f["id"].split("_")[2] in PATH_ROWS
            and (f["properties"].get("eo:cloud_cover") or 0) <= cloud]


def read(feat, bands) -> dict:
    """The scene's bands over the box on the grid (nearest neighbour; 0 where the scene has no data)."""
    t, shape = grid()
    out = {}
    with Env(**ENV):
        for band in bands:
            with rasterio.open(signed(feat["assets"][band]["href"])) as src:
                b = transform_bounds(CRS.from_epsg(4326), src.crs, *BOX)
                win = from_bounds(*b, transform=src.transform).round_offsets(op="floor").round_lengths(op="ceil")
                win = win.intersection(Window(0, 0, src.width, src.height))
                a = src.read(1, window=win)
                dst = np.zeros(shape, a.dtype)
                reproject(a, dst, src_transform=src.window_transform(win), src_crs=src.crs, dst_transform=t,
                          dst_crs=CRS.from_epsg(4326), resampling=Resampling.nearest, src_nodata=0, dst_nodata=0)
                out[band] = dst
    return out


def sr(a: np.ndarray) -> np.ndarray:
    return a.astype(np.float32) * SCALE + OFFSET


def process(feat) -> dict:
    p = feat["properties"]
    ch = channel()
    b = read(feat, ("green", "swir16", "nir08", "qa_pixel"))
    valid = (b["green"] > 0) & (b["swir16"] > 0) & (b["nir08"] > 0)
    clear = valid & ((b["qa_pixel"] & 0b11110) == 0)                 # dilated cloud, cirrus, cloud, shadow
    g, s, n = sr(b["green"]), sr(b["swir16"]), sr(b["nir08"])
    water = clear & ((g - s) / np.where(g + s == 0, 1, g + s) > 0) & (n < 0.10)
    seen = int((clear & ch).sum())
    return dict(item=feat["id"], date=p["datetime"][:10], platform=p.get("platform"),
                path_row=feat["id"].split("_")[2], inbox=round(float((valid & ch).sum() / ch.sum()), 4),
                clear=round(seen / float(ch.sum()), 4), wet=round(float((water & ch).sum()) / max(seen, 1), 4))


def persian(d: date) -> tuple[int, int]:
    """Persian year and month (1 = Farvardin) of a Gregorian date."""
    jy = d.year - 621 if d >= farvardin1(d.year - 621) else d.year - 622
    n = (d - farvardin1(jy)).days
    return jy, (n // 31 + 1 if n < 186 else min(12, (n - 186) // 30 + 7))


def table() -> pd.DataFrame:
    rows = [json.loads(f.read_text()) for f in sorted((DATA / "scenes").glob("*.json"))]
    df = pd.DataFrame([r for r in rows if not r.get("error")])
    df["date"] = pd.to_datetime(df["date"])
    pm = [persian(d) for d in df["date"].dt.date]
    df["jy"], df["jm"] = [x[0] for x in pm], [x[1] for x in pm]
    df["counts"] = df["clear"] >= CLEAR
    df["flowing"] = df["counts"] & (df["wet"] >= FLOW)
    return df


def calendar(df: pd.DataFrame) -> pd.DataFrame:
    g = df[df["counts"]].groupby(["jy", "jm"])
    return pd.DataFrame({"passes": g.size(), "flowing": g["flowing"].sum().astype(int), "wet_max": g["wet"].max()})


def picture(year: int) -> None:
    """The late-summer river reach in true colour: the per-pixel median of the clear passes."""
    t, shape = grid()
    window = [f for f in search(year, cloud=80)
              if f"{year}-{WINDOW[0]}" <= f["properties"]["datetime"][:10] <= f"{year}-{WINDOW[1]}"]
    feats = [f for f in window if not slc_off(f)]
    striped = not feats                                    # 2004-2012: only Landsat 7 after its failure;
    if striped:                                            # its gaps move from pass to pass, so the
        feats = window                                     # median of several fills them
    stack, items = [], []
    for f in feats:
        b = read(f, ("red", "green", "blue", "qa_pixel"))
        clear = (b["red"] > 0) & (b["green"] > 0) & (b["blue"] > 0) & ((b["qa_pixel"] & 0b11110) == 0)
        if clear.mean() < (0.3 if striped else 0.6):
            continue
        stack.append(np.stack([np.where(clear, sr(b[k]), np.nan) for k in ("red", "green", "blue")]))
        items.append(f["id"])
    if not stack:
        print(f"picture {year}: no clear pass", flush=True)
        return
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        med = np.nanmedian(np.stack(stack), axis=0)
    if striped and len(items) < 3:
        print(f"picture {year}: only {len(items)} striped passes, left out", flush=True)
        return
    np.savez_compressed(DATA / f"colour_{year}.npz", rgb=med.astype(np.float16), items=np.array(items),
                        striped=striped)
    print(f"picture {year}: {len(items)} {'striped ' if striped else ''}passes, unseen "
          f"{100 * np.isnan(med[0]).mean():.1f} % (channel {100 * np.isnan(med[0])[channel()].mean():.1f} %)", flush=True)


def one_year(year: int) -> None:
    for f in search(year):
        path = DATA / "scenes" / f"{f['id']}.json"
        if path.exists():
            continue
        for attempt in range(3):
            try:
                r = process(f)
                break
            except Exception as ex:                      # a dropped connection costs one try
                r = dict(item=f["id"], error=repr(ex)[:300])
        path.write_text(json.dumps(r))
    picture(year)
    print(year, "done", flush=True)


def main(years: list) -> None:
    (DATA / "scenes").mkdir(parents=True, exist_ok=True)
    ch = channel()
    print(f"channel: {int(ch.sum())} cells of about 30 m ({ch.sum() * 0.0009:.1f} km2)", flush=True)
    with ThreadPoolExecutor(4) as pool:
        list(pool.map(one_year, years))
    df = table()
    calendar(df).to_csv(DATA / "calendar.csv")
    c = df[df["counts"]]
    hist = np.histogram(c["wet"], bins=[0, .05, .1, .2, .3, .4, .5, .7, 1.01])[0]
    print(f"passes: {len(df)}, counted {len(c)}, flowing {int(c['flowing'].sum())}; wet-share histogram "
          f"(0,.05,.1,.2,.3,.4,.5,.7,1): {hist.tolist()}")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--years":
        main([int(a) for a in sys.argv[2:]])
    elif len(sys.argv) > 2 and sys.argv[1] == "--pictures":
        for y in [int(a) for a in sys.argv[2:]]:
            picture(y)
    else:
        main(list(range(YEARS[0], YEARS[1] + 1)))
