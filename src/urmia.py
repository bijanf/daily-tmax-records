"""LAKE URMIA FROM SPACE: the late-summer lake in true colour every year since 1986, and its level.

Measured data only:
- Pictures: Landsat Collection 2 Level-2 (USGS, via Microsoft's Planetary Computer), red, green
  and blue surface reflectance; per year and path the per-pixel median of the six least-cloudy
  scenes between 20 August and 10 October (29 Mordad to 18 Mehr) over those Landsat does not flag
  as cloud there (on the lake, where none is clear, over all: salt can be flagged), from
  get_urmia.py --colour; the paths' layers joined with matched tones. Land left without a clear
  view is taken from the nearest year with one; the lake is never filled. 1993, 1999, 2003 and
  2012 are left out (NO_PICTURE). White on the lakebed
  is salt crust or a thin film of brine over salt (reflectance cannot tell them apart).
- Level: the shore gauges' daily level to January 2020 (Mendeley deposit doi:10.17632/285n67m8zd.2,
  get_urmia.py --gauge), as the September mean; later years from official statements (OFFICIAL,
  with date and source: 1400, 1404, 1405; none found for 1399 or 1401-1403). September 1995:
  1,277.89 m; early Mehr 1404 (late September 2025): 1,269.50 m, 8.4 m lower; 19 Mehr 1405
  (11 October 2026): 1,270.58 m.
- The reported extent (EXTENT, on screen and in the caption): about 6,900 km2 in Khordad 1374
  (the official high; Aftab News 1051479) and 481 km2 in early Mehr 1404 (Mehr News 6745237),
  less than a tenth. A Landsat open-water check outside this repo (fact check of 27 Oct 2026)
  agrees: MNDWI > 0 and NIR < 0.10 gives 1.6 %, NDWI > 0 8.2 % of September 1995. The MNDWI
  areas in area_september.csv count salt crust as water in dry years and are not used.

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
EXTENT = {"Khordad 1374": 6900, "early Mehr 1404": 481}   # km2, reported (method not given)
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


NO_PICTURE = {1993: "no Landsat scene with at most 60 % cloud between 20 August and 10 October",
              1999: "the lake's south-east bay is under cloud in the only scene of path 168 (22 Sep)",
              2003: "no scene of path 168 in the window (path 169 has Landsat 5 of 24 Sep and 10 Oct): "
                    "6.4 % of the lake unseen",
              2012: "only Landsat 7 after its scan-line failure: its gaps stripe the salt flats"}


def years() -> list:
    """The years with a whole picture."""
    return [y for y in range(YEARS[0], YEARS[1] + 1) if y not in NO_PICTURE and (DATA / f"colour_{y}.npz").exists()]


@functools.cache
def lake() -> np.ndarray:
    """JRC's lake extent (any water 1984-2021) on the pictures' grid. Inside it get_urmia falls
    back to all scenes where none is clear, so an unseen pixel inside it was never seen at all."""
    return np.load(DATA / "picture_1995.npz")["lake"]


FEATHER = 8                                       # px: two layers blend over this width where they meet


def _matched(base: np.ndarray, layer: np.ndarray, over: np.ndarray) -> np.ndarray:
    """The layer in the base's tones: per band the least-squares gain and offset over their overlap
    (two paths' scenes are days apart: the water's colour and the light differ)."""
    out = layer.copy()
    for b in range(3):
        x, y = layer[b][over].astype(np.float64), base[b][over].astype(np.float64)
        gain, offset = np.linalg.lstsq(np.vstack([x, np.ones_like(x)]).T, y, rcond=None)[0]
        out[b] = gain * layer[b] + offset
    return out


def _join(strict: np.ndarray, loose: np.ndarray) -> np.ndarray:
    """One picture from the paths' layers: the first path's whole-scene layer, then each further
    layer (the other paths, then where any scene sees) matched to it and blended in at the join."""
    from scipy import ndimage
    rgb = strict[0].astype(np.float32)
    for layer in list(strict[1:]) + list(loose):
        layer = layer.astype(np.float32)
        have, new = np.isfinite(rgb[0]), np.isfinite(layer[0])
        if (have & new).sum() >= 1000:
            layer = _matched(rgb, layer, have & new)
        d = ndimage.distance_transform_edt(have)
        edge = have & new & (d <= FEATHER)
        w = d[edge] / FEATHER
        rgb[:, edge] = w * rgb[:, edge] + (1 - w) * layer[:, edge]
        rgb[:, ~have & new] = layer[:, ~have & new]
    return rgb


@functools.cache
def _rgb(year: int) -> np.ndarray:
    z = np.load(DATA / f"colour_{year}.npz")
    return _join(z["strict"], z["loose"])


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
