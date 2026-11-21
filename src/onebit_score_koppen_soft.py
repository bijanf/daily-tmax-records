"""Two soft, melodic scores for the Köppen film (koppen_fa; no narration), of the kind the owner approved on
19 November 2026 for the Caspian film ("1 is good": a real melody over an accompaniment, every sound plucked or struck
and dying away, quiet). Two options go to the owner before the hand-over; neither may sound like the earlier scores
(Caspian: E minor, four-four, a rolling arpeggio; Hormuz: D Dorian, six-eight; Khuzestan: A minor three-four and a
three-three-two on G).

    walk    F major in four-four at a walking pace: a low setar note on the first and the fifth eighth, santur notes
            on the off-beats (chord notes only), a setar melody on the beats; four to seven bars a scene.
    lilt    B minor in twelve-eight, slow: a low setar note on each bar's first eighth and the seventh, the santur
            on the second and third eighth of every group of three; the melody on the groups' first eighths.
    The melody of each scene follows a contour (it climbs where the hot land grows, falls with the freezing winters,
    rests for the question), built from the bar's chord notes with a passing note between beats now and then; it is
    written out by melody() from the seed, so it is the same at every run. The film ends on an open chord, struck once.
    The level is the Caspian soft score's: -22 LUFS integrated, the true peak under -7 dBTP, nothing above 6 kHz.

    python -I src/onebit_score_koppen_soft.py            # both: outputs/onebit/social/koppen_fa_<tune>_music.wav and
                                                         # koppen_fa_<tune>_music_reel.mp4 (the picture untouched)
    python -I src/onebit_score_koppen_soft.py walk       # one of them
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
FILM = ROOT / "outputs" / "onebit" / "koppen" / "film.json"
BASE = "koppen_fa"
SR = kit.SR
# a chord: its low note and its tones (MIDI)
CHORDS = dict(F=(41, (53, 57, 60, 65)), C=(48, (55, 60, 64, 67)), Dm=(50, (57, 62, 65, 69)), Bb=(46, (58, 62, 65, 70)),
              Am=(45, (57, 60, 64, 69)), Gm=(43, (55, 58, 62, 67)),
              Bm=(47, (59, 62, 66, 71)), G=(43, (55, 59, 62, 67)), D=(50, (57, 62, 66, 69)), A=(45, (57, 61, 64, 69)),
              Em=(52, (59, 64, 67, 71)), Fsm=(42, (54, 57, 61, 66)))
TUNES = dict(
    walk=dict(steps=8, low=(0, 4), comp=((1, 1, 0.20), (3, 2, 0.24), (5, 1, 0.20), (7, 3, 0.22)), beats=(0, 2, 4, 6),
              pace=(1.8, 2.5), scale=(65, 67, 69, 70, 72, 74, 76, 77, 79, 81),
              scenes=(("a", ("F", "C", "Dm", "Bb", "F", "C", "F"), (69, 79)),          # the hot land grows: up
                      ("b", ("Dm", "Bb", "Gm", "C", "Dm"), (77, 67)),                    # the freezing winters go: down
                      ("c", ("Bb", "F", "C", "Dm", "Bb", "C"), (72, 77)),
                      ("d", ("Dm", "Bb", "F", "C"), (70, 79))),
              last=("e", ("Bb", "F"), 1.6, (72, 69)), end=(41, 48, 53, 57, 60, 65)),
    lilt=dict(steps=12, low=(0, 6), comp=((1, 1, 0.19), (2, 2, 0.21), (4, 1, 0.19), (5, 3, 0.21), (7, 1, 0.19), (8, 2, 0.21), (10, 1, 0.19), (11, 3, 0.21)),
              beats=(0, 3, 6, 9), pace=(2.8, 4.2), scale=(66, 67, 69, 71, 73, 74, 76, 78, 79, 81),
              scenes=(("a", ("Bm", "G", "D", "A", "Bm"), (71, 79)),
                      ("b", ("Em", "Bm", "G", "Fsm"), (78, 69)),
                      ("c", ("G", "D", "Em", "Bm"), (74, 78)),
                      ("d", ("Bm", "G", "A"), (73, 81))),
              last=("e", ("G",), 2.6, (74, 71)), end=(47, 54, 59, 62, 66, 71)),
)


def melody(chords, beats, contour, scale, rng):
    """(bar, step, MIDI) for a scene: on each beat the chord tone (raised to the melody's octave) nearest to the contour's
    target at that moment, now and then a passing note of the scale between two beats."""
    n = len(chords) * len(beats)
    out = []
    for k in range(n):
        b, beat = divmod(k, len(beats))
        target = contour[0] + (contour[1] - contour[0]) * k / max(1, n - 1)
        tones = [t + 12 * o for t in CHORDS[chords[b]][1] for o in (0, 1) if 64 <= t + 12 * o <= 82]
        note = min(tones, key=lambda t: (abs(t - target), t))
        if k % len(beats) in (1, 3) and rng.random() < 0.3:
            continue                                     # a rest now and then: the tune breathes
        out.append((b, beats[beat], note))
        if rng.random() < 0.25 and beat + 1 < len(beats):                 # a passing note before the next beat
            nxt = [s for s in scale if s != note and abs(s - note) <= 2]
            if nxt:
                out.append((b, (beats[beat] + beats[beat + 1]) // 2 + (1 if (beats[beat + 1] - beats[beat]) > 2 else 0), int(rng.choice(nxt))))
    return out


def score(film: dict, tune: dict, seed: int) -> tuple:
    c, end = film["clock"], film["end"]
    rng = np.random.default_rng(seed)
    track = kit.new_track(end, 4.0)
    onsets = []
    steps = tune["steps"]

    def human(t: float, vel: float) -> tuple:
        return max(0.0, t + rng.normal(0, 0.005)), vel * (1 + rng.normal(0, 0.06))

    def bar(t0: float, length: float, chord: str, level: float = 1.0) -> None:
        low, tones = CHORDS[chord]
        e = length / steps
        for k, s in enumerate(tune["low"]):
            t, v = human(t0 + s * e, (0.5 if k == 0 else 0.36) * level)
            kit.place(track, kit.setar(hz(low + (0 if k == 0 else 7)), dur=3.0, vel=v, t60=2.2, bright=0.2, buzz=0.05), t, 1.0, 0.0)
            onsets.append(t)
        for s, which, vel in tune["comp"]:
            t, v = human(t0 + s * e, vel * level)
            kit.place(track, kit.santur(hz(tones[which]), dur=2.4, vel=v, t60=1.5, detune=2.0, spread=0.3, bright=0.3), t)
            onsets.append(t)

    def tune_of(t0: float, length: float, notes, level: float = 1.0) -> None:
        e = length / steps
        for k, (b, s, m) in enumerate(notes):
            t, v = human(t0 + b * length + s * e, 0.6 * level)
            kit.place(track, kit.setar(hz(m), dur=2.6, vel=v, t60=1.6, bright=0.3, buzz=0.08), t, 1.0, 0.18 if k % 2 else -0.18)
            onsets.append(t)

    for i, (key, chords, contour) in enumerate(tune["scenes"]):
        t0, t1 = c[key]
        length = (t1 - t0) / len(chords)
        assert tune["pace"][0] < length < tune["pace"][1], (key, length)
        level = 0.8 if i == 0 else 1.0
        for b, chord in enumerate(chords):
            bar(t0 + b * length, length, chord, level)
        tune_of(t0, length, melody(chords, tune["beats"], contour, tune["scale"], rng), level)
    key, chords, length, contour = tune["last"]
    t0 = c[key][0]
    for b, chord in enumerate(chords):
        bar(t0 + b * length, length, chord)
    tune_of(t0, length, melody(chords, tune["beats"], contour, tune["scale"], rng))
    t_end = t0 + len(chords) * length
    assert t_end < end - 2.0, (t_end, end)
    for k, m in enumerate(tune["end"]):
        snd = kit.setar(hz(m), dur=3.5, vel=0.3, t60=2.6, bright=0.25, buzz=0.05) if m < 60 else \
            kit.santur(hz(m), dur=3.5, vel=0.17, t60=2.6, detune=2.0, spread=0.3, bright=0.3)
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
    kit.reseed(61 + len(name))
    track, onsets, end, t_end = score(film, TUNES[name], seed=29 + len(name))
    music = kit.master(track, lufs=LUFS, tp=MASTER_TP, seconds=end, fade_out=1.2)
    light.write_wav(wav, music)
    kit.mux(video, wav, mp4)
    m = light._read_wav(wav)
    lufs, tp, aac = kit.integrated_lufs(m), kit.true_peak_dbtp(m), kit.aac_true_peak(mp4)
    mono = m.mean(axis=1)
    rms = [20 * np.log10(np.sqrt(np.mean(mono[k:k + SR] ** 2)) + 1e-12) for k in range(0, len(mono) - SR, SR // 10)]
    body = rms[:int((t_end - 1.0) * 10)]
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
