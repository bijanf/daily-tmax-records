"""The data of the Köppen film (koppen_fa): Iran's climate classes in the 1-km Köppen-Geiger maps of Beck et al.
(2023), the recent climate (1991-2020) against the end of the century (2071-2099), and what the film says with them.

What moves is warmth, not desert. In these maps a dry climate is "hot" (h) when its mean annual temperature is 18 C or
more and "cold" (k) below that, and a climate has a freezing winter (D) when its coldest month averages 0 C or less
(the paper's Table 1). Desert as a whole barely changes over Iran (51 % of the country in 1991-2020, 53 % in 2071-2099
under the middle scenario); the dry land above the 18 C line grows (52 % to 63 %) and the freezing-winter climates
shrink (13 % to 8 %). So the film counts those two, as shares of Iran's area, and never "how much of Iran changes
class": the two observed maps 1961-1990 and 1991-2020 already differ on 15 % of Iran, most of it at uncertain edges.
The checks in measures(): the shares hold where the maps are confident (kg_confidence >= 50 %); the 18 C line read
from ERA5-Land (a reanalysis, not the maps' own climatologies) gives the same picture for 1961-1990 and 1991-2020.

The future maps: the 1991-2020 climatology plus each climate model's monthly change (the delta method), the class of a
cell being the most common class among the models; the scenario on screen is SSP2-4.5 ("the middle scenario"), with
SSP1-2.6 and SSP5-8.5 as the range.

    python -I src/get_koppen.py        # the maps (first)
    python -I src/koppen.py            # the numbers; outputs/onebit/koppen/film.json and the map pictures
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import get_koppen  # noqa: E402

ROOT = get_koppen.ROOT
DATA = get_koppen.DATA
BUILD = ROOT / "outputs" / "onebit" / "koppen"
RELIEF = ROOT / "data" / "air" / "relief_v4.npz"
REL = dict(lon0=42.5, lat0=45.5, step=0.01)                 # the relief's grid (src/air_grid.py REL): north edge lat0
BLUE = ROOT / "data" / "air" / "bluemarble_srb_iran.jpg"
BM = dict(lon0=42.0, lat0=45.5, step=0.005)                 # the Blue Marble crop (src/onebit_air.py BM)
ERA5 = DATA / "era5land_t2m_monthly_1961_2020.nc"           # ERA5-Land monthly 2 m temperature over Iran's box (the check)
FPS = 30
BOX = (43.8, 24.8, 63.6, 40.0)                             # west, south, east, north: Iran's box on the maps
NOW, LATER = "1991_2020", "2071_2099_ssp245"
RANGE = ("2071_2099_ssp126", "2071_2099_ssp245", "2071_2099_ssp585")
# the film's groups of classes: key, the maps' class numbers, the colour, the name on screen
GROUPS = (("bwh", (4,), "#C9472D", "بیابانیِ گرم"),
          ("bwk", (5,), "#F1B898", "بیابانیِ سرد"),
          ("bsh", (6,), "#E39833", "نیمه‌خشکِ گرم"),
          ("bsk", (7,), "#F2DB9A", "نیمه‌خشکِ سرد"),
          ("cs", (8, 9, 10), "#9CC25A", "معتدل، تابستانِ خشک"),
          ("cf", (11, 12, 13, 14, 15, 16), "#3D9962", "معتدل و مرطوب"),
          ("d", tuple(range(17, 29)), "#6C9AD6", "زمستانِ یخ‌بندان"),
          ("e", (29, 30), "#EEF2F7", "توندرا (قله‌های سرد)"))
HOT_DRY, FREEZING, DESERT = (4, 6), tuple(range(17, 29)), (4, 5)
OTHER = "#C9C4BA"                                          # the winter scene: every class but the freezing-winter ones, faded to this grey
# the frames: the whole country, and Tehran with the Alborz (lon, lat at frame point (xc, yc); sx px per degree of longitude)
FRAMES = dict(iran=dict(lon=53.7, lat=32.4, sx=38.5, xc=540, yc=944), tehran=dict(lon=51.55, lat=35.75, sx=175.0, xc=540, yc=955))
SS = 2                                                     # the pictures are drawn at twice the frame's size, then reduced
# the places on the close map: name, lon, lat, the side of its pin the name stands on (e east, w west)
PLACES = (("تهران", 51.39, 35.69, "e"), ("کرج", 50.94, 35.84, "w"), ("قم", 50.88, 34.64, "e"), ("ساری", 53.06, 36.56, "e"), ("دماوند", 52.11, 35.95, "e"))
TEHRAN_BOX = (51.20, 35.58, 51.60, 35.85)                 # west, south, east, north: the city as a whole (approximate)
CITIES = {"تهران": (51.39, 35.69), "اصفهان": (51.67, 32.65), "کرمان": (57.08, 30.28), "همدان": (48.51, 34.80),
          "شیراز": (52.53, 29.59), "تبریز": (46.29, 38.08), "مشهد": (59.61, 36.30), "اهواز": (48.67, 31.32)}
_CACHE: dict = {}


def fa_year(y: int) -> int:
    """The Persian year in which the summer of a Gregorian year falls."""
    return y - 621


def half_up(x: float) -> int:
    return int(np.floor(x + 0.5))


def iran_shape():
    import shapefile
    from shapely.geometry import shape
    from shapely.ops import unary_union
    if "iran" not in _CACHE:
        r = shapefile.Reader(str(DATA / "ne" / "ne_10m_admin_1_states_provinces.shp"), encoding="utf-8")
        fields = [f[0] for f in r.fields[1:]]
        polys = [shape(sr.shape.__geo_interface__) for sr in r.iterShapeRecords() if dict(zip(fields, sr.record)).get("adm0_a3") == "IRN"]
        assert len(polys) == 31, len(polys)
        _CACHE["iran"] = unary_union(polys)
    return _CACHE["iran"]


def read(tag: str, box=BOX, confidence: bool = False):
    """A map's classes (and its confidence, %) over a box: arrays north to south, the cell centres' lon and lat."""
    import netCDF4
    key = (tag, box, confidence)
    if key not in _CACHE:
        d = netCDF4.Dataset(DATA / "nc" / f"{tag}.nc")
        d.set_auto_mask(False)
        lon, lat = d["lon"][:], d["lat"][:]
        i = np.where((lon >= box[0]) & (lon <= box[2]))[0]
        j = np.where((lat >= box[1]) & (lat <= box[3]))[0]
        c = d["kg_class"][j.min():j.max() + 1, i.min():i.max() + 1].astype(np.int16)
        k = d["kg_confidence"][j.min():j.max() + 1, i.min():i.max() + 1].astype(np.int16) if confidence else None
        la = lat[j.min():j.max() + 1]
        if la[0] < la[-1]:
            c, la = c[::-1], la[::-1]
            k = k[::-1] if k is not None else None
        _CACHE[key] = (c, k, lon[i.min():i.max() + 1], la)
    return _CACHE[key]


def iran_mask(lon, lat) -> np.ndarray:
    from rasterio.features import rasterize
    from rasterio.transform import from_origin
    step = float(lon[1] - lon[0])
    t = from_origin(float(lon[0]) - step / 2, float(lat[0]) + step / 2, step, step)
    return rasterize([(iran_shape(), 1)], out_shape=(len(lat), len(lon)), transform=t, fill=0, dtype="uint8").astype(bool)


def measures() -> dict:
    c0, k0, lon, lat = read(NOW, confidence=True)
    mask = iran_mask(lon, lat) & (c0 > 0)
    w = np.repeat(np.cos(np.radians(lat))[:, None], len(lon), axis=1)
    tot = w[mask].sum()
    pct = lambda sel: float(100 * w[sel & mask].sum() / tot)                                   # noqa: E731
    km2 = float(tot * (111.32 * abs(lon[1] - lon[0])) ** 2)
    out = dict(area_km2=km2, maps={})
    for tag in ("1961_1990", NOW, "2041_2070_ssp245", "2071_2099_ssp126", LATER, "2071_2099_ssp370", "2071_2099_ssp585"):
        c, k, _, _ = read(tag, confidence=True)
        sure = (k >= 50) & (k0 >= 50)
        row = dict(hot_dry=pct(np.isin(c, HOT_DRY)), freezing=pct(np.isin(c, FREEZING)), desert=pct(np.isin(c, DESERT)),
                   dry=pct(np.isin(c, (4, 5, 6, 7))), hot_dry_sure=pct(np.isin(c, HOT_DRY) & (k >= 50)), freezing_sure=pct(np.isin(c, FREEZING) & (k >= 50)),
                   changed=pct(c != c0), changed_sure=pct((c != c0) & sure),
                   groups={g: pct(np.isin(c, cls)) for g, cls, _, _ in GROUPS},
                   tropical=pct(np.isin(c, (1, 2, 3))))
        out["maps"][tag] = row
    # the cities: the class of the 5 x 5 cells around each (the most common), with the confidence of its centre
    sym = {4: "BWh", 5: "BWk", 6: "BSh", 7: "BSk", 8: "Csa", 9: "Csb", 14: "Cfa", 17: "Dsa", 18: "Dsb", 19: "Dsc", 26: "Dfb", 29: "ET"}
    out["cities"] = {}
    for name, (x, y) in CITIES.items():
        row = {}
        for tag in ("1961_1990", NOW, *RANGE):
            c, k, lo, la = read(tag, confidence=True)
            i, j = int(np.argmin(np.abs(lo - x))), int(np.argmin(np.abs(la - y)))
            vals, cnt = np.unique(c[j - 2:j + 3, i - 2:i + 3], return_counts=True)
            row[tag] = dict(cls=sym.get(int(vals[np.argmax(cnt)]), int(vals[np.argmax(cnt)])), of25=int(cnt.max()), conf=int(k[j, i]))
        out["cities"][name] = row
    out["tehran_city"] = {}
    for tag in (NOW, *RANGE):
        c, _, lo, la = read(tag, box=TEHRAN_BOX)
        wt = np.repeat(np.cos(np.radians(la))[:, None], len(lo), axis=1)
        out["tehran_city"][tag] = {sym.get(int(v), str(int(v))): float(100 * wt[c == v].sum() / wt[c > 0].sum()) for v in np.unique(c[c > 0])}
    out["era5"] = era5_check() if ERA5.exists() else None
    return out


def era5_check() -> dict:
    """The 18 C line from ERA5-Land: the share of Iran's dry area (the map's dry classes) at or above it, by period, and
    how much of the dry area the two agree on."""
    import netCDF4
    import rasterio
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject
    d = netCDF4.Dataset(ERA5)
    d.set_auto_mask(False)
    lat, lon = d["latitude"][:], d["longitude"][:]
    t = d["t2m"][:].astype(float) - 273.15
    tv = d["valid_time"]
    years = np.array([x.year for x in netCDF4.num2date(tv[:], tv.units)])
    t[np.abs(t) > 100] = np.nan
    assert lat[0] > lat[-1] and t.shape[0] == 720
    step = float(abs(lon[1] - lon[0]))
    tr = from_origin(float(lon[0]) - step / 2, float(lat[0]) + step / 2, step, step)
    m = iran_mask(lon, lat)
    w = np.repeat(np.cos(np.radians(lat))[:, None], len(lon), axis=1)
    out = {}
    for tag, (a, b) in (("1961_1990", (1961, 1990)), (NOW, (1991, 2020))):
        mat = np.nanmean(t[(years >= a) & (years <= b)], axis=0)
        with rasterio.open(DATA / "tif" / f"{tag}.tif") as src:
            c = np.zeros((len(lat), len(lon)), np.uint8)
            reproject(rasterio.band(src, 1), c, dst_transform=tr, dst_crs=src.crs, resampling=Resampling.mode)
        ok = m & np.isfinite(mat) & (c > 0)
        dry = ok & np.isin(c, (4, 5, 6, 7))
        out[tag] = dict(era5=float(100 * w[dry & (mat >= 18)].sum() / w[ok].sum()), maps=float(100 * w[ok & np.isin(c, HOT_DRY)].sum() / w[ok].sum()),
                        agree=float(100 * w[dry & ((mat >= 18) == np.isin(c, HOT_DRY))].sum() / w[dry].sum()),
                        mean_t=float(np.sum(mat[ok] * w[ok]) / w[ok].sum()))
    return out


def words_of(m: dict) -> dict:
    from onebit import fa
    M = m["maps"]
    y = lambda g: fa(fa_year(g))                                                                # noqa: E731
    now_span, later_span = f"{y(1991)} تا {y(2020)}", f"{y(2071)} تا {y(2099)}"
    p = lambda v: f"{fa(half_up(v))}٪"                                                           # noqa: E731
    return dict(
        hook=(f"اقلیمِ ایران: مناطقِ خشکِ گرم // {{{now_span}: {p(M[NOW]['hot_dry'])} از ایران}} // "
              f"{{{later_span}: {p(M[LATER]['hot_dry'])} از ایران}}"),
        note_a="گرم: میانگینِ سالانه ۱۸ درجه یا بیشتر؛ آینده: انتشارِ میانه",
        head_b=(f"مناطقِ زمستانِ یخ‌بندان // {{{now_span}: {p(M[NOW]['freezing'])} از ایران}} // "
                f"{{{later_span}: {p(M[LATER]['freezing'])} از ایران}}"),
        note_b="یخ‌بندان: میانگینِ سردترین ماه صفر یا کمتر؛ آینده: انتشارِ میانه",
        head_c=f"بیشترِ شهرِ تهران // {{{now_span}: نیمه‌خشکِ سرد}} // {{{later_span}: نیمه‌خشکِ گرم}}",
        note_c="آینده: انتشارِ میانه",
        head_d="پایانِ قرن، بسته به انتشارِ گازهای گلخانه‌ای // {سهمِ مناطقِ خشکِ گرم از ایران}",
        d_now=now_span, d_low="کم", d_mid="میانه", d_high="زیاد", d_later=f"{later_span}، سه سناریوی انتشار",
        v_now=p(M[NOW]["hot_dry"]), v_low=p(M[RANGE[0]]["hot_dry"]), v_mid=p(M[RANGE[1]]["hot_dry"]), v_high=p(M[RANGE[2]]["hot_dry"]),
        head_e="شهرِ شما // {چه رنگی است؟}", follow="برای یک دوست بفرستید",
        legend=[name for _, _, _, name in GROUPS], legend_d=["زمستانِ یخ‌بندان", "اقلیم‌های دیگر"],
        places=[name for name, _, _, _ in PLACES],
        src_a=CREDIT, src_b=CREDIT, src_c=CREDIT,
        src_d="همان نقشه‌ها؛ آینده: برآوردِ مدل‌های اقلیمی در سه سناریوی انتشار",
        src_e="منابع و روش در کامنتِ اول // " + CREDIT.split(" // ")[0])


# the credit on every map: the maps (CC BY 4.0), the relief (Copernicus DEM; the full notice is in the first comment)
# and the background outside Iran (NASA Blue Marble)
CREDIT = "داده: نقشه‌های ۱ کیلومتریِ کوپن، Beck و همکاران ۲۰۲۳ // پستی‌وبلندی: Copernicus DEM؛ تصویرِ زمینه: NASA"


def clock_of() -> dict:
    a = (0.0, 14.0)
    b = (a[1], a[1] + 10.5)
    c = (b[1], b[1] + 11.3)
    d = (c[1], c[1] + 8.6)
    e = (d[1], d[1] + 4.8)
    out = (e[1], e[1] + 0.8)
    return dict(a=a, b=b, c=c, d=d, e=e, out=out,
                wipe_a=(0.6, 6.0), wipe_b=(b[0] + 1.4, b[0] + 5.8), wipe_c=(c[0] + 1.4, c[0] + 5.8),
                bars=(d[0] + 0.6, d[0] + 3.0), follow=e[0] + 1.2)


def reading(Wd: dict, C: dict) -> None:
    """The owner's reading rule (src/onebit_reading.py), asserted on every scene: at least 1 s plus its words at 2.5 a
    second (headline and sentences in full, labels at half, source lines not at all) and 3 s after its last string."""
    import onebit_reading as rd
    wt = lambda xs: sum(rd.weight(x) for x in xs)    # noqa: E731
    plan = [("hook", C["a"], [Wd["hook"], Wd["note_a"]], Wd["legend"], C["wipe_a"][1]),
            ("winter", C["b"], [Wd["head_b"], Wd["note_b"]], Wd["legend_d"], C["wipe_b"][1]),
            ("tehran", C["c"], [Wd["head_c"], Wd["note_c"]], Wd["legend"] + Wd["places"], C["wipe_c"][1]),
            ("range", C["d"], [Wd["head_d"]], [Wd[k] for k in ("d_now", "d_low", "d_mid", "d_high", "d_later", "v_now", "v_low", "v_mid", "v_high")], C["bars"][1]),
            ("close", C["e"], [Wd["head_e"], Wd["follow"]], [], C["follow"])]
    print("\nreading (seconds the rule needs, seconds given):")
    short = []
    for name, (a, b), full, half, last in plan:
        w = wt(full) + rd.LABELS * wt(half)
        need = max(rd.SETTLE + w / rd.WPS, last - a + rd.HOLD)
        print(f"  {name:6s} {wt(full):4.1f} + {wt(half):4.1f}/2 words -> {need:4.1f} s needed, {b - a:4.1f} s given")
        if b - a + 0.051 < need:
            short.append((name, round(need, 2), round(b - a, 2)))
    assert not short, short


def hexrgb(h: str) -> np.ndarray:
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], float)


def frame_lonlat(f: dict, ss: int = SS):
    """The lon and lat of every pixel centre of a frame drawn at ss times its size."""
    sy = f["sx"] / np.cos(np.radians(f["lat"]))
    x = (np.arange(1080 * ss) + 0.5) / ss
    yy = (np.arange(1920 * ss) + 0.5) / ss
    return f["lon"] + (x[None, :] - f["xc"]) / f["sx"], f["lat"] - (yy[:, None] - f["yc"]) / sy


def sample(grid: np.ndarray, g: dict, lon, lat, fill=0):
    """Nearest cell of a north-to-south grid (north edge lat0, west edge lon0, square cells of g['step'] degrees)."""
    i = np.floor((lon - g["lon0"]) / g["step"]).astype(int)
    j = np.floor((g["lat0"] - lat) / g["step"]).astype(int)
    ok = (i >= 0) & (j >= 0) & (i < grid.shape[1]) & (j < grid.shape[0])
    out = np.full(np.broadcast(i, j).shape + grid.shape[2:], fill, grid.dtype)
    ii, jj = np.broadcast_arrays(i, j)
    out[ok] = grid[jj[ok], ii[ok]]
    return out


def pictures() -> dict:
    """The frames' pictures: the ground (the Blue Marble, dimmed, outside Iran) and, for each map, Iran in the film's
    colours over the hillshade (with transparency outside Iran); for the winter scene the freezing-winter climates in
    their colour and every other class faded to grey."""
    from PIL import Image
    BUILD.mkdir(parents=True, exist_ok=True)
    rel = np.load(RELIEF)
    hs, land = rel["hs"], rel["land"]
    lo, hi = np.percentile(hs[land > 0], [5, 95])
    bm = np.asarray(Image.open(BLUE).convert("RGB"))
    lut = np.zeros((31, 3))
    for _, cls, colour, _ in GROUPS:
        lut[list(cls)] = hexrgb(colour)
    grey = hexrgb(OTHER)
    out = {}
    for fname, f in FRAMES.items():
        lon, lat = frame_lonlat(f)
        lon2, lat2 = np.broadcast_arrays(lon, lat)
        shade = np.clip(0.86 + 0.34 * (sample(hs, REL, lon2, lat2, np.float32(np.median(hs))) - np.median(hs)) / (hi - lo), 0.6, 1.06)[..., None]
        ground = sample(bm, BM, lon2, lat2, 0).astype(float) * 0.5
        ground[lat2 > BM["lat0"]] = 0
        Image.fromarray(ground.astype(np.uint8)).resize((1080, 1920), Image.LANCZOS).save(BUILD / f"ground_{fname}.jpg", quality=92)
        layers = {}
        for tag in (NOW, LATER):
            c, _, glon, glat = read(tag)
            step = float(glon[1] - glon[0])
            g = dict(lon0=float(glon[0]) - step / 2, lat0=float(glat[0]) + step / 2, step=step)
            inside = sample(iran_mask(glon, glat).astype(np.uint8), g, lon2, lat2, 0) > 0
            cls = sample(c, g, lon2, lat2, 0)
            cls[~inside] = 0
            for kind in ("full", "winter"):
                rgb = lut[np.clip(cls, 0, 30)].copy()
                if kind == "winter":
                    other = ~np.isin(cls, FREEZING)
                    rgb[other] = 0.1 * rgb[other] + 0.9 * grey
                rgb = np.clip(rgb * shade, 0, 255)
                alpha = (inside & (cls > 0)).astype(float)[..., None] * 255
                im = Image.fromarray(np.concatenate([rgb, alpha], -1).astype(np.uint8), "RGBA").resize((1080, 1920), Image.LANCZOS)
                name = f"{fname}_{tag}_{kind}.png"
                im.save(BUILD / name)
                layers[f"{tag}_{kind}"] = name
        out[fname] = dict(frame=f, ground=f"ground_{fname}.jpg", layers=layers)
        if fname == "iran":
            inside_ = sample(iran_mask(*read(NOW)[2:]).astype(np.uint8), dict(lon0=float(read(NOW)[2][0]) - 0.5 / 120, lat0=float(read(NOW)[3][0]) + 0.5 / 120, step=1 / 120), lon2, lat2, 0) > 0
            out["other_swatch"] = "#" + "".join(f"{int(round(v)):02X}" for v in np.clip(grey * float(np.median(shade[..., 0][inside_])), 0, 255))
    return out


def film() -> dict:
    m = measures()
    M = m["maps"]
    for tag, r in M.items():
        print(f"{tag:18s} hot dry {r['hot_dry']:5.1f} ({r['hot_dry_sure']:5.1f} sure)  freezing {r['freezing']:5.1f} ({r['freezing_sure']:5.1f})  "
              f"desert {r['desert']:5.1f}  all dry {r['dry']:5.1f}  changed {r['changed']:5.1f} ({r['changed_sure']:5.1f} sure)")
    for name, row in m["cities"].items():
        print(f"  {name:8s}", "  ".join(f"{t}: {v['cls']} ({v['conf']} %)" for t, v in row.items()))
    print("ERA5-Land check:", m["era5"])
    now, later = M[NOW], M[LATER]
    # «۵۲٪ → ۶۳٪» and «۱۳٪ → ۸٪», and the range «۵۸ / ۶۳ / ۷۲»; each also where the maps are confident (within 1 point)
    assert (half_up(now["hot_dry"]), half_up(later["hot_dry"])) == (52, 63), (now["hot_dry"], later["hot_dry"])
    assert (half_up(now["freezing"]), half_up(later["freezing"])) == (13, 8), (now["freezing"], later["freezing"])
    assert [half_up(M[t]["hot_dry"]) for t in RANGE] == [58, 63, 72], [M[t]["hot_dry"] for t in RANGE]
    for r in (now, later):
        assert abs(r["hot_dry"] - r["hot_dry_sure"]) < 1 and abs(r["freezing"] - r["freezing_sure"]) < 1, r
    # not "desert spreads": desert as a whole moves by about 2 points, all dry climates by less than 1
    assert abs(later["desert"] - now["desert"]) < 3 and abs(later["dry"] - now["dry"]) < 1, (now, later)
    # the change of class is not shown: the observed noise floor is as large as the low scenario
    assert M["1961_1990"]["changed"] > 0.8 * M["2071_2099_ssp126"]["changed"]
    assert all(r["tropical"] == 0 for r in M.values())                                          # no class outside the legend
    # Tehran: cold semi-arid now, hot semi-arid later in every scenario, the models agreeing
    T = m["cities"]["تهران"]
    assert T[NOW]["cls"] == "BSk" and all(T[t]["cls"] == "BSh" for t in RANGE) and T[LATER]["conf"] >= 75, T
    TC = m["tehran_city"]                                        # «بیشترِ شهر»: more than half the city, now and later (middle)
    assert TC[NOW]["BSk"] > 50 and TC[LATER]["BSh"] > 50 and max(TC[NOW], key=TC[NOW].get) == "BSk" and max(TC[LATER], key=TC[LATER].get) == "BSh", TC
    if m["era5"]:
        e = m["era5"]
        assert e[NOW]["era5"] > e["1961_1990"]["era5"] and e[NOW]["maps"] > e["1961_1990"]["maps"]      # the same direction
        assert min(e[t]["agree"] for t in e) > 90 and abs(e[NOW]["era5"] - e[NOW]["maps"]) < 5, e
    Wd, C = words_of(m), clock_of()
    reading(Wd, C)
    pics = pictures()
    F = dict(fps=FPS, size=[1080, 1920], cover_t=4.0, end=C["out"][1], clock=C, words=Wd,
             colours=dict(gold="#F6C445", ink="#1d140c", paper="#FBF7F0", cool="#f3ead8", less="#BDE7B0", more="#FA8072",
                          groups=[colour for _, _, colour, _ in GROUPS], other=pics.pop("other_swatch"), freezing=GROUPS[6][2]),
             pair=dict(a=[None, "less", "more"], b=[None, "less", "more"], c=[None, "less", "more"]),
             bars=dict(values=[now["hot_dry"], M[RANGE[0]]["hot_dry"], M[RANGE[1]]["hot_dry"], M[RANGE[2]]["hot_dry"]], top=80),
             places=[dict(name=n, lon=x, lat=y, side=side) for n, x, y, side in PLACES],
             numbers=m, pictures=pics)
    (BUILD / "film.json").write_text(json.dumps(F, ensure_ascii=False, indent=1))
    print(f"saved {BUILD / 'film.json'} | end {F['end']:.1f} s")
    return F


if __name__ == "__main__":
    film()
