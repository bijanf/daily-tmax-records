"""THE LOST WATER OVER TEHRAN: «آبی که ایران از دست داد، روی تهران چقدر بالا می‌آید؟» A full-screen 3D reel: the
water Iran's land lost from 1382-1384 to 1402-1404 (GRACE and GRACE-FO, three solutions: src/grace.py), laid over
the city of Tehran as one layer of one thickness, cut through Milad Tower so its thickness shows (a comparison of
scale, not a flood), rising year by year from the measured values; then three short beats and a closing question.

Layers: the 3D frames of src/tehranwater3d.py (data/tehranwater/frames/, 30 a second, with the screen positions of
Milad Tower and of the water's surface above it), and on top the Persian type drawn here: a gold two-line headline
(Lalezar), the counter (billion m3) with its year chip, the labels of the tower and of the surface, one sources
line, and in the narrated cut the subtitles of the narration. Every number on screen comes from
data/tehranwater/timeline.json (src/tehranwater.py), asserted here.

    0.0 s        the end state: the layer at its final thickness, the hook, the counter «؟»
    1.6-2.4 s    the layer drains; 2.4-8.4 s it rises again, step by step: 1382-1384, 1385 ... 1401, 1402-1404
    8.4 s        the number lands: ۳۸۰ billion m3, ۶۰۰ m over Tehran, above Milad Tower (435 m)
    15.0, 19.0   about three years of Iran's renewable water; mostly groundwater, by the studies
    23.4-26 s    the question; the camera returns to its first frame (a loop)

    python -I src/onebit_tehranwater.py --stills          # cover and stills
    python -I src/onebit_tehranwater.py                   # the silent reel (music-only cut, no subtitles)
    python -I src/onebit_tehranwater.py --voice           # the narrated cut's picture (subtitles)
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

DATA = Path(__file__).resolve().parents[1] / "data" / "tehranwater"
W, H = 1080, 1920
LALEZAR = FONTS / "lalezar" / "Lalezar-Regular.ttf"
BLACK = FONTS / "vazirmatn" / "Vazirmatn-Black.ttf"
XBOLD = FONTS / "vazirmatn" / "Vazirmatn-ExtraBold.ttf"
MEDIUM = FONTS / "vazirmatn" / "Vazirmatn-Medium.ttf"
GOLD, WHITE, INK = (255, 205, 60, 255), (255, 255, 255, 255), (16, 10, 6, 255)
WATER_INK = (150, 225, 255, 255)
SAFE = (60, 1020)                                  # px: type stays between these x (the Reels buttons sit right)
Y_TITLE = (190, 324)                               # baselines of the two headline lines (room for the kasra)
Y_NOTE = 414
Y_CHIP, Y_COUNTER, Y_UNIT = 1150, 1305, 1372
Y_SUB = 1478                                       # the subtitle pill's baseline (narrated cut)
Y_SOURCES = (1556, 1590)
HOOK = ("آبی که ایران از دست داد،", "روی تهران چقدر بالا می‌آید؟")
NOTE = "فقط برای مقایسه: این آب از کلِ ایران کم شده، نه فقط از تهران"
UNIT = "میلیارد مترمکعب آبِ ازدست‌رفته"
THICKNESS = "ضخامتِ لایه‌ی آب"
SOURCES = ("منبع: GRACE و GRACE-FO (NASA و DLR و GFZ)؛ پردازش: CSR و GSFC و COST-G",
           "تصویر: Copernicus DEM و Sentinel-2 cloudless 2016 (EOX)؛ مرزِ شهر: OpenStreetMap")
GAP_NOTE = "۱۳۹۶: داده‌ی کافی نیست (بینِ دو مأموریت)"
CROSS_NOTE = "بالاتر از نوکِ برجِ میلاد"
# the narration's subtitles: (start s, end s, text); matched to the voice's measured segments (onebit_score_tehranwater)
SUBTITLES = ((0.15, 3.30, "ماهواره‌ها آبِ ایران را وزن کردند."),
             (3.40, 8.30, "از ۱۳۸۲ تا ۱۴۰۴، ایران آب از دست داد:"),
             (8.45, 11.32, "حدودِ ۳۸۰ میلیارد مترمکعب."),
             (11.35, 14.55, "روی تهران، حدودِ ۶۰۰ متر می‌شود؛"),
             (14.55, 16.45, "بلندتر از برجِ میلاد."),
             (16.65, 19.30, "تقریباً سه سال آبِ تجدیدپذیرِ ایران."),
             (19.50, 23.25, "به برآوردِ پژوهش‌ها، بیشترش آبِ زیرزمینی بود."),
             (23.60, 25.70, "آبِ شهرِ شما از کجا می‌آید؟"))


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


class TehranWaterFilm:
    def __init__(self, voice: bool):
        self.voice = voice
        self.tl = json.loads((DATA / "timeline.json").read_text())
        self.meta = json.loads((DATA / "frames" / "frames.json").read_text())
        self.n = len(self.meta)
        tl = self.tl
        assert self.n == round(tl["duration"] * tl["fps"]), ("render the 3D frames first", self.n)
        assert tl["shown_km3"] == 380 and tl["shown_m"] == 600, (tl["shown_km3"], tl["shown_m"])
        assert tl["milad"]["tip_m"] == 435.0
        assert 2.85 <= tl["years_renewable"] <= 3.05, tl["years_renewable"]
        assert tl["steps"][0]["km3"] == 0.0 and tl["steps"][-1]["label"] == "۱۴۰۲ تا ۱۴۰۴"
        self.L = type("L", (), {"end": tl["duration"]})()
        b = tl["beats"]
        self.beats = [(0.0, HOOK, None),
                      (b[0], (f"حدودِ {fa(tl['shown_m'])} متر آب روی تهران", "بلندتر از برجِ میلاد"), None),
                      (b[1], ("حدودِ سه سال", "آبِ تجدیدپذیرِ کلِ ایران"), None),
                      (b[2], ("به برآوردِ پژوهش‌ها:", "بیشترش آبِ زیرزمینی بود"), None),
                      (b[3], ("آبِ شهرِ شما", "از کجا می‌آید؟"), None)]
        for _, lines, _ in self.beats:                     # every headline fits the safe width at its size
            for s in lines:
                assert width(s, LALEZAR, 96) <= SAFE[1] - SAFE[0] - 40, s
        for s in SOURCES:                                  # inside the 828-px line, right edge at x 925
            assert width(s, MEDIUM, 22) <= 828, s
        for _, _, s in SUBTITLES:                          # the pill clear of the Reels buttons (x 932)
            assert 540 + width(s, XBOLD, 40) / 2 + 20 <= 930, s

    # ── the clock ──
    def step_at(self, t: float):
        """(the step shown, the counter's km3) at t: the hook hides the counter (None)."""
        tl = self.tl
        st = tl["steps"]
        if t < tl["rise"]:                                # the hook and the drain: the counter is «؟»
            return None, None
        if t >= tl["land"]:
            return st[-1], float(tl["shown_km3"])
        f = (t - tl["rise"]) / tl["t_step"]
        k = min(int(f), len(st) - 2)
        u = min(max(f - k, 0.0), 1.0)
        s = st[k + 1] if u >= 0.5 else st[k]           # the counter shows the chip's own value (the water eases)
        return s, s["km3"]

    def beat(self, t: float):
        return [bt for bt in self.beats if bt[0] <= t][-1]

    # ── the frame ──
    def frame(self, t: float) -> Image.Image:
        k = min(max(round(t * self.tl["fps"]), 0), self.n - 1)
        return Image.open(DATA / "frames" / f"f_{k:04d}.png").convert("RGBA"), self.meta[k]

    @staticmethod
    def focus(im: Image.Image) -> Image.Image:
        """A soft depth of field: the near ground (the frame's lower part, where the 10-m imagery is enlarged most)
        blurs gradually from y 1250 to the bottom."""
        blur = im.filter(ImageFilter.GaussianBlur(5))
        mask = Image.new("L", (W, H), 0)
        md = ImageDraw.Draw(mask)
        for y in range(1250, H):
            md.line([(0, y), (W, y)], fill=int(255 * min(1.0, (y - 1250) / 380)))
        return Image.composite(blur, im, mask)

    def draw(self, s: int = 1, t: float = 0.0, size=SIZES["reel"]) -> Image.Image:
        t = 0.0 if not np.isfinite(t) else t
        im, m = self.frame(t)
        im = self.focus(im)
        shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))   # soft dark bands under the type, top and bottom
        sd = ImageDraw.Draw(shade)
        for y in range(0, 430):
            sd.line([(0, y), (W, y)], fill=(0, 0, 0, int(110 * (1 - y / 430))))
        for y in range(1080, H):
            sd.line([(0, y), (W, y)], fill=(0, 0, 0, int(150 * min(1, (y - 1080) / 500))))
        im.alpha_composite(shade)
        d = ImageDraw.Draw(im)
        tl = self.tl
        _, lines, _ = self.beat(t)
        text(d, 540, Y_TITLE[0], lines[0], LALEZAR, 96, GOLD, 7)
        text(d, 540, Y_TITLE[1], lines[1], LALEZAR, 96, GOLD if lines is HOOK else WHITE, 7)
        if t >= tl["rise"]:
            text(d, 540, Y_NOTE, NOTE, XBOLD, 30, WHITE, 4)
        self.annotate(d, t, m)
        step, km3 = self.step_at(t)
        if step is None:
            text(d, 540, Y_COUNTER, "؟", LALEZAR, 170, WHITE, 8)
        else:
            pill(d, 540, Y_CHIP, fa(step["label"]) if step["label"].isdigit() else step["label"], BLACK, 44,
                 fill=(255, 205, 60, 235), colour=INK)
            shown = int(round(km3)) if t < tl["land"] else tl["shown_km3"]
            text(d, 540, Y_COUNTER, fa(shown), LALEZAR, 170, WHITE, 8)
            if step["label"] in ("1397", "1398") and t < tl["land"]:   # two steps: long enough to read
                text(d, 540, Y_CHIP - 70, GAP_NOTE, XBOLD, 30, WHITE, 4)
            if step["label"] == tl["cross"] and t < tl["land"]:
                text(d, 540, Y_CHIP - 70, CROSS_NOTE, BLACK, 36, GOLD, 6)
        text(d, 540, Y_UNIT, UNIT, BLACK, 44, WHITE, 5)
        if self.voice:
            sub = [s for a, b, s in SUBTITLES if a <= t < b]
            if sub:
                pill(d, 540, Y_SUB, sub[0], XBOLD, 40)
        for k, s in enumerate(SOURCES):
            text(d, 925, Y_SOURCES[k], s, MEDIUM, 22, (225, 230, 236, 255), 3, anchor="rs")
        return im.convert("RGB").resize(size, Image.LANCZOS) if tuple(size) != (W, H) else im.convert("RGB")

    def annotate(self, d: ImageDraw.ImageDraw, t: float, m: dict):
        """Milad Tower's label at its tip; from the rise on, the water's surface above the tower and its height."""
        tl = self.tl
        xt, yt = m["milad_tip"]
        xs, ys = m["surface"]
        if not (0 < xt < W and 380 < yt < 1100):
            return
        if t >= tl["rise"] and m["h_m"] > 20 and 440 < ys < 1100:   # not while it drains (the counter reads 0)
            for xx in range(80, W - 80, 28):                # the layer's top: a dashed line across the frame
                d.line([(xx, ys), (xx + 16, ys)], fill=WATER_INK, width=3)
            h_shown = tl["shown_m"] if t >= tl["land"] else int(round(self.step_at(t)[0]["depth_m"] / 10) * 10)
            text(d, 90, ys - 14, f"{THICKNESS}: {fa(h_shown)} متر", BLACK, 34, WATER_INK, 5, anchor="ls")
        lab = "برجِ میلاد ۴۳۵ متر"                         # drawn after the dashes, so they never cross it
        lw = width(lab, BLACK, 32)
        x0 = min(max(xt + 26, 70), 925 - lw)
        d.line([(xt + 4, yt), (x0 - 6, yt)], fill=WHITE, width=3)
        text(d, x0 + lw, yt + 11, lab, BLACK, 32, WHITE, 4, anchor="rs")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true", help="cover and stills only")
    ap.add_argument("--voice", action="store_true", help="the narrated cut's picture (with subtitles)")
    args = ap.parse_args()
    film = TehranWaterFilm(args.voice)
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / ("tehranwater_fa_voice" if args.voice else "tehranwater_fa")
    for old in (OUT / "social").glob(f"{base.name}_t*.png"):
        old.unlink()
    film.draw(1, 0.0).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        for t in (0.0, 2.0, 5.2, 6.9, 8.6, 12.0, 16.0, 20.0, 24.0):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
