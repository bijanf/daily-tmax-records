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
SCENES = ("hook", "mean", "pile", "rain", "answer")
SECONDS = (15.0, 12.0, 16.0, 14.0, 9.0)                                  # 66 s: few words, a hold of 3 s or more after each picture lands
# moments inside a scene (seconds after its start) where the narration reaches a picture
CUES = dict(hook=dict(rise=[[5.2, 7.0, 0.0, 1.0], [7.6, 8.8, 1.0, 1.5], [9.4, 10.8, 1.5, 2.0]]),   # the warming readout: t0, t1, from, to
            mean=dict(spin=[0.4, 8.5, 50.0], body=3.6, mercury=[6.0, 8.4]),
            pile=dict(pulse=5.2, shift=[8.2, 11.4], record=11.8),
            rain=dict(fill=[[0.8, 3.2, 0.0, 100.0], [6.0, 7.8, 100.0, 106.7], [9.0, 10.8, 106.7, 114.0]]),
            answer=dict(question=2.6, follow=4.8))
# IPCC AR6 WG1 SPM, Figure SPM.6: (global warming level, best estimate, range, increase in intensity)
HEAT50 = ((1.0, 4.8, (2.3, 6.4), 1.2), (1.5, 8.6, (4.3, 10.7), 2.0), (2.0, 13.9, (6.9, 16.6), 2.7))   # times per 50 years, C hotter
RAIN10 = ((1.0, 1.3, (1.2, 1.4), 6.7), (1.5, 1.5, (1.4, 1.7), 10.5), (2.0, 1.7, (1.6, 2.0), 14.0))    # times per 10 years, % wetter
RAIN_PER_DEGREE = 7                                                      # B.2.4, percent
PILE = (1, 2, 4, 7, 10, 13, 15, 14, 12, 9, 6, 4, 2, 1)                   # 100 summer days in 14 columns (a drawing)
PILE_SHIFT, PILE_LINE = 2, 12                                            # the pile moves 2 columns; «خیلی داغ» from column 12 on
LON0, LAT0, LAT1 = -127.0, -85.0, 85.0                                   # the world picture: 360 degrees from 127 W
GLOBE = dict(lat=24.0, lon=(44.0, 62.0))                                 # the globe looks at 24 N and turns slowly from 44 E to 62 E (Iran in view)


def dec(v: float) -> str:
    return fa(f"{v:.1f}".rstrip("0").rstrip(".")).replace(".", "٫")


def world() -> Path:
    """NASA Blue Marble of the whole Earth, two GIBS tiles stitched so that 53 E is in the middle."""
    out = BUILD / "world.jpg"
    if not out.exists():
        h = 782
        wa, wb = round(h * (180 - LON0) / (LAT1 - LAT0)), round(h * (LON0 + 180) / (LAT1 - LAT0))
        a = onebit_compare.fetch_bm(BUILD / "bm_a.jpg", LON0, 180.0, LAT0, LAT1, wa)
        b = onebit_compare.fetch_bm(BUILD / "bm_b.jpg", -180.0, LON0, LAT0, LAT1, wb)
        ia = Image.open(a).convert("RGB")
        ib = Image.open(b).convert("RGB").resize((wb, ia.height))
        im = Image.new("RGB", (ia.width + ib.width, ia.height))
        im.paste(ia, (0, 0))
        im.paste(ib, (ia.width, 0))
        im.save(out, quality=92)
    return out


def pile_count(shift: int) -> int:
    return sum(n for c, n in enumerate(PILE) if c + shift >= PILE_LINE)


def words() -> dict:
    Z = "\u200c"
    scene = dict(
        hook=("فقط ۲ درجه گرم‌تر؟ // {خب که چی؟}", "گرمای شدیدِ هر ۵۰ سال یک بار، روی خشکی‌ها"),
        mean=("این ۲ درجه، // {میانگینِ کلِ زمین} است", "شب و روز، تابستان و زمستان، خشکی و دریا"),
        pile=("تپه فقط کمی جابه‌جا می‌شود؛ // روزهای خیلی داغ {چند برابر}", "مثال: ۱۰۰ روزِ تابستان، هر دایره یک روز"),
        rain=(f"بارانِ خیلی شدید: // هر درجه، {{حدودِ {fa(RAIN_PER_DEGREE)}٪ سنگین‌تر}}", "هوای گرم‌تر، آبِ بیشتری برمی‌دارد"),
        answer=("۲ درجه یعنی // {تبِ زمین}", "عددها در مقایسه با ۱۸۵۰ تا ۱۹۰۰"))
    levels = [dict(g=0.0, n=1, count="۱ بار در ۵۰ سال", range="قبل از دورانِ صنعتی", read="قبل از صنعتی")]
    for g, n, r, _ in HEAT50:
        levels.append(dict(g=g, n=round(n), count=f"حدودِ {fa(round(n))} بار در ۵۰ سال", range=f"برآورد: از {dec(r[0])} تا {dec(r[1])} بار",
                           read=f"{dec(g)} درجه گرم‌تر"))
    return dict(
        scenes=scene, pill="۲ درجه یعنی چه؟", source="IPCC AR6 WG1 (2021), SPM",
        hook=dict(levels=levels, gauge="گرمایشِ زمین", scope=f"گرمای ۵۰{Z}ساله، روی خشکی‌ها"),
        mean=dict(tag="تشبیه: دمای بدن", marks=[dict(v=37, label="۳۷: عادی"), dict(v=39, label="۳۹: تب")]),
        pile=dict(chip="خیلی داغ", days="روز", tag="مثال", cold="خنک‌تر", hot="داغ‌تر", xaxis="دمای روز", yaxis="احتمال (روز از ۱۰۰)",
                  yticks=[dict(v=5, label="۵"), dict(v=10, label="۱۰"), dict(v=15, label="۱۵")], record="داغ‌تر از همه‌ی روزهای قبل"),
        rain=dict(marks=[dict(v=100.0, label="قبل از صنعتی: ۱۰۰"), dict(v=100.0 + RAIN10[0][3], label=f"با ۱ درجه: {fa(round(100 + RAIN10[0][3]))}"),
                         dict(v=100.0 + RAIN10[2][3], label=f"با ۲ درجه: {fa(round(100 + RAIN10[2][3]))}")],
                  tag="مثال", foot=f"بارانِ سنگینِ ۱۰{Z}ساله، روی خشکی‌ها"),
        answer=dict(question=["در شهرِ شما کدام را", "بیشتر حس کرده‌اید:", "گرما یا بارانِ شدید؟"],
                    follow="این را برای کسی بفرستید که می‌گوید ۲ درجه چیزی نیست"),
    )


def film() -> dict:
    w = words()
    starts = [sum(SECONDS[:i]) for i in range(len(SCENES))]
    order = list(range(50))
    random.Random(7).shuffle(order)                                      # which year-boxes of the ring light first (a drawing, not dates)
    assert [lv["n"] for lv in w["hook"]["levels"]] == [1, 5, 9, 14]
    assert (pile_count(0), pile_count(PILE_SHIFT)) == (3, 13) and sum(PILE) == 100
    assert [round(m["v"], 1) for m in w["rain"]["marks"]] == [100.0, 106.7, 114.0]
    return dict(
        fps=onebit.FPS, size=list(onebit.SIZES["reel"]), cover_t=12.0, cues=CUES,
        cuts=dict(a=dict(end=float(sum(SECONDS)), scenes=[dict(key=k, start=float(starts[i]), length=float(SECONDS[i]),
                  title=w["scenes"][k][0], small=w["scenes"][k][1]) for i, k in enumerate(SCENES)])),
        colours=dict(paper="#F3ECE1", ink="#2E2118", mark="#A03129", land="#E2D8C8", wet="#1c5cab", dry="#8c5a2b", pale="#d8cdbb"),
        pill=w["pill"], source=w["source"], hook=dict(w["hook"], order=order), mean=w["mean"],
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
