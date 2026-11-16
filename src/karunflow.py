"""«آبِ کارون کجا رفت؟» (karunflow_fa): the Karun's own before and after, from its gauge at Ahvaz, on the map of the
river (the satellite mosaic of 2016, the record's last year). One film, music only.

The owner, 16 Nov 2026, on the satellite cut (karun_fa: the Gotvand lake and the fields south of Ahvaz appearing): "I
don't see why it should be critical for Karun. You don't show before after thingy for Karun", then "use the gauge data,
rebuild Karun around the river flow". The river looks the same from space in late summer (research/feasibility/
feas_karun); its loss is in the gauge record.

The data: the Karun at Ahvaz, GRDC station 2423500 (provider: Iran's Ministry of Energy), from the GRDC download of June
2022 on PIK's cluster, extracted to the git-ignored data/karun/grdc (NOTES.md there). GRDC's policy guidelines (Annex 2):
the data are not transferred "in part or total to third parties or to the general public (e.g. by electronic media),
without the written consent of the GRDC", and publications cite "The Global Runoff Data Centre, 56068 Koblenz, Germany".
So only period means and mean years leave this file, never a year's value, and nothing of the record is in the repo; the
owner requests the station in his own name and writes to GRDC before posting.

What the record supports (asserted below; checked the same day by a second session from the same file):
- GRDC's monthly series: since 1950 the months are the daily means (identical where both exist); a month with only part
  of its days is the mean of those days; some months have no daily values (the provider's monthly data). Water years
  October-September, named by the year they end (Persian year = that year - 621); complete = all 12 months.
- 1379-1386 (2000-07) against 1387-1395 (2008-16): about half, the same in the years whose daily record is complete
  (every year of both periods but 1381 = 2002 is). This pair is the whole film's comparison (the opening's bars and the
  mean years), because it does not depend on how months with part of their days are counted.
- 1387-1395 is the lowest nine-year run of the record, in the monthly series and in the daily-complete years, and every
  year of it is under 400 m3/s.
- The earlier periods (1330-1355, 1356-1378) are about as high as 1379-1386 in GRDC's monthly values, but lower when
  the months with part of their days are left out (printed): not on screen, said in the first comment with the count
  of incomplete years. The spring flood (April) is less than half after 1386 however those months are treated.
- Upstream precipitation (CRU TS 4.10, October-April, a box over the Karun and Dez basins) was lower in 2008-16 than in
  1951-2007 (printed): the dry years are named first among the causes; how much each cause took is not known (no
  source gives shares; Tani et al. 2025 find the flow above the dams falling too, 1993-2022).
Not claimed: anything after Shahrivar 1395 (the record's end; the floods of 1398 are not in it), the fields south of
Ahvaz (they take their water below the gauge), shares of the causes, a rain-against-flow ratio.

    python -I src/karun.py          # the map card and the locator (first)
    python -I src/karunflow.py      # film.json
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import karun  # noqa: E402  (the map of the river and the locator: outputs/onebit/karun)
from onebit import fa  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "outputs" / "onebit" / "karunflow"
GRDC = ROOT / "data" / "karun" / "grdc" / "grdc_extract.txt"
STATION = "2423500"
FPS, W, H = 30, 1080, 1920
FIRST, LAST = 1951, 2016                              # the water years of the daily record (Mehr 1329 to Shahrivar 1395)
PERIODS = ((1951, 1976), (1977, 1999), (2000, 2007), (2008, 2016))
PAIR = (2, 3)                                         # the opening: 1379-1386 against 1387-1395
BEFORE_YEAR = (1951, 2007)                            # the years before 1387 (printed; the rain's comparison)
RAIN_BOX = (48.5, 52.0, 30.5, 34.0)                   # W, E, S, N: the Karun and Dez basins above Ahvaz, as a box


def solar(y: int) -> int:
    return y - 621                                    # the water year ending in September of y ends in Shahrivar y - 621


def r10(v: float) -> int:
    return int(np.floor(v / 10 + 0.5)) * 10


def load() -> tuple[pd.Series, pd.Series]:
    d, m = {}, {}
    for line in GRDC.read_text().splitlines():
        p = line.split()
        if len(p) == 4 and p[1] == STATION:
            (d if p[0] == "daily" else m if p[0] == "monthly" else {})[pd.Timestamp(p[2])] = float(p[3])
    d, m = pd.Series(d).sort_index(), pd.Series(m).sort_index()
    return d[d >= 0], m[m >= 0]


def wy(index: pd.DatetimeIndex) -> np.ndarray:
    return np.asarray(index.year + (index.month >= 10))


def years_monthly(m: pd.Series, keep: pd.Series | None = None) -> pd.Series:
    """Water-year means of the monthly series over the complete water years (12 months; keep drops months)."""
    s = m if keep is None else m[keep]
    g = s.groupby(wy(s.index))
    out = g.mean()[g.size() == 12]
    return out[(out.index >= FIRST) & (out.index <= LAST)]


def years_daily(d: pd.Series) -> pd.Series:
    """Water-year means of the daily record over the years with at least 95 % of their days."""
    g = d.groupby(wy(d.index))
    days = pd.Series({y: 366 if pd.Timestamp(y, 2, 28).is_leap_year else 365 for y in g.size().index})
    out = g.mean()[g.size() / days >= 0.95]
    return out[(out.index >= FIRST) & (out.index <= LAST)]


def mean(s: pd.Series, a: int, b: int) -> float:
    return float(s[(s.index >= a) & (s.index <= b)].mean())


def partial_months(d: pd.Series, m: pd.Series) -> pd.Series:
    cnt = d.groupby([d.index.year, d.index.month]).size()
    cnt.index = [pd.Timestamp(y, k, 1) for y, k in cnt.index]
    n = cnt.reindex(m.index).fillna(0)
    full = pd.Series([t.days_in_month for t in m.index], index=m.index)
    return (n > 0) & (n < 0.9 * full)


def mean_year(m: pd.Series, years: pd.Index, a: int, b: int) -> list:
    """The mean of each month, October to September, over the complete water years a-b."""
    w = wy(m.index)
    s = m[np.isin(w, years) & (w >= a) & (w <= b)]
    g = s.groupby(s.index.month).mean()
    return [float(g[k]) for k in (10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8, 9)]


def record() -> dict:
    d, m = load()
    am, ad = years_monthly(m), years_daily(d)
    part = partial_months(d, m)
    strict = years_monthly(m, ~part)
    missing = [y for y in range(FIRST, LAST + 1) if y not in am.index]
    per = [dict(a=a, b=b, label=[fa(solar(a)), fa(solar(b))], n=int(((am.index >= a) & (am.index <= b)).sum()),
                mean=mean(am, a, b), daily=mean(ad, a, b), strict=mean(strict, a, b)) for a, b in PERIODS]
    print(f"GRDC {STATION}: {len(am)} complete water years {FIRST}-{LAST}; incomplete: {missing}")
    for p in per:
        print(f"  {p['a']}-{p['b']} ({p['label'][0]}-{p['label'][1]}): monthly series {p['mean']:.0f} m3/s (n {p['n']}), "
              f"daily-complete {p['daily']:.0f}, without part-day months {p['strict']:.0f}")
    assert len(missing) == 12, missing                                       # «۱۲ سال آمارِ کامل ندارند»
    a, b = per[PAIR[0]], per[PAIR[1]]
    # the opening's pair: about half, the same in both series (both periods have complete daily years)
    assert abs(a["mean"] - a["daily"]) < 10 and abs(b["mean"] - b["daily"]) < 10, (a, b)
    assert 0.45 < b["mean"] / a["mean"] < 0.55 and 0.45 < b["daily"] / a["daily"] < 0.55, (a, b)
    # 1387-1395: every year under 400, the lowest nine-year run in both series
    last = am[am.index >= PERIODS[3][0]]
    assert len(last) == 9 and last.max() < 400, last.max()
    for name, s in (("monthly", am), ("daily-complete", ad)):
        runs = [(y0, s[(s.index >= y0) & (s.index <= y0 + 8)]) for y0 in range(FIRST, LAST - 7)]
        runs = [(y0, x.mean()) for y0, x in runs if len(x) >= 6]
        low = min(runs, key=lambda q: q[1])
        print(f"  lowest nine-year run ({name}): {low[0]}-{low[0] + 8}, {low[1]:.0f} m3/s")
        assert low[0] == PERIODS[3][0], (name, low)
    # the mean years of the pair (on screen) and of all years before 1387 (printed): the spring flood less than half
    # after 1386, however the part-day months are treated
    before, after = mean_year(m, am.index, *PERIODS[PAIR[0]]), mean_year(m, am.index, *PERIODS[PAIR[1]])
    apr = 6                                                                  # October = 0 ... April = 6
    for name, s, yrs in (("monthly", m, am.index), ("without part-day months", m[~part], strict.index)):
        for a0_, b0_ in (PERIODS[PAIR[0]], BEFORE_YEAR):
            b0, a0 = mean_year(s, yrs, a0_, b0_)[apr], mean_year(s, yrs, *PERIODS[3])[apr]
            print(f"  April ({name}): {a0_}-{b0_} {b0:.0f} -> {PERIODS[3][0]}-{PERIODS[3][1]} {a0:.0f} m3/s ({100 * (a0 / b0 - 1):+.0f} %)")
            assert a0 < 0.5 * b0, (name, b0, a0)
    print("  mean year, Oct-Sep, before:", [round(v) for v in before], "after:", [round(v) for v in after])
    return dict(periods=per, before=before, after=after, missing=len(missing), last_max=float(last.max()))


def rain() -> dict:
    """October-April precipitation over the basins (CRU TS 4.10), printed: how prominently the dry years are named."""
    import glob
    import xarray as xr
    w, e, s, n = RAIN_BOX
    parts = []
    for f in sorted(glob.glob(str(ROOT / "data" / "water" / "cru_ts4.10.*.pre.dat.nc"))):
        ds = xr.open_dataset(f).sel(lon=slice(w, e), lat=slice(s, n))
        parts.append(ds["pre"].weighted(np.cos(np.radians(ds.lat))).mean(("lat", "lon")).to_series())
    p = pd.concat(parts).sort_index()
    p = p[~p.index.duplicated()]
    p = p[p.index.month.isin([10, 11, 12, 1, 2, 3, 4])]
    g = p.groupby(wy(p.index))
    oa = g.sum()[g.size() == 7]
    b, a = mean(oa, *BEFORE_YEAR), mean(oa, *PERIODS[3])
    print(f"CRU October-April over {RAIN_BOX}: {BEFORE_YEAR[0]}-{BEFORE_YEAR[1]} {b:.0f} mm, {PERIODS[3][0]}-{PERIODS[3][1]} {a:.0f} mm ({100 * (a / b - 1):+.0f} %)")
    assert a < 0.9 * b, (b, a)                                               # «همان سال‌ها خشک‌تر هم بودند»
    return dict(before=b, after=a)


def assets() -> dict:
    """The map of the river and the corner locator, as the satellite cut built them (src/karun.py)."""
    k = json.loads((karun.BUILD / "film.json").read_text(encoding="utf-8"))
    BUILD.mkdir(parents=True, exist_ok=True)
    for f in (k["card"]["file"], k["locator"]["file"]):
        shutil.copy2(karun.BUILD / f, BUILD / f)
    return dict(card=k["card"], locator=k["locator"])


NEW = dict(
    hook="آبِ {کارون} کجا رفت؟", gauge="کارون در اهواز: میانگینِ جریان", unit="مترمکعب در ثانیه", half="نصف",
    station="ایستگاهِ اهواز", period="{} تا {}", low_small="هر ۹ سال زیرِ ۴۰۰ مترمکعب در ثانیه",
    seasons=("پاییز", "زمستان", "بهار", "تابستان"),
    year_head="سیلابِ بهار // {کمتر از نصف} شد",
    why_head="همان سال‌ها {خشک‌تر} هم بودند", why_small="و بالادست: سدهای تازه، انتقالِ آب، کشاورزی",
    share="سهمِ هر عامل محلِ بحث است", lake="سدِ گتوند، ۱۳۹۰", transfer="به فلاتِ مرکزی",
    close="شما {کارونِ پُرآب} را // دیده‌اید؟", follow=["برای کسی بفرستید", "که اهلِ خوزستان است"],
    src_gauge="جریان: وزارتِ نیرو، از GRDC (کوبلنتس، آلمان)؛ سالِ آبی: مهر تا شهریور",
    src_map="زمین: Sentinel-2 cloudless (EOX)، ۲۰۱۶؛ رود: OpenStreetMap",
    src_why="بارش: CRU TS 4.10؛ منابع در کامنتِ اول",
)


def cut() -> dict:
    hook = (0.0, 7.0)
    low = (hook[1], hook[1] + 7.3)
    year = (low[1], low[1] + 6.6)
    why = (year[1], year[1] + 9.3)
    close = (why[1], why[1] + 7.4)
    back = (close[1] - 0.7, close[1])
    return dict(
        scenes=dict(hook=hook, low=low, year=year, why=why, close=close), end=close[1], cover_t=2.6,                              # both bars and the half mark (frame 0 has the first bar)
        cues=dict(grow=(0.35, 1.9), tick=(1.9, 2.3), labels=2.6, locator=(0.0, 6.0), low_small=low[0] + 0.9,
                  curve_b=(year[0] + 0.5, year[0] + 1.6), curve_a=(year[0] + 1.9, year[0] + 3.0), spring=year[0] + 3.2,
                  lake=why[0] + 1.0, transfer=why[0] + 1.7, small=why[0] + 2.4, share=why[0] + 3.4,
                  follow=close[0] + 2.4, caveat=close[0] + 0.8, back=back),
    )


def reading(Wd: dict, c: dict, labels: dict) -> None:
    """The owner's reading rule (src/onebit_reading.py) on every scene, asserted."""
    import onebit_reading as rd
    S, Q = c["scenes"], c["cues"]
    wt = lambda xs: sum(rd.weight(x) for x in xs)    # noqa: E731
    plan = [
        ("hook", S["hook"], [Wd["hook"], Wd["gauge"]], [*labels["pair"], *labels["pair_n"], Wd["unit"], Wd["half"], Wd["station"]], Q["labels"]),
        ("low", S["low"], [Wd["low_head"], Wd["low_small"]], [*labels["pair"], *labels["pair_n"]], Q["low_small"]),
        ("year", S["year"], [Wd["year_head"]], [*Wd["seasons"], *labels["legend"]], Q["spring"]),
        ("why", S["why"], [Wd["why_head"], Wd["why_small"], Wd["share"]], [Wd["lake"], Wd["transfer"]], Q["share"]),
        ("close", (S["close"][0], Q["back"][0]), [Wd["close"], *Wd["follow"]], [labels["caveat"]], Q["follow"]),
    ]
    print("\nreading (words in full + labels at half weight; seconds the rule needs, seconds given):")
    total = 0.0
    for name, (a, b), full, half, last in plan:
        w = wt(full) + rd.LABELS * wt(half)
        need = max(rd.SETTLE + w / rd.WPS, last - a + rd.HOLD)
        total += w
        print(f"  {name:6s} {wt(full):5.1f} + {wt(half):4.1f}/2 words, last string at {last - a:4.1f} s -> {need:4.1f} s needed, {b - a:4.1f} s given")
        assert b - a + 0.051 >= need, (name, round(need, 2), round(b - a, 2))
    print(f"  {total:.0f} weighted words in {c['end']:.1f} s")


def main() -> None:
    R = record()
    rn = rain()
    A = assets()
    per = R["periods"]
    pair = [per[PAIR[0]], per[PAIR[1]]]
    label = lambda p: NEW["period"].format(*p["label"])                     # noqa: E731
    c = cut()
    low_head = f"{fa(solar(PERIODS[3][0]))} تا {fa(solar(PERIODS[3][1]))}: // {{کم‌آب‌ترین ۹ سالِ پیاپیِ}} آمار"   # a run of nine, not the nine lowest single years (1379 and 1380 are among those)
    caveat = f"آمارِ ایستگاه تا {fa(solar(LAST))} است"
    legend = [label(p) for p in pair]
    labels = dict(pair=[label(p) for p in pair], pair_n=[fa(r10(p["mean"])) for p in pair], legend=legend, caveat=caveat)
    words = dict(NEW, low_head=low_head, caveat=caveat, legend=legend)
    reading(words, c, labels)
    k = json.loads((karun.BUILD / "film.json").read_text(encoding="utf-8"))
    film = dict(
        fps=FPS, size=[W, H], cut=c, end=c["end"], cover_t=c["cover_t"], card=A["card"], locator=A["locator"], words=words,
        pair=[dict(label=label(p), value=r10(p["mean"]), shown=fa(r10(p["mean"]))) for p in pair],
        periods=[dict(label=label(p), mean=round(p["mean"]), daily=round(p["daily"]), strict=round(p["strict"]), n=p["n"]) for p in per],   # for the comment, not drawn
        year=dict(before=[round(v) for v in R["before"]], after=[round(v) for v in R["after"]]),
        places=dict(ahvaz=karun.AHVAZ, dam=karun.DAM, transfer_from=(49.62, 32.55)),
        colours=dict(gold="#F6C445", ink="#1d140c", paper="#FBF7F0", river="#49c0ff", before="#3F8FBF", after="#D9573B"),
        rain=dict(before=round(rn["before"]), after=round(rn["after"])),
    )
    assert k["card"]["box"] == A["card"]["box"]
    (BUILD / "film.json").write_text(json.dumps(film, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", BUILD / "film.json", "| end", c["end"])


if __name__ == "__main__":
    main()
