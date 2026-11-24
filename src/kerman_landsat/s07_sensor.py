"""Step 5: how much the sensor change moves NDVI and the thresholded areas, from near-simultaneous passes
(8 days apart, same path) of two sensors, compared on the pixels clear in both:
  Landsat 5 TM vs Landsat 7 ETM+ (2000-2002, before ETM+'s scan-line failure),
  Landsat 7 ETM+ vs Landsat 8 OLI (2013-2014; ETM+ striped, so only its pixels with data count),
  Landsat 8 OLI vs Landsat 9 OLI-2 (2022-2023).
Pairs are taken both ways in time (A before B and B before A) so a steady seasonal drift cancels in the mean.
Per pair: areas >= 0.15/0.20/0.25/0.30 on the common clear pixels of the zone, the desert's median NDVI, and a
reduced-major-axis line NDVI_B = a + b NDVI_A over common pixels with mean NDVI 0.08-0.60; and the
equal-area thresholds: for each threshold t on the newer sensor (0.100, 0.105, ..., 0.350) the NDVI t_old
on the older sensor above which the same number of common pixels lie (sensor_eq.csv).
More pairs: ETM+/OLI 2015, and TM/ETM+ 2009 (ETM+ after its scan-line failure, as in 2013-2015), so the
chain TM -> ETM+ -> OLI is tied at both ends of ETM+'s record.
    python -I s07_sensor.py
Writes sensor_pairs.csv and sensor_eq.csv."""
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HERE, path_row  # noqa: E402
from geom import masks, PIX_KM2  # noqa: E402
from s04_year import items, read_pass, ndvi_of, bbox_of  # noqa: E402

PAIRS = [  # (path_row, date A, date B)
    ("161039", "2000-08-06", "2000-08-14"), ("161039", "2000-08-14", "2000-08-22"),
    ("161039", "2001-08-09", "2001-08-17"),
    ("161039", "2002-07-19", "2002-07-27"), ("161039", "2002-08-04", "2002-08-12"),
    ("160039", "2000-07-22", "2000-07-30"), ("160039", "2000-07-30", "2000-08-07"),
    ("160039", "2000-08-07", "2000-08-15"), ("160039", "2001-08-18", "2001-08-26"),
    ("161039", "2014-07-20", "2014-07-28"), ("161039", "2014-07-28", "2014-08-05"),
    ("161039", "2014-08-05", "2014-08-13"), ("161039", "2014-08-13", "2014-08-21"),
    ("161039", "2014-08-21", "2014-08-29"), ("161039", "2013-08-18", "2013-08-26"),
    ("161039", "2013-08-26", "2013-09-03"),
    ("160039", "2014-07-21", "2014-07-29"), ("160039", "2014-08-14", "2014-08-22"),
    ("160039", "2014-08-22", "2014-08-30"),
    ("161039", "2022-08-03", "2022-08-11"), ("161039", "2023-08-06", "2023-08-14"),
    ("160039", "2023-08-07", "2023-08-15"),
    ("161039", "2015-08-08", "2015-08-16"), ("161039", "2015-08-16", "2015-08-24"),
    ("161039", "2015-08-24", "2015-09-01"),
    ("160039", "2015-08-09", "2015-08-17"), ("160039", "2015-08-17", "2015-08-25"),
    ("161039", "2009-07-22", "2009-07-30"), ("161039", "2009-07-30", "2009-08-07"),
    ("161039", "2009-08-07", "2009-08-15"), ("161039", "2009-08-15", "2009-08-23"),
    ("161039", "2009-08-23", "2009-08-31"),
    ("160039", "2009-07-23", "2009-07-31"), ("160039", "2009-07-31", "2009-08-08"),
    ("160039", "2009-08-08", "2009-08-16"), ("160039", "2009-08-16", "2009-08-24"),
]
THR = (0.15, 0.20, 0.25, 0.30)
GRID_T = np.round(np.arange(0.100, 0.3501, 0.005), 3)
ORDER = {"landsat-4": 4, "landsat-5": 5, "landsat-7": 7, "landsat-8": 8, "landsat-9": 9}


def feat(pr, date):
    y = int(date[:4])
    c = [f for f in items(y) if path_row(f) == pr and f["properties"]["datetime"][:10] == date]
    assert len(c) == 1, (pr, date, [f["id"] for f in c])
    return c[0]


def one(p):
    m = masks()
    pr, da, db = p
    zone = m["zw"] if pr == "161039" else m["ze"]
    sub = bbox_of(zone)
    r0, r1, c0, c1 = sub
    z = zone[r0:r1, c0:c1]
    fa, fb = feat(pr, da), feat(pr, db)
    nda, _ = ndvi_of(read_pass([fa], ["red", "nir08", "qa_pixel"], sub))
    ndb, _ = ndvi_of(read_pass([fb], ["red", "nir08", "qa_pixel"], sub))
    ok = z & np.isfinite(nda) & np.isfinite(ndb)
    a, b = nda[ok], ndb[ok]
    rec = dict(path_row=pr, date_a=da, sensor_a=fa["properties"]["platform"], date_b=db,
               sensor_b=fb["properties"]["platform"], common_km2=round(ok.sum() * PIX_KM2, 1),
               common_frac_of_zone=round(float(ok.sum() / z.sum()), 3),
               desert_a=round(float(np.median(a[(a < 0.15) & (b < 0.15)])), 4),
               desert_b=round(float(np.median(b[(a < 0.15) & (b < 0.15)])), 4))
    for t in THR:
        rec[f"A_km2_{t:.2f}"] = round(float((a >= t).sum() * PIX_KM2), 2)
        rec[f"B_km2_{t:.2f}"] = round(float((b >= t).sum() * PIX_KM2), 2)
    sel = ((a + b) / 2 >= 0.08) & ((a + b) / 2 <= 0.60)
    xa, xb = a[sel].astype(np.float64), b[sel].astype(np.float64)
    r = np.corrcoef(xa, xb)[0, 1]
    slope = np.sign(r) * xb.std() / xa.std()
    rec.update(rma_slope=round(float(slope), 4), rma_icpt=round(float(xb.mean() - slope * xa.mean()), 4),
               r=round(float(r), 4), n_fit=int(sel.sum()))
    old, new = (a, b) if ORDER[rec["sensor_a"]] <= ORDER[rec["sensor_b"]] else (b, a)
    srt = np.sort(old)
    eq = []
    for t in GRID_T:
        n = int((new >= t).sum())
        eq.append(dict(path_row=pr, date_a=da, date_b=db, old=min(rec["sensor_a"], rec["sensor_b"], key=ORDER.get),
                       new=max(rec["sensor_a"], rec["sensor_b"], key=ORDER.get), t_new=float(t), n_px=n,
                       t_old_eq=round(float(srt[len(srt) - n]), 4) if n > 0 else None))
    print(pr, da, db, rec["sensor_a"], rec["sensor_b"], rec["A_km2_0.20"], rec["B_km2_0.20"], flush=True)
    return rec, eq


if __name__ == "__main__":
    with ThreadPoolExecutor(3) as pool:
        out = list(pool.map(one, PAIRS))
    df = pd.DataFrame([r for r, _ in out])
    df.to_csv(HERE / "sensor_pairs.csv", index=False)
    pd.DataFrame([e for _, eq in out for e in eq]).to_csv(HERE / "sensor_eq.csv", index=False)
    pd.set_option("display.width", 250)
    print(df.to_string())
