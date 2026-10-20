"""Europe's drought as a 1-bit desktop (numbers in drought.py, style and motion in onebit.py).

Stations whose driest growing season (March to August, rain minus evaporation) on record
fell in the 2020s, against rain alone and against a stable climate; the year of each
station's driest season; each station's driest 2020s season as a rank; the decades as a race
of dry against wet records, with and without evaporation; and the stations whose 2026 season
was their driest on record.

    outputs/onebit/europe_drought[_<theme>].png       2160 x 2700 poster (no suffix for sand)
    outputs/onebit/europe_drought[_<theme>].mp4       1080 x 1350, 32 s animation
    outputs/onebit/europe_drought[_<theme>]_web.mp4   the same without the shimmer (--web)

    python -I src/plot_onebit_drought.py                     # Streusand poster and animation
    python -I src/plot_onebit_drought.py --theme berlin --no-video
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

import drought  # noqa: E402
import onebit  # noqa: E402
from onebit import Race, Story  # noqa: E402


def best_2020s_rank(ranks: dict) -> float:
    return min([r for y, r in ranks.items() if y >= 2020], default=np.nan)


def story(d: dict) -> Story:
    bal, rain, idx = d["balance"], d["rain"], d["idx"]
    fy = max(max(ys) for ys in bal["years"])
    first = min(min(ys) for ys in bal["years"])

    st = idx.loc[bal.index, ["name", "country", "lat", "lon"]].copy()
    st["year"] = bal["dry_year"]
    best = bal["rank"].map(best_2020s_rank)
    # grid class, light to dark: rank > 10, 4-10, 2-3, the driest on record; -1 without a 2020s season
    st["cls"] = np.select([best == 1, best <= 3, best <= 10, best > 10], [3, 2, 1, 0], -1)
    st["hit"] = best == 1

    race = []
    for label, y0, y1 in drought.PERIODS:
        dry, wet, _ = drought.period_counts(bal, y0, y1)
        r_dry, r_wet, _ = drought.period_counts(rain, y0, y1)
        label = f"{first}–1989" if y0 == 0 else label
        race.append(Race(label, "cold" if dry < wet else "hot" if label == "2020s" else "ink", dry, wet,
                         ghost=r_dry / max(r_wet, 0.25)))

    # the 2020s on equal footing: only stations with a complete 2020s water-balance season
    with20 = st.index[st["cls"] >= 0]
    n_dry, _, expected = drought.period_counts(bal, 2020, fy)
    n_rain, _, _ = drought.period_counts(rain.loc[rain.index.intersection(with20)], 2020, fy)
    sig = drought.significance(bal, 2020, fy)
    p = max(sig["n_exceed"], 1) / sig["n_draw"]
    has = bal[bal["years"].map(lambda ys: fy in ys)]
    n_latest = int((has["dry_year"] == fy).sum())
    n = len(bal)
    return Story(
        os_name="EU.DRY.OS1", app="EU.DRY 1.1",
        lead=f"Europe 2020–{fy}", tail="Stations with a record-dry growing season",
        big=n_dry, big_fmt="{}",
        stats=[(n_rain, "from rain alone"), (round(expected), "in a stable climate")],
        note=f"*of {len(with20)} stations with 2020s data · Mar–Aug rain minus evaporation (Hargreaves) · "
             f"p < {p:.0e}".replace("e-0", "e-"),
        secret=f"dry={n_dry} rain_only={n_rain} expected={expected:.1f} stations={len(with20)} p<{p:.0e} ",
        final_year=fy, stations=st,
        map_title="year of each station's driest Mar–Aug",
        grid_title="driest 2020s season, rank", grid_chip="RECORD DRY",
        grid_labels=("rank>10", "4–10", "2–3", "record"),
        race_left="< more wet records", race_right="more dry records >", race=race,
        race_legend=("rain alone", "with evaporation"),
        widget_title="Driest.Season 1.1", widget_line=f"Mar–Aug {fy}", widget_n=n_latest,
        widget_words=("stations", "driest ever"),
        notes=["Growing season: March to August. Evaporation: Hargreaves (1985),",
               "from daily Tmax and Tmin. Record: the station's own driest season.",
               f"{n} stations (>=50 seasons); {len(with20)} with 2020s data, {len(has)} in {fy}.",
               "Data: NOAA GHCN-Daily · p: 200,000 year shuffles"],
        loader_line=f"{n} stations, rain, evaporation", icon="drop")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", nargs="+", default=["sand"], choices=[*onebit.THEMES, "all"], help="colour themes")
    ap.add_argument("--no-video", action="store_true", help="posters only")
    ap.add_argument("--web", action="store_true", help="also a small video without the shimmer")
    args = ap.parse_args()
    onebit.render(story(drought.compute()), args.theme, "europe_drought", "sand", not args.no_video, args.web)


if __name__ == "__main__":
    main()
