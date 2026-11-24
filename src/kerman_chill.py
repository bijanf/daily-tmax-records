"""Winter chill around Rafsanjan and Kerman from hourly ERA5-Land 2 m temperature (cluster copy), 75 winters.

A winter is named by the year of its January: winter 1951 = 1 Oct 1950 .. 31 Mar 1951. For every 0.1-degree cell of the
box and every month Oct..Mar it sums three standard chill measures:
    ch     chill hours: hours with 0 <= T <= 7.2 C (Weinberger 1950)
    utah   Utah chill units (Richardson et al. 1974)
    cp     chill portions of the Dynamic Model (Fishman et al. 1987; Erez & Fishman 1997), accumulated hour by hour
           from 1 Oct of each winter, the formulation of chillR's Dynamic_Model
and the month's mean temperature (tm). Output: one npz, small.

Run on the cluster (the hourly ERA5-Land files live there; about 100 s a winter on the io partition), with
src/kerman_chill.sbatch; the 75 parts come back to data/kerman/chill/ and src/kerman.py reads them:

    sbatch kerman_chill.sbatch          # writes /p/tmp/<user>/kerman/parts/chill_<winter>.npz
    scp 'hpc:/p/tmp/<user>/kerman/parts/chill_*.npz' data/kerman/chill/
    ~/mambaforge/bin/python kerman_chill.py OUT.npz [first last]      # by hand
"""
import sys
import time

import numpy as np
import xarray as xr

SRC = "/p/projects/climate_data_central/reanalysis/ERA5-Land/2m_temperature/2m_temperature_ERA5-Land_{y}{m:02d}01-{y}{m:02d}{d:02d}.nc"
LAT = slice(31.25, 29.55)            # 30 N +- : Anar, Rafsanjan, Kerman, Bardsir
LON = slice(54.85, 57.65)
WINTERS = range(1951, 2026)
MONTHS = ((-1, 10), (-1, 11), (-1, 12), (0, 1), (0, 2), (0, 3))


def days(y, m):
    return (np.datetime64(f"{y + (m == 12)}-{m % 12 + 1:02d}-01") - np.datetime64(f"{y}-{m:02d}-01")).astype(int)


def utah(t):
    u = np.zeros_like(t)
    u[(t > 1.4) & (t <= 2.4)] = 0.5
    u[(t > 2.4) & (t <= 9.1)] = 1.0
    u[(t > 9.1) & (t <= 12.4)] = 0.5
    u[(t > 15.9) & (t <= 18.0)] = -0.5
    u[t > 18.0] = -1.0
    return u


def dynamic(t):
    """chillR's Dynamic_Model, hour by hour along axis 0, vectorised over cells; returns each hour's portions."""
    e0, e1, a0, a1, slp, tf = 4153.5, 12888.8, 139500.0, 2.567e18, 1.6, 277.0
    tk = t.astype(np.float64) + 273.0
    aa, ee = a0 / a1, e1 - e0
    sr = np.exp(slp * tf * (tk - tf) / tk)
    xi = sr / (1 + sr)
    xs = aa * np.exp(ee / tk)
    eak1 = np.exp(-a1 * np.exp(-e1 / tk))
    E = np.zeros(t.shape[1:])
    out = np.zeros(t.shape)
    for h in range(1, t.shape[0]):
        S = np.where(E < 1, E, E - E * xi[h - 1])
        E = xs[h] - (xs[h] - S) * eak1[h]
        out[h] = np.where(E >= 1, E * xi[h], 0.0)
        # once a portion is counted, the intermediate falls back (chillR: the next hour's S uses E*(1-xi))
    return out


def main(dst, first=None, last=None):
    """Writes one npz per winter (dst_<winter>.npz), so a killed job loses at most one winter; first/last pick a range."""
    res = None
    t0 = time.time()
    for k, w in enumerate(WINTERS):
        if (first and w < first) or (last and w > last):
            continue
        part = f"{dst[:-4]}_{w}.npz"
        try:
            np.load(part)
            continue                       # done before
        except OSError:
            pass
        hours, cuts = [], [0]
        for dy, m in MONTHS:
            y = w + dy
            ds = xr.open_dataset(SRC.format(y=y, m=m, d=days(y, m)))
            b = ds.t2m.sel(latitude=LAT, longitude=LON)
            if res is None:
                lat, lon = b.latitude.values, b.longitude.values
                res = {n: np.full((len(WINTERS), 6, len(lat), len(lon)), np.nan, np.float32) for n in ("ch", "utah", "cp", "tm")}
            a = b.values.astype(np.float64) - 273.15
            ds.close()
            hours.append(a)
            cuts.append(cuts[-1] + a.shape[0])
        T = np.concatenate(hours)
        cp = dynamic(T)
        ut = utah(T)
        ch = ((T >= 0.0) & (T <= 7.2)).astype(np.float64)
        for j in range(6):
            s = slice(cuts[j], cuts[j + 1])
            res["ch"][k, j] = ch[s].sum(0)
            res["utah"][k, j] = ut[s].sum(0)
            res["cp"][k, j] = cp[s].sum(0)
            res["tm"][k, j] = T[s].mean(0)
        np.savez_compressed(part, winter=w, months=np.array([m for _, m in MONTHS]), lat=lat, lon=lon,
                            **{n: v[k] for n, v in res.items()})
        print(w, f"{time.time() - t0:.0f}s", "box mean CP Oct-Mar %.1f, CH Nov-Feb %.0f" % (np.nanmean(res["cp"][k].sum(0)), np.nanmean(res["ch"][k, 1:5].sum(0))), flush=True)
    print("done", first, last)


if __name__ == "__main__":
    main(sys.argv[1], *(int(a) for a in sys.argv[2:4]))
