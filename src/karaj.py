"""KARAJ DAM, 40 AUTUMNS FROM SPACE: the open water of the Amir Kabir (Karaj) reservoir, one of the five
dams that supply Tehran, in one autumn Landsat pass a year, 1987-2026, and the storage figures that were
officially reported (outputs/karaj_log.txt).

Measured data only, from get_karaj.py (data/karaj): per year the chosen pass and its area of open water in
km2 on the pass's own grid (frames.csv). Every year 1987-2026 has a frame. Six of them are measured but not
shown (NOT_SHOWN): their only usable passes are striped Landsat 7 scenes, with 26-37 % of the reservoir without
data, so the picture would have holes; their areas count in every statistic, as the Lar film's did.
A Persian year P is the autumn of Gregorian year P + 621 (1366 = 1987, 1404 = 2025, 1405 = 2026).

- The usual autumn area: the median of the 40 single passes (km2), the dashed mark on the gauge.
- 1404 (2025) against that median, and how many autumns lie within 10 % of it.
- Pictures (picture): the pass in true colour, with land gaps taken from the nearest year with a view, as
  the Lar and Urmia pictures are. Display only; the reservoir is never filled, no area uses them.
- OFFICIAL: the storage figures reported in the Persian press, with their dates and sources. They are not an
  area and no volume is derived from one.

    python -I src/karaj.py > outputs/karaj_log.txt
"""

from __future__ import annotations

import functools
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import get_karaj  # noqa: E402
from wateryear import farvardin1  # noqa: E402

DATA = get_karaj.DATA
NO_PASS: dict = {}                                        # no year lacks a frame: every autumn has a pass
SHARE_LIMIT = 0.99                                        # a shown picture has at least this share of the reservoir with data
# Measured (their areas count in the median and the counts) but not shown: a striped Landsat 7 scene.
NOT_SHOWN = {2003: "its only pass (Landsat 7, 6 October 2003, scan-line gaps)",
             2004: "its only passes (Landsat 7, September and October 2004, scan-line gaps)",
             2005: "its only passes (Landsat 7, September and October 2005, scan-line gaps)",
             2007: "its only passes (Landsat 7, September 2007, scan-line gaps)",
             2011: "its only passes (Landsat 7, September 2011, scan-line gaps)",
             2012: "its only passes (Landsat 7, September 2012, scan-line gaps)"}
GAPS = {**NO_PASS, **NOT_SHOWN}                           # the years the film skips
# Storage as reported (dated; the article's date and the date of its data), the newest first. Mehr News 6989418
# of 4 Aban 1405 (26 Oct 2026) quotes the Tehran Regional Water Company for 1 Aban 1405 (23 Oct 2026).
OFFICIAL = {
    "amir_kabir": dict(date=date(2026, 10, 23), value=123, last_year=17, long_term=103, unit="million m3",
                       label="Amir Kabir (Karaj) dam, storage",
                       source="Mehr News 6989418, 4 Aban 1405 (26 Oct 2026), the Tehran Regional Water Company's data "
                              "for 1 Aban 1405 (23 Oct 2026): 123 million m3, 17 on the same date last year, a long-term "
                              "average of 103; the only one of Tehran's five dams above its long-term average"),
    "five_dams": dict(date=date(2026, 10, 23), value=359, last_year=217, long_term=548, unit="million m3",
                      label="five Tehran dams, storage",
                      source="the same article: Amir Kabir, Latyan, Lar, Taleghan and Mamloo, 359 million m3 "
                             "(217 last year, long-term average 548)"),
}
CAPACITY_NOTE = ("nominal capacity of the Amir Kabir reservoir: not stated in the article; not used on screen "
                 "unless a second source is cited")
MONTHS = ("Farvardin", "Ordibehesht", "Khordad", "Tir", "Mordad", "Shahrivar", "Mehr", "Aban", "Azar", "Dey",
          "Bahman", "Esfand")
NEAR = 0.10                                               # an autumn is 'about the usual' within this share of the median


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
    """The years whose picture is shown, in order (GAPS are left out and listed, never filled)."""
    return sorted(int(y) for y in frames().index if int(y) not in GAPS)


def all_years() -> list:
    return sorted(int(y) for y in frames().index)


def area(year: int) -> float:
    """The year's open water (km2) in its one pass."""
    return float(frames().loc[year, "area_km2"])


def valid(year: int) -> float:
    """The share of the reservoir with data in the year's pass."""
    return float(frames().loc[year, "valid_share"]) if "valid_share" in frames().columns else float("nan")


def median() -> float:
    """The usual autumn area: the median of the 40 single passes (km2)."""
    return float(np.median([area(y) for y in all_years()]))


def near_median(tol: float = NEAR) -> list:
    """The years whose pass lies within tol of the median (either side)."""
    m = median()
    return [y for y in all_years() if abs(area(y) / m - 1) <= tol]


def lowest_since(y: int) -> int:
    """The last year before y with a lower area (y is the lowest since then)."""
    below = [z for z in all_years() if z < y and area(z) < area(y)]
    return max(below)


@functools.cache
def colour(year: int) -> np.ndarray:
    """The year's pass in true colour: red, green and blue reflectance on the fixed grid, NaN where not clear."""
    return np.load(DATA / f"{year}.npz")["rgb"].astype(np.float32)


@functools.cache
def water(year: int) -> np.ndarray:
    """The year's pass: 1 water, 0 land and 255 not clear, inside the reservoir (255 outside it)."""
    return np.load(DATA / f"{year}.npz")["water"]


SPECK = 60                                                # px: a gap this small takes the same pass's nearest pixel
SPIKE = 0.10                                              # reflectance: a lone pixel this far off its neighbours


def spikes(rgb: np.ndarray) -> np.ndarray:
    """Lone coloured dots: pixels SPIKE or more off the median of their eight neighbours in some band, whose
    own bands spread by SPIKE or more and by three times the neighbours' spread (impulse noise in one band of
    the older passes, e.g. a red dot on the lake in 1987). Grey rock, roofs and the dam's concrete are not
    coloured enough to count; 13 pixels in 40 years do (1987, 1995, 2004)."""
    import warnings
    pad = np.pad(rgb, ((0, 0), (1, 1), (1, 1)), mode="edge")
    h, w = rgb.shape[1:]
    ring = np.stack([pad[:, 1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
                     for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN neighbourhoods (outside the pass)
        med = np.nanmedian(ring, axis=0)
        off = np.nanmax(np.abs(rgb - med), axis=0)
        spread = np.nanmax(rgb, axis=0) - np.nanmin(rgb, axis=0)
        around = np.nanmax(med, axis=0) - np.nanmin(med, axis=0)
    return (off >= SPIKE) & (spread >= SPIKE) & (spread >= 3 * np.maximum(around, 0.02))


@functools.cache
def picture(year: int) -> np.ndarray:
    """The year's picture (display only: the areas come from the pass alone). Gaps of a few pixels
    (cloud-mask specks, the shore's flagged pixels, lone coloured dots (spikes), inside the reservoir too)
    take the same pass's nearest clear pixel. Larger gaps on land take the nearest year with a clear view, its tones matched band by
    band to this pass over the land both saw clearly; the reservoir never takes another year's data."""
    from scipy import ndimage
    rgb = colour(year).copy()
    rgb[:, spikes(rgb)] = np.nan
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
        ok_src = ~np.isnan(src).any(axis=0)
        both = seen & ok_src
        ok = hole & ok_src
        if both.sum() > 1000:                             # match the tones over the land both passes saw
            gain = np.nanmedian(rgb[:, both], axis=1) / np.maximum(np.nanmedian(src[:, both], axis=1), 1e-4)
            rgb[:, ok] = src[:, ok] * gain[:, None]
        else:
            rgb[:, ok] = src[:, ok]
        hole &= ~ok
    return rgb


def checks() -> None:
    """The numbers the film states, as asserts (the film asserts its own on-screen figures too)."""
    a = OFFICIAL["amir_kabir"]
    assert jalali(a["date"]) == "1 Aban 1405", "1 Aban 1405 = 23 Oct 2026"
    assert a["value"] - a["long_term"] == 20, "the article: 20 million m3 above the long-term average"
    assert a["value"] > a["long_term"] > a["last_year"], "123 > 103 > 17"
    assert OFFICIAL["five_dams"]["value"] == 359 and OFFICIAL["five_dams"]["last_year"] == 217
    assert sorted(set(range(1987, 2027)) - set(all_years())) == [], "every autumn 1987-2026 has a frame"
    assert sorted(GAPS) == sorted(NOT_SHOWN), "the years the film skips are the NOT_SHOWN years"
    for y in NOT_SHOWN:                                   # striped scenes: holes in the reservoir
        assert valid(y) < SHARE_LIMIT, (y, valid(y))


def main() -> None:
    checks()
    fr = frames()
    m = median()
    print("KARAJ DAM (AMIR KABIR), one autumn Landsat pass a year (karaj.py; data/karaj, get_karaj.py)")
    print(f"measured: {len(fr)} years {fr.index.min()}-{fr.index.max()} (median and counts); shown in the film: "
          f"{len(years())}")
    for y, why in sorted(GAPS.items()):
        print(f"  {y} ({persian(y)}): measured, not shown: {why}; valid share {valid(y):.4f}")
    print("  passes left out of every count:")
    for k, v in get_karaj.EXCLUDE.items():
        print(f"    {k}: {v}")
    print(f"\nthe usual autumn area: median of the 40 single passes = {m:.4f} km2")
    print(f"autumns within {NEAR:.0%} of the median: {len(near_median())} of {len(all_years())} "
          f"({', '.join(str(y) for y in all_years() if y not in near_median())} outside)")
    print("\nyear  persian  date        platform    clear  valid  area km2  days  share of median")
    for y in all_years():
        r = fr.loc[y]
        print(f"{y}  {persian(y)}    {r['date'].date()}  {r['platform']:11s} {r['clear_share']:.4f} "
              f"{r['valid_share']:.4f} {r['area_km2']:9.4f}  {int(r['days_from_1Oct']):+4d}  {area(y) / m:6.1%}"
              f"{'  not shown' if y in NOT_SHOWN else ''}")
    a25, a26 = area(2025), area(2026)
    print("\n1404 AND 1405 AGAINST THE USUAL AREA")
    print(f"  1404 (2025): {a25:.4f} km2 = {a25 / m:.1%} of the median ({m:.4f}); lowest since {lowest_since(2025)} "
          f"({area(lowest_since(2025)):.4f} km2); lowest of the 40: {min(all_years(), key=area)} "
          f"({min(area(y) for y in all_years()):.4f} km2)")
    print(f"  1405 (2026): {a26:.4f} km2 = {a26 / m:.1%} of the median")
    print(f"  1404 against 1405: {100 * (a26 / a25 - 1):+.1f} %")
    print("\nOFFICIAL (storage as reported; not an area)")
    for o in OFFICIAL.values():
        print(f"  {o['label']}: {o['value']} {o['unit']} on {o['date']:%d %b %Y} ({jalali(o['date'])}); "
              f"source: {o['source']}")
    print(f"  note: {CAPACITY_NOTE}")


if __name__ == "__main__":
    main()
