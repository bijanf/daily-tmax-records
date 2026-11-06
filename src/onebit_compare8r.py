"""TEHRAN AND ISTANBUL, EIGHT WINTERS OF NO2 FROM SPACE, WITH THE REASONS: the eight-winter film (onebit_compare8) and a
final scene that names four reasons the ratio is high, not only the air inversion.

The film is onebit_compare8's, on the same clock up to 19.5 s: the frames before 19.5 s are the same pictures (the push-in
keeps the one-winter clock of 24 s, so the zoom does not change). From 19.5 s the eight-winter strip and its labels fade out
over 0.5 s; four reason chips then appear one by one, each at the onset of its word in the fifth narration line (N5):

    chip 1  وارونگیِ هوا            20.55 s   (the word وارونگی)
    chip 2  خودروهای فرسوده         23.31 s   (the word خودروهای)
    chip 3  سوختِ کم‌کیفیت          24.87 s   (the word سوختِ)
    chip 4  سوءمدیریت              26.29 s   (the word سوءمدیریت)

The headline stays. The chips sit in two rows (the first reason at the right of its row, as the Persian text reads), inside
the safe zone (nothing below y 1600; nothing below y 1000 within 150 px of the right edge).

N5 is longer than the 24 s of the one-winter clock allowed: it runs from 19.5 s to 28.75 s, so DURATION is 30.0 s (the line
ends 1.25 s before the end). The onsets come from a faster-whisper transcription of N5 (data/air/compare/narration8r/
transcripts.json), checked against the waveform envelope.

Clock (seconds; the score reads these through schedule()):
  the film's clock to 19.5 s (onebit_compare8)
  STRIP_FADE          19.5 - 20.0   the strip and its labels fade out
  CHIP_T              the four chips appear (each fades in over CHIP_FADE = 0.25 s from its onset)
  DURATION            30.0          the end (N5 ends at 28.75 s)
  STILLS              0, 10, 18, 21, 24, 27 s

    python -I src/onebit_compare8r.py              # the silent reel and the cover (frame 0)
    python -I src/onebit_compare8r.py --stills     # the stills at STILLS
    python -I src/onebit_compare8r.py --check      # the colour check of the close-ups (the one-winter check)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit_compare as oc  # noqa: E402
import onebit_compare8 as f8  # noqa: E402
from onebit import FA_BOLD, OUT, SIZES, SOCIAL_CRF, fa  # noqa: E402

W, H = oc.W, oc.H
BASE_DURATION = 24.0                              # s: the one-winter clock, kept for the push-in (frames before 19.5 s)
DURATION = 30.0                                   # s: the reel (N5 ends at 28.75 s; 1.25 s after it)
STILLS = (0.0, 10.0, 18.0, 21.0, 24.0, 27.0)
STRIP_FADE = (19.5, 20.0)                         # s: the eight-winter strip and its labels fade out
CHIP_FADE = 0.25                                  # s: each chip fades in from its onset
N5_START, N5_END = 19.5, 28.75                    # s: the fifth narration line's speech (the score's clock)
CHIP_TEXT = ("وارونگیِ هوا", "خودروهای فرسوده", "سوختِ کم‌کیفیت", "سوءمدیریت")
CHIP_T = (20.55, 23.31, 24.87, 26.29)             # s: the onsets of the words in N5 (narration8r/transcripts.json)
CHIP_PX = 40
CHIP_H = 54                                       # px: a chip's height
CHIP_ROW_Y = (1140, 1214)                         # px: the two rows' top edges
CHIP_GAP = 16                                     # px: between the two chips of a row
CHIP_PAD = 24                                     # px: the text's padding inside a chip (as the city chips)
ROW_OF = ((0, 1), (2, 3))                         # chips in each row, the first at the right (right-to-left reading)
TRANSCRIPT = oc.DATA / "narration8r" / "transcripts.json"
BASE = "compare8r_tehran_istanbul_fa"


def smoothstep(x: float) -> float:
    return f8.smoothstep(x)


def check_clock() -> None:
    """The clock of this film: N5 from the transcript, the chip onsets inside N5, the layout inside the safe zone."""
    tr = {r["name"]: r for r in json.loads(TRANSCRIPT.read_text(encoding="utf-8"))}
    n5 = tr["n5"]
    assert abs(n5["film_offset_s"] - (N5_START - 0.03)) < 1e-9 and abs(n5["window_start"] - N5_START) < 1e-9
    assert abs(N5_START + n5["speech_s"] - N5_END) < 0.01, (N5_START + n5["speech_s"], N5_END)
    assert N5_END <= DURATION - 0.6, "N5 must end at least 0.6 s before the end"
    onsets = n5["chip_onsets_film_s"]
    for txt, t in zip(CHIP_TEXT, CHIP_T):
        assert abs(onsets[txt] - t) < 1e-9, ("chip onset", txt, onsets[txt], t)
        assert N5_START < t < N5_END, t
    assert all(a < b for a, b in zip(CHIP_T, CHIP_T[1:])) and CHIP_T[0] > f8.T_HOLD + f8.T_HOLD_FADE
    assert STRIP_FADE[0] == 19.5 and STRIP_FADE[1] == 20.0 and CHIP_T[0] >= STRIP_FADE[1]
    assert f8.BAR_TIMES[-1] + f8.BAR_RISE <= 17.0 + 1e-9 and f8.T_HOLD == 17.0
    assert DURATION == 30.0 and BASE_DURATION == 24.0


def chip_layout() -> list:
    """Each chip's box (x0, y0, width) in px: two rows, centred, the first chip of a row at the right."""
    font = oc.font(FA_BOLD, CHIP_PX)
    boxes = [None] * 4
    for row, (a, b) in enumerate(ROW_OF):
        wa = font.getlength(CHIP_TEXT[a], direction="rtl", language="fa") + CHIP_PAD
        wb = font.getlength(CHIP_TEXT[b], direction="rtl", language="fa") + CHIP_PAD
        total = wa + CHIP_GAP + wb
        right = 540 + total / 2
        y0 = CHIP_ROW_Y[row]
        boxes[a] = (right - wa, y0, wa)
        boxes[b] = (right - wa - CHIP_GAP - wb, y0, wb)
    for x0, y0, bw in boxes:
        assert x0 >= 150 and x0 + bw <= 930, ("a chip leaves the safe width", x0, bw)
        assert y0 + CHIP_H < 1600 and (x0 + bw < 930 or y0 + CHIP_H < 1000), "a chip leaves the safe zone"
    bottom = CHIP_ROW_Y[1] + CHIP_H
    assert bottom < f8.Y_HEAD[0] - 0.9 * f8.HEAD_PX - 12, ("the chips touch the headline", bottom)
    return boxes


BOXES = None


class Film8R(f8.Film8):
    """The eight-winter film, to 19.5 s unchanged; then the strip fades and the four reason chips appear."""

    def __init__(self):
        super().__init__()
        self.L = type("L", (), {"end": DURATION})()     # the length onebit.video reads

    def checks(self) -> None:
        oc.Film.checks(self)                            # the one-winter checks (the colour scale, the halo)
        f8.Film8.checks(self)                           # the eight-winter checks (the strip, the layout, the headline)
        check_clock()
        assert f8.HEAD_PX >= 48 and f8.Y_HEAD[0] > f8.Y_STRIP

    def schedule(self) -> dict:
        s = super().schedule()
        s.update(end=DURATION, base_end=BASE_DURATION, strip_fade=STRIP_FADE, chips=dict(zip(CHIP_TEXT, CHIP_T)),
                 chip_fade=CHIP_FADE, n5=(N5_START, N5_END), stills=STILLS)
        return s

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]) -> Image.Image:
        assert s == 1 and tuple(size) == (W, H), (s, size)
        return self.draw_frame(DURATION if not np.isfinite(t) else min(max(t, 0.0), DURATION))

    def draw_frame(self, t: float) -> Image.Image:
        """The one-winter and eight-winter frame of onebit_compare8, with the zoom on the one-winter clock and the final scene."""
        t = min(max(t, 0.0), DURATION)
        s = 1.0 + oc.ZOOM * t / BASE_DURATION           # the push-in, as the one-winter film (unchanged before 19.5 s)
        w = self.weights(t)
        g = sum(wk * Gk for wk, Gk in zip(w, self.G))
        full = np.clip(oc.paint(self.base, g) + 0.5, 0, 255).astype(np.uint8)
        im = Image.fromarray(full, "RGB").transform(
            (W, H), Image.AFFINE, (1 / s, 0, 540 - 540 / s, 0, 1 / s, oc.CY - oc.CY / s), resample=Image.BILINEAR)
        im = im.convert("RGBA")
        for c in oc.CITY:
            gt = sum(wk * Gk for wk, Gk in zip(w, self.tg[c]))
            im.paste(oc.to_rgb(oc.paint(self.tile[c]["base"], gt)), (f8.SQ_X[c], f8.SQ_Y))
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        for c in oc.CITY:
            x, y = self.xy(*oc.CITY[c], s=s)
            d.line([(x, y), (f8.SQ_X[c] + f8.SQ / 2, f8.SQ_Y - 2)], fill=oc.PAPER[:3] + (170,), width=2)
        for c in oc.CITY:
            x, y = self.xy(*oc.CITY[c], s=s)
            d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=oc.PAPER, outline=oc.SHADOW, width=2)
            fnt = oc.font(FA_BOLD, 34)
            tw = fnt.getlength(f8.NAME[c], direction="rtl", language="fa")
            lx, ly = x + 16, y - 52
            d.rounded_rectangle([lx, ly, lx + tw + 22, ly + 46], radius=10, fill=(8, 10, 14, 215))
            oc.text(ov, lx + tw / 2 + 11, ly + 36, f8.NAME[c], FA_BOLD, 34, stroke=2)
        lab = f"زمستانِ {fa(f8.CLOSE_YEAR)}"
        tw = oc.font(FA_BOLD, 34).getlength(lab, direction="rtl", language="fa")
        d.rounded_rectangle([540 - tw / 2 - 12, f8.SQ_Y - 50, 540 + tw / 2 + 12, f8.SQ_Y - 8], radius=10,
                            fill=(8, 10, 14, 215))
        oc.text(ov, 540, f8.SQ_Y - 16, lab, FA_BOLD, 34, stroke=2)
        im.alpha_composite(ov)
        im.alpha_composite(self.static)
        self.counter(im, t)
        self.strip_part(im, t)
        self.headline(im, t)
        self.chips(im, t)
        return im.convert("RGB")

    def strip_part(self, im: Image.Image, t: float) -> None:
        """The strip and its labels as onebit_compare8 draws them, faded out from 19.5 s over 0.5 s."""
        if t < STRIP_FADE[0]:
            self.strip(im, t)
            return
        a = 1.0 - smoothstep((t - STRIP_FADE[0]) / (STRIP_FADE[1] - STRIP_FADE[0]))
        if a <= 0.0:
            return
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.strip(lay, t)
        im.alpha_composite(f8.fade(lay, a))

    def chips(self, im: Image.Image, t: float) -> None:
        """The four reason chips, each from its onset: the city chips' style (dark box, paper text, rounded)."""
        global BOXES
        if BOXES is None:
            BOXES = chip_layout()
        for txt, t0, (x0, y0, bw) in zip(CHIP_TEXT, CHIP_T, BOXES):
            if t < t0:
                continue
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            d.rounded_rectangle([x0, y0, x0 + bw, y0 + CHIP_H], radius=12, fill=(8, 10, 14, 215))
            oc.text(lay, x0 + bw / 2, y0 + CHIP_H - 14, txt, FA_BOLD, CHIP_PX, stroke=3)
            im.alpha_composite(f8.fade(lay, smoothstep((t - t0) / CHIP_FADE)))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true", help="the stills at STILLS, no video")
    ap.add_argument("--check", action="store_true", help="the colour check of the close-ups, as onebit_compare")
    args = ap.parse_args()
    f8.retune()
    film = Film8R()
    print("schedule", film.schedule(), flush=True)
    print("chip boxes", BOXES if BOXES is not None else chip_layout(), flush=True)
    if args.check:
        film.colour_check()
        return
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
