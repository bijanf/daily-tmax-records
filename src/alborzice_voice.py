"""THE OWNER'S VOICE AND FACE FOR «یخچال‌های البرز»: the chosen takes cut into one piece per scene.

The takes are chosen by reading the transcript (src/alborzice_transcribe.py) and written, by hand, into
data/alborzice/voice/pieces.json:

    {"hook":  {"file": "<recording>", "spans": [[12.30, 15.10]]},
     "takht": {"file": "<recording>", "spans": [[32.6, 41.0], [42.2, 50.0], [51.9, 61.7]], "cue_spans": [1, 2]},
     "face1": {"file": "<video's sound>", "video": "<video for the picture>", "spans": [[3.20, 8.05]], "face": true},
     "close": {"file": "<video>", "spans": [[13.6, 19.0], [19.6, 23.4], [4.1, 10.2, "<other file>"]], "face": true,
               "cue_spans": [1, 2]}, ...}

A scene's piece is its spans joined: a breath of 0.22 s and 15-ms fades between takes (none where one span ends
exactly where the next begins: such a cut only marks a turn); pauses longer than 0.32 s are shortened to 0.24 s.
"cue_spans" names the spans at which the narrator starts a later sentence: the picture turns there
(src/alborzice.py TURNS). A piece that is seen on camera ("face": true) keeps its first span untouched, because the
lips must match: the picture shows the video from LEAD before that span to its end ("face_until" seconds into the
piece, default the whole first span); later spans are heard over the film's own picture.

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

    def raw(path: str) -> np.ndarray:
        src = Path(path).expanduser()
        if src not in cache:
            cache[src] = audio(src)
        return cache[src]

    man = dict(lead=LEAD, tail=TAIL, pieces=[])
    for scene in SCENES:
        p = plan[scene]
        spans = [(float(sp[0]), float(sp[1]), sp[2] if len(sp) > 2 else p["file"]) for sp in p["spans"]]   # [start, end] or [start, end, file]
        parts, starts, t = [], [], 0.0
        # one gain per recording inside a piece (its loudest sample to 0.9): the pause detector's floor is absolute, and a
        # quiet recording (the phone a metre away) lost its soft last syllables to it («دارند», 13 Nov 2026)
        gain = {f: 0.9 / max(1e-6, max(float(np.max(np.abs(raw(f)[int(a * SR):int(b * SR)]))) for a, b, g in spans if g == f))
                for f in {sp[2] for sp in spans}}
        for k, (a, b, f) in enumerate(spans):
            x = raw(f)[int(a * SR):int(b * SR)] * gain[f]
            joined_before = k > 0 and spans[k - 1][2] == f and abs(spans[k - 1][1] - a) < 1e-6      # a cut only marks a turn: no fade
            joined_after = k + 1 < len(spans) and spans[k + 1][2] == f and abs(spans[k + 1][0] - b) < 1e-6
            if not (p.get("face") and k == 0):                 # the span seen on camera keeps its own timing: the lips must match
                x = squeeze_pauses(x, longest=0.32, keep=0.24)
            y = x.copy()
            n = min(len(y) // 2, int(SR * 0.015))
            r = np.linspace(0.0, 1.0, n)
            if not joined_before:
                y[:n] *= r
            if not joined_after:
                y[-n:] *= r[::-1]
            gap = np.zeros(0 if joined_before or k == 0 else int(0.22 * SR))     # a breath between two takes
            starts.append(t + len(gap) / SR)
            parts += [gap, y]
            t += (len(gap) + len(y)) / SR
        y = np.concatenate(parts)
        entry = dict(scene=scene)
        if p.get("face"):
            a0, b0, f0 = spans[0]
            shown = float(p.get("face_until", b0 - a0))
            assert shown <= b0 - a0 + 1e-6, (scene, "face_until is past the first span")
            tail = TAIL if len(spans) == 1 and "face_until" not in p else 0.0      # a one-take scene keeps the face to its end
            came = max(0.0, float(p.get("face_in", a0 - LEAD)) - (a0 - LEAD))       # "face_in": the video's second from which it is usable
            entry.update(face=dict(video=str(Path(p.get("video", f0)).expanduser()), video_start=round(a0 - LEAD, 3),
                                   shown=round(LEAD + shown + tail, 3), **({"from": round(came, 3)} if came > 0 else {})))
        peak = float(np.max(np.abs(y)))
        wavfile.write(OUT / f"v_{scene}.wav", SR, np.int16(np.clip(y, -1, 1) * 32767))
        entry.update(seconds=round(len(y) / SR, 3), peak=round(peak, 3))
        if p.get("cue_spans"):                                # the later sentences start where these spans start
            entry["cues"] = [round(starts[i], 3) for i in p["cue_spans"]]
        man["pieces"].append(entry)
    (OUT / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(q["seconds"] + LEAD + TAIL for q in man["pieces"])
    print(f"reel about {total:.1f} s")
    for q in man["pieces"]:
        print(f"  {q['scene']:7s} {q['seconds']:6.2f} s  peak {q['peak']:.2f}  cues {q.get('cues', [])}"
              + ("  on camera " + str(q["face"]["shown"]) + " s" if "face" in q else ""))


if __name__ == "__main__":
    main()
