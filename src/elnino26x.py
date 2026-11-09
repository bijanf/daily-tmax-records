"""THE NUMBERS OF THE EL NIÑO EXPLAINER, PART 1 (elnino26x_fa): what El Niño is, how strong this one is, why a few
strong events cannot tell Iran's future, and where the heat of global warming goes.

Every number of the reel's new scenes is computed or asserted here and written to data/enso/elnino26x/numbers.json
(the film reads it back and asserts it again). The scenes it shares with the narrated reel of 8 Nov (the 26 autumns,
the 123 %, the 22 winters) keep their numbers from src/elnino26s.py and src/enso.py.

- Weekly Niño indices: NOAA CPC's weekly OISST v2.1 file (wksst9120.for: weeks centred on Wednesdays since 3 Sep 1981,
  anomalies against 1991-2020), fetched to data/enso/wksst9120.for. The record: the highest weekly Niño-3.4 anomaly of
  each ENSO year (June to May): 2026 +3.4 °C (weeks of 21 and 28 Oct 2026) above 2015 +3.0, 1982 +2.6, 1997 +2.3.
- ONI and RONI (NOAA CPC, data/enso/oni.ascii.txt, RONI.ascii.txt): ASO 2026 +2.46, the highest ASO since 1950
  (1997 2.04, 2015 2.02); RONI +1.97, second after 1997 (2.07).
- The strong El Niño autumns (ONI of October-December at least +1.5): 1965, 1972, 1982, 1997, 2015, 2023, and Iran's
  autumn rain in each (CRU TS 4.10, src/enso.py) as a percent of the 1951-2024 mean (60.0 mm).
- Two weeks of the tropical Pacific (NOAA OISST v2.1 daily SST from NOAA PSL's THREDDS, minus PSL's 1991-2020 daily
  climatology, the base of NOAA's Niño indices): 1-7 Nov 2025 and 1-7 Nov 2026 (preliminary), 120 E to 80 W,
  30 S to 30 N. Their Niño-3.4 box means (-0.65 and +3.29 °C) cross-check CPC's weekly values (-0.6 and +3.3).
  (oisst() keeps the CoastWatch ERDDAP route, 1971-2000 base, for reference only: not on screen.)

    python -I src/elnino26x.py      fetches what is missing, computes, asserts, writes numbers.json and prints it
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import enso  # noqa: E402
import onebit  # noqa: E402

DATA = onebit.ROOT / "data" / "enso" / "elnino26x"
WEEKLY = onebit.ROOT / "data" / "enso" / "wksst9120.for"
WEEKLY_URL = "https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for"
ERDDAP = "https://coastwatch.pfeg.noaa.gov/erddap/griddap"
WEEKS = dict(ago=("ncdcOisst21Agg_LonPM180", "2025-11-01", "2025-11-07"),
             now=("ncdcOisst21NrtAgg_LonPM180", "2026-11-01", "2026-11-07"))
NINO34 = dict(lon0=190.0, lon1=240.0, lat0=-5.0, lat1=5.0)          # 170 W to 120 W, 5 S to 5 N
PATH_YEARS = (1982, 1997, 2015, 2023, 2026)                         # the lines of the record chart
STRONG_AT = 1.5                                                     # ONI of OND: a strong El Niño autumn
MON = {m: i for i, m in enumerate("JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split(), 1)}
# what the reel shows, asserted against the data (a change in a file stops the build)
EXPECT = dict(peak_2026=3.4, peak_2015=3.0, peak_1982=2.6, peak_1997=2.3, peak_2023=2.1, last_week="04NOV2026",
              last_n34=3.3, oni_aso=2.46, roni_aso=1.97, roni_first=(1997, 2.07),
              strong=((1965, 69), (1972, 101), (1982, 191), (1997, 113), (2015, 111), (2023, 67)))


def fetch(url: str, path: Path, tries: int = 6) -> Path:
    """GET url into path (a .part file renamed when complete), with a pause and a retry on a server error."""
    path.parent.mkdir(parents=True, exist_ok=True)
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=900) as r:
                part = path.with_suffix(path.suffix + ".part")
                part.write_bytes(r.read())
            part.rename(path)
            return path
        except Exception as e:                      # 503 from ERDDAP when it is busy
            if k == tries - 1:
                raise
            print(f"retry {k + 1} after {e}")
            time.sleep(20 * (k + 1))
    return path


def weekly() -> list:
    """The CPC weekly file as rows (date as 'DDMONYYYY', year, month, day, n12, n3, n34, n4): the anomalies."""
    if not WEEKLY.exists():
        fetch(WEEKLY_URL, WEEKLY)
    pat = re.compile(r"\s*(\d\d)([A-Z]{3})(\d{4})" + r"\s+(\d+\.\d)\s*(-?\d+\.\d)" * 4)
    rows = []
    for line in WEEKLY.read_text().splitlines():
        m = pat.match(line)
        if m:
            g = m.groups()
            v = [float(x) for x in g[3:]]
            rows.append(dict(date=f"{g[0]}{g[1]}{g[2]}", year=int(g[2]), month=MON[g[1]], day=int(g[0]),
                             n12=v[1], n3=v[3], n34=v[5], n4=v[7]))
    assert rows[0]["date"] == "02SEP1981", rows[0]
    return rows


def enso_year(r: dict) -> int:
    """The ENSO year of a week: June to May, named by its June."""
    return r["year"] if r["month"] >= 6 else r["year"] - 1


def peaks(rows: list, key: str = "n34") -> dict:
    """The highest weekly anomaly of each ENSO year since 1982 (the first full year), with its week."""
    best = {}
    for r in rows:
        y = enso_year(r)
        if y >= 1982 and (y not in best or r[key] > best[y][0]):
            best[y] = (r[key], r["date"])
    return best


def paths(rows: list) -> dict:
    """Each chart year's weekly Niño-3.4 anomaly from 1 June to 31 January, as (days after 1 June, anomaly)."""
    import datetime as dt
    out = {}
    for y in PATH_YEARS:
        t0 = dt.date(y, 6, 1)
        pts = []
        for r in rows:
            d = dt.date(r["year"], r["month"], r["day"])
            if t0 <= d <= dt.date(y + 1, 1, 31):
                pts.append(((d - t0).days, r["n34"]))
        out[y] = pts
    return out


def strong_autumns() -> list:
    """The El Niño autumns with ONI(OND) at least STRONG_AT, and Iran's autumn rain as % of the 1951-2024 mean."""
    au = enso.result("OND", STRONG_AT)
    rain = au["rain"]
    mean74 = float(np.mean([rain[y] for y in sorted(rain)]))
    o = enso.oni("oni").query("season == 'OND'").set_index("year")["oni"]
    out = []
    for y in sorted(au["years"]):
        out.append(dict(year=int(y), oni=round(float(o[y]), 2), mm=round(float(rain[y]), 1),
                        pct=int(round(100 * rain[y] / mean74)), wetter=bool(au["wetter"][y])))
    return out, round(mean74, 1)


def oisst(tag: str) -> dict:
    """One week of the OISST anomaly over the Pacific box (lon 120 E to 280 E ascending, lat ascending), the mean."""
    import xarray as xr
    ds, t0, t1 = WEEKS[tag]
    parts = []
    for la, lb, side in ((120.125, 179.875, "w"), (-179.875, -80.125, "e")):
        p = DATA / f"oisst_{tag}_{side}.nc"
        if not p.exists():
            q = f"anom[({t0}T12:00:00Z):1:({t1}T12:00:00Z)][(0.0):1:(0.0)][(-29.875):1:(29.875)][({la}):1:({lb})]"
            fetch(f"{ERDDAP}/{ds}.nc?" + urllib.parse.quote(q, safe="():,.-TZ"), p)
        a = xr.open_dataset(p)["anom"].squeeze("zlev", drop=True)
        parts.append(a.assign_coords(longitude=a.longitude % 360))
    full = xr.concat(parts, dim="longitude").sortby("longitude").sortby("latitude")
    days = [str(t)[:10] for t in full.time.values]
    assert len(days) == 7 and days[0] == t0 and days[-1] == t1, days
    lat, lon = full.latitude.values.astype(float), full.longitude.values.astype(float)
    mean = full.mean("time", skipna=True).values.astype(float)
    la = (lat >= NINO34["lat0"]) & (lat <= NINO34["lat1"])
    lo = (lon >= NINO34["lon0"]) & (lon <= NINO34["lon1"])
    sub = mean[np.ix_(la, lo)]
    w = np.cos(np.radians(lat[la]))[:, None] * np.ones((1, lo.sum()))
    ok = np.isfinite(sub)
    box = float((sub[ok] * w[ok]).sum() / w[ok].sum())
    return dict(days=days, lat=lat, lon=lon, mean=mean, nino34=round(box, 2), dataset=ds)


PSL = "https://psl.noaa.gov/thredds/dodsC/Datasets/noaa.oisst.v2.highres"
PSL_WEEKS = dict(ago=(2025, "2025-11-01", "2025-11-07"), now=(2026, "2026-11-01", "2026-11-07"))


def oisst91(tag: str) -> dict:
    """One week of OISST v2.1 over the Pacific box against the 1991-2020 daily climatology (the base of NOAA's
    Niño indices), from NOAA PSL's THREDDS (OPeNDAP subsets, cached): the mean of the week's SST minus the mean of
    the climatology's same seven days. lon 120 E to 280 E, lat 30 S to 30 N, both ascending."""
    import xarray as xr
    year, t0, t1 = PSL_WEEKS[tag]
    path = DATA / f"psl91_{tag}.nc"
    if not path.exists():
        box = dict(lat=slice(-29.875, 29.875), lon=slice(120.125, 279.875))
        sst = xr.open_dataset(f"{PSL}/sst.day.mean.{year}.nc")["sst"].sel(time=slice(t0, t1), **box).load()
        ltm = xr.open_dataset(f"{PSL}/sst.day.mean.ltm.1991-2020.nc", use_cftime=True)["sst"]
        days = [d for d in ltm.time.values if (d.month, d.day) >= (int(t0[5:7]), int(t0[8:])) and
                (d.month, d.day) <= (int(t1[5:7]), int(t1[8:]))]
        clim = ltm.sel(time=days, **box).load()
        assert sst.sizes["time"] == 7 and clim.sizes["time"] == 7, (sst.sizes, clim.sizes)
        out = xr.Dataset(dict(sst=sst.mean("time"), clim=clim.mean("time")))
        out.attrs.update(days=f"{t0}..{t1}", source=f"{PSL}/sst.day.mean.{year}.nc minus sst.day.mean.ltm.1991-2020.nc")
        DATA.mkdir(parents=True, exist_ok=True)
        out.to_netcdf(path)
    ds = xr.open_dataset(path)
    lat, lon = ds.lat.values.astype(float), ds.lon.values.astype(float)
    mean = (ds["sst"] - ds["clim"]).values.astype(float)
    la = (lat >= NINO34["lat0"]) & (lat <= NINO34["lat1"])
    lo = (lon >= NINO34["lon0"]) & (lon <= NINO34["lon1"])
    sub = mean[np.ix_(la, lo)]
    w = np.cos(np.radians(lat[la]))[:, None] * np.ones((1, lo.sum()))
    ok = np.isfinite(sub)
    box = float((sub[ok] * w[ok]).sum() / w[ok].sum())
    return dict(days=ds.attrs["days"], lat=lat, lon=lon, mean=mean, nino34=round(box, 2), dataset="PSL OISST v2.1")


def numbers() -> dict:
    rows = weekly()
    last = rows[-1]
    pk = peaks(rows)
    assert last["date"] == EXPECT["last_week"] and last["n34"] == EXPECT["last_n34"], last
    for y in (2026, 2015, 1982, 1997, 2023):
        assert pk[y][0] == EXPECT[f"peak_{y}"], (y, pk[y])
    ranked = sorted(pk.items(), key=lambda kv: -kv[1][0])
    assert ranked[0][0] == 2026 and ranked[1][0] == 2015, ranked[:3]
    pk3, pk12 = peaks(rows, "n3"), peaks(rows, "n12")
    o = enso.oni("oni")
    r = enso.oni("roni")
    aso = o.query("season == 'ASO'").sort_values("oni", ascending=False).reset_index(drop=True)
    raso = r.query("season == 'ASO'").sort_values("oni", ascending=False).reset_index(drop=True)
    assert (int(aso.year[0]), round(float(aso.oni[0]), 2)) == (2026, EXPECT["oni_aso"]), aso.head(3)
    assert (int(raso.year[0]), round(float(raso.oni[0]), 2)) == EXPECT["roni_first"], raso.head(3)
    assert (int(raso.year[1]), round(float(raso.oni[1]), 2)) == (2026, EXPECT["roni_aso"]), raso.head(3)
    allmax = o.sort_values("oni", ascending=False).reset_index(drop=True)
    pairs = {}                                            # classic ONI vs relative RONI, Aug-Oct, three big events
    for y in (1997, 2015, 2026):
        on = float(o.query("season == 'ASO' and year == @y").oni.iloc[0])
        ro = float(r.query("season == 'ASO' and year == @y").oni.iloc[0])
        pairs[str(y)] = dict(oni=round(on, 2), roni=round(ro, 2), gap=round(on - ro, 2))
    assert [(pairs[y]["oni"], pairs[y]["roni"]) for y in ("1997", "2015", "2026")] == \
        [(2.04, 2.07), (2.02, 1.8), (2.46, 1.97)], pairs
    strong, mean74 = strong_autumns()
    assert tuple((s["year"], s["pct"]) for s in strong) == EXPECT["strong"], strong
    assert mean74 == 60.0
    weeks = {k: oisst91(k) for k in PSL_WEEKS}            # the maps: against 1991-2020, as NOAA's indices
    assert abs(weeks["now"]["nino34"] - last["n34"]) <= 0.15, (weeks["now"]["nino34"], last["n34"])
    assert weeks["ago"]["nino34"] < -0.3, weeks["ago"]["nino34"]       # a year ago: cooler than usual (La Niña side)
    return dict(
        weekly=dict(source=WEEKLY_URL, base="1991-2020", last_week=last["date"], last_n34=last["n34"],
                    peaks_n34={str(y): v for y, v in sorted(pk.items())}, record_n34=dict(year=2026, value=pk[2026][0],
                    week=pk[2026][1], second=dict(year=2015, value=pk[2015][0], week=pk[2015][1])),
                    peak_n3_2026=pk3[2026], peak_n3_prev=max(v for y, v in pk3.items() if y != 2026),
                    peak_n12_2026=pk12[2026], peak_n12_prev=max(v for y, v in pk12.items() if y != 2026),
                    first_week=rows[0]["date"], years_of_record=2026 - 1981),
        paths={str(y): p for y, p in paths(rows).items()},
        oni=dict(aso_2026=EXPECT["oni_aso"], aso_rank=1, aso_next=[(int(aso.year[k]), round(float(aso.oni[k]), 2))
                 for k in (1, 2)], n_aso=len(aso), max_any=[(str(allmax.season[k]), int(allmax.year[k]),
                 round(float(allmax.oni[k]), 2)) for k in range(4)]),
        roni=dict(aso_2026=EXPECT["roni_aso"], aso_rank=2, aso_first=EXPECT["roni_first"]),
        pairs=pairs,
        strong=strong, strong_n=len(strong), strong_wetter=sum(s["wetter"] for s in strong), autumn_mean74=mean74,
        weeks={k: dict(days=v["days"], nino34_box=v["nino34"], dataset=v["dataset"], base="1991-2020 (PSL daily LTM)")
               for k, v in weeks.items()},
    )


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    nums = numbers()
    (DATA / "numbers.json").write_text(json.dumps(nums, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in nums.items() if k != "paths"}, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
