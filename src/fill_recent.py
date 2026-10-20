"""Bring European stations up to yesterday with national open data.

GHCN-Daily receives most European data through ECA&D, weeks or months late. The
national weather services below publish the same daily maximum temperature
openly and promptly. Each GHCN-Daily station of that country is matched to the
nearest national station (within 7 km and 100 m of elevation); the two sources
are compared on the days both have, and a station is filled only if they are
identical (within 0.05 degC) on at least 95 % of at least 30 shared days.

    GM  DWD         Germany      TXK
    SW  SMHI        Sweden       parameter 20 (max, 18-18 UTC, representative day)
    NL  KNMI        Netherlands  TX
    AU  GeoSphere   Austria      tlmax
    SZ  MeteoSwiss  Switzerland  tre200dx

Writes data/cache/recent_supplement.csv (id, date, tmax_tenths, source) with every
value of the accepted stations; build_tmax.py fills only the days GHCN-Daily
lacks. Needs data/cache/stations.csv from a first build_tmax.py run.
Run with `python -I src/fill_recent.py`.
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_tmax import DATE0, DLY, parse_dly  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
NAT = ROOT / "data" / "national"
MAX_KM = 7.0
MAX_DZ = 100.0
MIN_OVERLAP = 30
MIN_IDENTICAL = 0.95
YEAR0 = date.today().year - 1


def fetch(url: str, path: Path, conditional: bool = True) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    cond = ["-z", str(path)] if conditional and path.exists() and path.stat().st_size else []
    part = path.with_name(path.name + ".part")
    subprocess.run(["curl", "-sS", "-R", "-L", "-m", "300", *cond, "-o", str(part), url], check=True)
    if part.exists() and part.stat().st_size:
        part.replace(path)
    else:
        part.unlink(missing_ok=True)
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Sources: stations() -> DataFrame(key, name, lat, lon, elev); series(key) -> TX in degC by date
# ─────────────────────────────────────────────────────────────────────────────

class DWD:
    name = "DWD"
    base = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily/kl/recent"

    def stations(self):
        path = fetch(f"{self.base}/KL_Tageswerte_Beschreibung_Stationen.txt", NAT / "dwd" / "stations.txt")
        rows = []
        for ln in path.read_text(encoding="latin-1").splitlines()[2:]:
            m = re.match(r"\s*(\d+)\s+(\d{8})\s+(\d{8})\s+(-?\d+)\s+([\d.]+)\s+([\d.]+)\s+(.+?)\s{2,}", ln)
            if m and m[3] >= f"{YEAR0 + 1}0101":
                rows.append({"key": int(m[1]), "name": m[7].strip(), "elev": float(m[4]),
                             "lat": float(m[5]), "lon": float(m[6])})
        return pd.DataFrame(rows)

    def series(self, key):
        path = fetch(f"{self.base}/tageswerte_KL_{key:05d}_akt.zip", NAT / "dwd" / f"{key:05d}.zip")
        with zipfile.ZipFile(path) as z:
            name = next(n for n in z.namelist() if n.startswith("produkt_klima_tag"))
            df = pd.read_csv(io.BytesIO(z.read(name)), sep=";", skipinitialspace=True,
                             encoding="latin-1", dtype=str)
        df.columns = [c.strip() for c in df.columns]
        tx = pd.to_numeric(df["TXK"].str.strip(), errors="coerce").where(lambda v: v > -999)
        return pd.Series(tx.to_numpy(), index=pd.to_datetime(df["MESS_DATUM"].str.strip())).dropna()


class SMHI:
    name = "SMHI"
    base = "https://opendata-download-metobs.smhi.se/api/version/1.0/parameter/20"

    def stations(self):
        path = fetch(f"{self.base}.json", NAT / "smhi" / "stations.json", conditional=False)
        st = json.loads(path.read_text())["station"]
        return pd.DataFrame([{"key": int(s["key"]), "name": s["name"], "lat": s["latitude"],
                              "lon": s["longitude"], "elev": s["height"]} for s in st if s.get("active")])

    def series(self, key):
        parts = []
        for period in ("corrected-archive", "latest-months"):
            path = fetch(f"{self.base}/station/{key}/period/{period}/data.csv",
                         NAT / "smhi" / f"{key}_{period}.csv", conditional=False)
            lines = path.read_text(encoding="utf-8-sig").splitlines()
            start = next(i for i, ln in enumerate(lines) if ln.startswith("Från Datum Tid"))
            rows = [ln.split(";") for ln in lines[start + 1:] if ln.count(";") >= 4]
            s = pd.Series(pd.to_numeric([r[3] for r in rows], errors="coerce"),
                          index=pd.to_datetime([r[2] for r in rows]))
            parts.append(s[s.index.year >= YEAR0])
        s = pd.concat(parts)
        return s[~s.index.duplicated(keep="first")].dropna().sort_index()


class KNMI:
    name = "KNMI"
    url = "https://www.daggegevens.knmi.nl/klimatologie/daggegevens"

    def _get(self, stns, start, tag):
        end = date.today().strftime("%Y%m%d")
        return fetch(f"{self.url}?stns={stns}&vars=TX&start={start}&end={end}",
                     NAT / "knmi" / f"{tag}.txt", conditional=False).read_text(encoding="latin-1")

    def stations(self):
        rows = []
        for ln in self._get("ALL", date.today().strftime("%Y%m%d"), "stations").splitlines():
            m = re.match(r"#\s*(\d+):?\s+([\d.]+)\s+([\d.]+)\s+(-?[\d.]+)\s+(.+)", ln)
            if m:
                rows.append({"key": int(m[1]), "lon": float(m[2]), "lat": float(m[3]),
                             "elev": float(m[4]), "name": m[5].strip()})
        return pd.DataFrame(rows)

    def series(self, key):
        txt = self._get(key, f"{YEAR0}0101", str(key))
        rows = [ln.split(",") for ln in txt.splitlines() if ln and not ln.startswith("#")]
        s = pd.Series(pd.to_numeric([r[2] for r in rows], errors="coerce") / 10,
                      index=pd.to_datetime([r[1].strip() for r in rows]))
        return s.dropna()


class GeoSphere:
    name = "GeoSphere"
    base = "https://dataset.api.hub.geosphere.at/v1/station/historical/klima-v2-1d"

    def stations(self):
        path = fetch(f"{self.base}/metadata", NAT / "geosphere" / "metadata.json", conditional=False)
        st = json.loads(path.read_text())["stations"]
        return pd.DataFrame([{"key": int(s["id"]), "name": s["name"], "lat": s["lat"], "lon": s["lon"],
                              "elev": s["altitude"]} for s in st if s.get("is_active")])

    def series(self, key):
        url = (f"{self.base}?parameters=tlmax&start={YEAR0}-01-01&end={date.today():%Y-%m-%d}"
               f"&station_ids={key}")
        j = json.loads(fetch(url, NAT / "geosphere" / f"{key}.json", conditional=False).read_text())
        data = j["features"][0]["properties"]["parameters"]["tlmax"]["data"]
        idx = pd.to_datetime([t[:10] for t in j["timestamps"]])
        return pd.Series(pd.to_numeric(data, errors="coerce"), index=idx).dropna()


class MeteoSwiss:
    name = "MeteoSwiss"
    base = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn"

    def stations(self):
        path = fetch(f"{self.base}/ogd-smn_meta_stations.csv", NAT / "meteoswiss" / "stations.csv",
                     conditional=False)
        df = pd.read_csv(path, sep=";", encoding="latin-1")
        return pd.DataFrame({"key": df["station_abbr"].str.lower(), "name": df["station_name"],
                             "lat": df["station_coordinates_wgs84_lat"],
                             "lon": df["station_coordinates_wgs84_lon"], "elev": df["station_height_masl"]})

    def series(self, key):
        parts = []
        for period in ("historical", "recent"):
            try:
                path = fetch(f"{self.base}/{key}/ogd-smn_{key}_d_{period}.csv",
                             NAT / "meteoswiss" / f"{key}_{period}.csv", conditional=False)
            except subprocess.CalledProcessError:
                continue
            df = pd.read_csv(path, sep=";", encoding="latin-1", usecols=["reference_timestamp", "tre200dx"])
            s = pd.Series(pd.to_numeric(df["tre200dx"], errors="coerce").to_numpy(),
                          index=pd.to_datetime(df["reference_timestamp"], format="%d.%m.%Y %H:%M"))
            parts.append(s[s.index.year >= YEAR0])
        s = pd.concat(parts)
        return s[~s.index.duplicated(keep="last")].dropna().sort_index()


SOURCES = {"GM": DWD(), "SW": SMHI(), "NL": KNMI(), "AU": GeoSphere(), "SZ": MeteoSwiss()}


def km(lat1, lon1, lat2, lon2):
    p1, p2 = np.deg2rad(lat1), np.deg2rad(lat2)
    dlat, dlon = p2 - p1, np.deg2rad(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlon / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def main() -> None:
    st = pd.read_csv(CACHE / "stations.csv", index_col="id")
    st = st[st["n_complete_years"] >= 100]
    date0 = pd.Timestamp(str(DATE0))
    out = []
    for prefix, src in SOURCES.items():
        mine = st[st.index.str[:2] == prefix]
        if mine.empty:
            continue
        try:
            cands = src.stations()
        except Exception as exc:  # a service being down should not stop the others
            print(f"{src.name}: station list unavailable ({exc})")
            continue
        for sid, meta in mine.iterrows():
            d = km(meta["lat"], meta["lon"], cands["lat"].to_numpy(float), cands["lon"].to_numpy(float))
            j = int(np.argmin(d))
            c = cands.iloc[j]
            dz = abs(float(c["elev"]) - meta["elev"]) if pd.notna(c["elev"]) else 0.0
            label = f"{sid} {meta['name']:<24} {src.name:<10}"
            if d[j] > MAX_KM or dz > MAX_DZ:
                print(f"{label} no match (nearest {c['name']}, {d[j]:.1f} km, {dz:.0f} m)")
                continue
            try:
                tx = src.series(c["key"])
            except Exception as exc:
                print(f"{label} {c['name']}: download failed ({exc})")
                continue
            g_idx, g_val = parse_dly(DLY / f"{sid}.dly")
            ghcn = pd.Series(g_val, index=g_idx)
            idx = (tx.index - date0).days.to_numpy()
            tenths = np.round(tx.to_numpy() * 10).astype(int)
            shared = np.isin(idx, g_idx)
            same = (np.abs(ghcn.reindex(idx[shared]).to_numpy() - tenths[shared]) == 0).mean() \
                if shared.any() else 0.0
            new = ~shared
            ok = shared.sum() >= MIN_OVERLAP and same >= MIN_IDENTICAL
            last_new = tx.index[new].max().date() if new.any() else None
            print(f"{label} -> {c['name']} ({d[j]:.1f} km, {dz:.0f} m): {shared.sum()} shared days, "
                  f"identical {same:.1%}, {new.sum()} new days to {last_new} "
                  f"{'ACCEPTED' if ok else 'rejected'}")
            if ok:
                out.append(pd.DataFrame({"id": sid, "date": tx.index.strftime("%Y-%m-%d"),
                                         "tmax_tenths": tenths, "source": src.name}))
    res = pd.concat(out, ignore_index=True)
    res.to_csv(CACHE / "recent_supplement.csv", index=False)
    print(f"{res['id'].nunique()} stations accepted, {len(res)} station-days written")


if __name__ == "__main__":
    main()
