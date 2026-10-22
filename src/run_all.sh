#!/usr/bin/env bash
# Rebuild everything: NCEI inventory -> candidate stations -> .dly files ->
# TMAX matrix -> record per calendar day -> figures. Safe to re-run: only
# files NCEI has changed since the last run are downloaded again.
#
# Usage: src/run_all.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RAW="$ROOT/data/raw"
BASE="https://www.ncei.noaa.gov/pub/data/ghcn/daily"
YEAR="$(date +%Y)"
mkdir -p "$RAW" "$ROOT/outputs"
"$ROOT/src/get_fonts.sh"

for f in ghcnd-inventory.txt ghcnd-stations.txt ghcnd-countries.txt ghcnd-version.txt; do
    cond=()
    if [ -s "$RAW/$f" ]; then
        cond=(-z "$RAW/$f")
    fi
    curl -sS -R -m 600 "${cond[@]}" -o "$RAW/$f.part" "$BASE/$f"
    if [ -s "$RAW/$f.part" ]; then
        mv "$RAW/$f.part" "$RAW/$f"
    else
        rm -f "$RAW/$f.part"
    fi
done

# TMAX stations whose inventory spans 100+ years and that reported this year or last year
awk -v y="$((YEAR - 1))" '$4=="TMAX" && $6>=y && ($6-$5+1)>=100 {print $1}' "$RAW/ghcnd-inventory.txt" \
    | sort -u > "$RAW/candidates_tmax_100y_active.txt"
echo "candidates: $(wc -l < "$RAW/candidates_tmax_100y_active.txt")"

"$ROOT/src/download_dly.sh" 12
python -I "$ROOT/src/build_tmax.py"
python -I "$ROOT/src/fill_recent.py" | tee "$ROOT/outputs/fill_recent_log.txt"
python -I "$ROOT/src/build_tmax.py"
python -I "$ROOT/src/station_records.py"
rm -rf "$ROOT/outputs/stations/"{europe,north_america,asia,oceania,south_america,africa,thumbs}
python -I "$ROOT/src/plot_stations.py"
python -I "$ROOT/src/plot_monthly.py" > "$ROOT/outputs/stations_monthly_log.txt"
python -I "$ROOT/src/findings.py" > "$ROOT/outputs/findings_log.txt"
python -I "$ROOT/src/plot_findings.py"
python -I "$ROOT/src/plot_impact.py"
python -I "$ROOT/src/plot_posters.py"
python -I "$ROOT/src/plot_onebit.py" --theme all
python -I "$ROOT/src/drought.py" > "$ROOT/outputs/drought_log.txt"
python -I "$ROOT/src/plot_onebit_drought.py"
python -I "$ROOT/src/extremes.py" > "$ROOT/outputs/extremes_log.txt"
python -I "$ROOT/src/plot_onebit_extremes.py"
python -I "$ROOT/src/composite.py" | tee "$ROOT/outputs/composite_log.txt"
python -I "$ROOT/src/plot_records.py"
# soil and water stories last: ERA5 and ERA5-Land need a Copernicus CDS key in ~/.cdsapirc
python -I "$ROOT/src/get_soil.py"
python -I "$ROOT/src/soil.py" > "$ROOT/outputs/soil_log.txt"
python -I "$ROOT/src/onebit_soil.py"
python -I "$ROOT/src/get_water.py"
python -I "$ROOT/src/water.py" > "$ROOT/outputs/water_log.txt"
python -I "$ROOT/src/onebit_water.py"
