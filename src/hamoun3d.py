"""WHERE DID THE HAMOUN GO, the 3D layer: the Sistan basin from the Copernicus DEM (on hamoun.py's picture grid,
about 143 m, meshed every second pixel, heights x VEX) draped with each spring's true-colour Landsat picture, the
year's measured open water inside the lakes tinted blue (hamoun.water_map: the share of each pixel that is water;
the tint is that share, nothing is drawn where the satellites saw no water). One frame per 1/30 s to
data/hamoun/reel/frames/, and per frame the camera's projection (frames.json) so the film can draw the shore of the
full lake, the city of Tehran to scale and the place names exactly on the ground.

The clock (data/hamoun/reel/timeline.json, src/hamounreel.py): a spring's picture holds for its step and cross-fades
into the next (XF per run); a year without a clean picture holds the last clean picture, dimmed and
without any water tint (its area stays on the counter); the edges of the picture fade into a haze (no slab edge).

Needs pyvista (VTK) for off-screen rendering (see tehranwater3d.py):
    .venv3d/bin/python src/hamoun3d.py                    # all frames (about 10 minutes)
    .venv3d/bin/python src/hamoun3d.py --at 0,5,8.6,15    # stills only, to data/hamoun/reel/stills/
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pyvista as pv
from PIL import Image, ImageEnhance, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "hamoun" / "reel"
W, H = 1080, 1920
STEP = 2                                                   # mesh every second picture pixel (about 290 m)
VEX = 3.0                                                  # vertical exaggeration (the basin is nearly flat)
WATER = np.array([70, 185, 245], np.float32)               # the light tint of measured open water
TINT = 0.25                                                # its strength where a pixel is all water
CONTRAST, COLOUR = 1.15, 1.30                              # the pictures, lifted a little (Landsat's pale desert)
UP = 2                                                     # the textures enlarged (Lanczos) before the unsharp mask
XF = dict(A=0.12, A2=0.14, B=0.10, C=0.20)                          # s: cross-fade between springs, per run
HAZE_KM = 12.0                                             # km: the width of that fade
WIDE = (58.70, 28.65, 64.30, 33.45)                        # the surroundings' box (get_hamoun3d.WIDE)
SHIFT = 0.34                                               # the view's centre, raised by this share of the half-height
SKY_TOP, SKY_LOW = "#b9c7d2", "#e4d6bc"


def ease(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


class Scene:
    def __init__(self):
        self.tl = tl = json.loads((DATA / "timeline.json").read_text())
        a, _, c, _, e, f = tl["pic_transform"]
        self.ny, self.nx = tl["pic_shape"]
        self.w0, self.n0, self.dlon, self.dlat = c, f, a, -e
        self.s0 = f + self.ny * e
        self.kx = 111.32 * math.cos(math.radians((self.n0 + self.s0) / 2))
        self.ky = 110.85
        dem = np.load(DATA / "dem_pic.npy").astype(np.float32)
        self.dem = dem
        self.base = float(np.percentile(dem, 5))                     # the basin floor: heights above it, x VEX
        lat = self.n0 - (np.arange(self.ny) + 0.5) * self.dlat
        lon = self.w0 + (np.arange(self.nx) + 0.5) * self.dlon
        self.LON, self.LAT = np.meshgrid(lon[::STEP], lat[::STEP])
        self.X, self.Y = self.xy(self.LON, self.LAT)
        self.Z = (dem[::STEP, ::STEP] - self.base) / 1000.0 * VEX
        self.cache = {}
        yy, xx = np.mgrid[0:self.ny, 0:self.nx]
        d = np.minimum.reduce([xx * self.dlon * self.kx, (self.nx - 1 - xx) * self.dlon * self.kx,
                               yy * self.dlat * self.ky, (self.ny - 1 - yy) * self.dlat * self.ky])
        self.haze = (1 - np.clip(d / HAZE_KM, 0, 1)) ** 1.6                 # 1 at the edge, 0 inside
        self.zmin = float(self.Z.min())
        self.Z = self.zmin + (self.Z - self.zmin) * (1 - self.haze[::STEP, ::STEP])   # flattens into the plain
        self.haze = self.haze[..., None].astype(np.float32)
        # the surroundings: Sentinel-2 cloudless (EOX) in the tones of the Landsat pictures (per band, the
        # least-squares gain and offset over the land of the picture's box), the box's part on the picture grid
        im = Image.open(DATA / f"tex_{tl['last']}.jpg").convert("RGB")
        ref = np.asarray(ImageEnhance.Color(ImageEnhance.Contrast(im).enhance(CONTRAST)).enhance(COLOUR), np.float32)
        wide = Image.open(DATA / "wide.jpg").convert("RGB")
        ww, ws, we, wn = WIDE
        px = lambda lon, lat: ((lon - ww) / (we - ww) * wide.width, (wn - lat) / (wn - ws) * wide.height)  # noqa: E731
        (c0, r0), (c1, r1) = px(self.w0, self.n0), px(self.w0 + self.nx * self.dlon, self.s0)
        box = np.asarray(wide.resize((self.nx, self.ny), Image.BILINEAR, box=(c0, r0, c1, r1)), np.float32)
        land = ~np.asarray(Image.open(DATA / f"water_{tl['first']}.png")).astype(bool)
        land &= (d > 2.0) & ~ndimage.binary_dilation(np.asarray(Image.open(DATA / "lakes.png")) > 0, iterations=8)
        self.tone = []
        for b in range(3):
            x, y = box[..., b][land], ref[..., b][land]
            self.tone.append(np.linalg.lstsq(np.c_[x, np.ones_like(x)], y, rcond=None)[0])
        self.edge = self.toned(box)
        wa = self.toned(np.asarray(wide, np.float32))
        self.wide_tex = np.clip(wa, 0, 255).astype(np.uint8)
        self.plain_rgb = np.median(self.edge[d < 6.0], axis=0).astype(np.float32)

    def toned(self, rgb: np.ndarray) -> np.ndarray:
        return np.stack([g * rgb[..., b] + c for b, (g, c) in enumerate(self.tone)], axis=-1)

    def xy(self, lon, lat):
        return (np.asarray(lon) - self.w0) * self.kx, (np.asarray(lat) - self.s0) * self.ky

    def z(self, lon, lat) -> np.ndarray:
        from scipy import ndimage
        j = (self.n0 - np.asarray(lat)) / self.dlat - 0.5
        i = (np.asarray(lon) - self.w0) / self.dlon - 0.5
        h = ndimage.map_coordinates(self.dem, [np.atleast_1d(j), np.atleast_1d(i)], order=1)
        return (h - self.base) / 1000.0 * VEX

    def world(self, lonlat) -> np.ndarray:
        p = np.asarray(lonlat, float)
        x, y = self.xy(p[:, 0], p[:, 1])
        return np.c_[x, y, self.z(p[:, 0], p[:, 1]) + 0.02]

    # ── the pictures ──
    def picture(self, year: int, held: bool = False) -> np.ndarray:
        """A year's texture (8-bit, at UP x the picture grid): the true colour, lifted a little (contrast CONTRAST,
        saturation COLOUR, a light unsharp mask after the enlargement) and its measured water under a light tint
        (TINT at most, the share of each pixel that is water); held = the picture of a spring shown for another (no
        tint: the film lays a light veil over it and says so). The edges fade into the plain."""
        key = (year, held)
        if key not in self.cache:
            im = Image.open(DATA / f"tex_{year}.jpg").convert("RGB")
            im = ImageEnhance.Color(ImageEnhance.Contrast(im).enhance(CONTRAST)).enhance(COLOUR)
            rgb = np.asarray(im, np.float32)
            if not held:
                share = np.asarray(Image.open(DATA / f"water_{year}.png"), np.float32)[..., None] / 255.0
                alpha = TINT * np.clip((share - 0.15) / 0.55, 0, 1)
                rgb = rgb * (1 - alpha) + WATER * alpha
            rgb = rgb * (1 - self.haze) + self.edge * self.haze
            big = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((self.nx * UP, self.ny * UP),
                                                                                 Image.LANCZOS)
            self.cache[key] = np.asarray(big.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2)))
        return self.cache[key]

    def shown(self, year: int) -> tuple:
        """(the picture's year, held?) for a spring: its own picture, or the last clean one before it."""
        if year in self.tl["pictures"]:
            return year, False
        return max(y for y in self.tl["pictures"] if y < year), True

    @staticmethod
    def run(years: list, t0: float, dt: float, xf: float, t: float, before=None) -> list:
        """Springs shown one after another from t0, one every dt s; each cross-fades in from the one before over
        xf s at the start of its step (the first from `before`, if given); the last one holds."""
        f = (t - t0) / dt
        k = min(int(f), len(years) - 1)
        tau = t - t0 - k * dt
        prev = years[k - 1] if k > 0 else before
        if prev is None or tau >= xf:
            return [(years[k], 1.0)]
        u = ease(tau / xf)
        return [(prev, 1 - u), (years[k], u)]

    def mix(self, t: float) -> list:
        """[(year, weight)] of the springs on screen at t."""
        tl = self.tl
        runs = tl["runs"]
        first, last = runs[0]["steps"][0]["year"], runs[-1]["steps"][-1]["year"]
        if t < tl["rewind"]:
            return [(last, 1.0)]
        if t < tl["run_a"]:
            u = ease((t - tl["rewind"]) / (tl["run_a"] - tl["rewind"]))
            return [(last, 1 - u), (first, u)]
        k = max(j for j, r in enumerate(runs) if r["t0"] <= t)
        r = runs[k]
        before = runs[k - 1]["steps"][-1]["year"] if k > 0 else None
        return self.run([s["year"] for s in r["steps"]], r["t0"], r["dt"], XF[r["name"]], t, before=before)

    def texture_at(self, t: float) -> np.ndarray:
        mix = [(y, w) for y, w in self.mix(t) if w > 0]
        if len(mix) == 1:
            return self.picture(*self.shown(mix[0][0]))
        out = np.zeros((self.ny * UP, self.nx * UP, 3), np.float32)
        for year, wgt in mix:
            out += wgt * self.picture(*self.shown(year))
        return np.clip(out, 0, 255).astype(np.uint8)

    # ── the camera ──
    def camera(self, t: float):
        """(position, focal point): a cubic Hermite path through the views (point looked at, azimuth, elevation,
        distance), closed (the last view equals the first); the position follows from the interpolated numbers."""
        keys = self.tl["views"]
        ts = [k[0] for k in keys]
        V = [np.array(k[1:], float) for k in keys]
        t = t % ts[-1]
        i = max(j for j in range(len(ts) - 1) if ts[j] <= t)
        n = len(ts) - 1

        def tangent(j):
            """Monotone (Fritsch-Carlson) tangents per number: zero where the path turns back, the harmonic mean of
            the two sides' slopes otherwise, so the camera never overshoots a view and comes back."""
            a, b = (j - 1) % n, (j + 1) % n if j < n else 1
            ta = ts[a] if a < j else ts[a] - ts[-1]
            tb = ts[b] if b > j else ts[b] + ts[-1]
            left = (V[j % n] - V[a]) / (ts[j] - ta)
            right = (V[b] - V[j % n]) / (tb - ts[j])
            with np.errstate(divide="ignore", invalid="ignore"):
                m = np.where(left * right > 0, 2.0 / (1.0 / left + 1.0 / right), 0.0)
            return np.nan_to_num(m)

        h = ts[i + 1] - ts[i]
        u = (t - ts[i]) / h
        h00, h10, h01, h11 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u, -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
        fx, fy, az, el, dist = h00 * V[i] + h10 * h * tangent(i) + h01 * V[i + 1] + h11 * h * tangent(i + 1)
        a, e = math.radians(az), math.radians(el)
        d = np.array([math.cos(e) * math.sin(a), math.cos(e) * math.cos(a), -math.sin(e)])
        foc = np.array([fx, fy, 0.0])
        return [foc - dist * d, foc]

    def plain(self):
        """The ground around the pictures: the Sentinel-2 cloudless surroundings (WIDE) on a flat plane just under the
        basin's floor, and beyond them a plain of their median colour to the horizon."""
        ww, ws, we, wn = WIDE
        (x0, y0), (x1, y1) = self.xy(ww, ws), self.xy(we, wn)
        g = pv.Plane(center=((x0 + x1) / 2, (y0 + y1) / 2, self.zmin - 0.03), direction=(0, 0, 1),
                     i_size=x1 - x0, j_size=y1 - y0, i_resolution=1, j_resolution=1)
        g.active_texture_coordinates = np.c_[(g.points[:, 0] - x0) / (x1 - x0), (g.points[:, 1] - y0) / (y1 - y0)]
        far = pv.Plane(center=((x0 + x1) / 2, (y0 + y1) / 2, self.zmin - 0.06), direction=(0, 0, 1),
                       i_size=4000, j_size=4000, i_resolution=1, j_resolution=1)
        return g, far

    def terrain(self):
        g = pv.StructuredGrid(self.X, self.Y, self.Z)
        u = (self.LON - self.w0) / (self.nx * self.dlon)
        v = (self.LAT - self.s0) / (self.ny * self.dlat)
        g.active_texture_coordinates = np.c_[u.ravel(order="F"), v.ravel(order="F")]
        return g


def projection(p: pv.Plotter) -> list:
    """The 4x4 world-to-normalized-device matrix of the current camera (row-major)."""
    m = p.camera.GetCompositeProjectionTransformMatrix(W / H, -1, 1)
    return [[round(m.GetElement(i, j), 9) for j in range(4)] for i in range(4)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--at", help="comma-separated times (s): stills only")
    ap.add_argument("--span", help="a,b: re-render only the frames between a and b s (the others are kept)")
    args = ap.parse_args()
    pv.OFF_SCREEN = True
    sc = Scene()
    tl = sc.tl
    p = pv.Plotter(off_screen=True, window_size=(W, H))
    tex0 = sc.texture_at(0.0)
    actor = p.add_mesh(sc.terrain(), texture=pv.Texture(tex0), smooth_shading=True, ambient=0.80,
                       diffuse=0.32, specular=0.0)
    near, far = sc.plain()
    p.add_mesh(near, texture=pv.Texture(sc.wide_tex), ambient=0.80, diffuse=0.32, specular=0.0)
    p.add_mesh(far, color=tuple(np.clip(sc.plain_rgb, 0, 255) / 255), ambient=0.80, diffuse=0.32, specular=0.0)
    p.set_background(SKY_LOW, top=SKY_TOP)
    p.camera.up = (0, 0, 1)
    p.camera.view_angle = 50
    p.camera.SetWindowCenter(0.0, -SHIFT)                 # the point looked at sits above the frame's middle
    p.add_light(pv.Light(position=(-200, -150, 120), focal_point=(70, 90, 0), color="#fff1da", intensity=0.6))
    times = [float(x) for x in args.at.split(",")] if args.at else [k / tl["fps"] for k in range(round(tl["duration"] * tl["fps"]))]
    keep = None
    if args.span:
        a, b = (float(x) for x in args.span.split(","))
        keep = {k for k, t in enumerate(times) if a <= t <= b}
    out = DATA / ("stills" if args.at else "frames")
    out.mkdir(parents=True, exist_ok=True)
    if not args.at and keep is None:
        for old in out.glob("f_*.png"):
            old.unlink()
    outlines = json.loads((DATA / "outlines.json").read_text())
    geo = dict(shore=[sc.world(s).round(4).tolist() for s in tl["shore"]],
               water={y: [sc.world(s).round(3).tolist() for s in ls] for y, ls in outlines.items()},
               tehran=sc.world(tl["tehran"]).round(4).tolist(),
               places={k: sc.world([v])[0].round(4).tolist() for k, v in tl["places"].items()})
    meta, last = [], None
    old = json.loads((out / "frames.json").read_text())["frames"] if keep is not None else None
    for k, t in enumerate(times):
        if keep is not None and k not in keep:
            meta.append(old[k])
            continue
        mix = tuple((y, round(w, 3)) for y, w in sc.mix(t))
        if mix != last:                                   # a new texture only when the picture changes
            actor.texture = pv.Texture(sc.texture_at(t))
            last = mix
        pos, foc = sc.camera(t)
        p.camera.position, p.camera.focal_point = tuple(pos), tuple(foc)
        p.camera.clipping_range = (1.0, 2500.0)
        p.render()
        name = out / (f"t{t:05.2f}.png" if args.at else f"f_{k:04d}.png")
        p.screenshot(str(name))
        meta.append(dict(t=round(t, 4), mix=[list(m) for m in mix], proj=projection(p)))
        if k % 60 == 0:
            print(f"{t:6.2f} s  {mix} -> {name.name}", flush=True)
    (out / "frames.json").write_text(json.dumps(dict(geo=geo, frames=meta)))
    p.close()
    print("saved", len(times), "frames to", out)


if __name__ == "__main__":
    main()
