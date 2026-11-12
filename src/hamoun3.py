"""«آبِ هامون کجا رفت؟» (hamoun3_fa): the Hamoun lakes from space with the satellite picture as the whole frame,
in two parts without narration (p1 «آبِ هامون کجا رفت؟», p2 «وقتی هامون خالی است»).
The owner's direction (12 Nov 2026): the satellite animation is the hero and the bar chart the small one, a zoom-out
that shows the border of Iran and Afghanistan, catchy from the first second (the reference reels he sent are logged
in ~/Documents/instagram_research/reels.csv, "owner reference (12 Nov 2026)"). One 65-s film with all the scenes
was "too fast to read" (about 250 words on screen); he chose no narration, so the film became two parts with fewer
words, and every scene is sized by his reading rule (reading(), asserted).

This file is the film's data: it writes outputs/onebit/hamoun3/film.json (every string, every number, the clock, the
camera, the lines) and the pictures the page draws. src/hamoun3_page/ draws any moment from it and
src/onebit_hamoun3.py steps it frame by frame. Nothing new is measured here:

- The springs: the late-spring open water of the whole Hamoun, 1366-1405 (1987-2026), from hamounreel.areas()
  (hamoun.py's rule on get_hamoun.py's passes), 1381 (2002) without a trusted number (hamounreel.GAPS). The mean of
  the 39 measured springs and the counts on screen are asserted here exactly as in onebit_hamoun2.py (fact-checked
  8 Nov 2026): 12 of 12 springs of 1367-1378 above the mean, 5 of the 26 measured springs from 1379 above it, 10
  springs under 100 km2, 1405 about a third of the mean.
- The rain: the winter precipitation over the highlands that feed the lakes against the lakes' water, the springs of
  1366-1378 against 1379-1404, with hamoun_rain.py's own functions and its asserts (CRU TS 4.10 and ERA5).
- The words: the headlines, the small lines and the rows of dams are onebit_hamoun2.words() (reviewed); the new
  words are the place names, the hook and the "where" line (NEW below: they go through this film's fact check).
- The pictures: each clean spring's true colour (hamoun.colour, the fixed stretch of hamoun.display) on the picture
  grid; a spring without a clean picture (hamoun.NO_PICTURE) keeps its number and its bar, and the frame holds the
  last clean picture under a veil with a note, as in the first two films.
- The blue on the pictures: each measured spring's open water (hamoun.water_map: the share of water per pixel inside
  the lakes, the median over the spring's counted passes), drawn over the picture as a blue veil. The flood water is
  often so turbid that in true colour it looks like the sand around it (1384, 1386, 1388); the veil shows what the
  area on screen counts, and it gives the ten springs without a clean picture their own water. The unit under the
  number carries the same blue («کیلومترمربع آبِ باز»). 1381 (no trusted number) has no veil.
- What follows when the bed is dry (added 12 Nov 2026 at the owner's request): the dust storm of 22 September 2023
  in three passes of one day (NASA GIBS; the day NASA's Earth Observatory showed), NASA's sentence on dust since
  1999 and the people who sought medical help in that storm (news reports, quoted by NASA), what UNEP's 2006 report
  says of the dry years 1378-1383 (fishing, reeds, farming, emigration, deserted villages), and the dispute over the
  river's water (the 1973 treaty; the border clash of May 2023 as Al Jazeera reported it, both sides' words). No
  migration or unemployment figure: the censuses of 1385, 1390 and 1395 count about 388, 400 and 394 thousand people
  in Sistan's counties, and no source gives a traceable number.
- The clocks (part1(), part2(); a part has only its own scenes). Part 1 (43.7 s, a loop): the hook, a wipe from a
  full spring (1377, within 5 % of the wettest, said on screen) to this spring, from frame 0; the zoom-out with the
  border drawn; the forty springs one by one with the small bar chart; the whole river with the rain against the
  lake; the dams and the irrigated land in the river's order, with «سهمِ هر عامل محلِ بحث است» on screen; this spring
  against the mean and the next part's name; the wipe back to frame 0. Part 2 (46.4 s): the dust storm from frame 0
  under a question, the answer drawn on the bed; the people who sought medical help; the dry years; the dispute
  (the claim is Iran's, the Taliban deny it, who the three dead guards were, the cause not clear); this spring
  wiped back to the full lake of 1377 under the question and the call to send it on.
- The ground around the pictures and under the zoom-outs: Sentinel-2 cloudless 2016 by EOX (get_hamoun3.py), its
  tones matched once to the Landsat pictures' land (one mapping per band for the three ground pictures); the border
  and the river: Natural Earth 10 m (about 1 km accurate); the dams' places: Wikipedia's coordinates, checked on
  the pictures (the river bends at Kamal Khan; Kajaki and Lashkargah lie on the river's line).

The view: longitude and latitude as straight axes in units of the picture pixel; a view is (lon, lat of the frame's
centre, frame pixels per picture pixel). CLOSE shows the lakes at the pictures' own scale (about 143 m a pixel, the
frame 154 km wide), MID 2.5 times wider (the border, Zabol, the delta), WIDE 6 times wider (the whole river); DUST
and DUSTB hold the storm (inside the three passes' picture), DISP the lakes with the river across the frame.

Before rendering: python -I src/onebit_hamoun3_sweep.py (both parts every 0.25 s: the safe area, text on text,
strings of the other part).

    python -I src/hamoun3.py              # film.json and the pictures (cached pictures are kept)
    python -I src/hamoun3.py --pictures   # rebuild the pictures too
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

import get_hamoun as gh  # noqa: E402
import get_hamoun3 as g3  # noqa: E402
import hamoun  # noqa: E402
import hamoun_rain as rain  # noqa: E402
import hamounreel as reel  # noqa: E402  (the reviewed series: areas, GAPS, solar)
import onebit_hamoun2 as v2  # noqa: E402  (the reviewed words and the rounding on screen)
from onebit import fa  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "outputs" / "onebit" / "hamoun3"
FPS = 30
W, H = 1080, 1920
GW, GH = gh.PIC_SHAPE[1], gh.PIC_SHAPE[0]            # the picture grid: 1080 x 1240
LON0, LAT1 = gh.BOX[0], gh.BOX[3]                    # its west and north edges
NEAR_OFF = (200, 500)                                # the grid's corner inside near.jpg (px)
FEATHER = 120                                        # px: the pictures' edge blends into the ground over this width
WATER_RGB, WATER_ALPHA = (24, 104, 214), 0.62        # the measured open water's veil on the picture
BEFORE, NOW = 1998, 2026                             # the hook's two springs: 1377 (a full lake) and 1405

# the views: lon, lat of the frame's centre, frame pixels per picture pixel
CLOSE = (LON0 + 540 * gh.DLON, LAT1 - 809 * gh.DLAT, 0.78)   # the lakes between the headline and the spring's tag
MID = (61.45, 31.05, 0.40)
WIDE = (63.7, 32.0, 0.14)
DUST = (61.75, 30.45, 0.47)                          # the dust storm: the lakes at the top, the plume down the frame
DUSTB = (61.75, 30.60, 0.50)                         # the same storm a little closer (the camera never rests)
DISP = (61.85, 30.45, 0.40)                          # the dispute: the lakes on the left, the river across the frame
DRY = 2001                                           # the dry bed's picture (spring 1380: no open water)

# The two parts (12 Nov 2026: no narration; the owner found the 65-s cut "too fast to read", and it was: about 250
# words in 65 s against the 120 s his reading rule asks). Each part has its own scenes, each scene its own window
# (seconds); a scene that a part does not have is absent, never a zero-length window. reading() asserts the owner's
# rule (src/onebit_reading.py) on every scene.
def part1() -> dict:
    """«آبِ هامون کجا رفت؟»: the wipe and the border, the forty springs, the rain against the lake, the dams, this spring."""
    hook, run, why, dams, now = (0.0, 6.9), (6.9, 18.7), (18.7, 27.1), (27.1, 36.8), (36.8, 43.7)
    t0, s1, s2 = run[0] + 0.9, 0.30, 0.24                                 # 1366 at t0; 1366-1378 every s1, then s2
    spring_t = [round(t0 + s1 * k if k <= 12 else t0 + s1 * 13 + s2 * (k - 13), 3) for k in range(40)]
    assert spring_t[-1] + 0.5 < run[1]
    cues = dict(wipe=(0.0, 2.4), swap=3.2, border=(3.2, 4.1), labels=(3.4, 3.55, 3.7), t0=t0, spring_t=spring_t,
                river=(why[0] + 0.7, why[0] + 2.5), river_on=[(why[0] + 0.7, now[0] + 1.2)], card=why[0] + 1.6,
                pins=(dams[0] + 0.4, dams[0] + 1.3, dams[0] + 5.3, dams[0] + 6.0), leave=dams[0] + 4.0, hedge=dams[0] + 6.6,   # the irrigated land's three lines get 2.4 s before the camera leaves
                mid=[(2.6, run[0] + 0.9), (dams[0] + 4.0, now[0] + 1.2)],
                teaser=now[0] + 3.2, back=(now[1] - 0.7, now[1]))
    camera = [[0, "close", 1.0], [2.6, "close", 1.04], [3.7, "mid", 1.0], [run[0], "mid", 0.97], [run[0] + 0.9, "close", 1.0],
              [why[0], "close", 1.05], [why[0] + 1.6, "wide", 1.0], [dams[0] + 4.0, "wide", 0.97], [dams[0] + 5.1, "mid", 1.0],
              [now[0], "mid", 0.98], [now[0] + 1.2, "close", 1.0], [now[1] - 0.7, "close", 1.04], [now[1], "close", 1.0]]
    return dict(end=now[1], cover_t=0.0, scenes=dict(hook=hook, run=run, why=why, dams=dams, now=now), cues=cues, camera=camera)   # the cover: the full lake with its own year and number (half-way through the wipe the number of 1405 stands under the lake of 1377)


def part2() -> dict:
    """«وقتی هامون خالی است»: the dust storm, the people in it, the dry years, the dispute, the full lake and the question."""
    dust, health, lives, dispute, end2 = (0.0, 9.8), (9.8, 17.4), (17.4, 26.4), (26.4, 39.4), (39.4, 46.4)
    cues = dict(dframes=(-1.0, 0.4, 5.0), bed=(1.5, 2.1), wind=(2.4, 3.2), dsmall=4.2,
                notes=tuple(round(lives[0] + 1.4 + 1.0 * i, 2) for i in range(4)),
                boxes=(dispute[0] + 1.5, dispute[0] + 5.8), river_on=[(dispute[0] + 0.3, end2[0] + 1.2)],
                wipe2=(end2[0] + 0.5, end2[0] + 2.1), follow=end2[0] + 3.0)
    camera = [[0, "dust", 1.0], [health[1], "dustb", 1.0], [lives[0] + 1.3, "close", 1.0], [dispute[0], "close", 1.04],
              [dispute[0] + 1.3, "disp", 1.0], [end2[0], "disp", 1.03], [end2[0] + 1.2, "close", 1.0], [end2[1], "close", 1.04]]
    return dict(end=end2[1], cover_t=3.6, scenes=dict(dust=dust, health=health, lives=lives, dispute=dispute, end2=end2),
                cues=cues, camera=camera)


PLACES = dict(                                       # lon, lat
    zabol=(61.4878, 31.0339), kajaki=(65.1189, 32.3219), lashkargah=(64.369, 31.583), kamalkhan=(61.8834, 30.3240),
    chahnimeh=reel.PLACES["chahnimeh"],
    # where the map's words sit (each on its own side of the border, inside the frame's safe part in its view)
    iran_close=(61.31, 30.90), afg_close=(62.017, 31.137),
    border_end=(61.80, 30.86),                           # where the river reaches the border (the green band's end)
    iran_mid=(60.25, 31.75), afg_mid=(62.2, 32.2),
    iran_wide=(59.79, 33.3), afg_wide=(62.95, 34.21), pak_wide=(65.5, 28.3),
    kush=(65.84, 34.95), river_name=(63.2, 29.75),
    iran_dust=(60.643, 29.57), afg_dust=(62.48, 31.35), wind0=(61.144, 31.614), wind1=(61.501, 31.180), bed_name=(61.08, 30.30),
    iran_disp=(60.55, 31.05), afg_disp=(62.73, 31.60),
)

NEW = dict(                                          # this film's own words, as few as the pictures allow
    hook="آبِ {هامون} کجا رفت؟", spring="بهارِ {}", wet="از پُرآب‌ترین بهارها", this_spring="بهارِ امسال",
    unit_water="کیلومترمربع آبِ باز", mean_value="میانگین: {}",
    iran="ایران", afg="افغانستان", pak="پاکستان", zabol="زابل", river="رودِ هیرمند", lake="هامون",
    held="بدونِ تصویرِ صاف",
    # the rain against the lake: the reviewed numbers; what the two rows are, and the periods, are in the source line
    why="از ۱۳۷۹: بارش {کمی} کمتر، // آبِ هامون {خیلی} کمتر", rain_item="بارش", lake_item="آبِ هامون",
    less="{}٪ کمتر", less_range="{} تا {}٪ کمتر",
    dams="سدها و آبیاری، // {در دو سوی مرز}",
    pins=(("kajaki", "سدِ کجکی", "۱۳۳۲"), ("lashkargah", "کشاورزیِ آبی", "۶۲٪ بیشتر // از ۱۳۶۹ تا ۱۳۹۰"),
          ("kamalkhan", "سدِ کمال‌خان", "۱۴۰۰"), ("chahnimeh", "چاه‌نیمه‌ها", "۱۳۶۲")),
    share="سهمِ هر عامل محلِ بحث است",
    teaser=("قسمتِ بعد:", "وقتی هامون خالی است"),
    # the dust (NASA Earth Observatory, 28 Sep 2023, read 12 Nov 2026: the plume of 22 Sep 2023 "appears to emanate
    # from the ephemeral Hamun wetlands"; the Levar or "120-day wind"; "Since 1999, low water levels in the Hamun
    # wetlands have led to a marked increase in dust events originating there"; "More than 1,300 people in Iran's
    # Sistan and Baluchestan province sought medical attention for respiratory, heart, and other ailments, according
    # to news reports"; UNEP 2006: "the primary source of the dust plumes is the lakebed of the Hamoons"). The
    # headline asks; the answer is the name drawn on the bed, where the picture shows the plume begin.
    dust_head="این غبار از {کجا} می‌آید؟",
    dust_small="ناسا: از ۱۳۷۸، با کم‌آبیِ هامون، // به‌طورِ چشمگیری بیشتر شده",   # "a marked increase": not «خیلی»
    dust_date="۳۱ شهریور ۱۴۰۲", dust_hours=("ساعتِ ۹", "ساعتِ ۱۲", "ساعتِ ۱۳"), wind="بادِ ۱۲۰روزه", bed="بسترِ خشکِ هامون",
    health_head="بیش از {۱٬۳۰۰ نفر}",
    health_small="در مراکزِ درمانیِ سیستان و بلوچستان // همان روزها؛ گزارشِ رسانه‌ها، به نقلِ ناسا",
    # the dry years (UNEP 2006, History of Environmental Change in the Sistan Basin, read 12 Nov 2026: "the collapse of
    # the local economy during this latest drought period"; "fishing is not possible"; "caused damage to agriculture
    # in the delta"; "Loss of traditional livelihoods has resulted in emigration"; "local experts reported that more
    # than a hundred villages in the Saberi and Baringak region had been deserted" (January 2005). UNEP's drought is
    # "between 1999 and 2005" and ends with the floods of March 2005 (Esfand 1383); this film's own strip shows
    # spring 1384 full again: the Persian years are 1378 to 1383)
    lives_head="خشکسالیِ ۱۳۷۸ تا ۱۳۸۳: // {اقتصادِ محلی} فروپاشید", lives_small="گزارشِ سازمانِ ملل (۲۰۰۶)",
    lives_notes=("ماهیگیری ممکن نبود", "کشاورزی آسیب دید", "مهاجرت از منطقه", "بیش از ۱۰۰ روستای خالی، کنارِ هامون*"),
    lives_note="* به گفته‌ی کارشناسانِ محلی، دی ۱۳۸۳",
    # the dispute (Al Jazeera, 30 May 2023, read 12 Nov 2026: "at least two Iranian and one Afghan guard were killed";
    # "The reasons for the clashes are still unknown"; Iran's president "accused Afghanistan's Taliban rulers of
    # restricting the flow of water"; "The Taliban, which has denied the accusation"). Three things stay on screen:
    # the claim is Iran's, the Taliban deny it, the cause of the clash was not clear. Read again at the source for
    # the final check: "Both sides have accused each other of initiating the shooting in which at least two Iranian
    # and one Afghan guard were killed" (so the box says who the three were: a Persian reader takes «مرزبان» alone
    # for Iran's guards).
    dispute_head="۱۴۰۲: اختلاف بر سرِ // [آبِ هیرمند]",
    dispute_boxes=("ایران می‌گوید طالبان // جریانِ آب را محدود کرده‌اند؛ // طالبان رد می‌کنند",
                   "درگیریِ مرزی؛ دست‌کم ۳ مرزبان کشته شدند // (۲ ایرانی، ۱ افغانستانی) // علتش روشن نبود"),
    end_head="شما {هامونِ پُر} را // دیده‌اید؟", follow=("برای کسی بفرستید", "که هامون را می‌شناسد"),
    src_water="منبع: لندست (USGS)؛ مقایسه‌شده با آبِ سطحیِ JRC",
    src_map="زمینه: Sentinel-2 cloudless (EOX)؛ مرز و رود: Natural Earth",
    src_rain="بارشِ زمستان در بالادست (CRU، ERA5)؛ {} تا {} در برابرِ {} تا {}",
    src_dust="تصویرها و گزارش: ناسا (Terra، Suomi NPP، NOAA-20)",
    src_lives="منبع: برنامه‌ی محیط‌زیستِ ملل متحد (UNEP)؛ تصویر: لندست، بهارِ ۱۳۸۰",
    src_dispute="منبع: الجزیره، ۹ خرداد ۱۴۰۲",
)


def reading(words: dict, cuts: dict) -> None:
    """The owner's rule (src/onebit_reading.py, its weights imported) on every scene of both parts: a scene lasts at
    least 1 s + (headline, small line and sentences in full, labels at half weight) / 2.5 words a second, and at least
    3 s after its last string appears. Printed, and asserted."""
    import onebit_reading as rd
    W = words
    wt = lambda xs: sum(rd.weight(x) for x in xs)        # noqa: E731
    p1, p2 = cuts["p1"], cuts["p2"]
    s1, q1, s2, q2 = p1["scenes"], p1["cues"], p2["scenes"], p2["cues"]
    t13 = q1["spring_t"][13]
    tag = lambda y, n: [W["spring"].format(y), n, W["unit"]]   # noqa: E731
    pins = [x for _a, n, y in W["pins"] for x in (n, *y.split(" // "))]
    plan = [   # cut, scene, (from, to), in full, at half weight, when the last string appears
        ("p1", "hook", s1["hook"], [W["hook"]],
         [*tag("۱۳۷۷", "۴٬۰۷۰"), W["wet"], *tag("۱۴۰۵", "۵۶۰")[:2], W["this_spring"], W["iran"], W["afg"], W["zabol"], W["lake"]],
         q1["labels"][2] + 0.1),
        ("p1", "run, first headline", (s1["run"][0], t13), [W["era1"]], [*W["legend"], W["mean"]], s1["run"][0] + 0.3),
        ("p1", "run, second headline", (t13, s1["run"][1]), [W["era2"]], [W["held"]], t13),
        ("p1", "why", s1["why"], [W["why"], W["rain_item"], W["rain_less"], W["lake_item"], W["lake_less"]],
         [W["iran"], W["afg"], W["river"], W["lake"]], q1["card"] + 1.6),
        ("p1", "dams", s1["dams"], [W["dams"], W["share"]], [*pins, W["pak"]], q1["hedge"]),
        ("p1", "now", (s1["now"][0], q1["back"][0]), [W["now"], *W["teaser"]], [*tag("۱۴۰۵", "۵۶۰"), W["mean_value"]], q1["teaser"]),
        ("p2", "dust", s2["dust"], [W["dust_head"], *W["dust_small"].split(" // ")],
         [W["dust_date"], *W["dust_hours"], W["iran"], W["afg"], W["zabol"], W["bed"], W["wind"]], q2["dframes"][2] + 0.45),
        ("p2", "health", s2["health"], [W["health_head"], *W["health_small"].split(" // ")], [], s2["health"][0] + 0.3),
        ("p2", "lives", s2["lives"], [W["lives_head"], W["lives_small"]], [*W["lives_notes"], W["lives_note"]], q2["notes"][-1] + 0.2),
        ("p2", "dispute", s2["dispute"], [W["dispute_head"], *W["dispute_boxes"]], [W["iran"], W["afg"]], q2["boxes"][-1]),
        ("p2", "end", s2["end2"], [W["end_head"], *W["follow"]], tag("۱۳۷۷", "۴٬۰۷۰"), q2["follow"]),
    ]
    print("\nreading (words in full + labels at half weight; seconds the rule needs, seconds given):")
    total = {"p1": 0.0, "p2": 0.0}
    for cut, name, (a, b), full, half, last in plan:
        w = wt(full) + rd.LABELS * wt(half)
        need = max(rd.SETTLE + w / rd.WPS, last - a + rd.HOLD)
        total[cut] += w
        print(f"  {cut} {name:22s} {wt(full):5.1f} + {wt(half):4.1f}/2 words, last string at {last - a:4.1f} s -> "
              f"{need:4.1f} s needed, {b - a:4.1f} s given")
        assert b - a + 0.051 >= need, (cut, name, round(need, 2), round(b - a, 2))
    for cut in ("p1", "p2"):
        print(f"  {cut}: {total[cut]:.0f} weighted words in {cuts[cut]['end']:.1f} s ({total[cut] / cuts[cut]['end']:.2f} a second)")


def bars() -> list:
    """The forty springs, as hamounreel's timeline gives them (the reviewed series)."""
    a = reel.areas()
    assert list(a.index) == list(range(reel.FIRST, reel.LAST + 1)) and (reel.FIRST, reel.LAST) == (1987, 2026)
    return [dict(year=int(y), label=str(reel.solar(int(y))), km2=None if y in reel.GAPS else float(a.loc[y]))
            for y in range(reel.FIRST, reel.LAST + 1)]


def checked(b: list) -> dict:
    """The counts on screen, asserted as in onebit_hamoun2.Hamoun2.__init__ (the reviewed film)."""
    v = np.array([x["km2"] if x["km2"] is not None else np.nan for x in b], float)
    yrs = np.array([x["year"] for x in b])
    mean = float(np.nanmean(v))
    assert len(b) == 40 and np.isfinite(v).sum() == 39 and [x["year"] for x in b if x["km2"] is None] == [2002]
    assert 1560 < mean < 1570, mean
    era1 = (yrs >= 1988) & (yrs <= 1999)
    era2 = (yrs >= 2000) & np.isfinite(v)
    assert era1.sum() == 12 and (v[era1] > mean).all()
    assert era2.sum() == 26 and int((v[era2] > mean).sum()) == 5
    assert int((v < v2.NEAR_DRY).sum()) == 10 and all(yrs[v < v2.NEAR_DRY] >= 2000)
    assert 0.33 <= v[-1] / mean <= 0.38, v[-1] / mean                     # «حدودِ یک‌سومِ میانگین»
    return dict(v=v, mean=mean, vmax=float(np.nanmax(v)))


def rain_numbers(b: list) -> dict:
    """hamoun_rain.main()'s arithmetic on this computer's series, with its asserts (it reads the first film's
    timeline.json, which needs that film's Tehran outline; the numbers and the checks are the same)."""
    area = {x["year"]: x["km2"] for x in b if x["km2"] is not None}
    res = {}
    for name, p in (("cru", rain.monthly_cru()), ("era5", rain.monthly_era5())):
        w = rain.winters(p)
        ys = [y for y in range(1987, 2026) if y in w and y in area]
        P, A = np.array([w[y] for y in ys]), np.array([area[y] for y in ys])
        early = np.array([y <= 1999 for y in ys])
        med = float(np.median(P[early]))
        res[name] = dict(rain_share=float(P[~early].mean() / P[early].mean()),
                         wet_share=float(A[~early & (P >= med)].mean() / A[early & (P >= med)].mean()))
        res["lake_share"] = float(A[~early].mean() / A[early].mean())
        res["n_early"], res["n_late"] = int(early.sum()), int((~early).sum())
    assert res["n_early"] == 13 and res["n_late"] == 25, (res["n_early"], res["n_late"])
    assert 0.25 <= res["lake_share"] <= 0.27, res["lake_share"]                   # «۷۴٪ کمتر»
    assert 0.91 <= res["cru"]["rain_share"] <= 0.93 and 0.77 <= res["era5"]["rain_share"] <= 0.79
    assert 0.35 <= res["cru"]["wet_share"] <= 0.45 and 0.35 <= res["era5"]["wet_share"] <= 0.45
    less = sorted(round(100 * (1 - res[k]["rain_share"])) for k in ("cru", "era5"))
    assert less == [8, 23], less                                                  # «۸ تا ۲۳٪ کمتر» (the caption)
    assert round(100 * (1 - res["lake_share"])) == 74                             # «۷۴٪ کمتر»
    res["less"] = less
    return res


def match(src: np.ndarray, ref: np.ndarray, mask: np.ndarray) -> list:
    """Per band, the straight line (256 entries) that gives the ground picture the mean and the spread of the Landsat
    pictures on the land they share. A straight line keeps the ground's own colours in order (a curve fitted to this
    desert turned the mountains of the wide view orange)."""
    luts = []
    x = np.arange(256, dtype=np.float32)
    for b in range(3):
        s, r = src[..., b][mask], ref[..., b][mask]
        gain = float(np.clip(r.std() / max(s.std(), 1e-6), 0.6, 1.6))
        luts.append(np.clip(r.mean() + gain * (x - s.mean()), 0, 255).astype(np.uint8))
        print(f"  band {b}: ground {s.mean():.0f} +- {s.std():.0f}, pictures {r.mean():.0f} +- {r.std():.0f}, gain {gain:.2f}")
    return luts


def pictures(b: list, rebuild: bool) -> dict:
    """The springs' pictures (p<year>.jpg on the picture grid), the three ground pictures with matched tones, and the
    ring that blends a picture's edge into the ground."""
    from scipy import ndimage
    BUILD.mkdir(parents=True, exist_ok=True)
    clean = set(hamoun.years())
    assert {BEFORE, NOW} <= clean, "the hook's two springs have clean pictures"
    pics = {}
    for x in b:
        y = x["year"]
        if y not in clean:
            continue
        path = BUILD / f"p{y}.jpg"
        if rebuild or not path.exists():
            Image.fromarray(hamoun.display(hamoun.colour(y)["rgb"])).save(path, quality=92)
            print("  picture", y, flush=True)
        pics[y] = path.name
    waters = {}
    for x in b:                                                  # each measured spring's open water, as a blue veil
        y = x["year"]
        if x["km2"] is None:
            continue
        path = BUILD / f"w{y}.png"
        if rebuild or not path.exists():
            share = np.clip(np.nan_to_num(np.where(hamoun.lakes(), hamoun.water_map(y), 0.0)), 0, 1)
            share = ndimage.gaussian_filter(share, 0.8)
            rgba = np.zeros((GH, GW, 4), np.uint8)
            rgba[..., :3] = WATER_RGB
            rgba[..., 3] = (255 * WATER_ALPHA * share).astype(np.uint8)
            Image.fromarray(rgba, "RGBA").save(path)
            print(f"  water {y}: {share.sum() * 0.143 * 0.143:,.0f} km2 at the picture's pixel", flush=True)
        waters[y] = path.name
    # the tones: the ground (near.jpg) against the median of the clean pictures, on the land they share
    stack = np.stack([np.asarray(Image.open(BUILD / pics[y]).convert("RGB")) for y in sorted(pics)[::3]])
    ref = np.median(stack, axis=0).astype(np.float32)
    near = np.asarray(Image.open(g3.OUT / "near.jpg").convert("RGB"))
    ox, oy = NEAR_OFF
    assert near.shape[:2] == (2600, 1480) and abs(g3.GROUND["near"][0] + ox * gh.DLON - LON0) < 1e-9
    assert abs(g3.GROUND["near"][3] - oy * gh.DLAT - LAT1) < 1e-9
    sub = near[oy:oy + GH, ox:ox + GW].astype(np.float32)
    land = ~ndimage.binary_dilation(hamoun.lakes(), iterations=15)
    luts = match(sub, ref, land)
    ground = {}
    for name, (w, s, e, n, k) in g3.GROUND.items():
        im = np.asarray(Image.open(g3.OUT / f"{name}.jpg").convert("RGB"))
        out = np.stack([luts[c][im[..., c]] for c in range(3)], axis=-1)
        Image.fromarray(out).save(BUILD / f"{name}.jpg", quality=92)
        ground[name] = dict(file=f"{name}.jpg", w=w, s=s, e=e, n=n, k=k, px=[im.shape[1], im.shape[0]])
        if name == "near":
            near_adj = out
    d = np.minimum.reduce([np.arange(GW)[None, :] + 0 * np.arange(GH)[:, None], (GW - 1 - np.arange(GW))[None, :] + 0 * np.arange(GH)[:, None],
                           np.arange(GH)[:, None] + 0 * np.arange(GW)[None, :], (GH - 1 - np.arange(GH))[:, None] + 0 * np.arange(GW)[None, :]])
    p = np.clip(d / FEATHER, 0, 1)
    alpha = 1 - p * p * (3 - 2 * p)                                               # 1 at the edge, 0 inside
    ring = np.dstack([near_adj[oy:oy + GH, ox:ox + GW], (255 * alpha).astype(np.uint8)])
    Image.fromarray(ring, "RGBA").save(BUILD / "ring.png")
    err = np.abs(np.stack([luts[c][near[oy:oy + GH, ox:ox + GW][..., c]] for c in range(3)], -1).astype(np.float32) - ref)[land]
    print(f"ground tones matched on {land.mean() * 100:.0f} % of the grid (land): mean abs difference {err.mean():.1f} of 255")
    import shutil
    w, s, e, n = g3.DUST_BOX
    frames = []
    for i, (sensor, utc) in enumerate(g3.DUST_PASSES):
        src = g3.OUT / f"dust_{g3.DUST_DAY.replace('-', '')}_{sensor}.jpg"
        assert src.exists(), f"{src.name}: run src/get_hamoun3.py"
        a = np.asarray(Image.open(src).convert("RGB"), np.float32)              # one stretch for the three passes:
        a = 255 * np.clip((a - 38) / (228 - 38), 0, 1) ** 0.92                   # the haze's grey taken out, so the
        Image.fromarray(a.astype(np.uint8)).save(BUILD / f"dust{i + 1}.jpg", quality=92)   # plume stands on the ground
        frames.append(dict(file=f"dust{i + 1}.jpg", sensor=sensor, utc=utc))
    return dict(pics=pics, waters=waters, ground=ground, ring="ring.png", dust=dict(frames=frames, w=w, s=s, e=e, n=n))


def river() -> list:
    """The Helmand's main stem from the Hindu Kush to the Hamoun, one line (Natural Earth's three pieces in order)."""
    L = json.loads((g3.OUT / "lines.json").read_text())
    a, bb, c = L["Helmand"]
    assert c[-1][0] > 67 and a[-1][0] < 62, "piece 2 is the head, piece 0 the mouth"
    line = c[::-1] if c[0][0] < c[-1][0] else c
    line = line + (bb if abs(bb[0][0] - line[-1][0]) < 0.05 else bb[::-1])
    line = line + (a if abs(a[0][0] - line[-1][0]) < 0.05 else a[::-1])
    assert line[0][0] > 68 and 61.5 < line[-1][0] < 61.7 and 31.1 < line[-1][1] < 31.3, (line[0], line[-1])
    return line


def main() -> None:
    b = bars()
    c = checked(b)
    r = rain_numbers(b)
    pic = pictures(b, "--pictures" in sys.argv)
    w2 = v2.words()
    L = json.loads((g3.OUT / "lines.json").read_text())
    by = {x["year"]: x for x in b}
    cuts = dict(p1=part1(), p2=part2())
    springs = []
    for k, x in enumerate(b):
        gap = x["km2"] is None
        own = pic["pics"].get(x["year"])
        last = own or next(pic["pics"][z] for z in range(x["year"] - 1, reel.FIRST - 1, -1) if z in pic["pics"])
        springs.append(dict(year=x["year"], label=fa(x["label"]), km2=x["km2"],
                            shown=None if gap else v2.shown(x["km2"]), pic=last, held=own is None,
                            water=pic["waters"].get(x["year"]), above=bool((not gap) and x["km2"] > c["mean"])))
    assert springs[13]["label"] == fa("1379")
    assert springs[0]["held"] is False, "the first spring has its own picture"
    assert by[BEFORE]["km2"] >= 0.95 * c["vmax"], "the hook's first spring is among the fullest (within 5 % of the wettest)"
    held = [s["label"] for s in springs if s["held"]]
    dry = DRY - reel.FIRST
    assert springs[dry]["held"] is False and by[DRY]["km2"] < 1, "the dry bed's picture is its own, with no open water"
    assert (g3.DUST_DAY, [u for _s, u in g3.DUST_PASSES]) == ("2023-09-22", ["05:35", "08:36", "09:30"])   # 09:05, 12:06, 13:00 in Iran (UTC+3:30)
    outline = [[[round(a, 4), round(c2, 4)] for a, c2 in ring[::3]] for ring in reel.contour_lines(hamoun.lakes().astype(np.float32), 0.5, min_pts=60)]
    print(f"mean of the 39 measured springs {c['mean']:.1f} km2; the hook: {by[BEFORE]['label']} "
          f"{by[BEFORE]['km2']:.0f} -> {v2.shown(by[BEFORE]['km2'])}, {by[NOW]['label']} {by[NOW]['km2']:.0f} -> "
          f"{v2.shown(by[NOW]['km2'])}; 1405 / mean = {by[NOW]['km2'] / c['mean']:.3f}")
    print(f"rain: CRU {r['cru']['rain_share']:.3f}, ERA5 {r['era5']['rain_share']:.3f} of the earlier winters; the lake "
          f"{r['lake_share']:.3f}; on screen {r['less']} and 74 % less")
    print(f"springs without a clean picture ({len(held)}): {' '.join(held)}")
    now_head = w2["scenes"][6][0].replace("حدودِ ", "حدودِ // ")           # the reviewed line, on two lines
    assert now_head.count(" // ") == 1, now_head
    words = dict(
        hook=NEW["hook"], spring=NEW["spring"], unit=NEW["unit_water"], wet=NEW["wet"], this_spring=NEW["this_spring"],
        mean_value=NEW["mean_value"].format(v2.shown(c["mean"])),
        iran=NEW["iran"], afg=NEW["afg"], pak=NEW["pak"], zabol=NEW["zabol"], river=NEW["river"], lake=NEW["lake"],
        era1=w2["scenes"][1][0], era2=w2["scenes"][2][0], mean=w2["mean"], legend=w2["legend"], held=NEW["held"], gap=w2["gap"],
        why=NEW["why"], rain_item=NEW["rain_item"], lake_item=NEW["lake_item"],
        rain_less=NEW["less_range"].format(fa(r["less"][0]), fa(r["less"][1])), lake_less=NEW["less"].format(fa(74)),
        dams=NEW["dams"], pins=NEW["pins"], share=NEW["share"], now=now_head, teaser=NEW["teaser"],
        src_rain=NEW["src_rain"].format(fa(1379), fa(1404), fa(1366), fa(1378)),
        **{k: NEW[k] for k in ("dust_head", "dust_small", "dust_date", "dust_hours", "wind", "bed", "health_head",
                               "health_small", "lives_head", "lives_small", "lives_notes", "lives_note", "dispute_head",
                               "dispute_boxes", "end_head", "follow", "src_water", "src_map", "src_dust", "src_lives",
                               "src_dispute")},
    )
    assert NEW["why"].startswith("از ۱۳۷۹") and springs[13]["label"] == fa("1379"), "the later period starts in 1379"
    reading(words, cuts)
    film = dict(
        fps=FPS, size=[W, H], cuts=cuts,
        grid=dict(lon0=LON0, lat1=LAT1, dlon=gh.DLON, dlat=gh.DLAT, w=GW, h=GH),
        views=dict(close=CLOSE, mid=MID, wide=WIDE, dust=DUST, dustb=DUSTB, disp=DISP), dust=pic["dust"], dry=dry,
        ground=pic["ground"], ring=pic["ring"],
        springs=springs, mean=c["mean"], vmax=c["vmax"],
        before=BEFORE - reel.FIRST, now=NOW - reel.FIRST,          # the hook's two springs (indices)
        lines=dict(ia=L["Iran-Afghanistan"][0], ip=L["Iran-Pakistan"][0], ap=L["Afghanistan-Pakistan"][0], river=river(), lake=outline),
        places=PLACES, words=words,
        rain=dict(cru=r["cru"]["rain_share"], era5=r["era5"]["rain_share"], lake=r["lake_share"]),
        colours=dict(wet=v2.WET, dry=v2.DRY, gapc=v2.GAPC, gold="#F6C445", ink="#1d140c", paper="#FBF7F0",
                     river="#49c0ff", pin="#FF8A1F"),
    )
    (BUILD / "film.json").write_text(json.dumps(film, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", BUILD / "film.json")


if __name__ == "__main__":
    main()
