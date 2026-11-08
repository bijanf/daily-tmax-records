"""ALBORZ SNOW AFTER THE ABAN STORM: «طوفانِ آبان برفِ البرز را چقدر کرد؟» The central Alborz above Tehran (Taleqan to
Damavand, with Tehran's five dams) in true colour before and after the storm of 14-17 Aban 1405 (Sentinel-2), and the
snow-covered area above 2,000 m in 18-25 Aban of every year since 1379 against its mean (MODIS Terra), in the slide
frame (onebit_slides), no narration, a light score.

Data: src/get_alborzsnow.py (Sentinel-2 passes and the cloud-free 'before' composite: data/alborzsnow/tex_before.jpg;
the 'after' picture data/alborzsnow/tex_after.jpg once the first clear pass after the storm is in) and
src/get_alborzsnow_modis.py (data/alborzsnow/modis.csv, the 8-day period from day 313: 9-16 November, 18-25 Aban).
A year is measured when under 10 % of the high ground stayed unseen under cloud all 8 days; the mean is that of the
measured years 1379-1404. 1405 is drawn only when its MODIS period is in the table (until then the cut is a draft:
the bar is a «؟»).

Five scenes, 1 + 2 + 1.25 + 1.5 + 1.25 bars of 60 BPM = 28 s:
    0-4 s      the hook over the picture (before | after)
    4-12 s     the 26 years, 1379-1404, one by one (0.25 s each), the mean line, the cloudy years hatched
    12-17 s    last year, 1404
    17-23 s    1405 against the mean
    23-28 s    snow is the spring water of Tehran's dams; the question

    python -I src/onebit_alborzsnow.py --stills
    python -I src/onebit_alborzsnow.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402

import onebit  # noqa: E402
from onebit import FA_BOLD, FA_TEXT, OUT, SIZES, SOCIAL_CRF, Canvas, fa  # noqa: E402
from onebit_hamoun2 import dec, ease, shown  # noqa: E402
from onebit_slides import LEFT, RIGHT, Slides  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
DATA = Path(__file__).resolve().parents[1] / "data" / "alborzsnow"
THEME = "abi"
ABOVE, BELOW, CLOUDY = "#2B6289", "#9DB8C8", "#8A96A3"
PACE = dict(bpm=60, bars=(1, 2, 1.25, 1.5, 1.25))
DURATION = 28.0
T_BUILD, STEP = 4.4, 0.25                             # 1379 at 4.4 s, one year every 0.25 s
T_LAST, T_NOW, T_END = 12.0, 17.0, 23.0
DOY = 313
CLOUD_MAX = 0.10                                     # share of the high ground unseen: above it the year is not measured
FIELD = (LEFT, 720, RIGHT, 1400)
PIC = (LEFT, 640, RIGHT - LEFT)                      # x, y, width of the picture (2:1, the box's shape)
AXIS_Y, LEGEND_Y = 1442, 1500


def table() -> pd.DataFrame:
    d = pd.read_csv(DATA / "modis.csv")
    d = d[d.doy == DOY].sort_values("year").reset_index(drop=True)
    d["ok"] = d.cloud_km2 < CLOUD_MAX * d.high_km2
    return d


def words(now) -> dict:
    return dict(
        scenes=(("طوفانِ آبان // برفِ البرز را {چقدر} کرد؟", ""),
                ("برفِ ۱۸ تا ۲۵ آبان، // {۲۶ سال}", ""),
                ("پارسال: // حدودِ {یک‌چهارمِ} میانگین", ""),
                (now, ""),
                ("برف، // {آبِ بهارِ} سدهای تهران است", "شما برفِ امسال را دیده‌اید؟")),
        follow="این را برای کسی بفرستید که در تهران زندگی می‌کند",
        unit="کیلومتر مربع برف", legend=("بیشتر از میانگین", "کمتر از میانگین"), cloudy="ابری",
        mean="میانگینِ ۲۴ سال", before="قبل از طوفان", after="بعد از طوفان",
        sources=("منبع: MODIS Terra (NASA)، برفِ بالای ۲٬۰۰۰ متر، ۱۸ تا ۲۵ آبان",
                 "تصویر: Sentinel-2 (ESA Copernicus)؛ زمین: Copernicus DEM"),
    )


class AlborzSnow(Slides):
    def __init__(self, th: onebit.Theme, colour: dict):
        d = table()
        clim = d[(d.year <= 2025) & d.ok]
        assert len(d[d.year <= 2025]) == 26 and len(clim) == 24, (len(d), len(clim))
        self.mean = float(clim.snow_km2.mean())
        assert 4300 < self.mean < 4500, self.mean
        last = d[d.year == 2025].iloc[0]
        assert last.ok and 0.20 <= last.snow_km2 / self.mean <= 0.25, last.snow_km2 / self.mean   # «حدودِ یک‌چهارم»
        self.rows = [dict(year=int(r.year), solar=int(r.year) - 621, km2=float(r.snow_km2), ok=bool(r.ok))
                     for r in d.itertuples()]
        if not any(r["year"] == 2026 for r in self.rows):
            self.rows.append(dict(year=2026, solar=1405, km2=float("nan"), ok=False))   # the draft: «؟»
        assert [r["year"] for r in self.rows] == list(range(2000, 2027))
        now = self.rows[-1]
        if np.isfinite(now["km2"]):
            r = now["km2"] / self.mean
            line = (f"امسال: // {{{dec(r)} برابرِ}} میانگین" if r >= 1.15 else "امسال: // {نزدیکِ} میانگین"
                    if r >= 0.85 else f"امسال: // {{{fa(round(100 * r))}٪}} میانگین")
        else:
            line = "امسال: // {؟}"
        self.vmax = max(r["km2"] for r in self.rows if np.isfinite(r["km2"]))
        self.before = self.picture("before")
        self.after = self.picture("after") if (DATA / "tex_after.jpg").exists() else None
        self.hook_at_once = True
        self.setup(th, "fa", colour, words(line), PACE, "Alborz.Snow")
        assert abs(self.starts[-1] - DURATION) < 1e-9
        self.done = 0.6

    def picture(self, name: str) -> Image.Image:
        x, y, w = PIC
        return Image.open(DATA / f"tex_{name}.jpg").convert("RGB").resize((w, w // 2), Image.LANCZOS)

    def scaled(self, im: Image.Image, c: Canvas) -> Image.Image:
        return im if c.k == 1 else im.resize((round(im.width * c.k), round(im.height * c.k)), Image.LANCZOS)

    # ── geometry ──
    def slot(self, k: int) -> tuple:
        x0, _, x1, _ = FIELD
        s = (x1 - x0) / len(self.rows)
        xr = x1 - k * s
        return xr - s * 0.84, xr - s * 0.16

    def ybar(self, v: float) -> float:
        _, yt, _, yb = FIELD
        return yb - (yb - yt) * v / self.vmax

    # ── drawing ──
    def pictures(self, c: Canvas, t: float):
        th = self.th
        x, y, w = PIC
        h = w // 2
        im = self.before.copy()
        if self.after is not None and np.isfinite(t) and t >= T_END:
            im = self.after
        elif self.after is not None:                      # the hook and the cover: after on the left half
            half = w // 2
            im.paste(self.after.crop((0, 0, half, h)), (0, 0))
        c.im.paste(self.scaled(im, c), (c.X(x), c.Y(y)))
        c.frame(x, y, x + w, y + h)
        for s, xx, anchor in ((self.words["before"], x + w - 14, "rs"), (self.words["after"], x + 14, "ls")):
            if s == self.words["after"] and self.after is None:
                continue
            tw = c.width(s, FA_BOLD, 34, "rtl")
            x0 = xx - tw - 24 if anchor == "rs" else xx
            c.frame(x0, y + 14, x0 + tw + 24, y + 66, fill=th.field)
            c.text(x0 + tw + 12, y + 54, s, FA_BOLD, 34, th.ink, "rs", "rtl")

    def chart(self, c: Canvas, t: float):
        th = self.th
        x0, _, x1, yb = FIELD
        n = len(self.rows)
        upto = n - 2 if (np.isfinite(t) and t < T_NOW) else n - 1
        if np.isfinite(t) and t < T_LAST:
            upto = min(upto, int((t - T_BUILD) // STEP))
        for k, r in enumerate(self.rows[:upto + 1]):
            xa, xb = self.slot(k)
            grow = ease((t - (T_BUILD + k * STEP)) / 0.2) if np.isfinite(t) and t < T_LAST else 1.0
            if k == n - 1 and np.isfinite(t):
                grow = ease((t - T_NOW - 0.3) / 0.6)
            if not np.isfinite(r["km2"]):                  # 1405 not yet in: a «؟» over an empty slot
                c.text((xa + xb) / 2, yb - 30, "؟", FA_BOLD, 48, th.mark, "ms", "rtl")
                continue
            top = min(self.ybar(r["km2"] * grow), yb - 3)
            if r["ok"]:
                c.fill(xa, top, xb, yb, ABOVE if r["km2"] > self.mean else BELOW)
            else:                                          # cloudy: not measured, hatched
                for yy in np.arange(self.ybar(self.mean * 0.3), yb - 4, 10):
                    c.fill(xa, yy, xa + 2, yy + 5, CLOUDY)
                    c.fill(xb - 2, yy, xb, yy + 5, CLOUDY)
        c.fill(x0, yb, x1, yb + 2, th.ink)
        ym = self.ybar(self.mean)
        for xx in np.arange(x0, x1, 16):
            c.fill(xx, ym - 1.5, min(xx + 9, x1), ym + 1.5, th.ink)
        for k in (0, 5, 10, 15, 20, n - 1):
            xa, xb = self.slot(k)
            c.text((xa + xb) / 2, AXIS_Y, fa(self.rows[k]["solar"]), FA_TEXT, 26, th.ink, "ms", "rtl")
        focus = n - 2 if (np.isfinite(t) and T_LAST <= t < T_NOW) else n - 1 if (np.isfinite(t) and T_NOW <= t) else None
        if focus is not None and np.isfinite(self.rows[focus]["km2"]):
            r = self.rows[focus]
            xa, xb = self.slot(focus)
            top = self.ybar(r["km2"])
            c.frame(xa - 3, top - 3, xb + 3, yb, colour=th.ink)
            c.text(RIGHT, 676, f"{fa(r['solar'])}: {shown(r['km2'])} {self.words['unit']}", FA_BOLD, 44, th.ink,
                   "rs", "rtl")

    def legend(self, c: Canvas):
        th = self.th
        x = RIGHT
        for s, col in zip(self.words["legend"], (ABOVE, BELOW)):
            c.fill(x - 26, LEGEND_Y - 22, x, LEGEND_Y - 2, col)
            c.text(x - 36, LEGEND_Y, s, FA_TEXT, 26, th.ink, "rs", "rtl")
            x -= 36 + c.width(s, FA_TEXT, 26, "rtl") + 30
        for xx in range(int(x - 34), int(x), 12):
            c.fill(xx, LEGEND_Y - 13, xx + 7, LEGEND_Y - 10, th.ink)
        s = f"{self.words['mean']}: {shown(self.mean)}"
        c.text(x - 44, LEGEND_Y, s, FA_TEXT, 26, th.ink, "rs", "rtl")
        assert x - 44 - c.width(s, FA_TEXT, 26, "rtl") >= LEFT, "the legend runs out of the window"

    def body(self, c: Canvas, t: float):
        if not np.isfinite(t) or t < T_BUILD - 0.4 or t >= T_END:
            self.pictures(c, t)
            return
        self.chart(c, t)
        self.legend(c)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true")
    args = ap.parse_args()
    film = AlborzSnow(onebit.THEMES[THEME], {"land": "#D3E3EC"})
    base = OUT / "social" / "alborzsnow_fa"
    for old in (OUT / "social").glob(f"{base.name}_t*.png"):
        old.unlink()
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    if args.stills:
        for t in (0.0, 6.0, 11.0, 14.5, 20.0, 25.5):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
            print("saved", f"{base}_t{t:04.1f}.png", flush=True)
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
