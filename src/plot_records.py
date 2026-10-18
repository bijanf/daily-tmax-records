"""Social-media figures for the per-calendar-day TMAX record plot.

    outputs/records_master_wide.png   the full plot: one bar per day, record value,
                                      year of the record as a 90-degree label
    outputs/carousel/NN_*.png         1080 x 1350 slides (overview, one per month,
                                      method) for Instagram
    outputs/carousel/carousel.pdf     the same slides as one PDF (LinkedIn document post)

Run after composite.py:  python -I src/plot_records.py
"""

from __future__ import annotations

import calendar
import textwrap
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
SLIDES = OUT / "carousel"

# Dark theme tokens shared with the climate_shift Instagram slides
BG = "#0F1419"
TEXT = "#E8EAED"
SUB = "#9AA0A6"
RULE = "#3C4043"
ACC = "#FF6B6B"
FONT = ["Lato", "DejaVu Sans"]

SOURCE = "Data: NOAA NCEI GHCN-Daily"
CREDIT = "Analysis: Bijan Fallah"
BASE_LABEL = "1961–1990"

# Record-year eras, oldest first: (first year, last year, legend label, bar colour)
# (validated on the dark surface: adjacent CVD dE >= 12, normal-vision dE >= 16, all >= 3:1;
#  the grey is the deliberate neutral midpoint between "old" and "recent")
ERAS = [
    (0, 1949, "before 1950", "#3A84DC"),
    (1950, 1999, "1950–1999", "#A9B1BA"),
    (2000, 2009, "2000–2009", "#F6D257"),
    (2010, 2019, "2010–2019", "#F5822E"),
    (2020, 9999, "2020 onwards", "#E9365A"),
]

IG_W, IG_H, IG_DPI = 1080, 1350, 150

# Lato is installed system-wide but missing from matplotlib's font cache
for _ttf in Path("/usr/share/fonts/truetype/lato").glob("Lato-*.ttf"):
    font_manager.fontManager.addfont(str(_ttf))

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": FONT,
        "axes.facecolor": BG,
        "figure.facecolor": BG,
        "savefig.facecolor": BG,
        "text.color": TEXT,
        "axes.labelcolor": SUB,
        "xtick.color": SUB,
        "ytick.color": SUB,
        "axes.edgecolor": RULE,
        "pdf.fonttype": 42,
    }
)


def era_index(year: int) -> int:
    for i, (lo, hi, _, _) in enumerate(ERAS):
        if lo <= year <= hi:
            return i
    raise ValueError(year)


def era_colour(year: int) -> str:
    return ERAS[era_index(year)][3]


def load():
    rec = pd.read_csv(OUT / "records_by_day.csv", parse_dates=["date"])
    st = pd.read_csv(OUT / "stations_used.csv", index_col="id")
    return rec, st


def facts(rec: pd.DataFrame, st: pd.DataFrame) -> dict:
    summ = pd.read_csv(OUT / "summary.csv").set_index("key")["value"]
    first_year = int(summ["first_year"])
    final_year = int(summ["final_year"])
    last = rec["date"].iloc[-1]
    shares = {k[len("share_"):]: float(v) for k, v in summ.items() if k.startswith("share_")}
    return {
        "n_days": len(rec),
        "n_stations": len(st),
        "n_countries": int(summ["n_countries"]),
        "first_year": first_year,
        "expected_per_year": len(rec) / (final_year - first_year + 1),
        "final_year": final_year,
        "version": summ["ghcnd_version"],
        "counts": rec["record_year"].value_counts(),
        "since_2000": int(summ["since_2000"]),
        "since_2020": int(summ["since_2020"]),
        "expected_2000": float(summ["expected_since_2000"]),
        "expected_2020": float(summ["expected_since_2020"]),
        "shares": shares,
        "last_date": last,
        "last_label": f"{last.day} {last.strftime('%b')}",
        "last_label_long": f"{last.day} {last.strftime('%B')}",
    }


def style_axes(ax, ygrid=True):
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.spines["bottom"].set_linewidth(1.0)
    ax.tick_params(axis="both", length=0, pad=6)
    if ygrid:
        ax.yaxis.grid(True, color=RULE, linewidth=0.6)
        ax.set_axisbelow(True)


def round_top_bars(ax, x, h, colours, width=0.74, radius_px=4.0):
    """Columns with rounded data ends and a square baseline (axes limits must be final)."""
    p0 = ax.transData.transform((0, 0))
    p1 = ax.transData.transform((1, 1))
    rx = radius_px / abs(p1[0] - p0[0])
    ry = radius_px / abs(p1[1] - p0[1])
    r = min(rx, width / 2)
    ry_eff = ry * r / rx
    for xi, hi, c in zip(x, h, colours):
        if not np.isfinite(hi) or hi <= 0:
            continue
        if hi <= 2 * ry_eff:
            ax.add_patch(Rectangle((xi - width / 2, 0), width, hi, fc=c, ec="none", zorder=3))
            continue
        ax.add_patch(
            FancyBboxPatch(
                (xi - width / 2, 0), width, hi,
                boxstyle=f"round,pad=0,rounding_size={r}",
                mutation_aspect=ry / rx, fc=c, ec="none", zorder=3,
            )
        )
        ax.add_patch(Rectangle((xi - width / 2, 0), width, ry_eff, fc=c, ec="none", zorder=3))


def year_labels(ax, x, h, years, fontsize, pad, bold_from=2020):
    for xi, hi, yr in zip(x, h, years):
        recent = yr >= bold_from
        ax.text(
            xi, hi + pad, str(yr), rotation=90, ha="center", va="bottom",
            fontsize=fontsize, color=TEXT if recent else SUB,
            fontweight="bold" if recent else "normal", zorder=4,
        )


def era_legend(fig, x0, y0, fontsize, gap=0.012, swatch=0.012, ha="left", fig_w_in=None):
    """Swatch + label row in figure coordinates; returns nothing."""
    fig_w_in = fig_w_in or fig.get_figwidth()
    renderer = fig.canvas.get_renderer()
    items = []
    for _, _, label, colour in ERAS:
        t = fig.text(0, 0, label, fontsize=fontsize, color=SUB, va="center")
        w = t.get_window_extent(renderer).width / fig.dpi / fig_w_in
        t.remove()
        items.append((label, colour, w))
    total = sum(swatch + 0.006 + w for _, _, w in items) + gap * (len(items) - 1)
    x = x0 - total if ha == "right" else x0 - total / 2 if ha == "center" else x0
    aspect = fig.get_figwidth() / fig.get_figheight()
    for label, colour, w in items:
        fig.patches.append(
            FancyBboxPatch(
                (x, y0 - swatch * aspect / 2), swatch, swatch * aspect,
                boxstyle="round,pad=0,rounding_size=0.002", transform=fig.transFigure,
                fc=colour, ec="none", figure=fig,
            )
        )
        fig.text(x + swatch + 0.006, y0, label, fontsize=fontsize, color=SUB, va="center")
        x += swatch + 0.006 + w + gap


def month_ticks(ax, rec):
    starts = np.flatnonzero(rec["date"].dt.day.to_numpy() == 1)
    ax.set_xticks(starts)
    ax.set_xticklabels([f"1 {rec['date'].iloc[i].strftime('%b')}" for i in starts])
    for i in starts[1:]:
        ax.axvline(i - 0.5, color=RULE, linewidth=0.6, zorder=1)


# ─────────────────────────────────────────────────────────────────────────────
# Master figure
# ─────────────────────────────────────────────────────────────────────────────

def master(rec, f, path):
    W, H, DPI = 36.0, 12.0, 250
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    ax = fig.add_axes([0.045, 0.12, 0.94, 0.64])
    x = np.arange(len(rec))
    h = rec["record_anom"].to_numpy()
    ymax = np.ceil((h.max() + 0.9) * 2) / 2
    ax.set_xlim(-0.8, len(rec) - 0.2)
    ax.set_ylim(0, ymax)
    style_axes(ax)
    round_top_bars(ax, x, h, [era_colour(y) for y in rec["record_year"]], width=0.74, radius_px=6)
    year_labels(ax, x, h, rec["record_year"], fontsize=7.6, pad=0.05)
    month_ticks(ax, rec)
    ax.tick_params(axis="x", labelsize=17, colors=SUB)
    ax.tick_params(axis="y", labelsize=17, colors=SUB)
    ax.set_ylabel(f"Record daily max temperature anomaly (°C vs {BASE_LABEL})", fontsize=18, labelpad=14)

    fig.text(0.045, 0.955, headline(f), fontsize=46, fontweight="bold", color=ACC, va="top")
    fig.text(0.045, 0.875, subtitle(f), fontsize=22, color=TEXT, va="top")
    fig.canvas.draw()
    era_legend(fig, 0.985, 0.80, fontsize=17, ha="right", swatch=0.006)
    fig.text(0.045, 0.03, f"{SOURCE} · {method_line(f)} · {CREDIT}", fontsize=14, color=SUB)
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def headline(f) -> str:
    return (f"{f['since_2020']} of {f['n_days']} days so far in {f['final_year']} have their heat record "
            f"in the 2020s")


def subtitle(f) -> str:
    return (f"Hottest daily maximum temperature on each calendar day, 1 Jan – {f['last_label']}, "
            f"across {f['n_stations']:,} weather stations with 100+ years of data. "
            f"A stable climate would give about {f['expected_2020']:.0f} such days. "
            f"Label = year of the record.")


def method_line(f) -> str:
    return (f"{f['n_stations']:,} stations in {f['n_countries']} countries/territories, ≥100 complete "
            f"years, still reporting · anomalies vs each station's {BASE_LABEL} normal, "
            f"5°×5° area-weighted mean · candidate years {f['first_year']}–{f['final_year']} · each day compares "
            f"all years on the stations that have reported it in {f['final_year']}")


# ─────────────────────────────────────────────────────────────────────────────
# Instagram / LinkedIn slides (1080 x 1350)
# ─────────────────────────────────────────────────────────────────────────────

def new_slide():
    return plt.figure(figsize=(IG_W / IG_DPI, IG_H / IG_DPI), dpi=IG_DPI)


def slide_footer(fig, k, n_slides, extra=None):
    if extra:
        fig.text(0.5, 0.045, extra, fontsize=6.6, color=SUB, ha="center")
    fig.text(0.5, 0.022, f"{SOURCE} · {CREDIT}", fontsize=6.6, color=SUB, ha="center")
    fig.text(0.955, 0.022, f"{k}/{n_slides}", fontsize=6.6, color=SUB, ha="right")


def slide_overview(rec, f, k, n_slides):
    fig = new_slide()
    fig.text(0.5, 0.955, f"{f['since_2020']} of {f['n_days']}", fontsize=50, fontweight="bold",
             color=ACC, ha="center", va="top")
    fig.text(0.5, 0.862, f"days of {f['final_year']} so far have their heat record\nset in the 2020s",
             fontsize=17, fontweight="bold", color=TEXT, ha="center", va="top", linespacing=1.25)
    fig.text(0.5, 0.775,
             f"Hottest daily maximum temperature on each calendar day, 1 Jan – {f['last_label']},\n"
             f"across {f['n_stations']:,} weather stations with 100+ years of data. "
             f"A stable climate would give about {f['expected_2020']:.0f}.",
             fontsize=8.8, color=SUB, ha="center", va="top", linespacing=1.45)

    # a: record value per calendar day
    fig.text(0.10, 0.700, "The record for each calendar day", fontsize=9.5, color=TEXT,
             fontweight="bold", va="bottom")
    ax = fig.add_axes([0.10, 0.435, 0.86, 0.215])
    x = np.arange(len(rec))
    h = rec["record_anom"].to_numpy()
    ax.set_xlim(-1, len(rec))
    ax.set_ylim(0, np.ceil(h.max() + 0.2))
    style_axes(ax)
    ax.bar(x, h, width=0.8, color=[era_colour(y) for y in rec["record_year"]], linewidth=0, zorder=3)
    starts = np.flatnonzero(rec["date"].dt.day.to_numpy() == 1)
    ax.set_xticks(starts)
    ax.set_xticklabels([rec["date"].iloc[i].strftime("%b") for i in starts], fontsize=8)
    ax.tick_params(axis="y", labelsize=8)
    ax.set_ylabel(f"°C above {BASE_LABEL} normal", fontsize=8, labelpad=6)
    fig.canvas.draw()
    era_legend(fig, 0.5, 0.676, fontsize=8, ha="center", swatch=0.018, gap=0.022)

    # b: how many of those days each year holds
    fig.text(0.10, 0.345, "How many of those days each year holds", fontsize=9.5, color=TEXT,
             fontweight="bold", va="bottom")
    ax2 = fig.add_axes([0.10, 0.105, 0.86, 0.215])
    years = np.arange(f["first_year"], f["final_year"] + 1)
    cnt = f["counts"].reindex(years, fill_value=0).to_numpy()
    style_axes(ax2)
    ax2.set_xlim(years[0] - 1.5, f["final_year"] + 2.5)
    ax2.set_ylim(0, cnt.max() * 1.18)
    ax2.bar(years, cnt, width=0.8, color=[era_colour(y) for y in years], linewidth=0, zorder=3)
    ax2.axhline(f["expected_per_year"], color=TEXT, linewidth=1.0, zorder=4)
    for yr in sorted({int(f["counts"].index[0]), f["final_year"]}):
        if yr in f["counts"].index:
            ax2.text(yr, f["counts"][yr] + cnt.max() * 0.02, str(yr), fontsize=8, fontweight="bold",
                     color=TEXT, ha="center", va="bottom")
    ax2.tick_params(axis="both", labelsize=8)
    ax2.set_ylabel("Days holding the record", fontsize=8, labelpad=6)
    fig.lines.append(plt.Line2D([0.10, 0.135], [0.329, 0.329], color=TEXT, linewidth=1.0,
                                transform=fig.transFigure, figure=fig))
    fig.text(0.143, 0.329, f"expected in a stable climate: {f['expected_per_year']:.1f} days per year",
             fontsize=7.8, color=SUB, va="center")
    slide_footer(fig, k, n_slides)
    return fig


def slide_month(rec, f, month, k, n_slides):
    sub = rec[rec["date"].dt.month == month]
    fig = new_slide()
    name = calendar.month_name[month]
    fig.text(0.5, 0.955, name, fontsize=42, fontweight="bold", color=ACC, ha="center", va="top")
    n_new = int((sub["record_year"] >= 2020).sum())
    fig.text(0.5, 0.872, f"{n_new} of {len(sub)} days: record set in the 2020s",
             fontsize=15, fontweight="bold", color=TEXT, ha="center", va="top")
    fig.text(0.5, 0.825,
             f"Hottest each calendar day has been since {f['first_year']}, averaged over "
             f"{f['n_stations']:,} stations\nwith 100+ years of data · bar = record daily max "
             f"anomaly · label = year it was set",
             fontsize=8.8, color=SUB, ha="center", va="top", linespacing=1.45)

    ax = fig.add_axes([0.115, 0.135, 0.85, 0.58])
    days = sub["date"].dt.day.to_numpy()
    h = sub["record_anom"].to_numpy()
    ymax = np.ceil(h.max() + 1.0)
    ax.set_xlim(0.3, 31.7)
    ax.set_ylim(0, ymax)
    style_axes(ax)
    round_top_bars(ax, days, h, [era_colour(y) for y in sub["record_year"]], width=0.72, radius_px=4)
    year_labels(ax, days, h, sub["record_year"], fontsize=9.6, pad=ymax * 0.012)
    ax.set_xticks([1, 5, 10, 15, 20, 25, 30])
    ax.tick_params(axis="both", labelsize=8.5)
    ax.set_xlabel(f"Day of {name}", fontsize=8.5, labelpad=6)
    ax.set_ylabel(f"Record daily max temperature anomaly (°C vs {BASE_LABEL})", fontsize=8.5,
                  labelpad=8)
    fig.canvas.draw()
    era_legend(fig, 0.5, 0.745, fontsize=7.5, ha="center", swatch=0.018, gap=0.022)
    notes = []
    if sub["footprint_cover"].mean() < 0.9:
        notes.append("Some European stations have not reported these days yet, so every year is "
                     "compared on the stations that have")
    if month == f["last_date"].month and f["last_date"].day < calendar.monthrange(f["final_year"], month)[1]:
        notes.append(f"Data through {f['last_label']} {f['final_year']}")
    slide_footer(fig, k, n_slides, " · ".join(notes) or None)
    return fig


def slide_method(f, k, n_slides):
    fig = new_slide()
    fig.text(0.5, 0.955, "How?", fontsize=42, fontweight="bold", color=ACC, ha="center", va="top")
    fig.text(0.5, 0.872, "Data, method and caveats", fontsize=15, fontweight="bold", color=TEXT,
             ha="center", va="top")
    sh = f["shares"]
    sections = [
        ("Stations", [
            f"All {f['n_stations']:,} stations in NOAA's GHCN-Daily archive with at least 100 complete "
            f"years of daily maximum temperature (≥80% of days) that still report in {f['final_year']}",
            f"{f['n_countries']} countries and territories on four continents. Share of the area "
            f"weight: US {sh['United States']:.0%}, Europe {sh['Europe']:.0%}, Asia {sh['Asia']:.0%}, "
            f"Canada & Greenland {sh['Canada & Greenland']:.0%}, Australia {sh['Australia']:.0%}",
        ]),
        ("Method", [
            f"Each station's daily maximum minus its own {BASE_LABEL} seasonal normal; values "
            "failing NOAA quality control or beyond 6σ are dropped",
            "Stations averaged in 5°×5° boxes and boxes weighted by area, the convention of "
            "global temperature datasets",
            f"For every calendar day: the highest value across {f['first_year']}–{f['final_year']} and the year "
            "it was set; a year competes only if boxes holding ≥70% of the area reported",
            f"Each day compares all years on the boxes that have reported it in {f['final_year']}, because "
            "European reports arrive weeks late",
        ]),
        ("Caveats", [
            "Weighting matters: counting every station equally (87% are in the US) would put the "
            "US Dust Bowl summers of the 1930s on top",
            "Raw, unhomogenised data. Early instruments, station moves and US observing-time "
            "changes tend to bias early decades warm, favouring old records if anything",
            "Land only, with no stations from South America or Africa: not a global average",
            f"Data through {f['last_label']}; the latest days can change as late reports arrive",
        ]),
    ]
    renderer = fig.canvas.get_renderer()
    y = 0.80
    for title, items in sections:
        fig.text(0.08, y, title, fontsize=12, fontweight="bold", color=ACC, va="top")
        y -= 0.042
        for item in items:
            t = fig.text(0.105, y, textwrap.fill(item, 88), fontsize=8.4, color=TEXT, va="top",
                         linespacing=1.35)
            fig.text(0.08, y, "•", fontsize=8.4, color=ACC, va="top")
            y -= t.get_window_extent(renderer).height / fig.bbox.height + 0.016
        y -= 0.022
    slide_footer(fig, k, n_slides, f"GHCN-Daily v{f['version']}, accessed {date.today():%-d %b %Y} · "
                 "Menne et al. 2012, doi:10.1175/JTECH-D-11-00103.1")
    return fig


def main() -> None:
    SLIDES.mkdir(parents=True, exist_ok=True)
    rec, st = load()
    f = facts(rec, st)
    global SOURCE
    SOURCE = f"{SOURCE} v{f['version']}"
    ERAS[-1] = (2020, 9999, f"2020–{f['final_year']}", ERAS[-1][3])
    master(rec, f, OUT / "records_master_wide.png")

    months = sorted(rec["date"].dt.month.unique())
    n_slides = len(months) + 2
    figs = [("01_overview", slide_overview(rec, f, 1, n_slides))]
    for k, m in enumerate(months, start=2):
        figs.append((f"{k:02d}_{calendar.month_name[m].lower()}", slide_month(rec, f, m, k, n_slides)))
    figs.append((f"{n_slides:02d}_method", slide_method(f, n_slides, n_slides)))

    with PdfPages(SLIDES / "carousel.pdf") as pdf:
        for name, fig in figs:
            fig.savefig(SLIDES / f"{name}.png", dpi=IG_DPI)
            pdf.savefig(fig)
            plt.close(fig)
    print(f"wrote master + {len(figs)} slides to {OUT}")


if __name__ == "__main__":
    main()
