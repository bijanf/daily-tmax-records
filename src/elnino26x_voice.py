"""The owner's own voice for the El Niño explainer (elnino26x_fa), taken from the narrated El Niño reel of 8 Nov 2026.

The source is the voice-only cut that src/onebit_score_elnino26s_light.py wrote (the owner's recording, already cut,
cleaned and levelled by src/elnino26s_voice.py on the other computer), as it is on Drive:

    Instagram reels/iran_elnino26s/elnino26s_fa_voiceonly_reel.mp4      (35.5 s, AAC 48 kHz, voice only)

Its five pieces sit in the five scenes of that reel (0, 7.0, 14.75, 18.75, 26.75, 35.5 s), each piece's speech starting
0.15 s after its scene starts. This file cuts the track at those scene edges (each edge lies in a pause: checked
below), so every piece keeps its own lead and its own tail, and writes them as mono 48 kHz WAVs:

    data/enso/elnino26x/voice/n1.wav .. n5.wav      the pieces (mono, 48 kHz, 16 bit)
    data/enso/elnino26x/voice/manifest.json         per piece: the source window, the speech span, the words

    python -I src/elnino26x_voice.py [--src <voiceonly mp4>]     (default: fetched from Drive with rclone)

The words (the owner's, colloquial, as transcribed for elnino26s_voice.py):
    n1  «امسال ال‌نینو خیلی قوی بوده. خب این معنیش میشه که واقعاً طوفانِ نوح اتفاق می‌افته؟»
    n2  «بیست و یک پاییز از بیست و شیش پاییزی که ال‌نینو بوده، ایران بارانِ بیشتری از معمول گرفته.»
    n3  «به‌طورِ میانگین بیست و سه درصد بیشتر از معمول.»
    n4  «زمستان‌ها ولی نیمی‌شون پرباران بود و نیمی‌شون کم‌باران. انگار که مثلاً سکه بندازیم.»
    n5  «پس شانسِ پاییزِ پرباران بیشتر بوده، ولی طوفانِ نوح نمی‌شه. پاییزِ شهرِ شما چطور بوده تا الان؟»
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "enso" / "elnino26x" / "voice"
DRIVE = "gdrive-backup:Instagram reels/iran_elnino26s/elnino26s_fa_voiceonly_reel.mp4"
SR = 48000
EDGES = (0.0, 7.0, 14.75, 18.75, 26.75, 35.5)          # s: the scene edges of elnino26s_fa (its PACE at 60 BPM)
SPEECH_DB = -45.0                                      # dB full scale (10-ms RMS): above this is speech
QUIET_AT_EDGE = 0.05                                   # s: no speech this close to an edge (n4 starts 0.08 s in)
WORDS = dict(
    n1="امسال ال‌نینو خیلی قوی بوده. خب این معنیش میشه که واقعاً طوفانِ نوح اتفاق می‌افته؟",
    n2="بیست و یک پاییز از بیست و شیش پاییزی که ال‌نینو بوده، ایران بارانِ بیشتری از معمول گرفته.",
    n3="به‌طورِ میانگین بیست و سه درصد بیشتر از معمول.",
    n4="زمستان‌ها ولی نیمی‌شون پرباران بود و نیمی‌شون کم‌باران. انگار که مثلاً سکه بندازیم.",
    n5="پس شانسِ پاییزِ پرباران بیشتر بوده، ولی طوفانِ نوح نمی‌شه. پاییزِ شهرِ شما چطور بوده تا الان؟",
)
# the speech found in the source (10-ms RMS above SPEECH_DB, gaps under 0.35 s joined), s; asserted to +-0.05 s
SPEECH = dict(n1=(0.14, 6.60), n2=(7.14, 13.87), n3=(14.87, 17.92), n4=(18.83, 26.06), n5=(26.90, 34.36))


def decode(src: Path) -> np.ndarray:
    """The source's audio as mono float at 48 kHz (ffmpeg)."""
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "voice.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", str(SR), str(wav)],
                       check=True)
        sr, x = wavfile.read(wav)
    assert sr == SR
    return x.astype(np.float64) / 32768.0


def speech_spans(x: np.ndarray) -> list:
    """(start, end) of the speech, s: 10-ms RMS above SPEECH_DB, gaps shorter than 0.35 s joined."""
    h = SR // 100
    n = len(x) // h
    db = 20 * np.log10(np.maximum(np.sqrt(np.mean(x[: n * h].reshape(n, h) ** 2, axis=1)), 1e-9))
    spans, start, last = [], None, None
    for i, loud in enumerate(db > SPEECH_DB):
        t = i / 100
        if loud:
            start = t if start is None else start
            last = t
        elif start is not None and t - last > 0.35:
            spans.append((start, last + 0.01))
            start = None
    if start is not None:
        spans.append((start, last + 0.01))
    return spans


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, help="the voice-only mp4 (default: fetched from Drive)")
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        src = args.src
        if src is None:
            subprocess.run(["rclone", "copy", DRIVE, tmp], check=True)
            src = Path(tmp) / Path(DRIVE).name
        x = decode(src)
    assert abs(len(x) / SR - EDGES[-1]) < 0.05, len(x) / SR
    spans = speech_spans(x)
    # the pieces' speech: n1 and n5 are two lines each (joined in their scene), the others one line
    joined = [(spans[0][0], spans[1][1]), spans[2], spans[3], spans[4], (spans[5][0], spans[6][1])]
    assert len(spans) == 7, spans
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for k, name in enumerate(("n1", "n2", "n3", "n4", "n5")):
        a, b = EDGES[k], EDGES[k + 1]
        s0, s1 = joined[k]
        assert abs(s0 - SPEECH[name][0]) < 0.05 and abs(s1 - SPEECH[name][1]) < 0.05, (name, s0, s1)
        assert s0 - a >= QUIET_AT_EDGE and b - s1 >= QUIET_AT_EDGE, (name, "speech too close to an edge")
        piece = x[round(a * SR): round(b * SR)].copy()
        fade = round(0.01 * SR)
        piece[:fade] *= np.linspace(0, 1, fade)
        piece[-fade:] *= np.linspace(1, 0, fade)
        wavfile.write(OUT / f"{name}.wav", SR, np.clip(piece * 32767, -32768, 32767).astype(np.int16))
        manifest[name] = dict(source_window=[a, b], lead=round(s0 - a, 3), speech=round(s1 - s0, 3),
                              length=round(b - a, 3), words=WORDS[name])
        print(f"{name}: source {a:5.2f}-{b:5.2f} s, lead {s0 - a:.2f} s, speech {s1 - s0:.2f} s")
    manifest["_source"] = dict(drive=DRIVE, note="the owner's own recording of 8 Nov 2026, as mixed for elnino26s_fa")
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", OUT / "manifest.json")


if __name__ == "__main__":
    main()
