"""«آبِ هامون کجا رفت؟» (hamoun3_fa): the Hamoun lakes from space with the satellite picture as the whole frame.
The owner's direction (12 Nov 2026): the satellite animation is the hero and the bar chart the small one, a zoom-out
that shows the border of Iran and Afghanistan, catchy from the first second (the reference reels he sent are logged
in ~/Documents/instagram_research/reels.csv, "owner reference (12 Nov 2026)").

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
- The clock (64.5 s, a loop): the hook, a wipe from a full spring (1377, within 5 % of the wettest, said on screen)
  to this spring; the zoom-out with the border drawn; the forty springs one by one with the small bar chart; the
  whole river with the rain against the lake; the dams and the irrigated land in the river's order, with «سهمِ هر
  عامل محلِ بحث است» on screen; this spring against the mean; the wipe back to frame 0.
- The ground around the pictures and under the zoom-outs: Sentinel-2 cloudless 2016 by EOX (get_hamoun3.py), its
  tones matched once to the Landsat pictures' land (one mapping per band for the three ground pictures); the border
  and the river: Natural Earth 10 m (about 1 km accurate); the dams' places: Wikipedia's coordinates, checked on
  the pictures (the river bends at Kamal Khan; Kajaki and Lashkargah lie on the river's line).

The view: longitude and latitude as straight axes in units of the picture pixel; a view is (lon, lat of the frame's
centre, frame pixels per picture pixel). CLOSE shows the lakes at the pictures' own scale (about 143 m a pixel, the
frame 154 km wide), MID 2.5 times wider (the border, Zabol, the delta), WIDE 6 times wider (the whole river).

    python -I src/hamoun3.py              # film.json and the pictures (cached pictures are kept)
    python -I src/hamoun3.py --pictures   # rebuild the pictures too
"""

from __future__ import annotations

import json
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
DRY = 2001                                           # the dry bed's picture (spring 1380: no open water)

# the clock (s). Each scene: start, and the times inside it are in film.json's cues
T = dict(
    wipe=(0.35, 1.90),                               # the hook's wipe, 1377 -> 1405
    where=3.5, out1=(3.5, 4.6), border=(4.0, 4.9), labels=(4.5, 4.7, 4.9),
    run=6.4, in1=(6.4, 7.4), t0=7.4, step1=0.30, step2=0.24,       # 1366 at t0; 1366-1378 every step1, then step2
    why=18.6, out2=(18.6, 20.3), river=(19.6, 21.6), card=20.2,
    where2=24.4, pins=(24.8, 25.6, 28.1, 28.9), mid2=(26.7, 27.9),
    # what follows when the bed is dry: the dust storm of one day (three passes), what NASA says, the dry years of
    # 1378-1384 in UNEP's report, the dispute over the river's water
    dust=31.4, dustin=(31.4, 32.8), dframes=(31.6, 34.0, 35.6), dust2=37.4, dust2_chip=38.4,
    lives=44.0, livesin=(44.0, 45.3), lives_pins=(45.4, 46.15, 46.9, 47.65, 48.4),
    dispute=51.6, dispin=(51.6, 52.9), dispute_chips=(52.8, 54.0, 55.2),
    now=58.6, in2=(58.6, 59.8), ask=60.2, follow=62.0, back=(64.3, 65.0), end=65.1,
)
PLACES = dict(                                       # lon, lat
    zabol=(61.4878, 31.0339), kajaki=(65.1189, 32.3219), lashkargah=(64.369, 31.583), kamalkhan=(61.8834, 30.3240),
    chahnimeh=reel.PLACES["chahnimeh"],
    # where the map's words sit (each on its own side of the border, inside the frame's safe part in its view)
    iran_close=(61.31, 30.90), afg_close=(62.017, 31.137),
    border_end=(61.80, 30.86),                           # where the river reaches the border (the green band's end)
    iran_mid=(60.25, 31.75), afg_mid=(62.2, 32.2),
    iran_wide=(59.79, 33.3), afg_wide=(62.95, 34.21), pak_wide=(65.5, 28.3),
    kush=(65.84, 34.95), river_name=(63.2, 29.75),
    iran_dust=(60.58, 30.2), afg_dust=(62.48, 31.35), wind0=(61.144, 31.614), wind1=(61.501, 31.180), bed_name=(60.86, 30.42),
)

NEW = dict(                                          # this film's own words (checked on 12 Nov 2026)
    hook="آبِ {هامون} کجا رفت؟",
    spring="بهارِ {}",
    where="هامون، روی {مرزِ} ایران و افغانستان",
    wet="از پُرآب‌ترین بهارها", this_spring="بهارِ امسال", unit_water="کیلومترمربع آبِ باز", mean_value="میانگین: {}",
    # the reviewed headline with its verb said twice, so that the second half cannot be read as "more water"
    why="چرا؟ بارش {کمی} کم شد؛ // آبِ هامون {خیلی بیشتر} کم شد",
    iran="ایران", afg="افغانستان", pak="پاکستان", zabol="زابل", river="رودِ هیرمند", kush="کوه‌های بالادست", lake="هامون",
    run_small="هر بهار، از فضا",
    less="{}٪ کمتر", less_range="{} تا {}٪ کمتر",
    rain_item="بارشِ زمستان در بالادست", lake_item="آبِ هامون در بهار",
    periods="{} تا {} در برابرِ {} تا {}",
    pins=(("kajaki", "سدِ کجکی", "۱۳۳۲"), ("lashkargah", "کشاورزیِ آبی", "۶۲٪ بیشتر // ۱۳۶۹ تا ۱۳۹۰"),
          ("kamalkhan", "سدِ کمال‌خان", "۱۴۰۰"), ("chahnimeh", "چاه‌نیمه‌ها", "۱۳۶۲")),
    share="سهمِ هر عامل محلِ بحث است",
    # the dust (NASA Earth Observatory, 28 Sep 2023, read 12 Nov 2026: the plume of 22 Sep 2023 "appears to emanate
    # from the ephemeral Hamun wetlands"; the Levar or "120-day wind"; "Since 1999, low water levels in the Hamun
    # wetlands have led to a marked increase in dust events originating there"; "More than 1,300 people in Iran's
    # Sistan and Baluchestan province sought medical attention for respiratory, heart, and other ailments, according
    # to news reports")
    dust_head="[بسترِ خشکِ هامون]: // {طوفانِ گرد و غبار}، از فضا", dust_date="۳۱ شهریور ۱۴۰۲",
    dust_hours=("حدودِ ساعتِ ۹", "حدودِ ساعتِ ۱۲", "حدودِ ساعتِ ۱۳"), wind="بادِ ۱۲۰روزه", bed="بسترِ هامون",
    dust2_head="از ۱۳۷۸، با کم‌آبیِ هامون // طوفان‌های غبارش {خیلی بیشتر} شده", dust2_small="رصدخانه‌ی زمینِ ناسا، ۲۰۲۳",
    dust2_chip=("در طوفانِ همان روزها، در سیستان و بلوچستان", "بیش از ۱٬۳۰۰ نفر به مراکزِ درمانی رفتند",
                "(گزارشِ رسانه‌ها، به نقلِ ناسا)"),
    # the dry years 1999-2005 (UNEP 2006, History of Environmental Change in the Sistan Basin, read 12 Nov 2026:
    # "the collapse of the local economy during this latest drought period"; "fishing is not possible"; "The reed
    # beds provide fodder for livestock"; "caused damage to agriculture in the delta"; "Loss of traditional
    # livelihoods has resulted in emigration"; "local experts reported that more than a hundred villages in the
    # Saberi and Baringak region had been deserted")
    # UNEP's drought is "between 1999 and 2005" and ends with the floods of March 2005 (Esfand 1383); this film's own
    # strip shows spring 1384 full again, so the Persian years of the dry period are 1378 to 1383
    lives_head="خشکسالیِ ۱۳۷۸ تا ۱۳۸۳: // {اقتصادِ محلی} فروپاشید",
    lives_small="گزارشِ برنامه‌ی محیط‌زیستِ ملل متحد (۲۰۰۶)",
    lives_pins=("ماهیگیری ممکن نبود", "نیزار (علوفه‌ی دام) خشکید", "کشاورزی آسیب دید", "مهاجرت از منطقه",
                "بیش از ۱۰۰ روستای خالی، کنارِ هامون*"),
    lives_note="* به گفته‌ی کارشناسانِ محلی، دی ۱۳۸۳",
    # the dispute (Al Jazeera, 30 May 2023, read 12 Nov 2026: "at least two Iranian and one Afghan guard were
    # killed"; "The reasons for the clashes are still unknown"; Iran's president "accused Afghanistan's Taliban
    # rulers of restricting the flow of water"; "The Taliban, which has denied the accusation"). The wording of this
    # scene is the owner's to approve.
    dispute_head="و اختلاف بر سرِ [آبِ هیرمند]",
    dispute_chips=("۱۳۵۱: امضای معاهده‌ی آبِ هیرمند // میانِ ایران و افغانستان",
                   "اردیبهشت ۱۴۰۲: ایران می‌گوید طالبان، برخلافِ معاهده، // جریانِ آب را محدود کرده‌اند؛ طالبان رد می‌کنند",
                   "خرداد ۱۴۰۲: درگیریِ مرزی؛ دست‌کم ۳ مرزبان کشته شدند // الجزیره: علتِ درگیری روشن نبود"),
    src_dust="تصویرها و گزارش: ناسا (Terra، Suomi NPP، NOAA-20)", src_lives="تصویر: لندست (USGS)، بهارِ ۱۳۸۰",
    src_dispute="الجزیره، ۹ خرداد ۱۴۰۲؛ معاهده: UNEP، ۲۰۰۶",
    src_water="منبع: لندست (USGS)؛ مقایسه‌شده با آبِ سطحیِ JRC",
    src_map="زمینه: Sentinel-2 cloudless (EOX)؛ مرز و رود: Natural Earth",
    src_rain="بارش: CRU TS 4.10 و ERA5؛ پژوهش‌ها در کامنتِ اول",
)


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


def follow_lines(s: str) -> list:
    """The reviewed call to send the reel on, broken before «که» into two lines."""
    a, b = s.split(" که ")
    return [a, "که " + b]


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
    springs = []
    for k, x in enumerate(b):
        t = T["t0"] + T["step1"] * k if k <= 12 else T["t0"] + T["step1"] * 13 + T["step2"] * (k - 13)
        gap = x["km2"] is None
        own = pic["pics"].get(x["year"])
        last = own or next(pic["pics"][z] for z in range(x["year"] - 1, reel.FIRST - 1, -1) if z in pic["pics"])
        springs.append(dict(year=x["year"], label=fa(x["label"]), km2=x["km2"], t=round(t, 3),
                            shown=None if gap else v2.shown(x["km2"]), pic=last, held=own is None,
                            water=pic["waters"].get(x["year"]), above=bool((not gap) and x["km2"] > c["mean"])))
    assert springs[13]["label"] == fa("1379") and springs[-1]["t"] + 0.5 < T["why"]
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
    film = dict(
        fps=FPS, end=T["end"], cover_t=1.0, size=[W, H],
        grid=dict(lon0=LON0, lat1=LAT1, dlon=gh.DLON, dlat=gh.DLAT, w=GW, h=GH),
        views=dict(close=CLOSE, mid=MID, wide=WIDE, dust=DUST), clock=T, dust=pic["dust"], dry=dry,
        ground=pic["ground"], ring=pic["ring"],
        springs=springs, mean=c["mean"], vmax=c["vmax"],
        before=BEFORE - reel.FIRST, now=NOW - reel.FIRST,          # the hook's two springs (indices)
        lines=dict(ia=L["Iran-Afghanistan"][0], ip=L["Iran-Pakistan"][0], ap=L["Afghanistan-Pakistan"][0], river=river(), lake=outline),
        places=PLACES,
        words=dict(
            hook=NEW["hook"], spring=NEW["spring"], unit=NEW["unit_water"], wet=NEW["wet"],
            this_spring=NEW["this_spring"], mean_value=NEW["mean_value"].format(v2.shown(c["mean"])),
            where=NEW["where"], iran=NEW["iran"], afg=NEW["afg"], pak=NEW["pak"], zabol=NEW["zabol"],
            river=NEW["river"], kush=NEW["kush"], lake=NEW["lake"],
            era1=w2["scenes"][1][0], era2=w2["scenes"][2][0], run_small=NEW["run_small"],
            mean=w2["mean"], legend=w2["legend"], held=(w2["held"], w2["held2"]), gap=w2["gap"],
            why=NEW["why"], why_small=w2["scenes"][4][1],
            rain_item=NEW["rain_item"], lake_item=NEW["lake_item"],
            rain_less=NEW["less_range"].format(fa(r["less"][0]), fa(r["less"][1])), lake_less=NEW["less"].format(fa(74)),
            periods=NEW["periods"].format(fa(1379), fa(1404), fa(1366), fa(1378)),
            where2=w2["scenes"][5][0], where2_small=w2["scenes"][5][1], pins=NEW["pins"], share=NEW["share"],
            now=w2["scenes"][6][0], ask=w2["scenes"][6][1], follow=follow_lines(w2["follow"]),
            src_water=NEW["src_water"], src_map=NEW["src_map"], src_rain=NEW["src_rain"],
            **{k: NEW[k] for k in ("dust_head", "dust_date", "dust_hours", "wind", "bed", "dust2_head", "dust2_small",
                                   "dust2_chip", "lives_head", "lives_small", "lives_pins", "lives_note", "dispute_head",
                                   "dispute_chips", "src_dust", "src_lives", "src_dispute")},
        ),
        rain=dict(cru=r["cru"]["rain_share"], era5=r["era5"]["rain_share"], lake=r["lake_share"]),
        colours=dict(wet=v2.WET, dry=v2.DRY, gapc=v2.GAPC, gold="#F6C445", ink="#1d140c", paper="#FBF7F0",
                     river="#49c0ff", pin="#FF8A1F"),
    )
    (BUILD / "film.json").write_text(json.dumps(film, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", BUILD / "film.json")


if __name__ == "__main__":
    main()
