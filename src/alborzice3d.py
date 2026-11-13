"""DAMAVAND IN LATE SUMMER, ONE PICTURE PER MEASURED YEAR: each year's white (snow and clean ice) painted on the
snow-free ground of 13 Sept 2025 and rendered with the terrain, sky and sun of alborz3d.py, always from one viewpoint.

Two surfaces: the coarse Alborz mesh (3 arc-seconds, Sentinel-2 composite tex_<ground>.jpg) with a hole cut at the
12 km square around the summit, and a fine patch in that square (dem.npy 30 m, ground_2025-09-13.jpg 10 m, both in
data/alborzice/damavand/). The fine picture is matched in mean and contrast to the coarse texture over the square and
feathered into it over the last 300 m; the fine rim is dropped by a few metres so the surfaces never fight. The white
of the year is painted on the 10-m picture from white/<year>.npz (30-m cells, bilinear, about 15 m feather).
Far terrain is blended towards the horizon colour beyond about 35 km.

    venv3d/bin/python src/alborzice3d.py --ground summer2025 [--out DIR] [--years 1992,2022] [--view ...]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pyvista as pv
from PIL import Image
from rasterio.crs import CRS
from rasterio.warp import Resampling, reproject, transform
from affine import Affine
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import alborz3d as A  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ROOT = A.ROOT
SNOWDIR = A.DATA
ICE = ROOT / "data" / "alborzice" / "damavand"
PICS = ROOT / "data" / "alborzice" / "pics"
TEX_STEP = 0.00025
SNOW_RGB = np.array([250, 252, 255], np.float32)
SHOULDER, SHOULDER_MAX, WARM = 115.0, 150.0, np.array([1.0, 0.92, 0.74], np.float32)
SNOW_LIFT = 0.6                                     # share of the lit snow blended back towards white
SUN = (0.9, -0.5, 0.9)                              # sun from the east-south-east
SS = 2
OVERLAP, RIM_DROP = 300.0, 0.008                    # m of coarse/fine overlap; km the fine rim is dropped (8 m)
HAZE_KM, HAZE_LEN, HAZE_MAX = 30.0, 40.0, 0.7
# focus lon, lat, focus height (km, exaggerated), distance km, azimuth, elevation
VIEW = (52.109, 35.955, 6.4, 19.0, 60.0, 17.0)
UTM = CRS.from_epsg(32639)


def geometry(grid):
    n, res, x0, y1 = grid["n"], grid["res"], grid["x0"], grid["y1"]
    return n, res, x0, y1


def coarse_mesh(grid):
    """Coarse mesh without the cells inside the summit square (minus the overlap)."""
    m = A.mesh()
    n, res, x0, y1 = geometry(grid)
    lo, la = transform(UTM, CRS.from_epsg(4326), [x0 + OVERLAP, x0 + n * res - OVERLAP], [y1 - n * res + OVERLAP, y1 - OVERLAP])
    xa, ya = A.xy(np.array(lo), np.array(la))      # square corners in local km (the local frame is axis-aligned lon/lat)
    # cell centres in local km
    cells = m.cell_centers().points
    inside = (cells[:, 0] > xa.min()) & (cells[:, 0] < xa.max()) & (cells[:, 1] > ya.min()) & (cells[:, 1] < ya.max())
    return m.extract_cells(np.where(~inside)[0])


def fine_mesh(grid):
    n, res, x0, y1 = geometry(grid)
    h = np.load(ICE / "dem.npy").astype(np.float64)
    cx = x0 + (np.arange(n) + 0.5) * res
    cy = y1 - (np.arange(n) + 0.5) * res
    X, Y = np.meshgrid(cx, cy)
    lon, lat = transform(UTM, CRS.from_epsg(4326), X.ravel().tolist(), Y.ravel().tolist())
    LON, LAT = np.array(lon).reshape(X.shape), np.array(lat).reshape(X.shape)
    kx, ky = A.xy(LON, LAT)
    ramp = np.minimum.reduce([np.arange(n)[None, :] + 0 * h, (n - 1 - np.arange(n))[None, :] + 0 * h,
                              np.arange(n)[:, None] + 0 * h, (n - 1 - np.arange(n))[:, None] + 0 * h]) * res
    drop = RIM_DROP * np.clip(1 - ramp / OVERLAP, 0, 1)
    Z = np.maximum(h, 0) / 1000.0 * A.VEXAG - drop
    g = pv.StructuredGrid(kx, ky, Z)
    u = np.broadcast_to((np.arange(n) + 0.5) / n, X.shape)
    v = np.broadcast_to(1 - (np.arange(n)[:, None] + 0.5) / n, X.shape)
    g.active_texture_coordinates = np.c_[u.ravel(order="F"), v.ravel(order="F")]
    return g


def fine_ground(coarse: np.ndarray, grid) -> np.ndarray:
    """ground_2025-09-13.jpg matched to the coarse texture over the square, feathered into it at the edge (1200 x 1200)."""
    n, res, x0, y1 = geometry(grid)
    fine = np.asarray(Image.open(ICE / "ground_2025-09-13.jpg").convert("RGB")).astype(np.float32)
    m = fine.shape[0]
    dt = Affine(res * n / m, 0, x0, 0, -res * n / m, y1)
    w, s, e, nn = A.BOX
    st = Affine(TEX_STEP, 0, w, 0, -TEX_STEP, nn)
    c = np.zeros((3, m, m), np.float32)
    for k in range(3):                                # the coarse texture resampled onto the fine grid (UTM)
        reproject(coarse[..., k].astype(np.float32), c[k], src_transform=st, src_crs=CRS.from_epsg(4326),
                  dst_transform=dt, dst_crs=UTM, resampling=Resampling.bilinear)
    c = np.moveaxis(c, 0, -1)
    cs = ndimage.gaussian_filter(c, (4, 4, 0))
    out = fine.copy()
    for k in range(3):
        mf, sf, mc, sc = fine[..., k].mean(), fine[..., k].std(), c[..., k].mean(), c[..., k].std()
        out[..., k] = (fine[..., k] - mf) / sf * sc + mc
    # clouds and their shadows of the 13 Sept pass (north-east of the summit): refilled from the coarse composite
    mx, mn = fine.max(-1), fine.min(-1)
    rr, cc = np.mgrid[0:m, 0:m]
    far = np.hypot(rr - 610, cc - 616) > 170           # the summit snow within 1.7 km stays
    cloud = ndimage.binary_opening((mn > 150) & (mx - mn < 70) & far, iterations=2)
    cloud = ndimage.binary_dilation(cloud, iterations=6)
    lum = fine.mean(-1)
    shadow = (lum < 0.45 * ndimage.median_filter(lum[::4, ::4], size=15).repeat(4, 0).repeat(4, 1)[:m, :m]) & far
    shadow = ndimage.binary_opening(shadow, iterations=1) & ndimage.binary_dilation(cloud, iterations=30)
    bad = ndimage.binary_dilation(cloud | shadow, iterations=6)
    soft = ndimage.gaussian_filter(bad.astype(np.float32), 3)[..., None]
    print("cloud/shadow refilled:", round(float(bad.mean()) * 144, 2), "km2", flush=True)
    out = np.clip(out * (1 - soft) + c * soft, 0, 255)
    d = np.minimum.reduce([np.arange(m)[None, :] + 0 * out[..., 0], (m - 1 - np.arange(m))[None, :] + 0 * out[..., 0],
                           np.arange(m)[:, None] + 0 * out[..., 0], (m - 1 - np.arange(m))[:, None] + 0 * out[..., 0]]) * (res * n / m)
    a = np.clip((d - 0.0) / OVERLAP, 0, 1)[..., None]
    a = a * a * (3 - 2 * a)
    return np.clip(a * out + (1 - a) * cs, 0, 255)


def compress(img: np.ndarray) -> np.ndarray:
    """Soft shoulder on the ground's highlights (pale rock, sulphur) with a warm tint, so no ground reads white."""
    img = img.astype(np.float32)
    lum = img.mean(-1, keepdims=True)
    over = np.maximum(lum - SHOULDER, 0)
    new = SHOULDER + (SHOULDER_MAX - SHOULDER) * (1 - np.exp(-over / (SHOULDER_MAX - SHOULDER)))
    k = np.where(lum > 1, np.where(over > 0, new, lum) / np.maximum(lum, 1), 1.0)
    t = np.clip(over / 60.0, 0, 1)
    return np.clip(img * k * (1 - t + t * WARM), 0, 255)


def paint(fine: np.ndarray, white: np.ndarray):
    m = fine.shape[0]
    z = ndimage.zoom(white.astype(np.float32), m / white.shape[0], order=1, grid_mode=True, mode="nearest")
    z = ndimage.gaussian_filter(z, 1.5)               # about 15 m feather
    a = np.clip((z - 0.5) * 2.0 + 0.5, 0, 1)[..., None]
    return np.clip(fine * (1 - a) + SNOW_RGB * a, 0, 255).round().astype(np.uint8), a[..., 0]


class Scene:
    def __init__(self, ground_name: str):
        self.grid = json.loads((ICE / "grid.json").read_text())
        coarse_arr = np.asarray(Image.open(SNOWDIR / f"tex_{ground_name}.jpg").convert("RGB"))
        self.fine = compress(fine_ground(coarse_arr, self.grid))
        self.coarse_tex = pv.numpy_to_texture(np.ascontiguousarray(compress(coarse_arr).round().astype(np.uint8)))
        self.cm, self.fm = coarse_mesh(self.grid), fine_mesh(self.grid)
        pv.OFF_SCREEN = True
        p = pv.Plotter(off_screen=True, window_size=(A.W * SS, A.H * SS), lighting="none")
        p.set_background(A.SKY[1], top=A.SKY[0])
        self.sun = pv.Light(light_type="scene light", color="#fff1da", intensity=1.0)
        p.add_light(self.sun)
        p.add_light(pv.Light(light_type="headlight", color="#dfe8ff", intensity=0.25))
        self.p = p

    def render(self, white, view, path: Path) -> None:
        p = self.p
        lon, lat, fz, dist, az, el = view
        foc = A.ground(lon, lat)
        if fz is not None:
            foc[2] = fz
        a, e = math.radians(az), math.radians(el)
        pos = foc + dist * np.array([math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)])
        if white is None:
            img_fine, alpha = self.fine, None
        else:
            img_fine, alpha = paint(self.fine, white)
        p.clear_actors()
        kw = dict(smooth_shading=True, ambient=0.5, diffuse=0.75, specular=0.0)
        p.add_mesh(self.cm, texture=self.coarse_tex, **kw)
        p.add_mesh(self.fm, texture=pv.numpy_to_texture(np.ascontiguousarray(img_fine.round().astype(np.uint8))), **kw)
        p.camera.view_angle = 40
        p.camera.position, p.camera.focal_point, p.camera.up = tuple(pos), tuple(foc), (0, 0, 1)
        self.sun.position = tuple(foc + np.array(SUN) * dist * 2)
        self.sun.focal_point = tuple(foc)
        p.renderer.ResetCameraClippingRange()
        p.render()
        img = p.screenshot(return_img=True).astype(np.float32)
        if alpha is not None:                           # second pass: where the snow is, unlit, to lift it back to white
            p.clear_actors()
            grey = np.repeat((alpha * 255)[..., None], 3, -1).round().astype(np.uint8)
            p.add_mesh(self.cm, color="black", lighting=False)
            p.add_mesh(self.fm, texture=pv.numpy_to_texture(np.ascontiguousarray(grey)), lighting=False)
            p.render()
            m = p.screenshot(return_img=True).astype(np.float32)[..., :1] / 255.0 * SNOW_LIFT
            img = img * (1 - m) + SNOW_RGB * m
        depth = p.get_image_depth(fill_value=np.nan)    # distance from the camera along the view axis (km)
        far = np.nan_to_num(depth, nan=0.0)
        f = np.clip((far - HAZE_KM) / HAZE_LEN, 0, 1) * HAZE_MAX
        hz = np.array([int(A.SKY[1][i:i + 2], 16) for i in (1, 3, 5)], np.float32)
        img = img * (1 - f[..., None]) + hz * f[..., None]
        Image.fromarray(img.round().astype(np.uint8)).resize((A.W, A.H), Image.LANCZOS).save(path, quality=92)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ground", required=True)
    ap.add_argument("--years", default="")
    ap.add_argument("--out", default=str(PICS))
    ap.add_argument("--view", default="", help="lon,lat,focus_height_km,dist_km,azimuth,elevation")
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    view = VIEW
    if args.view:
        view = tuple(float(x) for x in args.view.split(","))
    sc = Scene(args.ground)
    wd = ICE / "white"
    if args.synthetic:
        h = np.load(ICE / "dem.npy")
        sc.render(h > 4700, view, out / f"test{args.tag}.jpg")
        return
    years = [int(y) for y in args.years.split(",")] if args.years else json.loads((wd / "years.json").read_text())
    t0 = time.time()
    sc.render(None, view, out / "dam_bare.jpg")
    print("bare", f"{time.time() - t0:.1f} s", flush=True)
    for y in years:
        t0 = time.time()
        sc.render(np.load(wd / f"{y}.npz")["white"], view, out / f"dam_{y}.jpg")
        print(y, f"{time.time() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    main()
