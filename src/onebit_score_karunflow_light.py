"""The light score of «آبِ کارون کجا رفت؟» (karunflow_fa; no narration): the light score's setar and checks
(onebit_score_air_light.py, imported, not copied), on the clock that src/karunflow.py writes into film.json, in G Mahur,
the Karun reel's mode, with G, B and D only (every pair that rings together is consonant). The notes fall as the second
bar stops at half (D5, B4, G4, then a low D4 under the half mark); D5 on each new headline, the spring curve's peak
on D5 and the low D4 on the spring mark; a soft note in each long reading hold (no second of digital silence: check f);
the ending, G4 and D5 struck together, rings out before the loop.
    the level     -14 LUFS, true peak -1 dBTP or lower after AAC (the music is the only sound).

    python -I src/onebit_score_karunflow_light.py [--force]
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
FILM = ROOT / "outputs" / "onebit" / "karunflow" / "film.json"
SR = kit.SR
BASE = "karunflow_fa"
LUFS, MASTER_TP, TP_WAV, TP_AAC = -14.0, -2.0, -1.5, -1.0
VEL_SOFT, VEL, VEL_HOLD, VEL_MARK = 0.55, 0.80, 0.90, 0.45
MODE = {7, 9, 11, 0, 2, 4, 6}                        # pitch classes of G Mahur (G A B C D E F#)


def score_notes(film: dict) -> tuple:
    S, Q = film["cut"]["scenes"], film["cut"]["cues"]
    end = film["end"]
    ending = end - 2.2
    plan = (
        (0.00, 74, VEL_SOFT),                        # D5: soft, the first sound: the map, the first bar
        (Q["grow"][0], 71, VEL_MARK),                # B4: the second bar starts ...
        (Q["grow"][1], 67, VEL),                     # G4: ... and stops at half
        (Q["tick"][1] + 0.05, 62, VEL_MARK),         # D4: the half mark
        (S["low"][0], 74, VEL),                      # D5: the lowest nine years
        (Q["low_small"], 71, VEL_MARK),              # B4: every year under 400
        (S["year"][0], 67, VEL),                     # G4: the mean year
        (Q["curve_b"][1], 74, VEL),                  # D5: the spring flood of 1379-1386 drawn
        (Q["curve_a"][0] + 0.1, 67, VEL_MARK),       # G4: the flat year of 1387-1395 ...
        (Q["spring"], 62, VEL),                      # D4: ... the spring mark
        (S["why"][0], 67, VEL),                      # G4: the map again, the dry years
        (Q["lake"], 71, VEL_MARK),                   # B4: the Gotvand lake
        (Q["transfer"], 74, VEL_MARK),               # D5: the water carried east
        (Q["share"], 67, VEL),                       # G4: the hedge
        (S["close"][0] + 0.3, 74, VEL),              # D5: the close
        (Q["caveat"], 71, VEL_MARK),                 # B4: the record's end
        (Q["follow"], 67, VEL),                      # G4: the call
        (ending, 67, VEL),                           # G4: the ending, an open fifth on the tonic
        (ending, 74, VEL),                           # D5
        # one soft note in each long reading hold (the 12 Nov lesson: no second of digital silence; G, B, D only)
        (4.2, 71, VEL_MARK), (5.8, 67, VEL_MARK),
        (S["low"][0] + 2.8, 67, VEL_MARK), (S["low"][0] + 4.6, 71, VEL_MARK), (S["low"][0] + 6.2, 74, VEL_MARK),
        (Q["spring"] + 1.7, 71, VEL_MARK),
        (Q["share"] + 1.7, 71, VEL_MARK), (Q["share"] + 3.4, 74, VEL_MARK), (Q["share"] + 5.0, 67, VEL_MARK),
        (Q["follow"] + 1.5, 71, VEL_MARK),
    )
    allnotes = sorted(plan, key=lambda p: p[0])
    assert all(m % 12 in (7, 11, 2) for _, m, _ in allnotes), "G, B and D only"
    assert all(m % 12 in MODE for _, m, _ in allnotes), "every note is in G Mahur"
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
    # the loudness each second: no stretch of digital silence (the 12 Nov lesson)
    mono = m.mean(axis=1)
    rms = [20 * np.log10(np.sqrt(np.mean(mono[int(s * SR):int((s + 1) * SR)] ** 2)) + 1e-12) for s in range(int(end))]
    print("(f) RMS per second (dBFS): " + " ".join(f"{r:.0f}" for r in rms))
    if min(rms[:-1]) < -70:
        fails.append("(f) a silent second")
    print("saved", wav, "\nsaved", mp4)
    if fails:
        sys.exit("CHECKS NOT PASSED: " + "; ".join(fails))
    print("all checks pass")


if __name__ == "__main__":
    main()
