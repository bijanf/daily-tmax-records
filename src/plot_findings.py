"""High-resolution figures for the findings in findings.py (2160 x 2700 px each).

    outputs/findings/1_germany_june_2026.png
    outputs/findings/2_record_highs_vs_lows.png
    outputs/findings/3_records_by_month.png
    outputs/findings/4_mountains_vs_cities.png
    outputs/findings/5_record_margins.png

Run with `python -I src/plot_findings.py`.
"""

from __future__ import annotations

import calendar
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cartopy.crs as ccrs  # noqa: E402
import cartopy.feature as cfeature  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import findings  # noqa: E402
import viz  # noqa: E402
from plot_stations import display_name, ghcnd_version  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "findings"
DPI = 300
SIZE = (7.2, 9.0)
COLD = "#3A84DC"
HOT = "#E9365A"
GREY = "#A9B1BA"
LAND = "#1E2630"


def new_fig():
    return plt.figure(figsize=SIZE, dpi=DPI)


def header(fig, big, line2, sub):
    fig.text(0.5, 0.962, big, fontsize=30, fontweight="bold", color=viz.ACC, ha="center", va="top")
    fig.text(0.5, 0.900, line2, fontsize=13.5, fontweight="bold", color=viz.TEXT, ha="center", va="top",
             linespacing=1.3)
    fig.text(0.5, 0.835, sub, fontsize=8.2, color=viz.SUB, ha="center", va="top", linespacing=1.45)


def footer(fig, source, note=None):
    if note:
        fig.text(0.5, 0.045, note, fontsize=6.4, color=viz.SUB, ha="center")
    fig.text(0.5, 0.022, f"{source} · {viz.CREDIT}", fontsize=6.4, color=viz.SUB, ha="center")


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    print(path)


# ─────────────────────────────────────────────────────────────────────────────

def germany(f, source):
    fy = f["final_year"]
    de = f["hot"][f["hot"]["country"] == "Germany"].copy()
    de["new"] = de["date"].between(f"{fy}-06-27", f"{fy}-06-28")
    de["label"] = [display_name({"id": i, "name": n, "country": "Germany", "state": ""})
                   for i, n in zip(de.index, de["name"])]
    new = de[de["new"]].sort_values("value")

    fig = new_fig()
    header(fig, f"27–28 June {fy}",
           f"{len(new)} of Germany's {len(de)} century-long weather stations\nmeasured their hottest day ever",
           f"Stations with 100+ years of daily maximum temperature · four passed 40 °C for the first time")

    proj = ccrs.LambertConformal(central_longitude=10.4, central_latitude=51.0)
    ax = fig.add_axes([0.03, 0.40, 0.48, 0.40], projection=proj)
    ax.set_extent([5.6, 15.3, 47.1, 55.2], crs=ccrs.PlateCarree())
    ax.set_facecolor(viz.BG)
    ax.add_feature(cfeature.NaturalEarthFeature("physical", "land", "50m"), facecolor=LAND, edgecolor="none")
    ax.add_feature(cfeature.NaturalEarthFeature("cultural", "admin_0_boundary_lines_land", "50m"),
                   facecolor="none", edgecolor=viz.SUB, linewidth=0.5)
    ax.add_feature(cfeature.NaturalEarthFeature("physical", "coastline", "50m"),
                   facecolor="none", edgecolor=viz.RULE, linewidth=0.5)
    ax.spines["geo"].set_visible(False)
    old = de[~de["new"]]
    ax.scatter(old["lon"], old["lat"], s=26, color=GREY, edgecolor=viz.BG, linewidth=0.8,
               transform=ccrs.PlateCarree(), zorder=3)
    ax.scatter(new["lon"], new["lat"], s=44, color=HOT, edgecolor=viz.BG, linewidth=0.9,
               transform=ccrs.PlateCarree(), zorder=4)
    place = {"GME00121258": (0.3, -0.18, "left"), "GM000003342": (-0.3, 0.15, "right"),
             "GME00102252": (-0.3, 0.05, "right"), "GME00125218": (0.3, -0.12, "left")}
    for sid, r in new[new["value"] >= 40].iterrows():
        dx, dy, ha = place.get(sid, (0.25, 0.08, "left"))
        ax.text(r["lon"] + dx, r["lat"] + dy, f"{r['label']} {r['value']:.1f}°", fontsize=6.2, ha=ha,
                color=viz.TEXT, transform=ccrs.PlateCarree(), zorder=5)

    lg = fig.add_axes([0.53, 0.62, 0.44, 0.14])
    lg.axis("off")
    lg.scatter([0.04], [0.78], s=44, color=HOT, edgecolor=viz.BG, transform=lg.transAxes)
    lg.text(0.10, 0.78, f"hottest day ever on 27 or 28 June {fy}", fontsize=8, color=viz.TEXT,
            va="center", transform=lg.transAxes)
    lg.scatter([0.04], [0.42], s=26, color=GREY, edgecolor=viz.BG, transform=lg.transAxes)
    lg.text(0.10, 0.42, "hottest day ever in another year", fontsize=8, color=viz.TEXT,
            va="center", transform=lg.transAxes)
    others = old["year"].value_counts()
    lg.text(0.10, 0.10, "others: " + ", ".join(f"{y} ({c})" for y, c in others.head(4).items()),
            fontsize=6.8, color=viz.SUB, va="center", transform=lg.transAxes)

    ax2 = fig.add_axes([0.30, 0.115, 0.62, 0.27])
    y = np.arange(len(new))
    viz.style_axes(ax2, ygrid=False)
    ax2.xaxis.grid(True, color=viz.RULE, linewidth=0.6)
    ax2.set_axisbelow(True)
    for yi, (_, r) in zip(y, new.iterrows()):
        ax2.plot([r["prev_value"], r["value"]], [yi, yi], color=viz.SUB, linewidth=1.2, zorder=2)
    ax2.scatter(new["prev_value"], y, s=22, color=GREY, edgecolor=viz.BG, linewidth=0.8, zorder=3)
    ax2.scatter(new["value"], y, s=30, color=HOT, edgecolor=viz.BG, linewidth=0.8, zorder=4)
    for yi, (_, r) in zip(y, new.iterrows()):
        ax2.text(r["prev_value"] - 0.12, yi, f"{r['prev_date'].year}", fontsize=5.8, color=viz.SUB,
                 ha="right", va="center")
        ax2.text(r["value"] + 0.12, yi, f"{r['value']:.1f}°", fontsize=6.2, color=viz.TEXT,
                 ha="left", va="center", fontweight="bold" if r["value"] >= 40 else "normal")
    ax2.axvline(40, color=viz.TEXT, linewidth=0.9, zorder=1)
    ax2.set_yticks(y)
    ax2.set_yticklabels(new["label"], fontsize=7)
    ax2.set_xlim(new["prev_value"].min() - 1.4, new["value"].max() + 1.1)
    ax2.set_ylim(-0.7, len(new) - 0.3)
    ax2.tick_params(axis="x", labelsize=7)
    ax2.set_xlabel("Hottest daily maximum on record (°C): previous record (grey, with its year) → "
                   f"{fy} (red)", fontsize=7.2, labelpad=5)
    footer(fig, source, "All-time maximum over each station's whole record; 2026 values confirmed against "
           "DWD open data (identical where both exist)")
    save(fig, "1_germany_june_2026.png")


def highs_vs_lows(f, source):
    fy = f["final_year"]
    fig = new_fig()
    eu_h, eu_l = findings.record_counts(f, "Europe", 2020, fy)
    na_h, na_l = findings.record_counts(f, "North America", 2020, fy)
    header(fig, f"{eu_h / eu_l:.0f} to 1",
           "In Europe, record-hot days now outnumber record-cold days\n"
           f"{eu_h / eu_l:.0f} to 1. In North America: {na_h / na_l:.1f} to 1",
           "Every calendar day at every century-long station has a record high and a record low of its "
           "daily maximum.\nBars: the year that set the record standing today, per station. "
           "A stable climate would give 1 to 1.")
    for k, (reg, box) in enumerate((("Europe", [0.12, 0.47, 0.84, 0.30]),
                                    ("North America", [0.12, 0.10, 0.84, 0.30]))):
        rows = f["region"] == reg
        n_st = int(rows.sum())
        w = f["window"][rows]
        yrs = np.arange(1880, fy + 1)
        hi = pd.Series(f["hi_year"][rows][w]).value_counts().reindex(yrs, fill_value=0) / n_st
        lo = pd.Series(f["lo_year"][rows][w]).value_counts().reindex(yrs, fill_value=0) / n_st
        ax = fig.add_axes(box)
        viz.style_axes(ax)
        ax.bar(yrs, hi.to_numpy(), width=0.85, color=HOT, linewidth=0, zorder=3)
        ax.bar(yrs, -lo.to_numpy(), width=0.85, color=COLD, linewidth=0, zorder=3)
        ax.axhline(0, color=viz.SUB, linewidth=0.8, zorder=4)
        top = max(hi.max(), lo.max()) * 1.15
        ax.set_ylim(-top, top)
        ax.set_xlim(1878, fy + 2)
        ax.yaxis.set_major_locator(plt.MaxNLocator(nbins=6, integer=True, symmetric=True))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{abs(v):g}"))
        ax.tick_params(axis="both", labelsize=7.5)
        ax.set_ylabel("Records per station", fontsize=7.5, labelpad=6)
        h20, l20 = findings.record_counts(f, reg, 2020, fy)
        ax.text(0.01, 0.97, f"{reg} · {n_st} stations", transform=ax.transAxes, fontsize=10,
                fontweight="bold", color=viz.TEXT, va="top")
        ax.text(0.01, 0.86, "record highs set that year ↑", transform=ax.transAxes, fontsize=7.5,
                color=viz.TEXT, va="top")
        ax.text(0.01, 0.05, "record lows set that year ↓", transform=ax.transAxes, fontsize=7.5,
                color=viz.TEXT, va="bottom")
        ax.text(0.99, 0.97, f"2020s: {h20:,} highs vs {l20:,} lows", transform=ax.transAxes, fontsize=8,
                color=viz.TEXT, ha="right", va="top")
    footer(fig, source, "Record of the daily maximum temperature for each calendar day, 1 Jan to each "
           "station's latest data; ties go to the earliest year")
    save(fig, "2_record_highs_vs_lows.png")


def by_month(f, source):
    rec, idx = f["rec"], f["idx"]
    fig = new_fig()
    tab = rec.assign(new=rec["record_year"] >= 2020).pivot_table(
        index="region", columns="month", values="new", aggfunc="mean") * 100
    exp = {r: 100 * idx.loc[idx["region"] == r, "expected_2020s"].sum() / idx.loc[idx["region"] == r, "n_days"].sum()
           for r in ("Europe", "North America")}
    eu, na = tab.loc["Europe"], tab.loc["North America"]
    summer = rec[(rec["region"] == "North America") & rec["month"].isin([6, 7, 8])]
    thirties = 100 * summer["record_year"].between(1930, 1939).mean()
    header(fig, "Not the same summer",
           "Europe breaks heat records in every season. In North America,\n"
           f"{thirties:.0f}% of summer records still date from the 1930s",
           "Share of calendar days whose record daily maximum was set in 2020 or later, by month\n"
           f"Stable climate: about {exp['Europe']:.0f}% of days")
    ax = fig.add_axes([0.12, 0.12, 0.84, 0.62])
    viz.style_axes(ax)
    months = np.arange(1, len(eu) + 1)
    wbar = 0.38
    ax.set_xlim(0.4, len(months) + 0.6)
    ax.set_ylim(0, max(eu.max(), na.max()) * 1.2)
    viz.round_top_bars(ax, months - wbar / 2 - 0.02, eu.to_numpy(), ["#F5822E"] * len(months), width=wbar,
                       radius_px=6)
    viz.round_top_bars(ax, months + wbar / 2 + 0.02, na.to_numpy(), [COLD] * len(months), width=wbar,
                       radius_px=6)
    for m in months:
        ax.text(m - wbar / 2 - 0.02, eu[m] + 0.4, f"{eu[m]:.0f}", ha="center", va="bottom", fontsize=7,
                color=viz.TEXT)
        ax.text(m + wbar / 2 + 0.02, na[m] + 0.4, f"{na[m]:.0f}", ha="center", va="bottom", fontsize=7,
                color=viz.SUB)
    ax.axhline(exp["Europe"], color=viz.TEXT, linewidth=1.0, zorder=4)
    ax.set_xticks(months)
    labels = [calendar.month_abbr[m] for m in months]
    labels[-1] += "*"
    ax.set_xticklabels(labels, fontsize=8)
    ax.tick_params(axis="y", labelsize=8)
    ax.set_ylabel("Days with a 2020s record (%)", fontsize=8, labelpad=6)
    fig.canvas.draw()
    for x0, colour, label in ((0.30, "#F5822E", f"Europe ({int((idx['region'] == 'Europe').sum())} stations)"),
                              (0.57, COLD, f"North America ({int((idx['region'] == 'North America').sum())})")):
        fig.patches.append(plt.Rectangle((x0, 0.765), 0.018, 0.0144, transform=fig.transFigure,
                                         color=colour, figure=fig))
        fig.text(x0 + 0.026, 0.772, label, fontsize=8, color=viz.TEXT, va="center")
    fig.lines.append(plt.Line2D([0.12, 0.155], [0.745, 0.745], color=viz.TEXT, linewidth=1.0,
                                transform=fig.transFigure, figure=fig))
    fig.text(0.162, 0.745, "stable climate", fontsize=7.5, color=viz.SUB, va="center")
    footer(fig, source, "*October so far · 1 Jan to each station's latest data")
    save(fig, "3_records_by_month.png")


def mountains(f, source):
    idx = f["idx"]
    eu = idx[(idx["region"] == "Europe") & (idx["n_days"] >= 200)].copy()
    eu["pct"] = 100 * eu["share"]
    exp = 100 * (eu["expected_2020s"] / eu["n_days"]).median()
    fig = new_fig()
    rho = eu["elev"].rank().corr(eu["share"].rank())
    header(fig, "Not urban heat",
           "Mountain summits with no city nearby break heat records\nas often as lowland cities",
           f"{len(eu)} European stations with 100+ years of data · share of calendar days whose record "
           f"was set in 2020 or later\nRank correlation with elevation: {rho:+.2f} · stable climate: about "
           f"{exp:.0f}% of days")
    ax = fig.add_axes([0.12, 0.10, 0.84, 0.64])
    viz.style_axes(ax)
    ax.xaxis.grid(True, color=viz.RULE, linewidth=0.6)
    ax.scatter(eu["elev"], eu["pct"], s=26, color="#F5822E", edgecolor=viz.BG, linewidth=0.8, zorder=3)
    ax.axhline(exp, color=viz.TEXT, linewidth=1.0, zorder=2)
    ax.text(3150, exp + 0.6, "stable climate", fontsize=7, color=viz.SUB, ha="right", va="bottom")
    place = {"GM000004155": (-8, 5, "right"), "AU000015410": (-8, -10, "right"),
             "SZ000002220": (6, 5, "left"), "SP000060010": (-8, -10, "right"),
             "GME00102348": (6, 4, "left"), "GME00114621": (6, -9, "left"),
             "GM000003319": (8, 6, "left"), "UK000056225": (8, -10, "left"),
             "AU000005901": (8, 4, "left"), "SP000003195": (8, 4, "left"), "SP000009981": (8, 0, "left")}
    for sid, (dx, dy, ha) in place.items():
        if sid not in eu.index:
            continue
        r = eu.loc[sid]
        name = display_name({"id": sid, "name": r["name"], "country": r["country"], "state": ""})
        ax.annotate(f"{name.split(',')[0]} ({r['elev']:.0f} m)", (r["elev"], r["pct"]), xytext=(dx, dy),
                    textcoords="offset points", fontsize=6.6, color=viz.TEXT, ha=ha, va="center")
    ax.set_xlim(-100, 3350)
    ax.set_ylim(0, eu["pct"].max() * 1.12)
    ax.tick_params(axis="both", labelsize=8)
    ax.set_xlabel("Station elevation (m)", fontsize=8, labelpad=6)
    ax.set_ylabel("Days with a 2020s record (%)", fontsize=8, labelpad=6)
    footer(fig, source, "Stations with data at least through July · 1 Jan to each station's latest data")
    save(fig, "4_mountains_vs_cities.png")


def margins(f, source):
    fig = new_fig()
    header(fig, "Records are broken by more",
           "Daily heat records from the 2020s beat the next-best year\nby a wider margin than older records",
           "Margin of each calendar day's record daily maximum over the best other year, by the era that\n"
           "set the record · box = middle half of all records, line = median, dot = mean")
    for k, (reg, box) in enumerate((("Europe", [0.22, 0.47, 0.72, 0.30]),
                                    ("North America", [0.22, 0.10, 0.72, 0.30]))):
        rows = f["region"] == reg
        ax = fig.add_axes(box)
        viz.style_axes(ax, ygrid=False)
        ax.xaxis.grid(True, color=viz.RULE, linewidth=0.6)
        ax.set_axisbelow(True)
        for e, (y0, y1, label) in enumerate(findings.ERAS):
            m = f["window"][rows] & (f["hi_year"][rows] >= y0) & (f["hi_year"][rows] <= y1) \
                & np.isfinite(f["margin"][rows])
            v = f["margin"][rows][m]
            q1, med, q3 = np.percentile(v, [25, 50, 75])
            colour = (viz.ERAS[0][3], viz.ERAS[1][3], viz.ERAS[3][3], viz.ERAS[4][3])[e]
            ax.barh(e, q3 - q1, left=q1, height=0.5, color=colour, alpha=0.85, zorder=3)
            ax.plot([med, med], [e - 0.25, e + 0.25], color=viz.BG, linewidth=2.2, zorder=4)
            ax.scatter([v.mean()], [e], s=22, color=viz.TEXT, edgecolor=viz.BG, zorder=5)
            ax.text(q3 + 0.05, e, f"median {med:.1f}° · mean {v.mean():.2f}° · {v.size:,} records",
                    fontsize=6.6, color=viz.SUB, va="center")
        ax.set_yticks(range(len(findings.ERAS)))
        ax.set_yticklabels([lab for _, _, lab in findings.ERAS], fontsize=8)
        ax.invert_yaxis()
        ax.set_xlim(0, 4.2)
        ax.tick_params(axis="x", labelsize=7.5)
        ax.set_xlabel("Margin over the best other year (°C)", fontsize=7.5, labelpad=5)
        ax.text(0.0, 1.06, reg, transform=ax.transAxes, fontsize=10, fontweight="bold", color=viz.TEXT)
    footer(fig, source, "Indicative only: records from the same heatwave are not independent, and older "
           "data are often rounded more coarsely")
    save(fig, "5_record_margins.png")


def main() -> None:
    f = findings.compute()
    viz.set_final_year(f["final_year"])
    ver = ghcnd_version()
    n_de = int((f["idx"]["country"] == "Germany").sum())
    source = (f"Data: NOAA NCEI GHCN-Daily v{ver} + national open data (DWD, SMHI, KNMI, GeoSphere, "
              f"MeteoSwiss) · {len(f['idx']):,} stations")
    germany(f, f"Data: NOAA NCEI GHCN-Daily v{ver} + DWD open data · {n_de} German stations")
    highs_vs_lows(f, source)
    by_month(f, source)
    mountains(f, source)
    margins(f, source)


if __name__ == "__main__":
    main()
