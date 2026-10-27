"""Daily rain over Iran and Tehran province from CHIRPS v3.0, read on the PIK cluster.

    data/chirps/chirps_iran_daily.csv   product (rnl, sat), date, iran, tehran (mm/day): the
                                         cos-latitude mean of CHIRPS v3.0's 0.05 deg cells whose
                                         centres lie inside Natural Earth's 50 m Iran and 10 m
                                         Tehran province

CHIRPS v3.0 (Climate Hazards Center, UC Santa Barbara) is at heart a 5-day and monthly product;
its daily values spread those totals over the days by ERA5's day-to-day pattern ("rnl") or
IMERG's ("sat", from 1998). Monthly and seasonal sums are the same in both. The cluster copy:
/p/projects/climate_data_central/observation/CHIRPS/v3.0/R05/{rnl,sat}. The masks are built here
(enso.country_mask, pyshp; no shapely next to netCDF) and sent with a small reader that runs on
the cluster read-only over ssh (alias "hpc") and prints the daily means; nothing is written there.

    python -I src/get_chirps.py            # about 15 minutes for both products, 1981 to now
"""

from __future__ import annotations

import base64
import json
import subprocess
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import shapefile  # noqa: E402
from matplotlib.path import Path as Outline  # noqa: E402

import enso  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "chirps" / "chirps_iran_daily.csv"
BASE = "/p/projects/climate_data_central/observation/CHIRPS/v3.0/R05"
BOX = (24.0, 41.0, 43.0, 64.0)                      # S, N, W, E: Iran with a margin
PROVINCES = Path.home() / ".local/share/cartopy/shapefiles/natural_earth/cultural/ne_10m_admin_1_states_provinces_lakes.shp"
CLUSTER_PY = "/home/fallah/.local/lib/python3.9/site-packages"   # netCDF4 on the cluster's python3

GRID = f"""
import sys, json; sys.path.insert(0, "{CLUSTER_PY}")
import netCDF4 as nc, numpy as np
d = nc.Dataset("{BASE}/rnl/chirps-v3.0.rnl.1981.days_p05.nc")
lat, lon = d["latitude"][:], d["longitude"][:]
i = np.where((lat >= {BOX[0]}) & (lat <= {BOX[1]}))[0]; j = np.where((lon >= {BOX[2]}) & (lon <= {BOX[3]}))[0]
print(json.dumps(dict(lat=lat[i].tolist(), lon=lon[j].tolist(), i0=int(i[0]), i1=int(i[-1]) + 1, j0=int(j[0]), j1=int(j[-1]) + 1)))
"""

READER = """
import sys, base64, zlib; sys.path.insert(0, "%(py)s")
import netCDF4 as nc, numpy as np
shape = %(shape)r
masks = {k: np.unpackbits(np.frombuffer(zlib.decompress(base64.b64decode(v)), np.uint8))[:shape[0] * shape[1]].reshape(shape).astype(bool)
         for k, v in %(masks)r.items()}
w = np.cos(np.deg2rad(np.array(%(lat)r)))[:, None] * np.ones((1, shape[1]))
print("product,date," + ",".join(masks))
for prod, first in (("rnl", 1981), ("sat", 1998)):
    for yr in range(first, %(last)d + 1):
        try:
            d = nc.Dataset("%(base)s/%%s/chirps-v3.0.%%s.%%d.days_p05.nc" %% (prod, prod, yr))
        except OSError:
            continue
        t = d["time"]; dates = nc.num2date(t[:], t.units, "standard"); pv = d["precip"]
        for a in range(0, len(dates), 30):
            blk = np.ma.filled(pv[a:a + 30, %(i0)d:%(i1)d, %(j0)d:%(j1)d].astype(np.float64), np.nan)
            for k in range(blk.shape[0]):
                p = blk[k]; ok = np.isfinite(p) & (p > -9000)
                vals = []
                for m in masks.values():
                    ww = w * (ok & m)
                    vals.append("%%.5f" %% (np.nansum(np.where(ok & m, p, 0.0) * ww) / ww.sum()))
                dd = dates[a + k]
                print("%%s,%%04d-%%02d-%%02d,%%s" %% (prod, dd.year, dd.month, dd.day, ",".join(vals)))
        d.close()
        sys.stdout.flush()
"""


def province(name: str, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Natural Earth 10 m province by its English name (Tehran and Alborz share the code IR-07)."""
    recs = [r for r in shapefile.Reader(str(PROVINCES)).iterShapeRecords()
            if r.record["adm0_a3"] == "IRN" and r.record["name"] == name]
    assert len(recs) == 1, name
    pts = np.column_stack([lon.ravel(), lat.ravel()])
    starts = list(recs[0].shape.parts) + [len(recs[0].shape.points)]
    hits = np.zeros(len(pts), int)
    for a, b in zip(starts[:-1], starts[1:]):
        hits += Outline(recs[0].shape.points[a:b]).contains_points(pts)
    return (hits % 2 == 1).reshape(lat.shape)


def pack(m: np.ndarray) -> str:
    return base64.b64encode(zlib.compress(np.packbits(m).tobytes())).decode()


def ssh(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(["ssh", "-o", "BatchMode=yes", "hpc", "python3", "-"], input=script, capture_output=True,
                          text=True, check=True)


def main() -> None:
    g = json.loads(ssh(GRID).stdout)
    lon, lat = np.meshgrid(g["lon"], g["lat"])
    masks = {"iran": enso.country_mask("Iran", lat, lon), "tehran": province("Tehran", lat, lon)}
    print({k: int(m.sum()) for k, m in masks.items()}, "cells", flush=True)
    from datetime import date
    script = READER % dict(py=CLUSTER_PY, shape=lat.shape, masks={k: pack(m) for k, m in masks.items()},
                           lat=g["lat"], last=date.today().year, base=BASE, i0=g["i0"], i1=g["i1"], j0=g["j0"], j1=g["j1"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    part = OUT.with_suffix(".part")
    with open(part, "w") as f:
        subprocess.run(["ssh", "-o", "BatchMode=yes", "hpc", "python3", "-"], input=script, stdout=f, text=True, check=True)
    part.rename(OUT)
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
