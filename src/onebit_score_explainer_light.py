"""The light scores of the El Niño explainer (9 Nov 2026): part 1 (elnino26x_fa, 55 s, the owner's own voice) and part 2
(twodeg_fa, 47 s, no voice). The light score's engine (onebit_score_air_light.py: the setar pluck, the duck, the
spectral clean-up, the master), imported, not copied; the notes are new and sit on the films' own clocks.

    the line   one setar pluck about every second, the chord tones of each slide (part 1 in E Mahur, E F# G# A B C# D#:
               I, IV, I-V, vi, IV, I, vi-V, I; part 2 in D Mahur, D E F# G A B C#: I, vi-I, IV-V, I, IV, vi, I-IV, I),
               rising where the picture rises (the 2026 line, the bars, the rows); an open fifth at the end that rings
               into the fade. No silence longer than 1.3 s (the review of 9 Nov found 3-4 s gaps in the first cut).
    the voice  part 1 only: the owner's five pieces (src/elnino26x_voice.py) at their scenes' starts. The music plays at
               its full level (as the music-only cut) on the slides without voice and is ducked DUCK_DB under the
               speech (the review of 9 Nov: the first mix left the voiceless slides 15-20 LU under the voiced ones).

Checks: every pair of notes less than 1.0 s apart (the pluck is 24 dB down after 1.0 s: T60 2.5 s) is a unison, third,
fourth, fifth, sixth or octave; at most two onsets in any 1 s; every note in C4-C6; no gap between onsets over 1.3 s;
the voice at least 18 dB over the ducked music in every speech span.

Files (48 kHz WAVs beside them; existing outputs are overwritten only with --force):
    elnino26x_fa_voice_reel.mp4       part 1: the owner's voice and the light music, -14.5 LUFS
    elnino26x_fa_lightmusic_reel.mp4  part 1: the light music alone, -14 LUFS (the fallback without voice)
    twodeg_fa_music_reel.mp4          part 2: the light music, -14 LUFS

    python -I src/onebit_score_explainer_light.py [--part 1|2|all] [--force]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
import onebit_elnino26x as film1  # noqa: E402
import onebit_persian as kit  # noqa: E402
import onebit_score_air_light as light  # noqa: E402
import onebit_twodeg as film2  # noqa: E402

SR = kit.SR
SOCIAL = onebit.OUT / "social"
VOICE_DIR = onebit.ROOT / "data" / "enso" / "elnino26x" / "voice"
MUSIC_LUFS, MIX_LUFS = -14.0, -14.5
MASTER_TP, MUSIC_TP = -2.0, -4.0                      # dBTP: the plucks alone overshoot more in AAC
DUCK_DB, DUCK_ATTACK, DUCK_RELEASE = 20.0, 0.15, 0.40
RATIO_MIN = 18.0                                      # dB: the voice over the ducked music, in every speech span
ALLOWED = {0, 3, 4, 5, 7, 8, 9}                       # unison, minor/major third, fourth, fifth, sixth, octave
OVERLAP_S = 1.0                                       # s: notes closer than this ring together (24 dB down at 1.0 s)
GAP_MAX = 1.3                                         # s: the longest silence between onsets
STEP = 1.0                                            # s: the pulse of the line

# chords as MIDI tones from low to high (C4-C6)
E_I, E_IV, E_V, E_vi = (64, 68, 71, 76, 80, 83), (69, 73, 76, 81), (71, 75, 78, 83), (61 + 12, 64 + 12, 68 + 12)
D_I, D_IV, D_V, D_vi = (62, 66, 69, 74, 78, 81), (67, 71, 74, 79, 83), (69, 73, 76, 81), (71, 74, 78, 83)
# part 1: (scene, chord tones, pattern of indices into the chord, one per pulse); a scene may split into two chords
PART1 = (("hook", E_I, (3, 2, 3, 1, 2, 0, 2)), ("what", E_IV, (0, 1, 2, 3, 2, 1)),
         ("record", E_I, (2, 3, 4, 5)), ("record", E_V, (3, 2, 1)),
         ("autumn", E_vi, (0, 1, 2, 1, 0, 1, 2, 1)), ("iran", E_IV, (1, 2, 3, 2)),
         ("winter", E_I, (1, 2, 3, 2, 1, 2, 3, 2)), ("strong", E_vi, (0, 1, 2, 1)), ("strong", E_V, (0, 1, 2)),
         ("answer", E_I, (0, 1, 3, 5, 4, 3, 2, 3)))
PART2 = (("hook", D_I, (3, 4, 3, 2, 3)), ("holocene", D_vi, (0, 1, 2)), ("holocene", D_I, (2, 3, 4, 5)),
         ("modern", D_IV, (1, 2, 3)), ("modern", D_V, (1, 2, 3)), ("ocean", D_I, (3, 2, 3, 4, 3, 2)),
         ("extremes", D_IV, (0, 1, 2, 3, 4)), ("rain", D_vi, (0, 1, 2, 3, 2, 1)),
         ("snow", D_I, (3, 2, 1, 2)), ("snow", D_IV, (2, 1, 0)), ("end", D_I, (0, 2, 3, 4, 3)))
END_FIFTH = {1: (64, 71), 2: (62, 69)}                # the open fifth that ends each part


class Note:
    def __init__(self, t: float, midi: int, vel: float, pan: float):
        self.t, self.midi, self.vel, self.pan = t, midi, vel, pan


def line(starts, scenes, plan, end_t: float) -> list:
    """One pluck a pulse on one continuous grid (0, 1, 2 ... s, so no two notes fall closer than STEP at a slide's
    edge); each (scene, chord, pattern) of the plan takes its share of its scene's pulses, in order."""
    by_scene: dict = {}
    for name, chord, pattern in plan:
        by_scene.setdefault(name, []).append((chord, pattern))
    pulses = np.arange(0.0, end_t, STEP)
    out, n = [], 0
    for i, name in enumerate(scenes):
        mine = [t for t in pulses if float(starts[i]) <= t < float(starts[i + 1])]
        parts = by_scene[name]
        cuts = np.array_split(np.arange(len(mine)), len(parts))
        for (chord, pattern), idx in zip(parts, cuts):
            for j, k in enumerate(idx):
                m = chord[pattern[j % len(pattern)]]
                vel = 0.80 if j == 0 else 0.62 + 0.08 * ((j % 4) == 2)
                out.append(Note(float(mine[k]), m, vel, 0.2 if n % 2 == 0 else -0.2))
                n += 1
    return out


def check_notes(notes: list, end: float) -> None:
    notes = sorted(notes, key=lambda nt: (nt.t, nt.midi))
    for a in notes:
        assert 60 <= a.midi <= 84, ("range", a.t, a.midi)
        assert 0.0 <= a.t < end, ("time", a.t)
    onsets = sorted({round(nt.t, 3) for nt in notes})
    for t in onsets:
        assert sum(t <= u < t + 1.0 for u in onsets) <= 2, ("more than two onsets in 1 s at", t)
    gaps = np.diff([0.0] + onsets)
    assert gaps.max() <= GAP_MAX + 1e-9, ("a silence", float(gaps.max()), onsets[int(np.argmax(gaps))])
    for i, a in enumerate(notes):
        for b in notes[i + 1:]:
            if b.t - a.t < OVERLAP_S:
                assert abs(b.midi - a.midi) % 12 in ALLOWED, ("interval", a.t, a.midi, b.t, b.midi)


def stem(notes: list, end: float) -> np.ndarray:
    kit.reseed(41)
    track = kit.new_track(end, light.TAIL)
    for nt in notes:
        kit.place(track, light.pluck(nt.midi, nt.vel), nt.t, 1.0, nt.pan)
    return light._bass_mono(light._air_cut(track))


def duck_gain(mask: np.ndarray) -> np.ndarray:
    a = math.exp(-1.0 / (SR * DUCK_ATTACK))
    r = math.exp(-1.0 / (SR * DUCK_RELEASE))
    target = np.where(mask, -DUCK_DB, 0.0)
    g = np.empty(len(target))
    cur = 0.0
    for i, t in enumerate(target):
        k = a if t < cur else r
        cur = k * cur + (1.0 - k) * t
        g[i] = cur
    return 10.0 ** (g / 20.0)


def voice_track(n: int, starts) -> tuple:
    """The owner's five pieces, each starting at its scene's start (the cut keeps the lead of 8 Nov's reel)."""
    man = json.loads((VOICE_DIR / "manifest.json").read_text(encoding="utf-8"))
    v = np.zeros(n)
    spans = []
    for scene, name in film1.VOICED.items():
        rate, pcm = wavfile.read(VOICE_DIR / f"{name}.wav")
        assert rate == SR and pcm.ndim == 1
        y = pcm.astype(float) / 32767.0
        t0 = float(starts[scene])
        assert len(y) / SR <= float(starts[scene + 1]) - t0 + 1e-6, (name, "the piece runs into the next scene")
        i0 = round(t0 * SR)
        v[i0:i0 + len(y)] += y[:max(0, n - i0)]
        a = t0 + man[name]["lead"]
        spans.append((name, a, a + man[name]["speech"]))
    return v, spans


def part1(force: bool) -> None:
    f = film1.ElNino26xFilm(onebit.THEMES["kahgel"], film1.COLOURS["kahgel"])
    starts, end = f.starts, film1.END
    silent = SOCIAL / f"{film1.BASE}_reel.mp4"
    assert silent.exists() and silent.stat().st_mtime > Path(film1.__file__).stat().st_mtime, \
        "render the silent master first (python -I src/onebit_elnino26x.py)"
    _, spans = voice_track(round(end * SR), starts)
    fifth_t = round(spans[-1][2] + 0.4, 2)                       # after the last word; it rings into the fade
    assert fifth_t <= end - 1.4, fifth_t
    notes = line(starts, film1.SCENES, PART1, fifth_t - 0.6)
    notes += [Note(fifth_t, m, 0.80, p) for m, p in zip(END_FIFTH[1], (0.2, -0.2))]
    check_notes(notes, end)
    music = kit.master(stem(notes, end), lufs=MUSIC_LUFS, tp=MUSIC_TP, seconds=end, fade_out=1.0)
    n = len(music)
    v, spans = voice_track(n, starts)
    mask = np.zeros(n, bool)
    for _, a, b in spans:
        mask[max(0, round((a - DUCK_ATTACK) * SR)):round(b * SR)] = True     # max(0, ...): the hook speaks at 0.14 s
    music_d = music * duck_gain(mask)[:, None]
    v = light._highpass20(v)
    mono = music_d.mean(axis=1)
    ratio = lambda x, a, b: 10 * np.log10(np.mean(x[round(a * SR):round(b * SR)] ** 2)  # noqa: E731
                                          / np.mean(mono[round(a * SR):round(b * SR)] ** 2))
    # the voice at the loudness of the music's own slides: its mean square over speech = the music's over the rest
    free = ~mask
    v_ms = np.mean(np.concatenate([v[round(a * SR):round(b * SR)] for _, a, b in spans]) ** 2)
    m_ms = np.mean(music.mean(axis=1)[free] ** 2)
    v = v * math.sqrt(m_ms / v_ms) * 10 ** (1.5 / 20)          # the voice 1.5 dB over the music's level
    ratios = [ratio(v, a, b) for _, a, b in spans]
    assert min(ratios) >= RATIO_MIN, ratios
    total = light._highpass20(light._air_cut(music_d + np.stack([v, v], axis=1)))
    mix = light._bass_mono(kit.master(total, lufs=MIX_LUFS, tp=MASTER_TP, seconds=end, fade_out=1.0))
    write(mix, f"{film1.BASE}_voice", silent, force)
    write(music, f"{film1.BASE}_lightmusic", silent, force)
    print("part 1 spans:", [(nm, round(a, 2), round(b, 2)) for nm, a, b in spans])
    print("part 1 voice over ducked music (dB):", [round(float(r), 1) for r in ratios])
    short_term(mix, starts, film1.SCENES, "part 1 voice cut")


def part2(force: bool) -> None:
    f = film2.TwoDegFilm(onebit.THEMES["kahgel"], film2.COLOURS["kahgel"])
    starts, end = f.starts, film2.END
    silent = SOCIAL / f"{film2.BASE}_reel.mp4"
    assert silent.exists() and silent.stat().st_mtime > Path(film2.__file__).stat().st_mtime, \
        "render the silent master first (python -I src/onebit_twodeg.py)"
    fifth_t = end - 2.2
    notes = line(starts, film2.SCENES, PART2, fifth_t - 0.6)
    notes += [Note(fifth_t, m, 0.80, p) for m, p in zip(END_FIFTH[2], (0.2, -0.2))]
    check_notes(notes, end)
    music = kit.master(stem(notes, end), lufs=MUSIC_LUFS, tp=MUSIC_TP, seconds=end, fade_out=1.0)
    write(music, f"{film2.BASE}_music", silent, force)
    short_term(music, starts, film2.SCENES, "part 2")


def short_term(x: np.ndarray, starts, scenes, label: str) -> None:
    """The loudness of each slide, so the slides without voice are never far under the others."""
    out = []
    for i, name in enumerate(scenes):
        a, b = round(float(starts[i]) * SR), round(min(float(starts[i + 1]), float(starts[-1]) - 1.0) * SR)
        out.append(f"{name} {kit.integrated_lufs(x[a:b]):.1f}")
    print(f"{label} LUFS per slide:", ", ".join(out))


def write(x: np.ndarray, stem_name: str, silent: Path, force: bool) -> None:
    wav = SOCIAL / f"{stem_name}.wav"
    mp4 = SOCIAL / f"{stem_name}_reel.mp4"
    if mp4.exists() and not force:
        sys.exit(f"{mp4} exists (pass --force to write it again)")
    light.write_wav(wav, x)
    kit.mux(silent, wav, mp4)
    print(f"saved {mp4.name}: {kit.integrated_lufs(x):.1f} LUFS, true peak {kit.true_peak_dbtp(x):.2f} dBTP (WAV)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--part", default="all", choices=["1", "2", "all"])
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if args.part in ("1", "all"):
        part1(args.force)
    if args.part in ("2", "all"):
        part2(args.force)


if __name__ == "__main__":
    main()
