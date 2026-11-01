"""THE GORGAN BAY FROM SPACE, 1986-2026: the bay's late-summer water area from Landsat, and the Caspian
Sea's level from altimetry, against 1374 (1995).

Measured data only, from get_gorgan.py (data/gorgan/):
- Bay area, per year: the wet share of the bay's clear pixels times the bay's area (R: JRC water south
  of the barrier's sea-side edge, 53.33-54.10 E, north of 36.78 N; 588.0 km2). Wet = MNDWI > 0 and
  NIR08 < 0.10 in at least half of the year's clear passes. 1995 is the single pass of 8 September 1995
  (see get_gorgan.py); the four-pass composite of 1995 is not used.
- Uncertain on screen: a year whose area depends on the wet rule by more than 5 % (wet in at least half
  of the passes against more than half: 1992 and 1997 here), and a year with more than a tenth of the bay
  never seen clear (1993, 2002, 2005). Their pictures are shown; their areas are not.
- Caspian Sea: NASA's GWM lake 270 (EGM2008 mean sea level, 10-day records). The Aug-Sep mean of each year
  (the Persian Mordad and Shahrivar of year Y - 621); 1371 has no such mean (the series starts in October
  1992), so the first reading is 1372. The change is measured against 1995 (1374), like for like: the
  same calendar month of 2025 and of 1995 for all twelve months, and the Aug-Sep means of the two years.

Checks (EXPECT) raise an error when a published number moves: the 1995 and 2025 areas (555 and 286 km2,
+-5), the ratios 2025/1995 and 2026/1995 in 0.45-0.58, the Caspian fall since 1995 in 2.5-3.0 m on the
Aug-Sep means, and 2026 not lower than 2025 in area and in level.

    python -I src/gorgan.py > outputs/gorgan_log.txt
"""

from __future__ import annotations

import functools
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import get_gorgan as gg  # noqa: E402  (the frames' grid and the data folder)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "gorgan"
YEARS = (1986, 2026)
NO_PICTURE = {2007: "no pass with half the bay clear (the one pass of 17 Sep 2007 is striped Landsat 7 with 69 % "
                    "cloud and none of the bay clear)"}
BASE, LOW, NOW = 1995, 2025, 2026              # Gregorian years: Persian 1374, 1404, 1405
RULE_GAP, UNSEEN = 5.0, 10.0                   # per cent: wet-rule gap, and share of the bay never seen clear
EXPECT = dict(area={1995: 555.0, 2025: 286.0}, tol=5.0,        # km2, the published values (+-5)
              ratio=(0.45, 0.58),                              # 2025/1995 and 2026/1995: about half
              fall=(2.5, 3.0))                                 # m: the Caspian, Aug-Sep 1995 to 2025


def persian(year: int) -> int:
    return year - 621                          # 1 Aug-30 Sep of year Y lies in Persian year Y - 621


@functools.cache
def geometry() -> dict:
    """The bay (R) and the sea (SEA) on the 30-m grid; RA = the bay's area per pixel (km2)."""
    z = np.load(DATA / "geometry.npz")
    RA = z["R"] * gg.ROW_KM2[:, None]
    return dict(R=z["R"], RA=RA, R_area=float(RA.sum()), lat=z["lat"], lon=z["lon"], edge=z["edge"],
                lake=z["lake"])


@functools.lru_cache(maxsize=6)
def masks(year: int) -> tuple:
    """The year's wet mask, seen mask and wet frequency (at most six years in memory)."""
    z = np.load(DATA / f"{year}.npz")
    return z["wet"], z["seen"], z["wetfreq"].astype(np.float32)


def years() -> list:
    """The years with a picture: every year of the frames but NO_PICTURE."""
    return [y for y in range(YEARS[0], YEARS[1] + 1) if y not in NO_PICTURE and (DATA / f"{y}.npz").exists()]


def area_with(year: int, R: np.ndarray | None = None, strict: bool = False) -> float:
    """The wet area (km2) of a year over region R (default: the bay). Wet: wet frequency at least 0.5 (the
    fact check's rule); strict: more than 0.5."""
    g = geometry()
    RA = g["RA"] if R is None else R * gg.ROW_KM2[:, None]
    _, seen, wf = masks(year)
    seen_area = float(np.sum(RA * seen))
    wet = (wf > 0.5) if strict else (wf >= 0.5)
    return float(np.sum(RA * wet)) / seen_area * float(RA.sum())


@functools.cache
def stats(year: int) -> dict:
    """The year's numbers: area (base rule), the strict rule's area, the share of the bay never seen clear."""
    g = geometry()
    wet, seen, _ = masks(year)
    base, strict = area_with(year), area_with(year, strict=True)
    return dict(area=base, strict=strict,
                unseen=100 * (1 - float(np.sum(g["RA"] * seen)) / g["R_area"]),
                gap=100 * abs(strict - base) / base)


def bay_km2(year: int) -> float:
    return stats(year)["area"]


def uncertain(year: int) -> bool:
    s = stats(year)
    return s["gap"] > RULE_GAP or s["unseen"] > UNSEEN


def on_screen(year: int) -> str:
    """The area as shown: to the nearest 10 km2 (half up; partly cloudy passes read up to a third high, a
    composite a few per cent low), or 'uncertain' for the years above. The checks use the raw values."""
    return "uncertain" if uncertain(year) else str(int(np.floor(bay_km2(year) / 10 + 0.5)) * 10)


@functools.cache
def records() -> pd.DataFrame:
    """NASA GWM lake 270, one row per 10-day record: year, month, height (m, EGM2008)."""
    rows = []
    for line in open(DATA / "caspian_nasa270.txt", encoding="utf-8", errors="replace"):
        if not line or line[0] in "cC" or ":" in line:
            continue
        p = line.split()
        if len(p) < 16 or not re.fullmatch(r"\d{8}", p[2]) or p[2].startswith("9999"):
            continue
        try:
            h = float(p[14])
        except ValueError:
            continue
        if h > 9000:
            continue
        rows.append((int(p[2][:4]), int(p[2][4:6]), h))
    return pd.DataFrame(rows, columns=["year", "month", "h"])


@functools.cache
def level() -> pd.DataFrame:
    """Per Gregorian year: the annual mean, the Aug-Sep mean (NaN where none) and the records (m)."""
    df = records()
    return pd.DataFrame({"annual": df.groupby("year")["h"].mean(),
                         "augsep": df[df["month"].isin([8, 9])].groupby("year")["h"].mean(),
                         "records": df.groupby("year").size()})


def caspian_change(year: int) -> float:
    """The Aug-Sep mean of a year minus 1995's (m; negative: lower); NaN where the series has no reading."""
    lv = level()
    if year not in lv.index or np.isnan(lv.loc[year, "augsep"]):
        return float("nan")
    return float(lv.loc[year, "augsep"] - lv.loc[BASE, "augsep"])


def same_month_changes(a: int = BASE, b: int = LOW) -> dict:
    """Month by month: the mean of calendar month m in year b minus the same month in year a (m)."""
    df = records()
    mm = df.groupby(["year", "month"])["h"].mean()
    rows = [(m, float(mm.loc[(a, m)]), float(mm.loc[(b, m)]), float(mm.loc[(b, m)] - mm.loc[(a, m)]))
            for m in range(1, 13) if (a, m) in mm.index and (b, m) in mm.index]
    return dict(rows=rows, lo=min(r[3] for r in rows), hi=max(r[3] for r in rows))


def fall_range(a: int = BASE, b: int = NOW) -> tuple:
    """The smallest and largest fall (m) of the Caspian between the same calendar months of years a and b."""
    sm = same_month_changes(a, b)
    return -sm["hi"], -sm["lo"]


def regress(years_: list, idx: str) -> dict:
    lv = level()
    x = np.array([lv.loc[y, idx] for y in years_], float)
    yv = np.array([bay_km2(y) for y in years_], float)
    b, a0 = np.polyfit(x, yv, 1)
    r2 = 1 - np.sum((yv - (a0 + b * x)) ** 2) / np.sum((yv - yv.mean()) ** 2)
    return dict(n=len(years_), slope=float(b), intercept=float(a0), r2=float(r2))


def region(shift: float = 0.0, cut: float = 36.78, lon_min: float = 53.33, lon_max: float = 54.10) -> np.ndarray:
    """The bay's region: the barrier edge moved by shift (deg north), a south cut, and the longitude limits."""
    g = geometry()
    lat, lon, ed = g["lat"][:, None], g["lon"][None, :], g["edge"][None, :]
    return g["lake"] & np.isfinite(ed) & (lon >= lon_min) & (lon <= lon_max) & (lat < ed + shift) & (lat > cut)


def checks() -> list:
    """The EXPECT checks as (name, value, passed); an AssertionError when one fails."""
    a95, a25, a26 = bay_km2(BASE), bay_km2(LOW), bay_km2(NOW)
    lv = level()
    fall = -caspian_change(LOW)
    out = [
        (f"area {BASE} within 5 of 555 km2", round(a95, 1), abs(a95 - EXPECT["area"][BASE]) <= EXPECT["tol"]),
        (f"area {LOW} within 5 of 286 km2", round(a25, 1), abs(a25 - EXPECT["area"][LOW]) <= EXPECT["tol"]),
        (f"ratio {LOW}/{BASE} in 0.45-0.58", round(a25 / a95, 3), EXPECT["ratio"][0] <= a25 / a95 <= EXPECT["ratio"][1]),
        (f"ratio {NOW}/{BASE} in 0.45-0.58", round(a26 / a95, 3), EXPECT["ratio"][0] <= a26 / a95 <= EXPECT["ratio"][1]),
        (f"Caspian fall {BASE} to {LOW}, Aug-Sep, in 2.5-3.0 m", round(fall, 3),
         EXPECT["fall"][0] <= fall <= EXPECT["fall"][1]),
        (f"area {NOW} not lower than {LOW}", (round(a26, 1), round(a25, 1)), a26 >= a25),
        (f"level {NOW} not lower than {LOW} (Aug-Sep)", (round(float(lv.loc[NOW, "augsep"]), 3),
                                                       round(float(lv.loc[LOW, "augsep"]), 3)),
         float(lv.loc[NOW, "augsep"]) >= float(lv.loc[LOW, "augsep"])),
        ("2007 has no picture", 2007 not in years(), 2007 not in years()),
        (f"fall {NOW} against {BASE}, same calendar month: 2.5 to 2.7 m", tuple(round(v, 3) for v in fall_range()),
         round(fall_range()[0], 1) == 2.5 and round(fall_range()[1], 1) == 2.7),
    ]
    for name, val, ok in out:
        assert ok, f"EXPECT failed: {name}: {val}"
    return out


def main() -> None:
    g = geometry()
    base = region()
    print(f"grid {gg.NX} x {gg.NY} px of about 30 m; the bay R {g['R_area']:.1f} km2 ({int(g['R'].sum())} px); "
          f"region function reproduces R: {bool(np.array_equal(base, g['R']))}")
    fr = pd.read_csv(DATA / "frames.csv") if (DATA / "frames.csv").exists() else None
    print(f"pictures: {len(years())} years ({years()[0]}-{years()[-1]}); none for {sorted(NO_PICTURE)}")
    print("\nBAY AREA, 1 Aug-30 Sep, km2 (wet in at least half the passes, of the bay seen clear):")
    print(f"  {'year':>4} {'Persian':>7} {'passes':>6} {'area':>8} {'unseen%':>7} {'rule gap%':>9} {'on screen':>10}  status")
    for y in years():
        st, n = "-", "-"
        if fr is not None and y in set(fr["year"]):
            row = fr[fr["year"] == y].iloc[0]
            st, n = str(row["status"]), str(int(row["n_accepted"]))
            assert abs(float(row["bay_wet_km2"]) - bay_km2(y)) < 0.05, \
                f"{y}: frames.csv {row['bay_wet_km2']} vs {bay_km2(y):.2f}"
        s = stats(y)
        print(f"  {y:>4} {persian(y):>7} {n:>6} {s['area']:8.1f} {s['unseen']:7.2f} {s['gap']:9.2f} "
              f"{on_screen(y):>10}  {st}")
    a95, a25, a26, a86 = bay_km2(BASE), bay_km2(LOW), bay_km2(NOW), bay_km2(1986)
    print("\nKEY NUMBERS:")
    print(f"  1986 ({persian(1986)}): {a86:.1f} km2;  1995 ({persian(BASE)}): {a95:.1f} km2 (single pass, 8 Sep);  "
          f"2025 ({persian(LOW)}): {a25:.1f} km2;  2026 ({persian(NOW)}): {a26:.1f} km2")
    print(f"  ratio 2025/1995 = {a25 / a95:.3f};  2026/1995 = {a26 / a95:.3f};  2026/2025 = {a26 / a25:.3f}")
    print(f"  uncertain on screen: {[y for y in years() if uncertain(y)]}")
    passes = pd.read_csv(DATA / "scenes.csv")
    for y in (BASE, LOW, NOW):
        rows = passes[(passes["year"] == y) & passes["scene_bay_km2"].notna()]
        print(f"  passes of {y}: " + "; ".join(
            f"{r.date} {100 * r.bay_clear_share:.0f} % clear -> {r.scene_bay_km2:.1f} km2"
            + (" (Tier 2)" if "_T2" in r.item else "") + ("" if r.accepted else " (not used)")
            for r in rows.itertuples()))
    print(f"  wet-rule gap above 5 %: {[y for y in years() if stats(y)['gap'] > RULE_GAP]}; "
          f"never-seen share above 10 %: {[y for y in years() if stats(y)['unseen'] > UNSEEN]}")

    lv = level()
    first = int(lv["augsep"].dropna().index.min())
    print("\nCASPIAN SEA, NASA GWM lake 270 (EGM2008 mean sea level, m):")
    print(f"  records {int(lv['records'].sum())}, years {int(lv.index.min())}-{int(lv.index.max())} "
          f"(first record {records()['year'].min()}-{int(records().loc[records()['year'].idxmin(), 'month']):02d}); "
          f"first Aug-Sep mean {first} (Persian {persian(first)})")
    print(f"  {'year':>4} {'Persian':>7} {'Aug-Sep':>9} {'vs 1995':>9} {'annual':>9} {'records':>8}")
    for y in lv.index:
        if y < first:
            continue
        print(f"  {y:>4} {persian(int(y)):>7} {lv.loc[y, 'augsep']:9.3f} {caspian_change(int(y)):+9.3f} "
              f"{lv.loc[y, 'annual']:9.3f} {int(lv.loc[y, 'records']):8d}")
    sm = same_month_changes()
    print(f"\n  same calendar month, {LOW} minus {BASE}: " + "  ".join(f"{m}:{d:+.3f}" for m, _, _, d in sm["rows"]))
    print(f"  over the twelve months: {sm['lo']:+.3f} to {sm['hi']:+.3f} m (like for like)")
    print(f"  Aug-Sep means: {LOW} minus {BASE} {caspian_change(LOW):+.3f} m; {NOW} minus {BASE} {caspian_change(NOW):+.3f} m")
    print("  not like for like (not used on screen): the June 1995 peak of the monthly means against the November "
          "2025 low: 3.03 m (different months)")

    print("\nREGRESSION of the bay area on the Aug-Sep Caspian level, 1993-2026:")
    reg = [y for y in years() if y >= 1993 and not np.isnan(lv.loc[y, "augsep"])]
    r = regress(reg, "augsep")
    print(f"  all pictures (flagged included): n {r['n']}, slope {r['slope']:.1f} km2 per m, "
          f"intercept {r['intercept']:.1f}, r2 {r['r2']:.3f}")
    print("  an association between two series that both fall, not a cause")

    print("\nSENSITIVITY of the 1995, 2025 and 2026 areas and of the ratios (km2):")
    variants = [("base: the bay as built", base),
                ("no south cut (lat > 36.60)", region(cut=36.60)),
                ("barrier edge 150 m further north", region(shift=+0.00135)),
                ("barrier edge 150 m further south", region(shift=-0.00135)),
                ("east cut at 53.95 E", region(lon_max=53.95)),
                ("west cut at 53.50 E", region(lon_min=53.50))]
    for name, R in variants:
        a, b, c = (area_with(y, R) for y in (BASE, LOW, NOW))
        print(f"  {name:34s} R {float((R * gg.ROW_KM2[:, None]).sum()):6.1f}  1995 {a:6.1f}  2025 {b:6.1f}  "
              f"2026 {c:6.1f}  ratio {b / a:.3f} / {c / a:.3f}")
    for y in (BASE, LOW, NOW):
        print(f"  strict wet rule (more than half), {y}: {stats(y)['strict']:.1f} km2 (base {stats(y)['area']:.1f})")

    print("\nEXPECT checks:")
    for name, val, _ in checks():
        print(f"  PASS  {name}: {val}")


if __name__ == "__main__":
    main()
