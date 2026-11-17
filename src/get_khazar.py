"""THE CASPIAN FILM, its data («آبِ خزر کجا رفت؟»): keyless public downloads into data/khazar/ (git-ignored).

THE PICTURES. NASA's daily corrected-reflectance mosaics (GIBS / Worldview, Web Mercator, public domain), for the
late summers (1 August to 30 September) of 2001-2026. One sensor per year: MODIS on Terra for 2001-2019 (a stable
10:30 orbit in those years) and VIIRS on NOAA-20 from 2020 (Terra's orbit drifts after 2020: its 2026 pictures are
washed out by glint). For every day of the window a small picture is scored (the share without data, the share that
is bright and grey: cloud), the clearest days are fetched at full size, and a year's picture is the median of them
per pixel and band (true colour, and the infrared composite that tells open water from salt and land: MODIS bands
7-2-1, VIIRS bands M11-I2-I1).

    frames (9:16 in Web Mercator):  ne    the north-east shelf (Kazakhstan's coast, the Ural's mouth, Kaydak)
                                    sea   the whole Caspian with Iran's coast and Tehran
                                    south the southern Caspian and Iran's coast
                                    wide  the Volga and the Kama down to the sea
    probe_<frame>.csv              frame, layer, day, nodata, cloud  (the score of each day)
    days/<frame>_<layer>_<day>.jpg the clearest days at full size
    <frame>_<year>_tc.jpg, _ir.jpg the year's median picture (true colour, infrared composite)
    wide.jpg                       NASA Blue Marble with relief and bathymetry
    lines.json                     the Volga, the Kama and the Ural (Natural Earth 10 m), the borders of the coastal states
    caspcom/                       the two catalogues of the Coordinating Committee on Hydrometeorology of the Caspian Sea
                                   (CASPCOM, http://www.caspcom.com): the sea's level per gauge and the rivers' runoff,
                                   monthly; level_<GAUGE>.csv, flow_<river>.csv and the annual tables

    python -I src/get_khazar.py --caspcom       # the catalogues (the .xls gauge files need xlrd: any Python with it)
    python -I src/get_khazar.py --probe         # score every day (about 10 minutes)
    python -I src/get_khazar.py                 # the clearest days, the yearly pictures, the map, the lines
"""

from __future__ import annotations

import io
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "khazar"
UA = {"User-Agent": "reel-map-fetch/1.0"}
R = 6378137.0
YEARS = range(2001, 2027)
WINDOW = ("08-01", "09-30")
SWITCH = 2020                                            # from this year VIIRS on NOAA-20; before it MODIS on Terra
N_BEST = 5                                               # days in a year's median picture
GIBS = ("https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1"
        "&LAYERS={}&STYLES=&SRS=EPSG:3857&BBOX={},{},{},{}&WIDTH={}&HEIGHT={}&FORMAT=image/jpeg&TIME={}")
GIBS_STATIC = ("https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1"
               "&LAYERS={}&STYLES=&SRS=EPSG:3857&BBOX={},{},{},{}&WIDTH={}&HEIGHT={}&FORMAT=image/jpeg")
CASPCOM = "http://caspcom.com/wp-content/uploads/2026/07/"
NE_URL = "https://naciscdn.org/naturalearth/10m/{}/{}.zip"


def mx(lon: float) -> float:
    return math.radians(lon) * R


def my(lat: float) -> float:
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * R


def lat_of(y: float) -> float:
    return math.degrees(2 * math.atan(math.exp(y / R)) - math.pi / 2)


def frame(west: float, east: float, south: float) -> tuple:
    """A 9:16 box in Web Mercator from its west and east edges and its south edge: (W, S, E, N) in degrees."""
    return west, south, east, lat_of(my(south) + (mx(east) - mx(west)) * 16 / 9)


# the frames, and the size at which a day is fetched (the page shows them 1080 wide: ne at about its native 250 m)
FRAMES = dict(ne=dict(box=frame(50.0, 54.6, 43.1), px=(1620, 2880)),
              sea=dict(box=frame(45.86, 55.54, 35.2), px=(2160, 3840)),
              south=dict(box=frame(47.9, 55.1, 31.5), px=(2160, 3840)),     # Iran's coast at the frame's middle
              wide=dict(box=frame(34.0, 59.2, 38.0), px=(2160, 3840)))      # the Volga from Rybinsk to its delta below the headline
SINGLE = dict(sea=(2001, 2026), south=(2026,))                             # frames shown for these summers only


def layers(year: int) -> tuple:
    """(true colour, infrared composite) of the sensor used for a year."""
    if year >= SWITCH:
        return "VIIRS_NOAA20_CorrectedReflectance_TrueColor", "VIIRS_NOAA20_CorrectedReflectance_BandsM11-I2-I1"
    return "MODIS_Terra_CorrectedReflectance_TrueColor", "MODIS_Terra_CorrectedReflectance_Bands721"


def fetch(url: str, tries: int = 4) -> bytes:
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=240) as r:
                return r.read()
        except Exception as ex:                              # the map service answers 5xx now and then
            if k == tries - 1:
                raise
            time.sleep(3 + 4 * k)
            print("   retry", str(ex)[:70], flush=True)
    return b""


def gibs(layer: str, day: str, box: tuple, px: tuple) -> Image.Image:
    w, s, e, n = box
    return Image.open(io.BytesIO(fetch(GIBS.format(layer, mx(w), my(s), mx(e), my(n), px[0], px[1], day)))).convert("RGB")


def days_of(year: int) -> list:
    d, e = date.fromisoformat(f"{year}-{WINDOW[0]}"), date.fromisoformat(f"{year}-{WINDOW[1]}")
    out = []
    while d <= e:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def score(im: Image.Image) -> tuple:
    a = np.asarray(im).astype(np.int16)
    hi, lo = a.max(axis=2), a.min(axis=2)
    return round(float((a.sum(axis=2) < 12).mean()), 4), round(float(((lo > 150) & (hi - lo < 40)).mean()), 4)


def _probe(job):
    name, layer, day = job
    path = OUT / "probe" / f"{name}_{layer}_{day}.jpg"
    try:
        if not path.exists():
            gibs(layer, day, FRAMES[name]["box"], (270, 480)).save(path, quality=88)
        return (name, layer, day) + score(Image.open(path).convert("RGB"))
    except Exception as ex:
        print("   probe failed", name, day, str(ex)[:60], flush=True)
        return (name, layer, day, 1.0, 1.0)


def probe(names: tuple = ("ne", "sea", "south")) -> None:
    (OUT / "probe").mkdir(parents=True, exist_ok=True)
    for name in names:
        years = SINGLE.get(name, YEARS)
        jobs = [(name, layers(y)[0], d) for y in years for d in days_of(y)]
        with ThreadPoolExecutor(6) as ex:
            rows = list(ex.map(_probe, jobs))
        df = pd.DataFrame(rows, columns=["frame", "layer", "day", "nodata", "cloud"])
        df.to_csv(OUT / f"probe_{name}.csv", index=False)
        print(f"probe {name}: {len(df)} days scored; clear days (no gap, cloud < 5 %) per year:",
              {int(y): int(((g.nodata < 0.002) & (g.cloud < 0.05)).sum()) for y, g in df.groupby(df.day.str[:4])}, flush=True)


def best(name: str, year: int, n: int = N_BEST) -> list:
    """The clearest days of a year's window: no swath gap, the least cloud."""
    df = pd.read_csv(OUT / f"probe_{name}.csv")
    g = df[(df.day.str[:4] == str(year)) & (df.nodata < 0.002)].sort_values("cloud")
    return list(g.day.head(n))


def _day(job):
    name, layer, day = job
    path = OUT / "days" / f"{name}_{layer}_{day}.jpg"
    if not path.exists():
        gibs(layer, day, FRAMES[name]["box"], FRAMES[name]["px"]).save(path, quality=95, subsampling=0)
    return path


def year_picture(name: str, year: int, n: int = N_BEST) -> dict:
    """The median of the clearest days, per pixel and band: true colour and the infrared composite."""
    (OUT / "days").mkdir(parents=True, exist_ok=True)
    tc, ir = layers(year)
    days = best(name, year, n)
    assert len(days) >= 3, (name, year, "fewer than three clear days")
    with ThreadPoolExecutor(4) as ex:
        paths = list(ex.map(_day, [(name, layer, d) for layer in (tc, ir) for d in days]))
    k = len(days)
    for kind, group in (("tc", paths[:k]), ("ir", paths[k:])):
        stack = np.stack([np.asarray(Image.open(p).convert("RGB")) for p in group])
        Image.fromarray(np.median(stack, axis=0).astype(np.uint8)).save(OUT / f"{name}_{year}_{kind}.jpg", quality=95, subsampling=0)
    return dict(frame=name, year=year, days=days, sensor=tc.split("_Corrected")[0])


def pictures() -> None:
    log = []
    for name in ("ne", "sea", "south"):
        for y in SINGLE.get(name, YEARS):
            if (OUT / f"{name}_{y}_ir.jpg").exists() and (OUT / f"{name}_{y}_tc.jpg").exists():
                continue
            r = year_picture(name, y)
            log.append(r)
            print("picture", r, flush=True)
    old = json.loads((OUT / "pictures.json").read_text()) if (OUT / "pictures.json").exists() else []
    keep = {(r["frame"], r["year"]): r for r in old + log}
    (OUT / "pictures.json").write_text(json.dumps(sorted(keep.values(), key=lambda r: (r["frame"], r["year"])), indent=1))


def wide() -> None:
    """The map of the rivers: NASA Blue Marble with shaded relief and bathymetry (public domain)."""
    path = OUT / "wide.jpg"
    if path.exists():
        return
    w, s, e, n = FRAMES["wide"]["box"]
    px = FRAMES["wide"]["px"]
    url = GIBS_STATIC.format("BlueMarble_ShadedRelief_Bathymetry", mx(w), my(s), mx(e), my(n), px[0], px[1])
    Image.open(io.BytesIO(fetch(url))).convert("RGB").save(path, quality=94, subsampling=0)
    print("saved", path.name)


def natural_earth(kind: str, name: str) -> Path:
    folder = OUT / "ne"
    folder.mkdir(parents=True, exist_ok=True)
    shp = folder / f"{name}.shp"
    if not shp.exists():
        z = zipfile.ZipFile(io.BytesIO(fetch(NE_URL.format(kind, name))))
        for i in z.infolist():
            if Path(i.filename).suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
                (folder / Path(i.filename).name).write_bytes(z.read(i))
    return shp


def lines() -> None:
    """The Volga, the Kama and the Ural; the land borders of the five coastal states and their neighbours in the frames."""
    import shapefile
    from shapely.geometry import LineString, MultiLineString, box as sbox, shape
    from shapely.ops import linemerge, unary_union
    rv = shapefile.Reader(str(natural_earth("physical", "ne_10m_rivers_lake_centerlines")))
    fields = [f[0] for f in rv.fields[1:]]
    rivers = {}
    for s in rv.iterShapeRecords():
        rec = dict(zip(fields, s.record))
        nm = (rec.get("name_en") or rec.get("name") or "").strip()
        if nm in ("Volga", "Kama", "Ural", "Akhtuba"):
            g = shape(s.shape.__geo_interface__)
            rivers.setdefault(nm, []).extend([list(l.coords) for l in getattr(g, "geoms", [g])])
    out = {}
    for nm, parts in rivers.items():
        merged = linemerge(MultiLineString(parts)) if len(parts) > 1 else LineString(parts[0])
        pieces = [merged] if isinstance(merged, LineString) else list(merged.geoms)
        out[nm.lower()] = [[(round(x, 4), round(y, 4)) for x, y in p.coords] for p in sorted(pieces, key=lambda p: -p.length)]
        print(f"river {nm}: {len(pieces)} piece(s), {sum(len(p.coords) for p in pieces)} points, "
              f"lat {min(y for p in pieces for _, y in p.coords):.2f} to {max(y for p in pieces for _, y in p.coords):.2f}")
    bd = shapefile.Reader(str(natural_earth("cultural", "ne_10m_admin_0_boundary_lines_land")))
    w, s, e, n = FRAMES["wide"]["box"]
    area = sbox(w - 1, s - 1, e + 1, n + 1)
    borders = []
    for sh in bd.iterShapes():
        g = shape(sh.__geo_interface__).intersection(area)
        for l in getattr(g, "geoms", [g]):
            if isinstance(l, LineString) and l.length > 0.05:
                borders.append([(round(x, 4), round(y, 4)) for x, y in l.coords])
    print(f"borders: {len(borders)} pieces, {sum(len(b) for b in borders)} points")
    cn = shapefile.Reader(str(natural_earth("cultural", "ne_10m_admin_0_countries")))
    cf = [f[0] for f in cn.fields[1:]]
    iran = None
    for sr in cn.iterShapeRecords():
        if dict(zip(cf, sr.record))["ADM0_A3"] == "IRN":
            g = shape(sr.shape.__geo_interface__)
            big = max(getattr(g, "geoms", [g]), key=lambda p: p.area)
            iran = [(round(x, 3), round(y, 3)) for x, y in big.exterior.simplify(0.01).coords]
    assert out.get("volga") and borders and iran
    (OUT / "lines.json").write_text(json.dumps(dict(rivers=out, borders=borders, iran=iran)))


# ---------------------------------------------------------------- CASPCOM's catalogues

RIVERS = dict(volga="VOLGA_V_.xlsx", ural="URAL_V_.xlsx", terek="TEREK_V_.xlsx", sulak="SULAK_V_.xlsx", kura="KURA_V_.xlsx",
              sefidrud="SEFIDRUD_V_.xlsx", haraz="HARAZ_V_.xlsx", chalus="CHALOOS_V_.xlsx", polrud="POLRUD_V_.xlsx")
MONTHS = [f"m{i}" for i in range(1, 13)]


def _num(v) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", ".").replace("−", "-"))
    except ValueError:
        return float("nan")


def _rows(path: Path) -> list:
    if path.suffix == ".xls":
        import xlrd                                          # not in the reel's environment: any Python that has it
        sh = xlrd.open_workbook(str(path)).sheet_by_index(0)
        return [sh.row_values(r) for r in range(sh.nrows)]
    import openpyxl
    return [list(r) for r in openpyxl.load_workbook(path, data_only=True).worksheets[0].iter_rows(values_only=True)]


def _table(path: Path) -> tuple:
    rows = _rows(path)
    head = " | ".join(str(c) for r in rows[:12] for c in r if c not in ("", None))
    data = []
    for r in rows:
        y = _num(r[0]) if r and r[0] not in ("", None) else float("nan")
        if 1800 < y < 2100:
            data.append([int(y)] + [_num(v) for v in r[1:13]] + [_num(r[13]) if len(r) > 13 else float("nan")])
    df = pd.DataFrame(data, columns=["year"] + MONTHS + ["printed"]).set_index("year")
    df["n"] = df[MONTHS].notna().sum(axis=1)
    return df, head


def caspcom() -> None:
    """Download the two catalogues and write every gauge and river as a CSV (monthly values, complete years marked)."""
    base = OUT / "caspcom"
    for sub in ("raw", "level", "flow"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    for zname, sub in (("Sea-Level-EN.zip", "level"), ("Flow-EN.zip", "flow")):
        raw = base / "raw" / zname
        if not raw.exists():
            raw.write_bytes(fetch(CASPCOM + zname))
        z = zipfile.ZipFile(raw)
        for i in z.infolist():
            if not i.is_dir():
                (base / sub / Path(i.filename).name.replace(" ", "_")).write_bytes(z.read(i))
    flows = {}
    for name, fname in RIVERS.items():
        df, _ = _table(base / "flow" / fname)
        df["sum12"] = df[MONTHS].sum(axis=1, min_count=12)   # km3 a year, complete years only
        df.to_csv(base / f"flow_{name}.csv")
        flows[name.capitalize()] = df["sum12"]
    pd.DataFrame(flows).to_csv(base / "flow_annual.csv")
    levels, meta = {}, []
    for path in sorted((base / "level").glob("*_av.xls*")):
        df, head = _table(path)
        df["mean12"] = df[MONTHS].mean(axis=1).where(df.n == 12)   # cm above the post's datum, complete years only
        g = path.stem.replace("_av", "")
        df.to_csv(base / f"level_{g}.csv")
        levels[g] = df["mean12"]
        datum = re.search(r"datum equals to\s*_*\s*([-−]?\d+[.,]?\d*)", head)
        meta.append(dict(gauge=g, datum=datum.group(1) if datum else "", system="Baltic" if "Baltic" in head else "Persian Gulf" if "Persian" in head else "",
                         first=int(df.index.min()), complete_years=int(df.mean12.notna().sum())))
    pd.DataFrame(levels).to_csv(base / "level_annual_cm.csv")
    pd.DataFrame(meta).to_csv(base / "level_gauges.csv", index=False)
    print("caspcom:", len(flows), "rivers,", len(levels), "gauges")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if "--caspcom" in sys.argv:
        caspcom()
        return
    if "--probe" in sys.argv:
        probe()
        return
    pictures()
    wide()
    lines()


if __name__ == "__main__":
    main()
