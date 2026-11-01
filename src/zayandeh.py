"""THE ZAYANDEH RUD AT SI-O-SE POL FROM SPACE: in which months of each year Landsat saw water in
the river's bed in the middle of Isfahan, 1370-1405, and the late-summer picture of the reach.

Measured data only, from get_zayandeh.py (Landsat Collection 2 Level-2, USGS, via Microsoft's
Planetary Computer). The reach: about 6 km of the bed, 2.7 km upstream and 2.5 km downstream of
Si-o-se Pol (JRC Global Surface Water's largest connected piece of water in the box). Open water =
MNDWI > 0 and NIR < 0.10 on Landsat's 30-m pixels. A pass counts when it saw at least half of the
reach clear of cloud; Landsat 7 after its scan-line failure is left out (its stripes hide water in
a 120-m river: the log compares it with Landsat 8 in the same years). A Persian month is "full"
when at least one counted pass saw open water on 30 % of the reach or more (passes with water
along the whole reach read 38-55 %: the banks, islands and trees of the bed count as land), "low"
when the largest share was 5-30 %, "dry" under 5 %, "none" when no pass counted.

"Full" means water seen at least once, not a river that ran all month: most official openings of
1397-1404 lasted 10-20 days (OFFICIAL), so the calendar is an upper bound on the time the river
ran. More satellites fly now than in the 1990s (Landsat 8 and 9 since 2013 and 2021), so a short
flow is more likely caught today: the comparison favours the recent years.

The calendar starts in 1370. In the pictures of 1365-1369 the river is a dark band like that of
the 1370s, but in most months at most 5-30 % of the reach reads as open water: the stream was too
narrow or too overgrown for 30-m pixels, so the satellite cannot say whether it ran.

Independent check: the openings reported in the Persian press (OFFICIAL), compared month by month
in the log, with the rule's sensitivity (clear share, threshold, two passes) beside it. Pictures:
the median of the clear passes of 20 Aug-10 Oct; land never seen clear is taken from the nearest
year (never the reach); a year with only striped Landsat 7 passes shows their median.

    python -I src/zayandeh.py > outputs/zayandeh_log.txt
"""

from __future__ import annotations

import functools
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wateryear import farvardin1  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "zayandeh"
YEARS = (1991, 2026)                                # Gregorian years of the pictures (late summer)
PERSIAN = (1370, 1405)                              # Persian years of the calendar
FULL, LOW = 0.30, 0.05                             # open-water share of the reach: full, low
NO_PICTURE = {2003: "no clear pass between 20 August and 10 October",
              2010: "no clear pass between 20 August and 10 October"}
# Water in the city as reported in the Persian press (first day, last day, water in the city,
# outlet and article number); dates converted from the Persian calendar. Not a complete list:
# several openings (four of the five of 1401, spring flows) were not found.
OFFICIAL = (
    ("2014-11-06", "2014-12-06", True, "Hamshahri 311940"),
    ("2015-11-06", "2015-12-02", True, "Daneshjoo 457869; Tehran Times 250658"),
    ("2016-02-20", "2016-02-20", True, "Asriran 518492"),
    ("2017-01-24", "2017-02-12", True, "Aftab 421910; Hamshahri 361935"),
    ("2019-01-30", "2019-02-16", True, "Etemad 265670; Aftab 576510"),
    ("2019-03-21", "2019-06-26", True, "Tehran Times 433727; yjc 6990053"),
    ("2019-07-04", "2019-10-04", True, "Tasnim 2152106"),
    ("2019-11-11", "2019-12-04", True, "Tasnim 2152106"),
    ("2020-09-22", "2021-07-09", False, "Mehr 5255208 (no water in the city for 10 months)"),
    ("2021-07-11", "2021-07-11", True, "Mehr 5255208"),
    ("2022-05-26", "2022-06-07", True, "Mehr 5704377"),
    ("2023-02-09", "2023-02-19", True, "Mehr 5704377; Hamshahri 806065"),
    ("2023-11-11", "2023-11-28", True, "Mehr 6060674; Tabnak 1204466"),
    ("2024-03-23", "2024-03-23", True, "Mehr 6060674"),
    ("2024-11-29", "2024-12-17", True, "Hamshahri 904972; Mehr 6424336"),
    ("2025-04-04", "2025-04-13", True, "Mehr 6424336; IMNA 855288"),
    ("2026-06-03", "2026-09-06", True, "IRIB 5813886; Hamshahri 1067735; Mashregh 1838774"),
)


@functools.cache
def calendar() -> pd.DataFrame:
    return pd.read_csv(DATA / "calendar.csv", index_col=["jy", "jm"])


@functools.cache
def newest() -> date:
    """The date of the newest pass read: later months are still to come."""
    return max(date.fromisoformat(json.loads(f.read_text()).get("date", "1900-01-01"))
               for f in (DATA / "scenes").glob("*.json"))


def month_start(jy: int, jm: int) -> date:
    return farvardin1(jy) + timedelta(days=31 * (jm - 1) if jm <= 7 else 186 + 30 * (jm - 7))


def months(jy: int) -> list:
    """The twelve months of Persian year jy, Farvardin first: 'full', 'low', 'dry', 'none' (no
    counted pass) or 'future' (after the newest pass)."""
    cal = calendar()
    out = []
    for jm in range(1, 13):
        if month_start(jy, jm) > newest():
            out.append("future")
        elif (jy, jm) not in cal.index:
            out.append("none")
        else:
            w = cal.loc[(jy, jm), "wet_max"]
            out.append("full" if w >= FULL else "low" if w >= LOW else "dry")
    return out


def counts(jy: int) -> tuple[int, int]:
    """(full months, months with a counted pass) of Persian year jy."""
    m = months(jy)
    return m.count("full"), sum(x in ("full", "low", "dry") for x in m)


def decade(a: int, b: int) -> float:
    """Full months per year, Persian years a to b."""
    return float(np.mean([counts(jy)[0] for jy in range(a, b + 1)]))


def years() -> list:
    """The Gregorian years with a late-summer picture."""
    return [y for y in range(YEARS[0], YEARS[1] + 1) if y not in NO_PICTURE and (DATA / f"colour_{y}.npz").exists()]


@functools.cache
def _rgb(year: int) -> np.ndarray:
    return np.load(DATA / f"colour_{year}.npz")["rgb"].astype(np.float32)


@functools.cache
def colour(year: int) -> np.ndarray:
    """The year's picture; land never seen clear taken from the nearest year (never the reach)."""
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


def variant(df: pd.DataFrame, clear=0.5, full=FULL, passes=1, striped=False) -> dict:
    """The calendar under another rule: {(jy, jm): 'full' | 'low' | 'dry'}."""
    c = df[(df["clear"] >= clear) & (striped | ~df["striped"])]
    out = {}
    for k, g in c.groupby(["jy", "jm"]):
        out[k] = "full" if (g["wet"] >= full).sum() >= passes else "low" if g["wet"].max() >= LOW else "dry"
    return out


def official_months() -> tuple[set, set]:
    """Months with water in the city on at least one reported day; months wholly inside a reported dry spell."""
    from get_zayandeh import persian
    wet, dry_days = set(), {}
    for a, b, flow, _ in OFFICIAL:
        d0, d1 = date.fromisoformat(a), date.fromisoformat(b)
        for k in range((d1 - d0).days + 1):
            m = persian(d0 + timedelta(days=k))
            if flow:
                wet.add(m)
            else:
                dry_days[m] = dry_days.get(m, 0) + 1
    length = lambda jy, jm: (month_start(jy, jm + 1) if jm < 12 else farvardin1(jy + 1)) - month_start(jy, jm)
    dry = {m for m, n in dry_days.items() if n == length(*m).days}
    return wet, dry


def checks() -> None:
    """The rule's sensitivity, Landsat 7's stripes against Landsat 8, and the press record."""
    from get_zayandeh import errors, table
    df = table()
    print(f"passes read {len(df)}, failed to read {len(errors())} {errors()}")
    s = df[(df["date"].dt.year >= 2013) & (df["date"].dt.year <= 2021) & (df["clear"] >= 0.5)]
    for name, rows in (("Landsat 7 striped", s[s["striped"]]), ("Landsat 8", s[s["platform"] == "landsat-8"])):
        print(f"2013-2021, counted passes of {name}: {len(rows)}, with water on 30 % or more: "
              f"{100 * (rows['wet'] >= FULL).mean():.0f} %")
    print("rule sensitivity: full months per year, 1370-1379 | 1400-1404 (months seen per year)")
    rules = (("as built: clear >= 0.5, full >= 0.30, 1 pass", {}), ("clear >= 0.4", dict(clear=0.4)),
             ("clear >= 0.8", dict(clear=0.8)),
             ("clear >= 0.9", dict(clear=0.9)), ("full >= 0.25", dict(full=0.25)), ("full >= 0.40", dict(full=0.40)),
             ("two passes >= 0.30", dict(passes=2)), ("striped Landsat 7 kept", dict(striped=True)))
    for name, kw in rules:
        v = variant(df, **kw)
        f = lambda a, b: np.mean([sum(v.get((jy, m)) == "full" for m in range(1, 13)) for jy in range(a, b + 1)])
        n = lambda a, b: np.mean([sum((jy, m) in v for m in range(1, 13)) for jy in range(a, b + 1)])
        print(f"  {name:46s} {f(1370, 1379):4.1f} ({n(1370, 1379):4.1f}) | {f(1400, 1404):4.1f} ({n(1400, 1404):4.1f})")
    wet, dry = official_months()
    for name, kw in (("as built", {}), ("clear >= 0.9", dict(clear=0.9))):
        v = variant(df, **kw)
        a = [v.get(m, "none") for m in sorted(wet)]
        b = [v.get(m, "none") for m in sorted(dry)]
        print(f"press record, {name}: {len(wet)} months with water reported -> full {a.count('full')}, low "
              f"{a.count('low')}, dry {a.count('dry')}, none {a.count('none')}; {len(dry)} months reported dry -> full "
              f"{b.count('full')}, low {b.count('low')}, dry {b.count('dry')}, none {b.count('none')}")
    v = variant(df)
    extra = sorted(m for m, x in v.items() if x == "full" and 1393 <= m[0] <= 1405 and m not in wet)
    print(f"full months 1393-1405 with no press report (spring flows were not searched): {len(extra)} "
          + " ".join(f"{jy}-{jm:02d}" for jy, jm in extra))
    missed = {k: [f"{jy}-{jm:02d}" for jy, jm in sorted(wet) if v.get((jy, jm), "none") == k] for k in ("low", "dry", "none")}
    print(f"months with water reported but not full: {missed}")
    e = [v.get((jy, m)) for jy in range(1365, 1370) for m in range(1, 13)]   # the years before the calendar
    print(f"1365-1369 (left out of the calendar): {sum(x is not None for x in e)} months counted, full "
          f"{e.count('full')}, low {e.count('low')}, dry {e.count('dry')}")
    c = df[df["counts"]]
    for a, b in ((1370, 1379), (1400, 1404)):
        n = c[(c["jy"] >= a) & (c["jy"] <= b)]
        print(f"counted passes per year {a}-{b}: {len(n) / (b - a + 1):.1f} (more passes catch more short flows)")


def main() -> None:
    print(f"reach: {int(channel().sum())} cells of about 30 m; newest pass {newest()}")
    print("Persian year: months Farvardin..Esfand (W full, w low, . dry, _ no counted pass, - to come); full / seen")
    for jy in range(PERSIAN[0], PERSIAN[1] + 1):
        m = months(jy)
        w, s = counts(jy)
        sym = {"full": "W", "low": "w", "dry": ".", "none": "_", "future": "-"}
        print(f"  {jy} ({jy + 621}/{(jy + 622) % 100:02d}): {''.join(sym[x] for x in m)}  {w:2d} / {s:2d}")
    for a, b in ((1370, 1374), (1375, 1379), (1370, 1379), (1380, 1384), (1385, 1389), (1390, 1394),
                 (1395, 1399), (1400, 1404)):
        s = np.mean([counts(jy)[1] for jy in range(a, b + 1)])
        print(f"  {a}-{b}: full months per year {decade(a, b):.1f} (of {s:.1f} seen)")
    checks()
    have = years()
    striped = [y for y in have if bool(np.load(DATA / f"colour_{y}.npz").get("striped", False))]
    print(f"pictures: {len(have)} years {have[0]}-{have[-1]}; none for "
          f"{sorted(set(range(YEARS[0], YEARS[1] + 1)) - set(have))}; striped Landsat 7 medians {striped}")


if __name__ == "__main__":
    main()
