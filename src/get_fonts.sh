#!/usr/bin/env bash
# Download the Inter typeface (SIL Open Font License) used by the posters into
# data/fonts/inter. Without it the posters fall back to Lato.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/data/fonts/inter"
if ls "$DEST"/ttf/Inter-*.ttf > /dev/null 2>&1; then
    exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -sS -L -m 300 -o "$TMP/inter.zip" https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip
unzip -q "$TMP/inter.zip" -d "$TMP/unpacked"
mkdir -p "$DEST/ttf"
for w in Regular Medium SemiBold Bold ExtraBold Black; do
    cp "$TMP/unpacked/extras/ttf/Inter-$w.ttf" "$TMP/unpacked/extras/ttf/InterDisplay-$w.ttf" "$DEST/ttf/"
done
cp "$TMP/unpacked/LICENSE.txt" "$DEST/"
echo "Inter installed in $DEST"
