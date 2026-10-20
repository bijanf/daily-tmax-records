"""Europe's extremes scoreboard as a 1-bit desktop (numbers in extremes.py, style in onebit.py).

How often days >= 35 C, hot nights, dry seasons, downpours and frost days happen in 2016-2025
against 1961-1990; the year of each station's warmest night ever; each station's change in
its own hot days; and Vienna, the one station whose two wettest days on record fell in the
same recent year.

    outputs/onebit/europe_scoreboard[_<theme>].png       2160 x 2700 poster (no suffix for beton)
    outputs/onebit/europe_scoreboard[_<theme>].mp4       1080 x 1350, 32 s animation
    outputs/onebit/social/europe_scoreboard_<theme>_reel.mp4, _cover.png, _slide1-5.png
                                                         30 s Instagram reel loop and carousel (--social)

    python -I src/plot_onebit_extremes.py --no-video --social   # Instagram cut in Beton
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

import extremes  # noqa: E402
import onebit  # noqa: E402
from onebit import Race, Story  # noqa: E402

SOURCES = "Data: NOAA GHCN-Daily · DWD · SMHI · KNMI · GeoSphere · MeteoSwiss"


def story(d: dict) -> Story:
    st, score, nights = d["st"], d["score"], d["nights"]
    hot35, hot = score["hot35"], score["hot_own"]
    ratio = (hot["recent"] / hot["base"]).reindex(st.index)

    stations = st[["name", "country", "lat", "lon"]].copy()
    stations["year"] = nights["year"].reindex(st.index)
    stations["cls"] = np.select([ratio > 5, ratio > 3, ratio > 2, ratio > 0], [3, 2, 1, 0], -1)
    stations["hit"] = ratio > 1

    def row(label, chip, key, scale=1.0, unit=" /yr", digits=1):
        f = score[key]
        return Race(label, chip, f["recent"].mean() * scale, f["base"].mean() * scale, unit=unit, digits=digits)

    race = [row("35°C days", "hot", "hot35", digits=2), row("hot nights", "hot", "nights"),
            row("dry season", "ink", "dry", 100, "%", 0), row("downpours", "cold", "downpours"),
            row("frost days", "cold", "frost", digits=0)]

    wien = d["wet"].loc["AU000005901"]
    b, r = hot35["base"].mean(), hot35["recent"].mean()
    n = len(hot35)
    return Story(
        os_name="EU.XTRM.OS1", app="EU.XTRM 1.1",
        lead="Europe 2016–2025 vs 1961–1990", tail="Days at 35 °C or more",
        big=r / b, big_fmt="×{:.1f}", big_digits=1,
        stats=[(r, "days ≥ 35 °C a year now", 2), (b, "a year in 1961–1990", 2)],
        note=f"*average of {n} stations with daily data in both periods · one scoreboard, five extremes",
        secret=" ".join(f"{k}={score[k]['base'].mean():.2f}>{score[k]['recent'].mean():.2f}"
                        for k in ("hot35", "nights", "dry", "downpours", "frost")) + " ",
        final_year=int(nights["year"].max()), stations=stations,
        map_title="year of each station's warmest night ever",
        grid_title="hot days vs 1961–90, per station", grid_chip="MORE HOT DAYS",
        grid_labels=("<2x", "2–3x", "3–5x", ">5x"),
        race_title="Extremes.Score", race_center="x1",
        race_left="< rarer than 1961–90", race_right="more often >", race=race,
        widget_title="Wettest.Days 1.1", widget_line=f"Wien · {wien['d1']:%Y}", widget_n=2,
        widget_words=("wettest days", f"since {wien['first']}"),
        notes=["35°C days, hot nights (min ≥ 20 °C), frost days (min < 0 °C): per year.",
               f"Downpours: rain above the station's own 1961–90 99th percentile ({d['p99'].median():.0f} mm).",
               "Dry season: Mar–Aug rain minus evaporation below its own 10th percentile.",
               SOURCES],
        loader_line=f"{len(st)} stations, 5 extremes", icon="bolt")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", nargs="+", default=["beton"], choices=[*onebit.THEMES, "all"], help="colour themes")
    ap.add_argument("--no-video", action="store_true", help="posters only")
    ap.add_argument("--web", action="store_true", help="also a small video without the shimmer")
    ap.add_argument("--social", action="store_true",
                    help="also the 30 s loop as an Instagram reel (9:16, with cover) and a 4:5 carousel")
    args = ap.parse_args()
    onebit.render(story(extremes.compute()), args.theme, "europe_scoreboard", "beton", not args.no_video,
                  args.web, args.social)


if __name__ == "__main__":
    main()
