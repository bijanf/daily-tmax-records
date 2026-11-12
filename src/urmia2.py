"""«دریاچه‌ی ارومیه واقعاً برگشته؟» (urmia2_fa): Lake Urmia from space, the satellite picture as the whole frame.

A sibling of hamoun3 (same engine, same look). This file is the film's data: it writes outputs/onebit/urmia2/film.json
(every string, number, the clock, the views, the colours) and the pictures the page draws; src/urmia2_page/ draws any
moment from it and src/onebit_urmia2.py steps it frame by frame.

- Pictures: data/urmia/colour_2025.npz and colour_2026.npz (Landsat 8/9 true colour, median of clear scenes between
  20 August and 10 October), joined by urmia._join. ONE tone curve for both years: clip(rgb / 0.55, 0, 1) ** (1 / 1.8)
  (the salt keeps its texture, the green water of 2026 stays visible). At 37.7 N a degree of longitude is shorter than
  a degree of latitude: each picture is resampled (Lanczos) from 733 to 580 pixels wide, so the grid is
  dlon = 0.0015 / cos(37.7 deg), dlat = 0.0015. Pixels never clear are filled from the other year, then from the ground.
- Ground: Sentinel-2 cloudless by EOX (get_urmia2.py), tone-matched once to the Landsat land (a straight line per band),
  and the Landsat picture's edge blends into it over a feather of 60 px.
- Numbers: FACTS (official), with asserts. Level now 1270.60 m, 116 cm above mid-Aban 1404 (1269.44 m, the lowest on
  record), area 1,995 km2, more than four times last year's (about 460): West Azerbaijan Regional Water Co., 20 Aban
  1405 (irib-news.ir/fa/news/5963578; mehrnews.com/news/6988836). Level of 19 Khordad 1405 (1271.13 m) and the
  ecological level (1274.10 m): Dept. of Environment, West Azerbaijan (aftabnews.ir/fa/news/1051479). No volume on
  screen: last year's official volumes disagree (240 against under 40 million m3). The quarter is by height:
  (1270.60 - 1269.44) / (1274.10 - 1269.44) = 24.9 %.
- Independent check (get_urmia2.py prints it): NASA Global Water Monitor altimetry. The north track (lake 1829) falls
  0.63 m from 10 June to 23 October 2026 (official: 0.53 m from 19 Khordad) and stands 0.40 m above autumn 2025; the
  south track (lake 115) 0.12 to 0.16 m above. Both tracks crossed dry bed in autumn 2025, so they give a lower bound
  and cannot confirm the 116 cm; the caption says so.

    python -I src/get_urmia2.py
    python -I src/urmia2.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

import get_urmia2 as g2  # noqa: E402
import urmia  # noqa: E402
from onebit import fa  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "outputs" / "onebit" / "urmia2"
FPS, W, H = 30, 1080, 1920
LON0, LAT1 = 44.9, 38.4
DLAT = 0.0015
DLON = 0.0015 / math.cos(math.radians(37.7))          # 0.0018958
GW, GH = 580, 933
FEATHER = 60
CENTRE = (45.45, 37.65)                               # the lake's centre
VIEWS = dict(hook=(540, 915, 0.96), data=(750, 945, 0.92))   # where the lake's centre sits in the frame, and the scale
PLACES = dict(urmia=(45.0761, 37.5527), tabriz=(46.2919, 38.0800))

FACTS = dict(last=1269.44, now=1270.60, june=1271.13, eco=1274.10, area_last=460, area_now=1995)
assert abs((FACTS["now"] - FACTS["last"]) - 1.16) < 0.005
assert 0.24 < (FACTS["now"] - FACTS["last"]) / (FACTS["eco"] - FACTS["last"]) < 0.26
assert abs((FACTS["june"] - FACTS["now"]) - 0.53) < 0.01
assert abs((FACTS["eco"] - FACTS["now"]) - 3.50) < 0.005
assert FACTS["area_now"] / FACTS["area_last"] > 4

# the gauge: the tube's bottom is last year's level, its top 1274.30 m, 570 px tall
GAUGE = dict(card=[96, 600, 390, 690], tube_bottom=FACTS["last"], tube_top=1274.30, tube_px=570)
GAUGE["per_m"] = GAUGE["tube_px"] / (GAUGE["tube_top"] - GAUGE["tube_bottom"])
assert abs(GAUGE["per_m"] - 117.3) < 0.1, GAUGE["per_m"]
_solid = (FACTS["now"] - FACTS["last"]) * GAUGE["per_m"]                 # px of water above the base at "now"
_line = (FACTS["eco"] - FACTS["last"]) * GAUGE["per_m"]                  # px from the base to the dashed line
assert abs(_solid / _line - (1270.60 - 1269.44) / (1274.10 - 1269.44)) < 1e-9 and abs(_solid / _line - 0.249) < 0.001, _solid / _line

T = dict(
    wipe1=(0.35, 1.90), up=3.6, shift1=(3.6, 4.3), rise=(4.8, 6.4),
    area=9.6, fade=(9.6, 10.0), wipe2=(10.6, 12.6),
    summer=15.4, june_in=(15.8, 16.6), june_out=(17.2, 19.2),
    gap=21.2, eco=(21.6, 22.2), parts=(22.4, 23.4),
    close=27.0, shift2=(27.0, 27.7), follow=28.0, wipe3=(31.9, 32.6), end=32.8,
)

WORDS = dict(
    hook="دریاچه‌ی ارومیه // {واقعاً برگشته}؟",
    year25="تابستانِ ۱۴۰۴", year26="تابستانِ ۱۴۰۵",
    up="در یک سال: // {۱۱۶ سانتی‌متر} بالاتر", up_small="آمارِ رسمی، آبان تا آبان",
    area="وسعتِ آب: // {بیش از ۴ برابرِ} پارسال", area_small="حدودِ ۴۶۰ ← ۱٬۹۹۵ کیلومترمربع",
    summer="ولی همین تابستان // {حدودِ نیم متر} پایین رفت", summer_small="خرداد تا آبانِ ۱۴۰۵",
    gap="تا ترازِ اکولوژیک // فقط {یک‌چهارمِ راه} آمده", gap_small="هنوز ۳٫۵ متر مانده",
    close="امسال دریاچه را // از نزدیک {دیده‌اید}؟", follow=["هر هفته: آبِ ایران از فضا", "دنبال کنید"],
    gauge_title="ترازِ آب",
    g_last="آبانِ ۱۴۰۴", g_now="حالا", g_june="خرداد", g_eco=["ترازِ", "اکولوژیک"],
    urmia="ارومیه", tabriz="تبریز",
    src_pic="تصویر: لندست ۸ و ۹ (USGS)، ۲۹ مرداد تا ۱۸ مهرِ هر سال",
    src_level="تراز و وسعت: شرکتِ آبِ منطقه‌ای آذربایجانِ غربی، ۲۰ آبانِ ۱۴۰۵",
    src_june="ترازِ خرداد: محیطِ زیستِ آذربایجانِ غربی؛ ارتفاع‌سنجی: ناسا",
)
assert "۱۱۶" in WORDS["up"] and fa(116) in WORDS["up"] and fa(1995) .replace("٬", "") in WORDS["area_small"].replace("٬", "")


def match(src: np.ndarray, ref: np.ndarray, mask: np.ndarray) -> list:
    """Per band the straight line (256 entries) giving the ground the mean and spread of the Landsat land."""
    luts = []
    x = np.arange(256, dtype=np.float32)
    for b in range(3):
        s, r = src[..., b][mask], ref[..., b][mask]
        gain = float(np.clip(r.std() / max(s.std(), 1e-6), 0.6, 1.6))
        luts.append(np.clip(r.mean() + gain * (x - s.mean()), 0, 255).astype(np.uint8))
        print(f"  band {b}: ground {s.mean():.0f} +- {s.std():.0f}, pictures {r.mean():.0f} +- {r.std():.0f}, gain {gain:.2f}")
    return luts


def tone(rgb: np.ndarray) -> np.ndarray:
    """The one fixed tone curve of both years."""
    return np.clip(rgb / 0.55, 0, 1) ** (1 / 1.8)


def resize(a: np.ndarray, size=(GW, GH)) -> np.ndarray:
    return np.stack([np.asarray(Image.fromarray(a[c].astype(np.float32), "F").resize(size, Image.LANCZOS)) for c in range(a.shape[0])])


def pictures() -> dict:
    BUILD.mkdir(parents=True, exist_ok=True)
    raw = {}
    for y in (2025, 2026):
        z = np.load(g2.ROOT / "data" / "urmia" / f"colour_{y}.npz")
        raw[y] = urmia._join(z["strict"], z["loose"])
        assert raw[y].shape == (3, 933, 733)
    img, valid = {}, {}
    for y, o in ((2025, 2026), (2026, 2025)):
        r = raw[y].copy()
        hole = np.isnan(r[0])
        ok = hole & ~np.isnan(raw[o][0])
        r[:, ok] = raw[o][:, ok]
        left = np.isnan(r[0])
        v = np.where(left, 0.0, 1.0).astype(np.float32)
        t = tone(np.where(np.isnan(r), 0.3, r))
        img[y] = np.clip(resize(t), 0, 1)
        valid[y] = np.clip(resize(v[None])[0], 0, 1)
        print(f"{y}: {hole.mean() * 100:.2f} % never clear, {left.mean() * 100:.2f} % left for the ground")
    # the ground on the picture grid
    gimg = Image.open(g2.OUT / "ground.jpg").convert("RGB")
    w, s, e, n = g2.BOX
    gw, gh = gimg.size
    px = lambda lon: (lon - w) / (e - w) * gw
    py = lambda lat: (n - lat) / (n - s) * gh
    box = (px(LON0), py(LAT1), px(LON0 + GW * DLON), py(LAT1 - GH * DLAT))
    sub = np.asarray(gimg.resize((GW, GH), Image.LANCZOS, box=box)).astype(np.float32)
    ref = np.mean([img[2025], img[2026]], axis=0).transpose(1, 2, 0) * 255
    ring = np.zeros((GH, GW), bool)
    ring[:80], ring[-80:], ring[:, :80], ring[:, -80:] = True, True, True, True
    ring &= (valid[2025] > 0.99) & (valid[2026] > 0.99)
    luts = match(sub, ref, ring)
    gm = np.stack([luts[c][np.asarray(gimg)[..., c]] for c in range(3)], axis=-1)
    Image.fromarray(gm).save(BUILD / "ground.jpg", quality=92)
    subm = np.stack([luts[c][sub[..., c].astype(np.uint8)] for c in range(3)], axis=-1).astype(np.float32)
    print(f"ground tones matched on {ring.mean() * 100:.0f} % of the grid: mean abs difference "
          f"{np.abs(subm - ref)[ring].mean():.1f} of 255")
    for y in (2025, 2026):
        a = valid[y][..., None]
        out = a * img[y].transpose(1, 2, 0) * 255 + (1 - a) * subm
        Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(BUILD / f"p{y}.jpg", quality=93)
        sal = (img[y] > 0.98).all(axis=0).mean()
        print(f"picture {y}: {sal * 100:.2f} % of pixels near white")
    d = np.minimum.reduce([np.arange(GW)[None, :] + 0 * np.arange(GH)[:, None], (GW - 1 - np.arange(GW))[None, :] + 0 * np.arange(GH)[:, None],
                           np.arange(GH)[:, None] + 0 * np.arange(GW)[None, :], (GH - 1 - np.arange(GH))[:, None] + 0 * np.arange(GW)[None, :]])
    p = np.clip(d / FEATHER, 0, 1)
    alpha = 1 - p * p * (3 - 2 * p)
    rgba = np.dstack([np.clip(subm, 0, 255).astype(np.uint8), (255 * alpha).astype(np.uint8)])
    Image.fromarray(rgba, "RGBA").save(BUILD / "ring.png")
    return dict(ground=dict(file="ground.jpg", w=w, s=s, e=e, n=n, px=[gw, gh]), ring="ring.png")


def main() -> None:
    pic = pictures()
    film = dict(
        fps=FPS, end=T["end"], cover_t=1.12, size=[W, H],
        grid=dict(lon0=LON0, lat1=LAT1, dlon=DLON, dlat=DLAT, w=GW, h=GH),
        views=dict(centre=list(CENTRE), hook=list(VIEWS["hook"]), data=list(VIEWS["data"])),
        clock=T, facts=FACTS, words=WORDS, places=PLACES, pics=dict(y2025="p2025.jpg", y2026="p2026.jpg"),
        ground=pic["ground"], ring=pic["ring"],
        gauge=GAUGE,
        colours=dict(wet="#1c5cab", gold="#F6C445", ink="#1d140c", paper="#FBF7F0", eco="#a03129"),
    )
    (BUILD / "film.json").write_text(json.dumps(film, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", BUILD / "film.json")


if __name__ == "__main__":
    main()
