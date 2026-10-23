"""A steam engine and a steam organ for the 1-bit films, synthesized from scratch and timed to the film.

A fourth voice beside the techno (onebit_audio), the 8-bit tune (onebit_chip) and the bells
(onebit_bell), for the industrial revolution: a locomotive's exhaust (band-passed noise, four
chuffs to a turn of the wheels, the first the loudest), the clack of the rails twice a bar, and
a calliope (whistle pipes with breath and a slow vibrato) holding one chord per bar in D minor
(Dm, Bb, F, C) over an organ pedal. The engine starts slow on the question and thickens with the
race, from quarters to eighths to sixteenths; it idles while the ratings come in and stops for
the close. A steam whistle sounds at the turns of the story (`desk.hits`); the last of them opens
the close. The close comes home: A major, then D minor held while the steam hisses out, and the
track fades to silence over its last 1.2 s. Like the bells, the track starts clean.

Sounds of the story: each caption word a soft typewriter key (`desk.appear(i)`: when each word
of scene i comes in); `desk.melody()` gives the data as calliope notes (time, step on the scale
with 0 the tonic, length, gain); `desk.cells_t` are stamps, one per battery.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from onebit_bell import SR, Mixer, _fade, _filter, _t, hz

RNG = np.random.default_rng(29)
SCALE = (0, 2, 3, 5, 7, 8, 10)              # natural minor
TONIC = 74                                  # D5: the calliope sings above the chords
CHORDS = ((50, 57, 62, 65), (46, 53, 58, 62), (53, 57, 60, 65), (48, 55, 60, 64))   # Dm, Bb, F, C
DOMINANT, HOME = (45, 52, 57, 61, 64), (38, 50, 57, 62, 65)                       # A, then Dm low
WHISTLE = (74, 77, 82)                      # D, F, B flat: the minor-sixth chord of an old whistle


def step_note(step: int) -> int:
    octave, k = divmod(int(step), len(SCALE))
    return TONIC + 12 * octave + SCALE[k]


# ── voices ──────────────────────────────────────────────────────────────────

def chuff(gain=1.0, length=0.16):
    """One puff of exhaust: noise through a band that closes as the puff dies."""
    n = int(length * SR)
    t = _t(n)
    x = RNG.standard_normal(n) * np.exp(-t / (0.045 * gain ** 0.5))
    lo, hi = _filter(x, "band", (300, 1400)), _filter(x, "band", (1400, 4200))
    return _fade((lo + 0.35 * hi * np.exp(-t / 0.02)) * 0.6 * gain, 0.004, 0.03)


def clack():
    """A rail joint: two short metallic knocks."""
    n = int(0.12 * SR)
    t = _t(n)
    out = np.zeros(n)
    for start, f in ((0.0, 1900), (0.055, 1500)):
        u = np.clip(t - start, 0, None)
        ping = np.sin(2 * np.pi * f * u) + 0.5 * np.sin(2 * np.pi * 2.76 * f * u)
        out += (t >= start) * (ping * np.exp(-u / 0.012) + 0.5 * RNG.standard_normal(n) * np.exp(-u / 0.004))
    return _fade(_filter(out, "high", 600) * 0.25, 0.0005, 0.01)


def pipe(note, length, breath=0.12, vib=0.004):
    """A whistle pipe of the calliope: nearly a sine, a touch of the octave, breath noise and a
    slow vibrato; it speaks in 40 ms and stops in 80."""
    n = int(length * SR)
    t = _t(n)
    f = hz(note) * (1 + vib * np.sin(2 * np.pi * 5.5 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.06 * np.sin(3 * ph)
    air = _filter(RNG.standard_normal(n), "band", (hz(note) * 0.8, hz(note) * 3.0)) * breath
    return _fade((tone + air) * 0.3, 0.04, 0.08)


def organ(chord, length):
    """The chord of the bar on soft pipes, quiet under the tune."""
    return sum(pipe(note, length, breath=0.05, vib=0.002) for note in chord) / len(chord)


def pedal(note, length):
    """An organ pedal: a low fundamental and its octave, no vibrato."""
    n = int(length * SR)
    t = _t(n)
    f = hz(note)
    return _fade((np.sin(2 * np.pi * f * t) + 0.4 * np.sin(4 * np.pi * f * t)) * 0.5, 0.03, 0.15)


def whistle(length=0.9):
    """A steam whistle: three pipes that scoop up into pitch, lots of steam."""
    n = int(length * SR)
    t = _t(n)
    out = np.zeros(n)
    for note in WHISTLE:
        f = hz(note) * (1 - 0.03 * np.exp(-t / 0.06))
        ph = 2 * np.pi * np.cumsum(f) / SR
        out += np.sin(ph) + 0.25 * np.sin(2 * ph)
    steam = _filter(RNG.standard_normal(n), "band", (1500, 6000)) * 0.6
    env = np.minimum(1, t / 0.05) * np.where(t > length - 0.2, (length - t) / 0.2, 1)
    return _fade((out / 3 + steam) * env * 0.4, 0.01, 0.05)


def hiss(length):
    """Steam let out of the cylinders: high noise that swells and dies."""
    n = int(length * SR)
    t = _t(n)
    env = np.minimum(1, t / 0.15) * np.exp(-t / (length / 3))
    return _fade(_filter(RNG.standard_normal(n), "band", (2500, 9000)) * env * 0.25, 0.01, 0.3)


def key():
    """A typewriter key, very soft (onebit_bell's, from this module's random numbers, so the
    track is the same on every render)."""
    n = int(0.02 * SR)
    return _fade(_filter(RNG.standard_normal(n), "band", (1500, 5000)) * np.exp(-_t(n) / 0.003) * 0.2,
                 0.0005, 0.004)


def stamp():
    """A rubber stamp on paper: a low thump and a slap."""
    n = int(0.25 * SR)
    t = _t(n)
    thump = np.sin(2 * np.pi * (60 + 80 * np.exp(-t / 0.02)) * t) * np.exp(-t / 0.07)
    slap = _filter(RNG.standard_normal(n), "band", (500, 3000)) * np.exp(-t / 0.008)
    return _fade((thump + 0.4 * slap) * 0.6, 0.001, 0.02)


# ── arrangement ─────────────────────────────────────────────────────────────

def soundtrack(desk) -> np.ndarray:
    bpm = getattr(desk, "bpm", 96)
    spb = 60 / bpm
    bar = 4 * spb
    end = desk.L.end
    assert abs(end / bar - round(end / bar)) < 1e-6, "the film must last a whole number of bars"
    global RNG
    RNG = np.random.default_rng(29)                    # the same track on every render
    starts = list(desk.L.scenes) + [end]
    m = Mixer(end)
    nbar = int(round(end / bar))
    race0, race1 = starts[1], starts[2]
    for b in range(nbar):
        t0 = b * bar
        final, cadence = b == nbar - 1, b == nbar - 2
        chord = HOME if final else DOMINANT if cadence else CHORDS[b % len(CHORDS)]
        length = bar * (2.0 if final else 1.0)
        m.add(organ(chord, length), t0, 0.35 if final else 0.22, pan=-0.25)
        m.add(pedal(chord[0], length), t0, 0.3 if final else 0.18)   # high enough for a phone's speaker
        if final:
            continue                                   # the engine has stopped
        # the engine: quarters on the question, eighths and then sixteenths in the race, idling
        # in quarters while the ratings come in
        for j in range(16):
            t = t0 + j * spb / 4
            if t < race0 or t >= race1:
                every = 4
            else:
                every = 2 if t < (race0 + race1) / 2 else 1
            if j % every:
                continue
            accent = (1.0, 0.45, 0.7, 0.45)[(j // every) % 4]
            m.add(chuff(accent), t, 0.9 if race0 <= t < race1 else 0.6, pan=RNG.uniform(-0.15, 0.15))
        if not cadence:
            m.add(clack(), t0 + 1.5 * spb, 0.5, pan=0.4)
            m.add(clack(), t0 + 3.5 * spb, 0.4, pan=0.4)
    # the close comes home: steam let out under the last chord
    m.add(hiss(bar), (nbar - 1) * bar, 0.6)

    # the data on the calliope, quantised to sixteenths, a soft echo an eighth later
    s16 = spb / 4
    if hasattr(desk, "melody"):
        for t, st, length, gain in desk.melody():
            q = round(t / s16) * s16
            m.add(pipe(step_note(st), length), q, gain, pan=0.2)
            m.add(pipe(step_note(st), length, breath=0.05), q + 2 * s16, gain * 0.25, pan=-0.5)
    for t in getattr(desk, "cells_t", []):
        m.add(stamp(), t, 0.7)
    for k, t in enumerate(getattr(desk, "hits", [])):
        m.add(whistle(1.4 if k == len(desk.hits) - 1 else 0.7), t, 0.5)
    # typewriter keys: one per caption word, as the word appears
    for i, t0 in enumerate(starts[:-1]):
        for a in desk.appear(i):
            m.add(key(), t0 + a, 0.6, pan=RNG.uniform(-0.3, 0.3))
    # clean the ends, cut the tails, fade in 20 ms and out 1.2 s, saturate gently, -3 dBFS
    out = _filter(_filter(m.out, "low", 12000), "high", 28)[:m.n0].copy()
    na, nr = int(0.02 * SR), int(1.2 * SR)
    out[:na] *= np.linspace(0, 1, na)[:, None]
    out[-nr:] *= np.linspace(1, 0, nr)[:, None] ** 2
    out = np.tanh(3.0 * out / np.abs(out).max()) / np.tanh(3.0)      # about as loud as the other reels
    return (out / np.abs(out).max() * 10 ** (-3 / 20)).astype(np.float32)      # AAC overshoots: keep 3 dB


def write(desk, path: Path) -> Path:
    """The soundtrack as a 48 kHz 16-bit stereo WAV."""
    pcm = (soundtrack(desk) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path
