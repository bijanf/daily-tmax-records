"""Network-mean daily TMAX anomaly and the record year of every calendar day.

Station selection: >= 100 complete years of TMAX (>= 80 % of days valid) and
still reporting this year. Each station's anomaly is taken against its own
1961-1990 seasonal cycle (3 harmonics); values beyond 6 sigma of the local
day-of-year spread are dropped as likely errors. Anomalies are averaged in
5 x 5 degree cells and cells are combined with cos(latitude) weights, so the
dense US network does not outvote the rest of the world station by station.
Latest reports arrive with a lag (European stations by weeks), so every year is
compared on the footprint of cells that have reported for that calendar day
this year; a year enters the competition only if cells holding at least 70 % of that
footprint's area weight reported, and the x-axis ends on the last day of this year whose
footprint holds at least 70 % of the whole network's weight.

Writes data/cache/network_daily.csv and, in outputs/, records_by_day.csv,
anomaly_by_year_and_day.csv, stations_used.csv and summary.csv, then prints a
summary plus robustness variants. Run with `python -I src/composite.py`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
OUT = ROOT / "outputs"

MISSING = -32768
DATE0 = np.datetime64("1800-01-01")
FINAL_YEAR = date.today().year


@dataclass(frozen=True)
class Config:
    min_complete_years: int = 100
    min_frac_final_year: float = 0.5
    base: tuple[int, int] = (1961, 1990)
    min_base_days: int = 15 * 292
    n_harm: int = 3
    qc_sigma: float = 6.0
    cell_deg: float = 5.0
    grid: bool = True
    min_cover: float = 0.7
    match_final_footprint: bool = True


def load(cfg: Config):
    st = pd.read_csv(CACHE / "stations.csv", index_col="id")
    keep = (st["n_complete_years"] >= cfg.min_complete_years) & (
        st["n_days_final_year"] >= cfg.min_frac_final_year * days_so_far()
    )
    st = st[keep].copy()
    raw = np.load(CACHE / "tmax_int16.npy", mmap_mode="r")
    tmax = raw[st["row"].to_numpy()].astype(np.float32)
    tmax[tmax == MISSING] = np.nan
    tmax /= 10.0
    dates = DATE0 + np.arange(tmax.shape[1])
    return st, tmax, dates


def days_so_far() -> int:
    return (date.today() - date(FINAL_YEAR, 1, 1)).days


def ghcnd_version() -> str:
    m = re.search(r"is (\d+\.\d+)", (ROOT / "data" / "raw" / "ghcnd-version.txt").read_text())
    return m.group(1) if m else ""


def harmonics(dates: np.ndarray, n_harm: int) -> np.ndarray:
    years = dates.astype("datetime64[Y]")
    doy = (dates - years.astype("datetime64[D]")).astype(int)
    ndays = ((years + 1).astype("datetime64[D]") - years.astype("datetime64[D]")).astype(int)
    phase = 2 * np.pi * (doy + 0.5) / ndays
    cols = [np.ones_like(phase)]
    for k in range(1, n_harm + 1):
        cols += [np.cos(k * phase), np.sin(k * phase)]
    return np.stack(cols, axis=1).astype(np.float32)


def anomalies(st: pd.DataFrame, tmax: np.ndarray, dates: np.ndarray, cfg: Config):
    """Anomaly vs the station's own baseline seasonal cycle, with a sigma QC."""
    X = harmonics(dates, cfg.n_harm)
    years = dates.astype("datetime64[Y]").astype(int) + 1970
    in_base = (years >= cfg.base[0]) & (years <= cfg.base[1])
    anom = np.full_like(tmax, np.nan)
    ok = np.zeros(len(st), bool)
    n_qc = 0
    for i in range(len(st)):
        y = tmax[i]
        m = in_base & np.isfinite(y)
        if m.sum() < cfg.min_base_days:
            continue
        beta, *_ = np.linalg.lstsq(X[m], y[m], rcond=None)
        clim = X @ beta
        r = y - clim
        gam, *_ = np.linalg.lstsq(X[m], r[m] ** 2, rcond=None)
        sd = np.sqrt(np.clip(X @ gam, 0.25, None))
        bad = np.abs(r) > cfg.qc_sigma * sd
        n_qc += int(bad.sum())
        r[bad] = np.nan
        anom[i] = r
        ok[i] = True
    return anom[ok], st[ok].copy(), n_qc


def cell_means(st: pd.DataFrame, anom: np.ndarray, cfg: Config):
    """Mean anomaly per grid cell and day, plus each cell's area weight."""
    if cfg.grid:
        ilat = np.floor((st["lat"].to_numpy() + 90) / cfg.cell_deg).astype(int)
        ilon = np.floor((st["lon"].to_numpy() + 180) / cfg.cell_deg).astype(int)
        cell = ilat * 1000 + ilon
        lat_c = -90 + (ilat + 0.5) * cfg.cell_deg
    else:
        cell = np.arange(len(st))
        lat_c = np.zeros(len(st))
    order = np.argsort(cell, kind="stable")
    cell_sorted = cell[order]
    starts = np.flatnonzero(np.r_[True, cell_sorted[1:] != cell_sorted[:-1]])
    a = anom[order]
    valid = np.isfinite(a)
    sums = np.add.reduceat(np.where(valid, a, 0.0), starts, axis=0)
    cnts = np.add.reduceat(valid, starts, axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        cmean = np.where(cnts > 0, sums / cnts, np.nan)
    w = np.cos(np.deg2rad(lat_c[order][starts]))
    return cmean, w


def weighted_mean(values: np.ndarray, w: np.ndarray):
    """Area-weighted mean over axis 0 ignoring NaN; returns (mean, weight fraction present)."""
    has = np.isfinite(values)
    wsum = (w[:, None] * has).sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = (np.where(has, values, 0.0) * w[:, None]).sum(axis=0) / wsum
    return mean, wsum / w.sum()


def calendar_records(dates, cmean, w, cfg: Config):
    """Record value/year for each calendar day of FINAL_YEAR up to its last covered day."""
    d = pd.to_datetime(dates)
    keep = ~((d.month == 2) & (d.day == 29))
    years_all = np.asarray(d.year)
    md_all = np.asarray(d.strftime("%m-%d"))
    fin = keep & (years_all == FINAL_YEAR)
    fin_idx = np.flatnonzero(fin)
    avail_fin = np.isfinite(cmean[:, fin_idx])
    cover_fin = (w[:, None] * avail_fin).sum(axis=0) / w.sum()
    ok = np.flatnonzero(cover_fin >= cfg.min_cover)
    n_md = ok.max() + 1
    mds = md_all[fin_idx[:n_md]]

    years = np.arange(years_all[np.isfinite(cmean).any(axis=0)].min(), FINAL_YEAR + 1)
    lookup = pd.Series(np.arange(len(dates)), index=pd.MultiIndex.from_arrays([years_all, md_all]))
    idx = np.full((len(years), n_md), -1)
    for i, y in enumerate(years):
        hit = lookup.reindex(pd.MultiIndex.from_product([[y], mds]))
        idx[i] = hit.fillna(-1).to_numpy(int)

    vals = np.full((len(years), n_md), np.nan)
    foot_cover = np.ones(n_md)
    for j in range(n_md):
        foot = np.ones(len(w), bool)
        if cfg.match_final_footprint and cover_fin[j] >= cfg.min_cover:
            foot = avail_fin[:, j]
        foot_cover[j] = w[foot].sum() / w.sum()
        cols = idx[:, j]
        v = np.where(cols[None, :] >= 0, cmean[np.ix_(foot, np.clip(cols, 0, None))], np.nan)
        mean, cover = weighted_mean(v, w[foot])
        vals[:, j] = np.where(cover >= cfg.min_cover, mean, np.nan)
    if not cfg.match_final_footprint:
        fin_mean, _ = weighted_mean(cmean[:, fin_idx[:n_md]], w)
        vals[-1] = np.where(cover_fin[:n_md] >= cfg.min_cover, fin_mean, np.nan)

    filled = np.where(np.isfinite(vals), vals, -np.inf)
    order = np.argsort(-filled, axis=0, kind="stable")
    cols = np.arange(n_md)
    final_vals = vals[-1]
    rank = (vals > final_vals[None, :]).sum(axis=0) + 1.0
    rec = pd.DataFrame(
        {
            "md": mds,
            "record_year": years[order[0]],
            "record_anom": filled[order[0], cols],
            "second_year": years[order[1]],
            "second_anom": filled[order[1], cols],
            "value_final_year": final_vals,
            "rank_final_year": np.where(np.isfinite(final_vals), rank, np.nan),
            "n_years": np.isfinite(vals).sum(axis=0),
            "footprint_cover": foot_cover,
        }
    )
    rec["date"] = pd.to_datetime(f"{FINAL_YEAR}-" + rec["md"])
    first_year = int(years[np.isfinite(vals).any(axis=1)].min())
    table = pd.DataFrame(vals, index=years, columns=mds)
    return rec, table, first_year


def run(cfg: Config, verbose: bool = False):
    st, tmax, dates = load(cfg)
    anom, st, n_qc = anomalies(st, tmax, dates, cfg)
    del tmax
    cmean, w = cell_means(st, anom, cfg)
    rec, table, first_year = calendar_records(dates, cmean, w, cfg)
    info = dict(n_stations=len(st), n_cells=len(w), n_qc=n_qc, first_year=first_year,
                last_md=rec["md"].iloc[-1])
    if verbose:
        mean, cover = weighted_mean(cmean, w)
        net = pd.DataFrame(
            {"date": dates.astype(str), "anom": mean, "cover": cover,
             "n_cells": np.isfinite(cmean).sum(axis=0),
             "n_stations": np.isfinite(anom).sum(axis=0)}
        )
        return rec, table, info, st, net
    return rec, table, info


EUROPE = {
    "Germany", "Sweden", "United Kingdom", "Estonia", "France", "Austria", "Netherlands",
    "Spain", "Romania", "Switzerland", "Ukraine", "Hungary", "Belgium",
    "Bosnia and Herzegovina", "Ireland", "Finland", "Norway", "Slovakia", "Portugal",
}


def region(country: str, lon: float) -> str:
    if country.startswith("United States") or country.startswith("Puerto Rico"):
        return "United States"
    if country in ("Canada", "Greenland [Denmark]"):
        return "Canada & Greenland"
    if country in EUROPE or (country == "Russia" and lon < 60):
        return "Europe"
    if country == "Australia":
        return "Australia"
    return "Asia"


def region_weight_shares(st: pd.DataFrame, cfg: Config) -> pd.Series:
    """Share of the network's area weight held by each region (cells by majority region)."""
    ilat = np.floor((st["lat"] + 90) / cfg.cell_deg).astype(int)
    ilon = np.floor((st["lon"] + 180) / cfg.cell_deg).astype(int)
    df = pd.DataFrame({
        "cell": ilat * 1000 + ilon,
        "lat_c": -90 + (ilat + 0.5) * cfg.cell_deg,
        "region": [region(c, lo) for c, lo in zip(st["country"], st["lon"])],
    })
    cells = df.groupby("cell").agg(region=("region", lambda r: r.mode()[0]), lat_c=("lat_c", "first"))
    cells["w"] = np.cos(np.deg2rad(cells["lat_c"]))
    return (cells.groupby("region")["w"].sum() / cells["w"].sum()).sort_values(ascending=False)


def expected_count(table: pd.DataFrame, start_year: int) -> float:
    """Records expected from years >= start_year if every competing year were equally likely."""
    competing = table.notna()
    return float((competing.loc[start_year:].sum() / competing.sum()).sum())


def summarise(rec: pd.DataFrame, table: pd.DataFrame, first_year: int) -> str:
    n = len(rec)
    n_years = FINAL_YEAR - first_year + 1
    counts = rec["record_year"].value_counts()
    lines = [
        f"{n} calendar days ({rec['md'].iloc[0]} .. {rec['md'].iloc[-1]}), "
        f"years {first_year}-{FINAL_YEAR} ({n_years} candidates; "
        f"{n / n_years:.1f} records per year expected if climate were stable)",
        "top record years: " + ", ".join(f"{y}: {c}" for y, c in counts.head(10).items()),
    ]
    for start in (2000, 2010, 2016, 2020):
        k = int((rec["record_year"] >= start).sum())
        exp = expected_count(table, start)
        lines.append(f"records since {start}: {k}/{n} ({100 * k / n:.0f} %; expected {exp:.1f})")
    k = int((rec["record_year"] < 1950).sum())
    lines.append(f"records before 1950: {k}/{n}")
    lines.append(f"{FINAL_YEAR} holds {int((rec['record_year'] == FINAL_YEAR).sum())} records; "
                 f"median rank of {FINAL_YEAR}: {rec['rank_final_year'].median():.0f}")
    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    cfg = Config()
    rec, table, info, st, net = run(cfg, verbose=True)
    print(info)
    print(st["country"].value_counts().to_string())
    print(summarise(rec, table, info["first_year"]))
    shares = region_weight_shares(st, cfg)
    print("area-weight share by region:", shares.round(3).to_dict())
    for start in (2000, 2020):
        info[f"since_{start}"] = int((rec["record_year"] >= start).sum())
        info[f"expected_since_{start}"] = round(expected_count(table, start), 2)
    info["n_countries"] = st["country"].nunique()
    info["final_year"] = FINAL_YEAR
    info["ghcnd_version"] = ghcnd_version()
    info.update({f"share_{k}": round(v, 3) for k, v in shares.items()})
    rec.to_csv(OUT / "records_by_day.csv", index=False, float_format="%.3f")
    net.to_csv(CACHE / "network_daily.csv", index=False, float_format="%.4f")
    table.to_csv(OUT / "anomaly_by_year_and_day.csv", float_format="%.3f")
    st.to_csv(OUT / "stations_used.csv")
    pd.Series(info, name="value").rename_axis("key").to_csv(OUT / "summary.csv")

    variants = {
        "station mean (no grid)": replace(cfg, grid=False),
        "10 deg cells": replace(cfg, cell_deg=10.0),
        "cover >= 0.8": replace(cfg, min_cover=0.8),
        "cover >= 0.6": replace(cfg, min_cover=0.6),
        "baseline 1991-2020": replace(cfg, base=(1991, 2020)),
        "QC 5 sigma": replace(cfg, qc_sigma=5.0),
        "full network (no footprint matching)": replace(cfg, match_final_footprint=False),
    }
    for name, vcfg in variants.items():
        vrec, vtable, vinfo = run(vcfg)
        main_years = rec.set_index("md")["record_year"]
        same = (vrec.set_index("md")["record_year"].reindex(main_years.index) == main_years).mean()
        print(f"\n--- {name}: {vinfo}; same record year on {100 * same:.0f} % of days")
        print(summarise(vrec, vtable, vinfo["first_year"]))


if __name__ == "__main__":
    main()
