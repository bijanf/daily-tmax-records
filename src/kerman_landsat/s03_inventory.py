"""Step 2: inventory of every Landsat C2 L2 pass of WRS-2 path 161 and 160, row 039 (and path 161
row 038, for the box's top strip), between 15 July and 15 September of 1982-2025 (STAC items cached
in stac/<year>.json).
    python -I s03_inventory.py
Writes inventory.csv (one row per pass: id, date, platform, tier, path/row, scene cloud, SLC-off)."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import search, path_row, tier, slc_off, HERE  # noqa: E402

POINT_BOX = (55.95, 30.35, 56.05, 30.45)        # around Rafsanjan: any scene of row 039 of 160/161 hits it
TOP_BOX = (55.75, 31.00, 55.85, 31.05)          # the box's top strip: path 161 row 038
CACHE = HERE / "stac"
CACHE.mkdir(exist_ok=True)
KEEP = {"160039", "161039"}
KEEP_TOP = {"161038"}


def year_items(y: int) -> list:
    c = CACHE / f"{y}.json"
    if c.exists():
        return json.loads(c.read_text())
    feats = [f for f in search(POINT_BOX, f"{y}-07-15", f"{y}-09-15") if path_row(f) in KEEP]
    feats += [f for f in search(TOP_BOX, f"{y}-07-15", f"{y}-09-15") if path_row(f) in KEEP_TOP]
    slim = [dict(id=f["id"], properties=f["properties"], geometry=f["geometry"],
                 assets={k: {"href": v["href"]} for k, v in f["assets"].items()
                         if k in ("red", "green", "blue", "nir08", "swir16", "swir22", "qa_pixel")})
            for f in feats]
    c.write_text(json.dumps(slim))
    return slim


with ThreadPoolExecutor(4) as pool:
    allf = [f for fs in pool.map(year_items, range(1982, 2026)) for f in fs]
rows = [dict(id=f["id"], date=f["properties"]["datetime"][:10], platform=f["properties"].get("platform"),
             tier=tier(f), path_row=path_row(f), cloud=f["properties"].get("eo:cloud_cover"),
             slc_off=slc_off(f)) for f in allf]
df = pd.DataFrame(rows).sort_values(["date", "path_row"])
df.to_csv(HERE / "inventory.csv", index=False)
df["year"] = df.date.str[:4].astype(int)
summ = df.groupby(["year", "path_row"]).apply(
    lambda g: " ".join(f"{r.date[5:]}:{r.platform[-1]}{r.tier}:{r.cloud:.0f}" for r in g.itertuples()),
    include_groups=False)
pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 200)
pd.set_option("display.max_rows", 200)
print(summ.to_string())
