"""TEHRAN AND BEIJING, EIGHT WINTERS OF NO2 FROM SPACE, PHONE-SIZED: the map of Asia from Iran to China, then the two
close-ups (Beijing on the left, Tehran on the right), then the strip of the ratio for each winter, then the reasons.

A sibling of onebit_compare8m.py (Tehran and Istanbul) on the same layout, type sizes, safe zones, colour transfer and
clock. Imported, not copied: the transfer (intensity, invert, bar_x), the glow and the paint (onebit_compare), the strip,
the counter, the chips and the word line (onebit_compare8m's and onebit_compare8's layers and constants), the fade, the
type. Nothing in those files is edited. What this film changes:
  - the map: the Blue Marble of Asia (NASA GIBS, keyless), darkened as onebit_compare's base, with the two cities marked
    and a thin arc between them. The map carries no NO2 glow: the satellite fields are the close-ups' only;
  - the close-ups: both are the same 2.0 x 2.0 degree square (+-1.0 deg of longitude and latitude), 480 px each. The
    ground width is 180 km for Tehran and 171 km for Beijing (one degree of longitude is 90 km at 35.7 N and 85 km at
    39.9 N). No scale bar: the squares are not the same size in km;
  - Beijing's field: the mean of the eight per-winter fields of data/air/compare/beijing/beijing_fields_v1.npz (the
    beijing_YYYY_field arrays, 1397-1404), on the same 100 x 100 grid; Tehran's field: winter8 of
    data/air/compare/region8/region_8winters_v1.npz (every 4th day, the same field as onebit_compare8m's), cropped to the
    same +-1.0 degree square. Both are sampled on each close-up's pixels by onebit_compare's sample_field;
  - the strip: the ratio R = Tehran / Beijing of each winter (beijing_v1.json, the pre-registered per-winter ratios: every
    valid day, the core +-0.15 deg), bars from 1397 (right) to 1404 (left);
  - the mean line and the headline: the ratio of the eight-winter means (sum of the eight Tehran winter means over the sum
    of the eight Beijing winter means), with its 90 % interval from a day bootstrap (10,000 draws, air_beijing's seed).
    The headline says «بیش از ۳ برابر» only if the interval's lower bound exceeds 3, else «حدودِ ۳ برابر» (asserted).

The eight-winter ratio of means is computed here from the day series (air_beijing) and cached in
data/air/compare/beijing/ratio_of_means_v1.json; the per-winter ratios are read from beijing_v1.json.

Clock (seconds; the narration clock is FIXED, as onebit_compare8r):
  N1 0.20-5.50, N2 5.50-10.20, N3 10.20-14.20, N4 17.00-19.70, N5 19.50-28.75; DURATION 30.0
  0 - 4.5      S1  the title, the darkened map of Asia with both cities and the arc, the label «میانگینِ هشت زمستان»
  4.5 - 5.3    S2  the map gives way; the two close-ups grow in; the colour bar and unit line fade in; the strip's bars rise
  17.0 - 17.5  S3  the counter fades; the headline comes in (the mean line from 17.0 s)
  19.5 - 20.0  S4  the strip fades out; four reason chips appear at the onsets of N5's words (20.55, 23.31, 24.87, 26.29 s)

Layout (px, 1080 x 1920) is onebit_compare8m's (same title, label, close-ups, colour bar, unit line, strip, headline,
chips and sources line). The close-ups are at SQ_X: Beijing 48 (left), Tehran 552 (right), top 362.

    python -I src/onebit_beijing.py              # the silent reel (its cover from frame 0, then the MP4)
    python -I src/onebit_beijing.py --stills     # the stills at STILLS
    python -I src/onebit_beijing.py --check      # the colour check of the close-ups (the land boxes against the fields)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit_compare as oc  # noqa: E402
import onebit_compare8 as f8  # noqa: E402
import onebit_compare8m as m8  # noqa: E402
import onebit_compare8r as f8r  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, SIZES, SOCIAL_CRF, fa  # noqa: E402

W, H = oc.W, oc.H
DURATION = 30.0                                   # s: the reel (N5 ends at 28.75 s)
BASE = "tehran_beijing_fa"
STILLS = (0.0, 3.0, 8.0, 13.0, 18.0, 22.0, 27.0)
S2 = m8.S2                                        # s: the map gives way, the close-ups grow in (0.8 s ease)
GLOW0, T_FULL = m8.GLOW0, m8.T_FULL
BAR_T0, BAR_RISE, BAR_TIMES = f8.BAR_T0, f8.BAR_RISE, f8.BAR_TIMES
T_HOLD, T_HOLD_FADE = f8.T_HOLD, f8.T_HOLD_FADE
STRIP_FADE = m8.STRIP_FADE                        # s: the strip and its labels fade out
CHIP_FADE, CHIP_TEXT = m8.CHIP_FADE, m8.CHIP_TEXT
CHIP_SHIFT = 0.36                                 # s: N5's new «یک دلیلِ احتمالی» moves each reason word later by this
                                                  # (measured on the wav: the envelope shifts by 0.36 s after «احتمالی»)
CHIP_T = tuple(round(t + CHIP_SHIFT, 2) for t in m8.CHIP_T)   # 20.91, 23.67, 25.23, 26.65 s
N5_START, N5_END = m8.N5_START, m8.N5_END
YEARS = list(f8.YEARS)
DARK = m8.DARK
REGION8 = oc.DATA / "region8" / "region_8winters_v1.npz"
BJ_DIR = oc.DATA / "beijing"
BJ_FIELDS = BJ_DIR / "beijing_fields_v1.npz"
BJ_TEST = BJ_DIR / "beijing_v1.json"
RATIO_JSON = BJ_DIR / "ratio_of_means_v1.json"
BM_ASIA = BJ_DIR / "bluemarble_asia_v1.jpg"
N_BOOT, SEED = 10000, None                        # SEED: air_beijing's (set on first use)

# ── the cities (deg) ──
CITY = dict(beijing=(116.40, 39.90), tehran=(51.39, 35.69))
NAME = dict(beijing="پکن", tehran="تهران")
CLOSE_ORDER = ("beijing", "tehran")              # Beijing on the left, Tehran on the right
HALF_DEG = 1.0                                    # deg: a close-up's half side (longitude and latitude)
MARGIN = oc.MARGIN                                # deg: the Blue Marble tile's margin around a close-up

# ── the map (px per degree of longitude; the centre (lon, lat) at (540, CY)) ──
CEN = (85.5, 37.8)
KX, CY = 12.0, 860.0
COS0 = math.cos(math.radians(CEN[1]))
ASIA = dict(lon0=30.0, lon1=138.0, lat0=0.0, lat1=72.0, w=2400)

# ── the layout (px): m8's ──
TITLE = ("هشت زمستان از فضا: تهران و پکن", "دی‌اکسیدِ نیتروژن کجا بیشتر است؟")
Y_TITLE = m8.Y_TITLE
WORD_PX, Y_WORD = m8.WORD_PX, m8.Y_WORD
WORD_LONG, WORD_SHORT = m8.WORD_LONG, m8.WORD_SHORT
SQ, SQ_Y = m8.SQ, m8.SQ_Y
SQ_X = dict(beijing=48, tehran=552)
NAME_PX = m8.NAME_PX
BAR_X, Y_BAR, BAR_H = m8.BAR_X, m8.Y_BAR, m8.BAR_H
TICK_PX, Y_BAR_NUM = m8.TICK_PX, m8.Y_BAR_NUM
Y_UNIT, UNIT_PX, PE_PX, COL, COL_C = m8.Y_UNIT, m8.UNIT_PX, m8.PE_PX, m8.COL, m8.COL_C
XR, Y_YEAR, Y_RATIO = m8.XR, m8.Y_YEAR, m8.Y_RATIO
STRIP_DX = 25                                     # px: keeps the strip's right label clear of the right-edge band
YEAR_PX, RATIO_PX, WORD_BIG_PX, LEFT_PX = m8.YEAR_PX, m8.RATIO_PX, m8.WORD_BIG_PX, m8.LEFT_PX
HMAX, Y_STRIP, BW, STEP, STRIP_X0 = m8.HMAX, m8.Y_STRIP, m8.BW, m8.STEP, m8.STRIP_X0
BJ_STRIP_X0, BJ_XR = STRIP_X0 - STRIP_DX, XR - STRIP_DX
Y_LAB, LAB_PX = m8.Y_LAB, m8.LAB_PX
Y_HEAD = m8.Y_HEAD
Y_SOURCES, SRC_PX = m8.Y_SOURCES, m8.SRC_PX
SOURCES = m8.SOURCES                                          # "(ESA)": the ESA/Copernicus form is 906 px at 40 px, over the 840 px limit
WORD_SHORT = f"میانگینِ هشت زمستان"                            # the close-ups' label (spelled out, as the headline)
LEFT_LABEL = f"نسبتِ تهران به پکن"


def smoothstep(x: float) -> float:
    return f8.smoothstep(x)


def _load_numbers() -> dict:
    """The per-winter ratios (beijing_v1.json) and the eight-winter ratio of means with its day-bootstrap interval
    (computed once from the day series by air_beijing and cached in RATIO_JSON)."""
    global SEED
    test = json.loads(BJ_TEST.read_text(encoding="utf-8"))
    per = {int(y): v for y, v in test["per_winter"].items()}
    R = {y: float(per[y]["R"]) for y in YEARS}
    if not RATIO_JSON.exists():
        RATIO_JSON.write_text(json.dumps(_ratio_of_means(), indent=1), encoding="utf-8")
    e = json.loads(RATIO_JSON.read_text(encoding="utf-8"))
    SEED = e["seed"]
    return dict(R=R, per=per, eight=float(e["ratio_of_means"]), ci=(float(e["ci90"][0]), float(e["ci90"][1])),
                tmean={int(y): v for y, v in e["tehran_means"].items()},
                bmean={int(y): v for y, v in e["beijing_means"].items()},
                n_t={int(y): v for y, v in e["days_T"].items()}, n_b={int(y): v for y, v in e["days_B"].items()})


def _ratio_of_means() -> dict:
    """The eight-winter ratio of means and its 90 % interval: days resampled with replacement within each city and winter
    (10,000 draws, air_beijing's seed), the ratio of the mean over the eight winters of the two resampled winter means."""
    import air_beijing as ab
    inv = ab.load_inventory()
    items = [r for r in inv["beijing"] if (ab.PIX_BEI / f"{r['id']}.npz").exists()]
    bdata = ab.build_city(ab.BEI, ab.PIX_BEI, items)
    B = ab.split_winters(ab.day_values(bdata))
    rep = ab.reproduce_tehran_core()
    T = {y: rep["winters"][y].pop("_values") for y in ab.WINTERS}
    tm = {y: float(np.mean(list(T[y].values()))) for y in YEARS}
    bm = {y: float(np.mean(list(B[y].values()))) for y in YEARS}
    ratio = float(np.mean(list(tm.values())) / np.mean(list(bm.values())))
    rng = np.random.default_rng(ab.SEED)
    bT = np.zeros((N_BOOT, len(YEARS)))
    bB = np.zeros((N_BOOT, len(YEARS)))
    for k, y in enumerate(YEARS):
        a, b = np.array(list(T[y].values())), np.array(list(B[y].values()))
        bT[:, k] = a[rng.integers(0, a.size, (N_BOOT, a.size))].mean(1)
        bB[:, k] = b[rng.integers(0, b.size, (N_BOOT, b.size))].mean(1)
    rb = bT.mean(1) / bB.mean(1)
    lo, hi = np.percentile(rb, [5, 95])
    return dict(tehran_means={str(y): tm[y] for y in YEARS}, beijing_means={str(y): bm[y] for y in YEARS},
                days_T={str(y): len(T[y]) for y in YEARS}, days_B={str(y): len(B[y]) for y in YEARS},
                ratio_of_means=ratio, ci90=[float(lo), float(hi)], boot_draws=N_BOOT, seed=int(ab.SEED),
                bootstrap="days resampled with replacement within each city and winter; ratio of the eight-winter means")


NUM = _load_numbers()
RATIOS = [NUM["R"][y] for y in YEARS]             # the bars: per-winter R = Tehran / Beijing (unrounded)
RAW = RATIOS                                      # the counter shows one decimal of each
MEAN = NUM["eight"]
LB = NUM["ci"][0]
HEAD_MORE = LB > 3.0                              # «بیش از ۳» only if the interval's lower bound exceeds 3
HEAD = ("در هر ۸ زمستان، در تهران بیشتر بود",   # «در تهران»: the quantity is higher in Tehran, not the city itself
        f"میانگین: {'بیش از' if HEAD_MORE else 'حدودِ'} {fa(3)} برابرِ پکن")
HEAD_PX = next(s for s in range(64, 55, -1) if max(oc.width(h, FA_BOLD, s) for h in HEAD) <= COL[1] - COL[0] - 4)
TITLE_PX = next(s for s in range(66, 59, -1) if max(oc.width(t, FA_BOLD, s) for t in TITLE) <= 940)


def intensity(raw):
    return m8.intensity(raw)


def _ss(x):
    return m8._ss(x)


class FilmBJ:
    """The Beijing and Tehran eight-winter film. Not a subclass of onebit_compare's Film: its base, close-ups and checks
    are this film's, and it reuses the layers of onebit_compare8m through its functions."""

    def __init__(self):
        self.checks()
        self.L = type("L", (), {"end": DURATION})()     # the length onebit.video reads
        self.base = self.make_map_base()
        self.fields = {"tehran": self.tehran_field(), "beijing": self.beijing_field()}
        self.tile = {c: self.make_tile(c) for c in CLOSE_ORDER}
        self.tg = {c: [self.make_tile_glow(c)] for c in CLOSE_ORDER}
        land = np.concatenate([self.tile[c]["base"][self.tile[c]["land"]] for c in CLOSE_ORDER])
        self.bar_base = np.median(land, axis=0).astype(np.float32)   # the one base of the bar (both squares)
        self.static = self.make_static()
        self.static_s2 = self.make_static_s2()

    # ── checks ──

    def checks(self) -> None:
        assert oc.VMIN == 2.0 and oc.VMAX == 100.0 and oc.GAMMA == 1.0
        f8r.check_clock()
        assert DURATION == 30.0 and 0 < S2[0] < S2[1] <= BAR_T0 + 0.8 + 1e-9 and S2[0] == BAR_T0
        assert len(BAR_TIMES) == 8 and abs(BAR_TIMES[0] - 4.5) < 1e-9 and abs(BAR_TIMES[-1] - 14.3) < 1e-9
        assert all(0 < r < 10 for r in RATIOS) and 0 < MEAN < 10
        assert HEAD_MORE == (LB > 3.0), "the headline rule"
        assert ("بیش از" in HEAD[1]) == (LB > 3.0) and ("حدودِ" in HEAD[1]) == (LB <= 3.0)
        assert fa(3) in HEAD[1] and "۷" not in HEAD[1]
        assert NUM["ci"][0] <= MEAN <= NUM["ci"][1], "the mean lies inside its interval"
        assert TITLE_PX >= 60 and max(oc.width(s, FA_BOLD, TITLE_PX) for s in TITLE) <= 940, "title line too wide"
        assert Y_TITLE[0] - 0.75 * TITLE_PX > 130, "title top below y 130"
        assert SQ >= 480 and SQ_X["beijing"] >= 40 and SQ_X["tehran"] + SQ <= 1040
        assert SQ_X["beijing"] + SQ + 16 < SQ_X["tehran"], "the squares do not touch"
        assert SQ_Y + SQ < 1000 and Y_WORD + 0.25 * WORD_PX < SQ_Y, "the label clears the close-ups"
        assert NAME_PX >= 56 and all(oc.width(n, FA_BOLD, NAME_PX) + 24 <= SQ - 28 for n in NAME.values())
        assert WORD_PX >= 40 and max(oc.width(WORD_LONG, FA_BOLD, WORD_PX), oc.width(WORD_SHORT, FA_BOLD, WORD_PX)) <= 900
        assert max(oc.width(s, FA_BOLD, HEAD_PX) for s in HEAD) <= COL[1] - COL[0] - 4, "headline too wide"
        assert HEAD_PX >= 56
        assert oc.width(LEFT_LABEL, FA_BOLD, LEFT_PX) < XR - COL[0] - 30 and LEFT_PX >= 40
        assert SRC_PX >= 40 and oc.width(SOURCES, FA_TEXT, SRC_PX) <= 840
        assert LAB_PX >= 40 and TICK_PX >= 40 and UNIT_PX >= 40 and PE_PX >= 28
        assert m8.HMAX == HMAX and HMAX == 208
        assert max(RATIOS) * HMAX / 10 < Y_STRIP - Y_HEAD[1]
        assert MEAN < 10 and HEAD[0] and "۷" not in HEAD[0]

    def schedule(self) -> dict:
        return dict(s2=S2, bar_times=BAR_TIMES, bar_rise=BAR_RISE, hold=T_HOLD, strip_fade=STRIP_FADE,
                    chips=dict(zip(CHIP_TEXT, CHIP_T)), chip_fade=CHIP_FADE, end=DURATION, stills=STILLS,
                    glow=(GLOW0, T_FULL), ratios=dict(zip(YEARS, RATIOS)), mean=MEAN, ci=NUM["ci"],
                    headline=HEAD, n5=(N5_START, N5_END))

    def glow_gain(self, t: float) -> float:
        return GLOW0 + (1.0 - GLOW0) * smoothstep(min(max(t, 0.0), T_FULL) / T_FULL)

    # ── the fields ──

    def tehran_field(self) -> dict:
        """winter8 of region8 (every 4th day), ascending in latitude, on its own grid."""
        z = np.load(REGION8)
        w8, lat = oc.ascending(z["winter8"].astype(np.float32), z["lat"], 0)
        return dict(arr=w8, lon=z["lon"], lat=lat)

    def beijing_field(self) -> dict:
        """The mean of the eight per-winter fields (beijing_YYYY_field), on the 100 x 100 grid of the close-up."""
        z = np.load(BJ_FIELDS)
        stack = np.stack([np.asarray(z[f"beijing_{y}_field"], np.float32) for y in YEARS])
        with np.errstate(all="ignore"):
            mean8 = np.nanmean(stack, axis=0)
        mean8 = np.nan_to_num(mean8, nan=0.0).astype(np.float32)
        lat = np.asarray(z["beijing_lat"], float)
        lon = np.asarray(z["beijing_lon"], float)
        assert lat[0] < lat[-1] and lon[0] < lon[-1], "the field's grid is ascending"
        return dict(arr=mean8, lon=lon, lat=lat)

    # ── the layers ──

    def make_map_base(self) -> np.ndarray:
        """The darkened Blue Marble of Asia on the frame (onebit_compare's base), the borders of Iran and China lighter."""
        import shapefile
        from onebit_compare import sample_bm, dim_base
        from air_grid import NE
        bm = np.asarray(Image.open(oc.fetch_bm(BM_ASIA, ASIA["lon0"], ASIA["lon1"], ASIA["lat0"], ASIA["lat1"],
                                              ASIA["w"])).convert("RGB"), np.float32)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
        lon = CEN[0] + (xx + 0.5 - 540.0) / KX
        lat = CEN[1] - (yy + 0.5 - CY) * COS0 / KX
        box = dict(lon0=ASIA["lon0"], lon1=ASIA["lon1"], lat0=ASIA["lat0"], lat1=ASIA["lat1"])
        rgb = sample_bm(bm, box, lon, lat)
        inside = (lon >= ASIA["lon0"]) & (lon <= ASIA["lon1"]) & (lat >= ASIA["lat0"]) & (lat <= ASIA["lat1"])
        base = dim_base(rgb)
        base[~inside] = np.asarray(DARK, np.float32)
        im = Image.fromarray(np.clip(base + 0.5, 0, 255).astype(np.uint8), "RGB")
        d = ImageDraw.Draw(im)
        r = shapefile.Reader(str(NE / "ne_10m_admin_0_countries.shp"))
        for sh, rec in zip(r.iterShapes(), r.iterRecords()):
            x0, y0, x1, y1 = sh.bbox
            if x1 < ASIA["lon0"] or x0 > ASIA["lon1"] or y1 < ASIA["lat0"] or y0 > ASIA["lat1"]:
                continue
            pts = np.asarray(sh.points, float)
            starts = list(sh.parts) + [len(pts)]
            own = rec["ADMIN"] in ("Iran", "China")
            for a, b in zip(starts[:-1], starts[1:]):
                q = pts[a:b]
                px = 540.0 + (q[:, 0] - CEN[0]) * KX
                py = CY - (q[:, 1] - CEN[1]) * KX / COS0
                d.line(list(zip(px.tolist(), py.tolist())), fill=(214, 220, 228) if own else (84, 92, 102),
                       width=2 if own else 1, joint="curve")
        return np.asarray(im, np.float32)

    def xy(self, lon: float, lat: float, s: float = 1.0):
        x = 540.0 + (lon - CEN[0]) * KX
        y = CY - (lat - CEN[1]) * KX / COS0
        return 540.0 + (x - 540.0) * s, CY + (y - CY) * s

    def make_tile(self, c: str) -> dict:
        """One close-up: the Blue Marble on the dark neutral base, the land share of each pixel, the coordinates."""
        from scipy import ndimage
        clon, clat = CITY[c]
        lon, lat = self.tile_lonlat(c)
        box = dict(lon0=clon - HALF_DEG - MARGIN, lon1=clon + HALF_DEG + MARGIN,
                   lat0=clat - HALF_DEG - MARGIN, lat1=clat + HALF_DEG + MARGIN)
        path = oc.fetch_bm(BJ_DIR / f"bluemarble_tile_{c}_bj_v1.jpg", box["lon0"], box["lon1"], box["lat0"], box["lat1"], 1000)
        tile = np.asarray(Image.open(path).convert("RGB"), np.float32)
        rgb = oc.sample_bm(tile, box, lon, lat)
        base = oc.dim_base(rgb)
        water = oc.water_mask(rgb, opening=False).astype(np.float32)
        wsoft = ndimage.gaussian_filter(water, 0.6)
        cov = np.clip(1.0 - wsoft, 0.0, 1.0).astype(np.float32)
        return dict(base=base, cov=cov, land=cov > 0.5, lon=lon, lat=lat)

    def tile_lonlat(self, c: str):
        clon, clat = CITY[c]
        yy, xx = np.mgrid[0:SQ, 0:SQ].astype(np.float64)
        lon = clon + (xx + 0.5 - SQ / 2) / SQ * 2 * HALF_DEG
        lat = clat - (yy + 0.5 - SQ / 2) / SQ * 2 * HALF_DEG
        return lon, lat

    def field_at(self, c: str, lon, lat) -> np.ndarray:
        f = self.fields["beijing" if c == "beijing" else "tehran"]
        return oc.sample_field(f["arr"], f["lon"], f["lat"], lon, lat)

    def make_tile_glow(self, c: str) -> np.ndarray:
        tl = self.tile[c]
        i = intensity(self.field_at(c, tl["lon"], tl["lat"]))
        return (oc.halo(i, oc.BLOOM_SIGMA) * tl["cov"]).astype(np.float32)

    def make_static(self) -> Image.Image:
        im = m8.layer()
        for s, y in zip(TITLE, Y_TITLE):
            oc.text(im, 540, y, s, FA_BOLD, TITLE_PX, stroke=5)
        oc.text(im, 505, Y_SOURCES, SOURCES, FA_TEXT, SRC_PX, stroke=3)
        return im

    def make_static_s2(self) -> Image.Image:
        """The colour bar with its ticks and the unit line: the key of the close-ups (from S2)."""
        im = m8.layer()
        d = ImageDraw.Draw(im)
        x0, x1 = BAR_X
        for xx in range(x0, x1 + 1):
            g = m8.GLOW_FLOOR + (xx - x0) / (x1 - x0) * (1.0 - m8.GLOW_FLOOR)
            col = np.clip(oc.paint(self.bar_base, np.full((1, 1), g, np.float32))[0, 0] + 0.5, 0, 255)
            d.line([(xx, Y_BAR), (xx, Y_BAR + BAR_H)], fill=tuple(int(q) for q in col) + (255,))
        d.rectangle([x0, Y_BAR, x1, Y_BAR + BAR_H], outline=oc.PAPER, width=2)
        for v in m8.TICK_VALUES:
            xt = m8.bar_x(v)
            d.line([(xt, Y_BAR + BAR_H), (xt, Y_BAR + BAR_H + 8)], fill=oc.PAPER, width=2)
            oc.text(im, xt, Y_BAR_NUM, fa(v), FA_TEXT, TICK_PX, stroke=3)
        oc.text(im, x0, Y_BAR_NUM, fa(int(oc.VMIN)), FA_TEXT, TICK_PX, stroke=3)
        oc.text(im, x1, Y_BAR_NUM, fa(int(oc.VMAX)), FA_TEXT, TICK_PX, stroke=3)
        oc.text(im, COL_C, Y_UNIT[0], m8.UNIT_L1, FA_TEXT, UNIT_PX, stroke=3)
        pe, gap = PE_PX, 10
        fa_, fe_ = oc.font(FA_TEXT, UNIT_PX), oc.font(FA_TEXT, pe)
        wA = fa_.getlength(m8.UNIT_A, direction="rtl", language="fa")
        wC = fa_.getlength(m8.UNIT_C, direction="rtl", language="fa")
        wE = fe_.getlength(m8.UNIT_E, direction="rtl", language="fa")
        total = wA + gap + wE + wC
        x_r = COL_C + total / 2 + 6
        oc.text(im, x_r - wA / 2, Y_UNIT[1], m8.UNIT_A, FA_TEXT, UNIT_PX, stroke=3)
        oc.text(im, x_r - wA - gap - wE / 2, Y_UNIT[1] - 0.45 * UNIT_PX, m8.UNIT_E, FA_TEXT, pe, stroke=2)
        oc.text(im, x_r - wA - gap - wE - wC / 2, Y_UNIT[1], m8.UNIT_C, FA_TEXT, UNIT_PX, stroke=3)
        return im

    def markers(self, a: float, s: float) -> Image.Image:
        """S1: the two cities marked, their names at 48 px, and a thin arc between them (north of the straight line)."""
        lay = m8.layer()
        d = ImageDraw.Draw(lay)
        p0 = np.array(self.xy(*CITY["tehran"], s=s))
        p1 = np.array(self.xy(*CITY["beijing"], s=s))
        mid = (p0 + p1) / 2
        dist = float(np.linalg.norm(p1 - p0))
        ctrl = mid + np.array([0.0, -0.30 * dist])
        pts = []
        for u in np.linspace(0.0, 1.0, 120):
            q = (1 - u) ** 2 * p0 + 2 * (1 - u) * u * ctrl + u ** 2 * p1
            pts.append((float(q[0]), float(q[1])))
        d.line(pts, fill=oc.PAPER[:3] + (190,), width=3, joint="curve")
        for c in CITY:
            x, y = self.xy(*CITY[c], s=s)
            d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=oc.PAPER, outline=oc.SHADOW, width=2)
            f = oc.font(FA_BOLD, 48)
            tw = f.getlength(NAME[c], direction="rtl", language="fa")
            if c == "tehran":
                lx, ly = x + 18, y - 90
            else:
                lx, ly = x - 18 - tw - 28, y - 90
            d.rounded_rectangle([lx, ly, lx + tw + 28, ly + 62], radius=12, fill=(8, 10, 14, 220))
            oc.text(lay, lx + tw / 2 + 14, ly + 48, NAME[c], FA_BOLD, 48, stroke=3)
        return f8.fade(lay, a)

    def closeups(self, t: float, e: float) -> Image.Image:
        lay = m8.layer()
        k = 0.72 + 0.28 * e
        n = round(SQ * k)
        d = ImageDraw.Draw(lay)
        for c in CLOSE_ORDER:
            gt = self.tg[c][0] * self.glow_gain(t)
            sq = oc.to_rgb(oc.paint(self.tile[c]["base"], gt)).convert("RGBA")
            if n != SQ:
                sq = sq.resize((n, n), Image.BILINEAR)
            x0 = round(SQ_X[c] + SQ / 2 - n / 2)
            y0 = round(SQ_Y + SQ / 2 - n / 2)
            lay.paste(sq, (x0, y0))
            d.rectangle([x0 - 1, y0 - 1, x0 + n, y0 + n], outline=oc.PAPER, width=2)
        for c in CLOSE_ORDER:
            lab = NAME[c]
            tw = oc.font(FA_BOLD, NAME_PX).getlength(lab, direction="rtl", language="fa")
            lx, ly = SQ_X[c] + 14, SQ_Y + 14
            d.rounded_rectangle([lx, ly, lx + tw + 24, ly + 76], radius=12, fill=(8, 10, 14, 220))
            oc.text(lay, lx + tw / 2 + 12, ly + 58, lab, FA_BOLD, NAME_PX, stroke=3)
        return f8.fade(lay, e)

    def strip_layer(self, t: float) -> Image.Image:
        lay = m8.layer()
        d = ImageDraw.Draw(lay)
        STRIP_X0, XR = BJ_STRIP_X0, BJ_XR              # the strip sits STRIP_DX px left of the counter's edge
        for k in range(8):
            tk = BAR_TIMES[k]
            if t < tk:
                continue
            a = smoothstep((t - tk) / BAR_RISE)
            x0 = STRIP_X0 + (7 - k) * STEP
            x1 = x0 + BW
            top = Y_STRIP - RATIOS[k] / 10 * HMAX * a
            d.rectangle([round(x0), round(top), round(x1) - 1, Y_STRIP], fill=oc.AMBER)
        d.line([(STRIP_X0 - 12, Y_STRIP), (XR, Y_STRIP)], fill=oc.PAPER[:3] + (150,), width=2)
        if t >= T_HOLD:
            y = Y_STRIP - MEAN / 10 * HMAX
            x = STRIP_X0 - 12
            while x < XR:
                d.line([(x, y), (min(x + 13, XR), y)], fill=oc.PAPER, width=2)
                x += 22
        oc.text(lay, XR - BW / 2, Y_LAB, fa(YEARS[0]), FA_TEXT, LAB_PX, stroke=3)
        oc.text(lay, STRIP_X0 + BW / 2, Y_LAB, fa(YEARS[-1]), FA_TEXT, LAB_PX, stroke=3)
        return lay

    def counter_layer(self, t: float) -> Image.Image:
        lay = m8.layer()
        oc.text(lay, COL[0] + oc.width(LEFT_LABEL, FA_BOLD, LEFT_PX) / 2, Y_YEAR, LEFT_LABEL, FA_BOLD, LEFT_PX, stroke=3)
        if t < BAR_T0:
            return lay
        k = max(i for i in range(8) if t >= BAR_TIMES[i])
        oc.text(lay, XR, Y_YEAR, f"زمستانِ {fa(YEARS[k])}", FA_BOLD, YEAR_PX, anchor="rs", stroke=3)
        word_w = oc.text(lay, XR, Y_RATIO, "برابر", FA_BOLD, WORD_BIG_PX, anchor="rs", stroke=3)
        m8.ratio_layer(lay, XR - word_w - 12, Y_RATIO, RAW[k])
        return lay

    def headline_layer(self) -> Image.Image:
        lay = m8.layer()
        for s, y in zip(HEAD, Y_HEAD):
            oc.text(lay, COL_C, y, s, FA_BOLD, HEAD_PX, fill=oc.AMBER, stroke=6)
        return lay

    def draw_frame(self, t: float) -> Image.Image:
        t = min(max(t, 0.0), DURATION)
        s = 1.0 + oc.ZOOM * t / DURATION
        e = smoothstep((t - S2[0]) / (S2[1] - S2[0]))
        base = self.base * (1.0 - e) + np.asarray(DARK, np.float32) * e
        full = np.clip(base + 0.5, 0, 255).astype(np.uint8)
        im = Image.fromarray(full, "RGB").transform(
            (W, H), Image.AFFINE, (1 / s, 0, 540 - 540 / s, 0, 1 / s, CY - CY / s), resample=Image.BILINEAR)
        im = im.convert("RGBA")
        if e < 1.0:
            im.alpha_composite(self.markers(1.0 - e, s))
        if e > 0.0:
            im.alpha_composite(self.closeups(t, e))
            im.alpha_composite(f8.fade(self.static_s2, e))
        if t >= BAR_T0:
            sf = e * (1.0 - smoothstep((t - STRIP_FADE[0]) / (STRIP_FADE[1] - STRIP_FADE[0])))
            if sf > 0.0:
                im.alpha_composite(f8.fade(self.strip_layer(t), sf))
        ca = e if t < T_HOLD else 1.0 - smoothstep((t - T_HOLD) / T_HOLD_FADE)
        if ca > 0.0 and (t >= S2[0] or e > 0.0):
            im.alpha_composite(f8.fade(self.counter_layer(t), ca))
        if t >= T_HOLD:
            im.alpha_composite(f8.fade(self.headline_layer(), smoothstep((t - T_HOLD) / T_HOLD_FADE)))
        for i, t0 in enumerate(CHIP_T):
            if t >= t0:
                im.alpha_composite(f8.fade(m8.Film8M.chip_layer(self, i), smoothstep((t - t0) / CHIP_FADE)))
        if t >= STRIP_FADE[1]:
            im.alpha_composite(f8.fade(m8.Film8M.hedge_layer(self), smoothstep((t - STRIP_FADE[1]) / CHIP_FADE)))
        im.alpha_composite(self.static)
        im.alpha_composite(word_layer(e))
        return im.convert("RGB")

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]) -> Image.Image:
        assert s == 1 and tuple(size) == (W, H), (s, size)
        return self.draw_frame(DURATION if not np.isfinite(t) else min(max(t, 0.0), DURATION))

    # ── the colour check ──

    def colour_check(self) -> bool:
        """Each close-up's land box (+-0.15 deg around the city centre) in the end frame, inverted pixel by pixel (each pixel's
        own base subtracted, the glow increment inverted through the composite, divided by the land share, then through the
        transfer). The land mean is compared with the mean of the field over the same land cells (values below 2 count as
        2, as they are drawn; cells with no data are left out). Tolerance 10 %."""
        frame = np.asarray(self.draw_frame(DURATION), np.float64)
        grid = np.linspace(0.0, 1.0, 401)
        inc = oc.paint(np.zeros(3), grid).astype(np.float64)
        ok_all = True
        glow_lum, rendered_mean = {}, {}
        half = 0.15
        for c in CLOSE_ORDER:
            tl = self.tile[c]
            lon, lat = tl["lon"], tl["lat"]
            hp = int(round(half / (2 * HALF_DEG) * SQ))           # px half side of the land box
            cy = cx = SQ // 2
            sub = (slice(cy - hp, cy + hp), slice(cx - hp, cx + hp))
            sl = (slice(SQ_Y + cy - hp, SQ_Y + cy + hp), slice(SQ_X[c] + cx - hp, SQ_X[c] + cx + hp))
            landm = tl["land"][sub]
            cov = np.maximum(tl["cov"][sub], 1e-6).astype(np.float64)
            base = tl["base"][sub].astype(np.float64)
            p = frame[sl]
            dv = (p - base).reshape(-1, 3)
            d2 = ((dv[:, None, :] - inc[None]) ** 2).sum(-1)
            g_hat = np.clip(grid[d2.argmin(1)].reshape(landm.shape) / cov, 0, 1)
            v_hat = invert(g_hat)
            rendered = float(v_hat[landm].mean())
            wf = self.field_at(c, lon[sub], lat[sub]).reshape(-1)
            sel = landm.reshape(-1) & (wf > 0)
            expected = float(np.clip(wf[sel], oc.VMIN, oc.VMAX).mean())
            dev = abs(rendered - expected) / expected
            good = dev <= oc.TOL
            ok_all &= bool(good)
            rendered_mean[c] = rendered
            glow_lum[c] = float(oc.luminance(p - base)[landm].mean())
            print(f"box {c}: rendered land mean {rendered:.2f}; field {expected:.2f} on {int(sel.sum())} land cells; "
                  f"deviation {100 * dev:.1f} % -> {'PASS' if good else 'FAIL'} ({100 * oc.TOL:.0f} % limit)", flush=True)
        ratio = glow_lum["tehran"] / glow_lum["beijing"]
        print(f"glow-only luminance tehran {glow_lum['tehran']:.2f}, beijing {glow_lum['beijing']:.2f}; ratio {ratio:.2f}",
              flush=True)
        if ratio <= 1.5:
            ok_all = False
        print("colour key:", "PASS" if ok_all else "FAIL", flush=True)
        return ok_all


def word_layer(e: float) -> Image.Image:
    """The label under the title: «میانگینِ هشت زمستان، ۱۳۹۷ تا ۱۴۰۴» (S1), then the close-ups' label (S2 on)."""
    long = m8.layer()
    oc.text(long, 540, Y_WORD, m8.WORD_LONG, FA_BOLD, WORD_PX, stroke=3)
    short = m8.layer()
    oc.text(short, 540, Y_WORD, WORD_SHORT, FA_BOLD, WORD_PX, stroke=3)
    return Image.alpha_composite(f8.fade(long, 1.0 - e), f8.fade(short, e))


def invert(g):
    return m8.invert(g)


def build() -> FilmBJ:
    return FilmBJ()



def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true", help="the stills at STILLS, no video")
    ap.add_argument("--check", action="store_true", help="the colour check of the close-ups")
    args = ap.parse_args()
    film = build()
    print("schedule", json.dumps(film.schedule(), ensure_ascii=False, default=str), flush=True)
    if args.check:
        sys.exit(0 if film.colour_check() else 1)
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / BASE
    if args.stills:
        for t in STILLS:
            p = f"{base}_t{t:04.1f}.png"
            film.draw(1, t).save(p)
            print("saved", p, flush=True)
        return
    film.draw(1, 0.0).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png", flush=True)
    import onebit
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
