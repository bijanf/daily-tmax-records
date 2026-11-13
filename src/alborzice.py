"""«یخچال‌های البرز» (alborzice_fa): how much white is left on Damavand and Alam-Kuh at the end of summer.

A narrated reel (the owner's recording arrives later). The numbers are the measured white (clean snow and ice above
the zone height, square kilometres, end of summer, Landsat 4-9 classified by USGS-sourced scenes, Sentinel-2 for the
ground) of data/alborzice/series.json, written by the analysis scripts; pictures come from data/alborzice/pics/
(dam_<year>.jpg, 1080x1920; takht_<year>.jpg, 1080x1080). What is missing is replaced IN THE BUILD FOLDER by a plain
placeholder (never in data/). Without series.json a DRAFT series (the numbers of the brief) is used and says so.

The clock: a scene is 0.3 s lead + voice + 0.5 s tail. The voice is the owner's, from data/alborzice/voice/manifest.json
({"pieces": [{"scene": "hook", "seconds": 3.2}, ...]}) or an estimate. Every event of a scene is a FRACTION of its length,
so the film re-times itself when the manifest changes. The page src/alborzice_page/ draws any moment from film.json.

    python -I src/alborzice.py          writes outputs/onebit/alborzice/film.json and the pictures, prints the clock
"""

from __future__ import annotations

import json
import shutil
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "alborzice"
BUILD = ROOT / "outputs" / "onebit" / "alborzice"
FONTS = ROOT / "data" / "fonts"
SCENES = ("hook", "face1", "dam", "takht", "mech", "budget", "thr", "fut", "close")
VOICE = dict(hook=3.0, face1=4.5, dam=8.5, takht=12.5, mech=15.5, budget=12.0, thr=11.5, fut=8.0, close=9.5)   # estimates, seconds
LEAD, TAIL = 0.3, 0.5
LAST_PY = 1405                                           # the film shows every measured summer, the newest one too
FPS = 30

DRAFT = dict(
    damavand={1987: 2.65, 1988: 2.42, 1989: 0.94, 1990: 0.42, 1991: 0.38, 1993: 1.34, 1994: 0.78, 1995: 1.48, 1997: 0.48,
              1998: 1.65, 1999: 1.13, 2000: 0.99, 2001: 0.29, 2002: 0.75, 2013: 1.28, 2016: 0.87, 2017: 1.37, 2018: 0.37,
              2019: 1.16, 2020: 1.22, 2021: 0.69, 2022: 0.24, 2023: 0.30, 2024: 0.47, 2025: 0.31, 2026: 1.02},
    takht={1984: 0.94, 1987: 2.67, 1989: 1.28, 1990: 0.48, 1991: 0.45, 1992: 2.53, 1993: 1.49, 1995: 2.68, 1996: 2.10,
           1997: 0.80, 1999: 0.45, 2000: 0.26, 2002: 0.76, 2006: 0.65, 2009: 0.69, 2013: 0.38, 2016: 1.14, 2017: 1.29,
           2019: 0.60, 2020: 0.45, 2021: 0.16, 2022: 0.26, 2023: 0.19, 2024: 0.33, 2025: 0.12, 2026: 0.77})


def fa(v) -> str:
    """Persian digits and «٫» decimals."""
    return str(v).replace(".", "٫").translate(str.maketrans("0123456789%", "۰۱۲۳۴۵۶۷۸۹٪"))


def dec2(v: float) -> str:
    return fa(f"{v:.2f}")


# ───────────────────────────── the data ─────────────────────────────

def site(raw: dict | None, name: str) -> dict:
    """One site: years (sorted, with py), the medians of the two eras, the run of the lowest summers."""
    if raw is None:                                      # the draft
        years = [dict(year=y, py=y - 621, km2=v) for y, v in sorted(DRAFT[name].items())]
        raw = dict(zone_m=4000 if name == "damavand" else 3800, years=years, early=[1363, 1378], late=[1392, 1405],
                   run=[1401, 1404] if name == "damavand" else [1400, 1404])
    raw.setdefault("run", [1401, 1404] if name == "damavand" else [1400, 1404])      # the brief's run when the file names none
    years = sorted((dict(year=int(y["year"]), py=int(y.get("py", int(y["year"]) - 621)), km2=float(y["km2"])) for y in raw["years"]),
                   key=lambda y: y["year"])
    for e in ("early", "late"):
        med = statistics.median(y["km2"] for y in years if raw[e][0] <= y["py"] <= raw[e][1])
        raw.setdefault("median_" + e, round(med, 2))
    out = dict(raw, years=years)
    out["shown"] = [y for y in years if y["py"] <= LAST_PY]              # the summers the film draws
    assert all(any(y["py"] == p for y in out["shown"]) for p in raw["run"]), (name, "run summers are not in the data")
    return out


def series() -> tuple[dict, dict, dict, bool]:
    p = DATA / "series.json"
    if p.exists():
        s = json.loads(p.read_text(encoding="utf-8"))
        return site(s["damavand"], "damavand"), site(s["takht"], "takht"), s.get("facts", {}), False
    return site(None, "damavand"), site(None, "takht"), {}, True


TURNS = dict(dam=[0.55], takht=[0.25, 0.70], mech=[0.60], budget=[0.55], thr=[0.45], close=[0.45, 0.80])
# the fractions of a scene at which its picture turns to the narrator's next sentence (the headline steps above)


def on_camera() -> set:
    """The scenes in which the owner's video takes the place of the film (the voice manifest's face entries)."""
    p = DATA / "voice" / "manifest.json"
    if not p.exists():
        return set()
    return {q["scene"] for q in json.loads(p.read_text(encoding="utf-8"))["pieces"] if "face" in q}


def clock() -> tuple[dict, bool, dict]:
    """The voice's seconds per scene and, where the manifest gives the seconds at which the narrator starts each
    later sentence ("cues"), the moments the picture must turn."""
    p = DATA / "voice" / "manifest.json"
    voice, real, cues = dict(VOICE), False, {}
    if p.exists():
        for piece in json.loads(p.read_text(encoding="utf-8"))["pieces"]:
            voice[piece["scene"]] = float(piece["seconds"])
            if piece.get("cues"):
                assert len(piece["cues"]) == len(TURNS[piece["scene"]]), piece["scene"]
                cues[piece["scene"]] = [float(c) for c in piece["cues"]]
        real = True
    return voice, real, cues


# ───────────────────────────── the pictures ─────────────────────────────

def placeholder(path: Path, size: tuple[int, int], label: str) -> None:
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", size, (128, 114, 100))                           # flat grey-brown
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(str(FONTS / "vazirmatn" / "Vazirmatn-Black.ttf"), 260)
    box = d.textbbox((0, 0), label, font=f)
    d.text(((size[0] - box[2] - box[0]) / 2, (size[1] - box[3] - box[1]) / 2), label, font=f, fill=(226, 216, 200))
    im.save(path, quality=90)


def pictures(dam: dict, takht: dict) -> tuple[dict, list]:
    """Copy data/alborzice/pics/*.jpg into the build folder; a plain placeholder for each missing one."""
    BUILD.mkdir(parents=True, exist_ok=True)
    out, fake = {}, []
    for kind, s, size in (("dam", dam, (1080, 1920)), ("takht", takht, (1080, 1080))):
        out[kind] = {}
        for y in s["shown"]:
            name = f"{kind}_{y['year']}.jpg"
            src = DATA / "pics" / name
            if src.exists():
                shutil.copyfile(src, BUILD / name)
            else:
                placeholder(BUILD / name, size, fa(y["py"]))
                fake.append(name)
            out[kind][str(y["year"])] = name
    photo = DATA / "pics" / "close.jpg"                      # the closing photograph (Unsplash), when it is there
    if photo.exists():
        shutil.copyfile(photo, BUILD / "close.jpg")
        out["close"] = "close.jpg"
    return out, fake


# ───────────────────────────── the words ─────────────────────────────

def words(dam: dict, takht: dict, facts: dict) -> dict:
    SRC_PIC = "سفیدی: اندازه‌گیریِ خودمان از لندست (USGS) · زمین: سنتینل‌۲"
    dr, tr = dam["run"], takht["run"]
    takht_mid = ("سفیدیِ پایانِ تابستان: // {حدودِ ۷۰٪ کمتر} از ۳۰ تا ۴۰ سال پیش" if facts.get("takht_headline") == "number"
                 else "سفیدیِ پایانِ تابستان: // {کمتر از نصفِ} ۳۰ تا ۴۰ سال پیش")
    fut_low = "بیشترِ یخ می‌رود" if facts.get("fut_low") == "words" else "حدودِ ۷۰٪ یخ می‌رود"
    hook = "آخرِ تابستان، // چقدر {برف و یخ} // روی دماوند می‌مانَد؟"
    S = dict(
        hook=dict(heads=[(0, 1, hook)], smalls=[], sources=[(0, 1, SRC_PIC)]),
        face1=dict(heads=[(0, 1, hook)], smalls=[], sources=[(0, 1, SRC_PIC)]),
        dam=dict(heads=[(0, 0.55, "دماوند: // یک سال پربرف، یک سال {کم‌برف}"),
                        (0.55, 1, "چهار تابستانِ پیاپی، // جزوِ {کم‌ترین‌های} ۴۰ سال")],
                 smalls=[(0, 1, f"برف و یخِ سفید بالای {fa(dam['zone_m'])} متر، پایانِ تابستان")],
                 sources=[(0, 1, SRC_PIC)]),
        takht=dict(heads=[(0, 0.25, "علم‌کوه: // {بزرگ‌ترین} منطقه‌ی یخچالیِ ایران"), (0.25, 0.70, takht_mid),
                          (0.70, 1, "پنج تابستانِ پیاپی، // فقط {چند لکه}")],
                   smalls=[(0, 1, f"برف و یخِ سفید بالای {fa(takht['zone_m'])} متر · {fa(len(takht['years']))} تابستانِ اندازه‌گیری‌شده")],
                   sources=[(0, 1, SRC_PIC)]),
        mech=dict(heads=[(0, 0.60, "برفِ تازه مثلِ {آینه} است"), (0.60, 1, "{بازخوردِ مثبت}: // چرخه‌ای که خودش را تندتر می‌کند")],
                  smalls=[(0.60, 1, "«مثبت» یعنی تقویت‌کننده، نه خوب")], sources=[(0, 1, "Marshall & Miller 2020, The Cryosphere")]),
        budget=dict(heads=[(0, 0.55, "یخچال از برفی ساخته می‌شود // که از {تابستان بگذرد}"),
                           (0.55, 1, "یخچالِ علم‌کوه: هر سال // حدودِ {۲۰ سانتی‌متر آب} کمتر")],
                    smalls=[(0.55, 1, "میانگینِ یخچال، ۱۳۸۹ تا ۱۴۰۲ · اندازه‌گیری با لیزر و پهپاد")],
                    sources=[(0, 0.55, SRC_PIC), (0.55, 1, "Karimi & Sheshangosht 2025")]),
        thr=dict(heads=[(0, 0.45, "یکی از {۱۶ سیستمِ بزرگِ} زمین // که آستانه دارد"), (0.45, 1, "برآوردِ آستانه: // حدودِ {۲ درجه} گرمایش")],
                 smalls=[(0.70, 1, "پیش از آستانه هم یخ کم می‌شود")],
                 sources=[(0, 1, "Armstrong McKay et al. 2022, Science · WMO")]),
        fut=dict(heads=[(0, 1, "قفقاز و خاورمیانه // تا {سالِ ۲۱۰۰ میلادی}")], smalls=[(0, 1, "برآوردِ مدل‌ها نسبت به سالِ ۲۰۱۵ میلادی")],
                 sources=[(0, 1, "Rounce et al. 2023, Science")]),
        close=dict(heads=[], smalls=[], sources=[(0, 1, "عکس: Arshia Jafari · Unsplash")]),
    )
    labels = dict(
        hook=["تابستانِ ۱۴۰۴"],
        face1=["بیژن فلاح", "پژوهشگرِ اقلیم", "جوابش را از ۴۰ سال عکسِ ماهواره درآوردم."],
        dam=["تابستانِ ۱۴۰۴", "کیلومترمربع سفیدی", f"{fa(dr[0])} تا {fa(dr[1])}"],
        takht=["علم‌کوه", "تخت‌سلیمان · ۱۱۵ کیلومتر غربِ دماوند", "تابستانِ ۱۴۰۴",
               f"میانه‌ی {fa(takht['early'][0])} تا {fa(takht['early'][1])}", f"میانه‌ی {fa(takht['late'][0])} تا {fa(takht['late'][1])}",
               f"{fa(tr[0])} تا {fa(tr[1])}"],
        mech=["برفِ تازه", "یخِ تیره و کثیف", "۹ از ۱۰ برمی‌گردد", "۱ از ۱۰ برمی‌گردد", "حدودِ ۹۰٪", "گاهی فقط ۱۰٪",
              "سفیدیِ کمتر", "گرمای بیشتر", "ذوبِ بیشتر"],
        budget=["تابستانِ ۱۳۷۴", "برفی که از تابستان گذشت", "این سال‌ها: تقریباً هیچ", "۲۰ سانتی‌متر"],
        thr=["یخچال‌های کوهستان", "الان: حدودِ ۱٫۴ درجه", "بازه‌ی برآورد: ۱٫۵ تا ۳"],
        fut=["انتشارِ کم", "انتشارِ زیاد", fut_low, "تقریباً همه"],
        close=["با هر دهمِ درجه گرمایش، // یخِ بیشتری از کوه‌ها آب می‌شود.", "این را برای کسی بفرستید // که {دماوند} را دوست دارد",
               "دنبال کنید: // هر هفته، آب و اقلیمِ ایران با داده"])
    return dict(scenes=S, labels=labels, tag="یخچال‌های البرز", fut_low=fut_low)


LAST = dict(hook=0.0, face1=0.27, dam=0.66, takht=0.78, mech=0.72, budget=0.80, thr=0.76, fut=0.62, close=0.86)   # when each scene's last picture has landed (fraction)


def reading(w: dict, k: str, length: float) -> tuple[float, bool]:
    """The reading rule of src/onebit_reading.py: 1 s + (headlines and small lines in full + labels at half) / 2.5 words a second."""
    from onebit_reading import weight
    sc = w["scenes"][k]
    full = sum(weight(h[2]) for h in sc["heads"]) + sum(weight(s[2]) for s in sc["smalls"])
    if k in ("face1", "close"):                                           # the overlay texts are the narrator's own lines: full weight
        full += sum(weight(x) for x in w["labels"][k] if k == "close" or x == w["labels"][k][-1])
        half = 0.0 if k == "close" else sum(weight(x) for x in w["labels"][k][:-1])
    else:
        half = sum(weight(x) for x in w["labels"][k])
    need = max(1.0 + (full + 0.5 * half) / 2.5, LAST[k] * length + 3.0)               # twodeg2's rule: 3 s after the last picture lands
    return need, length >= need - 0.25


# ───────────────────────────── the film ─────────────────────────────

def film() -> dict:
    dam, takht, facts, draft = series()
    voice, real, cues = clock()
    lengths = {k: round(round((LEAD + voice[k] + TAIL) * FPS) / FPS, 4) for k in SCENES}   # whole frames, so overlay frame i is video frame i
    starts, t = {}, 0.0
    for k in SCENES:
        starts[k] = round(t, 4)
        t += lengths[k]
    w = words(dam, takht, facts)
    pics, fake = pictures(dam, takht)
    rd = {k: reading(w, k, lengths[k]) for k in SCENES}
    scenes = [dict(key=k, start=starts[k], length=lengths[k], voice=voice[k], heads=[dict(a=a, b=b, text=x) for a, b, x in w["scenes"][k]["heads"]],
                   smalls=[dict(a=a, b=b, text=x) for a, b, x in w["scenes"][k]["smalls"]],
                   sources=[dict(a=a, b=b, text=x) for a, b, x in w["scenes"][k]["sources"]]) for k in SCENES]
    for sc in scenes:                                                     # the picture turns when the narrator starts the sentence, a little before
        if sc["key"] in cues:
            knots = [[round(min(0.97, max(0.03, (LEAD + c - 0.25) / sc["length"])), 4), d] for c, d in zip(cues[sc["key"]], TURNS[sc["key"]])]
            assert all(a[0] < b[0] for a, b in zip(knots, knots[1:])), (sc["key"], knots)
            sc["warp"] = knots
    faces = on_camera()
    for prev, sc in zip(scenes, scenes[1:]):                              # no dissolve out of a scene that was the owner's video
        if prev["key"] in faces:
            sc["hard_in"] = True
    for k in SCENES:                                                      # sources are small lines inside the safe area, one per scene at a time
        for s in w["scenes"][k]["sources"]:
            assert len(s[2]) <= 70, (k, s[2])
    dr, tr = dam["run"], takht["run"]
    return dict(
        fps=FPS, size=[1080, 1920], cover_t=round(starts["hook"] + 0.25, 2), draft=draft, voice_from_manifest=real, placeholders=fake,
        cuts=dict(a=dict(end=round(t, 3), scenes=scenes)),
        colours=dict(paper="#F3ECE1", ink="#2E2118", mark="#A03129", land="#E2D8C8", bar="#5f86ad", past="#A3968A"),
        tag=w["tag"], labels=w["labels"], pics=pics,
        dam=dict(years=[dict(year=y["year"], py=y["py"], km2=y["km2"]) for y in dam["shown"]], run=dr, zone_m=dam["zone_m"],
                 median_early=dam["median_early"], median_late=dam["median_late"], early=dam["early"], late=dam["late"],
                 unit="کیلومترمربع سفیدی", chip="تابستانِ ", bracket=f"{fa(dr[0])} تا {fa(dr[1])}", years_in_data=len(dam["years"])),
        takht=dict(years=[dict(year=y["year"], py=y["py"], km2=y["km2"]) for y in takht["shown"]], run=tr, zone_m=takht["zone_m"],
                   median_early=takht["median_early"], median_late=takht["median_late"], early=takht["early"], late=takht["late"],
                   place="علم‌کوه", place2="تخت‌سلیمان · ۱۱۵ کیلومتر غربِ دماوند", chip="تابستانِ ", bracket=f"{fa(tr[0])} تا {fa(tr[1])}",
                   med_early=f"میانه‌ی {fa(takht['early'][0])} تا {fa(takht['early'][1])}", med_late=f"میانه‌ی {fa(takht['late'][0])} تا {fa(takht['late'][1])}"),
        face=dict(name="بیژن فلاح", role="پژوهشگرِ اقلیم", sub="جوابش را از ۴۰ سال عکسِ ماهواره درآوردم."),
        mech=dict(snow="برفِ تازه", ice="یخِ تیره و کثیف", back=["۹ از ۱۰ برمی‌گردد", "۱ از ۱۰ برمی‌گردد"], pct=["حدودِ ۹۰٪", "گاهی فقط ۱۰٪"],
                  ring=["سفیدیِ کمتر", "گرمای بیشتر", "ذوبِ بیشتر"], of="از ۱۰ برمی‌گردد",
                  snow_sink=5, ice_bounce=3),
        budget=dict(early_py=1374, late_py=1404, callout=["برفی که از تابستان گذشت", "این سال‌ها: تقریباً هیچ"], chip="تابستانِ ",
                    gauge=dict(from_py=1389, to_py=1402, step_cm=20, label="۲۰ سانتی‌متر"), xy=[0.60, 0.47]),
        thr=dict(dots=16, red=7, red_label="یخچال‌های کوهستان", now=1.4, now_label="الان: حدودِ ۱٫۴ درجه", mark=2.0, band=[1.5, 3.0],
                 band_label="بازه‌ی برآورد: ۱٫۵ تا ۳", max=3.0),
        fut=dict(cols=[dict(label="انتشارِ کم", keep=0.29, text=w["fut_low"]), dict(label="انتشارِ زیاد", keep=0.02, text="تقریباً همه")]),
        close=dict(sub=w["labels"]["close"][0], card=w["labels"]["close"][1], follow=w["labels"]["close"][2], cuts=[0.45, 0.80]),
        reading={k: dict(need=round(rd[k][0], 2), length=lengths[k], fits=rd[k][1]) for k in SCENES},
    )


def main() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    data = film()
    (BUILD / "film.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    c = data["cuts"]["a"]
    print("DRAFT series (no data/alborzice/series.json)" if data["draft"] else "series from data/alborzice/series.json",
          "| voice:", "manifest" if data["voice_from_manifest"] else "estimates")
    print(f"{c['end']} s, {round(c['end'] * FPS)} frames:", ", ".join(f"{s['key']} {s['start']:g}+{s['length']:g}" for s in c["scenes"]))
    for k, r in data["reading"].items():
        print(f"  {k:7s} length {r['length']:6.2f}  needs {r['need']:6.2f}  {'ok' if r['fits'] else 'TOO SHORT TO READ'}")
    if data["placeholders"]:
        print(f"{len(data['placeholders'])} placeholder pictures in the build folder (missing in data/alborzice/pics)")
    print("saved", BUILD / "film.json")


if __name__ == "__main__":
    main()
