"""THE SCENERY for the cross-sections (src/onebit_section.py): the sky and its clouds, rain that splashes, the
Alborz as it stands behind Tehran, the city's roofs with the Milad Tower, plane trees in autumn, pumping wells,
a dam, a person for scale.

The mountains are measured, not drawn: src/alborz_profiles.json holds the horizon seen from 35.62 N, 51.40 E
(60 m above the ground: the elevation angle per azimuth of the terrain within 19 km, within 38 km and beyond,
with the earth's curvature and refraction) and the north-south section along 51.42 E from Tochal down to the
plain, both from the Copernicus GLO-30 elevation model. make_profiles() rebuilds the file from the tiles.

    python -I src/onebit_scenery.py --profiles      rebuild src/alborz_profiles.json (needs data/subsidence/dem_*.npy)
"""

from __future__ import annotations

import functools
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit_section as S  # noqa: E402
from onebit_section import SS, Box, hash01, mix, rgba  # noqa: E402

PROFILES = Path(__file__).with_name("alborz_profiles.json")
OBSERVER = (35.62, 51.40, 60.0)                     # lat, lon, m above the ground: the south of Tehran
SECTION_LON = 51.42                                 # the meridian of the section: Tochal, then the city
REFRACTION = 0.13
PANORAMA = Path(__file__).with_name("alborz_panorama.png")
PAN = dict(az0=-40.0, az1=70.0, daz=0.06, dth=0.02, rows=290, dmax=115.0, zlo=800.0, zhi=5700.0)
LIGHT = (240.0, 35.0)                               # where the light comes from: azimuth and height, degrees


def make_profiles(out: Path = PROFILES) -> None:
    """The skyline and the section from the GLO-30 tiles (1 arc second; row 0 = north)."""
    tiles = {(la, lo): np.load(Path(__file__).resolve().parents[1] / "data" / "subsidence" /
                               f"dem_N{la}_00_E0{lo}_00.npy", mmap_mode="r") for la in (35, 36) for lo in (50, 51, 52)}

    def z(lat, lon):
        lat, lon = np.asarray(lat), np.asarray(lon)
        res = np.full(lat.shape, np.nan, np.float32)
        for (la, lo), a in tiles.items():
            m = (lat >= la) & (lat < la + 1) & (lon >= lo) & (lon < lo + 1)
            if m.any():
                r = np.clip(((la + 1 - lat[m]) * 3600).astype(int), 0, 3599)
                c = np.clip(((lon[m] - lo) * 3600).astype(int), 0, 3599)
                res[m] = a[r, c]
        return res

    lat0, lon0, up = OBSERVER
    z0 = float(z(np.array([lat0]), np.array([lon0]))[0]) + up
    az = np.radians(np.linspace(-72, 82, 617))
    A, Dk = np.meshgrid(az, np.arange(2.5, 115.0, 0.2), indexing="ij")          # km
    lat = lat0 + Dk * np.cos(A) / 111.2
    lon = lon0 + Dk * np.sin(A) / (111.2 * np.cos(np.radians(lat0)))
    Z = z(lat, lon)
    re = 6371.0 / (1 - REFRACTION)
    ang = np.degrees(np.arctan((Z - z0 - (Dk * 1000) ** 2 / (2 * re * 1000)) / (Dk * 1000)))
    layers = {}
    for name, dmax in (("near", 19.0), ("mid", 38.0), ("far", 200.0)):
        a = np.where(Dk <= dmax, ang, -90)
        k = np.nanargmax(a, axis=1)
        layers[name] = dict(angle=np.round(np.nanmax(a, axis=1), 3).tolist(),
                            elev=np.round(Z[np.arange(len(az)), k]).astype(int).tolist(),
                            dist=np.round(Dk[np.arange(len(az)), k], 1).tolist())
    lats = np.linspace(35.99, 35.42, 480)
    cols = SECTION_LON + np.arange(-8, 9) / 3600
    ns = np.nanmean(np.stack([z(lats, np.full_like(lats, c)) for c in cols]), axis=0)
    _panorama(z, z0).save(PANORAMA, optimize=True)
    out.write_text(json.dumps(dict(observer=[lat0, lon0, z0], azimuth=np.round(np.degrees(az), 2).tolist(),
                                   layers=layers, ns=dict(lon=SECTION_LON, lat=np.round(lats, 4).tolist(),
                                                          elev=np.round(ns).astype(int).tolist()))))


def _panorama(z, z0: float) -> Image.Image:
    """The view from the observer as a picture in angles: per azimuth (PAN daz) a ray is walked outwards, and
    each elevation angle (PAN dth per row, the horizon at the bottom) keeps the first ground it meets: its shade
    under LIGHT (red), its distance (green) and its height (blue; 0 = sky)."""
    lat0, lon0, _ = OBSERVER
    az = np.radians(np.arange(PAN["az0"], PAN["az1"] + 1e-9, PAN["daz"]))
    A, Dk = np.meshgrid(az, np.arange(2.0, PAN["dmax"], 0.1), indexing="ij")
    lat = lat0 + Dk * np.cos(A) / 111.2
    lon = lon0 + Dk * np.sin(A) / (111.2 * np.cos(np.radians(lat0)))
    Z = z(lat, lon)
    e = 3.0 / 3600                                                             # the slope over 6 arc seconds
    ze = (z(lat, lon + e) - z(lat, lon - e)) / (2 * e * 111200 * np.cos(np.radians(lat)))
    zn = (z(lat + e, lon) - z(lat - e, lon)) / (2 * e * 111200)
    sa, sh = np.radians(LIGHT)
    shade = np.clip((-ze * math.sin(sa) * math.cos(sh) - zn * math.cos(sa) * math.cos(sh) + math.sin(sh))
                    / np.sqrt(1 + ze ** 2 + zn ** 2), 0.0, 1.0)
    re = 6371.0 / (1 - REFRACTION)
    ang = np.degrees(np.arctan((Z - z0 - (Dk * 1000) ** 2 / (2 * re * 1000)) / (Dk * 1000)))
    run = np.maximum.accumulate(np.where(np.isnan(ang), -90.0, ang), axis=1)
    th = (np.arange(PAN["rows"]) + 0.5) * PAN["dth"]
    out = np.zeros((PAN["rows"], len(az), 3), np.uint8)
    for i in range(len(az)):
        k = np.searchsorted(run[i], th)
        ok = k < run.shape[1]
        kk = k[ok]
        out[ok, i, 0] = np.clip(shade[i, kk] * 255, 0, 255)
        out[ok, i, 1] = np.clip(Dk[i, kk] / PAN["dmax"] * 255, 1, 255)
        out[ok, i, 2] = np.clip((Z[i, kk] - PAN["zlo"]) / (PAN["zhi"] - PAN["zlo"]) * 254 + 1, 1, 255)
    return Image.fromarray(out[::-1].copy())


@functools.lru_cache(maxsize=1)
def profiles() -> dict:
    return json.loads(PROFILES.read_text(encoding="utf-8"))


def section(w: float, y_top: float, y_low: float, lat_n: float = 35.99, lat_s: float = 35.42):
    """The real section along 51.42 E between two latitudes, as a surface y(x) across the width w (north at the
    left): the highest point at y_top, the lowest at y_low. Returns (surf, elev): both functions of x."""
    P = profiles()["ns"]
    lat, z = np.array(P["lat"]), np.array(P["elev"], np.float64)
    keep = (lat <= lat_n) & (lat >= lat_s)
    lat, z = lat[keep], z[keep]
    xs = (lat_n - lat) / (lat_n - lat_s) * w

    def elev(x):
        return float(np.interp(x, xs, z))

    def surf(x):
        return y_low - (elev(x) - z.min()) / (z.max() - z.min()) * (y_low - y_top)

    return surf, elev


# ── the sky ──

def sky(b: Box, y_h: float, storm: float = 0.0):
    """The sky down to y_h: clear blue fading to cream at the horizon; `storm` 0..1 turns it grey."""
    b.vgradient(0, 0, b.w, y_h, mix(S.SKY_TOP, S.STORM_TOP, storm), mix(S.SKY_LOW, S.STORM_LOW, storm))


def sun(b: Box, x: float, y: float, r: float = 24.0, a: float = 1.0):
    if a > 0.01:
        b.glow(x, y, r * 3.4, (255, 238, 176), 0.55 * a)
        b.ellipse(x, y, r, r, rgba((255, 216, 122), a))


@functools.lru_cache(maxsize=48)
def cloud_sprite(w: int, h: int, seed: int, dark: bool) -> Image.Image:
    """A cumulus w by h px: puffs on a flat base, soft edges, a shaded underside (RGBA, SS scale)."""
    W, H = w * SS, h * SS
    rng = np.random.default_rng(300 + seed)
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    n = 8
    for k in range(n):
        r = H * (0.16 + 0.17 * math.sin(math.pi * (k + 0.5) / n)) * rng.uniform(0.85, 1.15)
        cx = W * (0.17 + 0.66 * k / (n - 1)) + rng.uniform(-0.03, 0.03) * W
        cy = H * 0.62 - 0.55 * r + rng.uniform(-0.03, 0.03) * H
        d.ellipse([cx - 1.3 * r, cy - r, cx + 1.3 * r, cy + r], fill=255)
    d.rounded_rectangle([W * 0.07, H * 0.50, W * 0.93, H * 0.80], radius=H * 0.15, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(H * 0.030))
    yy = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None, None]
    top = np.array((204, 208, 216) if dark else (255, 255, 255), np.float32)
    base = np.array((92, 100, 118) if dark else (206, 216, 230), np.float32)
    shade = np.clip((yy - 0.22) / 0.55, 0.0, 1.0) ** 1.4
    col = (top * (1 - shade) + base * shade) * (0.93 + 0.14 * S.fbm((H, W), H * 0.22, seed + 5, 3)[:, :, None])
    im = Image.fromarray(np.uint8(np.clip(col, 0, 255))).convert("RGBA")
    im.putalpha(m)
    return im


def cloud(b: Box, x: float, y: float, w: int = 260, h: int = 104, seed: int = 0, storm: float = 0.0, a: float = 1.0):
    """A cloud centred on (x, y); `storm` 0..1 darkens it (two sprites cross-faded)."""
    if a <= 0.01:
        return
    if storm < 0.98:
        b.paste(cloud_sprite(w, h, seed, False), x=x - w / 2, y=y - h / 2, alpha=a)
    if storm > 0.02:
        b.paste(cloud_sprite(w, h, seed, True), x=x - w / 2, y=y - h / 2, alpha=a * min(1.0, storm))


def rain(b: Box, tp: float, strength: float, surf, x0: float = 0.0, x1: float | None = None, top: float = 0.0,
         n: int = 150, wind: float = 0.16, colour=(226, 238, 250), splash: bool = True):
    """Rain in three depth planes between x0 and x1, from y = top down to y = surf(x) (a number or a function),
    where each drop splashes. `strength` 0..1 thins it; `tp` is the clock of the particles (real seconds)."""
    if strength <= 0.01:
        return
    x1 = b.w if x1 is None else x1
    f = surf if callable(surf) else (lambda _x: surf)
    for k in range(n):
        if hash01(k, 3) > strength:
            continue
        plane = k % 3                                        # 0 far ... 2 near
        speed, ln, wd, al = ((520, 15, 1.1, 0.34), (700, 23, 1.6, 0.50), (900, 32, 2.2, 0.66))[plane]
        x = x0 + (x1 - x0) * hash01(k, 1)
        gy = f(x)
        period = (gy - top + ln) / speed + 0.14 + 0.3 * hash01(k, 7)
        s = ((tp / period + hash01(k, 2)) % 1.0) * period * speed      # px fallen by the drop's head
        y = top + s
        if y <= gy:
            xx = x + wind * (gy - y)
            b.line([(xx + wind * ln, y - ln), (xx, y)], rgba(colour, al), wd)
        elif splash:
            q = (y - gy) / speed / 0.14                      # 0..1 through the splash
            if q < 1.0:
                r = 2.0 + (5.0 + 3.0 * plane) * q
                b.ellipse(x, gy - 0.5, r, 0.34 * r, None, outline=rgba(colour, 0.8 * (1 - q)), width=1.3)
                if q < 0.5:
                    b.line([(x - 3 - 6 * q, gy - 5 - 10 * q), (x - 3 - 7 * q, gy - 7 - 12 * q)], rgba(colour, 0.7), 1.3)
                    b.line([(x + 3 + 6 * q, gy - 4 - 9 * q), (x + 3 + 7 * q, gy - 6 - 11 * q)], rgba(colour, 0.7), 1.3)


# ── the Alborz ──

@functools.lru_cache(maxsize=6)
def alborz_sprite(w: int, y_h: int, az0: float, az1: float, ppd: float, snow: float) -> Image.Image:
    pan = np.asarray(Image.open(PANORAMA).convert("RGB"))
    c0, c1 = (int(round((v - PAN["az0"]) / PAN["daz"])) for v in (az0, az1))
    assert 0 <= c0 < c1 <= pan.shape[1], (az0, az1)
    pan = pan[:, c0:c1]
    seen = pan[:, :, 2] > 0
    top = np.argmax(seen, axis=0)                           # the ridge's row; the sky above it borrows its values,
    src = np.maximum(np.arange(pan.shape[0])[:, None], top[None, :])           # so scaling mixes no sky into it
    pan = np.take_along_axis(pan, np.repeat(src[:, :, None], 3, axis=2), axis=0)
    W, Hs = w * SS, int(round(PAN["rows"] * PAN["dth"] * ppd * SS))

    def up(a, mode=Image.BICUBIC):
        return np.asarray(Image.fromarray(np.ascontiguousarray(a)).resize((W, Hs), mode), np.float32)

    shade = up(pan[:, :, 0]) / 255.0
    dist = up(pan[:, :, 1]) / 255.0 * PAN["dmax"]
    elev = PAN["zlo"] + (up(pan[:, :, 2]) - 1.0) / 254.0 * (PAN["zhi"] - PAN["zlo"])
    alpha = np.clip((up(np.uint8(seen) * 255, Image.BILINEAR) / 255.0 - 0.5) * 3.0 + 0.5, 0.0, 1.0)
    d01 = np.clip((dist - 12.0) / 75.0, 0.0, 1.0)[:, :, None]
    near_c, far_c = np.array((156, 128, 102), np.float32), np.array((148, 166, 196), np.float32)
    col = (near_c * (1 - d01) + far_c * d01) * (0.46 + 0.92 * shade)[:, :, None]
    wander = 240.0 * (S.noise((Hs, W), 20 * SS, 43) - 0.5)                    # m: the snow line is not a ruler
    s = np.clip((elev + wander - snow) / 150.0, 0.0, 1.0)[:, :, None]
    col = col * (1 - s) + np.array((250, 251, 253), np.float32) * (0.70 + 0.36 * shade)[:, :, None] * s
    up_deg = np.linspace(PAN["rows"] * PAN["dth"], 0.0, Hs, dtype=np.float32)[:, None]
    k = np.clip(0.10 + 0.52 * d01[:, :, 0] + 0.30 * (1 - np.clip(up_deg / 2.6, 0.0, 1.0)), 0.0, 0.9)[:, :, None]
    col = col * (1 - k) + np.array((230, 231, 226), np.float32) * k            # haze: with distance, and low down
    spr = Image.fromarray(np.uint8(np.clip(col, 0, 255))).convert("RGBA")
    spr.putalpha(Image.fromarray(np.uint8(alpha * 255)))
    im = Image.new("RGBA", (W, y_h * SS), (0, 0, 0, 0))
    im.paste(spr, (0, y_h * SS - Hs))
    return im


def alborz(b: Box, y_h: float, az0: float = -34.0, az1: float = 66.0, ppd: float = 38.0, a: float = 1.0,
           snow: float = 3650.0):
    """The Alborz behind Tehran as it is seen from the south of the city (src/alborz_panorama.png: every pixel
    is the real ground a ray from the observer meets, shaded by its real slope), standing on the horizon y_h: the
    azimuths az0..az1 (degrees east of north, within -40..70; Tochal is at 3.5, Damavand's cone at 60) across the
    box's width, `ppd` px per degree of elevation angle. The plain itself rises to about 2 degrees (north Tehran),
    Tochal to 5.25; the true ratio would be w / (az1 - az0) px per degree, so 38 is about 4.6 times taller than
    life. Paler with distance and low down, snow above `snow` m. Stand city() in front of its lowest 2 degrees."""
    b.paste(alborz_sprite(b.w, int(round(y_h)), az0, az1, ppd, snow), alpha=a)


# ── the city ──

def _milad(d: ImageDraw.ImageDraw, x: float, base: float, s: float, col):
    """The Milad Tower, s px tall (435 m): a tapering shaft, the head at 0.62-0.725 of its height, the mast."""
    d.polygon([(x - 0.032 * s, base), (x - 0.015 * s, base - 0.62 * s), (x + 0.015 * s, base - 0.62 * s),
               (x + 0.032 * s, base)], fill=col)
    d.polygon([(x - 0.018 * s, base - 0.615 * s), (x - 0.069 * s, base - 0.672 * s), (x - 0.064 * s, base - 0.698 * s),
               (x - 0.030 * s, base - 0.725 * s), (x + 0.030 * s, base - 0.725 * s), (x + 0.064 * s, base - 0.698 * s),
               (x + 0.069 * s, base - 0.672 * s), (x + 0.018 * s, base - 0.615 * s)], fill=col)
    d.rectangle([x - 0.009 * s, base - 0.80 * s, x + 0.009 * s, base - 0.72 * s], fill=col)
    d.rectangle([x - 0.004 * s, base - s, x + 0.004 * s, base - 0.79 * s], fill=col)


@functools.lru_cache(maxsize=8)
def city_sprite(w: int, h: int, seed: int, milad: float) -> Image.Image:
    W, H = w * SS, h * SS
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(500 + seed)
    for col, hmax in (((190, 196, 204), 0.40), ((160, 166, 176), 0.28)):       # the far plane, then the near one
        if hmax > 0.3 and milad >= 0:
            _milad(d, milad * W, H, 0.97 * H, col + (255,))
        x = -8.0 * SS
        while x < W:
            bw = rng.uniform(9, 24) * SS
            bh = H * hmax * rng.uniform(0.35, 1.0) * (1.7 if rng.random() < 0.07 else 1.0)
            d.rectangle([x, H - bh, x + bw, H], fill=col + (255,))
            dark = tuple(int(c * 0.86) for c in col) + (255,)
            for wy in np.arange(H - bh + 3 * SS, H - 2 * SS, 5 * SS):          # rows of windows
                for wx in np.arange(x + 2.5 * SS, x + bw - 3 * SS, 4.5 * SS):
                    if rng.random() < 0.8:
                        d.rectangle([wx, wy, wx + 1.8 * SS, wy + 2.2 * SS], fill=dark)
            x += bw + rng.uniform(-2, 4) * SS
    return im


def city(b: Box, y_h: float, h: int = 78, seed: int = 0, milad: float = 0.30, a: float = 1.0):
    """Tehran's roofs in two hazy planes standing on y_h, with the Milad Tower (435 m; the sprite is h px tall)
    at the fraction `milad` of the width (negative: no tower)."""
    b.paste(city_sprite(b.w, h, seed, milad), x=0, y=y_h - h, alpha=a)


FACADES = ((228, 216, 198), (210, 198, 182), (198, 152, 120), (190, 178, 168), (216, 206, 192), (178, 134, 106),
           (202, 192, 178), (222, 208, 180))
ROOF = 14                                           # px of headroom over a building's roof (tanks, coolers)


@functools.lru_cache(maxsize=96)
def building_sprite(w: int, h: int, seed: int) -> Image.Image:
    """An apartment block w by h px: a brick or stone front, a shaded side, rows of windows (a few lit), a darker
    ground floor, a parapet, a water tank or a cooler on the roof. RGBA, SS scale, ROOF px taller than h."""
    W, H, R = w * SS, (h + ROOF) * SS, ROOF * SS
    rng = np.random.default_rng(700 + seed)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im, "RGBA")
    face = tuple(int(c * rng.uniform(0.94, 1.04)) for c in FACADES[int(rng.integers(len(FACADES)))])
    side = tuple(int(c * 0.74) for c in face)
    fw = int(W * 0.86)
    d.rectangle([0, R, fw, H], fill=face + (255,))
    d.rectangle([fw, R + 2 * SS, W - 1, H], fill=side + (255,))
    d.rectangle([0, R, fw, R + 3 * SS], fill=tuple(int(c * 0.80) for c in face) + (255,))       # the parapet
    floor = rng.uniform(15.0, 18.0) * SS
    rows = max(2, int((H - R - 6 * SS) / floor))
    cols = max(2, int(fw / (13.0 * SS)))
    cw = fw / cols
    y0 = R + 7 * SS
    balcony = rng.random() < 0.45
    for r in range(rows):
        yy = y0 + r * floor
        if yy + 10 * SS > H - 4 * SS:
            break
        ground = r == rows - 1 and yy + floor > H - 6 * SS
        for c in range(cols):
            xx = c * cw + 0.22 * cw
            lit = rng.random() < 0.10
            glass = (240, 208, 136) if lit else (74, 92, 112) if not ground else (58, 62, 70)
            d.rectangle([xx, yy, xx + 0.56 * cw, yy + 9.5 * SS], fill=glass + (255,))
            if not lit:
                d.polygon([(xx, yy), (xx + 0.56 * cw, yy), (xx, yy + 6 * SS)], fill=(150, 176, 200, 90))
            d.rectangle([xx - 0.8 * SS, yy + 9.5 * SS, xx + 0.56 * cw + 0.8 * SS, yy + 11 * SS],
                        fill=tuple(int(k * 0.86) for k in face) + (255,))
        if balcony and r < rows - 1:
            d.rectangle([0, yy + 11.5 * SS, fw, yy + 13 * SS], fill=tuple(min(255, int(k * 1.06)) for k in face) + (255,))
    d.rectangle([0, H - 2.5 * SS, W, H], fill=(84, 78, 72, 150))                                 # where it meets the ground
    x = rng.uniform(0.12, 0.5) * fw                                                              # on the roof
    if rng.random() < 0.6:                                                                       # a water tank
        d.rounded_rectangle([x, R - 9 * SS, x + 13 * SS, R], radius=3 * SS, fill=(206, 210, 214, 255))
        d.rectangle([x + 2 * SS, R - 1.5 * SS, x + 11 * SS, R], fill=(120, 124, 130, 255))
    else:                                                                                        # an evaporative cooler
        d.rectangle([x, R - 8 * SS, x + 10 * SS, R], fill=(176, 182, 188, 255))
        for k in range(3):
            d.line([(x + 1.5 * SS, R - (6.4 - 2 * k) * SS), (x + 8.5 * SS, R - (6.4 - 2 * k) * SS)],
                   fill=(110, 116, 124, 255), width=max(1, SS // 2))
    return im


def buildings(b: Box, x0: float, x1: float, base, seed: int = 0, hmin: int = 56, hmax: int = 124, a: float = 1.0):
    """A row of apartment blocks from x0 to x1; each stands on base(x) at its middle (`base` is a number or a
    function: a block sinks as a whole when its ground does). The row is the same for the same seed.
    Returns the blocks as (x0, y_roof, x1, y_base)."""
    f = base if callable(base) else (lambda _x: base)
    out, x, k = [], x0, 0
    while True:
        w = int(34 + 30 * hash01(k, seed + 11))
        if x + w > x1:
            break
        h = int(hmin + (hmax - hmin) * hash01(k, seed + 12) ** 1.3)
        yb = f(x + w / 2)
        b.paste(building_sprite(w, h, seed * 100 + k), x=x, y=yb - h - ROOF, alpha=a)
        out.append((x, yb - h, x + w, yb))
        x += w + 3 + 7 * hash01(k, seed + 13)
        k += 1
    return out


AUTUMN = ((206, 162, 62), (214, 134, 54), (172, 162, 72), (188, 106, 50), (142, 152, 80), (224, 184, 84))


@functools.lru_cache(maxsize=48)
def tree_sprite(h: int, seed: int) -> Image.Image:
    """A plane tree in autumn, h px tall (RGBA, SS scale, 0.84 h wide)."""
    w = int(h * 0.84)
    W, H = w * SS, h * SS
    rng = np.random.default_rng(900 + seed)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im, "RGBA")
    bark = (108, 84, 64, 255)
    d.polygon([(0.455 * W, H), (0.545 * W, H), (0.525 * W, 0.42 * H), (0.475 * W, 0.42 * H)], fill=bark)
    d.line([(0.5 * W, 0.56 * H), (0.30 * W, 0.36 * H)], fill=bark, width=max(2, int(0.035 * W)))
    d.line([(0.5 * W, 0.52 * H), (0.70 * W, 0.34 * H)], fill=bark, width=max(2, int(0.035 * W)))
    puffs = [(rng.uniform(0.22, 0.78), rng.uniform(0.16, 0.50), rng.uniform(0.15, 0.23)) for _ in range(11)]
    for cx, cy, r in sorted(puffs, key=lambda p: -p[1]):                    # the low ones first
        col = AUTUMN[int(rng.integers(len(AUTUMN)))]
        col = tuple(int(c * (0.80 + 0.5 * (0.5 - cy))) for c in col)
        d.ellipse([(cx - r) * W, (cy - 0.85 * r) * H * 0.84 / 1.0, (cx + r) * W, (cy + 0.85 * r) * H * 0.84 / 1.0 + 0.0],
                  fill=col + (255,))
        d.ellipse([(cx - 0.6 * r) * W, (cy - 0.7 * r) * H * 0.84, (cx + 0.1 * r) * W, (cy - 0.1 * r) * H * 0.84],
                  fill=(255, 236, 170, 56))
    return im


def tree(b: Box, x: float, y: float, h: int = 62, seed: int = 0, a: float = 1.0):
    """A plane tree in autumn colours with its foot at (x, y)."""
    spr = tree_sprite(h, seed)
    b.paste(spr, x=x - spr.width / SS / 2, y=y - h, alpha=a)


def top_face(b: Box, surf, depth: float = 16.0, x0: float = 0.0, x1: float | None = None, colour=(190, 178, 140),
             n: int = 90):
    """The land's surface as a strip seen from a little above: `depth` px of it behind the cut edge y = surf(x)."""
    x1 = b.w if x1 is None else x1
    f = surf if callable(surf) else (lambda _x: surf)
    xs = np.linspace(x0, x1, n)
    front = [(x, f(x)) for x in xs]
    back = [(x, f(x) - depth) for x in xs]
    b.poly(back + front[::-1], colour)
    b.line(back, rgba(mix(colour, S.WHITE, 0.45), 0.9), 1.4)
    b.line(front, rgba(mix(colour, S.INK, 0.55), 0.9), 1.6)


def grass(b: Box, surf, x0: float, x1: float, seed: int = 0, step: float = 7.0, colour=(150, 146, 84), hgt: float = 7.0):
    """Tufts of dry autumn grass on y = surf(x)."""
    f = surf if callable(surf) else (lambda _x: surf)
    k, x = 0, x0
    while x < x1:
        y, hh = f(x), hgt * (0.6 + 0.8 * hash01(k, seed + 21))
        col = mix(colour, (112, 132, 72), hash01(k, seed + 22))
        for dx in (-2.6, 0.0, 2.8):
            b.line([(x, y), (x + dx, y - hh * (1.0 if dx == 0 else 0.72))], col, 1.3)
        x += step * (0.6 + 0.9 * hash01(k, seed + 23))
        k += 1


# ── water works ──

def well(b: Box, x: float, y_ground: float, y_bottom: float, y_water: float | None = None, tp: float = 0.0,
         pumping: float = 1.0, y_head: float | None = None, wd: float = 9.0, side: int = 1, a: float = 1.0):
    """A pumped well at x: the casing from the wellhead down to y_bottom with a slotted screen at its foot, water
    standing in it from y_water down, and (pumping 0..1) water rising in the pipe and pouring from the outlet to
    the ground on `side` (1 right, -1 left). The wellhead stands on y_head (default: the ground); when the ground
    has sunk below it, the bare casing shows between them."""
    yh = y_ground if y_head is None else y_head
    hw = wd / 2
    b.rect(x - hw, yh - 2, x + hw, y_bottom, rgba((234, 231, 226), 0.96 * a), outline=rgba(S.STEEL_DARK, a), width=1.3)
    if y_water is not None and y_water < y_bottom:
        b.rect(x - hw + 1.6, max(y_water, yh), x + hw - 1.6, y_bottom - 1.2, rgba(S.WATER, 0.92 * a))
    screen = min(64.0, 0.28 * (y_bottom - yh))
    y = y_bottom - screen
    while y < y_bottom - 3:                               # the screen: slots that let the water in
        b.line([(x - hw, y), (x + hw, y)], rgba(S.STEEL_DARK, 0.75 * a), 1.2)
        y += 5.0
    if pumping > 0.02:                                    # the riser, with light running up it
        b.rect(x - 1.7, yh, x + 1.7, y_bottom - 8, rgba(S.WATER_LIGHT, 0.95 * a))
        span = max(1.0, y_bottom - 8 - yh)
        for k in range(int(span / 26) + 1):
            yy = y_bottom - 8 - ((tp * 110.0 + k * 26.0) % span)
            b.rect(x - 1.7, max(yh, yy - 7), x + 1.7, yy, rgba(S.WHITE, 0.9 * a * pumping))
    if y_ground > yh + 1.5:                               # bare casing above the sunken ground
        b.rect(x - hw, yh - 2, x + hw, y_ground, rgba(S.STEEL_LIGHT, a), outline=rgba(S.STEEL_DARK, a), width=1.3)
        b.line([(x - hw + 2.2, yh), (x - hw + 2.2, y_ground - 1)], rgba(S.WHITE, 0.7 * a), 1.2)
    b.rect(x - 16, yh - 5, x + 16, yh, rgba((196, 192, 184), a), outline=rgba(S.STEEL_DARK, 0.8 * a), width=1.0)
    b.rect(x - 7.5, yh - 33, x + 7.5, yh - 5, rgba((54, 96, 142), a), radius=3.0)       # the motor
    b.rect(x - 7.5, yh - 23, x + 7.5, yh - 19, rgba((34, 66, 104), a))
    b.rect(x - 4.5, yh - 31, x - 2.0, yh - 8, rgba((128, 170, 210), 0.8 * a), radius=1.0)
    b.rect(x - 5.5, yh - 37, x + 5.5, yh - 32, rgba(S.STEEL_DARK, a), radius=2.0)
    xo = x + side * 27.0
    b.line([(x + side * 7.0, yh - 13), (xo, yh - 13)], rgba(S.STEEL, a), 5.0)             # the outlet
    b.line([(xo, yh - 15.4), (xo, yh - 7)], rgba(S.STEEL, a), 5.0)
    if pumping > 0.02:
        q = a * pumping
        pts = [(xo + side * 0.8 * math.sin(tp * 9 + j), yh - 7 + (y_ground - yh + 7) * j / 6) for j in range(7)]
        b.line(pts, rgba(S.WATER_LIGHT, 0.95 * q), 3.6)
        b.line(pts, rgba(S.WHITE, 0.55 * q), 1.2)
        b.ellipse(xo + side * 3, y_ground - 1.0, 12, 2.6, rgba(S.WATER, 0.85 * q))
        for k in range(5):
            ph = (tp * 2.4 + hash01(k, 51)) % 1.0
            b.ellipse(xo + side * (2 + 16 * ph) * (1 if k % 2 else -0.6), y_ground - 3 - 16 * ph * (1 - ph) * 2.2,
                      1.4, 1.4, rgba(S.WATER_LIGHT, 0.9 * q * (1 - ph)))


def person(b: Box, x: float, y: float, h: float, colour=S.INK, a: float = 1.0):
    """A standing person h px tall with the feet at (x, y)."""
    c = rgba(colour, a)
    b.ellipse(x, y - 0.915 * h, 0.072 * h, 0.082 * h, c)
    b.rect(x - 0.135 * h, y - 0.815 * h, x + 0.135 * h, y - 0.44 * h, c, radius=0.06 * h)
    b.rect(x - 0.205 * h, y - 0.80 * h, x - 0.150 * h, y - 0.46 * h, c, radius=0.027 * h)
    b.rect(x + 0.150 * h, y - 0.80 * h, x + 0.205 * h, y - 0.46 * h, c, radius=0.027 * h)
    b.rect(x - 0.125 * h, y - 0.47 * h, x - 0.012 * h, y, c, radius=0.03 * h)
    b.rect(x + 0.012 * h, y - 0.47 * h, x + 0.125 * h, y, c, radius=0.03 * h)


def pool(b: Box, x0: float, x1: float, y_surface: float, floor, a: float = 1.0, tp: float = 0.0, n: int = 60):
    """Standing water between x0 and x1 with a level surface at y_surface, lying on y = floor(x) (a number or a
    function); only where the floor is below the surface."""
    f = floor if callable(floor) else (lambda _x: floor)
    xs = np.linspace(x0, x1, n)
    low = [(x, max(y_surface, f(x))) for x in xs]
    if max(p[1] for p in low) <= y_surface + 0.5:
        return
    b.poly([(x0, y_surface), (x1, y_surface)] + low[::-1], rgba(S.WATER, 0.94 * a))
    wet = [x for x, y in low if y > y_surface + 0.8]
    xa, xb = min(wet), max(wet)
    b.poly([(xa, y_surface), (xb, y_surface), (xb, y_surface + 5), (xa, y_surface + 5)], rgba(S.WATER_LIGHT, 0.55 * a))
    b.line([(xa, y_surface), (xb, y_surface)], rgba((226, 240, 252), 0.95 * a), 1.6)
    for k in range(3):                                    # glints that drift
        u = (hash01(k, 61) + 0.05 * tp) % 1.0
        xg = xa + (xb - xa) * (0.12 + 0.76 * u)
        b.line([(xg - 9, y_surface + 3 + 2 * k), (xg + 9, y_surface + 3 + 2 * k)], rgba(S.WHITE, 0.5 * a), 1.2)


def dam(b: Box, x: float, y_crest: float, y_foot: float, a: float = 1.0):
    """A concrete dam in section: the water side (left) nearly upright at x, the air side sloping to the right;
    the crest at y_crest, the foundation at y_foot."""
    hgt = y_foot - y_crest
    body = [(x - 0.05 * hgt, y_foot), (x, y_crest), (x + 0.17 * hgt, y_crest), (x + 0.17 * hgt, y_crest + 0.12 * hgt),
            (x + 0.74 * hgt, y_foot)]
    b.poly(body, rgba((204, 200, 192), a))
    b.poly([(x + 0.10 * hgt, y_crest), (x + 0.17 * hgt, y_crest), (x + 0.17 * hgt, y_crest + 0.12 * hgt),
            (x + 0.74 * hgt, y_foot), (x + 0.50 * hgt, y_foot)], rgba((168, 164, 158), a))
    for k in range(1, 5):                                 # the lifts the concrete was poured in
        yy = y_crest + hgt * k / 5
        xr = x + 0.17 * hgt + (0.57 * hgt) * max(0.0, (yy - y_crest - 0.12 * hgt) / (0.88 * hgt))
        b.line([(x - 0.05 * hgt * k / 5, yy), (xr, yy)], rgba(S.STEEL_DARK, 0.28 * a), 1.0)
    b.line(body + [body[0]], rgba(S.STEEL_DARK, 0.85 * a), 1.4)
    b.rect(x - 2, y_crest - 3.2, x + 0.17 * hgt + 2, y_crest, rgba((120, 122, 126), a))


if __name__ == "__main__":
    if "--profiles" in sys.argv:
        make_profiles()
        print("wrote", PROFILES)
