"""«زمینِ رفسنجان پایین می‌رود» (kerman_fa): the words, numbers, pictures and clock of the Kerman reel.

Asked for by a reader from Kerman (a journalist of the province's meteorology office, 20 Nov 2026) and by the owner
("water and climate ... for Kerman, from open data", 23 Nov). Five scenes on the documentary night look of the ice-age
film's cut d, no voice:

    sink    all of Iran from space (EOX Sentinel-2 cloudless 2016) with every sinking ground of the radar glowing on it
            and Kerman province outlined; a dive into the Rafsanjan plain (Landsat 2025) in the first 3 s, the ground
            that sinks glowing on it (Sentinel-1: Payne et al. 2025, checked against Haghshenas Haghighi & Motagh 2024);
            a pole shows 8 years of it against a person
    qanat   a qanat with water (Shafiabad, Kerman province), then a dry one: «for centuries the qanat brought Kerman's
            water» / «the Rafsanjan plain today: the qanats have dried up» (Mirnezami et al. 2020)
    wells   the plain in 1987 wiped to 2025, the green canopy tinted: wells from about 70 to more than 1,300 (Motagh et
            al. 2017), the green ~1.4 times (src/kerman_landsat), the water table falling more than 70 cm a year
    warm    the plain's air about 1.7 degrees warmer (CRU TS 4.10, 1996-2025 against 1951-1980), over Iranian pistachios;
            Ohadi pistachio wants 800-900 hours of winter cold (Asadi Oskouei et al. 2023; Javanshah et al. 2010), and
            Rafsanjan's winters now have about a tenth fewer of them (hourly ERA5-Land, src/kerman_chill.py; the
            paper's "1 winter in 4" at Rafsanjan was not reproduced from the same data and is not used)
    city    Kerman: on 10 Aban 1405 the water company's head put a broken water main down to 3-4 cm of settlement (Mehr);
            an open question to end on

Every number on screen is computed here from data/subsidence, data/kerman and data/water, or is a published figure
named beside it (LIT), and is asserted against the words that carry it.

    python -I src/kerman_landsat/s13_stage.py   # data/kerman/landsat/stage (after run_all.sh)
    python -I src/kerman.py                     # outputs/onebit/kerman: film.json, the pictures
    python -I src/cycles_depth.py outputs/onebit/kerman     # depth for the photographs
"""

from __future__ import annotations

import glob
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
from onebit import fa  # noqa: E402

ROOT = onebit.ROOT
BUILD = ROOT / "outputs" / "onebit" / "kerman"
DATA = ROOT / "data" / "kerman"
STAGE = DATA / "landsat" / "stage"
SUB = ROOT / "data" / "subsidence"
R_KM = 6371.0088
FPS = 30

# published figures the film quotes (each read at its source on 23 Nov 2026; the notes are in the caption module)
LIT = dict(
    wells=(70, 1300),          # Motagh et al. 2017 (Eng. Geol. 218), citing Jaghdani & Bruemmer 2011: "from approximately 70 in
                               # the 1960s to more than 1300 in the 2000s"
    drawdown_cm=70,            # Mirnezami et al. 2020 (Env. Dev. Sustain. 22), citing IWRMC 2006: "more than 70 cm per year"
    qanat_ce=600,              # Qanat of Gowhar-riz, Jupar: "dates from c 600 CE" (ICOMOS 2016, The Persian Qanat, 1506-009)
    ohadi_h=(800, 900),        # Ohadi's chill requirement, hours at 0-7.2 C: 900 in Asadi Oskouei et al. 2023 (Nivar 47), Table 2;
                               # 800 in Javanshah et al. 2010 (Pistachio Research Institute report)
    pipe_cm=(3, 4), pipe_mm=1200,    # Mehr News 6995870, 10 Aban 1405: the Kerman water company's head, as reported
)
PERSON_M = 1.75                # a person, for scale

# the photographs: file in data/kerman/photos, credit, the line that says what it shows, the point the 9:16 crop is
# centred on (share of width, height), the camera's zoom from, to, the lift (px), a tone (CSS filter)
PHOTOS = dict(
    flow=("qanat_shafiabad_ninara.jpg", "Photo: Ninara · CC BY 2.0", "قنات، شفیع‌آباد، استانِ کرمان", 0.58, 0.5, 1.03, 1.12, 0, ""),
    dry=("qanat_gallery_edmunds.jpg", "Photo: Scott Edmunds · CC BY 2.0", "درونِ یک قنات، استانِ کرمان", 0.5, 0.5, 1.03, 1.12, 0,
         "saturate(.85) brightness(.92) contrast(1.06)"),
    nuts=("pistachio_sigsg510.jpg", "Photo: SIG SG 510 · CC0", "پسته‌ی ایرانی", 0.5, 0.5, 1.03, 1.10, 0, "saturate(.9)"),
    city=("kerman_jameh_edmunds.jpg", "Photo: Scott Edmunds · CC BY 2.0", "مسجدِ جامعِ کرمان", 0.5, 0.42, 1.03, 1.12, 0, ""),
)
PLACES = dict(bahreman=(30.868, 55.654), rafsanjan=(30.400, 55.994))     # the fastest square kilometre (OSM: Bahreman, Nough); the city


def dec(v: float, n: int = 1) -> str:
    return fa(f"{v:.{n}f}".rstrip("0").rstrip(".")).replace(".", "٫")


# ── the stage: the plain on one lon/lat grid (src/kerman_landsat/s13_stage.py) ─────────────────────────────────────
def stage() -> dict:
    from PIL import Image, ImageFilter
    meta = json.loads((STAGE / "stage.json").read_text())
    BUILD.mkdir(parents=True, exist_ok=True)
    for yr in (meta["then"], meta["now"]):
        Image.open(STAGE / f"sat_{yr}.jpg").save(BUILD / f"sat_{yr}.jpg", quality=93)
        g = np.asarray(Image.open(STAGE / f"green_{yr}.png").convert("L").filter(ImageFilter.GaussianBlur(0.8)), dtype=float) / 255
        rgba = np.zeros(g.shape + (4,), np.uint8)
        rgba[..., 0], rgba[..., 1], rgba[..., 2] = 148, 214, 62                  # pistachio green
        rgba[..., 3] = np.round(255 * 0.78 * np.clip(g, 0, 1)).astype(np.uint8)
        Image.fromarray(rgba, "RGBA").save(BUILD / f"green_{yr}.png", optimize=True)
    return meta


def lonlat(meta):
    lon = meta["west"] + (np.arange(meta["width"]) + 0.5) * meta["dlon"]
    lat = meta["north"] - (np.arange(meta["height"]) + 0.5) * meta["dlat"]
    return lon, lat


# ── the sinking ground ───────────────────────────────────────────────────────────────────────────────────────────
def radar() -> dict:
    """B: Payne et al. 2025, Rafsanjan_Bardsir vU (Oct 2014 - Dec 2022, mm/yr, negative = down). A: Haghshenas
    Haghighi & Motagh 2024 (2014-2020, cm/yr, positive = down, the authors' mask). Both as cm/yr down on B's grid."""
    import rasterio
    from rasterio import windows
    from rasterio.warp import Resampling, reproject
    with rasterio.open(SUB / "payne" / "Rafsanjan_Bardsir_vU.geo.tif") as b:
        B = b.read(1).astype(float)
        bt, bb = b.transform, b.bounds
    B[~np.isfinite(B)] = np.nan
    B = -B / 10.0
    with rasterio.open(SUB / "rate_A.tif") as a:
        w = windows.from_bounds(bb.left, bb.bottom, bb.right, bb.top, a.transform).round_offsets().round_lengths()
        A = a.read(1, window=w).astype(float)
        at = a.window_transform(w)
        A[A == a.nodata] = np.nan
    A2 = np.full(B.shape, np.nan)
    reproject(A, A2, src_transform=at, src_crs="EPSG:4326", dst_transform=bt, dst_crs="EPSG:4326",
              resampling=Resampling.nearest, src_nodata=np.nan, dst_nodata=np.nan)
    return dict(A=A2, B=B, T=bt)


def blocks(X, k=10):
    """The mean of every k x k block of pixels (about 1 km2 at 0.001 deg) with at least half of them measured."""
    ny, nx = X.shape
    Y = X[: ny // k * k, : nx // k * k].reshape(ny // k, k, nx // k, k)
    with np.errstate(all="ignore"):
        m = np.nanmean(Y, axis=(1, 3))
    m[np.isfinite(Y).sum(axis=(1, 3)) < k * k // 2] = np.nan
    return m


def sink(meta, R) -> dict:
    """The numbers of the sinking ground, and sink.png: the rate on the stage grid as a glow (2 cm/yr and more)."""
    from PIL import Image
    A, B, T = R["A"], R["B"], R["T"]
    bA, bB = blocks(A), blocks(B)
    iB = np.unravel_index(np.nanargmax(bB), bB.shape)
    lat_b = T.f + T.e * (iB[0] * 10 + 5)
    lon_b = T.c + T.a * (iB[1] * 10 + 5)
    lat = T.f + T.e * (np.arange(B.shape[0]) + 0.5)
    cell = (abs(T.e) * math.pi / 180 * R_KM) * (T.a * math.pi / 180 * R_KM * np.cos(np.radians(lat)))[:, None]
    years_b = 2022 + 12 / 12 - (2014 + 9.5 / 12)              # 1 Oct 2014 .. 31 Dec 2022 (the product's span), in years
    n = dict(block_A=float(np.nanmax(bA)), block_B=float(np.nanmax(bB)), px_A=float(np.nanmax(A)), px_B=float(np.nanmax(B)),
             at=[round(float(lat_b), 3), round(float(lon_b), 3)], years_B=years_b,
             area_ge10_B=float((cell * (B >= 10)).sum()), area_ge5_B=float((cell * (B >= 5)).sum()), area_ge1_B=float((cell * (B >= 1)).sum()),
             r_AB=float(np.corrcoef(A[np.isfinite(A) & np.isfinite(B) & (B >= 2)], B[np.isfinite(A) & np.isfinite(B) & (B >= 2)])[0, 1]))
    n["drop_m"] = n["block_B"] * years_b / 100
    # the glow on the stage grid (B, bilinear)
    lon, la = lonlat(meta)
    from scipy import ndimage
    fb = np.nan_to_num(B, nan=0.0)
    v = ndimage.map_coordinates(fb, [np.repeat((la[:, None] - T.f) / T.e - 0.5, len(lon), 1),
                                     np.repeat(((lon - T.c) / T.a - 0.5)[None, :], len(la), 0)], order=1, mode="nearest")
    v = ndimage.gaussian_filter(v, 2.0)                       # the 100-m pixels drawn soft, not as blocks
    u = np.clip((v - 2.0) / 26.0, 0, 1)                         # 2 .. 28 cm/yr
    stops = np.array([[255, 196, 92], [255, 92, 52], [232, 36, 50], [255, 214, 222]], float)   # amber, orange-red, red, white-hot
    x = u * (len(stops) - 1)
    k = np.clip(np.floor(x).astype(int), 0, len(stops) - 2)
    f = (x - k)[..., None]
    rgb = stops[k] * (1 - f) + stops[k + 1] * f
    alpha = np.where(v >= 2.0, 0.16 + 0.60 * np.sqrt(u), 0.0)                # the orchards show through
    rgba = np.dstack([rgb, 255 * alpha]).round().astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(BUILD / "sink.png", optimize=True)
    n["legend"] = [[2, "۲"], [10, "۱۰"], [20, "۲۰"], [28, "۲۸"]]
    return n


# ── the green: src/kerman_landsat (plain below 2,000 m, OLI 0.20 and its TM equivalent) ─────────────────────────────
def green() -> dict:
    import pandas as pd
    t = pd.read_csv(DATA / "landsat" / "then_now.csv")
    row = t[(t.region == "plain") & (t.method == "harm") & np.isclose(t.t_oli, 0.20)].iloc[0]
    return dict(then_km2=float(row.then_mean_km2), now_km2=float(row.now_mean_km2), ratio=float(row.ratio),
                ratio_lo=float(min(row.ratio_min, row.ratio_if_tm_thr_minus1sd)), ratio_hi=float(max(row.ratio_max, row.ratio_if_tm_thr_plus1sd)))


# ── the air: CRU TS 4.10 over the plain (cell centres in 55.0-56.5 E, 30.0-31.0 N) ────────────────────────────────
def air() -> dict:
    import pandas as pd
    import xarray as xr
    fs = sorted(f for f in glob.glob(str(ROOT / "data" / "water" / "cru_ts4.10.*.tmp.dat.nc")) if int(f.split(".")[-5]) >= 1941)
    ds = xr.open_mfdataset(fs, combine="by_coords")
    x = ds["tmp"].sel(lon=slice(55.0, 56.5), lat=slice(30.0, 31.0))
    s = x.weighted(np.cos(np.radians(x.lat))).mean(("lat", "lon")).to_series()
    s.index = pd.to_datetime(s.index)
    yr = s.groupby(s.index.year).mean().loc[1951:2025]
    a, b = float(yr.loc[1951:1980].mean()), float(yr.loc[1996:2025].mean())
    sm = yr.rolling(11, center=True, min_periods=6).mean()
    return dict(series=[[int(y), round(float(v), 3)] for y, v in yr.items()], smooth=[[int(y), round(float(v), 3)] for y, v in sm.items()],
                first=a, last=b, warming=b - a)


# ── winter chill at Rafsanjan: hourly ERA5-Land (src/kerman_chill.py on the cluster, data/kerman/chill) ─────────────
def chill() -> dict:
    """The 0.1-degree cell of Rafsanjan city: chill hours (0-7.2 C) Nov-Feb and chill portions Oct-Mar, 1996-2025
    against 1951-1980 (winters named by their January); the Mann-Kendall p of each over the 75 winters."""
    from scipy import stats
    Z = [np.load(f) for f in sorted(glob.glob(str(DATA / "chill" / "chill_*.npz")))]
    w = np.array([int(z["winter"]) for z in Z])
    assert len(Z) == 75 and w.min() == 1951 and w.max() == 2025, (len(Z), w.min(), w.max())
    lat, lon, months = Z[0]["lat"], Z[0]["lon"], list(Z[0]["months"])
    i, j = int(np.argmin(abs(lat - PLACES["rafsanjan"][0]))), int(np.argmin(abs(lon - PLACES["rafsanjan"][1])))
    nf = [months.index(m) for m in (11, 12, 1, 2)]
    ch = np.array([z["ch"][nf, i, j].sum() for z in Z])
    cp = np.array([z["cp"][:, i, j].sum() for z in Z])
    out = {}
    for k, v in (("ch", ch), ("cp", cp)):
        a, b = float(v[w <= 1980].mean()), float(v[w >= 1996].mean())
        out[k] = dict(first=a, last=b, change_pct=100 * (b / a - 1), mk_p=float(stats.kendalltau(w, v).pvalue))
    out["cell"] = [float(lat[i]), float(lon[j])]
    return out


# ── the dive: Iran, Kerman, the plain ───────────────────────────────────────────────────────────────────────────
ZOOM = DATA / "zoom"
TEX = dict(iran=((40.0, 22.0, 67.0, 44.0), "tex_iran.jpg"), kerman=((53.8, 27.6, 59.4, 32.4), "tex_kerman.jpg"))   # get_subsidence.wms boxes


def zoom() -> dict:
    """The two satellite pictures of the dive (EOX Sentinel-2 cloudless 2016, fetched with src/get_subsidence.py's
    wms() into data/kerman/zoom), each with the sinking ground of Haghshenas Haghighi & Motagh 2024 (all of Iran,
    2014-2020) as a glow on its own grid (the largest rate inside each of its pixels, so small patches still show at
    the scale of the country); Iran's border and Kerman province's (geoBoundaries ADM0, ADM1; ODbL), simplified."""
    import rasterio
    from PIL import Image
    from rasterio.transform import from_bounds
    from rasterio.warp import Resampling, reproject
    from scipy import ndimage
    from shapely.geometry import shape
    layers = []
    with rasterio.open(SUB / "rate_A.tif") as a:
        A = a.read(1).astype(np.float32)
        A[A == a.nodata] = np.nan
        at = a.transform
    for key, (box, file) in TEX.items():
        im = Image.open(ZOOM / file)
        if im.size[0] > 3072:                                 # a lighter picture for the page (several browsers render at once)
            im = im.resize((3072, round(im.size[1] * 3072 / im.size[0])), Image.LANCZOS)
        w, h = im.size
        im.save(BUILD / file, quality=90)
        g = np.full((h, w), np.nan, np.float32)
        reproject(np.nan_to_num(A, nan=-1.0), g, src_transform=at, src_crs="EPSG:4326", dst_transform=from_bounds(*box, w, h),
                  dst_crs="EPSG:4326", resampling=Resampling.max, src_nodata=None)
        g = ndimage.maximum_filter(np.where(g >= 2.0, g, 0.0), size=5 if key == "iran" else 1)       # seen at the scale of the country
        u = np.clip((g - 2.0) / 26.0, 0, 1)
        stops = np.array([[255, 196, 92], [255, 92, 52], [232, 36, 50], [255, 214, 222]], float)
        x = u * 3
        k = np.clip(np.floor(x).astype(int), 0, 2)
        f = (x - k)[..., None]
        rgb = stops[k] * (1 - f) + stops[k + 1] * f
        alpha = np.where(g >= 2.0, (0.75 if key == "iran" else 0.30) + 0.25 * np.sqrt(u), 0.0)
        Image.fromarray(np.dstack([rgb, 255 * alpha]).round().astype(np.uint8), "RGBA").save(BUILD / f"glow_{key}.png", optimize=True)
        layers.append(dict(key=key, file=file, glow=f"glow_{key}.png", bounds=list(box), w=w, h=h))

    def rings(geom, tol):
        g = shape(geom).simplify(tol)
        polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
        return [[[round(x, 3), round(y, 3)] for x, y in pl.exterior.coords] for pl in polys if pl.area > 0.02]
    a0 = json.loads((ZOOM / "geob_adm0.geojson").read_text())["features"][0]["geometry"]
    a1 = [f for f in json.loads((ZOOM / "geob_adm1.geojson").read_text())["features"] if f["properties"]["shapeName"] == "Kerman"]
    assert len(a1) == 1
    return dict(layers=layers, iran=rings(a0, 0.03), kerman=rings(a1[0]["geometry"], 0.01), label=[29.9, 57.3])


# ── the photographs ──────────────────────────────────────────────────────────────────────────────────────────────
def photos() -> dict:
    """Each photograph cut to 9:16 around its point (1620 x 2880, or the largest the picture allows if smaller), as
    photo_<key>.jpg in the build folder."""
    from PIL import Image, ImageOps
    out = {}
    for key, (file, credit, what, fx, fy, z0, z1, lift, tone) in PHOTOS.items():
        src, dst = DATA / "photos" / file, BUILD / f"photo_{key}.jpg"
        if not dst.exists() or dst.stat().st_mtime < max(src.stat().st_mtime, Path(__file__).stat().st_mtime):
            im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
            w, h = im.size
            cw = min(w, round(h * 9 / 16))
            ch = round(cw * 16 / 9)
            x0 = min(max(0, round(fx * w - cw / 2)), w - cw)
            y0 = min(max(0, round(fy * h - ch / 2)), h - ch)
            size = (1620, 2880) if cw >= 1300 else (1080, 1920)
            im.crop((x0, y0, x0 + cw, y0 + ch)).resize(size, Image.LANCZOS).save(dst, quality=90)
        out[key] = dict(file=dst.name, credit=credit, what=what, zoom=[z0, z1], lift=lift, tone=tone)
    return out


# ── the words ────────────────────────────────────────────────────────────────────────────────────────────────────
SCENES = ("sink", "qanat", "wells", "warm", "city")


def words(n: dict) -> dict:
    s, g, w = n["sink"], n["green"], n["air"]
    rate = 5 * round(s["block_B"] / 5)                        # «تا ۳۰»: the fastest square kilometre, to 5 cm
    assert rate == 30 and 26 <= s["block_A"] <= 32 and s["px_B"] > 30 and s["px_A"] > 30, s
    drop = s["drop_m"]
    assert 2.0 < drop < 2.5 and drop > PERSON_M, drop        # «بیش از ۲ متر؛ بلندتر از یک آدم»
    yrs = round(s["years_B"])
    assert yrs == 8
    ratio = round(g["ratio"], 1)
    assert ratio == 1.4 and g["ratio_lo"] > 1.2, g
    warm = round(w["warming"], 1)
    assert 1.5 <= warm <= 1.9, warm
    c = n["chill"]
    assert -12 < c["ch"]["change_pct"] < -8 and -14 < c["cp"]["change_pct"] < -8 and c["ch"]["mk_p"] < 0.01 and c["cp"]["mk_p"] < 0.01, c   # «حدودِ ۱۰٪ کمتر»
    age = 100 * round((2026 - LIT["qanat_ce"]) / 100)
    assert age == 1400
    w1, w2 = LIT["wells"]
    return dict(
        scenes=dict(
            sink=("زمینِ رفسنجان // {سالی تا %s سانتی‌متر پایین می‌رود}" % fa(rate),
                  "در %s سال: بیش از %s متر؛ بلندتر از یک آدم" % (fa(yrs), fa(int(drop)))),
            qanat=("دشتِ رفسنجان امروز: // {قنات‌ها خشک شده‌اند}", ""),
            wells=("چاه‌ها در ۴۰ سال: // {از %s به بیش از %s}" % (fa(w1), thou(w2)),
                   "باغِ سبز از فضا: حدودِ %s برابر // آبِ زیرِ زمین: سالی بیش از %s سانتی‌متر پایین‌تر" % (dec(ratio), fa(LIT["drawdown_cm"]))),
            warm=("هوای رفسنجان: // {حدودِ %s درجه گرم‌تر}" % dec(warm),
                  "پسته‌ی اوحدی %s تا %s ساعت سرمای زمستان می‌خواهد // ساعت‌های سردِ زمستانِ رفسنجان: حدودِ ۱۰٪ کمتر" % (fa(LIT["ohadi_h"][0]), fa(LIT["ohadi_h"][1]))),
            city=("شهرِ کرمان هم: // {زمین نشست، لوله‌ی آب شکست}",
                  "آبان ۱۴۰۵، آبفای استان: نشستِ %s تا %s سانتی‌متری // شما ترکِ زمین دیده‌اید؟" % (fa(LIT["pipe_cm"][0]), fa(LIT["pipe_cm"][1])))),
        qanat_before=("قرن‌ها قنات // {آبِ کرمان را می‌آورد}", "قناتِ گوهرریزِ جوپار: حدودِ %s سال (یونسکو)" % thou(age)),
        # province: the place's name, large over the province at frame 0 (the owner, 24 Nov 2026)
        sink=dict(bahreman="بهرمان", rafsanjan="رفسنجان", province="کرمان", then="زمین در ۱۳۹۳", now="۱۴۰۱", tag="%s متر" % dec(drop),
                  legend="فرونشست، سانتی‌متر در سال", person="۱٫۷۵ متر"),
        wells=dict(then="۱۳۶۶", now="۱۴۰۴", rafsanjan="رفسنجان"),
        warm=dict(first="۱۳۳۰", last="۱۴۰۴", unit="دمای میانگینِ سال، درجه", gap="+%s" % dec(warm)),
        sources=dict(sink="Sentinel-1 (Payne 2025; Haghshenas Haghighi 2024) · Landsat · EOX",
                     qanat="ICOMOS/UNESCO 2016 · Mirnezami 2020",
                     wells="Motagh 2017 · Mirnezami 2020 · Landsat 5, 8, 9 (USGS)",
                     warm="CRU TS 4.10 · ERA5-Land · Asadi Oskouei 2023 (Nivar)",
                     city="Mehr News, 1 Nov 2026"),
    )


def thou(n: int) -> str:
    return fa(f"{n:,}").replace(",", "٬")


def count(s: str) -> float:
    """Words a reader takes in: digits and signs count 0.4 (the rule of src/onebit_reading.py)."""
    toks = [t for t in str(s).replace("//", " ").replace("{", "").replace("}", "").split() if re.search(r"[\w؀-ۿ۰-۹]", t)]
    return sum(0.4 if re.match(r"^[\d۰-۹٪%٫٬.,:+\-−–()\[\]/«»؟?؛]+$", t) else 1.0 for t in toks)


def reading(W: dict, k: str) -> float:
    full = list(W["scenes"][k])
    half: list = []
    if k == "sink":
        half += [W["sink"][x] for x in ("bahreman", "rafsanjan", "province", "then", "now", "tag", "legend")]
    elif k == "qanat":
        full += list(W["qanat_before"])
    elif k == "wells":
        half += [W["wells"]["then"], W["wells"]["now"]]
    elif k == "warm":
        half += [W["warm"][x] for x in ("first", "last", "unit", "gap")]
    return 1.0 + (sum(map(count, full)) + 0.5 * sum(map(count, half))) / 2.5


# ── the clock ────────────────────────────────────────────────────────────────────────────────────────────────────
# moments inside a scene (seconds after its start). The small lines are not timed here: each comes in when the one
# before it has been read (its words at 2.5 a second, and 0.4 s), and a scene ends when its last line has been read
# and has stood 1.5 s more (the owner, 24 Nov 2026: "is it not too fast to read the Persian text and the plots?")
READ, HOLD, GAP = 2.5, 1.5, 0.4
CUES = dict(
    sink=dict(dive=[0.35, 3.0], glow=[2.7, 3.9], chips=[3.1, 3.6], legend=3.9, pole=[4.3, 7.9], tag=8.0, small=8.4),
    qanat=dict(),                                             # turn and swap: from the first headline's words (film())
    wells=dict(wipe=[0.5, 2.8], green=[2.9, 3.7], small=4.2),  # the map is looked at before the first line comes
    warm=dict(draw=[0.3, 3.0], gap=3.2, small=4.4),            # the chart is drawn and read before the first line
    city=dict(small=3.2),
)
END_HOLD = dict(city=0.5)                                     # the question at the end stands a little longer


def need(s: str) -> float:
    return count(s) / READ


def schedule(first: float, smalls: list) -> list:
    out = [first]
    for x in smalls[:-1]:
        out.append(round(out[-1] + need(x) + GAP, 2))
    return out


# the camera: [t, lon, lat of the anchor point, log10 of the screen pixels per degree of latitude, anchor x, y]
# (east-west is drawn at cos(30.6 deg) of north-south, the plain's own proportion; the Landsat stage has 2,500 px a
# degree, so its scale s is 10 ** v / 2500)
VIEW = dict(
    sink=[[0.0, 54.3, 32.0, math.log10(56), 540, 1000], [0.35, 54.4, 31.95, math.log10(60), 540, 1000],
          [3.0, 55.74, 30.78, math.log10(2650), 540, 900], [9.0, 55.69, 30.84, math.log10(3300), 540, 900],
          [15.0, 55.67, 30.855, math.log10(3500), 540, 900]],
    wells=[[0.0, 55.82, 30.62, math.log10(1950), 540, 1010], [12.0, 55.84, 30.61, math.log10(2150), 540, 1010]],
)


def film() -> dict:
    meta = stage()
    R = radar()
    n = dict(sink=sink(meta, R), green=green(), air=air(), chill=chill())
    W = words(n)
    cues = json.loads(json.dumps(CUES))
    t, scenes = 0.0, []
    for k in SCENES:
        title, small = W["scenes"][k]
        sc = dict(key=k, start=t, title=title, small=small, source=W["sources"][k])
        smalls = [x for x in small.split(" // ") if x] if small else []
        if k == "qanat":                                      # the first headline and its line are read over the flowing qanat
            first = 0.4 + need(W["qanat_before"][0] + " " + W["qanat_before"][1]) + 1.2
            cues[k].update(turn=round(first, 2), swap=[round(first - 0.5, 2), round(first + 0.4, 2)])
            sc.update(before=W["qanat_before"][0], before_small=W["qanat_before"][1], turn=cues[k]["turn"])
            done = first + 0.4 + need(title) + HOLD
        else:
            at = schedule(cues[k]["small"], smalls)
            sc["small_at"] = at
            cues[k]["small"] = at
            done = at[-1] + need(smalls[-1]) + HOLD + END_HOLD.get(k, 0.0)
        L = math.ceil(4 * max(done, reading(W, k))) / 4
        sc["length"] = L
        scenes.append(sc)
        t += L
    out = dict(size=[1080, 1920], fps=FPS, end=t, scenes=scenes, cues=cues, view=VIEW, words=W, zoom=zoom(),
               stage=dict(meta, files=dict(then=f"sat_{meta['then']}.jpg", now=f"sat_{meta['now']}.jpg",
                                           green_then=f"green_{meta['then']}.png", green_now=f"green_{meta['now']}.png", sink="sink.png")),
               places=dict(PLACES, fastest=n["sink"]["at"]), numbers=dict(sink={k: v for k, v in n["sink"].items() if k != "legend"},
                                                                          green=n["green"], air={k: v for k, v in n["air"].items() if k not in ("series", "smooth")}, chill=n["chill"]),
               legend=n["sink"]["legend"], air=dict(series=n["air"]["series"], smooth=n["air"]["smooth"], first=n["air"]["first"], last=n["air"]["last"]),
               photos=photos(), person_m=PERSON_M, cover_t=1.2)
    (BUILD / "film.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main() -> None:
    f = film()
    s = f["numbers"]["sink"]
    print("sink: fastest 1-km block B %.1f (A %.1f) cm/yr at %s; pixels B %.1f, A %.1f; r(A,B) %.3f; area >=10 cm/yr %.0f km2, >=5 %.0f, >=1 %.0f"
          % (s["block_B"], s["block_A"], s["at"], s["px_B"], s["px_A"], s["r_AB"], s["area_ge10_B"], s["area_ge5_B"], s["area_ge1_B"]))
    print("      %.1f yr x %.1f cm/yr = %.2f m" % (s["years_B"], s["block_B"], s["drop_m"]))
    g, a = f["numbers"]["green"], f["numbers"]["air"]
    print("green: %.1f -> %.1f km2, x%.2f (%.2f-%.2f)" % (g["then_km2"], g["now_km2"], g["ratio"], g["ratio_lo"], g["ratio_hi"]))
    print("air: 1951-1980 %.2f, 1996-2025 %.2f, +%.2f C" % (a["first"], a["last"], a["warming"]))
    c = f["numbers"]["chill"]
    print("chill at %s: hours Nov-Feb %.0f -> %.0f (%+.1f %%, p %.1g); portions Oct-Mar %.1f -> %.1f (%+.1f %%, p %.1g)"
          % (c["cell"], c["ch"]["first"], c["ch"]["last"], c["ch"]["change_pct"], c["ch"]["mk_p"], c["cp"]["first"], c["cp"]["last"], c["cp"]["change_pct"], c["cp"]["mk_p"]))
    print("clock: %.2f s, %d frames: " % (f["end"], round(f["end"] * FPS)) + ", ".join(f"{s['key']} {s['start']:g}+{s['length']:g}" for s in f["scenes"]))


if __name__ == "__main__":
    main()
