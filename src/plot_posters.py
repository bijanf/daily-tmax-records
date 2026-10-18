"""Posters for a general audience (2160 x 2700 px): Europe first, big type, plain words.

    outputs/posters/1_europe_23_to_1.png          heat records vs cold records, by decade
    outputs/posters/2_europe_map.png               where the hottest day ever happened recently
    outputs/posters/3_europe_2026.png              stations with their hottest day ever, by year
    outputs/posters/4_<station>_every_day.png      one city, every day since its first year
    outputs/posters/5_<station>_hottest_day.png    one city, its hottest day of every year

    python -I src/plot_posters.py                  # city posters for Potsdam
    python -I src/plot_posters.py --id GM000003319
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cartopy.crs as ccrs  # noqa: E402
import cartopy.feature as cfeature  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

import poster as P  # noqa: E402
import findings  # noqa: E402
from plot_impact import anomalies, station_series  # noqa: E402
from plot_stations import display_name, slug  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "posters"
OLD = "#636366"
SOFT = "#D1D1D6"
SOURCES = "Data: NOAA, DWD, SMHI, KNMI, GeoSphere, MeteoSwiss"
HEAT = LinearSegmentedColormap.from_list("heat", [
    (0.00, "#0A84FF"), (0.28, "#0B2F57"), (0.46, "#0B0B0D"), (0.54, "#0B0B0D"),
    (0.70, "#7A1410"), (0.84, P.RED), (0.94, P.ORANGE), (1.00, "#FFE8A3")])


def top(fig, big, line, big_size=100, line_y=None):
    """Huge headline, then one plain sentence in big type."""
    fig.text(P.LEFT, 0.945, big, fontfamily=P.DISPLAY, fontweight="bold", fontsize=big_size,
             color=P.INK, va="top", ha="left", linespacing=0.92)
    fig.text(P.LEFT, line_y if line_y is not None else 0.775, line, fontfamily=P.TEXT_FONT,
             fontweight="medium", fontsize=19, color=SOFT, va="top", ha="left", linespacing=1.22)


def bottom(fig, text):
    fig.text(P.LEFT, 0.03, text, fontsize=8, color=P.GRAY, va="bottom", ha="left", linespacing=1.45)
    fig.text(1 - P.LEFT, 0.03, P.SIGNATURE, fontsize=9, fontweight="semibold", color=P.INK,
             va="bottom", ha="right")


def fade_edges(fig, rect, band=0.07):
    """Black overlay that fades the outer band of a rectangle (figure coords) into the background."""
    ov = fig.add_axes(rect, zorder=5)
    ov.axis("off")
    ny, nx = 400, 400
    yy, xx = np.mgrid[0:1:complex(ny), 0:1:complex(nx)]
    w, h = rect[2] * P.W, rect[3] * P.H
    d = np.minimum.reduce([xx * w, (1 - xx) * w, yy * h, (1 - yy) * h]) / (band * P.W)
    img = np.zeros((ny, nx, 4))
    img[..., 3] = np.clip(1 - d, 0, 1) ** 1.5
    ov.imshow(img, extent=(0, 1, 0, 1), origin="lower", aspect="auto", interpolation="bilinear")
    ov.set_xlim(0, 1)
    ov.set_ylim(0, 1)


def europe(f):
    return f["hot"][f["hot"]["region"] == "Europe"]


# ─────────────────────────────────────────────────────────────────────────────

def poster_ratio(f):
    """Mirror chart: red up = heat records per cold record, blue down = cold records per heat record."""
    decades = np.arange(1880, 2030, 10)
    hc = np.array([findings.record_counts(f, "Europe", d, d + 9) for d in decades], dtype=float)
    heat_wins = hc[:, 0] >= hc[:, 1]
    size = np.where(heat_wins, hc[:, 0] / hc[:, 1], hc[:, 1] / hc[:, 0])
    top_ratio = size[-1]
    fig = P.new_poster(glow=P.RED, at=(0.86, 0.42), size=0.30, alpha=0.26)
    top(fig, f"{top_ratio:.0f} : 1", f"Europe now breaks {top_ratio:.0f} heat records\nfor every cold record.")

    ax = fig.add_axes([P.LEFT, 0.13, 1 - 2 * P.LEFT, 0.53])
    P.bare(ax)
    x = np.arange(len(decades))
    cold_max = size[~heat_wins].max()
    ax.set_xlim(-0.6, len(decades) - 0.4)
    ax.set_ylim(-cold_max * 3.1, top_ratio * 1.18)
    ax.set_yticks([])
    for xi, w, r, d in zip(x, heat_wins, size, decades):
        if not w:
            P.top_rounded_bar(ax, xi, -r, 0.66, P.BLUE, alpha=0.85, radius_px=8)
        elif d < decades[-1]:
            P.top_rounded_bar(ax, xi, r, 0.66, P.RED, alpha=0.8, radius_px=12)
            ax.text(xi, r + top_ratio * 0.02, f"{r:.0f}", ha="center", va="bottom", fontsize=15,
                    color=SOFT, fontweight="semibold")
        else:
            P.glow_box(ax, xi - 0.33, xi + 0.33, 0, r, P.RED, sigma_px=60, strength=0.6)
            P.top_rounded_bar(ax, xi, r, 0.66, P.RED, radius_px=16, zorder=4)
            ax.text(xi, r + top_ratio * 0.02, f"{r:.0f}", ha="center", va="bottom", fontsize=40,
                    fontfamily=P.DISPLAY, fontweight="bold", color=P.INK)
    worst = int(np.argmax(np.where(heat_wins, 0, size)))
    ax.text(x[worst], -size[worst] * 0.55, f"{size[worst]:.0f}", ha="center", va="center",
            fontsize=15, color=P.INK, fontweight="bold", zorder=6)
    ax.axhline(0, color=P.INK, linewidth=0.8, alpha=0.6, zorder=5)
    ax.text(-0.45, top_ratio * 0.30, "More heat records ↑", fontsize=15, color=P.RED, fontweight="semibold",
            va="bottom")
    ax.text(-0.45, top_ratio * 0.30 - top_ratio * 0.012, "red bar = heat records\nfor every cold record",
            fontsize=11, color=P.GRAY, va="top", linespacing=1.25)
    ax.text(-0.45, -cold_max * 1.25, "More cold records ↓", fontsize=15, color=P.BLUE,
            fontweight="semibold", va="top")
    ax.text(-0.45, -cold_max * 1.25 - top_ratio * 0.065, "blue bar = cold records for every heat record",
            fontsize=11, color=P.GRAY, va="top")
    show = {1880: "1880s", 1910: "1910s", 1950: "1950s", 1990: "1990s", 2020: "2020s"}
    ax.set_xticks([])
    for i, d in enumerate(decades):
        if d in show:
            ax.text(i, -cold_max * 2.85, show[d], ha="center", va="center", fontsize=12, color=P.GRAY)
    bottom(fig, "Heat record: the hottest day ever measured on that date. Cold record: the coldest.\n"
                f"{int((f['region'] == 'Europe').sum())} weather stations in Europe, each with more than "
                f"100 years of measurements\n{SOURCES}")
    P.save(fig, OUT / "1_europe_23_to_1.png")


def poster_map(f):
    eu = europe(f)
    fy = f["final_year"]
    groups = [(eu[eu["year"] < 2000], OLD, 34, "before 2000"),
              (eu[eu["year"].between(2000, 2019)], P.ORANGE, 46, "2000 to 2019"),
              (eu[eu["year"] >= 2020], P.RED, 62, f"2020 to {fy}")]
    share = (eu["year"] >= 2000).mean()
    fig = P.new_poster()
    top(fig, "2 in 3" if round(share * 3) == 2 else f"{share:.0%}",
        "of Europe's oldest weather stations measured\ntheir hottest day ever after the year 2000.")

    proj = ccrs.LambertConformal(central_longitude=17, central_latitude=52, standard_parallels=(38, 64))
    map_rect = [0.0, 0.17, 1.0, 0.50]
    ax = fig.add_axes(map_rect, projection=proj)
    ax.set_extent([-11, 52, 35.5, 70.5], crs=ccrs.PlateCarree())
    ax.set_facecolor("none")
    ax.spines["geo"].set_visible(False)
    ax.add_feature(cfeature.NaturalEarthFeature("physical", "land", "50m"), facecolor="#1C1C1E",
                   edgecolor="none")
    ax.add_feature(cfeature.NaturalEarthFeature("cultural", "admin_0_boundary_lines_land", "50m"),
                   facecolor="none", edgecolor="#3A3A3C", linewidth=0.45)
    for sub, colour, size, _ in groups:
        ax.scatter(sub["lon"], sub["lat"], s=size, color=colour, edgecolor=P.BLACK, linewidth=0.7,
                   transform=ccrs.PlateCarree(), zorder=4)
    new = groups[-1][0]
    ax.scatter(new["lon"], new["lat"], s=260, color=P.RED, alpha=0.10, linewidth=0,
               transform=ccrs.PlateCarree(), zorder=3)
    ax.apply_aspect()
    fade_edges(fig, list(ax.get_position().bounds))

    y = 0.135
    for i, (sub, colour, _, label) in enumerate(groups[::-1]):
        x0 = P.LEFT + i * 0.29
        fig.text(x0, y, f"{len(sub)}", fontfamily=P.DISPLAY, fontweight="bold", fontsize=34,
                 color=colour if colour != OLD else SOFT, va="center")
        fig.text(x0 + 0.105, y + 0.008, "stations", fontsize=10, color=P.GRAY, va="bottom")
        fig.text(x0 + 0.105, y - 0.004, label, fontsize=12, color=SOFT, va="top", fontweight="medium")
    bottom(fig, "Each dot is a weather station with more than 100 years of measurements,\n"
                "coloured by the year of its hottest day ever. Tenerife not shown.\n" + SOURCES)
    P.save(fig, OUT / "2_europe_map.png")


def poster_by_year(f):
    eu = europe(f)
    fy = f["final_year"]
    years = np.arange(1900, fy + 1)
    counts = eu["year"].value_counts().reindex(years, fill_value=0)
    n_fy = int(counts[fy])
    fig = P.new_poster(glow=P.RED, at=(0.88, 0.40), size=0.26, alpha=0.30)
    top(fig, f"{fy}", f"{n_fy} of Europe's oldest weather stations measured\n"
                      "their hottest day ever this year.\nMore than in any year before.", line_y=0.78)

    ax = fig.add_axes([P.LEFT, 0.15, 1 - 2 * P.LEFT, 0.44])
    P.bare(ax)
    ax.set_xlim(years[0] - 1.5, fy + 2)
    ax.set_ylim(0, n_fy * 1.22)
    ax.set_yticks([])
    for yr, c in counts.items():
        if c == 0:
            continue
        colour = P.RED if yr >= 2020 else P.ORANGE if yr >= 2000 else OLD
        if yr == fy:
            P.glow_box(ax, yr - 0.45, yr + 0.45, 0, c, P.RED, sigma_px=50, strength=0.65)
        P.top_rounded_bar(ax, yr, c, 0.82, colour, radius_px=5, zorder=4 if yr == fy else 3)
    second = counts.drop(fy).idxmax()
    ax.text(second - 1, counts[second], f"{second}: {counts[second]}", ha="right", va="center", fontsize=13,
            color=SOFT, fontweight="semibold")
    ax.text(fy, n_fy + n_fy * 0.02, f"{n_fy}", ha="center", va="bottom", fontsize=40,
            fontfamily=P.DISPLAY, fontweight="bold", color=P.INK)
    ax.set_xticks([1900, 1950, 2000])
    ax.set_xticklabels(["1900", "1950", "2000"], fontsize=12)
    bottom(fig, f"Bars: how many of the {len(eu)} stations had their hottest day ever in that year.\n"
                "Weather stations in Europe, each with more than 100 years of measurements\n" + SOURCES)
    P.save(fig, OUT / "3_europe_2026.png")


def poster_carpet(f, sid):
    meta = f["idx"].loc[sid]
    name = display_name({"id": sid, "name": meta["name"], "country": meta["country"], "state": meta["state"]})
    raw = anomalies(station_series(f, sid))
    a = raw.asfreq("D").rolling(31, center=True, min_periods=20).mean().reindex(raw.index)
    a = a[~((a.index.month == 2) & (a.index.day == 29))]
    cols = pd.Series(np.arange(365), index=pd.date_range("2001-01-01", "2001-12-31").strftime("%m-%d"))
    years = np.arange(a.index.year.min(), f["final_year"] + 1)
    grid = np.full((len(years), 365), np.nan)
    grid[a.index.year - years[0], cols.loc[a.index.strftime("%m-%d")].to_numpy()] = a.to_numpy()
    rec = f["rec"][f["rec"]["id"] == sid]

    fig = P.new_poster(glow=P.RED, at=(0.5, 0.12), size=0.45, alpha=0.16)
    top(fig, f"Every day\nsince {years[0]}", f"{name}. Each line is one year.\nRed: hotter than usual. "
             "Blue: colder.", big_size=72, line_y=0.735)
    ax = fig.add_axes([P.LEFT, 0.135, 1 - 2 * P.LEFT, 0.52])
    P.bare(ax)
    ax.imshow(grid, aspect="auto", cmap=HEAT, vmin=-5, vmax=5, interpolation="nearest",
              extent=(-0.5, 364.5, years[-1] + 0.5, years[0] - 0.5))
    ax.scatter(cols.loc[rec["md"]].to_numpy(), rec["record_year"].to_numpy(), s=6, color=P.INK,
               edgecolor=P.BLACK, linewidth=0.35, zorder=3)
    starts = pd.date_range("2001-01-01", periods=12, freq="MS")
    ax.set_xticks([cols[d.strftime("%m-%d")] + 14 for d in starts])
    ax.set_xticklabels([d.strftime("%b")[0] for d in starts], fontsize=11)
    ax.set_yticks([years[0], 1950, 2000, years[-1]])
    ax.set_yticklabels([years[0], 1950, 2000, years[-1]], fontsize=11)
    fig.text(P.LEFT, 0.098, "●", fontsize=12, color=P.INK, va="center")
    fig.text(P.LEFT + 0.03, 0.098, "the year that still holds the heat record for that day", fontsize=12,
             color=SOFT, va="center", fontweight="medium")
    src = meta["supplement_source"] if isinstance(meta["supplement_source"], str) else ""
    bottom(fig, f"Compared with the average of 1961–1990, smoothed over a month · {years[-1]} up to "
                f"{pd.Timestamp(meta['last_date']):%-d %B}\nData: NOAA{', ' + src if src else ''}")
    P.save(fig, OUT / f"4_{slug(meta['name'])}_every_day.png")


def poster_staircase(f, sid):
    meta = f["idx"].loc[sid]
    name = display_name({"id": sid, "name": meta["name"], "country": meta["country"], "state": meta["state"]})
    s = station_series(f, sid)
    summer = s[s.index.month.isin([6, 7, 8])]
    ok = summer.groupby(summer.index.year).count() >= 0.9 * 92
    ann = s.groupby(s.index.year).max()[ok[ok].index]
    run = ann.cummax()
    last, peak = ann.index[-1], ann.iloc[-1]
    prev_year = int(run.loc[:last - 1].idxmax())
    prev = run.loc[prev_year]
    hot_day = s[s.index.year == last].idxmax()

    fig = P.new_poster(glow=P.RED, at=(0.86, 0.56), size=0.26, alpha=0.30)
    top(fig, f"{peak:.1f} °C", f"{name}'s hottest day since measurements\nbegan in {ann.index[0]}: "
                               f"{hot_day.day} {hot_day:%B} {last}.")
    ax = fig.add_axes([P.LEFT, 0.17, 1 - 2 * P.LEFT, 0.47])
    P.bare(ax)
    ax.scatter(ann.index, ann.to_numpy(), s=14, color=OLD, linewidth=0, zorder=3)
    ax.step(run.index, run.to_numpy(), where="post", color=P.RED, linewidth=2.4, zorder=4)
    P.halo(ax, last, peak, P.RED, size=110, zorder=6)
    ax.text(last - 3, peak + 0.2, f"{peak:.1f}°", ha="right", va="bottom", fontsize=24,
            fontfamily=P.DISPLAY, fontweight="bold", color=P.INK)
    ax.text(prev_year - 1.5, prev + 0.3, f"old record: {prev:.1f}° in {prev_year}", ha="right", va="bottom",
            fontsize=12, color=SOFT)
    ax.set_xlim(ann.index[0] - 2, last + 3)
    ax.set_ylim(np.floor(ann.min()) - 0.8, peak + 1.8)
    ticks = np.arange(np.ceil(ann.min() / 5) * 5, peak + 1, 5)
    ax.set_yticks(ticks)
    ax.set_yticklabels([f"{v:.0f}°" for v in ticks], fontsize=11)
    ax.set_xticks([1900, 1950, 2000])
    ax.set_xticklabels(["1900", "1950", "2000"], fontsize=11)
    fig.text(P.LEFT, 0.115, "●", fontsize=12, color=OLD, va="center")
    fig.text(P.LEFT + 0.03, 0.115, "hottest day of each year", fontsize=12, color=SOFT, va="center",
             fontweight="medium")
    fig.lines.append(Line2D([0.50, 0.55], [0.115, 0.115], color=P.RED, linewidth=2.4,
                            transform=fig.transFigure, figure=fig))
    fig.text(0.565, 0.115, "hottest day ever, so far", fontsize=12, color=SOFT, va="center",
             fontweight="medium")
    src = meta["supplement_source"] if isinstance(meta["supplement_source"], str) else ""
    bottom(fig, f"Highest temperature of each year at the {name} weather station\n"
                f"Data: NOAA{', ' + src if src else ''}")
    P.save(fig, OUT / f"5_{slug(meta['name'])}_hottest_day.png")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", default="GM000003342", help="station for the city posters (default Potsdam)")
    args = ap.parse_args()
    f = findings.compute()
    P.apply_style()
    poster_ratio(f)
    poster_map(f)
    poster_by_year(f)
    poster_carpet(f, args.id)
    poster_staircase(f, args.id)


if __name__ == "__main__":
    main()
