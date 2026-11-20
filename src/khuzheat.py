"""The data of the Khuzestan heat film (khuzheat_fa): how many days a year reach 48 C at Abadan and at Ahvaz, in the
years around 1950 and in the last ten complete years, and what the film says with it.

The stations. NOAA's ISD archive holds the reports of the two stations (get_khuzheat.py). A day's maximum is the
station's own maximum report (the KA fields with code M), given to the local day in which the middle of the report's
period falls (a 24-hour maximum reported the next morning belongs to the day before; one afternoon cannot count
twice); a maximum more than 3 C above the highest hourly reading of its day is dropped as an error. The hourly
readings alone are not used for the count: there were 16 a day around 1950 and 40 a day now.
The count. Abadan's early reports are whole degrees Fahrenheit (118 F is 47.8 C, 119 F is 48.3 C), later ones fifths
and then tenths of a degree Celsius. So that all years are counted alike, a day is hot when its maximum, rounded to
the whole degree Fahrenheit, is 119 F or more: 48.3 C in the early reports, 48.2 C and 48.1 C in the later ones, and
in every case a true maximum above 48.06 C. On screen: «بالای ۴۸ درجه». (With a plain 48.0 C or more the early years
count the same and 2015 to 2024 count 41 a year, not 38: the days of exactly 48.0 C, which a whole-Fahrenheit report
could not show.) The count runs over May to September (11 Ordibehesht to 8 Mehr); no such day falls outside it. A
year counts when at least 140 of its 153 days have a maximum.
The eras. THEN: the eight complete years between 1949 and 1958 (1949 to 1955 and 1958). NOW: 2015 to 2024, the last
ten complete years (ISD ends on 24 August 2025). Between 1958 and 2000 the archive has no complete year of maximum
reports, so the years between are drawn from another estimate: ERA5-Land's hourly 2 m temperature at the station's
point, a model's estimate of air temperature, counted by the same rule and named as that on screen.
film() asserts every sentence of the film against these numbers.

    python -I src/khuzheat.py           # the numbers; outputs/onebit/khuzheat/film.json and the pictures
"""

from __future__ import annotations

import glob
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import get_khuzheat  # noqa: E402

ROOT = get_khuzheat.ROOT
DATA = get_khuzheat.DATA
BUILD = ROOT / "outputs" / "onebit" / "khuzheat"
FPS = 30
MONTHS = (5, 6, 7, 8, 9)                          # the count's months: 1 May to 30 September, 153 days
DAYS = 153
FULL = 140                                        # a year counts with at least this many days that have a maximum
HOT_F = 119                                       # whole degrees Fahrenheit: 48.3 C, «۴۸ درجه»
THEN, NOW = (1949, 1958), (2015, 2024)
AHVAZ_BEFORE = (2005, 2014)
ERA_THEN = (1950, 1959)                           # the model estimate's first ten years (it begins in 1950)
OK = list("0145ACIMPRU")                          # ISD quality flags that pass
LOCAL = pd.Timedelta(hours=3, minutes=30)
_CACHE: dict = {}


def hot(c) -> np.ndarray:
    """Whether a maximum in C, rounded to the whole degree Fahrenheit, reaches HOT_F."""
    return np.round(np.asarray(c, float) * 9.0 / 5.0 + 32.0) >= HOT_F


def isd(name: str) -> pd.DataFrame:
    if ("isd", name) not in _CACHE:
        sid = get_khuzheat.STATIONS[name]["isd"]
        cols = ("DATE", "TMP", "KA1", "KA2", "KA3", "KA4")
        d = pd.concat([pd.read_csv(f, dtype=str, low_memory=False, usecols=lambda c: c in cols)
                       for f in sorted(glob.glob(str(DATA / "isd" / f"{sid}_*.csv")))], ignore_index=True)
        d["utc"] = pd.to_datetime(d["DATE"])
        v = d["TMP"].fillna("+9999,9")
        x = pd.to_numeric(v.str.slice(0, 5), errors="coerce") / 10.0
        d["t"] = x.where((x < 60) & (x > -40) & v.str.slice(6, 7).isin(OK))
        _CACHE[("isd", name)] = d
    return _CACHE[("isd", name)]


def maxima(name: str) -> pd.Series:
    """The station's daily maximum (C) by local day, from its maximum reports."""
    d = isd(name)
    rows = []
    for c in ("KA1", "KA2", "KA3", "KA4"):
        if c not in d:
            continue
        s = d[c].dropna()
        p = s.str.split(",", expand=True)
        if p.shape[1] < 4:
            continue
        x = pd.to_numeric(p[2], errors="coerce") / 10.0
        ok = p[1].eq("M") & (x < 70) & (x > -40) & p[3].isin(OK)
        per = pd.to_numeric(p[0], errors="coerce")[ok] / 10.0
        rows.append(pd.DataFrame({"utc": d.loc[s.index, "utc"][ok], "x": x[ok], "per": per.where(per < 99)}))
    e = pd.concat(rows)
    mid = e["utc"] - pd.to_timedelta(e["per"].fillna(12.0) / 2, unit="h") + LOCAL        # the middle of the report's period, local
    ext = e.groupby(mid.dt.normalize())["x"].max()
    loc = d["utc"] + LOCAL
    peak = d.groupby(loc.dt.normalize())["t"].max()                                  # the day's highest hourly reading
    aft = d[loc.dt.hour.between(12, 17)].groupby(loc.dt.normalize())["t"].count()      # readings in the local afternoon
    a = pd.DataFrame({"ext": ext, "peak": peak, "aft": aft}).dropna(subset=["ext"])
    bad = (a["aft"] >= 2) & (a["ext"] > a["peak"] + 3.0)
    return a.loc[~bad, "ext"]


def years(name: str) -> pd.DataFrame:
    """Per year: the days with a maximum in May to September, the hot days among them, the year's highest and its day."""
    m = maxima(name)
    m = m[m.index.month.isin(MONTHS)]
    g = m.groupby(m.index.year)
    out = pd.DataFrame({"n": g.count(), "hot": g.apply(lambda s: int(hot(s.values).sum())), "top": g.max(),
                        "top_day": g.apply(lambda s: s.idxmax().strftime("%Y-%m-%d"))})
    return out


def reanalysis(name: str) -> pd.Series:
    """ERA5-Land's daily maximum of 2 m temperature (C) at the station's point, by local day."""
    z = zipfile.ZipFile(DATA / "era5" / f"era5land_{name}.zip")
    r = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])))
    loc = pd.to_datetime(r["valid_time"]) + LOCAL
    return (r["t2m"] - 273.15).groupby(loc.dt.normalize()).max()


def measures() -> dict:
    ab, ah = years("abadan"), years("ahvaz")
    full = lambda t, a, b: t[(t.n >= FULL) & (t.index >= a) & (t.index <= b)]                 # noqa: E731
    then, now = full(ab, *THEN), full(ab, *NOW)
    a0, a1 = full(ah, *AHVAZ_BEFORE), full(ah, *NOW)
    era = reanalysis("abadan")
    era = era[era.index.month.isin(MONTHS) & (era.index.year >= 1950) & (era.index.year <= 2026)]
    flag = pd.Series(hot(era.values), index=era.index)
    count = flag.groupby(flag.index.year).sum()
    doy = lambda day: (day - pd.Timestamp(year=day.year, month=5, day=1)).days                 # noqa: E731
    wall = {int(y): [int(doy(d)) for d in flag.index[(flag.index.year == y) & flag.values]] for y in count.index}
    top = ah.loc[(ah.n >= FULL)].sort_values("top").iloc[-1]
    allm = maxima("abadan")
    used = allm[allm.index.year.isin(list(then.index) + list(now.index)) & ~allm.index.month.isin(MONTHS)]
    outside = int(hot(used.values).sum())                 # hot days outside May to September in the years that are counted
    plain = lambda name, a, b: [int((v.values >= 48.0).sum()) for _, v in                      # noqa: E731  (a plain 48.0 C or more)
                                (lambda q: q[q.index.month.isin(MONTHS) & (q.index.year >= a) & (q.index.year <= b)].groupby(lambda d: d.year))(maxima(name))]
    stat = lambda t: dict(years=[int(y) for y in t.index], counts=[int(v) for v in t.hot], days=[int(v) for v in t.n],     # noqa: E731
                          mean=float(t.hot.mean()), low=int(t.hot.min()), high=int(t.hot.max()))
    return dict(then=stat(then), now=stat(now), ahvaz_before=stat(a0), ahvaz_now=stat(a1), outside=outside,
                ahvaz_all_top=float(maxima("ahvaz").max()), abadan_full=[int(y) for y in ab.index[ab.n >= FULL]],
                plain_now=float(np.mean(plain("abadan", *NOW))), isd_last=str(isd("abadan")["utc"].max().date()),
                plain_ahvaz=[float(np.mean(plain("ahvaz", *AHVAZ_BEFORE))), float(np.mean(plain("ahvaz", *NOW)))],
                ahvaz_top_hourly=float(isd("ahvaz").loc[(isd("ahvaz")["utc"] + LOCAL).dt.normalize() == pd.Timestamp(str(top.top_day)), "t"].max()),
                ahvaz_top=dict(value=float(top.top), day=str(top.top_day)),
                era=dict(years=[int(y) for y in count.index], counts=[int(v) for v in count.values], wall=wall,
                         then=float(count[(count.index >= ERA_THEN[0]) & (count.index <= ERA_THEN[1])].mean()),
                         now=float(count[(count.index >= NOW[0]) & (count.index <= NOW[1])].mean()),
                         decades={f"{a}": float(count[(count.index >= a) & (count.index <= a + 9)].mean()) for a in range(1950, 2020, 10)}))


def fa_year(y: int) -> int:
    """The Persian year in which the summer of a Gregorian year falls."""
    return y - 621


def half_up(x: float) -> int:
    return int(np.floor(x + 0.5))


def words_of(m: dict) -> dict:
    from onebit import fa
    import air
    y = lambda g: fa(fa_year(g))                                                               # noqa: E731
    assert air.jalali("1949-07-01")[0] == fa_year(1949) and air.jalali("2024-07-01")[0] == fa_year(2024)
    n_then, n_now = half_up(m["then"]["mean"]), half_up(m["now"]["mean"])
    then_span, now_span = f"{y(THEN[0])} تا {y(THEN[1])}", f"{y(NOW[0])} تا {y(NOW[1])}"
    code = lambda name: get_khuzheat.STATIONS[name]["isd"][:5]          # noqa: E731  (the WMO number: the archive's id without its last digits)
    assert (code("abadan"), code("ahvaz")) == ("40831", "40811")
    return dict(
        # the headline says which years are compared, in its own big type (the owner, 20 November 2026: "you say 4 to 38
        # but never say from which year to which year in the title and big font")
        hook=(f"آبادان: روزهای بالای ۴۸ درجه // {then_span}: {fa(n_then)} روز در سال // "
              f"{{{now_span}: {fa(n_now)} روز در سال}}"),
        tag_then=then_span, tag_now=now_span, dots="هر نقطه: یک روز",
        station_a="ایستگاهِ هواشناسیِ آبادان", code_a=f"کدِ WMO: {fa(code('abadan'))}",
        station_c="ایستگاهِ هواشناسیِ اهواز", code_c=f"کدِ WMO: {fa(code('ahvaz'))}",
        src_a=(f"میانگینِ سالانه؛ از دوره‌ی اول {fa(len(m['then']['years']))} سالِ کامل در بایگانی هست // "
               "داده: ایستگاهِ هواشناسیِ آبادان، بایگانیِ NOAA"),
        head_b=f"آبادان، {y(1950)} تا {y(2026)}، برآوردِ مدل // {{روزهای بالای ۴۸ درجه بیشتر شده}}",
        b_legend="هر ستون: یک سال", b_first=y(1950), b_last=y(2026), tick="{n} روز",
        b_then=f"میانگینِ مدل، {y(ERA_THEN[0])} تا {y(ERA_THEN[1])}: {fa(f'{m['era']['then']:.1f}'.replace('.', '٫'))} روز",
        b_now=f"میانگینِ مدل، {now_span}: {fa(half_up(m['era']['now']))} روز",
        src_b="مدل: ERA5-Land، نه اندازه‌گیریِ ایستگاه // تصویرِ ماهواره: Sentinel-2، کوپرنیک",
        head_c=(f"اهواز: روزهای بالای ۴۸ درجه // {y(AHVAZ_BEFORE[0])} تا {y(AHVAZ_BEFORE[1])}: {fa(half_up(m['ahvaz_before']['mean']))} روز در سال // "
                f"{{{now_span}: {fa(half_up(m['ahvaz_now']['mean']))} روز در سال}}"),
        tag_c0=f"{y(AHVAZ_BEFORE[0])} تا {y(AHVAZ_BEFORE[1])}", tag_c1=now_span,
        src_c="میانگینِ سالانه‌ی دو دهه // داده: ایستگاهِ هواشناسیِ اهواز، بایگانیِ NOAA",
        head_d="تابستانِ بچگیِ شما // {چطور بود؟}", follow="برای یک خوزستانی بفرستید",
        src_d="منابع و روش در کامنتِ اول")


def clock_of() -> dict:
    a = (0.0, 9.6)
    b = (a[1], a[1] + 9.0)
    c = (b[1], b[1] + 8.7)
    d = (c[1], c[1] + 4.6)
    out = (d[1], d[1] + 0.8)
    return dict(a=a, b=b, c=c, d=d, out=out,
                dots_now=(0.15, 2.4), legend_a=0.0,
                bars=(b[0] + 0.6, b[0] + 3.8), b_marks=b[0] + 4.0,
                dots_c=(c[0] + 0.6, c[0] + 2.4), follow=d[0] + 1.2)


def reading(Wd: dict, C: dict) -> None:
    """The owner's reading rule (src/onebit_reading.py) on every scene, asserted: a scene lasts at least 1 s plus its
    words at 2.5 a second (headline and sentences in full, labels at half) and 3 s after its last string."""
    import onebit_reading as rd
    wt = lambda xs: sum(rd.weight(x) for x in xs)    # noqa: E731
    ticks = [Wd["tick"].format(n=n) for n in TICKS]
    plan = [("hook", C["a"], [Wd["hook"]], [Wd["tag_then"], Wd["tag_now"], Wd["dots"], Wd["station_a"], Wd["code_a"]], C["dots_now"][1]),
            ("years", C["b"], [Wd["head_b"]], [Wd["b_legend"], Wd["b_then"], Wd["b_now"], Wd["b_first"], Wd["b_last"]] + ticks, C["b_marks"]),
            ("ahvaz", C["c"], [Wd["head_c"]], [Wd["station_c"], Wd["code_c"], Wd["tag_c0"], Wd["tag_c1"]], C["dots_c"][1]),
            ("close", C["d"], [Wd["head_d"], Wd["follow"]], [], C["follow"])]
    print("\nreading (seconds the rule needs, seconds given):")
    short = []
    for name, (a, b), full, half, last in plan:
        w = wt(full) + rd.LABELS * wt(half)
        need = max(rd.SETTLE + w / rd.WPS, last - a + rd.HOLD)
        print(f"  {name:6s} {wt(full):4.1f} + {wt(half):4.1f}/2 words -> {need:4.1f} s needed, {b - a:4.1f} s given")
        if b - a + 0.051 < need:
            short.append((name, round(need, 2), round(b - a, 2)))
    assert not short, short


TICKS = (20, 40)                                  # the chart's lines (days a year)
GAIN, COLOUR = 3.0, 1.3                           # the pictures' tone: the gain before the shoulder, the colour's strength


def pictures() -> dict:
    """The two cities from space as the film's 9:16 frames: true colour from the bands' reflectance, with a shoulder
    (x / (1 + x), white at a reflectance of 0.9) that keeps the bright desert's detail."""
    from PIL import Image
    BUILD.mkdir(parents=True, exist_ok=True)
    out = {}
    for name in ("abadan", "ahvaz"):
        v = np.load(DATA / f"scene_{name}.npz")["rgb"].astype(np.float32) / 10000.0
        x = GAIN * v
        x = np.clip(x / (1 + x) * (1 + 1 / (GAIN * 0.9)), 0, 1)
        g = x.mean(-1, keepdims=True)
        x = np.clip(g + COLOUR * (x - g), 0, 1)
        Image.fromarray((255 * x).astype(np.uint8)).save(BUILD / f"{name}.jpg", quality=92, subsampling=0)
        day = json.loads((DATA / f"scene_{name}.json").read_text())["day"]
        st = get_khuzheat.STATIONS[name]
        out[name] = dict(box=list(get_khuzheat.FRAMES[name]), file=f"{name}.jpg", day=day, station=[st["lon"], st["lat"]])
    return out


def film() -> dict:
    m = measures()
    t, n, e = m["then"], m["now"], m["era"]
    print(f"Abadan, hot days a year ({HOT_F} F or more): {t['years']} -> {t['counts']} (mean {t['mean']:.2f}); "
          f"{n['years']} -> {n['counts']} (mean {n['mean']:.2f}); hot days outside May to September in those years: {m['outside']}")
    print(f"ERA5-Land at Abadan: {ERA_THEN[0]}-{ERA_THEN[1]} mean {e['then']:.1f}, {NOW[0]}-{NOW[1]} mean {e['now']:.1f}; decades {dict((k, round(v, 1)) for k, v in e['decades'].items())}")
    print(f"Ahvaz: {m['ahvaz_before']['years'][0]}-{m['ahvaz_before']['years'][-1]} mean {m['ahvaz_before']['mean']:.1f}; "
          f"{m['ahvaz_now']['years'][0]}-{m['ahvaz_now']['years'][-1]} mean {m['ahvaz_now']['mean']:.1f}; highest {m['ahvaz_top']}")
    # «از ۴ به حدودِ ۴۰ روز در سال»: the station's two means; «در سال»: no such day outside the count's months
    assert t["years"] == [1949, 1950, 1951, 1952, 1953, 1954, 1955, 1958] and n["years"] == list(range(2015, 2025)), (t["years"], n["years"])
    assert (half_up(t["mean"]), half_up(n["mean"])) == (4, 38), (t["mean"], n["mean"])                 # «… ۴ روز در سال», «… ۳۸ روز در سال»
    assert float(np.min(np.arange(470, 490)[hot(np.arange(470, 490) / 10)])) == 481.0                  # «بالای ۴۸»: from 48.1 C on
    assert m["outside"] == 0, m["outside"]
    assert len(m["plain_now"] and [1]) and half_up(m["plain_now"]) == 41, m["plain_now"]              # the count the fact check saw, with a plain 48.0 C
    assert n["low"] > t["high"], (n["low"], t["high"])          # the mildest of the last ten years is above the hottest early year
    # «روزهای ۴۸ درجه بیشتر شده»: the other estimate agrees in direction and roughly in size, and rises decade after decade from the 1970s
    dec = [e["decades"][str(a)] for a in range(1970, 2020, 10)]
    assert round(e["then"], 2) == 3.5 and half_up(e["now"]) == 31 and e["now"] > 6 * e["then"], (e["then"], e["now"])       # «۳٫۵» and «۳۱»
    assert all(b > a for a, b in zip(dec, dec[1:])), dec
    assert e["years"] == list(range(1950, 2027)) and max(e["counts"]) < 50, (e["years"][0], e["years"][-1], max(e["counts"]))
    # Ahvaz: both decades complete; the hottest day of its data
    assert len(m["ahvaz_before"]["years"]) == 10 and len(m["ahvaz_now"]["years"]) == 10
    assert m["ahvaz_now"]["mean"] > 2 * m["ahvaz_before"]["mean"] and m["ahvaz_top"]["day"] == "2017-06-29", m["ahvaz_top"]
    assert m["ahvaz_top"]["value"] == m["ahvaz_all_top"], (m["ahvaz_top"], m["ahvaz_all_top"])       # the caption's highest maximum report: of every year, not only the complete ones
    assert m["ahvaz_top_hourly"] == 54.0, m["ahvaz_top_hourly"]                                      # the comment: that day's hourly readings reach 54
    Wd, C = words_of(m), clock_of()
    reading(Wd, C)
    pics = pictures()
    k_of = lambda year: e["years"].index(year)                                                    # noqa: E731
    F = dict(fps=FPS, size=[1080, 1920], cover_t=3.2, end=C["out"][1], clock=C, words=Wd,
             colours=dict(gold="#F6C445", ink="#1d140c", paper="#FBF7F0", hot="#E4472B", cool="#f3ead8"),
             dots=dict(then=half_up(t["mean"]), now=half_up(n["mean"]), c0=half_up(m["ahvaz_before"]["mean"]), c1=half_up(m["ahvaz_now"]["mean"])),
             bars=dict(years=e["years"], counts=e["counts"], top=50, ticks=list(TICKS),
                       means=[dict(k0=k_of(ERA_THEN[0]), k1=k_of(ERA_THEN[1]), value=e["then"]), dict(k0=k_of(NOW[0]), k1=k_of(NOW[1]), value=e["now"])]),
             numbers={k: v for k, v in m.items() if k != "era"} | dict(era={k: v for k, v in e.items() if k != "wall"}), pictures=pics)
    (BUILD / "film.json").write_text(json.dumps(F, ensure_ascii=False, indent=1))
    print(f"saved {BUILD / 'film.json'} | end {F['end']:.1f} s")
    return F


if __name__ == "__main__":
    film()
