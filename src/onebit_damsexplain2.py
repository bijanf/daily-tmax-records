"""«با این باران‌ها، سدهای تهران پر شدند؟» THE LONG CUT (damsexplain2_fa): the owner's request of 9 Nov 2026 after
reading the five-dam reel's comments («این همه سیل و باران اومده… با این همه بارندگی اب نیست؟»): break the crisis
down for ordinary people with newsroom-quality animation, up to about 2 minutes. The approved slides of
damsexplain_fa plus four animated cross-sections under Tehran (src/onebit_ground.py):

    hook      the five dams from space and the question
    answer    not yet: about 350 million m3 (Abfa, 18 Aban)
    grid      190 million m3 short of normal: two months of the city's water
    rain      «این همه سیل آمد؛ پس آب کجا رفت؟»: runoff that passes in hours, a thin wet skin of soil, some back to
              the air, about 1 in 10 to the dam soon (our estimate), the water table untouched
    soil      a storm wets the top few centimetres; the water table lies tens of metres down (camera pull-back)
    snow      in the mountains the storm's water is still snow (Abfa's words)
    seasons   the Karaj dam gets 60 % of its year in April-June
    ground    the water table under the Tehran plain has fallen for decades; one storm lifts it by a hair
    sink      pumped-out clay compacts: the ground sinks and the storage is gone for good
    urmia     Lake Urmia: a few centimetres of the 351 it lacks
    end       Kaveh Madani's words to Al Jazeera; follow the data

    python -I src/onebit_damsexplain2.py --stills
    python -I src/onebit_damsexplain2.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import onebit  # noqa: E402
import onebit_damsexplain as one  # noqa: E402
import onebit_elnino26x as part1  # noqa: E402   (the glyph guard)
import onebit_ground as G  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, SIZES, SOCIAL_CRF, Canvas, fa, title  # noqa: E402
from onebit_slides import COLOURS, LEFT, RIGHT, WIN  # noqa: E402

BASE = "damsexplain2_fa"
SCENES = ("hook", "answer", "grid", "rain", "soil", "snow", "seasons", "ground", "sink", "urmia", "end")
# sized by src/onebit_reading.py: 127.75 s
SECONDS_OF = dict(hook=8.5, answer=9.5, grid=10.25, rain=13.75, soil=11.0, snow=12.5, seasons=11.25, ground=12.5,
                  sink=12.0, urmia=12.0, end=14.5)
SECONDS = tuple(SECONDS_OF[k] for k in SCENES)
PACE = dict(bpm=60, bars=tuple(s / 4 for s in SECONDS))
END = sum(SECONDS)
COVER_T = 1.0
BOX = (LEFT, one.RULE_Y + 20, RIGHT - LEFT, 800)          # the animation box: x, y, w, h
APP = "Tehran.Water"

# the new numbers (fact check of 9 Nov 2026, scratch in the job's fc_ground folder):
# - WET_CM: a dry loam needs 16-22 mm of rain to refill its top 10 cm and 13-18 mm for each further 10 cm (FAO-56,
#   Allen et al. 1998, Table 19): about 0.5 cm a mm; Tehran got about 37-40 mm in the storm (Hamshahri 1084558;
#   Abfa: 16 → 56.5 mm since 1 Mehr) → the top 20-30 cm at most; the ECMWF model keeps 28-100 cm as dry as before.
# - GW_YEARS, GW_DROP_M: the Tehran plain's water table fell about 15 m in 1993-2021 (Tehran Municipality, reported,
#   Ecoiran 102001); 12 m in 1984-2011 (Haghshenas Haghighi & Motagh 2019, RSE, doi:10.1016/j.rse.2018.11.003, via
#   GFZ); Iran-wide 0.49 m a year and 5.4 km3 a year of non-renewable withdrawal (Noori et al. 2021 PNAS,
#   doi:10.1073/pnas.2024221118; Energy Ministry 4.4) → «سالی حدودِ نیم متر», «۴ تا ۵ میلیارد مترمکعب».
# - SINK_CM: more than 25 cm a year in the western Tehran plain, 2003-2017 (Haghshenas Haghighi & Motagh 2019);
#   Tehran and Karaj above 15 cm a year in 2014-2022 and at least 60 % of it irreversible (Payne et al. 2025 JGR,
#   doi:10.1029/2024JB030367); compaction mostly permanent (Haghshenas Haghighi & Motagh 2024, Sci. Adv.).
WET_CM = 20                                               # the owner says «حداکثر بیست سانت»; FAO-56: 18-26 cm
GW_YEARS, GW_DROP_M = (1372, 1400), 15
SINK_CM = 25


def words2() -> dict:
    w = one.words()
    base = dict(zip(one.SCENES, w["scenes"]))
    src = dict(zip(one.SCENES, w["sources"]))
    new = dict(
        rain=("این همه سیل آمد؛ // پس {آب} کجا رفت؟", "سیل یعنی بارانی که زمین نتوانست بنوشد"),
        soil=("بارانِ این چند روز، // فقط {پوستِ زمین} را خیس کرد", "هر میلی‌متر باران: نیم سانتی‌متر خاکِ خشک"),
        ground=("آبِ زیرِ زمینِ تهران: // سالی حدودِ {نیم متر} پایین‌تر", "۱۵ متر در ۲۸ سال؛ به گزارشِ شهرداری تهران"),
        sink=("زمینِ غربِ تهران فرو می‌نشیند: // جاهایی سالی {۲۵ سانتی‌متر}", "اندازه‌گیری با ماهواره، ۱۳۸۲ تا ۱۳۹۶"),
    )
    nsrc = dict(rain="FAO-56 · Hamshahri · our estimate", soil="FAO-56 (Allen et al. 1998) · Hamshahri",
                ground="Tehran Municipality · Noori 2021 (PNAS)", sink="Haghshenas Haghighi 2019 · Payne 2025")
    new["hook"] = ("باران و سیلِ این هفته؛ // سدهای تهران {پر شدند؟}", "خیلی از شما پرسیدید؛ جواب با آمارِ رسمی")
    nsrc["hook"] = "NASA (MODIS Terra), 7 Nov 2026"
    base.pop("hook")
    src.pop("hook")
    w["storm_chip"] = "طوفانِ ۱۶ آبان از فضا؛ تصویرِ ماهواره‌ی ناسا"
    w["storm_tehran"], w["storm_caspian"] = "تهران", "دریای خزر"
    w["scenes"] = tuple(base[k] if k in base else new[k] for k in SCENES)
    w["sources"] = tuple(src[k] if k in src else nsrc[k] for k in SCENES)
    w["rain_labels"] = ("سیل: آبی که زمین نگرفت؛ چند ساعته می‌رود", "فقط حدودِ ۲۰ سانتی‌مترِ رویی خیس می‌شود",
                        "بخشی به هوا برمی‌گردد", "حدودِ ۱ از ۱۰ زود به سد می‌رسد (برآوردِ ما)", "آبِ زیرزمینی: هنوز بی‌تغییر")
    w["soil_labels"] = ("بارانِ این چند روز: حدودِ ۲۰ سانتی‌مترِ رویی", "پایین‌تر: باران نرسیده", "آبِ زیرزمینی: خیلی پایین‌تر")
    w["ground_labels"] = ("سطحِ آب در ۱۳۷۲", "حدودِ ۱۵ متر پایین‌تر", "آبِ این طوفان: هنوز در خاکِ رویی",
                          "ایران سالی ۴ تا ۵ میلیارد مترمکعب از پس‌اندازِ زیرِ زمین برمی‌دارد")
    w["sink_labels"] = ("لوله‌ی چاه از زمین بیرون زده", "زمین پیش‌تر اینجا بود (بزرگ‌تر از واقع)", "بیشترِ این فرونشست برگشت‌ناپذیر است")
    flat = [y for k in ("scenes", "rain_labels", "soil_labels", "ground_labels", "sink_labels")
            for x in w[k] for y in (x if isinstance(x, tuple) else (x,))]
    bad = [x for x in flat if part1.dotted_yeh(x)]
    assert not bad, bad
    w["fa_digits"] = lambda n: fa(str(n))
    w["cm"] = lambda v: fa(str(round(v))) + " سانتی‌متر"
    w["m"] = lambda v: fa(str(round(v))) + " متر"
    return w


STORM = dict(sat="Terra", date="2026-11-07", box=(46.5, 58.5, 32.0, 39.5))   # W, E, S, N; 16 Aban 1405, morning pass
TEHRAN = (51.39, 35.69)
CASPIAN = (51.0, 38.4)


def storm_picture() -> tuple:
    """The storm of 16 Aban 1405 over northern Iran: MODIS Terra true colour (NASA GIBS, public domain), squeezed
    in longitude by cos(35.75°) so the land is not stretched, Iran's border (Natural Earth 50 m) drawn in white.
    Returns the picture and a function lon, lat → pixel."""
    import urllib.request
    from scipy import ndimage
    import enso
    W, E, S, N = STORM["box"]
    path = one.num.DATA / f"storm_{STORM['sat'].lower()}_{STORM['date'].replace('-', '')}.png"
    if not path.exists():
        raw = path.with_suffix(".jpg")
        url = ("https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0"
               f"&LAYERS=MODIS_{STORM['sat']}_CorrectedReflectance_TrueColor&CRS=EPSG:4326&BBOX={S},{W},{N},{E}"
               f"&WIDTH=1656&HEIGHT=1035&FORMAT=image/jpeg&TIME={STORM['date']}")
        urllib.request.urlretrieve(url, raw)
        im = Image.open(raw).convert("RGB")
        k = np.cos(np.deg2rad((S + N) / 2))
        im = im.resize((round(im.width * k), im.height), Image.LANCZOS)
        w, h = im.size
        lon = W + (np.arange(w) + 0.5) / w * (E - W)
        lat = N - (np.arange(h) + 0.5) / h * (N - S)
        LA, LO = np.meshgrid(lat, lon, indexing="ij")
        inside = enso.country_mask(["Iran"], LA, LO)
        border = inside & ~ndimage.binary_erosion(inside, iterations=3)
        a = np.array(im)
        a[border] = (255, 255, 255)
        Image.fromarray(a).save(path)
    im = Image.open(path).convert("RGB")
    w, h = im.size
    return im, (lambda lon, lat: ((lon - W) / (E - W) * w, (N - lat) / (N - S) * h))


class DamsFilm2(one.DamsFilm):
    def __init__(self, th: onebit.Theme, colour: dict):
        import json
        self.n = json.loads((one.num.DATA / "numbers.json").read_text(encoding="utf-8"))
        self.check_data()
        self.words = words2()
        self.setup(th, "fa", colour, self.words, PACE, APP)
        assert abs(self.starts[-1] - END) < 1e-9
        self.hook_at_once = True
        self.th = th
        self.grid_pic = one.five_dams()
        snow = Image.open(one.SNOW_PIC).convert("RGB")
        self.snow = snow.resize((snow.width // 3, snow.height // 3), Image.LANCZOS)
        self.sprites = {k: one.el2.ElNino2Film.sprite(self, k) for k in ("pale", "wet")}
        from PIL import ImageEnhance
        storm, self.storm_xy = storm_picture()                # a little more contrast so the clouds read on a phone
        self.storm = ImageEnhance.Color(ImageEnhance.Contrast(storm).enhance(1.18)).enhance(1.12)

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]):
        c = Canvas(s, self.th, 1.0, (0.0, 0.0), size)
        c.pixels(0, 0, self.dots, self.th.dots)
        i = self.scene(t)
        dt = t - self.starts[i] if np.isfinite(t) else np.inf
        self.window(c, i)
        self.progress(c, t)
        at = self.appear(i)
        title(c, self.th, self.S.scenes[i], dt, self.lang, 1.0, LEFT, RIGHT, WIN[1] + one.BARH + 96, at,
              sizes=((68, 92), (60, 82)), motion=False, line_at=at[-1] + 0.6, small=48)
        getattr(self, "s_" + SCENES[i])(c, dt)
        self.sources(c, i)
        return c.im

    # ── the hook: the storm from space ──

    def s_hook(self, c: Canvas, dt: float):
        th = self.th
        x0, y0, W = BOX[0], BOX[1], BOX[2]
        im = self.storm
        H = round(W * im.height / im.width)
        z = 1.0 + 0.012 * (1.0 if not np.isfinite(dt) else min(dt / SECONDS_OF["hook"], 1.0))
        tx, ty = self.storm_xy(*TEHRAN)
        cw, ch = im.width / z, im.height / z
        ox = (im.width - cw) * tx / im.width                # the push-in closes on Tehran
        oy = (im.height - ch) * ty / im.height
        pic = im.resize((W, H), Image.LANCZOS, box=(ox, oy, ox + cw, oy + ch))
        c.im.paste(pic, (c.X(x0), c.Y(y0)))
        c.frame(x0 - 1, y0 - 1, x0 + W + 1, y0 + H + 1, colour=th.ink)
        k = W / cw
        px, py = x0 + (tx - ox) * k, y0 + (ty - oy) * k
        tt = 0.0 if not np.isfinite(dt) else dt
        ph = (tt % 1.4) / 1.4                                # a ring that grows and fades every 1.4 s
        r = 12 + 30 * ph
        ring = tuple(int(v) for v in np.array([214, 40, 40]) * (1 - ph) + np.array([255, 255, 255]) * ph)
        c.d.ellipse([c.X(px - r), c.Y(py - r), c.X(px + r), c.Y(py + r)], outline=ring, width=4)
        c.d.ellipse([c.X(px - 11), c.Y(py - 11), c.X(px + 11), c.Y(py + 11)], fill=(214, 40, 40),
                    outline=(255, 255, 255), width=3)
        w_ = self.words
        for (lon, lat), text, dx in ((TEHRAN, w_["storm_tehran"], -22), (CASPIAN, w_["storm_caspian"], 0)):
            sx, sy = self.storm_xy(lon, lat)
            lx, ly = x0 + (sx - ox) * k + dx, y0 + (sy - oy) * k + (14 if dx else 0)
            c.d.text((c.X(lx), c.Y(ly)), text, font=c.font(FA_BOLD, 42), fill=(255, 255, 255),
                     anchor="rt" if dx else "mm", direction="rtl", stroke_width=4, stroke_fill=(46, 33, 24))
        lab = w_["storm_chip"]
        wl = c.width(lab, FA_BOLD, 32, "rtl")
        c.frame(RIGHT - wl - 26, y0 + H + 16, RIGHT, y0 + H + 62, fill=th.paper)
        c.text(RIGHT - 13, y0 + H + 50, lab, FA_BOLD, 32, th.ink, "rs", "rtl")
        assert y0 + H + 62 < one.SOURCE_Y - 40

    # ── the animated boxes ──

    def box(self, c: Canvas, b: G.Box):
        x, y, w, h = BOX
        c.im.paste(b.done(), (c.X(x), c.Y(y)))
        over = Image.new("RGBA", c.im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(over)
        items = []
        for L in b.labels:
            font = FA_BOLD if L["bold"] else FA_TEXT
            tw = c.width(L["text"], font, L["size"], "rtl")
            assert tw <= w - 20, L["text"]
            if L["anchor"] == "rs":                      # the whole label (and its pill) inside the box
                assert L["x"] - tw - 12 >= 0 and L["x"] + 12 <= w, L["text"]
            lx, ly = x + L["x"], y + L["y"]
            x1 = lx if L["anchor"] == "rs" else lx + tw
            if L["colour"] != G.WHITE:
                d.rounded_rectangle([c.X(x1 - tw - 12), c.Y(ly - 0.95 * L["size"]), c.X(x1 + 12),
                                     c.Y(ly + 0.35 * L["size"])], radius=10, fill=(243, 236, 225, 228))
            items.append((lx, ly, L, font))
        c.im.paste(Image.alpha_composite(c.im.convert("RGBA"), over).convert("RGB"))
        c.d = ImageDraw.Draw(c.im)
        for lx, ly, L, font in items:
            c.text(lx, ly, L["text"], font, L["size"], L["colour"], L["anchor"], "rtl")

    def s_rain(self, c: Canvas, dt: float):
        self.box(c, G.scene_rain(BOX[2], BOX[3], dt, self.words))

    def s_soil(self, c: Canvas, dt: float):
        self.box(c, G.scene_soil(BOX[2], BOX[3], dt, self.words, WET_CM))

    def s_ground(self, c: Canvas, dt: float):
        self.box(c, G.scene_ground(BOX[2], BOX[3], dt, self.words, GW_YEARS))

    def s_sink(self, c: Canvas, dt: float):
        self.box(c, G.scene_sink(BOX[2], BOX[3], dt, self.words))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--at", type=float, nargs="*")
    args = ap.parse_args()
    film = DamsFilm2(onebit.THEMES["kahgel"], COLOURS["kahgel"])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / BASE
    film.draw(1, COVER_T).save(f"{base}_cover.png", optimize=True)
    if args.stills or args.at:
        times = args.at or sorted({round(float(film.starts[i] + f * (film.starts[i + 1] - film.starts[i])), 2)
                                   for i in range(len(SECONDS)) for f in (0.3, 0.97)})
        if not args.at:
            for old in (OUT / "social").glob(f"{BASE}_t*.png"):
                old.unlink()
        for t in times:
            film.draw(1, t).save(f"{base}_t{t:06.2f}.png")
        print("stills", len(times))
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
