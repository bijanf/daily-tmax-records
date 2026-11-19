"""A soft, melodic score for the Hormuz NO2 film (hormuz_fa; no narration), written on 19 November 2026. The
owner had heard the Caspian film's light score (single plucks on three pitches at -14 LUFS) as "really boring and
loud" and approved the soft score that replaced it ("1 is good"); this film's light score was of the same kind.

The same kind of music as src/onebit_score_khazar_soft.py, and another piece (two reels must not sound alike):
    in six-eight, a boat song's sway: a low setar note on the first eighth of every bar and five santur notes after
    it (chord notes only); a setar melody over it, mostly one note on each half of the bar; D Dorian, the bars Dm, G,
    F, C and Am; four bars to a scene (six to the long scene of the ships), the bar following each scene's length,
    so the phrases begin with the pictures; the film ends on an open D chord, struck once and left to ring.
    Every sound is plucked or struck and dies away: no held tone anywhere.
    The level: -22 LUFS integrated with the true peak under -7 dBTP; warm (nothing above 6 kHz), a little room.

    python -I src/onebit_score_hormuz_soft.py                 # outputs/onebit/social/hormuz_fa_soft_music.wav and
                                                              # hormuz_fa_soft_music_reel.mp4 (the picture untouched)
    python -I src/onebit_score_hormuz_soft.py --video X.mp4   # the same sound on another cut of the film (its look B)
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
from onebit_score_khazar_soft import LUFS, MASTER_TP, ROOM, TP_AAC, WARM_HZ, hz  # noqa: E402  (the same level and room)

ROOT = Path(__file__).resolve().parents[1]
FILM = ROOT / "outputs" / "onebit" / "hormuz" / "film.json"
BASE = "hormuz_fa"
SR = kit.SR
# the bars: the low note of the bar, and the five notes the santur plays after it (MIDI)
CHORDS = dict(Dm=(50, (57, 62, 65, 62, 57)), G=(55, (62, 67, 71, 67, 62)), F=(53, (60, 65, 69, 65, 60)),
              C=(48, (55, 60, 64, 60, 55)), Am=(57, (64, 69, 72, 69, 64)))
# a scene: its bars, and its melody as (bar, eighth of the bar 0-5, MIDI note)
SCENES = (
    ("a", ("Dm", "Dm", "F", "C"),
     ((0, 0, 69), (0, 3, 74), (1, 0, 77), (1, 3, 76), (1, 5, 74), (2, 0, 72), (2, 3, 69), (3, 0, 67), (3, 3, 64))),
    ("b", ("Dm", "G", "F", "C"),
     ((0, 0, 74), (0, 3, 77), (1, 0, 79), (1, 3, 74), (1, 5, 71), (2, 0, 69), (2, 3, 72), (3, 0, 76), (3, 3, 72), (3, 5, 67))),
    ("c", ("Dm", "C", "F", "G", "Dm", "Am"),                      # the ships: the long scene
     ((0, 0, 69), (0, 2, 74), (0, 3, 77), (1, 0, 76), (1, 3, 72), (2, 0, 69), (2, 3, 77), (3, 0, 74), (3, 3, 71), (3, 5, 67),
      (4, 0, 69), (4, 3, 65), (5, 0, 64), (5, 3, 69))),
    ("e", ("F", "C", "Dm", "Am"),
     ((0, 0, 72), (0, 3, 77), (1, 0, 76), (1, 3, 67), (2, 0, 69), (2, 3, 74), (3, 0, 72), (3, 3, 76))),
    ("f", ("F", "G", "Am", "Dm"),
     ((0, 0, 69), (0, 3, 72), (1, 0, 71), (1, 3, 74), (2, 0, 76), (2, 3, 72), (2, 5, 69), (3, 0, 74), (3, 3, 69))),
)
LAST = ("h", ("F", "C"), ((0, 0, 72), (0, 3, 69), (1, 0, 67), (1, 3, 64)))      # two short bars, then the last chord
LAST_BAR = 1.7                                       # s: a bar of the last scene
END_CHORD = (50, 57, 62, 65, 69, 74)                 # D3 A3 D4 F4 A4 D5, struck from the bottom up


def score(film: dict) -> tuple:
    """The stereo track before the master, the list of every onset (s) and the film's length."""
    c, end = film["clock"], film["end"]
    rng = np.random.default_rng(11)
    track = kit.new_track(end, 4.0)
    onsets = []

    def human(t: float, vel: float) -> tuple:           # a hand is never exact: a few milliseconds, a little in level
        return max(0.0, t + rng.normal(0, 0.005)), vel * (1 + rng.normal(0, 0.06))

    def bar(t0: float, length: float, chord: str, level: float = 1.0) -> None:
        low, arp = CHORDS[chord]
        e = length / 6                                  # an eighth
        t, v = human(t0, 0.50 * level)
        kit.place(track, kit.setar(hz(low), dur=3.0, vel=v, t60=2.2, bright=0.2, buzz=0.05), t, 1.0, 0.0)
        onsets.append(t)
        for k, m in enumerate(arp, start=1):
            t, v = human(t0 + k * e, (0.27 if k == 3 else 0.21) * level)        # a little weight on the bar's second half
            kit.place(track, kit.santur(hz(m), dur=2.4, vel=v, t60=1.5, detune=2.0, spread=0.3, bright=0.3), t)
            onsets.append(t)

    def tune(t0: float, length: float, notes, level: float = 1.0) -> None:
        e = length / 6
        for k, (b, eighth, m) in enumerate(notes):
            t, v = human(t0 + b * length + eighth * e, 0.62 * level)
            kit.place(track, kit.setar(hz(m), dur=2.6, vel=v, t60=1.6, bright=0.3, buzz=0.08), t, 1.0, 0.18 if k % 2 else -0.18)
            onsets.append(t)

    for i, (key, chords, notes) in enumerate(SCENES):
        t0, t1 = c[key]
        length = (t1 - t0) / len(chords)
        assert 1.6 < length < 2.3, (key, length)           # the sway keeps its pace from scene to scene
        level = 0.8 if i == 0 else 1.0                      # the first scene a little softer: the film opens gently
        for b, chord in enumerate(chords):
            bar(t0 + b * length, length, chord, level)
        tune(t0, length, notes, level)
    key, chords, notes = LAST
    t0 = c[key][0]
    for b, chord in enumerate(chords):
        bar(t0 + b * LAST_BAR, LAST_BAR, chord)
    tune(t0, LAST_BAR, notes)
    t_end = t0 + len(chords) * LAST_BAR                    # the last chord, each string 55 ms after the one below it
    assert t_end < end - 2.0, (t_end, end)
    for k, m in enumerate(END_CHORD):
        snd = kit.setar(hz(m), dur=3.5, vel=0.3, t60=2.6, bright=0.25, buzz=0.05) if m < 60 else \
            kit.santur(hz(m), dur=3.5, vel=0.17, t60=2.6, detune=2.0, spread=0.3, bright=0.3)     # six strings together: each one soft
        kit.place(track, snd, t_end + 0.055 * k)
        onsets.append(t_end + 0.055 * k)
    wet = kit.reverb(track, t60=1.6, predelay=0.015, seed=11)[:len(track)]
    track = track + ROOM * wet
    track = sosfiltfilt(butter(4, WARM_HZ, "lowpass", fs=SR, output="sos"), track, axis=0)
    return light._bass_mono(track), sorted(onsets), end


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", type=Path, help="another silent cut of the film to carry the same sound (default: the film's own)")
    args = ap.parse_args()
    film = json.loads(FILM.read_text(encoding="utf-8"))
    social = onebit.OUT / "social"
    video = args.video or social / f"{BASE}_reel.mp4"
    wav = social / f"{BASE}_soft_music.wav"
    mp4 = video.with_name(video.stem.replace("_reel", "") + "_soft_music_reel.mp4")
    kit.reseed(47)
    track, onsets, end = score(film)
    music = kit.master(track, lufs=LUFS, tp=MASTER_TP, seconds=end, fade_out=1.2)
    light.write_wav(wav, music)
    kit.mux(video, wav, mp4)
    m = light._read_wav(wav)
    lufs, tp, aac = kit.integrated_lufs(m), kit.true_peak_dbtp(m), kit.aac_true_peak(mp4)
    mono = m.mean(axis=1)
    rms = [20 * np.log10(np.sqrt(np.mean(mono[k:k + SR] ** 2)) + 1e-12) for k in range(0, len(mono) - SR, SR // 10)]
    body = rms[:int((end - 3.4) * 10)]                  # the windows that end before the last chord dies away
    gap = float(np.diff(onsets).max())
    fails = []
    print(f"level     {lufs:+.2f} LUFS (aim {LUFS:+.0f}); true peak WAV {tp:+.2f} dBTP, decoded AAC {aac:+.2f} dBTP")
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
    if fails:
        sys.exit("CHECKS NOT PASSED: " + "; ".join(fails))
    print("all checks pass")


if __name__ == "__main__":
    main()
