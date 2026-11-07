"""HAMOUN: «هامون بیش از پنج تهران بود؛ بهارِ امسال، حدودِ یک تهران». A full-screen 3D reel: the Hamoun lakes
in Sistan every spring 1366-1405 (1987-2026) from Landsat, the measured open water tinted blue on each spring's true
colour, the city of Tehran drawn to scale on the ground, the area on a counter and in forty bars.

Layers: the 3D frames of src/hamoun3d.py (data/hamoun/reel/frames/, 30 a second, with each frame's camera
projection), and on top the Persian type drawn here: a gold two-line headline (Lalezar), the year chip, the counter
(km2 of water in late spring) and its unit, a slim strip of bars of every spring, the measured water's outline (a
thin cyan line: the photo keeps its own colours, the water under only a light tint), the shore of the full lake of
spring 1371 as a faint line, the outline of Tehran with its label, the place names, one sources line, and in the
narrated cut the
subtitles (their times measured from the voice: data/hamoun/reel/narration/manifest.json, onebit_score_hamoun).
Every number on screen comes from data/hamoun/reel/timeline.json (src/hamounreel.py), asserted here. A spring whose
picture is not clean keeps its number; its picture (the last clean one) goes under a light veil with a note.

    0.0 s          the end state: 1405 with Tehran beside its water, the hook, the counter at 1405's value
    1.6-2.8 s      the rewind; 2.8-15.95 s the springs, 1366-1405 (runs A, A2, B, C); 4.3 s the full lake (1372)
    4.3, 5.9, 7.5, 11.45, 16.0, 20.3, 23.85 s   the cards C1, C1b, low, C2, flood, C3, C4
    26 s           the camera is back at its first frame (a loop)

    python -I src/onebit_hamoun.py --stills          # cover and stills
    python -I src/onebit_hamoun.py                   # the silent reel (music-only cut, no subtitles)
    python -I src/onebit_hamoun.py --voice           # the narrated cut's picture (subtitles)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps  # noqa: E402

import onebit  # noqa: E402
from onebit import FONTS, OUT, SIZES, SOCIAL_CRF, fa  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data" / "hamoun" / "reel"
W, H = 1080, 1920
LALEZAR = FONTS / "lalezar" / "Lalezar-Regular.ttf"
BLACK = FONTS / "vazirmatn" / "Vazirmatn-Black.ttf"
XBOLD = FONTS / "vazirmatn" / "Vazirmatn-ExtraBold.ttf"
MEDIUM = FONTS / "vazirmatn" / "Vazirmatn-Medium.ttf"
GOLD, WHITE, INK = (255, 205, 60, 255), (255, 255, 255, 255), (16, 10, 6, 255)
WATER_INK = (90, 185, 245, 255)
CORAL = (255, 120, 95, 255)
SAFE = (60, 1020)
Y_TITLE = (190, 324)
Y_NOTE = 414
BARS = (170, 910, 1092, 56)                        # px: left, right, baseline, the height of the lakes' whole bed
Y_CHIP, Y_COUNTER, Y_UNIT = 1158, 1305, 1366
Y_SUB = (1458, (1440, 1492))                       # the subtitle's baseline: one line, two lines
Y_SOURCES = (1556, 1590)
CARDS = dict(
    hook=("هامون بیش از پنج تهران بود؛", "بهارِ امسال، حدودِ یک تهران"),
    c1=("هامونِ پُر:", "بیش از پنج برابرِ شهرِ تهران"),
    c1b=("در بهارهای پُرآب،", "حدودِ ۴٬۰۰۰ کیلومتر مربع"),
    low=("بعد، کم و زیاد شد؛", "گاهی تقریباً بی‌آب"),
    c2=("در اواخرِ بهارِ ده سالِ آخر،", "پنج بار زیرِ ۱۰۰ کیلومتر مربع"),
    flood=("امسال، سیلاب‌های فصلی", "بخشی از هامون را پُر کرد"),
    c3=("حدودِ یک تهران؛", "حدودِ یک‌هفتمِ هامونِ پُر"),
    c4=("هامونِ پُر را", "شما دیده‌اید؟"),
)
NOTE = "مساحت: کلِ هامون، در دو سوی مرز"
UNIT = "کیلومتر مربع آب، اواخرِ بهار"
HELD = "تصویرِ صافی از این بهار نیست؛ عدد از همین بهار است"
HELD_GAP = "تصویرِ صافی و عددِ مطمئنی از این بهار نیست"
HELD_MIN = 0.6                                     # s: the note shows only over a run of held springs this long
GAP = "عددِ مطمئنی نیست"
TEHRAN = ("شهرِ تهران", "به همین مقیاس")
PLACES = dict(zabol="زابل", chahnimeh="مخازنِ چاه‌نیمه")
SOURCES = ("تصویر: لندست ۴، ۵، ۷، ۸ و ۹ (USGS و NASA)؛ سنجیده با JRC؛ مرزِ تهران: OpenStreetMap",
           "زمین: Copernicus DEM (ارتفاع‌ها ۳ برابر)؛ پیرامون: Sentinel-2 cloudless (EOX)")
X_TITLE = 495                                      # the headline's centre: its ink, stroke included, inside x 60-930
TITLE_BOX = (60, 930)
FADE = 0.25                                         # s: the outline of Tehran fades in and out
VEIL = 0.75                                         # the veil over a held picture (a spring without a clean one)
CYAN = (120, 235, 255, 255)                         # the outline of each spring's measured water


def font(path: Path, px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), px)


def width(s: str, path: Path, px: int) -> float:
    return font(path, px).getlength(s, direction="rtl", language="fa")


def text(d: ImageDraw.ImageDraw, x, y, s, path, px, fill=WHITE, stroke=6, anchor="ms"):
    d.text((x, y), s, font=font(path, px), fill=fill, anchor=anchor, direction="rtl", language="fa",
           stroke_width=stroke, stroke_fill=INK)


def pill(d, x, y, s, path, px, fill=(0, 0, 0, 170), colour=WHITE, pad=20):
    w = width(s, path, px)
    d.rounded_rectangle([x - w / 2 - pad, y - px * 1.05, x + w / 2 + pad, y + px * 0.42], radius=px * 0.45, fill=fill)
    text(d, x, y, s, path, px, colour, stroke=0)


def ink(s: str, px: int, x: float = X_TITLE) -> tuple:
    """The left and right edges of a headline line's ink at x, its stroke included."""
    b = ImageDraw.Draw(Image.new("RGBA", (8, 8))).textbbox((x, 300), s, font=font(LALEZAR, px), anchor="ms",
                                                          direction="rtl", language="fa", stroke_width=7)
    return b[0], b[2]


def ink_fit(s: str, px: int = 96) -> int:
    """The largest size up to px (steps of 4) at which the line's ink stays inside TITLE_BOX."""
    while px > 40:
        a, b = ink(s, px)
        if a >= TITLE_BOX[0] and b <= TITLE_BOX[1]:
            return px
        px -= 4
    raise AssertionError(s)


def same(sub: str, card: str) -> bool:
    """A subtitle the card already says: the same words, or one holding all of the other's (two words more at most)."""
    a, b = set(plain(sub).split()), set(plain(card).split())
    return a <= b or (b <= a and len(a - b) <= 2)


def plain(s: str) -> str:
    """A line without its punctuation and extra spaces (to compare a subtitle with the card on screen)."""
    return " ".join(s.translate(str.maketrans("", "", "،؛:.؟!")).split())


def fit(s: str, path: Path, px: int, room: float) -> int:
    """The largest size up to px (in steps of 4) at which s fits in room px."""
    while width(s, path, px) > room and px > 40:
        px -= 4
    assert width(s, path, px) <= room, s
    return px


class HamounFilm:
    def __init__(self, voice: bool):
        self.voice = voice
        self.tl = tl = json.loads((DATA / "timeline.json").read_text())
        meta = json.loads((DATA / "frames" / "frames.json").read_text())
        self.geo, self.meta = meta["geo"], meta["frames"]
        self.n = len(self.meta)
        assert self.n == round(tl["duration"] * tl["fps"]), ("render the 3D frames first", self.n)
        assert tl["full_shown"] == 4000 and 4000 <= tl["full_lo"] <= 4200 and tl["shown_2026"] == 560
        assert tl["dry_last10"] == [2018, 2021, 2022, 2023, 2025]
        assert min(tl["full_lo"], 3802) / 750.0 > 5.0, "more than five Tehrans on every quoted area"
        self.steps = [s for r in tl["runs"] for s in r["steps"]]
        assert [s["year"] for s in self.steps] == list(range(tl["first"], tl["last"] + 1))
        self.pics = set(tl["pictures"])
        self.L = type("L", (), {"end": tl["duration"]})()
        self.subs = []
        if voice:
            man = json.loads((DATA / "narration" / "manifest.json").read_text(encoding="utf-8"))
            self.subs = [(x["start"], x["end"], x["text"]) for m in man for x in m["subtitles"]]
        self.card_px = {}                                  # one size per card: both lines' ink inside TITLE_BOX
        for k, v in CARDS.items():
            px = min(ink_fit(s) for s in v)
            assert px >= 84, (k, px)
            self.card_px[k] = [px, px]
        for s in SOURCES:
            assert width(s, MEDIUM, 22) <= 828, s
        self.sub_lines = {s: self.sub_layout(s) for _, _, s in self.subs}

    @staticmethod
    def sub_layout(s: str) -> list:
        """A subtitle as [(line, px)]: one line at 40 px down to 34, else two lines split at the comma nearest the
        middle; the pill stays clear of the Reels buttons (x 930)."""
        room = 2 * (930 - 20 - 540)
        for px in (40, 38, 36, 34):
            if width(s, XBOLD, px) <= room:
                return [(s, px)]
        cut = [k for k, c in enumerate(s) if c in "،؛" and 0.35 <= k / len(s) <= 0.65]
        cut = cut or [k for k, c in enumerate(s) if c == " "]          # no comma near the middle: a space
        k = min(cut, key=lambda k: abs(k - len(s) / 2))
        a, b = s[:k + 1].strip(), s[k + 1:].strip()
        px = min(fit(a, XBOLD, 38, room), fit(b, XBOLD, 38, room))
        return [(a, px), (b, px)]

    # ── the clock ──
    def step_at(self, t: float):
        """The spring on the counter at t: the end state (1405) before the rewind, none during it."""
        tl = self.tl
        if t < tl["rewind"]:
            return self.steps[-1]
        if t < tl["run_a"]:
            return None
        return [s for s in self.steps if s["t"] <= t + 1e-6][-1]

    def card(self, t: float) -> str:
        return [k for t0, k in self.tl["cards"] if t0 <= t][-1]

    def tehran_alpha(self, t: float) -> float:
        for a, b in self.tl["tehran_shown"]:
            if a <= t <= b:
                fin = 1.0 if a == 0.0 else min(1.0, (t - a) / FADE)
                fout = 1.0 if b >= self.tl["duration"] else min(1.0, (b - t) / FADE)
                return max(0.0, min(fin, fout))
        return 0.0

    def held_run(self, st: dict) -> float:
        """How long (s) the run of consecutive held springs that holds st lasts on screen."""
        k = self.steps.index(st)
        held = lambda s: s["year"] not in self.pics  # noqa: E731
        a = b = k
        while a > 0 and held(self.steps[a - 1]):
            a -= 1
        while b < len(self.steps) - 1 and held(self.steps[b + 1]):
            b += 1
        nxt = self.steps[b + 1]["t"] if b + 1 < len(self.steps) else self.tl["duration"]
        return nxt - self.steps[a]["t"]

    # ── projection ──
    def frame(self, t: float):
        k = min(max(round(t * self.tl["fps"]), 0), self.n - 1)
        return Image.open(DATA / "frames" / f"f_{k:04d}.png").convert("RGBA"), self.meta[k]

    @staticmethod
    def project(m: dict, pts) -> np.ndarray:
        P = np.array(m["proj"])
        p = np.c_[np.asarray(pts, float), np.ones(len(pts))] @ P.T
        ndc = p[:, :3] / p[:, 3:4]
        return np.c_[(ndc[:, 0] + 1) / 2 * W, (1 - (ndc[:, 1] + 1) / 2) * H]

    # ── the frame ──
    def draw(self, s: int = 1, t: float = 0.0, size=SIZES["reel"]) -> Image.Image:
        t = 0.0 if not np.isfinite(t) else t
        tl = self.tl
        im, m = self.frame(t)
        held = min(1.0, sum(w for y, w in m["mix"] if y not in self.pics))
        if held > 0:                                       # a spring without a clean picture: grey, under a veil
            im = Image.blend(im, ImageOps.grayscale(im).convert("RGBA"), held)
            im.alpha_composite(Image.new("RGBA", (W, H), (10, 8, 6, int(VEIL * 255 * held))))
        self.ground(im, t, m, labels=held <= 0.5)
        shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shade)
        for y in range(0, 440):
            sd.line([(0, y), (W, y)], fill=(0, 0, 0, int(120 * (1 - y / 440))))
        for y in range(1040, H):
            sd.line([(0, y), (W, y)], fill=(0, 0, 0, int(205 * min(1, (y - 1040) / 220))))
        im.alpha_composite(shade)
        type_ = Image.new("RGBA", (W, H), (0, 0, 0, 0))   # the type on its own layer (translucent pills and bars)
        d = ImageDraw.Draw(type_)
        key = self.card(t)
        lines = CARDS[key]
        px = self.card_px[key]
        text(d, X_TITLE, Y_TITLE[0], lines[0], LALEZAR, px[0], GOLD, 7)
        text(d, X_TITLE, Y_TITLE[1], lines[1], LALEZAR, px[1], GOLD if key == "hook" else WHITE, 7)
        text(d, 540, Y_NOTE, NOTE, XBOLD, 30, WHITE, 4)
        st = self.step_at(t)
        if held > 0.5 and st is not None and self.held_run(st) >= HELD_MIN:
            pill(d, 540, 700, HELD_GAP if st["gap"] else HELD, XBOLD, 30, fill=(0, 0, 0, 190))
        self.bars(d, t)
        if st is not None:
            pill(d, 540, Y_CHIP, f"بهارِ {fa(st['label'])}", BLACK, 44, fill=(255, 205, 60, 235), colour=INK)
            if st["gap"]:                                  # no trusted number: the note in the counter's place
                text(d, 540, Y_COUNTER - 40, GAP, XBOLD, 40, WHITE, 5)
            else:
                text(d, 540, Y_COUNTER, fa(f"{st['shown']:,}"), LALEZAR, 170, WHITE, 8)
            text(d, 540, Y_UNIT, UNIT, BLACK, 44, WHITE, 5)
        if self.voice:
            sub = [x for x in self.subs if x[0] <= t < x[1]]
            if sub and same(sub[0][2], " ".join(lines)):   # the card says it already
                sub = []
            if sub:
                lay = self.sub_lines[sub[0][2]]
                ys = [Y_SUB[0]] if len(lay) == 1 else Y_SUB[1]
                for (line, px), y in zip(lay, ys):
                    pill(d, 540, y, line, XBOLD, px)
        for k, s_ in enumerate(SOURCES):
            text(d, 925, Y_SOURCES[k], s_, MEDIUM, 22, (225, 230, 236, 255), 3, anchor="rs")
        im.alpha_composite(type_)
        return im.convert("RGB").resize(size, Image.LANCZOS) if tuple(size) != (W, H) else im.convert("RGB")

    def ground(self, im: Image.Image, t: float, m: dict, labels: bool = True):
        """On the ground: the shore of the full lake (a white line with a soft glow), the outline of Tehran to scale
        (gold) and the place names, projected through the frame's camera."""
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        g = ImageDraw.Draw(glow)
        lines = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lines)
        for s in self.geo["shore"]:
            p = [tuple(q) for q in self.project(m, s)]
            ld.line(p, fill=(255, 255, 255, 120), width=2, joint="curve")
        for year, w in m["mix"]:                           # the measured water's outline, faded with its picture
            if str(year) not in self.geo["water"] or w <= 0.02:
                continue
            for s in self.geo["water"][str(year)]:
                p = [tuple(q) for q in self.project(m, s)]
                g.line(p, fill=(90, 220, 255, int(200 * w)), width=9, joint="curve")
                ld.line(p, fill=CYAN[:3] + (int(255 * w),), width=3, joint="curve")
        im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(4)))
        im.alpha_composite(lines)
        a = self.tehran_alpha(t)
        if a > 0:
            p = [tuple(q) for q in self.project(m, self.geo["tehran"])]
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lay)
            ld.polygon(p, fill=(255, 205, 60, 60))
            ld.line(p + [p[0]], fill=GOLD, width=4, joint="curve")
            cx, cy = np.mean(np.array(p), axis=0)
            text(ld, cx, cy + 4, TEHRAN[0], BLACK, 32, WHITE, 5)
            text(ld, cx, cy + 40, TEHRAN[1], XBOLD, 24, WHITE, 4)
            if a < 1:
                lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
            im.alpha_composite(lay)
        d = ImageDraw.Draw(im)
        for k, name in (PLACES.items() if labels else ()):     # not under the veil's note
            x, y = self.project(m, [self.geo["places"][k]])[0]
            if not (90 < x < 1060 and 470 < y < 1040):
                continue
            if k == "zabol":
                w = width(name, BLACK, 30)
                if x - 12 - w < 70 or x > 925:
                    continue
                d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=WHITE, outline=INK, width=2)
                text(d, x - 12, y + 10, name, BLACK, 30, WHITE, 5, anchor="rs")
            else:                                          # under the reservoirs, inside x 70-925
                w = width(name, XBOLD, 24)
                cx = min(max(x, 70 + w / 2), 925 - w / 2)
                text(d, cx, y + 34, name, XBOLD, 24, (215, 235, 225, 255), 4)

    def bars(self, d: ImageDraw.ImageDraw, t: float):
        """A slim strip of every spring from 1364 (right) to 1405 (left): the bars shown so far in a soft white, the
        current one gold; a spring without a number (no scene, or no trusted number) an empty slot; from card C2 on the
        five dry springs of the last ten a small coral dot under them; the two end years only."""
        tl = self.tl
        x0, x1, base, hmax = BARS
        bars = tl["bars"]
        slot = (x1 - x0) / len(bars)
        bw = slot * 0.62
        if t < tl["rewind"]:
            upto, alpha = tl["last"], 1.0
        elif t < tl["run_a"]:
            upto, alpha = tl["last"], max(0.0, 1 - (t - tl["rewind"]) / 0.5)
        else:
            upto, alpha = self.step_at(t)["year"], 1.0
        if alpha <= 0:
            return
        cur = self.step_at(t)
        c2 = [t0 for t0, k in tl["cards"] if k == "c2"][0]
        for i, b in enumerate(bars):
            xr = x1 - i * slot
            xl = xr - bw
            if b["year"] > upto or b["km2"] is None:
                continue
            h = max(1.5, hmax * b["km2"] / tl["lakes_km2"]["total"])
            on = cur is not None and b["year"] == cur["year"]
            d.rectangle([xl, base - h, xr, base], fill=GOLD if on else (255, 255, 255, int(120 * alpha)))
            if t >= c2 and b["year"] in tl["dry_last10"]:
                cx = (xl + xr) / 2
                d.ellipse([cx - 3, base + 6, cx + 3, base + 12], fill=CORAL)
        d.line([(x0 - 4, base + 1), (x1 + 2, base + 1)], fill=(255, 255, 255, int(80 * alpha)), width=1)
        lab = (225, 225, 225, int(200 * alpha))
        text(d, x1 + 2, base + 30, fa(bars[0]["label"]), XBOLD, 20, lab, 3, anchor="rs")
        text(d, x0 - 4, base + 30, fa(bars[-1]["label"]), XBOLD, 20, lab, 3, anchor="ls")

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true", help="cover and stills only")
    ap.add_argument("--voice", action="store_true", help="the narrated cut's picture (with subtitles)")
    args = ap.parse_args()
    film = HamounFilm(args.voice)
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / ("hamoun_fa_voice" if args.voice else "hamoun_fa")
    for old in (OUT / "social").glob(f"{base.name}_t*.png"):
        old.unlink()
    film.draw(1, 0.0).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        for t in (0.0, 2.2, 4.8, 6.5, 7.6, 8.1, 9.2, 10.0, 13.6, 17.0, 21.5, 24.5):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
