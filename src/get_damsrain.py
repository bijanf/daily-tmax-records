"""DID THE NOVEMBER RAIN FILL TEHRAN'S DAMS? The open water of the five reservoirs that supply Tehran (Amirkabir/Karaj,
Taleqan, Latyan, Lar, Mamlu) in every Sentinel-2 pass of autumn 2026: the measured area before the storm of 14-17
Aban 1405 (5-8 Nov 2026) and after it, as the clear passes come in.

Measured data only: Sentinel-2 L2A (ESA Copernicus, via Microsoft's Planetary Computer with its anonymous token: the
helpers of get_urmia.py). The reservoirs are those of the per-dam reels (get_<dam>.py: JRC Global Surface Water's
extent, opened, the piece that holds the dam point), on each reel's fixed 1-arc-second grid. On that grid, from the
10-m and 20-m bands averaged into each cell: open water = MNDWI (B03, B11) > 0 and NIR (B08) < 0.10; clear = SCL not
no-data, saturated, cloud (medium, high), cirrus or snow, and not cloud shadow unless the cell is water by the test
above (SCL calls dark water "shadow" at times). Area = water / clear cells x the reservoir's area, for a pass with at
least 85 % of the reservoir clear (the same rule as the reels). Reflectance = (DN - 1000) / 10000 for processing
baseline 04.00 and later (ESA's BOA offset), DN / 10000 before.

    data/damsrain/s2_areas.csv       one row per pass and dam: date, clear share, water cells, area (km2), the
                                     reflectance scale used, the item
    data/damsrain/<dam>_<date>.npz   the pass on the dam's grid: RGB (0-1, NaN where not clear), water (1), land (0),
                                     not clear (255) inside the reservoir, 255 outside

    python -I src/get_damsrain.py                    # 15 Oct 2026 to today (cached passes are skipped)
"""

from __future__ import annotations

import datetime
import importlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.crs import CRS
from rasterio.env import Env
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import from_bounds

sys.path.insert(0, str(Path(__file__).resolve().parent))

import get_urmia as U  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "damsrain"
DAMS = ("karaj", "taleqan", "latyan", "lar", "mamlu")
START = "2026-10-15"
ACCEPT = 0.85
SCL_BAD = {0, 1, 8, 9, 10, 11}                   # no data, saturated, cloud medium/high, cirrus, snow
SCL_SHADOW = 3
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-2-l2a"   # the collection's own token
_token = {"token": None, "expiry": 0.0}
ENV = dict(GDAL_HTTP_MAX_RETRY="5", GDAL_HTTP_RETRY_DELAY="3", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
           CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif")


def signed(href: str) -> str:
    """The asset's URL with the Planetary Computer's anonymous token for Sentinel-2 L2A (renewed 5 min before expiry)."""
    if not _token["token"] or _token["expiry"] - time.time() < 300:
        d = U.get(SAS)
        e = datetime.datetime.strptime(d["msft:expiry"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        _token.update(token=d["token"], expiry=e.timestamp())
    return "/vsicurl/" + href + "?" + _token["token"]


def items(mod, end: str) -> list:
    d = U.get(U.STAC, {"collections": ["sentinel-2-l2a"], "bbox": list(mod.SEARCH), "limit": 200,
                       "datetime": f"{START}T00:00:00Z/{end}T23:59:59Z"})
    feats = d.get("features", [])
    assert len(feats) < 200
    return sorted((f for f in feats if mod.covers(f["geometry"], *mod.DAM)), key=lambda f: f["properties"]["datetime"])


def band(feat: dict, key: str, mod, resampling) -> np.ndarray:
    """One band on the dam's grid (float, NaN where no data)."""
    href = signed(feat["assets"][key]["href"])
    with Env(**ENV), rasterio.open(href) as src:
        b = transform_bounds(CRS.from_epsg(4326), src.crs, *mod.GRID, densify_pts=21)
        win = from_bounds(*b, transform=src.transform).round_offsets(op="floor").round_lengths(op="ceil")
        arr = src.read(1, window=win, boundless=True, fill_value=0).astype(np.float32)
        t = src.window_transform(win)
        crs = src.crs
    arr[arr == 0] = np.nan
    out = np.full(mod.SHAPE, np.nan, np.float32)
    reproject(source=arr, destination=out, src_transform=t, src_crs=crs, dst_transform=mod.GRID_T,
              dst_crs=CRS.from_epsg(4326), resampling=resampling, src_nodata=np.nan, dst_nodata=np.nan)
    return out


def measure(feat: dict, dam: str, mod, roi: np.ndarray) -> dict:
    p = feat["properties"]
    base = float(p.get("s2:processing_baseline", "0") or 0)
    off = 1000.0 if base >= 4.0 else 0.0
    refl = {k: (band(feat, k, mod, Resampling.average) - off) / 10000.0 for k in ("B02", "B03", "B04", "B08", "B11")}
    scl = band(feat, "SCL", mod, Resampling.nearest)
    g, s, n = refl["B03"], refl["B11"], refl["B08"]
    with np.errstate(invalid="ignore", divide="ignore"):
        mndwi = (g - s) / (g + s)
    water = (mndwi > 0) & (n < 0.10)
    valid = np.isfinite(scl) & np.isfinite(mndwi)
    bad = np.isin(np.nan_to_num(scl, nan=0).astype(int), list(SCL_BAD)) | ((scl == SCL_SHADOW) & ~water)
    clear = valid & ~bad
    roi_px = int(roi.sum())
    clear_px = int((clear & roi).sum())
    water_px = int((water & clear & roi).sum())
    lab = np.full(mod.SHAPE, 255, np.uint8)
    lab[roi & clear] = 0
    lab[roi & clear & water] = 1
    rgb = np.stack([refl["B04"], refl["B03"], refl["B02"]], -1)
    rgb[~clear] = np.nan
    date = p["datetime"][:10]
    np.savez_compressed(DATA / f"{dam}_{date}.npz", rgb=rgb.astype(np.float32), water=lab, roi=roi)
    return dict(dam=dam, date=date, item=feat["id"], baseline=base, offset=off,
                clear_share=round(clear_px / roi_px, 4), water_px=water_px, roi_px=roi_px,
                area_km2=round(water_px / clear_px * roi_px * mod.CELL_KM2, 3) if clear_px else float("nan"))


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    out = DATA / "s2_areas.csv"
    old = pd.read_csv(out) if out.exists() else pd.DataFrame(columns=["dam", "item"])
    done = set(zip(old["dam"], old["item"]))
    end = datetime.date.today().isoformat()
    rows = []
    for dam in DAMS:
        mod = importlib.import_module(f"get_{dam}")
        roi = mod.grid_roi()
        feats = items(mod, end)
        print(f"{dam}: {len(feats)} Sentinel-2 passes {START} to {end}; reservoir {int(roi.sum())} cells "
              f"({roi.sum() * mod.CELL_KM2:.2f} km2)", flush=True)
        seen = set()
        for f in feats:
            day = f["properties"]["datetime"][:10]
            if (dam, f["id"]) in done or (dam, day) in seen:   # one pass a day (a tile seam can give two items)
                continue
            seen.add((dam, day))
            try:
                r = measure(f, dam, mod, roi)
            except Exception as ex:                        # a pass that does not hold the reservoir
                print(f"   {day} {f['id']}: skipped ({ex!r})")
                continue
            rows.append(r)
            flag = "" if r["clear_share"] >= ACCEPT else "  (cloudy: not used)"
            print(f"   {day}  clear {r['clear_share']:6.1%}  water {r['area_km2']:7.3f} km2{flag}", flush=True)
    df = pd.concat([old, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(["dam", "item"])
    df.sort_values(["dam", "date"]).to_csv(out, index=False)
    print("saved", out, len(df), "rows")
    print(json.dumps({d: g[g.clear_share >= ACCEPT][["date", "area_km2"]].values.tolist()
                      for d, g in df.groupby("dam")}, indent=0))


if __name__ == "__main__":
    main()
