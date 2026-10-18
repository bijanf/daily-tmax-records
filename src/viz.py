"""Shared look and chart builders for the daily-record figures.

Dark theme tokens match the climate_shift Instagram slides. Every chart shows one
bar per calendar day (the record) coloured by the era of the record year, with
the year as a 90-degree label above the bar.
"""

from __future__ import annotations

import calendar
import math
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

BG = "#0F1419"
TEXT = "#E8EAED"
SUB = "#9AA0A6"
RULE = "#3C4043"
ACC = "#FF6B6B"
FONT = ["Lato", "DejaVu Sans"]
CREDIT = "Analysis: Bijan Fallah"

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


def set_final_year(final_year: int) -> None:
    lo, hi, _, colour = ERAS[-1]
    ERAS[-1] = (lo, hi, f"{lo}–{final_year}", colour)


def era_colour(year: int) -> str:
    for lo, hi, _, colour in ERAS:
        if lo <= year <= hi:
            return colour
    raise ValueError(year)


def nice_ylim(values: np.ndarray, label_room: float) -> tuple[float, float]:
    """Axis range from 0 (or below, for negative records) with headroom for the labels."""
    lo = min(0.0, float(np.floor(np.nanmin(values))) - 1.0)
    hi = float(np.nanmax(values))
    span = hi - lo
    step = 1 if span <= 8 else 2 if span <= 16 else 5
    top = hi + label_room * span
    return lo, math.ceil(top / step) * step


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
    """Columns from 0 with rounded data ends and a square baseline (axes limits must be final)."""
    p0 = ax.transData.transform((0, 0))
    p1 = ax.transData.transform((1, 1))
    rx = radius_px / abs(p1[0] - p0[0])
    ry = radius_px / abs(p1[1] - p0[1])
    r = min(rx, width / 2)
    ry_eff = ry * r / rx
    for xi, hi, c in zip(x, h, colours):
        if not np.isfinite(hi) or hi == 0:
            continue
        y0, height = (0, hi) if hi > 0 else (hi, -hi)
        if height <= 2 * ry_eff:
            ax.add_patch(Rectangle((xi - width / 2, y0), width, height, fc=c, ec="none", zorder=3))
            continue
        ax.add_patch(
            FancyBboxPatch(
                (xi - width / 2, y0), width, height,
                boxstyle=f"round,pad=0,rounding_size={r}",
                mutation_aspect=ry / rx, fc=c, ec="none", zorder=3,
            )
        )
        base = 0 if hi > 0 else -ry_eff
        ax.add_patch(Rectangle((xi - width / 2, base), width, ry_eff, fc=c, ec="none", zorder=3))


def year_labels(ax, x, h, years, fontsize, pad, bold_from=2020):
    for xi, hi, yr in zip(x, h, years):
        if not np.isfinite(hi):
            continue
        recent = yr >= bold_from
        ax.text(
            xi, max(hi, 0) + pad, str(yr), rotation=90, ha="center", va="bottom",
            fontsize=fontsize, color=TEXT if recent else SUB,
            fontweight="bold" if recent else "normal", zorder=4,
        )


def era_legend(fig, x0, y0, fontsize, gap=0.012, swatch=0.012, ha="left"):
    """Swatch + label row in figure coordinates."""
    renderer = fig.canvas.get_renderer()
    items = []
    for _, _, label, colour in ERAS:
        t = fig.text(0, 0, label, fontsize=fontsize, color=SUB, va="center")
        w = t.get_window_extent(renderer).width / fig.bbox.width
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


def month_ticks(ax, dates: pd.Series, short=False):
    starts = np.flatnonzero(dates.dt.day.to_numpy() == 1)
    ax.set_xticks(starts)
    fmt = "%b" if short else "1 %b"
    ax.set_xticklabels([dates.iloc[i].strftime(fmt) for i in starts])
    if not short:
        for i in starts[1:]:
            ax.axvline(i - 0.5, color=RULE, linewidth=0.6, zorder=1)


# ─────────────────────────────────────────────────────────────────────────────
# Wide chart: every day of the year so far, record value + rotated record year
# ─────────────────────────────────────────────────────────────────────────────

def wide_chart(rec: pd.DataFrame, value_col: str, path: Path, title: str, subtitle: str,
               ylabel: str, footer: str, size=(30.0, 10.0), dpi=220):
    """rec needs columns date, record_year and value_col, one row per calendar day."""
    W, H = size
    fig = plt.figure(figsize=(W, H), dpi=dpi)
    ax = fig.add_axes([0.05, 0.12, 0.935, 0.62])
    x = np.arange(len(rec))
    h = rec[value_col].to_numpy(dtype=float)
    ax.set_xlim(-0.8, len(rec) - 0.2)
    ax.set_ylim(*nice_ylim(h, 0.16))
    style_axes(ax)
    round_top_bars(ax, x, h, [era_colour(y) for y in rec["record_year"]], width=0.74, radius_px=5)
    year_labels(ax, x, h, rec["record_year"], fontsize=min(6.6, 6.6 * 288 / len(rec)),
                pad=(ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.008)
    month_ticks(ax, rec["date"])
    ax.tick_params(axis="x", labelsize=15, colors=SUB)
    ax.tick_params(axis="y", labelsize=15, colors=SUB)
    ax.set_ylabel(ylabel, fontsize=16, labelpad=12)

    fig.text(0.05, 0.955, title, fontsize=40, fontweight="bold", color=ACC, va="top")
    fig.text(0.05, 0.87, subtitle, fontsize=18, color=TEXT, va="top", linespacing=1.45)
    fig.canvas.draw()
    era_legend(fig, 0.985, 0.775, fontsize=14, ha="right", swatch=0.006)
    fig.text(0.05, 0.03, footer, fontsize=12, color=SUB)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi)
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# 1080 x 1350 slides
# ─────────────────────────────────────────────────────────────────────────────

def new_slide():
    return plt.figure(figsize=(IG_W / IG_DPI, IG_H / IG_DPI), dpi=IG_DPI)


def slide_footer(fig, k, n_slides, source, extra=None):
    if extra:
        fig.text(0.5, 0.045, extra, fontsize=6.6, color=SUB, ha="center")
    fig.text(0.5, 0.022, f"{source} · {CREDIT}", fontsize=6.6, color=SUB, ha="center")
    if n_slides:
        fig.text(0.955, 0.022, f"{k}/{n_slides}", fontsize=6.6, color=SUB, ha="right")


def overview_slide(rec, value_col, big, line2, sub, ylabel_a, counts, first_year, final_year,
                   expected_per_year, source, k, n_slides, top_label="The record for each calendar day",
                   bottom_label="How many of those days each year holds"):
    fig = new_slide()
    fig.text(0.5, 0.955, big, fontsize=50, fontweight="bold", color=ACC, ha="center", va="top")
    fig.text(0.5, 0.862, line2, fontsize=17, fontweight="bold", color=TEXT, ha="center", va="top",
             linespacing=1.25)
    fig.text(0.5, 0.775, sub, fontsize=8.8, color=SUB, ha="center", va="top", linespacing=1.45)

    fig.text(0.10, 0.700, top_label, fontsize=9.5, color=TEXT, fontweight="bold", va="bottom")
    ax = fig.add_axes([0.10, 0.435, 0.86, 0.215])
    x = np.arange(len(rec))
    h = rec[value_col].to_numpy(dtype=float)
    ax.set_xlim(-1, len(rec))
    ax.set_ylim(*nice_ylim(h, 0.05))
    style_axes(ax)
    ax.bar(x, h, width=0.8, color=[era_colour(y) for y in rec["record_year"]], linewidth=0, zorder=3)
    month_ticks(ax, rec["date"], short=True)
    ax.tick_params(axis="x", labelsize=8)
    ax.tick_params(axis="y", labelsize=8)
    ax.set_ylabel(ylabel_a, fontsize=8, labelpad=6)
    fig.canvas.draw()
    era_legend(fig, 0.5, 0.676, fontsize=8, ha="center", swatch=0.018, gap=0.022)

    fig.text(0.10, 0.345, bottom_label, fontsize=9.5, color=TEXT, fontweight="bold", va="bottom")
    ax2 = fig.add_axes([0.10, 0.105, 0.86, 0.215])
    years = np.arange(first_year, final_year + 1)
    cnt = counts.reindex(years, fill_value=0).to_numpy()
    style_axes(ax2)
    ax2.set_xlim(years[0] - 1.5, final_year + 2.5)
    ax2.set_ylim(0, max(cnt.max(), 1) * 1.18)
    ax2.bar(years, cnt, width=0.8, color=[era_colour(y) for y in years], linewidth=0, zorder=3)
    ax2.axhline(expected_per_year, color=TEXT, linewidth=1.0, zorder=4)
    for yr in sorted({int(counts.index[0]), final_year}):
        if yr in counts.index:
            ax2.text(yr, counts[yr] + cnt.max() * 0.02, str(yr), fontsize=8, fontweight="bold",
                     color=TEXT, ha="center", va="bottom")
    ax2.tick_params(axis="both", labelsize=8)
    ax2.set_ylabel("Days holding the record", fontsize=8, labelpad=6)
    fig.lines.append(plt.Line2D([0.10, 0.135], [0.329, 0.329], color=TEXT, linewidth=1.0,
                                transform=fig.transFigure, figure=fig))
    fig.text(0.143, 0.329, f"expected in a stable climate: {expected_per_year:.1f} days per year",
             fontsize=7.8, color=SUB, va="center")
    slide_footer(fig, k, n_slides, source)
    return fig


def month_slide(rec, value_col, month, line2, sub, ylabel, source, k, n_slides, notes=None):
    """rec: the rows of one month (columns date, record_year, value_col)."""
    fig = new_slide()
    name = calendar.month_name[month]
    fig.text(0.5, 0.955, name, fontsize=42, fontweight="bold", color=ACC, ha="center", va="top")
    fig.text(0.5, 0.872, line2, fontsize=15, fontweight="bold", color=TEXT, ha="center", va="top")
    fig.text(0.5, 0.825, sub, fontsize=8.8, color=SUB, ha="center", va="top", linespacing=1.45)

    ax = fig.add_axes([0.115, 0.135, 0.85, 0.58])
    days = rec["date"].dt.day.to_numpy()
    h = rec[value_col].to_numpy(dtype=float)
    ax.set_xlim(0.3, 31.7)
    lo, hi = nice_ylim(h, 0.14)
    ax.set_ylim(lo, hi)
    style_axes(ax)
    round_top_bars(ax, days, h, [era_colour(y) for y in rec["record_year"]], width=0.72, radius_px=4)
    year_labels(ax, days, h, rec["record_year"], fontsize=9.6, pad=(hi - lo) * 0.012)
    ax.set_xticks([1, 5, 10, 15, 20, 25, 30])
    ax.tick_params(axis="both", labelsize=8.5)
    ax.set_xlabel(f"Day of {name}", fontsize=8.5, labelpad=6)
    ax.set_ylabel(ylabel, fontsize=8.5, labelpad=8)
    fig.canvas.draw()
    era_legend(fig, 0.5, 0.745, fontsize=7.5, ha="center", swatch=0.018, gap=0.022)
    slide_footer(fig, k, n_slides, source, " · ".join(notes) if notes else None)
    return fig


def method_slide(sections, source, footnote, k, n_slides):
    """sections: list of (heading, [bullet text, ...])."""
    fig = new_slide()
    fig.text(0.5, 0.955, "How?", fontsize=42, fontweight="bold", color=ACC, ha="center", va="top")
    fig.text(0.5, 0.872, "Data, method and caveats", fontsize=15, fontweight="bold", color=TEXT,
             ha="center", va="top")
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
    slide_footer(fig, k, n_slides, source, footnote)
    return fig
