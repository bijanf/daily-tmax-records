"""Fetch and cache the inputs of the winter NO2 film (onebit_air.py): Sentinel-5P OFFL tropospheric NO2
granules over Iran for the twelve months Nov 2025 to Oct 2026 (plus the four fact-check seasons that the
ratio check reproduces), and the Copernicus GLO-30 terrain of the film's frame.

Granules are read through HTTP range requests (Planetary Computer, the SAS token of sentinel-5p-l2-netcdf),
each reduced to its valid pixels (qa_value >= 0.75) over Iran (43-65 E, 24.5-41.5 N) and stored as
data/air/granules/<id>.npz with its stats in <id>.json. Granules already in the fact-check cache are copied
rather than read again. A granule that does not reach Iran has a stats file and no npz (n_box 0).

    python -I src/get_air.py            # search, fetch what is missing, build the terrain
    python -I src/get_air.py --no-net  # only use what is already cached (fails if something is missing)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import urllib.request
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import air  # noqa: E402

DATA = air.DATA
GRANULES = DATA / "granules"
FACT_CACHE = Path(os.environ.get("AIR_FACT_CACHE", DATA / "fact_cache"))   # the fact check's granules and items (optional)
FACT_SEASONS = ("DJF2425", "DJF2526", "JJA2025", "JJA2026")
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-5p-l2-netcdf"
DEM_SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/cop-dem-glo-30"
DEM90_SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/cop-dem-glo-90"
IRAN = [43.0, 24.5, 65.0, 41.5]                  # W, S, E, N: the granule box
KEEP = (50.3, 34.2, 52.4, 37.2)                  # W, S, E, N: pixels kept (the frame and its margin)
FILL = 1e30
QA_MIN = 0.75
RES_DEM = 0.00083                                # deg, about 90 m
VE = 2.0                                         # vertical exaggeration of the hillshade
SUN = (315.0, 20.0)                              # azimuth and altitude of the low sun, degrees


def call(url: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"},
                                 method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def search(start: str, end: str) -> list:
    body = {"collections": ["sentinel-5p-l2-netcdf"], "bbox": IRAN, "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
            "limit": 500, "query": {"s5p:product_type": {"eq": "L2__NO2___"}}}
    page, feats = call(f"{STAC}/search", body), []
    for _ in range(100):
        feats += page.get("features", [])
        nxt = next((x for x in page.get("links", []) if x.get("rel") == "next"), None)
        if not nxt:
            break
        page = call(nxt["href"], nxt.get("body")) if nxt.get("method") == "POST" else call(nxt["href"])
    return [dict(id=f["id"], datetime=f["properties"]["datetime"], end=f["properties"].get("end_datetime"),
                 mode=f["properties"].get("s5p:processing_mode"), orbit=f["properties"].get("sat:absolute_orbit"),
                 href=next(iter(f["assets"].values()))["href"]) for f in feats]


def window_items() -> list:
    """Every granule of the window (Nov 2025 to Oct 2026, from the STAC search, cached in data/air/items_window.json),
    plus the last nine days of October 2025: the first Jalali month, Aban 1404, starts on 23 October 2025."""
    path = DATA / "items_window.json"
    if path.exists():
        rows = json.loads(path.read_text())
    else:
        rows = []
        for y, m in air.WINDOW:
            last = 31 if m in (1, 3, 5, 7, 8, 10, 12) else (30 if m != 2 else (29 if y % 4 == 0 else 28))
            rows += search(f"{y}-{m:02d}-01", f"{y}-{m:02d}-{last:02d}")
    if not any(r["datetime"] < "2025-11-01" for r in rows):
        rows += [r for r in search("2025-10-23", "2025-10-31") if r["datetime"] >= "2025-10-23"]
    rows = sorted({r["id"]: r for r in rows}.values(), key=lambda r: r["datetime"])
    path.write_text(json.dumps(rows))
    return rows


def copy_from_fact_check(gid: str) -> bool:
    """Copy a granule's stats and valid pixels from the fact check's cache, if it has them."""
    for season in FACT_SEASONS:
        j = FACT_CACHE / "granules" / season / f"{gid}.json"
        if j.exists():
            shutil.copy(j, GRANULES / f"{gid}.json")
            n = j.with_suffix(".npz")
            if n.exists():
                shutil.copy(n, GRANULES / f"{gid}.npz")
            return True
    return False


class RangeFile:
    """Read-only view of a remote blob through HTTP range requests, with a block cache."""

    def __init__(self, url: str, block: int = 1024 * 1024):
        self.url, self.block, self.pos, self.cache = url, block, 0, {}
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=120) as r:
            self.size = int(r.headers["Content-Length"])

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off)
        return self.pos

    def _get(self, start: int, end: int) -> bytes:
        for attempt in range(5):
            try:
                req = urllib.request.Request(self.url, headers={"Range": f"bytes={start}-{end}"})
                with urllib.request.urlopen(req, timeout=300) as r:
                    return r.read()
            except Exception:  # noqa: BLE001 - retried with a longer pause each time (HTTP 429 when busy)
                time.sleep(10 * (attempt + 1))
        raise RuntimeError("range read failed")

    def read(self, n: int = -1) -> bytes:
        if n is None or n < 0:
            n = self.size - self.pos
        end, out = min(self.pos + n, self.size), bytearray()
        while self.pos < end:
            bi = self.pos // self.block
            if bi not in self.cache:
                s = bi * self.block
                self.cache[bi] = self._get(s, min(s + self.block, self.size) - 1)
            blk = self.cache[bi]
            off = self.pos - bi * self.block
            take = min(len(blk) - off, end - self.pos)
            out += blk[off:off + take]
            self.pos += take
        return bytes(out)

    def readinto(self, b):
        data = self.read(len(b))
        b[:len(data)] = data
        return len(data)


def sas_url(href: str) -> str:
    with urllib.request.urlopen(SAS, timeout=120) as r:
        token = json.loads(r.read().decode())["token"]
    return href + "?" + token


def fetch(row: dict) -> tuple:
    """Read one granule's valid pixels over Iran (qa >= 0.75) and its stats; returns (id, status)."""
    import h5py
    stub = GRANULES / row["id"]
    err = None
    for _ in range(4):
        try:
            t0 = time.time()
            f = h5py.File(RangeFile(sas_url(row["href"])), "r")
            p = f["PRODUCT"]
            lat, lon = p["latitude"][0], p["longitude"][0]
            W, S, E, N = IRAN
            inb = (lat > S) & (lat < N) & (lon > W) & (lon < E)
            rows = np.where(inb.any(axis=1))[0]
            if rows.size == 0:
                json.dump(dict(id=row["id"], datetime=row["datetime"], n_box=0, n_valid=0), open(f"{stub}.json", "w"))
                return row["id"], "no-box"
            r0, r1 = int(rows.min()), int(rows.max()) + 1
            la, lo, ib = lat[r0:r1], lon[r0:r1], inb[r0:r1]
            raw = p["qa_value"][0, r0:r1, :]
            qa = np.where(raw == 255, np.nan, raw.astype(np.float32) * 0.01)
            no2 = p["nitrogendioxide_tropospheric_column"][0, r0:r1, :].astype(np.float32)
            good = np.isfinite(no2) & (np.abs(no2) < FILL)
            valid = ib & good & (qa >= QA_MIN)
            np.savez_compressed(f"{stub}.npz", lat=la[valid].astype(np.float32), lon=lo[valid].astype(np.float32),
                                no2=no2[valid], qa=qa[valid].astype(np.float32))
            json.dump(dict(id=row["id"], datetime=row["datetime"], n_box=int(ib.sum()), n_valid=int(valid.sum()),
                           seconds=round(time.time() - t0, 1)), open(f"{stub}.json", "w"))
            return row["id"], "ok"
        except Exception as ex:  # noqa: BLE001 - retried; reported if it keeps failing
            err = repr(ex)[:300]
            time.sleep(20)
    return row["id"], f"error {err}"


def dem_grid(lonmin, lonmax, latmin, latmax) -> np.ndarray:
    import rasterio
    from rasterio.windows import from_bounds
    token = json.loads(urllib.request.urlopen(DEM_SAS, timeout=120).read())["token"]
    nx, ny = int(np.ceil((lonmax - lonmin) / RES_DEM)), int(np.ceil((latmax - latmin) / RES_DEM))
    G = np.full((ny, nx), np.nan, np.float32)
    for lat0 in range(int(np.floor(latmin)), int(np.ceil(latmax))):
        for lon0 in range(int(np.floor(lonmin)), int(np.ceil(lonmax))):
            tile = f"Copernicus_DSM_COG_10_N{lat0:02d}_00_E{lon0:03d}_00_DEM"
            url = f"https://elevationeuwest.blob.core.windows.net/copernicus-dem/COP30_hh/{tile}.tif?{token}"
            with rasterio.open("/vsicurl/" + url) as src:
                tl = max(lonmin, lon0), min(latmax, lat0 + 1)
                br = min(lonmax, lon0 + 1), max(latmin, lat0)
                if tl[0] >= br[0] or br[1] >= tl[1]:
                    continue
                c0 = int(np.floor((tl[0] - lonmin) / RES_DEM))
                c1 = min(int(np.ceil((br[0] - lonmin) / RES_DEM)), nx)
                r0 = int(np.floor((latmax - tl[1]) / RES_DEM))
                r1 = min(int(np.ceil((latmax - br[1]) / RES_DEM)), ny)
                w = from_bounds(lonmin + c0 * RES_DEM, latmax - r1 * RES_DEM, lonmin + c1 * RES_DEM,
                                latmax - r0 * RES_DEM, src.transform)
                a = src.read(1, window=w, out_shape=(r1 - r0, c1 - c0),
                             resampling=rasterio.enums.Resampling.bilinear)
                G[r0:r1, c0:c1] = a
    return G


def terrain(path: Path) -> None:
    """Hillshade and elevation on the film's frame: the hillshade is made on the DEM grid (VE x2, sun NW
    at 20 degrees) and sampled onto the 1080 x 1920 frame, as in the fact check's frame."""
    from scipy import ndimage
    gl, gr = air.LON_L - 0.02, air.LON_R + 0.02
    gb, gt = air.LAT_B - 0.02, air.LAT_T + 0.02
    dem = dem_grid(gl, gr, gb, gt)
    dem = np.where(np.isfinite(dem), dem, 0.0)
    dy_m = RES_DEM * 110574.0
    dx_m = RES_DEM * 111320.0 * np.cos(np.radians((gb + gt) / 2))
    gy, gx = np.gradient(dem * VE, dy_m, dx_m)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    az, alt = np.radians(SUN[0]), np.radians(SUN[1])
    hs = np.clip(np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect), 0, 1)
    yy, xx = np.mgrid[0:air.H, 0:air.W]
    lon_f, lat_f = air.lonlat_of(xx.astype(float), yy.astype(float))
    ci, ri = (lon_f - gl) / RES_DEM, (gt - lat_f) / RES_DEM
    hs_f = ndimage.map_coordinates(hs, [ri, ci], order=1).astype(np.float32)
    elev_f = ndimage.map_coordinates(dem, [ri, ci], order=1).astype(np.float32)
    np.savez_compressed(path, hs=hs_f, elev=elev_f)


IRAN_GRID = dict(lon0=43.0, lat0=40.2, step=0.04, nx=525, ny=385)   # the country grid (air.iran_glow shares it)


def iran_relief(path: Path) -> None:
    """Relief of Iran on the country grid (0.04 deg, coarse by design): Copernicus GLO-30 tiles averaged to the grid,
    the hillshade (VE x2, sun NW at 20 degrees), the elevation, the sea (no tile or elevation <= 0), Iran's pixels and
    border (Natural Earth 50 m, enso.country_mask)."""
    import rasterio
    from scipy import ndimage
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import enso
    g = IRAN_GRID
    token30 = json.loads(urllib.request.urlopen(DEM_SAS, timeout=120).read())["token"]
    token90 = json.loads(urllib.request.urlopen(DEM90_SAS, timeout=120).read())["token"]
    LAT = g["lat0"] - (np.arange(g["ny"]) + 0.5) * g["step"]
    LON = g["lon0"] + (np.arange(g["nx"]) + 0.5) * g["step"]
    G = np.full((g["ny"], g["nx"]), np.nan, np.float32)
    missing, failed = [], []
    for lat0 in range(24, 41):
        for lon0 in range(43, 64):
            rows = np.flatnonzero((LAT >= lat0) & (LAT < lat0 + 1))
            cols = np.flatnonzero((LON >= lon0) & (LON < lon0 + 1))
            if rows.size == 0 or cols.size == 0:
                continue
            # GLO-30 first; a tile GLO-30 lacks (not found) is read from GLO-90 (coarser: fine on this grid)
            cands = [("COP30_hh", f"Copernicus_DSM_COG_10_N{lat0:02d}_00_E{lon0:03d}_00_DEM", token30),
                     ("COP90_hh", f"Copernicus_DSM_COG_30_N{lat0:02d}_00_E{lon0:03d}_00_DEM", token90)]
            a, kind = None, "sea"
            for folder, tile, tok in cands:
                url = f"https://elevationeuwest.blob.core.windows.net/copernicus-dem/{folder}/{tile}.tif?{tok}"
                for attempt in range(4):                  # 429 (busy) is retried
                    try:
                        with rasterio.open("/vsicurl/" + url) as src:
                            a = src.read(1, out_shape=(25, 25), resampling=rasterio.enums.Resampling.average).astype(np.float32)
                        break
                    except Exception as ex:  # noqa: BLE001
                        if "404" in str(ex) or "does not exist" in str(ex).lower():
                            break
                        kind = "failed"
                        time.sleep(15 * (attempt + 1))
                if a is not None:
                    kind = folder
                    break
            if a is None:
                (missing if kind == "sea" else failed).append(f"{lat0}N{lon0}E")
                continue
            ti = np.clip(np.floor((lat0 + 1 - LAT[rows]) / g["step"]).astype(int), 0, 24)
            tj = np.clip(np.floor((LON[cols] - lon0) / g["step"]).astype(int), 0, 24)
            G[np.ix_(rows, cols)] = a[np.ix_(ti, tj)]
    print("tiles without data (sea):", len(missing), missing, flush=True)
    print("tiles that failed after retries:", failed, flush=True)
    assert not failed, failed
    water = ~np.isfinite(G) | (G <= 0)
    elev = np.where(water, 0.0, G).astype(np.float32)
    dy_m = g["step"] * 110574.0
    dx_m = g["step"] * 111320.0 * np.cos(np.radians(LAT))
    z = elev * VE
    gy = np.gradient(z, dy_m, axis=0)
    gx = np.gradient(z, axis=1) / dx_m[:, None]
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    az, alt = np.radians(SUN[0]), np.radians(SUN[1])
    hs = np.clip(np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect), 0, 1)
    LA, LO = np.meshgrid(LAT, LON, indexing="ij")
    inside = enso.country_mask(["Iran"], LA, LO)
    empty = inside & ~np.isfinite(G)                  # a land cell with no relief is a gap: none allowed
    print("land cells with no relief:", int(empty.sum()), flush=True)
    assert empty.sum() == 0, int(empty.sum())
    border = inside & ~ndimage.binary_erosion(inside, iterations=1)
    np.savez_compressed(path, elev=elev, hs=hs.astype(np.float32), water=water.astype(np.float32),
                        inside=inside.astype(np.float32), border=border.astype(np.float32))
    print("saved", path, "inside cells", int(inside.sum()), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-net", action="store_true", help="use only what is cached")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--iran-relief", action="store_true", help="build data/air/iran_relief.npz and stop")
    args = ap.parse_args()
    if args.iran_relief:
        iran_relief(DATA / "iran_relief.npz")
        return
    GRANULES.mkdir(parents=True, exist_ok=True)
    for season in FACT_SEASONS:                     # the fact check's items, for the reproduction (optional copy)
        if (FACT_CACHE / f"items_{season}.json").exists():
            shutil.copy(FACT_CACHE / f"items_{season}.json", DATA / f"items_fact_{season}.json")
    if (FACT_CACHE / "ratio_table.csv").exists():
        shutil.copy(FACT_CACHE / "ratio_table.csv", DATA / "ratio_table_fact.csv")
    items = window_items()
    todo = []
    for r in items:
        if r["mode"] != "OFFL" or (GRANULES / f"{r['id']}.json").exists():
            continue
        if copy_from_fact_check(r["id"]):
            continue
        todo.append(r)
    for season in FACT_SEASONS:                     # the fact-check seasons not in the window: copy what is cached
        for it in json.loads((DATA / f"items_fact_{season}.json").read_text()):
            if it["mode"] == "OFFL" and not (GRANULES / f"{it['id']}.json").exists():
                copy_from_fact_check(it["id"])
    print(f"window: {len(items)} granules, OFFL {sum(r['mode'] == 'OFFL' for r in items)}, "
          f"to read {len(todo)}", flush=True)
    if todo and args.no_net:
        sys.exit(f"{len(todo)} granules are not cached and --no-net was given")
    t0, status = time.time(), {}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(fetch, r) for r in todo]
        for k, fu in enumerate(as_completed(futs), 1):
            gid, st = fu.result()
            status[st.split(" ")[0]] = status.get(st.split(" ")[0], 0) + 1
            if st.startswith("error"):
                print(gid, st, flush=True)
            if k % 40 == 0:
                print(f"{k}/{len(todo)} in {time.time() - t0:.0f} s", flush=True)
    print("read:", status, flush=True)
    missing = [r["id"] for r in items if r["mode"] == "OFFL" and not (GRANULES / f"{r['id']}.json").exists()]
    if missing:
        sys.exit(f"{len(missing)} OFFL granules still missing, first {missing[0]}")
    terrain_path = DATA / "terrain.npz"
    if not terrain_path.exists():
        terrain(terrain_path)
    print("saved", terrain_path, flush=True)


if __name__ == "__main__":
    main()
