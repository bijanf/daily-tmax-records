"""SINKING GROUND: «زیرِ پای کدام شهرها زمین پایین می‌رود؟» A full-screen 3D reel: the vertical land-subsidence rate
2014-2020 over Iran from Sentinel-1 radar (Haghshenas Haghighi & Motagh 2024, 100 m; checked against Payne et al.
2025), glowing on the photoreal country; the camera dives from all of Iran to the Tehran-Karaj plain and back.

Layers: the 3D frames of src/subsidence3d.py (data/subsidence/frames/, 30 a second, with the screen positions of the
labels), and on top the Persian type drawn here: a gold two-line headline (Lalezar), a line naming the measurement
and its period, the colour key, the counter with its chip, the town labels, one sources line, and in the narrated
cut the subtitles. Every number comes from data/subsidence/timeline.json (src/subsidence.py), asserted here.

    0.0 s        the end state: Iran glowing, the hook, the counter «؟», the newest headline (Karaj) over the map
    1.2-7.8 s    the counter counts the sinking area up while the labels appear; 7.8 s it lands: ۵۶٬۰۰۰ km2;
                 the headline leaves at 2.2-2.6 s
    8.6-13.0 s   the dive to the Tehran-Karaj plain; 13.0 s: up to 15-20 cm a year
    17.6 s       the cause; 20.5-26 s back out to Iran, 23.4 s the question
    26-31 s      the news: three headlines over the dimmed map (Karaj, south-west Tehran, Kerman); 30.4-31 s the
                 end eases into frame 0 (the Karaj card stays where it opens the reel): a loop

    python -I src/onebit_subsidence.py --stills          # cover and stills
    python -I src/onebit_subsidence.py                   # the silent reel (music-only cut, no subtitles)
    python -I src/onebit_subsidence.py --voice           # the narrated cut's picture (subtitles)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

import onebit  # noqa: E402
from onebit import FONTS, OUT, SIZES, SOCIAL_CRF, fa  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data" / "subsidence"
W, H = 1080, 1920
LALEZAR = FONTS / "lalezar" / "Lalezar-Regular.ttf"
BLACK = FONTS / "vazirmatn" / "Vazirmatn-Black.ttf"
XBOLD = FONTS / "vazirmatn" / "Vazirmatn-ExtraBold.ttf"
MEDIUM = FONTS / "vazirmatn" / "Vazirmatn-Medium.ttf"
GOLD, WHITE, INK = (255, 205, 60, 255), (255, 255, 255, 255), (16, 10, 6, 255)
SAFE = (60, 1020)                                  # px: type stays between these x (the Reels buttons sit right)
Y_TITLE = (190, 324)                               # baselines of the two headline lines (room for the kasra)
Y_NOTE = 414
Y_KEY = 462                                        # the colour key's bar (top)
Y_CHIP, Y_COUNTER, Y_UNIT = 1150, 1305, 1372
Y_SUB = 1478                                       # the subtitle pill's baseline (narrated cut)
Y_SOURCES = (1556, 1590)
HOOK = ("زیرِ پای کدام شهرها", "زمین پایین می‌رود؟")    # no kasra after a final ی: the fonts dot it
NOTE = "سرعتِ پایین‌رفتنِ زمین، ۲۰۱۴ تا ۲۰۲۰، از رادارِ ماهواره‌ی سنتینل-۱"
CAUSE_NOTE = "بیشترِ این پایین‌رفتن برگشت‌ناپذیر است"
KEY_TITLE = "سانتی‌متر در سال"
KEY_TICKS = (0, 10, 20, 30)
UNIT_AREA = "کیلومتر مربع زمینِ در حالِ پایین‌رفتن"
UNIT_RATE = "سانتی‌متر در سال، تندترین نقاط"
CHIP = "۲۰۱۴ تا ۲۰۲۰"
SOURCES = ("منبع: Haghshenas Haghighi و Motagh 2024؛ پژوهشِ مستقل: Payne و همکاران 2025",
           "تصویر: Copernicus DEM و Sentinel-2 cloudless (EOX)؛ استانِ تهران: سالنامه‌ی آماری ۱۳۹۵")
# the colour scale: the same stops as subsidence3d.RAMP (rate cm/yr, R, G, B)
RAMP = ((0.0, 255, 196, 72), (2.0, 255, 175, 55), (5.0, 255, 145, 35), (10.0, 250, 90, 35), (20.0, 228, 32, 62),
        (30.0, 196, 18, 150))
# the narration's subtitles: (start s, end s, text); the voice's measured segments (data/subsidence/narration/manifest.json)
SUBTITLES = ((0.15, 2.75, "ماهواره‌ها فرونشستِ زمین را سنجیدند."),
             (3.60, 7.55, "حدودِ ۵۶ هزار کیلومتر مربع از ایران پایین می‌رفت؛"),
             (7.80, 10.25, "بیش از چهار برابرِ استانِ تهران."),
             (10.35, 15.45, "در کرج و جنوب‌غربِ تهران، تندترین نقاط سالی ۱۵ تا ۲۰ سانتی‌متر؛"),
             (15.55, 17.45, "نزدیکِ یک وجب در سال."),
             (17.60, 23.10, "علتِ اصلی: برداشتِ آبِ زیرزمینی؛ و بیشترِ این فرونشست برگشت‌ناپذیر است."),
             (23.40, 25.70, "شهرِ شما روی این نقشه هست؟"))
LABEL_EVERY = 0.6                                  # s between the national labels' entrances (from 1.6 s)
# the news: three headlines, verbatim, each read on the outlet's own page on 7 Nov 2026 (links in the first comment).
# Only headlines about the slow sinking of the ground that the map measures: the Islamshahr underpass collapses of
# 1404 were sinkholes (an old qanat, a broken pipe), a different thing, and are left out. The newest opens the reel
# over the map (0-2.6 s); all three close it after the question, over the map dimmed (26-31 s).
NEWS = (("خبرگزاری صداوسیما", "۲۳ مهر ۱۴۰۵", "مهرشهر کرج سالانه ۱۴ سانتی‌متر پایین می‌رود"),
        ("تابناک", "۱۸ خرداد ۱۴۰۴", "وضعیت قرمز فرونشست زمین در جنوب‌غرب تهران"),
        ("خبرگزاری مهر", "۱۰ آبان ۱۴۰۵", "قطعی و افت فشار آب در کرمان؛ فرونشست خودنمایی کرد"))
NEWS_X, NEWS_TILT = (500, 508, 494), (-1.6, 1.2, -0.8)   # the cards' centres (x, px) and tilts (degrees)
NEWS_TOP, NEWS_OVERLAP = 572, 22                   # px: the first card's top; each card overlaps the one above
NEWS_IN = (26.0, 26.7, 27.4)                       # s: the closing cards' entrances (the first with the strike)
NEWS_NOTE = "در خبرها"
OPEN_OUT = (2.2, 2.6)                              # s: the opening card leaves
END = 31.0                                         # s: the reel; the 3D loop is 26 s, the last 5 s hold its end
LIFT = (30.4, 31.0)                                # s: cards 2-3 go, the map lightens into frame 0 (the loop)
PAPER, PAPER_INK, PAPER_DIM = (246, 242, 233, 255), (24, 18, 14, 255), (112, 102, 94, 255)
OUTLET_RED = (168, 32, 40, 255)


def font(path: Path, px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), px)


def width(s: str, path: Path, px: int) -> float:
    return font(path, px).getlength(s, direction="rtl", language="fa")


def text(d: ImageDraw.ImageDraw, x, y, s, path, px, fill=WHITE, stroke=6, anchor="ms"):
    d.text((x, y), s, font=font(path, px), fill=fill, anchor=anchor, direction="rtl", language="fa",
           stroke_width=stroke, stroke_fill=INK)


def pill(d, x, y, s, path, px, fill=(0, 0, 0, 170), colour=WHITE, pad=20):
    """A line on a dark rounded box, centred on x, baseline y."""
    w = width(s, path, px)
    d.rounded_rectangle([x - w / 2 - pad, y - px * 1.05, x + w / 2 + pad, y + px * 0.42], radius=px * 0.45, fill=fill)
    text(d, x, y, s, path, px, colour, stroke=0)


def split(a: float, b: float, s: str) -> list:
    """A sentence too wide for one pill: two halves, cut at the punctuation (else the space) nearest the middle, each
    shown for its share of the letters."""
    if 540 + width(s, XBOLD, 40) / 2 + 20 <= 930:
        return [(a, b, s)]
    words = s.split(" ")
    cuts = [k for k in range(1, len(words)) if words[k - 1][-1] in "،؛:"] or list(range(1, len(words)))
    mid = len(s) / 2
    k = min(cuts, key=lambda k: abs(len(" ".join(words[:k])) - mid))
    one, two = " ".join(words[:k]), " ".join(words[k:])
    tm = a + (b - a) * len(one) / (len(one) + len(two))
    return split(a, tm, one) + split(tm, b, two)


def ease(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def wrap(s: str, path: Path, px: int, w: float) -> list:
    """The headline in lines no wider than w: two lines balanced (the cut that makes the wider line narrowest) when
    two are enough, else greedy."""
    words = s.split(" ")
    if width(s, path, px) <= w:
        return [s]
    digits = set("0123456789۰۱۲۳۴۵۶۷۸۹")                # a number stays on the line of its unit
    two = [(" ".join(words[:k]), " ".join(words[k:])) for k in range(1, len(words)) if not set(words[k - 1]) <= digits]
    fits = [p for p in two if max(width(p[0], path, px), width(p[1], path, px)) <= w]
    if fits:
        return list(min(fits, key=lambda p: max(width(p[0], path, px), width(p[1], path, px))))
    lines, cur = [], ""
    for wd in words:
        trial = f"{cur} {wd}".strip()
        if cur and width(trial, path, px) > w:
            lines.append(cur)
            cur = wd
        else:
            cur = trial
    return lines + [cur]


def card(outlet: str, date: str, head: str, tilt: float, w: int = 780) -> Image.Image:
    """A news clipping: off-white paper, the outlet (right) and the date (left) over a rule, the headline in two lines
    of Vazirmatn Black, a soft shadow; turned by tilt degrees. No logo and no photograph: only the outlet's words."""
    pad, px, lead, sh = 30, 44, 60, 24
    lines = wrap(head, BLACK, px, w - 2 * pad)
    h = pad + 44 + 14 + 46 + (len(lines) - 1) * lead + 14 + pad
    im = Image.new("RGBA", (w + 2 * sh, h + 2 * sh), (0, 0, 0, 0))
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([sh, sh + 10, sh + w, sh + h + 10], radius=10, fill=(0, 0, 0, 130))
    im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(12)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([sh, sh, sh + w, sh + h], radius=10, fill=PAPER)
    x0, x1, y = sh + pad, sh + w - pad, sh + pad
    d.text((x1, y + 30), outlet, font=font(BLACK, 28), fill=OUTLET_RED, anchor="rs", direction="rtl", language="fa")
    d.text((x0, y + 30), date, font=font(MEDIUM, 26), fill=PAPER_DIM, anchor="ls", direction="rtl", language="fa")
    d.line([(x0, y + 44), (x1, y + 44)], fill=(205, 194, 182, 255), width=2)
    for k, s in enumerate(lines):
        d.text((x1, y + 44 + 14 + 46 + k * lead), s, font=font(BLACK, px), fill=PAPER_INK, anchor="rs",
               direction="rtl", language="fa")
    return im.rotate(tilt, resample=Image.BICUBIC, expand=True)


def fade(im: Image.Image, a: float) -> Image.Image:
    """im with its alpha scaled by a."""
    if a >= 1.0:
        return im
    out = im.copy()
    out.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return out


class SubsidenceFilm:
    def __init__(self, voice: bool):
        self.voice = voice
        self.tl = json.loads((DATA / "timeline.json").read_text())
        self.meta = json.loads((DATA / "frames" / "frames.json").read_text())
        self.n = len(self.meta)
        tl = self.tl
        assert self.n == round(tl["duration"] * tl["fps"]), ("render the 3D frames first", self.n)
        assert tl["shown_area"] == 56000 and 4.0 < tl["times_province"] < 4.2, (tl["shown_area"], tl["times_province"])
        assert tl["shown_range"] == [15, 20]
        peaks = [s["max"] for s in tl["stats"].values()]
        assert 14.5 <= min(peaks) and max(peaks) <= 20.5, peaks
        assert tl["duration"] == 26.0 and NEWS_IN[0] == tl["duration"] and END - NEWS_IN[-1] >= 3.0
        self.L = type("L", (), {"end": END})()
        self.cards, self.card_at, top = [], [], NEWS_TOP   # the clippings, stacked from the top, each a little over
        for (outlet, date, head), x, tilt in zip(NEWS, NEWS_X, NEWS_TILT):   # the one above
            im = card(outlet, date, head, tilt)
            cx, cy = x, top + im.height / 2 - 24          # 24: the shadow's margin
            assert 60 <= cx - im.width / 2 + 20 and cx + im.width / 2 - 20 <= 930, (head, cx, im.width)
            self.cards.append(im)
            self.card_at.append((cx, cy))
            top = cy + im.height / 2 - 24 - NEWS_OVERLAP
        assert NEWS_TOP >= 540 and top + NEWS_OVERLAP <= 1420, top   # clear of the key above, the subtitle below
        c0 = self.card_at[0]
        self.keepout = (c0[0] - self.cards[0].width / 2, c0[1] - self.cards[0].height / 2,
                        c0[0] + self.cards[0].width / 2, c0[1] + self.cards[0].height / 2)
        b = tl["beats"]
        self.beats = [(0.0, HOOK), (b[0], ("بیش از چهار برابرِ", "استانِ تهران")),
                      (b[1], ("کرج و جنوب‌غربِ تهران:", "نزدیکِ یک وجب در سال")),
                      (b[2], ("علتِ اصلی:", "برداشتِ آبِ زیرزمینی")),
                      (b[3], ("شهرِ شما", "روی این نقشه هست؟"))]
        for _, lines in self.beats:                        # every headline fits the safe width at its size
            for s in lines:
                assert 540 + width(s, LALEZAR, 96) / 2 + 7 <= 930, s       # with its stroke, inside x 930
        for s in SOURCES:                                  # inside the 828-px line, right edge at x 925
            assert width(s, MEDIUM, 22) <= 828, s
        man = json.loads((DATA / "narration" / "manifest.json").read_text())   # the voice as measured
        assert [m["text"] for m in man] == [s for _, _, s in SUBTITLES], "the subtitles are the spoken sentences"
        for k, (m, (a, b, _)) in enumerate(zip(man, SUBTITLES)):   # the question may stay a little longer
            hold = 1.0 if k == len(SUBTITLES) - 1 else 0.4
            assert abs(m["start"] - a) < 0.05 and m["end"] <= b <= m["end"] + hold, (m["name"], m["start"], m["end"], a, b)
        self.subs = [p for a, b, s in SUBTITLES for p in split(a, b, s)]
        for _, _, s in self.subs:                          # the pill clear of the Reels buttons (x 932)
            assert 540 + width(s, XBOLD, 40) / 2 + 20 <= 930, s
        for s in (NOTE, CAUSE_NOTE):
            assert width(s, XBOLD, 30) <= 860, s

    # ── the clock ──
    def counter(self, t: float):
        """(value text, unit, chip) at t; None while the hook hides the counter («؟»)."""
        tl = self.tl
        if t < tl["count"]:
            return None
        if tl["close"] - 0.6 <= t < tl["back"] + 1.6:      # the Tehran-Karaj plain
            if t < tl["close"]:
                return "", "", None                       # a beat of silence while the dive lands
            return f"{fa(15)} تا {fa(20)}", UNIT_RATE, CHIP
        if t < tl["land"]:
            v = tl["shown_area"] * ease((t - tl["count"]) / (tl["land"] - tl["count"]))
            return fa(f"{int(round(v / 100) * 100):,}").replace(",", "٬"), UNIT_AREA, CHIP
        return fa(f"{tl['shown_area']:,}").replace(",", "٬"), UNIT_AREA, CHIP

    def beat(self, t: float):
        return [bt for bt in self.beats if bt[0] <= t][-1]

    # ── the frame ──
    def frame(self, t: float):
        k = min(max(round(t * self.tl["fps"]), 0), self.n - 1)
        return Image.open(DATA / "frames" / f"f_{k:04d}.png").convert("RGBA"), self.meta[k]

    @staticmethod
    def bloom(im: Image.Image, amount: float) -> Image.Image:
        """From far, the glowing pixels (warm and saturated) bloom a little, so the small hotspots read from space."""
        if amount <= 0:
            return im
        a = np.asarray(im.convert("RGB"), np.float32)
        warm = np.clip((a[..., 0] - a[..., 2] - 70) / 90, 0, 1) * np.clip((a[..., 0] - 140) / 80, 0, 1)
        glow = (a * warm[..., None]).astype(np.uint8)
        g = Image.fromarray(glow)
        out = a
        for r, k in ((4, 0.9), (14, 0.7)):
            b = np.asarray(g.filter(ImageFilter.GaussianBlur(r)), np.float32) * k * amount
            out = 255 - (255 - out) * (1 - b / 255)
        res = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).convert("RGBA")
        return res

    @staticmethod
    def focus(im: Image.Image, amount: float) -> Image.Image:
        """A soft depth of field close up: the near ground (the frame's lower part) blurs gradually from y 1250."""
        if amount <= 0:
            return im
        blur = im.filter(ImageFilter.GaussianBlur(5))
        mask = Image.new("L", (W, H), 0)
        md = ImageDraw.Draw(mask)
        for y in range(1250, H):
            md.line([(0, y), (W, y)], fill=int(255 * amount * min(1.0, (y - 1250) / 380)))
        return Image.composite(blur, im, mask)

    # ── the news ──
    @staticmethod
    def lift(t: float) -> float:
        """0 to 1 over LIFT: the end eases into frame 0 (the loop)."""
        return ease((t - LIFT[0]) / (LIFT[1] - LIFT[0]))

    def tail(self, t: float) -> float:
        """How far the closing (26-31 s) has dimmed the map and hidden the labels and the counter."""
        return 0.0 if t < NEWS_IN[0] else ease((t - NEWS_IN[0]) / 0.35) * (1 - self.lift(t))

    def news(self, k: int, t: float, cover: bool) -> tuple:
        """(opacity, vertical offset px) of card k at t."""
        if t < NEWS_IN[0]:
            if k or cover:
                return 0.0, 0.0
            a = 1 - ease((t - OPEN_OUT[0]) / (OPEN_OUT[1] - OPEN_OUT[0]))
            return a, -30 * (1 - a)
        u = ease((t - NEWS_IN[k]) / 0.3)
        return u * (1 if k == 0 else 1 - self.lift(t)), 40 * (1 - u)

    @staticmethod
    def layer(im: Image.Image, a: float, paint) -> None:
        """paint(ImageDraw) on a clear layer, composited at opacity a."""
        if a <= 0:
            return
        ly = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        paint(ImageDraw.Draw(ly))
        im.alpha_composite(fade(ly, a))

    def draw(self, s: int = 1, t: float = 0.0, size=SIZES["reel"], cover: bool = False) -> Image.Image:
        t = 0.0 if not np.isfinite(t) else t
        im, m = self.frame(t)
        close = min(1.0, max(0.0, (np.log(300) - np.log(m["dist"])) / (np.log(300) - np.log(100))))
        im = self.focus(im, 0.6 * close)
        im = self.bloom(im, min(1.0, max(0.0, (np.log(m["dist"]) - np.log(200)) / (np.log(2000) - np.log(200)))))
        shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))   # soft dark bands under the type, top and bottom
        sd = ImageDraw.Draw(shade)
        for y in range(0, 520):
            sd.line([(0, y), (W, y)], fill=(0, 0, 0, int(120 * (1 - y / 520))))
        for y in range(1060, H):
            sd.line([(0, y), (W, y)], fill=(0, 0, 0, int(160 * min(1, (y - 1060) / 480))))
        im.alpha_composite(shade)
        tail, lift = self.tail(t), self.lift(t)
        if tail > 0:                                       # the map dimmed under the closing cards
            im.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(150 * tail))))
        d = ImageDraw.Draw(im)
        tl = self.tl
        _, lines = self.beat(t)

        def title(lines):
            return lambda dr: (text(dr, 540, Y_TITLE[0], lines[0], LALEZAR, 96, GOLD, 7),
                               text(dr, 540, Y_TITLE[1], lines[1], LALEZAR, 96, GOLD if lines is HOOK else WHITE, 7))

        def note(s):
            return lambda dr: text(dr, 540, Y_NOTE, s, XBOLD, 30, WHITE, 4)

        mid = (LIFT[0] + LIFT[1]) / 2                      # the end: the question out, then frame 0's hook in
        out_, in_ = ease((t - LIFT[0]) / (mid - LIFT[0])), ease((t - mid) / (LIFT[1] - mid))
        self.layer(im, 1 - out_, title(lines))
        self.layer(im, in_, title(HOOK))
        if t < NEWS_IN[0]:
            self.layer(im, 1 - ease((t - (NEWS_IN[0] - 0.3)) / 0.3),
                       note(CAUSE_NOTE if tl["beats"][2] <= t < tl["beats"][3] else NOTE))
        else:
            self.layer(im, ease((t - NEWS_IN[0]) / 0.3) * (1 - out_), note(NEWS_NOTE))
            self.layer(im, in_, note(NOTE))
        self.key(d)
        k0 = 0.0 if cover else self.news(0, t, cover)[0]
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))   # the labels on their own layer: their fades blend
        self.annotate(ImageDraw.Draw(layer), t, m, 1 - tail, k0)
        im.alpha_composite(layer)
        c = self.counter(t)

        def count(dr):
            if c is None:
                text(dr, 540, Y_COUNTER, "؟", LALEZAR, 170, WHITE, 8)
            elif c[0]:
                value, unit, chip = c
                pill(dr, 540, Y_CHIP, chip, BLACK, 44, fill=(255, 205, 60, 235), colour=INK)
                text(dr, 540, Y_COUNTER, value, LALEZAR, 150 if "تا" in value else 170, WHITE, 8)
                text(dr, 540, Y_UNIT, unit, BLACK, 44, WHITE, 5)

        self.layer(im, 1.0 if t < NEWS_IN[0] else 1 - ease((t - NEWS_IN[0]) / 0.35), count)
        self.layer(im, lift, lambda dr: text(dr, 540, Y_COUNTER, "؟", LALEZAR, 170, WHITE, 8))
        for k, (cim, (cx, cy)) in enumerate(zip(self.cards, self.card_at)):   # the clippings, over the map
            a, dy = self.news(k, t, cover)
            if a > 0:
                im.alpha_composite(fade(cim, a), (int(round(cx - cim.width / 2)), int(round(cy - cim.height / 2 + dy))))
        if self.voice:
            sub = [s for a, b, s in self.subs if a <= t < b]
            if sub:
                pill(d, 540, Y_SUB, sub[0], XBOLD, 40)
        for k, s in enumerate(SOURCES):
            text(d, 925, Y_SOURCES[k], s, MEDIUM, 22, (225, 230, 236, 255), 3, anchor="rs")
        return im.convert("RGB").resize(size, Image.LANCZOS) if tuple(size) != (W, H) else im.convert("RGB")

    def key(self, d: ImageDraw.ImageDraw):
        """The colour key: low rates on the right (read from the right), «۳۰+» on the left."""
        x0, x1, y0, h = 330, 730, Y_KEY, 16
        for x in range(x0, x1):
            r = (x1 - 1 - x) / (x1 - 1 - x0) * 30.0
            c = [np.interp(r, [s[0] for s in RAMP], [s[k] for s in RAMP]) for k in (1, 2, 3)]
            d.line([(x, y0), (x, y0 + h)], fill=tuple(int(v) for v in c) + (255,))
        d.rectangle([x0 - 1, y0 - 1, x1, y0 + h + 1], outline=(255, 255, 255, 200), width=2)
        for v in KEY_TICKS:
            x = x1 - (x1 - x0) * v / 30.0
            lab = fa(v) + ("+" if v == 30 else "")
            text(d, x, y0 + h + 30, lab, BLACK, 26, WHITE, 4)
        text(d, x1 + 14, y0 + h - 1, KEY_TITLE, XBOLD, 26, WHITE, 4, anchor="ls")

    def annotate(self, d: ImageDraw.ImageDraw, t: float, m: dict, show: float = 1.0, under: float = 0.0):
        """The national labels (far: their entrance one after another from 1.6 s), and the towns close up. show scales
        them all (the closing hides them); a label under the first card is scaled by 1 - under (that card's opacity)."""
        tl = self.tl
        far = min(1.0, max(0.0, (m["dist"] - 250) / 350)) * show
        if far > 0:
            for k, (lab, (x, y, z)) in enumerate(zip(tl["labels"], m["labels"])):
                t_in = 1.6 + k * LABEL_EVERY               # frame 0 = the end state: every label; they fade at
                if t < tl["count"] or t >= tl["back"]:     # the count's start and come back one by one
                    a = 1.0
                elif t < t_in:
                    a = 1 - ease((t - tl["count"]) / 0.3)
                else:
                    a = ease((t - t_in) / 0.25)
                a *= far
                if a <= 0 or not (40 < x < W - 40 and 470 < y < 1120):
                    continue
                self.label(d, x, y, lab["text"], lab["side"], lab["dy"], a, 30, (self.keepout, under))
        near = min(1.0, max(0.0, (160 - m["dist"]) / 80))
        if near > 0:
            for lab, (x, y, z) in zip(tl["local"], m["local"]):
                if 0 < z < 1 and 60 < x < W - 60 and 540 < y < 1100:
                    self.label(d, x, y, lab["text"], 1 if x < 620 else -1, -18, near, 32)

    @staticmethod
    def label(d, x, y, s, side, dy, a, px, hide=None):
        r = 7
        w = width(s, BLACK, px)
        if side > 0 and x + 24 + w > 925 or side < 0 and x - 24 - w < SAFE[0]:
            side = -side                                  # no room on its side: the label goes to the other side
        tx = x + side * 24
        ty = y + dy
        lx = tx if side > 0 else tx - w
        lx = min(max(lx, SAFE[0]), 925 - w)
        bb = d.textbbox((lx + w, ty), s, font=font(BLACK, px), anchor="rs", direction="rtl", language="fa",
                        stroke_width=4)
        if bb[1] < 520 or bb[3] > 1095 or y < 520 or y > 1095:   # clear of the key above and the chip below
            return
        if hide is not None and hide[1] > 0:              # under the opening card: it fades as the card leaves
            k = hide[0]
            x0, y0, x1, y1 = min(bb[0], x - r), min(bb[1], y - r), max(bb[2], x + r), max(bb[3], y + r)
            if x0 < k[2] and x1 > k[0] and y0 < k[3] and y1 > k[1]:
                a *= 1 - hide[1]
        if a <= 0:
            return
        col = (255, 255, 255, int(255 * a))
        ink = (16, 10, 6, int(255 * a))
        d.ellipse([x - r, y - r, x + r, y + r], outline=col, width=3)
        d.ellipse([x - 2.5, y - 2.5, x + 2.5, y + 2.5], fill=col)
        d.line([(x + side * (r + 2), y), (lx if side > 0 else lx + w, ty - px * 0.35)], fill=col, width=2)
        d.text((lx + w, ty), s, font=font(BLACK, px), fill=col, anchor="rs", direction="rtl", language="fa",
               stroke_width=4, stroke_fill=ink)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true", help="cover and stills only")
    ap.add_argument("--voice", action="store_true", help="the narrated cut's picture (with subtitles)")
    args = ap.parse_args()
    film = SubsidenceFilm(args.voice)
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / ("subsidence_fa_voice" if args.voice else "subsidence_fa")
    for old in (OUT / "social").glob(f"{base.name}_t*.png"):
        old.unlink()
    film.draw(1, 0.0, cover=True).save(f"{base}_cover.png", optimize=True)   # the cover: the map, no card
    print("saved", f"{base}_cover.png")
    if args.stills:
        for t in (0.0, 1.5, 2.4, 3.0, 5.5, 7.9, 10.5, 13.2, 16.0, 19.0, 22.0, 24.0, 25.9, 26.2, 26.9, 27.6, 28.5,
                  30.6, 30.97):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
