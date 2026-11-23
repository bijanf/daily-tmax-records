#!/usr/bin/env bash
# The finish of cycles_fa (ffmpeg only): a fine moving grain, so soft gradients do not fall into bands after
# Instagram's own compression, and the score laid under the picture at the loudness it was written at. The night
# look also gets a light vignette that pulls the eye to the middle; the paper look stays even to its edges.
#
#   src/cycles_finish.sh <silent reel .mp4> <score .wav> <out .mp4> [light|night]
set -euo pipefail
in="$1"; wav="$2"; out="$3"; look="${4:-light}"
if [ "$look" = night ]; then vf="vignette=angle=PI/7,noise=c0s=5:c0f=t+u,format=yuv420p"; else vf="noise=c0s=3:c0f=t+u,format=yuv420p"; fi
ffmpeg -y -loglevel error -i "$in" -i "$wav" -map 0:v -map 1:a -vf "$vf" \
  -c:v libx264 -preset slow -crf 17 -profile:v high \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -c:a aac -b:a 192k -shortest -movflags +faststart "$out"
echo "saved $out"
