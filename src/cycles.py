"""«زمین همیشه گرم و سرد شده؟» (cycles_fa): the words, numbers, pictures and clock of the reel that answers the comment
"the Earth has always warmed and cooled" (erty567889 on 18, 22 and 23 Nov 2026; tehrani3018 "a natural cycle").

One connected reel (the owner, 23 Nov 2026: "one long but connected part with light music"), no voice, eight scenes:
the Earth of the last ice age on a turning globe (ICE-6G_C ice sheets, the Persian Gulf as dry land) wiped to today;
the ice melting and the sea filling the Gulf while the Earth warms about 6 degrees in about 10,000 years (Osman et al.
2021); ten thousand calm years with Iranian markers; the last 150 years (HadCRUT5); the sun (NOAA TSI CDR); carbon
dioxide over 800,000 years (Bereiter et al. 2015) and today (NOAA Mauna Loa); whose fuel heated the planet (Jones et
al. 2023, release 2025.1, the owner's approved wording «چهار آلاینده‌ی بزرگ»); the owner's call to repost.

Every number on screen is computed here from the files in data/paleo and data/warming (downloaded 23 Nov 2026) and
asserted against the value the words carry. The globe's ice-age dress is a single picture, agemap.png, on the grid of
the Blue Marble picture (10 pixels a degree, 180 W to 180 E, 85 N to 85 S): red = the age (in hundreds of years) at which
a cell of today's sea was flooded (it is dry land for older ages: ETOPO1 depth plus the ICE-6G_C change of topography,
linear in time between the 1,000-year slices), green = the age at which ice left a cell (the ICE-6G_C ice fraction
crossing 50 %, linear in time; 0 where ice is still there today, which the Blue Marble shows itself), blue = the relief
of the surface at 21,000 years ago (ice sheets and exposed shelves) for shading. The Caspian, the Black Sea and the
Aral Sea keep today's shores (they were not part of the ocean; their old levels are another story).

    python -I src/cycles.py      writes outputs/onebit/cycles/film.json, world.jpg, agemap.png; prints the numbers
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
import onebit_compare  # noqa: E402
from onebit import fa  # noqa: E402

ROOT = onebit.ROOT
BUILD = ROOT / "outputs" / "onebit" / "cycles"
PALEO = ROOT / "data" / "paleo"
WARMING = ROOT / "data" / "warming"
PXD, LAT1, LAT0 = 10, 85.0, -85.0                                        # the pictures: 10 px a degree, 180 W .. 180 E
SLICES = tuple(range(0, 22))                                             # ICE-6G_C slices, thousands of years ago
INLAND = ((46.0, 56.5, 36.4, 47.6), (27.3, 42.5, 40.9, 47.6), (57.5, 62.5, 42.5, 47.5))   # Caspian, Black Sea + Azov, Aral (lon0, lon1, lat0, lat1)
GULF = (47.5, 56.6, 23.5, 31.0)                                          # the Persian Gulf box (the Gulf of Oman cut off below)


def dec(v: float, n: int = 1) -> str:
    return fa(f"{v:.{n}f}".rstrip("0").rstrip(".")).replace(".", "٫")


def thou(n: int) -> str:
    return fa(f"{n:,}").replace(",", "٬")


# ── the numbers ──────────────────────────────────────────────────────────────────────────────────────────────────
def osman() -> pd.DataFrame:
    """Osman et al. 2021 (LGMR), global mean surface temperature, 500 members in 200-year bins, as the anomaly against
    the youngest bin (age 100 = 1750-1950 CE): ensemble mean and 5-95 %."""
    o = xr.open_dataset(PALEO / "osman2021" / "LGMR_GMST_ens.nc")
    rel = o.gmst - o.gmst.sel(age=100.0)
    q = rel.quantile([0.05, 0.95], "nEns")
    return pd.DataFrame(dict(age=o.age.values, mean=rel.mean("nEns").values, lo=q.sel(quantile=0.05).values,
                             hi=q.sel(quantile=0.95).values))


def hadcrut() -> pd.Series:
    """HadCRUT 5.1.0.0 global annual anomaly against 1850-1900 (complete years only)."""
    h = pd.read_csv(PALEO / "hadcrut5" / "global_annual.csv")
    h.columns = ["year", "anom", "lo", "hi"]
    s = h.set_index("year").anom
    s = s[s.index <= 2025]                                               # 2026 is a part of a year
    return s - s.loc[1850:1900].mean()


def tsi() -> pd.Series:
    t = xr.open_dataset(PALEO / "tsi" / "tsi_v03r00_yearly_s1610_e2025_c20260305.nc", decode_times=xr.coders.CFDatetimeCoder(use_cftime=True))
    return pd.Series(t.TSI.values.astype(float), index=[x.year for x in t.time.values])


def co2() -> tuple[pd.DataFrame, pd.Series]:
    c = pd.read_csv(PALEO / "bereiter2015" / "antarctica2015co2composite.txt", comment="#", sep=r"\s+")
    c.columns = ["age", "ppm", "sig"]
    m = pd.read_csv(PALEO / "mlo" / "co2_annmean_mlo.txt", comment="#", sep=r"\s+", header=None, names=["year", "ppm", "unc"])
    return c, m.set_index("year").ppm


def shares() -> pd.Series:
    """Per cent of the warming caused through 2024 by each country's fossil CO2, CH4 and N2O (Jones et al., 2025.1)."""
    df = pd.read_csv(WARMING / "GMST_response_1851-2024.csv")
    d = df[(df.Gas == "3-GHG") & (df.Year == 2024) & (df.Component == "Fossil")].set_index("CNTR_NAME").Data
    return 100 * d / d["GLOBAL"]


def numbers() -> dict:
    o, h, s, (c, m), j = osman(), hadcrut(), tsi(), co2(), shares()
    at = o.set_index("age")["mean"]
    h11, s11 = h.rolling(11, center=True).mean(), s.rolling(11, center=True).mean()
    old = c[c.age > 100]                                                 # every sample older than 1850 CE
    return dict(
        lgm=float(o[(o.age >= 19000) & (o.age <= 23000)]["mean"].mean()),
        melt=float(at[9900] - at[20100]),
        holo_span=float(at.loc[100:9900].max() - at.loc[100:9900].min()),
        now=float(h.loc[2016:2025].mean()), y2024=float(h.loc[2024]),
        rate_ratio=float((h.loc[2016:2025].mean() / (2020.5 - 1875.0)) / ((at[9900] - at[20100]) / 10200.0)),
        co2_max_old=float(old.ppm.max()), co2_max_age=float(old.age[old.ppm.idxmax()]), co2_min=float(c.ppm.min()),
        co2_span=float(c.age.max()), mlo=float(m.loc[2025]), mlo_year=2025,
        tsi_1960=float(s11.loc[1960]), tsi_2014=float(s11.loc[2014]), tsi_trend=float(np.polyfit(s.loc[1960:].index, s.loc[1960:].values, 1)[0] * 10),
        t11_1960=float(h11.loc[1960]), t11_2020=float(h11.loc[2020]),
        usa=float(j["USA"]), china=float(j["China"]), eu=float(j["EU27"]), russia=float(j["Russia"]), iran=float(j["Iran"]),
        uk=float(j["United Kingdom"]),
        frames=dict(o=o, h=h, s=s, s11=s11, h11=h11, c=c, m=m))


# ── the pictures ─────────────────────────────────────────────────────────────────────────────────────────────────
def grid() -> tuple[np.ndarray, np.ndarray]:
    lon = -180 + (np.arange(360 * PXD) + 0.5) / PXD
    lat = LAT1 - (np.arange(round((LAT1 - LAT0) * PXD)) + 0.5) / PXD
    return lon, lat


def to_grid(da: xr.DataArray, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """An ICE-6G_C field (1 degree, 0.5..359.5 E) bilinear on the picture's grid (180 W .. 180 E), wrapped in longitude."""
    v = da.assign_coords(lon=((da.lon + 180) % 360) - 180).sortby("lon")
    v = xr.concat([v.isel(lon=-1).assign_coords(lon=v.lon[-1] - 360), v, v.isel(lon=0).assign_coords(lon=v.lon[0] + 360)], "lon")
    return v.interp(lat=lat, lon=lon, method="linear").values


def crossing(vals: list[np.ndarray]) -> np.ndarray:
    """The youngest age (thousands of years) at which vals (one array a slice, positive = 'old state') turns positive
    going back in time, linear between slices; 0 where it never does."""
    out = np.zeros_like(vals[0])
    done = vals[0] > 0                                                   # already in the 'old state' today: no change to draw
    for k in range(1, len(vals)):
        a, b = vals[k - 1], vals[k]
        hit = ~done & (b > 0)
        frac = np.where(hit, a / np.where(a - b == 0, -1e-9, a - b), 0.0)  # a <= 0 < b: where the line crosses 0
        out = np.where(hit, (k - 1) + np.clip(frac, 0, 1), out)
        done |= hit
    return out


def agemap() -> Path:
    out = BUILD / "agemap.png"
    if out.exists():
        return out
    from PIL import Image
    from scipy import ndimage
    lon, lat = grid()
    e = xr.open_dataset(PALEO / "etopo" / "etopo_0p1.nc").altitude
    z = e.interp(latitude=lat, longitude=lon, method="linear").values      # today's height (m); the sea is negative
    LON, LAT = np.meshgrid(lon, lat)
    inland = np.zeros_like(z, bool)
    for a, b, c, d in INLAND:
        inland |= (LON >= a) & (LON <= b) & (LAT >= c) & (LAT <= d) & (z < 0)
    sl = [xr.open_dataset(PALEO / "ice6g" / f"I6_C.VM5a_1deg.{k}.nc") for k in SLICES]
    sea = (z < 0) & ~inland
    flood = crossing([np.where(sea, z + to_grid(s.Topo_Diff, lon, lat), -1.0) for s in sl])
    ice0 = to_grid(sl[0].sftgif, lon, lat) >= 50
    melt = crossing([np.where(ice0, -1.0, to_grid(s.sftgif, lon, lat) - 50.0) for s in sl])
    ice21 = to_grid(sl[21].sftgif, lon, lat) >= 50
    surf = np.where(ice21, to_grid(sl[21].Topo, lon, lat), np.maximum(z + to_grid(sl[21].Topo_Diff, lon, lat), 0.0))
    surf = ndimage.gaussian_filter(surf, 2.0)
    gy, gx = np.gradient(surf, 11100.0 / PXD * 10)                       # metres a pixel (10 km at 10 px a degree, near enough for shading)
    shade = np.clip(0.62 + 9.0 * (-gx * 0.6 + gy * 0.8), 0.0, 1.0)       # light from the upper left
    rgb = np.stack([np.clip(np.round(flood * 10), 0, 255), np.clip(np.round(melt * 10), 0, 255), np.round(255 * shade)], -1).astype(np.uint8)
    Image.fromarray(rgb, "RGB").save(out, optimize=True)
    # the Persian Gulf on the picture, in the same terms as the reel: dry at 21,000 years ago, full by 7,000
    g = (LON >= GULF[0]) & (LON <= GULF[1]) & (LAT >= GULF[2]) & (LAT <= GULF[3]) & sea & ~((LON > 56.3) & (LAT < 26.0))
    dry = lambda ka: float(((flood[g] > 0) & (flood[g] < ka)).mean())    # noqa: E731  (dry land at age ka: older than its flood age)
    print("Gulf dry on the picture: 21 ka %.3f, 14 ka %.3f, 10 ka %.3f, 8 ka %.3f, 7 ka %.3f" % tuple(dry(k) for k in (20.99, 14, 10, 8, 7)))
    assert dry(20.99) > 0.97 and dry(7.0) < 0.01, "the Gulf is not dry at the ice age or not full by 7 ka"
    return out


def world() -> Path:
    return onebit_compare.fetch_bm(BUILD / "world.jpg", -180.0, 180.0, LAT0, LAT1, 360 * PXD)


# ── the words ────────────────────────────────────────────────────────────────────────────────────────────────────
SCENES = ("hook", "melt", "calm", "jump", "sun", "co2", "who", "call")
MARKERS = ((10000, "بزهای اهلیِ زاگرس"), (5200, "شهرِ سوخته"), (2500, "تخت‌جمشید"))   # years ago (see the sources in the caption)


def words(n: dict) -> dict:
    melt, now = round(n["melt"]), round(n["now"], 1)
    four = n["usa"] + n["china"] + n["eu"] + n["russia"]
    return dict(
        pill="طبیعی یا انسانی؟",
        scenes=dict(
            hook=("زمین همیشه گرم و سرد شده؟ // {آره، ولی نه با این سرعت}", ""),
            melt=(f"یخ‌ها آب شدند: // {{حدودِ {fa(melt)} درجه گرم‌تر، در ۱۰ هزار سال}}", "سطحِ دریا در کل حدودِ ۱۲۰ متر بالا آمد"),
            calm=("۱۰ هزار سالِ پایدار: // {کشاورزی، شهرها، تمدن‌ها}", "دما فقط حدودِ ۱ درجه تغییر کرد"),
            jump=(f"۱۵۰ سالِ اخیر: // {{{dec(now)} درجه گرم‌تر}}", "حدودِ ۱۰ برابر تندتر از میانگینِ گرم شدنِ پس از یخبندان"),
            sun=("کارِ خورشید است؟ // {نه}", "از ۱۹۶۰: زمین گرم‌تر شد، خورشید نه"),
            co2=("دی‌اکسیدِ کربنِ هوا: // {۸۰۰ هزار سال، هرگز بالای ۳۰۰}", "بیشترش از سوزاندنِ نفت، گاز و زغال‌سنگ"),
            who=("چهار آلاینده‌ی بزرگ: // {حدودِ ۶ از هر ۱۰}", "سهم از گرمایشِ سوخت‌های فسیلی، تا ۲۰۲۴"),
            call=("اگر می‌خواهید ادامه بدهم، // {با بازنشر انگیزه بدهید}", "با هم آگاهی را بیشتر می‌کنیم")),
        sources=dict(
            hook="ICE-6G_C (Peltier et al. 2015) · ETOPO1 · NASA Blue Marble",
            melt="ICE-6G_C · Osman et al. 2021 (Nature)",
            calm="Osman et al. 2021 (Nature)",
            jump="Osman et al. 2021 · HadCRUT5 (Met Office)",
            sun="NOAA TSI CDR · HadCRUT5 · 11-yr means",
            co2="Bereiter et al. 2015 · NOAA Mauna Loa 2025",
            who="Jones et al. 2023 (Sci. Data), v2025.1",
            call="NASA Blue Marble"),
        hook=dict(then="۲۰ هزار سال پیش", now="امروز", gulf="خلیجِ فارس: خشکی", iran="ایران"),
        melt=dict(chip=lambda a: f"{thou(a)} سال پیش", thermo="دمای میانگینِ زمین",
                  gap=f"{fa(melt)} درجه", gulf="خلیجِ فارس"),
        calm=dict(axis="سال پیش", ticks=[(20000, "۲۰ هزار"), (10000, "۱۰ هزار"), (0, "امروز")], y="دمای میانگینِ زمین",
                  yticks=[(-6, "۶ درجه سردتر"), (0, "پیش از صنعتی شدن")],
                  markers=[dict(age=a, label=s) for a, s in MARKERS]),
        jump=dict(chip="میانگینِ ۲۰۱۶ تا ۲۰۲۵", inset="۱۸۵۰ تا ۲۰۲۵"),
        sun=dict(temp="دمای زمین", sun="تابشِ خورشید", unit_t="درجه", unit_s="وات بر مترمربع", mean="میانگینِ ۱۱ ساله",
                 years=[(1960, "۱۹۶۰"), (1990, "۱۹۹۰"), (2025, "۲۰۲۵")]),
        co2=dict(unit="قسمت در میلیون (ppm)", now=f"امروز: {fa(round(n['mlo']))}", band="۱۸۰ تا ۳۰۰",
                 ticks=[(800000, "۸۰۰ هزار"), (400000, "۴۰۰ هزار"), (0, "امروز")], axis="سال پیش",
                 counter=lambda a: f"{thou(a)} سال پیش"),
        who=dict(groups=[dict(key="usa", label="آمریکا", v=round(n["usa"])), dict(key="china", label="چین", v=round(n["china"])),
                         dict(key="eu", label="اتحادیه‌ی اروپا", v=round(n["eu"])), dict(key="russia", label="روسیه", v=round(n["russia"])),
                         dict(key="iran", label="ایران", v=round(n["iran"], 1)), dict(key="rest", label="بقیه‌ی جهان", v=None)],
                 unit="هر مربع: ۱٪", four=round(four)),
        call=dict(follow="برای کسی بفرستید که می‌گوید زمین همیشه گرم و سرد شده"),
    )


def count(s: str) -> float:
    """Words a reader takes in: digits and signs count 0.4 (the rule of src/onebit_reading.py)."""
    import re
    toks = [t for t in str(s).replace("//", " ").replace("{", "").replace("}", "").split() if re.search(r"[\w؀-ۿ۰-۹]", t)]
    return sum(0.4 if re.match(r"^[\d۰-۹٪%٫٬.,:+\-−–()\[\]/«»؟?؛]+$", t) else 1.0 for t in toks)


def reading(w: dict, k: str) -> float:
    """1 s + (headline and small line + half the labels) / 2.5 words a second."""
    full = [w["scenes"][k][0], w["scenes"][k][1]]
    half: list = []
    if k == "hook":
        half += [w["hook"][x] for x in ("then", "now", "gulf")]
    elif k == "melt":
        half += [w["melt"]["chip"](10000), w["melt"]["thermo"], w["melt"]["gap"]]
    elif k == "calm":
        half += [w["calm"]["y"]] + [m["label"] for m in w["calm"]["markers"]] + [s for _, s in w["calm"]["yticks"]]
    elif k == "jump":
        half += [w["jump"]["chip"], w["jump"]["inset"]]
    elif k == "sun":
        half += [w["sun"][x] for x in ("temp", "sun", "mean")]
    elif k == "co2":
        half += [w["co2"]["unit"], w["co2"]["now"], w["co2"]["counter"](10000)]
    elif k == "who":
        half += [f"{g['label']} {dec(g['v'])}٪" for g in w["who"]["groups"] if g["v"]] + [w["who"]["unit"]]
    elif k == "call":
        full += [w["call"]["follow"]]
    return 1.0 + (sum(map(count, full)) + 0.5 * sum(map(count, half))) / 2.5


# ── the clock ────────────────────────────────────────────────────────────────────────────────────────────────────
# moments inside a scene (seconds after its start); the score plays to them
CUES = dict(
    hook=dict(wipe=[0.25, 1.75], back=[2.55, 3.45], gulf=3.55, spin=[30.0, 36.0]),
    melt=dict(age=[0.5, 7.0, 20.5, 7.0], zoom=[2.6, 6.4], thermo=0.3, gap=4.6),
    calm=dict(draw=[0.2, 3.2], band=3.4, markers=[4.0, 4.6, 5.2]),
    jump=dict(spike=[0.3, 1.9], chip=2.0, inset=[2.4, 3.4]),
    sun=dict(temp=[0.3, 2.3], sun=[0.9, 2.9], verdict=3.1),
    co2=dict(draw=[0.3, 4.6], spike=[4.8, 5.7], chip=5.8, small=6.3),
    who=dict(fill=[0.4, 4.6], four=4.9, iran=5.5),
    call=dict(card=0.5, icon=1.4, follow=3.3))
LAST = dict(hook=CUES["hook"]["gulf"] + 0.5, melt=CUES["melt"]["age"][1], calm=CUES["calm"]["markers"][-1] + 0.5,
            jump=CUES["jump"]["inset"][1], sun=CUES["sun"]["verdict"] + 0.5, co2=CUES["co2"]["small"] + 0.5,
            who=CUES["who"]["iran"] + 0.6, call=CUES["call"]["follow"] + 0.6)


def seconds(w: dict) -> list[float]:
    """Each scene: long enough to read and a hold of 3 s after its last picture lands, rounded up to 0.25 s."""
    import math
    return [math.ceil(4 * max(reading(w, k), LAST[k] + 3.0)) / 4 for k in SCENES]


# the globe: centre latitude, longitude, zoom and the disc (centre x, y, radius in px), keyframes per scene
VIEW = dict(
    hook=[[0.0, 44.0, 25.0, 1.0, 540, 1005, 420], [7.5, 44.0, 33.0, 1.0, 540, 1005, 420]],
    melt=[[0.0, 44.0, 33.0, 1.0, 540, 1005, 420], [2.6, 42.0, 38.0, 1.0, 540, 1005, 420], [6.4, 29.0, 50.5, 3.2, 540, 1005, 420],
          [99.0, 29.0, 52.0, 3.2, 540, 1005, 420]],
    call=[[0.0, 30.0, 40.0, 1.0, 540, 770, 220], [11.0, 30.0, 58.0, 1.0, 540, 770, 220]])
PLACES = dict(gulf=(27.3, 51.2), iran=(33.0, 54.0))


def film() -> dict:
    n = numbers()
    f = n.pop("frames")
    w = words(n)
    # the words carry the numbers: assert them against the data
    assert round(n["melt"]) == 6 and 5.5 < n["melt"] < 6.5, n["melt"]
    assert 0.9 < n["holo_span"] < 1.2, n["holo_span"]                     # «در بازه‌ی حدودِ ۱ درجه»
    assert round(n["now"], 1) == 1.3, n["now"]
    assert 8 < n["rate_ratio"] < 20, n["rate_ratio"]                     # «حدودِ ۱۰ برابر» (NASA: "roughly 10 times faster than the average rate of warming after an ice age")
    assert n["co2_max_old"] < 300 and n["co2_span"] > 800000 and n["co2_min"] > 170, (n["co2_max_old"], n["co2_span"])
    assert round(n["mlo"]) == 427
    assert abs(n["tsi_2014"] - n["tsi_1960"]) < 0.5 and n["t11_2020"] - n["t11_1960"] > 0.9   # flat sun, warmer Earth
    four = n["usa"] + n["china"] + n["eu"] + n["russia"]
    assert 55 < four < 65 and round(four / 10) == 6, four               # «حدودِ ۶ از هر ۱۰»
    assert [g["v"] for g in w["who"]["groups"][:5]] == [22, 16, 14, 7, 1.5]
    secs = seconds(w)
    starts = [sum(secs[:i]) for i in range(len(SCENES))]
    o, h, s, s11, h11, c, m = (f[k] for k in ("o", "h", "s", "s11", "h11", "c", "m"))
    temp = [[float(a), round(float(v), 3)] for a, v in zip(o.age, o["mean"]) if a <= 20100]
    band = [[float(a), round(float(lo), 3), round(float(hi), 3)] for a, lo, hi in zip(o.age, o.lo, o.hi) if a <= 20100]
    hc = [[int(y), round(float(v), 3)] for y, v in h.items()]
    sun = dict(t=[[int(y), round(float(v), 3)] for y, v in h.loc[1960:2025].items()], t11=[[int(y), round(float(v), 3)] for y, v in h11.loc[1960:2020].items()],
               s=[[int(y), round(float(v), 3)] for y, v in s.loc[1960:2025].items()], s11=[[int(y), round(float(v), 3)] for y, v in s11.loc[1960:2020].items()])
    cc = c[c.age > 100].sort_values("age", ascending=False)
    co = [[round(float(a)), round(float(p), 1)] for a, p in zip(cc.age, cc.ppm)]
    co += [[1950 - int(y), round(float(p), 2)] for y, p in m.items()]    # Mauna Loa, 1959-2025, as years before 1950
    chips = {k: v for k, v in w.items() if k not in ("melt", "co2")}
    chips["melt"] = {k: v for k, v in w["melt"].items() if k != "chip"}
    chips["co2"] = {k: v for k, v in w["co2"].items() if k != "counter"}
    return dict(
        fps=onebit.FPS, size=list(onebit.SIZES["reel"]), cover_t=1.0, cues=CUES, view=VIEW, places=PLACES, numbers={k: round(v, 3) for k, v in n.items()},
        cuts=dict(a=dict(end=float(sum(secs)), scenes=[dict(key=k, start=float(starts[i]), length=float(secs[i]), title=w["scenes"][k][0],
                  small=w["scenes"][k][1], source=w["sources"][k]) for i, k in enumerate(SCENES)])),
        colours=dict(paper="#F3ECE1", ink="#2E2118", mark="#A03129", land="#E2D8C8", ice="#EEF3F8", shelf="#CDB48A", sea="#1c5cab",
                     pale="#d8cdbb", gold="#C8902E", iran="#2F7D4F", usa="#A03129", china="#C0533F", eu="#D9785A", russia="#E6A07E", rest="#D8CDBB"),
        series=dict(temp=temp, band=band, hadcrut=hc, sun=sun, co2=co),
        maps=dict(world="world.jpg", age="agemap.png", pxd=PXD, lat1=LAT1, lat0=LAT0, lon0=-180.0),
        words={k: v for k, v in chips.items() if k not in ("scenes", "sources")},
        chip_ages=dict(melt=[[a, w["melt"]["chip"](a)] for a in range(0, 21001, 500)], co2=[[a, w["co2"]["counter"](a)] for a in range(0, 800001, 10000)]))


def main() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    world()
    agemap()
    data = film()
    (BUILD / "film.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in data["numbers"].items():
        print(f"  {k}: {v}")
    c = data["cuts"]["a"]
    print(f"{c['end']} s, {round(c['end'] * onebit.FPS)} frames:", ", ".join(f"{s['key']} {s['start']:g}+{s['length']:g}" for s in c["scenes"]))
    print("saved", BUILD / "film.json")


if __name__ == "__main__":
    main()
