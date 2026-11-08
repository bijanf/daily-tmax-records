"""The light score of the Hamoun reel, version 2 (hamoun2_fa, 30 s, no narration: the user's choice, 8 Nov 2026): the
light score's setar and checks (onebit_score_air_light.py, imported, not copied), on the clock of onebit_hamoun2.py,
in D Esfahan (D E F G A Bb C#: twelve-tone, no koron).

    the notes     a soft D5 at 0.00 s (frame 0 is not silent), A4 as the bars go; during the springs a soft note
                  only on the beats that matter: 1367, 1371 (the fullest), 1375, 1378 rising; 1379 a low D4 (the lake
                  nearly empty); after it a note only on the five springs above the mean (1384, 1386, 1388, 1398,
                  1399); 1405 a low D4; the chart's eras, the near-dry marks, the question; the ending, D4 and A4
                  struck together, ringing out before the end. Consonant pairs only (checked).
    the level     -14 LUFS, true peak -1 dBTP or lower after AAC (the music is the only sound).

Writes hamoun2_fa_music.wav and hamoun2_fa_music_reel.mp4 (the silent master hamoun2_fa_reel.mp4 with this track;
its video stream copied). Existing outputs are never overwritten.

    python -I src/onebit_score_hamoun2_light.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
import onebit_hamoun2 as film  # noqa: E402
import onebit_persian as kit  # noqa: E402
import onebit_score_air_light as light  # noqa: E402

SR = kit.SR
BASE = "hamoun2_fa"
END = 30.0
LUFS, MASTER_TP, TP_WAV, TP_AAC = -14.0, -2.0, -1.5, -1.0
VEL_SOFT, VEL, VEL_HOLD, VEL_MARK = 0.55, 0.80, 0.90, 0.45
ENDING_T = 28.0                                      # s: the ending, after the question has settled
MODE = {2, 4, 5, 7, 9, 10, 1}                        # pitch classes of D Esfahan (D E F G A Bb C#)
ABOVE = (18, 20, 22, 32, 33)                         # springs after 1379 above the mean: 1384 1386 1388 1398 1399


def clock() -> None:
    """The film's clock as this score was written for it. A change in onebit_hamoun2.py that moves it fails here."""
    assert film.DURATION == END and (film.T0, film.STEP1, film.T13, film.STEP2) == (2.4, 0.45, 8.4, 0.36)
    assert (film.REWIND, film.T_ERAS, film.T_DRY, film.T_NOW) == ((1.0, 2.2), 18.0, 18.4, 24.4)
    after = [k for k in range(13, 40) if film.bars_above(k)]
    assert tuple(after) == ABOVE, after


def score_notes() -> list:
    clock()
    t = film.spring_t                                 # the spring k's onset (k = 0: 1366)
    plan = (
        (0.00, 74, VEL_SOFT),                        # D5: soft, the first sound (frame 0 is not silent)
        (film.REWIND[0] + 0.2, 69, VEL),             # A4: the bars go
        (t(0), 65, VEL),                             # F4: 1366
        (t(1), 69, VEL_MARK), (t(5), 74, 0.70), (t(9), 77, VEL_MARK), (t(12), 74, VEL_MARK),   # 1367 1371 1375 1378
        (t(13), 62, VEL),                            # 1379: D4, low (nearly empty)
        (t(18), 69, VEL_MARK), (t(20), 74, VEL_MARK), (t(22), 69, VEL_MARK),   # 1384 1386 1388: above the mean
        (t(32), 77, VEL_MARK), (t(33), 74, VEL_MARK),   # 1398 1399: above the mean
        (t(39), 62, VEL),                            # 1405: D4
        (film.T_DRY, 74, VEL_HOLD),                  # D5: the chart alone, the eras and the near-dry springs
        (film.T_NOW, 65, VEL),                       # F4: 1405 against the mean
        (26.00, 69, VEL),                            # A4: the question
        (27.00, 74, VEL_SOFT),                       # D5
        (ENDING_T, 62, VEL),                         # D4: the ending, an open fifth on the tonic
        (ENDING_T, 69, VEL),                         # A4
    )
    allnotes = sorted(plan, key=lambda p: p[0])
    assert all(m % 12 in MODE for _, m, _ in allnotes), "every note is in D Esfahan"
    notes = [light.Note(float(tt), m, vel, light.PAN if i % 2 == 0 else -light.PAN)
             for i, (tt, m, vel) in enumerate(allnotes)]
    assert notes[-1].t < END - 1.5, "the ending must ring out before the end"
    return sorted(notes, key=lambda nt: nt.t)


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    social = onebit.OUT / "social"
    video = social / f"{BASE}_reel.mp4"
    if video.stat().st_mtime < Path(film.__file__).stat().st_mtime:
        sys.exit(f"{video.name} is older than src/onebit_hamoun2.py: render the film first")
    wav, mp4 = social / f"{BASE}_music.wav", social / f"{BASE}_music_reel.mp4"
    for f in (wav, mp4):
        if f.exists():
            sys.exit(f"{f.name} exists: the outputs are never overwritten; move it first")
    notes = score_notes()
    kit.reseed(41)
    track = kit.new_track(END, light.TAIL)
    for nt in notes:
        kit.place(track, light.pluck(nt.midi, nt.vel), nt.t, 1.0, nt.pan)
    k = round(0.025 * SR)
    track[:k] *= (0.5 - 0.5 * np.cos(np.linspace(0.0, np.pi, k)))[:, None]
    stem = light._bass_mono(light._air_cut(track))
    music = kit.master(stem, lufs=LUFS, tp=MASTER_TP, seconds=END, fade_out=1.0)
    light.write_wav(wav, music)
    before = os.stat(video)
    kit.mux(video, wav, mp4)
    print("the notes (D Esfahan):")
    for nt in notes:
        print(f"    {nt.t:6.2f} s  {light.NAMES[nt.midi % 12]}{nt.midi // 12 - 1}")
    fails = []
    m = light._read_wav(wav)
    tested, min_fall, sustained = light.check_sustained(m.mean(axis=1))
    print(f"(a) onsets {tested}; smallest fall in 2 s {min_fall:.1f} dB (limit 12); sustained {sustained}")
    if sustained or min_fall < 12.0:
        fails.append("(a) a sustained tone")
    on = sorted({nt.t for nt in notes})
    rate = max(sum(1 for u in on if s0 <= u < s0 + 1.0) for s0 in np.arange(0.0, END, 0.01))
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
