"""The light score of «۲ درجه گرم‌تر، یعنی چه؟» (twodeg2_fa; no narration): the light score's setar and checks
(onebit_score_air_light.py, imported, not copied), on the clock that src/twodeg2.py writes into film.json, in
A Esfahan (A B C D E F G#: twelve-tone, no koron). Few notes, each on a cue, and the pitch follows the picture:

    hook     a soft E5 at 0.00 s (frame 0 is not silent); the ring runs back (C5, A4, a low E4 on "1 time"); it counts
             up again in three rising figures that land on E5 (5 times), F5 (9) and A5 (14)
    mean     the turning Earth; the body's thermometer from A4 to F5 (the fever; F is the reel's note for heat)
    pile     the days fall into the pile (A4 C5 E5), the curve, the hot days; the pile moves (A4 D5 F5 G#5) and the
             days hotter than any before get B5, the highest note of the piece, once
    vapour   the two labels (air A4, vapour C5); each degree a rising figure, the second a step higher (to E5, to A5)
    rain     each rain a falling line that starts higher than the last (from E5, F5, A5) and lands on a higher note
             as the gauge fills (E4 at 100, A4 at 107, C5 at 114)
    answer   the question on F5, the call, and the ending, A4 and E5 struck together, ringing out before the end
    the level     -14 LUFS, true peak -1 dBTP or lower after AAC (the music is the only sound). Consonant pairs only
                  (checked): notes that ring together are thirds, fourths, fifths, sixths or octaves.

Writes twodeg2_fa_music.wav and twodeg2_fa_music_reel.mp4 (the silent master twodeg2_fa_reel.mp4 with this track;
its video stream copied). --force replaces this film's own earlier outputs.

    python -I src/onebit_score_twodeg2_light.py [--force]
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
FILM = ROOT / "outputs" / "onebit" / "twodeg2" / "film.json"
SR = kit.SR
BASE = "twodeg2_fa"
LUFS, MASTER_TP, TP_WAV, TP_AAC = -14.0, -2.0, -1.5, -1.0
VEL_SOFT, VEL, VEL_HOLD, VEL_MARK = 0.55, 0.80, 0.90, 0.45
MODE = {9, 11, 0, 2, 4, 5, 8}                        # pitch classes of A Esfahan (A B C D E F G#)
E4, A4, B4, C5, D5, E5, F5, GS5, A5, B5 = 64, 69, 71, 72, 74, 76, 77, 80, 81, 83


def score_notes(film: dict) -> tuple:
    cut, q = film["cuts"]["a"], film["cues"]
    end = cut["end"]
    s = {sc["key"]: sc["start"] for sc in cut["scenes"]}
    hook, mean, pile, vap, rain, ans = (s[k] for k in ("hook", "mean", "pile", "vapour", "rain", "answer"))
    back, rise = q["hook"]["rewind"], q["hook"]["rise"]
    merc, shift = q["mean"]["mercury"], q["pile"]["shift"]
    warm, fill = q["vapour"]["warm"], q["rain"]["fill"]
    mid = lambda r, f=0.5: r[0] + f * (r[1] - r[0])   # noqa: E731
    ending = end - 2.2
    plan = (
        # hook: the end state, back to the time before industry, up again to 5, 9 and 14 times
        (hook + 0.00, E5, VEL_SOFT),                 # the first sound (frame 0 is not silent)
        (hook + back[0], C5, VEL),                   # the ring runs back ...
        (hook + mid(back), A4, VEL),
        (hook + back[1], E4, VEL_HOLD),              # ... to one time in 50 years: the lowest note
        (hook + rise[0][0], A4, VEL_MARK), (hook + mid(rise[0]), C5, VEL_MARK), (hook + rise[0][1], E5, VEL),      # about 5 times
        (hook + mid(rise[1]), D5, VEL_MARK), (hook + rise[1][1], F5, VEL),                                         # about 9 times
        (hook + rise[2][0], C5, VEL_MARK), (hook + mid(rise[2]), E5, VEL_MARK), (hook + rise[2][1], A5, VEL_HOLD),  # about 14 times
        (hook + rise[2][1] + 1.3, A4, VEL_SOFT),     # the answer settles
        # mean: the turning Earth, the body's thermometer from 37 to 39
        (mean + 0.00, E5, VEL_SOFT),
        (mean + q["mean"]["body"], C5, VEL),         # the thermometer appears: 37, normal
        (mean + merc[0], A4, VEL_MARK), (mean + mid(merc), D5, VEL_MARK), (mean + merc[1], F5, VEL),               # 39: fever
        (mean + merc[1] + 1.5, A4, VEL_SOFT),        # a breath while the slide is read (no hold of the film is silent for 2 s)
        # pile: a hundred summer days, the pile moves, the days hotter than any before
        (pile + 0.00, A4, VEL_SOFT), (pile + 0.90, C5, VEL_MARK), (pile + 1.80, E5, VEL_MARK),                     # the days fall into the pile
        (pile + 2.90, A4, VEL),                      # the curve is drawn
        (pile + q["pile"]["pulse"], E5, VEL_SOFT),   # the very hot days: 3
        (pile + shift[0], A4, VEL_MARK), (pile + mid(shift, 0.34), D5, VEL_MARK), (pile + mid(shift, 0.68), F5, VEL_MARK),
        (pile + shift[1], GS5, VEL),                 # 13 very hot days: the leading tone
        (pile + q["pile"]["record"], B5, VEL_HOLD),  # hotter than any day before: the highest note, once
        (pile + q["pile"]["record"] + 1.4, E5, VEL_SOFT), (pile + q["pile"]["record"] + 2.8, C5, VEL_MARK),
        # vapour: the box of air; each degree lifts 7 more water molecules out of the sea
        (vap + 0.00, E5, VEL_SOFT),
        (vap + q["vapour"]["legend"][0], A4, VEL_MARK), (vap + q["vapour"]["legend"][1], C5, VEL_MARK),            # air, water vapour
        (vap + warm[0][0], A4, VEL), (vap + mid(warm[0]), C5, VEL_MARK), (vap + warm[0][1], E5, VEL),              # 107
        (vap + warm[1][0], C5, VEL), (vap + mid(warm[1]), E5, VEL_MARK), (vap + warm[1][1], A5, VEL),              # 114, a step higher
        (vap + warm[1][1] + 1.5, E5, VEL_SOFT),
        # rain: each rain falls from higher and the gauge's note climbs
        (rain + 0.00, E5, VEL_SOFT),
        (rain + fill[0][0], C5, VEL_MARK), (rain + mid(fill[0]), A4, VEL_MARK), (rain + fill[0][1], E4, VEL),      # 100
        (rain + fill[1][0], F5, VEL_MARK), (rain + mid(fill[1]), D5, VEL_MARK), (rain + fill[1][1], A4, VEL),      # 107
        (rain + fill[2][0], A5, VEL_MARK), (rain + mid(fill[2]), E5, VEL_MARK), (rain + fill[2][1], C5, VEL),      # 114
        (rain + fill[2][1] + 1.4, A4, VEL_SOFT),
        # answer: the question, the call, the ending
        (ans + 0.00, E5, VEL_SOFT),
        (ans + q["answer"]["question"], F5, VEL),    # the question, on the note of the heat
        (ans + q["answer"]["question"] + 1.4, A4, VEL_MARK),
        (ans + q["answer"]["follow"], D5, VEL_SOFT),  # the call to send it on
        (ans + q["answer"]["follow"] + 1.5, E5, VEL_MARK), (ans + 7.2, C5, VEL_MARK), (ans + 9.2, B4, VEL_MARK),   # breaths while the slide is read
        (ending, A4, VEL), (ending, E5, VEL),        # the ending, an open fifth on the tonic
    )
    allnotes = sorted(plan, key=lambda p: p[0])
    assert all(m % 12 in MODE for _, m, _ in allnotes), "every note is in A Esfahan"
    assert max(m for _, m, _ in allnotes) == B5 and [m for _, m, _ in allnotes].count(B5) == 1, "B5 is the highest, once"
    assert min(m for _, m, _ in allnotes) == E4, "E4 is the lowest"
    notes = [light.Note(float(tt), m, vel, light.PAN if i % 2 == 0 else -light.PAN)
             for i, (tt, m, vel) in enumerate(allnotes)]
    assert notes[-1].t < end - 1.5, "the ending must ring out before the end"
    return sorted(notes, key=lambda nt: nt.t), end


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="replace this film's earlier music outputs")
    ap.add_argument("--plan", action="store_true", help="print the notes and the checks of the plan only; write nothing")
    args = ap.parse_args()
    film = json.loads(FILM.read_text(encoding="utf-8"))
    notes, end = score_notes(film)
    if args.plan:
        on = sorted({nt.t for nt in notes})
        rate = max(sum(1 for u in on if s0 <= u < s0 + 1.0) for s0 in np.arange(0.0, end, 0.01))
        pairs, classes, bad = light.check_intervals(notes)
        for nt in notes:
            print(f"    {nt.t:6.2f} s  {light.NAMES[nt.midi % 12]}{nt.midi // 12 - 1}")
        print(f"{len(notes)} notes; at most {rate} onsets in 1 s; closest {float(np.diff(on).min()):.2f} s; {pairs} pairs, classes {classes}, violations {bad}")
        return
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
    kit.reseed(47)
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
    print("the notes (A Esfahan):")
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
