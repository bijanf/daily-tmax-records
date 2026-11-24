"""Step 4b: terrain on the box grid, to tell the plain's orchards from vegetation in mountain wadis.
Copernicus DEM GLO-30 (Planetary Computer collection cop-dem-glo-30, anonymous token), bilinear onto
the 30-m UTM grid; slope from the 3x3 gradient after a 3x3 mean (degrees).
    python -I s06_dem.py
Writes cache/dem.npz (elev m as int16, slope deg as uint8*4)."""
import sys
import datetime
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.env import Env
from rasterio.warp import Resampling, reproject
from rasterio.windows import from_bounds
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ENV, HERE, WGS, get, search  # noqa: E402
from geom import T, SHAPE, BOX, UTM  # noqa: E402

TOK = "https://planetarycomputer.microsoft.com/api/sas/v1/token/cop-dem-glo-30"
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"

d = get(STAC, {"collections": ["cop-dem-glo-30"], "bbox": [BOX[0] - 0.05, BOX[1] - 0.05, BOX[2] + 0.05, BOX[3] + 0.05],
               "limit": 50})
tok = get(TOK)["token"]
elev = np.full(SHAPE, np.nan, np.float32)
for f in d["features"]:
    href = f["assets"]["data"]["href"]
    with Env(**ENV), rasterio.open("/vsicurl/" + href + "?" + tok) as s:
        win = from_bounds(BOX[0] - 0.05, BOX[1] - 0.05, BOX[2] + 0.05, BOX[3] + 0.05, transform=s.transform)
        win = win.round_offsets(op="floor").round_lengths(op="ceil").intersection(
            rasterio.windows.Window(0, 0, s.width, s.height))
        a = s.read(1, window=win).astype(np.float32)
        tmp = np.full(SHAPE, np.nan, np.float32)
        reproject(a, tmp, src_transform=s.window_transform(win), src_crs=s.crs, dst_transform=T, dst_crs=UTM,
                  resampling=Resampling.bilinear, src_nodata=np.nan, dst_nodata=np.nan)
        elev = np.where(np.isnan(elev), tmp, elev)
    print(f["id"], flush=True)
sm = ndimage.uniform_filter(np.nan_to_num(elev, nan=np.nanmean(elev)), 3)
gy, gx = np.gradient(sm, 30.0)
slope = np.degrees(np.arctan(np.hypot(gx, gy)))
np.savez_compressed(HERE / "cache" / "dem.npz", elev=np.nan_to_num(elev, nan=-9999).astype(np.int16),
                    slope4=np.clip(slope * 4, 0, 255).astype(np.uint8))
print("elev range", np.nanmin(elev), np.nanmax(elev), "unseen", int(np.isnan(elev).sum()))
