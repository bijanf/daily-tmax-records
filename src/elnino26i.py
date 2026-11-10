"""THE EL NIÑO REEL AS AN INFOGRAPHIC (elnino26i_fa): the words, numbers and pictures of the page.

The same reel as src/onebit_elnino26x.py (the explainer, 86 s) and src/onebit_elnino26s.py (the narrated cut, 35.5 s),
drawn again as an infographic by a web page (src/elnino26i_page/) that src/onebit_elnino26i.py renders frame by frame.
Nothing is typed twice: this module builds the reviewed film object (so every assert of its numbers and words runs),
and writes what the page shows into outputs/onebit/elnino26i/:

    film.json            every on-screen string (onebit_elnino26x.words(), unchanged), every number (the numbers.json
                         of elnino26x and elnino26s, src/enso.py), the two clocks (cut a: 35.5 s, cut b: 86 s) and the
                         geometry of the pictures
    pacific_now.png      the week's tropical Pacific (120 E to 80 W, 30 S to 30 N): the film's own make_pacific recipe
                         (bm_crop, sample, warm), twice as large, without the box burnt in
    week_ago.png, week_now.png   the two weeks against 1991-2020 (25 S to 25 N): the film's make_anomaly recipe, larger
    key_pacific.png, key_weeks.png   the two colour keys (the film's own strips)
    iran_composite.png   the film's Iran map (make_iran, larger), cut out along the border (transparent outside)
    iran_land.png        the Blue Marble of Iran (NASA, natural colour), cut out along the border: the hook's picture

The page draws no land or sea from a mask: the pictures are the Blue Marble, as in the films; only Iran is cut out
along its border (src/enso.py's iran_mask, the polygon the rain statistics use).

    python -I src/elnino26i.py        builds the film object (asserts), writes film.json and the pictures, prints a summary
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from scipy.ndimage import binary_dilation, gaussian_filter  # noqa: E402

import enso  # noqa: E402
import onebit  # noqa: E402
import onebit_elnino2 as el2  # noqa: E402
import onebit_elnino26s as s26  # noqa: E402
import onebit_elnino26x as x26  # noqa: E402
from onebit import fa  # noqa: E402
from onebit_slides import COLOURS  # noqa: E402

BUILD = onebit.ROOT / "outputs" / "onebit" / "elnino26i"
SCALE = 2                                            # the pictures are exported at twice the page's pixels
IRAN_H = 1200                                        # px: the height of the Iran pictures (MAP_BOX), before the crop
# cut a: the narrated reel's clock (src/onebit_elnino26s.py, its soundtrack elnino26s_fa_light.wav)
CUT_A = ("hook", "autumn", "iran", "winter", "answer")
SECONDS_A = tuple(4 * b for b in s26.PACE["bars"])  # 7, 7.75, 4, 8, 8.75 s


def hexa(rgb) -> str:
    return "#%02x%02x%02x" % tuple(int(round(float(v))) for v in rgb)


def pacific(film, scale: int = SCALE) -> Image.Image:
    """The hook's Pacific: onebit_elnino26x.make_pacific's recipe at `scale` times the size, the box not burnt in."""
    W, H = s26.PAC_W * scale, s26.PAC_H * scale
    base = film.bm_crop(30.0, W, H)
    val, wet = film.sample(film.weeks["now"], 30.0, W, H)
    hot = wet & (val >= s26.KEY_LO)
    rgb, alpha = film.warm(val)
    alpha = np.maximum(alpha, s26.TINT_MIN_ALPHA)
    out = base.copy()
    out[hot] = (1 - alpha[hot][:, None]) * base[hot] + alpha[hot][:, None] * rgb[hot]
    return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8))


def anomaly(film, tag: str, scale: int = SCALE) -> Image.Image:
    """One of the two weeks: onebit_elnino26x.make_anomaly's recipe at `scale` times the size."""
    W, H = x26.AB_W * scale, x26.AB_H * scale
    base = film.bm_crop(x26.AB_LAT, W, H)
    val, wet = film.sample(film.weeks[tag], x26.AB_LAT, W, H)
    rgb, alpha = film.ab_colour(val)
    alpha = np.where(wet, alpha, 0.0)
    out = (1 - alpha[..., None]) * base + alpha[..., None] * rgb
    return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8))


def iran_grid(H: int) -> tuple:
    """The Iran pictures' size and the latitude and longitude of each pixel (as onebit_elnino26s.make_iran)."""
    w_, e_, s_, n_ = el2.MAP_BOX
    W = round(H * (e_ - w_) * math.cos(math.radians((s_ + n_) / 2)) / (n_ - s_))
    lon_d = w_ + (np.arange(W) + 0.5) / W * (e_ - w_)
    lat_d = n_ - (np.arange(H) + 0.5) / H * (n_ - s_)
    LON, LAT = np.meshgrid(lon_d, lat_d)
    return W, H, LAT, LON


def cutout(rgb: np.ndarray, mask: np.ndarray, pad: int = 12) -> tuple:
    """An RGBA picture, opaque inside the mask (its edge softened by a pixel), cropped to the mask with a margin."""
    alpha = np.clip(gaussian_filter(mask.astype(float), 1.0) * 1.6 - 0.3, 0, 1)
    ys, xs = np.nonzero(mask)
    y0, y1 = max(0, ys.min() - pad), min(mask.shape[0], ys.max() + 1 + pad)
    x0, x1 = max(0, xs.min() - pad), min(mask.shape[1], xs.max() + 1 + pad)
    rgba = np.dstack([rgb, np.round(alpha * 255).astype(np.uint8)])[y0:y1, x0:x1]
    return Image.fromarray(rgba, "RGBA"), (x0, y0, x1, y1)


def iran_pictures(film, H: int = IRAN_H) -> dict:
    """The film's Iran map, larger, cut out along the border, and the natural-colour Blue Marble of Iran, cut out."""
    W, H, LAT, LON = iran_grid(H)
    proxy = SimpleNamespace(map_w=W, map_h=H, comp=film.comp)
    rect = np.asarray(s26.ElNino26sFilm.make_iran(proxy))            # the reviewed picture, at this size
    mask = enso.iran_mask(LAT, LON)
    comp, box = cutout(rect, binary_dilation(mask, iterations=2))    # with the border line make_iran draws
    w_, e_, s_, n_ = el2.MAP_BOX
    bm = onebit.ROOT / "data" / "air" / "bluemarble_srb_iran.jpg"
    step, lon0, lat0 = 0.005, 42.0, 45.5                             # the file's grid (as in make_iran)
    crop = (round((w_ - lon0) / step), round((lat0 - n_) / step), round((e_ - lon0) / step), round((lat0 - s_) / step))
    land = np.asarray(Image.open(bm).convert("RGB").crop(crop).resize((W, H), Image.LANCZOS))
    land_cut, box2 = cutout(land, mask)
    return dict(comp=comp, land=land_cut, box=box, box2=box2, size=(W, H))


def seasons(film) -> dict:
    out = {}
    for key, season in (("autumn", x26.AUTUMN), ("winter", x26.WINTER)):
        r = film.res[season]
        flags = [bool(r["wetter"][y]) for y in r["years"]]
        out[key] = dict(years=[int(y) for y in r["years"]], wetter=flags, n=len(flags), n_wetter=int(sum(flags)),
                        per_row=s26.PER_ROW[season], count=f"{fa(sum(flags))} از {fa(len(flags))}",
                        turn0=s26.WET_T0[season], span=s26.WET_SPAN[season], count_t=s26.COUNT_T[season])
    return out


def film_json(film, pics: dict) -> dict:
    w, n, n26 = film.words, film.nums, film.n26
    scenes_b = [dict(key=k, start=float(film.starts[i]), length=float(x26.SECONDS[i]), title=w["scenes"][i][0],
                     small=w["scenes"][i][1], source=w["sources"][i], voice=x26.VOICE_OF.get(k),
                     counter=(f"[{i}/{len(x26.SCENES) - 2}]" if 0 < i < len(x26.SCENES) - 1 else ""))
                for i, k in enumerate(x26.SCENES)]
    by_key = {s["key"]: s for s in scenes_b}
    starts_a = np.cumsum((0.0,) + SECONDS_A)
    scenes_a = [dict(by_key[k], start=float(starts_a[i]), length=float(SECONDS_A[i]),
                     counter=(f"[{i}/{len(CUT_A) - 2}]" if 0 < i < len(CUT_A) - 1 else ""))
                for i, k in enumerate(CUT_A)]
    assert abs(starts_a[-1] - s26.END) < 1e-9 and abs(float(film.starts[-1]) - x26.END) < 1e-9
    mean, el = n26["iran_mean74"], n26["iran_mm_el"]
    paths = {y: [q for q in p if q[0] <= x26.CH_DAYS] for y, p in n["paths"].items()}
    peak = max(n["paths"]["2026"], key=lambda q: q[1])
    prev = n["weekly"]["record_n34"]["second"]["value"]
    lo, hi = el2.LO, el2.HI
    return dict(
        app=film.app, fps=onebit.FPS, size=list(onebit.SIZES["reel"]),
        cuts=dict(a=dict(end=float(s26.END), scenes=scenes_a), b=dict(end=float(x26.END), scenes=scenes_b)),
        cover_t=x26.COVER_T, follow=w["follow"],
        colours=dict(paper=film.th.paper, ink=film.th.ink, mark=film.th.mark, dots=film.th.dots,
                     land=COLOURS["kahgel"]["land"], wet=hexa(el2.WET), dry=hexa(el2.DRY), mid=hexa(el2.MID),
                     pale=hexa(el2.PALE), past=x26.PAST, near=hexa((176, 166, 152))),
        hook=dict(nino_label=s26.NINO_LABEL, pac_label=s26.PAC_LABEL, pac_key=list(w["pac_key"]),
                  pac_ticks=[dict(v=v, label=lab, f=(v - s26.KEY_LO) / (s26.KEY_HI - s26.KEY_LO))
                             for v, lab in zip((1.5, 2.0, 3.0, 4.0, 5.0), w["pac_ticks"])],
                  box=dict(x0=(190.0 - 120.0) / 160.0, x1=(240.0 - 120.0) / 160.0, y0=(30.0 - 5.0) / 60.0,
                           y1=(30.0 + 5.0) / 60.0),
                  oni=n26["oni"], oni_shown=x26.fa_dec(n26["oni_shown"]), scale=list(s26.BAR_SCALE),
                  scale_labels=[fa(int(s26.BAR_SCALE[0])), fa(int(s26.BAR_SCALE[1]))],
                  marks=[dict(label=lab, v=v) for lab, v in w["dam_marks"]], unit=list(w["dam_unit"])),
        what=dict(labels=list(w["ab_labels"]), key=list(w["ab_key"]), places=list(w["ab_places"]),
                  box=dict(x0=(190.0 - 120.0) / 160.0, x1=(240.0 - 120.0) / 160.0,
                           y0=(x26.AB_LAT - 5.0) / (2 * x26.AB_LAT), y1=(x26.AB_LAT + 5.0) / (2 * x26.AB_LAT))),
        record=dict(paths=paths, last_day=n["paths"]["2026"][-1][0], days=x26.CH_DAYS, vmax=x26.CH_MAX,
                    months=[dict(name=m, day=d) for m, d in x26.MONTHS],
                    grid=[dict(v=v, label=f"+{fa(v)}") for v in (1, 2, 3)], zero=fa(0),
                    prev=prev, prev_label=f"{w['ch_prev']}: {x26.fa_dec(prev)}",
                    peak=dict(day=peak[0], v=peak[1], label=f"۲۰۲۶: +{x26.fa_dec(peak[1])}"),
                    draw=[x26.DRAW_T0, x26.DRAW_T1], legend=w["ch_legend"], unit=w["ch_unit"], wmo=w["ch_wmo"]),
        seasons=seasons(film), legend=list(w["legend"]),
        iran=dict(scale=[dict(v=v, label=lab, f=(v - lo) / (hi - lo))
                         for v, lab in zip((100, 110, 120, 130, 140, 150), w["scale"])],
                  ramp=[dict(f=k / 24, colour=hexa(el2.colour_of(np.array([lo + (hi - lo) * k / 24]))[0]))
                        for k in range(25)],
                  unit=w["unit"], mean=mean, el=el, top=mean / s26.RAIN_MEAN_AT,
                  mean_label=fa(f"میانگین {round(mean)}"), el_label=fa(round(el)), zero=fa(0),
                  rain_unit=w["rain_unit"], rain_off=s26.RAIN_OFF, grow=s26.GROW,
                  comp_size=list(pics["comp"].size), land_size=list(pics["land"].size)),
        strong=dict(bars=[dict(year=fa(b["year"]), pct=b["pct"], label=fa(f"{b['pct']}٪"),
                               kind=("wet" if b["pct"] > 110 else "dry" if b["pct"] < 90 else "near"))
                          for b in n["strong"]],
                    vmax=x26.ST_MAX, this_year=fa(2026), question="؟", t0=x26.ST_T0, step=x26.ST_STEP,
                    unit=w["st_unit"], mean=w["st_mean"]),
        answer=dict(note=w["note"], recap=list(w["recap"]), question=w["question"].split(" // "),
                    reveal_gap=s26.REVEAL_GAP),
        pictures=dict(pacific="pacific_now.png", ago="week_ago.png", now="week_now.png", key_pacific="key_pacific.png",
                      key_weeks="key_weeks.png", iran_comp="iran_composite.png", iran_land="iran_land.png"),
    )


def main() -> None:
    film = x26.ElNino26xFilm(onebit.THEMES["kahgel"], COLOURS["kahgel"])     # every assert of the reviewed film runs
    BUILD.mkdir(parents=True, exist_ok=True)
    pacific(film).save(BUILD / "pacific_now.png")
    for tag in ("ago", "now"):
        anomaly(film, tag).save(BUILD / f"week_{tag}.png")
    film.key_pac.save(BUILD / "key_pacific.png")
    film.ab_key.save(BUILD / "key_weeks.png")
    pics = iran_pictures(film)
    pics["comp"].save(BUILD / "iran_composite.png")
    pics["land"].save(BUILD / "iran_land.png")
    data = film_json(film, pics)
    (BUILD / "film.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    for cut in ("a", "b"):
        c = data["cuts"][cut]
        print(f"cut {cut}: {c['end']} s, {round(c['end'] * onebit.FPS)} frames, scenes " +
              ", ".join(f"{s['key']} {s['start']:g}" for s in c["scenes"]))
    print("pictures:", {k: Image.open(BUILD / v).size for k, v in data["pictures"].items()})
    print("saved", BUILD / "film.json")


if __name__ == "__main__":
    main()
