"""THE OWNER'S VOICE AND FACE FOR «یخچال‌های البرز»: the chosen takes cut into one piece per scene.

The takes are chosen by reading the transcript (src/alborzice_transcribe.py) and written, by hand, into
data/alborzice/voice/pieces.json:

    {"hook":  {"file": "<recording>", "spans": [[12.30, 15.10]]},
     "face1": {"file": "<video>", "spans": [[3.20, 8.05]], "face": true},
     "close": {"file": "<video>", "spans": [[20.1, 24.3], [30.0, 33.2]], "face": true, "face_until": 4.2}, ...}

"cues": [seconds into the finished piece at which each later sentence starts] makes the picture turn with the
voice (src/alborzice.py TURNS). A scene's piece is its spans joined (15-ms fades at every cut); pauses longer than 0.40 s inside a voice-only piece
are shortened to 0.30 s. A piece that is seen on camera ("face": true) keeps its first span untouched, because the
lips must match: the picture shows the video from LEAD before that span to its end ("face_until" seconds into the
piece, default the whole first span), and later spans are heard over the film's own picture.

    data/alborzice/voice/v_<scene>.wav     48 kHz mono
    data/alborzice/voice/manifest.json     per scene: seconds (the film's clock), and for a face scene the video,
                                           the time in it where the scene starts and how long the face is shown

    python -I src/alborzice_voice.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

from damsexplain_voice import fade, squeeze_pauses  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "alborzice" / "voice"
SR = 48000
LEAD, TAIL = 0.3, 0.5                               # as in src/alborzice.py
SCENES = ("hook", "face1", "dam", "takht", "mech", "budget", "thr", "fut", "close")


def audio(src: Path) -> np.ndarray:
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "a.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le",
                        str(wav)], check=True)
        rate, x = wavfile.read(wav)
    assert rate == SR
    return x.astype(np.float64) / 32768.0


def main() -> None:
    plan = json.loads((OUT / "pieces.json").read_text(encoding="utf-8"))
    assert set(plan) == set(SCENES), sorted(set(SCENES) ^ set(plan))
    cache: dict = {}
    man = dict(lead=LEAD, tail=TAIL, pieces=[])
    for scene in SCENES:
        p = plan[scene]
        src = Path(p["file"]).expanduser()
        if src not in cache:
            cache[src] = audio(src)
        raw = cache[src]
        parts = [fade(raw[int(a * SR):int(b * SR)]) for a, b in p["spans"]]
        entry = dict(scene=scene)
        if p.get("face"):
            a0, b0 = p["spans"][0]
            rest = squeeze_pauses(np.concatenate(parts[1:])) if len(parts) > 1 else np.zeros(0)
            gap = np.zeros(int(0.25 * SR)) if len(parts) > 1 else np.zeros(0)
            y = np.concatenate([parts[0], gap, rest])
            shown = float(p.get("face_until", b0 - a0))
            assert shown <= b0 - a0 + 1e-6, (scene, "face_until is past the first span")
            entry.update(face=dict(video=str(src), video_start=round(a0 - LEAD, 3), shown=round(LEAD + shown, 3)))
        else:
            y = squeeze_pauses(np.concatenate(parts))
        peak = float(np.max(np.abs(y)))
        wavfile.write(OUT / f"v_{scene}.wav", SR, np.int16(np.clip(y, -1, 1) * 32767))
        entry.update(seconds=round(len(y) / SR, 3), peak=round(peak, 3))
        if p.get("cues"):                                 # seconds into the piece at which the later sentences start
            entry["cues"] = [round(float(c), 3) for c in p["cues"]]
        man["pieces"].append(entry)
    (OUT / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(q["seconds"] + LEAD + TAIL for q in man["pieces"])
    print(f"reel about {total:.1f} s")
    for q in man["pieces"]:
        print(f"  {q['scene']:7s} {q['seconds']:6.2f} s  peak {q['peak']:.2f}" + ("  on camera " + str(q["face"]["shown"]) + " s" if "face" in q else ""))


if __name__ == "__main__":
    main()
