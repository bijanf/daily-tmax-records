"""Step 4 (checks): quick-look PNGs of what each NDVI threshold counts, for a then and a now year.
    python -I s05_inspect.py 1987 2025
Writes check/overview_<year>.png (box, decimated), check/crop_<name>_<year>.png (30-m crops with the
counted pixels outlined: yellow >= 0.20, orange >= 0.25, red >= 0.30) and check/ndvi_hist.png."""
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HERE  # noqa: E402
from geom import masks, BOX  # noqa: E402
from view import ndvi, rgb, crop_ll, stretch  # noqa: E402

OUT = HERE / "check"
OUT.mkdir(exist_ok=True)
CROPS = {                       # name: (W, S, E, N)
    "rafsanjan_city": (55.90, 30.33, 56.08, 30.47),
    "koshkuiyeh": (55.55, 30.45, 55.75, 30.60),
    "anar": (55.15, 30.78, 55.40, 30.95),
    "bahreman_nough": (55.62, 30.82, 55.82, 30.98),
    "kabutarkhan_east": (56.15, 30.25, 56.42, 30.45),
    "volcanic_fan_sw": (55.15, 30.18, 55.45, 30.40),
    "desert_mid": (55.40, 30.60, 55.60, 30.75),
}
years = [int(a) for a in sys.argv[1:]] or [1987, 2025]
m = masks()
LO, HI = (0.03, 0.03, 0.02), (0.40, 0.36, 0.32)

fig, ax = plt.subplots(figsize=(8, 5), dpi=120)
for y in years:
    nd = ndvi(y)
    v = nd[m["inbox"] & np.isfinite(nd)]
    ax.hist(v, bins=np.arange(-0.1, 0.7, 0.005), histtype="step", label=str(y), log=True)
for t in (0.2, 0.25, 0.3):
    ax.axvline(t, color="k", lw=0.5)
ax.set_xlabel("median late-summer NDVI"); ax.set_ylabel("pixels"); ax.legend()
fig.savefig(OUT / "ndvi_hist.png", bbox_inches="tight"); plt.close(fig)

for y in years:
    nd = ndvi(y)
    im = rgb(y)
    dec = 4
    sm = stretch(im[:, ::dec, ::dec], LO, HI, 1.2)
    ov = sm.copy()
    ndd = nd[::dec, ::dec]
    ov[ndd >= 0.20] = [1, 1, 0]
    ov[ndd >= 0.25] = [1, 0.55, 0]
    ov[ndd >= 0.30] = [1, 0, 0]
    ov[~m["inbox"][::dec, ::dec]] *= 0.4
    fig, axs = plt.subplots(1, 2, figsize=(22, 9), dpi=110)
    axs[0].imshow(sm); axs[1].imshow(ov)
    for a in axs:
        a.contour(m["ze"][::dec, ::dec].astype(float), levels=[0.5], colors="c", linewidths=0.6)
        a.set_axis_off()
    axs[0].set_title(f"{y} median true colour (zone E right of cyan line: path 160)")
    axs[1].set_title("counted: yellow NDVI>=0.20, orange >=0.25, red >=0.30; dimmed = outside box")
    fig.savefig(OUT / f"overview_{y}.png", bbox_inches="tight"); plt.close(fig)
    for name, bb in CROPS.items():
        c_rgb = stretch(crop_ll(im, *bb), LO, HI, 1.2)
        c_nd = crop_ll(nd, *bb)
        fig, axs = plt.subplots(1, 3, figsize=(24, 8), dpi=100)
        axs[0].imshow(c_rgb)
        axs[1].imshow(c_rgb)
        for t, col in ((0.20, "yellow"), (0.25, "orange"), (0.30, "red")):
            axs[1].contour(np.nan_to_num(c_nd) >= t, levels=[0.5], colors=col, linewidths=0.5)
        h = axs[2].imshow(c_nd, cmap="RdYlGn", vmin=0, vmax=0.5)
        plt.colorbar(h, ax=axs[2], fraction=0.04)
        for a in axs:
            a.set_axis_off()
        fig.suptitle(f"{name} {y} {bb}")
        fig.savefig(OUT / f"crop_{name}_{y}.png", bbox_inches="tight"); plt.close(fig)
    print(y, "done", flush=True)
