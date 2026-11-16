"""A ZOOM FROM THE WHOLE EARTH TO A PLACE, drawn frame by frame and played by a film's page as pictures: the method of
src/hoor_zoom.py (the Hoor al-Azim reel, 15 Nov 2026: the owner asked that a place reel open on the globe so that
one sees where the place is) with the place as a parameter, for the next place reels. hoor_zoom.py stays as it is:
it is the posted film's own code.

A place is a dict (see PLACE_KEYS): the centre the camera falls to, the box and the file of the picture it lands
on (the page's own first picture, any size: the frame's cover scale is taken from it), the folder of the four ground
levels g, r, m, n with their levels.json (get_<film>_zoom.py), the countries whose outlines are drawn, the output
folder. configure(place) sets it; build() draws the frames and returns what the page needs to project its labels.

- The camera never turns: the frame's centre is the place's centre from the first frame to the last; only the scale
  changes (pixels a kilometre), along a smooth monotone curve: the globe, a rest at the scale of the country for the
  names, the landing.
- The projection is orthographic about that centre (a globe); over the last octaves it is blended into the film's own
  grid (longitude and latitude as straight axes), so that the last frame is the page's own picture.
- The ground is ONE product at every scale (Sentinel-2 cloudless 2016 by EOX), each level fading in when the frame is
  close enough for it; on the way down it takes the landing picture's tones (one factor per band, the ratio of the two
  pictures' means on the picture's rim). Mind what that mosaic shows: it is 2016, so land on a picture of the same
  state (a lake that exists in the mosaic must exist in the landing picture).
- Only the named countries' outlines are drawn (Natural Earth 10 m admin-0 polygons), white on a dark casing; they
  fade before the landing.

    import zoomkit; zoomkit.configure(place); zoom = zoomkit.build()
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from multiprocessing import get_context
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

W, H, CX, CY = 1080, 1920, 540.0, 960.0
FPS = 30
ZOOM_T = 3.0                                          # seconds from the globe to the place
N = round(ZOOM_T * FPS) + 1                           # frames 0 .. N - 1; the last one is the landing
K = 111.32                                            # km a degree of latitude (the films' grids)
R = K * 180.0 / math.pi                               # the sphere's radius (km) that fits those grids
GLOBE_PX = 470.0                                      # the Earth's radius on screen in frame 0
DWELL = (1.0, 1.85)                                   # seconds: the rest at the scale of the country
DWELL_S = (0.42, 0.52)                                # pixels a km at its start and its end (the frame about 2,300 km wide)
PLACE_KEYS = ("name", "lon0", "lat0", "box", "pic", "levels", "nested", "out", "outlines", "ne")
P = {}                                                # the place (configure)


def configure(place: dict) -> None:
    """name; lon0, lat0: the centre; box (W, S, E, N) and pic: the landing picture; levels: the folder of g, r, m, n and
    levels.json; nested: {level: (half-width, half-height, km a pixel)}; out: the frames' folder; outlines: ADM0_A3
    codes; ne: Natural Earth's 10 m admin-0 countries shapefile."""
    assert all(k in place for k in PLACE_KEYS), [k for k in PLACE_KEYS if k not in place]
    if place != P:
        P.clear()
        P.update(place)
        _T.clear()


def km_lon() -> float:
    return K * math.cos(math.radians(P["lat0"]))
LINES = dict(fade=(2.15, 2.65), alpha=0.9, width=(2.4, 4.0))
BG = np.array([9, 11, 16], np.float32)
HALO = np.array([110, 160, 235], np.float32)
RIM = np.array([150, 190, 245], np.float32)
# a level is used once a frame pixel is smaller than START times its own pixel; it is fully in a factor FULL later
START, FULL = 3.0, 1.7
FEATHER = 0.12                                        # a level's soft edge into the coarser one, a share of its box
TONE = (0.6, 0.15)                                    # km a frame pixel: the ground starts to take the Landsat tones, has them
PIC_FADE = (0.13, 0.075)                              # km a frame pixel: the Landsat picture starts and is fully in
PIC_FEATHER = 0.15                                    # its soft edge (a share of the box) while it is small; none on the landing
FLAT = (0.12, 0.35)                                   # px a km: the globe's light fades out between these scales


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def landing_scale(gw: int, gh_: int) -> dict:
    """The page's own camera at rest: the picture covers the frame (film.js: base)."""
    base = max(W / gw, H / gh_)
    w, s, e, n = P["box"]
    return dict(base=base, s1=base * gw / ((e - w) * km_lon()), gw=gw, gh=gh_)


def scales(s1: float) -> np.ndarray:
    """Pixels a kilometre for every frame: a monotone smooth curve through the knots, at rest on the landing."""
    from scipy.interpolate import PchipInterpolator
    s0 = GLOBE_PX / R
    t = [0.0, 0.2, DWELL[0], DWELL[1], ZOOM_T, ZOOM_T + 0.3]
    v = [math.log(s0), math.log(1.03 * s0), math.log(DWELL_S[0]), math.log(DWELL_S[1]), math.log(s1), math.log(s1)]
    f = PchipInterpolator(t, v)
    out = np.exp(f(np.arange(N) / FPS))
    out[-1] = s1
    assert (np.diff(out) > 0).all(), "the zoom only goes in"
    return out


def blend(srel: float) -> float:
    """The share of the film's own grid in the projection: 0 on the globe, 1 over the last half octave."""
    a, b = math.log(1 / 8), math.log(1 / 1.5)
    return float(smooth((math.log(srel) - a) / (b - a)))


# ── the projection (the page has the same two formulas) ──────────────────────────────────────────────────────────
def inverse(S: float, L: dict):
    """Longitude and latitude (degrees) of every frame pixel's centre, and its distance from the centre (km)."""
    srel = S / L["s1"]
    wE = blend(srel)
    x = (np.arange(W, dtype=np.float64) + 0.5 - CX)[None, :]
    y = (np.arange(H, dtype=np.float64) + 0.5 - CY)[:, None]
    X, Y = x / S, -y / S                                                   # km east and north of the centre
    rho = np.hypot(X, Y)
    p0 = math.radians(P["lat0"])
    q = np.clip(rho / R, 0.0, 1.0)
    c = np.arcsin(q)
    sc, cc = np.sin(c), np.cos(c)
    safe = np.where(rho > 0, rho, 1.0)
    lat = np.degrees(np.arcsin(np.clip(cc * math.sin(p0) + Y * sc * math.cos(p0) / safe, -1, 1)))
    lon = P["lon0"] + np.degrees(np.arctan2(X * sc, safe * math.cos(p0) * cc - Y * math.sin(p0) * sc))
    if wE > 0:
        w, s, e, n = P["box"]
        lon_e = P["lon0"] + x * (e - w) / (L["base"] * srel * L["gw"]) + 0 * y
        lat_e = P["lat0"] - y * (n - s) / (L["base"] * srel * L["gh"]) + 0 * x
        lon, lat = (1 - wE) * lon + wE * lon_e, (1 - wE) * lat + wE * lat_e
    return lon, lat, rho, X, Y


def forward(lon: np.ndarray, lat: np.ndarray, S: float, L: dict):
    """Frame x, y of a point, and whether it is on the near side of the globe."""
    srel = S / L["s1"]
    wE = blend(srel)
    p0, p = math.radians(P["lat0"]), np.radians(lat)
    dl = np.radians(lon - P["lon0"])
    cosc = math.sin(p0) * np.sin(p) + math.cos(p0) * np.cos(p) * np.cos(dl)
    xo = CX + S * R * np.cos(p) * np.sin(dl)
    yo = CY - S * R * (math.cos(p0) * np.sin(p) - math.sin(p0) * np.cos(p) * np.cos(dl))
    w, s, e, n = P["box"]
    xe = CX + (lon - P["lon0"]) / (e - w) * L["base"] * srel * L["gw"]
    ye = CY - (lat - P["lat0"]) / (n - s) * L["base"] * srel * L["gh"]
    return (1 - wE) * xo + wE * xe, (1 - wE) * yo + wE * ye, cosc > 0.02


# ── the pictures ──────────────────────────────────────────────────────────────────────────────────────────────────
def bilinear(img: np.ndarray, u: np.ndarray, v: np.ndarray, wrap: bool = False) -> np.ndarray:
    h, w = img.shape[:2]
    v = np.clip(v, 0, h - 1.001)
    y0 = v.astype(np.int32)
    fy = (v - y0)[..., None].astype(np.float32)
    if wrap:
        u = np.mod(u, w)
        x0 = u.astype(np.int32) % w
        x1 = (x0 + 1) % w
    else:
        u = np.clip(u, 0, w - 1.001)
        x0 = u.astype(np.int32)
        x1 = x0 + 1
    fx = (u - np.floor(u))[..., None].astype(np.float32) if wrap else (u - x0)[..., None].astype(np.float32)
    top = img[y0, x0] * (1 - fx) + img[y0, x1] * fx
    bot = img[y0 + 1, x0] * (1 - fx) + img[y0 + 1, x1] * fx
    return top * (1 - fy) + bot * fy


def mips(im: Image.Image, n: int = 4) -> list:
    out = [np.asarray(im, np.float32)]
    for _ in range(n - 1):
        im = im.reduce(2)
        out.append(np.asarray(im, np.float32))
    return out


def tone_gain(src: np.ndarray, ref: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Per band one factor: the ratio of the two pictures' means on the mask. A factor keeps every hue where it is; a
    line or matched quantiles per band (both tried) turned the mosaic's white salt and brightest sand lilac, because
    its red is saturated there and its blue is not."""
    out = np.zeros(3, np.float32)
    for b in range(3):
        s, r = src[..., b][mask], ref[..., b][mask]
        out[b] = r.mean() / s.mean()
        print(f"  band {b}: ground {s.mean():.0f} +- {s.std():.0f}, Landsat {r.mean():.0f} +- {r.std():.0f}, factor {out[b]:.3f}")
    return out


_T = {}


def load() -> None:
    """The levels (with their half-size copies), the Landsat picture with its water, the outlines."""
    if _T:
        return
    levels = Path(P["levels"])
    meta = json.loads((levels / "levels.json").read_text())
    pic = Image.open(P["pic"]).convert("RGB")
    p = np.asarray(pic, np.float32)
    _T["pic"] = p                                                         # what the page draws on the landing
    gw, gh_ = pic.size
    _T["L"] = landing_scale(gw, gh_)
    # the Landsat tones for the near levels: level n on the picture's grid against the picture, on a ring of land
    w, s, e, n_ = P["box"]
    nm = meta["n"]
    near = Image.open(levels / "n.jpg").convert("RGB")
    bx = nm["box"]
    px = lambda lon: (lon - bx[0]) / (bx[2] - bx[0]) * near.width      # noqa: E731
    py = lambda lat: (bx[3] - lat) / (bx[3] - bx[1]) * near.height     # noqa: E731
    sub = np.asarray(near.resize((gw, gh_), Image.LANCZOS, box=(px(w), py(n_), px(e), py(s))), np.float32)
    ring = np.zeros((gh_, gw), bool)
    k_ = max(8, round(0.085 * gw))                                        # the picture's rim: the land both pictures show
    ring[:k_], ring[-k_:], ring[:, :k_], ring[:, -k_:] = True, True, True, True
    _T["tone"] = tone_gain(sub, p, ring)
    print(f"  tones matched on {ring.mean() * 100:.0f} % of the picture's grid")
    for name in ("g", "r", "m", "n"):
        im = Image.open(levels / f"{name}.jpg").convert("RGB")
        _T[name] = dict(box=meta[name]["box"], mips=mips(im), km=None)
    for name, (dx, dy, km) in P["nested"].items():
        _T[name]["km"] = km
    _T["g"]["km"] = 360.0 * K / _T["g"]["mips"][0].shape[1]
    import shapefile
    rd = shapefile.Reader(str(P["ne"]))
    fields = [f[0] for f in rd.fields[1:]]
    rings = []
    for sr in rd.iterShapeRecords():
        if dict(zip(fields, sr.record))["ADM0_A3"] not in P["outlines"]:
            continue
        pts = np.array(sr.shape.points, np.float64)
        parts = list(sr.shape.parts) + [len(pts)]
        rings += [pts[i:j] for i, j in zip(parts[:-1], parts[1:]) if j - i > 3]
    _T["rings"] = rings


def level(name: str, lon, lat, res: float):
    """A level's colours on the frame and where it has them (a soft edge inside its box)."""
    t = _T[name]
    w, s, e, n = t["box"]
    j = int(np.clip(math.floor(math.log2(max(res / t["km"], 1.0))), 0, len(t["mips"]) - 1))
    img = t["mips"][j]
    fu, fv = (lon - w) / (e - w), (n - lat) / (n - s)
    rgb = bilinear(img, fu * img.shape[1] - 0.5, fv * img.shape[0] - 0.5, wrap=name == "g")
    if name == "g":
        return rgb, None
    d = np.minimum(np.minimum(fu, 1 - fu), np.minimum(fv, 1 - fv))
    return rgb, smooth(d / FEATHER).astype(np.float32)


def frame(i: int, S: float) -> np.ndarray:
    L = _T["L"]
    srel = S / L["s1"]
    res = 1.0 / S                                                          # km a frame pixel
    tz = i / FPS
    lon, lat, rho, X, Y = inverse(S, L)
    out, _ = level("g", lon, lat, res)
    for name in ("r", "m", "n"):
        km = _T[name]["km"]
        a = float(smooth((math.log(START * km) - math.log(res)) / math.log(FULL)))
        if a <= 0:
            continue
        rgb, edge = level(name, lon, lat, res)
        al = (a * edge)[..., None]
        out = out * (1 - al) + rgb * al
    k = float(smooth((math.log(TONE[0]) - math.log(res)) / (math.log(TONE[0]) - math.log(TONE[1]))))
    if k > 0:                                                             # the ground takes the Landsat picture's tones
        out = out * (1 - k + k * _T["tone"])
    a = float(smooth((math.log(PIC_FADE[0]) - math.log(res)) / (math.log(PIC_FADE[0]) - math.log(PIC_FADE[1]))))
    if a > 0:
        w, s, e, n = P["box"]
        pic = _T["pic"]
        fu, fv = (lon - w) / (e - w), (n - lat) / (n - s)
        rgb = bilinear(pic, fu * pic.shape[1] - 0.5, fv * pic.shape[0] - 0.5)
        d = np.minimum(np.minimum(fu, 1 - fu), np.minimum(fv, 1 - fv))
        feather = PIC_FEATHER * (1 - float(smooth((srel - 0.55) / 0.45)))  # none on the landing: the frame is the picture
        edge = smooth(d / feather) if feather > 1e-6 else (d >= 0).astype(np.float32)
        al = (a * edge)[..., None].astype(np.float32)
        out = out * (1 - al) + rgb * al
    # the globe: its light, its rim, the space around it
    rpx = S * R
    if rpx < 1300:
        nx, ny = X / R, Y / R
        nz = np.sqrt(np.clip(1 - (rho / R) ** 2, 0, 1))
        sh = 1.12 * np.clip(0.62 + 0.38 * (-0.45 * nx + 0.5 * ny + 0.74 * nz), 0, 1.1) * (0.74 + 0.26 * np.sqrt(nz))
        flat = float(smooth((math.log(S) - math.log(FLAT[0])) / (math.log(FLAT[1]) - math.log(FLAT[0]))))
        sh = (1 + (sh / (1.12 * (0.62 + 0.38 * 0.74)) - 1) * (1 - flat))[..., None].astype(np.float32)
        rim = (0.35 * (1 - nz) ** 2.5)[..., None].astype(np.float32)
        out = (out * sh) * (1 - rim) + RIM * rim
        dpx = rho * S - rpx                                                # px outside the limb
        disc = np.clip(0.5 - dpx, 0, 1)[..., None].astype(np.float32)
        glow = (0.55 * np.exp(-np.clip(dpx, 0, None) / 18.0))[..., None].astype(np.float32)
        space = BG * (1 - glow) + HALO * glow
        out = out * disc + space * (1 - disc)
    # the outlines of Iran and Iraq
    la = LINES["alpha"] * (1 - float(smooth((tz - LINES["fade"][0]) / (LINES["fade"][1] - LINES["fade"][0]))))
    if la > 0.003:
        lw = LINES["width"][0] + (LINES["width"][1] - LINES["width"][0]) * float(smooth(tz / DWELL[0]))
        casing, line = Image.new("L", (2 * W, 2 * H), 0), Image.new("L", (2 * W, 2 * H), 0)
        dc, dl = ImageDraw.Draw(casing), ImageDraw.Draw(line)
        for ring in _T["rings"]:
            x, y, vis = forward(ring[:, 0], ring[:, 1], S, L)
            if not vis.all() or (x.max() < -50 or x.min() > W + 50 or y.max() < -50 or y.min() > H + 50):
                continue
            keep = np.ones(len(x), bool)
            if len(x) > 400:                                               # drop points closer than half a pixel
                step = np.hypot(np.diff(x), np.diff(y))
                acc, keep[1:] = 0.0, False
                for k in range(1, len(x)):
                    acc += step[k - 1]
                    if acc >= 0.5:
                        keep[k], acc = True, 0.0
                keep[-1] = True
            pts = [(2 * float(a_), 2 * float(b_)) for a_, b_ in zip(x[keep], y[keep])]
            if len(pts) > 1:
                dc.line(pts, fill=255, width=round(2 * (lw + 2.6)), joint="curve")
                dl.line(pts, fill=255, width=round(2 * lw), joint="curve")
        ca = np.asarray(casing.resize((W, H), Image.LANCZOS), np.float32)[..., None] / 255.0 * 0.45 * la
        li = np.asarray(line.resize((W, H), Image.LANCZOS), np.float32)[..., None] / 255.0 * la
        out = out * (1 - ca)
        out = out * (1 - li) + 255.0 * li
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


def _work(args) -> int:
    i, S, place = args
    configure(place)
    load()
    Image.fromarray(frame(i, S)).save(Path(P["out"]) / f"z{i:03d}.jpg", quality=92, subsampling=0)
    return i


def build(workers: int = 6, only: list | None = None) -> dict:
    """The frames (all, or the ones named) and what the page needs to project its labels on them."""
    out = Path(P["out"])
    out.mkdir(parents=True, exist_ok=True)
    pic = Image.open(P["pic"])
    L = landing_scale(*pic.size)
    S = scales(L["s1"])
    todo = list(range(N)) if only is None else only
    stamp = out / "stamp.json"
    key = dict(place={k: str(P[k]) for k in PLACE_KEYS}, n=N, s=[round(float(v), 6) for v in S], lines=LINES, tone=TONE, fade=PIC_FADE, feather=FEATHER, v=2,
               pic=hashlib.md5(Path(P["pic"]).read_bytes()).hexdigest())
    key = json.loads(json.dumps(key))                                      # as it reads back (lists, not tuples)
    fresh = only is None and stamp.exists() and json.loads(stamp.read_text()) == key and all((out / f"z{i:03d}.jpg").exists() for i in range(N))
    if not fresh:
        load()                                                             # prints the tone factors once, here
        place = dict(P)
        with get_context("spawn").Pool(workers) as pool:
            for i in pool.imap_unordered(_work, [(i, float(S[i]), place) for i in todo]):
                pass
        if only is None:
            stamp.write_text(json.dumps(key))
        print(f"zoom: {len(todo)} frames in {out}")
    else:
        print("zoom: frames are up to date")
    return dict(n=N, fps=FPS, t=ZOOM_T, dir="zoom", S=[round(float(v), 6) for v in S],
                wE=[round(blend(float(v) / L["s1"]), 5) for v in S], s1=L["s1"], base=L["base"], R=R,
                lon0=P["lon0"], lat0=P["lat0"], dwell=list(DWELL), globe_px=GLOBE_PX)


def tones() -> np.ndarray:
    """The three factors that give the ground the landing picture's tones (for a film's other ground pictures)."""
    load()
    return _T["tone"]
