"""TEHRAN AND ISTANBUL, EIGHT WINTERS OF NO2 FROM SPACE, PHONE-SIZED: the map, then the two close-ups, then the strip, then
the reasons. A redesign of onebit_compare8r for a phone screen: one main picture per scene, and every word at 40 px or more.

The map, its glow, the close-up fields and the type are onebit_compare's (imported, not copied), as are the eight-winter
strip's data and clock (onebit_compare8) and the reason chips and the narration clock (onebit_compare8r). Nothing in those
files is edited. This film changes three things of onebit_compare's:
  - the field: the eight-winter average (winter8 of region_8winters_v1.npz: every 4th day, 539 passes), in the map and in
    both close-ups; the bars and the headline use every day (clim_v1.json);
  - the transfer (1e15 molec/cm2): no glow at NO2 <= 2 (clean air stays dark land); a smoothstep rise from 2 to 5 to a glow
    of 0.40; from 5 on, glow = 0.40 + 0.60 * ((NO2 - 5) / 95) ** 0.6, clipped at 1. The same transfer for the map, the
    close-ups and the colour bar;
  - the map's push-in (1 + ZOOM at 30 s), and a glow that starts at GLOW0 (55 %) at 0 s and reaches full strength at T_FULL.

Clock (seconds; the narration clock is FIXED, as onebit_compare8r):
  N1 0.20-4.81, N2 5.50-8.34, N3 10.20-14.2, N4 17.00-19.09, N5 19.50-28.75; DURATION 30.0
  0 - 4.5      S1  the title, and the Turkey-Iran glow map as large as the width allows, with both city labels and the
                   label «میانگینِ هشت زمستان، ۱۳۹۷ تا ۱۴۰۴» under the title
  4.5 - 5.3    S2  the map gives way (its glow fades, the land goes flat); the two close-ups grow from 72 % to full size
                   (smoothstep); the colour bar, the unit line and the scale bar fade in; the label becomes «میانگینِ ۸ زمستان»
                   above the close-ups; the strip's bars rise from 4.5 s
  17.0 - 17.5  S3  the counter fades; the headline fades in (the mean line from 17.0 s)
  19.5 - 20.0  S4  the strip and its labels fade out; the four reason chips appear, each at its word onset in N5:
                   20.55 (وارونگیِ هوا), 23.31 (خودروهای فرسوده), 24.87 (سوختِ کم‌کیفیت), 26.29 (سوءمدیریت)

Layout (px, 1080 x 1920). Below y 1000 nothing lies right of x 930 (the Instagram buttons), and nothing is read below y 1600.
  title         146-290   two lines, 60-66 px, centred (the top below y 130)
  label         ~318-345  40 px, centred: the long label (S1) and the short one with the close-ups (S2 on)
  close-ups     362-842   two 480 px squares, 24 px apart; Istanbul left, Tehran right; name chips 56 px inside
  scale bar     ~862-895  20 km (53 px) under Istanbul, label 40 px
  colour bar    920-942   x 120-930, ticks 40 px at baseline 996 (2, 10, 25, 50, 100 at their transfer positions)
  unit line     1014-1102 40 px, two lines: «دی‌اکسیدِ نیتروژن در ستونِ هوا،» / «۱۰^۱۵ مولکول بر سانتی‌مترِ مربع»
  counter       1100-1262 year 48 px and ratio 120 px (right, x 930), the left label 40 px (S2 and S3 only)
  headline      1156-1232 two lines, 64 px (S3 on), centred at x 510 (inside 90-930)
  strip         bars 1284-1492 (HMAX 208 = 1.6 x 130), 1397 at the RIGHT, 1404 at the LEFT; labels 40 px at 1528
  hedge label   1284      «دلیل‌های احتمالی» 40 px (S4, with the chips)
  reason chips  1300-1492 2 x 2, 56 px, centred at x 510 (S4 only; the strip has faded)
  sources       1576      40 px, one line (ESA and NASA credits)

    python -I src/onebit_compare8m.py              # the silent reel (its cover from frame 0, then the MP4)
    python -I src/onebit_compare8m.py --stills     # the stills at STILLS
    python -I src/onebit_compare8m.py --check      # the colour check of the close-ups (the land boxes against winter8)
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
import onebit_compare8 as f8  # noqa: E402
import onebit_compare8r as f8r  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, SIZES, SOCIAL_CRF, fa  # noqa: E402

W, H = oc.W, oc.H
DURATION = 30.0                                   # s: the reel (N5 ends at 28.75 s)
BASE = "compare8m_tehran_istanbul_fa"
STILLS = (0.0, 3.0, 8.0, 13.0, 18.0, 22.0, 27.0)
S2 = (4.5, 5.3)                                   # s: the map gives way, the close-ups grow in (0.8 s ease)
GLOW0, T_FULL = 0.55, 4.8                         # the glow: 55 % at 0 s, full strength at T_FULL
BAR_T0, BAR_RISE = f8.BAR_T0, f8.BAR_RISE
BAR_TIMES = f8.BAR_TIMES
T_HOLD, T_HOLD_FADE = f8.T_HOLD, f8.T_HOLD_FADE   # s: the counter fades, the headline and the mean line come in
STRIP_FADE = f8r.STRIP_FADE                       # s: the strip and its labels fade out
CHIP_FADE = f8r.CHIP_FADE                         # s: each chip fades in from its onset
CHIP_TEXT, CHIP_T = f8r.CHIP_TEXT, f8r.CHIP_T
N5_START, N5_END = f8r.N5_START, f8r.N5_END    # s: the fifth narration line's speech (the score's clock)
CLOSE_YEAR = f8.CLOSE_YEAR
YEARS, RATIOS, RAW, MEAN = f8.YEARS, f8.RATIOS, f8.RAW, f8.MEAN
DIGIT = int(math.floor(MEAN))                     # the headline rounds DOWN: 6.88 is shown as «حدودِ ۶ برابر»
HEAD = ("در هر ۸ زمستان، در تهران بیشتر بود", f"میانگین: حدودِ {fa(DIGIT)} برابرِ استانبول")
DARK = (10.0, 12.0, 16.0)                         # the flat ground under the close-ups (S2 on)
REGION8 = oc.DATA / "region8" / "region_8winters_v1.npz"   # the eight-winter field (winter8) and its coverage

# ── the transfer: one scale for the map, the close-ups and the bar ──
GLOW_FLOOR, GAMMA_T = 0.40, 0.6                   # the glow at the knee (5, 1e15) is 0.40; the curve above it rises as a square root
KNEE_LO, KNEE_HI = 2.0, 5.0                       # 1e15 molec/cm2: no glow at or below KNEE_LO; smoothstep up to GLOW_FLOOR at KNEE_HI
TICK_VALUES = (10, 25, 50)                        # the bar's ticks; 2 and 100 are its ends

# ── the layout (px) ──
KX, CY = 25.0, 660.0                              # the map: px per degree of longitude; the map's centre height
TITLE = ("هشت زمستان از فضا: تهران و استانبول", "دی‌اکسیدِ نیتروژن کجا بیشتر است؟")
TITLE_PX = next(s for s in range(66, 59, -1) if max(oc.width(t, FA_BOLD, s) for t in TITLE) <= 940)
Y_TITLE = (196, 276)
Y_WORD, WORD_PX = 340, 40
WORD_LONG = f"میانگینِ هشت زمستان، {fa(1397)} تا {fa(1404)}"
WORD_SHORT = f"میانگینِ {fa(8)} زمستان"
SQ = 480                                          # px: a close-up's side
SQ_X = dict(istanbul=48, tehran=552)              # px: the close-ups' left edges (Tehran's right edge at 1032)
SQ_Y = 362                                        # px: the close-ups' top edge (their bottom at 842)
NAME_PX = 56
SCALE_KM = 20
Y_SCALE = 880                                     # px: the scale bar's line
SCALE_PX = 40
BAR_X, Y_BAR, BAR_H = (120, 930), 920, 22         # px: the colour bar (x 120-930, the right edge within the content column)
TICK_PX, Y_BAR_NUM = 40, 996
Y_UNIT = (1044, 1092)                             # px: the unit line's two baselines
UNIT_PX = 40
PE_PX = 32                                        # px: the exponent «۱۵» (raised; 28 px is the floor on a phone)
COL = (90, 930)                                   # px: the content column below y 1000
COL_C = 510                                       # px: its centre
XR = 930                                          # px: the strip's and the counter's right edge
Y_YEAR, Y_RATIO = 1150, 1262                      # px: the counter's year line and its ratio line
YEAR_PX, RATIO_PX, WORD_BIG_PX = 48, 120, 48
LEFT_PX = 40                                      # px: the counter's left label
HMAX = 208                                        # px: the strip's height for a ratio of 10 (1.6 x 130)
Y_STRIP = 1492                                    # px: the bars' baseline (value 0)
BW, STEP = 56, 97.5                               # px: bar width and pitch (eight bars across 190-930)
STRIP_X0 = XR - 7 * STEP - BW                     # px: the strip's left edge (the 1404 bar)
Y_LAB, LAB_PX = 1528, 40
Y_HEAD = (1156, 1232)                             # px: the headline's two baselines
HEAD_PX = next(s for s in range(64, 55, -1)                  # the largest size (64 px at most) that fits the column
                 if max(oc.width(h, FA_BOLD, s) for h in HEAD) <= COL[1] - COL[0] - 4)
CHIP_ROW_Y = (1300, 1408)                         # px: the reason chips' two rows
CHIP_PX, CHIP_H, CHIP_GAP, CHIP_PAD = 56, 84, 16, 48
HEDGE, HEDGE_PX, Y_HEDGE = "دلیل‌های احتمالی", 40, 1284   # px: the hedge above the chips (the narration's «می‌تواند»)
ROW_OF = ((0, 1), (2, 3))                         # chips per row; the first of a row at the right (reading order)
Y_SOURCES, SRC_PX = 1576, 40
SOURCES = "Sentinel-5P (ESA) · NASA Blue Marble"
UNIT_A, UNIT_E, UNIT_C = "۱۰", "۱۵", " مولکول بر سانتی‌مترِ مربع"
UNIT_L1 = "دی‌اکسیدِ نیتروژن در ستونِ هوا،"


def smoothstep(x: float) -> float:
    return oc.smoothstep(x)


def _ss(x):
    """smoothstep on arrays, clipped to 0-1."""
    t = np.clip(np.asarray(x, float), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def layer() -> Image.Image:
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def intensity(raw):
    """The one transfer (map, close-ups, bar): NO2 (1e15 molec/cm2) to a glow 0-1. Zero at or below KNEE_LO (clean land
    stays dark); a smoothstep to GLOW_FLOOR at KNEE_HI; above it 0.40 + 0.60 * ((v - KNEE_HI) / 95) ** GAMMA_T, clipped."""
    v = np.nan_to_num(np.asarray(raw, float), nan=oc.VMIN)
    low = GLOW_FLOOR * _ss((v - KNEE_LO) / (KNEE_HI - KNEE_LO))
    span = oc.VMAX - KNEE_HI
    high = GLOW_FLOOR + (1.0 - GLOW_FLOOR) * np.clip((v - KNEE_HI) / span, 0.0, 1.0) ** GAMMA_T
    return np.where(v <= KNEE_HI, low, high)


def invert(g):
    """The NO2 value of a glow g (the inverse of intensity, clipped to the scale): values with no glow read as KNEE_LO."""
    g = np.clip(np.asarray(g, float), 0.0, 1.0)
    grid = np.linspace(0.0, 1.0, 20001)
    x_low = np.interp(np.clip(g / GLOW_FLOOR, 0.0, 1.0), _ss(grid), grid)     # the smoothstep's inverse
    v_low = KNEE_LO + (KNEE_HI - KNEE_LO) * x_low
    y = np.clip((g - GLOW_FLOOR) / (1.0 - GLOW_FLOOR), 0.0, 1.0)
    v_high = KNEE_HI + (oc.VMAX - KNEE_HI) * y ** (1.0 / GAMMA_T)
    return np.clip(np.where(g <= GLOW_FLOOR, v_low, v_high), oc.VMIN, oc.VMAX)


def bar_x(v: float) -> float:
    """Output px of value v on this film's colour bar: the bar is linear in glow, from 0 (2) to 1 (100)."""
    return BAR_X[0] + float(intensity(v)) * (BAR_X[1] - BAR_X[0])


def retune() -> None:
    """onebit_compare's functions read the layout and the transfer from its module globals: set them here."""
    oc.KX, oc.CY, oc.SQ, oc.SQ_X, oc.SQ_Y = KX, CY, SQ, SQ_X, SQ_Y
    oc.intensity = intensity


def ratio_layer(lay, x_right: float, y: float, value: float) -> float:
    """The ratio on screen, one decimal, with a drawn dot. The font draws the Persian decimal sign as a slash, which a
    lay viewer reads as a fraction («۹/۹»); the dot is drawn on the baseline between the two digits instead."""
    ip, dp = f"{value:.1f}".split(".")
    w_dec = oc.text(lay, x_right, y, fa(dp), FA_BOLD, RATIO_PX, anchor="rs", stroke=4)
    r = 0.065 * RATIO_PX                                   # px: the dot's radius (8 px at 120 px)
    cx = x_right - w_dec - 14 - r
    ImageDraw.Draw(lay).ellipse([cx - r, y - 2 * r, cx + r, y], fill=oc.PAPER, outline=oc.SHADOW, width=3)
    return oc.text(lay, cx - r - 14, y, fa(ip), FA_BOLD, RATIO_PX, anchor="rs", stroke=4)


def chip_boxes() -> list:
    """Each reason chip's box (x0, y0, width) in px: two rows, centred on COL_C, the first chip of a row at the right."""
    wid = [oc.width(s, FA_BOLD, CHIP_PX) + CHIP_PAD for s in CHIP_TEXT]
    boxes = [None] * 4
    for row, (a, b) in enumerate(ROW_OF):
        total = wid[a] + CHIP_GAP + wid[b]
        right = COL_C + total / 2
        y0 = CHIP_ROW_Y[row]
        boxes[a] = (right - wid[a], y0, wid[a])
        boxes[b] = (right - wid[a] - CHIP_GAP - wid[b], y0, wid[b])
    for x0, y0, bw in boxes:
        assert COL[0] <= x0 and x0 + bw <= COL[1], ("a chip leaves the content column", x0, bw)
        assert y0 + CHIP_H < 1600, "a chip leaves the safe zone"
    return boxes


BOXES = None


class Film8M(oc.Film):
    """The phone-sized eight-winter film: the map, the close-ups, the strip, the headline and the reason chips."""

    def __init__(self):
        retune()
        super().__init__()
        z8 = np.load(REGION8)
        w8, _ = oc.ascending(z8["winter8"].astype(np.float32), z8["lat"], 0)
        self.fields = {"winter8": w8}
        self.G = [self.make_map_glow("winter8")]                       # the map: the eight-winter average
        self.tg = {c: [self.make_tile_glow(c, "winter8")] for c in oc.CITY}   # the close-ups: the same field
        self.static_s2 = self.make_static_s2()
        self.L = type("L", (), {"end": DURATION})()     # the length onebit.video reads

    # ── checks ──

    def checks(self) -> None:
        assert oc.VMIN == 2.0 and oc.VMAX == 100.0
        f8r.check_clock()
        assert DURATION == 30.0 and 0 < S2[0] < S2[1] <= BAR_T0 + 0.8 + 1e-9
        assert S2[0] == BAR_T0, "the close-ups and the strip start together"
        assert 0 < GLOW0 < 1 and 0 < T_FULL <= S2[0] + 0.5
        assert 0.35 <= GLOW_FLOOR <= 0.45 and GAMMA_T == 0.6 and KNEE_LO == 2.0 and KNEE_HI == 5.0, "the transfer"
        assert float(intensity(2.0)) == 0.0 and float(intensity(1.0)) == 0.0, "clean air takes no glow"
        assert abs(float(intensity(KNEE_HI)) - GLOW_FLOOR) < 1e-12 and abs(float(intensity(100.0)) - 1.0) < 1e-12
        assert abs(float(intensity(10.0)) - (GLOW_FLOOR + 0.6 * (5.0 / 95.0) ** 0.6)) < 1e-9, "the knee formula"
        assert float(intensity(79.2)) / float(intensity(10.7)) > 1.5, "Tehran reads clearly brighter than Istanbul"
        assert np.all(np.diff(intensity(np.linspace(0, 100, 2000))) >= 0), "the transfer is monotone"
        assert np.all(np.abs(invert(intensity(np.linspace(2, 100, 400))) - np.linspace(2, 100, 400)) < 1e-3), "invert inverts"
        assert abs(bar_x(2.0) - BAR_X[0]) < 1e-9 and abs(bar_x(100.0) - BAR_X[1]) < 1e-9
        assert all(BAR_X[0] < bar_x(v) < BAR_X[1] for v in TICK_VALUES)
        assert HMAX == round(1.6 * f8.HMAX), ("the strip is 1.6 x taller than onebit_compare8's", HMAX)
        assert all(0 < r < 10 for r in RATIOS) and 0 < MEAN < 10
        d = json.loads((oc.DATA / "clim_v1.json").read_text(encoding="utf-8"))
        assert [round(d["winters"][str(y)]["ratio"], 2) for y in YEARS] == RATIOS, "the bars are clim_v1's ratios"
        assert DIGIT == 6 and math.floor(MEAN) == DIGIT and HEAD[1].count(fa(DIGIT)) == 1 and "۷" not in HEAD[1], \
            ("the headline digit is the floor of the mean", MEAN, DIGIT)
        assert "۷" not in HEAD[1]
        assert TITLE_PX >= 60 and max(oc.width(s, FA_BOLD, TITLE_PX) for s in TITLE) <= 940, "title line too wide"
        assert Y_TITLE[0] - 0.75 * TITLE_PX > 130, "title top below y 130"
        assert SQ >= 480 and SQ_X["istanbul"] >= 40 and SQ_X["tehran"] + SQ <= 1040
        assert SQ_X["istanbul"] + SQ + 16 < SQ_X["tehran"], "the squares do not touch"
        assert SQ_Y + SQ < 1000 and Y_WORD + 0.25 * WORD_PX < SQ_Y, "the label clears the close-ups"
        assert max(oc.width(WORD_LONG, FA_BOLD, WORD_PX), oc.width(WORD_SHORT, FA_BOLD, WORD_PX)) <= 900
        assert WORD_PX >= 40 and Y_TITLE[1] + 0.25 * TITLE_PX < Y_WORD - 0.75 * WORD_PX, "the label clears the title"
        assert NAME_PX >= 56 and all(oc.width(n, FA_BOLD, NAME_PX) + 24 <= SQ - 28 for n in oc.NAME.values())
        assert SCALE_PX >= 40 and TICK_PX >= 40 and UNIT_PX >= 40 and LEFT_PX >= 40 and LAB_PX >= 40 and HEDGE_PX >= 40
        assert Y_HEAD[1] + 0.25 * HEAD_PX < Y_HEDGE - 0.75 * HEDGE_PX and Y_HEDGE + 0.25 * HEDGE_PX < CHIP_ROW_Y[0] - 4
        assert BAR_X[1] <= XR and Y_BAR_NUM < 1000 and Y_BAR + BAR_H + 8 < Y_BAR_NUM - 30
        assert max(oc.width(s, FA_TEXT, UNIT_PX) for s in (UNIT_L1,)) <= 840
        assert Y_UNIT[0] > Y_BAR_NUM and Y_UNIT[1] < 1100 + 1
        assert YEAR_PX >= 48 and RATIO_PX >= 120 and WORD_BIG_PX >= 48
        assert oc.width(f"زمستانِ {fa(1397)}", FA_BOLD, YEAR_PX) < XR - (COL[0] + oc.width("نسبتِ تهران به استانبول", FA_BOLD, LEFT_PX)) - 30
        assert max(oc.width(s, FA_BOLD, HEAD_PX) for s in HEAD) <= COL[1] - COL[0] - 4, "headline too wide for the column"
        assert HEAD_PX >= 56 and Y_HEAD[0] > Y_UNIT[1] + 40, "the headline sits below the unit line"
        assert Y_HEAD[1] + 14 < Y_STRIP - HMAX, "the headline clears the strip's tallest bar"
        assert Y_STRIP < Y_LAB < Y_LAB + 10 < 1600 - SRC_PX, "the strip's labels stay above the sources line"
        assert SRC_PX >= 40 and oc.width(SOURCES, FA_TEXT, SRC_PX) <= 840, ("sources line", oc.width(SOURCES, FA_TEXT, SRC_PX))
        assert PE_PX >= 28, "the exponent is at least 28 px"
        assert Y_SOURCES < 1600 - 8 and CHIP_ROW_Y[1] + CHIP_H < 1600
        assert CHIP_PX >= 56 and f8r.CHIP_T[0] > S2[1] and f8r.CHIP_T[0] >= STRIP_FADE[1]
        assert all(a < b for a, b in zip(CHIP_T, CHIP_T[1:]))
        assert oc.width(UNIT_A + UNIT_E + UNIT_C, FA_TEXT, UNIT_PX) < 840, "the second unit line fits"
        assert 0 < T_HOLD < STRIP_FADE[0] + 0.5, "the headline comes in with the counter's fade"

    def schedule(self) -> dict:
        """The film's clock, for the score."""
        return dict(s2=S2, step_a=f8.STEP_A, step_b=f8.STEP_B, bar_times=BAR_TIMES, bar_rise=BAR_RISE,
                    hold=T_HOLD, hold_fade=(T_HOLD, T_HOLD + T_HOLD_FADE), strip_fade=STRIP_FADE,
                    chips=dict(zip(CHIP_TEXT, CHIP_T)), chip_fade=CHIP_FADE, end=DURATION, stills=STILLS,
                    glow=(GLOW0, T_FULL), ratios=dict(zip(YEARS, RATIOS)), mean=MEAN, headline_digit=DIGIT)

    def glow_gain(self, t: float) -> float:
        """The glow's strength: 55 % at 0 s, full at T_FULL (smoothstep)."""
        return GLOW0 + (1.0 - GLOW0) * smoothstep(min(max(t, 0.0), T_FULL) / T_FULL)

    # ── the static layers ──

    def make_static(self) -> Image.Image:
        """The title and the sources line (on all the time)."""
        im = layer()
        for s, y in zip(TITLE, Y_TITLE):
            oc.text(im, 540, y, s, FA_BOLD, TITLE_PX, stroke=5)
        oc.text(im, 505, Y_SOURCES, SOURCES, FA_TEXT, SRC_PX, stroke=3)
        return im

    def make_static_s2(self) -> Image.Image:
        """The colour bar with its ticks, the unit line, the scale bar: the key of the close-ups (from S2)."""
        im = layer()
        d = ImageDraw.Draw(im)
        x0, x1 = BAR_X
        for xx in range(x0, x1 + 1):
            g = GLOW_FLOOR + (xx - x0) / (x1 - x0) * (1.0 - GLOW_FLOOR)   # the bar shows the glow itself
            col = np.clip(oc.paint(self.bar_base, np.full((1, 1), g, np.float32))[0, 0] + 0.5, 0, 255)
            d.line([(xx, Y_BAR), (xx, Y_BAR + BAR_H)], fill=tuple(int(q) for q in col) + (255,))
        d.rectangle([x0, Y_BAR, x1, Y_BAR + BAR_H], outline=oc.PAPER, width=2)
        for v in TICK_VALUES:
            xt = bar_x(v)
            d.line([(xt, Y_BAR + BAR_H), (xt, Y_BAR + BAR_H + 8)], fill=oc.PAPER, width=2)
            oc.text(im, xt, Y_BAR_NUM, fa(v), FA_TEXT, TICK_PX, stroke=3)
        oc.text(im, x0, Y_BAR_NUM, fa(int(oc.VMIN)), FA_TEXT, TICK_PX, stroke=3)
        oc.text(im, x1, Y_BAR_NUM, fa(int(oc.VMAX)), FA_TEXT, TICK_PX, stroke=3)
        # the unit: two lines, the exponent raised (the font has no superscript digits), read from the right
        oc.text(im, COL_C, Y_UNIT[0], UNIT_L1, FA_TEXT, UNIT_PX, stroke=3)
        pe, gap = PE_PX, 10                                # px: the exponent, 10 px clear of the base
        fa_, fe_ = oc.font(FA_TEXT, UNIT_PX), oc.font(FA_TEXT, pe)
        wA = fa_.getlength(UNIT_A, direction="rtl", language="fa")
        wC = fa_.getlength(UNIT_C, direction="rtl", language="fa")
        wE = fe_.getlength(UNIT_E, direction="rtl", language="fa")
        total = wA + gap + wE + wC
        x_r = COL_C + total / 2 + 6
        oc.text(im, x_r - wA / 2, Y_UNIT[1], UNIT_A, FA_TEXT, UNIT_PX, stroke=3)
        oc.text(im, x_r - wA - gap - wE / 2, Y_UNIT[1] - 0.45 * UNIT_PX, UNIT_E, FA_TEXT, pe, stroke=2)
        oc.text(im, x_r - wA - gap - wE - wC / 2, Y_UNIT[1], UNIT_C, FA_TEXT, UNIT_PX, stroke=3)
        # the scale bar under Istanbul: 20 km at the close-ups' scale
        px_km = SQ / (2 * oc.HALF_KM)
        L = SCALE_KM * px_km
        sx = SQ_X["istanbul"]
        d.line([(sx, Y_SCALE), (sx + L, Y_SCALE)], fill=oc.PAPER, width=4)
        d.line([(sx, Y_SCALE - 9), (sx, Y_SCALE + 9)], fill=oc.PAPER, width=3)
        d.line([(sx + L, Y_SCALE - 9), (sx + L, Y_SCALE + 9)], fill=oc.PAPER, width=3)
        lab = f"{fa(SCALE_KM)} کیلومتر"
        wl = oc.font(FA_TEXT, SCALE_PX).getlength(lab, direction="rtl", language="fa")
        oc.text(im, sx + L + 18 + wl / 2, Y_SCALE + 12, lab, FA_TEXT, SCALE_PX, stroke=3)
        return im

    # ── the layers of each scene ──

    def markers(self, a: float, s: float) -> Image.Image:
        """S1: the two cities, marked, with their names at 48 px (the map's labels), under the push-in s."""
        lay = layer()
        d = ImageDraw.Draw(lay)
        for c in oc.CITY:
            x, y = self.xy(*oc.CITY[c], s=s)
            d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=oc.PAPER, outline=oc.SHADOW, width=2)
            f = oc.font(FA_BOLD, 48)
            tw = f.getlength(oc.NAME[c], direction="rtl", language="fa")
            if c == "istanbul":
                lx, ly = x + 18, y - 90
            else:
                lx, ly = x + 22, y - 31
            d.rounded_rectangle([lx, ly, lx + tw + 28, ly + 62], radius=12, fill=(8, 10, 14, 220))
            oc.text(lay, lx + tw / 2 + 14, ly + 48, oc.NAME[c], FA_BOLD, 48, stroke=3)
        return f8.fade(lay, a)

    def closeups(self, t: float, e: float) -> Image.Image:
        """S2: the two close-ups, from 72 % of their size to full, with their name chips (56 px)."""
        lay = layer()
        k = 0.72 + 0.28 * e
        n = round(SQ * k)
        d = ImageDraw.Draw(lay)
        for c in oc.CITY:
            gt = self.tg[c][0] * self.glow_gain(t)
            sq = oc.to_rgb(oc.paint(self.tile[c]["base"], gt)).convert("RGBA")
            if n != SQ:
                sq = sq.resize((n, n), Image.BILINEAR)
            x0 = round(SQ_X[c] + SQ / 2 - n / 2)
            y0 = round(SQ_Y + SQ / 2 - n / 2)
            lay.paste(sq, (x0, y0))
            d.rectangle([x0 - 1, y0 - 1, x0 + n, y0 + n], outline=oc.PAPER, width=2)
        for c in oc.CITY:
            lab = oc.NAME[c]
            tw = oc.font(FA_BOLD, NAME_PX).getlength(lab, direction="rtl", language="fa")
            lx, ly = SQ_X[c] + 14, SQ_Y + 14
            d.rounded_rectangle([lx, ly, lx + tw + 24, ly + 76], radius=12, fill=(8, 10, 14, 220))
            oc.text(lay, lx + tw / 2 + 12, ly + 58, lab, FA_BOLD, NAME_PX, stroke=3)
        return f8.fade(lay, e)

    def strip_layer(self, t: float) -> Image.Image:
        """The eight-winter strip (1397 at the RIGHT, 1404 at the left), the mean line from T_HOLD, the two year labels."""
        lay = layer()
        d = ImageDraw.Draw(lay)
        for k in range(8):
            tk = BAR_TIMES[k]
            if t < tk:
                continue
            a = smoothstep((t - tk) / BAR_RISE)
            x0 = STRIP_X0 + (7 - k) * STEP            # winter k: time runs right to left (1397 at the right)
            x1 = x0 + BW
            top = Y_STRIP - RATIOS[k] / 10 * HMAX * a
            d.rectangle([round(x0), round(top), round(x1) - 1, Y_STRIP], fill=oc.AMBER)
        d.line([(STRIP_X0 - 12, Y_STRIP), (XR, Y_STRIP)], fill=oc.PAPER[:3] + (150,), width=2)
        if t >= T_HOLD:
            y = Y_STRIP - MEAN / 10 * HMAX
            x = STRIP_X0 - 12
            while x < XR:
                d.line([(x, y), (min(x + 13, XR), y)], fill=oc.PAPER, width=2)
                x += 22
        oc.text(lay, XR - BW / 2, Y_LAB, fa(YEARS[0]), FA_TEXT, LAB_PX, stroke=3)
        oc.text(lay, STRIP_X0 + BW / 2, Y_LAB, fa(YEARS[-1]), FA_TEXT, LAB_PX, stroke=3)
        return lay

    def counter_layer(self, t: float) -> Image.Image:
        """The counter beside the strip: the winter's year (48 px) and its ratio (120 px), and the left label (40 px)."""
        lay = layer()
        wl = oc.font(FA_BOLD, LEFT_PX).getlength("نسبتِ تهران به استانبول", direction="rtl", language="fa")
        oc.text(lay, COL[0] + wl / 2, Y_YEAR, "نسبتِ تهران به استانبول", FA_BOLD, LEFT_PX, stroke=3)
        if t < BAR_T0:
            return lay
        k = max(i for i in range(8) if t >= BAR_TIMES[i])
        oc.text(lay, XR, Y_YEAR, f"زمستانِ {fa(YEARS[k])}", FA_BOLD, YEAR_PX, anchor="rs", stroke=3)
        word_w = oc.text(lay, XR, Y_RATIO, "برابر", FA_BOLD, WORD_BIG_PX, anchor="rs", stroke=3)
        ratio_layer(lay, XR - word_w - 12, Y_RATIO, RAW[k])
        return lay

    def headline_layer(self) -> Image.Image:
        lay = layer()
        for s, y in zip(HEAD, Y_HEAD):
            oc.text(lay, COL_C, y, s, FA_BOLD, HEAD_PX, fill=oc.AMBER, stroke=6)
        return lay

    def hedge_layer(self) -> Image.Image:
        lay = layer()
        oc.text(lay, COL_C, Y_HEDGE, HEDGE, FA_BOLD, HEDGE_PX, stroke=3)
        return lay

    def chip_layer(self, i: int) -> Image.Image:
        global BOXES
        if BOXES is None:
            BOXES = chip_boxes()
        lay = layer()
        d = ImageDraw.Draw(lay)
        x0, y0, bw = BOXES[i]
        d.rounded_rectangle([x0, y0, x0 + bw, y0 + CHIP_H], radius=12, fill=(8, 10, 14, 220))
        oc.text(lay, x0 + bw / 2, y0 + CHIP_H - 22, CHIP_TEXT[i], FA_BOLD, CHIP_PX, stroke=3)
        return lay

    def word_layer(self, e: float) -> Image.Image:
        """The label under the title (S1, «میانگینِ هشت زمستان»), which becomes the close-ups' label (S2 on, «میانگینِ ۸ زمستان»)."""
        long = layer()
        oc.text(long, 540, Y_WORD, WORD_LONG, FA_BOLD, WORD_PX, stroke=3)
        short = layer()
        oc.text(short, 540, Y_WORD, WORD_SHORT, FA_BOLD, WORD_PX, stroke=3)
        return Image.alpha_composite(f8.fade(long, 1.0 - e), f8.fade(short, e))

    # ── the frame ──

    def draw_frame(self, t: float) -> Image.Image:
        t = min(max(t, 0.0), DURATION)
        s = 1.0 + oc.ZOOM * t / DURATION                       # the push-in, as onebit_compare
        e = smoothstep((t - S2[0]) / (S2[1] - S2[0]))
        g = self.G[0] * self.glow_gain(t) * (1.0 - e)
        base = self.base * (1.0 - e) + np.asarray(DARK, np.float32) * e
        full = np.clip(oc.paint(base, g) + 0.5, 0, 255).astype(np.uint8)
        im = Image.fromarray(full, "RGB").transform(
            (W, H), Image.AFFINE, (1 / s, 0, 540 - 540 / s, 0, 1 / s, CY - CY / s), resample=Image.BILINEAR)
        im = im.convert("RGBA")
        if e < 1.0:
            im.alpha_composite(self.markers(1.0 - e, s))
        if e > 0.0:
            im.alpha_composite(self.closeups(t, e))
            im.alpha_composite(f8.fade(self.static_s2, e))
        if t >= BAR_T0:
            sf = e * (1.0 - smoothstep((t - STRIP_FADE[0]) / (STRIP_FADE[1] - STRIP_FADE[0])))
            if sf > 0.0:
                im.alpha_composite(f8.fade(self.strip_layer(t), sf))
        ca = e if t < T_HOLD else 1.0 - smoothstep((t - T_HOLD) / T_HOLD_FADE)
        if ca > 0.0 and (t >= S2[0] or e > 0.0):
            im.alpha_composite(f8.fade(self.counter_layer(t), ca))
        if t >= T_HOLD:
            im.alpha_composite(f8.fade(self.headline_layer(), smoothstep((t - T_HOLD) / T_HOLD_FADE)))
        for i, t0 in enumerate(CHIP_T):
            if t >= t0:
                im.alpha_composite(f8.fade(self.chip_layer(i), smoothstep((t - t0) / CHIP_FADE)))
        if t >= STRIP_FADE[1]:
            im.alpha_composite(f8.fade(self.hedge_layer(), smoothstep((t - STRIP_FADE[1]) / CHIP_FADE)))
        im.alpha_composite(self.static)
        im.alpha_composite(self.word_layer(e))
        return im.convert("RGB")

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]) -> Image.Image:
        assert s == 1 and tuple(size) == (W, H), (s, size)
        return self.draw_frame(DURATION if not np.isfinite(t) else min(max(t, 0.0), DURATION))

    # ── the colour check ──

    def colour_check(self) -> bool:
        """Each close-up's land box (+-0.15 deg around the city centre) in the end frame, inverted pixel by pixel: each
        pixel's own base is subtracted, the glow increment is inverted through the composite (the nearest g of a 401-step
        grid, all three channels), divided by the land share, and inverted through the bar's transfer. The land mean is
        compared with the mean of the eight-winter field (winter8) over the same land cells (values below 2 count as 2,
        as they are drawn). Tolerance 10 %. Also the glow-only luminance of each box, and the ratio Tehran / Istanbul."""
        frame = np.asarray(self.draw_frame(DURATION), np.float64)
        z = np.load(REGION8)
        lat_r, lon_r = z["lat"], z["lon"]
        w8 = z["winter8"].astype(np.float32)
        inside_f = z["inside"].astype(np.float32)
        grid = np.linspace(0.0, 1.0, 401)
        inc = oc.paint(np.zeros(3), grid).astype(np.float64)           # (401, 3): the glow increment of each g
        ok_all = True
        glow_lum, rendered_mean = {}, {}
        for c in oc.CITY:
            lon, lat, hl, hb = oc.tile_lonlat(c)
            hx = int(round(oc.BOX_DEG / (2 * hl / SQ)))
            hy = int(round(oc.BOX_DEG / (2 * hb / SQ)))
            cy, cx = SQ // 2, SQ // 2
            sl = (slice(SQ_Y + cy - hy, SQ_Y + cy + hy), slice(SQ_X[c] + cx - hx, SQ_X[c] + cx + hx))
            sub = (slice(cy - hy, cy + hy), slice(cx - hx, cx + hx))
            tl = self.tile[c]
            landm = tl["land"][sub]
            cov = np.maximum(tl["cov"][sub], 1e-6).astype(np.float64)
            base = tl["base"][sub].astype(np.float64)
            p = frame[sl]
            dv = (p - base).reshape(-1, 3)                              # each pixel's own glow increment
            d2 = ((dv[:, None, :] - inc[None]) ** 2).sum(-1)
            g_hat = np.clip(grid[d2.argmin(1)].reshape(landm.shape) / cov, 0, 1)
            v_hat = invert(g_hat)
            rendered = float(v_hat[landm].mean())
            lo, la = lon[sub].reshape(-1), lat[sub].reshape(-1)
            wf = oc.sample_field(w8, lon_r, lat_r, lo, la)
            inside = oc.sample_field(inside_f, lon_r, lat_r, lo, la) > 0.5
            sel = inside & landm.reshape(-1) & (wf > 0)
            expected = float(np.clip(wf[sel], oc.VMIN, oc.VMAX).mean())
            dev = abs(rendered - expected) / expected
            good = dev <= oc.TOL
            ok_all &= bool(good)
            rendered_mean[c] = rendered
            glow_lum[c] = float(oc.luminance(p - base)[landm].mean())
            centre = float(oc.sample_field(w8, lon_r, lat_r, np.array([oc.CITY[c][0]]), np.array([oc.CITY[c][1]]))[0])
            print(f"box {c}: rendered land mean {rendered:.2f}; winter8 {expected:.2f} on {int(sel.sum())} land cells "
                  f"(centre cell {centre:.1f}); deviation {100 * dev:.1f} % -> {'PASS' if good else 'FAIL'} "
                  f"({100 * oc.TOL:.0f} % limit)", flush=True)
        ratio = glow_lum["tehran"] / glow_lum["istanbul"]
        print(f"glow-only luminance tehran {glow_lum['tehran']:.2f}, istanbul {glow_lum['istanbul']:.2f} (levels); "
              f"ratio {ratio:.2f} (limit 1.5)", flush=True)
        if ratio <= 1.5:
            ok_all = False
        print("colour key:", "PASS" if ok_all else "FAIL", flush=True)
        return ok_all


def build() -> Film8M:
    return Film8M()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true", help="the stills at STILLS, no video")
    ap.add_argument("--check", action="store_true", help="the colour check of the close-ups (the land boxes against winter8)")
    args = ap.parse_args()
    film = build()
    print("schedule", json.dumps(film.schedule(), ensure_ascii=False, default=str), flush=True)
    if args.check:
        ok = film.colour_check()
        sys.exit(0 if ok else 1)
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / BASE
    if args.stills:
        for t in STILLS:
            p = f"{base}_t{t:04.1f}.png"
            film.draw(1, t).save(p)
            print("saved", p, flush=True)
        return
    film.draw(1, 0.0).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png", flush=True)
    import onebit
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
