"""SINKING GROUND, the 3D layer: Iran from the Copernicus DEM (GLO-90 at 0.02 deg) and the Tehran-Karaj plain from
GLO-30 (meshed at 90 m), both draped with Sentinel-2 cloudless 2016 (EOX), and on them the subsidence rate of
Haghshenas Haghighi & Motagh 2024 (100 m, 2014-2020) as a glowing colour (one scale, the film draws its key). Outside
Iran the picture is dimmed and Iran's outline drawn (Natural Earth). The camera dives from the whole country to the
Tehran-Karaj plain and back (subsidence.CAMERA, cubic Hermite in log distance); the relief is exaggerated more from
far away (x6) than close up (x1.3), and the film says so nowhere because no height is read off the picture.

Iran's land is dimmed on both textures alike (so the glow reads from space) and lit back up close to the ground; outside
Iran the picture is darker still and fades into the night towards the edges of the national texture.

One frame per 1/30 s to data/subsidence/frames/, and the screen positions of the labels (frames.json).

Needs pyvista (VTK), pyshp and rasterio (the 3D environment of tehranwater3d.py plus two packages):
    uv pip install --python .venv3d/bin/python pyshp rasterio
    venv3d/bin/python src/subsidence3d.py                   # all frames (about 20 minutes)
    venv3d/bin/python src/subsidence3d.py --at 0,8,13,18     # stills only, to data/subsidence/stills/
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pyvista as pv
import rasterio
import shapefile
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "subsidence"
NE = ROOT / "data" / "grace" / "ne_10m_admin_0_countries" / "ne_10m_admin_0_countries.shp"
W, H = 1080, 1920
STEP = 3                                                    # arc-seconds: the fine patch's mesh (about 90 m)
SKY_FAR = ("#04070d", "#05090f")                           # the night from space (top, low): the texture's rim ...
SKY_NEAR = ("#3a6aa8", "#e6cfa4")                          # ... and close to the ground
# the colour scale of the rate (cm/yr): stops (rate, R, G, B, opacity)
RAMP = np.array([(0.0, 255, 196, 72, 0.14), (2.0, 255, 175, 55, 0.30), (5.0, 255, 145, 35, 0.62),
                 (10.0, 250, 90, 35, 0.82), (20.0, 228, 32, 62, 0.92), (30.0, 196, 18, 150, 0.96)])


# close up the slow ground is only tinted, so the city shows through; the fast ground glows as from far
NEAR_ALPHA = np.array([(0.0, 0.05), (2.0, 0.13), (5.0, 0.36), (10.0, 0.68), (20.0, 0.88), (30.0, 0.95)])


def ramp(rate: np.ndarray, near: bool = False) -> tuple:
    r = np.clip(rate, RAMP[0, 0], RAMP[-1, 0])
    rgb = np.stack([np.interp(r, RAMP[:, 0], RAMP[:, k]) for k in (1, 2, 3)], -1)
    if near:
        return rgb, np.interp(r, NEAR_ALPHA[:, 0], NEAR_ALPHA[:, 1])
    return rgb, np.interp(r, RAMP[:, 0], RAMP[:, 4])


def ease(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def lonlat_grid(box, step_deg):
    w, s, e, n = box
    lon = w + (np.arange(round((e - w) / step_deg)) + 0.5) * step_deg
    lat = n - (np.arange(round((n - s) / step_deg)) + 0.5) * step_deg
    return np.meshgrid(lon, lat)


class Scene:
    def __init__(self):
        self.tl = json.loads((DATA / "timeline.json").read_text())
        self.lon0, self.lat0 = self.tl["lon0"], self.tl["lat0"]

    def xy(self, lon, lat):
        lon, lat = np.asarray(lon, float), np.asarray(lat, float)
        return (lon - self.lon0) * 111.32 * np.cos(np.radians(lat)), (lat - self.lat0) * 110.574

    # ── the textures: imagery + the glowing rate ──
    def rate_on(self, box, shape) -> tuple:
        """The rate (cm/yr) and the covered share of each texture pixel of a box (lon/lat grid, rows from the north):
        A block-averaged to about the texture's pixel, then interpolated."""
        w, s, e, n = box
        hh, ww = shape
        with rasterio.open(DATA / "rate_A.tif") as src:
            res = abs(src.transform.a)
            f = max(1, int(((e - w) / ww) / res))           # A pixels per block
            win = rasterio.windows.from_bounds(w, s, e, n, src.transform).round_offsets().round_lengths()
            a = src.read(1, window=win, boundless=True, fill_value=src.nodata)
            tr = src.window_transform(win)
        cov = (a != -999.0).astype(np.float32)
        val = np.where(cov > 0, a, 0).astype(np.float32)
        if f > 1:
            r, c = a.shape[0] // f * f, a.shape[1] // f * f
            cov = cov[:r, :c].reshape(r // f, f, c // f, f).mean(axis=(1, 3))
            val = val[:r, :c].reshape(r // f, f, c // f, f).mean(axis=(1, 3))
        rate = np.where(cov > 0, val / np.maximum(cov, 1e-6), 0)
        bres = res * f
        lon, lat = np.meshgrid(w + (np.arange(ww) + 0.5) * (e - w) / ww, n - (np.arange(hh) + 0.5) * (n - s) / hh)
        ci = (lon - tr.c) / bres - 0.5
        ri = (tr.f - lat) / bres - 0.5
        cov_t = ndimage.map_coordinates(cov, [ri, ci], order=1, mode="constant", cval=0)
        rate_t = ndimage.map_coordinates(rate, [ri, ci], order=1 if f == 1 else 0, mode="constant", cval=0)
        return rate_t, np.clip(cov_t, 0, 1)

    def glow(self, img: Image.Image, box, sharp_sigma: float, wide_sigma: float, gain: float, paint: bool,
             bloom=(0.55, 0.45)) -> Image.Image:
        """The rate's colour over the imagery (painted from far; close up a tint that keeps the imagery's detail),
        with a soft bloom so the hotspots read."""
        base = np.asarray(img, np.float32)
        rate, cov = self.rate_on(box, base.shape[:2])
        rgb, alpha = ramp(rate, near=not paint)
        a = np.clip(cov * gain, 0, 1) * alpha
        lum = base.mean(-1, keepdims=True) / 255
        tint = rgb if paint else rgb * (0.55 + 0.75 * lum)    # close up: the colour, shaded by the ground below
        out = base * (1 - a[..., None]) + tint * a[..., None]
        for sig, k in zip((sharp_sigma, wide_sigma), bloom):
            bl = np.stack([ndimage.gaussian_filter(rgb[..., c] * a, sig) for c in range(3)], -1)
            out = 255 - (255 - out) * (1 - k * bl / 255)      # screen blend
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

    def iran_mask(self, box, shape) -> tuple:
        w, s, e, n = box
        hh, ww = shape
        sf = shapefile.Reader(str(NE))
        f = [i for i, r in enumerate(sf.records()) if r["ADM0_A3"] == "IRN"][0]
        shp = sf.shape(f)
        parts = list(shp.parts) + [len(shp.points)]
        m = Image.new("L", (ww, hh), 0)
        md = ImageDraw.Draw(m)
        rings = []
        for a, b in zip(parts[:-1], parts[1:]):
            pts = [((x - w) / (e - w) * ww, (n - y) / (n - s) * hh) for x, y in shp.points[a:b]]
            md.polygon(pts, fill=255)
            rings.append(pts)
        return np.asarray(m, np.float32) / 255, rings

    def textures(self) -> tuple:
        out = []
        for name, box, ss, ws, gain, dim in (("iran", self.tl["iran_box"], 7.0, 26.0, 5.0, True),
                                              ("karaj", self.tl["karaj_box"], 2.0, 10.0, 1.0, False)):
            path = DATA / f"tex_{name}_glow.jpg"
            if not path.exists():
                im = Image.open(DATA / f"tex_{name}.jpg").convert("RGB")
                im = ImageEnhance.Color(im).enhance(0.85)
                if not dim:                                   # the same tone as Iran's land on the national map
                    arr = np.asarray(im, np.float32)
                    im = Image.fromarray(np.clip(arr * 0.62 + arr.mean(-1, keepdims=True) * 0.10, 0, 255).astype(np.uint8))
                if dim:                                       # outside Iran: dimmed and greyer; Iran's outline
                    inside, rings = self.iran_mask(box, (im.height, im.width))
                    arr = np.asarray(im, np.float32)
                    grey = arr.mean(-1, keepdims=True)
                    outside = arr * 0.30 + grey * 0.08
                    land = arr * 0.62 + grey * 0.10               # Iran dimmed too, so the glow reads from space
                    k = ndimage.gaussian_filter(inside, 1.0)[..., None]
                    arr = land * k + outside * (1 - k)
                    hh, ww = inside.shape                    # towards the box's edges: fade into the night sky
                    ey = np.minimum(np.arange(hh), hh - 1 - np.arange(hh)) / (hh * 0.16)
                    ex = np.minimum(np.arange(ww), ww - 1 - np.arange(ww)) / (ww * 0.16)
                    v = np.clip(np.minimum(ey[:, None], ex[None, :]), 0, 1)[..., None] ** 1.5
                    night = np.array([5, 9, 18], np.float32)
                    arr = arr * v + night * (1 - v)
                    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
                im = self.glow(im, box, ss, ws, gain, paint=dim, bloom=(1.1, 0.9) if dim else (0.55, 0.45))
                if dim:
                    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
                    od = ImageDraw.Draw(ov)
                    for r in rings:
                        if len(r) > 200:                       # the mainland and big islands only
                            od.line(r + [r[0]], fill=(255, 255, 255, 170), width=4)
                    im = Image.alpha_composite(im.convert("RGBA"), ov.filter(ImageFilter.GaussianBlur(0.8))).convert("RGB")
                im.save(path, quality=93)
                print("saved", path.name, im.size, flush=True)
            out.append(pv.read_texture(str(path)))
        return out

    # ── the meshes ──
    def national(self):
        w, s, e, n = self.tl["iran_box"]
        st = self.tl["iran_step"]
        dem = np.load(DATA / "dem_iran.npy").astype(np.float32) / 1000.0
        dem = np.maximum(dem, -0.03)
        LON, LAT = lonlat_grid((w, s, e, n), st)
        assert LON.shape == dem.shape, (LON.shape, dem.shape)
        X, Y = self.xy(LON, LAT)
        g = pv.StructuredGrid(X, Y, dem)
        g.active_texture_coordinates = np.c_[((LON - w) / (e - w)).ravel(order="F"),
                                             ((LAT - s) / (n - s)).ravel(order="F")]
        kw, ks, ke, kn = self.tl["karaj_box"]                # a hole where the fine patch lies (a cell's margin)
        cl = LON[:-1, :-1] + st / 2
        ct = LAT[:-1, :-1] - st / 2
        inside = (cl > kw + st) & (cl < ke - st) & (ct > ks + st) & (ct < kn - st)
        ny = LON.shape[0]
        ci = np.arange(g.n_cells)
        rr, cc = ci % (ny - 1), ci // (ny - 1)                # VTK: the first axis (rows) fastest
        keep = ~inside[rr, cc]
        self.dem_n, self.box_n = dem, (w, s, e, n)
        return g.extract_cells(np.nonzero(keep)[0])

    def patch(self):
        w, s, e, n = self.tl["karaj_box"]
        t = {k: np.load(DATA / f"dem_{k}.npy") for k in ("N35_00_E050_00", "N36_00_E050_00", "N35_00_E051_00",
                                                          "N36_00_E051_00")}
        big = np.vstack([np.hstack([t["N36_00_E050_00"], t["N36_00_E051_00"]]),
                         np.hstack([t["N35_00_E050_00"], t["N35_00_E051_00"]])])   # 37 -> 35 N, 50 -> 52 E
        r0, r1 = round((37 - n) * 3600), round((37 - s) * 3600)
        c0, c1 = round((w - 50) * 3600), round((e - 50) * 3600)
        dem = big[r0:r1:STEP, c0:c1:STEP].astype(np.float32) / 1000.0 + 0.004
        ny, nx = dem.shape
        lat = n - (np.arange(ny) + 0.5) * STEP / 3600
        lon = w + (np.arange(nx) + 0.5) * STEP / 3600
        LON, LAT = np.meshgrid(lon, lat)
        X, Y = self.xy(LON, LAT)
        g = pv.StructuredGrid(X, Y, dem)
        g.active_texture_coordinates = np.c_[((LON - w) / (e - w)).ravel(order="F"),
                                             ((LAT - s) / (n - s)).ravel(order="F")]
        self.dem_p, self.box_p, self.step_p = dem, (w, s, e, n), STEP / 3600
        far = g.copy()                                       # the same patch with the national texture, 5 m lower:
        far.points[:, 2] -= 0.005                            # from far the fine patch fades into it (no seam)
        iw, is_, ie, in_ = self.tl["iran_box"]
        far.active_texture_coordinates = np.c_[((LON - iw) / (ie - iw)).ravel(order="F"),
                                               ((LAT - is_) / (in_ - is_)).ravel(order="F")]
        return g, far

    def ground(self, lon, lat) -> float:
        """Height (km) of the ground: the fine patch inside it, else the national grid."""
        w, s, e, n = self.box_p
        if w < lon < e and s < lat < n:
            dem, st = self.dem_p, self.step_p
        else:
            (w, s, e, n), dem, st = self.box_n, self.dem_n, self.tl["iran_step"]
        j, i = (n - lat) / st - 0.5, (lon - w) / st - 0.5
        return float(ndimage.map_coordinates(dem, [[j], [i]], order=1)[0])

    # ── the camera ──
    def camera(self, t: float):
        """(position, focal point, vertical exaggeration) at t: a closed cubic Hermite path through the keys in
        (focal x, y, z, log distance, azimuth, elevation)."""
        keys = self.tl["camera"]
        ts = [k["t"] for k in keys]
        V = [np.array(k["focal"] + [math.log(k["dist"]), k["az"], k["el"]]) for k in keys]
        t = t % ts[-1]
        i = max(j for j in range(len(ts) - 1) if ts[j] <= t)
        n = len(ts) - 1

        def tangent(j):
            """Monotone (Fritsch-Carlson): no overshoot between keys; at rest at the loop's seam and wherever a
            component turns."""
            if j in (0, n):
                return np.zeros_like(V[0])
            d0 = (V[j] - V[j - 1]) / (ts[j] - ts[j - 1])
            d1 = (V[j + 1] - V[j]) / (ts[j + 1] - ts[j])
            m = np.where(d0 * d1 > 0, 2 * d0 * d1 / np.where(d0 + d1 == 0, 1, d0 + d1), 0.0)
            return m

        h = ts[i + 1] - ts[i]
        u = (t - ts[i]) / h
        h00, h10, h01, h11 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u, -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
        v = h00 * V[i] + h10 * h * tangent(i) + h01 * V[i + 1] + h11 * h * tangent(i + 1)
        fx, fy, fz, ld, az, el = v
        dist = math.exp(ld)
        zs = zscale(dist)
        foc = np.array([fx, fy, fz * zs])
        a, e = math.radians(az), math.radians(el)
        pos = foc + dist * np.array([math.cos(e) * math.sin(a), math.cos(e) * math.cos(a), math.sin(e)])
        return pos, foc, zs, dist


def zscale(dist: float) -> float:
    """The vertical exaggeration: 1.3 close up (<= 100 km), 6 from far (>= 2,500 km), log-linear between."""
    f = (math.log(dist) - math.log(100)) / (math.log(2500) - math.log(100))
    return 1.3 + (6.0 - 1.3) * min(max(f, 0.0), 1.0)


def display(p: pv.Plotter, xyz) -> list:
    r = p.renderer
    r.SetWorldPoint(float(xyz[0]), float(xyz[1]), float(xyz[2]), 1.0)
    r.WorldToDisplay()
    x, y, z = r.GetDisplayPoint()
    return [round(x, 1), round(H - y, 1), round(z, 5)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--at", help="comma-separated times (s): stills only")
    args = ap.parse_args()
    pv.OFF_SCREEN = True
    sc = Scene()
    tex_n, tex_p = sc.textures()
    p = pv.Plotter(off_screen=True, window_size=(W, H), lighting="none")
    a_n = p.add_mesh(sc.national(), texture=tex_n, smooth_shading=True, ambient=0.40, diffuse=0.70, specular=0.0)
    fine, coarse = sc.patch()
    a_f = p.add_mesh(coarse, texture=tex_n, smooth_shading=True, ambient=0.40, diffuse=0.70, specular=0.0)
    a_p = p.add_mesh(fine, texture=tex_p, smooth_shading=True, ambient=0.40, diffuse=0.70, specular=0.0)
    p.camera.up = (0, 0, 1)
    p.camera.view_angle = 40
    sun = pv.Light(light_type="scene light", color="#fff1da", intensity=1.0)
    fill = pv.Light(light_type="headlight", color="#dfe8ff", intensity=0.25)
    p.add_light(sun)
    p.add_light(fill)
    tl = sc.tl
    labels = [(lab["text"], lab["x"], lab["y"], sc.ground(lab["lon"], lab["lat"])) for lab in tl["labels"]]
    local = [(lab["text"], lab["x"], lab["y"], sc.ground(lab["lon"], lab["lat"])) for lab in tl["local"]]
    times = [float(x) for x in args.at.split(",")] if args.at else [k / tl["fps"] for k in range(round(tl["duration"] * tl["fps"]))]
    out = DATA / ("stills" if args.at else "frames")
    out.mkdir(parents=True, exist_ok=True)
    if not args.at:
        for old in out.glob("f_*.png"):
            old.unlink()
    meta = []
    for k, t in enumerate(times):
        pos, foc, zs, dist = sc.camera(t)
        p.set_scale(zscale=zs, reset_camera=False)
        p.camera.position, p.camera.focal_point = tuple(pos), tuple(foc)
        p.camera.up = (0, 0, 1)
        sun.position = tuple(foc + np.array([-0.9, -0.7, 1.0]) * dist * 2)   # low from the south-west
        sun.focal_point = tuple(foc)
        f = min(1.0, max(0.0, (math.log(dist) - math.log(60)) / (math.log(1500) - math.log(60))))
        mix = lambda a, b: "#" + "".join(f"{round(int(a[i:i + 2], 16) * (1 - f) + int(b[i:i + 2], 16) * f):02x}"
                                         for i in (1, 3, 5))
        p.set_background(mix(SKY_NEAR[1], SKY_FAR[1]), top=mix(SKY_NEAR[0], SKY_FAR[0]))
        g = 1.0 + 0.38 * (1 - f)                              # close up the (dimmed) imagery is lit back to its tone
        a_p.prop.opacity = min(1.0, max(0.0, (math.log(1200) - math.log(dist)) / (math.log(1200) - math.log(400))))
        a_p.visibility = a_p.prop.opacity > 0.002
        for a in (a_n, a_f, a_p):
            a.prop.ambient = 0.40 * g
        sun.intensity, fill.intensity = 1.0 * g, 0.25 * g
        p.renderer.ResetCameraClippingRange()
        p.render()
        name = out / (f"t{t:05.2f}.png" if args.at else f"f_{k:04d}.png")
        p.screenshot(str(name))
        meta.append(dict(t=round(t, 4), dist=round(dist, 2), zscale=round(zs, 3),
                         labels=[display(p, (x, y, z * zs)) for _, x, y, z in labels],
                         local=[display(p, (x, y, z * zs)) for _, x, y, z in local]))
        if k % 60 == 0 or args.at:
            print(f"{t:6.2f} s  distance {dist:7.1f} km  x{zs:.2f}  -> {name.name}", flush=True)
    (out / "frames.json").write_text(json.dumps(meta))
    p.close()
    print("saved", len(times), "frames to", out)


if __name__ == "__main__":
    main()
