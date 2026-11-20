"""Two soft, melodic scores for the Khuzestan heat film (khuzheat_fa; no narration), of the kind the owner approved on
19 November 2026 for the Caspian film ("1 is good": a real melody over an accompaniment, every sound plucked or
struck and dying away, quiet). Two options go to the owner before the hand-over; neither may sound like the Caspian
score (E minor, four-four, a rolling arpeggio) or the Hormuz one (D Dorian, six-eight).

    waltz   A minor in three-four, slow: a low setar note on the first beat, three santur notes after it (chord
            notes only), a setar melody of two or three notes a bar; six bars to a scene; it ends on an open A chord.
    ride    G Mixolydian in four-four, the eight eighths grouped three, three and two (a walking pace): a low setar
            note on the first eighth, santur notes on the others with a little weight where a group begins, a setar
            melody of three notes a bar; four bars to a scene; it ends on an open G chord.
    In both the bar follows each scene's length (the phrases begin with the pictures) and there is no held tone.
    The level is the Caspian soft score's: -22 LUFS integrated, the true peak under -7 dBTP, nothing above 6 kHz.

    python -I src/onebit_score_khuzheat_soft.py            # both: outputs/onebit/social/khuzheat_fa_<tune>_music.wav
                                                           # and khuzheat_fa_<tune>_music_reel.mp4 (the picture untouched)
    python -I src/onebit_score_khuzheat_soft.py waltz      # one of them
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
import onebit_persian as kit  # noqa: E402
import onebit_score_air_light as light  # noqa: E402
from onebit_score_khazar_soft import LUFS, MASTER_TP, ROOM, TP_AAC, WARM_HZ, hz  # noqa: E402  (the same level and room)

ROOT = Path(__file__).resolve().parents[1]
FILM = ROOT / "outputs" / "onebit" / "khuzheat" / "film.json"
BASE = "khuzheat_fa"
SR = kit.SR
# a chord: the low note of the bar and the three notes the santur takes from (MIDI)
CHORDS = dict(Am=(57, (64, 69, 72)), F=(53, (60, 65, 69)), C=(48, (55, 60, 64)), G=(55, (62, 67, 71)),
              Dm=(50, (57, 62, 65)), Em=(52, (59, 64, 67)))
TUNES = dict(
    waltz=dict(
        steps=6,                                         # the bar in eighths (three beats)
        comp=((2, 0, 0.21), (3, 1, 0.19), (4, 2, 0.24)),  # the santur: (eighth of the bar, which chord note, level)
        pace=(1.15, 1.55),                               # a bar lasts between these (s)
        scenes=(
            ("a", ("Am", "Am", "F", "F", "C", "G"),
             ((0, 0, 69), (0, 4, 72), (1, 0, 76), (1, 4, 74), (2, 0, 72), (2, 3, 69), (2, 4, 72), (3, 0, 77), (3, 4, 76),
              (4, 0, 76), (4, 4, 72), (5, 0, 74), (5, 4, 71))),
            ("b", ("Am", "Dm", "G", "C", "F", "Em"),         # the columns rise: so does the tune
             ((0, 0, 69), (0, 4, 72), (1, 0, 74), (1, 4, 77), (2, 0, 79), (2, 4, 74), (3, 0, 76), (3, 2, 72), (3, 4, 76),
              (4, 0, 77), (4, 4, 72), (5, 0, 71), (5, 4, 76))),
            ("c", ("Am", "F", "C", "G", "Dm", "Am"),
             ((0, 0, 76), (0, 4, 72), (1, 0, 69), (1, 4, 72), (2, 0, 76), (2, 4, 79), (3, 0, 74), (3, 4, 71),
              (4, 0, 74), (4, 2, 77), (4, 4, 74), (5, 0, 72), (5, 4, 69))),
        ),
        last=("d", ("F", "G"), ((0, 0, 72), (0, 4, 69), (1, 0, 71), (1, 4, 74)), 1.3),      # two bars of this length, then the last chord
        end=(52, 57, 64, 69, 72, 76)),                   # E3 A3 E4 A4 C5 E5, struck from the bottom up
    ride=dict(
        steps=8,                                         # the bar in eighths, grouped three, three and two
        comp=((1, 0, 0.19), (2, 1, 0.19), (3, 2, 0.25), (4, 1, 0.19), (5, 0, 0.19), (6, 2, 0.25), (7, 1, 0.19)),
        pace=(1.8, 2.3),
        scenes=(
            ("a", ("G", "F", "C", "G"),
             ((0, 0, 74), (0, 3, 71), (0, 6, 74), (1, 0, 72), (1, 3, 69), (1, 6, 72), (2, 0, 76), (2, 3, 72), (2, 6, 67),
              (3, 0, 71), (3, 3, 74), (3, 6, 79))),
            ("b", ("Am", "F", "C", "G"),
             ((0, 0, 76), (0, 3, 72), (0, 6, 69), (1, 0, 77), (1, 3, 72), (1, 6, 77), (2, 0, 79), (2, 3, 76), (2, 6, 72),
              (3, 0, 74), (3, 3, 79), (3, 6, 74))),
            ("c", ("Dm", "Am", "F", "G"),
             ((0, 0, 74), (0, 3, 77), (0, 6, 74), (1, 0, 72), (1, 3, 76), (1, 6, 72), (2, 0, 69), (2, 3, 72), (2, 6, 77),
              (3, 0, 74), (3, 3, 71), (3, 6, 67))),
        ),
        last=("d", ("C",), ((0, 0, 72), (0, 3, 76), (0, 6, 74)), 2.0),
        end=(55, 62, 67, 71, 74, 79)),                   # G3 D4 G4 B4 D5 G5
)


def score(film: dict, tune: dict, seed: int) -> tuple:
    """The stereo track before the master, the list of every onset (s) and the film's length."""
    c, end = film["clock"], film["end"]
    rng = np.random.default_rng(seed)
    track = kit.new_track(end, 4.0)
    onsets = []
    steps = tune["steps"]

    def human(t: float, vel: float) -> tuple:           # a hand is never exact: a few milliseconds, a little in level
        return max(0.0, t + rng.normal(0, 0.005)), vel * (1 + rng.normal(0, 0.06))

    def bar(t0: float, length: float, chord: str, level: float = 1.0) -> None:
        low, notes = CHORDS[chord]
        e = length / steps
        t, v = human(t0, 0.50 * level)
        kit.place(track, kit.setar(hz(low), dur=3.0, vel=v, t60=2.2, bright=0.2, buzz=0.05), t, 1.0, 0.0)
        onsets.append(t)
        for k, which, vel in tune["comp"]:
            t, v = human(t0 + k * e, vel * level)
            kit.place(track, kit.santur(hz(notes[which]), dur=2.4, vel=v, t60=1.5, detune=2.0, spread=0.3, bright=0.3), t)
            onsets.append(t)

    def melody(t0: float, length: float, notes, level: float = 1.0) -> None:
        e = length / steps
        for k, (b, step, m) in enumerate(notes):
            t, v = human(t0 + b * length + step * e, 0.62 * level)
            kit.place(track, kit.setar(hz(m), dur=2.6, vel=v, t60=1.6, bright=0.3, buzz=0.08), t, 1.0, 0.18 if k % 2 else -0.18)
            onsets.append(t)

    for i, (key, chords, notes) in enumerate(tune["scenes"]):
        t0, t1 = c[key]
        length = (t1 - t0) / len(chords)
        assert tune["pace"][0] < length < tune["pace"][1], (key, length)       # the pace holds from scene to scene
        level = 0.8 if i == 0 else 1.0                      # the first scene a little softer: the film opens gently
        for b, chord in enumerate(chords):
            bar(t0 + b * length, length, chord, level)
        melody(t0, length, notes, level)
    key, chords, notes, length = tune["last"]
    t0 = c[key][0]
    for b, chord in enumerate(chords):
        bar(t0 + b * length, length, chord)
    melody(t0, length, notes)
    t_end = t0 + len(chords) * length                      # the last chord, each string 55 ms after the one below it
    assert t_end < end - 2.0, (t_end, end)
    for k, m in enumerate(tune["end"]):
        snd = kit.setar(hz(m), dur=3.5, vel=0.3, t60=2.6, bright=0.25, buzz=0.05) if m < 60 else \
            kit.santur(hz(m), dur=3.5, vel=0.17, t60=2.6, detune=2.0, spread=0.3, bright=0.3)     # six strings together: each one soft
        kit.place(track, snd, t_end + 0.055 * k)
        onsets.append(t_end + 0.055 * k)
    wet = kit.reverb(track, t60=1.6, predelay=0.015, seed=11)[:len(track)]
    track = track + ROOM * wet
    track = sosfiltfilt(butter(4, WARM_HZ, "lowpass", fs=SR, output="sos"), track, axis=0)
    return light._bass_mono(track), sorted(onsets), end, t_end


def build(name: str, film: dict) -> list:
    social = onebit.OUT / "social"
    video = social / f"{BASE}_reel.mp4"
    wav, mp4 = social / f"{BASE}_{name}_music.wav", social / f"{BASE}_{name}_music_reel.mp4"
    kit.reseed(53 + len(name))
    track, onsets, end, t_end = score(film, TUNES[name], seed=17 + len(name))
    music = kit.master(track, lufs=LUFS, tp=MASTER_TP, seconds=end, fade_out=1.2)
    light.write_wav(wav, music)
    kit.mux(video, wav, mp4)
    m = light._read_wav(wav)
    lufs, tp, aac = kit.integrated_lufs(m), kit.true_peak_dbtp(m), kit.aac_true_peak(mp4)
    mono = m.mean(axis=1)
    rms = [20 * np.log10(np.sqrt(np.mean(mono[k:k + SR] ** 2)) + 1e-12) for k in range(0, len(mono) - SR, SR // 10)]
    body = rms[:int((t_end - 1.0) * 10)]                # the windows that end before the last chord
    gap = float(np.diff(onsets).max())
    fails = []
    print(f"\n{name}\nlevel     {lufs:+.2f} LUFS (aim {LUFS:+.0f}); true peak WAV {tp:+.2f} dBTP, decoded AAC {aac:+.2f} dBTP")
    if abs(lufs - LUFS) > 0.5 or aac > TP_AAC:
        fails.append("level")
    print(f"evenness  one-second windows before the ending: quietest {min(body):.1f} dBFS, loudest {max(body):.1f} dBFS")
    if min(body) < -70 or max(body) - min(body) > 12:
        fails.append("uneven")
    print(f"notes     {len(onsets)}; first at {onsets[0]:.3f} s; longest gap between two notes {gap:.2f} s")
    if onsets[0] > 0.1 or gap > 1.2:
        fails.append("a gap in the music")
    if light._md5(video, "0:v:0") != light._md5(mp4, "0:v:0"):
        fails.append("the picture changed")
    print("saved", wav, "\nsaved", mp4)
    return [f"{name}: {f}" for f in fails]


def main() -> None:
    names = sys.argv[1:] or list(TUNES)
    assert all(n in TUNES for n in names), names
    film = json.loads(FILM.read_text(encoding="utf-8"))
    fails = [f for n in names for f in build(n, film)]
    if fails:
        sys.exit("CHECKS NOT PASSED: " + "; ".join(fails))
    print("\nall checks pass")


if __name__ == "__main__":
    main()
