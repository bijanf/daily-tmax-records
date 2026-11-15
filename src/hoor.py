"""«آبِ هورالعظیم کجا رفت؟» (hoor_fa): the Hoor al-Azim / Hawizeh marsh from space, the satellite picture as the whole
frame, one part without narration. A sibling of hamoun3 and urmia2 (same engine, same look). This file is the film's
data: it writes outputs/onebit/hoor/film.json (every string, number, the clock, the colours) and the pictures the
page draws; src/hoor_page/ draws any moment from it and src/onebit_hoor.py steps it frame by frame.

The owner (15 Nov 2026), after Hamoun part 1 made 521,808 views: a before/after of the Karun "like the Hamoun". The
Karun itself shows no before/after from space (research/feasibility/feas_karun/README.md); Hoor al-Azim does, and a
viewer asked for it under the Hamoun reel. He agreed to build it first, saying plainly that here Iran is the upstream
side (the Karkheh, the border embankment), causes on both sides, shares contested.

- The springs: get_hoor.py's late-spring open water (15 Apr-15 Jun, MNDWI > 0 and SWIR1 < 0.15, the median of a
  spring's accepted passes) inside the marsh (JRC occurrence > 0 in a hand polygon), split by the border.
- The counts on screen are computed and asserted here (counts, not "a third": the floods of 1398 lifted 1398-1400
  above the early springs, and the early years were not "full": UNEP 2001 says Hawizeh had lost about two thirds by
  2000, so no word «پُر» or «سالم» for them).
- The words on causes follow the fact check of 15 Nov 2026 (research/feasibility/feas_karun/): drought, dams and
  water use in BOTH countries and a border embankment (about 65 km, 1388 = 2009; Iraqi Civil Society, KBA 8056,
  Reuters 2025); oil (Azadegan) is an official's and the press's claim, contested: caption only, not on screen.

- The opening (the owner on the first cut, 15 Nov 2026: «معلوم نیست هورالعظیم کجاست؛ باید از کره‌ی زمین اولش زوم کنی آدم
  بفهمه»): the film opens on the whole Earth and falls to the marsh in hoor_zoom.ZOOM_T seconds, resting at the scale
  of Iran and Iraq for the names («ایران», «عراق», «خلیجِ فارس») and a gold pin on the place; the before/after wipe
  follows the landing. The last 0.8 s plays the same frames backwards, so the loop closes on the globe.

    python -I src/get_hoor.py
    python -I src/get_hoor_zoom.py
    python -I src/hoor.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))

import get_hoor as gh  # noqa: E402
import hoor_zoom as hz  # noqa: E402
from onebit import fa  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "outputs" / "onebit" / "hoor"
FPS, W, H = 30, 1080, 1920
WATER_RGB, WATER_ALPHA = (24, 104, 214), 0.62
FIRST, LAST = 1986, 2026
SPLIT = 1999                                         # the first spring of the second era (1378)
LINE = 700                                           # km2: every spring of 1986-1998 had more open water than this


def solar(y: int) -> int:
    return y - 621                                   # a late-spring date of year y is in Persian year y - 621


def springs() -> pd.DataFrame:
    sp = pd.read_csv(gh.OUT / "springs.csv").set_index("year")
    return sp.reindex(range(FIRST, LAST + 1))


def counts(sp: pd.DataFrame) -> dict:
    v = sp["water_all"]
    early, late = v.loc[FIRST:SPLIT - 1], v.loc[SPLIT:]
    out = dict(n_early=int(early.notna().sum()), early_min=float(early.min()), n_late=int(late.notna().sum()),
               late_above=[int(y) for y in late.index if late[y] > LINE], late_below=int((late <= LINE).sum()),
               missing=[int(y) for y in v.index if pd.isna(v[y])], now=float(v[LAST]), mean_early=float(early.median()))
    print(json.dumps(out, indent=1))
    return out


def tone(rgb: np.ndarray) -> np.ndarray:
    """One fixed stretch for every year (hamoun.display): reflectance 0-0.42, gamma 1/1.5."""
    x = np.clip(np.nan_to_num(rgb, nan=0.0) / 0.42, 0, 1) ** (1 / 1.5)
    return (255 * np.moveaxis(x, 0, -1)).astype(np.uint8)


def pictures(sp: pd.DataFrame) -> dict:
    """Each spring with a clean picture: its true colour (p<year>.jpg) and its measured open water as a blue veil
    inside the marsh (v<year>.png). A spring without one holds the last clean picture."""
    BUILD.mkdir(parents=True, exist_ok=True)
    z = np.load(gh.OUT / "marsh.npz")
    marsh = z["marsh"]
    Hm, Wm = (s // gh.PIC for s in marsh.shape)
    m2 = marsh[:Hm * gh.PIC, :Wm * gh.PIC].reshape(Hm, gh.PIC, Wm, gh.PIC).mean(axis=(1, 3))
    have, size = {}, None
    for y in range(FIRST, LAST + 1):
        f = gh.OUT / f"pic_{y}.npz"
        if not f.exists():
            continue
        p = np.load(f)
        img = tone(p["rgb"])
        hole = ~np.isfinite(p["rgb"]).all(axis=0)
        if hole.mean() > 0.02:
            print(f"picture {y}: {hole.mean() * 100:.1f} % unseen: no picture")
            continue
        Image.fromarray(img).save(BUILD / f"p{y}.jpg", quality=92)
        wat = np.nan_to_num(p["water"], nan=0.0) * (m2 > 0.5)
        rgba = np.zeros(wat.shape + (4,), np.uint8)
        rgba[..., :3] = WATER_RGB
        rgba[..., 3] = (255 * WATER_ALPHA * np.clip(wat, 0, 1)).astype(np.uint8)
        Image.fromarray(rgba, "RGBA").filter(ImageFilter.GaussianBlur(0.6)).save(BUILD / f"v{y}.png")
        have[y] = str(p["date"])
        size = img.shape[1], img.shape[0]
    # the border, on the picture grid (px), from Natural Earth's Iran polygon edge inside the frame
    return dict(have=have, size=size)


def border() -> list:
    """The Iran-Iraq boundary inside the frame as lon/lat points (Natural Earth 10 m land boundary lines)."""
    import shapefile
    r = shapefile.Reader(str(gh.OUT / "ne" / "ne_10m_admin_0_countries.shp"))
    fields = [f[0] for f in r.fields[1:]]
    w, s, e, n = gh.BOX
    pts = []
    for sr in r.iterShapeRecords():
        if dict(zip(fields, sr.record))["ADM0_A3"] != "IRQ":
            continue
        P = sr.shape.points
        parts = list(sr.shape.parts) + [len(P)]
        for a, b in zip(parts[:-1], parts[1:]):
            ring = P[a:b]
            run = []
            for lon, lat in ring:
                inside = w - 0.02 <= lon <= e + 0.02 and s - 0.02 <= lat <= n + 0.02
                if inside:
                    run.append([round(lon, 5), round(lat, 5)])
                elif run:
                    if len(run) > 1:
                        pts.append(run)
                    run = []
            if len(run) > 1:
                pts.append(run)
    # keep the eastern edge of Iraq (the border with Iran), not the coast
    pts = [p for p in pts if max(q[0] for q in p) > 47.55]
    return pts


DYKE_LAT = (31.14, 31.79)                            # where the 2025 picture shows the straight wet/dry edge on the border (about 75 km)


def clock_of(bars: list) -> dict:
    """The scenes (s) and their cues. Each scene is sized by the owner's reading rule (reading(), asserted)."""
    n = len(bars)
    Z = hz.ZOOM_T                                                          # the zoom from the globe lands here
    hook = (0.0, 7.8)
    # the springs: the early ones slower (their headline is longer), the ones without a picture a little slower too
    # (their note has to be read), the rest fast
    t0, k1 = hook[1] + 0.6, SPLIT - FIRST
    dur = [0.32 if k < k1 else 0.25 if bars[k]["held"] else 0.20 for k in range(n)]
    st = [round(t0 + sum(dur[:k]), 3) for k in range(n)]
    run = (hook[1], round(st[-1] + 0.95, 1))
    held = [k for k in range(n) if bars[k]["held"]]
    assert held == list(range(held[0], held[-1] + 1)), "the springs without a picture are one block"
    side = (run[1], run[1] + 7.2)
    why_a = (side[1], side[1] + 5.3)                                       # two halves, two rivers, the embankment
    why = (why_a[1], why_a[1] + 6.6)                                       # the causes on both sides, the hedge
    end = (why[1], why[1] + 7.5)
    out = (end[1], end[1] + 0.8)                                           # the same zoom backwards: the loop closes on the globe
    return dict(hook=hook, run=run, side=side, whyA=why_a, why=why, close=end, out=out, end=out[1], cover=Z + 0.3, zoom=Z,
                far=(hz.DWELL[0] - 0.18, hz.DWELL[0] + 0.02, hz.DWELL[1], hz.DWELL[1] + 0.25),   # the far names: in, out (gone before they reach the credit line)
                pin=(Z - 0.65, Z - 0.25), land=(Z - 0.55, Z - 0.1),            # the pin leaves, the border and the near tags come
                wipe1=(Z + 1.0, Z + 2.5), labels=Z - 0.3, t0=t0, spring_t=st,
                held=(st[held[0]], st[held[-1] + 1]),                         # the block of springs without a clean picture
                split=st[k1], side_wipe=(side[0], side[0] + 1.2), split_on=side[0] + 1.6,
                pins=(why_a[0] + 0.6, why_a[0] + 1.2, why_a[0] + 1.8), share=why[0] + 0.8,
                now_wipe=(end[0], end[0] + 1.2), follow=end[0] + 2.4, back=(end[1] - 0.7, end[1]))


def reading(W: dict, C: dict, bars: list) -> None:
    """The owner's reading rule (src/onebit_reading.py) on every scene, asserted."""
    import onebit_reading as rd
    wt = lambda xs: sum(rd.weight(x) for x in xs)        # noqa: E731
    tag = [W["spring"].format("۱۳۷۱"), "۱٬۰۰۰", W["unit"]]
    plan = [("hook", C["hook"], [W["hook"]],
             [W["iran"], W["iraq"], W["gulf"], W["hoor"], *tag, W["iran"], W["iraq"], W["spring"].format("۱۴۰۵"), "۳۲۸"],
             sum(C["wipe1"]) / 2),                                        # the last string: this spring's tag, half-way through the wipe
            ("run 1", (C["run"][0], C["split"]), [W["era1"]], [*tag], C["run"][0] + 0.3),
            ("run 2", (C["split"], C["run"][1]), [W["era2"]], [W["held"]], C["split"]),
            ("held", C["held"], [W["held"]], [], C["held"][0]),            # the note over the springs without a picture
            ("side", C["side"], [W["side"], W["side_small"]], [*tag, W["iran"], W["iraq"]], C["split_on"]),
            ("why a", C["whyA"], [W["why_a"]], [W["karkheh"], W["tigris"], W["dyke"], W["iran"], W["iraq"]], C["pins"][2]),
            ("why b", C["why"], [W["why"], W["share"]], [], C["share"]),
            ("close", (C["close"][0], C["back"][0]), [W["close"], *W["follow"]], tag, C["follow"])]
    print("\nreading (seconds the rule needs, seconds given):")
    for name, (a, b), full, half, last in plan:
        w = wt(full) + rd.LABELS * wt(half)
        need = max(rd.SETTLE + w / rd.WPS, last - a + (rd.HOLD if name != "held" else 0))   # the held note stands from its start
        print(f"  {name:6s} {wt(full):4.1f} + {wt(half):4.1f}/2 words -> {need:4.1f} s needed, {b - a:4.1f} s given")
        assert b - a + 0.051 >= need, (name, round(need, 2), round(b - a, 2))


def main() -> None:
    sp = springs()
    c = counts(sp)
    assert c["n_early"] == 13 and c["early_min"] > LINE, c
    pic = pictures(sp)
    have = pic["have"]
    full = max((y for y in range(FIRST, SPLIT) if y in have), key=lambda y: sp.loc[y, "water_all"])
    assert LAST in have, "no clean picture of this spring"
    lines = border()
    bars = [dict(year=y, label=fa(solar(y)), km2=None if pd.isna(sp.loc[y, "water_all"]) else round(float(sp.loc[y, "water_all"])),
                 iran=None if pd.isna(sp.loc[y, "water_iran"]) else round(float(sp.loc[y, "water_iran"])),
                 pic=y if y in have else max([h for h in have if h <= y], default=min(have)), held=y not in have)
            for y in range(FIRST, LAST + 1)]
    k_above = len(c["late_above"])
    n_late = c["n_late"]
    yrs_above = [solar(y) for y in c["late_above"]]
    words = dict(
        hook="آبِ {هورالعظیم} کجا رفت؟", spring="بهارِ {}", this_spring="بهارِ امسال",
        unit="کیلومترمربع آبِ باز", iran="ایران", iraq="عراق", hoor="هورالعظیم", hawizeh="هورِ حویزه",
        gulf="خلیجِ فارس",
        border="مرز",
        era1=f"{fa(solar(FIRST))} تا {fa(solar(SPLIT - 1))}: // هر {fa(c['n_early'])} بهار {{بیش از {fa(LINE)}}}",
        era2=f"از {fa(solar(SPLIT))}: فقط {fa(k_above)} بهار // {{{fa(yrs_above[0])} تا {fa(yrs_above[-1])}، بعد از سیل}}",
        held="بدونِ تصویرِ صاف",
        why_a="دو نیمه، {دو رود}",
        why="خشکسالی، سدها، برداشتِ آب // {در هر دو کشور}",
        karkheh="رودِ کرخه، از ایران", tigris="شاخه‌های دجله، از عراق", dyke="خاک‌ریزِ مرزی، حدودِ ۱۳۸۸",
        share="سهمِ هر عامل محلِ بحث است",
        side="بهارِ {}: // آبِ باز {بیشتر در سمتِ ایران}",
        close="شما {هورالعظیمِ پُرآب} را // دیده‌اید؟", follow=["برای کسی بفرستید", "که اهلِ خوزستان است"],
        src_water="منبع: لندست (USGS)؛ مقایسه‌شده با آبِ سطحیِ JRC",
        src_map="مرز: Natural Earth؛ خاک‌ریز: گزارش‌های رسانه‌ها و سازمان‌های محیط‌زیستی",
        src_zoom="زمین: Sentinel-2 cloudless (EOX)؛ مرز: Natural Earth",
    )
    side_year = LAST - 1
    si, sq = sp.loc[side_year, "water_iran"], sp.loc[side_year, "water_iraq"]
    assert si > sq, (si, sq)
    words["side"] = words["side"].replace("{}", fa(solar(side_year)), 1)
    words["side_small"] = f"ایران {fa(round(si / 10) * 10)}، عراق {fa(round(sq / 10) * 10)} کیلومترمربع"
    assert yrs_above == [1398, 1399, 1400], yrs_above                    # the headline names them as one run of years
    clock = clock_of(bars)
    reading(words, clock, bars)
    zoom = hz.build(full)                                                  # the frames of the opening, and its camera
    film = dict(fps=FPS, size=[W, H], clock=clock, end=clock["end"], cover_t=clock["cover"], side_year=side_year, zoom=zoom, dyke_lat=list(DYKE_LAT),
                grid=dict(w=pic["size"][0], h=pic["size"][1], box=list(gh.BOX)),
                full=full, now=LAST, bars=bars, counts=c, line=LINE, words=words, border=lines,
                places=dict(hoor=(47.80, 31.62), hawizeh=(47.52, 31.45), iran=(47.93, 31.50), iraq=(47.50, 31.50),
                            karkheh=(47.95, 31.30), tigris=(47.47, 31.22), dyke=(47.70, 31.45),
                            iran_far=(54.3, 32.4), iraq_far=(43.4, 33.0), gulf=(51.0, 27.2)),
                colours=dict(wet="#1c5cab", gold="#F6C445", ink="#1d140c", paper="#FBF7F0", eco="#a03129"))
    (BUILD / "film.json").write_text(json.dumps(film, ensure_ascii=False, indent=1), encoding="utf-8")
    print("full spring:", full, solar(full), sp.loc[full, "water_all"], "| this spring:", sp.loc[LAST].to_dict())
    print("saved", BUILD / "film.json")


if __name__ == "__main__":
    main()
