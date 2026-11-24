"""Step 1b: a clear late-summer 2024 true-colour and NDVI overview of a wide box around the
Rafsanjan plain at ~110 m (COG overviews, decimate 4), from paths 161 and 160, to place the box.
    python -I s02_overview.py
Writes overview/overview_2024_rgb.png, overview/overview_2024_ndvi.png, overview/overview_2024.npz"""
import sys
import warnings
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import search, read_window, WGS, SCALE, OFFSET, HERE, to_grid  # noqa: E402

WIDE = (54.9, 29.7, 56.9, 31.4)
RES = 0.001
T = from_origin(WIDE[0], WIDE[3], RES, RES)
SHAPE = (round((WIDE[3] - WIDE[1]) / RES), round((WIDE[2] - WIDE[0]) / RES))
OUT = HERE / "overview"
OUT.mkdir(exist_ok=True)
ITEMS = ["LC08_L2SP_161039_20240808_02_T1", "LC08_L2SP_161038_20240808_02_T1",
         "LC09_L2SP_160039_20240809_02_T1", "LC09_L2SP_160038_20240809_02_T1"]

feats = {f["id"]: f for f in search(WIDE, "2024-08-07", "2024-08-10")}
layers = {}
for it in ITEMS:
    f = feats[it]
    d, t, crs = read_window(f, ["red", "green", "blue", "nir08", "qa_pixel"], WIDE, decimate=4)
    g = {k: to_grid(v, t, crs, T, WGS, SHAPE) for k, v in d.items()}
    ok = (g["red"] > 0) & (g["nir08"] > 0) & ((g["qa_pixel"] & 0b11110) == 0)
    sr = np.stack([np.where(ok, g[b].astype(np.float32) * SCALE + OFFSET, np.nan) for b in ("red", "green", "blue", "nir08")])
    layers[it] = sr
    print(it, "valid share", ok.mean().round(3), flush=True)

mos = np.full((4,) + SHAPE, np.nan, np.float32)
for it in ITEMS:                                  # path 161 first, then 160 fills
    mos = np.where(np.isnan(mos), layers[it], mos)
np.savez_compressed(OUT / "overview_2024.npz", sr=mos.astype(np.float16), transform=np.array(tuple(T)[:6]))
# path-161-only coverage mask, for the report
p161 = ~np.isnan(np.where(np.isnan(layers[ITEMS[0]]), layers[ITEMS[1]], layers[ITEMS[0]])[0])
p160 = ~np.isnan(np.where(np.isnan(layers[ITEMS[2]]), layers[ITEMS[3]], layers[ITEMS[2]])[0])

rgb = mos[:3].transpose(1, 2, 0)
lo, hi = np.nanpercentile(rgb, 1), np.nanpercentile(rgb, 99.5)
img = np.clip((rgb - lo) / (hi - lo), 0, 1) ** (1 / 1.3)
img = np.nan_to_num(img, nan=0)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    ndvi = (mos[3] - mos[0]) / (mos[3] + mos[0])
ext = (WIDE[0], WIDE[2], WIDE[1], WIDE[3])
places = {"Rafsanjan": (55.99, 30.40), "Anar": (55.27, 30.87)}
for name, arr, kw in (("rgb", img, {}), ("ndvi", ndvi, dict(cmap="RdYlGn", vmin=0, vmax=0.5))):
    fig, ax = plt.subplots(figsize=(16, 13.6), dpi=110)
    ax.imshow(arr, extent=ext, interpolation="nearest", **kw)
    ax.contour(np.linspace(WIDE[0], WIDE[2], SHAPE[1]), np.linspace(WIDE[3], WIDE[1], SHAPE[0]), p161.astype(float),
               levels=[0.5], colors="cyan", linewidths=1)
    ax.contour(np.linspace(WIDE[0], WIDE[2], SHAPE[1]), np.linspace(WIDE[3], WIDE[1], SHAPE[0]), p160.astype(float),
               levels=[0.5], colors="magenta", linewidths=1)
    for nm, (x, y) in places.items():
        ax.plot(x, y, "w+", ms=12)
        ax.text(x + 0.02, y + 0.02, nm, color="w", fontsize=10)
    ax.set_xticks(np.arange(55.0, 56.91, 0.1), minor=True)
    ax.set_yticks(np.arange(29.7, 31.41, 0.1), minor=True)
    ax.grid(which="both", color="w", alpha=0.25, lw=0.5)
    ax.set_title(f"2024-08-08/09 Landsat 8/9 {name}; cyan = path 161 data edge, magenta = path 160")
    fig.savefig(OUT / f"overview_2024_{name}.png", bbox_inches="tight")
    plt.close(fig)
print("done")
