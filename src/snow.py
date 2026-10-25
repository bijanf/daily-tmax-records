"""SNOW BECOMES RAIN: how much of the highlands' precipitation falls as snow, every water year
since ERA5 begins.

ERA5 monthly means (get_snow.py; Hersbach et al. 2020) over the highlands from Turkey to the
edge of Tibet: land cells (land-sea mask > 0.5) between 25-43 N and 26-80 E standing at least
1,000 m high, which takes in the Anatolian and Iranian plateaus, the Zagros, Alborz, Caucasus,
Hindu Kush and Pamir and leaves out the lowland deserts and the Mesopotamian plain. Snowfall
and total precipitation are monthly means of daily totals (m of water); times are stamped at
06:00 on the first of the month. Water years run October to September (water year 2026 =
October 2025 to September 2026) and are summed cell by cell, then averaged over the area
(cos-latitude weights). The snow share of a water year is the area's snowfall over its total
precipitation, both in water equivalent: of every 100 litres that fell, how many came as snow.

    python -I src/snow.py                 # the shares, decade by decade, and the checks
"""

from __future__ import annotations

import functools
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
SNOW = ROOT / "data" / "snow"
HIGH = 1000.0                               # m: the highlands
G = 9.80665


def grid(da):
    """Latitudes and longitudes in float64 to 4 decimals: ERA5-Land's invariants come in float32,
    a few millionths of a degree off its fields, and would not align with them."""
    return da.assign_coords(latitude=da["latitude"].astype("float64").round(4),
                            longitude=da["longitude"].astype("float64").round(4))


def field(var: str, short: str) -> xr.DataArray:
    """A variable over all downloaded months, the time floored to the month."""
    parts = [xr.open_dataset(p)[short] for p in sorted(SNOW.glob(f"era5_{var}_*.nc"))]
    da = xr.concat(parts, "valid_time").sortby("valid_time")
    da = da.assign_coords(valid_time=da["valid_time"].values.astype("datetime64[M]").astype("datetime64[ns]"))
    da = da.isel(valid_time=~da.get_index("valid_time").duplicated())
    return grid(da.drop_vars([c for c in ("expver", "number") if c in da.coords]).rename(valid_time="time"))


def use(folder: str) -> None:
    """Read the ERA5 files of another download (get_snow.py --region): "snow" or "snow_alps"."""
    global SNOW
    SNOW = ROOT / "data" / folder
    masks.cache_clear()
    series.cache_clear()


@functools.lru_cache(maxsize=8)
def shape(name: str):
    """The outline of a country (Natural Earth 1:50 m, by its ADMIN name, e.g. "Iran") or of a
    mountain range (Natural Earth 1:10 m geography regions, by NAME, e.g. "ALPS")."""
    import cartopy.io.shapereader as shp

    for res, cat, layer, key in (("50m", "cultural", "admin_0_countries", "ADMIN"),
                                 ("10m", "physical", "geography_regions_polys", "NAME")):
        for r in shp.Reader(shp.natural_earth(res, cat, layer)).records():
            if r.attributes[key] == name:
                return r.geometry
    raise KeyError(name)


def within(name: str, like: xr.DataArray) -> xr.DataArray:
    """True where a cell's centre lies inside a country or range (shape())."""
    from shapely.geometry import Point
    from shapely.prepared import prep

    outline = prep(shape(name))
    lon, lat = np.meshgrid(like["longitude"].values, like["latitude"].values)
    inside = np.array([outline.contains(Point(x, y)) for x, y in zip(lon.ravel(), lat.ravel())]).reshape(lon.shape)
    return xr.DataArray(inside, coords={"latitude": like["latitude"], "longitude": like["longitude"]},
                        dims=("latitude", "longitude"))


@functools.lru_cache(maxsize=8)
def masks(high: float = HIGH, region: str | None = None) -> tuple:
    """Land, the land counted (at least `high` m, inside `region` if given), terrain height (m)."""
    inv = grid(xr.open_dataset(SNOW / "era5_invariant.nc"))
    lsm = inv["lsm"].isel(valid_time=0, drop=True)
    height = inv["z"].isel(valid_time=0, drop=True) / G
    land = lsm > 0.5
    counted = land & (height >= high)
    if region:
        counted = counted & within(region, height)
    return land, counted, height


def water_years(da: xr.DataArray) -> xr.DataArray:
    """Monthly means of daily totals (m) -> water-year totals (mm), complete years only."""
    mm = da * da["time"].dt.days_in_month * 1000
    wy = (mm["time"].dt.year + (mm["time"].dt.month >= 10)).rename("wy")
    months = pd.Series(1, index=wy.values).groupby(level=0).sum()
    return mm.groupby(wy).sum("time").sel(wy=months.index[months == 12].values)


def area_mean(da: xr.DataArray, mask: xr.DataArray) -> pd.Series:
    w = np.cos(np.deg2rad(da["latitude"])) * mask
    return (da * w).sum(("latitude", "longitude")).to_series() / float(w.sum())


@functools.lru_cache(maxsize=8)
def series(high: float = HIGH, region: str | None = None) -> pd.DataFrame:
    """Water year -> snowfall, precipitation (mm, area mean), snow share (%), cold-season
    (November to March) 2 m temperature (°C), over the land counted by masks()."""
    _, mask, _ = masks(high, region)
    sf, tp = water_years(field("snowfall", "sf")), water_years(field("total_precipitation", "tp"))
    t2 = field("2m_temperature", "t2m") - 273.15
    cold = t2.where(t2["time"].dt.month.isin([11, 12, 1, 2, 3]), drop=True)
    season = cold["time"].dt.year + (cold["time"].dt.month >= 11)
    cold = cold.groupby(season.rename("wy")).mean("time")
    out = pd.DataFrame({"snow": area_mean(sf, mask), "precip": area_mean(tp, mask)})
    out["share"] = 100 * out["snow"] / out["precip"]
    out["cold_t2m"] = area_mean(cold, mask).reindex(out.index)
    return out


def cru_winter(region: str, y0: int, y1: int, z0: int, z1: int) -> float:
    """How much warmer November-March was in z0-z1 than in y0-y1 over a region (°C), from the
    stations of CRU TS 4.10 (0.5 deg; data/water/cru_ts4.10.<decade>.tmp.dat.nc). A season is
    named by its March."""
    import glob

    t = xr.open_mfdataset(sorted(glob.glob(str(ROOT / "data" / "water" / "cru_ts4.10.*.tmp.dat.nc"))),
                          combine="by_coords")["tmp"]
    t = t.rename(lat="latitude", lon="longitude")
    inside = within(region, t.isel(time=0))
    t = t.where(inside, drop=True)
    cold = t.where(t["time"].dt.month.isin([11, 12, 1, 2, 3]), drop=True)
    season = (cold["time"].dt.year + (cold["time"].dt.month >= 11)).rename("wy")
    w = np.cos(np.deg2rad(cold["latitude"])) * inside.sel(latitude=cold["latitude"], longitude=cold["longitude"])
    s = ((cold.groupby(season).mean("time") * w).sum(("latitude", "longitude")) / w.sum()).compute().to_series()
    return float(s.loc[z0:z1].mean() - s.loc[y0:y1].mean())


def spring_bands(region: str, bands, then=(1951, 1980), now=(2017, 2026), months=(3, 4)) -> pd.DataFrame:
    """The snowpack in spring (ERA5-Land snow water equivalent, mean of March and April, mm) by
    elevation band (the grid cell's mean height): band -> 1951-80, 2017-26, change (%), cells.
    Without the cells still under snow in September (over 10 mm on average in either period),
    mostly the model's glaciers: ERA5-Land holds snow on them all year, up to its 10 m cap, so
    they hardly change."""
    _, inside, height = masks(0.0, region)
    swe = field("snow_depth_water_equivalent", "sd") * 1000
    september = swe.where(swe["time"].dt.month == 9, drop=True)
    lasting = [september.sel(time=slice(str(y[0]), str(y[1]))).mean("time") for y in (then, now)]
    assert not any((inside & s.isnull()).any() for s in lasting), "September snow missing"
    inside = inside & (lasting[0] <= 10) & (lasting[1] <= 10)
    spring = swe.where(swe["time"].dt.month.isin(list(months)), drop=True)
    spring = spring.groupby(spring["time"].dt.year.rename("yr")).mean("time")
    years = spring["yr"].values
    assert {*range(then[0], then[1] + 1), *range(now[0], now[1] + 1)} <= set(years), "a spring is missing"
    w = np.cos(np.deg2rad(spring["latitude"]))
    rows = []
    for lo, hi in bands:
        m = inside & (height >= lo) & (height < hi)
        def mean(y, m=m):
            v = spring.sel(yr=slice(*y)).mean("yr").where(m)
            return float((v * w).sum() / (w * v.notnull()).sum())
        a, b = mean(then), mean(now)
        rows.append(dict(lo=lo, hi=hi, then=a, now=b, change=100 * (b / a - 1), cells=int(m.sum())))
    return pd.DataFrame(rows)


def maps(y0: int, y1: int, high: float = HIGH) -> xr.DataArray:
    """Snow share (%) of each cell over the water years y0-y1."""
    sf, tp = water_years(field("snowfall", "sf")), water_years(field("total_precipitation", "tp"))
    sl = slice(y0, y1)
    return 100 * sf.sel(wy=sl).sum("wy") / tp.sel(wy=sl).sum("wy")


def main() -> None:
    for high in (0.0, HIGH, 2000.0):
        s = series(high)
        print(f"== land {'all' if not high else f'>= {high:.0f} m'}: water years {s.index[0]}-{s.index[-1]}")
        d = s.groupby((s.index - 1) // 10 * 10 + 1)[["snow", "precip", "share", "cold_t2m"]].mean().round(1)
        print(d.to_string())
        early, late = s.loc[1951:1980], s.loc[2017:2026]
        print("1951-80 vs 2017-26: share %.1f -> %.1f %%, snow %.0f -> %.0f mm, precip %.0f -> %.0f mm, cold T %.1f -> %.1f"
              % (early.share.mean(), late.share.mean(), early.snow.mean(), late.snow.mean(), early.precip.mean(),
                 late.precip.mean(), early.cold_t2m.mean(), late.cold_t2m.mean()))
        b = np.polyfit(s.index, s.share, 1)[0] * 10
        print(f"trend {b:+.2f} %-points per decade; per °C of cold-season warming "
              f"{np.polyfit(s.cold_t2m, s.share, 1)[0]:+.1f} %-points")


if __name__ == "__main__":
    main()
