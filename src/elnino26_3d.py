"""EL NIÑO 2026, the 3D layer: the Earth as a globe draped with Sentinel-2 cloudless 2016 (EOX, CC BY 4.0), the
ocean tinted by this year's sea-surface temperature anomaly (NOAA OISST v2.1, mean of 16-22 Oct 2026, against
1991-2020): only water more than 1.5 °C warmer than normal is tinted, orange to red (the film's key says so). Iran's outline (Natural
Earth) in white. The camera starts over the equatorial Pacific, turns west over the Indian Ocean to Iran (8.5-12.5
s), stays, and returns to the Pacific by 30 s (a loop). One frame per 1/30 s to data/elnino26/frames/, with the
screen positions of the labels (frames.json).

    venv3d/bin/python src/elnino26_3d.py                 # all frames
    venv3d/bin/python src/elnino26_3d.py --at 0,6,10,14   # stills to data/elnino26/stills/
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pyvista as pv
import shapefile
import xarray as xr
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "elnino26"
SRC = ROOT / "data" / "enso_rain"
NE = ROOT / "data" / "grace" / "ne_10m_admin_0_countries" / "ne_10m_admin_0_countries.shp"
W, H = 1080, 1920
TW, TH = 8192, 4096                                        # the texture (equirectangular, 0.044 deg a pixel)
PACIFIC, IRAN = (-140.0, 2.0, 6.2), (53.5, 30.0, 2.75)    # (lon, lat of the view's centre, distance in radii)
# the anomaly's colours (°C, R, G, B, opacity): warm glows, cold is a faint blue
WARM = np.array([(1.5, 255, 200, 70, 0.0), (2.0, 255, 170, 50, 0.55), (3.0, 250, 110, 35, 0.8),
                 (4.0, 235, 45, 45, 0.9), (5.0, 205, 20, 100, 0.95)])
COLD = np.array([(-1.5, 120, 170, 255, 0.0), (-3.0, 90, 140, 255, 0.0)])   # off: the reel is about the warm water


def ease(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def texture() -> Path:
    path = DATA / "globe_texture.jpg"
    if path.exists():
        return path
    west = Image.open(SRC / "eox_-180.jpg").convert("RGB")
    east = Image.open(SRC / "eox_0.jpg").convert("RGB")
    base = Image.new("RGB", (TW, TH))
    base.paste(west, (0, 0))
    base.paste(east, (4096, 0))
    arr = np.asarray(base, np.float32) * 0.92
    d = xr.open_dataset(SRC / "oisst_anom_20261022.nc", engine="netcdf4")["anom"].squeeze().mean("time")
    a = d.values                                           # lat ascending -89.875..89.875, lon -179.875..179.875
    lat = d.latitude.values
    lon = d.longitude.values
    rows = (90 - (np.arange(TH) + 0.5) * 180 / TH)
    cols = -180 + (np.arange(TW) + 0.5) * 360 / TW
    ri = np.interp(rows, lat, np.arange(len(lat)))
    ci = np.interp(cols, lon, np.arange(len(lon)))
    ocean = np.isfinite(a).astype(np.float32)
    aa = np.where(np.isfinite(a), a, 0).astype(np.float32)
    R, C = np.meshgrid(ri, ci, indexing="ij")
    anom = ndimage.map_coordinates(aa, [R, C], order=1, mode="nearest")
    wet = ndimage.map_coordinates(ocean, [R, C], order=1, mode="nearest")
    out = arr
    for ramp, sel in ((WARM, anom > 0), (COLD, anom < 0)):
        x = np.clip(anom, ramp[:, 0].min(), ramp[:, 0].max())
        rgb = np.stack([np.interp(x, ramp[:, 0], ramp[:, k]) for k in (1, 2, 3)], -1)
        alp = np.interp(x, ramp[:, 0], ramp[:, 4]) * wet * sel
        out = out * (1 - alp[..., None]) + rgb * alp[..., None]
        if ramp is WARM:                                   # a soft bloom of the warm water
            for s, k in ((4, 0.45), (14, 0.25)):
                bl = np.stack([ndimage.gaussian_filter(rgb[..., c] * alp, s) for c in range(3)], -1)
                out = 255 - (255 - out) * (1 - k * bl / 255)
    im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    sf = shapefile.Reader(str(NE))
    k = [i for i, r in enumerate(sf.records()) if r["ADM0_A3"] == "IRN"][0]
    shp = sf.shape(k)
    parts = list(shp.parts) + [len(shp.points)]
    ov = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for a0, b0 in zip(parts[:-1], parts[1:]):
        pts = [((x + 180) / 360 * TW, (90 - y) / 180 * TH) for x, y in shp.points[a0:b0]]
        if len(pts) > 200:
            od.line(pts + [pts[0]], fill=(255, 255, 255, 240), width=6)
    im = Image.alpha_composite(im.convert("RGBA"), ov.filter(ImageFilter.GaussianBlur(0.6))).convert("RGB")
    im.save(path, quality=93)
    print("saved", path.name, im.size, "Nino-3.4 box mean anomaly",
          round(float(d.sel(latitude=slice(-5, 5), longitude=slice(-170, -120)).mean()), 2), flush=True)
    return path


def globe(r: float = 1.0):
    lon = np.linspace(-180, 180, 1441)
    lat = np.linspace(90, -90, 721)
    LON, LAT = np.meshgrid(np.radians(lon), np.radians(lat))
    X, Y, Z = r * np.cos(LAT) * np.cos(LON), r * np.cos(LAT) * np.sin(LON), r * np.sin(LAT)
    g = pv.StructuredGrid(X, Y, Z)
    g.active_texture_coordinates = np.c_[((np.degrees(LON) + 180) / 360).ravel(order="F"),
                                         ((np.degrees(LAT) + 90) / 180).ravel(order="F")]
    return g


def xyz(lon: float, lat: float, r: float = 1.0) -> np.ndarray:
    lo, la = math.radians(lon), math.radians(lat)
    return np.array([r * math.cos(la) * math.cos(lo), r * math.cos(la) * math.sin(lo), r * math.sin(la)])


def view(t: float, tl: dict):
    """(lon, lat, distance) of the camera at t: the Pacific, a turn west to Iran, the hold, the return."""
    a, b = tl["turn"]
    back0, back1 = tl["question_at"] + 0.3, tl["duration"]
    plon, plat, pd = PACIFIC
    ilon, ilat, idist = IRAN
    ilon_w = ilon - 360                                    # westward from the Pacific: over Asia and the Indian Ocean
    if t < a:
        drift = 4.0 * t / a                                # a slow drift west over the Pacific
        return plon - drift, plat, pd - 0.25 * t / a
    if t < b:
        u = ease((t - a) / (b - a))
        lon = (plon - 4.0) + (ilon_w - (plon - 4.0)) * u
        lat = plat + (ilat - plat) * u
        dist = math.exp(math.log(pd - 0.25) + (math.log(idist) - math.log(pd - 0.25)) * u)
        dist += 0.9 * math.sin(math.pi * u)                # pull back a little mid-turn: the whole Earth shows
        return lon, lat, dist
    if t < back0:
        k = (t - b) / (back0 - b)
        return ilon_w + 2.0 * k, ilat, idist - 0.12 * k     # a slow drift over Iran
    u = ease((t - back0) / (back1 - back0))
    lon0, dist0 = ilon_w + 2.0, idist - 0.12
    lon = lon0 + (plon - lon0) * u                         # east, back over Asia to the Pacific (the turn reversed)
    lat = ilat + (plat - ilat) * u
    dist = math.exp(math.log(dist0) + (math.log(pd) - math.log(dist0)) * u) + 0.9 * math.sin(math.pi * u)
    return lon, lat, dist


def display(p, pt) -> list:
    r = p.renderer
    r.SetWorldPoint(float(pt[0]), float(pt[1]), float(pt[2]), 1.0)
    r.WorldToDisplay()
    x, y, z = r.GetDisplayPoint()
    return [round(x, 1), round(H - y, 1), round(z, 5)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--at", help="comma-separated times (s): stills only")
    args = ap.parse_args()
    tl = json.loads((DATA / "timeline.json").read_text())
    pv.OFF_SCREEN = True
    tex = pv.read_texture(str(texture()))
    p = pv.Plotter(off_screen=True, window_size=(W, H), lighting="none")
    p.add_mesh(globe(), texture=tex, smooth_shading=True, ambient=0.30, diffuse=0.85, specular=0.15, specular_power=20)
    halo = pv.Sphere(radius=1.025, theta_resolution=120, phi_resolution=60)
    p.add_mesh(halo, color="#6fb3ff", opacity=0.10, ambient=1.0, diffuse=0.0, specular=0.0)
    p.set_background("#02040a", top="#0a1630")
    p.camera.view_angle = 40
    sun = pv.Light(light_type="scene light", color="#fff4e6", intensity=1.1)
    fill = pv.Light(light_type="headlight", color="#cfdcff", intensity=0.35)
    p.add_light(sun)
    p.add_light(fill)
    marks = {"nino": xyz(-140, 0, 1.0), "iran": xyz(54.0, 32.5, 1.0)}
    times = [float(x) for x in args.at.split(",")] if args.at else [k / tl["fps"] for k in range(round(tl["duration"] * tl["fps"]))]
    out = DATA / ("stills" if args.at else "frames")
    out.mkdir(parents=True, exist_ok=True)
    if not args.at:
        for old in out.glob("f_*.png"):
            old.unlink()
    meta = []
    for k, t in enumerate(times):
        lon, lat, dist = view(t, tl)
        foc = np.zeros(3)
        pos = xyz(lon, lat, dist)
        p.camera.position, p.camera.focal_point, p.camera.up = tuple(pos), tuple(foc), (0, 0, 1)
        sun.position = tuple(xyz(lon - 55, lat + 25, 30.0))  # the sun from the west and above
        sun.focal_point = (0, 0, 0)
        p.renderer.ResetCameraClippingRange()
        p.render()
        name = out / (f"t{t:05.2f}.png" if args.at else f"f_{k:04d}.png")
        p.screenshot(str(name))
        cam = np.array(pos)
        meta.append(dict(t=round(t, 4), lon=round(lon, 3), lat=round(lat, 3), dist=round(dist, 3),
                         marks={n: display(p, v) + [bool(np.dot(v, cam - v) > 0)] for n, v in marks.items()}))
        if k % 90 == 0 or args.at:
            print(f"{t:6.2f} s  lon {lon:8.2f}  lat {lat:6.2f}  distance {dist:5.2f}  -> {name.name}", flush=True)
    (out / "frames.json").write_text(json.dumps(meta))
    p.close()
    print("saved", len(times), "frames to", out)


if __name__ == "__main__":
    main()
