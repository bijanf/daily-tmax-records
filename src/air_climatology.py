"""TEHRAN AND ISTANBUL, WINTER NO2 FROM SPACE: the multi-year climatology behind the one-winter comparison.

The method is src/air_compare.py's, reused function by function (the granule read, the 0.02-degree cell sums, the
land mask with the Golden Horn burned in, the day table with at least three valid pixels per day, the bootstrap over
days). What differs is the record: every winter (1 Azar to 30 Bahman) of 1397 to 1404 (2018/19 to 2025/26) for both
cities, every summer (1 Tir to 31 Shahrivar) of 1397 to 1405 (2018 to 2026) for Tehran: the core, and the Tehran-Karaj
box 51.0-51.8 E, 35.4-36.0 N. Sentinel-5P TROPOMI L2 NO2 from Planetary Computer (collection sentinel-5p-l2-netcdf,
product L2__NO2___), qa_value >= 0.75, tropospheric column x 6.02214e19 / 1e15.

Processor versions: the granule file name carries the mode (OFFL, RPRO or NRTI, the STAC label is not always the
same) and the processor version (..._01_010202_... is 01.02.02, ..._03_020901_... is 02.09.01). Every granule's mode and
version are recorded. NRTI granules are never used. The mode per window: RPRO where the collection holds the whole
window in RPRO (summer 1397 only), else OFFL. Winters have no RPRO for their whole window.

The 1404 granules already read for the pre-registration (data/air/compare/pix, read only here) are copied into
data/air/compare/clim/ when needed; new granules are read into data/air/compare/clim/. Nothing else is written.

    python -I src/air_climatology.py --search          # STAC inventory of the record (writes clim/inventory.json)
    python -I src/air_climatology.py --plan            # the granules and the days each window will use (no reading)
    python -I src/air_climatology.py --read            # read the planned granules (3 readers, resumable)
    python -I src/air_climatology.py                   # analysis: clim_v1.json and clim_v1.log
    python -I src/air_climatology.py --every-2nd-day   # every second day of the record (the same days for both cities)
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import air  # noqa: E402
import air_compare as ac  # noqa: E402
from air_compare import day_table  # noqa: E402
import get_air  # noqa: E402

COMP = air.DATA / "compare"
CLIM = COMP / "clim"                              # the new cache: granules, inventory, plan
PIX_RO = COMP / "pix"                             # the 1404 cache: read only
INVENTORY = CLIM / "inventory.json"               # the STAC inventory as searched
PARSED = CLIM / "inventory_parsed.json"           # the inventory with mode and version read from the file names
PLAN_FULL = CLIM / "plan_full.json"        # every granule of the record
PLAN_USED = CLIM / "plan_used.json"      # the granules read and analysed (all, or every second day)
RESULT = COMP / "clim_v1.json"
LOG = COMP / "clim_v1.log"
ac.PIX = CLIM                                   # air_compare reads and builds from the clim cache
CITY = ac.CITY
PH, BOX, SENS = ac.PH, ac.BOX, ac.SENS
TEHRAN_KARAJ = (51.0, 35.4, 51.8, 36.0)           # W, S, E, N: the Tehran-Karaj box of the other reel
WINTER_YEARS = range(1397, 1405)                  # Azar 1397 to Bahman 1404
SUMMER_YEARS = range(1397, 1406)                  # Tir 1397 to Shahrivar 1405
BOOT_SEED = ac.BOOT_SEED
N_BOOT = 10000
READERS = 3
NAME_RE = re.compile(r"^S5P_(OFFL|RPRO|NRTI)_L2__NO2____")
VER_RE = re.compile(r"_(\d{2})_(\d{2})(\d{2})(\d{2})_\d{8}T\d{6}\.nc$")
DATE_MONTHS = (6, 7, 8, 9, 11, 12, 1, 2)          # Gregorian months holding every Tir-Shahrivar and Azar-Bahman day
LOGLINES: list = []


def say(*a) -> None:
    line = " ".join(str(x) for x in a)
    print(line, flush=True)
    LOGLINES.append(line)


def winter_keys(y: int) -> tuple:
    return (f"{y}-09", f"{y}-10", f"{y}-11")      # Azar, Dey, Bahman


def summer_keys(y: int) -> tuple:
    return (f"{y}-04", f"{y}-05", f"{y}-06")      # Tir, Mordad, Shahrivar


def season_of(d: str) -> tuple | None:
    """('W', y) or ('S', y) for a calendar day, None outside the windows."""
    jk = air.jkey(d)
    y, m = int(jk[:4]), int(jk[5:])
    if m in (9, 10, 11) and y in WINTER_YEARS:
        return ("W", y)
    if m in (4, 5, 6) and y in SUMMER_YEARS:
        return ("S", y)
    return None


def _check_windows() -> None:
    """The window edges, asserted with the converter (Azar 1 and Bahman 30, Tir 1 and Shahrivar 31)."""
    assert air.jkey("2018-11-22") == "1397-09" and air.jkey("2018-11-21") == "1397-08"
    assert air.jkey("2019-02-19") == "1397-11" and air.jkey("2019-02-20") == "1397-12"
    assert air.jkey("2018-06-22") == "1397-04" and air.jkey("2018-06-21") == "1397-03"
    assert air.jkey("2018-09-22") == "1397-06" and air.jkey("2018-09-23") == "1397-07"


_check_windows()


# ── 1. the inventory: every granule of the record, with its mode and processor version ──

def parse_name(href: str, gid: str) -> dict:
    fname = href.rsplit("/", 1)[-1]
    m = NAME_RE.match(fname) or NAME_RE.match(gid)
    v = VER_RE.search(fname)
    return dict(mode=m.group(1) if m else "?",
                version=f"{int(v.group(2))}.{int(v.group(3))}.{int(v.group(4))}" if v else "?")


def search_inventory() -> list:
    """STAC search over both city boxes, month by month over the window months, every mode kept."""
    rows: dict = {}
    months = [(y, m) for y in range(2018, 2027) for m in DATE_MONTHS
              if not ((y == 2018 and m < 6) or (y == 2026 and m > 9))]
    for c, (cx, cy) in CITY.items():
        bbox = [cx - PH - 0.05, cy - PH - 0.05, cx + PH + 0.05, cy + PH + 0.05]
        for y, m in months:
            last = {1: 31, 2: 28 if y % 4 else 29, 6: 30, 7: 31, 8: 31, 9: 30, 11: 30, 12: 31}[m]
            body = {"collections": ["sentinel-5p-l2-netcdf"], "bbox": bbox,
                    "datetime": f"{y}-{m:02d}-01T00:00:00Z/{y}-{m:02d}-{last:02d}T23:59:59Z", "limit": 500,
                    "query": {"s5p:product_type": {"eq": "L2__NO2___"}}}
            page = get_air.call(f"{get_air.STAC}/search", body)
            feats = []
            for _ in range(100):
                feats += page.get("features", [])
                nxt = next((x for x in page.get("links", []) if x.get("rel") == "next"), None)
                if not nxt:
                    break
                page = (get_air.call(nxt["href"], nxt.get("body")) if nxt.get("method") == "POST"
                        else get_air.call(nxt["href"]))
            for f in feats:
                href = next(iter(f["assets"].values()))["href"]
                row = rows.setdefault(f["id"], dict(id=f["id"], datetime=f["properties"]["datetime"],
                                                    stac_mode=f["properties"].get("s5p:processing_mode"),
                                                    href=href, cities=[]))
                if c not in row["cities"]:
                    row["cities"].append(c)
            say(f"search {c} {y}-{m:02d}: {len(feats)} granules, total {len(rows)}")
    out = sorted(rows.values(), key=lambda r: r["datetime"])
    CLIM.mkdir(parents=True, exist_ok=True)
    INVENTORY.write_text(json.dumps(out))
    return out


def load_inventory() -> list:
    """The searched inventory with mode and version parsed from the file names (written as a new file)."""
    if PARSED.exists():
        return json.loads(PARSED.read_text())
    rows = json.loads(INVENTORY.read_text())
    for r in rows:
        r.update(parse_name(r["href"], r["id"]))
    PARSED.write_text(json.dumps(rows))
    return rows


# ── 2. the plan: which granules each window uses, and the days (no reading) ──

def mode_for(season: tuple, rows: list) -> str:
    """RPRO where the whole window is in RPRO, else OFFL. Never NRTI."""
    kind, y = season
    keys = winter_keys(y) if kind == "W" else summer_keys(y)
    in_win = [r for r in rows if air.jkey(r["datetime"][:10]) in keys]
    days = {r["datetime"][:10] for r in in_win}
    rpro_days = {r["datetime"][:10] for r in in_win if r["mode"] == "RPRO"}
    if days and rpro_days == days:
        return "RPRO"
    return "OFFL"


def make_plan() -> dict:
    """The full record's granules (every day of every window) and the days, written to plan_full.json."""
    rows = load_inventory()
    chosen = []
    modes = {}
    for kind, years in (("W", WINTER_YEARS), ("S", SUMMER_YEARS)):
        for y in years:
            keys = winter_keys(y) if kind == "W" else summer_keys(y)
            pool = [r for r in rows if air.jkey(r["datetime"][:10]) in keys]
            mode = mode_for((kind, y), pool)
            modes[f"{kind}{y}"] = mode
            for r in pool:
                if r["mode"] != mode:
                    continue
                if kind == "S" and "tehran" not in r["cities"]:
                    continue
                chosen.append(dict(id=r["id"], datetime=r["datetime"], href=r["href"], mode=r["mode"],
                                   version=r["version"], cities=r["cities"], season=f"{kind}{y}"))
    days = sorted({r["datetime"][:10] for r in chosen})
    plan = dict(every_2nd_day=False, modes=modes, days=len(days), granules=chosen)
    CLIM.mkdir(parents=True, exist_ok=True)
    PLAN_FULL.write_text(json.dumps(plan))
    return plan


def subsample(plan: dict) -> dict:
    """Every second day of the record (the same days for both cities): the read and analysis set."""
    days = sorted({r["datetime"][:10] for r in plan["granules"]})
    keep = set(days[::2])
    used = [r for r in plan["granules"] if r["datetime"][:10] in keep]
    return dict(every_2nd_day=True, modes=plan["modes"], days=len(keep), granules=used)


# ── 3. the reads: the 1404 cache copied (read only), the rest read into clim/ with three readers ──

def stage_cached_1404(plan: dict) -> int:
    n = 0
    for r in plan["granules"]:
        dst = CLIM / f"{r['id']}.npz"
        src = PIX_RO / f"{r['id']}.npz"
        if not dst.exists() and src.exists():
            shutil.copy2(src, dst)
            n += 1
    return n


def timed_read(row: dict) -> dict:
    t = time.time()
    out = ac.read_one(row)
    out["seconds"] = round(time.time() - t, 1)
    return out


def read_plan(plan: dict) -> None:
    ac.PIX = CLIM                                  # the read writes into clim/ (ac.read_one uses ac.PIX)
    copied = stage_cached_1404(plan)
    todo = [r for r in plan["granules"] if not (CLIM / f"{r['id']}.npz").exists()]
    say(f"plan granules {len(plan['granules'])}, copied from the read-only 1404 cache {copied}, to read {len(todo)}")
    stat: dict = {}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=READERS) as ex:
        futs = [ex.submit(timed_read, r) for r in todo]
        for k, fu in enumerate(as_completed(futs), 1):
            res = fu.result()
            stat[res["status"]] = stat.get(res["status"], 0) + 1
            if res["status"] == "error":
                say("ERROR", res)
            if k % 25 == 0 or k == len(futs):
                say(f"read {k}/{len(futs)} elapsed {round(time.time() - t0)} s, status {stat}")
    say("read done", stat, f"{round(time.time() - t0)} s")


# ── 4. the analysis: the same cell and day tables as air_compare, for each window ──

@contextmanager
def window_keys(keys: tuple):
    """air_compare.build_cells keeps the days whose Jalali month is in air.WINTER_JK; the record's keys go there."""
    old = air.WINTER_JK
    air.WINTER_JK = tuple(keys)
    try:
        yield
    finally:
        air.WINTER_JK = old


def build_window(plan: dict, kind: str) -> dict:
    items = [r for r in plan["granules"] if r["season"][0] == kind and (CLIM / f"{r['id']}.npz").exists()]
    keys = tuple(k for y in (WINTER_YEARS if kind == "W" else SUMMER_YEARS)
                 for k in (winter_keys(y) if kind == "W" else summer_keys(y)))
    with window_keys(keys):
        return ac.build_cells(items)


def box_table(data: dict, W: float, S: float, E: float, N: float) -> dict:
    """air_compare.day_table for a rectangle (Tehran's cells, all land): per day the box value and pixel count."""
    m = data["masks"]["tehran"]
    LO, LA = np.meshgrid(m["lon"], m["lat"])
    cellm = (LO > W) & (LO < E) & (LA > S) & (LA < N)
    p = data["pix"]
    ci = list(CITY).index("tehran")
    pm = (p["city"] == ci) & (p["lon"] > W) & (p["lon"] < E) & (p["lat"] > S) & (p["lat"] < N) & p["valid"]
    nv = np.bincount(p["day"][pm], minlength=len(data["days"]))
    SS = data["S"]["tehran"][:, cellm].sum(1)
    WW = data["W"]["tehran"][:, cellm].sum(1)
    valid = {}
    for k, d in enumerate(data["days"]):
        v = float(SS[k] / WW[k]) if WW[k] > 0 else np.nan
        if nv[k] >= 3 and np.isfinite(v):
            valid[str(d)] = v
    return dict(valid=valid, n=len(valid), mean=float(np.mean(list(valid.values()))) if valid else float("nan"))


def by_season(valid: dict) -> dict:
    out: dict = {}
    for d, v in valid.items():
        s = season_of(d)
        if s is not None:
            out.setdefault(s, {})[d] = v
    return out


def winter_boot(T: dict, I: dict, n: int = N_BOOT) -> tuple:
    """Eight-winter ratio of the winter day-means: winters resampled with replacement, then the days within each."""
    rng = np.random.default_rng(BOOT_SEED)
    ws = sorted(T)
    A = [np.array(list(T[w].values())) for w in ws]
    B = [np.array(list(I[w].values())) for w in ws]
    nw = len(ws)
    pick = rng.integers(0, nw, (n, nw))
    tm = np.zeros((n, nw))
    im = np.zeros((n, nw))
    for s in range(nw):
        for j in range(nw):
            rows = np.flatnonzero(pick[:, s] == j)
            if rows.size == 0:
                continue
            tm[rows, s] = A[j][rng.integers(0, A[j].size, (rows.size, A[j].size))].mean(1)
            im[rows, s] = B[j][rng.integers(0, B[j].size, (rows.size, B[j].size))].mean(1)
    ratio = tm.mean(1) / im.mean(1)
    mean_t = np.mean([a.mean() for a in A])
    mean_i = np.mean([b.mean() for b in B])
    return float(mean_t / mean_i), float(np.percentile(ratio, 5)), float(np.percentile(ratio, 95))


def versions_of(plan: dict, season: str) -> dict:
    out: dict = {}
    for r in plan["granules"]:
        if r["season"] == season:
            k = f"{r['mode']} {r['version']}"
            out[k] = out.get(k, 0) + 1
    return out


def analyse(plan: dict, full: dict) -> dict:
    t0 = time.time()
    wdata = build_window(plan, "W")
    sdata = build_window(plan, "S")
    say(f"winter days {len(wdata['days'])}, summer days {len(sdata['days'])}")
    # winters: the core for both cities (air_compare's day_table), the box for Tehran
    Tcore_w = day_table(wdata, "tehran", BOX, False)["valid"]
    Icity_w = day_table(wdata, "istanbul", BOX, True)["valid"]
    Ibox_all_w = day_table(wdata, "istanbul", BOX, False)["valid"]
    Tbox_w = box_table(wdata, *TEHRAN_KARAJ)["valid"]
    Tcore_s = day_table(sdata, "tehran", BOX, False)["valid"]
    Tbox_s = box_table(sdata, *TEHRAN_KARAJ)["valid"]
    TW, IW = by_season(Tcore_w), by_season(Icity_w)
    TBW = by_season(Tbox_w)
    TS, TBS = by_season(Tcore_s), by_season(Tbox_s)
    winters = {}
    for y in WINTER_YEARS:
        s = ("W", y)
        t, i = TW.get(s, {}), IW.get(s, {})
        if not t or not i:
            winters[y] = dict(missing=True, tehran_days=len(t), istanbul_days=len(i))
            continue
        r, lo, hi = ac.ratio_ci(t, i)
        winters[y] = dict(
            tehran_days=len(t), tehran=float(np.mean(list(t.values()))),
            istanbul_days=len(i), istanbul=float(np.mean(list(i.values()))),
            ratio=r, ci90=[lo, hi],
            tehran_box_days=len(TBW.get(s, {})),
            tehran_box=float(np.mean(list(TBW[s].values()))) if TBW.get(s) else None,
            versions=versions_of(plan, f"W{y}"))
        if s in TBW:
            winters[y]["box_over_istanbul_ratio"] = float(np.mean(list(TBW[s].values())) / np.mean(list(i.values())))
    say("per winter", {y: (round(v.get("ratio", float("nan")), 2), v.get("tehran_days"), v.get("istanbul_days"))
                       for y, v in winters.items()})
    full_w = [y for y in WINTER_YEARS if not winters[y].get("missing")]
    eight = {}
    if len(full_w) >= 2:
        rt = {("W", y): TW[("W", y)] for y in full_w}
        ri = {("W", y): IW[("W", y)] for y in full_w}
        m, lo, hi = winter_boot(rt, ri)
        eight = dict(winters=full_w, ratio=m, ci90=[lo, hi],
                     lowest=min(full_w, key=lambda y: winters[y]["ratio"]),
                     highest=max(full_w, key=lambda y: winters[y]["ratio"]))
    # summer and winter of the same Jalali year (Tehran, core and box)
    sw = {}
    for y in range(1397, 1405):
        w, s_ = ("W", y), ("S", y)
        entry = {}
        if TW.get(w) and TS.get(s_):
            entry["core"] = float(np.mean(list(TW[w].values())) / np.mean(list(TS[s_].values())))
            entry["core_days"] = [len(TW[w]), len(TS[s_])]
        if TBW.get(w) and TBS.get(s_):
            entry["box"] = float(np.mean(list(TBW[w].values())) / np.mean(list(TBS[s_].values())))
            entry["box_days"] = [len(TBW[w]), len(TBS[s_])]
        if entry:
            sw[y] = entry
    summers = {y: dict(core_days=len(TS.get(("S", y), {})),
                       core=float(np.mean(list(TS[("S", y)].values()))) if TS.get(("S", y)) else None,
                       box_days=len(TBS.get(("S", y), {})),
                       box=float(np.mean(list(TBS[("S", y)].values()))) if TBS.get(("S", y)) else None,
                       versions=versions_of(plan, f"S{y}")) for y in SUMMER_YEARS}
    result = dict(plan_every_2nd_day=plan["every_2nd_day"], modes=plan["modes"], winters=winters,
                  eight_winters=eight, summer_winter=sw, summers=summers,
                  unpaired_summer_1405=summers[1405],
                  seconds_analysis=round(time.time() - t0))
    # the 1404 check (the pre-registered values)
    if winters.get(1404) and not winters[1404].get("missing"):
        w = winters[1404]
        result["check_1404"] = dict(tehran=(round(w["tehran"], 1), w["tehran_days"]),
                                    istanbul_land=(round(w["istanbul"], 1), w["istanbul_days"]),
                                    ratio=round(w["ratio"], 2), ci90=[round(x, 2) for x in w["ci90"]],
                                    expected=dict(tehran=72.2, days_tehran=61, istanbul=12.4, days_istanbul=31,
                                                  ratio=5.82, ci90=[4.54, 7.68]))
    # the 1404 reproduction on every day (the 1404 granules are all cached), next to the used set's 1404
    w1404 = dict(granules=[r for r in full["granules"] if r["season"] == "W1404"], modes=full["modes"], every_2nd_day=False)
    if all((CLIM / f"{r['id']}.npz").exists() for r in w1404["granules"]) and w1404["granules"]:
        d = build_window(w1404, "W")
        t = day_table(d, "tehran", BOX, False)["valid"]
        i = day_table(d, "istanbul", BOX, True)["valid"]
        tt, ii = by_season(t).get(("W", 1404), {}), by_season(i).get(("W", 1404), {})
        r1404, lo, hi = ac.ratio_ci(tt, ii)
        result["check_1404_all_days"] = dict(tehran=(round(float(np.mean(list(tt.values()))), 1), len(tt)),
                                             istanbul_land=(round(float(np.mean(list(ii.values()))), 1), len(ii)),
                                             ratio=round(r1404, 2), ci90=[round(lo, 2), round(hi, 2)])
    result["version_tests"] = version_tests(winters, plan)
    return result


def version_tests(winters: dict, plan: dict) -> dict:
    """The ratio before and after a processor change inside one winter, and the ratio step at each winter edge."""
    out = {}
    edges = []
    prev = None
    for y in WINTER_YEARS:
        w = winters.get(y, {})
        if w.get("missing"):
            continue
        vs = tuple(sorted(w["versions"]))
        if prev is not None:
            edges.append(dict(from_winter=prev[0], to_winter=y, same_version=prev[1] == vs,
                              ratio_jump=round(w["ratio"] - prev[2], 2)))
        prev = (y, vs, w["ratio"])
    out["winter_edges"] = edges
    return out


def write_result(result: dict) -> None:
    RESULT.write_text(json.dumps(result, indent=1, ensure_ascii=False, default=float))
    LOG.write_text("\n".join(LOGLINES) + "\n")


if __name__ == "__main__":
    every = "--every-2nd-day" in sys.argv
    if "--search" in sys.argv:
        search_inventory()
        load_inventory()
    if "--plan" in sys.argv or "--read" in sys.argv:
        full = make_plan()
        plan = subsample(full) if every else full
        PLAN_USED.write_text(json.dumps(plan))
        say(f"plan: modes {full['modes']}, record days {full['days']}, granules {len(full['granules'])}; "
            f"used: days {plan['days']}, granules {len(plan['granules'])}")
        if "--read" in sys.argv:
            read_plan(plan)
    if not any(a in sys.argv for a in ("--search", "--plan", "--read")):
        full = json.loads(PLAN_FULL.read_text())
        plan = json.loads(PLAN_USED.read_text())
        result = analyse(plan, full)
        write_result(result)
        say(json.dumps(result.get("check_1404", {})))
