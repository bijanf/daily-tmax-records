"""THE LAR RESERVOIR, AUTUMN 1987-2026: the open water in one autumn Landsat pass a year, its statistics,
and the storage figures that were officially reported (outputs/lar_log.txt).

Measured data only, from get_lar.py (data/lar): per year the chosen pass and its area of open water in
km2 on the pass's own grid (frames.csv). 2003 and 2011 have no frame (GAPS); they are skipped, never filled.
A Persian year P is the autumn of Gregorian year P + 621 (1366 = 1987, 1405 = 2026).

- Decades (single passes, the film's numbers): the 1370s (autumn 1991-2000) and the last ten autumns
  (1396-1405, 2017-2026): the median of their passes, and the ratio of the two.
- Ranks: on the single passes, and on the drawdown-adjusted index: every pass moved to 1 October with the
  within-season drawdown k (fixed effects over the accepted passes within 25 days of 1 October, 1995-09-15
  left out), and the median of the adjusted passes of each year. The adjusted index is the basis of the
  1405 rank and of the +61 % figure; the single passes give +76 %.
- Pictures (picture): the pass in true colour, with land gaps taken from the nearest year with a view, as
  the Urmia and Zayandeh pictures are. Display only; the reservoir is never filled, no area uses them.
- OFFICIAL: the storage figures reported in the Persian press, with their dates and sources. They are not
  an area and no volume is derived from one.

    python -I src/lar.py > outputs/lar_log.txt
"""

from __future__ import annotations

import functools
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import get_lar  # noqa: E402
from wateryear import farvardin1  # noqa: E402

DATA = get_lar.DATA
NO_PASS = {2003: "no scene of the dam between 1 September and 15 November",
           2011: "its only clear pass (3 September) is 28 days before 1 October"}
# Measured (their areas count in the medians and ranks) but not shown: the picture has holes on the lake.
NOT_SHOWN = {2005: "its only clean-enough pass (Landsat 7, 18 September) has scan gaps over 1 % of the reservoir",
             2012: "its only pass (Landsat 7, 21 September) has scan gaps over 2.7 % of the reservoir",
             2015: "its best pass (22 September) has cloud over 7.9 % of the reservoir"}
GAPS = {**NO_PASS, **NOT_SHOWN}                           # the years the film skips
# Storage as reported (dated; the article's date and the date of its data), the newest first. The five
# dams: Amir Kabir, Latyan, Taleghan, Mamloo and Lar. Re-read the press on the posting day.
OFFICIAL = {
    "five_dams": dict(date=date(2026, 10, 23), value=359, last_year=217, long_term=548, unit="million m3",
                      label="five Tehran dams, storage",
                      source="Mehr News 6989418, 4 Aban 1405 (26 Oct 2026), data of the Tehran Regional Water "
                             "Company for 1 Aban 1405 (23 Oct 2026); the same date last year 217, the long-term "
                             "average 548"),
    "lar": dict(date=date(2026, 10, 23), value=29, last_year=16, long_term=79, unit="million m3",
                label="Lar dam, storage",
                source="the same article; nominal capacity 920 million m3 (the company's deputy, same article) "
                       "or about 960 (Mehr News 6981337)"),
}
EARLIER = ("Mehr News 6981337, 26 Mehr 1405 (18 Oct 2026), citing the national water statistics: 383 million m3 "
           "for the five dams and 35 for Lar on 19 Mehr 1405 (11 Oct 2026)")
# Figures seen in the Persian press but not used on screen: a different date and total, to be settled.
NOT_USED = ("Tehran water and wastewater spokesman, 17 Mehr 1405 (9 Oct 2026): 391 million m3 'at the start of "
            "Mehr' for the five dams (Mehr News: 383 on 19 Mehr)")
MONTHS = ("Farvardin", "Ordibehesht", "Khordad", "Tir", "Mordad", "Shahrivar", "Mehr", "Aban", "Azar", "Dey",
          "Bahman", "Esfand")


def persian(year: int) -> int:
    return year - 621                                     # the autumn of Y lies in Persian year Y - 621


def jalali(d: date) -> str:
    """A date of 1405 as the Persian press writes it: 1 Aban 1405 = 23 October 2026."""
    n = (d - farvardin1(1405)).days                       # days since 1 Farvardin 1405
    assert 0 <= n < 365, d
    jm, day = (n // 31, n % 31 + 1) if n < 186 else (6 + (n - 186) // 30, (n - 186) % 30 + 1)
    return f"{day} {MONTHS[jm]} 1405"


@functools.cache
def frames() -> pd.DataFrame:
    return pd.read_csv(DATA / "frames.csv", parse_dates=["date"]).set_index("year")


def years() -> list:
    """The years with a clean frame, in order (GAPS are left out and listed, never filled)."""
    return sorted(int(y) for y in frames().index if int(y) not in GAPS)


def area(year: int) -> float:
    """The year's open water (km2) in its one pass."""
    return float(frames().loc[year, "area_km2"])


@functools.cache
def colour(year: int) -> np.ndarray:
    """The year's pass in true colour: red, green and blue reflectance on the fixed grid, NaN where not clear."""
    return np.load(DATA / f"{year}.npz")["rgb"].astype(np.float32)


@functools.cache
def water(year: int) -> np.ndarray:
    """The year's pass: 1 water, 0 land and 255 not clear, inside the reservoir (255 outside it)."""
    return np.load(DATA / f"{year}.npz")["water"]


SPECK = 60                                                 # px: a gap this small takes the same pass's nearest pixel


@functools.cache
def picture(year: int) -> np.ndarray:
    """The year's picture (display only: the areas come from the pass alone). Gaps of a few pixels
    (cloud-mask specks, the shore's flagged pixels, inside the reservoir too) take the same pass's nearest
    clear pixel. Larger gaps on land take the nearest year with a clear view, its tones matched band by
    band to this pass over the land both saw clearly (as the Urmia and Zayandeh pictures fill land); the
    reservoir never takes another year's data."""
    from scipy import ndimage
    rgb = colour(year).copy()
    roi = np.load(DATA / f"{year}.npz")["roi"]
    gap = np.isnan(rgb).any(axis=0)
    lab, n = ndimage.label(gap)
    if n:
        sizes = ndimage.sum(gap, lab, range(1, n + 1))
        speck = np.isin(lab, 1 + np.flatnonzero(sizes <= SPECK))
        if speck.any():
            _, (iy, ix) = ndimage.distance_transform_edt(gap, return_indices=True)
            rgb[:, speck] = rgb[:, iy[speck], ix[speck]]
    hole = np.isnan(rgb).any(axis=0) & ~roi
    seen = ~np.isnan(rgb).any(axis=0) & ~roi
    for d in (1, -1, 2, -2, 3, -3, 4, -4):
        other = year + d
        if not hole.any():
            break
        if not (DATA / f"{other}.npz").exists():
            continue
        src = colour(other)
        valid = ~np.isnan(src).any(axis=0)
        both = seen & valid
        ok = hole & valid
        if both.sum() > 1000:                             # match the tones over the land both passes saw
            gain = np.nanmedian(rgb[:, both], axis=1) / np.maximum(np.nanmedian(src[:, both], axis=1), 1e-4)
            rgb[:, ok] = src[:, ok] * gain[:, None]
        else:
            rgb[:, ok] = src[:, ok]
        hole &= ~ok
    return rgb


def decade(a: int, b: int) -> float:
    """The median of the single passes' areas, Gregorian years a to b."""
    vals = [area(y) for y in years() if a <= y <= b]
    assert len(vals) == b - a + 1, (a, b, len(vals))
    return float(np.median(vals))


@functools.cache
def passes() -> pd.DataFrame:
    """The accepted passes within 25 days of 1 October, without the excluded one, with positive area."""
    df = get_lar.table()
    keep = df["accepted"] & (df["dt"].abs() <= get_lar.WINDOW) & ~df["item"].isin(get_lar.EXCLUDE)
    return df[keep & (df["area_km2"] > 0)].copy()


def drawdown(c: pd.DataFrame) -> tuple:
    """k per day (positive = shrinking): the fixed-effects slope of log area on the day from 1 October,
    within each year with two passes or more; and the number of such years."""
    num = den = 0.0
    n = 0
    for _, g in c.groupby("year"):
        if len(g) < 2 or g["dt"].nunique() < 2:
            continue
        n += 1
        x = g["dt"] - g["dt"].mean()
        y = np.log(g["area_km2"]) - np.log(g["area_km2"]).mean()
        num += float((x * y).sum())
        den += float((x * x).sum())
    return -num / den, n


@functools.cache
def adjusted() -> tuple:
    """(median adjusted area per year, k, years used, passes used): each pass moved to 1 October."""
    c = passes()
    k, n = drawdown(c)
    c = c.assign(adj=c["area_km2"] * np.exp(k * c["dt"]))
    med = c.groupby("year")["adj"].median()
    return med, k, n, len(c)


def ranks(series: pd.Series, y: int) -> tuple:
    """(rank from the lowest, of how many, the value) of year y."""
    r = series.rank(method="min")
    return int(r.loc[y]), len(series), float(series.loc[y])


def lowest_since(series: pd.Series, y: int) -> int:
    """The last year before y with a lower value (the year y is the lowest since then)."""
    below = [z for z in series.index if z < y and series.loc[z] < series.loc[y]]
    return max(below)


def checks() -> None:
    """The numbers the film states, as asserts."""
    assert jalali(OFFICIAL["five_dams"]["date"]) == "1 Aban 1405", "1 Aban 1405 = 23 Oct 2026"
    assert jalali(OFFICIAL["lar"]["date"]) == "1 Aban 1405" and jalali(date(2026, 10, 11)) == "19 Mehr 1405"
    assert sorted(set(range(1987, 2027)) - set(years())) == sorted(GAPS), "the years left out are GAPS"


def main() -> None:
    checks()
    fr = frames()
    print("LAR RESERVOIR, one autumn Landsat pass a year (lar.py; data/lar, get_lar.py)")
    print(f"measured: {len(fr)} years {fr.index.min()}-{fr.index.max()} (medians and ranks); shown in the film: "
          f"{len(years())}")
    for y, why in sorted(GAPS.items()):
        print(f"  {y} ({persian(y)}): {'no frame' if y in NO_PASS else 'measured, not shown'}: {why}")
    print("  passes left out of every count: " + "; ".join(f"{k}: {v}" for k, v in get_lar.EXCLUDE.items()))
    med, k, n_years, n_passes = adjusted()
    print(f"drawdown k = {k:.5f} per day ({100 * (np.exp(k) - 1):.2f} % per day) from {n_years} years, "
          f"{n_passes} accepted passes within 25 days (the excluded passes left out)")
    print("\nyear  persian  date        platform    clear  area km2  grid km2  days  adjusted km2  passes")
    for y in years():
        r = fr.loc[y]
        print(f"{y}  {persian(y)}    {r['date'].date()}  {r['platform']:11s} {r['clear_share']:.4f}  "
              f"{r['area_km2']:8.3f}  {r['area_km2_grid']:8.3f}  {int(r['days_from_1Oct']):+4d}  "
              f"{med.loc[y]:12.3f}  {int(passes().query('year == @y').shape[0])}")
    single = fr["area_km2"]
    print("\nDECADES (median of the single passes, km2)")
    t70, recent = decade(1991, 2000), decade(2017, 2026)
    print(f"  1370s, autumn 1991-2000 (Persian 1370-1379): {t70:.3f}")
    print(f"  1396-1405, autumn 2017-2026: {recent:.3f}")
    print(f"  ratio recent / 1370s: {recent / t70:.3f}")
    print("\nRANKS (1 = lowest)")
    r25, n, v25 = ranks(single, 2025)
    r26, _, v26 = ranks(single, 2026)
    print(f"  single passes: 2025 (1404) {v25:.3f} km2, rank {r25} of {n}; lowest since {lowest_since(single, 2025)}; "
          f"2026 (1405) {v26:.3f} km2, rank {r26} of {n}")
    a25, na, av25 = ranks(med, 2025)
    a26, _, av26 = ranks(med, 2026)
    print(f"  adjusted index: 2025 (1404) {av25:.3f} km2, rank {a25} of {na}; lowest since "
          f"{lowest_since(med, 2025)}; 2026 (1405) {av26:.3f} km2, rank {a26} of {na}")
    print(f"  lowest single pass: {int(single.idxmin())} at {single.min():.3f} km2; "
          f"lowest adjusted: {int(med.idxmin())} at {med.min():.3f} km2")
    print("\n1405 AGAINST 1404")
    p25 = frames().loc[2025, "date"].date()
    p26 = frames().loc[2026, "date"].date()
    print(f"  single passes: {v26:.3f} km2 ({p26}) against {v25:.3f} km2 ({p25}): "
          f"{100 * (v26 / v25 - 1):+.1f} %")
    print(f"  adjusted index: {av26:.3f} against {av25:.3f}: {100 * (av26 / av25 - 1):+.1f} %")
    print("\nOFFICIAL (storage as reported; not an area)")
    for o in OFFICIAL.values():
        print(f"  {o['label']}: {o['value']} {o['unit']} on {o['date']:%d %b %Y} ({jalali(o['date'])}); "
              f"source: {o['source']}")
    print(f"  earlier: {EARLIER}")
    print(f"  not used: {NOT_USED}")


if __name__ == "__main__":
    main()
