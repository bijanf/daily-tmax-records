"""Berlin minimal techno for the 1-bit desktops, synthesized from scratch and timed to the film.

64 beats fill the video exactly (128 BPM for the 30 s social cut), and every echo and reverb
tail is wrapped round to the start, so the track loops with the picture. Kick, off-beat hats,
clap, a rolling bass ducked by the kick, dub-techno chord stabs in a ping-pong tape echo and a
1-bit square arpeggio enter bar by bar as the windows open, and drop out for a pad when the
camera returns to the poster.

The data are audible: every station appearing on the map is a blip, higher and louder for the
2020s; the grid cells chirp by class; each race square glides in pitch to its ratio; the
screen switching off powers down, the loader beeps up its progress bar, the camera whooshes.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
BEATS = 64
RNG = np.random.default_rng(7)

# dub chords (MIDI notes) and the 1-bit arpeggio scale (A minor pentatonic)
AM9, FMAJ9 = (57, 60, 64, 67, 71), (53, 57, 60, 64, 67)
PAD = (45, 52, 57, 60, 64, 67)
PENTA = (81, 84, 86, 88, 91, 93, 96)


def hz(note: float) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)


def _t(n: int) -> np.ndarray:
    return np.arange(n) / SR


def _filter(x, kind, f, order=2):
    return sosfilt(butter(order, f, kind, fs=SR, output="sos"), x, axis=0)


def _fade(x, a=0.002, r=0.01):
    """Short linear fades against clicks."""
    n = len(x)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    shape = (-1,) + (1,) * (x.ndim - 1)
    x[:na] *= np.linspace(0, 1, na).reshape(shape)
    x[n - nr:] *= np.linspace(1, 0, nr).reshape(shape)
    return x


def saw(f, n, k=40):
    """Band-limited sawtooth (sum of harmonics below 0.45 SR)."""
    t, out = _t(n), np.zeros(n)
    for h in range(1, min(k, int(0.45 * SR / f)) + 1):
        out += np.sin(2 * np.pi * h * f * t) / h
    return out * 2 / np.pi


def square(f, n, k=13):
    """Band-limited square: the 1-bit voice, odd harmonics only."""
    t, out = _t(n), np.zeros(n)
    for h in range(1, min(k, int(0.45 * SR / f)) + 1, 2):
        out += np.sin(2 * np.pi * h * f * t) / h
    return out * 4 / np.pi


# ── instruments ──────────────────────────────────────────────────────────────

def kick():
    n = int(0.45 * SR)
    t = _t(n)
    f = 44 + 120 * np.exp(-t / 0.03)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.30)
    click = _filter(RNG.standard_normal(n), "high", 2000) * np.exp(-t / 0.002) * 0.25
    return _fade(np.tanh(1.6 * (body + click)) / np.tanh(1.6), 0.0005, 0.02)


def hat(open_=False):
    n = int((0.3 if open_ else 0.08) * SR)
    x = _filter(RNG.standard_normal(n), "high", 6000 if open_ else 7500)
    return _fade(x * np.exp(-_t(n) / (0.085 if open_ else 0.018)) * 0.5, 0.0005)


def clap():
    n = int(0.4 * SR)
    t, x = _t(n), np.zeros(n)
    for d in (0.0, 0.011, 0.023):
        i = int(d * SR)
        x[i:] += np.exp(-_t(n - i) / 0.006)
    x += 0.6 * np.exp(-t / 0.14)
    return _fade(_filter(RNG.standard_normal(n) * x, "band", (900, 2600)) * 0.6, 0.0005)


def bass(note, length):
    n = int(length * SR)
    f = hz(note)
    x = 0.7 * _filter(saw(f, n, 40), "low", 600) + 0.5 * np.sin(2 * np.pi * f * _t(n))
    return _fade(np.tanh(1.4 * x * np.exp(-_t(n) / 0.12)), 0.003, 0.02)


def chord(notes, length, cutoff=1500, attack=0.002, tau=0.10, detune=0.0):
    """Stacked sawtooth voices, filtered; detune > 0 spreads two copies left and right."""
    n = int(length * SR)
    out = np.zeros((n, 2))
    for side, cents in ((0, -detune), (1, detune)):
        x = sum(saw(hz(m + cents / 100), n, 24) for m in notes) / len(notes)
        out[:, side] = _filter(_filter(x, "low", cutoff), "high", 160)
    env = np.minimum(_t(n) / max(attack, 1e-4), 1) * np.exp(-_t(n) / tau)
    return _fade(out * env[:, None], attack, 0.03)


def blip(note, length=0.05, tau=0.02):
    n = int(length * SR)
    return _fade(square(hz(note), n, 9) * np.exp(-_t(n) / tau) * 0.5, 0.001, 0.005)


def glide(n0, n1, length):
    """A square voice sliding from one note to another (exponential in frequency)."""
    n = int(length * SR)
    f = hz(n0) * (hz(n1) / hz(n0)) ** (np.linspace(0, 1, n) ** 0.7)
    x = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR))
    x = _filter(x, "low", 5000) * np.exp(-_t(n) / (length * 0.8))
    return _fade(x * 0.35, 0.002, 0.03)


def power_down(length):
    n = int(length * SR)
    f = 900 * (35 / 900) ** np.linspace(0, 1, n)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.linspace(1, 0.2, n)
    crackle = _filter(RNG.standard_normal(n), "band", (300, 3000)) * 0.15
    return _fade((tone + crackle) * 0.6, 0.002, 0.05)


def whoosh(length):
    n = int(length * SR)
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    return _fade(_filter(RNG.standard_normal(n), "band", (500, 4000)) * env * 0.35)


def echo(x, delay, feedback=0.5, repeats=6, cutoff=2500):
    """Ping-pong tape echo of a mono signal: each repeat darker, alternating sides."""
    d = int(delay * SR)
    out = np.zeros((len(x) + repeats * d, 2))
    y = x.copy()
    for k in range(1, repeats + 1):
        y = _filter(y, "low", cutoff, 1) * feedback
        out[k * d:k * d + len(y), k % 2] += y
    return out


def reverb_ir(seconds=2.4, decay=0.9):
    n = int(seconds * SR)
    ir = RNG.standard_normal((n, 2)) * np.exp(-_t(n) / decay)[:, None]
    ir = _filter(ir, "low", 6000)
    return ir / np.sqrt((ir ** 2).sum(axis=0))


# ── arrangement ──────────────────────────────────────────────────────────────

class Mixer:
    def __init__(self, seconds, tail=4.0):
        self.n0 = int(round(seconds * SR))
        self.buses = {k: np.zeros((self.n0 + int(tail * SR), 2)) for k in ("drums", "music", "sfx", "send")}

    def add(self, bus, sig, t, gain=1.0, pan=0.0):
        sig = np.asarray(sig)
        if sig.ndim == 1:   # constant-power pan
            a = (pan + 1) * np.pi / 4
            sig = np.stack([sig * np.cos(a), sig * np.sin(a)], axis=1)
        i = int(round(t * SR))
        b = self.buses[bus]
        j = min(len(b), i + len(sig))
        if j > i >= 0:
            b[i:j] += gain * sig[:j - i]


def soundtrack(desk) -> np.ndarray:
    """Stereo track (float32, -1..1) for a Desktop's timeline and story."""
    L, S = desk.L, desk.S
    spb = L.end / BEATS
    s16, bar = spb / 4, spb * 4
    nxt = lambda t, step: np.ceil(t / step - 1e-9) * step  # noqa: E731
    keys = L.camera
    groove_end = np.floor(keys[-1][0] / bar) * bar if keys[-1][1] == keys[0][1] else L.end
    kick_on, bass_on = nxt(L.desk, bar), nxt(L.grid, bar)
    clap_on, stab_on = nxt(L.race, bar), nxt(L.widget, bar)
    moving = [(t0, t1) for (t0, b0), (t1, b1) in zip(keys, keys[1:]) if b0 != b1]
    arp_on = nxt(moving[0][0], bar) if moving else groove_end
    m = Mixer(L.end)

    # drums
    k, hc, ho, cl = kick(), hat(), hat(True), clap()
    kicks = np.arange(kick_on, groove_end - 1e-9, spb)
    for i, t in enumerate(kicks):
        m.add("drums", k, t, 0.9)
        m.add("drums", ho, t + spb / 2, 0.22, pan=0.25)
        if t >= clap_on:
            for j in (1, 3):
                m.add("drums", hc, t + j * s16, 0.12 + 0.05 * RNG.random(), pan=-0.3)
            if i % 2 == 1:
                m.add("drums", cl, t, 0.35, pan=0.05)
                m.add("send", cl, t, 0.25)

    # rolling bass on the three sixteenths after each kick; G for the last beat of every 4th bar
    for i, t in enumerate(np.arange(bass_on, groove_end - 1e-9, spb)):
        note = 31 if (i % 16) == 15 else 33
        for j in (1, 2, 3):
            m.add("music", bass(note, s16 * 0.9), t + j * s16, 0.42)

    # dub stabs on the "and" of beats 2 and 4, chords changing every two bars, into the echo
    for i, t in enumerate(np.arange(stab_on, groove_end - 1e-9, bar)):
        notes = AM9 if (i // 2) % 2 == 0 else FMAJ9
        for off in (1.5, 3.5):
            st = chord(notes, 0.35)
            m.add("music", st, t + off * spb, 0.30)
            m.add("music", echo(st.mean(axis=1), 0.75 * spb), t + off * spb, 0.22)
            m.add("send", st, t + off * spb, 0.15)

    # 1-bit arpeggio while the camera tours
    pattern = (0, 2, 4, 1, 3, 5, 2, 4, 6, 3, 1, 4, 2, 5, 3, 0)
    for i, t in enumerate(np.arange(arp_on, groove_end - 1e-9, s16)):
        note = PENTA[pattern[i % 16]] - (12 if (i // 32) % 2 else 0)
        b = blip(note, s16 * 0.8, 0.03)
        m.add("music", b, t, 0.10, pan=0.4 if i % 2 else -0.4)
        if i % 4 == 2:
            m.add("music", echo(b, 0.75 * spb, 0.4, 4), t, 0.06)

    # pad when the camera is back on the poster; it runs past the end and wraps into the intro
    if groove_end < L.end:
        length = L.end - groove_end + L.intro + 0.3
        p = chord(PAD, length, cutoff=900, attack=0.6, tau=60, detune=7)
        n_out = int(0.3 * SR)
        p[-n_out:] *= np.linspace(1, 0, n_out)[:, None]
        m.add("music", p, groove_end, 0.35)
        m.add("send", p, groove_end, 0.12)

    # screen off, loader, windows opening
    if L.intro:
        m.add("sfx", power_down(0.5), L.intro, 0.55)
        start = L.intro + 0.5
    else:
        start = 0.0
    for i, t in enumerate(np.arange(nxt(start + 0.1, s16), L.desk - 1e-9, s16)):
        m.add("sfx", blip(PENTA[min(i, len(PENTA) - 1)] - 12, 0.04), t, 0.18)
    for t0 in (L.map, L.grid, L.race, L.widget):
        m.add("sfx", glide(76, 88, 0.15), t0, 0.5)

    # stations popping onto the map, quantised to sixteenths: brighter for the 2020s
    st = desk.map_st
    t_map = L.map + desk.d(1.0) + desk.d(4.0) * (np.arange(len(st)) + 1) / len(st)
    era = np.where(st["year"].to_numpy() >= 2020, 0, np.where(st["year"].to_numpy() >= 2000, 1, 2))
    _sonify(m, t_map, era, {2: (69, 0.10), 1: (76, 0.14), 0: (84, 0.26)}, s16, best=min)

    # grid cells filling (ease-out in time), pitch by class
    g = desk.grid_st["cls"].to_numpy()
    p = (np.arange(len(g)) + 1) / len(g)
    t_grid = L.grid + desk.d(0.6) + desk.d(3.5) * (1 - (1 - p) ** (1 / 3))
    keep = g >= 0
    _sonify(m, t_grid[keep], g[keep], {0: (69, 0.10), 1: (72, 0.13), 2: (76, 0.16), 3: (81, 0.22)}, s16, best=max)

    # race squares gliding to their ratios
    for i, row in enumerate(S.race):
        r = row.a / max(row.b, 0.25)
        t0 = L.race + desk.d(0.8 + 0.5 * i)
        m.add("sfx", glide(69, 69 + 6 * np.log2(max(r, 1 / 8)), desk.d(1.6)), t0, 0.35, pan=-0.2 + 0.1 * i)

    # widget counting up
    count_t0, count_d = L.widget + desk.open, desk.d(1.2)
    steps = max(S.widget_n, 1)
    times = sorted({float(nxt(count_t0 + count_d * (1 - (1 - (i + 1) / steps) ** (1 / 3)), s16))
                    for i in range(steps)})
    for t in times:
        m.add("sfx", blip(93, 0.03, 0.01), t, 0.15)

    # camera moves
    for t0, t1 in moving:
        m.add("sfx", whoosh(t1 - t0), t0, 0.25)

    return _master(m, kicks, L.end)


def _sonify(m, times, kinds, voice, s16, best):
    """One blip per sixteenth for a burst of events; the slot sounds like its strongest event."""
    slots = {}
    for t, kind in zip(times, kinds):
        q = float(np.ceil(t / s16 - 1e-9) * s16)
        slots[q] = best(slots.get(q, kind), kind)
    for t, kind in slots.items():
        note, gain = voice[int(kind)]
        m.add("sfx", blip(note, 0.06, 0.025), t, gain, pan=RNG.uniform(-0.5, 0.5))


def _master(m: Mixer, kicks, seconds) -> np.ndarray:
    n = len(m.buses["music"])
    # sidechain: the music ducks under every kick
    duck = np.ones(n)
    for t in kicks:
        i = int(t * SR)
        seg = 1 - 0.55 * np.exp(-_t(min(int(0.3 * SR), n - i)) / 0.09)
        duck[i:i + len(seg)] = np.minimum(duck[i:i + len(seg)], seg)
    music = m.buses["music"] * duck[:, None]
    wet = fftconvolve(m.buses["send"], reverb_ir(), axes=0)[:n] * 0.6
    mix = m.buses["drums"] + music + m.buses["sfx"] * 0.9 + wet
    mix = _filter(mix, "high", 25)
    # wrap the tails round to the start: the last sample flows into the first
    out = mix[:m.n0].copy()
    tail = mix[m.n0:]
    out[:len(tail)] += tail[:m.n0]
    # gentle saturation of a mix normalised to full scale, then -1 dBFS peak
    out = np.tanh(1.2 * out / np.abs(out).max()) / np.tanh(1.2)
    return (out / np.abs(out).max() * 10 ** (-1 / 20)).astype(np.float32)


def write(desk, path: Path) -> Path:
    """The soundtrack as a 48 kHz 16-bit stereo WAV."""
    pcm = (soundtrack(desk) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path
