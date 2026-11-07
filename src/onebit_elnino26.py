"""EL NIÑO 2026: «النینوی بسیار قوی آمده؛ یعنی طوفانِ نوح؟» A 30-s reel: the globe with this year's warm Pacific
(src/elnino26_3d.py), the ONI of Aug-Oct 2026 (+2.46, the highest for that season since 1950), then the answer from
75 years of Iran's rain (src/enso.py, CRU TS 4.10): 21 of 26 El Niño autumns were wetter than the median, the
strong ones 4 of 6, the winters 11 of 22. One drop per season. Numbers from data/elnino26/timeline.json, asserted.

    python -I src/onebit_elnino26.py --stills     # cover and stills
    python -I src/onebit_elnino26.py              # the music cut's picture
    python -I src/onebit_elnino26.py --voice      # the narrated cut's picture (subtitles)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import onebit  # noqa: E402
from onebit import OUT, SIZES, SOCIAL_CRF, fa  # noqa: E402
from onebit_subsidence import (BLACK, GOLD, INK, LALEZAR, MEDIUM, SAFE, WHITE, XBOLD, ease, font,  # noqa: E402
                               pill, split, text, width)

DATA = Path(__file__).resolve().parents[1] / "data" / "elnino26"
W, H = 1080, 1920
Y_TITLE, Y_NOTE, Y_KEY = (190, 324), 414, 452
Y_DROPS = (1112, 1186)                              # the two rows of drops (centres)
Y_CHIP, Y_COUNTER, Y_UNIT = 1150, 1318, 1384
Y_SUB, Y_SOURCES = 1478, (1556, 1590)
BLUE, GREY, RING = (110, 190, 255, 255), (150, 156, 165, 255), (255, 205, 60, 255)
HOOK = ("النینوی بسیار قوی آمده؛", "یعنی طوفانِ نوح؟")
NOTE_SEA = "رنگی: دریای بیش از ۱٫۵ درجه گرم‌تر از معمول، ۱۶ تا ۲۲ اکتبر ۲۰۲۶"
NOTE_RAIN = "بارشِ ایران، ۱۹۵۱ تا ۲۰۲۴؛ «پرباران‌تر» یعنی بیش از میانه‌ی همان فصل"
UNIT_ONI = "درجه گرم‌تر از معمول: مرکز و شرقِ اقیانوسِ آرامِ استوایی"
CHIP_ONI = "مرداد تا مهرِ ۱۴۰۵"
SOURCES = ("منبع: شاخصِ ONI و دمای OISST (نوآ)؛ بارش: CRU TS 4.10 (دانشگاه ایست‌آنگلیا)",
           "تصویر: Sentinel-2 cloudless (EOX)؛ مرز: Natural Earth")
SUBTITLES = ((0.15, 2.80, "النینو برگشته؛ و این بار خیلی قوی."),
             (3.10, 7.75, "آبِ مرکزِ اقیانوسِ آرام، دو و نیم درجه گرم‌تر از معمول شد."),
             (8.50, 10.70, "برای بارانِ ایران یعنی چه؟"),
             (11.50, 16.08, "۲۱ پاییز از ۲۶ پاییزِ النینو، پرباران‌تر از معمول بود."),
             (16.12, 19.45, "ولی النینوی قوی‌تر، بارانِ بیشتر نیاورد."),
             (19.50, 22.95, "زمستان‌ها نیمی پرباران‌تر بود، نیمی کم‌باران‌تر."),
             (23.00, 26.40, "شانسِ پاییزِ پرباران بالا می‌رود؛ نه طوفانِ نوح."),
             (26.50, 29.50, "پاییزِ امسال در شهرِ شما چطور بوده؟"))


class ElNinoFilm:
    def __init__(self, voice: bool):
        self.voice = voice
        self.tl = tl = json.loads((DATA / "timeline.json").read_text())
        self.meta = json.loads((DATA / "frames" / "frames.json").read_text())
        self.n = len(self.meta)
        assert self.n == round(tl["duration"] * tl["fps"]), ("render the 3D frames first", self.n)
        au, wi = tl["autumn"], tl["winter"]
        assert (au["wetter"], au["n"], wi["wetter"], wi["n"], au["strong_wetter"], len(au["strong"])) == (21, 26, 11, 22, 4, 6)
        assert tl["oni_rank"] == 1 and 2.4 <= tl["oni_now"] <= 2.5 and tl["oni_shown"] == 2.5
        assert not au["wet"]["2023"]
        self.L = type("L", (), {"end": tl["duration"]})()
        self.beats = [(0.0, HOOK),
                      (tl["land"], ("یکی از قوی‌ترین النینوها", "برای این وقتِ سال، از ۱۹۵۰")),
                      (tl["turn"][0], ("برای بارانِ ایران", "چه معنایی دارد؟")),
                      (tl["autumn_at"], ("در ۲۱ پاییز از ۲۶ پاییزِ النینو،", "ایران پرباران‌تر از معمول بود")),
                      (tl["strong_at"], ("النینوهای قوی: ۴ از ۶ پرباران‌تر؛", "پاییزِ ۲۰۲۳ (۱۴۰۲) کم‌باران‌تر بود")),
                      (tl["winter_at"], ("زمستان‌ها: ۱۱ از ۲۲؛", "نیمی بله، نیمی نه")),
                      (tl["verdict_at"], ("شانسِ پاییزِ پرباران بالا می‌رود؛", "نه طوفانِ نوح")),
                      (tl["question_at"], ("پاییزِ امسال تا امروز", "در شهرِ شما چطور بوده؟"))]
        for _, lines in self.beats:
            for s in lines:
                assert 540 + width(s, LALEZAR, self.size(lines)) / 2 + 7 <= 930, s
        for s in SOURCES:
            assert width(s, MEDIUM, 22) <= 828, s
        for s in (NOTE_SEA, NOTE_RAIN):
            assert width(s, XBOLD, 26) <= 860, s
        self.subs = [p for a, b, s in SUBTITLES for p in split(a, b, s)]
        for _, _, s in self.subs:
            assert 540 + width(s, XBOLD, 40) / 2 + 20 <= 930, s
        man = DATA / "narration" / "manifest.json"
        if voice:                                           # the subtitles are the spoken sentences, on time
            m = json.loads(man.read_text())
            assert [x["text"] for x in m] == [s for _, _, s in SUBTITLES], "subtitles vs the narration"
            for k, (x, (a, b, _)) in enumerate(zip(m, SUBTITLES)):
                hold = 1.0 if k == len(SUBTITLES) - 1 else 0.4
                assert abs(x["start"] - a) < 0.05 and x["end"] <= b <= x["end"] + hold, (x["name"], x["start"], x["end"], a, b)

    @staticmethod
    def size(lines) -> int:
        """96 px, or smaller so the longer line fits inside x 60-930 with its stroke."""
        w = max(width(s, LALEZAR, 96) for s in lines)
        return min(96, int(96 * 766 / w))                 # 540 + w/2 + 7 <= 930

    def beat(self, t):
        return [b for b in self.beats if b[0] <= t][-1]

    def frame(self, t):
        k = min(max(round(t * self.tl["fps"]), 0), self.n - 1)
        return Image.open(DATA / "frames" / f"f_{k:04d}.png").convert("RGBA"), self.meta[k]

    def draw(self, s: int = 1, t: float = 0.0, size=SIZES["reel"]) -> Image.Image:
        tl = self.tl
        t = 0.0 if not np.isfinite(t) else t
        im, m = self.frame(t)
        shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shade)
        for y in range(0, 500):
            sd.line([(0, y), (W, y)], fill=(0, 0, 0, int(130 * (1 - y / 500))))
        for y in range(1040, H):
            sd.line([(0, y), (W, y)], fill=(0, 0, 0, int(175 * min(1, (y - 1040) / 360))))
        im.alpha_composite(shade)
        d = ImageDraw.Draw(im)
        _, lines = self.beat(t)
        px = self.size(lines)
        text(d, 540, Y_TITLE[0], lines[0], LALEZAR, px, GOLD, 7)
        text(d, 540, Y_TITLE[1], lines[1], LALEZAR, px, GOLD if lines is HOOK else WHITE, 7)
        sea = t < tl["autumn_at"] or t >= tl["question_at"] + 1.2
        text(d, 540, Y_NOTE, NOTE_SEA if sea else NOTE_RAIN, XBOLD, 26, WHITE, 4)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        if sea:
            self.key(ld)
        self.labels(ld, t, m)
        self.drops(ld, t)
        im.alpha_composite(layer)
        d = ImageDraw.Draw(im)
        self.counter(d, t)
        if self.voice:
            sub = [x for a, b, x in self.subs if a <= t < b]
            if sub:
                pill(d, 540, Y_SUB, sub[0], XBOLD, 40)
        for k, s in enumerate(SOURCES):
            text(d, 925, Y_SOURCES[k], s, MEDIUM, 22, (225, 230, 236, 255), 3, anchor="rs")
        return im.convert("RGB").resize(size, Image.LANCZOS) if tuple(size) != (W, H) else im.convert("RGB")

    def key(self, d):
        """The sea key: 1.5 to 5 °C warmer than normal (the 3D layer's colours), read from the right."""
        stops = ((1.5, (255, 200, 70)), (2.0, (255, 170, 50)), (3.0, (250, 110, 35)), (4.0, (235, 45, 45)),
                 (5.0, (205, 20, 100)))
        x0, x1, h = 380, 700, 14
        for x in range(x0, x1):
            v = 1.5 + (x1 - 1 - x) / (x1 - 1 - x0) * 3.5
            c = [np.interp(v, [s[0] for s in stops], [s[1][k] for s in stops]) for k in range(3)]
            d.line([(x, Y_KEY), (x, Y_KEY + h)], fill=tuple(int(q) for q in c) + (255,))
        d.rectangle([x0 - 1, Y_KEY - 1, x1, Y_KEY + h + 1], outline=(255, 255, 255, 200), width=2)
        for v in (2, 3, 4, 5):
            x = x1 - (x1 - x0) * (v - 1.5) / 3.5
            text(d, x, Y_KEY + h + 28, fa(v) + ("+" if v == 5 else ""), BLACK, 24, WHITE, 4)
        text(d, x1 + 14, Y_KEY + h - 1, "درجه", XBOLD, 24, WHITE, 4, anchor="ls")

    def labels(self, d, t, m):
        tl = self.tl
        for name, txt, show in (("nino", "النینو", t < tl["turn"][0] + 1.0 or t > tl["question_at"] + 2.0),
                                ("iran", "ایران", tl["turn"][1] - 1.0 <= t < tl["question_at"] + 1.5)):
            x, y, z, front = m["marks"][name]
            if not (show and front and 70 < x < 1010 and 520 < y < 1060):
                continue
            w = width(txt, BLACK, 34)
            r = 7
            d.ellipse([x - r, y - r, x + r, y + r], outline=WHITE, width=3)
            lx = min(max(x - w / 2, SAFE[0]), 925 - w)
            d.text((lx + w, y - 20), txt, font=font(BLACK, 34), fill=WHITE, anchor="rs", direction="rtl",
                   language="fa", stroke_width=5, stroke_fill=INK)

    def drops(self, d, t):
        """One drop per El Niño season, oldest on the right: filled blue = wetter than the median, grey = drier;
        the strong ones ringed in gold from strong_at."""
        tl = self.tl
        if tl["autumn_at"] <= t < tl["winter_at"]:
            sea, t0 = tl["autumn"], tl["autumn_at"]
        elif tl["winter_at"] <= t < tl["verdict_at"]:
            sea, t0 = tl["winter"], tl["winter_at"]
        else:
            return
        years = sea["years"]
        n = len(years)
        per = math.ceil(n / 2)
        gap = 58
        for k, y in enumerate(years):
            a = ease((t - t0 - 0.06 * k) / 0.2)
            if a <= 0:
                continue
            row, col = divmod(k, per)
            x = 540 + (per - 1) / 2 * gap - col * gap      # right to left
            cy = Y_DROPS[row]
            wet = sea["wet"][str(y)]
            strong = sea is tl["autumn"] and y in tl["autumn"]["strong"] and t >= tl["strong_at"]
            dim = sea is tl["autumn"] and t >= tl["strong_at"] and not strong
            col_ = BLUE if wet else GREY
            alpha = int(255 * a * (0.35 if dim else 1.0))
            fill = col_[:3] + (alpha,) if wet else (0, 0, 0, 0)
            outline = col_[:3] + (alpha,)
            r = 15
            d.ellipse([x - r, cy - r + 6, x + r, cy + r + 6], fill=fill, outline=outline, width=3)
            d.polygon([(x - r * 0.87, cy - 1), (x, cy - 2.2 * r + 6), (x + r * 0.87, cy - 1)], fill=fill,
                      outline=outline)
            if strong:
                d.ellipse([x - 25, cy - 30, x + 25, cy + 26], outline=RING[:3] + (int(255 * a),), width=3)

    def counter(self, d, t):
        tl = self.tl
        if t < 1.0:
            text(d, 540, Y_COUNTER, "؟", LALEZAR, 160, WHITE, 8)
            return
        if t < tl["autumn_at"] or t >= tl["question_at"] + 1.2:
            v = tl["oni_shown"] * ease((t - 1.0) / (tl["land"] - 1.0)) if t < tl["land"] else tl["oni_shown"]
            pill(d, 540, Y_CHIP - 40, CHIP_ONI, BLACK, 40, fill=(255, 205, 60, 235), colour=INK)
            text(d, 540, Y_COUNTER, "+" + fa(f"{v:.1f}").replace(".", "٫"), LALEZAR, 160, WHITE, 8)
            text(d, 540, Y_UNIT, UNIT_ONI, BLACK, 40, WHITE, 5)
            return
        if t < tl["winter_at"]:
            au = tl["autumn"]
            big = f"{fa(au['strong_wetter'])} از {fa(len(au['strong']))}" if t >= tl["strong_at"] else \
                f"{fa(au['wetter'])} از {fa(au['n'])}"
            unit = "النینوهای قوی (۱٫۵ درجه یا بیشتر)" if t >= tl["strong_at"] else "پاییزهای النینو، پرباران‌تر از معمول"
        elif t < tl["verdict_at"]:
            big = f"{fa(tl['winter']['wetter'])} از {fa(tl['winter']['n'])}"
            unit = "زمستان‌های النینو، پرباران‌تر از معمول"
        else:
            return
        text(d, 540, Y_COUNTER, big, LALEZAR, 130, WHITE, 8)
        text(d, 540, Y_UNIT, unit, BLACK, 38, WHITE, 5)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--voice", action="store_true")
    args = ap.parse_args()
    film = ElNinoFilm(args.voice)
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / ("elnino26_fa_voice" if args.voice else "elnino26_fa")
    for old in (OUT / "social").glob(f"{base.name}_t*.png"):
        old.unlink()
    film.draw(1, 0.0).save(f"{base}_cover.png", optimize=True)
    if args.stills:
        for t in (0.0, 3.5, 6.5, 10.5, 14.8, 17.5, 21.0, 24.5, 28.0):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
        print("saved stills of", base.name)
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
