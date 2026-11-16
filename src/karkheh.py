"""«سدِ کرخه پر شد؟» (karkheh_fa): an answer to a post of 15 Nov 2026 that said the Karkheh dam "filled", and the side
such posts leave out. The satellite picture is the whole frame; one part, no narration. A sibling of karun (same
engine, same look). This file is the film's data: it writes outputs/onebit/karkheh/film.json (every string, number,
the clock, the colours) and the pictures the page draws; src/karkheh_page/ draws any moment from it and
src/onebit_karkheh.py steps it frame by frame.

The owner (16 Nov 2026): the post does not show downstream: the marsh, the land across the border, the dust that comes
back to Khuzestan; Iran asks Afghanistan for the Hamoun's water right and is itself upstream on the Karkheh. He wants
a SOFT, scientific critique: numbers and sourced statements, no blame words, no accused person or body.

The scenes (the payoff stands in frame 0: the first 3 s are the skip window):
  a  the lake on 19 Aban 1405 inside the shoreline of the full lake (May 2019), wiped back to 19 Aban 1404 (the post's
     own comparison) and forward again; the official volume
  c  the river from the dam down to the marsh; the marsh's water right
  b  the marsh in spring 1404, both sides of the border
  d  two days of May 2022 from space: a wall of dust in Iraq at the border, then haze over Khuzestan
  e  the Hamoun in the same spring 1404: the mirror
  f  the lake again: the question

Numbers on screen are this film's own measurements (get_karkheh.py: lake.csv) or official figures named in the source
line, asserted here. Fact checks of 16 Nov 2026: research/feasibility/feas_karkheh/README.md.

    python -I src/get_karkheh.py && python -I src/get_karkheh.py --series
    python -I src/karkheh.py
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

import get_karkheh as gkh  # noqa: E402
import get_karun as gk  # noqa: E402
from onebit import fa  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "outputs" / "onebit" / "karkheh"
HOOR = ROOT / "outputs" / "onebit" / "hoor"            # the Hoor film's build: its picture of spring 1404
HAMOUN = ROOT / "outputs" / "onebit" / "hamounenso"    # the Hamoun film's build: its picture of spring 1404
ZOOM = ROOT / "data" / "karun" / "zoom"                # the regional mosaic (EOX), for the corner locator
FPS, W, H = 30, 1080, 1920
NOW, LAST, FULL = gkh.DAYS
GOLD = (246, 196, 69)
OFFICIAL_FILL = 40                                    # % «پرشدگی» with the data to 10 Aban 1405 (Iran Water Resources Company; Tasnim through Entekhab 946979, 17 Aban 1405; read on the page)
IRAQ_SIDE, IRAN_SIDE = 20, 260                        # km2 of open water in spring 1404 (the Hoor film's measurement, hoor.py)
DUST_SHARE = 69                                       # 68.8 %: Iraq's share of the dust ENTERING Khuzestan from the neighbouring countries, 2003-2017 (Dargahian et al. 2024, read on the page)


def tone(rgb: np.ndarray) -> np.ndarray:
    """Reflectance (rows, columns, 3) to a picture: one fixed stretch for both years."""
    return (np.clip(np.nan_to_num(rgb, nan=0.0) / 0.34, 0, 1) ** (1 / 1.55) * 255).astype(np.uint8)


def cover(im: Image.Image, area: tuple) -> tuple:
    """A picture of a lon/lat box scaled to fill the frame and cut to it about its centre: the picture and the box it then shows."""
    w, s, e, n = area
    k = max(W / im.width, H / im.height)
    big = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    x0, y0 = (big.width - W) // 2, (big.height - H) // 2
    fx, fy = (e - w) / big.width, (n - s) / big.height
    return big.crop((x0, y0, x0 + W, y0 + H)), [w + x0 * fx, n - (y0 + H) * fy, w + (x0 + W) * fx, n - y0 * fy]


def numbers() -> dict:
    d = pd.read_csv(gkh.OUT / "lake.csv")
    day = lambda s: d[d.date == s].iloc[0]            # noqa: E731
    now, last = day(NOW), day(LAST)
    full = d[d.label == "full 2019"]
    assert now.zone_clear >= 0.98 and last.zone_clear >= 0.98 and (full.zone_clear >= 0.98).all(), "a headline day is not clear"
    nov = d[d.label.str.startswith("Nov")].copy()
    nov["year"] = nov.label.str[4:].astype(int)
    best = nov.sort_values(["year", "zone_clear"]).groupby("year").tail(1).set_index("year")   # the clearer pass of each November
    larger = [int(y) for y in best.index if y != 2026 and best.km2[y] > 1.05 * now.km2]        # clearly larger (more than 5 %)
    same = [int(y) for y in best.index if y != 2026 and abs(best.km2[y] / now.km2 - 1) <= 0.05]  # about the same
    aut = d[(d.date >= "2026-10-16") & (d.date <= NOW) & (d.zone_clear >= 0.98)]
    n = dict(now=float(now.km2), last=float(last.km2), full=float(full.km2.max()), full_loose=float(full.km2_loose.max()),
             nov={int(y): float(v) for y, v in best.km2.items()}, nov_clear={int(y): float(v) for y, v in best.zone_clear.items()},
             larger=larger, same=same, nov2024=float(best.km2[2024]), autumn=[float(aut.km2.min()), float(aut.km2.max())],
             sept=float(d[d.date == "2026-09-21"].km2.iloc[0]))
    print(json.dumps({k: (round(v, 1) if isinstance(v, float) else v) for k, v in n.items()}, indent=1))
    # the statements on screen and in the caption
    assert 1.45 < n["now"] / n["last"] < 1.8, n                           # "larger than a year ago" (about 60 %)
    assert 0.48 < n["now"] / n["full"] < 0.60, n                          # "about half of the full lake" (by area)
    assert 150 < n["full"] < 170 and n["full_loose"] < 170, n             # the nominal area at normal level is 162 km2
    assert larger == [2017, 2018, 2019] and same == [2020, 2024], (larger, same)   # of the nine earlier Novembers: three larger, two about the same (first comment)
    assert abs(n["nov2024"] / n["now"] - 1) < 0.05, n                     # two years ago about the same (caption)
    assert n["autumn"][1] - n["autumn"][0] < 3.0 and n["sept"] > n["now"], n   # no rise this autumn (caption)
    return n


def lake_pictures() -> dict:
    BUILD.mkdir(parents=True, exist_ok=True)
    w, s, e, n = gkh.FRAME
    ratio = (e - w) * 111.32 * math.cos(math.radians((s + n) / 2)) / ((n - s) * 111.32)
    assert abs(ratio - W / H) < 0.002, ratio                             # the frame is 9:16 on the ground
    z = {d: np.load(gkh.OUT / f"frame_{d}.npz") for d in gkh.DAYS}
    for name, d in (("p_now.jpg", NOW), ("p_last.jpg", LAST)):
        rgb = z[d]["rgb"]
        assert np.isfinite(rgb).all(axis=2).mean() > 0.999, (d, "holes in the picture")
        Image.fromarray(tone(rgb)).resize((W, H), Image.LANCZOS).save(BUILD / name, quality=93)
    near = gk.masks("kframe")["near"]
    lab, k = ndimage.label(z[FULL]["loose"] & near)
    big = ndimage.binary_fill_holes(lab == 1 + int(np.argmax(ndimage.sum(z[FULL]["loose"] & near, lab, range(1, k + 1)))))
    edge = ndimage.binary_dilation(big, iterations=3) & ~ndimage.binary_erosion(big, iterations=1)
    a = Image.fromarray((edge * 255).astype(np.uint8)).resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.8))
    line = Image.new("RGBA", (W, H), GOLD + (0,))
    line.putalpha(a.point(lambda v: min(255, int(v * 1.7))))
    line.save(BUILD / "shore.png")
    print(f"the full lake's outline: {big.sum() * (gk.M / 1000) ** 2:.0f} km2 inside it on the frame")
    return dict(box=list(gkh.FRAME), now="p_now.jpg", last="p_last.jpg", shore="shore.png")


def card() -> dict:
    im = Image.open(gkh.OUT / "card.jpg").convert("RGB")
    assert im.size == tuple(gkh.CARD_PX)
    im.resize((W, H), Image.LANCZOS).save(BUILD / "card.jpg", quality=92)
    line = json.loads((gkh.OUT / "river.json").read_text())
    keep, last = [line[0]], line[0]
    for p in line[1:]:                                # one point about every 400 m is enough for the line on the map
        if math.hypot((p[0] - last[0]) * 94.5, (p[1] - last[1]) * 111.32) >= 0.4:
            keep.append(p)
            last = p
    keep.append(line[-1])
    return dict(file="card.jpg", box=list(gkh.CARD_BOX), river=keep, border=json.loads((gkh.OUT / "border.json").read_text()))


def marsh() -> dict:
    f = json.loads((HOOR / "film.json").read_text())
    assert f["side_year"] == 2025, f["side_year"]                         # spring 1404
    row = pd.read_csv(ROOT / "data" / "hoor" / "springs.csv").set_index("year").loc[2025]      # the Hoor film's own table
    assert round(row.water_iraq / 10) * 10 == IRAQ_SIDE and round(row.water_iran / 10) * 10 == IRAN_SIDE, (row.water_iraq, row.water_iran)
    im, area = cover(Image.open(HOOR / "p2025.jpg").convert("RGB"), f["grid"]["box"])
    im.save(BUILD / "p_marsh.jpg", quality=93)
    return dict(file="p_marsh.jpg", box=area, border=f["border"])


def dust() -> dict:
    out = []
    for (sat, d), name in zip(gkh.DUST, ("p_dust_a.jpg", "p_dust_b.jpg")):
        Image.open(gkh.OUT / f"dust_{d}.jpg").convert("RGB").save(BUILD / name, quality=93)
        out.append(name)
    return dict(a=out[0], b=out[1], box=list(gkh.DUST_BOX), border=gkh.border(gkh.DUST_BOX))


def hamoun() -> dict:
    f = json.loads((HAMOUN / "film.json").read_text())
    g = f["grid"]
    area = [g["lon0"], g["lat1"] - g["dlat"] * g["h"], g["lon0"] + g["dlon"] * g["w"], g["lat1"]]
    im, shown = cover(Image.open(HAMOUN / "p2025.jpg").convert("RGB"), area)   # spring 1404
    im.save(BUILD / "p_hamoun.jpg", quality=93)
    w, s, e, n = shown
    line = [p for p in f["lines"]["ia"] if w - 0.2 < p[0] < e + 0.2 and s - 0.2 < p[1] < n + 0.2]   # the Iran-Afghanistan border
    return dict(file="p_hamoun.jpg", box=shown, border=[line])


def locator() -> dict:
    """The corner locator: Iran on the regional mosaic, its outline, a gold dot on the dam (drawn by the page)."""
    import shapefile
    from shapely.geometry import shape
    lv = json.loads((ZOOM / "levels.json").read_text())["r"]
    (bw, bs, be, bn), (pw, ph) = lv["box"], lv["size"]
    px = lambda lon, lat: ((lon - bw) / (be - bw) * pw, (bn - lat) / (bn - bs) * ph)   # noqa: E731
    cx, cy = px(53.6, 32.4)
    half = 660                                       # pixels of the mosaic: about 2,000 km across
    crop = (round(cx - half), round(cy - half), round(cx + half), round(cy + half))
    im = Image.open(ZOOM / "r.jpg").convert("RGB").crop(crop).resize((600, 600), Image.LANCZOS)
    k = 600 / (2 * half)
    d = ImageDraw.Draw(im)
    r = shapefile.Reader(str(gkh.NE))
    fields = [f[0] for f in r.fields[1:]]
    for s in r.iterShapeRecords():
        if dict(zip(fields, s.record))["ADM0_A3"] == "IRN":
            g = shape(s.shape.__geo_interface__)
            for poly in getattr(g, "geoms", [g]):
                d.line([((px(x, y)[0] - crop[0]) * k, (px(x, y)[1] - crop[1]) * k) for x, y in poly.exterior.coords], fill=(255, 255, 255), width=4)
    im.resize((300, 300), Image.LANCZOS).save(BUILD / "locator.jpg", quality=92)
    q = px(*gkh.DAM)
    dot = [(q[0] - crop[0]) * k / 600, (q[1] - crop[1]) * k / 600]
    assert 0.1 < dot[0] < 0.9 and 0.1 < dot[1] < 0.9, dot
    return dict(file="locator.jpg", dot=dot)


def clock_of() -> dict:
    a = (0.0, 7.4)                                   # the lake: now, back to a year ago by 1.7 s, forward again by 3.7 s
    c = (a[1], a[1] + 7.0)                           # the map: down the river to the marsh
    b = (c[1], c[1] + 5.6)                           # the marsh, both sides
    d = (b[1], b[1] + 7.2)                           # the dust: two days
    e = (d[1], d[1] + 5.6)                           # the Hamoun: the mirror
    f = (e[1], e[1] + 5.0)                           # the lake again: the question
    out = (f[1], f[1] + 0.8)
    return dict(a=a, c=c, b=b, d=d, e=e, f=f, out=out, end=round(out[1], 3), cover=0.0,
                a_back=(0.5, 1.7), a_fwd=(2.5, 3.7), small_a=3.9, locator=(0.0, 4.6),
                small_c=c[0] + 1.6, d_wipe=(d[0] + 1.4, d[0] + 2.6), small_d=d[0] + 1.0, follow=f[0] + 1.6)


def reading(Wd: dict, C: dict) -> None:
    """The owner's reading rule (src/onebit_reading.py) on every scene, asserted."""
    import onebit_reading as rd
    wt = lambda xs: sum(rd.weight(x) for x in xs)    # noqa: E731
    plan = [("lake", C["a"], [Wd["hook"], Wd["small_a"]], [Wd["day_now"], "۸۶", Wd["unit"], Wd["day_last"], "۵۳", Wd["full"]], C["small_a"]),
            ("map", C["c"], [Wd["head_c"], Wd["small_c"]], [Wd["dam"], Wd["marsh"], Wd["iran"], Wd["iraq"]], C["small_c"]),
            ("marsh", C["b"], [Wd["head_b"]], [Wd["spring"], Wd["iran_b"], Wd["iraq_b"]], C["b"][0] + 0.3),
            ("dust", C["d"], [Wd["head_d"], Wd["small_d"]], [Wd["day_d1"], Wd["day_d2"], Wd["iraq"], Wd["khuz"]], C["d_wipe"][1]),
            ("hamoun", C["e"], [Wd["head_e"]], [Wd["tag_e"], Wd["iran"], Wd["afg"]], C["e"][0] + 0.3),
            ("close", C["f"], [Wd["head_f"], Wd["follow"]], [], C["follow"])]
    print("\nreading (seconds the rule needs, seconds given):")
    short = []
    for name, (a, b), full, half, last in plan:
        w = wt(full) + rd.LABELS * wt(half)
        need = max(rd.SETTLE + w / rd.WPS, last - a + rd.HOLD)
        print(f"  {name:6s} {wt(full):4.1f} + {wt(half):4.1f}/2 words -> {need:4.1f} s needed, {b - a:4.1f} s given")
        if b - a + 0.051 < need:
            short.append((name, round(need, 2), round(b - a, 2)))
    assert not short, short


def main() -> None:
    n = numbers()
    lake = lake_pictures()
    words = dict(
        hook="سدِ {کرخه} پر شد؟ // {حدودِ نصفِ} دریاچه‌ی پُر", small_a=f"پُرشدگیِ مخزن (حجم): {fa(OFFICIAL_FILL)}٪",
        day_now="۱۹ آبانِ ۱۴۰۵", day_last="۱۹ آبانِ ۱۴۰۴", unit="کیلومترمربع آب",
        dam="سدِ کرخه", full=f"دریاچه‌ی پُر، ۱۳۹۸: {fa(round(n['full']))}",
        head_c="پایین‌دستِ سد: {هورالعظیم}", small_c="محیطِ زیست: حقابه‌اش در سال‌های اخیر جز ۱۳۹۸ تأمین نشده",
        marsh="هورالعظیم", iran="ایران", iraq="عراق", iran_b=f"ایران: حدودِ {fa(IRAN_SIDE)}", iraq_b=f"عراق: حدودِ {fa(IRAQ_SIDE)}",
        head_b=f"آن‌سوی مرز، همان تالاب: // {{حدودِ {fa(IRAQ_SIDE)} کیلومترمربع}} آبِ باز", spring="بهارِ ۱۴۰۴",
        head_d=f"گرد و خاکِ ورودی به خوزستان: // {{{fa(DUST_SHARE)}٪ از عراق}}", small_d="مطالعه‌ی ۲۰۲۴ (۱۳۸۲ تا ۱۳۹۶)",
        day_d1="نمونه: ۲۶ اردیبهشتِ ۱۴۰۱", day_d2="یک روز بعد", khuz="خوزستان",
        head_e="ایران حقابه‌ی هامون را می‌خواهد؛ // {هورالعظیم هم حقابه‌ای دارد}", tag_e="هامون، بهارِ ۱۴۰۴", afg="افغانستان",
        head_f="آبِ رودِ مشترک: // {چطور تقسیم شود؟}", follow="برای یک خوزستانی بفرستید",
        src_a="تصویر و سنجش: Sentinel-2 (Copernicus)؛ پُرشدگی: شرکتِ منابعِ آب، تا ۱۰ آبانِ ۱۴۰۵",
        src_c="حقابه: مدیرکلِ محیطِ زیستِ خوزستان، خبرگزاریِ مهر، ۲۳ شهریورِ ۱۴۰۵ // نقشه: Sentinel-2 cloudless (EOX)، OpenStreetMap، Natural Earth",
        src_b="تصویر و سنجش: لندست (USGS)؛ مرز: Natural Earth",
        src_d="تصویر: MODIS (NASA Worldview)؛ مطالعه: درگاهیان و همکاران، ۲۰۲۴",
        src_e="تصویر: لندست (USGS)؛ مطالبه‌ی رسمیِ ایران: پیمانِ هیرمند، ۱۳۵۱",
        src_f="منابع در کامنتِ اول",
    )
    tags = dict(now=dict(day=words["day_now"], n=fa(round(n["now"]))), last=dict(day=words["day_last"], n=fa(round(n["last"]))))
    clock = clock_of()
    reading(words, clock)
    film = dict(fps=FPS, size=[W, H], clock=clock, end=clock["end"], cover_t=clock["cover"], numbers=n, words=words, tags=tags,
                lake=lake, card=card(), marsh=marsh(), dust=dust(), hamoun=hamoun(), locator=locator(),
                places=dict(dam=gkh.DAM, full=(48.10, 32.652), marsh=(47.95, 31.47), c_iran=(47.86, 32.22), c_iraq=(47.24, 31.95),
                            b_iran=(47.93, 31.50), b_iraq=(47.52, 31.45), d_iraq=(45.3, 32.3), d_khuz=(49.35, 31.75),
                            e_iran=(61.16, 30.98), e_afg=(61.86, 31.42)),
                colours=dict(gold="#F6C445", ink="#1d140c", paper="#FBF7F0", river="#49c0ff"))
    (BUILD / "film.json").write_text(json.dumps(film, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", BUILD / "film.json", "| end", clock["end"])


if __name__ == "__main__":
    main()
