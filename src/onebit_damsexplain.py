"""«با این باران‌ها، سدهای تهران پر شدند؟» (damsexplain_fa): the answer, at primary-school level, to the question
dozens of viewers asked under the five-dam reel after the storm of 14-17 Aban 1405. The frame of the five-dam reel
(onebit_slides, "Tehran.Dams"), its five Landsat pictures in frame 0, one number or picture per slide, headlines whole
on each slide's first frame, a light score, no narration. Numbers: src/damsexplain.py (asserted).

Eight slides at 60 BPM, 90 s; each slide long enough to read (owner, 9 Nov: "too little time to read"): 1 s to
settle, then the headline and half the labels at 2.5 words a second, and at least 3 s after the last element appears:
    hook     0-8.5       the five dams from space (the five-dam reel's picture, Mehr 1405, before the rains) and the question
    answer   8.5-18      not yet: about 350 million m3, under a fifth of the five dams' capacity (Abfa, 18 Aban)
    drops    18-29.5     of 10 drops of autumn rain, about 1 reaches a dam soon (our estimate); where the other 9 go
    snow     29.5-42     the storm's water is still snow on the heights (Abfa's own words); the Alborz in winter
    seasons  42-53.25    the Karaj dam gets 60 % of its year's water in April-June, from melting snow
    grid     53.25-63.5  the dams are about 190 million m3 short of normal (1 Aban: 359 against the average 548): about
                         two months of the city's water, 190 squares of 1 million m3 (8 hours of Tehran's water each)
    urmia    63.5-75.5   Lake Urmia: about 30 mm of Aban rain on the basin, 3 cm on the lake itself, at most about 15 cm
                         with the rivers, of the 351 cm it lacks
    end      75.5-90     Kaveh Madani (Stockholm Water Prize 2026): with the first rain people may forget; follow the data

    python -I src/onebit_damsexplain.py --stills
    python -I src/onebit_damsexplain.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import damsexplain as num  # noqa: E402
import onebit  # noqa: E402
import onebit_elnino2 as el2  # noqa: E402   (the drop sprites)
import onebit_elnino26x as part1  # noqa: E402   (the glyph guard)
from onebit import FA_BOLD, FA_TEXT, OUT, PIXEL, SIZES, SOCIAL_CRF, TEXT, Canvas, fa, title  # noqa: E402
from onebit_slides import COLOURS, LEFT, RIGHT, WIN, Slides  # noqa: E402

BASE = "damsexplain_fa"
SCENES = ("hook", "answer", "drops", "snow", "seasons", "grid", "urmia", "end")
# sized by src/onebit_reading.py (owner, 9 Nov: "too little time to read"); the end slide holds the quote and the call
SECONDS_OF = dict(hook=8.5, answer=9.5, drops=11.5, snow=12.5, seasons=11.25, grid=10.25, urmia=12.0, end=14.5)
SECONDS = tuple(SECONDS_OF[k] for k in SCENES)
PACE = dict(bpm=60, bars=tuple(s / 4 for s in SECONDS))
END = sum(SECONDS)                                                # 90 s
COVER_T = 1.0
BARH, RULE_Y, SOURCE_Y = 64, 664, 1532
SOURCE = 42
MIDX = (LEFT + RIGHT) / 2
BLUE, GREY, PALE = "#2a78d6", "#B9AE9E", "#E2D8C8"
HOT = "#A03129"
# the five-dam reel's frame 0 picture: frame 3.6 s of Drive "Instagram reels/iran_tehran5/tehran5_kahgel_fa_music_reel.mp4"
T5_DRIVE = "gdrive-backup:Instagram reels/iran_tehran5/tehran5_kahgel_fa_music_reel.mp4"
T5_BOX = (63, 590, 957, 1300)                                     # the lakes, their names and the scale bar
SNOW_PIC = onebit.ROOT / "data" / "alborzsnow" / "tex_2026-01-26.jpg"


def fa_dec(x: float, digits: int = 1) -> str:
    return fa(f"{x:.{digits}f}").replace(".", "٫")


def words() -> dict:
    scene = dict(
        hook=("با این باران‌ها، // سدهای تهران {پر شدند؟}", "خیلی از شما پرسیدید؛ جواب با آمارِ رسمی"),
        answer=("هنوز نه: // حدودِ {۳۵۰} میلیون مترمکعب", "کمتر از یک‌پنجمِ گنجایشِ پنج سد؛ ۱۸ آبان"),
        drops=("از هر ۱۰ قطره بارانِ پاییز، // {حدودِ یکی} زود به سد می‌رسد", "برآوردِ ما؛ شاید کمتر"),
        snow=("در کوه‌ها، آبِ این طوفان // هنوز {برف است}", "بیش از یک متر برف در توچال، ۱۷ آبان"),
        seasons=("سدِ کرج کِی آب می‌گیرد؟ // {بهار}، با آبِ برف", "بیش از نیمِ آبِ سالش در بهار می‌رسد"),
        grid=("سدها تا حدِ معمول حدودِ // {۱۹۰} میلیون مترمکعب کم دارند", "۱ آبان: ۳۵۹ در برابرِ میانگینِ ۵۴۸"),
        urmia=("دریاچه‌ی ارومیه با این باران‌ها؟ // {چند سانتی‌متر} از ۳۵۱", "برآوردِ ما با حدودِ ۳۰ میلی‌متر بارانِ آبان"),
        end=("یک باران، // حسابِ آب را {پر نمی‌کند}", "کمبودِ آب سال‌ها جمع شده است"))
    source = dict(hook="Landsat (USGS), Mehr 1405", answer="Abfa via IRIB · Tehran Regional Water",
                  drops="Mohammadi 2005 · JICA 2001 (estimate)", snow="Abfa via IRIB · Tabnak · Sentinel-2",
                  seasons="Mohammadi et al. 2005 (1970-1999)", grid="Tehran Regional Water via Mehr · Abfa",
                  urmia="West Azerbaijan Water · DoE via Mehr", end="Al Jazeera (Nov 2025) · UNU · KVA")
    w = dict(
        scenes=tuple(scene[k] for k in SCENES),
        follow="این را برای کسی بفرستید که فکر می‌کند سدها پر شدند",
        sources=tuple(source[k] for k in SCENES),
        hook_chip="تصویرها: لندست، مهرِ ۱۴۰۵، پیش از باران‌ها",
        tank=("گنجایشِ پنج سد: حدودِ ۱۹۳۰", "برای خیالِ راحت: ۸۰۰ تا ۸۵۰", "میانگینِ ۱ آبان: ۵۴۸", "اکنون: حدودِ ۳۵۰"),
        tank_unit="میلیون مترمکعب",
        drop_dam="به سد",
        drop_rest=("بخشی را خاکِ خشک می‌نوشد", "بخشی به هوا برمی‌گردد", "بخشی به زیرِ زمین می‌رود"),
        drop_rest_head="۹ قطره‌ی دیگر، فعلاً:",
        snow_pic="عکسِ زمستانِ پارسال: البرز، بهمنِ ۱۴۰۴",
        quote_snow=("«بارش‌های اخیر در ارتفاعات به شکل برف بوده", "و هنوز ذوب نشده است»"),
        quote_snow_by="سخنگوی آبفای استانِ تهران، ۱۸ آبانِ ۱۴۰۵",
        season_names=("پاییز", "زمستان", "بهار", "تابستان"),
        season_unit="سهمِ هر سه‌ماهه‌ی میلادی از آبِ سالِ سدِ کرج، ۱۹۷۰ تا ۱۹۹۹",
        grid_lines=("۱۹۰ مربع: مصرفِ حدودِ دو ماهِ شهرِ تهران", "هر مربع: یک میلیون مترمکعب، مصرفِ حدودِ ۸ ساعتِ تهران"),
        urmia_labels=("ترازِ اکولوژیک: ۱۲۷۴٫۱۰ متر", "پیش از طوفان: ۱۲۷۰٫۵۹ متر (۱۳ آبان)", "بارانِ روی دریاچه: ۳ سانتی‌متر",
                      "با آبِ رودها: حداکثر ۱۵ سانتی‌متر", "کم دارد: ۳۵۱ سانتی‌متر"),
        quote_end=("«فکر می‌کنم با اولین باران یا سیل، مردم", "ممکن است وضعیت را فراموش کنند»"),
        quote_end_by="کاوه مدنی، برنده‌ی جایزه‌ی آبِ استکهلم؛ الجزیره، آبانِ ۱۴۰۴",
        end_line="آمارِ سدها عمومی است؛ آن را دنبال کنیم",
    )
    flat = [y for v in w.values() for x in (v if isinstance(v, tuple) else (v,))
            for y in (x if isinstance(x, tuple) else (x,)) if isinstance(y, str)]
    bad = [x for x in flat if part1.dotted_yeh(x)]
    assert not bad, bad
    return w


def five_dams() -> Image.Image:
    """The five-dam reel's picture of the five lakes (fetched once from Drive, cached in data/damsexplain)."""
    path = num.DATA / "five_dams.png"
    if not path.exists():
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["rclone", "copy", T5_DRIVE, tmp], check=True)
            mp4 = Path(tmp) / Path(T5_DRIVE).name
            png = Path(tmp) / "f.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "3.6", "-i", str(mp4), "-frames:v", "1", str(png)],
                           check=True)
            Image.open(png).convert("RGB").crop(T5_BOX).save(path)
    return Image.open(path).convert("RGB")


class DamsFilm(Slides):
    def __init__(self, th: onebit.Theme, colour: dict):
        self.n = json.loads((num.DATA / "numbers.json").read_text(encoding="utf-8"))
        self.check_data()
        self.words = words()
        self.setup(th, "fa", colour, self.words, PACE, "Tehran.Dams")
        assert abs(self.starts[-1] - END) < 1e-9
        self.hook_at_once = True
        self.th = th
        self.grid_pic = five_dams()
        snow = Image.open(SNOW_PIC).convert("RGB")
        self.snow = snow.resize((snow.width // 3, snow.height // 3), Image.LANCZOS)
        self.sprites = {k: el2.ElNino2Film.sprite(self, k) for k in ("pale", "wet")}

    def check_data(self):
        n = self.n
        assert n["now"] == 350 and 17 < n["fill_pct"] < 20 and round(n["capacity"]) == 1930
        assert n["avg_1aban"] == 548 and n["gap_1aban"] == 189 and 60 <= n["gap_days"] <= 70
        assert n["hours_per_mcm"] == 8.0 and n["urmia"]["rain_mm"] == 30
        assert n["urmia"]["direct_cm"] == 3.0 and n["urmia"]["max_cm"] < 15
        assert n["season_pct"] == dict(autumn=10, winter=12, spring=60, summer=18)
        assert abs(n["tehran_draw"] - 1.95) < 0.01
        u = n["urmia"]
        assert u["depth_m"] == 3.51 and u["pct_of_gap"][1] < 3.0 and u["level"] == 1270.59

    # ── time and frame ──

    def appear(self, i: int) -> list:
        ws = [w for w, _ in onebit.words_of(self.S.scenes[i].title, self.th)]
        return [-1.0] * (len(ws) - ws.count("//"))

    def window(self, c: Canvas, i: int):
        th = self.th
        x, y, w, h = WIN
        c.frame(x, y, x + w, y + h, fill=th.paper)
        c.fill(x, y, x + w, y + BARH, th.ink)
        c.frame(x + 3, y + BARH + 3, x + w - 3, y + h - 3)
        if i == len(self.S.scenes) - 1:
            c.text(x + w - 14, y + BARH - 18, self.words["follow"], FA_TEXT, 34, th.title, "rs", "rtl")
            assert c.width(self.words["follow"], FA_TEXT, 34, "rtl") <= w - 28
        else:
            c.text(x + 14, y + BARH - 14, self.app, PIXEL, 48, th.title)
            if i > 0:
                c.text(x + w - 14, y + BARH - 14, f"[{i}/{len(self.S.scenes) - 2}]", PIXEL, 48, th.title, "rs")
        c.fill(x + 3, RULE_Y, x + w - 3, RULE_Y + 2, th.ink)

    def sources(self, c: Canvas, i: int):
        s = self.words["sources"][i]
        assert c.width(s, TEXT, SOURCE) <= RIGHT - LEFT, s
        c.text(RIGHT, SOURCE_Y, s, TEXT, SOURCE, self.th.head, "rs")

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]):
        c = Canvas(s, self.th, 1.0, (0.0, 0.0), size)
        c.pixels(0, 0, self.dots, self.th.dots)
        i = self.scene(t)
        dt = t - self.starts[i] if np.isfinite(t) else np.inf
        self.window(c, i)
        self.progress(c, t)
        at = self.appear(i)
        title(c, self.th, self.S.scenes[i], dt, self.lang, 1.0, LEFT, RIGHT, WIN[1] + BARH + 96, at,
              sizes=((68, 92), (60, 82)), motion=False, line_at=at[-1] + 0.6, small=48)
        getattr(self, "s_" + SCENES[i])(c, dt)
        self.sources(c, i)
        return c.im

    def line(self, c: Canvas, y: float, s: str, size: int = 38, bold: bool = False, colour=None, x=None,
             anchor: str = "rs"):
        font = FA_BOLD if bold else FA_TEXT
        assert c.width(s, font, size, "rtl") <= RIGHT - LEFT, s
        c.text(RIGHT if x is None else x, y, s, font, size, colour or self.th.ink, anchor, "rtl")

    def on(self, dt: float, t0: float) -> bool:
        return (not np.isfinite(dt)) or dt >= t0

    def grow(self, dt: float, t0: float, dur: float) -> float:
        p = 1.0 if not np.isfinite(dt) else min(max((dt - t0) / dur, 0.0), 1.0)
        return p * p * (3 - 2 * p)

    # ── slides ──

    def s_hook(self, c: Canvas, dt: float):
        th = self.th
        W = RIGHT - LEFT
        im = self.grid_pic
        z = 1.0 + 0.012 * (1.0 if not np.isfinite(dt) else min(dt / SECONDS_OF["hook"], 1.0))   # past ~1.018 the frame's
        # own borders (the year chip, the scale bar) are cut
        H = round(W * im.height / im.width)
        cw, ch = im.width / z, im.height / z
        x0, y0 = (im.width - cw) / 2, (im.height - ch) / 2
        pic = im.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))
        y = 690
        c.im.paste(pic, (c.X(LEFT), c.Y(y)))
        c.frame(LEFT - 1, y - 1, RIGHT + 1, y + H + 1, colour=th.ink)
        lab = self.words["hook_chip"]
        w = c.width(lab, FA_BOLD, 32, "rtl")
        c.frame(RIGHT - w - 26, y + H + 16, RIGHT, y + H + 62, fill=th.paper)
        c.text(RIGHT - 13, y + H + 50, lab, FA_BOLD, 32, th.ink, "rs", "rtl")
        assert y + H + 62 < SOURCE_Y - 40

    def s_answer(self, c: Canvas, dt: float):
        th = self.th
        n = self.n
        x0, x1, ybot, ytop = 140, 400, 1440, 730                     # the tank, at the left
        k = (ybot - ytop) / n["capacity"]
        Y = lambda v: ybot - v * k  # noqa: E731
        c.frame(x0, ytop, x1, ybot, fill="#F7F2EA", colour=th.ink)
        f = self.grow(dt, 0.2, 1.0)
        c.fill(x0 + 3, Y(n["now"] * f), x1 - 3, ybot - 3, BLUE)
        for v, col in ((n["avg_1aban"], th.ink), (sum(n["comfort"]) / 2, HOT)):
            for xx in np.arange(x0 - 20, x1 + 20, 16):
                c.fill(xx, Y(v) - 1.5, xx + 9, Y(v) + 1.5, col)
        tops = (ytop + 34, Y(sum(n["comfort"]) / 2) + 12, Y(n["avg_1aban"]) + 12, Y(n["now"]) + 12)
        cols = (th.ink, HOT, th.ink, BLUE)
        for k_, (s, yy, col) in enumerate(zip(self.words["tank"], tops, cols)):
            if k_ == 3 and f < 1.0:
                continue
            self.line(c, yy, s, 40, True, col)
        self.line(c, ybot - 6, self.words["tank_unit"], 34)

    def s_drops(self, c: Canvas, dt: float):
        th = self.th
        pitch = (RIGHT - LEFT) / 10
        cell = el2.CELL
        size = cell * len(el2.DROP)
        for k in range(10):                                        # right to left: the first drop is the one that arrives
            x = RIGHT - pitch / 2 - k * pitch
            if not self.on(dt, 0.2 + 0.12 * k):
                continue
            sp = self.sprites["wet" if k == 0 else "pale"]
            side = round(min(size * 1.6, pitch * 0.78))                # each drop inside its own slot
            sp = sp.resize((side, side), Image.NEAREST)
            c.im.paste(sp, (c.X(x - sp.width / 2), c.Y(800 - sp.height / 2)), sp)
        if self.on(dt, 1.6):
            x = RIGHT - pitch / 2
            c.fill(x - 2, 860, x + 2, 930, BLUE)
            c.text(x, 975, self.words["drop_dam"], FA_BOLD, 40, BLUE, "ms", "rtl")
            self.line(c, 1070, self.words["drop_rest_head"], 42, True)
            for k, s in enumerate(self.words["drop_rest"]):
                if self.on(dt, 2.0 + 0.45 * k):
                    self.line(c, 1140 + 62 * k, "• " + s, 40)

    def s_snow(self, c: Canvas, dt: float):
        th = self.th
        W, H = RIGHT - LEFT, 400
        im = self.snow
        k = max(W / im.width, H / im.height)
        cw, ch = W / k, H / k
        x0, y0 = min((im.width - cw) / 2 + im.width * 0.08, im.width - cw), (im.height - ch) / 2
        pic = im.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))
        y = 700
        c.im.paste(pic, (c.X(LEFT), c.Y(y)))
        c.frame(LEFT - 1, y - 1, RIGHT + 1, y + H + 1, colour=th.ink)
        lab = self.words["snow_pic"]
        w = c.width(lab, FA_BOLD, 32, "rtl")
        c.frame(RIGHT - w - 26, y + 10, RIGHT - 8, y + 54, fill=th.paper)
        c.text(RIGHT - 17, y + 44, lab, FA_BOLD, 32, th.ink, "rs", "rtl")
        if self.on(dt, 0.6):
            c.frame(LEFT, 1140, RIGHT, 1400, fill="#F7F2EA", colour=th.ink)
            for k_, s in enumerate(self.words["quote_snow"]):
                c.text(MIDX, 1210 + 64 * k_, s, FA_BOLD, 42, th.ink, "ms", "rtl")
                assert c.width(s, FA_BOLD, 42, "rtl") <= RIGHT - LEFT - 40, s
            c.text(MIDX, 1360, self.words["quote_snow_by"], FA_TEXT, 32, th.ink, "ms", "rtl")

    def s_seasons(self, c: Canvas, dt: float):
        th = self.th
        pcts = [self.n["season_pct"][k] for k in ("autumn", "winter", "spring", "summer")]
        x0, x1, ytop, ybot = LEFT + 20, RIGHT - 20, 770, 1270
        slot = (x1 - x0) / 4
        for k, (pct, name) in enumerate(zip(pcts, self.words["season_names"])):
            xr = x1 - k * slot                                       # autumn at the right
            xa, xb = xr - slot * 0.80, xr - slot * 0.20
            f = self.grow(dt, 0.3 + 0.35 * k, 0.6)
            top = ybot - (ybot - ytop) * pct / 64 * f
            c.fill(xa, top, xb, ybot, BLUE if name == "بهار" else GREY)
            if f >= 1.0:
                c.text((xa + xb) / 2, top - 16, fa(f"{pct}٪"), FA_BOLD, 52, BLUE if name == "بهار" else th.ink, "ms",
                       "rtl")
            c.text((xa + xb) / 2, ybot + 56, name, FA_BOLD, 44, th.ink, "ms", "rtl")
        c.fill(x0, ybot, x1, ybot + 2, th.ink)
        self.line(c, ybot + 130, self.words["season_unit"], 34)

    def s_grid(self, c: Canvas, dt: float):
        th = self.th
        cols, rows = 19, 10                                          # 190 squares of 1 million m3
        cell = (RIGHT - LEFT) / cols
        y0 = 760
        for r in range(rows):
            if not self.on(dt, 0.2 + 0.12 * r):
                continue
            for q in range(cols):
                x = RIGHT - (q + 1) * cell                           # from the top right, as Persian reads
                y = y0 + r * cell
                c.fill(x + 3, y + 3, x + cell - 3, y + cell - 3, BLUE if r == q == 0 else PALE)
        yb = y0 + rows * cell
        if self.on(dt, 1.6):
            self.line(c, yb + 60, self.words["grid_lines"][0], 40, True)
            self.line(c, yb + 116, self.words["grid_lines"][1], 34, False, BLUE)

    def s_urmia(self, c: Canvas, dt: float):
        th = self.th
        u = self.n["urmia"]
        x0, x1, ytop, ybot = 150, 330, 740, 1400                    # the gauge, 3.51 m tall, at the left
        k = (ybot - ytop) / (100 * u["depth_m"])                     # px per cm
        c.frame(x0, ytop, x1, ybot, fill="#F7F2EA", colour=th.ink)
        f = self.grow(dt, 0.6, 0.8)
        c.fill(x0 + 3, ybot - u["max_cm"] * k * f, x1 - 3, ybot - 3, "#9FC4E0")
        c.fill(x0 + 3, ybot - u["direct_cm"] * k * f, x1 - 3, ybot - 3, BLUE)
        labs = self.words["urmia_labels"]
        self.line(c, ytop + 40, labs[0], 38, True)
        self.line(c, ybot - 4, labs[1], 38, True)
        mid = (ytop + ybot) / 2
        # a bracket from the gauge to the label
        c.fill(x1 + 14, ytop + 3, x1 + 17, ybot - 3, th.ink)
        c.fill(x1 + 14, mid - 1.5, x1 + 40, mid + 1.5, th.ink)
        self.line(c, mid + 14, labs[4], 40, True, x=x1 + 52, anchor="ls")
        if f >= 1.0:
            self.line(c, ybot - 130, labs[2], 38, True, BLUE)
            self.line(c, ybot - 72, labs[3], 36, False, "#4F86B0")
            for s_, z_, f_ in ((labs[2], 38, FA_BOLD), (labs[3], 36, FA_TEXT), (labs[1], 38, FA_BOLD)):
                assert RIGHT - c.width(s_, f_, z_, "rtl") > x1 + 26, s_          # clear of the bracket

    def s_end(self, c: Canvas, dt: float):
        th = self.th
        c.frame(LEFT, 730, RIGHT, 1080, fill="#F7F2EA", colour=th.ink)
        for k, s in enumerate(self.words["quote_end"]):
            c.text(MIDX, 830 + 76 * k, s, FA_BOLD, 50, th.ink, "ms", "rtl")
            assert c.width(s, FA_BOLD, 50, "rtl") <= RIGHT - LEFT - 40, s
        c.text(MIDX, 1030, self.words["quote_end_by"], FA_TEXT, 34, th.ink, "ms", "rtl")
        if self.on(dt, 0.8):
            c.text(MIDX, 1230, self.words["end_line"], FA_BOLD, 46, HOT, "ms", "rtl")
            assert c.width(self.words["end_line"], FA_BOLD, 46, "rtl") <= RIGHT - LEFT


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--at", type=float, nargs="*")
    args = ap.parse_args()
    film = DamsFilm(onebit.THEMES["kahgel"], COLOURS["kahgel"])
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / BASE
    film.draw(1, COVER_T).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills or args.at:
        times = args.at or sorted({0.0} | {round(float(film.starts[i] + f * (film.starts[i + 1] - film.starts[i])), 2)
                                           for i in range(len(SECONDS)) for f in (0.35, 0.95)})
        if not args.at:
            for old in (OUT / "social").glob(f"{BASE}_t*.png"):
                old.unlink()
        for t in times:
            film.draw(1, t).save(f"{base}_t{t:05.2f}.png")
            print("saved", f"{base}_t{t:05.2f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
