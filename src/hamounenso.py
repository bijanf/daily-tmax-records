"""«ال‌نینو برای هامون آب می‌آورد؟» (hamounenso_fa): the Hamoun's late-spring water after El Niño, neutral and La Niña
winters, from space; one film, music only (16 Nov 2026, the owner: "go ahead with the Hamoun El Niño reel").

The question after the 521k Hamoun reel: the lakes have had little water in most springs since 1379, and this winter a
strong El Niño is expected (NOAA CPC, ENSO diagnostic discussion of 12 Nov 2026, read that day: "a strong-to-very
strong El Niño likely through January-March 2027 (remaining greater than a 79% chance)"). Does an El Niño winter
bring water to the Hamoun?

Measured data only. This file writes outputs/onebit/hamounenso/film.json (every string, every number, the clock, the
camera) and the pictures; src/hamounenso_page/ draws any moment; src/onebit_hamounenso.py steps it into the reel.
- The springs: the late-spring open water of the whole Hamoun from hamounreel.areas() (hamoun.py's rule on
  get_hamoun.py's Landsat passes, the reviewed series of the Hamoun films; 1381 = 2002 has no trusted number): the 26
  measured springs of 1379-1405 (2000-2026).
- The winters: NOAA CPC's Oceanic Niño Index of January-March of the spring's year (data/enso/oni.ascii.txt):
  El Niño at or above +0.5, La Niña at or below -0.5, neutral between (the season and the threshold of the owner's
  El Niño reels: «زمستان (ژانویه تا مارس)», "ONI of the same season at least 0.5"). "Nearly without water" = under
  100 km2 of open water (onebit_hamoun2.NEAR_DRY, «تقریباً بی‌آب»). After the 8 El Niño winters no spring was nearly
  without water; after the 8 neutral winters 4 were, after the 10 La Niña winters 6 (Fisher's exact test, El Niño
  against La Niña, p = 0.013).
- Checked (printed, not on screen): JRC's monthly water (Pekel et al. 2016, an independent classifier) gives the same
  nearly-dry calls in all 21 measured springs of 2000-2021; the split is the same for every threshold from 50 to 300 km2;
  with RONI (NOAA's official index since February 2026) or December-February, still no spring nearly without water
  after an El Niño winter (the counts and p change: RONI JFM 4 against 14, p 0.08; ONI DJF 9 against 11, p 0.005).
- The rain upstream: October-April precipitation over the highlands that feed the lakes (hamoun_rain.BOX), the 40
  winters to the springs of 1986-2025, CRU TS 4.10 and ERA5: El Niño winters 10 and 17 % above the 40 winters' mean,
  La Niña winters 12 and 20 % below (GPCC monitoring 1986-2021: +16 and -12 %, printed). In the literature: El Niño
  favours a wetter cold season in southwest Asia (Mariotti 2007, GRL, doi:10.1029/2007GL030078), La Niña a dry one
  more strongly than El Niño a wet one (Hoell et al. 2018, J. Climate, doi:10.1175/JCLI-D-17-0456.1). No paper links
  ENSO to the Hamoun itself: the reel says «سنجشِ ما».
- No guarantee: spring 1403 (2024), after a strong El Niño winter (JFM ONI +1.5), had about 590 km2; FEWS NET, 22 Feb
  2024: "An El Niño-driven boost in precipitation that was anticipated for Central Southwest Asia has fallen short"
  (the caption). On screen the reviewed sentence of the Hamoun 2 reel, «با بارشِ مشابه، آبِ کمتری به هامون می‌رسد»:
  since about 2004 the Helmand's flow at the border fell "despite large amounts of upstream precipitation" (Akbari et
  al. 2022, J. Great Lakes Res. 48:876-889, doi:10.1016/j.jglr.2022.05.004).

    python -I src/hamounenso.py              # film.json and the pictures (cached pictures are kept)
    python -I src/hamounenso.py --pictures   # rebuild the pictures too
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

import enso  # noqa: E402
import get_hamoun as gh  # noqa: E402
import get_hamoun3 as g3  # noqa: E402
import hamoun  # noqa: E402
import hamoun3 as h3  # noqa: E402  (the views, the places, the tone match, the river line)
import hamoun_rain as rain  # noqa: E402
import hamounreel as reel  # noqa: E402
import onebit_hamoun2 as v2  # noqa: E402  (shown(), NEAR_DRY)
from onebit import fa  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "outputs" / "onebit" / "hamounenso"
FPS = 30
W, H = 1080, 1920
GW, GH = h3.GW, h3.GH
FIRST, LAST = 2000, 2026                              # the springs of 1379-1405
HOOK = (2020, 2021)                                   # 1399 after an El Niño winter, 1400 after a La Niña winter
BUT = 2024                                            # 1403 after a strong El Niño winter
TILE = (180, 215)                                     # px of a tile's picture (twice its size on screen)
CLASSES = ("en", "ne", "ln")


def winters() -> tuple[dict, pd.Series]:
    """The winter of each spring: El Niño, neutral or La Niña by the JFM ONI of the spring's year."""
    o = enso.oni("oni").query("season == 'JFM'").set_index("year")["oni"]
    c = {}
    for y in range(1950, int(o.index.max()) + 1):
        v = round(float(o[y]), 2)
        c[y] = "en" if v >= enso.THRESHOLD else "ln" if v <= -enso.THRESHOLD else "ne"
    return c, o


def springs() -> list:
    a = reel.areas()
    cls, oni = winters()
    rows = [dict(year=y, label=fa(str(reel.solar(y))), km2=float(a.loc[y]), cls=cls[y], oni=round(float(oni[y]), 1),
                 dry=bool(a.loc[y] < v2.NEAR_DRY)) for y in range(FIRST, LAST + 1) if y not in reel.GAPS]
    assert len(rows) == 26 and [r["year"] for r in rows][:3] == [2000, 2001, 2003]
    return rows


def counted(rows: list) -> dict:
    from scipy.stats import fisher_exact
    n = {c: sum(r["cls"] == c for r in rows) for c in CLASSES}
    d = {c: sum(r["cls"] == c and r["dry"] for r in rows) for c in CLASSES}
    assert (n, d) == ({"en": 8, "ne": 8, "ln": 10}, {"en": 0, "ne": 4, "ln": 6}), (n, d)
    p = float(fisher_exact([[d["en"], n["en"] - d["en"]], [d["ln"], n["ln"] - d["ln"]]])[1])
    assert 0.012 < p < 0.014, p
    by = {r["year"]: r for r in rows}
    assert by[HOOK[0]]["cls"] == "en" and by[HOOK[1]]["cls"] == "ln" and by[BUT]["cls"] == "en" and by[BUT]["oni"] >= 1.5
    assert v2.shown(by[HOOK[0]]["km2"]) == "۲٬۲۱۰" and v2.shown(by[HOOK[1]]["km2"]) == "۳" and v2.shown(by[BUT]["km2"]) == "۵۹۰"
    en = [r["km2"] for r in rows if r["cls"] == "en"]
    print(f"springs 1379-1405 by the winter before them (JFM ONI +-0.5): El Niño {n['en']} ({d['en']} nearly dry, least "
          f"{min(en):.0f} km2), neutral {n['ne']} ({d['ne']}), La Niña {n['ln']} ({d['ln']}); Fisher p {p:.3f}")
    for c in CLASSES:
        print(f"  {c}: " + ", ".join(f"{r['label']}={r['km2']:.0f}" for r in rows if r["cls"] == c))
    return dict(n=n, dry=d, p=p)


def robustness(rows: list) -> None:
    """Printed only: the split with JRC's water, other thresholds, RONI and December-February."""
    from scipy.stats import fisher_exact
    t = pd.read_csv(ROOT / "outputs" / "hamoun_area.csv").set_index("year")
    cls, _ = winters()
    jrc = t.loc[FIRST:2021, "jrc_km2"].dropna()
    both = [r for r in rows if r["year"] in jrc.index]
    agree = sum((r["dry"] == (jrc[r["year"]] < v2.NEAR_DRY)) for r in both)
    jen = [jrc[y] for y in jrc.index if cls[y] == "en"]
    assert len(both) == 21 and agree == 21 and min(jen) > v2.NEAR_DRY, (len(both), agree, min(jen))
    print(f"JRC monthly water 2000-2021: the same nearly-dry call in {agree} of {len(both)} measured springs; after El Niño winters least {min(jen):.0f} km2")
    for thr in (50, 200, 300):
        e = [r for r in rows if r["cls"] == "en"]
        lo = [r for r in rows if r["cls"] == "ln"]
        de, dl = sum(r["km2"] < thr for r in e), sum(r["km2"] < thr for r in lo)
        assert de == 0, thr
        print(f"  threshold {thr} km2: El Niño {de} of {len(e)}, La Niña {dl} of {len(lo)}")
    a = {r["year"]: r["km2"] for r in rows}
    for idx in ("oni", "roni"):
        for season in ("JFM", "DJF"):
            o = enso.oni(idx).query("season == @season").set_index("year")["oni"]
            e = [y for y in a if round(o[y], 2) >= 0.5]
            lo = [y for y in a if round(o[y], 2) <= -0.5]
            de, dl = sum(a[y] < v2.NEAR_DRY for y in e), sum(a[y] < v2.NEAR_DRY for y in lo)
            assert de == 0, (idx, season)
            p = fisher_exact([[de, len(e) - de], [dl, len(lo) - dl]])[1]
            print(f"  {idx.upper()} {season}: El Niño {len(e)} springs ({de} nearly dry), La Niña {len(lo)} ({dl}), p {p:.3f}")


def rain_numbers() -> dict:
    """October-April precipitation upstream, the 40 winters to the springs of 1986-2025: each kind of winter against
    the 40 winters' mean, CRU TS 4.10 and ERA5 (GPCC printed as a check)."""
    cls, _ = winters()

    def winter_sums(p: pd.Series) -> pd.Series:
        out = {}
        for y in range(1986, 2026):
            s = p[(p.index >= f"{y - 1}-10-01") & (p.index < f"{y}-05-01")]
            if len(s) == 7 and np.isfinite(s).all():
                out[y] = float(s.sum())
        return pd.Series(out)

    res = {}
    for name, p in (("cru", rain.monthly_cru()), ("era5", rain.monthly_era5())):
        w = winter_sums(p)
        assert list(w.index) == list(range(1986, 2026)), name
        c = pd.Series({y: cls[y] for y in w.index})
        res[name] = {k: float(100 * (w[c == k].mean() / w.mean() - 1)) for k in CLASSES}
        res[name]["n"] = {k: int((c == k).sum()) for k in CLASSES}
        res[name]["y2024"] = float(100 * w[2024] / w.mean())
        print(f"{name}: 40 winters, mean {w.mean():.0f} mm; El Niño {res[name]['en']:+.1f} %, neutral {res[name]['ne']:+.1f} %, "
              f"La Niña {res[name]['ln']:+.1f} % (n {res[name]['n']}); the winter to spring 1403: {res[name]['y2024']:.0f} % of the mean")
    more = sorted(round(res[k]["en"]) for k in ("cru", "era5"))
    less = sorted(round(-res[k]["ln"]) for k in ("cru", "era5"))
    assert (more, less) == ([10, 17], [12, 20]), (more, less)                    # «۱۰ تا ۱۷٪ بیشتر»، «۱۲ تا ۲۰٪ کمتر»
    import xarray as xr                                                          # GPCC, printed as a check
    g = xr.open_dataset(ROOT / "data" / "enso_rain" / "gpcc_monitor_1x1.nc")["precip"]
    g = g.sel(lat=slice(rain.BOX[3], rain.BOX[2]), lon=slice(rain.BOX[0], rain.BOX[1])).load()
    g = g.where((g >= 0) & (g < 5000))
    gs = winter_sums(g.weighted(np.cos(np.radians(g.lat))).mean(("lat", "lon")).to_series()).loc[1986:2021]
    gc = pd.Series({y: cls[y] for y in gs.index})
    print("gpcc 1986-2021: " + ", ".join(f"{k} {100 * (gs[gc == k].mean() / gs.mean() - 1):+.0f} %" for k in CLASSES))
    res["more"], res["less"] = more, less
    return res


def pictures(rows: list, rebuild: bool) -> dict:
    """The hook's and the caveat's spring pictures with their water veils, the three ground pictures with matched
    tones and the ring (hamoun3.pictures' recipe, without the dust), and one small tile per spring for the tally: the
    lakes' basin in pale sand and that spring's open water in blue."""
    from scipy import ndimage
    BUILD.mkdir(parents=True, exist_ok=True)
    clean = set(hamoun.years())
    need = sorted({*HOOK, BUT})
    assert set(need) <= clean, "the hook's and the caveat's springs have clean pictures"
    pics = {}
    for y in sorted(clean):                           # all clean springs: the tone match uses their median, as hamoun3
        path = BUILD / f"p{y}.jpg"
        if rebuild or not path.exists():
            Image.fromarray(hamoun.display(hamoun.colour(y)["rgb"])).save(path, quality=92)
            print("  picture", y, flush=True)
        pics[y] = path.name
    lakes = hamoun.lakes()
    waters = {}
    for y in need:
        path = BUILD / f"w{y}.png"
        if rebuild or not path.exists():
            share = np.clip(np.nan_to_num(np.where(lakes, hamoun.water_map(y), 0.0)), 0, 1)
            share = ndimage.gaussian_filter(share, 0.8)
            rgba = np.zeros((GH, GW, 4), np.uint8)
            rgba[..., :3] = h3.WATER_RGB
            rgba[..., 3] = (255 * h3.WATER_ALPHA * share).astype(np.uint8)
            Image.fromarray(rgba, "RGBA").save(path)
        waters[y] = path.name
    stack = np.stack([np.asarray(Image.open(BUILD / pics[y]).convert("RGB")) for y in sorted(pics)[::3]])
    ref = np.median(stack, axis=0).astype(np.float32)
    near = np.asarray(Image.open(g3.OUT / "near.jpg").convert("RGB"))
    ox, oy = h3.NEAR_OFF
    sub = near[oy:oy + GH, ox:ox + GW].astype(np.float32)
    land = ~ndimage.binary_dilation(lakes, iterations=15)
    luts = h3.match(sub, ref, land)
    ground = {}
    for name, (w, s, e, n, k) in g3.GROUND.items():
        im = np.asarray(Image.open(g3.OUT / f"{name}.jpg").convert("RGB"))
        out = np.stack([luts[c][im[..., c]] for c in range(3)], axis=-1)
        Image.fromarray(out).save(BUILD / f"{name}.jpg", quality=92)
        ground[name] = dict(file=f"{name}.jpg", w=w, s=s, e=e, n=n, k=k, px=[im.shape[1], im.shape[0]])
        if name == "near":
            near_adj = out
    yy, xx = np.mgrid[0:GH, 0:GW]
    d = np.minimum.reduce([xx, GW - 1 - xx, yy, GH - 1 - yy])
    p = np.clip(d / h3.FEATHER, 0, 1)
    alpha = 1 - p * p * (3 - 2 * p)
    Image.fromarray(np.dstack([near_adj[oy:oy + GH, ox:ox + GW], (255 * alpha).astype(np.uint8)]), "RGBA").save(BUILD / "ring.png")
    # the tiles: the lakes' bounding box (a margin of 12 px), the same crop for every spring
    ys, xs = np.nonzero(lakes)
    y0, y1, x0, x1 = max(ys.min() - 12, 0), min(ys.max() + 13, GH), max(xs.min() - 12, 0), min(xs.max() + 13, GW)
    basin = ndimage.gaussian_filter(lakes.astype(np.float32), 1.2)[y0:y1, x0:x1]
    tiles = {}
    for r in rows:
        y = r["year"]
        path = BUILD / f"t{y}.png"
        if rebuild or not path.exists():
            share = np.clip(np.nan_to_num(np.where(lakes, hamoun.water_map(y), 0.0)), 0, 1)
            share = ndimage.gaussian_filter(share, 1.0)[y0:y1, x0:x1]
            rgb = np.empty(share.shape + (3,), np.float32)
            sand, blue = np.array([233, 220, 194], np.float32), np.array([28, 104, 214], np.float32)
            rgb[:] = sand
            rgb = rgb * (1 - share[..., None]) + blue * share[..., None]
            a = np.clip(np.maximum(basin, share) * 255, 0, 255)
            im = Image.fromarray(np.dstack([rgb, a]).astype(np.uint8), "RGBA").resize(TILE, Image.LANCZOS)
            im.save(path)
        tiles[y] = path.name
    aspect = (x1 - x0) / (y1 - y0)
    print(f"tiles: the lakes' box {x1 - x0} x {y1 - y0} picture px (width/height {aspect:.3f}), saved at {TILE}")
    assert abs(aspect - TILE[0] / TILE[1]) < 0.04, ("the tile's shape follows the lakes' box", aspect)
    return dict(pics=pics, waters=waters, ground=ground, ring="ring.png", tiles=tiles)


NEW = dict(
    hook="ال‌نینو برای {هامون} آب می‌آورد؟", spring="بهارِ {}", unit="کیلومترمربع آبِ باز",
    after_en="بعد از زمستانِ ال‌نینو", after_ln="بعد از زمستانِ لانینا", after_strong="بعد از زمستانِ ال‌نینوی قوی",
    iran="ایران", afg="افغانستان", zabol="زابل", lake="هامون", river="رودِ هیرمند",
    tally1="۲۶ بهارِ هامون، از ۱۳۷۹", col_lead="زمستانِ",
    cols=("ال‌نینو", "خنثی", "لانینا"), count="{} از {}", dry="تقریباً بی‌آب",
    tally2="بعد از زمستانِ ال‌نینو، // {هیچ بهاری} تقریباً بی‌آب نبود",
    why="چرا؟ بارشِ زمستان // در {کوه‌های بالادست}",
    rows=("زمستانِ ال‌نینو", "زمستانِ لانینا"), more="{} تا {}٪ بیشتر", less="{} تا {}٪ کمتر",
    now="امسال: {ال‌نینوی قوی} // ولی تضمین نیست", now_small="با بارشِ مشابه، آبِ کمتری به هامون می‌رسد",
    end="بهارِ ۱۴۰۶ را با هم // {از فضا} می‌بینیم", follow=("برای کسی بفرستید", "که هامون را می‌شناسد"),
    end_pic="تصویر: بهارِ {}",                         # the end's full lake is 1399 (the GO/NO-GO: never read as 1406)
    src_water="منبع: لندست (USGS)؛ مقایسه‌شده با آبِ سطحیِ JRC",
    src_map="زمینه: Sentinel-2 cloudless (EOX)؛ مرز و رود: Natural Earth",
    src_tally="سنجشِ ما: لندست؛ زمستان: شاخصِ ONI، ژانویه تا مارس (NOAA) // تقریباً بی‌آب: کمتر از ۱۰۰ کیلومترمربع آبِ باز",
    src_rain="بارشِ مهر تا فروردین در بالادست، نسبت به میانگینِ // ۴۰ زمستان (۱۳۶۴ تا ۱۴۰۳)؛ CRU و ERA5",
    src_now="ال‌نینوی امسال: NOAA، ۲۱ آبانِ ۱۴۰۵ // «با بارشِ مشابه»: از حدودِ ۱۳۸۳ (Akbari و همکاران ۲۰۲۲)",
)


def cut() -> dict:
    """The clock: five scenes, each sized by the owner's reading rule (asserted in reading())."""
    hook, tally, why, now, end = (0.0, 7.0), (7.0, 20.4), (20.4, 28.3), (28.3, 36.9), (36.9, 44.9)
    t = tally[0]
    cols = []
    for k, (start, n) in enumerate(((t + 0.6, 8), (t + 2.1, 8), (t + 3.6, 10))):   # the tiles come column by column
        cols.append(dict(tiles=[round(start + 0.12 * i, 3) for i in range(n)], count=round(start + 0.12 * n + 0.25, 3)))
    cues = dict(wipe=(0.0, 2.4), border=(3.0, 3.9), labels=(3.2, 3.35, 3.5),
                dim=(t, t + 0.5), cols=cols, swap=round(t + 8.8, 2),             # the second headline of the tally
                river=(why[0] + 0.6, why[0] + 2.4), card=why[0] + 1.5,
                pic=(now[0] + 0.2, now[0] + 0.9), small=now[0] + 2.2,
                wipe2=(end[0] + 0.4, end[0] + 2.0), follow=end[0] + 2.6, back=(end[1] - 0.7, end[1]))
    camera = [[0, "close", 1.0], [hook[1], "close", 1.04], [tally[1] - 0.2, "close", 1.07], [why[0] + 1.5, "wide", 1.0],
              [now[0], "wide", 0.97], [now[0] + 1.1, "close", 1.0], [end[1] - 0.7, "close", 1.04], [end[1], "close", 1.0]]
    return dict(end=end[1], cover_t=0.0, scenes=dict(hook=hook, tally=tally, why=why, now=now, end=end), cues=cues, camera=camera)


def reading(words: dict, c: dict) -> None:
    """The owner's rule (src/onebit_reading.py): a scene lasts at least 1 s + (strings in full, labels at half
    weight) / 2.5 words a second, and at least 3 s after its last string appears."""
    import onebit_reading as rd
    Wd, S, Q = words, c["scenes"], c["cues"]
    wt = lambda xs: sum(rd.weight(x) for x in xs)        # noqa: E731
    years = [r["label"] for r in words["_rows"]]
    tag = lambda y, sub, n: [Wd["spring"].format(y), sub, n, Wd["unit"]]   # noqa: E731
    counts = [Wd["count"].format(fa(0), fa(8)), Wd["count"].format(fa(4), fa(8)), Wd["count"].format(fa(6), fa(10))]
    plan = [
        ("hook", S["hook"], [Wd["hook"]],
         [*tag("۱۳۹۹", Wd["after_en"], "۲٬۲۱۰"), *tag("۱۴۰۰", Wd["after_ln"], "۳")[:3], Wd["iran"], Wd["afg"], Wd["zabol"]],
         Q["labels"][2]),
        ("tally, first headline", (S["tally"][0], Q["swap"]), [Wd["tally1"], *counts, Wd["dry"]],
         [*(f"{Wd['col_lead']} {c}" for c in Wd["cols"]), *years], Q["cols"][2]["count"]),
        ("tally, second headline", (Q["swap"], S["tally"][1]), [Wd["tally2"]], [], Q["swap"]),
        ("why", S["why"], [Wd["why"], *Wd["rows"], Wd["rain_more"], Wd["rain_less"]],
         [Wd["river"], Wd["lake"]], Q["card"]),
        ("now", S["now"], [Wd["now"], Wd["now_small"]], tag("۱۴۰۳", Wd["after_strong"], "۵۹۰"), Q["small"]),
        ("end", (S["end"][0], Q["back"][0]), [Wd["end"], *Wd["follow"]], [Wd["end_pic"].format("۱۳۹۹")], Q["follow"]),
    ]
    print("\nreading (words in full + labels at half weight; seconds the rule needs, seconds given):")
    total = 0.0
    for name, (a, b), full, half, last in plan:
        w = wt(full) + rd.LABELS * wt(half)
        need = max(rd.SETTLE + w / rd.WPS, last - a + rd.HOLD)
        total += w
        print(f"  {name:24s} {wt(full):5.1f} + {wt(half):4.1f}/2 words, last string at {last - a:4.1f} s -> {need:4.1f} s needed, {b - a:4.1f} s given")
        assert b - a + 0.051 >= need, (name, round(need, 2), round(b - a, 2))
    print(f"  {total:.0f} weighted words in {c['end']:.1f} s ({total / c['end']:.2f} a second)")


def main() -> None:
    rows = springs()
    cnt = counted(rows)
    robustness(rows)
    r = rain_numbers()
    pic = pictures(rows, "--pictures" in sys.argv)
    L = json.loads((g3.OUT / "lines.json").read_text())
    by = {x["year"]: x for x in rows}
    c = cut()
    sp = lambda y: dict(year=y, label=by[y]["label"], km2=by[y]["km2"], shown=v2.shown(by[y]["km2"]),   # noqa: E731
                        pic=pic["pics"][y], water=pic["waters"][y])
    words = dict(NEW, end_pic=NEW["end_pic"].format(by[HOOK[0]]["label"]), rain_more=NEW["more"].format(fa(r["more"][0]), fa(r["more"][1])),
                 rain_less=NEW["less"].format(fa(r["less"][0]), fa(r["less"][1])),
                 counts=[NEW["count"].format(fa(cnt["dry"][k]), fa(cnt["n"][k])) for k in CLASSES], _rows=rows)
    reading(words, c)
    words.pop("_rows")
    tally = {k: [dict(year=x["year"], label=x["label"], tile=pic["tiles"][x["year"]], dry=x["dry"], km2=round(x["km2"]))
                 for x in rows if x["cls"] == k] for k in CLASSES}
    outline = [[[round(a, 4), round(b, 4)] for a, b in ring[::3]] for ring in reel.contour_lines(hamoun.lakes().astype(np.float32), 0.5, min_pts=60)]
    film = dict(
        fps=FPS, size=[W, H], cuts=dict(main=c),
        grid=dict(lon0=h3.LON0, lat1=h3.LAT1, dlon=gh.DLON, dlat=gh.DLAT, w=GW, h=GH),
        views=dict(close=h3.CLOSE, mid=h3.MID, wide=h3.WIDE), ground=pic["ground"], ring=pic["ring"],
        a=sp(HOOK[0]), b=sp(HOOK[1]), but=sp(BUT), tally=tally, tile=list(TILE),
        lines=dict(ia=L["Iran-Afghanistan"][0], ip=L["Iran-Pakistan"][0], ap=L["Afghanistan-Pakistan"][0], river=h3.river(), lake=outline),
        places=dict(h3.PLACES, river_wide=(65.3, 32.95)), words=words,   # the river's name above its middle course (the card holds the south)
        rain=dict(en=[r["cru"]["en"], r["era5"]["en"]], ln=[r["cru"]["ln"], r["era5"]["ln"]]),
        colours=dict(gold="#F6C445", ink="#1d140c", paper="#FBF7F0", river="#49c0ff", pin="#FF8A1F",
                     en="#D9573B", ne="#8E8374", ln="#3F8FBF", more="#1c5cab", less="#B5763A"),
    )
    (BUILD / "film.json").write_text(json.dumps(film, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", BUILD / "film.json")


if __name__ == "__main__":
    main()
