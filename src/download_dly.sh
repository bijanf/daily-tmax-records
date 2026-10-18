#!/usr/bin/env bash
# Download GHCN-Daily .dly files for every candidate station (TMAX, 100+ year
# inventory span, reporting this year or last year) straight from NCEI, which is updated
# daily. The AWS mirror (noaa-ghcn-pds) stopped updating in Feb 2025.
#
# Re-running refreshes only files NCEI has changed since the local copy
# (conditional GET on the file's modification time), so it is cheap to run
# again for an up-to-date plot.
#
# Usage: src/download_dly.sh [n_parallel]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LIST="$ROOT/data/raw/candidates_tmax_100y_active.txt"
OUT="$ROOT/data/dly"
NPAR="${1:-12}"
BASE="https://www.ncei.noaa.gov/pub/data/ghcn/daily/all"

mkdir -p "$OUT"
export OUT BASE

fetch() {
    local id="$1" f="$OUT/$1.dly"
    local cond=()
    if [ -s "$f" ]; then
        cond=(-z "$f")
    fi
    if curl -sS -R --retry 4 --retry-delay 5 -m 600 "${cond[@]}" -o "$f.part" "$BASE/$id.dly"; then
        if [ -s "$f.part" ]; then
            mv "$f.part" "$f"
        else
            rm -f "$f.part"
        fi
    else
        rm -f "$f.part"
        echo "FAILED $id" >&2
    fi
}
export -f fetch

xargs -P "$NPAR" -I{} bash -c 'fetch "$@"' _ {} < "$LIST"
echo "done: $(ls "$OUT"/*.dly | wc -l) files, $(du -sh "$OUT" | cut -f1)"
