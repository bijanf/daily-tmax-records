# Daily heat records, station by station

For every weather station with at least 100 complete years of daily maximum
temperature (TMAX) that is still reporting, one plot: a bar for every calendar
day from 1 January up to the station's latest data, bar height = the highest
TMAX ever measured on that day, 90-degree label = the year that set the record.

## Outputs (`outputs/`)

| Path | What |
|---|---|
| `stations/<region>/<country>/<ID>_<name>.png` | one plot per station (6600 × 2200 px), 1,109 stations |
| `stations_monthly/<region>/<country>/<ID>_<name>_monthly.png` | monthly view per station (1080 × 1350): warmest month on record by average daily maximum, labelled with its year; the unfinished month compares the same days in every year |
| `findings/1_…5_*.png` | findings figures (2160 × 2700): Germany 27–28 June 2026, record highs vs lows, records by month, mountains vs cities, record margins; numbers in `findings_log.txt` |
| `impact/A_*, B_*, C_*.png` | high-impact figures (2160 × 2700): daily heat carpet of a station with its standing records, Europe's record-hot ÷ record-cold days by decade, a station's hottest day of every year (`plot_impact.py --id <ID>`) |
| `posters/1_…5_*.png` | posters for a general audience (2160 × 2700), plain words and big type: Europe 23 : 1, Europe map of hottest days ever, Europe 2026, and two city posters (`plot_posters.py --id <ID>`, default Potsdam); Inter font in `data/fonts/inter` (SIL Open Font License) |
| `onebit/europe_extremes[_<theme>].png`, `.mp4` | Europe's heat extremes as a 1-bit retro desktop (2160 × 2700 poster; 1080 × 1350, 32 s animation of the poster assembling itself, ending on a close-up of the hottest day): heat : cold ratio, map of each station's hottest-day year, one grid cell per station, decade race. Themes: `pink` (no suffix), `violet` Violet.Hour, `orange` BSR.Orange, `berlin` BVG.Gelb, `xberg` SO36.Nacht (`plot_onebit.py --theme`); VT323 and JetBrains Mono in `data/fonts` (SIL Open Font License) |
| `stations/index.html` | every station in a sortable, filterable table with thumbnails (open locally) |
| `stations/station_index.csv` | per-station summary: years, data end, records in the 2020s vs expected, top year, hottest record |
| `stations/records_long.csv.gz` | record value, record year, ties and years of data for every station and day |
| `stations/carousels/<ID>_<name>/` | 1080 × 1350 Instagram/LinkedIn slides + `carousel.pdf` (made on request) |
| `stations/*.zip` | Germany (35 plots) and the rest of Europe (3 parts, 88 plots) |
| `records_master_wide.png`, `carousel/` | bonus: one composite of all stations (5° area-weighted anomaly) |

Stations by region: North America 955, Europe 123 (Germany 35), Asia 22, Oceania 9.

## Setup

```bash
pip install -r requirements.txt   # numpy, pandas, matplotlib, scipy, cartopy, pillow
src/get_fonts.sh                  # Inter, VT323, JetBrains Mono for the posters (else Lato is used)
src/run_all.sh                    # downloads ~4 GB of station data, then builds everything
```

Only the code, the five posters (`outputs/posters/`), the findings report
(`outputs/findings_log.txt`) and the station index (`outputs/stations/station_index.csv`)
are in the repository; `data/` and every other output are rebuilt by `src/run_all.sh`.

## Re-run

```bash
src/run_all.sh                                   # everything; downloads only what changed
python -I src/plot_stations.py --region Europe   # re-plot one region
python -I src/plot_stations.py --carousel GM000003342 UK000056225   # slides for chosen stations
python -I src/plot_monthly.py --ids GM000003319 GM000003342          # monthly view for chosen stations
python -I src/plot_onebit.py --theme all --no-video   # 1-bit desktop posters in every theme (drop the flag for MP4s)
```

## Data and method

- **Stations:** NOAA NCEI GHCN-Daily (v3.35), downloaded from NCEI (the AWS mirror
  `noaa-ghcn-pds` stopped updating its per-station files in February 2025). Kept:
  ≥ 100 complete years (≥ 80 % of days valid) and valid TMAX on at least half of
  2025's days or of 2026's days so far.
- **Quality control:** values with a GHCN quality flag are dropped, and so are values
  more than 6σ from the station's own seasonal cycle.
- **Record:** for each calendar day (29 Feb skipped), the highest TMAX across all
  years. Ties go to the year that first reached the value; a later year that only
  equals it is not counted as a record breaker.
- **"Expected in a stable climate":** if every year were equally likely to hold a
  record, with the same tie rule: with k years tied among n, the record falls in
  the last m years with probability C(m, k) / C(n, k), summed over days.
- **Up to today for Europe:** GHCN-Daily receives most European data weeks or months
  late. `src/fill_recent.py` fills the missing days from national open data, but
  only for stations whose national series is identical to GHCN-Daily on ≥ 95 % of
  ≥ 30 shared days: DWD (35 German stations), SMHI (11 Swedish), KNMI (5 Dutch),
  GeoSphere (3 Austrian), MeteoSwiss (1). UK, France, Estonia, Romania, Spain,
  Ireland, Hungary and Finland end on their last GHCN-Daily day (21 Mar to 31 Aug):
  no keyless daily feed, or none newer than GHCN-Daily.

- **Significance (Europe, 2020s):** all 123 European stations, one by one, have more
  heat records than cold records since 2020 (5,515 vs 241 in total; about 1,700 of each
  expected in a stable climate). Shuffling whole years (which keeps neighbouring
  stations and days linked) 200,000 times never gives a 7-year group above 9.4 : 1,
  against 23 : 1 for 2020–2026 (p < 5 × 10⁻⁶; `findings.py`, section 6).

## Data sources

NOAA NCEI GHCN-Daily (Menne et al. 2012, doi:10.1175/JTECH-D-11-00103.1), plus the
open daily data of DWD, SMHI, KNMI, GeoSphere Austria and MeteoSwiss for the latest
weeks. These services ask to be credited; the figures name them.

## Caveats

- Raw, unhomogenised station data. Early instruments, station moves and US
  observing-time changes tend to bias early decades warm, so old records are
  favoured if anything. US stations still hold many 1930s Dust Bowl records.
- Isolated bad values can survive the checks. Example: Atyrau (Kazakhstan),
  50.0 °C on 4 July 1911, between 42.5 and 35.5 °C, above the national record. Before
  posting a station, glance at its hottest records (`hottest_record_*` columns).
  A blanket spike test was tried and rejected: it would delete over 10,000
  genuine records.
- The latest days can still change as late reports arrive.

## Prior art (searched 18 Oct 2026)

Each piece exists somewhere; this exact combination was not found:

- Uppsala University "Daily statistics" (https://celsius.met.uu.se/?pageid=25):
  one station, monthly panels with each day's record and its year as a label.
- Iowa Environmental Mesonet Autoplot 190 (https://mesonet.agron.iastate.edu/plotting/auto/?q=190):
  year of each day's record for any US station or state average, year on the y-axis.
- The Pudding, "Tracking Heat Records in 400 U.S. Cities" (https://pudding.cool/projects/heat-records/).

No published set was found covering every 100+ year station, with the record
value and a rotated year label for each day, running to the current date.
X and Bluesky are poorly indexed, so check there by hand before claiming novelty.
