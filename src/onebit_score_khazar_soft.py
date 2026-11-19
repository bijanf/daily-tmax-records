"""A soft, melodic score for the Caspian film (khazar_fa_b; no narration), written on 19 November 2026 after the
owner heard the light score on his phone: "really boring and loud". That score was single plucks on three pitches,
mastered to -14 LUFS: sparse notes at that loudness each stand near full scale.

This one is music first, and quiet:
    a santur plays a rolling arpeggio in eighths (chord notes only, so what rings together is consonant) over a low
    setar note on every bar; a setar plays a melody over it, one phrase a scene (eight beats to a scene, the beat
    following each scene's length, so the phrases begin with the pictures); E minor, the bars Em, D, C, G and Am;
    the melody falls as the sea shrinks (scene b), climbs to the sea's highest year and comes down again (scene f),
    and the film ends on an open E chord, struck once and left to ring.
    Every sound is plucked or struck and dies away: no held tone anywhere (the owner hears a held tone as an alarm).
    The level: -22 LUFS integrated with the true peak under -7 dBTP, 8 dB under the light score and with its peaks
    far lower; warm (nothing above 6 kHz), a little room.

    python -I src/onebit_score_khazar_soft.py          # outputs/onebit/social/khazar_fa_b_soft_music.wav and
                                                       # khazar_fa_b_soft_music_reel.mp4 (the picture untouched)
    python -I src/onebit_score_khazar_soft.py --quiet  # instead: the light score's own notes, 10 dB lower and warmer
                                                       # (khazar_fa_b_quiet_music.wav, _quiet_music_reel.mp4)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
import onebit_persian as kit  # noqa: E402
import onebit_score_air_light as light  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FILM = ROOT / "outputs" / "onebit" / "khazar" / "film.json"
BASE = "khazar_fa_b"
SR = kit.SR
LUFS, MASTER_TP, TP_AAC = -22.0, -7.0, -6.0          # the soft score's level; the limits of its peaks
QUIET_LUFS = -24.0                                   # the light score's notes, made quiet
WARM_HZ = 6000.0                                     # nothing above this (a soft top)
ROOM = 0.22                                          # how much of the room is mixed in
# the bars: the low note of the bar, and the seven notes the santur plays after it (MIDI)
CHORDS = dict(Em=(52, (59, 64, 67, 71, 67, 64, 59)), D=(50, (57, 62, 66, 69, 66, 62, 57)),
              C=(48, (55, 60, 64, 67, 64, 60, 55)), G=(55, (62, 67, 71, 74, 71, 67, 62)),
              Am=(57, (64, 69, 72, 76, 72, 69, 64)))
# a scene: its two bars, and its melody as (beat, MIDI note); eight beats to a scene
SCENES = (
    ("a", ("Em", "Em"), ((0, 71), (1.5, 76), (2, 74), (3, 71), (4, 69), (5.5, 67), (6, 69), (7, 71))),
    ("b", ("Em", "D"), ((0, 76), (1, 74), (2, 71), (3, 69), (4, 69), (5.5, 66), (6, 64))),              # the sea shrinks: down
    ("c", ("C", "D"), ((0, 67), (1, 72), (2, 76), (3.5, 74), (4, 74), (5, 69), (6, 66), (7, 69))),
    ("e", ("Em", "G"), ((0, 71), (1.5, 67), (2, 64), (3, 67), (4, 71), (5, 74), (6, 71))),
    ("f", ("C", "D"), ((0, 64), (0.5, 67), (1, 72), (1.5, 76), (2.5, 79), (4, 78), (5, 74), (6, 69), (7, 66))),   # up to the highest year, down again
    ("g", ("Am", "Em"), ((0, 69), (1, 72), (2, 76), (4, 71), (5, 67), (6, 64))),
)
LAST = ("h", ("C", "D"), ((0, 67), (1, 72), (2, 74), (3, 69)))        # two short bars, then the last chord
LAST_BEAT = 0.85                                     # s: the beat of the last scene
END_CHORD = (52, 59, 64, 67, 71, 76)                 # E3 B3 E4 G4 B4 E5, struck from the bottom up


def hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def score(film: dict) -> tuple:
    """The stereo track before the master, the list of every onset (s) and the film's length."""
    c, end = film["clock"], film["end"]
    rng = np.random.default_rng(7)
    track = kit.new_track(end, 4.0)
    onsets = []

    def human(t: float, vel: float) -> tuple:           # a hand is never exact: a few milliseconds, a little in level
        return max(0.0, t + rng.normal(0, 0.005)), vel * (1 + rng.normal(0, 0.06))

    def bar(t0: float, beat: float, chord: str, eighths: int = 8, level: float = 1.0) -> None:
        low, arp = CHORDS[chord]
        t, v = human(t0, 0.50 * level)
        kit.place(track, kit.setar(hz(low), dur=3.0, vel=v, t60=2.2, bright=0.2, buzz=0.05), t, 1.0, 0.0)
        onsets.append(t)
        for k in range(1, eighths):
            t, v = human(t0 + k * beat / 2, (0.26 if k % 2 else 0.21) * level)
            kit.place(track, kit.santur(hz(arp[k - 1]), dur=2.4, vel=v, t60=1.5, detune=2.0, spread=0.3, bright=0.3), t)
            onsets.append(t)

    def tune(t0: float, beat: float, notes, level: float = 1.0) -> None:
        for k, (b, m) in enumerate(notes):
            t, v = human(t0 + b * beat, 0.62 * level)
            kit.place(track, kit.setar(hz(m), dur=2.6, vel=v, t60=1.6, bright=0.3, buzz=0.08), t, 1.0, 0.18 if k % 2 else -0.18)
            onsets.append(t)

    for i, (key, chords, notes) in enumerate(SCENES):
        t0, t1 = c[key]
        beat = (t1 - t0) / 8
        level = 0.8 if i == 0 else 1.0                  # the first scene a little softer: the film opens gently
        bar(t0, beat, chords[0], level=level)
        bar(t0 + 4 * beat, beat, chords[1], level=level)
        tune(t0, beat, notes, level)
    key, chords, notes = LAST
    t0 = c[key][0]
    bar(t0, LAST_BEAT, chords[0], eighths=4)
    bar(t0 + 2 * LAST_BEAT, LAST_BEAT, chords[1], eighths=4)
    tune(t0, LAST_BEAT, notes)
    t_end = t0 + 4 * LAST_BEAT                          # the last chord, each string 55 ms after the one below it
    assert t_end < end - 2.0, (t_end, end)
    for k, m in enumerate(END_CHORD):
        t = t_end + 0.055 * k
        snd = kit.setar(hz(m), dur=3.5, vel=0.3, t60=2.6, bright=0.25, buzz=0.05) if m < 60 else \
            kit.santur(hz(m), dur=3.5, vel=0.17, t60=2.6, detune=2.0, spread=0.3, bright=0.3)     # six strings together: each one soft
        kit.place(track, snd, t)
        onsets.append(t)
    wet = kit.reverb(track, t60=1.6, predelay=0.015, seed=11)[:len(track)]
    track = track + ROOM * wet
    track = sosfiltfilt(butter(4, WARM_HZ, "lowpass", fs=SR, output="sos"), track, axis=0)
    return light._bass_mono(track), sorted(onsets), end


def quiet(wav: Path, end: float) -> np.ndarray:
    """The light score as it was written, warmer and 10 dB lower."""
    x = light._read_wav(wav)
    x = sosfiltfilt(butter(4, 4000.0, "lowpass", fs=SR, output="sos"), x, axis=0)
    return kit.master(x, lufs=QUIET_LUFS, tp=-9.0, seconds=end, fade_out=1.0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quiet", action="store_true", help="the light score's notes, 10 dB lower and warmer, instead of the new score")
    args = ap.parse_args()
    film = json.loads(FILM.read_text(encoding="utf-8"))
    social = onebit.OUT / "social"
    video = social / f"{BASE}_reel.mp4"
    tag = "quiet" if args.quiet else "soft"
    wav, mp4 = social / f"{BASE}_{tag}_music.wav", social / f"{BASE}_{tag}_music_reel.mp4"
    if args.quiet:
        music, onsets, end = quiet(social / f"{BASE}_music.wav", film["end"]), [], film["end"]
        target = QUIET_LUFS
    else:
        kit.reseed(43)
        track, onsets, end = score(film)
        music = kit.master(track, lufs=LUFS, tp=MASTER_TP, seconds=end, fade_out=1.2)
        target = LUFS
    light.write_wav(wav, music)
    kit.mux(video, wav, mp4)
    m = light._read_wav(wav)
    lufs, tp, aac = kit.integrated_lufs(m), kit.true_peak_dbtp(m), kit.aac_true_peak(mp4)
    mono = m.mean(axis=1)
    rms = [20 * np.log10(np.sqrt(np.mean(mono[k:k + SR] ** 2)) + 1e-12) for k in range(0, len(mono) - SR, SR // 10)]
    body = rms[:int((end - 3.4) * 10)]               # the windows that end before the last chord dies away
    fails = []
    print(f"level     {lufs:+.2f} LUFS (aim {target:+.0f}); true peak WAV {tp:+.2f} dBTP, decoded AAC {aac:+.2f} dBTP")
    if abs(lufs - target) > 0.5 or aac > TP_AAC:
        fails.append("level")
    print(f"evenness  one-second windows before the ending: quietest {min(body):.1f} dBFS, loudest {max(body):.1f} dBFS")
    if min(body) < -70:
        fails.append("a silent second")
    if onsets:
        gap = float(np.diff(onsets).max())
        print(f"notes     {len(onsets)}; first at {onsets[0]:.3f} s; longest gap between two notes {gap:.2f} s")
        if onsets[0] > 0.1 or gap > 1.2:
            fails.append("a gap in the music")
        if not args.quiet and max(body) - min(body) > 12:
            fails.append("uneven")
    if light._md5(video, "0:v:0") != light._md5(mp4, "0:v:0"):
        fails.append("the picture changed")
    print("saved", wav, "\nsaved", mp4)
    if fails:
        sys.exit("CHECKS NOT PASSED: " + "; ".join(fails))
    print("all checks pass")


if __name__ == "__main__":
    main()
