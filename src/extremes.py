"""Europe's extremes scoreboard: how often each kind of extreme happens now against 1961-1990.

For every European station of the record set, events per year in 1961-1990 and in 2016-2025:

    days >= 35 C          daily maximum (TMAX, with the national fill of fill_recent.py)
    hot nights            daily minimum >= 20 C ("tropical nights", TMIN)
    frost days            daily minimum < 0 C
    hot days              daily maximum above the station's own 1961-1990 99th percentile
    downpours             daily rain above the station's own 1961-1990 99th percentile of wet
                          days (>= 1 mm, PRCP)
    dry seasons           March-August water balance (drought.py) below the station's own
                          1961-1990 10th percentile, as a share of seasons

A year counts if >= 90 % of its days have the variable; a station counts for an extreme if it
has >= 20 such years in 1961-1990 and >= 7 in 2016-2025 (seasons: drought.py's own rules).
Values with a GHCN-Daily quality flag are dropped; temperatures also beyond 6 sigma of the
station's seasonal cycle (station_records.qc_outliers). The averages are over stations.

Also: the year of each station's warmest night ever, and the stations whose two wettest days
on record fell in the same recent year.

    outputs/extremes_log.txt

Run with `python -I src/extremes.py > outputs/extremes_log.txt`.
"""

from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import drought  # noqa: E402
import station_records as sr  # noqa: E402
from build_tmax import DLY, parse_dly  # noqa: E402

BASE, RECENT = (1961, 1990), (2016, 2025)
YEAR_FRAC, MIN_BASE, MIN_RECENT = 0.9, 20, 7


def _series(args) -> np.ndarray:
    sid, element, n = args
    out = np.full(n, np.nan, np.float32)
    i, v = parse_dly(DLY / f"{sid}.dly", element)
    keep = i < n
    out[i[keep]] = v[keep] / 10
    return out


def load() -> dict:
    """European stations and their quality-controlled daily TMAX, TMIN and PRCP."""
    st, tmax, dates = sr.load()
    eu = np.array([sr.region(c, lo, la) == "Europe" for c, lo, la in zip(st["country"], st["lon"], st["lat"])])
    st, tmax = st[eu].copy(), tmax[eu]
    sr.qc_outliers(tmax, dates)
    n = tmax.shape[1]
    with ProcessPoolExecutor(max_workers=12) as pool:
        tmin = np.stack(list(pool.map(_series, [(s, b"TMIN", n) for s in st.index])))
        prcp = np.stack(list(pool.map(_series, [(s, b"PRCP", n) for s in st.index])))
    sr.qc_outliers(tmin, dates)
    prcp[prcp < 0] = np.nan
    return dict(st=st, dates=pd.DatetimeIndex(dates), tmax=tmax, tmin=tmin, prcp=prcp)


def per_year(event: np.ndarray, valid: np.ndarray, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Events per year (year x station); NaN for years with < YEAR_FRAC of days valid."""
    frame = pd.DataFrame(np.where(valid, event, np.nan).T, index=dates)
    g = frame.groupby(dates.year)
    days = pd.Series(1, index=dates).groupby(dates.year).size()
    return (g.mean() * 365.25).where(g.count().ge(YEAR_FRAC * days, axis=0))


def base_recent(per: pd.DataFrame) -> pd.DataFrame:
    """Per station: mean of the base and of the recent period, for stations with enough years."""
    b, r = per.loc[BASE[0]:BASE[1]], per.loc[RECENT[0]:RECENT[1]]
    ok = (b.count() >= MIN_BASE) & (r.count() >= MIN_RECENT)
    return pd.DataFrame({"base": b.mean()[ok], "recent": r.mean()[ok]})


def own_percentile(x: np.ndarray, dates: pd.DatetimeIndex, q: float, wet: bool = False) -> np.ndarray:
    """Each station's q-th percentile over 1961-1990 (wet days >= 1 mm only if wet)."""
    base = np.asarray((dates.year >= BASE[0]) & (dates.year <= BASE[1]))
    out = np.full(x.shape[0], np.nan)
    for i in range(x.shape[0]):
        v = x[i, base]
        v = v[np.isfinite(v)]
        if len(v) < 2 / 3 * base.sum():
            continue
        if wet:
            v = v[v >= 1]
        out[i] = np.percentile(v, q)
    return out


def dry_seasons() -> pd.DataFrame:
    """Share of March-August seasons below the station's own 1961-1990 10th percentile."""
    seasons = drought.compute()["seasons"].pivot(index="year", columns="id", values="balance")
    b, r = seasons.loc[BASE[0]:BASE[1]], seasons.loc[RECENT[0]:RECENT[1]]
    ok = (b.count() >= MIN_BASE) & (r.count() >= MIN_RECENT)
    q10 = b.quantile(0.10)
    share = lambda s: (s.lt(q10) & s.notna()).sum() / s.count()  # noqa: E731
    return pd.DataFrame({"base": share(b)[ok], "recent": share(r)[ok]})


def compute() -> dict:
    d = load()
    st, dates, tmax, tmin, prcp = d["st"], d["dates"], d["tmax"], d["tmin"], d["prcp"]
    vx, vn, vp = np.isfinite(tmax), np.isfinite(tmin), np.isfinite(prcp)
    tx99 = own_percentile(tmax, dates, 99)
    p99 = own_percentile(prcp, dates, 99, wet=True)
    ids = st.index
    frame = lambda per: base_recent(per.set_axis(ids, axis=1))  # noqa: E731
    score = {
        "hot35": frame(per_year(tmax >= 35, vx, dates)),
        "nights": frame(per_year(tmin >= 20, vn, dates)),
        "dry": dry_seasons(),
        "downpours": frame(per_year(prcp >= p99[:, None], vp & np.isfinite(p99)[:, None], dates)),
        "frost": frame(per_year(tmin < 0, vn, dates)),
        "hot_own": frame(per_year(tmax >= tx99[:, None], vx & np.isfinite(tx99)[:, None], dates)),
    }
    # warmest night ever per station
    tn = np.where(vn, tmin, -np.inf)
    j = tn.argmax(axis=1)
    has = vn.any(axis=1)
    nights = pd.DataFrame({"value": tn.max(axis=1), "date": dates[j]}, index=ids)[has]
    nights["year"] = nights["date"].dt.year
    # stations whose two wettest days fell in the same year since 2020
    wet_rows = []
    for i, sid in enumerate(ids):
        s = pd.Series(prcp[i], index=dates).dropna()
        full = s.groupby(s.index.year).count() >= 0.95 * 365
        s = s[s.index.year.isin(full[full].index)]
        if len(s) and s.index.year.max() >= 2020:
            top = s.nlargest(2)
            if top.index.year.nunique() == 1 and top.index.year[0] >= 2020:
                wet_rows.append(dict(id=sid, first=int(s.index.year.min()), years=int(full.sum()),
                                     d1=top.index[0], mm1=float(top.iloc[0]), d2=top.index[1], mm2=float(top.iloc[1])))
    return dict(st=st, score=score, nights=nights, wet=pd.DataFrame(wet_rows).set_index("id") if wet_rows else
                pd.DataFrame(), p99=pd.Series(p99, index=ids), tx99=pd.Series(tx99, index=ids))


LABELS = {"hot35": "days >= 35 C (per year)", "nights": "hot nights, min >= 20 C (per year)",
          "dry": "dry Mar-Aug seasons (share, own p10)", "downpours": "downpours > own p99 (per year)",
          "frost": "frost days, min < 0 C (per year)", "hot_own": "hot days > own p99 (per year)"}


def main() -> None:
    d = compute()
    st = d["st"]
    print(f"European stations: {len(st)}; base {BASE[0]}-{BASE[1]}, recent {RECENT[0]}-{RECENT[1]}")
    print("\n1. Scoreboard: station averages, base -> recent, ratio of the averages")
    for key, f in d["score"].items():
        print(f"   {LABELS[key]:<40} n={len(f):3d}  {f['base'].mean():7.2f} -> {f['recent'].mean():7.2f}  "
              f"x{f['recent'].mean() / f['base'].mean():5.2f}  up {(f['recent'] > f['base']).sum():3d} "
              f"down {(f['recent'] < f['base']).sum():3d} same {(f['recent'] == f['base']).sum():3d}")
    print(f"   median own 99th percentile of wet-day rain: {d['p99'].median():.1f} mm")

    h = d["score"]["hot_own"]
    ratio = h["recent"] / h["base"]
    print("\n2. Hot days above the own 99th percentile, ratio per station:",
          pd.cut(ratio, [0, 1, 2, 3, 5, np.inf]).value_counts().sort_index().to_dict())

    n = d["nights"]
    era = pd.cut(n["year"], [0, 1999, 2019, 9999], labels=["before 2000", "2000-2019", "2020s"])
    print("\n3. Year of the warmest night ever:", era.value_counts().sort_index().to_dict())
    last = n[n["year"] == n["year"].max()]
    print(f"   in {n['year'].max()}: {len(last)} stations; most common dates:",
          last["date"].dt.strftime("%d %b").value_counts().head(3).to_dict())

    print("\n4. Stations whose two wettest days on record fell in the same year since 2020 (complete years):")
    for sid, r in d["wet"].iterrows():
        print(f"   {st.loc[sid, 'name'].title():<24} {r['d1']:%d %b %Y} {r['mm1']:.1f} mm, {r['d2']:%d %b %Y} "
              f"{r['mm2']:.1f} mm; {r['years']} complete years since {r['first']}")


if __name__ == "__main__":
    main()
