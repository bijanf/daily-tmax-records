"""«۲ درجه گرم‌تر، یعنی چه؟» (twodeg2_fa): the words, numbers and clock of the reel that explains a global mean.

Iranian viewers read "2 degrees of global warming" as "a summer of 40 becomes 42" (the owner, 11 Nov 2026). The reel
answers with how often extremes come. Every number is from the IPCC AR6 Working Group I Summary for Policymakers
(2021, doi:10.1017/9781009157896.001), read in the report's own text on 11 Nov 2026:

    Figure SPM.6, hot temperature extremes over land, against 1850-1900 (a climate without human influence):
        50-year event, times per 50 years: 4.8 (2.3-6.4) at 1 C, 8.6 (4.3-10.7) at 1.5 C, 13.9 (6.9-16.6) at 2 C;
        hotter by 1.2, 2.0 and 2.7 C.
    Figure SPM.6, heavy 1-day precipitation over land, 10-year event: 1.3 (1.2-1.4), 1.5 (1.4-1.7), 1.7 (1.6-2.0) times;
        wetter by 6.7, 10.5 and 14.0 %.
    B.2.4  extreme daily precipitation intensifies by about 7 % for each 1 C of global warming.

The report names no country; neither does the reel. The pile of 100 summer days (scene 3) is a drawing: its count of
very hot days (3, then 13 after the pile moves two columns) is the drawing's own and is labelled an example. The body
temperature and the sponge are analogies and carry no number from the report.

Second cut (the owner, 11 Nov: "nice, still very fast, more animation, only temperature and heavy rain, real Earth
pictures, not much text"): five scenes, 66 s, one headline, one number and one small line each, a hold of 3 s or more
after each picture lands. The Earth is NASA's Blue Marble as a slowly turning globe, left in its natural colours (a
tint would be a warming map this reel does not have). The ring of 50 year-boxes lights only at the levels the report
gives (1; 5 at 1 C; 9 at 1.5 C; 14 at 2 C). The rain gauge (100, 107, 114) is an example built from the figure's
6.7 % and 14.0 %. The owner narrates over the silent reel; CUES are the moments inside a scene where his line
reaches a picture (seconds after the scene's start). The page
src/twodeg2_page/ draws any moment; src/onebit_twodeg2.py renders it.

Third cut (the owner, 12 Nov: the first slide's sentence was split above and below the globe, "many lines of text";
the law behind the rain needs "a more powerful animation than a simple cloud ... molecules of air and water vapour"):
six scenes, 76 s. The hook carries one sentence in one card under the globe (the event and its count at the warming
level, both with their 50 years), opens on the end state, runs back to the time before industry and counts up at
the narration's cues; the card names the level the ring is counting up to, from that level's first box on. A new
scene draws the law itself (Clausius-Clapeyron: air holds about 7 % more water vapour for each degree, IPCC AR6 WG1
chapter 8): a glass box of air over the sea in three dimensions, air molecules and water molecules, 100 water
molecules, 7 more leaving the sea with each degree (107, 114; a drawing on the same scale as the gauge, labelled an
example; the molecules' quicker motion in warmer air is exaggerated to be seen). The rain scene then lets that
vapour rise into a cloud that swells and rains into the gauge.

    python -I src/twodeg2.py        writes outputs/onebit/twodeg2/film.json and world.jpg, prints the clock
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image  # noqa: E402

import onebit  # noqa: E402
import onebit_compare  # noqa: E402
from onebit import fa  # noqa: E402

BUILD = onebit.ROOT / "outputs" / "onebit" / "twodeg2"
SCENES = ("hook", "mean", "pile", "vapour", "rain", "answer")
SECONDS = (15.0, 12.0, 16.0, 12.0, 12.0, 9.0)                            # 76 s: few words, a hold of 3 s or more after each picture lands
# moments inside a scene (seconds after its start) where the narration reaches a picture
CUES = dict(hook=dict(rewind=[0.9, 2.1], spin=[0.0, 2.6, -34.0],                              # the end state first, then back to the time before industry
                      rise=[[5.2, 7.0, 0.0, 1.0], [7.6, 8.8, 1.0, 1.5], [9.4, 10.8, 1.5, 2.0]]),   # the warming level: t0, t1, from, to
            mean=dict(spin=[0.4, 8.5, 50.0], body=3.6, mercury=[6.0, 8.4]),
            pile=dict(pulse=5.2, shift=[8.2, 11.4], record=11.8),
            vapour=dict(legend=[1.5, 2.4], warm=[[3.6, 5.2, 0.0, 1.0], [7.2, 8.8, 1.0, 2.0]]),     # the two labels beat (air, vapour); the box warms: t0, t1, from, to (degrees)
            rain=dict(fill=[[0.6, 2.6, 0.0, 100.0], [4.8, 6.4, 100.0, 106.7], [7.4, 9.0, 106.7, 114.0]]),
            answer=dict(question=2.6, follow=4.8))
# IPCC AR6 WG1 SPM, Figure SPM.6: (global warming level, best estimate, range, increase in intensity)
HEAT50 = ((1.0, 4.8, (2.3, 6.4), 1.2), (1.5, 8.6, (4.3, 10.7), 2.0), (2.0, 13.9, (6.9, 16.6), 2.7))   # times per 50 years, C hotter
RAIN10 = ((1.0, 1.3, (1.2, 1.4), 6.7), (1.5, 1.5, (1.4, 1.7), 10.5), (2.0, 1.7, (1.6, 2.0), 14.0))    # times per 10 years, % wetter
RAIN_PER_DEGREE = 7                                                      # B.2.4, percent
VAPOUR_PER_DEGREE = 7                                                    # chapter 8, executive summary: water-holding capacity, about 7 % per 1 C
VAPOUR = tuple(round(100 * (1 + VAPOUR_PER_DEGREE / 100) ** k) for k in range(3))   # water molecules in the drawn box: 100, 107, 114
PILE = (1, 2, 4, 7, 10, 13, 15, 14, 12, 9, 6, 4, 2, 1)                   # 100 summer days in 14 columns (a drawing)
PILE_SHIFT, PILE_LINE = 2, 12                                            # the pile moves 2 columns; «خیلی داغ» from column 12 on
LON0, LAT0, LAT1 = -127.0, -85.0, 85.0                                   # the world picture: 360 degrees from 127 W
GLOBE = dict(lat=24.0, lon=(44.0, 62.0))                                 # the globe looks at 24 N and turns slowly from 44 E to 62 E (Iran in view)


def dec(v: float) -> str:
    return fa(f"{v:.1f}".rstrip("0").rstrip(".")).replace(".", "٫")


TILES = ("https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/BlueMarble_ShadedRelief_Bathymetry/default/2004-08-01/500m/"
         "2/{row}/{col}.jpeg")                                           # level 2: 72 degrees a tile of 512 px, 5 columns, 3 rows from 90 N


def world_from_tiles(h: int) -> Image.Image:
    """The same Blue Marble layer from NASA GIBS's static tiles (the map service timed out on 12 Nov 2026)."""
    import io
    import urllib.request
    px = 512 / 72.0                                                      # pixels a degree
    mosaic = Image.new("RGB", (5 * 512, 3 * 512))
    for row in range(3):
        for col in range(5):
            with urllib.request.urlopen(TILES.format(row=row, col=col), timeout=120) as r:
                mosaic.paste(Image.open(io.BytesIO(r.read())).convert("RGB"), (col * 512, row * 512))
    band = mosaic.crop((0, round((90 - LAT1) * px), round(360 * px), round((90 - LAT0) * px)))   # 180 W to 180 E, LAT1 to LAT0
    cut = round((LON0 + 180) * px)                                       # the picture starts at LON0
    rolled = Image.new("RGB", band.size)
    rolled.paste(band.crop((cut, 0, band.width, band.height)), (0, 0))
    rolled.paste(band.crop((0, 0, cut, band.height)), (band.width - cut, 0))
    return rolled.resize((round(h * 360 / (LAT1 - LAT0)), h), Image.LANCZOS)


def world() -> Path:
    """NASA Blue Marble of the whole Earth, two GIBS maps stitched so that 53 E is in the middle (or the same layer's tiles)."""
    out = BUILD / "world.jpg"
    if not out.exists():
        h = 782
        wa, wb = round(h * (180 - LON0) / (LAT1 - LAT0)), round(h * (LON0 + 180) / (LAT1 - LAT0))
        try:
            a = onebit_compare.fetch_bm(BUILD / "bm_a.jpg", LON0, 180.0, LAT0, LAT1, wa)
            b = onebit_compare.fetch_bm(BUILD / "bm_b.jpg", -180.0, LON0, LAT0, LAT1, wb)
            ia = Image.open(a).convert("RGB")
            ib = Image.open(b).convert("RGB").resize((wb, ia.height))
            im = Image.new("RGB", (ia.width + ib.width, ia.height))
            im.paste(ia, (0, 0))
            im.paste(ib, (ia.width, 0))
        except OSError as err:                                           # urllib's errors are OSErrors
            print("GIBS map service failed (", err, "): using the layer's tiles")
            im = world_from_tiles(h)
        im.save(out, quality=92)
    return out


def pile_count(shift: int) -> int:
    return sum(n for c, n in enumerate(PILE) if c + shift >= PILE_LINE)


def words() -> dict:
    Z = "\u200c"
    scene = dict(
        hook=("فقط ۲ درجه گرم‌تر؟ // {خب که چی؟}", ""),
        mean=("این ۲ درجه، // {میانگینِ کلِ زمین} است", "شب و روز، تابستان و زمستان، خشکی و دریا"),
        pile=("تپه فقط کمی جابه‌جا می‌شود؛ // روزهای خیلی داغ {چند برابر}", "مثال: ۱۰۰ روزِ تابستان، هر دایره یک روز"),
        vapour=("هوای گرم‌تر، // {آبِ بیشتری} برمی‌دارد", f"هر درجه گرم‌تر: جا برای حدودِ {fa(VAPOUR_PER_DEGREE)}٪ بخارِ بیشتر"),
        rain=(f"بارانِ خیلی شدید: // هر درجه، {{حدودِ {fa(RAIN_PER_DEGREE)}٪ سنگین‌تر}}", ""),
        answer=("۲ درجه یعنی // {تبِ زمین}", "عددها در مقایسه با ۱۸۵۰ تا ۱۹۰۰"))
    land = "روی خشکی‌ها"
    levels = [dict(g=0.0, n=1, line="قبل از دورانِ صنعتی: ۱ بار در ۵۰ سال", note=f"{land}؛ در مقایسه با ۱۸۵۰ تا ۱۹۰۰")]
    for g, n, r, _ in HEAT50:                                            # the figure's medians and the 5-95 % range of its models (CMIP6)
        levels.append(dict(g=g, n=round(n), line=f"با {dec(g)} درجه: حدودِ {fa(round(n))} بار در ۵۰ سال",
                           note=f"{land}؛ بازه‌ی مدل‌ها: {dec(r[0])} تا {dec(r[1])} بار"))
    return dict(
        scenes=scene, pill="۲ درجه یعنی چه؟", source="IPCC AR6 WG1 (2021), SPM",
        hook=dict(levels=levels, event="گرمای شدیدی که هر ۵۰ سال یک بار می‌آمد"),
        vapour=dict(counts=list(VAPOUR), air=58, faster=0.16, launch=1.1, yaw=[-24.0, 7.0, 13.0], pitch=15.0,
                    chip=["قبل از گرمایش"] + [f"{fa(k)} درجه گرم‌تر" for k in (1, 2)], water="بخارِ آب", unit="مولکول", gas="هوا", sea="دریا", tag="مثال",
                    source="Clausius–Clapeyron · IPCC AR6 WG1, Ch. 8"),
        mean=dict(tag="تشبیه: دمای بدن", marks=[dict(v=37, label="۳۷: عادی"), dict(v=39, label="۳۹: تب")]),
        pile=dict(chip="خیلی داغ", days="روز", tag="مثال", cold="خنک‌تر", hot="داغ‌تر", xaxis="دمای روز", yaxis="احتمال (روز از ۱۰۰)",
                  yticks=[dict(v=5, label="۵"), dict(v=10, label="۱۰"), dict(v=15, label="۱۵")], record="داغ‌تر از همه‌ی روزهای قبل"),
        rain=dict(marks=[dict(v=100.0, label="قبل از صنعتی: ۱۰۰"), dict(v=100.0 + RAIN10[0][3], label=f"با ۱ درجه: {fa(round(100 + RAIN10[0][3]))}"),
                         dict(v=100.0 + RAIN10[2][3], label=f"با ۲ درجه: {fa(round(100 + RAIN10[2][3]))}")],
                  tag="مثال", foot="بارانِ سنگینی که هر ۱۰ سال یک بار می‌آمد؛ روی خشکی‌ها"),
        answer=dict(question=["در شهرِ شما کدام را", "بیشتر حس کرده‌اید:", "گرما یا بارانِ شدید؟"],
                    follow="این را برای کسی بفرستید که می‌گوید ۲ درجه چیزی نیست"),
    )


def film() -> dict:
    w = words()
    starts = [sum(SECONDS[:i]) for i in range(len(SCENES))]
    order = list(range(50))
    random.Random(7).shuffle(order)                                      # which year-boxes of the ring light first (a drawing, not dates)
    assert [lv["n"] for lv in w["hook"]["levels"]] == [1, 5, 9, 14]
    assert list(VAPOUR) == [100, 107, 114] == [round(m["v"]) for m in w["rain"]["marks"]]      # the box and the gauge share one scale
    assert all(b[0] >= a[1] for a, b in zip(CUES["hook"]["rise"], CUES["hook"]["rise"][1:])) and CUES["hook"]["rewind"][1] < CUES["hook"]["rise"][0][0]
    for k, n in zip(SCENES, SECONDS):                                    # every scene holds 3 s or more after its last cue
        last = max([c[1] for key in ("rise", "warm", "fill") for c in CUES[k].get(key, [])] + [0.0])
        assert n - last >= 3.0, (k, n, last)
    assert (pile_count(0), pile_count(PILE_SHIFT)) == (3, 13) and sum(PILE) == 100
    assert [round(m["v"], 1) for m in w["rain"]["marks"]] == [100.0, 106.7, 114.0]
    return dict(
        fps=onebit.FPS, size=list(onebit.SIZES["reel"]), cover_t=12.0, cues=CUES,
        cuts=dict(a=dict(end=float(sum(SECONDS)), scenes=[dict(key=k, start=float(starts[i]), length=float(SECONDS[i]),
                  title=w["scenes"][k][0], small=w["scenes"][k][1], source=w.get(k, {}).get("source", w["source"]))
                  for i, k in enumerate(SCENES)])),
        colours=dict(paper="#F3ECE1", ink="#2E2118", mark="#A03129", land="#E2D8C8", wet="#1c5cab", dry="#8c5a2b", pale="#d8cdbb"),
        pill=w["pill"], source=w["source"], hook=dict(w["hook"], order=order), mean=w["mean"], vapour=w["vapour"],
        pile=dict(w["pile"], cols=list(PILE), shift=PILE_SHIFT, line=PILE_LINE),
        rain=w["rain"], answer=w["answer"],
        map=dict(file="world.jpg", lon0=LON0, lat0=LAT0, lat1=LAT1), globe=GLOBE,
    )


def main() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    world()
    data = film()
    (BUILD / "film.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    c = data["cuts"]["a"]
    print(f"{c['end']} s, {round(c['end'] * onebit.FPS)} frames:", ", ".join(f"{s['key']} {s['start']:g}" for s in c["scenes"]))
    print("saved", BUILD / "film.json")


if __name__ == "__main__":
    main()
