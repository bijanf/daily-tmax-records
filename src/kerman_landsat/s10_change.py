"""Step 8: where the green orchards appeared and disappeared, then (1987-1990) vs now (2022-2025).

A pixel is 'green' in a period when its late-summer median NDVI is at or above the threshold in at least
2 of the period's 4 years (OLI threshold t for 2022-2025; the TM-equivalent threshold of harmonisation.csv
for 1987-1990). Classes on the plain (box below 2,000 m): stable (green then and now), new (green now
only), lost (green then only: orchards that died, were abandoned, or are alive but too sparse/stressed to
pass the threshold now).
    python -I s10_change.py [t]          # default t = 0.20
Writes change_<t>.json, check/change_<t>_overview.png and check/change_<t>_crop_<name>.png."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HERE  # noqa: E402
from geom import masks, PIX_KM2  # noqa: E402
from view import ndvi, rgb, crop_ll, stretch  # noqa: E402

t = float(sys.argv[1]) if len(sys.argv) > 1 else 0.20
THEN, NOW = (1987, 1988, 1989, 1990), (2022, 2023, 2024, 2025)
H = pd.read_csv(HERE / "harmonisation.csv")
t_tm = float(H[np.isclose(H.t_oli, t)].t_tm_eq.iloc[0])
m = masks()
dem = np.load(HERE / "cache" / "dem.npz")["elev"]
plain = m["inbox"] & (dem < 2000)
then_n = sum((ndvi(y) >= t_tm).astype(np.uint8) for y in THEN)
now_n = sum((ndvi(y) >= t).astype(np.uint8) for y in NOW)
g_then, g_now = (then_n >= 2) & plain, (now_n >= 2) & plain
cls = dict(stable=g_then & g_now, new=g_now & ~g_then, lost=g_then & ~g_now)
res = dict(t_oli=t, t_tm_equivalent=t_tm, rule=">= threshold in at least 2 of the period's 4 years, plain below 2,000 m",
           then_green_km2=round(g_then.sum() * PIX_KM2, 1), now_green_km2=round(g_now.sum() * PIX_KM2, 1),
           **{f"{k}_km2": round(v.sum() * PIX_KM2, 1) for k, v in cls.items()})
(HERE / f"change_{t:.2f}.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))

im = rgb(2025)
LO, HI = (0.03, 0.03, 0.02), (0.40, 0.36, 0.32)
d = 4
base = stretch(im[:, ::d, ::d], LO, HI, 1.2) * 0.75
col = {"stable": (0.1, 0.8, 0.1), "new": (1.0, 0.85, 0.0), "lost": (0.9, 0.0, 0.9)}
ov = base.copy()
for k, c in col.items():
    ov[cls[k][::d, ::d]] = c
ov[~m["inbox"][::d, ::d]] *= 0.4
fig, ax = plt.subplots(figsize=(15, 11.5), dpi=100)
ax.imshow(ov)
ax.set_axis_off()
ax.set_title(f"green = stable, yellow = new, magenta = lost (NDVI >= {t:.2f} OLI / {t_tm:.3f} TM, >= 2 of 4 yrs); "
             f"background 2025")
fig.savefig(HERE / "check" / f"change_{t:.2f}_overview.png", bbox_inches="tight")
plt.close(fig)
for name, bb in {"anar": (55.15, 30.78, 55.40, 30.95), "rafsanjan_city": (55.90, 30.33, 56.08, 30.47),
                 "koshkuiyeh": (55.55, 30.45, 55.75, 30.60)}.items():
    c_rgb = stretch(crop_ll(im, *bb), LO, HI, 1.2) * 0.75
    c_ov = c_rgb.copy()
    for k, c in col.items():
        c_ov[crop_ll(cls[k], *bb)] = c
    fig, axs = plt.subplots(1, 2, figsize=(18, 8), dpi=90)
    axs[0].imshow(c_rgb / 0.75)
    axs[1].imshow(c_ov)
    for a in axs:
        a.set_axis_off()
    fig.suptitle(f"{name}: 2025 true colour | stable green, new yellow, lost magenta")
    fig.savefig(HERE / "check" / f"change_{t:.2f}_crop_{name}.png", bbox_inches="tight")
    plt.close(fig)
