#!/usr/bin/env bash
# Download the typefaces (all SIL Open Font License) used by the posters into data/fonts:
#   inter/           Inter and Inter Display, the posters (without it they fall back to Lato)
#   vt323/           VT323, the pixel terminal type of the 1-bit posters (plot_onebit.py)
#   jetbrains-mono/  JetBrains Mono, the code labels of the 1-bit posters
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FONTS="$ROOT/data/fonts"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

DEST="$FONTS/inter"
if ! ls "$DEST"/ttf/Inter-*.ttf > /dev/null 2>&1; then
    curl -sS -L -m 300 -o "$TMP/inter.zip" https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip
    unzip -q "$TMP/inter.zip" -d "$TMP/inter"
    mkdir -p "$DEST/ttf"
    for w in Regular Medium SemiBold Bold ExtraBold Black; do
        cp "$TMP/inter/extras/ttf/Inter-$w.ttf" "$TMP/inter/extras/ttf/InterDisplay-$w.ttf" "$DEST/ttf/"
    done
    cp "$TMP/inter/LICENSE.txt" "$DEST/"
    echo "Inter installed in $DEST"
fi

DEST="$FONTS/vt323"
if [ ! -f "$DEST/VT323-Regular.ttf" ]; then
    mkdir -p "$DEST"
    curl -sS -L -m 120 -o "$DEST/VT323-Regular.ttf" https://github.com/google/fonts/raw/main/ofl/vt323/VT323-Regular.ttf
    curl -sS -L -m 120 -o "$DEST/OFL.txt" https://github.com/google/fonts/raw/main/ofl/vt323/OFL.txt
    echo "VT323 installed in $DEST"
fi

DEST="$FONTS/jetbrains-mono"
if ! ls "$DEST"/JetBrainsMono-*.ttf > /dev/null 2>&1; then
    curl -sS -L -m 300 -o "$TMP/jbm.zip" \
        https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip
    unzip -q "$TMP/jbm.zip" -d "$TMP/jbm"
    mkdir -p "$DEST"
    for w in Regular Medium Bold; do
        cp "$TMP/jbm/fonts/ttf/JetBrainsMono-$w.ttf" "$DEST/"
    done
    cp "$TMP/jbm/OFL.txt" "$DEST/"
    echo "JetBrains Mono installed in $DEST"
fi
