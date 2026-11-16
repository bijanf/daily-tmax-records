"""«آبِ کارون کجا می‌رود؟» (karun_fa): two places on the Karun from space, late summer 1369 against 1405, the satellite
picture as the whole frame, one part without narration. A sibling of hoor (same engine, same look). This file is the
film's data: it writes outputs/onebit/karun/film.json (every string, number, the clock, the colours) and the pictures
the page draws; src/karun_page/ draws any moment from it and src/onebit_karun.py steps it frame by frame.

The owner (15-16 Nov 2026): a before/after of the Karun "like the Hamoun". The river itself shows none from space (its
late-summer water surface through Ahvaz is nearly the same in 1990 and 2026: research/feasibility/feas_karun), so the
film shows what appeared along it:

- upstream, the lake behind the Gotvand dam (filling began on 8 Mordad 1390; design area 96.5 km2 at normal level:
  the independent check of the measured area), where 1369 has only the river's thread;
- downstream, south of Ahvaz, the watered fields (green in late summer, when nothing has rained since spring): the
  cane units of the development plan and other irrigated crops, where 1369 has bare plain.

The film opens on the whole Earth and falls to the lake (zoomkit.py; the mosaic it falls through is of 2016, so it
lands on the lake as it is now and the wipe runs BACK to 1369, then forward again). Between the two places a map of
the river (the same mosaic, the Karun's line from OpenStreetMap) carries a marker down the river. The causes are
named without shares (fact check of 16 Nov 2026: no source gives shares; the transfers' volumes are disputed).

Numbers on screen are this film's own measurements (get_karun.py), asserted here against the table.

    python -I src/get_karun.py
    python -I src/get_karun_zoom.py
    python -I src/karun.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))

import get_karun as gk  # noqa: E402
import get_karun_zoom as gz  # noqa: E402
import zoomkit  # noqa: E402
from onebit import fa  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "outputs" / "onebit" / "karun"
FPS, W, H = 30, 1080, 1920
BEFORE, NOW = gk.PICTURES                            # 1990 (1369) and 2026 (1405)
EARLY, LATE = (1987, 1994), (2022, 2026)             # the summers behind "then" and "now" in the caption
DAM = (48.937, 32.268)                               # the Gotvand dam (the lake's western end on the pictures)
AHVAZ = (48.684, 31.319)
FIELDS_AT = (48.40, 31.00)                           # where the marker stops on the river, between the cane blocks
NE = ROOT / "data" / "hoor" / "ne" / "ne_10m_admin_0_countries.shp"   # Natural Earth, kept by get_hoor.py


def solar(y: int) -> int:
    return y - 621                                   # a late-summer date of year y is in Persian year y - 621


def tone(rgb: np.ndarray) -> np.ndarray:
    """One fixed stretch for both years (hamoun.display): reflectance 0-0.42, gamma 1/1.5."""
    x = np.clip(np.nan_to_num(rgb, nan=0.0) / 0.42, 0, 1) ** (1 / 1.5)
    return (255 * np.moveaxis(x, 0, -1)).astype(np.uint8)


def pictures() -> dict:
    """Each place's two pictures on the frame's own grid (1080 x 1920: the place's box is 9:16 on the ground). Pixels
    never clear in a summer's passes take the other summer's, then their nearest clear neighbour (printed)."""
    BUILD.mkdir(parents=True, exist_ok=True)
    out = {}
    for name in gk.PLACES:
        raw = {y: np.load(gk.OUT / f"{name}_{y}.npz") for y in (BEFORE, NOW)}
        for y, o in ((BEFORE, NOW), (NOW, BEFORE)):
            rgb = raw[y]["rgb"].copy()
            hole = np.isnan(rgb).any(axis=0)
            other = raw[o]["rgb"]
            take = hole & ~np.isnan(other).any(axis=0)
            rgb[:, take] = other[:, take]
            left = np.isnan(rgb).any(axis=0)
            if left.any():
                idx = ndimage.distance_transform_edt(left, return_distances=False, return_indices=True)
                rgb = rgb[:, idx[0], idx[1]]
            print(f"picture {name} {y}: {len(raw[y]['dates'])} passes ({', '.join(str(d) for d in raw[y]['dates'])}); "
                  f"{hole.mean() * 100:.2f} % never clear, {left.mean() * 100:.2f} % from the nearest clear pixel")
            assert hole.mean() < 0.03, (name, y, hole.mean())
            Image.fromarray(tone(rgb)).resize((W, H), Image.LANCZOS).save(BUILD / f"p_{name}_{y}.jpg", quality=93)
        box = gk.PLACES[name]["box"]
        w, s, e, n = box
        ratio = (e - w) * 111.32 * math.cos(math.radians((s + n) / 2)) / ((n - s) * 111.32)
        assert abs(ratio - W / H) < 0.002, (name, ratio)                  # the box is 9:16 on the ground
        out[name] = dict(box=list(box), w=W, h=H)
    return out


def numbers() -> dict:
    sm = pd.read_csv(gk.OUT / "summers.csv").set_index(["place", "year"])
    lake, fields = sm.loc["gotvand"].km2, sm.loc["fields"].km2
    odd = lake[lake < 0.5]                           # 1992: the one counted pass (Landsat 4, 20 Aug) finds no water at all, not
    assert list(odd.index) in ([], [1992]), odd      # even the river every other early summer shows: left out, never on screen
    lake = lake[lake >= 0.5]
    n = dict(lake_then=float(lake[BEFORE]), lake_now=float(lake[NOW]), fields_then=float(fields[BEFORE]), fields_now=float(fields[NOW]),
             lake_early=float(lake.loc[EARLY[0]:EARLY[1]].median()), lake_late=float(lake.loc[LATE[0]:LATE[1]].median()),
             lake_late_range=[float(lake.loc[2013:].min()), float(lake.loc[2013:].max())],
             fields_early=float(fields.loc[EARLY[0]:EARLY[1]].median()), fields_late=float(fields.loc[LATE[0]:LATE[1]].median()),
             fields_early_range=[float(fields.loc[EARLY[0]:EARLY[1]].min()), float(fields.loc[EARLY[0]:EARLY[1]].max())],
             fields_late_range=[float(fields.loc[LATE[0]:LATE[1]].min()), float(fields.loc[LATE[0]:LATE[1]].max())],
             n_early=int(fields.loc[EARLY[0]:EARLY[1]].count()), n_late=int(fields.loc[LATE[0]:LATE[1]].count()))
    print(json.dumps({k: (round(v, 1) if isinstance(v, float) else v) for k, v in n.items()}, indent=1))
    # the statements on screen and in the caption
    assert n["lake_then"] < 10 and n["lake_now"] > 80, n                 # the river's thread against a lake
    assert n["lake_now"] <= 96.5 + 2, n                                  # not above the design area at normal level
    assert n["fields_then"] < 120 and n["fields_now"] > 800, n
    assert n["fields_late_range"][0] > 6 * n["fields_early_range"][1], n  # every late summer far above every early one
    return n


def card(tones: np.ndarray) -> dict:
    """The map between the places: the mosaic over the river, in the landing picture's tones."""
    im = np.asarray(Image.open(gz.OUT / "card.jpg").convert("RGB"), np.float32) * tones
    Image.fromarray(np.clip(im + 0.5, 0, 255).astype(np.uint8)).save(BUILD / "card.jpg", quality=92)
    line = json.loads((gz.OUT / "river.json").read_text())
    w, s, e, n = gz.CARD_BOX
    # one point about every 400 m is enough for the line on the map; keep the first and the last
    keep, last = [line[0]], line[0]
    for p in line[1:]:
        if math.hypot((p[0] - last[0]) * 95.0, (p[1] - last[1]) * 111.32) >= 0.4:
            keep.append(p)
            last = p
    keep.append(line[-1])
    km = np.cumsum([0.0] + [math.hypot((b[0] - a[0]) * 95.0, (b[1] - a[1]) * 111.32) for a, b in zip(keep[:-1], keep[1:])])
    at = lambda q: int(np.argmin([math.hypot((p[0] - q[0]) * 95.0, (p[1] - q[1]) * 111.32) for p in keep]))   # noqa: E731
    i_dam, i_ahvaz, i_fields = at(DAM), at(AHVAZ), at(FIELDS_AT)
    assert i_dam < i_ahvaz < i_fields, (i_dam, i_ahvaz, i_fields)
    print(f"river on the map: {len(keep)} points; along it from the dam to Ahvaz {km[i_ahvaz] - km[i_dam]:.0f} km, to the fields {km[i_fields] - km[i_dam]:.0f} km")
    return dict(file="card.jpg", box=[w, s, e, n], px=list(gz.CARD_PX), river=keep, i_dam=i_dam, i_fields=i_fields,
                km_fields=float(km[i_fields] - km[i_dam]))


def clock_of() -> dict:
    Z = zoomkit.ZOOM_T
    a = (Z, 12.6)                                    # the lake
    c = (a[1], a[1] + 3.4)                           # the map: down the river
    b = (c[1], c[1] + 8.4)                           # the fields
    why = (b[1], b[1] + 5.5)
    end = (why[1], why[1] + 7.5)
    out = (end[1], end[1] + 0.8)
    return dict(zoom=Z, hook=(0.0, 4.4), a=a, card=c, b=b, why=why, close=end, out=out, end=out[1], cover=Z + 0.4,
                far=(zoomkit.DWELL[0] - 0.18, zoomkit.DWELL[0] + 0.02, zoomkit.DWELL[1], zoomkit.DWELL[1] + 0.25),
                pin=(Z - 0.65, Z - 0.25), land=(Z - 0.4, Z - 0.05),
                head_a=4.4, a_back=(5.6, 6.9), a_fwd=(8.6, 9.9),
                head_b=b[0], b_back=(b[0] + 1.4, b[0] + 2.7), b_fwd=(b[0] + 4.2, b[0] + 5.5),
                share=why[0] + 0.8, follow=end[0] + 2.4, back=(end[0], end[0] + 0.6))


def reading(Wd: dict, C: dict) -> None:
    """The owner's reading rule (src/onebit_reading.py) on every scene, asserted."""
    import onebit_reading as rd
    wt = lambda xs: sum(rd.weight(x) for x in xs)    # noqa: E731
    tag = [Wd["summer"].format("۱۴۰۵"), "۹۱", Wd["unit_a"], Wd["summer"].format("۱۳۶۹"), "۳"]
    tagb = [Wd["summer"].format("۱۴۰۵"), "۱٬۰۰۰", Wd["unit_b"], Wd["summer"].format("۱۳۶۹"), "۶۰"]
    plan = [("hook", C["hook"], [Wd["hook"]], [Wd["iran"], Wd["gulf"], Wd["karun"], Wd["dam"]], C["far"][1]),
            ("lake", (C["head_a"], C["a"][1]), [Wd["head_a"], Wd["small_a"]], [*tag, Wd["dam"]], sum(C["a_fwd"]) / 2),
            ("map", C["card"], [Wd["head_c"]], [Wd["dam"], Wd["ahvaz"], Wd["river"]], C["card"][0] + 0.4),
            ("fields", C["b"], [Wd["head_b"], Wd["small_b"]], [*tagb, Wd["river"]], sum(C["b_fwd"]) / 2),
            ("why", C["why"], [Wd["why"], Wd["share"]], [], C["share"]),
            ("close", (C["close"][0], C["close"][1] - 0.7), [Wd["close"], *Wd["follow"]], [], C["follow"])]
    print("\nreading (seconds the rule needs, seconds given):")
    for name, (a, b), full, half, last in plan:
        w = wt(full) + rd.LABELS * wt(half)
        need = max(rd.SETTLE + w / rd.WPS, last - a + rd.HOLD)
        print(f"  {name:6s} {wt(full):4.1f} + {wt(half):4.1f}/2 words -> {need:4.1f} s needed, {b - a:4.1f} s given")
        assert b - a + 0.051 >= need, (name, round(need, 2), round(b - a, 2))


def main() -> None:
    grids = pictures()
    n = numbers()
    place = dict(name="karun", lon0=gz.LON0, lat0=gz.LAT0, box=gk.PLACES["gotvand"]["box"], pic=str(BUILD / f"p_gotvand_{NOW}.jpg"),
                 levels=str(gz.OUT), nested=gz.NESTED, out=str(BUILD / "zoom"), outlines=["IRN"], ne=str(NE))
    zoomkit.configure(place)
    zoom = zoomkit.build()
    crd = card(zoomkit.tones())
    r10 = lambda v: round(v / 10) * 10               # noqa: E731
    words = dict(
        hook="آبِ {کارون} کجا می‌رود؟", summer="تابستانِ {}", iran="ایران", gulf="خلیجِ فارس", karun="کارون",
        dam="سدِ گتوند", ahvaz="اهواز", river="رودِ کارون",
        unit_a="کیلومترمربع آب", unit_b="کیلومترمربع کشتِ سبز",
        head_a="بالادست: این دریاچه // {در ۱۳۶۹ نبود}", small_a="آبگیریِ سدِ گتوند: از ۱۳۹۰",
        head_c="پایین‌دست، {جنوبِ اهواز}",
        head_b="{بیشترِ این مزرعه‌ها} هم // در ۱۳۶۹ نبودند", small_b="نیشکر و کشتِ آبیِ دیگر",   # "most": 1369 has 60 km2 of green of its own
        why="سد، کشاورزی، // انتقالِ آب، خشکسالی", share="سهمِ هر عامل محلِ بحث است",
        close="شما {کارونِ پُرآب} را // دیده‌اید؟", follow=["برای کسی بفرستید", "که اهلِ خوزستان است"],
        src_zoom="زمین: Sentinel-2 cloudless (EOX)؛ مرز: Natural Earth",
        src_pic="منبع: لندست (USGS)؛ سنجش از همین تصویرها",
        src_card="زمین: Sentinel-2 cloudless (EOX)، ۲۰۱۶؛ رود: OpenStreetMap",
        src_why="منابع در کامنتِ اول",
    )
    tags = dict(gotvand={str(BEFORE): dict(year=fa(solar(BEFORE)), n=fa(round(n["lake_then"]))), str(NOW): dict(year=fa(solar(NOW)), n=fa(round(n["lake_now"])))},
                fields={str(BEFORE): dict(year=fa(solar(BEFORE)), n=fa(r10(n["fields_then"]))), str(NOW): dict(year=fa(solar(NOW)), n=fa(r10(n["fields_now"])))})
    clock = clock_of()
    reading(words, clock)
    film = dict(fps=FPS, size=[W, H], clock=clock, end=clock["end"], cover_t=clock["cover"], zoom=zoom, grids=grids, card=crd,
                before=BEFORE, now=NOW, tags=tags, numbers=n, words=words,
                places=dict(dam=DAM, ahvaz=AHVAZ, river_b=(48.385, 31.035), iran_far=(54.3, 32.4), gulf=(51.0, 27.2)),
                colours=dict(wet="#1c5cab", gold="#F6C445", ink="#1d140c", paper="#FBF7F0", river="#49c0ff"))
    (BUILD / "film.json").write_text(json.dumps(film, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", BUILD / "film.json", "| end", clock["end"])


if __name__ == "__main__":
    main()
