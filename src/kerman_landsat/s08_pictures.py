"""Step 6: the then/now true-colour pictures (JPG) of the same frames.

Source: the per-pixel median surface reflectance (red, green, blue) of each year's late-summer passes
(s04_year.py --rgb; 1987: Landsat 5 TM, 4 passes path 161 + 3 passes path 160; 2025: Landsat 8/9 OLI,
4 + 4 passes), path 161 west and path 160 east, blended linearly over 3 km at the zone border (view.rgb).

Tone matching (documented per-image adjustment): TM and OLI surface reflectance of the same desert differ a
little, so the 'then' bands are mapped linearly onto the 'now' bands so that their desert reflectance
quantiles (5th, 10th, ..., 95th percentile of pixels with NDVI < 0.10 in both years, below 2,000 m) agree
(least-squares line through the quantile pairs, one per band). Then both pictures get the SAME stretch:
a stretch of brightness only, so the hue stays natural: L = mean(R, G, B), L' = ((L - lo)/(hi - lo))^(1/1.2)
with lo/hi = the 0.5th/99.8th percentile of L in the 'now' frame, each band multiplied by L'/L, then a
saturation boost of 1.3 (distance from grey x 1.3); identical numbers for both years. The unmatched pair (same stretch, no matching) is written too, for transparency.

Pixels that no pass saw clear take the nearest seen pixel's colour (display only; 2025 full box: 409 px).
    python -I s08_pictures.py               # frames as set below
Writes pictures/<frame>_<year>[_raw].jpg and pictures/tone_match.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HERE  # noqa: E402
from geom import masks  # noqa: E402
from view import ndvi, rgb, crop_ll  # noqa: E402

THEN, NOW = 1987, 2025
OUT = HERE / "pictures"
OUT.mkdir(exist_ok=True)
FRAMES = {  # name: ((W, S, E, N), output width px, output height px or None = keep aspect)
    "portrait_9x16": ((55.600, 30.185, 56.150, 31.030), 1080, 1920),      # Nough-Koshkuiyeh-Rafsanjan
    "portrait_9x16_zoom": ((55.720, 30.300, 56.100, 30.885), 1080, 1920),  # Rafsanjan's belt, ~34 m/px
    "fullbox": ((55.12, 30.175, 56.43, 31.005), 1080, None),               # the box, inset ~2 km: no
                                                                           # empty wedges from UTM rotation
}
QS = np.arange(5, 96, 5)


def match(then, now, sel):
    """Per band a, b with now ~ a + b * then, fitted through desert quantile pairs."""
    coef = []
    for k in range(3):
        qt = np.percentile(then[k][sel], QS)
        qn = np.percentile(now[k][sel], QS)
        b, a = np.polyfit(qt, qn, 1)
        coef.append((float(a), float(b)))
    return coef


def render(arr, lo, hi, gamma=1.2, sat=1.3):
    arr = np.nan_to_num(arr, nan=0)
    L = arr.mean(axis=0)
    Ls = np.clip((L - lo) / (hi - lo), 0, 1) ** (1 / gamma)
    x = arr * (Ls / np.maximum(L, 1e-4))[None]
    lum = x.mean(axis=0, keepdims=True)
    x = np.clip(lum + (x - lum) * sat, 0, 1)
    return (x.transpose(1, 2, 0) * 255 + 0.5).astype(np.uint8)


def fill_nearest(arr):
    """Pixels no pass saw clear (2025: 409 px of a bright pond west of the plain, flagged in every pass)
    take the colour of the nearest seen pixel, for display only."""
    from scipy import ndimage
    bad = np.isnan(arr[0])
    if not bad.any():
        return arr
    idx = ndimage.distance_transform_edt(bad, return_distances=False, return_indices=True)
    return arr[:, idx[0], idx[1]]


def resize(img, w, h, bb):
    im = Image.fromarray(img)
    if h is None:
        h = int(round(img.shape[0] * w / img.shape[1]))
    return im.resize((w, h), Image.LANCZOS)


def main():
    m = masks()
    dem = np.load(HERE / "cache" / "dem.npz")["elev"]
    nd_t, nd_n = ndvi(THEN), ndvi(NOW)
    im_t, im_n = rgb(THEN), rgb(NOW)
    sel = m["inbox"] & (nd_t < 0.10) & (nd_n < 0.10) & (dem < 2000) & np.isfinite(im_t[0]) & np.isfinite(im_n[0])
    coef = match(im_t, im_n, sel)
    im_tm = np.stack([a + b * im_t[k] for k, (a, b) in enumerate(coef)])
    log = dict(then=THEN, now=NOW, coef_now_eq_a_plus_b_then={c: v for c, v in zip("RGB", coef)}, frames={})
    for name, (bb, w, h) in FRAMES.items():
        cn = crop_ll(im_n, *bb)
        lum = cn.mean(axis=0)
        lo, hi = float(np.nanpercentile(lum, 0.5)), float(np.nanpercentile(lum, 99.8))
        log["frames"][name] = dict(bbox=bb, lo=round(lo, 4), hi=round(hi, 4), size=[w, h])
        for tag, arr, yr in (("", crop_ll(im_tm, *bb), THEN), ("", cn, NOW), ("_raw", crop_ll(im_t, *bb), THEN)):
            log["frames"][name][f"{yr}{tag}_unseen_px"] = int(np.isnan(arr[0]).sum())
            arr = fill_nearest(arr)
            img = render(arr, lo, hi)
            out = resize(img, w, h, bb)
            out.save(OUT / f"{name}_{yr}{tag}.jpg", quality=92, optimize=True)
        print(name, "done", flush=True)
    (OUT / "tone_match.json").write_text(json.dumps(log, indent=1))
    print(json.dumps(log, indent=1))


if __name__ == "__main__":
    main()
