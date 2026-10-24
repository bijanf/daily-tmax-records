"""IRAN'S SNOW: 29 % less of it, in winters about 2 °C warmer.

Three facts, each from its own source, shown side by side and not as one chain (no study
attributes Iran's snow loss to people; part of it is the drought's lack of precipitation):
- Iran's snowfall, ERA5 (snow.py, land inside Iran's borders, water years October to
  September): 58 mm a year in 1951-1980, 41 mm in 2017-2026, 29 % less. In ERA5 about three
  quarters of it is a smaller snow share of the precipitation (19.9 -> 15.3 %), the rest less
  precipitation (-6 %; CRU TS: -13 %). The 1940s are left out: ERA5 is too dry then.
- Iran's winters (November-March) warmed between 1951-1980 and 2016-2025: +1.6 °C at the
  stations of CRU TS 4.10, +2.4 °C in ERA5 (snow.cru_winter, snow.series).
- Human-caused warming made Iran's five-year drought (to mid-2025, 60-month SPEI) about 50
  times more likely: probability ratio 53.7, 95 % range 9.7 to 815, "due to the planet warming
  by 1.3 °C"; water use and management lie outside the statistics. World Weather Attribution,
  21 November 2025, a rapid study from observations only:
  https://www.worldweatherattribution.org/human-induced-climate-change-compounded-by-socio-economic-water-stressors-increased-severity-of-5-year-drought-in-iran-and-euphrates-and-tigris-basin/

A slow, still 1-bit slide. One window that never moves; its top holds the scene's bold line.
Below it Iran alone (Mercator; its mountains above 2,000 m in a dense dot screen, the rest of
the country sparse) and a row of ten big snowflakes for the snow of 1951-1980. Then, one every
two beats, three flakes fade to dots: today's snow. Nothing else moves.

Four scenes, 10 bars of 60 BPM = 40 s, with onebit_atari's slow Atari tune: a plip and a falling
note for each flake that fades. Persian (--lang fa) mirrors the type and the row.

    outputs/onebit/social/iran_snow_<theme>[_fa]_reel.mp4, _cover.png, _music.wav

    python -I src/onebit_iran_snow.py --lang fa       # Schnee.1bit, Persian
    python -I src/onebit_iran_snow.py --stills
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from scipy import ndimage  # noqa: E402

import onebit  # noqa: E402
import snow  # noqa: E402
from onebit import (FA_BOLD, FULL, GROTESK, MONO, OUT, PIXEL, SIZES, SOCIAL_CRF, Canvas, Scene,  # noqa: E402
                    Timeline, fa, title, words_of)
from onebit_snow import FLAKE, highland_map, mercator_y  # noqa: E402

PACE = dict(bpm=60, bars=(2, 3, 2, 3), lead=2, per=2)   # beats before the fade, beats per flake
THEN, NOW, WARM = (1951, 1980), (2017, 2026), (2016, 2025)   # CRU TS 4.10 ends in 2025
DROUGHT = 50                                     # WWA 2025: probability ratio 53.7 (9.7-815)
EXTENT = (43.5, 63.8, 24.8, 40.2)                # W, E, S, N: Iran
WIN = (60, 196, 900, 1356)
BAR = 40
LEFT, RIGHT = 96, 924
RULE = 556
MAP_W = 760
MAP_H = round(MAP_W * (mercator_y(EXTENT[3]) - mercator_y(EXTENT[2])) / np.deg2rad(EXTENT[1] - EXTENT[0]))
MAP = ((LEFT + RIGHT - MAP_W) // 2, 584, MAP_W, MAP_H)
ROW, PITCH, CELL = 1350, 82, 7                   # the flakes: centre line, pitch, sprite pixel
MOUNTAIN = 2000.0                                # m: Iran's mountains on the map
FOOTER = 1592
SOURCE = "Data: ERA5 · CRU TS 4.10 · World Weather Attribution 2025"


def words(lang: str, lost: int, loss: float, cru: float, era: float) -> dict:
    warm = (cru + era) / 2
    if lang == "fa":
        return dict(scenes=(("برفِ ایران {کجا رفت؟}", f"برف در ایران، {fa(1951)} تا {fa(2026)} (ERA5)"),
                            (f"از هر ۱۰ دانهٔ برف، // {{{fa(lost)} دانه کم شده است}}", f"{fa(f'{100 * loss:.0f}%')} برفِ کمتر نسبت به {fa(THEN[0])} تا {fa(THEN[1])}"),
                            (f"زمستان‌های ایران حالا // {{حدود {fa(f'{warm:.0f}')} درجه}} گرم‌تر است", f"نوامبر تا مارس؛ ایستگاه‌ها {fa(f'{cru:.1f}')} و ERA5 {fa(f'{era:.1f}')} درجه"),
                            (f"خشکسالیِ ۵ سالهٔ ایران: // احتمالش {{حدود {fa(DROUGHT)} برابر}} شد", "به‌دلیلِ گرمایشِ انسان‌ساز (WWA، نوامبر ۲۰۲۵)")),
                    follow="برای داده‌های اقلیمی بیشتر، فالو کنید")
    return dict(scenes=(("Where did {Iran's snow} go?", "snow in Iran, 1951–2026 (ERA5)"),
                        (f"Of every 10 snowflakes, // {{{lost} are gone}}", f"{100 * loss:.0f} % less snow than in {THEN[0]}–{str(THEN[1])[2:]}"),
                        (f"Iran's winters are // {{about {warm:.0f} °C}} warmer", f"Nov–Mar: stations +{cru:.1f} °C, ERA5 +{era:.1f} °C"),
                        (f"Iran's 5-year drought: // about {{{DROUGHT}×}} more likely", "due to human-caused warming (WWA, Nov 2025)")),
                follow="Follow for more climate data in 1-bit")


class IranSnowFilm:
    """Draws the film; exposes L, S, bpm, appear(), melody() and blips for onebit_atari."""

    def __init__(self, th: onebit.Theme, lang: str = "en"):
        self.th, self.lang, self.fa = th, lang, lang == "fa"
        s = snow.series(0.0, "Iran")
        then, now = s.loc[THEN[0]:THEN[1], "snow"], s.loc[NOW[0]:NOW[1], "snow"]
        assert len(then) == 30 and len(now) == 10, "complete water years only"
        self.loss = 1 - now.mean() / then.mean()               # 0.29
        self.lost = round(10 * self.loss)                      # of every 10 flakes: 3
        era = float(s.loc[WARM[0]:WARM[1], "cold_t2m"].mean() - s.loc[THEN[0]:THEN[1], "cold_t2m"].mean())   # 2.4 °C
        cru = snow.cru_winter("Iran", *THEN, *WARM)            # 1.6 °C
        assert round((cru + era) / 2) == 2, (cru, era)
        self.words = words(lang, self.lost, self.loss, cru, era)
        self.bpm = PACE["bpm"]
        self.beat = 60 / self.bpm
        scenes = tuple(Scene(b, FULL, t, line) for b, (t, line) in zip(PACE["bars"], self.words["scenes"]))
        starts = np.cumsum([0.0] + [sc.bars * 4 * self.beat for sc in scenes])
        self.starts = starts
        self.L = Timeline(0, 0, 0, 0, 0, end=float(starts[-1]), camera=((0.0, FULL),),
                          scenes=tuple(float(t) for t in starts[:-1]))
        self.S = SimpleNamespace(scenes=scenes, os_name="IRAN.SNOW", lang=lang, race=[])
        self.blips = [float(starts[1]) + (PACE["lead"] + k * PACE["per"]) * self.beat for k in range(self.lost)]
        self.done = self.blips[-1] - float(starts[1]) + 0.5   # s into the fade: the number and today's years
        assert self.blips[-1] < starts[2] - 2 * self.beat, "the fade must finish with time to read"
        # Iran alone: its mountains in a dense dot screen, the rest of it sparse, its border dotted
        x, y, w, h = MAP
        land, borders, _, _, z, inside = highland_map(w, h, EXTENT, "Iran")
        yy, xx = np.mgrid[0:h, 0:w]
        dense = (yy % 4 < 2) & ((xx + 2 * (yy // 4 % 2)) % 4 < 2)
        sparse = (yy % 8 < 2) & (xx % 8 < 2)
        edge = inside & ~ndimage.binary_erosion(inside, iterations=2)
        self.stipple = np.where(z >= MOUNTAIN, dense, sparse) & inside & ~edge
        self.border = edge & ((xx + yy) % 2 == 0)
        dots = np.zeros((1920, 1080), bool)
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        dots[FOOTER - 32:FOOTER + 16] = False
        self.dots = dots

    # ── time ──

    def scene(self, t: float) -> int:
        return int(np.searchsorted(self.starts[:-1], t, side="right")) - 1 if np.isfinite(t) else 0

    def faded(self, t: float) -> int:
        i = self.scene(t)
        return 0 if i < 1 else self.lost if i > 1 else int(np.searchsorted(self.blips, t, side="right"))

    def appear(self, i: int) -> list:
        """Slow: a line comes in over 1.6 s; a line with a break shows its second part later: in
        the fade once the last flake has gone, in the drought scene two beats on."""
        ws = [w for w, _ in words_of(self.S.scenes[i].title, self.th)]
        n = len(ws) - ws.count("//")
        if "//" not in ws:
            return [0.3 + 1.6 * k / n for k in range(n)]
        first = ws.index("//")
        later = self.done if i == 1 else 2 * self.beat + 0.3
        return [0.3 + 1.2 * k / first for k in range(first)] + [later + 0.3 * k for k in range(n - first)]

    def melody(self):
        """A tune note each time a flake fades, falling to the tonic."""
        return [(t, self.lost - 1 - k, 1.6, 0.35) for k, t in enumerate(self.blips)]

    # ── drawing ──

    def window(self, c: Canvas, i: int):
        th = self.th
        x, y, w, h = WIN
        c.frame(x, y, x + w, y + h, fill=th.paper)
        c.fill(x, y, x + w, y + BAR, th.ink)
        c.frame(x + 3, y + BAR + 3, x + w - 3, y + h - 3)
        last = i == len(self.S.scenes) - 1
        if last and self.fa:
            c.text(x + w - 12, y + BAR - 10, self.words["follow"], onebit.FA_TEXT, 28, th.title, "rs", "rtl")
        else:
            c.text(x + 12, y + BAR - 9, self.words["follow"] if last else "Iran.Snow", PIXEL, 32, th.title)
            if not last:
                c.text(x + w - 12, y + BAR - 9, f"[{i + 1:02d}/{len(self.S.scenes):02d}]", PIXEL, 32, th.title, "rs")
        c.fill(x + 3, RULE, x + w - 3, RULE + 2, th.ink)

    def flakes(self, c: Canvas, t: float):
        """Ten flakes; the last ones in reading order fade to a dotted ghost."""
        gone = self.faded(t)
        h, w = len(FLAKE), len(FLAKE[0])
        for k in range(10):
            j = 9 - k if self.fa else k                       # Persian reads the row from the right
            cx = (LEFT + RIGHT) / 2 + (j - 4.5) * PITCH
            x0, y0 = cx - w * CELL / 2, ROW - h * CELL / 2
            ghost = k >= 10 - gone
            for r, row in enumerate(FLAKE):
                for q, ch in enumerate(row):
                    if ch == "#" and (not ghost or (r + q) % 2 == 0):
                        a, b = x0 + q * CELL, y0 + r * CELL
                        if ghost:                             # a faded flake: one dot per pixel, its middle
                            c.fill(a + 2, b + 2, a + CELL - 2, b + CELL - 2, self.th.ink)
                        else:
                            c.fill(a, b, a + CELL, b + CELL, self.th.ink)

    def era(self, c: Canvas, t: float):
        i = self.scene(t)
        y0, y1 = THEN if i < 1 or (i == 1 and t - self.starts[1] <= self.done) else NOW
        if self.fa:
            c.text((LEFT + RIGHT) / 2, ROW + 108, f"{fa(y0)} تا {fa(y1)}", FA_BOLD, 50, self.th.ink, "ms", "rtl")
        else:
            c.text((LEFT + RIGHT) / 2, ROW + 108, f"{y0}–{y1}", GROTESK, 50, self.th.ink, "ms")

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]):
        c = Canvas(s, self.th, 1.0, (0.0, 0.0), size)
        c.pixels(0, 0, self.dots, self.th.dots)
        i = self.scene(t)
        dt = t - self.starts[i] if np.isfinite(t) else np.inf
        self.window(c, i)
        at = self.appear(i)
        title(c, self.th, self.S.scenes[i], dt, self.lang, 1.0, LEFT, RIGHT, WIN[1] + BAR + 96, at,
              motion=False, line_at=at[-1] + 0.6)
        x, y, _, _ = MAP
        c.pixels(x, y, self.stipple, self.th.ink)
        c.pixels(x, y, self.border, self.th.ink)
        self.flakes(c, t)
        self.era(c, t)
        c.text(onebit.LEFT, FOOTER, SOURCE, MONO, 20, self.th.head)
        return c.im


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="schnee1", choices=list(onebit.THEMES), help="colour theme")
    ap.add_argument("--lang", default="en", choices=("en", "fa"))
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    args = ap.parse_args()
    film = IranSnowFilm(onebit.THEMES[args.theme], args.lang)
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / (f"iran_snow_{args.theme}" + ("" if args.lang == "en" else f"_{args.lang}"))
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (st[1] + 3.0, st[1] + film.done + 2, st[2] + 4.0, st[3] + 1.0, st[4] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
        print("saved", f"{base}_t*.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="atari")


if __name__ == "__main__":
    main()
