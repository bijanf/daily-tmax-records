"""Persian sound kit for the 1-bit reels: dastgah tuning, plucked and struck strings, frame drums,
modern drums, a pad and effects, and a BS.1770 master at -14 LUFS. Everything is synthesized here
from sine waves, noise and filters: no samples, no recordings, no voices.

The music is a modern half-time groove at 120 BPM (a beat is 0.5 s, a bar 2 s). The films' 60 BPM
grid is one beat per second, so every second beat of the music is a film beat, and scene starts
fall on the grid.

Tuning. MODES holds the dastgah and avaz scales as cents above a tonic, seven steps to the octave.
The koron (a half-flat) is taken as 50 cents below the 12-tone note and the sori (a half-sharp) as
50 cents above. Both are approximations: players bend them by phrase and by instrument, so the
modes are a starting point to tune by ear, not transcriptions. degree() gives the frequency of a
step; note_hz() reads note names such as 'D4' or 'Eb3'.

Sounds. setar: a Karplus-Strong plucked string, bright and short, with a little buzz. santur: a
hammered dulcimer, two detuned strings struck by a hammer, a long ring, the strings apart in the
stereo image. daf: a frame drum, a low bam in the centre, a tak on the rim, zang (the jingles).
tombak: a goblet drum, a deep tom and a sharp bak. kamancheh: a bowed lead with vibrato. Drums:
an 808 kick with a pitch glide, clap, snare, closed and open hats with rolls. sub: a sine with soft
saturation and glide, kept mono. pad: detuned saws, low-passed, wide. Also a riser, an impact,
reverse, a tape stop and a rewind.

Mix. place() adds a sound to a stereo track at a time with a gain and a pan. duck() sidechains a
bus to the kick times. reverb() and pingpong() are the send effects. master() measures integrated
loudness (BS.1770-4: K-weighting, 400 ms blocks, absolute and relative gates) and true peak (4x
oversampled), sets the gain to -14 LUFS and limits to -1 dBTP. write_wav() writes 48 kHz 16-bit
stereo, and mux() puts the track under the picture (video stream copied, AAC 192 kbps).

Self-test: `python -I src/onebit_persian.py --demo` writes a 12 s demo (Shur on the setar, a santur
arpeggio, a daf pattern, a half-time beat with sub, a riser into the drop) to
outputs/onebit/social/persian_kit_demo.wav, prints its loudness and true peak, and asserts
-15 <= LUFS <= -13 and TP <= -1.
"""

from __future__ import annotations

import argparse
import functools
import re
import subprocess
import time
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.ndimage import minimum_filter1d, uniform_filter1d
from scipy.signal import butter, fftconvolve, lfilter, resample_poly, sawtooth, sosfilt

SR = 48000                  # every sound here is 48 kHz
BPM = 120                   # the music's tempo: a beat is 0.5 s, a bar 2 s
BEAT = 60 / BPM
BAR = 4 * BEAT
KORON = -50                 # cents: a half-flat (an approximation, see the docstring)
SORI = 50                   # cents: a half-sharp
ROOT = Path(__file__).resolve().parents[1]
_RNG = np.random.default_rng(19)


# ── tuning ──────────────────────────────────────────────────────────────────

# key: (name, default tonic, cents of the seven steps above the tonic, what the mode is)
MODES = {
    "shur": ("Shur", "D4", (0, 200 + KORON, 300, 500, 700, 800, 1000),
             "D, E-koron, F, G, A, Bb, C: koron second, minor third and sixth"),
    "chahargah": ("Chahargah", "C4", (0, 200 + KORON, 400, 500, 700, 900 + KORON, 1100),
                  "C, D-koron, E, F, G, A-koron, B"),
    "dashti": ("Dashti", "G4", (0, 200 + KORON, 300, 500, 700, 800, 1000),
               "an avaz of Shur, here the Shur set on G (an avaz is known by its phrases, not its set)"),
    "segah": ("Segah", "E4", (0, 200 + KORON, 300 + SORI, 500, 700, 800 + KORON, 1000),
              "E, F-koron, G-sori (the neutral third that names the mode), A, B, C-koron, D"),
    "bayat_tork": ("Bayat-e Tork", "E4", (0, 200, 300 + KORON, 500, 700, 800, 1000),
                   "E, F#, G-koron, A, B, C, D: a whole-tone second and a koron third"),
    "homayoun": ("Homayoun", "D4", (0, 100, 400, 500, 700, 800, 1000),
                 "D, Eb, F#, G, A, Bb, C: the augmented second of the Hijaz family"),
}

_PITCH_CLASS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note_hz(name: str) -> float:
    """Equal-tempered frequency of a note name: 'A4' is 440 Hz, 'D4' 293.66 Hz, 'Eb3', 'F#2'."""
    m = re.fullmatch(r"([A-G])([#b]?)(-?\d+)", name.strip())
    if m is None:
        raise ValueError(f"not a note name: {name!r}")
    letter, acc, octave = m.groups()
    midi = 12 * (int(octave) + 1) + _PITCH_CLASS[letter] + {"#": 1, "b": -1, "": 0}[acc]
    return 440.0 * 2 ** ((midi - 69) / 12)


def mode_cents(mode) -> tuple:
    """The seven cents values of a MODES key, or of a tuple of cents given as a custom mode."""
    return MODES[mode][2] if isinstance(mode, str) else tuple(mode)


def degree(mode, step: int, octave: int = 0, tonic_hz: float | None = None) -> float:
    """Frequency in Hz of scale step `step` of `mode`: 0 is the tonic, 1 the second, ... 6 the
    seventh. `octave` moves it up by whole octaves, and steps past 6 wrap into the next octave, so
    degree(m, 7) is the tonic an octave up. `mode` is a MODES key or seven cents values; tonic_hz
    defaults to the mode's own tonic (Shur on D4, Chahargah on C4, ...) and transposes any mode."""
    if tonic_hz is None:
        if not isinstance(mode, str):
            raise ValueError("a custom mode needs tonic_hz")
        tonic_hz = note_hz(MODES[mode][1])
    up, k = divmod(int(step), 7)
    cents = mode_cents(mode)[k] + 1200 * (octave + up)
    return float(tonic_hz * 2 ** (cents / 1200))


def scale(mode, octave: int = 0, tonic_hz: float | None = None) -> list:
    """The eight frequencies of a mode, from the tonic to the octave above."""
    return [degree(mode, k, octave, tonic_hz) for k in range(8)]


# ── helpers ─────────────────────────────────────────────────────────────────

def reseed(seed: int = 19) -> None:
    """Restart the noise generator: the same calls then give the same sounds."""
    global _RNG
    _RNG = np.random.default_rng(seed)


def _t(n: int) -> np.ndarray:
    return np.arange(n) / SR


@functools.lru_cache(maxsize=256)
def _sos(kind: str, f, order: int = 2):
    """Butterworth sections: kind 'lowpass', 'highpass' or 'bandpass' (f a pair for a band)."""
    return butter(order, f, kind, fs=SR, output="sos")


def _lp(x, f, order: int = 2):
    return sosfilt(_sos("lowpass", float(f), order), x, axis=0)


def _hp(x, f, order: int = 2):
    return sosfilt(_sos("highpass", float(f), order), x, axis=0)


def _bp(x, lo, hi, order: int = 2):
    return sosfilt(_sos("bandpass", (float(lo), float(hi)), order), x, axis=0)


def _fade(x, a: float = 0.002, r: float = 0.01):
    """Linear fades in over a seconds and out over r seconds, in place: no clicks at the edges."""
    n = len(x)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    shape = (-1,) + (1,) * (x.ndim - 1)
    if na:
        x[:na] *= np.linspace(0, 1, na).reshape(shape)
    if nr:
        x[n - nr:] *= np.linspace(1, 0, nr).reshape(shape)
    return x


def _frozen(x):
    """Cached sounds are read-only, so a caller cannot change one by accident."""
    x.flags.writeable = False
    return x


def _sat(x, drive: float):
    """Soft clipping, normalised so that a full-scale input stays at full scale."""
    return np.tanh(drive * x) / np.tanh(drive)


def _peak(x, level: float):
    """Scale x so that its peak is `level`."""
    m = np.abs(x).max()
    return x * (level / m) if m > 0 else x


def _fit(x, n: int):
    """Crop or zero-pad x along time to n rows."""
    if len(x) >= n:
        return x[:n]
    return np.concatenate([x, np.zeros((n - len(x),) + x.shape[1:])])


def new_track(seconds: float, tail: float = 0.0) -> np.ndarray:
    """A silent stereo track (float64, shape (n, 2)): `seconds` plus an optional `tail` for echoes."""
    return np.zeros((int(round((seconds + tail) * SR)), 2))


def pan_gains(pan: float) -> tuple:
    """Equal-power gains (left, right) for pan from -1 (left) through 0 to +1 (right)."""
    a = (np.clip(pan, -1, 1) + 1) * np.pi / 4
    return float(np.cos(a)), float(np.sin(a))


def place(track: np.ndarray, sound, t: float, gain: float = 1.0, pan: float = 0.0) -> None:
    """Add `sound` to `track` in place, starting at t seconds. A mono sound goes to the equal-power
    position `pan` (-1 left, 0 centre, +1 right). A stereo sound keeps its own image, and pan acts
    as a balance. Anything outside the track is cut off."""
    s = np.asarray(sound, float)
    i = int(round(t * SR))
    if i < 0:
        s, i = s[-i:], 0
    n = min(len(s), len(track) - i)
    if n <= 0:
        return
    s = s[:n] * gain
    if s.ndim == 1:
        gl, gr = pan_gains(pan)
        track[i:i + n, 0] += s * gl
        track[i:i + n, 1] += s * gr
    else:
        track[i:i + n, 0] += s[:, 0] * min(1.0, 1 - pan)
        track[i:i + n, 1] += s[:, 1] * min(1.0, 1 + pan)


def widen(x, amount: float = 0.3):
    """Stereo width: the side signal (L minus R) scaled by 1 + amount, the middle kept."""
    mid, side = 0.5 * (x[:, 0] + x[:, 1]), 0.5 * (x[:, 0] - x[:, 1]) * (1 + amount)
    return np.stack([mid + side, mid - side], axis=1)


# ── tuned strings ───────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=8)
def _pick(bright: float):
    """The setar's pick: one smooth pulse with no DC, flat up to a roll-off that a harder pick pushes
    higher (2.5 kHz at bright 0, 5.5 kHz at 1). It is built in the frequency domain, so its
    harmonic weights are deterministic, and its DC is zero: the loop would otherwise hold a DC
    offset for seconds, since its closed-loop gain at DC is about 2000."""
    NF = 4096
    f = np.fft.rfftfreq(NF, 1 / SR)
    fc = 2500.0 + 3000.0 * bright
    h = np.fft.irfft((1 - np.exp(-(f / 25.0) ** 2)) / (1 + (f / fc) ** 4), NF)
    L = 256
    p = np.roll(h, L)[L - 32:L + 480]           # the peak 0.7 ms in, the wings kept
    p = p - p.mean()                            # the last trace of DC, removed exactly
    return _frozen(p / np.abs(p).max())


@functools.lru_cache(maxsize=128)
def _setar(freq: float, dur: float, t60: float, bright: float, buzz: float):
    n = int(dur * SR)
    D = SR / freq - 0.5                         # the two-tap averaging filter adds half a sample
    N = int(D)
    frac = D - N
    c = (1 - frac) / (1 + frac)                 # first-order all-pass: the fractional delay
    g = 0.9995                                  # loop gain near 1; the envelope sets the decay
    ex = _pick(float(bright))                   # the pluck: a short smooth pulse
    e = np.zeros(n)
    m = min(len(ex), n)
    e[:m] = ex[:m]
    # the loop as one recursive filter: y = e + g * 0.5(1 + z^-1) * z^-N * allpass(z) * y
    a = np.zeros(N + 3)
    a[0], a[1] = 1.0, c
    a[N], a[N + 1], a[N + 2] = -0.5 * g * c, -0.5 * g * (1 + c), -0.5 * g
    y = lfilter([1.0, c], a, e)
    y = _hp(y, 30.0)                            # remove any drift before the envelope
    t = _t(n)
    y = y * np.exp(-t / (t60 / 6.9)) * np.minimum(1.0, t / 0.0015)
    y = _peak(y, 1.0)
    y = (1 - buzz) * y + buzz * _sat(y, 4.0)    # the bridge's buzz: odd harmonics from saturation
    return _frozen(_fade(_peak(y, 1.0), 0.0005, 0.02))


def setar(freq: float, dur: float = 1.2, vel: float = 0.8, t60: float = 1.3,
          bright: float = 0.5, buzz: float = 0.12) -> np.ndarray:
    """Setar, mono: a plucked string (Karplus-Strong). A short smooth pluck circulates in a loop as
    long as one period of `freq`, and the loop's averaging filter takes a little of the high end at
    every turn, so the note starts bright and rounds off into a clean harmonic series. t60: seconds
    to fall 60 dB (1.3 is short and ringing); bright: 0 a soft pluck, 1 a hard pick; buzz: 0 to 0.3,
    the bridge's buzz. Peak vel*0.6."""
    return 0.6 * vel * _setar(float(freq), float(dur), float(t60), float(bright), float(buzz))


@functools.lru_cache(maxsize=64)
def _santur(freq: float, dur: float, t60: float, detune: float, spread: float, bright: float):
    n = int(dur * SR)
    t = _t(n)
    K = max(1, min(14, int(0.45 * SR / freq)))  # partials up to 0.45 SR, at most 14
    k = np.arange(1, K + 1)
    p = 1.4 - 0.8 * bright                      # level falls as 1/k^p; a harder hammer gives more upper partials
    ring = t60 / (1 + 0.5 * (k - 1)) / 6.9      # the high partials die first
    env = np.exp(-t[None, :] / ring[:, None])   # the same decay for both strings
    out = np.zeros((n, 2))
    for cents, pan in ((-detune, -spread), (detune, spread)):   # two strings a few cents apart
        f0 = freq * 2 ** (cents / 1200)
        B = 3e-4                                 # stiff steel: the upper partials sit a hair sharp ...
        fk = k * f0 * np.sqrt((1 + B * k * k) / (1 + B))   # ... and the first is exactly f0
        phase = _RNG.uniform(0, 2 * np.pi, K)
        s = (k ** -p)[:, None] * env * np.sin(2 * np.pi * fk[:, None] * t[None, :] + phase[:, None])
        s = s.sum(axis=0)
        gl, gr = pan_gains(pan)
        out[:, 0] += s * gl
        out[:, 1] += s * gr
    m = min(int(0.03 * SR), n)                  # the hammer: a short bandpassed burst at the start
    hammer = _bp(_RNG.standard_normal(m), 1800, 6000) * np.exp(-_t(m) / 0.003)
    out[:m] += 0.3 * hammer[:, None]
    return _frozen(_fade(_peak(out, 1.0), 0.001, 0.05))


def santur(freq: float, dur: float = 2.0, vel: float = 0.8, t60: float = 2.6, detune: float = 2.5,
           spread: float = 0.35, bright: float = 0.6) -> np.ndarray:
    """Santur, stereo: a hammered dulcimer. Each note is two strings a few cents apart (their
    beating gives the shimmer), each a stack of partials whose high ones die first, and a hammer
    click at the start. The strings sit at -spread and +spread across the image. t60: the ring of
    the fundamental in seconds (2.6 is a long ring); detune: cents between the strings; bright: the
    hammer's hardness. Peak vel."""
    return vel * _santur(float(freq), float(dur), float(t60), float(detune), float(spread), float(bright))


@functools.lru_cache(maxsize=64)
def _kamancheh(freq: float, dur: float, vib_hz: float, vib_cents: float, bow: float):
    n = int(dur * SR)
    t = _t(n)
    vib = vib_cents * np.sin(2 * np.pi * vib_hz * t) * np.clip((t - 0.3) / 0.6, 0, 1)   # comes in once the bow holds
    x = sawtooth(2 * np.pi * np.cumsum(freq * 2 ** (vib / 1200)) / SR)
    x = 0.5 * x + 0.5 * _bp(x, 900, 3000)       # the body's nasal formants
    x = x + 0.02 * _bp(_RNG.standard_normal(n), 2000, 6000)   # bow hair
    env = np.minimum(1.0, t / bow) * np.minimum(1.0, (dur - t) / 0.2)
    return _frozen(_peak(x * env, 1.0))


def kamancheh(freq: float, dur: float = 1.6, vel: float = 0.7, vib_hz: float = 5.5,
              vib_cents: float = 30.0, bow: float = 0.12) -> np.ndarray:
    """Kamancheh-like bowed lead, mono: a sawtooth with a vibrato that comes in after the bow takes
    hold, a nasal body formant and a little bow hiss. bow: the attack in seconds. Peak vel*0.5."""
    return 0.5 * vel * _kamancheh(float(freq), float(dur), float(vib_hz), float(vib_cents), float(bow))


# ── drums and percussion ────────────────────────────────────────────────────

@functools.lru_cache(maxsize=64)
def _daf(kind: str, pitch: float):
    if kind == "bam":        # the centre stroke: a thump that drops, and the head's second mode
        n = int(1.0 * SR)
        t = _t(n)
        f = pitch * (1 + 0.9 * np.exp(-t / 0.04))
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.13)
        x = x + 0.25 * np.sin(2 * np.pi * 1.59 * pitch * t) * np.exp(-t / 0.05)
        x = x + 0.15 * _lp(_RNG.standard_normal(n), 4000) * np.exp(-t / 0.002)
    elif kind == "tak":      # the rim stroke: a short bright knock
        n = int(0.35 * SR)
        t = _t(n)
        f = pitch * (1 + 0.25 * np.exp(-t / 0.01))
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.05)
        x = x + 0.3 * np.sin(2 * np.pi * 1.59 * pitch * t) * np.exp(-t / 0.02)
        x = x + 0.5 * _bp(_RNG.standard_normal(n), 2000, 6000) * np.exp(-t / 0.004)
    else:                    # zang: the metal jingles in the frame, a high rattle
        n = int(0.6 * SR)
        t = _t(n)
        x = _bp(_RNG.standard_normal(n), 5000, 9000) * np.exp(-t / 0.09)
        for f in (4100, 5900, 7400):
            x = x + 0.08 * np.sin(2 * np.pi * f * t) * np.exp(-t / 0.1)
    return _frozen(_fade(_peak(x, 1.0), 0.0005, 0.02))


def daf(kind: str = "bam", vel: float = 1.0, pitch: float | None = None) -> np.ndarray:
    """Daf, the Persian frame drum, mono. 'bam': the centre stroke, a low thump with a glide down
    (98 Hz by default). 'tak': the rim stroke, a short higher knock (330 Hz). 'zang': the metal
    jingles, a high rattle. Peak vel."""
    default = {"bam": 98.0, "tak": 330.0, "zang": 0.0}[kind]
    return vel * _daf(kind, float(pitch or default))


@functools.lru_cache(maxsize=16)
def _tombak(kind: str, pitch: float):
    if kind == "tom":        # the centre of the goblet: a deep rounded boom
        n = int(0.9 * SR)
        t = _t(n)
        f = pitch * (1 + 1.2 * np.exp(-t / 0.03))
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.25)
        x = x + 0.2 * np.sin(2 * np.pi * 1.5 * pitch * t) * np.exp(-t / 0.1)
        x = x + 0.12 * _lp(_RNG.standard_normal(n), 3000) * np.exp(-t / 0.003)
    else:                    # bak: the rim, a sharp slap
        n = int(0.25 * SR)
        t = _t(n)
        f = pitch * (1 + 0.2 * np.exp(-t / 0.008))
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.04)
        x = x + 0.6 * _hp(_RNG.standard_normal(n), 2500) * np.exp(-t / 0.004)
    return _frozen(_fade(_peak(x, 1.0), 0.0005, 0.02))


def tombak(kind: str = "tom", vel: float = 1.0, pitch: float | None = None) -> np.ndarray:
    """Tombak, the goblet drum, mono. 'tom': the centre stroke, deep and rounded (95 Hz by default).
    'bak': the rim stroke, a sharp slap (420 Hz). Peak vel."""
    default = 95.0 if kind == "tom" else 420.0
    return vel * _tombak(kind, float(pitch or default))


@functools.lru_cache(maxsize=64)
def _kick(hz: float, decay: float, drive: float):
    n = int(min(1.6, 1.3 * decay + 0.05) * SR)
    t = _t(n)
    f = hz * (1 + 2.4 * np.exp(-t / 0.035))     # the pitch falls from 3.4 times hz in about 0.1 s
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (decay / 6.9))
    click = _hp(_RNG.standard_normal(n), 3000) * np.exp(-t / 0.002) * 0.25
    # normalise before the saturation, which only ever reduces a peak of 1: the kick's peak is exactly vel
    return _frozen(_fade(_sat(_peak(body + click, 1.0), drive), 0.0, 0.01))


def kick808(hz: float = 36.7, vel: float = 1.0, decay: float = 0.9, drive: float = 1.3) -> np.ndarray:
    """808-style kick, mono: a sine that falls from 3.4 times hz to hz, a soft click, a decay of
    `decay` seconds to 60 dB, and soft saturation for the harmonics small speakers need. hz is the
    note the kick sits on (36.7 Hz is D1, the bass of the tonic). Peak vel."""
    return vel * _kick(float(hz), float(decay), float(drive))


@functools.lru_cache(maxsize=8)
def _clap():
    n = int(0.4 * SR)
    t = _t(n)
    env = np.zeros(n)
    for d in (0.0, 0.011, 0.021, 0.032):       # four hands, a few milliseconds apart
        i = int(d * SR)
        env[i:] += np.exp(-_t(n - i) / 0.007)
    env = env + 0.5 * np.exp(-t / 0.12) * (t >= 0.032)   # the reverberant tail of the claps
    return _frozen(_fade(_peak(_bp(_RNG.standard_normal(n) * env, 900, 2800), 1.0), 0.0005, 0.02))


def clap(vel: float = 1.0) -> np.ndarray:
    """Clap, mono: four hands in a few milliseconds, and a tail, band-passed at 0.9 to 2.8 kHz."""
    return vel * _clap()


@functools.lru_cache(maxsize=16)
def _snare(tone: float, decay: float):
    n = int(0.35 * SR)
    t = _t(n)
    f = tone * (1 + 0.3 * np.exp(-t / 0.015))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.06) * 0.6
    noise = _hp(_RNG.standard_normal(n), 1500) * np.exp(-t / (decay / 6.9))
    return _frozen(_fade(_peak(_sat(body + noise, 1.3), 1.0), 0.0005, 0.01))


def snare(vel: float = 1.0, tone: float = 185.0, decay: float = 0.2) -> np.ndarray:
    """Snare, mono: a short tone that falls onto `tone` Hz, and high-passed noise over `decay`
    seconds (to 60 dB). Peak vel."""
    return vel * _snare(float(tone), float(decay))


@functools.lru_cache(maxsize=4)
def _hat(open_: bool):
    n = int((0.32 if open_ else 0.09) * SR)
    t = _t(n)
    # six square partials at the drum machine's metal ratios, mixed with noise, high-passed
    metal = sum(np.sign(np.sin(2 * np.pi * f * t)) for f in (205.3, 304.4, 369.6, 522.7, 540.0, 800.0)) / 6
    x = 0.6 * _hp(_RNG.standard_normal(n), 7000, 4) + 0.4 * _hp(metal, 6000, 4)
    x = x * np.exp(-t / (0.11 if open_ else 0.022))
    return _frozen(_fade(_peak(x, 1.0), 0.0005, 0.01))


def hat(open_: bool = False, vel: float = 1.0) -> np.ndarray:
    """Hi-hat, mono: a metal chord of six square partials mixed with noise, above about 6 to 7 kHz.
    Closed: a 22 ms decay. Open: 110 ms. Peak vel."""
    return vel * _hat(bool(open_))


def roll(track: np.ndarray, t0: float, dur: float, n: int, open_: bool = False, vel0: float = 0.5,
         vel1: float = 1.0, pan: float = 0.0, gain: float = 1.0) -> None:
    """A hat roll: n hats spread over `dur` seconds from t0, the velocity rising from vel0 to vel1."""
    for i in range(n):
        v = vel0 + (vel1 - vel0) * i / max(1, n - 1)
        place(track, hat(open_, 1.0), t0 + dur * i / n, gain * v, pan)


def sub(freq: float, dur: float, vel: float = 0.9, glide_from: float | None = None,
        glide_s: float = 0.05, drive: float = 0.3) -> np.ndarray:
    """Sub bass, mono: a sine at `freq`, optionally sliding from `glide_from` over `glide_s` seconds
    (the 808 slide), with a little soft saturation so that it shows on small speakers. Keep it
    below about 120 Hz and mono. Attack 8 ms, release 30 ms."""
    n = int(dur * SR)
    t = _t(n)
    f = np.full(n, float(freq))
    if glide_from:
        f = freq + (glide_from - freq) * np.exp(-t / glide_s)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR)
    x = (1 - drive) * s + drive * _sat(s, 3.0)
    return vel * _fade(x, 0.008, 0.03)


def pad(freqs, dur: float, vel: float = 0.4, width: float = 0.8, detune: float = 7.0,
        cutoff: float = 1800.0, attack: float = 0.35, release: float = 0.6) -> np.ndarray:
    """Warm pad, stereo: for each note of the chord `freqs` three sawtooths (a centre one, and two
    detuned by `detune` cents and panned out to `width`), low-passed at `cutoff` Hz, with a slow
    swell in and out. Peak vel."""
    n = int(dur * SR)
    t = _t(n)
    out = np.zeros((n, 2))
    for f in freqs:
        for cents, pan in ((0.0, 0.0), (-detune, -width), (detune, width)):
            x = sawtooth(2 * np.pi * float(f) * 2 ** (cents / 1200) * t)
            gl, gr = pan_gains(pan)
            out[:, 0] += gl * x
            out[:, 1] += gr * x
    out = _lp(out, cutoff)
    env = np.minimum(1.0, t / attack) * np.minimum(1.0, (dur - t) / release)
    return vel * _peak(out * env[:, None], 1.0)


def riser(dur: float = 1.0, vel: float = 0.6, f0: float = 180.0, f1: float = 1600.0) -> np.ndarray:
    """Riser, stereo: a pitch sweep from f0 to f1 (exponential) under noise that opens from dark to
    bright and swells over `dur` seconds. Peak vel."""
    n = int(dur * SR)
    t = _t(n)
    u = t / dur
    f = f0 * (f1 / f0) ** (u ** 1.5)
    tone = sawtooth(2 * np.pi * np.cumsum(f) / SR) * 0.3
    noise = _RNG.standard_normal((n, 2))
    w = (u ** 2)[:, None]
    air = (1 - w) * _lp(noise, 1200) + w * _hp(noise, 2500)
    x = (0.6 * air + tone[:, None]) * (u ** 1.5)[:, None]
    return vel * _peak(_fade(x, 0.0, 0.01), 1.0)


def impact(dur: float = 2.2, vel: float = 1.0, pitch: float = 42.0) -> np.ndarray:
    """Impact, the drop, mono: a boom that falls from 3.5 times `pitch` to `pitch`, a body of low
    noise that rolls off over about a second, and a crack of high noise at the first sample."""
    n = int(dur * SR)
    t = _t(n)
    f = pitch * (1 + 2.5 * np.exp(-t / 0.08))
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.35)
    body = _lp(_RNG.standard_normal(n), 900) * np.exp(-t / 0.45)
    crack = _hp(_RNG.standard_normal(n), 3000) * np.exp(-t / 0.05) * 0.4
    x = _sat(boom + 0.6 * body + crack, 1.5)
    return vel * _fade(_peak(x, 1.0), 0.0005, 0.05)


# ── tape effects ────────────────────────────────────────────────────────────

def _varispeed(x, speed, start: float = 0.0):
    """Read x at a changing speed (samples per output sample): 1 is normal, 0 a stop, negative runs
    backwards. Linear interpolation; the read head stays inside x."""
    x = np.asarray(x, float)
    pos = start + np.concatenate([[0.0], np.cumsum(speed)[:-1]])
    pos = np.clip(pos, 0, len(x) - 1)
    idx = np.arange(len(x))
    if x.ndim == 1:
        return np.interp(pos, idx, x)
    return np.stack([np.interp(pos, idx, x[:, c]) for c in range(x.shape[1])], axis=1)


def reverse(x):
    """The sound played backwards, with a 5 ms fade at its new end (the old start)."""
    return _fade(np.array(x[::-1], dtype=float), 0.0, 0.005)


def tape_stop(x, seconds: float | None = None, shape: float = 2.0):
    """The tape slowing to a halt: the sound plays from its start and its speed falls from 1 to 0
    over `seconds` (default: the length of x), as (1 - u)**shape. The pitch falls with the speed."""
    n_out = int(round((seconds or len(x) / SR) * SR))
    u = np.arange(n_out) / n_out
    speed = (1 - u) ** shape
    total = speed.sum()
    if total > len(x) - 1:                      # never read past the end of x
        speed = speed * (len(x) - 1) / total
    return _varispeed(x, speed)


def rewind(x, seconds: float | None = None, shape: float = 2.0):
    """The tape rewinding: the sound plays backwards from its end and slows to a halt at its start."""
    n_out = int(round((seconds or len(x) / SR) * SR))
    u = np.arange(n_out) / n_out
    speed = -(1 - u) ** shape
    total = -speed.sum()
    if total > len(x) - 1:
        speed = speed * (len(x) - 1) / total
    return _varispeed(x, speed, start=len(x) - 1)


# ── effects ─────────────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=16)
def _ir(t60: float, predelay: float, seed: int):
    """A synthetic stereo room: exponentially decaying noise (60 dB at t60) that is darker as it
    decays, five early reflections, a predelay, and an independent noise per channel."""
    rng = np.random.default_rng(seed)
    n = int((predelay + 1.1 * t60) * SR)
    t = _t(n)
    ir = np.zeros((n, 2))
    for c in range(2):
        env = np.where(t >= predelay, 10 ** (-3 * (t - predelay) / t60), 0.0)
        tail = _lp(rng.standard_normal(n) * env, 6000)
        for ms in (7, 11, 17, 23, 31):
            i = int((predelay + ms / 1000 + 0.0007 * c) * SR)
            if i < n:
                tail[i] += rng.uniform(0.4, 0.8) * rng.choice((-1.0, 1.0))
        ir[:, c] = tail / np.sqrt((tail ** 2).sum())   # energy-normalised: the send level sets the wet level
    return _frozen(ir)


def reverb(x, t60: float = 2.2, predelay: float = 0.02, seed: int = 5) -> np.ndarray:
    """Stereo reverb: the input convolved with a synthetic room, left with left and right with right,
    so a stereo input keeps its image. Returns the wet signal, longer than x by the tail. Mix it in
    at a gain of about 0.3 to 0.5."""
    ir = _ir(float(t60), float(predelay), int(seed))
    x = np.asarray(x, float)
    chans = [x, x] if x.ndim == 1 else [x[:, 0], x[:, 1]]
    return np.stack([fftconvolve(chans[c], ir[:, c]) for c in range(2)], axis=1)


def pingpong(x, delay: float = 0.375, feedback: float = 0.45, taps: int = 8,
             tone: float = 3500.0) -> np.ndarray:
    """Ping-pong delay: a repeat every `delay` seconds (0.375 s is a dotted eighth at 120 BPM), the
    first on the right, the next on the left, and so on. Each repeat is fed back at `feedback` and
    filtered darker by a low-pass at `tone` Hz. Returns the wet stereo signal, taps*delay longer."""
    x = np.asarray(x, float)
    mono = x.mean(axis=1) if x.ndim == 2 else x
    d = int(round(delay * SR))
    n = len(mono)
    out = np.zeros((n + taps * d, 2))
    b, a = butter(1, tone, "lowpass", fs=SR)
    y = mono
    for k in range(1, taps + 1):
        y = lfilter(b, a, y) * feedback
        out[k * d:k * d + n, 0 if k % 2 == 0 else 1] += y
    return out


def duck(x, times, depth_db: float = 5.0, release: float = 0.18) -> np.ndarray:
    """Sidechain ducking: the signal dips by depth_db at each time in `times` (the kick), within
    3 ms, and comes back over about `release` seconds. Mono or stereo; returns a new array."""
    x = np.asarray(x, float)
    n = x.shape[0]
    env = np.ones(n)
    floor = 10 ** (-depth_db / 20)
    m = int(4 * release * SR)
    k = np.arange(m) / SR
    for t0 in times:
        i = int(round(t0 * SR))
        if i >= n:
            continue
        L = min(m, n - i)
        shape = 1 - (1 - floor) * np.minimum(1.0, k[:L] / 0.003) * np.exp(-k[:L] / (release / 3))
        env[i:i + L] = np.minimum(env[i:i + L], shape)
    return x * env.reshape((-1,) + (1,) * (x.ndim - 1))


# ── metering and mastering ──────────────────────────────────────────────────

_K_CACHE: dict = {}


def _k_weighting(fs: int):
    """BS.1770 K-weighting: a high shelf (+4 dB above about 1.7 kHz) and a high-pass near 38 Hz,
    from the analogue prototypes; at 48 kHz these match the standard's tabled coefficients."""
    if fs not in _K_CACHE:
        f0, G, Q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
        K = np.tan(np.pi * f0 / fs)
        Vh = 10 ** (G / 20)
        Vb = Vh ** 0.4996667741545416
        a0 = 1 + K / Q + K * K
        b1 = np.array([(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0])
        a1 = np.array([1.0, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0])
        f0, Q = 38.13547087602444, 0.5003270373238773
        K = np.tan(np.pi * f0 / fs)
        a0 = 1 + K / Q + K * K
        b2 = np.array([1.0, -2.0, 1.0])
        a2 = np.array([1.0, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0])
        _K_CACHE[fs] = ((b1, a1), (b2, a2))
    return _K_CACHE[fs]


def kweight(x, fs: int = SR) -> np.ndarray:
    """The K-weighted signal (BS.1770), along the first axis."""
    (b1, a1), (b2, a2) = _k_weighting(fs)
    return lfilter(b2, a2, lfilter(b1, a1, np.asarray(x, float), axis=0), axis=0)


def integrated_lufs(x, fs: int = SR) -> float:
    """Integrated loudness in LUFS (ITU-R BS.1770-4) of a mono or stereo signal: K-weighting, 400 ms
    blocks every 100 ms, an absolute gate at -70 LUFS and a relative gate 10 LU under the mean of
    the blocks that pass the absolute one. -inf for silence."""
    x = np.asarray(x, float)
    if x.ndim == 1:
        x = x[:, None]
    y = kweight(x, fs)
    block, hop = int(0.4 * fs), int(0.1 * fs)
    if len(y) < block:
        y = np.vstack([y, np.zeros((block - len(y), y.shape[1]))])
    cs = np.concatenate([np.zeros((1, y.shape[1])), np.cumsum(y * y, axis=0)])
    starts = np.arange(0, len(y) - block + 1, hop)
    z = ((cs[starts + block] - cs[starts]) / block).sum(axis=1)   # channel weights are 1
    l = -0.691 + 10 * np.log10(np.maximum(z, 1e-30))
    gate_abs = l > -70.0
    if not gate_abs.any():
        return -np.inf
    gamma_a = -0.691 + 10 * np.log10(z[gate_abs].mean())
    gate_rel = gate_abs & (l > gamma_a - 10.0)
    return float(-0.691 + 10 * np.log10(z[gate_rel].mean()))


def true_peak_dbtp(x) -> float:
    """Estimated true peak in dBTP: the largest sample of the signal oversampled 4 times."""
    x = np.asarray(x, float)
    if x.ndim == 1:
        x = x[:, None]
    p = np.abs(resample_poly(x, 4, 1, axis=0)).max()
    return float(20 * np.log10(p)) if p > 0 else -np.inf


def _limit(x, ceiling_db: float):
    """A look-ahead peak limiter. The peak of each sample is taken 4x oversampled; the gain falls
    ahead of every peak above the ceiling, then returns smoothly: a minimum filter and a moving
    average over 5 ms, so no sample can exceed the ceiling, and nothing clicks."""
    ceil = 10 ** (ceiling_db / 20)
    n, ch = x.shape
    up = resample_poly(x, 4, 1, axis=0)
    peak = np.abs(up).reshape(n, 4, ch).max(axis=(1, 2))
    gain = np.minimum(1.0, ceil / np.maximum(peak, 1e-12))
    w = int(0.005 * SR) | 1
    gain = uniform_filter1d(minimum_filter1d(gain, w, mode="nearest"), w, mode="nearest")
    return x * gain[:, None]


def master(track, lufs: float = -14.0, tp: float = -1.0, seconds: float | None = None,
           fade_out: float = 1.0) -> np.ndarray:
    """Master a stereo track: crop to `seconds`, fade out over the last `fade_out` seconds (a cos^2
    fade, so the last hit and the reverb tail die away), set the integrated loudness to `lufs` and
    limit the true peak to `tp` dBTP. Limiting costs loudness, so the gain is found by iterating.
    Returns a new array."""
    x = np.asarray(track, float)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    if seconds is not None:
        x = x[:int(round(seconds * SR))]
    x = _hp(np.array(x, dtype=float), 12.0)         # a DC blocker: hundreds of hits add up their offsets
    nf = min(int(fade_out * SR), len(x))
    if nf > 0:
        x[-nf:] *= (np.cos(np.linspace(0, np.pi / 2, nf)) ** 2)[:, None]
    L0 = integrated_lufs(x)
    if not np.isfinite(L0):
        return x
    ceiling = tp - 0.1                              # the limiter aims a little under the ceiling
    gain_db = lufs - L0
    y = _limit(x * 10 ** (gain_db / 20), ceiling)
    for _ in range(4):                              # limiting took loudness: push the gain back up
        L1 = integrated_lufs(y)
        if not np.isfinite(L1) or abs(L1 - lufs) < 0.03 or gain_db > (lufs - L0) + 12:
            break
        gain_db += lufs - L1
        y = _limit(x * 10 ** (gain_db / 20), ceiling)
    for _ in range(4):                              # the true-peak check, and a lower ceiling if needed
        t_pk = true_peak_dbtp(y)
        if t_pk <= tp - 0.005:
            break
        ceiling -= (t_pk - tp) + 0.1
        y = _limit(x * 10 ** (gain_db / 20), ceiling)
    return y


# ── files ───────────────────────────────────────────────────────────────────

def write_wav(path, x, fs: int = SR) -> Path:
    """A 48 kHz, 16-bit, stereo WAV, with a little TPDF dither (seeded, so a re-run is identical)."""
    x = np.clip(np.asarray(x, float), -1, 1)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    rng = np.random.default_rng(3)
    dither = (rng.random(x.shape) - rng.random(x.shape)) / 32768
    pcm = np.clip(np.round((x + dither) * 32767), -32768, 32767).astype("<i2")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(path), fs, pcm)
    return path


def aac_true_peak(media) -> float:
    """The true peak in dBTP of the audio as a player decodes it (the encoded file, not the WAV)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(media), "-vn", "-f", "f32le",
                          "-ac", "2", "-ar", str(SR), "-"], check=True, capture_output=True).stdout
    return true_peak_dbtp(np.frombuffer(raw, dtype="<f4").reshape(-1, 2).astype(float))


def mux(video_mp4, wav, out_mp4) -> Path:
    """Put the track under the picture: the video stream is copied, the audio is AAC at 192 kbps,
    and the file ends with the shorter of the two streams. AAC overshoots the WAV by a few tenths
    of a dB, so the decoded audio's true peak is measured; above -1 dBTP a warning says to master
    again with tp=-1.5 for the delivered file."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_mp4), "-i", str(wav),
           "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           "-ar", "48000", "-ac", "2", "-shortest", "-movflags", "+faststart", str(out_mp4)]
    subprocess.run(cmd, check=True)
    peak = aac_true_peak(out_mp4)
    if peak > -1.0:
        print(f"warning: the encoded audio peaks at {peak:.2f} dBTP; master again with tp=-1.5")
    return Path(out_mp4)


# ── demo ────────────────────────────────────────────────────────────────────

def demo(out_path=None) -> dict:
    """The 12 s demo, six bars at 120 BPM: a half-time beat with an 808 sub under Persian melody.
    Bars 1-2: Shur on the setar, up and then down, over a pad. Bars 3-4: a santur arpeggio. Bars
    5-6: a daf pattern and a setar hook, with a riser into the drop at 8 s. Writes the WAV, reads
    it back, prints the loudness and true peak it measures, and asserts the targets."""
    t_start = time.time()
    reseed(19)
    S8, S16 = BEAT / 2, BEAT / 4
    seconds, tail = 12.0, 3.0
    drums, bass, music, echo, send, sfx = (new_track(seconds, tail) for _ in range(6))
    kick_s, snare_s, clap_s = kick808(note_hz("D1"), decay=0.9), snare(), clap()
    daf_s = {k: daf(k) for k in ("bam", "tak", "zang")}
    kicks = []

    # the groove: kicks on the 1, the 'and' of 2 and the 'and' of 3 (16ths 0, 6, 10); the snare and
    # the clap on beat 3, the half-time backbeat; hats in eighths; a roll in every other bar
    roots = (0, 0, 3, 3, 0, 4)                              # Shur steps of the sub: D D G G D A
    for b in range(6):
        t0 = b * BAR
        for i in (0, 6, 10):
            place(drums, kick_s, t0 + i * S16, 0.95)
            kicks.append(t0 + i * S16)
        place(drums, snare_s, t0 + 2 * BEAT, 0.55)
        place(drums, clap_s, t0 + 2 * BEAT, 0.28, pan=0.1)
        for i in range(7):
            place(drums, hat(False), t0 + i * S8, 0.22 if i % 2 else 0.15, pan=0.3 if i % 2 else -0.2)
        if b % 2:
            roll(drums, t0 + 1.75, 0.25, 8, vel0=0.4, vel1=1.0, gain=0.2, pan=-0.2)
        else:
            place(drums, hat(True), t0 + 1.75, 0.2, pan=0.2)
        glide = degree("shur", roots[b - 1], -2) if b else None
        # each root lasts a bar and its release (30 ms) runs under the next note, so the sub never drops out
        place(bass, sub(degree("shur", roots[b], -2), BAR + 0.03, vel=0.8, glide_from=glide), t0, 0.7)

    # the setar: bar 1 up the Shur scale in eighths, bar 2 down, the hook in bars 5-6
    notes = [(i * S8, degree("shur", i)) for i in range(8)]
    notes += [(BAR + i * S8, degree("shur", 7 - i)) for i in range(8)]
    hook = ((4, 6, 7, 9, 7, 6, 4, 2), (0, 0, 2, 4, 6, 4, 2, 0))
    for bar_i, steps in zip((4, 5), hook):
        notes += [(bar_i * BAR + i * S8, degree("shur", st)) for i, st in enumerate(steps)]
    for j, (t, f) in enumerate(notes):
        pan = -0.25 if j % 2 else 0.25
        s = setar(f, dur=1.1, vel=1.0, t60=1.3)
        place(music, s, t, 0.5, pan=pan)
        place(send, s, t, 0.3, pan=pan)
        place(echo, s, t, 0.4, pan=pan)

    # the pad: one chord per two bars, D, G, A, under the scale
    chords = ([degree("shur", s, -1) for s in (0, 2, 4)],
              [degree("shur", s, -1) for s in (3, 5, 7)],
              [degree("shur", s, -1) for s in (4, 6, 8)])
    for k, chord in enumerate(chords):             # each pad's release runs under the next one's attack
        place(music, pad(chord, dur=4.0 + 0.6, vel=0.3), k * 2 * BAR, 0.5)

    # the santur: bars 3-4, a sixteenth-note arpeggio over the octave above the setar
    arp = (0, 2, 4, 6, 7, 6, 4, 2)
    for i in range(32):
        place(music, santur(degree("shur", arp[i % 8], 1), dur=1.6, vel=0.4), 2 * BAR + i * S16, 0.5)
        place(send, santur(degree("shur", arp[i % 8], 1), dur=1.6, vel=0.4), 2 * BAR + i * S16, 0.2)

    # the daf: bars 5-6, bam on the 1, tak and tak, bam and tak in eighths, a jingle on each tak
    pattern = ("bam", "tak", "tak", "bam", "tak", "tak", "bam", "tak")
    for b in (4, 5):
        for i, k in enumerate(pattern):
            t = b * BAR + i * S8
            pan = 0.0 if k == "bam" else (0.35 if i % 2 else -0.35)
            place(drums, daf_s[k], t, 0.6 if k == "bam" else 0.42, pan=pan)
            if k == "tak":
                place(drums, daf_s["zang"], t, 0.16, pan=pan)

    # the drop: a riser into bar 5, an impact on the first daf stroke
    place(sfx, riser(1.0, vel=0.6), 7.0, 0.5)
    place(sfx, impact(2.2, vel=1.0, pitch=42.0), 8.0, 0.8)

    # the mix: the music and bass ducked to the kick, the setar and santur sent to a room and a
    # ping-pong echo, then the master
    music_d = duck(music, kicks, depth_db=5.0, release=0.18)
    bass_d = duck(bass, kicks, depth_db=3.0, release=0.12)
    wet = reverb(send, t60=2.2) * 0.5
    dly = pingpong(echo, delay=0.375, feedback=0.42, taps=8) * 0.6
    mix = drums + music_d + bass_d + sfx
    mix = mix + _fit(wet, len(mix)) + _fit(dly, len(mix))
    out = master(mix, lufs=-14.0, tp=-1.0, seconds=seconds, fade_out=1.0)

    path = Path(out_path) if out_path else ROOT / "outputs" / "onebit" / "social" / "persian_kit_demo.wav"
    write_wav(path, out)
    _, pcm = wavfile.read(str(path))
    back = pcm.astype(float) / 32768.0          # the file as a listener gets it
    loud, peak = integrated_lufs(back), true_peak_dbtp(back)
    print(f"{path}")
    print(f"integrated loudness {loud:.2f} LUFS, true peak {peak:.2f} dBTP, "
          f"{seconds:.0f} s, synthesized in {time.time() - t_start:.1f} s")
    assert -15 <= loud <= -13, f"loudness {loud:.2f} LUFS is outside -15..-13"
    assert peak <= -1, f"true peak {peak:.2f} dBTP is above -1"
    return {"path": str(path), "lufs": loud, "tp_dbtp": peak}


def main() -> None:
    """Command line: --demo writes and checks the demo; otherwise print the usage."""
    ap = argparse.ArgumentParser(description="Persian sound kit: the self-test demo.")
    ap.add_argument("--demo", action="store_true",
                    help="write outputs/onebit/social/persian_kit_demo.wav and check its loudness")
    args = ap.parse_args()
    if args.demo:
        demo()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
