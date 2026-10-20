"""Drought at Europe's long-record stations: record-dry growing seasons, with and without heat.

Every European station of the record set gets two totals for the growing season (March to
August) of each year:

    rain           precipitation (PRCP)
    water balance  precipitation minus potential evaporation; the evaporation follows
                   Hargreaves & Samani (1985) from daily TMAX and TMIN and the
                   top-of-atmosphere radiation of the station's latitude (FAO-56)

A season counts when >= 95 % of its days have precipitation (rain) or >= 90 % have
precipitation and both temperatures (water balance); the mean of the valid days is scaled
to the 184 days of the season. GHCN-Daily values with a quality flag are dropped.

A station's record-dry season is its lowest total, its record-wet season the highest; ties
go to the first year. In a stable climate every complete season is equally likely to hold a
record, so a station with n seasons, k of them in a period, expects k / n records there.

    outputs/drought_log.txt         the numbers (printed)
    outputs/drought_seasons.csv     station x year: rain, evaporation, water balance (mm)

Run with `python -I src/drought.py > outputs/drought_log.txt`.
"""

from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from build_tmax import DATE0, DLY, N_DAYS, parse_dly  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
INDEX = OUT / "stations" / "station_index.csv"
MONTHS = (3, 4, 5, 6, 7, 8)
SEASON = "Mar–Aug"
RAIN_FRAC, BALANCE_FRAC = 0.95, 0.90
PERIODS = [("before 1990", 0, 1989), ("1990s", 1990, 1999), ("2000s", 2000, 2009), ("2010s", 2010, 2019),
           ("2020s", 2020, 9999)]

DATES = DATE0 + np.arange(N_DAYS).astype("timedelta64[D]")
_D = pd.DatetimeIndex(DATES)
YEAR, MONTH, DOY = _D.year.to_numpy(), _D.month.to_numpy(), _D.dayofyear.to_numpy()
IN_SEASON = np.isin(MONTH, MONTHS)
SEASON_DAYS = sum(pd.Timestamp(2001, m, 1).days_in_month for m in MONTHS)


def radiation_mm(lat: float, doy: np.ndarray) -> np.ndarray:
    """Top-of-atmosphere radiation as evaporation equivalent (mm/day), FAO-56 eq. 21."""
    phi = np.radians(lat)
    dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)
    dec = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(dec), -1, 1))
    ra = 24 * 60 / np.pi * 0.0820 * dr * (ws * np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.sin(ws))
    return 0.408 * ra


def _series(path: Path, element: bytes) -> np.ndarray:
    out = np.full(N_DAYS, np.nan, np.float32)
    i, v = parse_dly(path, element)
    out[i] = v / 10
    return out


def station_seasons(args) -> pd.DataFrame:
    """Rain, evaporation and water balance of every growing season of one station."""
    sid, lat = args
    path = DLY / f"{sid}.dly"
    p, tx, tn = (_series(path, e) for e in (b"PRCP", b"TMAX", b"TMIN"))
    p[p < 0] = np.nan
    tmean, span = (tx + tn) / 2, np.clip(tx - tn, 0, None)
    pet = 0.0023 * radiation_mm(lat, DOY) * (tmean + 17.8) * np.sqrt(span)
    both = np.isfinite(p) & np.isfinite(pet)
    df = pd.DataFrame({"year": YEAR, "p": p, "pet": np.where(both, pet, np.nan),
                       "pb": np.where(both, p, np.nan)})[IN_SEASON]
    g = df.groupby("year")
    n_p, n_b = g["p"].count(), g["pb"].count()
    out = pd.DataFrame({
        "rain": (g["p"].mean() * SEASON_DAYS).where(n_p >= RAIN_FRAC * SEASON_DAYS),
        "evaporation": (g["pet"].mean() * SEASON_DAYS).where(n_b >= BALANCE_FRAC * SEASON_DAYS),
    })
    out["balance"] = ((g["pb"].mean() - g["pet"].mean()) * SEASON_DAYS).where(n_b >= BALANCE_FRAC * SEASON_DAYS)
    out = out.dropna(how="all").reset_index()
    out.insert(0, "id", sid)
    return out


def records(seasons: pd.DataFrame, var: str, min_seasons: int = 50) -> pd.DataFrame:
    """Per station: number of seasons, years of the record-dry and record-wet season, and the
    rank of every season (1 = driest)."""
    rows = []
    for sid, g in seasons.dropna(subset=[var]).groupby("id"):
        s = g.set_index("year")[var]
        if len(s) < min_seasons:
            continue
        rows.append(dict(id=sid, n=len(s), dry_year=int(s.idxmin()), wet_year=int(s.idxmax()),
                         years=tuple(s.index), rank=s.rank(method="min").astype(int).to_dict()))
    return pd.DataFrame(rows).set_index("id")


def period_counts(rec: pd.DataFrame, y0: int, y1: int) -> tuple[int, int, float]:
    """Record-dry and record-wet seasons in [y0, y1], and the number expected in a stable climate."""
    k = rec["years"].map(lambda ys: sum(y0 <= y <= y1 for y in ys))
    return (int(rec["dry_year"].between(y0, y1).sum()), int(rec["wet_year"].between(y0, y1).sum()),
            float((k / rec["n"]).sum()))


def significance(rec: pd.DataFrame, y0: int, y1: int, n_draw: int = 200_000, seed: int = 42) -> dict:
    """Year-shuffle test as in findings.significance: record-dry seasons in [y0, y1] against
    random sets of the same number of years since 1900 (keeps the dependence between stations)."""
    last = max(max(ys) for ys in rec["years"])
    years = np.arange(1900, last + 1)
    dry = rec["dry_year"].value_counts().reindex(years, fill_value=0).to_numpy()
    k = min(y1, last) - y0 + 1
    pick = np.argsort(np.random.default_rng(seed).random((n_draw, len(years))), axis=1)[:, :k]
    null = dry[pick].sum(axis=1)
    obs = int(dry[(years >= y0) & (years <= y1)].sum())
    # the most extreme k-year window anywhere in a shuffled record: holds even if the window had
    # been chosen for being extreme (findings.best_window)
    rng = np.random.default_rng(seed + 1)
    best = np.array([np.convolve(dry[rng.permutation(len(years))], np.ones(k), "valid").max()
                     for _ in range(n_draw // 4)])
    return dict(observed=obs, null_median=float(np.median(null)), null_max=int(null.max()),
                n_exceed=int((null >= obs).sum()), n_draw=n_draw,
                n_exceed_window=int((best >= obs).sum()), n_window=len(best))


def compute() -> dict:
    idx = pd.read_csv(INDEX).set_index("id")
    eu = idx[idx["region"] == "Europe"]
    with ProcessPoolExecutor(max_workers=12) as pool:
        seasons = pd.concat(pool.map(station_seasons, zip(eu.index, eu["lat"]), chunksize=4), ignore_index=True)
    return dict(idx=eu, seasons=seasons, rain=records(seasons, "rain"), balance=records(seasons, "balance"))


def main() -> None:
    d = compute()
    seasons, rain, bal, idx = d["seasons"], d["rain"], d["balance"], d["idx"]
    seasons.round(1).to_csv(OUT / "drought_seasons.csv", index=False)
    last = int(seasons["year"].max())

    print(f"Growing season {SEASON}; stations with >= 50 complete seasons: rain {len(rain)}, "
          f"water balance {len(bal)} (of {len(idx)} European stations)")
    m = seasons[seasons["year"].between(1991, 2020)]
    print(f"   median 1991-2020 season: rain {m['rain'].median():.0f} mm, evaporation "
          f"{m['evaporation'].median():.0f} mm, water balance {m['balance'].median():.0f} mm")

    for name, rec in (("rain", rain), ("water balance", bal)):
        n20 = int(rec["years"].map(lambda ys: any(y >= 2020 for y in ys)).sum())
        print(f"   {name}: {n20} stations with a complete 2020s season")
    with20 = bal.index[bal["years"].map(lambda ys: any(y >= 2020 for y in ys))]
    nd, _, _ = period_counts(rain.loc[rain.index.intersection(with20)], 2020, 9999)
    print(f"   rain alone on the {len(with20)} stations with a 2020s water balance: {nd} record-dry 2020s seasons")

    print("\n1. Record-dry vs record-wet seasons by period (expected = each, in a stable climate)")
    for label, y0, y1 in PERIODS:
        out = []
        for name, rec in (("rain", rain), ("water balance", bal)):
            nd, nw, exp = period_counts(rec, y0, y1)
            out.append(f"{name}: dry {nd:3d} wet {nw:3d} expected {exp:5.1f}")
        print(f"   {label:<12} " + " | ".join(out))

    print(f"\n2. {last}: stations with a complete {SEASON} {last} and it was their driest on record")
    for name, rec in (("rain", rain), ("water balance", bal)):
        has = rec[rec["years"].map(lambda ys: last in ys)]
        top = has[has["dry_year"] == last]
        top3 = int(has["rank"].map(lambda r: r[last] <= 3).sum())
        print(f"   {name:<14} {len(top)} of {len(has)} (top 3: {top3}): "
              + ", ".join(idx.loc[top.index, "name"].str.title()))

    print("\n3. Stations whose driest season is in the 2020s, by rank of their driest 2020s season")
    for name, rec in (("rain", rain), ("water balance", bal)):
        best = rec["rank"].map(lambda r: min([v for y, v in r.items() if y >= 2020], default=np.nan))
        bands = pd.cut(best, [0, 1, 3, 10, 10_000], labels=["record", "2-3", "4-10", ">10"])
        print(f"   {name:<14} " + "  ".join(f"{k}: {v}" for k, v in bands.value_counts().sort_index().items()))

    print("\n4. Significance, 2020s record-dry seasons, year-shuffle test (random 7-year sets since 1900)")
    for name, rec in (("rain", rain), ("water balance", bal)):
        s = significance(rec, 2020, last)
        print(f"   {name:<14} observed {s['observed']}, random sets: median {s['null_median']:.0f}, max {s['null_max']}; "
              f"{s['n_exceed']} of {s['n_draw']:,} reach it (p < {max(s['n_exceed'], 1) / s['n_draw']:.0e}); "
              f"against the most extreme window anywhere: p = {(s['n_exceed_window'] + 1) / (s['n_window'] + 1):.2f}")


if __name__ == "__main__":
    main()
