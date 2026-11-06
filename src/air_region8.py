"""TEHRAN AND ISTANBUL, EIGHT WINTERS OF NO2 FROM SPACE: the regional winter field of air_compare, averaged over the
winters 1397 to 1404 (Jalali). The same method as air_compare's region mode (region v1), reused by import:
Sentinel-5P TROPOMI OFFL L2 NO2, valid pixels only (qa_value >= 0.75), each pixel spread over its footprint on the
0.02-degree lattice of the region grid, the NRTI granules only on a day with no OFFL granule over the region, the
fields smoothed by normalised convolution, clipped to the land of Iran and Turkey.

The calendar rule: every 4th day of each winter, counted from 1 Azar (day 0, 4, 8, ..., 88 of the 90 days Azar to
Bahman), the same rule for every winter. The winter field is pooled over its days; the eight-winter mean gives each
winter that covers a cell the same weight.

Inputs: the STAC search (sentinel-5p-l2-netcdf over the region), the granules through air_compare.read_region (the
pixel caches of data/air/compare/region and data/air/fine are read only: the 1404 granules are linked, not copied).
Outputs, all under data/air/compare/region8/: region8_items.json, granules/ (per-granule pixel files, links into
region/ for the cached granules), region8_days_v1.json, region_8winters_v1.npz and region_8winters_v1.log.

    python -I src/air_region8.py              # search (if needed), read the missing granules (3 readers), build
    python -I src/air_region8.py --search     # search again
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import air  # noqa: E402
import air_compare as ac  # noqa: E402
import air_grid  # noqa: E402
import get_air  # noqa: E402

WINTERS = tuple(range(1397, 1405))
STRIDE = 4                                       # every 4th day of the winter, counted from 1 Azar
OUT = air.DATA / "compare" / "region8"
GR = OUT / "granules"                            # the per-granule pixel files of this run
ITEMS = OUT / "region8_items.json"
DAYS = OUT / "region8_days_v1.json"
FIELD = OUT / "region_8winters_v1.npz"
LOG = OUT / "region_8winters_v1.log"
SRC = ac.RDIR                                    # the region v1 pixel cache (read only)
CLIM = air.DATA / "compare" / "clim_v1.json"
LINES: list = []


def say(*a) -> None:
    line = " ".join(str(x) for x in a)
    print(line, flush=True)
    LINES.append(line)


# ── the calendar: 90 days per winter, from 1 Azar (Jalali month 9) ──

def winter_days(y: int) -> list:
    d = dt.date(y + 621, 11, 1)                  # 1 Azar falls between 21 and 22 November in every winter here
    while air.jalali(d.isoformat()) != (y, 9, 1):
        d += dt.timedelta(days=1)
    days = [(d + dt.timedelta(days=k)).isoformat() for k in range(90)]
    assert air.jalali(days[-1]) == (y, 11, 30), y
    assert all(air.jalali(x)[1] in (9, 10, 11) for x in days), y
    return days


# ── the granules: the STAC search over the region, per winter ──

def search_winter(y: int, full: list, sel: set) -> list:
    body = {"collections": ["sentinel-5p-l2-netcdf"], "bbox": list(ac.RBOX),
            "datetime": f"{full[0]}T00:00:00Z/{full[-1]}T23:59:59Z", "limit": 500,
            "query": {"s5p:product_type": {"eq": "L2__NO2___"}}}
    page, feats = get_air.call(f"{get_air.STAC}/search", body), []
    for _ in range(100):
        feats += page.get("features", [])
        nxt = next((x for x in page.get("links", []) if x.get("rel") == "next"), None)
        if not nxt:
            break
        page = (get_air.call(nxt["href"], nxt.get("body")) if nxt.get("method") == "POST"
                else get_air.call(nxt["href"]))
    rows = {}
    for f in feats:
        mode = f["properties"].get("s5p:processing_mode")
        day = f["properties"]["datetime"][:10]
        if mode not in ac.MODE_OF or day not in sel:
            continue
        rows.setdefault(f["id"], dict(id=f["id"], datetime=f["properties"]["datetime"], mode=mode, winter=y,
                                      href=next(iter(f["assets"].values()))["href"]))
    say(f"winter {y}: search {len(feats)} granules, selected days {len(sel)}, OFFL+NRTI in them {len(rows)}")
    return sorted(rows.values(), key=lambda r: r["datetime"])


def link_cached(rows: list) -> int:
    """The granules already read by region v1 are linked into this run's folder (read only on the source side)."""
    n = 0
    for r in rows:
        src, dst = SRC / f"{r['id']}.npz", GR / f"{r['id']}.npz"
        if src.exists() and not os.path.lexists(dst):
            os.symlink(src, dst)
            n += 1
    return n


# ── the build: the pooled winter fields, the eight-winter mean, the checks ──

def build(rows: list, sel: dict, full: dict) -> None:
    t0 = time.time()
    g = ac.RGRID
    ny, nx = g["ny"], g["nx"]
    ncell = nx * ny
    wts = air_grid._subpoints()
    days = [d for y in WINTERS for d in sel[y]]
    day_i = {d: k for k, d in enumerate(days)}
    win_of = {d: y for y in WINTERS for d in sel[y]}
    mode_of_day = {}
    for r in rows:
        mode_of_day.setdefault(r["datetime"][:10], r["mode"])
    crop = {c: ac.city_crop(c) for c in ac.CITY}
    lnd = {c: ac.land_fraction(c) for c in ac.CITY}
    CS = {c: np.zeros((2, len(days), crop[c]["h"], crop[c]["w"])) for c in ac.CITY}
    CW = {c: np.zeros((2, len(days), crop[c]["h"], crop[c]["w"])) for c in ac.CITY}
    NV = {c: np.zeros((2, len(days)), int) for c in ac.CITY}
    NVL = {c: np.zeros((2, len(days)), int) for c in ac.CITY}
    Sw = {y: np.zeros(ncell) for y in WINTERS}
    Ww = {y: np.zeros(ncell) for y in WINTERS}
    npx, nmiss, ngrid = 0, 0, 0
    for r in rows:
        if not (ac.RDIR / f"{r['id']}.npz").exists():
            nmiss += 1
            continue
        res = ac.region_pixels(r)
        if res is None:
            continue
        day = r["datetime"][:10]
        if day not in day_i:
            continue
        k, md, y = day_i[day], ac.MODE_OF[r["mode"]], win_of[day]
        npx += res["no2"].size
        ngrid += 1
        ix, iy, val, unit = ac.region_deposit(None, None, res, wts)
        cell = iy * nx + ix
        Sw[y] += np.bincount(cell, weights=val, minlength=ncell)
        Ww[y] += np.bincount(cell, weights=unit, minlength=ncell)
        for c in ac.CITY:
            cr = crop[c]
            sel_ = (ix >= cr["x0"]) & (ix < cr["x1"]) & (iy >= cr["y0"]) & (iy < cr["y1"])
            loc = (iy[sel_] - cr["y0"]) * cr["w"] + (ix[sel_] - cr["x0"])
            CS[c][md, k] += np.bincount(loc, weights=val[sel_], minlength=cr["w"] * cr["h"]).reshape(cr["h"], cr["w"])
            CW[c][md, k] += np.bincount(loc, weights=unit[sel_], minlength=cr["w"] * cr["h"]).reshape(cr["h"], cr["w"])
            cx, cy = ac.CITY[c]
            m = lnd[c]
            lon_e, lat_e = m["lon"][0] - ac.STEP / 2, m["lat"][0] - ac.STEP / 2
            inb = (np.abs(res["lon"] - cx) < ac.BOX) & (np.abs(res["lat"] - cy) < ac.BOX)
            ixc = np.floor((res["lon"] - lon_e) / ac.STEP).astype(int)
            iyc = np.floor((res["lat"] - lat_e) / ac.STEP).astype(int)
            inside_ = (ixc >= 0) & (ixc < m["lon"].size) & (iyc >= 0) & (iyc < m["lat"].size)
            landc = np.zeros(ixc.size, bool)
            landc[inside_] = m["frac"][iyc[inside_], ixc[inside_]] >= 0.5
            NV[c][md, k] += int(inb.sum())
            NVL[c][md, k] += int((inb & landc).sum())
    say(f"granules gridded {ngrid}, missing from the cache {nmiss}, pixels {npx}; seconds {time.time() - t0:.0f}")

    # the box of each city on the crop (Tehran: all cells; Istanbul: land cells of the crop), and the day values
    box = {}
    for c in ac.CITY:
        cr, m = crop[c], lnd[c]
        cx, cy = ac.CITY[c]
        cl_lon = g["lon0"] + (np.arange(cr["x0"], cr["x1"]) + 0.5) * ac.STEP
        cl_lat = g["lat0"] - (np.arange(cr["y0"], cr["y1"]) + 0.5) * ac.STEP
        CLO, CLA = np.meshgrid(cl_lon, cl_lat)
        b = (np.abs(CLO - cx) < ac.BOX) & (np.abs(CLA - cy) < ac.BOX)
        if c == "istanbul":
            fr = np.zeros(CLO.shape)
            ii = np.rint((CLO - m["lon"][0]) / ac.STEP).astype(int)
            jj = np.rint((CLA - m["lat"][0]) / ac.STEP).astype(int)
            okk = (ii >= 0) & (ii < m["lon"].size) & (jj >= 0) & (jj < m["lat"].size)
            fr[okk] = m["frac"][jj[okk], ii[okk]]
            b &= fr >= 0.5
        box[c] = b

    recs = []
    for k, d in enumerate(days):
        rec = dict(day=d, winter=win_of[d], jalali=air.jkey(d), mode=mode_of_day.get(d))
        for c in ac.CITY:
            ss = sum(CS[c][md, k][box[c]].sum() for md in (0, 1))
            ww = sum(CW[c][md, k][box[c]].sum() for md in (0, 1))
            nv = int(sum((NVL if c == "istanbul" else NV)[c][md, k] for md in (0, 1)))
            rec[c] = float(ss / ww) if ww > 0 else None
            rec[c + "_nv"] = nv
        recs.append(rec)
    # each city's valid days (at least 3 valid pixel centres in its box), as the every-day climatology of clim_v1
    valid = {c: [r for r in recs if r[c] is not None and r[c + "_nv"] >= 3] for c in ac.CITY}

    # per-winter cores (equal weight per day inside a winter) and the eight-winter values
    core = {}
    for y in WINTERS:
        cy_ = {c: [r[c] for r in valid[c] if r["winter"] == y] for c in ac.CITY}
        if cy_["tehran"] and cy_["istanbul"]:
            core[y] = dict(tehran=float(np.mean(cy_["tehran"])), istanbul=float(np.mean(cy_["istanbul"])),
                           n_t=len(cy_["tehran"]), n_i=len(cy_["istanbul"]),
                           n_all=sum(1 for r in recs if r["winter"] == y))
    ymean_t = float(np.mean([core[y]["tehran"] for y in core]))
    ymean_i = float(np.mean([core[y]["istanbul"] for y in core]))
    pool_t = float(np.mean([r["tehran"] for r in valid["tehran"]]))
    pool_i = float(np.mean([r["istanbul"] for r in valid["istanbul"]]))

    # the fields: pooled per winter, then the eight-winter mean over the winters that cover each cell
    inside = air_grid.burn(air_grid.ne_countries_polygons({"Iran", "Turkey"}, g), g) > 0
    F, C, save = {}, {}, {}
    for y in WINTERS:
        f, cov = air_grid.field_of(Sw[y].reshape(ny, nx), Ww[y].reshape(ny, nx), inside)
        F[y], C[y] = f, cov
        save[f"winter_{y}"] = f
        save[f"cov_winter_{y}"] = cov.astype(np.uint8)
    Fa = np.stack([F[y] for y in WINTERS]).astype(np.float64)
    Ca = np.stack([C[y] for y in WINTERS]).astype(np.float64)
    cnt = Ca.sum(0)
    w8 = np.where(cnt > 0, Fa.sum(0) / np.maximum(cnt, 1), 0.0).astype(np.float32)
    cov8 = cnt > 0
    lon_ax, lat_ax = air_grid.grid_axes(g)
    save.update(lon=lon_ax, lat=lat_ax, inside=inside.astype(np.uint8), winter8=w8,
                cov_winter8=cov8.astype(np.uint8), n_winters_cover=cnt.astype(np.uint8),
                winters=np.array(WINTERS), stride=np.array(STRIDE))
    np.savez_compressed(FIELD, **save)
    DAYS.write_text(json.dumps(dict(days=recs, grid=g, box=ac.BOX, stride=STRIDE,
                                    winters={str(y): dict(full=full[y], selected=sel[y]) for y in WINTERS}),
                               indent=1, ensure_ascii=False))

    # the checks on the field: the land-core means of the eight-winter field
    LO, LA = np.meshgrid(lon_ax, lat_ax)
    fb = (np.abs(LO - ac.CITY["tehran"][0]) < ac.BOX) & (np.abs(LA - ac.CITY["tehran"][1]) < ac.BOX) & cov8
    m = lnd["istanbul"]
    ii = np.rint((LO - m["lon"][0]) / ac.STEP).astype(int)
    jj = np.rint((LA - m["lat"][0]) / ac.STEP).astype(int)
    okk = (ii >= 0) & (ii < m["lon"].size) & (jj >= 0) & (jj < m["lat"].size)
    fr = np.zeros(LO.shape)
    fr[okk] = m["frac"][jj[okk], ii[okk]]
    ib = (np.abs(LO - ac.CITY["istanbul"][0]) < ac.BOX) & (np.abs(LA - ac.CITY["istanbul"][1]) < ac.BOX) & \
         (fr >= 0.5) & cov8
    ft, fi = float(w8[fb].mean()), float(w8[ib].mean())
    say(f"CHECK winter8 field, Tehran land core (box +-{ac.BOX}, {int(fb.sum())} cells): {ft:.1f}")
    say(f"CHECK winter8 field, Istanbul land core (box +-{ac.BOX}, {int(ib.sum())} cells): {fi:.1f}")
    say(f"CHECK winter8 field ratio Tehran / Istanbul: {ft / fi:.2f}")
    say(f"CHECK day means over all valid days (equal weight per day, every {STRIDE}th day): Tehran {pool_t:.1f}, "
        f"Istanbul land {pool_i:.2f} on {len(valid['tehran'])} and {len(valid['istanbul'])} days, ratio {pool_t / pool_i:.2f} "
        f"(headline every-day climatology 6.88: difference {pool_t / pool_i - 6.88:+.2f})")
    say(f"CHECK each winter equal weight: Tehran {ymean_t:.1f}, Istanbul land {ymean_i:.2f}, "
        f"ratio {ymean_t / ymean_i:.2f}")
    say(f"CHECK cells covered by all eight winters {int((cnt == len(WINTERS))[inside].sum())}, by at least one "
        f"{int(cov8[inside].sum())}, inside {int(inside.sum())}")
    k = int(np.argmax(w8))
    say(f"CHECK field max {float(w8.max()):.1f} at lon {float(LO.ravel()[k]):.2f} lat {float(LA.ravel()[k]):.2f}")

    # the per-winter core values against the every-day climatology of clim_v1
    clim = json.loads(CLIM.read_text())["winters"]
    say("CHECK per winter, every-4th-day core here (Tehran / Istanbul land / ratio, days) vs clim_v1 (every day):")
    for y in WINTERS:
        if y not in core:
            say(f"  {y}: no valid day")
            continue
        c_ = core[y]
        cl = clim.get(str(y), {})
        cl_s = (f"clim {cl['tehran']:.1f} / {cl['istanbul']:.2f} / {cl['ratio']:.2f} on {cl['tehran_days']} "
                f"and {cl['istanbul_days']} days") if cl else "clim none"
        say(f"  {y}: {c_['tehran']:.1f} / {c_['istanbul']:.2f} / {c_['tehran'] / c_['istanbul']:.2f} on "
            f"{c_['n_t']} and {c_['n_i']} valid of {c_['n_all']} selected days; {cl_s}")
    say(f"done; seconds {time.time() - t0:.0f}")


def main() -> None:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    GR.mkdir(parents=True, exist_ok=True)
    full = {y: winter_days(y) for y in WINTERS}
    sel = {y: full[y][::STRIDE] for y in WINTERS}
    say(f"winters {WINTERS[0]}-{WINTERS[-1]}: 90 days each, every {STRIDE}th day: {len(sel[WINTERS[0]])} days each")
    if "--search" in sys.argv or not ITEMS.exists():
        rows = []
        for y in WINTERS:
            rows += search_winter(y, full[y], set(sel[y]))
        ITEMS.write_text(json.dumps(rows))
    items = json.loads(ITEMS.read_text())
    rows = ac.select_region(items)
    say(f"granules listed {len(items)}; used {len(rows)} (OFFL {sum(r['mode'] == 'OFFL' for r in rows)}, "
        f"NRTI {sum(r['mode'] == 'NRTI' for r in rows)}); days with a granule "
        f"{len({r['datetime'][:10] for r in rows})} of {sum(len(v) for v in sel.values())} selected")
    say(f"per winter days with a granule: " + ", ".join(
        f"{y}: {len({r['datetime'][:10] for r in rows if r['winter'] == y})}" for y in WINTERS))
    ac.RDIR = GR                                 # air_compare's readers write here (never into region/)
    say(f"linked from the region v1 cache: {link_cached(rows)}")
    ac.fetch_region(rows)
    say(f"reads done; seconds {time.time() - t0:.0f}")
    build(rows, sel, full)
    LOG.write_text("\n".join(LINES) + "\n")
    say(f"runtime seconds {time.time() - t0:.0f}")
    LOG.write_text("\n".join(LINES) + "\n")


if __name__ == "__main__":
    main()
