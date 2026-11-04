"""The winter NO2 layer over Tehran from Sentinel-5P, in numbers (onebit_air.py and onebit_score_air.py read it).

Sentinel-5P OFFL tropospheric NO2 (data/air/granules, made by get_air.py), valid pixels only: qa >= 0.75. The
Tehran-Karaj box (51.0-51.8 E, 35.4-36.0 N) gives the ratio: a Jalali month's pixel mean over the summer reference's
pixel mean (Tir to Shahrivar 1405: 22 June to 22 September 2026, pooled). The winter state is Azar to Bahman 1404
(22 November 2025 to 19 February 2026), pooled. The four season pairs of the fact check (two winters, two summers,
its Gregorian DJF and JJA) are reproduced here and must agree with its table (data/air/ratio_table_fact.csv).

The film's year is Aban 1404 to Mehr 1405 (23 October 2025 to 22 October 2026): the latest complete Jalali year.

    python -I src/air.py        # the fact check reproduced, the monthly table, the checks
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "air"
K = 6.02214e19 / 1e15                            # mol/m2 -> 1e15 molec/cm2 (as the fact check)
QA_MIN = 0.75
KEEP = (50.3, 34.2, 52.4, 37.2)                  # W, S, E, N: the pixels read (frame and margin)
TEHRAN_KARAJ = (51.0, 35.4, 51.8, 36.0)          # W, S, E, N: the box of the ratio
CORE = (51.25, 35.55, 51.55, 35.85)              # city core (fact check)
WIDE = (50.6, 35.2, 52.2, 36.2)                  # wider metro and Alborz foothills (fact check)
FACT_SEASONS = {"DJF2425": ("2024-12-01", "2025-02-28"), "DJF2526": ("2025-12-01", "2026-02-28"),
                "JJA2025": ("2025-06-01", "2025-08-31"), "JJA2026": ("2026-06-01", "2026-08-31")}
WINDOW = [(2025, 11), (2025, 12)] + [(2026, m) for m in range(1, 11)]
# Jalali months (Persian solar calendar): the film's dial and the comparison
JALALI_NAMES = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
DIAL_JK = [f"1404-{m:02d}" for m in range(8, 13)] + [f"1405-{m:02d}" for m in range(1, 8)]   # Aban 1404 to Mehr 1405
REF_JK = ("1405-04", "1405-05", "1405-06")      # the summer reference: Tir to Shahrivar 1405 (22 Jun-22 Sep 2026)
WINTER_JK = ("1404-09", "1404-10", "1404-11")   # the winter state: Azar to Bahman 1404 (22 Nov 2025-19 Feb 2026)
BIN = 0.04                                       # deg: the field's bins (fact check)
SMOOTH = 0.8                                     # bins: the field's smoothing (fact check)
CNT_MIN = 3                                      # a bin needs this many pixels

# frame geometry (the fact check's frame: 171 km across 1080 px, centred on Tehran)
W, H = 1080, 1920
LAT_C, LON_C, KMPP = 35.70, 51.35, 0.1583
LON_L = LON_C - (W / 2) * KMPP / (111.32 * np.cos(np.radians(LAT_C)))
LON_R = LON_C + (W / 2) * KMPP / (111.32 * np.cos(np.radians(LAT_C)))
LAT_T = LAT_C + (H / 2) * KMPP / 110.574
LAT_B = LAT_C - (H / 2) * KMPP / 110.574


def jalali(d: str) -> tuple:
    """Gregorian date 'YYYY-MM-DD' to the Persian solar (Jalali) date (jy, jm, jd): the 2820-year arithmetic rule
    (as in the jalaali-js conversion; exact for the years of the film)."""
    gy, gm, gd = (int(v) for v in d.split("-"))
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 + gd + g_d_m[gm - 1]
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    return jy, jm, jd


def jkey(d: str) -> str:
    jy, jm, _ = jalali(d)
    return f"{jy}-{jm:02d}"


def _check_calendar() -> None:
    """The Jalali boundaries of the film, asserted with the converter (Aban 1404 to Mehr 1405)."""
    assert jalali("2025-03-21") == (1404, 1, 1) and jalali("2026-03-21") == (1405, 1, 1)
    spans = {"1404-08": ("2025-10-23", "2025-11-21"), "1404-09": ("2025-11-22", "2025-12-21"),
             "1404-10": ("2025-12-22", "2026-01-20"), "1404-11": ("2026-01-21", "2026-02-19"),
             "1404-12": ("2026-02-20", "2026-03-20"), "1405-01": ("2026-03-21", "2026-04-20"),
             "1405-02": ("2026-04-21", "2026-05-21"), "1405-03": ("2026-05-22", "2026-06-21"),
             "1405-04": ("2026-06-22", "2026-07-22"), "1405-05": ("2026-07-23", "2026-08-22"),
             "1405-06": ("2026-08-23", "2026-09-22"), "1405-07": ("2026-09-23", "2026-10-22")}
    for jk, (a, b) in spans.items():
        assert jkey(a) == jk and jkey(b) == jk, (jk, a, b, jalali(a), jalali(b))
        pa = str(np.datetime64(a) - np.timedelta64(1, "D"))
        nb = str(np.datetime64(b) + np.timedelta64(1, "D"))
        assert jkey(pa) != jk and jkey(nb) != jk, (jk, pa, nb)
    assert list(spans) == DIAL_JK
    assert jalali("2025-11-25") == (1404, 9, 4) and jalali("2026-01-26") == (1404, 11, 6)   # the school closures


_check_calendar()


def lonlat_of(px, py):
    lon = LON_L + (np.asarray(px) + 0.5) * (LON_R - LON_L) / W
    lat = LAT_T - (np.asarray(py) + 0.5) * (LAT_T - LAT_B) / H
    return lon, lat


def px_of(lon: float, lat: float) -> tuple:
    return (lon - LON_L) / (LON_R - LON_L) * W, (LAT_T - lat) / (LAT_T - LAT_B) * H


def _granule(gid: str):
    """One granule's valid pixels inside KEEP: (lat, lon, no2 in 1e15 molec/cm2), or None if not cached."""
    npz = DATA / "granules" / f"{gid}.npz"
    if not npz.exists():
        return None
    z = np.load(npz)
    lat, lon = z["lat"].astype(np.float64), z["lon"].astype(np.float64)
    w, s, e, n = KEEP
    m = (lon > w) & (lon < e) & (lat > s) & (lat < n) & (z["qa"] >= QA_MIN)
    return lat[m], lon[m], z["no2"][m].astype(np.float64) * K


def records(rows: list) -> pd.DataFrame:
    """The valid pixels of the given items (OFFL, dicts with id and datetime), one row per pixel."""
    parts = []
    for it in rows:
        g = _granule(it["id"]) if it["mode"] == "OFFL" else None
        if g is None or g[0].size == 0:
            continue
        lat, lon, no2 = g
        day = it["datetime"][:10]
        parts.append(pd.DataFrame(dict(day=day, ym=it["datetime"][:7], jk=jkey(day), lat=lat, lon=lon, no2=no2)))
    cols = ["day", "ym", "jk", "lat", "lon", "no2"]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=cols)


def window_rows() -> list:
    return json.loads((DATA / "items_window.json").read_text())


def fact_rows(season: str) -> list:
    s, e = FACT_SEASONS[season]
    rows = json.loads((DATA / f"items_fact_{season}.json").read_text())
    return [r for r in rows if r["datetime"][:10] >= s and r["datetime"][:10] <= e]


def box_stats(df: pd.DataFrame, box: tuple) -> dict:
    w, s, e, n = box
    d = df[(df.lon > w) & (df.lon < e) & (df.lat > s) & (df.lat < n)]
    daily = d.groupby("day").no2.mean()
    return dict(pix_mean=d.no2.mean(), pix_median=d.no2.median(), n_pix=len(d), n_days=int(daily.size),
                day_mean=daily.mean(), day_median=daily.median())


def fact_check() -> pd.DataFrame:
    """The fact check's table, reproduced from the cached granules and asserted against its CSV."""
    rows = []
    for season in FACT_SEASONS:
        df = records(fact_rows(season))
        for name, box in (("core0.15", CORE), ("TehranKaraj", TEHRAN_KARAJ), ("wide", WIDE)):
            rows.append(dict(box=name, season=season, **box_stats(df, box)))
    table = pd.DataFrame(rows)
    ref = pd.read_csv(DATA / "ratio_table_fact.csv")
    merged = table.merge(ref, on=["box", "season"], suffixes=("", "_fact"))
    assert len(merged) == len(ref) == len(table), (len(merged), len(ref), len(table))
    for col in ("pix_mean", "pix_median", "n_pix", "n_days", "day_mean", "day_median"):
        scale = max(1.0, float(np.abs(merged[f"{col}_fact"]).max()))
        diff = float(np.abs(merged[col] - merged[f"{col}_fact"]).max())
        assert diff < 1e-6 * scale, (col, diff)
    return table


def pairs(table: pd.DataFrame, box: str) -> pd.DataFrame:
    """Winter over summer for the four season pairs, by pixel mean and by the median of the daily means."""
    out = []
    for dj in ("DJF2425", "DJF2526"):
        for jj in ("JJA2025", "JJA2026"):
            a = table[(table.box == box) & (table.season == dj)].iloc[0]
            b = table[(table.box == box) & (table.season == jj)].iloc[0]
            out.append(dict(winter=dj, summer=jj, ratio=a.pix_mean / b.pix_mean,
                            ratio_daymed=a.day_median / b.day_median))
    return pd.DataFrame(out)


def monthly() -> pd.DataFrame:
    """Per dial month (Jalali, Aban 1404 to Mehr 1405): the Tehran-Karaj pixel mean, its pixel count and days, and
    the ratio to the summer reference (Tir to Shahrivar 1405, pooled). The attributes hold the reference (its pixel
    mean) and the winter ratio (Azar to Bahman 1404, pooled, over the same reference)."""
    df = records(window_rows())
    ref = box_stats(df[df.jk.isin(REF_JK)], TEHRAN_KARAJ)["pix_mean"]
    out = []
    for jk in DIAL_JK:
        st = box_stats(df[df.jk == jk], TEHRAN_KARAJ)
        out.append(dict(jk=jk, pix_mean=st["pix_mean"], n_pix=st["n_pix"], n_days=st["n_days"],
                        ratio=st["pix_mean"] / ref))
    t = pd.DataFrame(out)
    t.attrs["ref"] = float(ref)
    t.attrs["winter"] = float(box_stats(df[df.jk.isin(WINTER_JK)], TEHRAN_KARAJ)["pix_mean"] / ref)
    return t


def comparison() -> pd.DataFrame:
    """The film's comparison: Azar to Bahman 1404 over Tir to Shahrivar 1405, in three boxes (the Tehran-Karaj box,
    the city core at +-0.15 deg of the centre, the wider box): the pixel-mean ratio and the ratio of the daily medians."""
    df = records(window_rows())
    win, sm = df[df.jk.isin(WINTER_JK)], df[df.jk.isin(REF_JK)]
    rows = []
    for name, box in (("TehranKaraj", TEHRAN_KARAJ), ("core0.15", CORE), ("wide", WIDE)):
        a, b = box_stats(win, box), box_stats(sm, box)
        rows.append(dict(box=name, ratio_pix=a["pix_mean"] / b["pix_mean"], ratio_daymed=a["day_median"] / b["day_median"],
                         win_pix=a["n_pix"], sum_pix=b["n_pix"], win_days=a["n_days"], sum_days=b["n_days"]))
    return pd.DataFrame(rows)


def field(df: pd.DataFrame) -> np.ndarray:
    """The mean NO2 field of the records on the frame grid (1e15 molec/cm2), NaN where there is no data:
    0.04-deg bins with at least 3 pixels, smoothed as in the fact check's frame, sampled per frame pixel."""
    gl, gr, gb, gt = LON_L - 0.02, LON_R + 0.02, LAT_B - 0.02, LAT_T + 0.02
    ni, nj = int(np.ceil((gr - gl) / BIN)), int(np.ceil((gt - gb) / BIN))
    ix = np.floor((df.lon.values - gl) / BIN).astype(int)
    iy = np.floor((gt - df.lat.values) / BIN).astype(int)
    ok = (ix >= 0) & (ix < ni) & (iy >= 0) & (iy < nj)
    ssum, cnt = np.zeros((nj, ni)), np.zeros((nj, ni))
    np.add.at(ssum, (iy[ok], ix[ok]), df.no2.values[ok])
    np.add.at(cnt, (iy[ok], ix[ok]), 1)
    mean = np.where(cnt >= CNT_MIN, ssum / np.maximum(cnt, 1), np.nan)
    have = np.isfinite(mean).astype(float)
    wgt = ndimage.gaussian_filter(have, SMOOTH)
    sm = ndimage.gaussian_filter(np.where(np.isfinite(mean), mean, 0.0), SMOOTH) / np.maximum(wgt, 1e-6)
    yy, xx = np.mgrid[0:H, 0:W]
    lon_f, lat_f = lonlat_of(xx.astype(float), yy.astype(float))
    fi, fj = (lon_f - gl) / BIN, (gt - lat_f) / BIN
    out = ndimage.map_coordinates(sm, [fj, fi], order=1)
    cover = ndimage.map_coordinates(wgt, [fj, fi], order=1)
    return np.where(cover > 0.2, out, np.nan)


def fields() -> dict:
    """The film's fields on the frame: each dial month (keys 'YYYY-MM' in Jalali), 'winter' (Azar to Bahman 1404
    pooled) and 'summer' (Tir to Shahrivar 1405 pooled)."""
    df = records(window_rows())
    out = {jk: field(df[df.jk == jk]) for jk in DIAL_JK}
    out["winter"] = field(df[df.jk.isin(WINTER_JK)])
    out["summer"] = field(df[df.jk.isin(REF_JK)])
    return out


def main() -> None:
    table = fact_check()
    print("fact check reproduced (table agrees with ratio_table_fact.csv)")
    pr = pairs(table, "TehranKaraj")
    print(pr.round(3).to_string(index=False))
    assert round(pr.ratio.min(), 2) == 2.89 and round(pr.ratio.max(), 2) == 3.43, pr.ratio.values
    assert 2.2 <= pr.ratio_daymed.min() and pr.ratio_daymed.max() <= 3.1, pr.ratio_daymed.values
    core = pairs(table, "core0.15")
    assert 3.38 <= core.ratio.min() and core.ratio.max() <= 4.19, core.ratio.values
    cmp = comparison()
    print("Azar-Bahman 1404 over Tir-Shahrivar 1405 (pooled):")
    print(cmp.round(3).to_string(index=False))
    m = monthly()
    print(m.round(3).to_string(index=False))
    print(f"summer reference Tir-Shahrivar 1405 pixel mean {m.attrs['ref']:.3f}; "
          f"winter Azar-Bahman 1404 ratio {m.attrs['winter']:.3f}")
    print("RESULT ok")


if __name__ == "__main__":
    sys.exit(main())
