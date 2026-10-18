"""Record daily maximum temperature for every calendar day, station by station.

Stations: >= 100 complete years of TMAX (>= 80 % of days valid) and still
reporting: valid TMAX on at least half of last year's days or of this year's
days so far. Values with a GHCN quality flag were dropped when parsing;
here values beyond 6 sigma of the station's own seasonal cycle (3 harmonics
fitted to the whole record) are dropped too, because a single bad value would
otherwise become a record.

For each calendar day (29 Feb skipped) up to the station's last day of data this
year, or up to today's date for stations not yet reporting this year: the
highest TMAX over all years and the year that first reached it (ties go to the
earliest year, the one that set the record; later years only equalled it).

"Expected in a stable climate" uses the same tie rule: with k years tied at the
record among n years with data, the record falls in a set of m years at the
end of the record with probability C(m, k) / C(n, k).

Writes outputs/stations/records_long.csv.gz and outputs/stations/station_index.csv.
Run with `python -I src/station_records.py`.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
OUT = ROOT / "outputs" / "stations"

MISSING = -32768
DATE0 = np.datetime64("1800-01-01")
FINAL_YEAR = date.today().year
MIN_COMPLETE_YEARS = 100
QC_SIGMA = 6.0
N_HARM = 3

EUROPE = {
    "Germany", "Sweden", "United Kingdom", "Estonia", "France", "Austria", "Netherlands",
    "Spain", "Romania", "Switzerland", "Ukraine", "Hungary", "Belgium", "Ireland", "Finland",
    "Norway", "Slovakia", "Portugal", "Bosnia and Herzegovina", "Croatia", "Lithuania",
    "Latvia", "Czech Republic", "Czechia", "Poland", "Moldova", "Slovenia", "Bulgaria", "Italy",
    "Denmark", "Greece", "Serbia", "Iceland", "Luxembourg", "Belarus", "North Macedonia",
}
AFRICA = {"Algeria", "Morocco", "Niger", "Tunisia", "Egypt", "South Africa", "Libya"}


def region(country: str, lon: float, lat: float) -> str:
    if country == "Russia" or country == "Turkey":
        return "Europe" if lon < 60 and lat > 40 else "Asia"
    if country in EUROPE:
        return "Europe"
    if country in AFRICA or (country == "Spain" and lat < 30):
        return "Africa" if country != "Spain" else "Europe"
    if country.startswith(("United States", "Puerto Rico")) or country in ("Canada", "Greenland [Denmark]", "Mexico"):
        return "North America"
    if country in ("Australia", "New Zealand"):
        return "Oceania"
    if country in ("Argentina", "Brazil", "Chile", "Uruguay"):
        return "South America"
    return "Asia"


def load():
    st = pd.read_csv(CACHE / "stations.csv", index_col="id")
    so_far = (date.today() - date(FINAL_YEAR, 1, 1)).days
    prev_len = (date(FINAL_YEAR, 1, 1) - date(FINAL_YEAR - 1, 1, 1)).days
    active = (st["n_days_final_year"] >= 0.5 * so_far) | (st["n_days_prev_year"] >= 0.5 * prev_len)
    st = st[(st["n_complete_years"] >= MIN_COMPLETE_YEARS) & active].copy()
    st["region"] = [region(c, lo, la) for c, lo, la in zip(st["country"], st["lon"], st["lat"])]
    raw = np.load(CACHE / "tmax_int16.npy", mmap_mode="r")
    tmax = raw[st["row"].to_numpy()].astype(np.float32)
    tmax[tmax == MISSING] = np.nan
    tmax /= 10.0
    dates = DATE0 + np.arange(tmax.shape[1])
    return st, tmax, dates


def qc_outliers(tmax: np.ndarray, dates: np.ndarray) -> int:
    """Blank values beyond QC_SIGMA of each station's seasonal cycle; returns how many."""
    years = dates.astype("datetime64[Y]")
    doy = (dates - years.astype("datetime64[D]")).astype(int)
    ndays = ((years + 1).astype("datetime64[D]") - years.astype("datetime64[D]")).astype(int)
    phase = 2 * np.pi * (doy + 0.5) / ndays
    X = np.stack([np.ones_like(phase)] + [f(k * phase) for k in range(1, N_HARM + 1)
                                          for f in (np.cos, np.sin)], axis=1).astype(np.float32)
    n_bad = 0
    for i in range(tmax.shape[0]):
        y = tmax[i]
        m = np.isfinite(y)
        beta, *_ = np.linalg.lstsq(X[m], y[m], rcond=None)
        r = y - X @ beta
        gam, *_ = np.linalg.lstsq(X[m], r[m] ** 2, rcond=None)
        sd = np.sqrt(np.clip(X @ gam, 0.25, None))
        bad = np.abs(r) > QC_SIGMA * sd
        n_bad += int(bad.sum())
        y[bad] = np.nan
    return n_bad


def calendar_cube(tmax: np.ndarray, dates: np.ndarray):
    """station x year x calendar day (365, no 29 Feb) array of TMAX."""
    d = pd.to_datetime(dates)
    keep = ~((d.month == 2) & (d.day == 29))
    first = int(d.year[np.isfinite(tmax).any(axis=0)].min())
    keep &= np.asarray(d.year >= first)
    md = pd.date_range("2001-01-01", "2001-12-31")
    md_index = pd.Series(np.arange(365), index=md.strftime("%m-%d"))
    yi = np.asarray(d.year[keep]) - first
    di = md_index.loc[np.asarray(d.strftime("%m-%d")[keep])].to_numpy()
    years = np.arange(first, FINAL_YEAR + 1)
    cube = np.full((tmax.shape[0], len(years), 365), np.nan, dtype=np.float32)
    cube[:, yi, di] = tmax[:, keep]
    return cube, years, md


def prob_recent(n: np.ndarray, k: np.ndarray, m: np.ndarray) -> np.ndarray:
    """C(m, k) / C(n, k): chance that the earliest of k tied years falls in the last m years."""
    p = np.ones_like(n, dtype=float)
    for i in range(int(k.max())):
        active = k > i
        p = np.where(active, p * np.clip(m - i, 0, None) / np.maximum(n - i, 1), p)
    return p


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    st, tmax, dates = load()
    n_bad = qc_outliers(tmax, dates)
    cube, years, md = calendar_cube(tmax, dates)
    del tmax

    valid = np.isfinite(cube)
    filled = np.where(valid, cube, -np.inf)
    rec = filled.max(axis=1)
    at_rec = valid & (filled == rec[:, None, :])
    rec_year = years[at_rec.argmax(axis=1)]
    n_tied = at_rec.sum(axis=1)
    n_years = valid.sum(axis=1)
    final = cube[:, -1, :]

    today_i = (date.today() - date(FINAL_YEAR, 1, 1)).days
    has_final = np.isfinite(final).any(axis=1)
    last_final = np.where(has_final, 364 - np.isfinite(final)[:, ::-1].argmax(axis=1), -1)
    end_i = np.where(has_final, last_final, min(today_i, 364))

    rows, index = [], []
    for s, (sid, meta) in enumerate(st.iterrows()):
        e = end_i[s] + 1
        days = slice(0, e)
        n, k = n_years[s, days], n_tied[s, days]
        exp = {}
        for start in (2000, 2020):
            m = valid[s, years >= start, :e].sum(axis=0)
            exp[start] = float(prob_recent(n, k, m).sum())
        ry = rec_year[s, days]
        df = pd.DataFrame({
            "id": sid,
            "md": md.strftime("%m-%d")[days],
            "record_c": rec[s, days].round(1),
            "record_year": ry,
            "n_tied": k,
            "n_years": n,
            "value_final_year": final[s, days].round(1),
        })
        rows.append(df)
        counts = pd.Series(ry).value_counts()
        hottest = int(np.argmax(rec[s, days]))
        index.append({
            "id": sid,
            "name": meta["name"], "state": meta["state"], "country": meta["country"],
            "region": meta["region"], "lat": meta["lat"], "lon": meta["lon"], "elev": meta["elev"],
            "first_date": meta["first_date"], "last_date": meta["last_date"],
            "n_complete_years": int(meta["n_complete_years"]),
            "n_days_supplement": int(meta["n_days_supplement"]),
            "supplement_source": meta["supplement_source"] if isinstance(meta["supplement_source"], str) else "",
            "has_final_year": bool(has_final[s]),
            "end_md": md.strftime("%m-%d")[e - 1],
            "n_days": e,
            "records_2020s": int((ry >= 2020).sum()),
            "expected_2020s": round(exp[2020], 2),
            "records_since_2000": int((ry >= 2000).sum()),
            "expected_since_2000": round(exp[2000], 2),
            "records_final_year": int((ry == FINAL_YEAR).sum()),
            "top_year": int(counts.index[0]),
            "top_year_days": int(counts.iloc[0]),
            "hottest_record_c": round(float(rec[s, hottest]), 1),
            "hottest_record_md": md.strftime("%m-%d")[hottest],
            "hottest_record_year": int(ry[hottest]),
            "days_with_ties": int((k > 1).sum()),
            "min_years_per_day": int(n.min()),
        })

    long = pd.concat(rows, ignore_index=True)
    long.to_csv(OUT / "records_long.csv.gz", index=False)
    idx = pd.DataFrame(index).sort_values(["region", "country", "name"])
    idx["final_year"] = FINAL_YEAR
    idx.to_csv(OUT / "station_index.csv", index=False)

    print(f"{len(idx)} stations, {n_bad} values dropped by the {QC_SIGMA:g}-sigma screen")
    print(idx["region"].value_counts().to_string())
    print(f"stations reporting in {FINAL_YEAR}: {idx['has_final_year'].sum()}")
    eu = idx[idx["region"] == "Europe"]
    print(f"Europe: {len(eu)} stations; median 2020s records {eu['records_2020s'].median():.0f} "
          f"vs expected {eu['expected_2020s'].median():.1f}")
    print(f"min years per plotted day: {idx['min_years_per_day'].min()}")


if __name__ == "__main__":
    main()
