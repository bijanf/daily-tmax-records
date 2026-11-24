"""Step 7: the orchard-area tables, then vs now, raw and sensor-harmonised, and the yearly series.

Inputs: results/<year>.json (s04_year.py: exact counts per zone from float NDVI), cache/ndvi_<year>.npz,
cache/dem.npz (s06_dem.py), sensor_eq.csv (s07_sensor.py).

Areas:
  box    = the whole box (zone W from path 161, zone E from path 160)
  plain  = the box below 2,000 m (Copernicus DEM): drops the green wadis and shrubland of the volcano
           in the south-west and of the north-eastern ridge, which are not orchards
Raw: NDVI >= t on every sensor. Harmonised: Landsat 8/9 OLI is the reference; for TM (Landsat 4/5) and
ETM+ (Landsat 7, used only before 31 May 2003) years the threshold is replaced by the TM/ETM+ NDVI that
covers the same area as OLI >= t on the same day (equal-area thresholds of s07_sensor.py, chained
TM -> ETM+ -> OLI; mean over pairs; +-1 SD over pairs gives the harmonisation's spread).
Area at a threshold between the 0.005 steps of the cached NDVI is interpolated linearly within the step.

    python -I s09_tables.py
Writes table_years.csv, then_now.csv, timeseries_plain_oli020.csv, harmonisation.csv, and prints the summary."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HERE  # noqa: E402
from geom import masks, PIX_KM2  # noqa: E402

THR = (0.15, 0.20, 0.25, 0.30)
THEN = (1987, 1988, 1989, 1990)
NOW = (2022, 2023, 2024, 2025)
OLD = {"landsat-4", "landsat-5", "landsat-7"}


def harmonisation() -> pd.DataFrame:
    """Per OLI threshold t: the equivalent ETM+ and TM thresholds (mean, SD over pairs)."""
    eq = pd.read_csv(HERE / "sensor_eq.csv")
    e78 = eq[(eq.old == "landsat-7") & (eq.new == "landsat-8")]
    e57 = eq[(eq.old == "landsat-5") & (eq.new == "landsat-7")]
    rows = []
    for t in THR:
        x = e78[np.isclose(e78.t_new, t)].t_old_eq.astype(float)
        etm, etm_sd = x.mean(), x.std(ddof=1)
        tm_vals = []                                       # per TM/ETM+ pair: TM eq. of the ETM+ threshold
        for (pr, da, db), g in e57.groupby(["path_row", "date_a", "date_b"]):
            g = g.sort_values("t_new")
            tm_vals.append(np.interp(etm, g.t_new.values, g.t_old_eq.values.astype(float)))
        tm_vals = np.array(tm_vals)
        tm, tm_sd_pairs = tm_vals.mean(), tm_vals.std(ddof=1)
        # spread of the chain: ETM+->OLI spread and TM->ETM+ spread, added in quadrature
        rows.append(dict(t_oli=t, t_etm_eq=round(etm, 4), t_etm_sd=round(etm_sd, 4), n_pairs_78=len(x),
                         t_tm_eq=round(tm, 4), t_tm_sd_57pairs=round(tm_sd_pairs, 4), n_pairs_57=len(tm_vals),
                         t_tm_sd_total=round(float(np.hypot(etm_sd, tm_sd_pairs)), 4)))
    return pd.DataFrame(rows)


def area_at(hist_cum: np.ndarray, t: float) -> float:
    """km2 with NDVI >= t from cumulative counts per 0.005 step (q = floor((ndvi+0.2)/0.005)),
    linear within a step."""
    x = (t + 0.2) / 0.005
    k = int(np.floor(x))
    frac = x - k
    k = min(max(k, 0), 240)
    above_k = hist_cum[k]                        # count with q >= k
    above_k1 = hist_cum[k + 1] if k + 1 <= 240 else 0
    return float((above_k - frac * (above_k - above_k1)) * PIX_KM2)


def main():
    m = masks()
    dem = np.load(HERE / "cache" / "dem.npz")["elev"]
    regions = {"box": m["inbox"], "plain": m["inbox"] & (dem < 2000)}
    print("region areas km2:", {k: round(v.sum() * PIX_KM2, 1) for k, v in regions.items()})
    H = harmonisation()
    H.to_csv(HERE / "harmonisation.csv", index=False)
    print(H.to_string())
    rows = []
    for f in sorted((HERE / "results").glob("*.json")):
        r = json.loads(f.read_text())
        y = r["year"]
        zs = r["zones"]
        avail = {k: v.get("available", False) and len(v["passes"]) > 0 for k, v in zs.items()}
        if not any(avail.values()):
            rows.append(dict(year=y, complete=False, note="no usable pass (only Landsat 7 after its scan-line failure)"))
            continue
        plats = sorted({p["platform"] for v in zs.values() for p in v["passes"]})
        sensor = "OLI" if set(plats) <= {"landsat-8", "landsat-9"} else ("TM/ETM+" if set(plats) <= OLD else "mixed")
        row = dict(year=y, complete=all(avail.values()), sensor=sensor, platforms="+".join(p[-1] for p in plats),
                   passes_W=len(zs["W"]["passes"]), passes_E=len(zs["E"]["passes"]),
                   dates_W=" ".join(p["date"][5:] for p in zs["W"]["passes"]),
                   dates_E=" ".join(p["date"][5:] for p in zs["E"]["passes"]),
                   unseen_frac_W=zs["W"].get("unseen_frac"), unseen_frac_E=zs["E"].get("unseen_frac"),
                   desert_ndvi_W=zs["W"].get("desert_ndvi_median"), desert_ndvi_E=zs["E"].get("desert_ndvi_median"))
        for t in THR:
            row[f"W_raw_{t:.2f}"] = zs["W"].get(f"veg_km2_thr{t:.2f}")
            row[f"E_raw_{t:.2f}"] = zs["E"].get(f"veg_km2_thr{t:.2f}")
        q = np.load(HERE / "cache" / f"ndvi_{y}.npz")["q"]
        for rname, reg in regions.items():
            for zname, zm in (("W", m["zw"]), ("E", m["ze"])):
                if not avail[zname]:
                    continue
                v = q[reg & zm]
                v = v[v != 255]
                h = np.bincount(v, minlength=241)[:241]
                cum = h[::-1].cumsum()[::-1]                     # cum[k] = count q >= k
                for t in THR:
                    row[f"{rname}{zname}_raw_{t:.2f}"] = area_at(cum, t)
                    if sensor == "OLI":
                        tt, lo, hi = t, t, t
                    else:
                        h_ = H[np.isclose(H.t_oli, t)].iloc[0]
                        tt, sd = h_.t_tm_eq, h_.t_tm_sd_total
                        lo, hi = tt - sd, tt + sd
                    row[f"{rname}{zname}_harm_{t:.2f}"] = area_at(cum, tt)
                    row[f"{rname}{zname}_harmhi_{t:.2f}"] = area_at(cum, lo)   # lower threshold -> more area
                    row[f"{rname}{zname}_harmlo_{t:.2f}"] = area_at(cum, hi)
            for kind in ("raw", "harm", "harmhi", "harmlo"):
                for t in THR:
                    a, b = row.get(f"{rname}W_{kind}_{t:.2f}"), row.get(f"{rname}E_{kind}_{t:.2f}")
                    row[f"{rname}_{kind}_{t:.2f}"] = (a + b) if (a is not None and b is not None) else None
        rows.append(row)
    df = pd.DataFrame(rows).sort_values("year")
    # sanity: the cache-based raw box areas reproduce the float counts of results/*.json
    ok = df.complete.fillna(False).astype(bool)
    for t in THR:
        dif = (df.loc[ok, f"box_raw_{t:.2f}"] - df.loc[ok, f"W_raw_{t:.2f}"] - df.loc[ok, f"E_raw_{t:.2f}"]).abs().max()
        assert dif < 0.05, (t, dif)
    df.round(3).to_csv(HERE / "table_years.csv", index=False)

    # then / now
    out = []
    for rname in ("box", "plain"):
        for kind in ("raw", "harm"):
            for t in THR:
                c = f"{rname}_{kind}_{t:.2f}"
                th = df[df.year.isin(THEN)][c].astype(float)
                nw = df[df.year.isin(NOW)][c].astype(float)
                rec = dict(region=rname, method=kind, t_oli=t, then_years="-".join(map(str, THEN)),
                           now_years="-".join(map(str, NOW)),
                           then_mean_km2=th.mean(), then_sd=th.std(ddof=1), then_min=th.min(), then_max=th.max(),
                           now_mean_km2=nw.mean(), now_sd=nw.std(ddof=1), now_min=nw.min(), now_max=nw.max(),
                           ratio=nw.mean() / th.mean(), ratio_min=nw.min() / th.max(), ratio_max=nw.max() / th.min(),
                           growth_km2=nw.mean() - th.mean())
                if kind == "harm":
                    thl = df[df.year.isin(THEN)][f"{rname}_harmlo_{t:.2f}"].astype(float).mean()
                    thh = df[df.year.isin(THEN)][f"{rname}_harmhi_{t:.2f}"].astype(float).mean()
                    rec.update(then_mean_if_tm_thr_plus1sd=thl, then_mean_if_tm_thr_minus1sd=thh,
                               ratio_if_tm_thr_plus1sd=nw.mean() / thl, ratio_if_tm_thr_minus1sd=nw.mean() / thh)
                out.append(rec)
    tn = pd.DataFrame(out)
    tn.round(4).to_csv(HERE / "then_now.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    show = tn[["region", "method", "t_oli", "then_mean_km2", "then_sd", "now_mean_km2", "now_sd", "ratio",
               "ratio_min", "ratio_max"]].copy()
    print(show.round(3).to_string())
    hcols = [c for c in tn.columns if c.startswith("ratio_if")]
    print(tn[tn.method == "harm"][["region", "t_oli"] + hcols].round(3).to_string())

    # the yearly series, one threshold: plain, OLI-equivalent 0.20
    ts = df[["year", "complete", "sensor", "platforms", "passes_W", "passes_E", "dates_W", "dates_E"]].copy()
    ts["plain_km2_oli_eq_0.20"] = df["plain_harm_0.20"]
    ts["plain_km2_oli_eq_0.20_lo"] = df["plain_harmlo_0.20"]
    ts["plain_km2_oli_eq_0.20_hi"] = df["plain_harmhi_0.20"]
    ts["plain_km2_raw_0.20"] = df["plain_raw_0.20"]
    ts["plain_W_only_km2_oli_eq_0.20"] = df["plainW_harm_0.20"]
    ts["note"] = df.get("note")
    ts.loc[ts.year == 1986, "note"] = "path 160 (zone E) has no pass: total missing; zone W only"
    ts.round(2).to_csv(HERE / "timeseries_plain_oli020.csv", index=False)
    print(ts[["year", "sensor", "passes_W", "passes_E", "plain_km2_oli_eq_0.20", "plain_km2_raw_0.20",
              "plain_W_only_km2_oli_eq_0.20"]].round(1).to_string())


if __name__ == "__main__":
    main()
