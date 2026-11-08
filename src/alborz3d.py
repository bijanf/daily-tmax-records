"""THE ALBORZ ABOVE TEHRAN IN 3D, the scene of the post-storm reel: Copernicus DEM GLO-30 (3 arc-seconds, heights
x VEXAG) draped with one Sentinel-2 true-colour pass (data/alborzsnow/tex_<date>.jpg, get_alborzsnow.py), lit by a low
sun from the south-west and a soft fill. Local flat coordinates in km about LON0, LAT0 (x east, y north, z up).

The views (lon, lat of the focus, distance km, azimuth deg from north towards the camera, elevation deg) are given
per still; the film's camera path comes later, when the after-storm pass is in.

    venv3d/bin/python src/alborz3d.py --date 2026-11-02 --views wide,lar,damavand
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pyvista as pv
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "alborzsnow"
BOX = (50.55, 35.45, 52.45, 36.40)                 # get_alborzsnow.BOX
LON0, LAT0 = 51.5, 35.9
KX, KY = 111.32 * math.cos(math.radians(LAT0)), 110.574
VEXAG = 1.6
W, H = 1080, 1920
SKY = ("#7fa6cf", "#e9dcc4")                       # top, horizon
DAMS = {"taleqan": (50.6343, 36.1891), "karaj": (51.091, 35.957), "latyan": (51.6793, 35.7901),
        "lar": (51.9988, 35.8901), "mamlu": (51.7872, 35.5827)}     # the dam points of get_<dam>.py
PLACES = {"tehran": (51.39, 35.69), "damavand": (52.109, 35.955), "karaj_city": (50.99, 35.83)}
VIEWS = {                                          # focus lon, lat, distance km, azimuth, elevation
    "wide": (51.50, 35.98, 140.0, 188.0, 42.0),    # from the south over Tehran: the whole range
    "lar": (51.98, 35.92, 45.0, 200.0, 30.0),      # the Lar reservoir under Damavand
    "damavand": (52.10, 35.95, 30.0, 215.0, 24.0),
    "karaj": (51.08, 36.00, 40.0, 185.0, 32.0),
}


def xy(lon, lat):
    return (np.asarray(lon) - LON0) * KX, (np.asarray(lat) - LAT0) * KY


def mesh() -> pv.StructuredGrid:
    h = np.load(DATA / "dem.npy")
    rows, cols = h.shape
    w, s, e, n = BOX
    lon = w + (np.arange(cols) + 0.5) * (e - w) / cols
    lat = n - (np.arange(rows) + 0.5) * (n - s) / rows
    LON, LAT = np.meshgrid(lon, lat)
    X, Y = xy(LON, LAT)
    Z = np.maximum(h, 0) / 1000.0 * VEXAG
    g = pv.StructuredGrid(X, Y, Z)
    u = (LON - w) / (e - w)
    v = (LAT - s) / (n - s)
    g.active_texture_coordinates = np.c_[u.ravel(order="F"), v.ravel(order="F")]
    return g


def ground(lon: float, lat: float) -> np.ndarray:
    h = np.load(DATA / "dem.npy")
    rows, cols = h.shape
    w, s, e, n = BOX
    r = min(rows - 1, max(0, int((n - lat) / (n - s) * rows)))
    c = min(cols - 1, max(0, int((lon - w) / (e - w) * cols)))
    x, y = xy(lon, lat)
    return np.array([float(x), float(y), max(h[r, c], 0) / 1000.0 * VEXAG])


def camera(view: tuple) -> tuple:
    lon, lat, dist, az, el = view
    foc = ground(lon, lat)
    a, e = math.radians(az), math.radians(el)
    pos = foc + dist * np.array([math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)])
    return pos, foc, dist


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True)
    ap.add_argument("--views", default="wide,lar,damavand,karaj")
    args = ap.parse_args()
    pv.OFF_SCREEN = True
    tex = pv.read_texture(str(DATA / f"tex_{args.date}.jpg"))
    p = pv.Plotter(off_screen=True, window_size=(W, H), lighting="none")
    p.add_mesh(mesh(), texture=tex, smooth_shading=True, ambient=0.45, diffuse=0.75, specular=0.0)
    p.set_background(SKY[1], top=SKY[0])
    p.camera.view_angle = 40
    sun = pv.Light(light_type="scene light", color="#fff1da", intensity=1.0)
    fill = pv.Light(light_type="headlight", color="#dfe8ff", intensity=0.25)
    p.add_light(sun)
    p.add_light(fill)
    out = DATA / "stills"
    out.mkdir(parents=True, exist_ok=True)
    for name in args.views.split(","):
        pos, foc, dist = camera(VIEWS[name])
        p.camera.position, p.camera.focal_point, p.camera.up = tuple(pos), tuple(foc), (0, 0, 1)
        sun.position = tuple(foc + np.array([-0.9, -0.7, 1.1]) * dist * 2)
        sun.focal_point = tuple(foc)
        p.renderer.ResetCameraClippingRange()
        p.render()
        path = out / f"{args.date}_{name}.png"
        p.screenshot(str(path))
        print("saved", path.name, flush=True)
    p.close()


if __name__ == "__main__":
    main()
