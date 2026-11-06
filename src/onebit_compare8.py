"""TEHRAN AND ISTANBUL, EIGHT WINTERS OF NO2 FROM SPACE: the one-winter film's map and close-ups (winter 1404), and a strip
with the ratio of each winter from 1397 to 1404.

The map, the Turkey-Iran band, the close-ups, the glow, the colour bar and the type are onebit_compare's (imported, not
copied). This module changes the layout (the map band and the close-ups a little smaller, the strip below the close-ups),
adds the counter, the strip, the mean line and the headline, and reads every number from data/air/compare/clim_v1.json.

The one-winter comparison (winter 1404) was pre-registered. The eight-winter climatology uses the same method but was not
pre-registered. The eight-winter ratio is the ratio of the mean Tehran winter day-mean to the mean Istanbul winter
day-mean (air_climatology.winter_boot); the headline shows it rounded down.

Clock (seconds; the score reads these through schedule()):
  STEP_A, STEP_B      the crossfades of the winter field (Azar, Azar + Dey, the whole winter), as onebit_compare
  WORD_SWITCH         the month word changes, as onebit_compare (before the strip starts)
  BAR_TIMES           the bar of winter k (0 for 1397 ... 7 for 1404) starts to rise; BAR_DT apart from BAR_T0
  BAR_RISE            each bar's rise (smoothstep: a soft ease-in and ease-out)
  BAR_TIMES           the counter changes to winter k at the same time as its bar starts
  T_HOLD              the mean line and the headline fade in (T_HOLD_FADE)
  STILLS              the frames the stills are rendered at
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit_compare as oc  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, SIZES, SOCIAL_CRF, fa  # noqa: E402

W, H = oc.W, oc.H
DURATION = oc.DURATION                            # s
STILLS = (0.0, 3.0, 6.0, 10.0, 14.0, 18.0, 23.5)
STEP_A, STEP_B, WORD_SWITCH = oc.STEP_A, oc.STEP_B, oc.WORD_SWITCH
BAR_T0, BAR_DT, BAR_RISE = 4.5, 1.4, 0.8          # s: the first bar, the pitch, each bar's rise
BAR_TIMES = tuple(round(BAR_T0 + k * BAR_DT, 2) for k in range(8))
T_HOLD, T_HOLD_FADE = 17.0, 0.5                   # s: the mean line and the headline
T_LABEL_FADE = 0.5                                # s: the strip's baseline and labels

# ── the layout (px): the map band and the close-ups a little smaller than the one-winter film ──
KX, CY = 24.0, 540.0                              # px per degree of longitude; the map's centre height
SQ = 330                                          # px: a close-up's side (one-winter film: 380)
SQ_X = dict(istanbul=150, tehran=594)
SQ_Y = 740                                        # px: the close-ups' top edge
Y_SCALE = 1096                                    # px: the shared 10 km bar
Y_STRIP = 1252                                    # px: the bars' baseline (value 0)
HMAX = 130.0                                      # px: the height of a ratio of 10
XR, BW, STEP = 880, 32, 48                        # px: winter 1397's bar right edge (RTL), bar width, pitch
STRIP_X = (XR - 7 * STEP - BW, XR)                # the strip's left and right edges (512, 880)
CNT_R = 470                                       # px: the counter's right edge, beside the strip
Y_YEAR, Y_RATIO = 1136, Y_STRIP                   # px: the counter's year line and its ratio line
Y_LAB = 1286                                      # px: the strip's first and last labels
Y_HEAD = (1352, 1420)                             # px: the headline's two baselines
Y_BAR, Y_BAR_NUM, Y_UNIT, Y_SOURCES = 1466, 1512, 1542, 1584
Y_TITLE = (196, 262)
TITLE = ("هشت زمستان از فضا: تهران و استانبول", "دی‌اکسیدِ نیتروژنِ کدام بیشتر است؟")
NAME = oc.NAME
CLOSE_YEAR = 1404                                 # the close-ups and the chips
YEARS = list(range(1397, 1405))
EXPECT = {1397: 4.55, 1398: 5.50, 1399: 9.91, 1400: 9.41, 1401: 6.41, 1402: 8.05, 1403: 6.74, 1404: 5.82}
EXPECT_EIGHT = (6.88, 5.80, 8.11)                 # the eight-winter ratio and its 90 % interval


def load_clim() -> dict:
    """Every number on screen: clim_v1.json, checked against the values the brief names."""
    d = json.loads((oc.DATA / "clim_v1.json").read_text(encoding="utf-8"))
    w = {y: d["winters"][str(y)] for y in YEARS}
    ratio = {y: round(w[y]["ratio"], 2) for y in YEARS}
    assert ratio == EXPECT, ratio
    raw = {y: float(w[y]["ratio"]) for y in YEARS}
    shown = [f"{raw[y]:.1f}" for y in YEARS]
    assert shown == ["4.6", "5.5", "9.9", "9.4", "6.4", "8.0", "6.7", "5.8"], shown
    e = d["eight_winters"]
    assert e["winters"] == YEARS
    eight = (round(e["ratio"], 2), round(e["ci90"][0], 2), round(e["ci90"][1], 2))
    assert eight == EXPECT_EIGHT, eight
    mt = np.mean([w[y]["tehran"] for y in YEARS])
    mi = np.mean([w[y]["istanbul"] for y in YEARS])
    assert abs(mt / mi - e["ratio"]) < 1e-6, "the eight-winter ratio is the ratio of the mean winter day-means"
    c = w[CLOSE_YEAR]
    chips = dict(tehran=round(c["tehran"], 1), istanbul=round(c["istanbul"], 1))
    assert chips == dict(tehran=72.2, istanbul=12.4), chips
    head_n = math.floor(e["ratio"])
    assert head_n == 6
    return dict(w=w, raw=raw, ratio=ratio, eight=e["ratio"], ci=(e["ci90"][0], e["ci90"][1]), chips=chips, head_n=head_n,
                days={y: (w[y]["tehran_days"], w[y]["istanbul_days"]) for y in YEARS})


CLIM = load_clim()
RATIOS = [CLIM["ratio"][y] for y in YEARS]        # the bars, on a 0-10 scale (rounded to 2 places)
RAW = [CLIM["raw"][y] for y in YEARS]             # the counter's figures, shown to 1 decimal from the unrounded ratio
MEAN = CLIM["eight"]
HEAD = (f"در هر ۸ زمستان، تهران بیشتر بود", f"میانگین: حدودِ {fa(CLIM['head_n'])} برابرِ استانبول")
assert HEAD[1].count("۶") == 1 and "۵" not in HEAD[1]
HEAD_PX = next(s for s in range(72, 40, -1)
               if max(oc.width(h, FA_BOLD, s) for h in HEAD) <= 780)      # both lines within the safe width
assert HEAD_PX >= 48, HEAD_PX


def smoothstep(x: float) -> float:
    return oc.smoothstep(x)


def retune() -> None:
    """The one-winter film's functions read their layout from module globals: set this film's layout there."""
    oc.KX, oc.CY, oc.SQ, oc.SQ_X, oc.SQ_Y = KX, CY, SQ, SQ_X, SQ_Y
    oc.Y_SCALE = Y_SCALE
    oc.Y_BAR, oc.Y_BAR_NUM, oc.Y_UNIT, oc.Y_SOURCES = Y_BAR, Y_BAR_NUM, Y_UNIT, Y_SOURCES
    oc.TITLE = TITLE
    c = CLIM["chips"]
    oc.day_means = lambda: {"tehran": c["tehran"], "istanbul": c["istanbul"]}   # the chips: winter 1404's day-means


def fade(layer: Image.Image, a: float) -> Image.Image:
    arr = np.asarray(layer).copy()
    arr[..., 3] = (arr[..., 3].astype(np.float32) * float(np.clip(a, 0, 1))).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


class Film8(oc.Film):
    """The one-winter film's map, close-ups and colour bar, with the eight-winter strip, the counter and the headline."""

    def checks(self) -> None:
        assert oc.VMIN == 2.0 and oc.VMAX == 100.0 and oc.GAMMA == 1.0
        assert len(BAR_TIMES) == 8 and BAR_TIMES[0] == BAR_T0 and abs(BAR_TIMES[-1] - 14.3) < 1e-9
        assert BAR_TIMES[-1] + BAR_RISE <= T_HOLD == 17.0 and 0 < STEP_A[0] < STEP_A[1] <= STEP_B[0] < STEP_B[1]
        assert STEP_B[1] < BAR_T0 + 0.5 and WORD_SWITCH[1] < BAR_T0 and DURATION == 24.0
        for s in TITLE:
            assert oc.width(s, FA_BOLD, 58) <= 960, ("title line too wide", s)
        assert Y_TITLE[0] - 0.9 * 58 > 130, "title top below y 130"
        assert SQ_X["istanbul"] >= 150 and SQ_X["tehran"] + SQ <= 930 and SQ_X["istanbul"] + SQ < SQ_X["tehran"]
        assert SQ_Y + SQ < Y_SCALE - 14 and Y_SCALE + 14 < Y_STRIP - HMAX - 8, "the scale bar sits between the close-ups and the strip"
        assert Y_STRIP < Y_HEAD[0] - 0.9 * HEAD_PX, "the headline clears the strip's labels"
        assert Y_HEAD[1] + 0.3 * HEAD_PX < Y_BAR - 8, "the headline clears the colour bar"
        assert Y_BAR + 24 < Y_BAR_NUM + 4 and Y_BAR_NUM < Y_UNIT < Y_SOURCES < 1600 - 6, "the bottom lines stay above y 1600"
        assert max(oc.width(h, FA_BOLD, HEAD_PX) for h in HEAD) <= 780, "the headline stays off the right edge band"
        assert oc.width(oc.SOURCES, FA_TEXT, 28) <= 780
        assert STRIP_X[0] > CNT_R + 20 and XR <= 930, "the strip stays off the right edge band"
        assert CNT_R - oc.width(f"{fa(1397)}", FA_BOLD, 44) > 130
        ratio_w = oc.width(fa("0.0") + " برابر", FA_BOLD, 40) + oc.width(fa("0.0"), FA_BOLD, 110) + 12
        assert CNT_R - ratio_w > 130, ("counter too wide", ratio_w)
        for t in (0.0, WORD_SWITCH[0] + 1.0, WORD_SWITCH[1] + 1.0):
            assert oc.width(self.word_at(t), FA_BOLD, 40) <= 340, ("month word too wide", self.word_at(t))
        assert 0 < MEAN < 10 and all(0 < r < 10 for r in RATIOS)

    def schedule(self) -> dict:
        """The film's clock, for the score."""
        return dict(step_a=STEP_A, step_b=STEP_B, build=(0.0, oc.T_MAP), month_changes=WORD_SWITCH,
                    bar_times=BAR_TIMES, bar_rise=BAR_RISE, counter_changes=BAR_TIMES,
                    labels_fade=(BAR_T0, BAR_T0 + T_LABEL_FADE), hold=T_HOLD,
                    hold_fade=(T_HOLD, T_HOLD + T_HOLD_FADE), end=DURATION, stills=STILLS,
                    ratios=dict(zip(YEARS, RATIOS)), mean=MEAN)

    # ── the frame ──

    def draw_frame(self, t: float) -> Image.Image:
        t = min(max(t, 0.0), DURATION)
        s = 1.0 + oc.ZOOM * t / DURATION                       # the push-in, as onebit_compare
        w = self.weights(t)
        g = sum(wk * Gk for wk, Gk in zip(w, self.G))
        full = np.clip(oc.paint(self.base, g) + 0.5, 0, 255).astype(np.uint8)
        im = Image.fromarray(full, "RGB").transform(
            (W, H), Image.AFFINE, (1 / s, 0, 540 - 540 / s, 0, 1 / s, oc.CY - oc.CY / s), resample=Image.BILINEAR)
        im = im.convert("RGBA")
        for c in oc.CITY:
            gt = sum(wk * Gk for wk, Gk in zip(w, self.tg[c]))
            im.paste(oc.to_rgb(oc.paint(self.tile[c]["base"], gt)), (SQ_X[c], SQ_Y))
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        for c in oc.CITY:                                       # the leader lines, under the static layer
            x, y = self.xy(*oc.CITY[c], s=s)
            d.line([(x, y), (SQ_X[c] + SQ / 2, SQ_Y - 2)], fill=oc.PAPER[:3] + (170,), width=2)
        for c in oc.CITY:
            x, y = self.xy(*oc.CITY[c], s=s)
            d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=oc.PAPER, outline=oc.SHADOW, width=2)
            f = oc.font(FA_BOLD, 34)
            tw = f.getlength(NAME[c], direction="rtl", language="fa")
            lx, ly = x + 16, y - 52
            d.rounded_rectangle([lx, ly, lx + tw + 22, ly + 46], radius=10, fill=(8, 10, 14, 215))
            oc.text(ov, lx + tw / 2 + 11, ly + 36, NAME[c], FA_BOLD, 34, stroke=2)
        lab = f"زمستانِ {fa(CLOSE_YEAR)}"                       # the close-ups' winter, between the two frames
        tw = oc.font(FA_BOLD, 34).getlength(lab, direction="rtl", language="fa")
        d.rounded_rectangle([540 - tw / 2 - 12, SQ_Y - 50, 540 + tw / 2 + 12, SQ_Y - 8], radius=10, fill=(8, 10, 14, 215))
        oc.text(ov, 540, SQ_Y - 16, lab, FA_BOLD, 34, stroke=2)
        im.alpha_composite(ov)
        im.alpha_composite(self.static)
        self.counter(im, t)
        self.strip(im, t)
        self.headline(im, t)
        return im.convert("RGB")

    def counter(self, im: Image.Image, t: float) -> None:
        """The counter, fading out over the hold's fade-in so that only the headline carries the mean."""
        if t >= T_HOLD + T_HOLD_FADE:
            return
        if t >= T_HOLD:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            self._counter(lay, t)
            im.alpha_composite(fade(lay, 1 - smoothstep((t - T_HOLD) / T_HOLD_FADE)))
            return
        self._counter(im, t)

    def _counter(self, im: Image.Image, t: float) -> None:
        """Beside the strip: the month word while the map builds, then the current winter and its ratio."""
        if t < BAR_T0:
            oc.text(im, CNT_R, Y_RATIO, self.word_at(t), FA_BOLD, 40, anchor="rs")
            return
        k = max(i for i in range(8) if t >= BAR_TIMES[i])
        word_w = oc.text(im, CNT_R, Y_RATIO, "برابر", FA_BOLD, 40, anchor="rs")
        oc.text(im, CNT_R - word_w - 12, Y_RATIO, fa(f"{RAW[k]:.1f}"), FA_BOLD, 110, anchor="rs")   # the house «٫»
        oc.text(im, CNT_R, Y_YEAR, fa(YEARS[k]), FA_BOLD, 44, anchor="rs")

    def strip(self, im: Image.Image, t: float) -> None:
        """Eight bars, one per winter, 1397 on the right; each rises from its BAR_TIMES entry; the mean line from T_HOLD."""
        if t < BAR_T0:
            return
        bars = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(bars)
        for k in range(8):
            tk = BAR_TIMES[k]
            if t < tk:
                continue
            a = smoothstep((t - tk) / BAR_RISE)
            x1 = XR - k * STEP
            x0 = x1 - BW
            top = Y_STRIP - RATIOS[k] / 10 * HMAX * a
            d.rectangle([round(x0), round(top), round(x1) - 1, Y_STRIP], fill=oc.AMBER)
        if t >= T_HOLD:
            y = Y_STRIP - MEAN / 10 * HMAX
            xa, xb = STRIP_X[0] - 12, STRIP_X[1]
            x = xa
            while x < xb:
                d.line([(x, y), (min(x + 13, xb), y)], fill=oc.PAPER, width=2)
                x += 22
        im.alpha_composite(bars)
        lab = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lab)
        d.line([(STRIP_X[0] - 12, Y_STRIP), (STRIP_X[1], Y_STRIP)], fill=oc.PAPER[:3] + (150,), width=2)
        oc.text(lab, XR - BW / 2, Y_LAB, fa(YEARS[0]), FA_TEXT, 30, anchor="ms", stroke=3)
        oc.text(lab, XR - 7 * STEP - BW / 2, Y_LAB, fa(YEARS[-1]), FA_TEXT, 30, anchor="ms", stroke=3)
        im.alpha_composite(fade(lab, (t - BAR_T0) / T_LABEL_FADE))

    def headline(self, im: Image.Image, t: float) -> None:
        if t < T_HOLD:
            return
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        oc.text(lay, 540, Y_HEAD[0], HEAD[0], FA_BOLD, HEAD_PX, fill=oc.AMBER, stroke=6)
        oc.text(lay, 540, Y_HEAD[1], HEAD[1], FA_BOLD, HEAD_PX, fill=oc.AMBER, stroke=6)
        im.alpha_composite(fade(lay, smoothstep((t - T_HOLD) / T_HOLD_FADE)))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true", help="the stills at STILLS, no video")
    ap.add_argument("--check", action="store_true", help="the colour check of the close-ups, as onebit_compare")
    args = ap.parse_args()
    retune()
    film = Film8()
    print("schedule", film.schedule(), flush=True)
    print("headline size", HEAD_PX, "px; chips", CLIM["chips"], "; eight-winter", round(MEAN, 2), CLIM["ci"], flush=True)
    if args.check:
        film.colour_check()
        return
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / "compare8_tehran_istanbul_fa"
    if args.stills:
        for t in STILLS:
            p = f"{base}_t{t:04.1f}.png"
            film.draw(1, t).save(p)
            print("saved", p, flush=True)
        return
    import onebit
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
