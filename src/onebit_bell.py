"""Slow bells for the 1-bit films, synthesized from scratch and timed to the film.

A third voice beside the techno (onebit_audio) and the 8-bit tune (onebit_chip), for stories
that ask for quiet: two-operator FM bells (the tubular bells of the early digital synthesizers)
in A minor, an electric piano holding one chord per bar (Am, F, C, G), a low drone on A and E
that swells scene by scene, a clock that ticks every beat, and from the second scene a soft
double pulse on the first beat of each bar, like a slow heart. A heavy bell tolls at the turns
of the story. Every tail wraps round to the start, so the track loops with the picture.

Sounds of the story: each caption word a soft typewriter tick; `desk.melody()` gives the data
as bell notes (time, step on the scale with 0 the tonic, length, gain), echoed three
sixteenths later on the other side; `desk.hits` are the tolls.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
RNG = np.random.default_rng(23)
SCALE = (0, 2, 3, 5, 7, 8, 10)              # natural minor
TONIC = 69                                  # A4: the bells sit above the piano
CHORDS = ((45, 52, 57, 60), (41, 48, 53, 57), (48, 55, 60, 64), (43, 50, 55, 59))   # Am, F, C, G
MOTIF = (4, 2, 0, -1, 0, -3)                # the close, in quarter notes: falling home to A


def hz(note: float) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)


def step_note(step: int) -> int:
    octave, k = divmod(int(step), len(SCALE))
    return TONIC + 12 * octave + SCALE[k]


def _t(n: int) -> np.ndarray:
    return np.arange(n) / SR


def _filter(x, kind, f, order=2):
    return sosfilt(butter(order, f, kind, fs=SR, output="sos"), x, axis=0)


def _fade(x, a=0.002, r=0.02):
    n = len(x)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    x[:na] *= np.linspace(0, 1, na)
    x[n - nr:] *= np.linspace(1, 0, nr)
    return x


# ── voices ──────────────────────────────────────────────────────────────────

def bell(note, length=2.4, ratio=3.5, index=2.6, tau=0.9):
    """Two-operator FM: an inharmonic modulator ratio rings like struck metal; the brightness
    (modulation index) dies away faster than the tone."""
    n = int(length * SR)
    t = _t(n)
    f = hz(note)
    mod = index * np.exp(-t / (tau / 3)) * np.sin(2 * np.pi * ratio * f * t)
    return _fade(np.sin(2 * np.pi * f * t + mod) * np.exp(-t / tau) * 0.5)


def piano(chord, length):
    """Electric piano: FM at ratio 1, a quick bright attack, a long soft decay."""
    n = int(length * SR)
    t = _t(n)
    out = np.zeros(n)
    for note in chord:
        f = hz(note)
        mod = 1.2 * np.exp(-t / 0.08) * np.sin(2 * np.pi * f * t)
        out += np.sin(2 * np.pi * f * t + mod) * np.exp(-t / 1.6)
    return _fade(out / len(chord) * 0.6, 0.004, 0.2)


def toll(note=45, length=5.0):
    """A church bell: hum, prime, minor third, fifth, nominal and two upper partials, the low
    ones ringing longest."""
    n = int(length * SR)
    t = _t(n)
    f = hz(note)
    out = np.zeros(n)
    for ratio, gain, tau in ((0.5, 0.5, 3.0), (1.0, 0.8, 2.2), (1.19, 0.5, 1.6), (1.5, 0.35, 1.2),
                             (2.0, 0.45, 1.0), (2.52, 0.25, 0.6), (3.0, 0.15, 0.4)):
        out += gain * np.sin(2 * np.pi * f * ratio * t + RNG.uniform(0, 2 * np.pi)) * np.exp(-t / tau)
    strike = _filter(RNG.standard_normal(n), "band", (800, 3000)) * np.exp(-t / 0.01) * 0.3
    return _fade((out + strike) * 0.35, 0.001, 0.3)


def drone(length):
    """A and E, low, breathing slowly."""
    n = int(length * SR)
    t = _t(n)
    x = sum(g * np.sin(2 * np.pi * hz(note) * t) for note, g in ((33, 0.6), (40, 0.35), (45, 0.2)))
    return _fade(x * (0.75 + 0.25 * np.sin(2 * np.pi * t / 6.0)) * 0.5, 0.5, 0.5)


def tick(high=True):
    """The clock: a short resonant click, tick a little higher than tock."""
    n = int(0.03 * SR)
    t = _t(n)
    f = 3400 if high else 2600
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.004) + 0.4 * RNG.standard_normal(n) * np.exp(-t / 0.002)
    return _fade(_filter(x, "high", 800) * 0.35, 0.0005, 0.005)


def heart():
    """Lub-dub, low and muffled."""
    n = int(0.6 * SR)
    t = _t(n)
    out = np.zeros(n)
    for start, gain in ((0.0, 1.0), (0.2, 0.6)):
        u = np.clip(t - start, 0, None)
        out += (t >= start) * gain * np.sin(2 * np.pi * (48 + 30 * np.exp(-u / 0.03)) * u) * np.exp(-u / 0.09)
    return _fade(_filter(out, "low", 160) * 0.9)


def key():
    """A typewriter key, very soft."""
    n = int(0.02 * SR)
    return _fade(_filter(RNG.standard_normal(n), "band", (1500, 5000)) * np.exp(-_t(n) / 0.003) * 0.2,
                 0.0005, 0.004)


# ── arrangement ─────────────────────────────────────────────────────────────

class Mixer:
    def __init__(self, seconds, tail=6.0):
        self.n0 = int(round(seconds * SR))
        self.out = np.zeros((self.n0 + int(tail * SR), 2))

    def add(self, sig, t, gain=1.0, pan=0.0):
        a = (pan + 1) * np.pi / 4
        i = int(round(t * SR))
        j = min(len(self.out), i + len(sig))
        if j > i >= 0:
            self.out[i:j, 0] += gain * np.cos(a) * sig[:j - i]
            self.out[i:j, 1] += gain * np.sin(a) * sig[:j - i]


def soundtrack(desk) -> np.ndarray:
    bpm = getattr(desk, "bpm", 96)
    spb = 60 / bpm
    bar, s16 = 4 * spb, spb / 4
    end = desk.L.end
    starts = list(desk.L.scenes) + [end]
    sec = lambda i: starts[min(i, len(starts) - 1)]  # noqa: E731
    m = Mixer(end)
    hb = heart()
    swell = (0.25, 0.35, 0.45, 0.45, 0.4)
    for i in range(len(starts) - 1):
        m.add(drone(starts[i + 1] - starts[i] + 1.0), starts[i], swell[min(i, len(swell) - 1)])
    nbar = int(round(end / bar))
    for b in range(nbar):
        t0 = b * bar
        chord = CHORDS[b % len(CHORDS)]
        m.add(piano(chord, bar * 1.6), t0, 0.55, pan=-0.2)
        for j in range(4):
            m.add(tick(j % 2 == 0), t0 + j * spb, 0.5 if t0 >= sec(1) else 0.3, pan=0.35)
        if t0 >= sec(1):
            m.add(hb, t0, 0.8)
        if sec(3) <= t0 < sec(4):                        # the countries: the chord rings out in eighths
            for j in range(8):
                m.add(bell(chord[j % 4] + 24, 0.8, tau=0.4), t0 + j * 2 * s16, 0.15, pan=0.5 - 0.15 * (j % 4))
        if t0 >= sec(4):                                 # the close: the tune falls home to A
            k = int(round((t0 - sec(4)) / bar))
            for j in range(4):
                idx = 4 * k + j
                if idx < len(MOTIF):
                    m.add(bell(step_note(MOTIF[idx]), 2.0, tau=0.8), t0 + j * spb, 0.45, pan=-0.1)

    # the data as bells, quantised to sixteenths, echoed three sixteenths later on the other side
    if hasattr(desk, "melody"):
        slots = {}
        for t, st, length, gain in desk.melody():
            q = round(t / s16) * s16
            if q not in slots or gain > slots[q][2]:
                slots[q] = (st, length, gain)
        for q, (st, length, gain) in slots.items():
            note = step_note(st)
            m.add(bell(note, max(length, 1.2)), q, gain, pan=0.2)
            m.add(bell(note, max(length, 1.2), tau=0.6), q + 3 * s16, gain * 0.3, pan=-0.6)
    # typewriter keys: one per caption word, as the word appears
    for t0, sc in zip(starts, desk.S.scenes):
        words = sc.title.replace("{", " ").replace("}", " ").replace("[", " ").replace("]", " ").split()
        for j in range(len(words)):
            m.add(key(), t0 + 0.15 + 0.6 * j / len(words), 0.6, pan=RNG.uniform(-0.3, 0.3))
    for t in getattr(desk, "hits", []):
        m.add(toll(), t, 0.9)
    # clean the ends, wrap the tails round, saturate gently, -1.5 dBFS
    mix = _filter(_filter(m.out, "low", 12000), "high", 28)
    out = mix[:m.n0].copy()
    tail = mix[m.n0:]
    out[:len(tail)] += tail[:m.n0]
    out = np.tanh(3.0 * out / np.abs(out).max()) / np.tanh(3.0)      # about as loud as the other reels
    return (out / np.abs(out).max() * 10 ** (-1.5 / 20)).astype(np.float32)      # AAC overshoots: keep 1.5 dB


def write(desk, path: Path) -> Path:
    """The soundtrack as a 48 kHz 16-bit stereo WAV."""
    pcm = (soundtrack(desk) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path
