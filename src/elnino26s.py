"""THE NUMBERS AND THE PICTURES OF THE SELF-DESCRIBING EL NIÑO REEL, VERSION B (elnino26s).

Every number on screen, in the caption and in the first comment is computed here and asserted; the result is written
to data/enso/elnino26s/numbers.json (the film and the score read it and check it again).

- ONI and RONI (NOAA CPC, data/enso/oni.ascii.txt and RONI.ascii.txt, refreshed on 8 Nov 2026): ASO 2026 at rank 1
  (ONI) and rank 2 (RONI) of the 77 ASO values since 1950.
- Iran's rain (src/enso.py, CRU TS 4.10, 621 cells, 1951-2024): the 26 El Niño autumns (October-December, ONI at least
  +0.5 °C) against all 74 autumns; the random-26 check (5,000 draws, seed fixed here).
- The Pacific picture: NOAA OISST v2.1 daily anomaly (0.25°, vs 1991-2020) from CoastWatch ERDDAP, the seven most
  recent days (17-23 October 2026), averaged; the Blue Marble of the box stitched from two GIBS requests across the
  dateline (120° E to 80° W, 30° S to 30° N), cached in data/enso/elnino26s/.

    python -I src/elnino26s.py     fetches what is missing, computes, asserts, writes numbers.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

import enso  # noqa: E402
import onebit  # noqa: E402
import onebit_compare  # noqa: E402  (fetch_bm: the GIBS request, cached)

DATA = onebit.ROOT / "data" / "enso" / "elnino26s"
EL2 = onebit.ROOT / "data" / "enso" / "elnino2"
WEEK = ("2026-10-17", "2026-10-23")                # the seven most recent days on CoastWatch (its last day is 23 Oct)
PAC = dict(lon0=120.0, lon1=280.0, lat0=-30.0, lat1=30.0)      # 280 E = 80 W, across the dateline
NINO = dict(lon0=190.0, lon1=240.0, lat0=-5.0, lat1=5.0)       # Niño-3.4: 170 W to 120 W
TINT_AT = 1.5                                       # °C: the Pacific is tinted where the week's mean is at least this
OISST = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21Agg_LonPM180.nc"
BM_W = 12.5                                         # px per degree of the stitched Blue Marble (2000 x 750)
ONI_ASO = 2.46
RONI_ASO = 1.97
SHUFFLES, SEED = 5000, 20261108


def oisst_part(lon_a: float, lon_b: float, name: str) -> Path:
    """One longitude band of the week's OISST anomaly (surface, 0.25 degrees), cached as netCDF."""
    path = DATA / name
    if path.exists():
        return path
    import urllib.request
    q = (f"anom[({WEEK[0]}T12:00:00Z):1:({WEEK[1]}T12:00:00Z)][(0.0):1:(0.0)]"
         f"[(-29.875):1:(29.875)][({lon_a}):1:({lon_b})]")
    with urllib.request.urlopen(f"{OISST}?{q}", timeout=600) as r:
        part = path.with_suffix(".part")
        part.write_bytes(r.read())
    part.rename(path)
    return path


def week_grid() -> dict:
    """The week's mean anomaly on the Pacific grid (lon 120 E to 280 E, lat ascending), cached files only."""
    import xarray as xr
    a = oisst_part(120.125, 179.875, "oisst_week_a.nc")
    b = oisst_part(-179.875, -80.125, "oisst_week_b.nc")
    da = xr.open_dataset(a)["anom"].squeeze("zlev", drop=True)
    db = xr.open_dataset(b)["anom"].squeeze("zlev", drop=True)
    db = db.assign_coords(longitude=db.longitude % 360)
    full = xr.concat([da, db], dim="longitude").sortby("longitude").sortby("latitude")
    days = [str(t)[:10] for t in full.time.values]
    assert days == [f"2026-10-{d:02d}" for d in range(17, 24)], days
    return dict(days=days, lat=full.latitude.values.astype(float), lon=full.longitude.values.astype(float),
                daily=full.values.astype(float), mean=full.mean("time", skipna=True).values.astype(float))


def week() -> dict:
    """The week's mean anomaly: the Niño-3.4 box mean (area-weighted), the daily box means, the tinted cells."""
    g = week_grid()
    lat, lon, m = g["lat"], g["lon"], g["mean"]
    assert lon.min() >= 120 and lon.max() <= 280 and lat.min() == -29.875 and lat.max() == 29.875
    la = (lat >= NINO["lat0"]) & (lat <= NINO["lat1"])
    lo = (lon >= NINO["lon0"]) & (lon <= NINO["lon1"])
    sub = m[np.ix_(la, lo)]
    w = np.cos(np.radians(lat[la]))[:, None] * np.ones((1, lo.sum()))
    ok = np.isfinite(sub)
    nino_mean = float((sub[ok] * w[ok]).sum() / w[ok].sum())
    daily = []
    for d in g["daily"]:
        dd = d[np.ix_(la, lo)]
        daily.append(round(float(np.nanmean(dd)), 2))
    return dict(days=g["days"], nino34=round(nino_mean, 2), nino34_daily=daily,
                tinted=int(np.nansum(m >= TINT_AT)), cells=int(np.isfinite(m).sum()))


def blue_marble() -> Path:
    """The Blue Marble of the box across the dateline: two GIBS tiles (120-180 E and 180-80 W) stitched, 2000 x 750."""
    out = DATA / "bluemarble_pacific_2000x750.jpg"
    if out.exists():
        return out
    a = onebit_compare.fetch_bm(DATA / "bm_tile_a.jpg", 120.0, 180.0, -30.0, 30.0, 750)
    b = onebit_compare.fetch_bm(DATA / "bm_tile_b.jpg", -180.0, -80.0, -30.0, 30.0, 1250)
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    assert ia.size == (750, 750) and ib.size == (1250, 750), (ia.size, ib.size)
    im = Image.new("RGB", (2000, 750))
    im.paste(ia, (0, 0))
    im.paste(ib, (750, 0))
    im.save(out, quality=92)
    return out


def iran() -> dict:
    """Iran's autumn numbers from enso.result (asserted) and the random-26 check."""
    au = enso.result("OND")
    monthly, _ = enso.iran_rain()
    ann = monthly.loc["1951":"2024"]
    yearly = float(ann.groupby(ann.index.year).sum().mean())
    years = au["years"]
    rain = au["rain"]
    all74 = np.array([rain[y] for y in sorted(rain)])
    en = np.array([rain[y] for y in years])
    assert len(all74) == 74 and len(en) == 26
    mean74 = float(all74.mean())
    mm_en = float(en.mean())
    pct = 100 * mm_en / mean74
    rng = np.random.default_rng(SEED)
    draws = np.array([100 * all74[rng.choice(74, 26, replace=False)].mean() / mean74 for _ in range(SHUFFLES)])
    lo, hi = np.percentile(draws, [2.5, 97.5])
    wettest = max(rain, key=rain.get)
    share = 100 * mean74 / yearly
    return dict(n_all=74, n_el=len(years), mean74=round(mean74, 1), mm_el=round(mm_en, 1), pct=round(pct, 1),
                pct_text=int(round(pct)), median=round(float(np.median(all74)), 1), yearly=round(yearly, 1),
                share_pct=round(share), wettest=int(wettest), wettest_mm=round(rain[wettest]),
                wettest_is_el=bool(wettest in years), rand_lo=round(lo, 1), rand_hi=round(hi, 1),
                rand_max=round(float(draws.max()), 1), rand_ge=int((draws >= pct).sum()), rand_n=SHUFFLES,
                p_autumn=round(au["p"], 3), n_wetter=au["n_wetter"], autumn_years=years)


def indices() -> dict:
    o = enso.oni("oni")
    last = o.iloc[-1]
    assert (last.season, int(last.year)) == ("ASO", 2026) and round(float(last.oni), 2) == ONI_ASO, last
    aso = o.query("season == 'ASO'").sort_values("oni", ascending=False).reset_index(drop=True)
    r = enso.oni("roni")
    rl = r.iloc[-1]
    assert (rl.season, int(rl.year)) == ("ASO", 2026) and round(float(rl.oni), 2) == RONI_ASO, rl
    raso = r.query("season == 'ASO'").sort_values("oni", ascending=False).reset_index(drop=True)
    assert len(aso) == 77 and len(raso) == 77, (len(aso), len(raso))
    rank = int((aso.oni > ONI_ASO).sum()) + 1
    rrank = int((raso.oni > RONI_ASO).sum()) + 1
    nxt = [(int(aso.year[k]), round(float(aso.oni[k]), 2)) for k in (1, 2)]
    rnxt = [(int(raso.year[k]), round(float(raso.oni[k]), 2)) for k in (0, 1)]
    assert rank == 1 and nxt == [(1997, 2.04), (2015, 2.02)], (rank, nxt)
    assert rrank == 2 and rnxt[0] == (1997, 2.07), (rrank, rnxt)
    assert int(raso.year[0]) == 1997 and round(float(raso.oni[0]), 2) == 2.07
    return dict(oni=ONI_ASO, oni_shown=round(ONI_ASO, 1), oni_rank=rank, oni_next=nxt,
                roni=RONI_ASO, roni_rank=rrank, roni_top=(1997, 2.07), n_aso=len(aso))


def strong_and_winter() -> dict:
    """The autumn and winter counts (all El Niño seasons, ONI at least +0.5) and the strong ones (ONI at least +1.5)."""
    a = enso.result("OND")
    w = enso.result("JFM")
    sa = enso.result("OND", 1.5)
    sw = enso.result("JFM", 1.5)
    assert (a["n_wetter"], len(a["years"])) == (21, 26) and (w["n_wetter"], len(w["years"])) == (11, 22)
    assert a["wetter"][2023] is False and a["wetter"][1965] is False, "1965 and 2023 are the drier strong autumns"
    s_aut = (sa["n_wetter"], len(sa["years"]))
    s_win = (sw["n_wetter"], len(sw["years"]))
    assert s_aut == (4, 6), s_aut
    return dict(strong_autumn=s_aut[0], strong_autumn_n=s_aut[1], strong_winter=s_win[0], strong_winter_n=s_win[1],
                p_autumn=round(a["p"], 3), p_winter=round(w["p"], 2), rho_autumn=round(a["rho"], 2),
                rho_winter=round(w["rho"], 2), autumn_mm_mean=round(a["mean"], 1), winter_mm_mean=round(w["mean"], 1))


def composite_check() -> dict:
    d = np.load(EL2 / "composite_ond_mean.npz")
    p = d["pct"][np.isfinite(d["pct"])]
    assert p.size == 621 and 110 < p.min() < 112 and 140 < p.max() < 142, (p.min(), p.max())
    return dict(cells=int(p.size), map_min=round(float(p.min())), map_max=round(float(p.max())),
                map_median=round(float(np.median(p))))


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    idx = indices()
    ir = iran()
    assert ir["pct_text"] == 123 and round(ir["mm_el"]) == 74 and round(ir["mean74"]) == 60
    assert ir["wettest"] == 1982 and ir["wettest_mm"] == 114 and ir["wettest_is_el"]
    assert round(ir["yearly"]) == 226 and ir["share_pct"] == 27
    assert round(ir["rand_lo"]) == 90 and round(ir["rand_hi"]) == 111 and ir["rand_ge"] == 0, (ir["rand_lo"], ir["rand_hi"])
    st = strong_and_winter()
    comp = composite_check()
    wk = week()
    tinted = wk["tinted"]
    assert tinted > 0 and wk["nino34"] == wk["nino34"], wk
    bm = blue_marble()
    nums = dict(week=dict(days=WEEK, dates_shown="۱۷ تا ۲۳ اکتبر ۲۰۲۶", dataset="ncdcOisst21Agg_LonPM180", var="anom",
                          baseline="1971-2000 (the dataset's own metadata: 'Climatology is based on 1971-2000'; "
                                   "the brief asked for 1991-2020, which this copy does not carry: the reel says 1971-2000)",
                          nino34_week_mean_c=wk["nino34"], nino34_daily_c=wk["nino34_daily"],
                          nino34_note="not on screen: above CPC's 8 Oct figure (about 2.1) and ONI 2.46; flagged in the report",
                          tinted_cells=tinted, cells=wk["cells"], tint_at=TINT_AT),
                **idx, **{f"iran_{k}": v for k, v in ir.items()}, **st, map=comp,
                bluemarble=bm.name, scalars=dict(strong_autumn_text="۴ از ۶", five_dam_bar_max=3.0))
    nums["scenes"] = dict(autumn_shown="۲۱ از ۲۶", winter_shown="۱۱ از ۲۲", pct_shown="۱۲۳٪", mean_shown="۶۰",
                          mm_shown="۷۴", pct_more_shown="۲۳٪")
    (DATA / "numbers.json").write_text(json.dumps(nums, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(nums, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
