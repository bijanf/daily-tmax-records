"""The light score of «ال‌نینو برای هامون آب می‌آورد؟» (hamounenso_fa, no narration): the light score's setar and checks
(onebit_score_air_light.py, imported, not copied) on the clock that src/hamounenso.py writes into film.json, in
D Esfahan (D E F G A Bb C#: twelve-tone, no koron), the mode of the Hamoun 3 scores, so the series sounds as one.

    the hook    a soft D5 at 0.00 s (frame 0 is not silent), A4 as the line moves, a low D4 as the water goes (the
                spring after La Niña), F4 as the border is drawn
    the tally   D5 into the springs; each column's count on its own note: El Niño a bright F5, neutral A4, La Niña a
                low D4; D5 with the second headline (no spring nearly without water after El Niño)
    the rain    Bb4 as the camera leaves for the mountains, F4 as the bars grow
    this year   A4 with the headline, F4 with «با بارشِ مشابه ...»
    the end     A4 as the hook's full lake (1398) comes back, D5 with the call to send it on, D4 and A4 struck together,
                ringing out before the loop
    the level   -14 LUFS, true peak -1 dBTP or lower after AAC (the music is the only sound). Consonant pairs only.

Writes hamounenso_fa_music.wav and hamounenso_fa_music_reel.mp4 (the silent master hamounenso_fa_reel.mp4 with this
track; its video stream copied). --force replaces this film's own earlier outputs.

    python -I src/onebit_score_hamounenso_light.py [--force]
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
FILM = ROOT / "outputs" / "onebit" / "hamounenso" / "film.json"
SR = kit.SR
BASE = "hamounenso_fa"
LUFS, MASTER_TP, TP_WAV, TP_AAC = -14.0, -2.0, -1.5, -1.0
VEL_SOFT, VEL, VEL_MARK = 0.55, 0.80, 0.45
MODE = {2, 4, 5, 7, 9, 10, 1}                        # pitch classes of D Esfahan (D E F G A Bb C#)


def plan(cut: dict) -> tuple:
    q, sc = cut["cues"], cut["scenes"]
    ending = cut["end"] - 2.2
    return (
        (0.00, 74, VEL_SOFT),                        # D5: soft, the first sound (frame 0 is not silent)
        (0.45, 69, VEL),                             # A4: the line moves
        (sum(q["wipe"]) / 2 + 0.05, 62, VEL),        # D4: the water goes (the spring after La Niña)
        (q["border"][1], 65, VEL_SOFT),              # F4: the border is drawn
        (sc["tally"][0], 74, VEL_SOFT),              # D5: into the springs
        (q["cols"][0]["count"], 77, VEL_MARK),       # F5: after El Niño, none nearly without water
        (q["cols"][1]["count"], 69, VEL_MARK),       # A4: neutral
        (q["cols"][2]["count"], 62, VEL),            # D4: after La Niña, six of ten
        (q["swap"] + 0.05, 74, VEL),                 # D5: the second headline
        (sc["why"][0], 70, VEL),                     # Bb4: to the mountains
        (q["card"] + 0.6, 65, VEL_MARK),             # F4: the bars grow
        (sc["now"][0], 69, VEL),                     # A4: this year
        (q["small"], 65, VEL_MARK),                  # F4: with similar precipitation, less water
        (sum(q["wipe2"]) / 2, 69, VEL),              # A4: the hook's full lake (1398) comes back
        (q["follow"], 74, VEL_SOFT),                 # D5: the call
        (ending, 62, VEL),                           # D4: the ending, an open fifth on the tonic
        (ending, 69, VEL),                           # A4
        # one soft note in each long reading hold, so that no second falls silent (the 12 Nov lesson; check (f)):
        # the hook's rest, the La Niña count, the tally's second headline, the rain card, this year's lines
        (sc["hook"][1] - 1.5, 69, VEL_MARK),         # A4
        (q["cols"][2]["count"] + 1.85, 65, VEL_MARK),   # F4
        (q["swap"] + 2.25, 65, VEL_MARK),            # F4 (a fourth under the rain's Bb4, never A4 against it)
        (q["card"] + 2.7, 74, VEL_MARK),             # D5
        (q["card"] + 4.7, 65, VEL_MARK),             # F4
        (q["small"] + 2.1, 74, VEL_MARK),            # D5
        (q["small"] + 4.1, 69, VEL_MARK),            # A4
        (q["small"] + 6.0, 65, VEL_MARK),            # F4
    )


def score_notes(film: dict) -> tuple:
    cut = film["cuts"]["main"]
    end = cut["end"]
    allnotes = sorted(plan(cut), key=lambda p: p[0])
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
    # the loudness each second: no stretch of digital silence (the 12 Nov lesson: print it after every score)
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
