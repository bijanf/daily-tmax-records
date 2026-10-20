"""Europe's heat extremes as a 1-bit desktop (style and motion in onebit.py).

Heat records against cold records since 2020, the year of each station's hottest day ever,
each station's own heat : cold ratio, the decades as a race, and the day in 2026 when most
stations measured their hottest day ever.

    outputs/onebit/europe_extremes[_<theme>].png       2160 x 2700 poster (no suffix for pink)
    outputs/onebit/europe_extremes[_<theme>].mp4       1080 x 1350, 32 s: the poster assembling itself
    outputs/onebit/europe_extremes[_<theme>]_web.mp4   the same without the shimmer, small enough
                                                       for a web page (--web)

    python -I src/plot_onebit.py                        # pink poster and animation
    python -I src/plot_onebit.py --theme berlin xberg   # chosen themes
    python -I src/plot_onebit.py --theme all --no-video # every theme, posters only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import findings  # noqa: E402
import onebit  # noqa: E402
from onebit import Race, Story  # noqa: E402

SOURCES = "Data: NOAA GHCN-Daily · DWD · SMHI · KNMI · GeoSphere · MeteoSwiss"
# station grid: heat:cold ratio of 2020-latest, upper bound of each class
BOUNDS = (10, 20, 50, np.inf)


def story(f: dict) -> Story:
    """Numbers behind the poster, Europe only: decades, stations, hottest days."""
    fy = f["final_year"]
    rows = f["region"] == "Europe"
    w = f["window"][rows]
    h20 = ((f["hi_year"][rows] >= 2020) & w).sum(axis=1)
    c20 = ((f["lo_year"][rows] >= 2020) & w).sum(axis=1)
    st = f["idx"].loc[rows, ["name", "country", "lat", "lon"]].copy()
    ratio = np.where(c20 > 0, h20 / np.maximum(c20, 1), np.inf)
    st["year"] = f["hot"].loc[st.index, "year"]
    st["cls"] = np.searchsorted(BOUNDS, ratio, side="right").clip(max=3)
    st["hit"] = h20 > c20

    periods = [("1880–1989", 1880, 1989), ("1990s", 1990, 1999), ("2000s", 2000, 2009),
               ("2010s", 2010, 2019), ("2020s", 2020, fy)]
    race = []
    for label, y0, y1 in periods:
        heat, cold = findings.record_counts(f, "Europe", y0, y1)
        race.append(Race(label, "cold" if heat < cold else "hot" if label == "2020s" else "ink", heat, cold))

    hot_date = f["hot"].loc[st.index, "date"]
    latest = hot_date[st["year"] == fy].value_counts()
    day, n_day = pd.Timestamp(latest.index[0]), int(latest.iloc[0])
    sig = findings.significance(f)
    p = max(sig["n_exceed"], 1) / sig["n_draw"]
    n = len(st)
    return Story(
        os_name="EU.TMAX.OS1", app="EU.TMAX 1.1",
        lead=f"Europe 2020–{fy}", tail="Heat records per cold record",
        big=sig["observed"], big_fmt="{} : 1",
        stats=[(sig["heat"], "heat records"), (sig["cold"], "cold records")],
        note=f"*{n} stations, each with >100 years of daily data · year-shuffle test "
             f"p < {p:.0e}".replace("e-0", "e-"),
        secret=f"heat={sig['heat']} cold={sig['cold']} ratio={sig['observed']:.1f} stations={n} p<{p:.0e} ",
        final_year=fy, stations=st,
        map_title="year of each station's hottest day ever",
        grid_title="heat : cold records per station", grid_chip="HEAT > COLD",
        grid_labels=("<10:1", "10–20", "20–50", "≥50:1"),
        race_left="< more cold records", race_right="more heat records >", race=race,
        widget_title="Hottest.Day 1.1", widget_line=day.strftime("%a, %b %d, %Y"), widget_n=n_day,
        widget_words=("stations", "all-time high"),
        notes=["Heat record: the hottest day ever measured on that calendar date.",
               "Cold record: the coldest daily maximum. p: 200,000 year shuffles.",
               f"{n} stations, each >100 years of daily TMAX. Izaña not mapped.",
               SOURCES],
        loader_line=f"{n} stations, records, copy", icon="thermometer")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", nargs="+", default=["pink"], choices=[*onebit.THEMES, "all"], help="colour themes")
    ap.add_argument("--no-video", action="store_true", help="posters only")
    ap.add_argument("--web", action="store_true", help="also a small video without the shimmer")
    args = ap.parse_args()
    onebit.render(story(findings.compute()), args.theme, "europe_extremes", "pink",
                  not args.no_video, args.web)


if __name__ == "__main__":
    main()
