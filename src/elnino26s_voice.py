"""The owner's own voice for the El Niño reel (elnino26s_fa): the recording cut into five narration pieces.

    data/enso/elnino26s/voice_raw/elnino_own_voice_20261108_mono48k.wav   the recording (mono, 48 kHz, 51.7 s)
    data/enso/elnino26s/narration_own/n1.wav .. n5.wav                     the pieces (mono, 48 kHz, 16 bit)
    data/enso/elnino26s/narration_own/manifest.json                        the pieces' lead, speech and text

    python -I src/elnino26s_voice.py

Each cut is a nominal time in the recording. It moves to the quietest 1-ms point within SNAP of it, so a cut falls in
silence and never inside a word; the pieces are then checked by a speech-recognition transcription (medium
model, run outside this file) that every word of the spoken text is present. The cleaning is light: a high-pass at 70 Hz, a gentle
FFT noise reduction, a compressor of ratio 2.5, and one loudness for all five pieces.

The pieces (the owner's words, colloquial, kept):
    n1 = L1 + 0.35 s + L2   «امسال ال‌نینو خیلی قوی بوده. خب این معنیش میشه که واقعاً طوفانِ نوح اتفاق می‌افته؟»
                            (the first «خب» is dropped; the 0.35 s between them is the room's own tone)
    n2 = L3                 «بیست و یک پاییز از بیست و شیش پاییزی که ال‌نینو بوده، ایران بارانِ بیشتری از معمول گرفته.»
                            (the preamble 12.78-21.72 s is not used; the pause after «بوده،» is 0.30 s, not 0.54 s)
    n3 = L4                 «به‌طورِ میانگین بیست و سه درصد بیشتر از معمول.»
    n4 = L5                 «زمستان‌ها ولی نیمی‌شون پرباران بود و نیمی‌شون کم‌باران. انگار که مثلاً سکه بندازیم.»
                            (no internal pause is longer than 0.4 s, so none is shortened)
    n5 = L6 + 0.30 s + L7   «پس شانسِ پاییزِ پرباران بیشتر بوده، ولی طوفانِ نوح نمی‌شه.» «پاییزِ شهرِ شما چطور بوده تا الان؟»
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit_persian as kit  # noqa: E402  (integrated loudness and true peak, as in the other scores)

SR = kit.SR                                             # 48 kHz
RAW = ROOT / "data" / "enso" / "elnino26s" / "voice_raw" / "elnino_own_voice_20261108_mono48k.wav"
OUT = ROOT / "data" / "enso" / "elnino26s" / "narration_own"
VOICE = "own voice, recorded 8 Nov 2026"
SNAP = 0.06                                             # s: a cut moves to the quietest 1-ms point within this
SPEECH_DB = -40.0                                       # dB (full scale): a 1-ms frame above this is speech
PAUSE_MAX, PAUSE_KEEP = 0.4, 0.3                        # s: an internal pause above 0.4 s is kept at 0.3 s
FADE = 0.010                                            # s: each piece starts and ends with a 10-ms fade
LEVEL = -22.0                                           # LUFS: every piece at this loudness before the mix
GAP_TONE = (40.80, 41.15)                               # s: the room's own tone (between L5 and L6), for the gaps
L3_PAUSE = (26.27, 26.51)                               # s: L3 keeps 0.15 s after «بوده،» (26.12) and 0.15 s before «ایران» (26.66)
# nominal cuts in the recording (s); the snapped cut is the one used
CUTS = dict(
    L1=(5.58, 8.00),        # «امسال ال‌نینو خیلی قوی بوده.»; the first «خب» (about 4.92-5.52) is dropped in the gap before «امسال» (about 5.66)
    L2=(8.86, 12.52),       # «خب این معنیش میشه که واقعاً طوفانِ نوح اتفاق می‌افته؟»
    L3=(21.73, 28.76),      # «بیست و یک پاییز … گرفته.» (the preamble before 21.72 is dropped)
    L4=(29.22, 32.36),      # «به‌طورِ میانگین بیست و سه درصد بیشتر از معمول.»
    L5=(32.92, 40.10),      # «زمستان‌ها ولی … سکه بندازیم.»
    L6=(41.18, 46.22),      # «پس شانسِ پاییزِ پرباران … نمی‌شه.»
    L7=(46.40, 48.62),      # «پاییزِ شهرِ شما چطور بوده تا الان؟»
)
TEXT = dict(
    n1="امسال ال‌نینو خیلی قوی بوده. خب این معنیش میشه که واقعاً طوفانِ نوح اتفاق می‌افته؟",
    n2="بیست و یک پاییز از بیست و شیش پاییزی که ال‌نینو بوده، ایران بارانِ بیشتری از معمول گرفته.",
    n3="به‌طورِ میانگین بیست و سه درصد بیشتر از معمول.",
    n4="زمستان‌ها ولی نیمی‌شون پرباران بود و نیمی‌شون کم‌باران. انگار که مثلاً سکه بندازیم.",
    n5="پس شانسِ پاییزِ پرباران بیشتر بوده، ولی طوفانِ نوح نمی‌شه. پاییزِ شهرِ شما چطور بوده تا الان؟",
)


def envelope_db(x: np.ndarray) -> np.ndarray:
    """1-ms RMS in dB over a 20-ms window (centred), full scale."""
    h, w = round(0.001 * SR), round(0.020 * SR)
    sq = np.pad(x.astype(float) ** 2, (w // 2, w // 2))
    c = np.cumsum(np.concatenate([[0.0], sq]))
    n = len(x) // h
    starts = np.arange(n) * h
    ms = (c[starts + w] - c[starts]) / w
    return 10 * np.log10(np.maximum(ms, 1e-12))


def snap(env: np.ndarray, t: float) -> float:
    """The quietest 1-ms point within SNAP of t (s)."""
    lo, hi = max(0, round((t - SNAP) * 1000)), min(len(env) - 1, round((t + SNAP) * 1000))
    return (lo + int(np.argmin(env[lo:hi + 1]))) / 1000.0


def seg(x: np.ndarray, a: float, b: float) -> np.ndarray:
    return x[round(a * SR):round(b * SR)]


def tone(seconds: float, x: np.ndarray, env: np.ndarray) -> np.ndarray:
    """The room's own tone, `seconds` long, from the quiet stretch GAP_TONE (looped if needed)."""
    t = seg(x, *GAP_TONE)
    reps = int(np.ceil(seconds * SR / len(t)))
    return np.tile(t, reps)[:round(seconds * SR)].copy()


def shorten_pauses(x: np.ndarray) -> np.ndarray:
    """Every internal pause (quiet, with speech on both sides) longer than PAUSE_MAX becomes PAUSE_KEEP long."""
    env = envelope_db(x)
    quiet = env < SPEECH_DB
    loud = env > -30.0
    runs, i = [], 0
    while i < len(quiet):
        if not quiet[i]:
            i += 1
            continue
        j = i
        while j < len(quiet) and quiet[j]:
            j += 1
        if i > 0 and j < len(quiet) and loud[:i].any() and loud[j:].any() and (j - i) / 1000.0 > PAUSE_MAX:
            runs.append((i, j))
        i = j
    print(f"    internal pauses over {PAUSE_MAX:.1f} s: {len(runs)}")
    ms = round(SR / 1000)
    for a, b in reversed(runs):
        keep = round(PAUSE_KEEP * 1000)
        head = keep // 2
        x = np.concatenate([x[:(a + head) * ms], x[(b - (keep - head)) * ms:]])
    return x


def clean(x: np.ndarray, tmp: Path) -> np.ndarray:
    """High-pass 70 Hz, gentle FFT noise reduction, compression at ratio 2.5 (ffmpeg), then the 10-ms fades."""
    src, dst = tmp / "in.wav", tmp / "out.wav"
    wavfile.write(str(src), SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
    chain = ("highpass=f=70:poles=2,afftdn=nr=6:nf=-50:tn=1,"
             "acompressor=threshold=0.0631:ratio=2.5:attack=10:release=200")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-af", chain,
                    "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", str(dst)], check=True)
    _, y = wavfile.read(str(dst))
    y = y.astype(float) / 32767.0
    k = round(FADE * SR)
    w = 0.5 - 0.5 * np.cos(np.linspace(0.0, np.pi, k))
    y[:k] *= w
    y[-k:] *= w[::-1]
    return y


def measure(y: np.ndarray) -> tuple:
    """The lead (silence before the first speech frame) and the speech length, in s."""
    env = envelope_db(y)
    on = np.flatnonzero(env > SPEECH_DB)
    lead = on[0] / 1000.0
    speech = (on[-1] - on[0] + 1) / 1000.0
    return round(lead, 4), round(speech, 4)


def main() -> None:
    _, raw = wavfile.read(str(RAW))
    assert raw.ndim == 1 and raw.dtype == np.int16, (raw.shape, raw.dtype)
    x = raw.astype(float) / 32768.0
    env = envelope_db(x)
    cut = {k: (snap(env, a), snap(env, b)) for k, (a, b) in CUTS.items()}
    for k, (a, b) in cut.items():
        print(f"  {k}: nominal {CUTS[k][0]:.2f}-{CUTS[k][1]:.2f} s, cut {a:.3f}-{b:.3f} s")
    gap = tone(0.35, x, env)
    gap3 = tone(0.30, x, env)
    parts = {
        "n1": [seg(x, *cut["L1"]), gap, seg(x, *cut["L2"])],
        "n2": [seg(x, cut["L3"][0], L3_PAUSE[0]), seg(x, L3_PAUSE[1], cut["L3"][1])],
        "n3": [seg(x, *cut["L4"])],
        "n4": [seg(x, *cut["L5"])],
        "n5": [seg(x, *cut["L6"]), gap3, seg(x, *cut["L7"])],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for name, pieces in parts.items():
            p = np.concatenate(pieces)
            if name == "n4":
                p = shorten_pauses(p)
            y = clean(p, tmp)
            lufs = kit.integrated_lufs(y)
            y = y * 10 ** ((LEVEL - lufs) / 20.0)
            tp = kit.true_peak_dbtp(y)
            assert tp <= -3.0, (name, tp)
            lead, speech = measure(y)
            assert lead >= 0.02, (name, lead)
            wavfile.write(str(OUT / f"{name}.wav"), SR, (np.clip(y, -1, 1) * 32767).astype(np.int16))
            manifest.append(dict(name=name, voice=VOICE, text=TEXT[name], lead=lead, speech=speech,
                                 length=round(len(y) / SR, 4), lufs=round(kit.integrated_lufs(y), 2),
                                 true_peak=round(tp, 2)))
            print(f"  {name}: lead {lead:.3f} s, speech {speech:.3f} s, length {len(y) / SR:.3f} s, "
                  f"{kit.integrated_lufs(y):+.2f} LUFS, {tp:+.2f} dBTP")
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()
