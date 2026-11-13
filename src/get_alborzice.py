"""THE WHITE LEFT AT THE END OF SUMMER ON DAMAVAND AND ALAM-KUH: every Landsat pass of late summer, 1984-2026.

For each pass between 25 July and 20 October over a 12-km square around the summit this script stores the snow
and ice mask pixel by pixel, so that src/alborzice_measure.py can vet the passes, take each year's minimum and
draw each year's white. It measures "snow, firn and clean ice", never glacier extent: debris-covered ice is dark.

Data, keyless Planetary Computer:
- Landsat Collection 2 Level 2 surface reflectance, 30 m (green, nir08, swir16, qa_pixel), Tier 1 only.
  Landsat 7 after 31 May 2003 has scan-line gaps: those passes are stored and flagged (slc_off) and are used only
  to compare the old sensor family (TM, ETM+) with the new one (OLI) on the pixels both see.
- Copernicus DEM GLO-30 on the Landsat grid (the fixed elevation zones).
- Sentinel-2 L2A, 10 m (B04, B03, B02) of one clear late-summer pass: the ground picture under each year's white.

Snow or ice: NDSI = (green - swir1) / (green + swir1) >= 0.40 and nir >= 0.11 (loose: nir >= 0.05).

    python -I src/get_alborzice.py damavand            # data/alborzice/damavand/{scenes.csv, masks/, quick/, dem.npy}
    python -I src/get_alborzice.py takht
    python -I src/get_alborzice.py takht --ground 2025-09-03   # ground_<site>.jpg from Sentinel-2
"""
from __future__ import annotations

import argparse
import csv
import json
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from PIL import Image
from rasterio.crs import CRS
from rasterio.enums import Resampling as RS
from rasterio.env import Env
from rasterio.warp import Resampling, reproject
from rasterio.warp import transform as warp_transform
from rasterio.windows import Window

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "alborzice"
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/{}"
UTM = CRS.from_epsg(32639)                            # UTM 39N: both sites, every Landsat path used
SITES = {
    # summit, half-width of the square, the elevation floors of the counted zone (z1) and of a higher zone (z2)
    "damavand": dict(lon=52.1090, lat=35.9553, half_m=6000.0, z=(4000.0, 4500.0)),
    "takht": dict(lon=50.9610, lat=36.3750, half_m=6000.0, z=(3800.0, 4100.0)),
}
ENVOPT = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".TIF,.tif",
              GDAL_HTTP_MAX_RETRY="5", GDAL_HTTP_RETRY_DELAY="2", VSI_CACHE="TRUE")
_tok: dict = {}
_lock = threading.Lock()


def http_json(url: str, body: dict | None = None) -> dict:
    last = None
    for k in range(5):
        try:
            data = json.dumps(body).encode() if body is not None else None
            req = urllib.request.Request(url, data=data, method="POST" if body is not None else "GET",
                                         headers={"Content-Type": "application/json", "User-Agent": "reel-data"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except Exception as e:                        # 429 and timeouts: back off and retry
            last = e
            time.sleep(3 * (k + 1))
    raise RuntimeError(f"{url}: {last!r}")


def sign(coll: str, href: str) -> str:
    with _lock:
        if coll not in _tok:
            _tok[coll] = http_json(SAS.format(coll))["token"]
    return "/vsicurl/" + href + "?" + _tok[coll]


def search(coll: str, start: str, end: str, lon: float | None = None, lat: float | None = None,
           bbox: list | None = None) -> list:
    body: dict = {"collections": [coll], "limit": 250, "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z"}
    if bbox is not None:
        body["bbox"] = bbox
    else:
        body["intersects"] = {"type": "Point", "coordinates": [lon, lat]}
    feats: list = []
    url = STAC
    while True:
        js = http_json(url, body)
        feats += js.get("features", [])
        nxt = [ln for ln in js.get("links", []) if ln.get("rel") == "next"]
        if not nxt:
            return feats
        nb = dict(body)
        nb.update(nxt[0].get("body", {}))
        body, url = nb, nxt[0].get("href", STAC)


def site_grid(site: dict, res: float = 30.0) -> tuple:
    """Grid on the Landsat lattice (edges at 15 m + k * 30 m); res 10 gives the same square at 10 m."""
    xs, ys = warp_transform(CRS.from_epsg(4326), UTM, [site["lon"]], [site["lat"]])
    h = site["half_m"]
    x0 = np.floor((xs[0] - h - 15.0) / 30.0) * 30.0 + 15.0
    y1 = np.ceil((ys[0] + h - 15.0) / 30.0) * 30.0 + 15.0
    n = int(round(2 * h / res))
    return Affine(res, 0.0, float(x0), 0.0, -res, float(y1)), (n, n)


def dem_on_grid(site: dict, tr: Affine, shape: tuple) -> np.ndarray:
    box = [site["lon"] - 0.12, site["lat"] - 0.09, site["lon"] + 0.12, site["lat"] + 0.09]
    feats = search("cop-dem-glo-30", "2000-01-01", "2030-01-01", bbox=box)
    dem = np.full(shape, np.nan, np.float32)
    for f in feats:
        with Env(**ENVOPT), rasterio.open(sign("cop-dem-glo-30", f["assets"]["data"]["href"])) as src:
            tmp = np.full(shape, np.nan, np.float32)
            reproject(rasterio.band(src, 1), tmp, dst_transform=tr, dst_crs=UTM, dst_nodata=np.nan,
                      resampling=Resampling.bilinear)
            dem = np.where(np.isnan(dem), tmp, dem)
    if np.isnan(dem).any():
        raise RuntimeError(f"DEM gap: {int(np.isnan(dem).sum())} px from {len(feats)} tiles")
    return dem


def read_win(href: str, tr: Affine, shape: tuple) -> np.ndarray:
    with rasterio.open(href) as src:
        if src.crs != UTM:
            raise RuntimeError(f"crs {src.crs}")
        c = (tr.c - src.transform.c) / src.transform.a
        r = (tr.f - src.transform.f) / src.transform.e
        if abs(c - round(c)) > 0.01 or abs(r - round(r)) > 0.01:
            raise RuntimeError(f"grid offset {c:.2f} {r:.2f}")
        win = Window(int(round(c)), int(round(r)), shape[1], shape[0])
        return src.read(1, window=win, boundless=True, fill_value=0)


def one_pass(item: dict, tr: Affine, shape: tuple, zones: dict, out: Path) -> dict:
    p, a = item["properties"], item["assets"]
    coll = "landsat-c2-l2"
    date, plat = p["datetime"][:10], p.get("platform")
    row = dict(id=item["id"], date=date, platform=plat, path=p.get("landsat:wrs_path"),
               slc_off=int(plat == "landsat-7" and date > "2003-05-31"), scene_cc=p.get("eo:cloud_cover"),
               sun_elev=p.get("view:sun_elevation"))
    with Env(**ENVOPT):
        g = read_win(sign(coll, a["green"]["href"]), tr, shape)
        n = read_win(sign(coll, a["nir08"]["href"]), tr, shape)
        s = read_win(sign(coll, a["swir16"]["href"]), tr, shape)
        q = read_win(sign(coll, a["qa_pixel"]["href"]), tr, shape)
    valid = (g > 0) & (n > 0) & (s > 0) & ((q & 1) == 0)
    G = g.astype(np.float32) * 2.75e-5 - 0.2
    N = n.astype(np.float32) * 2.75e-5 - 0.2
    S = s.astype(np.float32) * 2.75e-5 - 0.2
    den = G + S
    ok = np.abs(den) > 1e-6
    ndsi = np.where(ok, (G - S) / np.where(ok, den, 1.0), 0.0)
    snow = valid & (ndsi >= 0.40) & (N >= 0.11)
    loose = valid & (ndsi >= 0.40) & (N >= 0.05)
    bright = valid & (G > 0.30) & (ndsi < 0.40)                    # bright and not snow: cloud
    qcloud = (((q >> 3) & 1) == 1) | (((q >> 2) & 1) == 1)
    qshadow = ((q >> 4) & 1) == 1
    key = f"{date}_{plat}_{row['path']}"
    np.savez_compressed(out / "masks" / f"{key}.npz", snow=snow, loose=loose, valid=valid, bright=bright,
                        qcloud=qcloud, qshadow=qshadow)
    for k, m in zones.items():
        npx = int(m.sum())
        row[f"{k}_valid"] = round(float((valid & m).sum()) / npx, 4)
        row[f"{k}_bright"] = round(float((bright & m).sum()) / npx, 4)
        row[f"{k}_snow_km2"] = round(float((snow & m).sum()) * 9e-4, 4)
        row[f"{k}_loose_km2"] = round(float((loose & m).sum()) * 9e-4, 4)
    fc = np.stack([np.clip(x / 0.7, 0, 1) for x in (S, N, G)], axis=-1)        # swir1, nir, green: snow is cyan
    fc = (fc ** 0.8 * 255).astype(np.uint8)
    fc[~valid] = 0
    Image.fromarray(fc).save(out / "quick" / f"{key}.jpg", quality=88)
    row["key"] = key
    return row


def passes(name: str, y0: int, y1: int) -> None:
    site = SITES[name]
    out = DATA / name
    (out / "masks").mkdir(parents=True, exist_ok=True)
    (out / "quick").mkdir(parents=True, exist_ok=True)
    tr, shape = site_grid(site)
    dem = dem_on_grid(site, tr, shape)
    np.save(out / "dem.npy", dem)
    (out / "grid.json").write_text(json.dumps(dict(crs="EPSG:32639", x0=tr.c, y1=tr.f, res=30.0, n=shape[0],
                                                   lon=site["lon"], lat=site["lat"], z=site["z"])))
    zones = {"z1": dem >= site["z"][0], "z2": dem >= site["z"][1]}
    print(f"{name}: grid {shape}, DEM {dem.min():.0f}-{dem.max():.0f} m, "
          + ", ".join(f"{k} {m.sum() * 9e-4:.2f} km2" for k, m in zones.items()), flush=True)
    items: list = []
    with ThreadPoolExecutor(6) as ex:
        for fs in ex.map(lambda y: search("landsat-c2-l2", f"{y}-07-25", f"{y}-10-20", lon=site["lon"],
                                          lat=site["lat"]), range(y0, y1 + 1)):
            items += fs
    keep = [it for it in items if it["properties"].get("landsat:collection_category") == "T1"]
    print(f"{name}: {len(items)} passes found, {len(keep)} Tier 1", flush=True)
    rows, errs = [], []
    with ThreadPoolExecutor(10) as ex:
        fut = {ex.submit(one_pass, it, tr, shape, zones, out): it["id"] for it in keep}
        for f in as_completed(fut):
            try:
                rows.append(f.result())
            except Exception as e:                    # one failed pass must not stop the others
                errs.append((fut[f], repr(e)[:200]))
    rows.sort(key=lambda r: (r["date"], r["id"]))
    with open(out / "scenes.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    (out / "errors.json").write_text(json.dumps(errs, indent=1))
    print(f"{name}: {len(rows)} passes stored, {len(errs)} errors", flush=True)


def ground(name: str, date: str) -> None:
    """True colour of one Sentinel-2 pass on the 10 m grid of the site's square (fixed stretch)."""
    site = SITES[name]
    tr, shape = site_grid(site, 10.0)
    feats = [f for f in search("sentinel-2-l2a", date, date, lon=site["lon"], lat=site["lat"])]
    if not feats:
        raise SystemExit(f"no Sentinel-2 pass on {date}")
    best, arrs = None, None
    for it in feats:
        p, a = it["properties"], it["assets"]
        off = -1000.0 if float(p.get("s2:processing_baseline", "0") or 0) >= 4.0 else 0.0
        with Env(**ENVOPT):
            bands = []
            for b in ("B04", "B03", "B02"):
                with rasterio.open(sign("sentinel-2-l2a", a[b]["href"])) as src:
                    c = (tr.c - src.transform.c) / src.transform.a
                    r = (tr.f - src.transform.f) / src.transform.e
                    win = Window(int(round(c)), int(round(r)), shape[1], shape[0])
                    bands.append(src.read(1, window=win, boundless=True, fill_value=0, resampling=RS.nearest))
        full = float((bands[0] > 0).mean())
        if best is None or full > best:
            best, arrs = full, [(x.astype(np.float32) + off) / 10000.0 for x in bands]
    rgb = np.stack([np.clip((x - 0.02) / (0.38 - 0.02), 0, 1) for x in arrs], axis=-1)
    rgb = (rgb ** 0.85 * 255).astype(np.uint8)
    out = DATA / name
    out.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb).save(out / f"ground_{date}.jpg", quality=92)
    print(f"{name}: ground_{date}.jpg {rgb.shape[1]} x {rgb.shape[0]} px, {best:.3f} of the square covered")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("site", choices=sorted(SITES))
    ap.add_argument("--years", type=int, nargs=2, default=(1984, 2026))
    ap.add_argument("--ground", help="date of a clear Sentinel-2 pass: write ground_<date>.jpg and stop")
    args = ap.parse_args()
    if args.ground:
        ground(args.site, args.ground)
    else:
        passes(args.site, *args.years)


if __name__ == "__main__":
    main()
