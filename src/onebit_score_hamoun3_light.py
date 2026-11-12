"""The light score of the third Hamoun reel (hamoun3_fa, the satellite picture as the whole frame; no narration): the
light score's setar and checks (onebit_score_air_light.py, imported, not copied), on the clock that src/hamoun3.py
writes into film.json, in D Esfahan (D E F G A Bb C#: twelve-tone, no koron), as the second film's score.

    the notes     a soft D5 at 0.00 s (frame 0 is not silent), A4 as the wipe starts, a low D4 as the water goes;
                  the "where" scene and its border; during the springs a soft note only on the beats that matter:
                  1366, 1367, 1371 (the fullest), 1375, 1378; 1379 a low D4 (the lake nearly empty); after it a note
                  on 1384 and 1388 (above the mean), 1398 (above the mean); 1405 a low D4; the "why" scene and its
                  card; the dams, one soft note each; this spring, the question, the call; the ending, D4 and A4
                  struck together, ringing out before the end. Consonant pairs only (checked).
    the level     -14 LUFS, true peak -1 dBTP or lower after AAC (the music is the only sound).

Writes hamoun3_fa_music.wav and hamoun3_fa_music_reel.mp4 (the silent master hamoun3_fa_reel.mp4 with this track;
its video stream copied). --force replaces this film's own earlier outputs.

    python -I src/onebit_score_hamoun3_light.py [--force]
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
FILM = ROOT / "outputs" / "onebit" / "hamoun3" / "film.json"
SR = kit.SR
BASE = "hamoun3_fa"
LUFS, MASTER_TP, TP_WAV, TP_AAC = -14.0, -2.0, -1.5, -1.0
VEL_SOFT, VEL, VEL_HOLD, VEL_MARK = 0.55, 0.80, 0.90, 0.45
MODE = {2, 4, 5, 7, 9, 10, 1}                        # pitch classes of D Esfahan (D E F G A Bb C#)
ABOVE = (18, 20, 22, 32, 33)                         # springs after 1379 above the mean: 1384 1386 1388 1398 1399


def score_notes(film: dict) -> tuple:
    c, s = film["clock"], film["springs"]
    end = film["end"]
    assert [k for k in range(13, 40) if s[k]["above"]] == list(ABOVE), "the springs above the mean after 1379"
    t = lambda k: s[k]["t"]                           # noqa: E731  (the spring k's onset; k = 0: 1366)
    ending = end - 2.2
    plan = (
        (0.00, 74, VEL_SOFT),                        # D5: soft, the first sound (frame 0 is not silent)
        (c["wipe"][0], 69, VEL),                     # A4: the wipe starts
        (sum(c["wipe"]) / 2 + 0.05, 62, VEL),        # D4: the water goes
        (c["where"], 65, VEL),                       # F4: where it lies
        (c["border"][1], 69, VEL_SOFT),              # A4: the border is drawn
        (c["run"], 74, VEL_SOFT),                    # D5: into the springs
        (t(0), 65, VEL),                             # F4: 1366
        (t(1) + 0.1, 69, VEL_MARK), (t(5), 74, 0.70), (t(9), 77, VEL_MARK), (t(12), 74, VEL_MARK),   # 1367 1371 1375 1378
        (t(13) + 0.1, 62, VEL),                      # 1379: D4, low (nearly empty)
        (t(18), 69, VEL_MARK), (t(22), 74, VEL_MARK),   # 1384 1388: above the mean
        (t(32), 77, VEL_MARK),                       # 1398: above the mean
        (t(39), 62, VEL),                            # 1405: D4
        (c["why"], 70, VEL),                         # Bb4: why? the rain and the lake
        (c["card"] + 0.6, 65, VEL_MARK),             # F4: the two bars
        (c["where2"], 69, VEL),                      # A4: where did the water go
        (c["pins"][0] + 0.05, 74, VEL_SOFT),         # D5: Kajaki
        (c["pins"][1], 65, VEL_MARK),                # F4: the irrigated land
        (c["pins"][2], 69, VEL_MARK),                # A4: Kamal Khan
        (c["pins"][3], 74, VEL_SOFT),                # D5: Chah-nimeh
        (c["now"], 65, VEL),                         # F4: this spring against the mean
        (c["ask"], 69, VEL),                         # A4: the question
        (c["follow"], 74, VEL_SOFT),                 # D5: the call
        (ending, 62, VEL),                           # D4: the ending, an open fifth on the tonic
        (ending, 69, VEL),                           # A4
    )
    allnotes = sorted(plan, key=lambda p: p[0])
    assert all(m % 12 in MODE for _, m, _ in allnotes), "every note is in D Esfahan"
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
