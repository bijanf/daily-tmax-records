"""Three high-impact figures (2160 x 2700 px) built from the same data as findings.py.

    outputs/impact/A_<station>_heat_carpet.png        every day since the first year, one row
                                                       per year; white dots = standing daily records
    outputs/impact/B_europe_hot_vs_cold_by_decade.png  record-hot / record-cold days by decade
    outputs/impact/C_<station>_hottest_day_each_year.png  annual maximum and the all-time record

    python -I src/plot_impact.py                 # Potsdam
    python -I src/plot_impact.py --id GM000003319
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

import findings  # noqa: E402
import viz  # noqa: E402
from plot_findings import COLD, DPI, HOT, SIZE, footer, header  # noqa: E402
from plot_stations import display_name, ghcnd_version, slug  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "impact"
EMBER = LinearSegmentedColormap.from_list("ember", [
    (0.00, "#3A84DC"), (0.30, "#1D3B5E"), (0.47, "#161C24"), (0.53, "#161C24"),
    (0.70, "#8C1C24"), (0.84, "#E9365A"), (0.94, "#FF8A3D"), (1.00, "#FFE29A")])


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=DPI)
    plt.close(fig)
    print(OUT / name)


def station_series(f, sid):
    row = list(f["idx"].index).index(sid)
    return pd.Series(f["tmax"][row], index=f["dates"]).dropna()


def anomalies(s: pd.Series) -> pd.Series:
    """Daily maximum minus the station's own 1961-1990 seasonal cycle (3 harmonics)."""
    doy = s.index.dayofyear.to_numpy()
    ndays = np.where(s.index.is_leap_year, 366, 365)
    ph = 2 * np.pi * (doy - 0.5) / ndays
    X = np.column_stack([np.ones_like(ph)] + [g(k * ph) for k in (1, 2, 3) for g in (np.cos, np.sin)])
    base = (s.index.year >= 1961) & (s.index.year <= 1990)
    beta, *_ = np.linalg.lstsq(X[base], s.to_numpy()[base], rcond=None)
    return s - X @ beta


def heat_carpet(f, sid, source):
    meta = f["idx"].loc[sid]
    name = display_name({"id": sid, "name": meta["name"], "country": meta["country"], "state": meta["state"]})
    raw = anomalies(station_series(f, sid))
    a = raw.asfreq("D").rolling(31, center=True, min_periods=20).mean().reindex(raw.index)
    a = a[~((a.index.month == 2) & (a.index.day == 29))]
    md = a.index.strftime("%m-%d")
    cols = pd.Series(np.arange(365), index=pd.date_range("2001-01-01", "2001-12-31").strftime("%m-%d"))
    years = np.arange(a.index.year.min(), f["final_year"] + 1)
    grid = np.full((len(years), 365), np.nan)
    grid[a.index.year - years[0], cols.loc[md].to_numpy()] = a.to_numpy()
    rec = f["rec"][f["rec"]["id"] == sid]

    fig = plt.figure(figsize=SIZE, dpi=DPI)
    header(fig, f"Every day since {years[0]}",
           f"{name}: daily maximum temperature, one row per year.\nThe heat is piling up at the bottom",
           f"Each pixel is one day: the 31-day average of the daily maximum, compared with the "
           f"{name} normal of 1961–1990.\nWhite dots: for each day of the year so far, the year that "
           f"still holds its heat record")
    ax = fig.add_axes([0.11, 0.075, 0.86, 0.69])
    im = ax.imshow(grid, aspect="auto", cmap=EMBER, vmin=-5, vmax=5, interpolation="nearest",
                   extent=(-0.5, 364.5, years[-1] + 0.5, years[0] - 0.5))
    ax.scatter(cols.loc[rec["md"]].to_numpy(), rec["record_year"].to_numpy(), s=5.5, color="white",
               edgecolor="#0F1419", linewidth=0.35, zorder=3)
    starts = pd.date_range("2001-01-01", periods=12, freq="MS")
    ax.set_xticks([cols[d.strftime("%m-%d")] for d in starts])
    ax.set_xticklabels([d.strftime("%b") for d in starts], fontsize=7.5)
    yt = [y for y in range(1900, years[-1], 20) if y >= years[0]] + [years[-1]]
    ax.set_yticks(yt)
    ax.set_yticklabels(yt, fontsize=7.5)
    for side in ax.spines.values():
        side.set_visible(False)
    ax.tick_params(length=0, pad=4)
    cax = fig.add_axes([0.30, 0.788, 0.48, 0.010])
    cb = fig.colorbar(im, cax=cax, orientation="horizontal", extend="both")
    cb.outline.set_visible(False)
    cb.set_ticks([-4, -2, 0, 2, 4])
    cb.set_ticklabels(["−4", "−2", "0", "+2", "+4 °C"])
    cb.ax.tick_params(labelsize=6.8, colors=viz.SUB, length=0, pad=2)
    fig.text(0.29, 0.793, "colder than normal", fontsize=6.8, color=viz.SUB, ha="right", va="center")
    fig.text(0.79, 0.793, "hotter", fontsize=6.8, color=viz.SUB, ha="left", va="center")
    footer(fig, source, f"GHCN-Daily {sid}; {years[-1]} through {meta['last_date']}; "
           "29 Feb not shown")
    save(fig, f"A_{slug(meta['name'])}_heat_carpet.png")


def hot_vs_cold(f, source):
    decades = np.arange(1880, 2030, 10)
    ratios, labels = [], []
    for dec in decades:
        h, lo = findings.record_counts(f, "Europe", dec, dec + 9)
        ratios.append(h / lo)
        labels.append(f"{dec}s" if dec < 2020 else f"2020–{str(f['final_year'])[2:]}")
    ratios = np.array(ratios)
    n_eu = int((f["region"] == "Europe").sum())

    fig = plt.figure(figsize=SIZE, dpi=DPI)
    header(fig, f"{ratios[-1]:.0f} to 1",
           "For a century, Europe's record-cold days outnumbered\nrecord-hot days. Then it flipped",
           f"Record-hot days ÷ record-cold days, by the decade that set the record standing today\n"
           f"{n_eu} European weather stations with 100+ years of data · 1880s–1980s: between "
           f"{ratios[decades < 1990].min():.1f} and {ratios[decades < 1990].max():.1f}")
    ax = fig.add_axes([0.12, 0.13, 0.84, 0.64])
    viz.style_axes(ax)
    x = np.arange(len(decades))
    ax.set_xlim(-0.7, len(decades) - 0.3)
    ax.set_ylim(0, np.ceil(ratios.max() / 5) * 5 + 2)
    viz.round_top_bars(ax, x, ratios, [HOT if r > 1 else COLD for r in ratios], width=0.68, radius_px=8)
    for xi, r in zip(x, ratios):
        if r > 1:
            ax.text(xi, r + 0.35, f"{r:.1f}" if r < 10 else f"{r:.0f}", ha="center", va="bottom",
                    fontsize=9 if r > 10 else 8, color=viz.TEXT, fontweight="bold")
    ax.axhline(1, color=viz.TEXT, linewidth=1.0, zorder=4)
    ax.text(-0.55, 1.35, "stable climate: 1 to 1", fontsize=7.5, color=viz.SUB, va="bottom")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7.2, rotation=90)
    ax.tick_params(axis="y", labelsize=8)
    ax.set_ylabel("Record-hot days per record-cold day", fontsize=8, labelpad=6)
    footer(fig, source, "Records of the daily maximum temperature for each calendar day, 1 Jan to each "
           "station's latest data; ties go to the earliest year")
    save(fig, "B_europe_hot_vs_cold_by_decade.png")


def hottest_each_year(f, sid, source):
    meta = f["idx"].loc[sid]
    name = display_name({"id": sid, "name": meta["name"], "country": meta["country"], "state": meta["state"]})
    s = station_series(f, sid)
    summer = s[s.index.month.isin([6, 7, 8])]
    ok = summer.groupby(summer.index.year).count() >= 0.9 * 92
    ann = s.groupby(s.index.year).max()[ok[ok].index]
    run = ann.cummax()
    new = ann[(ann == run) & (ann > run.shift(1).fillna(-np.inf))]
    last = ann.index[-1]
    prev = run.loc[:last - 1].iloc[-1]

    fig = plt.figure(figsize=SIZE, dpi=DPI)
    header(fig, f"{ann.iloc[-1]:.1f} °C",
           f"{name}'s hottest day of every year since {ann.index[0]}.\n"
           f"{last} beat the all-time record by {ann.iloc[-1] - prev:.1f} °C",
           "Dots: the hottest day of each year · line: the all-time record up to that year\n"
           "Red: years that set a new all-time record")
    ax = fig.add_axes([0.12, 0.11, 0.84, 0.66])
    viz.style_axes(ax)
    ax.step(run.index, run.to_numpy(), where="post", color=viz.ACC, linewidth=1.6, zorder=3)
    ax.scatter(ann.index, ann.to_numpy(), s=16, color=viz.SUB, edgecolor=viz.BG, linewidth=0.6, zorder=4)
    ax.scatter(new.index, new.to_numpy(), s=30, color=HOT, edgecolor=viz.BG, linewidth=0.8, zorder=5)
    for y, v in new.items():
        if y > new.index[0]:
            ax.text(y, v + 0.35, str(y), fontsize=6.6, color=viz.TEXT, ha="center", va="bottom")
    ax.scatter([last], [ann.iloc[-1]], s=120, color=HOT, edgecolor="white", linewidth=1.2, zorder=6)
    hot_day = s[s.index.year == last].idxmax()
    ax.annotate(f"{ann.iloc[-1]:.1f} °C on {hot_day.day} {hot_day.strftime('%B')} {last}",
                (last, ann.iloc[-1]), xytext=(-14, 10), textcoords="offset points", ha="right",
                fontsize=8.5, fontweight="bold", color=viz.TEXT)
    ax.set_xlim(ann.index[0] - 3, last + 4)
    ax.set_ylim(np.floor(ann.min()) - 1, np.ceil(ann.max()) + 2)
    ax.tick_params(axis="both", labelsize=8)
    ax.set_ylabel("Hottest daily maximum of the year (°C)", fontsize=8, labelpad=6)
    footer(fig, source, "Years with at least 90% of summer days measured")
    save(fig, f"C_{slug(meta['name'])}_hottest_day_each_year.png")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", default="GM000003342", help="station for figures A and C (default Potsdam)")
    args = ap.parse_args()
    f = findings.compute()
    viz.set_final_year(f["final_year"])
    ver = ghcnd_version()
    src = f["idx"].loc[args.id, "supplement_source"]
    station_source = f"Data: NOAA NCEI GHCN-Daily v{ver}" + (f" + {src} open data" if isinstance(src, str) and src else "")
    heat_carpet(f, args.id, station_source)
    hot_vs_cold(f, f"Data: NOAA NCEI GHCN-Daily v{ver} + national open data")
    hottest_each_year(f, args.id, station_source)


if __name__ == "__main__":
    main()
