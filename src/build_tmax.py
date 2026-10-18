"""Parse GHCN-Daily .dly files into one station x day TMAX matrix.

Keeps TMAX only, drops values with a non-blank GHCN quality flag, and counts
"complete" years (>= 80 % of days with a valid TMAX) per station. Writes

    data/cache/tmax_int16.npy   station x day, tenths of degC, MISSING = -32768
    data/cache/stations.csv     metadata + completeness counts per station row

If data/cache/recent_supplement.csv exists (fill_recent.py), its national
open-data values fill days that GHCN-Daily does not have yet.

Run with `python -I src/build_tmax.py` (the .dly files are downloaded data).
"""

from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DLY = ROOT / "data" / "dly"
CACHE = ROOT / "data" / "cache"

MISSING = np.int16(-32768)
LINE_LEN = 269
DATE0 = np.datetime64("1800-01-01")
DATE1 = np.datetime64(f"{date.today().year}-12-31")
N_DAYS = int((DATE1 - DATE0).astype(int)) + 1
COMPLETE_FRAC = 0.8
SUPPLEMENT = CACHE / "recent_supplement.csv"


def parse_dly_tmax(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Return (day_index, value_tenths_degC) for every valid TMAX value in a .dly file."""
    lines = [ln for ln in path.read_bytes().splitlines() if ln[17:21] == b"TMAX"]
    if not lines:
        return np.empty(0, np.int32), np.empty(0, np.int16)
    lines = [ln.ljust(LINE_LEN)[:LINE_LEN] for ln in lines]
    arr = np.frombuffer(b"".join(lines), dtype=np.uint8).reshape(len(lines), LINE_LEN)

    year = _digits_to_int(arr[:, 11:15])
    month = _digits_to_int(arr[:, 15:17])

    fields = arr[:, 21 : 21 + 31 * 8].reshape(len(lines), 31, 8)
    chars = fields[:, :, 0:5]
    is_digit = (chars >= ord("0")) & (chars <= ord("9"))
    weights = 10 ** np.arange(4, -1, -1)
    value = ((chars - ord("0")) * is_digit * weights).sum(axis=2)
    value = np.where((chars == ord("-")).any(axis=2), -value, value)
    qflag = fields[:, :, 6]

    month_start = (
        (year - 1970) * 12 + (month - 1)
    ).astype("timedelta64[M]") + np.datetime64("1970-01", "M")
    first_day = month_start.astype("datetime64[D]")
    n_in_month = ((month_start + 1).astype("datetime64[D]") - first_day).astype(int)

    day = np.arange(31)[None, :]
    ok = (value != -9999) & (qflag == ord(" ")) & (day < n_in_month[:, None])
    idx = (first_day - DATE0).astype(int)[:, None] + day
    keep = ok & (idx >= 0) & (idx < N_DAYS)
    return idx[keep].astype(np.int32), value[keep].astype(np.int16)


def _digits_to_int(block: np.ndarray) -> np.ndarray:
    n = block.shape[1]
    return ((block - ord("0")) * 10 ** np.arange(n - 1, -1, -1)).sum(axis=1)


def read_stations() -> pd.DataFrame:
    rows = []
    with open(RAW / "ghcnd-stations.txt", encoding="latin-1") as f:
        for ln in f:
            rows.append(
                {
                    "id": ln[0:11],
                    "lat": float(ln[12:20]),
                    "lon": float(ln[21:30]),
                    "elev": float(ln[31:37]),
                    "state": ln[38:40].strip(),
                    "name": ln[41:71].strip(),
                }
            )
    st = pd.DataFrame(rows).set_index("id")
    countries = {}
    with open(RAW / "ghcnd-countries.txt", encoding="latin-1") as f:
        for ln in f:
            countries[ln[0:2]] = ln[3:].strip()
    st["country_code"] = st.index.str[:2]
    st["country"] = st["country_code"].map(countries)
    return st


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    ids = (RAW / "candidates_tmax_100y_active.txt").read_text().split()
    paths = [DLY / f"{i}.dly" for i in ids]
    missing = [p.name for p in paths if not p.exists()]
    if missing:
        sys.exit(f"{len(missing)} .dly files missing, e.g. {missing[:3]}; rerun the download")

    tmax = np.full((len(ids), N_DAYS), MISSING, dtype=np.int16)
    with ProcessPoolExecutor(max_workers=12) as pool:
        for row, (idx, val) in enumerate(pool.map(parse_dly_tmax, paths, chunksize=8)):
            tmax[row, idx] = val

    n_supplement = pd.Series(0, index=ids)
    sources = pd.Series("", index=ids)
    if SUPPLEMENT.exists():
        sup = pd.read_csv(SUPPLEMENT)
        sup = sup[sup["id"].isin(ids)]
        rows = pd.Series(np.arange(len(ids)), index=ids).loc[sup["id"]].to_numpy()
        cols = (pd.to_datetime(sup["date"]) - pd.Timestamp(str(DATE0))).dt.days.to_numpy()
        ok = cols < N_DAYS
        rows, cols, vals = rows[ok], cols[ok], sup["tmax_tenths"].to_numpy()[ok]
        fill = tmax[rows, cols] == MISSING
        tmax[rows[fill], cols[fill]] = vals[fill]
        n_supplement = n_supplement.add(pd.Series(sup["id"].to_numpy()[ok][fill]).value_counts(),
                                        fill_value=0).astype(int)
        sources.update(sup.groupby("id")["source"].first())

    dates = DATE0 + np.arange(N_DAYS)
    years = dates.astype("datetime64[Y]").astype(int) + 1970
    year_list = np.arange(years.min(), years.max() + 1)
    days_per_year = np.bincount(years - years.min())
    valid = tmax != MISSING
    counts = np.add.reduceat(valid, np.searchsorted(years, year_list), axis=1)
    complete = counts >= COMPLETE_FRAC * days_per_year[None, :]

    st = read_stations().loc[ids].copy()
    st["row"] = np.arange(len(ids))
    st["n_valid_days"] = valid.sum(axis=1)
    st["n_complete_years"] = complete.sum(axis=1)
    first = np.where(valid.any(axis=1), valid.argmax(axis=1), -1)
    last = np.where(valid.any(axis=1), N_DAYS - 1 - valid[:, ::-1].argmax(axis=1), -1)
    st["first_date"] = np.where(first >= 0, dates[first].astype(str), "")
    st["last_date"] = np.where(last >= 0, dates[last].astype(str), "")
    st["n_days_final_year"] = counts[:, -1]
    st["n_days_prev_year"] = counts[:, -2]
    st["n_days_supplement"] = n_supplement.loc[ids].to_numpy()
    st["supplement_source"] = np.where(st["n_days_supplement"] > 0, sources.loc[ids].to_numpy(), "")

    np.save(CACHE / "tmax_int16.npy", tmax)
    st.to_csv(CACHE / "stations.csv")
    print(f"parsed {len(ids)} stations, {N_DAYS} days; matrix {tmax.nbytes / 1e6:.0f} MB")
    print(st[["n_complete_years", "n_days_final_year"]].describe().round(1))


if __name__ == "__main__":
    main()
