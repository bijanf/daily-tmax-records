"""One record plot per station, plus a browsable index and optional carousels.

    outputs/stations/<region>/<country>/<ID>_<name>.png   wide plot per station: one bar
        per day from 1 Jan to the last day of data, height = record daily maximum
        temperature, label = year the record was set
    outputs/stations/index.html                            every station, sortable, with thumbnails
    outputs/stations/carousels/<ID>_<name>/                1080 x 1350 slides + PDF (--carousel)

Run after station_records.py:
    python -I src/plot_stations.py --region Europe
    python -I src/plot_stations.py                         # every station
    python -I src/plot_stations.py --carousel GM000003342  # Instagram / LinkedIn slides
"""

from __future__ import annotations

import argparse
import calendar
import html
import re
import string
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from PIL import Image  # noqa: E402

import viz  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "stations"
RAW = ROOT / "data" / "raw"
UPPER = {"Ap", "Ny", "Wso", "Afb", "Nws", "Faa", "Wfo", "Nyc", "Usa", "Ii", "Iii"}
# GHCN-Daily cuts names at 30 characters; full names for stations that need them
NAME_OVERRIDES = {
    "SP000009981": "Tortosa, Observatori de l'Ebre",
    "USW00094728": "New York Central Park, NY",
    "GME00102308": "Görlitz",
    "GM000004199": "München-Nymphenburg",
    "GME00102380": "Nürnberg",
    "GME00120994": "Angermünde",
    "GM000010147": "Hamburg-Fuhlsbüttel",
    "GME00111457": "Kahler Asten",
    "GM000010962": "Hohenpeißenberg",
    "GMM00010761": "Weißenburg",
    "SZ000002220": "Säntis",
    "SZ000003700": "Zürich-Fluntern",
    "SP000060010": "Izaña",
}


def ghcnd_version() -> str:
    m = re.search(r"is (\d+\.\d+)", (RAW / "ghcnd-version.txt").read_text())
    return m.group(1) if m else ""


def display_name(meta: dict) -> str:
    if meta["id"] in NAME_OVERRIDES:
        return NAME_OVERRIDES[meta["id"]]
    words = [w.upper() if w in UPPER else w for w in string.capwords(meta["name"].lower()).split()]
    name = re.sub(r"([-/])(\w)", lambda m: m[1] + m[2].upper(), " ".join(words))
    if meta["country"].startswith("United States") and isinstance(meta["state"], str):
        return f"{name}, {meta['state']}"
    return name


def country_label(country: str) -> str:
    return "USA" if country == "United States" else re.sub(r" \[.*\]", "", country)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def station_path(meta: dict) -> Path:
    return (OUT / slug(meta["region"]) / slug(country_label(meta["country"]))
            / f"{meta['id']}_{slug(meta['name'])}.png")


def day_label(md: str) -> str:
    d = pd.Timestamp(f"2001-{md}")
    return f"{d.day} {d.strftime('%b')}"


def texts(meta: dict, version: str) -> dict:
    fy = int(meta["final_year"])
    name, country = display_name(meta), country_label(meta["country"])
    first, last = meta["first_date"][:4], meta["last_date"][:4]
    k, n, exp = meta["records_2020s"], meta["n_days"], meta["expected_2020s"]
    src = meta.get("supplement_source") if isinstance(meta.get("supplement_source"), str) else ""
    extra = (f" · latest weeks from {src} open data (identical to GHCN-Daily where both exist)"
             if src and meta.get("n_days_supplement", 0) > 0 else "")
    if meta["has_final_year"]:
        this_year = f"{meta['records_final_year']} set in {fy}"
    else:
        this_year = f"no {fy} data yet (latest {meta['last_date']})"
    return {
        "name": name,
        "country": country,
        "title": f"{name}, {country}",
        "subtitle": (
            f"Record daily maximum temperature for every day from 1 Jan to {day_label(meta['end_md'])}, "
            f"the highest value in {first}–{last} ({meta['n_complete_years']} complete years). "
            f"Label = year the record was set.\n"
            f"{k} of {n} days have their record in the 2020s; a stable climate would give about "
            f"{exp:.0f} · {this_year}"
        ),
        "footer": (
            f"Data: NOAA NCEI GHCN-Daily v{version} · station {meta['id']} · {meta['lat']:.2f}°, "
            f"{meta['lon']:.2f}°, {meta['elev']:.0f} m · raw station data; GHCN-flagged values and "
            f">6σ outliers removed · ties go to the year that first set the record · 29 Feb not "
            f"shown{extra} · {viz.CREDIT}"
        ),
        "source": f"Data: NOAA NCEI GHCN-Daily v{version}{' + ' + src if extra else ''} · station {meta['id']}",
        "first": first,
    }


def station_frame(rec: pd.DataFrame, final_year: int) -> pd.DataFrame:
    rec = rec.copy()
    rec["date"] = pd.to_datetime(f"{final_year}-" + rec["md"])
    return rec


def render_station(args):
    meta, rec, version = args
    viz.set_final_year(int(meta["final_year"]))
    t = texts(meta, version)
    path = station_path(meta)
    viz.wide_chart(station_frame(rec, int(meta["final_year"])), "record_c", path, t["title"],
                   t["subtitle"], "Record daily maximum temperature (°C)", t["footer"])
    thumb = OUT / "thumbs" / f"{meta['id']}.jpg"
    thumb.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(path) as im:
        im.convert("RGB").resize((960, 320), Image.LANCZOS).save(thumb, quality=85)
    return str(path)


def carousel(meta: dict, rec: pd.DataFrame, version: str) -> Path:
    fy = int(meta["final_year"])
    viz.set_final_year(fy)
    t = texts(meta, version)
    rec = station_frame(rec, fy)
    folder = OUT / "carousels" / f"{meta['id']}_{slug(meta['name'])}"
    folder.mkdir(parents=True, exist_ok=True)
    months = sorted(rec["date"].dt.month.unique())
    n_slides = len(months) + 2
    first_year = int(t["first"])
    counts = rec["record_year"].value_counts()
    n_years = fy - first_year + 1
    end = day_label(meta["end_md"])

    figs = [("01_overview", viz.overview_slide(
        rec, "record_c", f"{meta['records_2020s']} of {meta['n_days']}",
        f"days so far this year have their\n{t['name']} heat record set in the 2020s",
        f"Record daily maximum temperature for each calendar day, 1 Jan – {end}, {t['name']}, "
        f"{t['country']}\n{meta['n_complete_years']} complete years of data since {first_year}. "
        f"A stable climate would give about {meta['expected_2020s']:.0f}.",
        "Record daily max temperature (°C)", counts, first_year, fy,
        meta["n_days"] / n_years, t["source"], 1, n_slides))]
    for k, m in enumerate(months, start=2):
        sub = rec[rec["date"].dt.month == m]
        n_new = int((sub["record_year"] >= 2020).sum())
        notes = []
        if m == months[-1] and sub["date"].dt.day.max() < calendar.monthrange(fy, m)[1]:
            notes.append(f"Data through {end} {fy}" if meta["has_final_year"]
                         else f"No {fy} data yet; latest data {meta['last_date']}")
        figs.append((f"{k:02d}_{calendar.month_name[m].lower()}", viz.month_slide(
            sub, "record_c", m, f"{n_new} of {len(sub)} days: record set in the 2020s",
            f"{t['name']}, {t['country']} · hottest each calendar day has been since {first_year}\n"
            f"bar = record daily maximum temperature · label = year it was set",
            "Record daily maximum temperature (°C)", t["source"], k, n_slides, notes)))
    sections = [
        ("Station", [
            f"{t['name']}, {t['country']} (GHCN-Daily {meta['id']}, {meta['lat']:.2f}°, "
            f"{meta['lon']:.2f}°, {meta['elev']:.0f} m)",
            f"Daily maximum temperature from {meta['first_date']} to {meta['last_date']}: "
            f"{meta['n_complete_years']} complete years (≥80% of days)",
        ]),
        ("Method", [
            "For every calendar day: the highest daily maximum across all years, and the year "
            "that first reached it (a later year that only equals the record does not count)",
            "Values flagged by NOAA quality control, or more than 6σ from the station's seasonal "
            "cycle, are dropped",
            f"In a stable climate every year is equally likely to hold a record: about "
            f"{meta['expected_2020s']:.0f} of these {meta['n_days']} days would fall in the 2020s",
        ]),
        ("Caveats", [
            "Raw, unhomogenised station data: early instruments, station moves and changes in "
            "observing time can bias early decades warm, favouring old records if anything",
            "One station shows local weather history; a single hot summer can hold many records",
            f"Data through {meta['last_date']}; the latest days can change as late reports arrive",
        ]),
    ]
    figs.append((f"{n_slides:02d}_method", viz.method_slide(
        sections, t["source"], f"GHCN-Daily v{version}, accessed {date.today():%-d %b %Y} · "
        "Menne et al. 2012, doi:10.1175/JTECH-D-11-00103.1", n_slides, n_slides)))
    with PdfPages(folder / "carousel.pdf") as pdf:
        for name, fig in figs:
            fig.savefig(folder / f"{name}.png", dpi=viz.IG_DPI)
            pdf.savefig(fig)
            plt.close(fig)
    return folder


def write_index(idx: pd.DataFrame) -> Path:
    rows = []
    for _, m in idx.iterrows():
        meta = m.to_dict()
        if not station_path(meta).exists():
            continue
        rel = station_path(meta).relative_to(OUT).as_posix()
        ratio = m["records_2020s"] / m["expected_2020s"] if m["expected_2020s"] > 0 else float("nan")
        rows.append(
            f"<tr><td>{html.escape(m['region'])}</td><td>{html.escape(country_label(m['country']))}</td>"
            f"<td><a href='{rel}'>{html.escape(display_name(meta))}</a><br><small>{m['id']}</small></td>"
            f"<td data-v='{m['first_date'][:4]}'>{m['first_date'][:4]}–{m['last_date'][:4]}</td>"
            f"<td data-v='{m['n_complete_years']}'>{m['n_complete_years']}</td>"
            f"<td>{m['last_date']}</td>"
            f"<td data-v='{m['records_2020s']}'>{m['records_2020s']} / {m['n_days']}</td>"
            f"<td data-v='{ratio:.3f}'>{ratio:.1f}×</td>"
            f"<td data-v='{m['records_final_year']}'>{m['records_final_year']}</td>"
            f"<td data-v='{m['top_year']}'>{m['top_year']} ({m['top_year_days']})</td>"
            f"<td><a href='{rel}'><img loading='lazy' src='thumbs/{m['id']}.jpg' width='480'></a></td></tr>"
        )
    page = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily heat records by station</title>
<style>
body {{ background:#0F1419; color:#E8EAED; font-family: Lato, "DejaVu Sans", sans-serif; margin: 16px; }}
h1 {{ color:#FF6B6B; font-size: 28px; margin: 8px 0; }}
p {{ color:#9AA0A6; max-width: 70em; }}
input {{ background:#1E2630; color:#E8EAED; border:1px solid #3C4043; padding:6px 10px; width: 22em; }}
table {{ border-collapse: collapse; margin-top: 12px; width: 100%; }}
th, td {{ border-bottom: 1px solid #3C4043; padding: 6px 8px; text-align: left; vertical-align: middle; }}
th {{ color:#9AA0A6; cursor: pointer; position: sticky; top: 0; background:#0F1419; }}
a {{ color:#E8EAED; }} small {{ color:#9AA0A6; }}
.wrap {{ overflow-x: auto; }}
</style></head><body>
<h1>Daily heat records, station by station</h1>
<p>{len(rows)} GHCN-Daily stations with at least 100 complete years of daily maximum temperature that
reported in {int(idx['final_year'].iloc[0]) - 1} or {int(idx['final_year'].iloc[0])}. Each plot shows,
for every day from 1 January to the station's latest data, the highest daily maximum on record and
the year that set it. "2020s records" counts days whose record was set in 2020 or later; "vs stable"
divides that by the number expected if every year were equally likely. Click a column to sort.</p>
<input id="q" placeholder="Filter by station, country or region">
<div class="wrap"><table id="t"><thead><tr><th>Region</th><th>Country</th><th>Station</th><th>Years</th>
<th>Complete years</th><th>Data through</th><th>2020s records</th><th>vs stable</th>
<th>Set in {int(idx['final_year'].iloc[0])}</th><th>Top year (days)</th><th>Plot</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<script>
const t = document.getElementById('t'), q = document.getElementById('q');
q.addEventListener('input', () => {{
  const s = q.value.toLowerCase();
  for (const r of t.tBodies[0].rows) r.style.display = r.textContent.toLowerCase().includes(s) ? '' : 'none';
}});
t.tHead.addEventListener('click', e => {{
  const th = e.target.closest('th'); if (!th) return;
  const i = th.cellIndex, asc = th.dataset.asc !== '1'; th.dataset.asc = asc ? '1' : '0';
  const key = c => {{ const v = c.dataset.v ?? c.textContent; const n = parseFloat(v); return isNaN(n) ? v : n; }};
  const rows = [...t.tBodies[0].rows].sort((a, b) => {{
    const x = key(a.cells[i]), y = key(b.cells[i]);
    return (x > y ? 1 : x < y ? -1 : 0) * (asc ? 1 : -1);
  }});
  rows.forEach(r => t.tBodies[0].appendChild(r));
}});
</script></body></html>"""
    path = OUT / "index.html"
    path.write_text(page, encoding="utf-8")
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", help="only stations in this region, e.g. Europe")
    ap.add_argument("--ids", nargs="+", help="only these station IDs")
    ap.add_argument("--carousel", nargs="+", metavar="ID", help="make 1080x1350 slides for these IDs")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    idx = pd.read_csv(OUT / "station_index.csv", keep_default_na=False, na_values=[""])
    long = pd.read_csv(OUT / "records_long.csv.gz")
    groups = dict(tuple(long.groupby("id")))
    version = ghcnd_version()

    if args.carousel:
        for sid in args.carousel:
            meta = idx[idx["id"] == sid].iloc[0].to_dict()
            print(carousel(meta, groups[sid], version))
        return

    sel = idx
    if args.region:
        sel = sel[sel["region"].str.lower() == args.region.lower()]
    if args.ids:
        sel = sel[sel["id"].isin(args.ids)]
    jobs = [(m.to_dict(), groups[m["id"]], version) for _, m in sel.iterrows()]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for i, path in enumerate(pool.map(render_station, jobs), start=1):
            if i % 50 == 0 or i == len(jobs):
                print(f"{i}/{len(jobs)} plots")
    print(write_index(idx))


if __name__ == "__main__":
    main()
