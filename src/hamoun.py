"""WHERE DID THE HAMOUN GO? The Hamoun lakes (Sistan, on the Iran-Afghanistan border) in late spring every
year 1985-2026: one true-colour picture a year and the open water's area, from get_hamoun.py's cache.

Measured data only (every rule is in get_hamoun.py's docstring):
- Area: the Hamoun lakes (JRC's extent of any water 1984-2021, its main body: Puzak, Sabari, Hirmand,
  4,267 km2; the Chah-nimeh reservoirs, rivers and canals left out), measured at 30 m on each accepted pass
  of Landsat path 157 (rows 038 + 039, one date) between 1 May and 15 June (widened to 15 April - 20 June
  where fewer than two passes are accepted), the year's median over its passes.
- RULE, chosen against JRC's Monthly Water History (1987-2021, 32 years with a JRC month that saw at least
  half the lakes) and the true colour: water = MNDWI > 0 and SWIR1 < 0.15. In the 23 wet years (JRC >= 500
  km2) it reads a median 4.5 % above JRC (15 years within 10 %; 10-90 % of years -5 % to +20 %); in the 8 dry
  years (JRC < 100 km2) within -44 to +22 km2 of JRC (median -1.5). Pooled agreement of the water pixels
  (intersection over union) 0.85. Where it reads more than JRC the true colour shows very turbid flood water
  (1987, 1988, 1994, 1996: JRC's classifier takes it for land) and water among reeds; where it reads less
  (2019, 2013, 2021) the flood rose or fell within the month (JRC's month covers all its scenes, a pass one
  day). NIR caps (NIR < 0.10: -88 %, < 0.15: -55 %) and NDWI > 0 (-24 %) miss the turbid water; MNDWI > 0
  alone counts damp salt and mud on a drying bed (2000: 51 km2, JRC 3; 2006: 48, JRC 16); MNDWI > 0.1 halves
  that; the SWIR1 cap removes it (damp salt keeps SWIR1 near 0.18-0.30, water below 0.1 even when turbid).
- Reedbeds: water is what shows from above. A pixel where water dominates counts even with plants in it
  ("with plants" = MNDWI > 0 and NDVI > 0.2: 30-150 km2 in wet years, mostly in Puzak); dense green reeds
  (NDVI > 0.3, MNDWI < 0) are not counted even when flooded beneath (JRC counts neither).
- Iran and Afghanistan: the same areas split by the Natural Earth 10 m border (a line about 1 km accurate;
  for the log only: the reel names neither country as a cause).
- Pictures: per year the median of the accepted path-157 passes' cloud-free pixels (get_urmia's recipe);
  gaps narrower than about 5 pixels (700 m: Landsat 7's stripes where every pass has its gap in the same
  place, at the scenes' edges) interpolated across from both sides of the same picture; on the land the
  neighbouring paths' scenes before path 157's striped passes, joined with matched tones; land still unseen
  taken from the nearest year with a view; the lakes (grown by 2 pixels) are never filled from another
  date: a speck of at most 25 pixels (0.5 km2) that QA_PIXEL flagged in every pass takes its nearest seen
  pixel of the same picture, a larger hole stays and is logged. NO_PICTURE lists the years left out and why.

    python -I src/hamoun.py > outputs/hamoun_log.txt   # the log; outputs/hamoun_area.csv, hamoun_calibration.csv
    python -I src/hamoun.py --check [years]            # quick looks: outputs/hamoun_check/ (calib_<year>.png)
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import get_hamoun as gh  # noqa: E402  (reads its cache only)

ROOT = Path(__file__).resolve().parents[1]
DATA = gh.DATA
CHECK = ROOT / "outputs" / "hamoun_check"
YEARS = gh.YEARS
RULE = "mndwi0_swir15"                            # MNDWI > 0 and SWIR1 < 0.15: chosen by the calibration
SLC = ("only Landsat 7 after its scan-line failure (31 May 2003): its passes have their stripe gaps in nearly the "
       "same places, so the median changes tone along them and stripes show on the land at the scenes' edges")
NO_PICTURE = {                                    # year -> why it has no picture (its area stays in the series)
    2002: "its passes span April's flood pulse (18 and 26 April: 182 and 308 km2) and June's dry bed (13 June: 0): "
          "the median picture is a ghost of both",
    2003: "one accepted pass (7 May 2003): clouds over Hamoun-e Hirmand leave 9 % of the lakes unseen",
    2004: SLC, 2005: SLC, 2006: SLC, 2007: SLC, 2012: SLC,
    2008: "two passes 24 days apart (4 May, Landsat 7 with its stripes: 839 km2; 28 May, Landsat 5: 430 km2): the "
          "median picture blends two shorelines, with a blocky patch where the stripes fall",
    1994: "one pass (22 May; 23 June is past 31 Khordad): 3.5 % of the lakes unseen under its cloud flags, black "
          "holes in the picture",
    2009: "two passes (29 April, 15 May) both flag the south-east of Hamoun-e Puzak and differ there: 1.0 % of "
          "the lakes unseen, black spots in the picture",
}
LEFT_OUT = {1985: "no Landsat scene of the lakes in the archive after 26 March 1985 (path 157: January-March only)",
            1986: "no pass with 85 % of the lakes clear between 15 April and 20 June: 30 April has row 039 only "
                  "(41 % of the lakes), 16 May 81 % clear with whole tiles under cloud, 17 June 54 % clear"}
FEATHER = 8                                       # px: two layers blend over this width where they meet
SPECK = 25                                        # px (0.5 km2): a hole in the lakes this small is filled from its neighbours
GAP = 2                                           # px: gaps narrower than a disk of this radius are interpolated
WET, DRY = 500, 100                               # km2 of JRC water: the calibration's wet and dry years
MIN_JRC_OBS = 0.5                                 # a pass enters the calibration if JRC saw half the lakes


@functools.cache
def passes() -> pd.DataFrame:
    return gh.table()


@functools.cache
def series() -> pd.DataFrame:
    return gh.annual(passes())


def calibration() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per year (to 2021) the median over its counted passes of each rule's area and JRC's, on the pixels
    both see; and per rule the summary over the years."""
    df = passes()
    d = df[df.counts & df.jrc.notna() & (df.jrc_obs >= MIN_JRC_OBS)]
    g = d.groupby("year")
    per = pd.DataFrame({"n": g.size(), "jrc": g["jrc"].median(), "jrc_obs": g["jrc_obs"].median()})
    for r in gh.RULES:
        per[r] = g[f"{r}_co"].median()
        per[f"{r}_err"] = per[r] - per["jrc"]
        per[f"{r}_pct"] = 100 * per[f"{r}_err"] / per["jrc"]
    summ = []
    for r in gh.RULES:
        wet, dry, mid = per[per.jrc >= WET], per[per.jrc < DRY], per[(per.jrc >= DRY) & (per.jrc < WET)]
        some = per[per.jrc >= 20]
        logr = np.log(per.loc[some.index, r] / some.jrc)
        both, com, om = d[f"{r}_both"].sum(), d[f"{r}_commission"].sum(), d[f"{r}_omission"].sum()
        summ.append(dict(rule=r, text=gh.RULE_TEXT[r], iou=both / (both + com + om),
                         wet_n=len(wet), wet_bias_pct=wet[f"{r}_pct"].median(), wet_abs_pct=wet[f"{r}_pct"].abs().median(),
                         wet_lo_pct=wet[f"{r}_pct"].min(), wet_hi_pct=wet[f"{r}_pct"].max(),
                         wet_p10_pct=wet[f"{r}_pct"].quantile(0.1), wet_p90_pct=wet[f"{r}_pct"].quantile(0.9),
                         wet_within10=int((wet[f"{r}_pct"].abs() <= 10).sum()),
                         mid_n=len(mid), mid_abs_pct=mid[f"{r}_pct"].abs().median(),
                         dry_n=len(dry), dry_bias_km2=dry[f"{r}_err"].median(), dry_abs_km2=dry[f"{r}_err"].abs().median(),
                         dry_lo_km2=dry[f"{r}_err"].min(), dry_hi_km2=dry[f"{r}_err"].max(),
                         dry_years=" ".join(str(y) for y in dry.index),
                         med_abs_log=float(np.median(np.abs(logr))),
                         commission_km2=d[f"{r}_commission"].median(), omission_km2=d[f"{r}_omission"].median()))
    return per, pd.DataFrame(summ).set_index("rule")


@functools.cache
def jrc_months() -> pd.DataFrame:
    """JRC's own monthly water on the lakes, May and June 1985-2021 (from the cached tiles): the share of
    the lakes JRC observed, its raw water (km2) and the water scaled to the lakes by the strata."""
    g = gh.grids()
    flat, sidx, K = g["flat"], g["sidx"], len(g["ids"])
    roi = np.bincount(sidx, minlength=K).astype(float)
    rows = []
    for y in range(YEARS[0], gh.JRC_LAST + 1):
        for m in (5, 6):
            f = DATA / "jrc" / f"{y}_{m:02d}.npz"
            if not f.exists():
                continue
            code = np.load(f)["code"].ravel()[flat]
            obs = np.bincount(sidx, weights=(code == 1) | (code == 2), minlength=K)
            wat = np.bincount(sidx, weights=code == 2, minlength=K)
            seen = obs >= gh.MIN_CLEAR_STRATUM * roi
            overall = wat.sum() / obs.sum() if obs.sum() else np.nan
            share = np.where(seen, wat / np.maximum(obs, 1), overall)
            rows.append(dict(year=y, month=m, observed=obs.sum() / roi.sum(), raw_km2=wat.sum() * gh.PIX_KM2,
                             scaled_km2=float((share * roi).sum() * gh.PIX_KM2)))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------- pictures

def _matched(base: np.ndarray, layer: np.ndarray, over: np.ndarray) -> np.ndarray:
    """The layer in the base's tones: per band the least-squares gain and offset over their overlap."""
    out = layer.copy()
    for b in range(3):
        x, y = layer[b][over].astype(np.float64), base[b][over].astype(np.float64)
        gain, offset = np.linalg.lstsq(np.vstack([x, np.ones_like(x)]).T, y, rcond=None)[0]
        out[b] = gain * layer[b] + offset
    return out


def _join(layers: list) -> np.ndarray:
    """One picture from the layers: the first, then each further layer matched to it and blended in
    over FEATHER pixels where it meets the picture so far (as urmia.py)."""
    from scipy import ndimage
    rgb = layers[0].astype(np.float32)
    for layer in layers[1:]:
        layer = layer.astype(np.float32)
        have, new = np.isfinite(rgb[0]), np.isfinite(layer[0])
        if not (~have & new).any():
            continue
        if (have & new).sum() >= 1000:
            layer = _matched(rgb, layer, have & new)
        d = ndimage.distance_transform_edt(have)
        edge = have & new & (d <= FEATHER)
        w = d[edge] / FEATHER
        rgb[:, edge] = w * rgb[:, edge] + (1 - w) * layer[:, edge]
        rgb[:, ~have & new] = layer[:, ~have & new]
    return rgb


def _inpaint_thin(rgb: np.ndarray) -> tuple[np.ndarray, int]:
    """Gaps narrower than a disk of radius GAP (Landsat 7's stripes that no pass fills, at most about 5
    pixels or 700 m wide) interpolated across from both sides of the same picture: a Gaussian-weighted mean
    of the seen pixels (sigma 1.5 pixels). Wider holes are left."""
    from scipy import ndimage
    gap = np.isnan(rgb).any(axis=0)
    thin = gap & ~ndimage.binary_opening(gap, structure=gh.disk(GAP))
    if not thin.any():
        return rgb, 0
    seen = (~gap).astype(np.float32)
    den = ndimage.gaussian_filter(seen, 1.5)
    out = rgb.copy()
    for b in range(3):
        num = ndimage.gaussian_filter(np.where(gap, 0, rgb[b]).astype(np.float32), 1.5)
        ok = thin & (den > 0.05)
        out[b][ok] = num[ok] / den[ok]
    return out, int((thin & (den > 0.05)).sum())


@functools.cache
def _rgb(year: int) -> tuple[np.ndarray, int]:
    """Inside the lakes (grown by 2 pixels): path 157's whole passes, then its striped ones, thin gaps
    interpolated. On the land: path 157's whole passes, then the other paths, then (only in a year without
    a whole pass) the striped passes; what is left the nearest year fills (colour)."""
    from scipy import ndimage
    z = np.load(DATA / f"colour_{year}.npz")
    strict, loose, fills = list(z["strict"]), list(z["loose"]), list(z["fills"])
    lake, n = _inpaint_thin(_join(strict + loose))
    land, m = _inpaint_thin(_join(strict + fills) if strict else _join(loose + fills))
    ring = ndimage.binary_dilation(lakes(), iterations=2)
    return np.where(ring, lake, land), int(n + m)


def years() -> list:
    """The years with a picture."""
    return [y for y in range(YEARS[0], YEARS[1] + 1) if y not in NO_PICTURE and (DATA / f"colour_{y}.npz").exists()]


def lakes() -> np.ndarray:
    return gh.grids()["pic_lakes"]


def colour(year: int) -> dict:
    """The year's picture (reflectance, 3 x 1240 x 1080): land without a view from the nearest year with one;
    inside the lakes (grown by 2 pixels, as get_hamoun) never from another year, but a hole of at most
    SPECK pixels (a few cells QA_PIXEL flagged in every pass) takes its nearest seen pixel of the same picture."""
    from scipy import ndimage
    rgb, stripes = _rgb(year)
    rgb = rgb.copy()
    ring = ndimage.binary_dilation(lakes(), iterations=2)
    hole = np.isnan(rgb).any(axis=0) & ~ring
    filled = 0
    for d in (1, -1, 2, -2, 3, -3):
        other = year + d
        if not hole.any() or other in NO_PICTURE or not (DATA / f"colour_{other}.npz").exists():
            continue
        src = _rgb(other)[0]
        ok = hole & ~np.isnan(src).any(axis=0)
        rgb[:, ok] = src[:, ok]
        hole &= ~ok
        filled += int(ok.sum())
    gap = np.isnan(rgb).any(axis=0)
    lab, n = ndimage.label(gap & ring)
    sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1)) if n else np.array([])
    small = np.isin(lab, 1 + np.flatnonzero(sizes <= SPECK)) & (lab > 0)
    if small.any():
        _, (iy, ix) = ndimage.distance_transform_edt(gap, return_indices=True)
        rgb[:, small] = rgb[:, iy[small], ix[small]]
    z = np.load(DATA / f"colour_{year}.npz")
    return dict(rgb=rgb, passes=[str(p) for p in z["passes"]], items=[str(i) for i in z["items"]],
                window=str(z["window"]), n_fill_layers=len(z["fills"]), filled=filled / rgb[0].size,
                specks=int(small.sum()), big_holes=int((sizes > SPECK).sum()), stripes=stripes,
                lake_unseen=float(np.isnan(rgb[0])[lakes()].mean()), unseen=float(np.isnan(rgb[0]).mean()))


def display(rgb: np.ndarray) -> np.ndarray:
    """Reflectance to 8-bit with one fixed stretch for every year (so years compare): 0-0.42, gamma 1/1.5."""
    x = np.clip(np.nan_to_num(rgb, nan=0.0) / 0.42, 0, 1) ** (1 / 1.5)
    return (255 * np.moveaxis(x, 0, -1)).astype(np.uint8)


def water_map(year: int, rule: str = RULE) -> np.ndarray:
    """The year's water share (0-1) per picture pixel: the median over its counted passes, NaN unseen."""
    names = passes().query("counts and year == @year")["name"]
    stack = []
    for n in names:
        a = np.load(DATA / "maps" / f"{n}.npz")[rule].astype(np.float32)
        stack.append(np.where(a == 255, np.nan, a / 100))
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmedian(np.stack(stack), axis=0)


def check() -> None:
    """Quick looks in outputs/hamoun_check/: each year's picture and a contact sheet of all years."""
    from PIL import Image, ImageDraw
    CHECK.mkdir(parents=True, exist_ok=True)
    thumbs, halves = [], []
    for y in range(YEARS[0], YEARS[1] + 1):
        if not (DATA / f"colour_{y}.npz").exists():
            continue
        c = colour(y)
        im = Image.fromarray(display(c["rgb"]))
        im.save(CHECK / f"hamoun_{y}.png")
        label = f"{y}{' X' if y in NO_PICTURE else ''}"
        t = im.resize((im.width // 4, im.height // 4), Image.LANCZOS)
        ImageDraw.Draw(t).text((6, 4), label, fill=(255, 0, 0))
        thumbs.append(t)
        hf = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
        ImageDraw.Draw(hf).text((8, 6), label, fill=(255, 0, 0))
        halves.append((y, hf))
    cols = 7
    w, h = thumbs[0].size
    sheet = Image.new("RGB", (cols * w, -(-len(thumbs) // cols) * h), "white")
    for k, t in enumerate(thumbs):
        sheet.paste(t, ((k % cols) * w, (k // cols) * h))
    sheet.save(CHECK / "contact_sheet.png")
    w, h = halves[0][1].size
    for k in range(0, len(halves), 4):                 # four years at half size: for seams and stripes
        group = halves[k:k + 4]
        quad = Image.new("RGB", (2 * w, 2 * h), "white")
        for j, (_, hf) in enumerate(group):
            quad.paste(hf, ((j % 2) * w, (j // 2) * h))
        quad.save(CHECK / f"quad_{group[0][0]}-{group[-1][0]}.png")
    print(f"wrote {len(thumbs)} pictures, the contact sheet and {-(-len(halves) // 4)} quads to {CHECK}")


def calib_figure(year: int, crop: tuple | None = None) -> None:
    """One year's picture beside each rule's water and JRC's (medians over its passes), for the eye:
    outputs/hamoun_check/calib_<year>.png; crop = (row0, row1, col0, col1) on the picture grid."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    c = colour(year)
    r0, r1, c0, c1 = crop or (0, gh.PIC_SHAPE[0], 0, gh.PIC_SHAPE[1])
    panels = [("true colour", display(c["rgb"]))] + [(gh.RULE_TEXT[r], water_map(year, r)) for r in gh.RULES]
    if year <= gh.JRC_LAST:
        panels.append(("JRC monthly", water_map(year, "jrc")))
    panels.append(("green plants NDVI>0.3", water_map(year, "veg")))
    s = series().loc[year]
    fig, axes = plt.subplots(3, 4, figsize=(20, 18))
    for ax, (title, a) in zip(axes.ravel(), panels):
        if a.ndim == 3:
            ax.imshow(a[r0:r1, c0:c1])
        else:
            ax.imshow(np.where(lakes(), a, np.nan)[r0:r1, c0:c1], cmap="Blues", vmin=0, vmax=1)
            k = {v: k for k, v in gh.RULE_TEXT.items()}.get(title)
            if k:
                title += f": {s[k]:,.0f} km2"
        ax.set_title(title, fontsize=11)
        ax.set_xticks([])
        ax.set_yticks([])
    for ax in axes.ravel()[len(panels):]:
        ax.axis("off")
    fig.suptitle(f"Hamoun, late spring {year}: water share per picture pixel inside the lakes", fontsize=13)
    fig.tight_layout()
    fig.savefig(CHECK / f"calib_{year}.png", dpi=70)
    plt.close(fig)


# ------------------------------------------------------------------------------------------------ log

FAMILY = ("mndwi0", "mndwi01", "mndwi0_swir10", "mndwi0_swir15")   # the rules that see turbid water
NEARLY_DRY = 100                                  # km2: under this a spring is "nearly dry" (2.3 % of the lakes)


def lakes_km2() -> dict:
    g = gh.grids()
    cty = np.array([gh.stratum_country(sid) for sid in g["ids"]])
    px = np.bincount(g["sidx"], minlength=len(g["ids"]))
    return dict(total=px.sum() * gh.PIX_KM2, iran=px[cty == 1].sum() * gh.PIX_KM2, afghanistan=px[cty == 2].sum() * gh.PIX_KM2)


def flags(y: int) -> list:
    """What to know about a year's number."""
    s, df = series(), passes()
    r = s.loc[y]
    out = []
    if r.window == "wide":
        out.append("window widened to 15 Apr-20 Jun")
    if r.n_passes == 1:
        out.append("one pass")
    used = df[df.counts & (df.year == y)]
    if used.slc_off.all():
        out.append("Landsat 7 SLC-off only")
    fam = [r[k] for k in FAMILY]
    if max(fam) - min(fam) > 20 and max(fam) > 1.5 * max(min(fam), 1):
        out.append(f"rule-sensitive ({min(fam):.0f}-{max(fam):.0f})")
    lo, hi = r[RULE + "_low"], r[RULE + "_high"]
    if hi - lo > 100 and hi - lo > 0.5 * max(r[RULE], 1):
        out.append(f"changing within the window ({lo:.0f}-{hi:.0f})")
    return out


def picture_scenes(c: dict) -> str:
    by = {}
    for i in c["items"]:
        pr = i.split("_")[2]
        by.setdefault(pr, []).append(i)
    return "; ".join(f"{pr} {len(v)}" for pr, v in sorted(by.items()))


def main() -> None:
    df, s = passes(), series()
    lk = lakes_km2()
    print(__doc__.split("\n\n")[0].replace("\n", " "))
    print(f"\nTHE LAKES: {lk['total']:,.0f} km2 on the 30-m grid (JRC any water 1984-2021, its main body); by the "
          f"Natural Earth border {lk['iran']:,.0f} km2 in Iran, {lk['afghanistan']:,.0f} km2 in Afghanistan.")
    print(f"RULE (chosen below): {RULE} = {gh.RULE_TEXT[RULE]}")

    jm = jrc_months()
    print("\nJRC MONTHLY WATER HISTORY on the lakes, by itself (its own coverage; km2 scaled to the lakes by the strata; "
          "'obs' = share of the lakes JRC observed that month):")
    for y, g in jm.groupby("year"):
        print(f"  {y}: " + "   ".join(f"{'May' if r.month == 5 else 'June'} {r.scaled_km2:6.0f} (obs {100 * r.observed:3.0f} %)"
                                       for _, r in g.iterrows()))

    per, summ = calibration()
    print("\nCALIBRATION against JRC Monthly Water History: each counted pass against JRC's month of the pass, on the "
          f"pixels clear in the pass and observed by JRC (passes where JRC saw at least {100 * MIN_JRC_OBS:.0f} % of "
          "the lakes), both scaled to the lakes by the same strata; per year the median over its passes, km2 "
          "(difference from JRC in %):")
    print(f"{'year':>4} {'n':>2} {'JRC':>6} " + " ".join(f"{r:>17}" for r in gh.RULES))
    for y, r in per.iterrows():
        print(f"{y:>4} {int(r.n):>2} {r.jrc:6.0f} " + " ".join(
            f"{r[k]:7.0f} ({r[k + '_pct']:+5.0f}%)" if r.jrc >= 20 else f"{r[k]:7.0f} ({r[k + '_err']:+5.0f}km2)"
            for k in gh.RULES))
    print(f"\nper rule: wet years JRC >= {WET} km2 (bias and |error| in %, median; lo/hi = the extreme years), "
          f"dry years JRC < {DRY} km2 (km2); iou = pooled intersection over union of the water pixels; "
          "commission/omission = median per pass, km2 on the pixels both see:")
    print(summ.drop(columns="text").round(2).to_string())

    print("\nPASSES (path 157, rows 038+039 of one date; shift = against the reference pass, pixels east, south):")
    for _, r in df.iterrows():
        flag = "COUNTED" if r.counts else ("accepted, outside the year's window" if r.accepted else "left out")
        extra = "" if pd.isna(r.get("valid")) else (
            f" {r.platform} {r.tier}{' SLC-off' if r.slc_off else ''} rows {r.rows} scene cloud {r.cloud_scene:.0f}% "
            f"valid {100 * r.valid:.1f}% clear {100 * r.clear:.1f}% (rescued {100 * r.rescued:.1f}%, QA cloud "
            f"{100 * r.qa_cloud:.1f}%, snow {100 * r.qa_snow:.1f}%) shift ({r.shift_x:+.2f},{r.shift_y:+.2f}) "
            f"peak {r.shift_peak:.0f}; {RULE} {r[RULE]:.0f} km2")
        print(f"  {r['name']} {flag}{extra}{'; ' + r.reason if r.reason else ''}")

    print("\nAREA (km2) of open water, late spring, the median over the year's counted passes. low/high = its passes; "
          "family = the range over the MNDWI rules that see turbid water (" + ", ".join(FAMILY) + "); JRC = the "
          "calibration's JRC (same passes, pixels both see); with plants = MNDWI > 0 and NDVI > 0.2:")
    print(f"{'year':>4} {'window':>7} {'n':>2} {'platforms':>9} {RULE:>9} {'low':>6} {'high':>6} "
          + " ".join(f"{r:>13}" for r in gh.RULES if r != RULE)
          + f" {'family':>11} {'JRC':>6} {'Iran':>6} {'Afgh.':>6} {'plants':>6}  flags")
    for y in range(YEARS[0], YEARS[1] + 1):
        if y not in s.index:
            print(f"{y:>4}  LEFT OUT: {LEFT_OUT.get(y, 'no accepted pass')}")
            continue
        r = s.loc[y]
        fam = [r[k] for k in FAMILY]
        jrc = per.jrc.get(y, np.nan) if len(per) else np.nan
        print(f"{y:>4} {r.window:>7} {int(r.n_passes):>2} {r.platforms:>9} {r[RULE]:9.0f} {r[RULE + '_low']:6.0f} "
              f"{r[RULE + '_high']:6.0f} " + " ".join(f"{r[k]:13.0f}" for k in gh.RULES if k != RULE)
              + f" {min(fam):5.0f}-{max(fam):<5.0f} {jrc:6.0f} {r[RULE + '_iran']:6.0f} {r[RULE + '_afg']:6.0f} "
              f"{r.vegwater:6.0f}  {'; '.join(flags(y))}")

    print("\nPICTURES (true colour on the 1080 x 1240 grid):")
    for y in range(YEARS[0], YEARS[1] + 1):
        if y in NO_PICTURE:
            print(f"  {y}: LEFT OUT: {NO_PICTURE[y]}")
            continue
        if not (DATA / f"colour_{y}.npz").exists():
            print(f"  {y}: no picture ({LEFT_OUT.get(y, 'no accepted pass')})")
            continue
        c = colour(y)
        print(f"  {y} ({c['window']} window): path-157 passes {', '.join(p[5:] for p in c['passes'])}; scenes per "
              f"path-row: {picture_scenes(c)}; thin gaps interpolated {c['stripes']} px; land from a nearby year "
              f"{100 * c['filled']:.1f} %; specks filled "
              f"{c['specks']} px; lake unseen {100 * c['lake_unseen']:.2f} % ({c['big_holes']} holes > {SPECK} px); "
              f"still unseen {100 * c['unseen']:.2f} %")

    a = s[RULE]
    top = a.idxmax()
    print("\nHEADLINES (" + RULE + "):")
    print(f"  wettest late spring: {top}: {a.max():,.0f} km2 ({100 * a.max() / lk['total']:.0f} % of the lakes' "
          f"{lk['total']:,.0f} km2)")
    near = a[a >= 0.95 * a.max()]
    print(f"  within 5 % of it (one class: the lakes full): " + ", ".join(f"{y} {v:,.0f}" for y, v in near.items()))
    print(f"  driest: " + ", ".join(f"{y} {v:.0f}" for y, v in a.nsmallest(8).items()) + " km2")
    if 2026 in a.index:
        print(f"  2026: {a.loc[2026]:,.0f} km2 = {100 * a.loc[2026] / a.max():.0f} % of {top}")
    for n in (10, 20, 26):
        last = a[a.index > YEARS[1] - n]
        print(f"  last {n} springs ({YEARS[1] - n + 1}-{YEARS[1]}): {len(last)} measured, {int((last < NEARLY_DRY).sum())} "
              f"under {NEARLY_DRY} km2: {sorted(int(y) for y in last[last < NEARLY_DRY].index)}")
    out = pd.DataFrame({"area_km2": a.round(0), "low_km2": s[RULE + "_low"].round(0), "high_km2": s[RULE + "_high"].round(0),
                        "family_min_km2": s[list(FAMILY)].min(axis=1).round(0), "family_max_km2": s[list(FAMILY)].max(axis=1).round(0),
                        "jrc_km2": per.jrc.reindex(s.index).round(0), "iran_km2": s[RULE + "_iran"].round(0),
                        "afghanistan_km2": s[RULE + "_afg"].round(0), "window": s.window, "n_passes": s.n_passes,
                        "dates": s.dates, "platforms": s.platforms, "flags": [";".join(flags(y)) for y in s.index]})
    out.index.name = "year"
    (ROOT / "outputs").mkdir(exist_ok=True)
    out.to_csv(ROOT / "outputs" / "hamoun_area.csv")
    per.round(1).to_csv(ROOT / "outputs" / "hamoun_calibration.csv")
    early = a[a.index < 2000]
    print(f"  {early.index.min()}-1999: {len(early)} springs measured, {int((early < NEARLY_DRY).sum())} under {NEARLY_DRY} km2; "
          f"median {early.median():,.0f} km2; 2000-2026 median {a[a.index >= 2000].median():,.0f} km2")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
        CALIB_YEARS = [int(a) for a in sys.argv[sys.argv.index("--check") + 1:] if a.isdigit()]
        for y in CALIB_YEARS:
            calib_figure(y)
    else:
        main()
