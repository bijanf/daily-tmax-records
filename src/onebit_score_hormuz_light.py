"""The light score of the Hormuz NO2 film (hormuz_fa; no narration): the light score's setar and checks
(onebit_score_air_light.py, imported, not copied), on the clock that src/hormuz.py writes into film.json, on D with
D, F and A only (every pair that rings together is consonant; the mode's other notes are not used). A soft D5 on the
first picture; the wipe to this year's map falls to D4 and the wipe back rises to D5; a note with the names; with
the ships a note as the lane is drawn, one where the map is wiped to this year and D4 where this year's picture
stands; a note on each of the six places as it is named; in the chart a D5 on the columns of the closure and a note
on the line that names them; a note in each reading hold (no second of digital silence: check f); the ending, D4 and
A4 struck together, rings out before the loop.
    the level     -14 LUFS, true peak -1 dBTP or lower after AAC (the music is the only sound).

    python -I src/onebit_score_hormuz_light.py [--force]
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
FILM = ROOT / "outputs" / "onebit" / "hormuz" / "film.json"
SR = kit.SR
LUFS, MASTER_TP, TP_WAV, TP_AAC = -14.0, -2.0, -1.5, -1.0
VEL_SOFT, VEL, VEL_HOLD, VEL_MARK = 0.55, 0.80, 0.90, 0.45
MODE = {2, 5, 9}                                     # D, F and A


def score_notes(film: dict) -> tuple:
    c = film["clock"]
    end = film["end"]
    ending = end - 2.2
    go, bk, st = c["a_go"], c["a_back"], c["sites"]
    D4, F4, A4, D5 = 62, 65, 69, 74
    b0, c0, e0, f0, h0 = c["b"][0], c["c"][0], c["e"][0], c["f"][0], c["h"][0]
    plan = (
        (0.00, D5, VEL_SOFT),                        # soft, the first sound: last year's map
        (go[1], D4, VEL),                            # this year's map
        (bk[0], F4, VEL_MARK),                       # the wipe back starts ...
        (bk[1], D5, VEL),                            # ... last year again
        (bk[1] + 1.6, A4, VEL_MARK),                 # the hold: the colour bar and the days are read
        (bk[1] + 3.0, F4, VEL_MARK),
        (b0, D4, VEL),                               # what the colour is
        (c["names_b"] + 0.5, A4, VEL_MARK),          # the names
        (c["names_b"] + 2.1, F4, VEL_MARK),
        (c["names_b"] + 3.7, A4, VEL_MARK),
        (c["names_b"] + 5.3, F4, VEL_MARK),
        (c0, D4, VEL),                               # the ships
        (c["lane"][1], A4, VEL),                     # the lane is drawn
        (c["c_wipe"][0] + 0.1, D5, VEL),             # the wipe to this year starts
        (c["c_wipe"][1], D4, VEL),                   # this year's picture stands
        (c["c_note"] + 0.2, A4, VEL_MARK),           # the note on the count
        (c["c_share"] + 0.2, F4, VEL_MARK),          # not the ships alone
        (c["c_share"] + 1.8, A4, VEL_MARK),
        (c["c_share"] + 3.3, F4, VEL_MARK),
        (e0, D4, VEL),                               # the places, this year
        (st[0], D5, VEL),                            # the six places, one after another
        (st[1], A4, VEL_MARK),
        (st[2], F4, VEL_MARK),
        (st[3], A4, VEL_MARK),
        (st[4], F4, VEL_MARK),
        (st[5], D4, VEL),
        (st[5] + 1.5, A4, VEL_MARK),
        (st[5] + 3.0, F4, VEL_MARK),
        (f0, D4, VEL),                               # every part of the year
        (c["f_key"], A4, VEL_MARK),                  # the columns come, with the line that names the closure's
        (c["parts"][0] + 1.9, D5, VEL),              # the closure's columns hang below the line
        (c["f_low"] + 0.1, F4, VEL),                 # the deepest of them is named
        (c["f_low"] + 1.7, A4, VEL_MARK),
        (c["f_low"] + 3.1, F4, VEL_MARK),
        (h0, D5, VEL),                               # the question
        (c["follow"], A4, VEL),                      # the call
        (c["follow"] + 1.3, F4, VEL_MARK),
        (ending, D4, VEL),                           # the ending, an open fifth
        (ending, A4, VEL),
    )
    allnotes = sorted(plan, key=lambda p: p[0])
    assert all(m % 12 in MODE for _, m, _ in allnotes), "D, F and A only"
    notes = [light.Note(float(tt), m, vel, light.PAN if i % 2 == 0 else -light.PAN)
             for i, (tt, m, vel) in enumerate(allnotes)]
    assert notes[-1].t < end - 1.5, "the ending must ring out before the end"
    return sorted(notes, key=lambda nt: nt.t), end


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="replace this film's earlier music outputs")
    args = ap.parse_args()
    BASE = "hormuz_fa"
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
    print("the notes (D, F, A):")
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
