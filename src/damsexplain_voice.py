"""THE OWNER'S VOICE FOR THE LONG CUT (damsexplain2v_fa): his recording of 9 Nov 2026 (3:50, the script
outputs/onebit/social/damsexplain2_voice_script_fa.txt read in his own words), cut into the eleven slide pieces.

The cut points come from a Whisper large-v3 transcript (word times) checked against the pauses ffmpeg's
silencedetect finds at -38 dB. Edits, all at word boundaries with 15-ms fades:
- seasons: «از آب شدنِ برف‌ها» kept, «و یخچال‌ها» dropped (the Karaj dam's catchment has no glaciers to speak of);
- end: the false start «گفت که فکر کنم، پارسال گفت اینو» and the repeated «و دنبالش کنید» dropped.
Pauses longer than 0.40 s inside a piece are shortened to 0.30 s; then, only if the reel would run past MAX_REEL,
the pieces are sped up together (ffmpeg atempo, pitch kept) by the least factor that fits.

    data/damsexplain/voice/source.m4a      the recording as received (never committed: data/ is ignored)
    data/damsexplain/voice/v01..v11.wav    the pieces, 48 kHz mono
    data/damsexplain/voice/manifest.json   per piece: scene, seconds; the speed factor

    python -I src/damsexplain_voice.py <recording.m4a>
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402

OUT = onebit.ROOT / "data" / "damsexplain" / "voice"
SR = 48000
MAX_REEL = 174.0                                   # s: Instagram recommends reels up to 3 minutes
LEAD, TAIL = 0.30, 0.50                            # s of the slide before and after its piece
PIECES = (                                         # (scene, [(start, end) in the recording, s])
    ("hook", [(4.95, 21.20)]),
    ("answer", [(22.30, 33.45)]),
    ("grid", [(35.25, 50.28)]),
    ("rain", [(51.30, 85.70)]),
    ("soil", [(88.90, 107.35)]),
    ("snow", [(109.05, 118.80)]),
    ("seasons", [(119.35, 128.62)]),
    ("ground", [(132.70, 155.13)]),
    ("sink", [(155.78, 184.62)]),
    ("urmia", [(185.15, 197.78)]),
    ("end", [(198.84, 203.00), (205.86, 226.25)]),
)


def fade(x: np.ndarray, ms: float = 15.0) -> np.ndarray:
    n = min(len(x) // 2, int(SR * ms / 1000))
    r = np.linspace(0.0, 1.0, n)
    y = x.copy()
    y[:n] *= r
    y[-n:] *= r[::-1]
    return y


def squeeze_pauses(x: np.ndarray, longest: float = 0.40, keep: float = 0.30, floor_db: float = -38.0) -> np.ndarray:
    """Shorten every pause longer than `longest` s to `keep` s (its middle is cut, 20-ms crossfade)."""
    hop = int(0.010 * SR)
    win = int(0.030 * SR)
    frames = max(1, (len(x) - win) // hop)
    rms = np.array([np.sqrt(np.mean(x[i * hop:i * hop + win] ** 2) + 1e-12) for i in range(frames)])
    quiet = 20 * np.log10(rms) < floor_db
    out, i0, i = [], 0, 0
    while i < frames:
        if quiet[i]:
            j = i
            while j < frames and quiet[j]:
                j += 1
            a, b = i * hop + win // 2, j * hop + win // 2
            if (b - a) / SR > longest:
                cut_a = a + int(keep / 2 * SR)
                cut_b = b - int(keep / 2 * SR)
                out.append(x[i0:cut_a])
                i0 = cut_b
            i = j
        else:
            i += 1
    out.append(x[i0:])
    xf = int(0.020 * SR)
    y = out[0]
    for seg in out[1:]:                            # crossfade the joins
        if len(y) > xf and len(seg) > xf:
            r = np.linspace(0, 1, xf)
            y = np.concatenate([y[:-xf], y[-xf:] * (1 - r) + seg[:xf] * r, seg[xf:]])
        else:
            y = np.concatenate([y, seg])
    return y


def tempo(x: np.ndarray, factor: float) -> np.ndarray:
    if abs(factor - 1.0) < 1e-3:
        return x
    with tempfile.TemporaryDirectory() as tmp:
        a, b = Path(tmp) / "a.wav", Path(tmp) / "b.wav"
        wavfile.write(a, SR, np.int16(np.clip(x, -1, 1) * 32767))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(a), "-af", f"atempo={factor:.4f}", str(b)], check=True)
        _, y = wavfile.read(b)
    return y.astype(np.float64) / 32768.0


def main() -> None:
    src = Path(sys.argv[1])
    OUT.mkdir(parents=True, exist_ok=True)
    if src.resolve() != (OUT / "source.m4a").resolve():
        shutil.copy2(src, OUT / "source.m4a")
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "raw.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(OUT / "source.m4a"), "-ac", "1", "-ar", str(SR),
                        "-c:a", "pcm_s16le", str(wav)], check=True)
        rate, raw = wavfile.read(wav)
    assert rate == SR
    raw = raw.astype(np.float64) / 32768.0
    pieces = []
    for scene, spans in PIECES:
        parts = [fade(raw[int(a * SR):int(b * SR)]) for a, b in spans]
        pieces.append((scene, squeeze_pauses(np.concatenate(parts))))
    speech = sum(len(p) / SR for _, p in pieces)
    room = MAX_REEL - len(pieces) * (LEAD + TAIL)
    factor = max(1.0, speech / room)
    assert factor <= 1.15, f"the recording needs {factor:.2f}x to fit; cut words instead"
    man = dict(source=src.name, factor=round(factor, 4), lead=LEAD, tail=TAIL, pieces=[])
    for k, (scene, p) in enumerate(pieces, 1):
        y = tempo(p, factor)
        name = f"v{k:02d}"
        wavfile.write(OUT / f"{name}.wav", SR, np.int16(np.clip(y, -1, 1) * 32767))
        man["pieces"].append(dict(name=name, scene=scene, seconds=round(len(y) / SR, 3)))
    (OUT / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(q["seconds"] for q in man["pieces"]) + len(pieces) * (LEAD + TAIL)
    print(f"speech {speech:.1f} s after the pause squeeze; speed {factor:.3f}x; reel about {total:.1f} s")
    for q in man["pieces"]:
        print(f"  {q['name']} {q['scene']:8s} {q['seconds']:6.2f} s")


if __name__ == "__main__":
    main()
