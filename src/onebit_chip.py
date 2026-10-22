"""8-bit chiptune for the 1-bit films, synthesized from scratch and timed to the film.

The voices of a home console of 1985: two pulse waves (duty 12.5, 25 and 50 %), a 4-bit
stepped triangle for the bass and the kick, and sample-and-hold noise for snare and hats, with
volume envelopes in 16 steps. The key is D Phrygian dominant (D Eb F# G A Bb C), the "desert"
scale, at the film's tempo (`desk.bpm`, default 112). The parts enter scene by scene: a lone
chord arpeggio under the question, hats and bass as the data start to move, the full beat for
the main scene, a half-time break, the tune at the close. Every echo tail wraps round to the
start, so the track loops with the picture.

Sounds of the story: each caption word is a dialogue beep, like a console role-playing game
typing its text box; `desk.melody()` gives the data as lead notes (time, step on the scale
with 0 the tonic, length, gain); `desk.hits` are fanfares; `desk.drips` and `desk.sweeps`
(optional) are water drops and rising whistles, (start, end) in seconds.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
RNG = np.random.default_rng(11)
SCALE = (0, 1, 4, 5, 7, 8, 10)              # Phrygian dominant
TONIC = 62                                  # D4
CHORDS = ((50, 54, 57), (51, 55, 58), (48, 51, 55), (51, 55, 58))   # D, Eb, Cm, Eb: one per bar
MOTIF = (4, 5, 4, 2, 1, 2, 0, -1, 0, 1, 2, 4, 2, 1, 0, 0)          # the tune, in eighths over two bars


def hz(note: float) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)


def step_note(step: int) -> int:
    octave, k = divmod(int(step), len(SCALE))
    return TONIC + 12 * octave + SCALE[k]


def _t(n: int) -> np.ndarray:
    return np.arange(n) / SR


def _filter(x, kind, f, order=2):
    return sosfilt(butter(order, f, kind, fs=SR, output="sos"), x, axis=0)


def _fade(x, a=0.001, r=0.006):
    n = len(x)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    x[:na] *= np.linspace(0, 1, na)
    x[n - nr:] *= np.linspace(1, 0, nr)
    return x


def _steps(env):
    """A volume envelope in the 16 steps of a 4-bit register."""
    return np.floor(np.clip(env, 0, 1) * 15 + 0.5) / 15


# ── voices ──────────────────────────────────────────────────────────────────

def pulse(f, n, duty=0.5):
    """Pulse wave; f may be an array (vibrato, glides). DC removed."""
    phase = np.cumsum(np.broadcast_to(np.asarray(f, float), (n,))) / SR
    return np.where(phase % 1 < duty, 1.0, -1.0) - (2 * duty - 1)


def tri(f, n):
    """The console's triangle: 32 steps per cycle, 16 levels."""
    phase = np.cumsum(np.broadcast_to(np.asarray(f, float), (n,))) / SR
    x = 4 * np.abs(phase % 1 - 0.5) - 1
    return np.round((x + 1) * 7.5) / 7.5 - 1


def noise(n, rate):
    """Sample-and-hold noise: a lower rate sounds darker, like the console's long noise periods."""
    k = int(n * rate / SR) + 2
    return RNG.choice([-1.0, 1.0], k)[(np.arange(n) * rate / SR).astype(int)]


def lead(note, length, duty=0.25, tau=0.5):
    n = int(length * SR)
    t = _t(n)
    vib = 1 + 0.012 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.12) / 0.1, 0, 1)
    env = _steps(np.minimum(t / 0.005, 1) * np.exp(-t / tau))
    return _fade(pulse(hz(note) * vib, n, duty) * env * 0.5)


def arp(chord, length, rate=1 / 60):
    """A chord as the console plays it: one voice cycling through the notes 60 times a second."""
    n = int(length * SR)
    f = np.array([hz(chord[int(i / (rate * SR)) % len(chord)] + 12) for i in range(0, n, 64)])
    f = np.repeat(f, 64)[:n]
    env = _steps(np.exp(-_t(n) / 0.35))
    return _fade(pulse(f, n, 0.125) * env * 0.35)


def bass(note, length):
    n = int(length * SR)
    return _fade(tri(hz(note), n) * 0.8, 0.001, 0.01)


def kick():
    n = int(0.16 * SR)
    t = _t(n)
    return _fade(tri(55 + 160 * np.exp(-t / 0.025), n) * _steps(np.exp(-t / 0.08)) * 1.1)


def snare():
    n = int(0.18 * SR)
    t = _t(n)
    x = 0.7 * noise(n, 14000) * _steps(np.exp(-t / 0.06)) + 0.5 * tri(190 * np.exp(-t / 0.05), n) * np.exp(-t / 0.03)
    return _fade(x * 0.6)


def hat(open_=False):
    n = int((0.22 if open_ else 0.05) * SR)
    return _fade(_filter(noise(n, 32000), "high", 5000) * _steps(np.exp(-_t(n) / (0.07 if open_ else 0.012))) * 0.35)


def beep(note):
    """Dialogue beep of a console text box."""
    n = int(0.035 * SR)
    return _fade(pulse(hz(note), n, 0.5) * 0.28)


def drip():
    n = int(0.09 * SR)
    t = _t(n)
    return _fade(tri(hz(84 + RNG.integers(0, 7)) * (1 + 0.6 * np.exp(-t / 0.01)), n) * np.exp(-t / 0.025) * 0.5)


def sweep(length, n0=62, n1=86):
    """A whistle rising like a kettle: the air's growing thirst."""
    n = int(length * SR)
    f = hz(n0) * (hz(n1) / hz(n0)) ** np.linspace(0, 1, n)
    env = np.minimum(_t(n) / 0.3, 1) * np.minimum((length - _t(n)) / 0.2, 1)
    return _fade(pulse(f, n, 0.5) * _steps(env) * 0.22)


def crash():
    n = int(1.2 * SR)
    return _fade(_filter(noise(n, 26000), "high", 3000) * _steps(np.exp(-_t(n) / 0.35)) * 0.4)


# ── arrangement ─────────────────────────────────────────────────────────────

class Mixer:
    def __init__(self, seconds, tail=3.0):
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
    bpm = getattr(desk, "bpm", 112)
    spb = 60 / bpm
    bar, s16 = 4 * spb, spb / 4
    end = desk.L.end
    starts = list(desk.L.scenes) + [end]
    sec = lambda i: starts[min(i, len(starts) - 1)]  # noqa: E731
    m = Mixer(end)
    k, sn, hc, ho = kick(), snare(), hat(), hat(True)
    nbar = int(round(end / bar))
    for b in range(nbar):
        t0 = b * bar
        chord = CHORDS[b % len(CHORDS)]
        root = chord[0] - 12
        rising, walking, breaking, closing = (sec(1) <= t0 < sec(2), sec(2) <= t0 < sec(3),
                                              sec(3) <= t0 < sec(4), t0 >= sec(4))
        moving = t0 >= sec(1)
        # chord arpeggio: eighths from the start, sixteenths when the beat is full
        step = s16 if (walking or closing) else 2 * s16
        for j, t in enumerate(np.arange(t0, t0 + bar - 1e-9, step)):
            m.add(arp(chord, step * 0.9), t, 0.5 if j % 2 == 0 else 0.35, pan=-0.35)
        # triangle bass: octave jumps in eighths once the data move
        if moving:
            for j in range(8):
                note = root + (12 if j % 2 else 0) + (7 if j in (5,) else 0)
                m.add(bass(note, 2 * s16 * (0.5 if breaking else 0.85)), t0 + j * 2 * s16, 0.9)
        else:
            m.add(bass(root, bar * 0.95), t0, 0.6)
        # drums
        for j in range(16):
            t = t0 + j * s16
            if moving and j % 2 == 0:
                m.add(hc, t, 0.8, pan=0.3)
            if walking or closing:
                if j in (0, 8):
                    m.add(k, t, 1.0)
                if j in (4, 12):
                    m.add(sn, t, 0.9)
                if j % 2 == 1:
                    m.add(hc, t, 0.5, pan=0.3)
                if closing and j in (6, 14):
                    m.add(ho, t, 0.6, pan=0.3)
            elif breaking:
                if j == 0:
                    m.add(k, t, 1.0)
                if j == 8:
                    m.add(sn, t, 0.9)
            elif rising and j in (0, 8) and t0 >= sec(1) + bar:
                m.add(k, t, 0.9)
        # the tune at the close, an octave up on the last bar so it falls back into the opening
        if closing:
            half = int((t0 - sec(4)) / bar) % 2
            for j in range(8):
                st = MOTIF[8 * half + j]
                m.add(lead(step_note(st), 2 * s16 * 0.95, 0.25, 0.4), t0 + j * 2 * s16, 0.75, pan=0.2)
                m.add(lead(step_note(st), 2 * s16 * 0.95, 0.25, 0.4), t0 + j * 2 * s16 + 3 * s16, 0.25, pan=-0.5)

    # the data as the lead, quantised to sixteenths, echoed three sixteenths later on the other side
    if hasattr(desk, "melody"):
        slots = {}
        for t, st, length, gain in desk.melody():
            q = round(t / s16) * s16
            if q not in slots or gain > slots[q][2]:
                slots[q] = (st, length, gain)
        for q, (st, length, gain) in slots.items():
            note = step_note(st)
            m.add(lead(note, length, 0.25, 0.25), q, gain, pan=0.15)
            m.add(lead(note, length, 0.125, 0.2), q + 3 * s16, gain * 0.35, pan=-0.6)
    # dialogue beeps: one per caption word, as the word appears
    for t0, sc in zip(starts, desk.S.scenes):
        words = sc.title.replace("{", " ").replace("}", " ").replace("[", " ").replace("]", " ").split()
        for j in range(len(words)):
            m.add(beep(step_note(7 + RNG.integers(0, 5))), t0 + 0.15 + 0.6 * j / len(words), 0.5,
                  pan=RNG.uniform(-0.3, 0.3))
    for t in getattr(desk, "hits", []):
        m.add(crash(), t, 0.8)
        for j, st in enumerate((0, 2, 4, 7)):
            m.add(lead(step_note(st), 0.6, 0.5, 0.3), t + j * 0.04, 0.45, pan=-0.2 + 0.15 * j)
    for a, b in getattr(desk, "drips", []):
        for t in np.sort(RNG.uniform(a, b, int((b - a) * 4))):
            m.add(drip(), round(t / s16) * s16, 0.6, pan=RNG.uniform(-0.7, 0.7))
    for a, b in getattr(desk, "sweeps", []):
        m.add(sweep(b - a), a, 0.9, pan=0.4)
    # soften the aliasing a little, wrap the tails round, saturate (as loud as the techno reels), -1.5 dBFS
    mix = _filter(_filter(m.out, "low", 11000), "high", 30)
    out = mix[:m.n0].copy()
    tail = mix[m.n0:]
    out[:len(tail)] += tail[:m.n0]
    out = np.tanh(2.2 * out / np.abs(out).max()) / np.tanh(2.2)
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
