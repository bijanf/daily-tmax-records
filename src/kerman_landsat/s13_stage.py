"""Step 13 (for the film): the Rafsanjan plain as one stage the camera moves over, on a single lon/lat grid with
square pixels of about 44 m: 55.30-56.15 E, 30.15-31.03 N (the box's north edge; its east edge stops at 56.15 E,
where the measured box's Zarand corner begins). For 1987 and 2025:

    stage/sat_1987.jpg, stage/sat_2025.jpg   true colour, the 1987 bands tone-matched onto 2025 exactly as
                                             s08_pictures.py does it (desert quantiles), the same brightness
                                             stretch for both (its lo/hi from the 2025 stage)
    stage/green_1987.png, stage/green_2025.png   white where the canopy was green in at least 2 of the period's
                                             4 years (s10_change.py's rule at OLI 0.20 and its TM equivalent;
                                             plain below 2,000 m), black elsewhere; the film tints them
    stage/stage.json                         the grid: west, north, dlon, dlat, width, height

Each stage pixel takes the bilinear value of the 30-m UTM grid at its centre (the green masks: nearest).
    python -I s13_stage.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HERE  # noqa: E402
from geom import masks, T, SHAPE  # noqa: E402
from view import ndvi, rgb  # noqa: E402
from s08_pictures import match, render, fill_nearest, THEN, NOW  # noqa: E402

W_, E_, S_, N_ = 55.30, 56.15, 30.15, 31.03
DLAT = 0.0004
DLON = DLAT / np.cos(np.radians(30.6))          # square pixels at the plain's middle latitude
OUT = HERE / "stage"


def grid():
    w = int(round((E_ - W_) / DLON))
    h = int(round((N_ - S_) / DLAT))
    lon = W_ + (np.arange(w) + 0.5) * DLON
    lat = N_ - (np.arange(h) + 0.5) * DLAT
    LON, LAT = np.meshgrid(lon, lat)
    x, y = Transformer.from_crs("EPSG:4326", "EPSG:32640", always_xy=True).transform(LON, LAT)
    col = (x - T.c) / T.a - 0.5                     # fractional row/column of the 30-m grid (pixel centres)
    row = (y - T.f) / T.e - 0.5
    return w, h, row, col


def sample(arr, row, col, order):
    return ndimage.map_coordinates(arr, [row, col], order=order, mode="nearest", cval=np.nan)


def main():
    OUT.mkdir(exist_ok=True)
    w, h, row, col = grid()
    m = masks()
    dem = np.load(HERE / "cache" / "dem.npz")["elev"]
    nd_t, nd_n = ndvi(THEN), ndvi(NOW)
    im_t, im_n = rgb(THEN), rgb(NOW)
    sel = m["inbox"] & (nd_t < 0.10) & (nd_n < 0.10) & (dem < 2000) & np.isfinite(im_t[0]) & np.isfinite(im_n[0])
    coef = match(im_t, im_n, sel)                   # the same tone match as the pictures of s08
    im_tm = np.stack([a + b * im_t[k] for k, (a, b) in enumerate(coef)])
    st_n = np.stack([sample(np.nan_to_num(fill_nearest(im_n)[k], nan=0), row, col, 1) for k in range(3)])
    st_t = np.stack([sample(np.nan_to_num(fill_nearest(im_tm)[k], nan=0), row, col, 1) for k in range(3)])
    lum = st_n.mean(axis=0)
    lo, hi = float(np.percentile(lum, 0.5)), float(np.percentile(lum, 99.8))
    for yr, arr in ((THEN, st_t), (NOW, st_n)):
        Image.fromarray(render(arr, lo, hi)).save(OUT / f"sat_{yr}.jpg", quality=93, optimize=True)
    with rasterio.open(HERE / "geotiff" / "change_0.20.tif") as r:
        ch = r.read(1)
    c = sample(ch.astype(np.float32), row, col, 0).astype(np.uint8)
    for yr, keep in ((THEN, (1, 3)), (NOW, (1, 2))):  # 1 stable, 2 new, 3 lost (green in >= 2 of the 4 years)
        g = np.isin(c, keep)
        Image.fromarray((g * 255).astype(np.uint8), "L").save(OUT / f"green_{yr}.png", optimize=True)
        print(yr, "green stage pixels", int(g.sum()), f"= {g.sum() * (DLAT * 111.195) * (DLON * 111.195 * np.cos(np.radians(30.6))):.0f} km2 (display grid)")
    meta = dict(west=W_, east=E_, south=S_, north=N_, dlon=DLON, dlat=DLAT, width=w, height=h, lo=lo, hi=hi,
                then=THEN, now=NOW, tone_coef=[list(map(float, k)) for k in coef])
    (OUT / "stage.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
