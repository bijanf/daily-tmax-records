"""THE ZAYANDEH RUD IN ISFAHAN FROM SPACE: in which months of each year Landsat saw the river
flowing through the city, 1365-1405, and the late-summer picture of the reach.

Measured data only, from get_zayandeh.py (Landsat Collection 2 Level-2, USGS, via Microsoft's
Planetary Computer; the channel from JRC Global Surface Water; open water = MNDWI > 0 and
NIR < 0.10). A Persian month takes the largest open-water share of the channel among its passes
that saw at least half of the channel clear: "full" at 30 % or more (the river running through its
bed), "low" at 5-30 % (a narrow or reed-filled stream: most of these months are in 1365-1369,
where the pictures show a dark, green, narrow river), "dry" under 5 % (puddles at most); "none"
when no pass counted (clouds, or Landsat 7's stripes). Landsat cannot see a stream narrower than
its 30-m pixels: "dry" means no water the satellite can see. More satellites fly now than in the
1980s (Landsat 8 and 9 since 2013 and 2021), so a short flow is more likely caught today: the
comparison favours the recent years, not the old ones. Pictures of 2004-2012 are medians of
Landsat 7's striped passes (its gaps move from pass to pass).

    python -I src/zayandeh.py > outputs/zayandeh_log.txt
"""

from __future__ import annotations

import functools
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "zayandeh"
YEARS = (1986, 2026)                                # Gregorian years of the pictures (late summer)
PERSIAN = (1365, 1405)                              # Persian years of the calendar
FULL, LOW = 0.30, 0.05                             # open-water share of the channel: full, low
NO_PICTURE = {2003: "no clear pass between 20 August and 10 October",
              2010: "no clear pass between 20 August and 10 October"}


@functools.cache
def calendar() -> pd.DataFrame:
    return pd.read_csv(DATA / "calendar.csv", index_col=["jy", "jm"])


def months(jy: int) -> list:
    """The twelve months of Persian year jy, Farvardin first: 'full', 'low', 'dry' or 'none'."""
    cal = calendar()
    out = []
    for jm in range(1, 13):
        if (jy, jm) not in cal.index:
            out.append("none")
        else:
            w = cal.loc[(jy, jm), "wet_max"]
            out.append("full" if w >= FULL else "low" if w >= LOW else "dry")
    return out


def counts(jy: int) -> tuple[int, int]:
    """(full months, months with a counted pass) of Persian year jy."""
    m = months(jy)
    return m.count("full"), 12 - m.count("none")


def years() -> list:
    """The Gregorian years with a late-summer picture."""
    return [y for y in range(YEARS[0], YEARS[1] + 1) if y not in NO_PICTURE and (DATA / f"colour_{y}.npz").exists()]


@functools.cache
def _rgb(year: int) -> np.ndarray:
    return np.load(DATA / f"colour_{year}.npz")["rgb"].astype(np.float32)


@functools.cache
def colour(year: int) -> np.ndarray:
    """The year's picture; land never seen clear taken from the nearest year (never the channel)."""
    rgb = _rgb(year).copy()
    hole = np.isnan(rgb).any(axis=0) & ~channel()
    for d in (1, -1, 2, -2, 3, -3):
        other = year + d
        if not hole.any() or other in NO_PICTURE or not (DATA / f"colour_{other}.npz").exists():
            continue
        src = _rgb(other)
        ok = hole & ~np.isnan(src).any(axis=0)
        rgb[:, ok] = src[:, ok]
        hole &= ~ok
    return rgb


@functools.cache
def channel() -> np.ndarray:
    return np.load(DATA / "channel.npz")["channel"]


def main() -> None:
    print(f"channel: {int(channel().sum())} cells of about 30 m")
    print("Persian year: months Farvardin..Esfand (W full, w low, . dry, _ no counted pass); full / seen")
    for jy in range(PERSIAN[0], PERSIAN[1] + 1):
        m = months(jy)
        w, s = counts(jy)
        print(f"  {jy} ({jy + 621}/{jy + 622 - 2000:02d}): {''.join({'full': 'W', 'low': 'w', 'dry': '.', 'none': '_'}[x] for x in m)}"
              f"  {w:2d} / {s:2d}")
    for a, b in ((1365, 1369), (1370, 1374), (1375, 1379), (1380, 1384), (1385, 1389), (1390, 1394),
                 (1395, 1399), (1400, 1404)):
        w = [counts(jy)[0] for jy in range(a, b + 1)]
        s = [counts(jy)[1] for jy in range(a, b + 1)]
        print(f"  {a}-{b}: full months per year {np.mean(w):.1f} (of {np.mean(s):.1f} seen)")
    have = years()
    print(f"pictures: {len(have)} years {have[0]}-{have[-1]}; none for "
          f"{sorted(set(range(YEARS[0], YEARS[1] + 1)) - set(have))}")


if __name__ == "__main__":
    main()
