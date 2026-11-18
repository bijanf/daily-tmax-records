"""Fetch and cache the inputs of the Hormuz NO2 film: Sentinel-5P OFFL tropospheric NO2 over the Persian Gulf, the
Strait of Hormuz and the Gulf of Oman for the same calendar window (WINDOW) of each year, and the IMF PortWatch daily
transit calls of the Strait of Hormuz.

NO2: orbits are read through HTTP range requests (Planetary Computer, the keyless SAS token of sentinel-5p-l2-netcdf,
as get_air.py). Of each orbit only the block of scanlines and ground pixels that covers BOX is kept, with one pixel of
margin on every side so that pixel corners can be rebuilt from the centres (air_grid.corners):
data/hormuz/granules/<id>.npz holds lat, lon (float32, pixel centres) and no2 (float32, mol m-2; NaN where
qa_value < 0.75, the product's own recommendation, or where the value is fill); <id>.json holds the counts, the
processor version and the seconds the read took. Only OFFL orbits are used: the near-real-time stream has another
processing chain, so the window of every year ends where OFFL ends for the newest year.

What the film needs (about 2,200 orbits, 20 to 25 MB read of each; eight readers take about three hours):

    python -I src/get_hormuz.py --years 2025 2026             # March to 7 November of the two years compared
    python -I src/get_hormuz.py --months 2025-01 2025-02 2026-01 2026-02      # the two months before the event
    python -I src/get_hormuz.py --months 2023-03 2023-04 2023-05 2023-06 2024-03 2024-04 2024-05 2024-06   # two normal springs
    python -I src/get_hormuz.py --portwatch                    # the ships: data/hormuz/portwatch_hormuz_daily.csv
    python -I src/get_hormuz.py --maps                         # the inventory of ship NOx, the coast, the base maps

The lanes are not taken from the NO2 map: EDGAR v8.1 (European Commission, JRC) gives the NOx that ships emitted in
2022 on a 0.1-degree grid (sector TNR_Ship) beside the NOx of every sector (TOTALS); the box of both is kept in
data/hormuz/edgar_nox_2022.npz. Base maps: NASA Blue Marble with shaded relief and bathymetry (GIBS, public domain).
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import get_air  # noqa: E402  (RangeFile: the block-cached HTTP range reader)
import get_khazar  # noqa: E402  (the 9:16 Web Mercator frame, the GIBS request, the retrying fetch)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "hormuz"
GRANULES = DATA / "granules"
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-5p-l2-netcdf"
PORTWATCH = ("https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Chokepoints_Data/"
             "FeatureServer/0/query")
HORMUZ_ID = "chokepoint6"                        # PortWatch's id of the Strait of Hormuz
AGENT = {"User-Agent": "research-script/1.0"}
BOX = (47.0, 21.5, 61.5, 31.0)                   # W, S, E, N
WINDOW = ("03-01", "11-07")                      # first and last day of every year's window (month-day)
QA_MIN = 0.75
EDGAR = ("https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/EDGAR/datasets/v81_FT2022_AP_new/NOx/{0}/emi_nc/"
         "v8.1_FT2022_AP_NOx_2022_{0}_emi_nc.zip")
NE_URL = "https://naciscdn.org/naturalearth/10m/{}/{}.zip"
NE_LAYERS = (("physical", "ne_10m_land"), ("cultural", "ne_10m_admin_0_boundary_lines_land"))
# the film's pictures: the strait and the Gulf of Oman as one 9:16 frame; the whole Gulf as a wide panel (two are stacked)
EAST = get_khazar.frame(55.2, 60.8, 21.6)                       # W, S, E, N


def panel(west: float, east: float, south: float, ratio: float) -> tuple:
    """A Web Mercator box of a given width-to-height ratio from its west, east and south edges: (W, S, E, N)."""
    mx, my = get_khazar.mx, get_khazar.my
    return west, south, east, get_khazar.lat_of(my(south) + (mx(east) - mx(west)) / ratio)


GULF = panel(47.5, 57.1, 23.2, 1080 / 960)                      # the whole Gulf, 1080 x 960
LOCATOR = get_khazar.frame(42.5, 64.5, 10.5)                    # the corner map: Arabia, Iran and the seas between
FILL = 1e30
BLOCK = 2 * 1024 * 1024                          # bytes per range request
_TOKEN = dict(value=None, at=0.0)


def call(url: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **AGENT},
                                 method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def search(start: str, end: str) -> list:
    """Every OFFL NO2 orbit whose footprint touches BOX between two days (inclusive)."""
    body = {"collections": ["sentinel-5p-l2-netcdf"], "bbox": list(BOX), "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
            "limit": 500, "query": {"s5p:product_type": {"eq": "L2__NO2___"}, "s5p:processing_mode": {"eq": "OFFL"}}}
    page, feats = call(STAC, body), []
    for _ in range(200):
        feats += page.get("features", [])
        nxt = next((x for x in page.get("links", []) if x.get("rel") == "next"), None)
        if not nxt:
            break
        page = call(nxt["href"], nxt.get("body")) if nxt.get("method") == "POST" else call(nxt["href"])
    rows = [dict(id=f["id"], datetime=f["properties"]["datetime"], mode=f["properties"].get("s5p:processing_mode"),
                 orbit=f["properties"].get("sat:absolute_orbit"), href=next(iter(f["assets"].values()))["href"])
            for f in feats if f["properties"].get("s5p:processing_mode") == "OFFL"]
    return sorted({r["id"]: r for r in rows}.values(), key=lambda r: r["datetime"])


def items(year: int) -> list:
    path = DATA / f"items_{year}.json"
    if path.exists():
        return json.loads(path.read_text())
    rows = []
    months = [(3, 31), (4, 30), (5, 31), (6, 30), (7, 31), (8, 31), (9, 30), (10, 31), (11, 30)]
    for m, last in months:                       # month by month: the search pages stay small
        a, b = f"{year}-{m:02d}-01", f"{year}-{m:02d}-{last:02d}"
        rows += [r for r in search(max(a, f"{year}-{WINDOW[0]}"), min(b, f"{year}-{WINDOW[1]}"))
                 ] if a <= f"{year}-{WINDOW[1]}" else []
    rows = sorted({r["id"]: r for r in rows}.values(), key=lambda r: r["datetime"])
    DATA.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows))
    return rows


def month_items(ym: str) -> list:
    """Every OFFL orbit of one calendar month ("2026-01"); from the year's window file when that covers the month."""
    path = DATA / "items" / f"{ym}.json"
    if path.exists():
        return json.loads(path.read_text())
    y, m = int(ym[:4]), int(ym[5:7])
    last = 31 if m in (1, 3, 5, 7, 8, 10, 12) else (30 if m != 2 else (29 if y % 4 == 0 else 28))
    whole = DATA / f"items_{y}.json"
    if whole.exists() and f"{WINDOW[0]}" <= f"{m:02d}-01" and f"{m:02d}-{last:02d}" <= WINDOW[1]:
        rows = [r for r in json.loads(whole.read_text()) if r["datetime"][:7] == ym]
    else:
        rows = search(f"{ym}-01", f"{ym}-{last:02d}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows))
    return rows


def token() -> str:
    """The SAS token, asked for again after twenty minutes (per process)."""
    if _TOKEN["value"] is None or time.time() - _TOKEN["at"] > 1200:
        _TOKEN["value"], _TOKEN["at"] = call(SAS)["token"], time.time()
    return _TOKEN["value"]


def inside(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    W, S, E, N = BOX
    return (lat > S) & (lat < N) & (lon > W) & (lon < E)


def geoloc(p) -> tuple:
    """Pixel centres of the scanlines that can reach BOX: (first scanline, lat, lon). BOX lies north of the equator,
    in the second half of the daytime orbit, so the second chunk-row of the file is read first; the whole array only
    if BOX touches that block's first scanline (or is not in it)."""
    la, lo = p["latitude"], p["longitude"]
    n, half = la.shape[1], (la.chunks[1] if la.chunks else 0)
    if 0 < half < n:
        lat, lon = la[0, half:, :], lo[0, half:, :]
        rows = np.flatnonzero(inside(lat, lon).any(axis=1))
        if rows.size and rows.min() > 1:
            return half, lat, lon
    return 0, la[0], lo[0]


def fetch(row: dict) -> tuple:
    """Read one orbit's block over BOX; returns (id, status)."""
    import h5py
    stub = GRANULES / row["id"]
    if Path(f"{stub}.json").exists():                 # read by an earlier or a parallel run
        return row["id"], "cached"
    err = None
    for attempt in range(4):
        try:
            t0 = time.time()
            rf = get_air.RangeFile(row["href"] + "?" + token(), block=BLOCK)
            f = h5py.File(rf, "r")
            p = f["PRODUCT"]
            first, lat, lon = geoloc(p)
            inb = inside(lat, lon)
            version = f.attrs.get("processor_version")
            version = version.decode() if isinstance(version, bytes) else (str(version) if version is not None else None)
            meta = dict(id=row["id"], datetime=row["datetime"], orbit=row.get("orbit"), version=version)
            if not inb.any():
                json.dump(dict(meta, n_box=0, n_valid=0), open(f"{stub}.json", "w"))
                return row["id"], "no-box"
            rr, cc = np.flatnonzero(inb.any(axis=1)), np.flatnonzero(inb.any(axis=0))
            a0, a1 = max(int(rr.min()) - 1, 0), min(lat.shape[0], int(rr.max()) + 2)
            c0, c1 = max(int(cc.min()) - 1, 0), min(lat.shape[1], int(cc.max()) + 2)
            raw = p["qa_value"][0, first + a0:first + a1, c0:c1]
            qa = np.where(raw == 255, np.nan, raw.astype(np.float32) * 0.01)
            no2 = p["nitrogendioxide_tropospheric_column"][0, first + a0:first + a1, c0:c1].astype(np.float32)
            valid = np.isfinite(no2) & (np.abs(no2) < FILL) & (qa >= QA_MIN)
            no2 = np.where(valid, no2, np.nan).astype(np.float32)
            ib = inb[a0:a1, c0:c1]
            tmp = Path(f"{stub}.part.npz")
            np.savez_compressed(tmp, lat=lat[a0:a1, c0:c1].astype(np.float32), lon=lon[a0:a1, c0:c1].astype(np.float32),
                                no2=no2)
            tmp.replace(f"{stub}.npz")
            json.dump(dict(meta, n_box=int(ib.sum()), n_valid=int((ib & valid).sum()), shape=list(no2.shape),
                           mb=round(len(rf.cache) * BLOCK / 1e6, 1), seconds=round(time.time() - t0, 1)),
                      open(f"{stub}.json", "w"))
            return row["id"], "ok"
        except Exception as ex:  # noqa: BLE001 - retried with a pause; reported if it keeps failing
            err = repr(ex)[:300]
            _TOKEN["value"] = None
            time.sleep(20 * (attempt + 1))
    return row["id"], f"error {err}"


def granules(years: list, months: list, workers: int) -> None:
    GRANULES.mkdir(parents=True, exist_ok=True)
    rows = [r for y in years for r in items(y)] + [r for ym in months for r in month_items(ym)]
    rows = list({r["id"]: r for r in rows}.values())
    todo = [r for r in rows if not (GRANULES / f"{r['id']}.json").exists()]
    todo.sort(key=lambda r: r["datetime"][5:])        # by month and day: the years advance together
    print(f"years {years}, months {months}: {len(rows)} OFFL orbits, {len(todo)} to read, {workers} readers", flush=True)
    t0, done, bad = time.time(), 0, []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch, r): r for r in todo}
        for fu in as_completed(futs):
            gid, status = fu.result()
            done += 1
            if status.startswith("error"):
                bad.append((gid, status))
                print("FAILED", gid, status, flush=True)
            if done % 50 == 0 or done == len(todo):
                print(f"  {done}/{len(todo)} read, {time.time() - t0:.0f} s, failed {len(bad)}", flush=True)
    print("done; failed:", len(bad), flush=True)


def portwatch() -> None:
    """IMF PortWatch: daily transit calls of the Strait of Hormuz (AIS-based), all days from 2019."""
    rows, off = [], 0
    while True:
        q = dict(where=f"portid='{HORMUZ_ID}'", outFields="*", orderByFields="date ASC", resultOffset=off,
                 resultRecordCount=1000, f="json")
        req = urllib.request.Request(PORTWATCH + "?" + urllib.parse.urlencode(q), headers=AGENT)
        with urllib.request.urlopen(req, timeout=180) as r:
            d = json.loads(r.read().decode())
        fs = d.get("features", [])
        if not fs:
            break
        rows += [f["attributes"] for f in fs]
        off += len(fs)
        if len(fs) < 1000 and not d.get("exceededTransferLimit"):
            break
    for a in rows:
        v = a["date"]
        a["date"] = (datetime.datetime.fromtimestamp(v / 1000, datetime.timezone.utc).strftime("%Y-%m-%d")
                     if isinstance(v, (int, float)) else str(v)[:10])
    assert rows and rows[0]["portname"] == "Strait of Hormuz", rows[:1]
    keys = ["date", "n_total", "n_tanker", "n_container", "n_dry_bulk", "n_general_cargo", "n_roro", "n_cargo",
            "capacity", "capacity_tanker"]
    DATA.mkdir(parents=True, exist_ok=True)
    out = DATA / "portwatch_hormuz_daily.csv"
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"saved {out}: {len(rows)} days, {rows[0]['date']} to {rows[-1]['date']}")


def edgar() -> None:
    """The box of EDGAR v8.1's NOx of 2022: ships (TNR_Ship) and every sector (TOTALS), tonnes per 0.1-degree cell."""
    import io
    import tempfile
    import zipfile
    import netCDF4
    out = DATA / "edgar_nox_2022.npz"
    if out.exists():
        return
    W, S, E, N = BOX
    keep = {}
    for sector, key in (("TNR_Ship", "ship"), ("TOTALS", "total")):
        z = zipfile.ZipFile(io.BytesIO(get_khazar.fetch(EDGAR.format(sector))))
        name = next(n for n in z.namelist() if n.endswith(".nc"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "edgar.nc"
            path.write_bytes(z.read(name))
            nc = netCDF4.Dataset(path)
            lat, lon = np.asarray(nc.variables["lat"][:]), np.asarray(nc.variables["lon"][:])
            assert nc.variables["emissions"].units == "Tonnes", nc.variables["emissions"].units
            ii, jj = np.flatnonzero((lat >= S) & (lat <= N)), np.flatnonzero((lon >= W) & (lon <= E))
            keep[key] = np.ma.filled(nc.variables["emissions"][ii.min():ii.max() + 1, jj.min():jj.max() + 1], 0.0)
            keep["lat"], keep["lon"] = lat[ii], lon[jj]
            nc.close()
    DATA.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, **keep)
    print(f"saved {out.name}: ships {keep['ship'].sum() / 1e3:.0f} kt, every sector {keep['total'].sum() / 1e3:.0f} kt")


def natural_earth() -> None:
    import io
    import zipfile
    folder = DATA / "ne"
    folder.mkdir(parents=True, exist_ok=True)
    for kind, name in NE_LAYERS:
        if (folder / f"{name}.shp").exists():
            continue
        z = zipfile.ZipFile(io.BytesIO(get_khazar.fetch(NE_URL.format(kind, name))))
        for i in z.infolist():
            if Path(i.filename).suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
                (folder / Path(i.filename).name).write_bytes(z.read(i))
        print("saved", name)


def bases() -> None:
    """NASA Blue Marble (shaded relief and bathymetry) for the two pictures of the film."""
    import io
    from PIL import Image
    mx, my = get_khazar.mx, get_khazar.my
    assert BOX[1] < GULF[1] and GULF[3] < BOX[3] and BOX[1] < EAST[1] and EAST[3] < BOX[3], (GULF, EAST)   # inside the data
    for name, box, px in (("east", EAST, (1620, 2880)), ("gulf", GULF, (1620, 1440)), ("locator", LOCATOR, (504, 896))):
        path = DATA / f"base_{name}.jpg"
        if path.exists():
            continue
        w, s, e, n = box
        url = get_khazar.GIBS_STATIC.format("BlueMarble_ShadedRelief_Bathymetry", mx(w), my(s), mx(e), my(n), px[0], px[1])
        Image.open(io.BytesIO(get_khazar.fetch(url))).convert("RGB").save(path, quality=94, subsampling=0)
        print("saved", path.name)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, nargs="*", default=[])
    ap.add_argument("--months", nargs="*", default=[])
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--portwatch", action="store_true")
    ap.add_argument("--maps", action="store_true")
    a = ap.parse_args()
    if a.portwatch:
        portwatch()
    if a.maps:
        edgar()
        natural_earth()
        bases()
    if a.years or a.months:
        granules(a.years, a.months, a.workers)


if __name__ == "__main__":
    main()
