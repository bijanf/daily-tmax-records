"""MAMLU DAM, 40 AUTUMNS FROM SPACE: the open water of the Mamlu reservoir, one of the five dams that supply
Tehran, in one autumn Landsat pass a year, 1987-2026.

Measured data only, from get_mamlu.py (data/mamlu): per year the chosen pass and its area of open water in km2
on the pass's own grid (frames.csv). Six of the 40 are measured but not shown (NOT_SHOWN): striped Landsat 7
scenes or scenes with cloud, so the picture would have holes; their areas count in every statistic.
A Persian year P is the autumn of Gregorian year P + 621 (1366 = 1987, 1404 = 2025, 1405 = 2026).

- The median of the 40 single passes (km2) is printed for completeness only: the reservoir is absent before its
  first autumn of more than 1 km2 (2008), so no usual is drawn or quoted for Mamlu.
- 1404 (2025) against that median, and how many autumns lie within 10 % of it.
- Pictures (picture): the pass in true colour, with land gaps taken from the nearest year with a view, as the
  Mamlu and Lar pictures are. Display only; the reservoir is never filled, no area uses them.
- The storage figures are not here: they come from the official article (src/tehran5.py).

    python -I src/mamlu.py
"""

from __future__ import annotations

import functools
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import get_mamlu  # noqa: E402
from wateryear import farvardin1  # noqa: E402

DATA = get_mamlu.DATA
NO_PASS = {
    2003: "the catalogue search found no Landsat scene covering the dam point between 1 September and 15 November 2003",
}
NOT_SHOWN = {
    2004: "its chosen pass (Landsat 7, 1 October 2004: 4 % of the reservoir without data, 4 % not clear)",
    2005: "its chosen pass (Landsat 7, 4 October 2005: 5 % of the reservoir without data, 5 % not clear)",
    2006: "its chosen pass (Landsat 7, 7 October 2006: 10 % of the reservoir without data, 10 % not clear)",
    2007: "its chosen pass (Landsat 7, 24 September 2007: 4 % of the reservoir without data, 4 % not clear)",
    2011: "its chosen pass (Landsat 7, 19 September 2011: 8 % of the reservoir without data, 8 % not clear)",
    2012: "its chosen pass (Landsat 7, 7 October 2012: 10 % of the reservoir without data, 10 % not clear)"}
SHARE_LIMIT = 0.99                                        # a shown picture has at least this share of the reservoir with data and clear
GAPS = {**NO_PASS, **NOT_SHOWN}                           # the years the film skips                           # the years the film skips
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


def clear(year: int) -> float:
    """The share of the reservoir that is clear in the year's pass."""
    return float(frames().loc[year, "clear_share"])


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
    coloured enough to count (the Karaj passes have a few such dots)."""
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
    """The measured data's own asserts (the film asserts its on-screen figures too)."""
    assert sorted(set(range(1987, 2027)) - set(all_years())) == sorted(NO_PASS), "the autumns without a frame are NO_PASS"
    assert sorted(NOT_SHOWN) == [2004, 2005, 2006, 2007, 2011, 2012], sorted(NOT_SHOWN)
    for y in NOT_SHOWN:                                   # holes in the reservoir: striped or cloudy
        assert min(valid(y), clear(y)) < SHARE_LIMIT, (y, valid(y), clear(y))
    for y in years():                                     # every shown picture is whole over the reservoir
        assert valid(y) >= SHARE_LIMIT and clear(y) >= SHARE_LIMIT, (y, valid(y), clear(y))


def main() -> None:
    checks()
    fr = frames()
    m = median()
    print("MAMLU DAM, one autumn Landsat pass a year (mamlu.py; data/mamlu, get_mamlu.py)")
    print(f"measured: {len(fr)} years {fr.index.min()}-{fr.index.max()} (median and counts); shown in the film: "
          f"{len(years())}")
    for y, why in sorted(NO_PASS.items()):
        print(f"  {y} ({persian(y)}): no frame: {why}")
    for y, why in sorted(NOT_SHOWN.items()):
        print(f"  {y} ({persian(y)}): measured, not shown: {why}; valid share {valid(y):.4f}, clear {clear(y):.4f}")
    print("  passes left out of every count:")
    for k, v in get_mamlu.EXCLUDE.items():
        print(f"    {k}: {v}")
    print(f"\nthe usual autumn area: median of the 40 single passes = {m:.4f} km2")
    print(f"autumns within {NEAR:.0%} of the median: {len(near_median())} of {len(all_years())} "
          f"({', '.join(str(y) for y in near_median())})")
    print("\nyear  persian  date        platform    clear  valid  area km2  days  share of median")
    for y in all_years():
        r = fr.loc[y]
        print(f"{y}  {persian(y)}    {r['date'].date()}  {r['platform']:11s} {r['clear_share']:.4f} "
              f"{r['valid_share']:.4f} {r['area_km2']:9.4f}  {int(r['days_from_1Oct']):+4d}  {area(y) / m:6.1%}"
              f"{'  not shown' if y in NOT_SHOWN else ''}")
    a25, a26 = area(2025), area(2026)
    print("\n1404 AND 1405 AGAINST THE USUAL AREA")
    second = sorted(all_years(), key=area)[1]
    print(f"  1404 (2025): {a25:.4f} km2 = {a25 / m:.1%} of the median ({m:.4f}); the smallest of the {len(all_years())}: "
          f"{min(all_years(), key=area)} ({min(area(y) for y in all_years()):.4f} km2); the next smallest: {second} "
          f"({area(second):.4f} km2)")
    print(f"  1405 (2026): {a26:.4f} km2 = {a26 / m:.1%} of the median")
    print(f"  1404 against 1405: {100 * (a26 / a25 - 1):+.1f} %")


if __name__ == "__main__":
    main()
