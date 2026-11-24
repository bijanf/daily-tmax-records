"""Step 9 (checks): what the harmonised thresholds count, then and now, on 30-m crops: OLI 0.15 (cyan)
and 0.20 (yellow) on 2025; their TM equivalents (harmonisation.csv) on 1987. Pixels above 2,000 m are
not counted (dimmed outline not drawn).
    python -I s11_check_harm.py
Writes check/harm_<crop>.png."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HERE  # noqa: E402
from view import ndvi, rgb, crop_ll, stretch  # noqa: E402

H = pd.read_csv(HERE / "harmonisation.csv")
eq = {t: float(H[np.isclose(H.t_oli, t)].t_tm_eq.iloc[0]) for t in (0.15, 0.20)}
dem = np.load(HERE / "cache" / "dem.npz")["elev"]
CROPS = {"anar": (55.15, 30.78, 55.40, 30.95), "kabutarkhan_east": (56.15, 30.25, 56.42, 30.45),
         "desert_mid": (55.40, 30.60, 55.60, 30.75), "koshkuiyeh": (55.55, 30.45, 55.75, 30.60),
         "rafsanjan_city": (55.90, 30.33, 56.08, 30.47)}
LO, HI = (0.03, 0.03, 0.02), (0.40, 0.36, 0.32)
data = {y: (rgb(y), ndvi(y)) for y in (1987, 2025)}
for name, bb in CROPS.items():
    fig, axs = plt.subplots(1, 2, figsize=(20, 8.5), dpi=90)
    for ax, y in zip(axs, (1987, 2025)):
        im, nd = data[y]
        c = stretch(crop_ll(im, *bb), LO, HI, 1.2)
        n = np.nan_to_num(crop_ll(nd, *bb)) * (crop_ll(dem, *bb) < 2000)
        ax.imshow(c)
        for t, col in ((0.15, "cyan"), (0.20, "yellow")):
            tt = t if y == 2025 else eq[t]
            ax.contour(n >= tt, levels=[0.5], colors=col, linewidths=0.5)
        lab = "OLI 0.15 cyan / 0.20 yellow" if y == 2025 else \
            f"TM {eq[0.15]:.3f} cyan / {eq[0.20]:.3f} yellow (= OLI 0.15 / 0.20)"
        ax.set_title(f"{name} {y}: {lab}")
        ax.set_axis_off()
    fig.savefig(HERE / "check" / f"harm_{name}.png", bbox_inches="tight")
    plt.close(fig)
print("done", eq)
