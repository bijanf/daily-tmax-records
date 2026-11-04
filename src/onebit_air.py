"""WINTER NO2 OVER TEHRAN, FROM SPACE: the tropospheric NO2 column that Sentinel-5P sees over Tehran and the
Alborz foothills, in the winter of 2025/26 against its summer. A full-screen film in the style of mapped.earth:
a real-relief base filling the frame, the data glowing, one big counter, a month dial, a two-line title.

Measured data only, from air.py (the granules of get_air.py): valid pixels with qa >= 0.75, the Tehran-Karaj box
(51.0-51.8 E, 35.4-36.0 N). The counter is a month's pixel mean over the summer reference (JJA 2026, x1.0); the
winter state is DJF 2025/26 pooled (x3 as shown: 3.3 in the box). The glow is each month's mean field on the frame.
The dial runs the twelve months November 2025 to October 2026, the latest complete year, at 1.3 months a second.

    0.0 s         the end state: the winter field glowing, the counter x3 and the whole two-line title
    1.0-1.5 s     the reset: the summer reference (x1.0); the glow fades from the winter to the summer field
    1.5-9.96 s    the dial from November 2025 to October 2026 at 1.3 months a second; the counter is that
                  month's value over the summer reference
    9.96-10.86 s  October turns back to the winter state (x3)
    0.3-0.7 s     Tehran, Karaj and the Alborz pop in, once, in the first second of the dial
    11.0 s        the reason, in Persian (longer NO2 life in winter; cold air held under the Alborz)
    16.0 s        what this is not: NO2 is not the fine dust (PM2.5) behind the school closures
    24.0 s        the end, held on the winter state

Three bars of 4 s at 60 BPM (the score: src/onebit_score_air.py).

    outputs/onebit/social/air_tehran_fa_reel.mp4, _cover.png, _t*.png

    python -I src/onebit_air.py
    python -I src/onebit_air.py --stills
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

import air  # noqa: E402
import onebit  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, SIZES, SOCIAL_CRF, fa  # noqa: E402

W, H = air.W, air.H
DURATION = 24.0                                  # s
PACE = dict(bpm=60, bars=(1.5, 2.0, 2.5))        # three parts of the reel in bars (4 s a bar at 60 BPM)
RESET = 1.0                                      # s: the summer reference comes in
DIAL_START = 1.5                                 # s: November 2025
RATE = 1.3                                       # months a second
TURN = 0.9                                       # s: October turns back to the winter state
POP = (0.30, 0.50, 0.70)                         # s: Tehran, Karaj and the Alborz pop in
WHY_AT, PM_AT = 11.0, 16.0                       # s: the two lines of the hold
VMIN, VMAX, GAMMA = 15.0, 60.0, 1.2              # 1e15 molec/cm2: the glow's range (as the fact check)
ORANGE = np.array([255, 120, 30], np.float32)
HOT = np.array([255, 214, 140], np.float32)
PAPER, SHADOW, AMBER = (250, 246, 238, 255), (8, 10, 14, 255), (255, 150, 60, 255)
MONTHS = air.DIAL_JK                             # Aban 1404 to Mehr 1405 (Jalali keys "YYYY-MM")
TERRAIN = air.DATA / "terrain.npz"
SOURCES = "منبع: Sentinel-5P (ESA/Copernicus)؛ ارتفاع: Copernicus DEM"
UNIT = "ستونِ دی‌اکسیدِ نیتروژن، ۱۰¹⁵ مولکول بر سانتی‌مترِ مربع"
TITLE = ("دی‌اکسیدِ نیتروژنِ تهران از فضا", "آذر تا بهمن: حدودِ سه برابرِ تابستان")
SUB = "آذر تا بهمن به تیر تا شهریور"
NUMWORD = {2: "دو", 3: "سه", 4: "چهار"}
STORY = {WHY_AT: ("در زمستان این گاز دیرتر از میان می‌رود", "و هوای سردِ سنگین زیرِ لایه‌ای گرم‌تر می‌ماند"),
         PM_AT: ("این گازِ دی‌اکسیدِ نیتروژن است، نه گردِ ریزِ PM2.5",)}
STORY_UNTIL = {WHY_AT: PM_AT - 0.5, PM_AT: DURATION}      # one pair of lines at a time: the first gives way
SAFE = (80, 930)                                         # px: x of the dial, legend and text below y 1000
PLACES = {"تهران": (51.39, 35.69), "کرج": (50.97, 35.84), "البرز": (50.85, 36.10)}
MAX_LINE = 960                                   # px: the widest line on the frame (a 60 px gutter a side)
# the layout, in px (baselines unless stated)
Y_TITLE = (262, 336)
Y_COUNTER, Y_SUB = 640, 760
Y_SCALE = 1130
Y_MONTH, Y_STRIP, Y_NUM = 1176, 1202, 1250
Y_UNIT, Y_BAR, Y_TICK = 1300, 1314, 1376
Y_STORY = 1398                                            # top of the story pill (two lines, 40 px)
Y_SOURCES = 1560


def font(path, px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), px)


def pct(v: float) -> str:
    return "×" + fa(f"{v:.1f}")                  # one decimal on the dial: ×۱٫۰


def glow_of(f: np.ndarray) -> np.ndarray:
    """A month's field as glow, 0-1 (no data: 0). The fact check's glow: a stretch from 15 to 60, a bloom."""
    from scipy import ndimage
    i = np.where(np.isfinite(f), np.clip((np.nan_to_num(f) - VMIN) / (VMAX - VMIN), 0, 1) ** GAMMA, 0.0)
    bloom = ndimage.gaussian_filter(i, 10) * 0.9
    return np.clip(0.85 * i + 0.6 * bloom, 0, 1).astype(np.float32)


def line_layer(s: str, path, px: int, fill=PAPER, stroke: int = 4) -> Image.Image:
    """One Persian line on a transparent layer (RTL, raqm), for pops and fades."""
    f = font(path, px)
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    bb = probe.textbbox((0, 0), s, font=f, anchor="ls", direction="rtl", language="fa", stroke_width=stroke)
    im = Image.new("RGBA", (bb[2] - bb[0] + 4, bb[3] - bb[1] + 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((2 - bb[0], 2 - bb[1]), s, font=f, fill=fill, anchor="ls", direction="rtl",
                            language="fa", stroke_width=stroke, stroke_fill=SHADOW)
    return im


def text(im: Image.Image, x: float, y: float, s: str, path, px: int, anchor: str = "rs", direction="rtl",
         fill=PAPER, stroke: int = 4) -> float:
    """Draws s on im at (x, y) with an anchor (rs: right edge at x, baseline y; ms: centred); returns its width."""
    f = font(path, px)
    d = ImageDraw.Draw(im)
    d.text((x, y), s, font=f, fill=fill, anchor=anchor, direction=direction, language="fa",
           stroke_width=stroke, stroke_fill=SHADOW)
    return d.textlength(s, font=f, direction=direction, language="fa")


def pill_w(s: str, path, px: int) -> float:
    return font(path, px).getlength(s, direction="rtl", language="fa")


def box(im: Image.Image, x0, y0, x1, y1, alpha: int = 200):
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle([x0, y0, x1, y1], radius=18, fill=(8, 10, 14, alpha))
    im.alpha_composite(layer)


class AirFilm:
    """The film: draw(1, t) is the frame at t seconds (t = inf: the end state, the cover)."""

    def __init__(self):
        m = air.monthly()
        self.table = m
        self.ratio = {jk: float(r) for jk, r in zip(m.jk, m.ratio)}
        self.winter = float(m.attrs["winter"])
        self.ref = float(m.attrs["ref"])
        self.checks()
        fields = air.fields()
        self.glow = {k: glow_of(v) for k, v in fields.items() if k in MONTHS or k in ("winter", "summer")}
        ter = np.load(TERRAIN)
        self.base = self.make_base(ter["hs"], ter["elev"])
        self.L = SimpleNamespace(end=DURATION)
        self.starts = np.array([0.0, 4.0 * PACE["bars"][0], 4.0 * sum(PACE["bars"][:2])])
        self.bpm = PACE["bpm"]
        self.dial_end = DIAL_START + (len(MONTHS) - 1) / RATE
        assert self.dial_end < 10.0 and self.dial_end + TURN < WHY_AT, (self.dial_end, WHY_AT)
        assert PM_AT >= WHY_AT + 3.0 and PM_AT + 3.0 <= DURATION, (WHY_AT, PM_AT)
        self.pins = {k: self.place(lon, lat) for k, (lon, lat) in PLACES.items()}
        self.labels = {k: line_layer(k, FA_BOLD, 42) for k in PLACES}
        self.story = {at: [line_layer(x, FA_TEXT, 40) for x in pair] for at, pair in STORY.items()}
        for at, lays in self.story.items():
            for lay, x in zip(lays, STORY[at]):
                assert lay.width - 4 <= SAFE[1] - SAFE[0] - 40, (x, lay.width)
        assert pill_w(SUB, FA_TEXT, 48) <= SAFE[1] - SAFE[0] and pill_w(UNIT, FA_TEXT, 38) <= SAFE[1] - SAFE[0]

    # ── checks: every number on the screen ──

    def checks(self):
        m, r = self.table, self.ratio
        assert list(m.jk) == MONTHS, list(m.jk)
        assert (m.n_pix > 1000).all() and (m.n_days >= 5).all(), m[["jk", "n_pix", "n_days"]]
        summer = [r[jk] for jk in air.REF_JK]
        assert all(0.7 < v < 1.3 for v in summer), summer              # Tir to Shahrivar: about x1.0
        assert 2.5 <= self.winter <= 4.5, self.winter
        self.held = int(round(self.winter))                            # the held counter: the box ratio, rounded
        assert self.held == 3 and NUMWORD[self.held] in TITLE[1], (self.held, TITLE[1])
        assert max(r, key=r.get) == "1404-10", r                       # the peak month is Dey (x4.2)
        assert r["1404-12"] < r["1404-09"] and r["1404-11"] < r["1404-09"], r   # Bahman and Esfand are below Azar

    @staticmethod
    def place(lon: float, lat: float) -> tuple:
        x, y = air.px_of(lon, lat)
        return int(round(x)), int(round(y))

    @staticmethod
    def make_base(hs: np.ndarray, elev: np.ndarray) -> np.ndarray:
        """The real relief, darkened: a blue-grey hillshade (sun from the north-west) with a faint altitude tint."""
        base = np.zeros((H, W, 3), np.float32)
        base[:] = np.array([58, 70, 84], np.float32) * (0.16 + 0.95 * hs[..., None])
        base += (np.clip(elev, 0, 5000)[..., None] / 5000.0) * np.array([10, 9, 6], np.float32)
        return base

    # ── time ──

    def state(self, t: float):
        """(glow A, glow B, blend, counter value, dial label, dial position, phase) at t seconds."""
        win = self.glow["winter"]
        if not np.isfinite(t) or t < RESET or t >= self.dial_end + TURN:
            return win, win, 0.0, self.winter, "winter", 1.0, "winter"
        if t < DIAL_START:                          # the reset: the reference is the summer itself, x1.0
            w = min((t - RESET) / 0.5, 1.0)
            return win, self.glow["summer"], w, 1.0, "ref", 0.0, "reset"
        if t < self.dial_end:
            p = min((t - DIAL_START) * RATE, len(MONTHS) - 1)
            a = int(math.floor(p))
            b = min(a + 1, len(MONTHS) - 1)
            k = int(round(p))
            return self.glow[MONTHS[a]], self.glow[MONTHS[b]], p - a, self.ratio[MONTHS[k]], MONTHS[k], p, "dial"
        w = min((t - self.dial_end) / TURN, 1.0)    # the turn: October to the winter
        last = MONTHS[-1]
        return self.glow[last], win, w, self.ratio[last] + (self.winter - self.ratio[last]) * w, "turn", \
            len(MONTHS) - 1, "turn"

    # ── drawing ──

    def compose(self, gA, gB, w) -> Image.Image:
        g = gA if w <= 0 else (1 - w) * gA + w * gB
        col = ORANGE[None, None] + (HOT - ORANGE)[None, None] * g[..., None]
        img = self.base + g[..., None] * col
        return Image.fromarray(np.clip(img + 0.5, 0, 255).astype(np.uint8)).convert("RGBA")

    def draw_frame(self, t: float) -> Image.Image:
        gA, gB, w, value, label, p, phase = self.state(t)
        im = self.compose(gA, gB, w)
        self.title(im)
        self.counter(im, value, phase)
        self.scale_bar(im)
        self.labels_on(im, t)
        self.dial_strip(im, label, p, phase)
        self.legend(im)
        self.hold_lines(im, t)
        self.sources(im)
        return im.convert("RGB")

    def title(self, im: Image.Image):
        for s, y in zip(TITLE, Y_TITLE):
            w = text(im, 540, y, s, FA_BOLD, 58, anchor="ms", stroke=5)
            assert w <= MAX_LINE, (s, w)

    def counter(self, im: Image.Image, value: float, phase: str):
        s = "×" + fa(f"{value:.0f}") if phase in ("winter", "turn") and value >= 2.5 else pct(value)
        text(im, 540, Y_COUNTER, s, FA_BOLD, 270, anchor="ms", direction="ltr", fill=AMBER[:3] + (255,), stroke=6)
        w = pill_w(SUB, FA_TEXT, 48)
        box(im, 540 - w / 2 - 22, Y_SUB - 50, 540 + w / 2 + 22, Y_SUB + 14)
        text(im, 540, Y_SUB, SUB, FA_TEXT, 48, anchor="ms", stroke=0)

    def scale_bar(self, im: Image.Image):
        km = 20.0 / air.KMPP                                   # px: 20 km at the frame's scale
        x0 = 80
        d = ImageDraw.Draw(im)
        d.rectangle([x0, Y_SCALE, x0 + km, Y_SCALE + 10], fill=PAPER)
        text(im, x0 + km / 2, Y_SCALE - 14, "۲۰ کیلومتر", FA_TEXT, 36, anchor="ms", stroke=3)

    def labels_on(self, im: Image.Image, t: float):
        for k, (name, (x, y)) in enumerate(self.pins.items()):
            p = (t - POP[k]) / 0.30 if np.isfinite(t) else 1.0
            if p <= 0:
                continue
            s = min(p, 1.0)
            sc = 0.6 + 0.4 * s + 0.08 * math.sin(s * math.pi) * (1 - s)     # a pop: overshoot, then settle
            lab = self.labels[name]
            ww, hh = max(1, int(lab.width * sc)), max(1, int(lab.height * sc))
            pad = 16
            ox, oy = x - 20 - ww - pad, y - hh // 2 - pad
            layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
            ImageDraw.Draw(layer).rounded_rectangle([ox, oy, ox + ww + 2 * pad, oy + hh + 2 * pad], radius=18,
                                                    fill=(8, 10, 14, 200))
            layer.alpha_composite(lab.resize((ww, hh), Image.LANCZOS), (int(ox + pad), int(oy + pad)))
            im.alpha_composite(layer)
            r = 9
            ImageDraw.Draw(im).ellipse([x - r, y - r, x + r, y + r], fill=PAPER, outline=SHADOW, width=2)

    def dial_strip(self, im: Image.Image, label: str, p: float, phase: str):
        x0, x1 = SAFE[0] + 30, SAFE[1] - 30
        if label in MONTHS:                                  # the year once: at Aban and at Farvardin
            name = air.JALALI_NAMES[int(label[5:]) - 1]
            if label in ("1404-08", "1405-01"):
                name += " " + fa(label[:4])
        elif label == "ref":
            name = "مرجع: تیر تا شهریور ۱۴۰۵"
        else:
            name = "آذر تا بهمن ۱۴۰۴"
        text(im, 540, Y_MONTH, name, FA_BOLD, 50, anchor="ms", stroke=4)
        d = ImageDraw.Draw(im)
        d.line([(x0, Y_STRIP), (x1, Y_STRIP)], fill=PAPER, width=3)
        step = (x1 - x0) / (len(MONTHS) - 1)
        for k, ym in enumerate(MONTHS):
            xx = x0 + k * step
            d.line([(xx, Y_STRIP - 8), (xx, Y_STRIP + 8)], fill=PAPER, width=3)
            text(im, xx, Y_NUM, fa(int(ym[5:])), FA_TEXT, 32, anchor="ms", stroke=3)
        if phase == "dial":
            xp = x0 + p * step
            d.ellipse([xp - 12, Y_STRIP - 12, xp + 12, Y_STRIP + 12], fill=AMBER, outline=SHADOW, width=2)
        elif phase in ("winter", "turn"):                       # the winter: a box round December to February
            xa, xb = x0 + 1 * step, x0 + 3 * step
            d.rectangle([xa - 8, Y_STRIP - 14, xb + 8, Y_STRIP + 14], outline=AMBER, width=3)

    def legend(self, im: Image.Image):
        x0, x1 = SAFE
        d = ImageDraw.Draw(im)
        for xx in range(x0, x1):
            v = VMIN + (xx - x0) / (x1 - x0) * (VMAX - VMIN)
            c = np.clip((v - VMIN) / (VMAX - VMIN), 0, 1) ** GAMMA
            d.line([(xx, Y_BAR), (xx, Y_BAR + 24)], fill=tuple(int(q) for q in ORANGE * (1 - c) + HOT * c) + (255,))
        d.rectangle([x0, Y_BAR, x1, Y_BAR + 24], outline=PAPER, width=2)
        for v in (15, 30, 45, 60):
            xx = x0 + (v - VMIN) / (VMAX - VMIN) * (x1 - x0)
            d.line([(xx, Y_BAR + 24), (xx, Y_BAR + 34)], fill=PAPER, width=2)
            text(im, xx, Y_TICK, fa(v), FA_TEXT, 32, anchor="ms", stroke=3)
        self.unit(im)

    def unit(self, im: Image.Image):
        """The unit with a raised 15 (Vazirmatn has no superscript five): ستونِ دی‌اکسیدِ نیتروژن، ۱۰¹⁵ مولکول…"""
        f, fs = font(FA_TEXT, 38), font(FA_TEXT, 24)
        right = SAFE[1] - 6
        seg_a = "ستونِ دی‌اکسیدِ نیتروژن، "
        seg_c = " مولکول بر سانتی‌مترِ مربع"
        wa = f.getlength(seg_a, direction="rtl", language="fa")
        wc = f.getlength(seg_c, direction="rtl", language="fa")
        w10, w15 = f.getlength("۱۰"), fs.getlength("۱۵")
        x_c = right - wa
        d = ImageDraw.Draw(im)
        d.text((right, Y_UNIT), seg_a, font=f, fill=PAPER, anchor="rs", direction="rtl", language="fa",
               stroke_width=3, stroke_fill=SHADOW)
        d.text((x_c, Y_UNIT), "۱۰", font=f, fill=PAPER, anchor="rs", stroke_width=3, stroke_fill=SHADOW)
        d.text((x_c - w10 + 0.0, Y_UNIT - 22), "۱۵", font=fs, fill=PAPER, anchor="rs", stroke_width=2,
               stroke_fill=SHADOW)
        d.text((x_c - w10 - w15 - 4, Y_UNIT), seg_c, font=f, fill=PAPER, anchor="rs", direction="rtl",
               language="fa", stroke_width=3, stroke_fill=SHADOW)

    def hold_lines(self, im: Image.Image, t: float):
        for at, lays in self.story.items():
            if not np.isfinite(t) or t < at or t >= STORY_UNTIL[at]:
                continue
            a = min((t - at) / 0.5, 1.0)                        # a fade in over half a second
            cx = (SAFE[0] + SAFE[1]) / 2
            layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
            hh = max(lay.height for lay in lays)
            ww = max(lay.width for lay in lays) - 4
            x0, y0 = int(cx - ww / 2) - 18, int(Y_STORY)
            ImageDraw.Draw(layer).rounded_rectangle([x0, y0, x0 + ww + 36, y0 + len(lays) * hh + 16], radius=18,
                                                    fill=(8, 10, 14, int(200 * a)))
            for k, lay in enumerate(lays):
                if a < 1.0:
                    lay = lay.copy()
                    lay.putalpha(Image.fromarray((np.array(lay.getchannel("A"), np.float32) * a).astype(np.uint8)))
                layer.alpha_composite(lay, (int(cx - (lay.width - 4) / 2), int(y0 + 8 + k * hh)))
            im.alpha_composite(layer)

    def sources(self, im: Image.Image):
        w = text(im, 540, Y_SOURCES, SOURCES, FA_TEXT, 30, anchor="ms", stroke=3)
        assert w <= SAFE[1] - SAFE[0], w

    # ── film interface ──

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]) -> Image.Image:
        assert s == 1 and tuple(size) == (W, H), (s, size)
        return self.draw_frame(t)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="tehran", choices=["tehran"], help="colour theme")
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    args = ap.parse_args()
    film = AirFilm()
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / f"air_{args.theme}_fa"
    for old in (OUT / "social").glob(f"{base.name}_t*.png"):
        old.unlink()
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        for t in (0.0, 1.5, 3.04, 7.65, 23.9):           # the start, the reset, Dey (the peak), Tir (summer), the end
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
