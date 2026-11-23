"""«زمین همیشه گرم و سرد شده؟» (cycles_fa): the words, numbers, pictures and clock of the reel that answers the comment
"the Earth has always warmed and cooled" (erty567889 on 18, 22 and 23 Nov 2026; tehrani3018 "a natural cycle").

One connected reel (the owner, 23 Nov 2026: "one long but connected part with light music"), no voice, eight scenes:
the Earth of the last ice age on a turning globe (ICE-6G_C ice sheets, the Persian Gulf as dry land) wiped to today;
the ice melting and the sea filling the Gulf while the Earth warms about 6 degrees in about 10,000 years (Osman et al.
2021); the ten thousand calm years of the Holocene with what Iran built in them (goats herded in the Zagros,
Shahr-e Sukhteh, Persepolis) and, on the same curve, the last 150 years (HadCRUT5); the sun (NOAA TSI CDR); carbon
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
        decades=[float(h.loc[a:a + 9].mean()) for a in range(1966, 2017, 10)],
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


def relief() -> Path:
    """relief.png on the same grid: red = today's land height (square root of m / 6000), green = the ice thickness of
    21,000 years ago (square root of m / 4500), blue = 255 where today's surface is water. Only for light and shade."""
    out = BUILD / "relief.png"
    if out.exists():
        return out
    from PIL import Image
    lon, lat = grid()
    z = xr.open_dataset(PALEO / "etopo" / "etopo_0p1.nc").altitude.interp(latitude=lat, longitude=lon, method="linear").values
    thick = np.clip(to_grid(xr.open_dataset(PALEO / "ice6g" / "I6_C.VM5a_1deg.21.nc").stgit, lon, lat), 0, 4500)
    rgb = np.stack([255 * np.sqrt(np.clip(z, 0, 6000) / 6000), 255 * np.sqrt(thick / 4500), 255.0 * (z < 0)], -1)
    Image.fromarray(np.round(rgb).astype(np.uint8), "RGB").save(out, optimize=True)
    return out


def world() -> Path:
    return onebit_compare.fetch_bm(BUILD / "world.jpg", -180.0, 180.0, LAT0, LAT1, 360 * PXD)


def photos() -> dict:
    """The photographs of PHOTOS, each cut to the frame's shape (9:16, 1620 x 2880 so the camera can move in) around its
    own point, as photo_<key>.jpg in the build folder; what the page needs to know about each."""
    from PIL import Image, ImageOps
    out = {}
    for key, (file, credit, what, fx, fy, z0, z1, lift, tone) in PHOTOS.items():
        src, dst = PALEO / "photos" / file, BUILD / f"photo_{key}.jpg"
        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime or dst.stat().st_mtime < Path(__file__).stat().st_mtime:
            im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")       # one of them is stored on its side
            w, h = im.size
            cw = min(w, round(h * 9 / 16))
            ch = round(cw * 16 / 9)
            x0 = min(max(0, round(fx * w - cw / 2)), w - cw)
            y0 = min(max(0, round(fy * h - ch / 2)), h - ch)
            im.crop((x0, y0, x0 + cw, y0 + ch)).resize((1620, 2880), Image.LANCZOS).save(dst, quality=90)
        out[key] = dict(file=dst.name, credit=credit, what=what, zoom=[z0, z1], lift=lift, tone=tone)
    return out


# ── the words ────────────────────────────────────────────────────────────────────────────────────────────────────
SCENES = ("hook", "melt", "speed", "sun", "co2", "who", "accel", "call")
# what Iran built on the level part of the curve, years ago: goats first herded in the Zagros (Zeder & Hesse 2000, Science
# 287, 2254: "10,000 years ago"); Shahr-e Sukhteh, "founded around 3200 BC" (UNESCO World Heritage List no. 1456);
# Persepolis, "founded by Darius I in 518 B.C." (UNESCO World Heritage List no. 114)
MARKERS = ((10000, "بزهای اهلیِ زاگرس"), (5200, "شهرِ سوخته"), (2500, "تخت‌جمشید"))
# the curve scene has two headlines: the calm ten thousand years first (the owner, 23 Nov 2026: "mention the Holocene and
# which civilizations appeared ... Persians love Persepolis"), then the human side when the spike rises. "In this calm",
# not "because of it": the stable climate as the condition of farming is a hypothesis (Richerson, Boyd & Bettinger 2001,
# American Antiquity 66, 387). The Holocene began 11,700 years ago; "about 1 degree" is measured over the last 10,000.
CALM = "۱۰ هزار سالِ آرام (هولوسِن): // {ایران در همین آرامش ساخته شد}"

# ── the documentary cut, "d" (the owner, 23 Nov 2026, evening: "like a documentary ... movies of Persepolis or Shahr-e
# Sukhteh", "I like the night view", "the corridor of life, from mid-Holocene to today, that all the civilization of the
# human beings have shaped, coming from hunter and gatherers and sticking to agriculture"). Six scenes, pictures to the
# edges of the frame: the Persian Gulf as dry land filling with the sea; the thaw seen from space with the curve under it;
# the corridor of life (the curve zoomed on the last 11,000 years, a band between the coldest and the warmest 200-year
# mean of the last 10,000, a photograph behind each marker); the last 150 years leaving the corridor; carbon dioxide; and
# the call to send it on, over Persepolis. The cut "a" (the eight scenes above) stays as it was.
DOC = ("gulf", "thaw", "life", "exit", "co2", "send")
# the photographs (data/paleo/photos, fetched by src/get_cycles.py, all from Wikimedia Commons under Creative Commons
# Attribution licences, none share-alike): the file, the credit as its licence asks (the author as Commons names him, the
# licence), the point of the photograph that stays in the middle of the frame (x, y as fractions), how far the camera
# moves in (zoom at the start and at the end of its time on screen), how many pixels the picture is lifted, so that its
# subject stands in the clear part of the frame, above the curve, and a tone for a picture whose colours fight the film's
# (a museum's red cloth). Each has one small line that says what it shows, where the headline does not. Cut to 9:16 on
# the page; the first comment says so, as the licences ask.
#   zagros      a clay human figure from Tepe Sarab, Kermanshah, 7000-6100 BC (National Museum of Iran, inventory
#               number 4560, as the museum's label reads on the photograph's Commons page): made by the herders and
#               farmers of the Zagros themselves. The owner, 23 Nov 2026, on the photograph of a shepherd of today that
#               stood here first: "a recent human. If not available use a reconstructed man". No reconstruction of an
#               early Iranian was found under an open licence; this figure is from the time itself.
#   sukhteh     the painted goblet with the goats and the tree from Shahr-e Sukhteh, National Museum of Iran
#   persepolis  the winged bull of the Gate of All Nations
#   today       Milad Tower at dusk, Tehran
#   end         the north-western colossus of the Gate of All Nations and a column
PHOTOS = dict(
    zagros=("sarab_figurine_albers.jpg", "Photo: Erik Albers · CC0", "تندیسِ گِلی، تپه سراب، کرمانشاه (۷۰۰۰ تا ۶۱۰۰ پیش از میلاد)",
            0.53, 0.5, 1.03, 1.12, 150, "saturate(.52) brightness(.94) contrast(1.05)"),
    sukhteh=("sukhteh_goblet_darafsh.jpg", "Photo: Darafsh · CC BY 3.0", "جامِ سفالی با نقشِ بز، از شهرِ سوخته", 0.52, 0.5, 1.03, 1.12, 240, ""),
    persepolis=("persepolis_gate_guillot.jpg", "Photo: Valerian Guillot · CC BY 2.0", "دروازه‌ی ملل", 0.42, 0.5, 1.04, 1.16, 0, ""),
    today=("tehran_milad_rezvani.jpg", "Photo: Behrooz Rezvani · CC BY 3.0", "برجِ میلاد، تهران", 0.38, 0.5, 1.03, 1.12, -110, ""),
    end=("persepolis_colossus_krol.jpg", "Photo: Laurens R. Krol · CC BY 4.0", "دروازه‌ی ملل، تخت‌جمشید", 0.5, 0.5, 1.03, 1.12, 0, ""))
# the corridor's markers: years ago, the name over the picture, the photograph, the line under the name. The first is the
# turn from hunting to herding and farming in the Zagros about 10,000 years ago (goats first herded: Zeder & Hesse 2000,
# as for MARKERS; cereals at Chogha Golan: Riehl et al. 2013, Science 341, 65, cited from memory, to be checked)
LIFE = ((10000, "از شکار به کشاورزی", "zagros", "زاگرس، حدودِ ۱۰ هزار سال پیش"),
        (5200, "شهرِ سوخته", "sukhteh", ""), (2500, "تخت‌جمشید", "persepolis", ""))


def words(n: dict) -> dict:
    melt, now = round(n["melt"]), round(n["now"], 1)
    four = n["usa"] + n["china"] + n["eu"] + n["russia"]
    return dict(
        pill=dict(nat="طبیعی", hum="انسانی"),
        scenes=dict(
            hook=("زمین همیشه گرم و سرد شده؟ // {آره، ولی نه با این سرعت}", ""),
            melt=(f"طبیعی: // {{حدودِ {fa(melt)} درجه، در ۱۰ هزار سال}}", ""),
            speed=("انسانی: // {حدودِ ۱۰ برابر تندتر}", ""),
            sun=("خورشید؟ // {گرم‌تر نشده}", ""),
            co2=("دی‌اکسیدِ کربنِ هوا: // {۸۰۰ هزار سال، هرگز بالای ۳۰۰}", ""),
            who=("چهار آلاینده‌ی بزرگ: // {حدودِ ۶ از هر ۱۰}", "سهم از گرمایشِ سوخت‌های فسیلی، تا ۲۰۲۴"),
            accel=("گرم شدن // {تندتر هم می‌شود}", "COP31 هم بدونِ توافق تمام شد"),
            call=("اگر می‌خواهید ادامه بدهم، // {با بازنشر انگیزه بدهید}", "با هم آگاهی را بیشتر می‌کنیم"),
            # the documentary cut
            gulf=("زمین همیشه گرم و سرد شده؟ // {آره. ولی تمدن، فقط در آرامش}", ""),
            thaw=("گرم شدنِ طبیعی: // {حدودِ %s درجه، در ۱۰ هزار سال}" % fa(melt), "آدم‌ها هنوز شکارچی و گردآورنده بودند"),
            life=("همه‌ی تمدن // {در همین دالان ساخته شد}", ""),
            exit=("۱۵۰ سالِ اخیر: // {بیرون از دالان}", "حدودِ ۱۰ برابر تندتر (ناسا)"),
            send=("برای کسی بفرستید که می‌گوید: // {«زمین همیشه گرم و سرد شده»}", "اگر می‌خواهید ادامه بدهم، // با بازنشر انگیزه بدهید")),
        sources=dict(
            hook="ICE-6G_C (Peltier et al. 2015) · ETOPO1 · NASA Blue Marble",
            melt="ICE-6G_C · Osman et al. 2021 (Nature)",
            speed="Osman et al. 2021 · HadCRUT5 · NASA · IPCC AR6",
            sun="NOAA TSI CDR · HadCRUT5 · 11-yr means",
            co2="Bereiter et al. 2015 · NOAA Mauna Loa 2025",
            who="Jones et al. 2023 (Sci. Data), v2025.1",
            accel="HadCRUT5 · COP31: CNN, NPR, 22 Nov 2026",
            call="NASA Blue Marble",
            gulf="ICE-6G_C (Peltier et al. 2015) · ETOPO1 · NASA Blue Marble", thaw="ICE-6G_C · Osman et al. 2021 (Nature)",
            life="Osman et al. 2021 (Nature) · IPCC AR6", exit="Osman et al. 2021 · HadCRUT5 · NASA · IPCC AR6", send=""),
        hook=dict(then="۲۰ هزار سال پیش", now="امروز", gulf="خلیجِ فارس: خشکی", iran="ایران"),
        melt=dict(chip=lambda a: f"{thou(a)} سال پیش", gap=f"{fa(melt)} درجه", gulf="خلیجِ فارس پُر شد"),
        speed=dict(nat=f"طبیعی: {fa(melt)} درجه در ۱۰ هزار سال", hum=f"انسانی: {dec(now)} درجه در ۱۵۰ سال",
                   calm=CALM, markers=[dict(age=a, label=m) for a, m in MARKERS],
                   ticks=[(20000, "۲۰ هزار"), (10000, "۱۰ هزار"), (0, "امروز")], axis="سال پیش"),
        sun=dict(temp="دمای زمین", sun="تابشِ خورشید", unit_t="درجه", unit_s="وات بر مترمربع",
                 years=[(1960, "۱۹۶۰"), (1990, "۱۹۹۰"), (2025, "۲۰۲۵")]),
        co2=dict(unit="ppm", now=f"امروز: {fa(round(n['mlo']))}", nat="طبیعی", hum="انسانی",
                 ticks=[(800000, "۸۰۰ هزار"), (400000, "۴۰۰ هزار"), (0, "امروز")], axis="سال پیش",
                 counter=lambda a: f"{thou(a)} سال پیش"),
        who=dict(groups=[dict(key="usa", label="آمریکا", v=round(n["usa"])), dict(key="china", label="چین", v=round(n["china"])),
                         dict(key="eu", label="اتحادیه‌ی اروپا", v=round(n["eu"])), dict(key="russia", label="روسیه", v=round(n["russia"])),
                         dict(key="rest", label="بقیه‌ی جهان", v=None), dict(key="iran", label="ایران", v=round(n["iran"], 1))],
                 unit="هر مکعب: ۱٪", four=round(four)),
        accel=dict(values=[dec(v, 2) for v in n["decades"]], first="۱۹۶۶ تا ۱۹۷۵", last="۲۰۱۶ تا ۲۰۲۵", tag=f"{dec(n['steps'][-1], 2)} بیشتر از دهه‌ی قبل",
                   unit="هر ستون: یک دهه // درجه گرم‌تر از ۱۸۵۰ تا ۱۹۰۰", paris="حدِ ۱٫۵ درجه‌ی پاریس", year=f"۲۰۲۴: {dec(n['y2024'], 2)}"),
        call=dict(),
        gulf=dict(before="۲۰ هزار سال پیش، // {خلیجِ فارس خشکی بود}", gulf="خلیجِ فارس", iran="ایران"),
        strip=dict(wide=[(20000, "۲۰ هزار"), (10000, "۱۰ هزار"), (0, "امروز")], near=[(10000, "۱۰ هزار"), (5000, "۵ هزار"), (0, "امروز")],
                   axis="سال پیش"),
        life=dict(before="دالانِ زندگی: // {۱۰ هزار سال، فقط حدودِ ۱ درجه}",
                  markers=[dict(age=a, label=m, photo=ph, ago=sub or f"{thou(a)} سال پیش") for a, m, ph, sub in LIFE]),
        exit=dict(tag=f"{dec(now)} درجه"),                     # the number alone: its headline has the 150 years, the pill the side
        send=dict(),
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
        half += [w["melt"]["chip"](10000), w["melt"]["gap"], w["melt"]["gulf"]]
    elif k == "speed":
        full += [w["speed"]["calm"], w["speed"]["nat"], w["speed"]["hum"]]
        half += [s for _, s in w["speed"]["ticks"]] + [w["speed"]["axis"]] + [m["label"] for m in w["speed"]["markers"]]
    elif k == "sun":
        half += [w["sun"][x] for x in ("temp", "sun", "unit_t", "unit_s")]
    elif k == "co2":
        half += [w["co2"][x] for x in ("unit", "now", "nat", "hum", "axis")] + [w["co2"]["counter"](10000)]
    elif k == "accel":
        full += [w["accel"]["tag"], w["accel"]["paris"]]
        half += w["accel"]["values"] + [w["accel"][x] for x in ("first", "last", "unit", "year")]
    elif k == "who":
        full += [f"{g['label']} {dec(g['v'])}٪" if g["v"] else g["label"] for g in w["who"]["groups"]]
        half += [w["who"]["unit"]]
    elif k == "gulf":
        full += [w["gulf"]["before"]]
        half += [w["gulf"]["iran"], w["melt"]["chip"](10000)]
    elif k == "thaw":
        half += [s for _, s in w["strip"]["wide"]] + [w["strip"]["axis"]]
    elif k == "life":
        full += [w["life"]["before"]]
        half += [x for m in w["life"]["markers"] for x in (m["label"], m["ago"])] + [s for _, s in w["strip"]["near"]] + [w["strip"]["axis"]]
    elif k == "exit":
        full += [w["exit"]["tag"]]
    return 1.0 + (sum(map(count, full)) + 0.5 * sum(map(count, half))) / 2.5


# ── the clock ────────────────────────────────────────────────────────────────────────────────────────────────────
# moments inside a scene (seconds after its start); the score plays to them
CUES = dict(
    hook=dict(wipe=[0.25, 1.75], back=[2.55, 3.45], gulf=3.55),
    melt=dict(age=[0.4, 6.0, 20.5, 7.0], zoom=[2.4, 5.6], gap=3.8),
    # the curve, the band of the calm years, one marker at a time; at "human" the headline and the pill turn to the human side
    speed=dict(draw=[0.2, 3.0], band=3.2, marks=[3.8, 4.8, 5.8], human=7.6, nat=7.9, spike=[8.4, 9.6], hum=9.7),
    sun=dict(temp=[0.3, 2.3], sun=[0.6, 2.6], verdict=3.1),
    co2=dict(draw=[0.3, 4.3], nat=4.4, spike=[5.0, 5.9], chip=6.0, hum=6.3),
    who=dict(groups=dict(usa=[0.6, 2.8], china=[3.2, 5.0], eu=[5.4, 7.0], russia=[7.4, 8.4], rest=[9.4, 10.4]), four=8.8, iran=10.8),
    accel=dict(bars=[0.3, 4.5], paris=4.8, year=5.4, tag=6.0),
    call=dict(icon=1.0),
    # the documentary cut. gulf: the sea comes in (age from, to), then the headline turns to the question. thaw: the ice
    # goes and the curve draws to 10,000 years ago. life: three beats, one thing at a time. The curve's frame closes in on
    # the last 11,000 years (zoom) under the corridor's headline, which leaves at "head"; then the playhead runs through
    # the corridor (seconds, years ago) and reaches each marker at its moment, a photograph coming up under each, the
    # frame clear for it; at "last" the conclusion comes in over Persepolis. exit: the last 150 years rise out of the
    # corridor. send: the icons.
    # "small": when a scene's small line comes in (one thing at a time: the owner's reference reels, read on 23 Nov 2026,
    # never put a headline, its sub-line and the labels on screen together)
    gulf=dict(age=[0.3, 2.9, 20.0, 7.0], turn=4.0),           # from 20,000 years ago, as its headline says
    thaw=dict(age=[0.4, 5.0, 20.0, 10.0], small=3.2),         # 20,000 to 10,000 years ago: the ten thousand years of its headline
    life=dict(zoom=[0.2, 1.8], head=4.6, run=[[0.0, 10000], [4.9, 10000], [8.5, 5200], [12.1, 2500], [17.6, 150]], marks=[4.9, 8.5, 12.1],
              fade=[1.2, 0.4], last=14.5),
    exit=dict(spike=[0.8, 2.2], tag=2.4, small=3.4),
    send=dict(icon=1.0, small=2.6))
PILL = dict(hook="both", melt="nat", speed=("nat", CUES["speed"]["human"], "hum"), sun="nat",
            co2=("nat", CUES["co2"]["spike"][0], "hum"), who="hum", accel="hum", call="both",
            gulf="both", thaw="nat", life="nat", exit="hum", send="both")
LAST = dict(hook=CUES["hook"]["gulf"] + 0.5, melt=CUES["melt"]["age"][1], speed=CUES["speed"]["hum"] + 0.5,
            sun=CUES["sun"]["verdict"] + 0.5, co2=CUES["co2"]["hum"] + 0.5, who=CUES["who"]["iran"] + 0.6, accel=CUES["accel"]["tag"] + 0.5, call=CUES["call"]["icon"] + 0.6)


LAST.update(gulf=CUES["gulf"]["turn"] + 0.5, thaw=CUES["thaw"]["age"][1], life=CUES["life"]["last"] + 0.5,
            exit=CUES["exit"]["small"] + 0.5, send=CUES["send"]["small"] + 0.6)


def seconds(w: dict, scenes: tuple = SCENES) -> list[float]:
    """Each scene: long enough to read and a hold of 3 s after its last picture lands, rounded up to 0.25 s."""
    import math
    return [math.ceil(4 * max(reading(w, k), LAST[k] + 3.0)) / 4 for k in scenes]


# the globe: centre latitude, longitude, zoom and the disc (centre x, y, radius in px), keyframes per scene
VIEW = dict(
    hook=[[0.0, 44.0, 25.0, 1.0, 540, 1005, 420], [7.5, 44.0, 33.0, 1.0, 540, 1005, 420]],
    melt=[[0.0, 44.0, 33.0, 1.0, 540, 1005, 420], [2.4, 42.0, 38.0, 1.0, 540, 1005, 420], [5.6, 29.0, 50.5, 3.2, 540, 1005, 420],
          [9.5, 28.4, 53.5, 3.5, 540, 1005, 420]],                                 # the Gulf: a slow drift and zoom while it holds
    call=[[0.0, 30.0, 40.0, 1.0, 540, 795, 215], [11.0, 30.0, 58.0, 1.0, 540, 795, 215]],
    # the documentary cut: the Gulf to the edges of the frame; the ice-age Earth wider than the frame
    gulf=[[-1.6, 31.6, 46.4, 2.3, 540, 1000, 420], [3.2, 29.2, 50.6, 3.25, 540, 1000, 420],        # already moving in at frame 0
          [10.5, 28.6, 52.6, 3.5, 540, 1000, 420]],
    thaw=[[0.0, 58.0, 20.0, 1.3, 540, 1160, 430], [8.5, 54.0, 36.0, 1.3, 540, 1160, 430]])   # a dome rising from the curve: the ice sheets under the headline
PLACES = dict(gulf=(27.3, 51.2), iran=(33.0, 54.0))


def film() -> dict:
    n = numbers()
    f = n.pop("frames")
    n["steps"] = [b - a for a, b in zip(n["decades"], n["decades"][1:])]
    assert max(n["steps"]) == n["steps"][-1] and n["steps"][-1] > 1.3 * max(n["steps"][:-1]), n["steps"]   # the last step the biggest
    assert round(n["decades"][-1], 2) == 1.28 and 1.5 < n["y2024"] < 1.55, (n["decades"], n["y2024"])      # the bars and 2024 against 1.5
    w = words(n)
    # the words carry the numbers: assert them against the data
    assert round(n["melt"]) == 6 and 5.5 < n["melt"] < 6.5, n["melt"]
    assert 0.9 < n["holo_span"] < 1.2, n["holo_span"]                     # «در بازه‌ی حدودِ ۱ درجه»
    assert round(n["now"], 1) == 1.3, n["now"]
    calm = 1.0 + (count(w["speed"]["calm"]) + 0.5 * sum(map(count, [m["label"] for m in w["speed"]["markers"]] + [s for _, s in w["speed"]["ticks"]] + [w["speed"]["axis"]]))) / 2.5
    assert calm <= CUES["speed"]["human"] + 0.05, calm                 # time to read the calm headline and its markers before it turns
    assert all(100 <= a <= 10000 for a, _ in MARKERS)                  # every marker on the level part that holo_span measures
    assert 8 < n["rate_ratio"] < 20, n["rate_ratio"]                     # «حدودِ ۱۰ برابر» (NASA: "roughly 10 times faster than the average rate of warming after an ice age")
    assert n["co2_max_old"] < 300 and n["co2_span"] > 800000 and n["co2_min"] > 170, (n["co2_max_old"], n["co2_span"])
    assert round(n["mlo"]) == 427
    assert abs(n["tsi_2014"] - n["tsi_1960"]) < 0.5 and n["t11_2020"] - n["t11_1960"] > 0.9   # flat sun, warmer Earth
    four = n["usa"] + n["china"] + n["eu"] + n["russia"]
    assert 55 < four < 65 and round(four / 10) == 6, four               # «حدودِ ۶ از هر ۱۰»
    assert [g["v"] for g in w["who"]["groups"]] == [22, 16, 14, 7, None, 1.5]
    secs = seconds(w)
    starts = [sum(secs[:i]) for i in range(len(SCENES))]
    dsecs = seconds(w, DOC)
    dstarts = [sum(dsecs[:i]) for i in range(len(DOC))]
    lead = 1.0 + count(w["gulf"]["before"]) / 2.5
    assert lead <= CUES["gulf"]["turn"] + 0.05, lead                     # time to read the first headline before it turns
    lead = 1.0 + count(w["life"]["before"]) / 2.5
    assert lead <= CUES["life"]["head"] + 0.05, lead                     # and the corridor's headline before it leaves

    def more(k: str) -> dict:                                            # what a scene of the documentary cut has beyond its headline
        e: dict = {}
        if k == "gulf":
            e.update(before=w["gulf"]["before"], turn=CUES["gulf"]["turn"])
        if k == "life":
            e.update(before=w["life"]["before"], turn=CUES["life"]["head"], late=CUES["life"]["last"])
        if "small" in CUES[k]:
            e["small_at"] = CUES[k]["small"]
        return e
    assert CUES["life"]["marks"] == [t for t, a in CUES["life"]["run"] if a in [m["age"] for m in w["life"]["markers"]] and t > 0][:3]
    o, h, s, s11, h11, c, m = (f[k] for k in ("o", "h", "s", "s11", "h11", "c", "m"))
    temp = [[float(a), round(float(v), 3)] for a, v in zip(o.age, o["mean"]) if a <= 20100]
    band = [[float(a), round(float(lo), 3), round(float(hi), 3)] for a, lo, hi in zip(o.age, o.lo, o.hi) if a <= 20100]
    hc = [[int(y), round(float(v), 3)] for y, v in h.items()]
    sun = dict(t=[[int(y), round(float(v), 3)] for y, v in h.loc[1960:2025].items()], t11=[[int(y), round(float(v), 3)] for y, v in h11.loc[1960:2020].items()],
               s=[[int(y), round(float(v), 3)] for y, v in s.loc[1960:2025].items()], s11=[[int(y), round(float(v), 3)] for y, v in s11.loc[1960:2020].items()])
    calm = o[(o.age >= 100) & (o.age <= 9900)]["mean"]                   # the corridor: the coldest and the warmest 200-year mean
    corridor = [round(float(calm.min()), 3), round(float(calm.max()), 3)]   # of the last 10,000 years (Osman et al. 2021)
    assert abs((corridor[1] - corridor[0]) - n["holo_span"]) < 2e-3 and n["now"] > corridor[1] + 1.0, (corridor, n["now"])   # "about 1 degree"; today is outside it
    cc = c[c.age > 100].sort_values("age", ascending=False)
    co = [[round(float(a)), round(float(p), 1)] for a, p in zip(cc.age, cc.ppm)]
    co += [[1950 - int(y), round(float(p), 2)] for y, p in m.items()]    # Mauna Loa, 1959-2025, as years before 1950
    chips = {k: v for k, v in w.items() if k not in ("melt", "co2")}
    chips["melt"] = {k: v for k, v in w["melt"].items() if k != "chip"}
    chips["co2"] = {k: v for k, v in w["co2"].items() if k != "counter"}
    return dict(
        fps=onebit.FPS, size=list(onebit.SIZES["reel"]), cover_t=1.0, cues=CUES, pill=PILL, view=VIEW, places=PLACES, numbers={k: (round(v, 3) if isinstance(v, (int, float)) else [round(x, 3) for x in v]) for k, v in n.items()},
        cuts=dict(a=dict(end=float(sum(secs)), scenes=[dict(key=k, start=float(starts[i]), length=float(secs[i]), title=w["scenes"][k][0],
                  small=w["scenes"][k][1], source=w["sources"][k], **({"before": w["speed"]["calm"], "turn": CUES["speed"]["human"]} if k == "speed" else {})) for i, k in enumerate(SCENES)]),
                  d=dict(end=float(sum(dsecs)), scenes=[dict(key=k, start=float(dstarts[i]), length=float(dsecs[i]), title=w["scenes"][k][0],
                  small=w["scenes"][k][1], source=w["sources"][k], **more(k)) for i, k in enumerate(DOC)])),
        corridor=corridor, photos=photos(),
        colours=dict(paper="#F3ECE1", ink="#2E2118", mark="#A03129", land="#E2D8C8", ice="#EEF3F8", shelf="#CDB48A", sea="#1c5cab",
                     pale="#d8cdbb", gold="#C8902E", nat="#2468B4", iran="#2F7D4F", usa="#A03129", china="#C0533F", eu="#D9785A", russia="#E6A07E", rest="#D8CDBB"),
        series=dict(temp=temp, band=band, hadcrut=hc, sun=sun, co2=co, y2024=round(n['y2024'], 3), decades=[[1966 + 10 * i, round(v, 3)] for i, v in enumerate(n['decades'])]),
        maps=dict(world="world.jpg", age="agemap.png", relief="relief.png", pxd=PXD, lat1=LAT1, lat0=LAT0, lon0=-180.0),
        words={k: v for k, v in chips.items() if k not in ("scenes", "sources")},
        chip_ages=dict(melt=[[a, w["melt"]["chip"](a)] for a in range(0, 21001, 500)], co2=[[a, w["co2"]["counter"](a)] for a in range(0, 800001, 10000)]))


def main() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    world()
    agemap()
    relief()
    data = film()
    (BUILD / "film.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in data["numbers"].items():
        print(f"  {k}: {v}")
    for name, c in data["cuts"].items():
        print(f"cut {name}: {c['end']} s, {round(c['end'] * onebit.FPS)} frames:", ", ".join(f"{s['key']} {s['start']:g}+{s['length']:g}" for s in c["scenes"]))
    print("saved", BUILD / "film.json")


if __name__ == "__main__":
    main()
