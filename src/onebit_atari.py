"""A slow Atari tune for the 1-bit films: the sound chip of the Atari 2600, synthesized from
scratch and timed to the film.

A fifth voice beside the techno (onebit_audio), the 8-bit tune (onebit_chip), the bells
(onebit_bell) and the steam engine (onebit_steam), for stories that should feel calm. The 2600's
TIA makes its notes by dividing a 31.4 kHz clock by a whole number, so only some pitches exist
and most are a little out of tune: every note here is snapped to the nearest one the chip can
play, in the mode it would use (square waves divided by 2 or 6 for the tune and the chords). The
bass has the chip's buzzy 31-step pattern but true pitch: the chip's own bass notes sit 40-60
cents off, sour under the chords. Volumes move in the chip's 16 steps, so notes fade in
stairs. On top of the chip, only a soft low-pass and an echo, to make it gentle.

The music: A minor pentatonic at a slow tempo (`desk.bpm`, default 60). Each bar's chord (Am,
Am, C, G) held as a soft pad that melts into the next, a bass humming under it, the chord broken
in quiet quarters, a tune of long notes, and the hiss of the noise channel like snow falling.
Nothing thumps: the loudness stays level from bar to bar. `desk.melody()` adds the data as tune notes
(time, step on the scale with 0 the tonic, length, gain); `desk.blips` are falling plips (a flake
that turns into a drop). The last bar holds A minor, the hiss fades and the track fades to
silence over its last 2 s. Like the bells and the steam, the track starts clean.
"""

from __future__ import annotations

import functools
import wave
from pathlib import Path

import numpy as np

from onebit_bell import SR, Mixer, _fade, _filter, _t, hz

CLOCK = 31_400.0                            # TIA audio clock (NTSC 3.58 MHz / 114)
PENTA = (0, 3, 5, 7, 10)                    # A minor pentatonic: A C D E G
TONIC = 69                                  # A4
BASS = (45, 45, 48, 43)                     # A2, A2, C3, G2: one per bar
CHORDS = ((57, 60, 64), (57, 60, 64), (55, 60, 64), (55, 59, 62))   # Am, Am, C, G


def step_note(step: int) -> int:
    octave, k = divmod(int(step), len(PENTA))
    return TONIC + 12 * octave + PENTA[k]


@functools.lru_cache(maxsize=4096)
def tia(note: float, divs=(2, 6)) -> float:
    """The pitch the chip plays for a note: CLOCK / (div * (N + 1)) for N in 0-31, in whichever
    of the modes `divs` comes closest (the 2600's composers switched modes note by note to dodge
    the worst of the detuning)."""
    f = hz(note)
    best = []
    for div in divs:
        n = np.clip(np.round(CLOCK / (div * f)) - 1, 0, 31)
        g = CLOCK / (div * (n + 1))
        best.append((abs(np.log2(g / f)), g))
    return min(best)[1]


# ── voices ──────────────────────────────────────────────────────────────────

def stairs(env: np.ndarray) -> np.ndarray:
    """The chip's 4-bit volume: 16 steps."""
    return np.round(np.clip(env, 0, 1) * 15) / 15


def square(note, length, attack=0.02, tau=0.8, gain=1.0):
    """A pure tone of the chip (modes 4 and 12: a square wave), fading in volume stairs."""
    n = int(length * SR)
    t = _t(n)
    f = tia(note)
    wave_ = np.sign(np.sin(2 * np.pi * f * t))
    env = stairs(np.minimum(1, t / attack) * np.exp(-t / tau))
    return _fade(wave_ * env * 0.25 * gain, 0.002, 0.03)


def buzz(note, length, attack=0.2, tau=8.0):
    """The bass: the chip's 31-step pattern (high 18 steps, low 13), filtered warm and held
    through the bar, so it hums instead of thumping."""
    n = int(length * SR)
    t = _t(n)
    f = hz(note)        # tuned true: the chip's bass notes sit 40-60 cents off, sour under the chords
    phase = (f * t) % 1.0
    x = np.where(phase < 18 / 31, 1.0, -1.0)
    env = stairs(np.minimum(1, t / attack) * np.exp(-t / tau))
    return _fade(_filter(x * env * 0.3, "low", 700), 0.003, 0.6)


def pad(chord, length, attack=0.8, release=1.0):
    """The chord of the bar held on soft chip squares: slow in, slow out, longer than the bar so
    that one chord melts into the next and the music never pumps."""
    n = int(length * SR)
    t = _t(n)
    x = sum(np.sign(np.sin(2 * np.pi * tia(note) * t + k)) for k, note in enumerate(chord)) / len(chord)
    env = np.minimum(1, t / attack) * np.minimum(1, np.clip(length - t, 0, None) / release)
    return _filter(x * stairs(env) * 0.25, "low", 1400)


def hiss(length, rng):
    """The noise channel, very quiet and dark: snow falling."""
    n = int(length * SR)
    x = _filter(rng.standard_normal(n), "band", (300, 2400))
    t = _t(n)
    return _fade(x * (0.6 + 0.4 * np.sin(2 * np.pi * t / 7.0)) * 0.05, 1.0, 1.5)


def plip(start=81, drop=12, length=0.35):
    """A flake turns into a drop: a short pure tone that falls an octave in chip steps."""
    n = int(length * SR)
    t = _t(n)
    notes = start - drop * np.minimum(1, t / (length * 0.6))
    f = np.array([tia(float(v)) for v in np.round(notes * 2) / 2])
    ph = 2 * np.pi * np.cumsum(f) / SR
    env = stairs(np.exp(-t / 0.12))
    return _fade(np.sign(np.sin(ph)) * env * 0.18, 0.001, 0.02)


def pip():
    """A word appears: the faintest high blip."""
    n = int(0.04 * SR)
    t = _t(n)
    return _fade(np.sign(np.sin(2 * np.pi * tia(93) * t)) * stairs(np.exp(-t / 0.01)) * 0.05, 0.001, 0.005)


def echo(x: np.ndarray, delay: float, feedback=0.35, mix=0.3) -> np.ndarray:
    """A soft echo, darker each time round."""
    d = int(delay * SR)
    out = x.copy()
    tap = x.copy()
    for _ in range(4):
        tap = _filter(np.concatenate([np.zeros((d, x.shape[1])), tap[:-d]]), "low", 2500) * feedback
        out += tap * mix / feedback
    return out


# ── arrangement ─────────────────────────────────────────────────────────────

def soundtrack(desk) -> np.ndarray:
    bpm = getattr(desk, "bpm", 60)
    spb = 60 / bpm
    bar = 4 * spb
    end = desk.L.end
    assert abs(end / bar - round(end / bar)) < 1e-6, "the film must last a whole number of bars"
    rng = np.random.default_rng(31)                    # the same track on every render
    starts = list(desk.L.scenes) + [end]
    m = Mixer(end, tail=4.0)
    nbar = int(round(end / bar))
    m.add(hiss(end + 1.0, rng), 0.0, 1.0)
    for b in range(nbar):
        t0 = b * bar
        final = b == nbar - 1
        chord = CHORDS[0] if final else CHORDS[b % len(CHORDS)]
        hold = bar * (1.5 if final else 1.0) + 1.0        # each bar's pad and bass overlap the next
        m.add(pad(chord, hold), t0 - (0.5 if b else 0.0), 0.9, pan=-0.1)
        m.add(buzz(BASS[0] if final else BASS[b % len(BASS)], hold), t0, 0.5)
        for j in range(2 if final else 4):           # the broken chord in quarters, quietly
            m.add(square(chord[(0, 1, 2, 1)[j]], spb * 1.8, tau=0.7), t0 + j * spb, 0.2, pan=0.3 - 0.2 * (j % 2))
        if final:
            m.add(square(step_note(0), bar * 1.4, tau=2.0), t0, 0.4)
            m.add(square(step_note(-5), bar * 1.4, tau=2.2), t0, 0.3, pan=-0.2)
    if hasattr(desk, "melody"):
        for t, st, length, gain in desk.melody():
            m.add(square(step_note(st), max(length, 0.6), tau=max(length, 0.6) * 0.6), t, gain, pan=-0.15)
    for t in getattr(desk, "blips", []):
        m.add(plip(), t, 0.8, pan=rng.uniform(-0.4, 0.4))
    for i, t0 in enumerate(starts[:-1]):
        for a in desk.appear(i):
            m.add(pip(), t0 + a, 0.5, pan=rng.uniform(-0.3, 0.3))
    # soft: low-pass the chip, an echo of a dotted eighth, fade in 20 ms and out 2 s, -3 dBFS
    out = echo(_filter(m.out, "low", 3500), 0.75 * spb)
    out = _filter(out, "high", 40)[:m.n0].copy()
    na, nr = int(0.02 * SR), int(2.0 * SR)
    out[:na] *= np.linspace(0, 1, na)[:, None]
    out[-nr:] *= np.linspace(1, 0, nr)[:, None] ** 2
    out = np.tanh(1.5 * out / np.abs(out).max()) / np.tanh(1.5)      # gentler than the other reels
    return (out / np.abs(out).max() * 10 ** (-3 / 20)).astype(np.float32)


def write(desk, path: Path) -> Path:
    """The soundtrack as a 48 kHz 16-bit stereo WAV."""
    pcm = (soundtrack(desk) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path
