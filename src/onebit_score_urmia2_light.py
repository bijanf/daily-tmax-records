"""The light score of the second Urmia reel (urmia2_fa; no narration): the light score's setar and checks
(onebit_score_air_light.py, imported, not copied), on the clock that src/urmia2.py writes into film.json, in G Mahur
(G A B C D E F#: twelve-tone, no koron). Few notes, each on a cue: a soft D5 at 0.00 s, the wipe and the water
appearing, the rise of the water (G4 B4 D5), the area, the second wipe, the summer and the sinking level (B4, A4), the
gap with G5 (the highest note) on the dashed line, the close, the call, and the ending, G4 and D5 struck together,
ringing out before the end. Consonant pairs only (checked).
    the level     -14 LUFS, true peak -1 dBTP or lower after AAC (the music is the only sound).

Writes urmia2_fa_music.wav and urmia2_fa_music_reel.mp4 (the silent master urmia2_fa_reel.mp4 with this track;
its video stream copied). --force replaces this film's own earlier outputs.

    python -I src/onebit_score_urmia2_light.py [--force]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
import onebit_persian as kit  # noqa: E402
import onebit_score_air_light as light  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FILM = ROOT / "outputs" / "onebit" / "urmia2" / "film.json"
SR = kit.SR
BASE = "urmia2_fa"
LUFS, MASTER_TP, TP_WAV, TP_AAC = -14.0, -2.0, -1.5, -1.0
VEL_SOFT, VEL, VEL_HOLD, VEL_MARK = 0.55, 0.80, 0.90, 0.45
MODE = {7, 9, 11, 0, 2, 4, 6}                        # pitch classes of G Mahur (G A B C D E F#)


def score_notes(film: dict) -> tuple:
    c = film["clock"]
    end = film["end"]
    ending = end - 2.2
    w1, rise, w2 = c["wipe1"], c["rise"], c["wipe2"]
    plan = (
        (0.00, 74, VEL_SOFT),                        # D5: soft, the first sound (frame 0 is not silent)
        (w1[0], 67, VEL),                            # G4: the wipe starts
        (sum(w1) / 2, 71, VEL),                      # B4: the water appears ...
        (sum(w1) / 2 + 0.42, 74, VEL),               # D5: ... a small rising figure
        (c["up"], 67, VEL),                          # G4: the level
        (rise[0], 67, VEL_MARK), (sum(rise) / 2, 71, VEL_MARK), (rise[1], 74, VEL),   # the water rises: G4 B4 D5
        (c["area"], 76, VEL_SOFT),                   # E5: the area
        (w2[0], 67, VEL),                            # G4: the second wipe starts
        (w2[1], 71, VEL),                            # B4: it ends
        (c["summer"], 69, VEL),                      # A4: the summer
        (c["june_in"][1], 74, VEL),                  # D5: June's level
        (c["june_out"][0] + 0.1, 71, VEL),           # B4: the level sinks ...
        (c["june_out"][1], 69, VEL),                 # A4: ... and arrives
        (c["gap"], 67, VEL),                         # G4: the gap
        (c["eco"][1], 79, VEL_SOFT),                 # G5: the dashed line, the highest note
        (c["parts"][1], 76, VEL_SOFT),               # E5: the missing stretch
        (c["close"], 74, VEL),                       # D5: the close
        (c["follow"], 71, VEL),                      # B4: the call
        (ending, 67, VEL),                           # G4: the ending, an open fifth on the tonic
        (ending, 74, VEL),                           # D5
    )
    allnotes = sorted(plan, key=lambda p: p[0])
    assert all(m % 12 in MODE for _, m, _ in allnotes), "every note is in G Mahur"
    assert max(m for _, m, _ in allnotes) == 79 and [m for _, m, _ in allnotes].count(79) == 1, "G5 is the highest, once"
    notes = [light.Note(float(tt), m, vel, light.PAN if i % 2 == 0 else -light.PAN)
             for i, (tt, m, vel) in enumerate(allnotes)]
    assert notes[-1].t < end - 1.5, "the ending must ring out before the end"
    return sorted(notes, key=lambda nt: nt.t), end


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="replace this film's earlier music outputs")
    args = ap.parse_args()
    film = json.loads(FILM.read_text(encoding="utf-8"))
    social = onebit.OUT / "social"
    video = social / f"{BASE}_reel.mp4"
    if video.stat().st_mtime < FILM.stat().st_mtime:
        sys.exit(f"{video.name} is older than film.json: render the film first")
    wav, mp4 = social / f"{BASE}_music.wav", social / f"{BASE}_music_reel.mp4"
    for f in (wav, mp4):
        if f.exists():
            if not args.force:
                sys.exit(f"{f.name} exists: pass --force to replace it")
            f.unlink()
    notes, end = score_notes(film)
    kit.reseed(43)
    track = kit.new_track(end, light.TAIL)
    for nt in notes:
        kit.place(track, light.pluck(nt.midi, nt.vel), nt.t, 1.0, nt.pan)
    k = round(0.025 * SR)
    track[:k] *= (0.5 - 0.5 * np.cos(np.linspace(0.0, np.pi, k)))[:, None]
    stem = light._bass_mono(light._air_cut(track))
    music = kit.master(stem, lufs=LUFS, tp=MASTER_TP, seconds=end, fade_out=1.0)
    light.write_wav(wav, music)
    before = os.stat(video)
    kit.mux(video, wav, mp4)
    print("the notes (G Mahur):")
    for nt in notes:
        print(f"    {nt.t:6.2f} s  {light.NAMES[nt.midi % 12]}{nt.midi // 12 - 1}")
    fails = []
    m = light._read_wav(wav)
    tested, min_fall, sustained = light.check_sustained(m.mean(axis=1))
    print(f"(a) onsets {tested}; smallest fall in 2 s {min_fall:.1f} dB (limit 12); sustained {sustained}")
    if sustained or min_fall < 12.0:
        fails.append("(a) a sustained tone")
    on = sorted({nt.t for nt in notes})
    rate = max(sum(1 for u in on if s0 <= u < s0 + 1.0) for s0 in np.arange(0.0, end, 0.01))
    gap = float(np.diff(on).min())
    print(f"(b) at most {rate} onsets in 1 s (limit 2); closest onsets {gap:.2f} s (limit 0.35)")
    if rate > 2 or gap < 0.35:
        fails.append("(b) too dense")
    pairs, classes, bad = light.check_intervals(notes)
    print(f"(c) {pairs} pairs ring together; intervals {classes}; violations {len(bad)}")
    if bad or not all(light.NOTE_RANGE[0] <= nt.midi <= light.NOTE_RANGE[1] for nt in notes):
        fails.append("(c) interval or register")
    lufs, tp = kit.integrated_lufs(m), kit.true_peak_dbtp(m)
    aac = kit.aac_true_peak(mp4)
    print(f"(d) {lufs:+.2f} LUFS, WAV {tp:+.2f} dBTP, decoded AAC {aac:+.2f} dBTP")
    if abs(lufs - LUFS) > 0.5 or tp > TP_WAV or aac > TP_AAC:
        fails.append("(d) level")
    if light._md5(video, "0:v:0") != light._md5(mp4, "0:v:0"):
        fails.append("(e) the video stream changed")
    after = os.stat(video)
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        fails.append("(e) the silent reel was rewritten")
    print("saved", wav, "\nsaved", mp4)
    if fails:
        sys.exit("CHECKS NOT PASSED: " + "; ".join(fails))
    print("all checks pass")


if __name__ == "__main__":
    main()
