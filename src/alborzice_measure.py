"""THE WHITE LEFT AT THE END OF SUMMER, MEASURED: one number a year for Damavand and for Alam-Kuh, 1984-2026.

Reads the passes stored by src/get_alborzice.py and writes what the film and its fact check need:

    data/alborzice/series.json                 each measured summer's white (km2), the era medians, the low runs
    data/alborzice/<site>/white/<year>.npz     the white of that summer's pass, pixel by pixel (the pictures)
    data/alborzice/<site>/vet_<site>.jpg       every chosen pass, zoomed, with the footprint drawn (look at it)
    outputs/alborzice_measure_log.txt          (redirect stdout) passes, vetoes, trend tests, the sensor bridge

The rule. Snow, firn and clean ice (NDSI >= 0.40 and nir >= 0.11) above a fixed height (Damavand 4,000 m,
Takht-e Soleyman 3,800 m) in every Landsat pass between 15 August and 30 September; a year's number is the
LOWEST of its clear passes: what is still white when the melt season ends. Debris-covered ice is dark and is not
counted, so this is never a glacier's extent.

Clear means: no missing pixel above the height, and no cloud over the footprint. The footprint is every pixel that
was white in at least 5 % of the provisionally clear late-summer passes of all years, widened by 240 m; cloud is
"bright and not snow" (green reflectance over 0.30 with NDSI under 0.40) inside it, above the site's own clear-sky
level (bright rock and the summit's sulphur are always there). Passes that still failed the eye are in VETO.

The sensor bridge. Until 2011 the passes are Landsat 4, 5 and 7 (TM and ETM+), from 2013 Landsat 8 and 9 (OLI).
Landsat 7 kept flying until 2022 with scan-line gaps; on the pixels both see, its white is compared with Landsat
8's white 8 days before and after. If the old sensor family saw more white than the new one in the same weeks, a
fall from the 1980s to the 2020s would partly be the instruments. The log gives the ratio.

    python -I src/alborzice_measure.py > outputs/alborzice_measure_log.txt
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage, stats

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "alborzice"
WINDOW = ("08-15", "09-30")
SITES = {
    # clear-sky ceiling of "bright and not snow" above the height (first screen), margin over the footprint's own level
    "damavand": dict(zone_m=4000, bright_max=0.035, core_margin=0.03, early=(1984, 1999), late=(2013, 2026)),
    "takht": dict(zone_m=3800, bright_max=0.02, core_margin=0.02, early=(1984, 1999), late=(2013, 2026)),
}
VETO: dict = {            # date of a pass: why the eye rejected it (vet_<site>.jpg, looked at on 13 Nov 2026)
    "damavand": {
        "1994-08-27": "cloud and its shadow on the south-east side of the summit, over the snowfield",
        "2001-09-15": "a cloud over the summit's east side, where the white is",
        "2015-09-22": "fresh snowfall: the whole cone white (18.7 km2, twenty times a usual September)",
        "2020-09-03": "cloud shadow on the north flank and haze over the summit",
    },
    "takht": {
        "1994-09-19": "fresh snowfall: white on the northern ridges where no other year has any (6.2 km2)",
        "2000-09-03": "cloud shadows over the cirques",
        "2022-09-08": "cloud wisps over the cirques",
    },
}
PX = 9e-4                                             # km2 of a 30 m pixel


def day(s: str) -> date:
    y, m, d = (int(x) for x in s.split("-"))
    return date(y, m, d)


def load(name: str) -> tuple:
    d = DATA / name
    rows = list(csv.DictReader(open(d / "scenes.csv")))
    dem = np.load(d / "dem.npy")
    zone = dem >= SITES[name]["zone_m"]
    for r in rows:
        r["year"] = int(r["date"][:4])
        r["md"] = r["date"][5:]
        r["slc"] = r["slc_off"] == "1"
        r["m"] = np.load(d / "masks" / f"{r['key']}.npz")
    return rows, dem, zone


def measure(name: str) -> dict:
    cfg = SITES[name]
    rows, dem, zone = load(name)
    inwin = [r for r in rows if WINDOW[0] <= r["md"] <= WINDOW[1]]
    full = [r for r in inwin if not r["slc"]]
    for r in inwin:
        m = r["m"]
        r["valid"] = float((m["valid"] & zone).sum()) / zone.sum()
        r["bright"] = float((m["bright"] & zone).sum()) / zone.sum()
        r["km2"] = float((m["snow"] & zone).sum()) * PX
        r["loose"] = float((m["loose"] & zone).sum()) * PX
    prov = [r for r in full if r["valid"] >= 0.999 and r["bright"] <= cfg["bright_max"]]
    freq = np.mean([r["m"]["snow"] for r in prov], axis=0)
    foot = ndimage.binary_dilation((freq >= 0.05) & zone, iterations=8) & (dem >= cfg["zone_m"] - 200)
    for r in inwin:
        v = r["m"]["valid"] & foot
        r["core_valid"] = float(v.sum()) / foot.sum()
        r["core_bright"] = float((r["m"]["bright"] & foot).sum()) / max(1, v.sum())
    base = float(np.median([r["core_bright"] for r in prov if float(r["scene_cc"]) < 5.0]))
    ceil = base + cfg["core_margin"]
    for r in inwin:
        r["clear"] = (not r["slc"] and r["valid"] >= 0.999 and r["bright"] <= cfg["bright_max"]
                      and r["core_bright"] <= ceil and r["date"] not in VETO[name])
    print(f"\n===== {name}: zone above {cfg['zone_m']} m = {zone.sum() * PX:.2f} km2; footprint {foot.sum() * PX:.2f} km2; "
          f"{len(inwin)} passes in the window ({len(full)} without scan-line gaps), {len(prov)} provisionally clear, "
          f"{sum(r['clear'] for r in inwin)} clear; footprint's clear-sky bright share {base:.3f}, ceiling {ceil:.3f}")
    for k, why in VETO[name].items():
        print(f"  veto {k}: {why}")
    years = {}
    print("year  passes clear | clear passes: date km2 (loose) sensor")
    for y in range(1984, 2027):
        ys = [r for r in inwin if r["year"] == y and not r["slc"]]
        cs = sorted((r for r in ys if r["clear"]), key=lambda r: r["date"])
        print(f"{y}  {len(ys):3d}   {len(cs):3d}   | "
              + "  ".join(f"{r['md']} {r['km2']:.2f} ({r['loose']:.2f}) {r['platform'][-1]}" for r in cs))
        if cs:
            years[y] = min(cs, key=lambda r: r["km2"])
    ys = np.array(sorted(years))
    v = np.array([years[y]["km2"] for y in ys])
    out = dict(zone_m=cfg["zone_m"], zone_km2=round(float(zone.sum() * PX), 2), n=len(ys),
               years=[dict(year=int(y), py=int(y) - 621, km2=round(float(years[y]["km2"]), 2), date=years[y]["date"],
                           sensor=years[y]["platform"]) for y in ys])
    e0, e1 = cfg["early"]
    l0, l1 = cfg["late"]
    early, late = v[(ys >= e0) & (ys <= e1)], v[(ys >= l0) & (ys <= l1)]
    out.update(median_early=round(float(np.median(early)), 2), median_late=round(float(np.median(late)), 2),
               early=[e0 - 621, e1 - 621], late=[l0 - 621, l1 - 621], n_early=len(early), n_late=len(late))
    tau, p = stats.kendalltau(ys, v)
    mw = stats.mannwhitneyu(early, late).pvalue
    print(f"trend, all {len(ys)} summers: Kendall tau {tau:+.2f}, p {p:.4f}; Theil-Sen "
          f"{stats.theilslopes(v, ys)[0] * 10:+.3f} km2 per decade")
    print(f"medians: {e0}-{e1} {np.median(early):.2f} km2 (n {len(early)}), {l0}-{l1} {np.median(late):.2f} km2 "
          f"(n {len(late)}), ratio {np.median(late) / np.median(early):.2f}, Mann-Whitney p {mw:.4f}")
    for lab, m in (("TM and ETM+ years (to 2011)", ys <= 2011), ("OLI years (from 2013)", ys >= 2013)):
        t, pp = stats.kendalltau(ys[m], v[m])
        print(f"  {lab}: n {m.sum()}, tau {t:+.2f}, p {pp:.4f}, median {np.median(v[m]):.2f}")
    a, b = v[(ys >= 1984) & (ys <= 1996)], v[(ys >= 1997) & (ys <= 2011)]
    print(f"  inside the TM years: 1984-1996 median {np.median(a):.2f} (n {len(a)}), 1997-2011 median "
          f"{np.median(b):.2f} (n {len(b)}), Mann-Whitney p {stats.mannwhitneyu(a, b).pvalue:.4f}")
    order = np.argsort(v)
    print("lowest eight summers: " + ", ".join(f"{ys[i]} {v[i]:.2f}" for i in order[:8]))
    out["rank"] = {int(ys[i]): int(k + 1) for k, i in enumerate(order)}
    out["p_trend"] = round(float(p), 4)
    out["p_medians"] = round(float(mw), 4)

    # the sensor bridge: Landsat 7 (ETM+, scan-line gaps) against Landsat 8 (OLI) 8 days apart, same pixels
    l8 = [r for r in inwin if r["platform"] == "landsat-8" and r["clear"]]
    ratios = []
    print("sensor bridge, Landsat 7 against Landsat 8 on the pixels both see (km2 inside the zone):")
    for r in (x for x in inwin if x["slc"] and x["year"] >= 2013):
        if r["core_bright"] > ceil or r["core_valid"] < 0.5:
            continue
        near = [x for x in l8 if 0 < abs((day(x["date"]) - day(r["date"])).days) <= 8]
        if not near:
            continue
        both = [x for x in near]
        common = r["m"]["valid"] & zone
        a7 = float((r["m"]["snow"] & common).sum()) * PX
        a8 = [float((x["m"]["snow"] & common).sum()) * PX for x in both]
        m8 = float(np.mean(a8))
        if max(a7, m8) < 0.05:
            continue
        ratios.append((a7, m8, len(both)))
        print(f"  L7 {r['date']} {a7:.2f}   L8 " + ", ".join(f"{x['date']} {y:.2f}" for x, y in zip(both, a8)))
    if ratios:
        a7 = np.array([x[0] for x in ratios])
        a8 = np.array([x[1] for x in ratios])
        two = np.array([x[2] == 2 for x in ratios])
        print(f"  {len(ratios)} pairs: sum L7 {a7.sum():.2f}, sum L8 {a8.sum():.2f}, ratio of sums L7/L8 "
              f"{a7.sum() / a8.sum():.2f}; median of the pair ratios {np.median(a7 / np.maximum(a8, 1e-6)):.2f}")
        if two.any():
            print(f"  pairs with a Landsat 8 pass on both sides ({two.sum()}): ratio of sums "
                  f"{a7[two].sum() / a8[two].sum():.2f}")
        out["bridge"] = dict(pairs=len(ratios), ratio=round(float(a7.sum() / a8.sum()), 2))

    # each summer's white for the pictures, and the vetting sheet
    wd = DATA / name / "white"
    wd.mkdir(exist_ok=True)
    floor = dem >= cfg["zone_m"] - 300
    for y in ys:
        np.savez_compressed(wd / f"{y}.npz", white=years[y]["m"]["snow"] & floor)
    (wd / "years.json").write_text(json.dumps([int(y) for y in ys]))
    np.save(DATA / name / "footprint.npy", foot)
    sheet(name, [years[y] for y in ys], foot, zone)
    return out


def sheet(name: str, chosen: list, foot: np.ndarray, zone: np.ndarray) -> None:
    """Every chosen pass in false colour (snow cyan, cloud white), zoomed on the footprint, footprint edge in yellow."""
    rr, cc = np.where(foot)
    r0, r1, c0, c1 = max(0, rr.min() - 20), min(400, rr.max() + 20), max(0, cc.min() - 20), min(400, cc.max() + 20)
    side = max(r1 - r0, c1 - c0)
    r1, c1 = min(400, r0 + side), min(400, c0 + side)
    edge = foot & ~ndimage.binary_erosion(foot)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
    except OSError:
        font = ImageFont.load_default()
    T, cols = 380, 7
    out = Image.new("RGB", (cols * T, ((len(chosen) + cols - 1) // cols) * T), (20, 20, 20))
    d = ImageDraw.Draw(out)
    for i, r in enumerate(chosen):
        im = np.array(Image.open(DATA / name / "quick" / f"{r['key']}.jpg"))
        im[edge] = (255, 230, 0)
        tile = Image.fromarray(im[r0:r1, c0:c1]).resize((T, T), Image.LANCZOS)
        x, y = (i % cols) * T, (i // cols) * T
        out.paste(tile, (x, y))
        d.rectangle((x, y, x + T, y + 28), fill=(0, 0, 0))
        d.text((x + 4, y + 2), f"{r['date']} L{r['platform'][-1]}  {r['km2']:.2f}", fill=(255, 255, 255), font=font)
    out.save(DATA / name / f"vet_{name}.jpg", quality=88)


def main() -> None:
    series = {name: measure(name) for name in SITES}
    # the runs of low summers the film names (Persian years), each checked against the ranks
    for name, (g0, g1), worst in (("damavand", (2022, 2025), 8), ("takht", (2021, 2025), 5)):
        ranks = [series[name]["rank"][str(y) if str(y) in series[name]["rank"] else y] for y in range(g0, g1 + 1)]
        assert max(ranks) <= worst, (name, ranks)
        series[name]["run"] = [g0 - 621, g1 - 621]
        print(f"{name}: the summers {g0}-{g1} rank {ranks} of {series[name]['n']} (1 = least white)")
    t = series["takht"]
    assert t["median_late"] / t["median_early"] <= 0.36 and t["p_medians"] < 0.01 and 0.9 <= t["bridge"]["ratio"] <= 1.1
    series["facts"] = dict(takht_headline="number", fut_low="number")     # "about 70 % less" holds; Rounce Table S5: 71 +- 9 %
    for name in SITES:
        ys = [x["year"] for x in series[name]["years"]]
        print(f"{name}: measured summers {len(ys)}: {ys}")
    (DATA / "series.json").write_text(json.dumps(series, ensure_ascii=False, indent=1))
    print("wrote", DATA / "series.json", file=sys.stderr)


if __name__ == "__main__":
    main()
