"""Exploratory findings from the per-station record set.

    1. year of each station's all-time hottest day
    2. record highs vs record lows of the daily maximum, 2020s and this year
    3. month of the 2020s records, by region
    4. elevation: do mountain stations show the same surge?
    5. record margins: do 2020s records beat the runner-up by more?

Same stations and quality control as station_records.py. compute() is shared
with plot_findings.py. Run with `python -I src/findings.py` for the report.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import station_records as sr  # noqa: E402

ERAS = [(0, 1949, "before 1950"), (1950, 1999, "1950–1999"), (2000, 2019, "2000–2019"),
        (2020, 9999, "2020s")]


def compute() -> dict:
    st, tmax, dates = sr.load()
    sr.qc_outliers(tmax, dates)
    d = pd.to_datetime(dates)
    fy = sr.FINAL_YEAR
    idx = pd.read_csv(sr.OUT / "station_index.csv").set_index("id").loc[st.index]
    idx["share"] = idx["records_2020s"] / idx["n_days"]

    # all-time hottest day, and the best value before this year
    filled = np.where(np.isfinite(tmax), tmax, -np.inf)
    i = filled.argmax(axis=1)
    before = np.where(np.asarray(d.year)[None, :] < fy, filled, -np.inf)
    j = before.argmax(axis=1)
    hot = idx[["name", "country", "region", "lat", "lon", "elev"]].copy()
    hot["date"], hot["value"] = d[i], filled.max(axis=1)
    hot["prev_date"], hot["prev_value"] = d[j], before.max(axis=1)
    hot["year"] = hot["date"].dt.year

    # current record high and record low of TMAX for each calendar day
    cube, years, md = sr.calendar_cube(tmax, dates)
    valid = np.isfinite(cube)
    hi = np.where(valid, cube, -np.inf)
    lo = np.where(valid, cube, np.inf)
    hi_max = hi.max(axis=1, keepdims=True)
    hi_year = years[(hi == hi_max).argmax(axis=1)]
    lo_year = years[(lo == lo.min(axis=1, keepdims=True)).argmax(axis=1)]
    second = np.where(hi == hi_max, -np.inf, hi).max(axis=1)
    margin = hi_max[:, 0, :] - second
    window = np.arange(365)[None, :] < idx["n_days"].to_numpy()[:, None]

    rec = pd.read_csv(sr.OUT / "records_long.csv.gz").merge(idx[["region"]], left_on="id", right_index=True)
    rec["month"] = rec["md"].str[:2].astype(int)
    return dict(idx=idx, hot=hot, years=years, hi_year=hi_year, lo_year=lo_year, margin=margin,
                window=window, region=idx["region"].to_numpy(), rec=rec, final_year=fy,
                tmax=tmax, dates=d)


def record_counts(f: dict, reg: str | None, y0: int, y1: int) -> tuple[int, int]:
    rows = np.ones(len(f["idx"]), bool) if reg is None else f["region"] == reg
    w = f["window"][rows]
    hi = ((f["hi_year"][rows] >= y0) & (f["hi_year"][rows] <= y1) & w).sum()
    lo = ((f["lo_year"][rows] >= y0) & (f["lo_year"][rows] <= y1) & w).sum()
    return int(hi), int(lo)


def main() -> None:
    f = compute()
    hot, idx, fy = f["hot"], f["idx"], f["final_year"]

    print("1. Year of the all-time hottest day (stations; ties go to the first occurrence)")
    for reg in ("Europe", "North America", "Asia", "Oceania"):
        sub = hot[hot["region"] == reg]
        top = sub["year"].value_counts().head(6)
        print(f"   {reg:<14} n={len(sub):4d}  " + ", ".join(f"{y}: {c}" for y, c in top.items())
              + f"  | since 2000: {(sub['year'] >= 2000).mean():.0%}")
    eu = hot[(hot["region"] == "Europe") & (hot["year"] == fy)]
    print(f"   Europe, all-time hottest day in {fy}: {len(eu)} stations; most common dates: "
          + ", ".join(f"{k:%d %b}: {v}" for k, v in eu["date"].value_counts().head(4).items()))
    de = hot[hot["country"] == "Germany"]
    print(f"   Germany: {int((de['year'] == fy).sum())} of {len(de)} stations had their hottest day "
          f"ever in {fy}; on 27-28 Jun {fy}: "
          f"{int(de['date'].between(f'{fy}-06-27', f'{fy}-06-28').sum())}")

    print("\n2. Record highs vs record lows of the daily maximum (station-days, 1 Jan to latest data)")
    for reg in ("Europe", "North America", "Asia", "Oceania", None):
        for label, y0, y1 in (("2020s", 2020, fy), (str(fy), fy, fy)):
            nh, nl = record_counts(f, reg, y0, y1)
            print(f"   {reg or 'All':<14} {label:<6} highs {nh:6d}  lows {nl:5d}  ratio "
                  f"{(nh / nl if nl else float('inf')):.1f}:1")

    print("\n3. Share of station-days whose record is from the 2020s, by month")
    rec = f["rec"]
    tab = rec.assign(new=rec["record_year"] >= 2020).pivot_table(
        index="region", columns="month", values="new", aggfunc="mean")
    print((tab * 100).round(0).astype(int).to_string())

    print("\n4. Share of days with a 2020s record vs station elevation")
    for reg in ("Europe", "North America"):
        sub = idx[(idx["region"] == reg) & (idx["n_days"] >= 200)]
        bands = pd.cut(sub["elev"], [-50, 300, 800, 1500, 5000],
                       labels=["<300 m", "300-800 m", "800-1500 m", ">1500 m"])
        g = sub.groupby(bands, observed=True)["share"].agg(["count", "median"])
        rho = sub["elev"].rank().corr(sub["share"].rank())
        print(f"   {reg}: Spearman rho(elevation, share) = {rho:+.2f}")
        print("   " + g.round(3).to_string().replace("\n", "\n   "))

    print("\n5. Margin of the record over the best other year (degC), by the era of the record")
    for reg in ("Europe", "North America"):
        rows = f["region"] == reg
        out = []
        for y0, y1, label in ERAS:
            m = f["window"][rows] & (f["hi_year"][rows] >= y0) & (f["hi_year"][rows] <= y1) \
                & np.isfinite(f["margin"][rows])
            vals = f["margin"][rows][m]
            out.append(f"{label}: median {np.median(vals):.2f}, mean {vals.mean():.2f} (n={vals.size})")
        print(f"   {reg}: " + " | ".join(out))


def significance(f: dict, reg: str = "Europe", n_draw: int = 200_000, seed: int = 42) -> dict:
    """Stations agreeing, and a year-shuffle test of the 2020s heat/cold record ratio.

    Under a stable climate the years are exchangeable. Shuffling whole years keeps the
    spatial and day-to-day dependence, so the statistic for the years labelled 2020s is
    the ratio over a random set of the same number of years (drawn from 1900 on)."""
    fy = f["final_year"]
    rows = f["region"] == reg
    w = f["window"][rows]
    hi, lo, years = f["hi_year"][rows], f["lo_year"][rows], f["years"]
    h20, c20 = ((hi >= 2020) & w).sum(axis=1), ((lo >= 2020) & w).sum(axis=1)
    H = pd.Series(hi[w]).value_counts().reindex(years, fill_value=0)
    C = pd.Series(lo[w]).value_counts().reindex(years, fill_value=0)
    pool = years[(years >= 1900) & (years <= fy)]
    k = fy - 2020 + 1
    idx = np.argsort(np.random.default_rng(seed).random((n_draw, len(pool))), axis=1)[:, :k]
    ratio = H.loc[pool].to_numpy()[idx].sum(axis=1) / np.maximum(C.loc[pool].to_numpy()[idx].sum(axis=1), 1)
    obs = H.loc[2020:fy].sum() / C.loc[2020:fy].sum()
    return dict(n_stations=int(rows.sum()), more_heat=int((h20 > c20).sum()), no_cold=int((c20 == 0).sum()),
                heat=int(h20.sum()), cold=int(c20.sum()), observed=float(obs), null_median=float(np.median(ratio)),
                null_max=float(ratio.max()), n_draw=n_draw, n_exceed=int((ratio >= obs).sum()))


def best_window(f: dict, reg: str = "Europe", n_draw: int = 50_000, seed: int = 7) -> dict:
    """The 2020s ratio against the best contiguous window of the same length in shuffled years.

    Hausfather (2026, "How not to detect warming acceleration") shows that choosing a period
    by looking at the data and then testing it as if it had been fixed inflates false
    positives. Here the null takes the most extreme window anywhere in each shuffled record,
    so the test holds even if the 2020s had been picked for being extreme."""
    fy = f["final_year"]
    rows = f["region"] == reg
    w = f["window"][rows]
    pool = f["years"][(f["years"] >= 1900) & (f["years"] <= fy)]
    H = pd.Series(f["hi_year"][rows][w]).value_counts().reindex(pool, fill_value=0).to_numpy()
    C = pd.Series(f["lo_year"][rows][w]).value_counts().reindex(pool, fill_value=0).to_numpy()
    k = fy - 2020 + 1
    obs = H[-k:].sum() / C[-k:].sum()
    rng = np.random.default_rng(seed)
    best = np.empty(n_draw)
    for i in range(n_draw):
        order = rng.permutation(len(pool))
        h = np.convolve(H[order], np.ones(k), "valid")
        c = np.convolve(C[order], np.ones(k), "valid")
        best[i] = (h / np.maximum(c, 1)).max()
    return dict(observed=float(obs), null_max=float(best.max()), n_exceed=int((best >= obs).sum()), n_draw=n_draw)


def steady_warming(f: dict, reg: str = "Europe", runs: int = 300, seed: int = 3) -> dict:
    """Heat : cold ratio of 2020-latest if warming had gone on at its 1980-2019 rate.

    Ratios of record holders rise towards the present even without acceleration: later heat
    records overwrite earlier ones while early cold records survive. Synthetic stations carry
    the regional anomaly of daily TMAX (vs 1961-1990), smoothed to 2019 with its 1980-2019
    linear trend continued to the final year, plus year-to-year, region-wide daily and local
    daily noise sized from the data; their records give the ratio steady warming would produce."""
    fy = f["final_year"]
    rows = f["region"] == reg
    tx, d = f["tmax"][rows], f["dates"]
    yr, doy = np.asarray(d.year), np.asarray(d.dayofyear)
    base = (yr >= 1961) & (yr <= 1990)
    anom = np.empty_like(tx)
    for i in range(len(tx)):
        clim = pd.Series(tx[i, base]).groupby(doy[base]).mean().reindex(range(1, 367)).interpolate(limit_direction="both")
        anom[i] = tx[i] - clim.rolling(31, center=True, min_periods=1).mean().to_numpy()[doy - 1]
    frame = pd.DataFrame(anom.T, index=yr)
    annual = frame.groupby(level=0).mean().where(frame.groupby(level=0).count() >= 0.8 * 365)
    years = np.arange(1880, fy + 1)
    region = annual.mean(axis=1).reindex(years)
    b, a = np.polyfit(np.arange(1980, 2020), region.loc[1980:2019].to_numpy(), 1)
    year_sd = float(np.std(region.loc[1980:2019].to_numpy() - (a + b * np.arange(1980, 2020))))
    daily = anom - annual.reindex(yr).to_numpy().T
    shared_sd = float(np.nanstd(np.nanmean(daily, axis=0)[yr >= 1950]))
    local_sd = float(np.sqrt(max(np.nanstd(daily) ** 2 - shared_sd ** 2, 0.1)))
    smooth = region.loc[:1979].rolling(11, center=True, min_periods=4).mean().reindex(range(1880, 1980)).bfill()
    signal = np.concatenate([smooth.to_numpy(), a + b * np.arange(1980, fy + 1)])
    rng = np.random.default_rng(seed)
    out = np.empty(runs)
    for r in range(runs):
        x = ((signal + rng.normal(0, year_sd, len(years)))[None, None, :]
             + rng.normal(0, shared_sd, (365, len(years)))[None]
             + rng.normal(0, local_sd, (int(rows.sum()), 365, len(years)))).reshape(-1, len(years))
        hy, ly = years[x.argmax(axis=1)], years[x.argmin(axis=1)]
        out[r] = (hy >= 2020).sum() / max((ly >= 2020).sum(), 1)
    heat, cold = record_counts(f, reg, 2020, fy)
    return dict(trend=float(b * 10), median=float(np.median(out)), q95=float(np.percentile(out, 95)),
                observed=heat / cold, share=float(np.mean(out >= heat / cold)), runs=runs)


if __name__ == "__main__":
    main()
    sig = significance(compute())
    print("\n6. Significance, Europe 2020s: "
          f"{sig['more_heat']} of {sig['n_stations']} stations have more heat than cold records "
          f"({sig['no_cold']} have none of the latter); ratio {sig['observed']:.1f} vs random 7-year sets: "
          f"median {sig['null_median']:.2f}, max {sig['null_max']:.2f}; {sig['n_exceed']} of {sig['n_draw']:,} "
          f"random sets reach it (p < {max(sig['n_exceed'], 1) / sig['n_draw']:.0e})")
    f = compute()
    bw = best_window(f)
    print(f"\n7. The same, against the most extreme {f['final_year'] - 2019}-year window anywhere in each "
          f"shuffled record: max {bw['null_max']:.1f}; {bw['n_exceed']} of {bw['n_draw']:,} reach "
          f"{bw['observed']:.1f} (p < {max(bw['n_exceed'], 1) / bw['n_draw']:.0e})")
    sw = steady_warming(f)
    print(f"\n8. Steady warming at the 1980-2019 rate ({sw['trend']:.2f} C/decade) would give a 2020s ratio of "
          f"{sw['median']:.1f} (95th percentile {sw['q95']:.1f}) against {sw['observed']:.1f} observed; "
          f"{sw['share']:.1%} of {sw['runs']} synthetic runs reach it")
