"""LAKE URMIA FROM SPACE: the late-summer lake in true colour every year since 1986, and its level.

Measured data only:
- Pictures: Landsat Collection 2 Level-2 (USGS, via Microsoft's Planetary Computer), red, green
  and blue surface reflectance; per year the per-pixel median of the six least-cloudy scenes of
  each path between 20 August and 10 October (29 Mordad to 18 Mehr), clouds flagged by Landsat
  dropped outside the lake, from get_urmia.py --colour. Land left without a clear view (cloud in
  every scene) is taken from the nearest year with one; the lake is never filled. 1993 has no
  scene and 2003 none for the lake's south-east: both are left out. White on the lakebed is salt
  crust or a thin film of brine over salt (reflectance cannot tell them apart).
- Level: the shore gauges' daily level to January 2020 (Mendeley deposit doi:10.17632/285n67m8zd.2,
  get_urmia.py --gauge), as the September mean; later years from official statements (OFFICIAL,
  with date and source: 1400, 1404, 1405; none found for 1399 or 1401-1403). September 1995:
  1,277.89 m; early Mehr 1404 (late September 2025): 1,269.50 m, 8.4 m lower; 19 Mehr 1405
  (11 October 2026): 1,270.58 m.
- Not from this module (fact check, in the caption): the reported extent fell from about 6,900 km2
  (Khordad 1374, the official high) to 481 km2 (early Mehr 1404), less than a tenth; open water
  in Landsat (MNDWI > 0 and NIR < 0.10, the rule closest to JRC's monthly maps) 1.6 % of
  September 1995, NDWI > 0 8.2 %. The MNDWI areas in area_september.csv count salt crust as
  water in dry years and are not used.

    python -I src/urmia.py > outputs/urmia_log.txt
"""

from __future__ import annotations

import functools
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "urmia"
YEARS = (1986, 2026)
BASE, LOW, NOW = 1995, 2025, 2026
# Official statements (level in m above sea level), for the years after the gauge record ends. No
# end-of-Shahrivar figure was found for 1399 or 1401-1403 (only spring or autumn readings, or "the
# lake dried" without a number; level search of 27 Oct 2026): those years have no level.
OFFICIAL = {
    2021: (1270.66, "30 Shahrivar 1400 (21 Sep 2021); West Azarbaijan Regional Water Co. (CEO) via ISNA, Tehran "
                    "Times 465314; the same company gives 1,270.69 on 18 Shahrivar and 1,270.65 at 1 Mehr 1400"),
    2025: (1269.50, "early Mehr 1404 (23-30 Sep 2025); West Azarbaijan Regional Water Co., citing the "
                    "Ministry of Energy; Mehr News 6745237"),
    2026: (1270.58, "19 Mehr 1405 (11 Oct 2026); East Azarbaijan Regional Water Co.; Mehr News 6974755"),
}


@functools.cache
def gauge() -> pd.Series:
    d = pd.read_csv(DATA / "level_insitu_daily.csv", parse_dates=["date"]).set_index("date").level_m
    sep = d[d.index.month == 9]
    n = sep.groupby(sep.index.year).size()
    return sep.groupby(sep.index.year).mean()[n >= 28]          # a full September only


@functools.cache
def levels() -> pd.Series:
    """The lake's level for each year of the film: the gauges' September mean, later official."""
    g = gauge()
    out = {y: float(g.loc[y]) for y in range(YEARS[0], YEARS[1] + 1) if y in g.index}
    for y, (v, _) in OFFICIAL.items():
        assert y not in out, f"{y}: gauge and official both"
        out[y] = v
    return pd.Series(out).sort_index()


NO_PICTURE = {1993: "no Landsat scene between 20 August and 10 October",
              2003: "no scene of path 168 in the window: 6 % of the lake unseen (the only one, Landsat 7 of "
                    "11 October, is striped)"}


def years() -> list:
    """The years with a whole picture."""
    return [y for y in range(YEARS[0], YEARS[1] + 1) if y not in NO_PICTURE and (DATA / f"colour_{y}.npz").exists()]


@functools.cache
def lake() -> np.ndarray:
    """JRC's lake extent (any water 1984-2021) on the pictures' grid. get_urmia drops clouds only
    outside it widened by two pixels, so an unseen pixel inside it was never seen at all."""
    return np.load(DATA / "picture_1995.npz")["lake"]


@functools.cache
def _rgb(year: int) -> np.ndarray:
    return np.load(DATA / f"colour_{year}.npz")["rgb"].astype(np.float32)


def colour(year: int) -> dict:
    """The year's picture; land without a clear view taken from the nearest year with one."""
    rgb = _rgb(year).copy()
    hole = np.isnan(rgb).any(axis=0) & ~lake()
    filled = 0
    for d in (1, -1, 2, -2, 3, -3):
        other = year + d
        if not hole.any() or other in NO_PICTURE or not (DATA / f"colour_{other}.npz").exists():
            continue
        src = _rgb(other)
        ok = hole & ~np.isnan(src).any(axis=0)
        rgb[:, ok] = src[:, ok]
        hole &= ~ok
        filled += int(ok.sum())
    z = np.load(DATA / f"colour_{year}.npz")
    return dict(rgb=rgb, items=[str(i) for i in z["items"]], filled=filled / rgb[0].size,
                lake_unseen=float((np.isnan(rgb[0]) & lake()).mean()))


def main() -> None:
    lv = levels()
    have = years()
    print(f"pictures: {len(have)} years, {have[0]}-{have[-1]}; none for "
          f"{sorted(set(range(YEARS[0], YEARS[1] + 1)) - set(have))}")
    print(f"level: gauge September means {gauge().index.min()}-{gauge().index.max()}; official {sorted(OFFICIAL)}; "
          f"missing {sorted(set(range(YEARS[0], YEARS[1] + 1)) - set(lv.index))}")
    for y in (BASE, LOW, NOW):
        print(f"  {y} ({y - 621}): {lv.loc[y]:.2f} m")
    print(f"  {BASE} to {LOW}: {lv.loc[BASE] - lv.loc[LOW]:.2f} m lower; {BASE} to {NOW}: "
          f"{lv.loc[BASE] - lv.loc[NOW]:.2f} m lower; {LOW} to {NOW}: {lv.loc[NOW] - lv.loc[LOW]:+.2f} m")
    for y in have:
        c = colour(y)
        print(f"  picture {y}: {len(c['items'])} scenes; land from a nearby year {100 * c['filled']:.1f} % of the box; "
              f"lake unseen {100 * c['lake_unseen']:.2f} %; still unseen {100 * np.isnan(c['rgb'][0]).mean():.2f} %")
    for y, (v, src) in OFFICIAL.items():
        print(f"  official {y}: {v} m, {src}")


if __name__ == "__main__":
    main()
