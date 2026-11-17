"""The light score of «آبِ خزر کجا رفت؟» (khazar_fa, both cuts; no narration): the light score's setar and checks
(onebit_score_air_light.py, imported, not copied), on the clock that src/khazar.py writes into film.json, on E with
E, G and B only (every pair that rings together is consonant; the mode's other notes are not used). A soft E5 on the
first picture; the wipe back to 2001 falls to E4 and the wipe forward rises to E5 again; through the run of the
summers the notes fall as the sea does and the last summer is struck on E5; a note on the first dam and on the last;
the river's four low years on E5; the sea's peak of 1374 on E5 and the way down after it; rising notes with the
vapour; a note on each line that arrives and a soft note in each reading hold (no second of digital silence: check f); the ending, E4 and B4 struck
together, rings out before the loop. The two cuts share one clock, so the music is the same.
    the level     -14 LUFS, true peak -1 dBTP or lower after AAC (the music is the only sound).

    python -I src/onebit_score_khazar_light.py --cut b [--force]
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
FILM = ROOT / "outputs" / "onebit" / "khazar" / "film.json"
SR = kit.SR
CUTS = ("a", "b")
LUFS, MASTER_TP, TP_WAV, TP_AAC = -14.0, -2.0, -1.5, -1.0
VEL_SOFT, VEL, VEL_HOLD, VEL_MARK = 0.55, 0.80, 0.90, 0.45
MODE = {4, 7, 11}                                    # E, G and B


def score_notes(film: dict) -> tuple:
    c = film["clock"]
    end = film["end"]
    ending = end - 2.2
    ab, af, yr, pins = c["a_back"], c["a_fwd"], c["years"], c["pins"]
    E4, G4, B4, E5 = 64, 67, 71, 76
    peak = c["line"][0] + (c["line"][1] - c["line"][0]) * 57 / 86      # the line reaches 1995, the sea's highest year
    plan = (
        (0.00, E5, VEL_SOFT),                        # soft, the first sound: the sea now, inside the shore of 2001
        (ab[0], B4, VEL_MARK),                       # the wipe back starts ...
        (ab[1], E4, VEL),                            # ... the summer of 2001
        (af[0], G4, VEL_MARK),                       # forward again ...
        (af[1], E5, VEL),                            # ... now
        (c["ruler"] + 0.45, B4, VEL),                # the ruler (not closer than 0.35 s to the wipe's end)
        (c["ruler"] + 2.0, G4, VEL_MARK),
        (c["b"][0], E4, VEL),                        # the run of the summers
        (yr[0], E5, VEL_SOFT),                       # 2001 ...
        (yr[7], B4, VEL_MARK),                       # ... the notes fall as the sea does ...
        (yr[14], G4, VEL_MARK),
        (yr[20], E4, VEL_MARK),
        (yr[25], E5, VEL),                           # ... the last summer
        (yr[25] + 1.25, G4, VEL_MARK),
        (c["c"][0], E4, VEL),                        # the map
        (c["chip_c"], B4, VEL_MARK),                 # the river's share
        (pins[0], G4, VEL),                          # the first dam
        (pins[4], B4, VEL_MARK),
        (pins[8], G4, VEL_MARK),
        (pins[10], E5, VEL),                         # the last dam
        (pins[10] + 1.4, B4, VEL_MARK),
        (c["e"][0], E4, VEL),                        # the river's years
        (c["e"][0] + 1.6, G4, VEL_MARK),             # the columns grow
        (c["bars"][1], B4, VEL_MARK),                # the columns stand
        (c["late"], E5, VEL),                        # the four low years
        (c["late"] + 1.6, G4, VEL_MARK),
        (c["late"] + 3.2, B4, VEL_MARK),
        (c["f"][0], E4, VEL),                        # Iran's coast
        (c["small_f"], G4, VEL_MARK),                # the damage
        (peak, E5, VEL),                             # the sea's highest year
        (peak + 1.0, B4, VEL_MARK),                  # down again ...
        (peak + 2.6, G4, VEL_MARK),
        (peak + 4.1, B4, VEL_MARK),
        (c["g"][0], E4, VEL),                        # why
        (c["small_g"], G4, VEL_MARK),                # the shares are open
        (c["small_g"] + 1.0, B4, VEL),               # the vapour rises ...
        (c["small_g"] + 2.5, E5, VEL_MARK),
        (c["small_g"] + 4.0, G4, VEL_MARK),
        (c["h"][0], E5, VEL),                        # the question
        (c["follow"], B4, VEL),                      # the call
        (c["follow"] + 1.3, G4, VEL_MARK),
        (ending, E4, VEL),                           # the ending, an open fifth
        (ending, B4, VEL),
    )
    allnotes = sorted(plan, key=lambda p: p[0])
    assert all(m % 12 in MODE for _, m, _ in allnotes), "E, G and B only"
    notes = [light.Note(float(tt), m, vel, light.PAN if i % 2 == 0 else -light.PAN)
             for i, (tt, m, vel) in enumerate(allnotes)]
    assert notes[-1].t < end - 1.5, "the ending must ring out before the end"
    return sorted(notes, key=lambda nt: nt.t), end


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cut", choices=CUTS, default="b")
    ap.add_argument("--force", action="store_true", help="replace this film's earlier music outputs")
    args = ap.parse_args()
    BASE = f"khazar_fa_{args.cut}"
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
    print("the notes (E, G, B):")
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
    # the loudness in every one-second window (0.1-s steps): no stretch of digital silence (the 12 Nov lesson; code
    # review of 16 Nov: whole seconds alone missed a 1.4-s gap)
    mono = m.mean(axis=1)
    hop = SR // 10
    rms = [20 * np.log10(np.sqrt(np.mean(mono[k:k + SR] ** 2)) + 1e-12) for k in range(0, len(mono) - SR, hop)]
    last = int((end - 1.5) * 10)                                             # the ending's fade is allowed to go quiet
    low = min(rms[:last])
    print(f"(f) quietest one-second window before the ending: {low:.1f} dBFS at {rms.index(low) / 10:.1f} s (limit -70)")
    if low < -70:
        fails.append("(f) a silent second")
    print("saved", wav, "\nsaved", mp4)
    if fails:
        sys.exit("CHECKS NOT PASSED: " + "; ".join(fails))
    print("all checks pass")


if __name__ == "__main__":
    main()
