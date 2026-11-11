"""«۲ درجه گرم‌تر، یعنی چه؟» (twodeg2_fa): the words, numbers and clock of the reel that explains a global mean.

Iranian viewers read "2 degrees of global warming" as "a summer of 40 becomes 42" (the owner, 11 Nov 2026). The reel
answers with how often extremes come. Every number is from the IPCC AR6 Working Group I Summary for Policymakers
(2021, doi:10.1017/9781009157896.001), read in the report's own text on 11 Nov 2026:

    Figure SPM.6, hot temperature extremes over land, against 1850-1900 (a climate without human influence):
        50-year event, times per 50 years: 4.8 (2.3-6.4) at 1 C, 8.6 (4.3-10.7) at 1.5 C, 13.9 (6.9-16.6) at 2 C;
        hotter by 1.2, 2.0 and 2.7 C.
    Figure SPM.6, heavy 1-day precipitation over land, 10-year event: 1.3 (1.2-1.4), 1.5 (1.4-1.7), 1.7 (1.6-2.0) times;
        wetter by 6.7, 10.5 and 14.0 %.
    Figure SPM.6, agricultural and ecological droughts in drying regions, 10-year event: 1.7 (0.7-4.1), 2.0 (1.0-5.1),
        2.4 (1.3-5.8) times.
    B.2.1  the land surface warms more than the ocean surface, likely 1.4 to 1.7 times more.
    B.2.3  in some mid-latitude and semi-arid regions the hottest days warm at about 1.5 to 2 times the rate of
           global warming.
    B.2.4  extreme daily precipitation intensifies by about 7 % for each 1 C of global warming.

The report names no country; neither does the reel. The pile of 100 summer days (scene 3) is a drawing: its count of
very hot days (3, then 13 after the pile moves two columns) is the drawing's own and is labelled an example. The body
temperature and the sponge are analogies and carry no number from the report.

The clock is the narration script's (seven lines, 80 s; the owner narrates over the silent reel). The page
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
SCENES = ("hook", "mean", "pile", "heat", "rain", "drought", "answer")
SECONDS = (9.0, 13.0, 13.0, 15.0, 12.0, 9.0, 9.0)                       # the script's lines: 80 s
# IPCC AR6 WG1 SPM, Figure SPM.6: (global warming level, best estimate, range, increase in intensity)
HEAT50 = ((1.0, 4.8, (2.3, 6.4), 1.2), (1.5, 8.6, (4.3, 10.7), 2.0), (2.0, 13.9, (6.9, 16.6), 2.7))   # times per 50 years, C hotter
RAIN10 = ((1.0, 1.3, (1.2, 1.4), 6.7), (1.5, 1.5, (1.4, 1.7), 10.5), (2.0, 1.7, (1.6, 2.0), 14.0))    # times per 10 years, % wetter
DRY10 = ((1.0, 1.7, (0.7, 4.1)), (1.5, 2.0, (1.0, 5.1)), (2.0, 2.4, (1.3, 5.8)))                      # times per 10 years
LAND_OCEAN = (1.4, 1.7)                                                  # B.2.1
HOTTEST_DAYS = (1.5, 2.0)                                                # B.2.3
RAIN_PER_DEGREE = 7                                                      # B.2.4, percent
PILE = (1, 2, 4, 7, 10, 13, 15, 14, 12, 9, 6, 4, 2, 1)                   # 100 summer days in 14 columns (a drawing)
PILE_SHIFT, PILE_LINE = 2, 12                                            # the pile moves 2 columns; «خیلی داغ» from column 12 on
LON0, LAT0, LAT1 = -127.0, -85.0, 85.0                                   # the world map: 360 degrees from 127 W (Iran in the middle)


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
    h1, h15, h2 = HEAT50
    scene = dict(
        hook=("۲ درجه گرم‌تر؛ یعنی ۴۰ می‌شود // ۴۲ و {تمام؟ نه.}", "گرمای شدیدی که هر ۵۰ سال یک بار می‌آمد:"),
        mean=("این ۲ درجه دمای شهرِ شما نیست؛ // {میانگینِ کلِ زمین} است", "شب و روز، تابستان و زمستان، خشکی و اقیانوس"),
        pile=("کلِ تپه کمی جابه‌جا می‌شود؛ // روزهای خیلی داغ {چند برابر}", "مثال: ۱۰۰ روزِ تابستان، هر دایره یک روز"),
        heat=(f"گرمای ۵۰ساله: {{حدودِ {fa(round(h2[1]))} بار}} // و نزدیکِ ۳ درجه داغ‌تر", "روی خشکی‌ها، با ۲ درجه گرمایش"),
        rain=(f"بارانِ خیلی شدید: // هر درجه، {{حدودِ {fa(RAIN_PER_DEGREE)}٪ شدیدتر}}", "هوای گرم‌تر، آبِ بیشتری برمی‌دارد"),
        drought=(f"خشکسالیِ ۱۰ساله: // با ۲ درجه، {{حدودِ {dec(DRY10[2][1])} بار}}", "در مناطقی که رو به خشکی‌اند"),
        answer=("۲ درجه یعنی // {تبِ زمین}", "عددها نسبت به ۱۸۵۰ تا ۱۹۰۰ است"))
    return dict(
        scenes=scene, pill="۲ درجه یعنی چه؟", source="IPCC AR6 WG1 (2021), SPM",
        hook=dict(strips=[dict(label="قبل از دورانِ صنعتی", count="۱ بار در ۵۰ سال", n=1, range=""),
                          dict(label="با ۱ درجه گرمایش، که گذشته‌ایم", count=f"حدودِ {fa(round(h1[1]))} بار", n=round(h1[1]),
                               range=f"بازه‌ی برآورد: {dec(h1[2][0])} تا {dec(h1[2][1])} بار"),
                          dict(label="با ۲ درجه گرمایش", count=f"حدودِ {fa(round(h2[1]))} بار", n=round(h2[1]),
                               range=f"بازه‌ی برآورد: {dec(h2[2][0])} تا {dec(h2[2][1])} بار")],
                  key="هر خانه یک سال؛ قرمز: سالِ گرمای شدید", base="روی خشکی‌ها؛ مبنا: ۱۸۵۰ تا ۱۹۰۰"),
        mean=dict(map_chip="میانگینِ همه‌جا، در کلِ سال", body=("دمای بدن", "۳۷: عادی", "۳۹: تب"), analogy="تشبیه",
                  land=("اقیانوس", "خشکی"), land_note=f"خشکی {dec(LAND_OCEAN[0])} تا {dec(LAND_OCEAN[1])} برابرِ اقیانوس گرم می‌شود"),
        pile=dict(chip="خیلی داغ", days="روز", tag="مثال", cold="خنک‌تر", hot="داغ‌تر", before="قبل", after="بعد از کمی گرم شدن"),
        heat=dict(tiles=[dict(n="۱", label="قبل از صنعتی", range=""),
                         dict(n=fa(round(h1[1])), label="با ۱ درجه", range=f"{dec(h1[2][0])} تا {dec(h1[2][1])}"),
                         dict(n=fa(round(h2[1])), label="با ۲ درجه", range=f"{dec(h2[2][0])} تا {dec(h2[2][1])}")],
                  unit="بار در ۵۰ سال (زیرِ هر عدد: بازه‌ی برآورد)", hotter_title="و هر بار داغ‌تر:",
                  hotter=[dict(label=f"با {dec(g)} درجه", value=f"{dec(i)} درجه", v=i) for g, _, _, i in HEAT50],
                  note=f"بعضی مناطقِ نیمه‌خشک: داغ‌ترین روزها {dec(HOTTEST_DAYS[0])} تا {dec(HOTTEST_DAYS[1])} برابرِ میانگینِ زمین"),
        rain=dict(bars=[dict(label=f"با {dec(g)} درجه", value=f"{dec(w)}٪", v=w, times=f"{dec(t)} بار") for g, t, _, w in RAIN10],
                  title="بارانِ سنگینِ ۱۰ساله، روی خشکی‌ها", unit="چقدر پرآب‌تر، و چند بار در ۱۰ سال"),
        drought=dict(rows=[dict(label="قبل از صنعتی", value="۱ بار", v=1.0, lo=1.0, hi=1.0)] +
                          [dict(label=f"با {dec(g)} درجه", value=f"{dec(t)} بار", v=t, lo=r[0], hi=r[1]) for g, t, r in DRY10],
                     unit="چند بار در ۱۰ سال؛ خطِ نازک: بازه‌ی برآورد", vmax=6.0),
        answer=dict(rows=["گرمای شدید: چند برابر", "بارانِ سیل‌آسا: سنگین‌تر", "خشکسالی: بیشتر"],
                    question=["در شهرِ شما", "کدام را بیشتر", "حس کرده‌اید؟"],
                    follow="این را برای کسی بفرستید که می‌گوید ۲ درجه چیزی نیست"),
    )


def film() -> dict:
    w = words()
    starts = [sum(SECONDS[:i]) for i in range(len(SCENES))]
    rnd = random.Random(7)
    for s in w["hook"]["strips"]:
        s["hot"] = sorted(rnd.sample(range(50), s["n"]))                # the hot years, scattered over the 50 (a drawing, not dates)
    assert [s["n"] for s in w["hook"]["strips"]] == [1, 5, 14]
    assert (pile_count(0), pile_count(PILE_SHIFT)) == (3, 13) and sum(PILE) == 100
    return dict(
        fps=onebit.FPS, size=list(onebit.SIZES["reel"]), cover_t=8.6,
        cuts=dict(a=dict(end=float(sum(SECONDS)), scenes=[dict(key=k, start=float(starts[i]), length=float(SECONDS[i]),
                  title=w["scenes"][k][0], small=w["scenes"][k][1]) for i, k in enumerate(SCENES)])),
        colours=dict(paper="#F3ECE1", ink="#2E2118", mark="#A03129", land="#E2D8C8", wet="#1c5cab", dry="#8c5a2b", pale="#d8cdbb"),
        pill=w["pill"], source=w["source"], hook=w["hook"], mean=w["mean"],
        pile=dict(w["pile"], cols=list(PILE), shift=PILE_SHIFT, line=PILE_LINE),
        heat=w["heat"], rain=w["rain"], drought=w["drought"], answer=w["answer"],
        land_ocean=list(LAND_OCEAN), map=dict(file="world.jpg", lon0=LON0, lat0=LAT0, lat1=LAT1),
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
