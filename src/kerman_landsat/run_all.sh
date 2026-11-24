#!/usr/bin/env bash
# Rafsanjan plain orchards from Landsat C2 L2 (Planetary Computer, keyless): the full run, in order.
# About 40 minutes on a fast connection; reads windows of the COGs only. Outputs go to data/kerman/landsat
# (common.HERE); s13_stage.py then writes the film's stage pictures (data/kerman/landsat/stage).
set -euo pipefail
cd "$(dirname "$0")"
python -I s01_scout.py                       # which path/rows cover the box (prints)
python -I s02_overview.py                    # overview/: 2024 true colour + NDVI, ~110 m, to place the box
python -I s03_inventory.py                   # stac/<year>.json, inventory.csv
python -I geom.py                            # cache/geom.npz: grid, box, zones W (path 161) and E (path 160)
python -I s04_year.py 1987 2025 --rgb        # composites with colour for the pictures
python -I s04_year.py $(seq 1986 2024)       # every other year (cached years are skipped)
python -I s06_dem.py                         # cache/dem.npz (Copernicus GLO-30)
python -I s05_inspect.py 1987 2025           # check/: threshold overlays
python -I s07_sensor.py                      # sensor_pairs.csv, sensor_eq.csv (TM/ETM+/OLI pairs)
python -I s09_tables.py                      # harmonisation.csv, table_years.csv, then_now.csv, timeseries_plain_oli020.csv
python -I s10_change.py 0.20                 # change_0.20.json, check/change_0.20_*.png
python -I s10_change.py 0.15
python -I s11_check_harm.py                  # check/harm_*.png
python -I s08_pictures.py                    # pictures/*.jpg, pictures/tone_match.json
python -I s12_geotiff.py                     # geotiff/*.tif
python -I s13_stage.py                       # stage/: the film's then/now pictures and green masks on one lon/lat grid
