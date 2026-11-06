"""THE LOST WATER OVER TEHRAN, the 3D layer: Tehran and the Alborz from the Copernicus DEM (30 m, meshed at 90 m,
no vertical exaggeration) draped with Sentinel-2 cloudless 2016 (EOX), Milad Tower as a simple model of its true
height (435 m), and the water layer of tehranwater.py over the city's outline (one thickness everywhere: the
surface follows the ground; glass walls along the outline). One frame per 1/30 s to data/tehranwater/frames/, and
the screen positions of Milad's foot and tip and of the water's surface above it (frames.json) for the film's
labels. The thickness follows the counter's steps (eased between steps); the camera follows a cubic Hermite
path through tehranwater.CAMERA.

Needs pyvista (VTK) for off-screen rendering, which the repo's main environment does not carry:
    uv venv .venv3d && uv pip install --python .venv3d/bin/python pyvista vtk numpy scipy pillow matplotlib
    .venv3d/bin/python src/tehranwater3d.py              # all frames (about 10 minutes)
    .venv3d/bin/python src/tehranwater3d.py --at 0,5,8.4,15   # stills only, to data/tehranwater/stills/
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pyvista as pv
from matplotlib.path import Path as MPath
from PIL import Image, ImageEnhance
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "tehranwater"
STEP = 3                                                   # arc-seconds: the terrain mesh (about 90 m)
W, H = 1080, 1920
WATER, WALL = "#1f9fe6", "#4cc8f5"
SKY_TOP, SKY_LOW = "#21508f", "#f0cf9e"


def ease(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


class Scene:
    def __init__(self):
        self.tl = json.loads((DATA / "timeline.json").read_text())
        w0, s0, e0, n0 = self.tl["bbox"]
        self.w0, self.s0, self.e0, self.n0 = w0, s0, e0, n0
        big = np.vstack([np.load(DATA / "dem_N36_00_E051_00.npy"), np.load(DATA / "dem_N35_00_E051_00.npy")])
        r0, r1 = round((37 - n0) * 3600), round((37 - s0) * 3600)
        c0, c1 = round((w0 - 51) * 3600), round((e0 - 51) * 3600)
        self.dem = big[r0:r1:STEP, c0:c1:STEP].astype(np.float32) / 1000.0       # km
        ny, nx = self.dem.shape
        self.ny, self.nx = ny, nx
        lat = n0 - (np.arange(ny) + 0.5) * STEP / 3600
        lon = w0 + (np.arange(nx) + 0.5) * STEP / 3600
        self.kx, self.ky = 111.32 * math.cos(math.radians(35.70)), 110.574
        self.LON, self.LAT = np.meshgrid(lon, lat)
        self.X, self.Y = (self.LON - w0) * self.kx, (self.LAT - s0) * self.ky
        m = self.tl["milad"]
        self.mx, self.my = self.xy(m["lon"], m["lat"])
        self.mz = self.ground(m["lon"], m["lat"])
        d = json.loads((DATA / "tehran_osm.json").read_text())
        self.ring = np.array((d if isinstance(d, list) else [d])[0]["geojson"]["coordinates"][0])
        self.inside = MPath(self.ring).contains_points(np.c_[self.LON.ravel(), self.LAT.ravel()]).reshape(self.LON.shape)

    def xy(self, lon, lat):
        return (np.asarray(lon) - self.w0) * self.kx, (np.asarray(lat) - self.s0) * self.ky

    def ground(self, lon, lat) -> float:
        j = (self.n0 - lat) / (STEP / 3600) - 0.5
        i = (lon - self.w0) / (STEP / 3600) - 0.5
        return float(ndimage.map_coordinates(self.dem, [[j], [i]], order=1)[0])

    # ── the clock ──
    def thickness(self, t: float) -> float:
        """The layer's thickness (km) at t s."""
        tl = self.tl
        d = [s["depth_m"] / 1000.0 for s in tl["steps"]]
        if t < tl["drain"] or t >= tl["land"]:
            return d[-1]
        if t < tl["rise"]:
            return d[-1] * (1 - ease((t - tl["drain"]) / (tl["rise"] - tl["drain"])))
        f = (t - tl["rise"]) / tl["t_step"]
        k = min(int(f), len(d) - 2)
        return d[k] + (d[k + 1] - d[k]) * ease(f - k)

    def camera(self, t: float):
        """(position, focal point) in scene km: a cubic Hermite path through the keys (tangents from the
        neighbours; the path is closed: the last key equals the first)."""
        keys = self.tl["camera"]
        ts = [k[0] for k in keys]
        P = [np.array(k[1]) for k in keys]
        F = [np.array(k[2]) for k in keys]
        t = t % ts[-1]
        i = max(j for j in range(len(ts) - 1) if ts[j] <= t)
        n = len(ts) - 1

        def tangent(A, j):
            a, b = (j - 1) % n, (j + 1) % n if j < n else 1
            ta = ts[a] if a < j else ts[a] - ts[-1]
            tb = ts[b] if b > j else ts[b] + ts[-1]
            return (A[b] - A[a]) / (tb - ta)

        h = ts[i + 1] - ts[i]
        u = (t - ts[i]) / h
        h00, h10, h01, h11 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u, -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
        out = []
        for A in (P, F):
            v = h00 * A[i] + h10 * h * tangent(A, i) + h01 * A[i + 1] + h11 * h * tangent(A, i + 1)
            out.append(v + np.array([self.mx, self.my, self.mz]))
        return out

    # ── meshes ──
    def terrain(self):
        g = pv.StructuredGrid(self.X, self.Y, self.dem)
        g.active_texture_coordinates = np.c_[((self.LON - self.w0) / (self.e0 - self.w0)).ravel(order="F"),
                                             ((self.LAT - self.s0) / (self.n0 - self.s0)).ravel(order="F")]
        return g

    def water_template(self):
        """The layer at zero thickness, cut along the east-west line through Milad Tower (a cutaway: the layer north
        of the line stays, so the camera south of it sees the layer's full thickness behind the tower): its top
        surface (cells with all four corners inside the outline and north of the line; VTK numbers a structured
        grid's cells with the first axis, the rows, fastest), the walls along the outline north of the line, and the
        cut face along the line. Returns the meshes, their zero-thickness heights and which points rise."""
        top = pv.StructuredGrid(self.X, self.Y, self.dem)
        ci = np.arange(top.n_cells)
        rr, cc = ci % (self.ny - 1), ci // (self.ny - 1)
        ins = self.inside & (self.Y >= self.my - STEP / 3600 * self.ky)   # one row south of the line ...
        keep = ins[rr, cc] & ins[rr + 1, cc] & ins[rr, cc + 1] & ins[rr + 1, cc + 1]
        surf = top.extract_cells(np.nonzero(keep)[0]).extract_surface(algorithm="dataset_surface")
        sp = surf.points.copy()                           # ... clamped onto the line: no strip of ground at the cut
        south = sp[:, 1] < self.my
        sp[south, 1] = self.my
        sp[south, 2] = [self.ground(self.w0 + x / self.kx, self.s0 + self.my / self.ky) for x in sp[south, 0]]
        surf.points = sp
        r = self.ring[::2]
        px, py = self.xy(r[:, 0], r[:, 1])
        zt = np.array([self.ground(lo, la) for lo, la in r])
        quads, pts = [], []
        for k in range(len(r) - 1):                      # the outline's walls, north of the line
            if py[k] >= self.my and py[k + 1] >= self.my:
                b = len(pts)
                pts += [(px[k], py[k], zt[k]), (px[k + 1], py[k + 1], zt[k + 1]),
                        (px[k + 1], py[k + 1], zt[k + 1]), (px[k], py[k], zt[k])]
                quads += [4, b, b + 1, b + 2, b + 3]
        lat_cut = self.s0 + self.my / self.ky             # the cut face: the line through Milad, inside the outline
        lons = np.arange(self.w0, self.e0, 0.0008)
        inn = MPath(self.ring).contains_points(np.c_[lons, np.full(len(lons), lat_cut)])
        for k in range(len(lons) - 1):
            if inn[k] and inn[k + 1]:
                (x0, x1), y = self.xy(lons[k:k + 2], lat_cut)[0], self.my
                z0, z1 = self.ground(lons[k], lat_cut), self.ground(lons[k + 1], lat_cut)
                b = len(pts)
                pts += [(x0, y, z0), (x1, y, z1), (x1, y, z1), (x0, y, z0)]
                quads += [4, b, b + 1, b + 2, b + 3]
        wall = pv.PolyData(np.array(pts, float), faces=np.array(quads))
        rise = np.zeros(len(pts), bool)
        rise[2::4] = True
        rise[3::4] = True                                 # the third and fourth corner of each quad are its top
        return surf, surf.points[:, 2].copy(), wall, rise

    def milad(self):
        mx, my, mz = self.mx, self.my, self.mz
        return [pv.Cylinder(center=(mx, my, mz + 0.14), direction=(0, 0, 1), radius=0.016, height=0.28, resolution=12),
                pv.Cylinder(center=(mx, my, mz + 0.29), direction=(0, 0, 1), radius=0.045, height=0.045, resolution=32),
                pv.Cone(center=(mx, my, mz + 0.335), direction=(0, 0, 1), radius=0.03, height=0.05, resolution=24),
                pv.Cylinder(center=(mx, my, mz + 0.395), direction=(0, 0, 1), radius=0.004, height=0.08, resolution=8)]


def texture(path: Path) -> pv.Texture:
    toned = path.with_name("texture_toned.jpg")
    if not toned.exists():
        im = Image.open(path).convert("RGB")
        ImageEnhance.Color(im).enhance(0.85).save(toned, quality=92)
    return pv.read_texture(str(toned))


def display(p: pv.Plotter, xyz) -> list:
    """Screen position (px from the top left) of a scene point."""
    r = p.renderer
    r.SetWorldPoint(float(xyz[0]), float(xyz[1]), float(xyz[2]), 1.0)
    r.WorldToDisplay()
    x, y, _ = r.GetDisplayPoint()
    return [round(x, 1), round(H - y, 1)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--at", help="comma-separated times (s): stills only")
    args = ap.parse_args()
    pv.OFF_SCREEN = True
    sc = Scene()
    surf, base_z, wall, rise = sc.water_template()
    p = pv.Plotter(off_screen=True, window_size=(W, H))
    p.add_mesh(sc.terrain(), texture=texture(DATA / "texture.jpg"), smooth_shading=True, ambient=0.35, diffuse=0.75,
               specular=0.0)
    for m in sc.milad():
        p.add_mesh(m, color="#ffffff", smooth_shading=True, specular=0.4, ambient=0.75, diffuse=0.4)
    a_surf = p.add_mesh(surf, color=WATER, opacity=0.40, smooth_shading=True, specular=0.9, specular_power=60,
                        ambient=0.3)
    a_wall = p.add_mesh(wall, color=WALL, opacity=0.34, ambient=0.55, specular=0.6)
    p.set_background(SKY_LOW, top=SKY_TOP)
    p.enable_depth_peeling(8)                             # translucent layers in order: no stripes
    p.camera.up = (0, 0, 1)
    p.camera.view_angle = 40
    p.add_light(pv.Light(position=(-40, -60, 60), focal_point=(sc.mx, sc.my, 1.2), color="#fff1da", intensity=0.85))
    wall_z0 = wall.points[:, 2].copy()
    tl = sc.tl
    times = [float(x) for x in args.at.split(",")] if args.at else [k / tl["fps"] for k in range(round(tl["duration"] * tl["fps"]))]
    out = DATA / ("stills" if args.at else "frames")
    out.mkdir(parents=True, exist_ok=True)
    if not args.at:
        for old in out.glob("f_*.png"):
            old.unlink()
    meta = []
    for k, t in enumerate(times):
        h = sc.thickness(t)
        pts = surf.points.copy()
        pts[:, 2] = base_z + h
        surf.points = pts
        wp = wall.points.copy()
        wp[rise, 2] = wall_z0[rise] + h
        wall.points = wp
        fade = min(1.0, h / 0.03)                         # the last 30 m fade out (no pop when it drains to 0)
        a_surf.visibility = a_wall.visibility = h > 0.0005
        a_surf.prop.opacity, a_wall.prop.opacity = 0.40 * fade, 0.34 * fade
        pos, foc = sc.camera(t)
        p.camera.position, p.camera.focal_point = tuple(pos), tuple(foc)
        p.render()
        name = out / (f"t{t:05.2f}.png" if args.at else f"f_{k:04d}.png")
        p.screenshot(str(name))
        meta.append(dict(t=round(t, 4), h_m=round(h * 1000, 1), milad_foot=display(p, (sc.mx, sc.my, sc.mz)),
                         milad_tip=display(p, (sc.mx, sc.my, sc.mz + 0.435)),
                         surface=display(p, (sc.mx, sc.my, sc.mz + h))))
        if k % 60 == 0:
            print(f"{t:6.2f} s  thickness {h * 1000:5.0f} m  -> {name.name}", flush=True)
    (out / "frames.json").write_text(json.dumps(meta))
    p.close()
    print("saved", len(times), "frames to", out)


if __name__ == "__main__":
    main()
