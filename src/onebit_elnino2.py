"""EL NIÑO AND IRAN'S AUTUMN RAIN, SELF-DESCRIBING: the same data as onebit_elnino.py, told the way the five-dam reel
tells its story (one picture, one headline with its number, one bar of the scene's own counter).

Measured data only, no forecast. Every number comes from enso.py (outputs/enso_iran_log.txt, asserted below):
- Iran's rain: CRU TS 4.10 (University of East Anglia), 621 cells inside Iran, 1951-2024.
- El Niño seasons: NOAA CPC's Oceanic Niño Index (ONI) of the same season at least +0.5 °C. Autumn = October to
  December (Persian Mehr-Azar), winter = January to March (Dey-Esfand). Autumn: 21 of 26 El Niño autumns wetter than
  the 1951-2024 median (permutation p = 0.001); winter: 11 of 22 (p = 0.31). Strong El Niños (ONI at least +1.5):
  4 of 6 autumns and 2 of 6 winters wetter. Autumn brings 27 % of the year's rain, winter 46 %.
- Status: the first line of the caption (CPC's ENSO Diagnostic Discussion, the latest issue read on the day).

The map (scene 1): for each of the 621 cells, the mean rain of the 26 El Niño autumns as a percent of the cell's own
1951-2024 mean autumn rain (all 74 autumns; the mean, not the median, because rain is skewed and the mean of any 26
autumns already sits above the median: about 108 % over Iran for random years); smooth-upsampled for display and drawn over a darkened NASA Blue
Marble view of Iran (GIBS, the cached crop data/air/bluemarble_srb_iran.jpg, read only). Blue = wetter than usual,
brown = drier; 100 % = the 1951-2024 average autumn. Range 111-141 %.

Scenes (bars of 60 BPM, one beat = 1 s): S1 0-4.5 s the hook and the map; S2 [1/2] 4.5-11 s the 26 autumns, one
drop each, earliest first in reading order, solid = wetter, hollow = drier; S3 [2/2] 11-17.5 s the 22 winters;
S4 17.5-25.5 s the answer, the not-a-forecast line and the question.

    outputs/onebit/social/iran_elnino2_fa_reel.mp4 (silent master), _cover.png (frame 0), _t<sec>.png (stills)

    python -I src/onebit_elnino2.py              # the silent reel and the cover
    python -I src/onebit_elnino2.py --stills     # the cover and the stills of the iterations
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import warnings  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from scipy import ndimage  # noqa: E402

import enso  # noqa: E402
import onebit  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, PIXEL, SIZES, SOCIAL_CRF, TEXT, Canvas, fa, title, words_of  # noqa: E402
from onebit_slides import COLOURS, LEFT, RIGHT, WIN, Slides  # noqa: E402

DATA = onebit.ROOT / "data" / "enso" / "elnino2"
BASE = "iran_elnino2_fa"
AUTUMN, WINTER = "OND", "JFM"                     # enso.SEASONS: October-December, January-March
EXPECT = {AUTUMN: (21, 26), WINTER: (11, 22)}     # wetter of all El Niño seasons, and their number
SHARE = {AUTUMN: 27, WINTER: 46}                  # % of the year's rain (enso.py)
P_VALUE = {AUTUMN: 0.001, WINTER: 0.31}           # permutation p, two-sided (enso.py, to two decimals)
STRONG = {AUTUMN: (4, 6), WINTER: (2, 6)}         # ONI at least +1.5: wetter of those (enso.py checks)
PACE = dict(bpm=60, bars=(1.125, 1.625, 1.625, 2.0))   # 4.5, 6.5, 6.5, 8.0 s: 25.5 s
MAP_BOX = (43.0, 65.0, 24.0, 41.0)                # W, E, S, N of the Blue Marble crop (Iran with its margin)
MAP_H = 590                                       # px: the map's height; its width keeps Iran's true shape
MAP_Y = 770                                       # px: the map's top (the rule is at 664)
LO, HI = 90.0, 150.0                              # % of the usual autumn: the colour scale's ends (100 = usual);
                                                  # the cells run 111-141 %, so the brown end is kept for the legend only
DRY = (0x8C, 0x5A, 0x2B)                          # brown: drier than usual
MID = (0xF4, 0xEF, 0xE4)                          # the usual autumn
WET = (0x1C, 0x5C, 0xAB)                          # blue: wetter than usual (the water of the other reels)
PALE = (0xD8, 0xCD, 0xBB)                         # a drop not yet turned
BARH = 64                                         # px: the title bar (the type in it is 48 px)
RULE_Y = 664                                      # px: the rule under the headline
SOURCE_Y = 1584                                   # px: the sources' baseline, above 1600
DROP = ["....#....", "....#....", "...###...", "..#####..", ".#######.", ".#######.", ".#######.",
        "..#####..", "...###..."]                 # onebit_elnino's rain drop
CELL = 8                                          # px per drop pixel: a drop is 72 px
PER_ROW = {AUTUMN: 9, WINTER: 8}                  # reading order, right to left: 9+9+8 and 8+8+6
ROW_PITCH = 112                                   # px
DROP_TOP = 748                                    # px: centre of the first row of drops
WET_T0, WET_SPAN, COUNT_T = 1.0, 3.6, 5.0         # s into a scene: the first drop turns, the last ends, the counter


def words(res: dict) -> dict:
    a, w = res[AUTUMN], res[WINTER]
    na, nw = (a["n_wetter"], len(a["years"])), (w["n_wetter"], len(w["years"]))
    return dict(
        scenes=(("امسال ال‌نینو داریم // پاییزِ ال‌نینو پرباران‌تر بوده؟", "بارانِ ۲۶ پاییزِ ال‌نینو، به درصدِ میانگین"),
                (f"پاییز: {{{fa(na[0])} از {fa(na[1])}}} // ال‌نینو پرباران‌تر از معمول",
                 "اکتبر تا دسامبر؛ هر قطره یک پاییزِ ال‌نینو"),
                (f"زمستان: {{{fa(nw[0])} از {fa(nw[1])}}} // ال‌نینو پرباران‌تر از معمول",
                 "ژانویه تا مارس؛ مثلِ شیر یا خط"),
                ("پاییزهای ال‌نینو اغلب پرباران‌تر بوده‌اند؛ زمستان‌ها روشن نیست",
                 "این پیش‌بینی نیست؛")),
        question="شهرِ شما امسال // چطور بوده؟",
        note="درباره‌ی ال‌نینوهای ۱۹۵۱ تا ۲۰۲۴ است",
        sources="CRU TS 4.10 · NOAA ONI · Blue Marble",
        legend=("توپُر: بیش از معمولِ ۱۹۵۱–۲۰۲۴", "خالی: کم‌بارش‌تر از معمول"),
        scale=("۱۰۰٪", "۱۱۰٪", "۱۲۰٪", "۱۳۰٪", "۱۴۰٪", "۱۵۰٪"),
        unit="درصدِ میانگینِ پاییزها (۱۰۰٪ = میانگینِ ۱۹۵۱–۲۰۲۴)",
    )


# ── the data: the composite map and the drops, read from enso.py and asserted ─────────────

def composite() -> dict:
    """Per cell (the 621 CRU cells of Iran, NaN elsewhere): the mean rain of the El Niño autumns as a percent of the
    cell's 1951-2024 mean autumn (all 74 autumns). Cached in data/enso/elnino2/ (new files only)."""
    cache = DATA / "composite_ond_mean.npz"
    if cache.exists():
        d = np.load(cache)
        return dict(pct=d["pct"], lat=d["lat"], lon=d["lon"], years=[int(y) for y in d["years"]])
    _, cells = enso.iran_rain()
    warnings.filterwarnings("ignore", "All-NaN slice|Mean of empty slice")   # cells outside Iran are NaN
    assert int(np.isfinite(cells.isel(time=0).values).sum()) == 621
    yrs = list(range(enso.YEARS[0], enso.YEARS[1] + 1))
    ond = np.stack([cells.sel(time=slice(f"{y}-10-01", f"{y}-12-31")).sum("time", skipna=False).values for y in yrs])
    el = enso.result(AUTUMN)["years"]
    comp = 100 * np.nanmean(ond[[yrs.index(y) for y in el]], axis=0) / np.nanmean(ond, axis=0)
    ok = np.isfinite(comp)
    assert ok.sum() == 621 and 110 < comp[ok].min() < 112 and 140 < comp[ok].max() < 142, (comp[ok].min(), comp[ok].max())
    lat, lon = cells.lat.values, cells.lon.values
    DATA.mkdir(parents=True, exist_ok=True)
    np.savez(cache, pct=comp, lat=lat, lon=lon, years=np.array(el))
    return dict(pct=comp, lat=lat, lon=lon, years=el)


def colour_of(pct: np.ndarray) -> np.ndarray:
    """A diverging colour per value: brown below 100 %, the cream of the usual at 100 %, blue above; clipped at LO, HI."""
    p = np.asarray(pct, float)
    dry, wet, mid = np.array(DRY, float), np.array(WET, float), np.array(MID, float)
    f_dry = np.clip((100 - p) / (100 - LO), 0, 1)[..., None]
    f_wet = np.clip((p - 100) / (HI - 100), 0, 1)[..., None]
    out = np.where((p < 100)[..., None], mid + (dry - mid) * f_dry, mid + (wet - mid) * f_wet)
    return out


class ElNino2Film(Slides):
    def __init__(self, th: onebit.Theme, colour: dict):
        self.res = {s: enso.result(s) for s in (AUTUMN, WINTER)}
        self.check_data()
        self.setup(th, "fa", colour, words(self.res), PACE, "ElNino.Iran")
        self.hook_at_once = True
        self.th = th
        self.comp = composite()
        self.map_w, self.map_h = self.geometry()
        self.map = self.make_map()
        self.sprites = {k: self.sprite(k) for k in ("pale", "wet", "dry")}
        self.check_layout()

    # ── checks: every number on screen is asserted here ──

    def check_data(self) -> None:
        for s, r in self.res.items():
            got = (r["n_wetter"], len(r["years"]))
            assert got == EXPECT[s], f"{s}: the data now give {got}, the published numbers {EXPECT[s]}"
            assert round(r["p"], 3) == P_VALUE[s] or (s == WINTER and round(r["p"], 2) == P_VALUE[s]), (s, r["p"])
            strong = enso.result(s, 1.5)
            assert (strong["n_wetter"], len(strong["years"])) == STRONG[s], (s, strong["n_wetter"])
        assert enso.THRESHOLD == 0.5, "the sources line says ONI at least +0.5 C"
        annual = enso.iran_rain()[0].loc["1951":"2024"]
        annual = annual.groupby(annual.index.year).sum().mean()
        for s, r in self.res.items():
            assert round(100 * r["mean"] / annual) == SHARE[s], (s, 100 * r["mean"] / annual)
        assert [k for k in self.res[AUTUMN]["years"]] == sorted(self.res[AUTUMN]["years"])

    def check_layout(self) -> None:
        for s in (AUTUMN, WINTER):
            n = len(self.res[s]["years"])
            rows = math.ceil(n / PER_ROW[s])
            assert DROP_TOP + ROW_PITCH * (rows - 1) + CELL * len(DROP) / 2 < 1200, s
        assert RULE_Y + 30 < DROP_TOP - CELL * len(DROP) / 2 + 20
        assert self.map_h == MAP_H and MAP_Y + MAP_H < 1380, "the map runs into the colour bar"

    def geometry(self) -> tuple:
        """The map's width at Iran's true shape: longitude at the cosine of the mid latitude."""
        w, e, s, n = MAP_BOX
        km_w = (e - w) * math.cos(math.radians((s + n) / 2))
        return round(MAP_H * km_w / (n - s)), MAP_H

    # ── the map ──

    def make_map(self) -> Image.Image:
        """The darkened Blue Marble crop, the composite over Iran (its 621 cells, bilinear), Iran's outline."""
        w_, e_, s_, n_ = MAP_BOX
        W, H = self.map_w, self.map_h
        bm = onebit.ROOT / "data" / "air" / "bluemarble_srb_iran.jpg"
        assert bm.exists(), f"{bm}: the cached Blue Marble tile (onebit_air ensure_bluemarble)"
        step, lon0, lat0 = 0.005, 42.0, 45.5
        box = (round((w_ - lon0) / step), round((lat0 - n_) / step), round((e_ - lon0) / step), round((lat0 - s_) / step))
        base = Image.open(bm).convert("RGB").crop(box).resize((W, H), Image.LANCZOS)
        base = np.asarray(base, float) * 0.42                       # darkened: the colour carries the map
        lon_d = w_ + (np.arange(W) + 0.5) / W * (e_ - w_)
        lat_d = n_ - (np.arange(H) + 0.5) / H * (n_ - s_)
        LON, LAT = np.meshgrid(lon_d, lat_d)
        pct = self.comp["pct"]
        idx = ndimage.distance_transform_edt(np.isnan(pct), return_distances=False, return_indices=True)
        filled = pct[tuple(idx)]                                     # nearest cell where NaN (outside Iran)
        lat_c, lon_c = self.comp["lat"], self.comp["lon"]
        dlat, dlon = lat_c[1] - lat_c[0], lon_c[1] - lon_c[0]
        iy = (lat_c[0] - LAT) / dlat if dlat < 0 else (LAT - lat_c[0]) / dlat
        ix = (LON - lon_c[0]) / dlon
        up = ndimage.map_coordinates(filled, [iy, ix], order=1, mode="nearest")
        mask = enso.iran_mask(LAT, LON)
        edge = mask & ~ndimage.binary_erosion(mask, iterations=1)
        rgb = colour_of(up)
        out = base.copy()
        out[mask] = 0.12 * base[mask] + 0.88 * rgb[mask]
        outline = ndimage.binary_dilation(edge, iterations=2)
        out[outline] = np.array(MID, float)
        return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8))

    # ── sprites: a drop pale (not turned), solid blue (wetter), hollow brown (drier) ──

    def sprite(self, kind: str) -> Image.Image:
        on = np.array([[ch == "#" for ch in row] for row in DROP])
        edge = on & ~ndimage.binary_erosion(on, iterations=1, border_value=0)
        if kind == "pale":
            m, col = on, PALE
        elif kind == "wet":
            m, col = on, WET
        else:
            m, col = edge, DRY
        big = np.kron(m, np.ones((CELL, CELL), bool))
        rgba = np.zeros(big.shape + (4,), np.uint8)
        rgba[..., :3] = col
        rgba[..., 3] = big * 255
        return Image.fromarray(rgba, "RGBA")

    # ── time ──

    def turn(self, season: str, k: int) -> float:
        """s into the scene at which drop k of the season turns (the first at 1.0 s, the last at 4.6 s)."""
        n = len(self.res[season]["years"])
        return WET_T0 + k * WET_SPAN / n

    # ── drawing ──

    def appear(self, i: int) -> list:
        """As in Slides, but after the hook a line break is only a break: the whole headline comes in over 1.6 s, so its
        number and the key line under it are read together (the key line follows 0.6 s after the last word)."""
        if i == 0:
            return super().appear(i)
        ws = [w for w, _ in words_of(self.S.scenes[i].title, self.th)]
        n = len(ws) - ws.count("//")
        return [0.3 + 1.6 * k / n for k in range(n)]

    def window(self, c: Canvas, i: int):
        th = self.th
        x, y, w, h = WIN
        c.frame(x, y, x + w, y + h, fill=th.paper)
        c.fill(x, y, x + w, y + BARH, th.ink)
        c.frame(x + 3, y + BARH + 3, x + w - 3, y + h - 3)
        c.text(x + 14, y + BARH - 14, self.app, PIXEL, 48, th.title)
        if i in (1, 2):
            c.text(x + w - 14, y + BARH - 14, f"[{i}/2]", PIXEL, 48, th.title, "rs")
        c.fill(x + 3, RULE_Y, x + w - 3, RULE_Y + 2, th.ink)

    def sources(self, c: Canvas):
        s = self.words["sources"]
        assert c.width(s, TEXT, 40) <= RIGHT - LEFT, s
        c.text(RIGHT, SOURCE_Y, s, TEXT, 40, self.th.head, "rs")

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]):
        """The Slides frame, with the headline below the title bar (BARH) and above the rule (RULE_Y)."""
        c = Canvas(s, self.th, 1.0, (0.0, 0.0), size)
        c.pixels(0, 0, self.dots, self.th.dots)
        i = self.scene(t)
        dt = t - self.starts[i] if np.isfinite(t) else np.inf
        self.window(c, i)
        self.progress(c, t)
        at = self.appear(i)
        title(c, self.th, self.S.scenes[i], dt, self.lang, 1.0, LEFT, RIGHT, WIN[1] + BARH + 96, at,
              sizes=((68, 92), (64, 86)), motion=False, line_at=at[-1] + 0.6, small=48)
        self.body(c, t)
        self.sources(c)
        return c.im

    def body(self, c: Canvas, t: float):
        i = self.scene(t)
        if i == 0:
            self.map_scene(c)
        elif i in (1, 2):
            self.drops(c, t, i)
        else:
            self.answer(c, t)

    def map_scene(self, c: Canvas):
        th = self.th
        x0 = (1080 - self.map_w) // 2
        c.im.paste(self.map, (x0, MAP_Y))
        c.frame(x0 - 1, MAP_Y - 1, x0 + self.map_w + 1, MAP_Y + self.map_h + 1, colour=th.ink)
        # the colour bar: 90 % to 150 %, one tick per label, under the map
        bx0, bx1, by = LEFT + 40, RIGHT - 40, 1392
        n = 200
        for k in range(n):
            pct = LO + (HI - LO) * (k + 0.5) / n
            rgb = colour_of(np.array([pct]))[0].astype(int)
            c.fill(bx0 + (bx1 - bx0) * k / n, by, bx0 + (bx1 - bx0) * (k + 1) / n, by + 30,
                   "#%02x%02x%02x" % tuple(rgb))
        c.frame(bx0, by, bx1, by + 30, colour=th.ink)
        ticks = (100, 110, 120, 130, 140, 150)
        for v, lab in zip(ticks, self.words["scale"]):
            xv = bx0 + (v - LO) / (HI - LO) * (bx1 - bx0)
            c.fill(xv - 1, by + 30, xv + 1, by + 40, th.ink)
            c.text(xv, by + 78, lab, FA_TEXT, 40, th.ink, "ms", "rtl")
        c.text(540, 1530, self.words["unit"], FA_TEXT, 40, th.ink, "ms", "rtl")
        assert c.width(self.words["unit"], FA_TEXT, 40, "rtl") <= RIGHT - LEFT

    def drops(self, c: Canvas, t: float, i: int):
        th = self.th
        season = AUTUMN if i == 1 else WINTER
        r = self.res[season]
        flags = [bool(r["wetter"][y]) for y in r["years"]]
        n = len(flags)
        dt = t - self.starts[i] if np.isfinite(t) else np.inf
        per = PER_ROW[season]
        pitch = (RIGHT - LEFT) / per
        for k, wet in enumerate(flags):
            row, col = divmod(k, per)
            cx = RIGHT - pitch / 2 - col * pitch
            cy = DROP_TOP + row * ROW_PITCH
            turned = np.isfinite(dt) and dt >= self.turn(season, k)
            kind = ("wet" if wet else "dry") if turned else "pale"
            sp = self.sprites[kind]
            c.im.paste(sp, (c.X(cx - CELL * len(DROP) / 2), c.Y(cy - CELL * len(DROP) / 2)), sp)
        if np.isfinite(dt) and dt >= COUNT_T:
            c.text(540, 1196, f"{fa(sum(flags))} از {fa(n)}", FA_BOLD, 120, th.ink, "ms", "rtl")
        else:
            c.text(540, 1196, f"{fa(sum(flags))} از {fa(n)}", FA_BOLD, 120, th.paper, "ms", "rtl")
        ly = 1282
        for k, (kind, lab) in enumerate((("wet", self.words["legend"][0]), ("dry", self.words["legend"][1]))):
            y = ly + k * 66
            sp = self.sprites[kind]
            c.im.paste(sp.resize((40, 40), Image.NEAREST), (c.X(RIGHT - 40), c.Y(y - 34)),
                       sp.resize((40, 40), Image.NEAREST))
            c.text(RIGHT - 60, y, lab, FA_TEXT, 48, th.ink, "rs", "rtl")

    def answer(self, c: Canvas, t: float):
        th = self.th
        a, w = self.res[AUTUMN], self.res[WINTER]
        if t - self.starts[3] >= self.appear(3)[-1] + 0.6:       # with the small line it continues, never before it
            c.text(RIGHT, 602, self.words["note"], FA_TEXT, 48, th.ink, "rs", "rtl")
        assert c.width(self.words["note"], FA_TEXT, 48, "rtl") <= RIGHT - LEFT
        c.text(540, 860, f"پاییز: {fa(a['n_wetter'])} از {fa(len(a['years']))}", FA_BOLD, 96, th.ink, "ms", "rtl")
        c.text(540, 1000, f"زمستان: {fa(w['n_wetter'])} از {fa(len(w['years']))}", FA_BOLD, 96, th.ink, "ms", "rtl")
        c.frame(LEFT + 60, 1160, RIGHT - 60, 1380, colour=th.ink)
        for k, line in enumerate(self.words["question"].split(" // ")):
            c.text(540, 1248 + 88 * k, line, FA_BOLD, 72, th.ink, "ms", "rtl")
            assert c.width(line, FA_BOLD, 72, "rtl") <= RIGHT - LEFT - 120, line


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="kahgel", choices=["kahgel"], help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and stills only, no video")
    args = ap.parse_args()
    film = ElNino2Film(onebit.THEMES[args.theme], COLOURS[args.theme])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / BASE
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        for t in (0.0, 3.0, 8.0, 14.0, 20.0, 25.0):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
