"""Step 1: which WRS-2 path/rows cover the Rafsanjan box, and how far each footprint reaches.
    python -I s01_scout.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import search, path_row, tier  # noqa: E402

BOX = (55.3, 29.9, 56.5, 31.0)
feats = search(BOX, "2024-07-15", "2024-09-15")
seen = {}
for f in feats:
    pr = path_row(f)
    xs = [c[0] for c in f["geometry"]["coordinates"][0]] if f["geometry"]["type"] == "Polygon" else \
        [c[0] for poly in f["geometry"]["coordinates"] for c in poly[0]]
    ys = [c[1] for c in f["geometry"]["coordinates"][0]] if f["geometry"]["type"] == "Polygon" else \
        [c[1] for poly in f["geometry"]["coordinates"] for c in poly[0]]
    print(f["id"], f["properties"].get("platform"), f["properties"].get("eo:cloud_cover"),
          f"lon {min(xs):.2f}-{max(xs):.2f} lat {min(ys):.2f}-{max(ys):.2f}")
    seen.setdefault(pr, f["geometry"])
print(sorted(seen))
for pr, g in sorted(seen.items()):
    print(pr, g["coordinates"][0] if g["type"] == "Polygon" else g["coordinates"])
