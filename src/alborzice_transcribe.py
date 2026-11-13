"""The owner's recordings for «یخچال‌های البرز», heard by a machine: every word with its time.

Nobody in this pipeline can listen, so the takes are found by reading: faster-whisper large-v3 (Persian, word
times) on each recording (a voice memo or a video); the words go to data/alborzice/voice/<stem>.words.json and a
readable list of takes (a take ends at a pause of 0.7 s or more) is printed. src/alborzice_voice.py then cuts the
chosen takes.

    venv_asr/bin/python src/alborzice_transcribe.py <recording> [<recording> ...]
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "alborzice" / "voice"
PAUSE = 0.7


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    model = WhisperModel("large-v3", device="cpu", compute_type="int8")
    for src in map(Path, sys.argv[1:]):
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "a.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
            with wave.open(str(wav)) as wf:               # the samples themselves: PyAV's file reader is skipped
                pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
            segs, info = model.transcribe(pcm, language="fa", word_timestamps=True, vad_filter=True,
                                          vad_parameters=dict(min_silence_duration_ms=400), beam_size=5,
                                          condition_on_previous_text=False)
            words = [dict(w=w.word.strip(), a=round(w.start, 2), b=round(w.end, 2)) for s in segs for w in (s.words or [])]
        (OUT / f"{src.stem}.words.json").write_text(json.dumps(dict(source=str(src), duration=round(info.duration, 2), words=words),
                                                               ensure_ascii=False, indent=0), encoding="utf-8")
        print(f"\n===== {src.name}: {info.duration:.1f} s, {len(words)} words")
        take: list = []
        for i, w in enumerate(words):
            take.append(w)
            if i == len(words) - 1 or words[i + 1]["a"] - w["b"] >= PAUSE:
                print(f"[{take[0]['a']:7.2f} - {take[-1]['b']:7.2f}] " + " ".join(x["w"] for x in take))
                take = []


if __name__ == "__main__":
    main()
