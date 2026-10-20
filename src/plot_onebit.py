"""Europe's heat extremes as a 1-bit desktop (style and motion in onebit.py).

Heat records against cold records since 2020, the year of each station's hottest day ever,
each station's own heat : cold ratio, the decades as a race, and the day in 2026 when most
stations measured their hottest day ever.

    outputs/onebit/europe_extremes[_<theme>].png       2160 x 2700 poster (no suffix for pink)
    outputs/onebit/europe_extremes[_<theme>].mp4       1080 x 1350, 32 s: the poster assembling itself
    outputs/onebit/europe_extremes[_<theme>]_web.mp4   the same without the shimmer, small enough
                                                       for a web page (--web)
    outputs/onebit/social/europe_extremes_<theme>_reel.mp4, _cover.png, _slide1-5.png
                                                       30 s Instagram reel loop and carousel (--social)

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
from onebit import BIG_NUMBER, FOLLOW, FA_MONTHS, FULL, GRID, RACE, WIDGET, Race, Scene, Story, fa  # noqa: E402

SOURCES = "Data: NOAA GHCN-Daily · DWD · SMHI · KNMI · GeoSphere · MeteoSwiss"
# station grid: heat:cold ratio of 2020-latest, upper bound of each class
BOUNDS = (10, 20, 50, np.inf)


def story(f: dict, lang: str = "en", cut: str = "long") -> Story:
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
    hot = f["hot"].loc[st.index]
    on_day = hot[hot["date"] == day]
    named = " · ".join(f"{name} {on_day.loc[sid, 'value']:.1f} °C" for sid, name in
                       (("GM000003342", "Potsdam"), ("GM000003319", "Berlin-Dahlem")) if sid in on_day.index)
    old, mid, now = race[0], race[3], race[4]
    # the story cut: one message per scene, 20 bars = 37.5 s
    scenes = (
        Scene(2, FULL, "Is Europe breaking more {heat records} than cold ones?",
              f"{n} weather stations, each with 100+ years of data"),
        Scene(3, BIG_NUMBER, f"Since 2020: {{{sig['observed']:.0f} heat records}} for every cold one",
              f"{sig['heat']:,} heat records · {sig['cold']:,} cold records", count=True),
        Scene(2, RACE, "Until 1990, {cold records} won",
              f"{old.b:,} cold against {old.a:,} heat records, 1880–1989", focus=0),
        Scene(2, RACE, f"2000s and 2010s: {{{mid.a / mid.b:.0f} heat records}} per cold one",
              "the balance tipped in the 1990s", focus=3),
        Scene(2, RACE, f"2020s: {{{now.a / now.b:.0f} to 1}}", f"{now.a:,} heat · {now.b:,} cold records", focus=4),
        Scene(2, GRID, f"{{{int(st['hit'].sum())} of {n}}} stations lean hot",
              f"{int((c20 == 0).sum())} have not set a single cold record since 2020"),
        Scene(3, WIDGET, f"{day:%-d %B %Y}: {{{n_day} stations}} hit their hottest day ever", named),
        Scene(4, FULL, f"Europe now breaks {{{sig['observed']:.0f} heat records}} for every cold one.",
              FOLLOW["en"]),
    )
    if cut == "one":
        scenes = (
            Scene(4, FULL, "Is Europe breaking more {heat} records or {cold} records?",
                  "the continent's longest-running weather stations"),
            Scene(6, BIG_NUMBER, f"{{{sig['observed']:.0f} heat records}} for every cold one",
                  "since 2020", count=True),
            Scene(6, FULL, "Europe is breaking heat records, {not cold ones.}", FOLLOW["en"]),
        )
    if lang == "fa":
        r = sig["observed"]
        named = " · ".join(f"{city} {fa(format(on_day.loc[sid, 'value'], '.1f'))} درجه" for sid, city in
                           (("GM000003342", "پوتسدام"), ("GM000003319", "برلین-دالم")) if sid in on_day.index)
        scenes = (
            Scene(2, FULL, "اروپا بیشتر {رکورد گرما} می‌شکند یا رکورد سرما؟",
                  fa(f"{n} ایستگاه هواشناسی، هرکدام با دست‌کم 100 سال داده")),
            Scene(3, BIG_NUMBER, fa(f"از 2020 تا امروز: {{{r:.0f} رکورد گرما}} در برابر هر رکورد سرما"),
                  fa(f"{sig['heat']:,} رکورد گرما · {sig['cold']:,} رکورد سرما"), count=True),
            Scene(2, RACE, "تا ۱۹۹۰، {رکوردهای سرما} برنده بودند",
                  fa(f"{old.b:,} رکورد سرما در برابر {old.a:,} رکورد گرما، 1880 تا 1989"), focus=0),
            Scene(2, RACE, fa(f"دهه‌های 2000 و 2010: {{{mid.a / mid.b:.0f} رکورد گرما}} به ازای هر رکورد سرما"),
                  "کفه‌ی ترازو در دهه‌ی ۱۹۹۰ به سمت گرما چرخید", focus=3),
            Scene(2, RACE, fa(f"دهه‌ی 2020: {{{now.a / now.b:.0f} به 1}}"),
                  fa(f"{now.a:,} رکورد گرما · {now.b:,} رکورد سرما"), focus=4),
            Scene(2, GRID, fa(f"{{{int(st['hit'].sum())} از {n}}} ایستگاه به سمت گرما رفته‌اند"),
                  fa(f"{int((c20 == 0).sum())} ایستگاه از 2020 حتی یک رکورد سرما هم نداشته‌اند")),
            Scene(3, WIDGET, fa(f"{day.day} {FA_MONTHS[day.month]} {day.year}: {{{n_day} ایستگاه}} "
                                "گرم‌ترین روز تاریخشان را ثبت کردند"), named),
            Scene(4, FULL, fa(f"اروپا حالا {{{r:.0f} رکورد گرما}} در برابر هر رکورد سرما می‌شکند."), FOLLOW["fa"]),
        )
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
        loader_line=f"{n} stations, records, copy", icon="thermometer",
        scenes=scenes, lang=lang, cut=cut if cut != "long" else "")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", nargs="+", default=["pink"], choices=[*onebit.THEMES, "all"], help="colour themes")
    ap.add_argument("--no-video", action="store_true", help="posters only")
    ap.add_argument("--web", action="store_true", help="also a small video without the shimmer")
    ap.add_argument("--lang", default="en", choices=["en", "fa"], help="language of the reel's captions")
    ap.add_argument("--cut", default="one", choices=["one", "long"],
                    help="reel: one message per scene in three scenes (one), or eight scenes (long)")
    ap.add_argument("--social", action="store_true",
                    help="also the 30 s loop as an Instagram reel (9:16, with cover) and a 4:5 carousel")
    args = ap.parse_args()
    onebit.render(story(findings.compute(), args.lang, args.cut), args.theme, "europe_extremes", "pink",
                  not args.no_video, args.web, args.social)


if __name__ == "__main__":
    main()
