"""Step 10: two small GeoTIFFs on the box's 30-m UTM 40N grid (EPSG:32640), deflate-compressed.
  geotiff/green_years_0.20.tif  band 1: then (1987-1990) count of years with NDVI >= 0.1683 (TM equivalent of
                                OLI 0.20); band 2: now (2022-2025) count of years with NDVI >= 0.20 (OLI);
                                255 = outside the box
  geotiff/change_0.20.tif       0 = never green, 1 = stable, 2 = new, 3 = lost (s10_change.py rule: >= 2 of 4
                                years, plain below 2,000 m), 4 = above 2,000 m, 255 = outside the box
    python -I s12_geotiff.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HERE  # noqa: E402
from geom import masks, T, SHAPE, UTM  # noqa: E402
from view import ndvi  # noqa: E402

t = 0.20
H = pd.read_csv(HERE / "harmonisation.csv")
t_tm = float(H[np.isclose(H.t_oli, t)].t_tm_eq.iloc[0])
m = masks()
dem = np.load(HERE / "cache" / "dem.npz")["elev"]
then_n = sum((ndvi(y) >= t_tm).astype(np.uint8) for y in (1987, 1988, 1989, 1990))
now_n = sum((ndvi(y) >= t).astype(np.uint8) for y in (2022, 2023, 2024, 2025))
out = HERE / "geotiff"
out.mkdir(exist_ok=True)
prof = dict(driver="GTiff", height=SHAPE[0], width=SHAPE[1], dtype="uint8", crs=UTM, transform=T, nodata=255,
            compress="deflate", predictor=2, tiled=True)
b1, b2 = then_n.astype(np.uint8), now_n.astype(np.uint8)
b1[~m["inbox"]] = 255
b2[~m["inbox"]] = 255
with rasterio.open(out / "green_years_0.20.tif", "w", count=2, **prof) as d:
    d.write(b1, 1)
    d.write(b2, 2)
    d.set_band_description(1, f"years 1987-1990 with NDVI >= {t_tm:.4f} (TM, = OLI 0.20)")
    d.set_band_description(2, "years 2022-2025 with NDVI >= 0.20 (OLI)")
plain = m["inbox"] & (dem < 2000)
gt, gn = (then_n >= 2) & plain, (now_n >= 2) & plain
c = np.zeros(SHAPE, np.uint8)
c[gt & gn] = 1
c[gn & ~gt] = 2
c[gt & ~gn] = 3
c[m["inbox"] & (dem >= 2000)] = 4
c[~m["inbox"]] = 255
with rasterio.open(out / "change_0.20.tif", "w", count=1, **prof) as d:
    d.write(c, 1)
    d.set_band_description(1, "0 never, 1 stable, 2 new, 3 lost, 4 above 2000 m")
for f in out.glob("*.tif"):
    print(f, round(f.stat().st_size / 1e6, 2), "MB")
