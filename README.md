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
| `onebit/europe_drought[_<theme>].png`, `.mp4` | the same desktop for drought (`plot_onebit_drought.py`, default theme `sand` Streusand): stations whose driest growing season (March–August, rain minus Hargreaves evaporation) on record fell in the 2020s, against rain alone and a stable climate; numbers in `drought_log.txt` (`drought.py`) |
| `onebit/social/<story>_<theme>_reel.mp4`, `_cover.png`, `_slide1-5.png` | Instagram cut (`--social`): a 30 s 9:16 loop that opens on the poster, rebuilds it and tours every window with the camera (2 x 2 px dots, BT.709, silent audio track), its cover, and a 5-slide 4:5 carousel |
| `onebit/europe_scoreboard[_<theme>].png`, `social/europe_scoreboard_*` | Europe's extremes scoreboard (`plot_onebit_extremes.py`, default theme `beton`): how often days ≥ 35 °C, hot nights, dry seasons, downpours and frost days happen in 2016–2025 against 1961–1990, the year of each station's warmest night, and Vienna's two wettest days (2024); numbers in `extremes_log.txt` (`extremes.py`) |
| `onebit/social/europe_soil_<theme>_reel.mp4`, `_cover.png` | DRY SOIL, WARM PLANET (`onebit_soil.py`, default theme `feld` Tempelhof.Feld): 36 s reel, global temperature bars since 1950 and Europe as a halftone of dots, each the number of summers out of ten in soil drought, walking from 1951–60 to 2017–26; numbers in `soil_log.txt` (`soil.py`), inputs from `get_soil.py` |
| `onebit/social/europe_water_<theme>_reel.mp4`, `_cover.png` | SAME RAIN, HOTTER AIR (`onebit_water.py`, default theme `kanal` Landwehr.Kanal; `--theme pink1` or `gelb1` for true two-colour 1-bit, accents in inverse video): a still 39 s 1-bit desktop with an 8-bit soundtrack (`onebit_chip.py`): 25 five-year temperature bars since 1901, and Europe in Mercator as a halftone of square dots (solid red drier, hollow wetter than 1951–80) that steps five years per beat from 1901–10 to 2016–25; a plain-words box: litres less water per m², rain "same", evaporation "+13 %", buckets; numbers in `water_log.txt` (`water.py`), inputs from `get_water.py` |
| `onebit/social/<story>_<theme>_music.wav` | the reel's soundtrack (`onebit_audio.py`): minimal techno synthesized from scratch, 64 beats per film so it loops with the picture, with the data sonified (station blips, grid chirps, race glides) |
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
python -I src/drought.py > outputs/drought_log.txt    # drought: record-dry growing seasons, rain and water balance
python -I src/plot_onebit_drought.py --web           # drought desktop: poster, animation, small web cut
python -I src/plot_onebit_drought.py --theme uv --no-video --social   # Instagram: 30 s reel loop, cover, carousel
python -I src/extremes.py > outputs/extremes_log.txt   # extremes scoreboard numbers
python -I src/plot_onebit_extremes.py --no-video --social   # scoreboard reel with soundtrack
python -I src/get_soil.py                              # ERA5-Land soil water (needs a CDS key), HadCRUT5, CPC
python -I src/soil.py > outputs/soil_log.txt           # soil drought vs global temperature, with three checks
python -I src/onebit_soil.py                           # soil reel with soundtrack (--stills: frames only)
python -I src/get_water.py                             # CRU TS 1901-2025; ERA5 monthly means (needs a CDS key)
python -I src/water.py > outputs/water_log.txt         # summer water balance: rain, the air's thirst, the gap
python -I src/onebit_water.py --theme gelb1           # water reel with the 8-bit soundtrack (38.6 s)
python -I src/onebit_water.py --theme gelb1 --cut 20s # the same in 20 s
python -I src/water.py --region iran > outputs/water_iran_log.txt   # Iran, water years Oct-Sep, from 1951
python -I src/onebit_water.py --region iran --lang fa --theme firuzeh --cut 25s   # Iran reel in Persian, 25 s, big captions
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

- **Soil drought (`soil.py`):** ERA5-Land monthly soil water, layers 0–7, 7–28 and
  28–100 cm weighted by depth, mean of June–August, 0.1° cells of European countries
  (Natural Earth) west of 45 E. A summer is a soil drought where it is drier than nine
  in ten summers of 1951–1980 at that cell. In 1951–1980 that puts 10 % of Europe in
  drought in an average summer; in 2017–2026, 32 %. The slope on global temperature
  (HadCRUT5, against 1850–1900) is +16 points of Europe per +1 °C (95 %: +9 to +21,
  moving-block bootstrap). Checks in `soil_log.txt`: the 20th percentile (20 → 46 %),
  April–September (10 → 33 %), and the NOAA CPC soil moisture model instead of
  ERA5-Land (10 → 27 %, +13 points per °C).

- **Water deficit (`water.py`):** CRU TS 4.10, station-based rain and Penman–Monteith
  potential evaporation, June–August, 0.5° cells of the same Europe inside the reel's map
  frame (11 W–42 E, no Iceland), 1901–2025. Against 1951–1980, the summers of 2016–2025 had
  the same rain (204 → 201 mm) and more evaporation (334 → 377 mm, +13 %), so a water
  balance 45 mm (45 litres per m²) lower; per +1 °C of global temperature the balance falls
  27 mm (95 %: 8 to 35) and evaporation rises 28 mm (15 to 34). Five of the six driest
  summers since 1901 came after 2000. Check: ERA5 with FAO-56 ET0 agrees from the 1960s on
  (2020s: −50 vs −49 mm), but its rain of the 1940s and 1950s is 20–35 mm below the
  stations', so it is not the record.

- **Iran (`water.py --region iran`):** the same balance per water year (October to
  September, Iran's rain falls October to May), from 1951, when CRU TS has stations within
  reach of every cell of the country (before 1941 about three cells in four). Against
  1951–1980, the water years 2016–2025 had less rain (237 → 206 mm) and more evaporation
  (1509 → 1572 mm): 93 mm (93 litres per m²) less water every year, drier on all of Iran's
  area; −93 mm per +1 °C of global temperature (95 %: −127 to −65). The six driest water
  years since 1902 all came after 1999. CRU TS has fewer Iranian stations after 2010 (86 %
  of cells in reach in the 2020s) and falls back on the long-term mean where none reports,
  which damps rather than inflates the recent change. ERA5 with FAO-56 ET0 (the check) finds
  more: rain −18 mm, evaporation +117 mm, a balance 135 mm lower (2017–2026), drier on 99 %
  of the area, every one of its six driest water years after 1999 (2025 the driest).

## Data sources

NOAA NCEI GHCN-Daily (Menne et al. 2012, doi:10.1175/JTECH-D-11-00103.1), plus the
open daily data of DWD, SMHI, KNMI, GeoSphere Austria and MeteoSwiss for the latest
weeks. These services ask to be credited; the figures name them. The soil story uses
ERA5-Land (Muñoz-Sabater et al. 2021, doi:10.5194/essd-13-4349-2021; Copernicus Climate
Change Service), HadCRUT5 (Morice et al. 2021, doi:10.1029/2019JD032361) and CPC soil
moisture (Fan & van den Dool 2004, doi:10.1029/2003JD004345); the water story CRU TS (Harris et
al. 2020, doi:10.1038/s41597-020-0453-3), ERA5 (Hersbach et al. 2020, doi:10.1002/qj.3803) and
FAO-56 (Allen et al. 1998).

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
