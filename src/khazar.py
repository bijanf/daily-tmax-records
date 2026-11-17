"""«آبِ خزر کجا رفت؟» (khazar_fa): the falling Caspian Sea, its shallow north-east from space, and the claim that the
Volga "has been shut". The satellite picture is the whole frame; one part, no narration; two cuts that differ only in
the hook's first line (a: the claim with the country's name, as a question; b: no country). This file is the film's
data: it writes outputs/onebit/khazar/film.json (every string, number, the clock, the colours) and the pictures the
page draws; src/khazar_page/ draws any moment from it and src/onebit_khazar.py steps it frame by frame.

The owner (17 Nov 2026): a reel on the Caspian, especially its north; he remembers the sea RISING in his childhood and
taking homes on the coast of Mazandaran; people say the rivers were closed; perhaps there is less water because of
climate change. What the measurements say (fact checks of 17 Nov 2026, four agents, the numbers recomputed from the raw
files):

  the river   CASPCOM's catalogue of runoff (the joint hydrometeorological committee of the five coastal states), the
              Volga at Verkhneye Lebyazhye, the head of the delta, below every dam, 1938-2024: 237.5 km3 a year on
              average (84 complete years); 267.7 in 1978-1995; 209.6 in 2021-2024 (12 % below the average). Not shut;
              less. The cascade's hydropower dams began working between 1937 and 1980.
  the sea     CASPCOM's catalogue of levels: the four reference gauges rose 2.43 m from 1977 to 1995 (Anzali 2.40 m);
              by 2024 Makhachkala and Anzali were back within 15 cm of 1977. NASA altimetry agrees on the fall
              (1995-2024: 2.43 m against Makhachkala's 2.37 m) and gives the newest years.
  the north   NASA's daily pictures (MODIS on Terra to 2019, VIIRS on NOAA-20 from 2020), the median of each late
              summer's twelve clearest days; open water = dark in the near and the shortwave infrared. In the
              rectangle of Court et al. 2025 (45.27-47.12 N, 52.05-53.43 E) the open-water AREA of 2022 and of 2026
              is measured against 2001's (the paper: 0.605 for 2022, 0.54 for 2024): about half. On single days of
              one late summer it ranges over about 0.35-0.65 (wind on a flat shelf, and the fall from August to
              September), so no yearly area runs on screen: the running number is the sea's level.
  the causes  Chen et al. 2017 (more evaporation over the sea, dominant) against Duku et al. 2026 (less inflow, mainly
              the Volga): both on screen, the shares left open.

    python -I src/get_khazar.py --caspcom && python -I src/get_khazar.py --probe && python -I src/get_khazar.py
    python -I src/khazar.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))

import get_khazar as gk  # noqa: E402
from onebit import fa  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = gk.OUT
BUILD = ROOT / "outputs" / "onebit" / "khazar"
ALT = ROOT / "data" / "gorgan" / "caspian_nasa270.txt"      # NASA altimetry, lake 270 (EGM2008): changes only
FPS, W, H = 30, 1080, 1920
FIRST, LAST = 2001, 2026
NIR = 55                                                     # of 255: open water is darker than this in the near and the shortwave infrared
COURT = dict(box=(52.05, 45.27, 53.43, 47.12), km2={2001: 15194, 2022: 9197, 2024: 8183}, shore_km=56.17)   # Court et al. 2025, doi 10.1038/s43247-025-02212-5
GOLD = (246, 196, 69)
REF = ("BAKU", "MAKH", "FORT", "KRASN")                      # the four reference gauges (Baltic system, post datum -28.0 m)
# the cascade's hydropower dams on the Volga and the Kama: the year the first unit ran (Russian Wikipedia's table
# «Волжско-Камский каскад ГЭС», read 17 Nov 2026; coordinates from each station's page). Sheksna (1965, 84 MW, on a
# tributary) is the table's twelfth station and is left out.
DAMS = [("Ivankovo", 37.12, 56.735, 1937), ("Uglich", 38.298, 57.528, 1940), ("Rybinsk", 38.825, 58.082, 1941),
        ("Kama", 56.329, 58.115, 1954), ("Nizhny Novgorod", 43.376, 56.651, 1955), ("Zhiguli", 49.479, 53.426, 1955),
        ("Volga (Volgograd)", 44.677, 48.824, 1958), ("Votkinsk", 54.084, 56.792, 1961), ("Saratov", 47.762, 52.048, 1967),
        ("Nizhnekamsk", 52.279, 55.700, 1979), ("Cheboksary", 47.466, 56.137, 1980)]


def persian(year: int) -> int:
    return year - 621                                        # a late summer, or most of a calendar year, of year Y is Persian Y - 621


# ---------------------------------------------------------------- the numbers

def altimetry() -> pd.DataFrame:
    rows = []
    for line in ALT.read_text().splitlines():
        p = line.split()
        if len(p) > 15 and len(p[2]) == 8 and p[2].isdigit():
            try:
                rows.append((int(p[2][:4]), int(p[2][4:6]), float(p[-2])))
            except ValueError:
                pass
    a = pd.DataFrame(rows, columns=["y", "m", "h"])
    return a[(a.h > -40) & (a.h < -20)]                      # the file's fill value is 9999.99


def numbers() -> dict:
    c = DATA / "caspcom"
    v = pd.read_csv(c / "flow_volga.csv", index_col=0)
    flow = v.sum12.dropna()                                  # km3 a year: the sum of twelve monthly volumes, complete years
    mean = float(flow.mean())
    late = float(flow.loc[2021:2024].mean())
    rise_years = float(flow.loc[1978:1995].mean())
    lev = pd.read_csv(c / "level_annual_cm.csv", index_col=0)
    four = lev[list(REF)]
    m4 = four.mean(axis=1).where(four.notna().all(axis=1))
    mk, an = lev["MAKH"].dropna(), lev["ANZALI"].dropna()
    sef = pd.read_csv(c / "flow_sefidrud.csv", index_col=0).sum12.dropna()
    s0, s1 = float(sef.loc[1981:1995].mean()), float(sef.loc[2006:2019].mean())
    alt = altimetry()
    mon = alt.groupby(["y", "m"]).h.mean()
    ann = mon.groupby("y").agg(["mean", "count"])
    ann = ann[ann["count"] >= 11]["mean"]                    # years with at least eleven months
    last_full = int(ann.index.max())
    cur = mon.loc[LAST]
    same = [m for m in cur.index if m in mon.loc[last_full].index]
    step = float((cur[same] - mon.loc[last_full][same]).mean())      # the newest year against the year before, the same months
    level = {int(y): float(ann[y] - ann[FIRST]) for y in range(FIRST, last_full + 1)}      # m against 2001
    if LAST not in level:
        level[LAST] = level[last_full] + step
    n = dict(volga_mean=mean, volga_years=int(len(flow)), volga_first=int(flow.index.min()), volga_last=int(flow.index.max()),
             volga_late=late, volga_rise=rise_years, volga_ratio=late / mean, volga_ratio_rise=late / rise_years,
             volga_late_years=[float(flow[y]) for y in range(2021, 2025)],
             rise_four=float((m4[1995] - m4[1977]) / 100), rise_makh=float((mk[1995] - mk[1977]) / 100), rise_anzali=float((an[1995] - an[1977]) / 100),
             fall_makh_2024=float((mk[1995] - mk[2024]) / 100), fall_anzali_2024=float((an[1995] - an[2024]) / 100),
             back_makh=float((mk[2024] - mk[1977]) / 100), back_anzali=float((an[2024] - an[1977]) / 100),
             alt_fall_2024=float(ann[1995] - ann[2024]), alt_fall_last_full=float(ann[1995] - ann[last_full]), alt_last_full=last_full, alt_step=step,
             level=level, sefid=[s0, s1, 1 - s1 / s0])
    print(json.dumps({k: (round(x, 3) if isinstance(x, float) else x) for k, x in n.items() if k != "level"}, indent=1))
    print("level against 2001 (m):", {y: round(x, 2) for y, x in level.items()})
    # the statements on screen and in the caption
    assert n["volga_years"] == 84 and (n["volga_first"], n["volga_last"]) == (1938, 2024), n       # «میانگینِ ۸۴ سال»، «۱۳۱۷ تا ۱۴۰۳»
    assert 0.875 < n["volga_ratio"] < 0.885, n               # «۱۲٪ کمتر» than the 84-year average
    assert 0.77 < n["volga_ratio_rise"] < 0.80, n            # 78 % of 1978-1995 (caption)
    assert 1.10 < rise_years / mean < 1.16, n                # «ولگا پرآب»: 1978-1995 carried about 13 % more than the 84-year average
    assert 2.40 <= n["rise_makh"] <= 2.60, n                 # «حدودِ ۲ متر و نیم»: Makhachkala, the gauge the card's line shows
    assert all(200 < x < 215 for x in n["volga_late_years"]), n     # four low years, each still above 200 km3: not shut
    assert 2.35 < n["rise_four"] < 2.50 and 2.35 < n["rise_anzali"] < 2.45, n     # the four-gauge mean and Anzali (caption, first comment)
    assert abs(n["back_makh"]) < 0.2 and abs(n["back_anzali"]) < 0.2, n           # «تا ۱۴۰۳: برگشت به حدودِ سطحِ ۱۳۵۶»
    assert abs(n["alt_fall_2024"] - n["fall_makh_2024"]) < 0.12, n                # the altimetry and the gauge agree on the fall
    assert -2.25 < level[LAST] < -1.85, level[LAST]          # «حدودِ ۲ متر»
    assert 0.70 < n["sefid"][2] < 0.74, n                    # «۷۲٪ کمتر»
    assert min(d[3] for d in DAMS) == 1937 and max(d[3] for d in DAMS) == 1980 and len(DAMS) == 11     # «۱۳۱۶ تا ۱۳۵۹»
    chart = dict(years=[int(y) for y in range(1938, 2025)],
                 flow=[(round(float(flow[y]), 1) if y in flow.index else None) for y in range(1938, 2025)],
                 level=[(round(float(mk[y]), 1) if y in mk.index else None) for y in range(1938, 2025)],      # Makhachkala, cm above -28.0 m
                 mean=round(mean, 1), rise=[1978, 1995], late=[2021, 2024], low=1977, high=1995)
    return dict(n=n, chart=chart)


# ---------------------------------------------------------------- the pictures of the north-east

def grid(name: str, shape: tuple) -> tuple:
    """The latitude of each row, the longitude of each column, and each cell's ground area (km2) on a frame's picture."""
    w, s, e, n_ = gk.FRAMES[name]["box"]
    hh, ww = shape
    step = (gk.mx(e) - gk.mx(w)) / ww
    lat = np.degrees(2 * np.arctan(np.exp((gk.my(n_) - (np.arange(hh) + 0.5) * step) / gk.R)) - math.pi / 2)
    lon = w + (np.arange(ww) + 0.5) * (e - w) / ww
    return lat, lon, ((step * np.cos(np.radians(lat))) ** 2 / 1e6)[:, None] * np.ones((1, ww)), step


def water(year: int, t: int = NIR) -> np.ndarray:
    a = np.asarray(Image.open(DATA / f"ne_{year}_ir.jpg").convert("RGB")).astype(np.int16)
    return (a[..., 1] < t) & (a[..., 0] < t)


def measure() -> dict:
    """Open water per late summer in Court et al.'s rectangle, and how far the bed exposed since 2001 lies from the water."""
    first = water(FIRST)
    lat, lon, km2, step = grid("ne", first.shape)
    LAT, LON = lat[:, None] * np.ones((1, len(lon))), lon[None, :] * np.ones((len(lat), 1))
    w_, s_, e_, n_ = COURT["box"]
    box = (LAT >= s_) & (LAT <= n_) & (LON >= w_) & (LON <= e_)
    rows = []
    for y in range(FIRST, LAST + 1):
        rows.append(dict(year=y, box_km2=float(km2[water(y) & box].sum()), box_lo=float(km2[water(y, 30) & box].sum()),
                         box_hi=float(km2[water(y, 80) & box].sum()), frame_km2=float(km2[water(y)].sum())))
    df = pd.DataFrame(rows).set_index("year")
    df["ratio"] = df.box_km2 / df.box_km2[FIRST]
    df.round(3).to_csv(DATA / "areas.csv")
    def body(wm: np.ndarray) -> np.ndarray:                     # the sea itself: the largest body of water (the Kaydak inlet of 2001 is a body of its own)
        lab, k = ndimage.label(wm)
        return lab == 1 + int(np.argmax(ndimage.sum(wm, lab, range(1, k + 1))))
    sea = body(water(LAST))
    lost = body(first) & ~sea
    dist = ndimage.distance_transform_edt(~sea) * (step / 1000.0) * np.cos(np.radians(lat))[:, None]      # km on the ground
    d = dist[lost]
    out = dict(rect_km2=float(km2[box].sum()), ratio={int(y): float(r) for y, r in df.ratio.items()},
               ratio_lo=float(df.box_lo[LAST] / df.box_lo[FIRST]), ratio_hi=float(df.box_hi[LAST] / df.box_hi[FIRST]),
               far_max=float(d.max()), far_p99=float(np.percentile(d, 99)), far_p95=float(np.percentile(d, 95)),
               lost_frame=float(km2[lost].sum()))
    print("the rectangle:", round(out["rect_km2"]), "km2 (the paper: 21,901); open water against 2001:",
          {y: round(out["ratio"][y], 3) for y in (2005, 2010, 2015, 2020, 2022, 2023, 2024, 2025, 2026)},
          "| the paper: 2022", round(COURT["km2"][2022] / COURT["km2"][2001], 3), "2024", round(COURT["km2"][2024] / COURT["km2"][2001], 3))
    print(f"the bed exposed since {FIRST}: {out['lost_frame']:.0f} km2 in the frame; its distance from today's water: "
          f"95 % within {out['far_p95']:.0f} km, 99 % within {out['far_p99']:.0f} km, the farthest {out['far_max']:.0f} km")
    assert abs(out["rect_km2"] - 21901) < 60, out["rect_km2"]                          # the same rectangle as the paper's
    assert abs(out["ratio"][2022] - COURT["km2"][2022] / COURT["km2"][2001]) < 0.05, out["ratio"][2022]       # the paper's own year, within 0.05
    recent = [out["ratio"][y] for y in (2023, 2025, 2026)]
    assert all(0.45 < r < 0.60 for r in recent) and 0.45 < out["ratio_lo"] < 0.60 and 0.45 < out["ratio_hi"] < 0.60, (recent, out)   # «نیمی»
    assert out["far_p99"] > 50 and out["far_max"] > COURT["shore_km"] and out["far_p95"] < 50, out     # «جاهایی بیش از ۵۰ کیلومتر»: in places, not everywhere
    return out


def ne_pictures() -> dict:
    BUILD.mkdir(parents=True, exist_ok=True)
    box = gk.FRAMES["ne"]["box"]
    for y in range(FIRST, LAST + 1):
        im = Image.open(DATA / f"ne_{y}_tc.jpg").convert("RGB")
        assert im.size == gk.FRAMES["ne"]["px"], im.size
        im.resize((W, H), Image.LANCZOS).save(BUILD / f"p{y}.jpg", quality=91)
    # the shore of 2001: the edge of that summer's water (pieces smaller than 60 km2 left out), as a gold line
    first = water(FIRST)
    lat, lon, km2, step = grid("ne", first.shape)
    lab, k = ndimage.label(first)
    size = ndimage.sum(km2 * first, lab, range(1, k + 1))
    big = np.isin(lab, 1 + np.where(size > 300)[0])            # the sea and the Kaydak inlet; reed-fringed ponds and islets left out
    big = ndimage.binary_fill_holes(ndimage.binary_closing(big, iterations=6))
    big = ndimage.binary_opening(big, iterations=5)
    edge = ndimage.binary_dilation(big, iterations=4) & ~ndimage.binary_erosion(big, iterations=1)
    edge[:12, :] = edge[-12:, :] = False                      # the frame's own border is not a shore
    edge[:, :12] = edge[:, -12:] = False
    a = Image.fromarray((edge * 255).astype(np.uint8)).resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.9))
    line = Image.new("RGBA", (W, H), GOLD + (0,))
    line.putalpha(a.point(lambda v: min(255, int(v * 1.8))))
    line.save(BUILD / "shore.png")
    return dict(box=list(box), years=list(range(FIRST, LAST + 1)), shore="shore.png")


def cover(im: Image.Image, size: tuple = (W, H)) -> Image.Image:
    assert abs(im.width / im.height - size[0] / size[1]) < 0.002, im.size
    return im.resize(size, Image.LANCZOS)


def other_pictures() -> dict:
    cover(Image.open(DATA / "wide.jpg").convert("RGB")).save(BUILD / "wide.jpg", quality=92)
    cover(Image.open(DATA / f"south_{LAST}_tc.jpg").convert("RGB")).save(BUILD / "south.jpg", quality=92)
    # the locator: the whole sea in the last summer, Iran's border on it, the film's frame as a gold box (drawn by the page)
    sea = Image.open(DATA / f"sea_{LAST}_tc.jpg").convert("RGB")
    loc = sea.resize((390, 693), Image.LANCZOS)
    w, s, e, n_ = gk.FRAMES["sea"]["box"]
    px = lambda lon, lat: (390 * (lon - w) / (e - w), 693 * (gk.my(n_) - gk.my(lat)) / (gk.my(n_) - gk.my(s)))   # noqa: E731
    d = ImageDraw.Draw(loc)
    lines = json.loads((DATA / "lines.json").read_text())
    pts = [px(x, y) for x, y in lines["iran"]]
    d.line(pts, fill=(255, 255, 255), width=3)
    loc.save(BUILD / "locator.jpg", quality=92)
    b = gk.FRAMES["ne"]["box"]
    x0, y0 = px(b[0], b[3])
    x1, y1 = px(b[2], b[1])
    return dict(wide=dict(file="wide.jpg", box=list(gk.FRAMES["wide"]["box"])), south=dict(file="south.jpg", box=list(gk.FRAMES["south"]["box"])),
                locator=dict(file="locator.jpg", frame=[x0 / 390, max(0.012, y0 / 693), x1 / 390, y1 / 693],      # the film's frame reaches a little north of this picture
                             iran=[px(53.2, 35.9)[0] / 390, px(53.2, 35.9)[1] / 693]))


def rivers() -> dict:
    """The Volga from its source to the delta and the Kama down to the Volga, as single lines; the borders inside the map."""
    L = json.loads((DATA / "lines.json").read_text())
    near = lambda p, q: math.hypot(p[0] - q[0], p[1] - q[1]) < 0.05      # noqa: E731
    parts = L["rivers"]["volga"]
    head = next(p for p in parts if abs(p[0][0] - 32.6) < 0.2 or abs(p[-1][0] - 32.6) < 0.2)
    line = list(head) if abs(head[0][0] - 32.6) < 0.2 else list(head[::-1])
    left = [p for p in parts if p is not head]
    while True:
        nxt = next((p for p in left if near(p[0], line[-1]) or near(p[-1], line[-1])), None)
        if nxt is None:
            break
        left.remove(nxt)
        line += (nxt if near(nxt[0], line[-1]) else nxt[::-1])[1:]
    assert line[0][1] > 57 and line[-1][1] < 46 and len(left) <= 1, (line[0], line[-1], len(left))     # source to delta; only a delta branch is left
    kama = max(L["rivers"]["kama"], key=len)
    kama = kama if kama[0][1] > kama[-1][1] else kama[::-1]             # downstream: north to the Volga
    kama = [p for p in kama if p[1] < 59.2]
    thin = lambda pts, step: [p for i, p in enumerate(pts) if i % step == 0] + [pts[-1]]      # noqa: E731
    km = lambda a, b: math.hypot((a[0] - b[0]) * 111.32 * math.cos(math.radians(a[1])), (a[1] - b[1]) * 111.32)   # noqa: E731
    for name, lon, lat, _ in DAMS:                                       # every dam lies on one of the two lines
        dmin = min(min(km((lon, lat), p) for p in line), min(km((lon, lat), p) for p in kama))
        assert dmin < 25, (name, round(dmin, 1))
    w, s, e, n_ = gk.FRAMES["wide"]["box"]
    borders = [b for b in L["borders"] if any(w < x < e and s < y < n_ for x, y in b)]
    return dict(volga=thin(line, 2), kama=thin(kama, 2), borders=borders, iran=L["iran"])


# ---------------------------------------------------------------- the clock, the words, the reading rule

def clock_of() -> dict:
    a = (0.0, 7.4)                                   # the north-east: now, back to 2001 by 1.7 s, forward again by 3.7 s; the ruler
    b = (a[1], a[1] + 7.4)                           # every late summer 2001-2026, the level running; the rectangle
    c = (b[1], b[1] + 7.0)                           # the Volga on the map; its dams in the order they were built
    e = (c[1], c[1] + 6.8)                           # the river's 84 years
    f = (e[1], e[1] + 8.0)                           # Iran's coast: the rise of 1356-1374
    g = (f[1], f[1] + 6.8)                           # why it falls
    h = (g[1], g[1] + 5.0)                           # the north-east again: the question
    out = (h[1], h[1] + 0.8)
    run0 = b[0] + 0.9
    step = 0.165
    years = [round(run0 + i * step, 3) for i in range(LAST - FIRST + 1)]
    pins0 = c[0] + 2.6
    return dict(a=a, b=b, c=c, e=e, f=f, g=g, h=h, out=out, end=round(out[1], 3), cover=0.0,
                a_back=(0.5, 1.7), a_fwd=(2.5, 3.7), ruler=3.9, locator=(0.0, a[1] - 0.3),
                rect=b[0] + 0.4, years=years, river=(c[0] + 0.4, c[0] + 2.4), chip_c=c[0] + 1.0,
                pins=[round(pins0 + i * 0.25, 3) for i in range(len(DAMS))],
                card=(e[0] + 0.3, f[1] - 0.2), bars=(e[0] + 0.6, e[0] + 2.8), late=e[0] + 3.2,
                line=(f[0] + 0.9, f[0] + 3.2), small_f=f[0] + 1.4,
                small_g=g[0] + 1.4, vapour=g[0] + 0.6, follow=h[0] + 1.2)


def reading(Wd: dict, C: dict) -> None:
    """The owner's reading rule (src/onebit_reading.py) on every scene, asserted: a scene lasts at least 1 s plus its
    words at 2.5 a second (headline, small line and sentences in full, labels at half) and 3 s after its last string."""
    import onebit_reading as rd
    wt = lambda xs: sum(rd.weight(x) for x in xs)    # noqa: E731
    plan = [("hook", C["a"], [max((Wd["hook_a"], Wd["hook_b"]), key=rd.weight)], [Wd["tag_now"], Wd["tag_then"], Wd["shore"], Wd["ruler"], Wd["loc_iran"]], C["ruler"]),
            ("run", C["b"], [Wd["head_b"]], [Wd["unit_b"], Wd["rect"], "۱۴۰۵", "۲٫۱"], C["rect"]),
            ("volga", C["c"], [Wd["head_c"]], [Wd["chip_c"], Wd["russia"], Wd["kazakhstan"], Wd["sea"], "۱۳۵۹"], C["chip_c"]),
            ("flow", C["e"], [Wd["head_e"]], [Wd["leg_up"], Wd["leg_down"], Wd["leg_unit"], Wd["leg_mean"], Wd["late"], Wd["tick0"]], C["late"]),
            ("rise", C["f"], [Wd["head_f"], Wd["small_f"]], [Wd["leg_line"], Wd["gilan"], Wd["mazandaran"], Wd["y_low"], Wd["y_high"]], C["small_f"]),   # the colour key was read in the scene before
            ("why", C["g"], [Wd["head_g"], Wd["small_g"]], [Wd["vapour"]], C["small_g"]),
            ("close", C["h"], [Wd["head_h"], Wd["follow"]], [], C["follow"])]
    print("\nreading (seconds the rule needs, seconds given):")
    short, total = [], 0.0
    for name, (a, b), full, half, last in plan:
        w = wt(full) + rd.LABELS * wt(half)
        total += w
        need = max(rd.SETTLE + w / rd.WPS, last - a + rd.HOLD)
        print(f"  {name:6s} {wt(full):4.1f} + {wt(half):4.1f}/2 words -> {need:4.1f} s needed, {b - a:4.1f} s given")
        if b - a + 0.051 < need:
            short.append((name, round(need, 2), round(b - a, 2)))
    print(f"  weighted words in the film: {total:.0f}")
    assert not short, short


def words_of(n: dict, m: dict) -> dict:
    late = n["volga_late"]
    less = round(100 * (1 - n["volga_ratio"]))
    lev = abs(n["level"][LAST])
    return dict(
        hook_a="روسیه جلوی آبِ خزر را گرفته؟ // ساحل، جاهایی {بیش از ۵۰ کیلومتر} عقب‌تر",      # the owner's decision; not rendered without his yes
        hook_b="آبِ خزر کجا رفت؟ // ساحل، جاهایی {بیش از ۵۰ کیلومتر} عقب‌تر",
        tag_now=f"تابستانِ {fa(persian(LAST))}", tag_then=f"تابستانِ {fa(persian(FIRST))}",
        shore=f"ساحلِ {fa(persian(FIRST))}", ruler="۵۰ کیلومتر", loc_iran="ایران",
        head_b=f"{{{fa(round(lev))} متر}} افتِ سطحِ دریا: // {{حدودِ نیمی}} از پهنه‌ی آبیِ این کادر رفت",
        unit_b=f"سطحِ دریا نسبت به {fa(persian(FIRST))}", metre="متر", rect="این کادر",
        head_c=f"می‌گویند ولگا را بسته‌اند. // آخرین سدِ بزرگش: {{{fa(persian(2026) - persian(1980))} سال پیش}}",
        chip_c="ولگا: حدودِ ۸۰٪ // آبِ رودهای خزر", russia="روسیه", kazakhstan="قزاقستان", sea="دریای خزر",
        head_e=f"آبِ ولگا قطع نشده؛ // {{{fa(less)}٪ کمتر}} از میانگینِ {fa(n['volga_years'])} سال",
        leg_up="بالای میانگین", leg_down="زیرِ میانگین", leg_unit="کیلومترمکعب در سال", leg_mean=f"میانگین: {fa(round(n['volga_mean']))}",
        late=f"{fa(persian(2021))} تا {fa(persian(2024))}: {fa(round(late))}", tick0=fa(persian(1938)), tick1=fa(persian(2024)),
        head_f=f"{fa(persian(1977))} تا {fa(persian(1995))}: ولگا پرآب، // دریا {{حدودِ ۲ متر و نیم}} بالاتر",
        small_f="خانه‌های ساحلی آسیبِ شدید دیدند",
        leg_line="سطحِ دریا", y_low=fa(persian(1977)), y_high=fa(persian(1995)),
        gilan="گیلان", mazandaran="مازندران",
        head_g="چرا پایین می‌رود؟ // {آبِ رودها کمتر، تبخیر بیشتر}", small_g="سهمِ هر کدام هنوز بحث دارد",
        vapour="تبخیر",
        head_h="بالا آمدنِ دریا را // {یادتان هست؟}", follow="برای یک شمالی بفرستید",
        src_a="تصویر: MODIS و VIIRS، ناسا // عقب‌نشینی: Court و همکاران ۲۰۲۵؛ سنجش روی همین تصویرها",
        src_b="سطحِ دریا: ارتفاع‌سنجیِ ماهواره‌ای، ناسا // پهنه‌ی آب: سنجش روی همین تصویرها؛ Court و همکاران ۲۰۲۵",
        src_c="سدها: ۱۱ نیروگاهِ آبیِ ولگا و کاما؛ نقشه: Blue Marble، ناسا",
        src_e=f"داده: کمیته‌ی آب‌وهواشناسیِ پنج کشورِ خزر (CASPCOM) // ایستگاه: سرِ دلتا، پایین‌تر از همه‌ی سدها؛ {fa(persian(1938))} تا {fa(persian(2024))}",
        src_f="سطحِ دریا: ایستگاهِ ماخاچ‌قلعه، CASPCOM // آسیب: Kakroodi و همکاران ۲۰۱۵",
        src_g="Chen و همکاران ۲۰۱۷؛ Duku و همکاران ۲۰۲۶ // Court و همکاران ۲۰۲۵",
        src_h="منابع در کامنتِ اول",
    )


def main() -> None:
    num = numbers()
    n = num["n"]
    m = measure()
    ne = ne_pictures()
    oth = other_pictures()
    riv = rivers()
    words = words_of(n, m)
    clock = clock_of()
    reading(words, clock)
    lev = n["level"]
    run = [dict(year=y, label=fa(persian(y)), pic=f"p{y}.jpg",
                level=("−" if lev[y] < -0.05 else "+" if lev[y] > 0.05 else "") + fa(f"{abs(lev[y]):.1f}")) for y in range(FIRST, LAST + 1)]
    b = gk.FRAMES["ne"]["box"]
    km_lon = 111.32 * math.cos(math.radians(45.42))                     # the ruler lies along 45.42 N, on the bed of the emptied bay
    ruler = [[52.28, 45.42], [52.28 + 50.0 / km_lon, 45.42]]
    film = dict(fps=FPS, size=[W, H], clock=clock, end=clock["end"], cover_t=clock["cover"], numbers=n, measure=m, words=words,
                ne=ne, run=run, wide=oth["wide"], south=oth["south"], locator=oth["locator"], rivers=riv, chart=num["chart"],
                dams=[dict(lon=d[1], lat=d[2], year=d[3], label=fa(persian(d[3])), at="left" if d[0].startswith("Volga") else "above")
                      for d in sorted(DAMS, key=lambda d: d[3])],
                rect=list(COURT["box"]), ruler=ruler,
                places=dict(shore=(53.55, 46.05), russia=(42.0, 54.2), kazakhstan=(53.6, 48.2), sea_wide=(51.0, 46.6),
                            chip_c=(49.3, 50.3), gilan=(49.5, 37.1), mazandaran=(52.6, 36.78), vapour=(49.75, 38.42)),
                colours=dict(gold="#F6C445", ink="#1d140c", paper="#FBF7F0", river="#49c0ff", wet="#1c5cab", dry="#B5763A", pin="#FF8A1F"))
    assert abs(b[3] - 48.78) < 0.01
    (BUILD / "film.json").write_text(json.dumps(film, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", BUILD / "film.json", "| end", clock["end"])


if __name__ == "__main__":
    main()
