"""BEIJING AND TEHRAN, WINTER NO2 FROM SPACE: the eight-winter test of the Tehran / Beijing ratio.

The pre-registered design (written before the full Beijing record was read): Sentinel-5P TROPOMI OFFL L2 NO2 only,
valid pixels with qa_value >= 0.75, tropospheric column x 6.02214e19 / 1e15, footprint oversampling on 0.02-degree
cells, every day of every winter (1 Azar to 30 Bahman) from 1397 to 1404. The core for both cities is the centre
+- 0.15 deg. A valid day holds at least three valid pixel centres in the core; a winter's value is the day-mean of its
valid days. The per-winter ratio is R = Tehran / Beijing.

Reuse: the granule read (air_compare.read_one, with the radius and the centre table set per worker process), the cell
lattice (air_compare.lattice), the footprint weights (air_compare.W_SUB), the field smoother (air_compare.field_of),
the day-table rule, the inventory parser and the window helpers (air_climatology). Tehran's eight core day-series come
from the climatology cache (data/air/compare/clim) through air_climatology.build_window, the same code that wrote
clim_v1.json; this module reproduces its winter means before using them.

Reads: Beijing, every OFFL granule of the eight winters whose footprint meets the box +- 1.0 deg around the centre (the
same read gives the core day-means and the close-up fields); Tehran, the same radius for winters 1397 and 1404 only
(close-up fields). Pixels within 1.0 deg of a centre are kept; the core uses the pixels within 0.15 deg.

Outputs (data/air/compare/beijing/): inventory.json, plan.json, granules.json (every granule with mode and processor
version), beijing_v1.json (the test), beijing_fields_v1.npz (close-up winter fields), beijing_v1.log. Nothing outside
data/air/compare/beijing and the granule caches under it is written, apart from the 1404 caches read by the
climatology module.

    python -I src/air_beijing.py --search     # STAC inventory: Beijing for 1397-1404, Tehran for 1397 and 1404
    python -I src/air_beijing.py --read       # read the OFFL granules (3 readers, resumable)
    python -I src/air_beijing.py --analyse    # the test, the fields, the log
"""

from __future__ import annotations

import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import air  # noqa: E402
import air_compare as ac  # noqa: E402
import air_climatology as acl  # noqa: E402
import air_grid  # noqa: E402
import get_air  # noqa: E402

BEI = (116.40, 39.90)                             # Beijing centre (all land in the core)
TEH = ac.CITY["tehran"]                           # Tehran centre (51.39 E, 35.69 N)
RAD = 1.0                                         # deg: the read radius (pixels within this of a centre)
PAD = 0.05                                        # deg: search padding around the box
CORE = ac.BOX                                     # deg: the metric core (+- 0.15)
WINTERS = tuple(range(1397, 1405))
TEH_FIELD_WINTERS = (1397, 1404)
FIRST, LAST = (1397, 1398), (1403, 1404)          # the primary: first two vs last two winters
V2_FIRST, V2_LAST = (1400, 1401), (1403, 1404)    # the change within processor v2.x only
READERS = 3
N_BOOT = 10000
SEED = ac.BOOT_SEED
OUT = air.DATA / "compare" / "beijing"
PIX_BEI = OUT / "pix_beijing"                     # per-granule reads, radius 1.0 deg, Beijing
PIX_TEH = OUT / "pix_tehran_r1"                   # per-granule reads, radius 1.0 deg, Tehran (1397 and 1404)
INV = OUT / "inventory.json"
PLAN = OUT / "plan.json"
GRANULES = OUT / "granules.json"
RESULT = OUT / "beijing_v1.json"
FIELDS = OUT / "beijing_fields_v1.npz"
LOG = OUT / "beijing_v1.log"
CLIM_V1 = air.DATA / "compare" / "clim_v1.json"
LOGLINES: list = []


def say(*a) -> None:
    line = " ".join(str(x) for x in a)
    print(line, flush=True)
    LOGLINES.append(line)


def _jsonable(o):
    return o.item() if hasattr(o, "item") else float(o)


# ── 1. the inventory ──

def search_city(name: str, centre: tuple, years: tuple) -> list:
    """Every granule of the box (centre +- RAD + PAD) in each winter window; OFFL kept, other modes counted."""
    cx, cy = centre
    bbox = [cx - RAD - PAD, cy - RAD - PAD, cx + RAD + PAD, cy + RAD + PAD]
    rows: dict = {}
    other: dict = {}
    for y in years:
        g = 2018 + (y - 1397)                     # Gregorian year of Azar 1 (22 November)
        keys = acl.winter_keys(y)
        body = {"collections": ["sentinel-5p-l2-netcdf"], "bbox": bbox,
                "datetime": f"{g}-11-01T00:00:00Z/{g + 1}-03-01T23:59:59Z", "limit": 500,
                "query": {"s5p:product_type": {"eq": "L2__NO2___"}}}
        page, feats = get_air.call(f"{get_air.STAC}/search", body), []
        for _ in range(100):
            feats += page.get("features", [])
            nxt = next((x for x in page.get("links", []) if x.get("rel") == "next"), None)
            if not nxt:
                break
            page = (get_air.call(nxt["href"], nxt.get("body")) if nxt.get("method") == "POST"
                    else get_air.call(nxt["href"]))
        kept = 0
        for f in feats:
            dt = f["properties"]["datetime"]
            if air.jkey(dt[:10]) not in keys:
                continue
            href = next(iter(f["assets"].values()))["href"]
            meta = acl.parse_name(href, f["id"])
            if meta["mode"] != "OFFL":
                other[meta["mode"]] = other.get(meta["mode"], 0) + 1
                continue
            kept += 1
            rows.setdefault(f["id"], dict(id=f["id"], datetime=dt, href=href, mode="OFFL",
                                          version=meta["version"], season=f"W{y}", city=name))
        say(f"search {name} W{y}: {len(feats)} granules returned, {kept} OFFL in the window, total {len(rows)}")
    say(f"search {name}: non-OFFL granules in the window (not used): {other or 'none'}")
    return sorted(rows.values(), key=lambda r: r["datetime"])


def search() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    inv = dict(beijing=search_city("beijing", BEI, WINTERS),
               tehran=search_city("tehran", TEH, TEH_FIELD_WINTERS))
    INV.write_text(json.dumps(inv))
    say("inventory written:", {k: len(v) for k, v in inv.items()})
    return inv


def load_inventory() -> dict:
    if not INV.exists():
        return search()
    return json.loads(INV.read_text())


# ── 2. the reads ──

def _read_worker(row: dict, name: str, centre: tuple, cache: str) -> dict:
    """One granule with the air_compare reader; its centre table, radius and cache are set for this process."""
    ac.CITY = {name: centre}
    ac.PH = RAD
    ac.PIX = Path(cache)
    t = time.time()
    out = ac.read_one(row)
    out["seconds"] = round(time.time() - t, 1)
    out["city"] = name
    return out


def read_all(inv: dict) -> None:
    jobs = [(r, "beijing", BEI, str(PIX_BEI)) for r in inv["beijing"]]
    jobs += [(r, "tehran", TEH, str(PIX_TEH)) for r in inv["tehran"]
             if r["season"] in {f"W{y}" for y in TEH_FIELD_WINTERS}]
    todo = [j for j in jobs if not (Path(j[3]) / f"{j[0]['id']}.npz").exists()]
    say(f"read plan: beijing granules {len(inv['beijing'])}, tehran radius-1.0 granules {len(jobs) - len(inv['beijing'])}, "
        f"cached {len(jobs) - len(todo)}, to read {len(todo)}")
    stat: dict = {}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=READERS) as ex:
        futs = [ex.submit(_read_worker, *j) for j in todo]
        for k, fu in enumerate(as_completed(futs), 1):
            res = fu.result()
            stat[res["status"]] = stat.get(res["status"], 0) + 1
            if res["status"] == "error":
                say("ERROR", res.get("city"), res["id"], res.get("err"))
            if k % 20 == 0 or k == len(futs):
                say(f"read {k}/{len(futs)} elapsed {round(time.time() - t0)} s, status {stat}")
    say("read done", stat, f"{round(time.time() - t0)} s")


# ── 3. the cells and the days (air_compare's rule, one centre, a box of RAD) ──

def land_grid(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Land fraction of each cell (Natural Earth 10 m land, 5 x 5 sub-points), the air_compare rule."""
    import geopandas as gpd
    from shapely import contains_xy
    geom = gpd.read_file(str(air_grid.NE / "ne_10m_land.shp"),
                         bbox=(lon[0] - 0.1, lat[0] - 0.1, lon[-1] + 0.1, lat[-1] + 0.1)).geometry.union_all()
    LO, LA = np.meshgrid(lon, lat)
    frac = np.zeros(LO.shape)
    s = (np.arange(5) + 0.5) / 5 - 0.5
    for a in s:
        for b in s:
            frac += contains_xy(geom, LO + a * ac.STEP, LA + b * ac.STEP)
    return frac / 25


def build_city(centre: tuple, cache: Path, items: list) -> dict:
    cx, cy = centre
    lon, lat = ac.lattice(cx, cy, RAD)
    lon_e, lat_e = lon[0] - ac.STEP / 2, lat[0] - ac.STEP / 2
    ny, nx = lat.size, lon.size
    days = sorted({r["datetime"][:10] for r in items})
    di = {d: k for k, d in enumerate(days)}
    S = np.zeros((len(days), ny, nx))
    W = np.zeros((len(days), ny, nx))
    nv = np.zeros(len(days), int)
    nsub = ac.W_SUB[0].size
    gran = []
    for r in items:
        z = np.load(cache / f"{r['id']}.npz")
        k = di[r["datetime"][:10]]
        if int(z["n"]) == 0:
            gran.append(dict(id=r["id"], core_valid=0, grid_valid=0))
            continue
        la, lo = z["lat"], z["lon"]
        qa, no2 = z["qa"], z["no2"]
        valid = np.isfinite(no2) & (np.abs(no2) < get_air.FILL) & (qa >= air.QA_MIN)
        core_n = int((valid & (np.abs(lo - cx) < CORE) & (np.abs(la - cy) < CORE)).sum())
        nv[k] += core_n
        ii = np.flatnonzero(valid)
        if ii.size:
            clat, clon = z["clat"][ii], z["clon"][ii]
            no2c = no2[ii] * air.K
            lat_s = sum(clat[:, q:q + 1] * ac.W_SUB[q][None, :] for q in range(4))
            lon_s = sum(clon[:, q:q + 1] * ac.W_SUB[q][None, :] for q in range(4))
            ix = np.floor((lon_s - lon_e) / ac.STEP).astype(np.int64)
            iy = np.floor((lat_s - lat_e) / ac.STEP).astype(np.int64)
            ok = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
            cell = (iy * nx + ix)[ok]
            val = np.broadcast_to((no2c / nsub)[:, None], lat_s.shape)[ok]
            S[k] += np.bincount(cell, weights=val, minlength=ny * nx).reshape(ny, nx)
            W[k] += np.bincount(cell, weights=np.full(cell.shape, 1.0 / nsub), minlength=ny * nx).reshape(ny, nx)
        gran.append(dict(id=r["id"], core_valid=core_n, grid_valid=int(ii.size)))
    return dict(days=np.array(days), S=S, W=W, nv=nv, lon=lon, lat=lat, centre=centre, gran=gran)


def day_values(data: dict) -> dict:
    """Per valid day (>= 3 valid pixel centres in the core): the core's cell-sum ratio, as air_compare.day_table."""
    cx, cy = data["centre"]
    LO, LA = np.meshgrid(data["lon"], data["lat"])
    cellm = (np.abs(LO - cx) < CORE) & (np.abs(LA - cy) < CORE)
    SS = data["S"][:, cellm].sum(1)
    WW = data["W"][:, cellm].sum(1)
    out = {}
    for k, d in enumerate(data["days"]):
        v = float(SS[k] / WW[k]) if WW[k] > 0 else float("nan")
        if data["nv"][k] >= 3 and np.isfinite(v):
            out[str(d)] = v
    return out


def split_winters(vals: dict) -> dict:
    out: dict = {y: {} for y in WINTERS}
    for d, v in vals.items():
        s = acl.season_of(d)
        if s is not None and s[0] == "W":
            out[s[1]][d] = v
    return out


# ── 4. the statistics ──

def pooled(means: dict, n: dict, city: str, years: tuple) -> float:
    """Pooled day-mean over several winters: each winter's mean weighted by its valid days."""
    return sum(n[(city, y)] * means[(city, y)] for y in years) / sum(n[(city, y)] for y in years)


def boot_means(vals: dict, B: int, rng) -> dict:
    """Per (city, winter): B bootstrap means over the valid days (days resampled with replacement)."""
    out = {}
    for key, dd in vals.items():
        a = np.array(list(dd.values()))
        out[key] = a[rng.integers(0, a.size, (B, a.size))].mean(1)
    return out


def ci90(x: np.ndarray) -> list:
    return [float(np.percentile(x, 5)), float(np.percentile(x, 95))]


def theil(years_vals: dict) -> dict:
    """Theil-Sen slope over the winters, in percent of the mean of those winters per winter."""
    from scipy.stats import theilslopes
    ys = sorted(years_vals)
    x = np.array(ys, float)
    v = np.array([years_vals[y] for y in ys], float)
    slope = theilslopes(v, x)[0]
    return float(100 * slope / v.mean())


def run_test(T: dict, B: dict) -> dict:
    """The primary, the secondary and the v2.x-only results from the valid-day values per city and winter."""
    rng = np.random.default_rng(SEED)
    vals = {}
    for y in WINTERS:
        vals[("T", y)] = T[y]
        vals[("B", y)] = B[y]
    n = {k: len(v) for k, v in vals.items()}
    m = {k: float(np.mean(list(v.values()))) for k, v in vals.items()}
    bm = boot_means(vals, N_BOOT, rng)
    res: dict = {"per_winter": {}}
    for y in WINTERS:
        r_b = bm[("T", y)] / bm[("B", y)]
        res["per_winter"][y] = dict(tehran_days=n[("T", y)], tehran=m[("T", y)], beijing_days=n[("B", y)],
                                    beijing=m[("B", y)], R=m[("T", y)] / m[("B", y)], R_ci90=ci90(r_b))
    Tm = {y: m[("T", y)] for y in WINTERS}
    Bm = {y: m[("B", y)] for y in WINTERS}
    Rm = {y: Tm[y] / Bm[y] for y in WINTERS}

    def change_block(first: tuple, last: tuple) -> dict:
        def pT(bmm, years):
            return sum(n[("T", y)] * bmm[("T", y)] for y in years) / sum(n[("T", y)] for y in years)

        def pB(bmm, years):
            return sum(n[("B", y)] * bmm[("B", y)] for y in years) / sum(n[("B", y)] for y in years)

        def ptot(mm, city, years):
            return sum(n[(city, y)] * mm[(city, y)] for y in years) / sum(n[(city, y)] for y in years)

        Rf = ptot(m, "T", first) / ptot(m, "B", first)
        Rl = ptot(m, "T", last) / ptot(m, "B", last)
        Rf_b = pT(bm, first) / pB(bm, first)
        Rl_b = pT(bm, last) / pB(bm, last)
        ch_b = Rl_b / Rf_b
        out = dict(first=list(first), last=list(last), R_first=Rf, R_last=Rl, change=Rl / Rf,
                   change_ci90=ci90(ch_b), excludes_1=bool(not (ci90(ch_b)[0] <= 1 <= ci90(ch_b)[1])),
                   change_pct=(Rl / Rf - 1) * 100)
        for city, label in (("T", "tehran"), ("B", "beijing")):
            a = ptot(m, city, first)
            b = ptot(m, city, last)
            cb = (pT(bm, last) if city == "T" else pB(bm, last)) / (pT(bm, first) if city == "T" else pB(bm, first))
            out[label] = dict(first=a, last=b, change=b / a, change_pct=(b / a - 1) * 100,
                              change_ci90=ci90(cb), excludes_1=bool(not (ci90(cb)[0] <= 1 <= ci90(cb)[1])))
        return out

    res["primary"] = change_block(FIRST, LAST)
    res["v2_only"] = change_block(V2_FIRST, V2_LAST)
    yrs = list(WINTERS)
    v2 = [y for y in WINTERS if y >= 1400]
    res["theil_sen_pct_per_winter"] = dict(
        tehran=theil({y: Tm[y] for y in yrs}), beijing=theil({y: Bm[y] for y in yrs}),
        R=theil({y: Rm[y] for y in yrs}))
    res["theil_sen_pct_per_winter_v2x"] = dict(
        tehran=theil({y: Tm[y] for y in v2}), beijing=theil({y: Bm[y] for y in v2}),
        R=theil({y: Rm[y] for y in v2}))
    return res


# ── 5. the fields ──

def winter_fields(data: dict, land: np.ndarray, tag: str, save: dict, summary: dict) -> None:
    days = data["days"]
    for y in WINTERS:
        sel = np.array([acl.season_of(str(d)) == ("W", y) for d in days], bool)
        if not sel.any():
            continue
        S = data["S"][sel].sum(0)
        W = data["W"][sel].sum(0)
        cover = land >= 0.5
        f, local = ac.field_of(S, W, cover)
        mean = np.where(W > ac.WMIN, S / np.maximum(W, 1e-12), np.nan)
        save[f"{tag}_{y}_mean"] = mean.astype(np.float32)
        save[f"{tag}_{y}_weight"] = W.astype(np.float32)
        save[f"{tag}_{y}_field"] = np.where(local, f, np.nan).astype(np.float32)
        save[f"{tag}_{y}_days"] = np.array(int(sel.sum()))
        summary.setdefault(tag, {})[str(y)] = dict(
            days_with_granules=int(sel.sum()),
            box_1deg_pooled=float(S.sum() / W.sum()) if W.sum() > 0 else None,
            cells_with_data=int((W > ac.WMIN).sum()))
    save[f"{tag}_lon"] = data["lon"]
    save[f"{tag}_lat"] = data["lat"]
    save[f"{tag}_land"] = land.astype(np.float32)


# ── 6. the analysis ──

def reproduce_tehran_core() -> dict:
    """Tehran's core day-series from the climatology cache, checked against clim_v1.json before use."""
    plan = json.loads(acl.PLAN_FULL.read_text())
    wdata = acl.build_window(plan, "W")
    vals = ac.day_table(wdata, "tehran", ac.BOX, False)["valid"]
    by = acl.by_season(vals)
    clim = json.loads(CLIM_V1.read_text())["winters"]
    out, ok = {}, True
    for y in WINTERS:
        s = ("W", y)
        mine = by.get(s, {})
        ref = clim[str(y)]
        mean = float(np.mean(list(mine.values()))) if mine else float("nan")
        same = (len(mine) == ref["tehran_days"]) and abs(mean - ref["tehran"]) < 0.05
        ok = ok and same
        out[y] = dict(days=len(mine), mean=mean, clim_v1_days=ref["tehran_days"], clim_v1_mean=ref["tehran"],
                      reproduced=bool(same))
        out[y]["_values"] = mine
    return dict(winters=out, all_reproduced=bool(ok), plan_granules=len(plan["granules"]))


def analyse() -> None:
    t0 = time.time()
    inv = load_inventory()
    say("inventory:", {k: len(v) for k, v in inv.items()})
    # Beijing: every OFFL granule with its read, the cells, the core day-series
    bei_items = [r for r in inv["beijing"] if (PIX_BEI / f"{r['id']}.npz").exists()]
    say(f"beijing granules with a read: {len(bei_items)} of {len(inv['beijing'])}")
    bdata = build_city(BEI, PIX_BEI, bei_items)
    bvals = day_values(bdata)
    B = split_winters(bvals)
    # Tehran core: the climatology cache (checked against clim_v1.json)
    rep = reproduce_tehran_core()
    T = {y: rep["winters"][y].pop("_values") for y in WINTERS}
    say("tehran core reproduced from the climatology cache:", rep["all_reproduced"],
        {y: (rep["winters"][y]["days"], round(rep["winters"][y]["mean"], 2)) for y in WINTERS})
    test = run_test(T, B)
    per_winter = {}
    granules_out = []
    for r in bei_items:
        granules_out.append(dict(city="beijing", id=r["id"], datetime=r["datetime"], season=r["season"],
                                 mode=r["mode"], version=r["version"]))
    for r in inv["tehran"]:
        if (PIX_TEH / f"{r['id']}.npz").exists():
            granules_out.append(dict(city="tehran", id=r["id"], datetime=r["datetime"], season=r["season"],
                                     mode=r["mode"], version=r["version"]))
    gmap = {g["id"]: g for g in granules_out}
    for g_ in bdata["gran"]:
        gmap[g_["id"]].update(core_valid=g_["core_valid"], grid_valid=g_["grid_valid"])
    GRANULES.write_text(json.dumps(granules_out, indent=0))
    versions: dict = {}
    for g in granules_out:
        k = f"{g['city']}|{g['season']}|{g['mode']} {g['version']}"
        versions[k] = versions.get(k, 0) + 1
    for y in WINTERS:
        per_winter[y] = dict(
            beijing_granules=sum(1 for g in granules_out if g["city"] == "beijing" and g["season"] == f"W{y}"),
            beijing_versions={k.split("|")[2]: v for k, v in versions.items() if k.startswith(f"beijing|W{y}|")},
            tehran_versions={k.split("|")[2]: v for k, v in versions.items() if k.startswith(f"tehran|W{y}|")})
    # close-up fields
    fields: dict = {}
    fields_summary: dict = {}
    land_b = land_grid(bdata["lon"], bdata["lat"])
    winter_fields(bdata, land_b, "beijing", fields, fields_summary)
    tgran = [r for r in inv["tehran"] if (PIX_TEH / f"{r['id']}.npz").exists()]
    tdata = build_city(TEH, PIX_TEH, tgran)
    land_t = land_grid(tdata["lon"], tdata["lat"])
    winter_fields(tdata, land_t, "tehran", fields, fields_summary)
    np.savez_compressed(FIELDS, **fields)
    # the result
    result = dict(
        design=dict(radius_deg=RAD, core_deg=CORE, qa_min=air.QA_MIN, column_factor=air.K, mode="OFFL only",
                    first=list(FIRST), last=list(LAST), v2x_first=list(V2_FIRST), v2x_last=list(V2_LAST),
                    bootstrap="days resampled with replacement within each city and winter, 10,000 draws, 90 %",
                    centres=dict(beijing=BEI, tehran=TEH)),
        tehran_core_reproduction=dict(all_reproduced=rep["all_reproduced"], winters=rep["winters"],
                                      plan_granules=rep["plan_granules"]),
        per_winter={str(y): v for y, v in test["per_winter"].items()},
        primary=test["primary"],
        secondary=dict(v2_only=test["v2_only"], theil_sen_pct_per_winter=test["theil_sen_pct_per_winter"],
                       theil_sen_pct_per_winter_v2x=test["theil_sen_pct_per_winter_v2x"]),
        versions={str(y): v for y, v in per_winter.items()},
        fields=fields_summary,
        granules=dict(beijing=len(bei_items), beijing_inventory=len(inv["beijing"]),
                      tehran_radius1=len(tgran), tehran_inventory_1397_1404=len(inv["tehran"])),
        seconds=round(time.time() - t0))
    gate = bool(test["primary"]["excludes_1"])
    bj = test["v2_only"]["beijing"]
    result["gate"] = dict(
        diverging_story_allowed=gate,
        beijing_fell_claim_allowed=bool(bj["change"] < 1 and bj["excludes_1"]),
        note="Beijing's own decline must also hold within v2.x and its interval exclude 1; the secondary "
             "all-version change is caveated across the processor change")
    RESULT.write_text(json.dumps(result, indent=1, default=_jsonable))
    LOG.write_text("\n".join(LOGLINES) + "\n")
    say("result written", RESULT, FIELDS)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    if "--search" in sys.argv:
        search()
    if "--read" in sys.argv:
        inv = load_inventory()
        read_all(inv)
    if "--analyse" in sys.argv:
        analyse()
