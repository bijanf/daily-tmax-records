"""Warmest month on record, station by station: the monthly view of the daily records.

For every calendar month up to the station's latest data: the average of the
daily maximum temperatures of that month in each year, and the year with the
highest average (ties go to the earliest year). A month counts for a year only if
at least 80 % of its days have data. The current, unfinished month is compared on
the same days in every year (e.g. 1-17 October), so the comparison stays fair.

One 1080 x 1350 image per station:
    outputs/stations_monthly/<region>/<country>/<ID>_<name>_monthly.png

    python -I src/plot_monthly.py --ids GM000003319 GM000003342
    python -I src/plot_monthly.py --region Europe
"""

from __future__ import annotations

import argparse
import calendar
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import station_records as sr  # noqa: E402
import viz  # noqa: E402
from plot_stations import country_label, display_name, ghcnd_version, slug  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "stations_monthly"
MIN_FRAC = 0.8


def monthly_records(t: np.ndarray, dates: pd.DatetimeIndex, end: pd.Timestamp) -> pd.DataFrame:
    """One row per calendar month up to `end`: record mean TMAX, its year, and context."""
    s = pd.Series(t, index=dates)
    s = s[s.index.year <= end.year]
    rows = []
    for m in range(1, end.month + 1):
        partial = m == end.month and end.day < calendar.monthrange(end.year, m)[1]
        sub = s[(s.index.month == m) & ((s.index.day <= end.day) if partial else True)]
        g = sub.groupby(sub.index.year)
        need = pd.Series({y: MIN_FRAC * (end.day if partial else calendar.monthrange(y, m)[1])
                          for y in g.groups})
        means = g.mean()[g.count() >= need]
        if means.empty:
            continue
        best = means.max()
        year = int(means.index[means == best].min())
        rows.append({
            "month": m, "partial_to": end.day if partial else None,
            "record_c": round(float(best), 2), "record_year": year,
            "n_years": len(means), "n_since_2000": int((means.index >= 2000).sum()),
            "final_year_c": float(means.get(end.year, np.nan)),
        })
    return pd.DataFrame(rows)


def plot(meta: dict, rec: pd.DataFrame, version: str, path: Path) -> None:
    fy = int(meta["final_year"])
    viz.set_final_year(fy)
    name, country = display_name(meta), country_label(meta["country"])
    k = int((rec["record_year"] >= 2000).sum())
    expected = float((rec["n_since_2000"] / rec["n_years"]).sum())
    first = meta["first_date"][:4]

    fig = viz.new_slide()
    fig.text(0.5, 0.955, name, fontsize=34, fontweight="bold", color=viz.ACC, ha="center", va="top")
    fig.text(0.5, 0.885, f"{k} of {len(rec)} months: warmest on record since 2000",
             fontsize=15, fontweight="bold", color=viz.TEXT, ha="center", va="top")
    fig.text(0.5, 0.838,
             f"{country} · warmest month on record by average daily maximum temperature, "
             f"{first}–{fy}\nbar = record monthly average · label = year it was set · "
             f"a stable climate would give about {expected:.1f} of {len(rec)}",
             fontsize=8.8, color=viz.SUB, ha="center", va="top", linespacing=1.45)

    ax = fig.add_axes([0.12, 0.15, 0.84, 0.57])
    x = np.arange(len(rec))
    h = rec["record_c"].to_numpy(dtype=float)
    lo, hi = viz.nice_ylim(h, 0.10)
    ax.set_xlim(-0.6, len(rec) - 0.4)
    ax.set_ylim(lo, hi)
    viz.style_axes(ax)
    viz.round_top_bars(ax, x, h, [viz.era_colour(y) for y in rec["record_year"]], width=0.66, radius_px=6)
    for xi, hv, yr in zip(x, h, rec["record_year"]):
        recent = yr >= 2020
        ax.text(xi, max(hv, 0) + (hi - lo) * 0.012, str(yr), ha="center", va="bottom", fontsize=11,
                color=viz.TEXT if recent else viz.SUB, fontweight="bold" if recent else "normal")
    ticks = [calendar.month_abbr[m] if pd.isna(p) else f"{calendar.month_abbr[m]}\n1–{int(p)}"
             for m, p in zip(rec["month"], rec["partial_to"])]
    ax.set_xticks(x)
    ax.set_xticklabels(ticks, fontsize=9)
    ax.tick_params(axis="y", labelsize=8.5)
    ax.set_ylabel("Record average daily maximum temperature of the month (°C)", fontsize=8.5, labelpad=8)
    fig.canvas.draw()
    viz.era_legend(fig, 0.5, 0.752, fontsize=7.5, ha="center", swatch=0.018, gap=0.022)

    notes = []
    if rec["partial_to"].notna().any():
        p = rec[rec["partial_to"].notna()].iloc[0]
        notes.append(f"{calendar.month_name[int(p['month'])]}: every year compared on days "
                     f"1–{int(p['partial_to'])} because {fy} is not over yet")
    notes.append("months need ≥80% of days with data · ties go to the earliest year")
    src = meta.get("supplement_source") if isinstance(meta.get("supplement_source"), str) else ""
    source = f"Data: NOAA NCEI GHCN-Daily v{version}{' + ' + src if src else ''} · station {meta['id']}"
    viz.slide_footer(fig, "", "", source, " · ".join(notes))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=viz.IG_DPI)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region")
    ap.add_argument("--ids", nargs="+")
    args = ap.parse_args()

    idx = pd.read_csv(sr.OUT / "station_index.csv", keep_default_na=False, na_values=[""])
    if args.region:
        idx = idx[idx["region"].str.lower() == args.region.lower()]
    if args.ids:
        idx = idx[idx["id"].isin(args.ids)]
    st, tmax, dates = sr.load()
    sr.qc_outliers(tmax, dates)
    dates = pd.to_datetime(dates)
    rows = {sid: i for i, sid in enumerate(st.index)}
    version = ghcnd_version()
    summary = []
    for _, m in idx.iterrows():
        meta = m.to_dict()
        end = pd.Timestamp(f"{meta['final_year']}-{meta['end_md']}") if meta["has_final_year"] \
            else pd.Timestamp(meta["last_date"])
        rec = monthly_records(tmax[rows[meta["id"]]], dates, end)
        path = OUT / slug(meta["region"]) / slug(country_label(meta["country"])) / \
            f"{meta['id']}_{slug(meta['name'])}_monthly.png"
        plot(meta, rec, version, path)
        summary.append({"id": meta["id"], "name": meta["name"],
                        **{calendar.month_abbr[int(r.month)]: f"{r.record_year} ({r.record_c:.1f})"
                           for r in rec.itertuples()}})
        print(path)
    print(pd.DataFrame(summary).to_string(index=False))


if __name__ == "__main__":
    main()
