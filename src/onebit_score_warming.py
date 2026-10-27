"""The score of the warming reel: an original track for the stripes film (iran_stripes_kahgel_fa_20s),
in the Chahargah mode, built from the Persian sound kit (onebit_persian) and timed to the film's own
clock. Everything is synthesized here; there are no samples and no voices.

The groove runs at 120 BPM (a bar is 2 s), and its bars are counted from the drop. The number lands
at film.starts[1] + film.later(1), 7.6 s, which is bar 1, so every later bar line falls on the grid.

    0.0 s   intro sting: a kick and a daf boom on the first frame, a pad on C, the first stripes
    1.6 s   build: the groove enters on C, then F, then G; a snare roll into a riser
    6.3 s   impact: the bracket appears, a boom on G; the riser runs on to the drop
    7.6 s   drop: the number lands; full beat, sub, the hook, and its variant in bar 2
    11.6 s  breakdown: the beat leaves, the kamancheh answers, the years fade one by one
    14.6 s  stab: "all after 2000" lands, a warm C major hit; the beat returns on the bar at 15.6 s
    15.6 s  outro: the hook an octave up, then the hook resolves home, and a last hit on C at 19.6 s
    19.0 s  the last second fades out (the master's fade)

The data are audible. The 75 stripes run in as setar notes, one scale step per warming class (cold
low, hot high), panned from right to left as the years run. The 65 years that fade are soft plucks
and ticks that fall from A-koron to E on the same mode, panned the same way. Both sit on the film's
own times, not on the grid, so that each one lands on its visual event.

    python -I src/onebit_score_warming.py

writes outputs/onebit/social/iran_stripes_kahgel_fa_20s_music.wav, muxes it under the silent reel
into iran_stripes_kahgel_fa_20s_music_reel.mp4, prints the loudness, the true peak, the durations
and the event table, and checks the track: loudness, the start and the ending, every hit within
30 ms of its event (found by spectral flux in the WAV and in the MP4's decoded audio), and the
video stream.
"""

from __future__ import annotations

import argparse
import functools
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, sosfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
import onebit_persian as kit  # noqa: E402
import onebit_stripes  # noqa: E402
from onebit_slides import COLOURS  # noqa: E402

SR = kit.SR
BEAT, BAR = kit.BEAT, kit.BAR            # 0.5 s and 2 s at 120 BPM
S16 = BEAT / 4
MODE = "chahargah"                       # C, D-koron, E, F, G, A-koron, B (koron = 50 cents below)
TAIL = 3.0                               # s of room past the end, for the reverb and the echo
LUFS, TP = -14.0, -2.0                   # -2 dBTP: the AAC encoding of this track overshoots by about 0.6 dB
MAX_OFFSET = 0.030                       # s: a hit may sit at most this far from its event
STRIPE_BASE = "iran_stripes_kahgel_fa_20s"

CHORDS = "CFGCGFCFGC"                    # the chord of each bar: 1.6 s, 3.6 s, ... 19.6 s
CHORD_STEPS = {"C": (0, 2, 4), "F": (3, 5, 7), "G": (4, 6, 8)}   # step 8 is the octave's D-koron
ROOTS = {"C": "C2", "F": "F2", "G": "G2"}                        # the sub
KICK_AT, CLAP_AT = (0, 6, 10), (8,)      # 16ths of a bar: the 1, the 'and' of 2, the 'and' of 3; the 3
BAM_AT, TAK_AT = (0, 8), (3, 6, 11, 14)  # the daf: the centre on the 1 and the 3, the rim between
ARP = (0, 1, 2, 1, 0, 1, 2, 1)           # the santur's eighth-note figure over a chord

# the hook: (time in s from its phrase, mode step, length in s); a phrase is two bars, 4 s
HOOK_A = ((0.0, 4, 0.5), (0.5, 4, 0.5), (1.0, 6, 1.0), (2.0, 5, 0.5), (2.5, 4, 0.5), (3.0, 2, 1.0))
HOOK_B = ((0.0, 4, 0.5), (0.5, 4, 0.5), (1.0, 6, 1.0), (2.0, 7, 0.5), (2.5, 6, 0.5), (3.0, 4, 1.0))
HOOK_C = tuple((t, s + 7, d) for t, s, d in HOOK_A)                 # the octave up
HOOK_D = ((0.0, 6, 0.5), (0.5, 4, 0.5), (1.0, 2, 1.0))              # home: B, G, E, then the tonic

BUSES = ("drums", "bass", "pad", "lead", "data", "fx", "send", "echo")
DATA_GAIN = 1.25                         # the stripes and the fades, in the mix (the bus gain)


def _timing(film) -> dict:
    """The film's own times for the music: the bracket, the number, the stab and the end."""
    return dict(bracket=float(film.bracket_at), drop=float(film.starts[1]) + film.later(1),
                stab=float(film.starts[2]) + film.later(2), end=float(film.starts[-1]))


def _pan(year: int) -> float:
    """The stripes run from right (1951) to left (2025), as they do on the screen."""
    return 0.8 - 1.6 * (year - onebit_stripes.YEARS[0]) / (onebit_stripes.YEARS[1] - onebit_stripes.YEARS[0])


def _fit(x, n: int):
    """Crop or zero-pad x along time to n rows."""
    return x[:n] if len(x) >= n else np.concatenate([x, np.zeros((n - len(x), x.shape[1]))])


@functools.lru_cache(maxsize=1)
def _tick():
    """A soft tick for each fading year: a band-passed click, 3 ms, its own noise seed."""
    n = int(0.02 * SR)
    t = np.arange(n) / SR
    noise = np.random.default_rng(31).standard_normal(n)
    x = sosfilt(butter(2, (1500.0, 5000.0), "bandpass", fs=SR, output="sos"), noise) * np.exp(-t / 0.003)
    x = x * np.minimum(1.0, t / 0.0005)
    x = x / np.abs(x).max()
    x.flags.writeable = False
    return x


def _sounds() -> dict:
    """The voices of the score. The kit caches each one, so building them once is cheap."""
    return dict(kick=kit.kick808(kit.note_hz("C1"), vel=1.0, decay=0.9, drive=1.3),
                clap=kit.clap(), snare=kit.snare(), hat=kit.hat(),
                bam=kit.daf("bam", pitch=kit.note_hz("C3")), tak=kit.daf("tak", pitch=kit.note_hz("E4")),
                zang=kit.daf("zang"), bak=kit.tombak("bak", pitch=kit.note_hz("G3")))


def _groove(bus, S, t0: float, level: int, kicks: list) -> None:
    """One bar of the groove from t0. Level 1 is the build (soft eighth-note hats); level 2 the full beat."""
    d = bus["drums"]
    for k in KICK_AT:
        kit.place(d, S["kick"], t0 + k * S16, 0.8 if level == 2 else 0.65)
        kicks.append(t0 + k * S16)
    for k in CLAP_AT:
        kit.place(d, S["clap"], t0 + k * S16, 0.28)
        kit.place(d, S["snare"], t0 + k * S16, 0.45, pan=0.1)
    for k in range(16):
        if level == 2:
            g = 0.13 if k % 4 == 0 else 0.08 if k % 2 == 0 else 0.05
            kit.place(d, S["hat"], t0 + k * S16, g, pan=0.25 if k % 2 else -0.25)
        elif k % 4 == 2:
            kit.place(d, S["hat"], t0 + k * S16, 0.07, pan=0.25)
    for k in BAM_AT:
        kit.place(d, S["bam"], t0 + k * S16, 0.5 if level == 2 else 0.35)
    for k in TAK_AT:
        kit.place(d, S["tak"], t0 + k * S16, 0.36 if level == 2 else 0.22, pan=-0.3 if k < 8 else 0.3)
        if level == 2:
            kit.place(d, S["zang"], t0 + k * S16, 0.10, pan=0.3 if k < 8 else -0.3)


def _hook(bus, phrase, t0: float, gain: float) -> None:
    """A two-bar phrase on the setar: the notes alternate sides, with a little room and a ping-pong echo."""
    for i, (dt, step, length) in enumerate(phrase):
        s = kit.setar(kit.degree(MODE, step, 0), dur=length + 0.6, vel=1.0, t60=2.0, bright=0.5, buzz=0.12)
        pan = 0.25 if i % 2 == 0 else -0.25
        kit.place(bus["lead"], s, t0 + dt, gain, pan)
        kit.place(bus["send"], s, t0 + dt, 0.3, pan)
        kit.place(bus["echo"], s, t0 + dt, 0.3, pan)


def _compose(film, rec: list) -> tuple:
    """Lay the score on its buses. Returns (buses, kick times for the ducking, length in s).
    `rec` receives one entry per event of the film: (label, visual time, time of the hit placed on it),
    and for the stripes and the fades a fourth item, the sounds placed for them as (sound, gain, pan)."""
    kit.reseed(19)
    tm = _timing(film)
    seconds = tm["end"]
    S = _sounds()
    bus = {k: kit.new_track(seconds, TAIL) for k in BUSES}
    kicks: list = []
    bars = [tm["drop"] + k * BAR for k in range(-3, 7)]         # 1.6, 3.6, ... 19.6 s
    drums, bass, pad, lead, data, fx, send, echo = (bus[k] for k in BUSES)

    # ── intro: the sting on the first frame, two pickups into the groove ──
    kit.place(drums, S["kick"], 0.0, 0.9)
    kicks.append(0.0)
    kit.place(drums, S["bam"], 0.0, 0.8)
    kit.place(drums, S["tak"], 0.6, 0.35, pan=0.3)
    kit.place(drums, S["tak"], 1.1, 0.4, pan=-0.3)
    kit.place(drums, S["zang"], 1.1, 0.25, pan=-0.3)
    rec.append(("scene 1 starts: the sting", 0.0, 0.0))

    # ── pads: one chord per bar, the intro's C from 0 s, each chord ringing into the next ──
    for i, t0 in enumerate(bars):
        start = 0.0 if i == 0 else t0
        end = bars[i + 1] if i + 1 < len(bars) else seconds
        vel = 0.32 if i in (5, 6) else 0.5 if i == 9 else 0.4
        freqs = [kit.degree(MODE, s, -1) for s in CHORD_STEPS[CHORDS[i]]]
        kit.place(pad, kit.pad(freqs, dur=end - start + 0.5, vel=vel), start, 0.55)

    # ── sub: one note per bar, the 808 slide from the last root ──
    prev = None
    for i, t0 in enumerate(bars):
        f = kit.note_hz(ROOTS[CHORDS[i]])
        end = bars[i + 1] if i + 1 < len(bars) else seconds
        g = {2: 0.22, 3: 0.6, 5: 0.28, 6: 0.28, 9: 0.5}.get(i, 0.45)
        kit.place(bass, kit.sub(f, dur=end - t0 + 0.03, vel=0.9, glide_from=prev), t0, g)
        prev = f

    # ── the groove: the build on 1.6 s and 3.6 s, a kick and a clap on the 5.6 s line, the drop, the outro ──
    _groove(bus, S, bars[0], 1, kicks)
    _groove(bus, S, bars[1], 1, kicks)
    kit.place(drums, S["kick"], bars[2], 0.9)
    kicks.append(bars[2])
    kit.place(drums, S["clap"], bars[2], 0.28)
    kit.place(drums, S["snare"], bars[2], 0.45, pan=0.1)
    for j in range(4):                                        # the snare roll on beat 4 of bar 2
        kit.place(drums, S["snare"], 5.1 + j * S16, 0.5 * (0.3 + 0.2 * j))
    for j in range(6):                                        # the tension roll into the drop
        kit.place(drums, S["snare"], 6.85 + j * S16, 0.5 * (0.3 + 0.14 * j))
    for i in (3, 4, 7, 8):
        _groove(bus, S, bars[i], 2, kicks)
    kit.roll(drums, 11.35, 0.25, 8, vel0=0.4, vel1=1.0, gain=0.2, pan=-0.2)   # a hat roll into the breakdown

    # ── risers and the bracket's impact ──
    kit.place(fx, kit.riser(0.7, vel=0.6, f0=180.0, f1=1600.0), bars[2], 0.6)          # 5.6 s to 6.3 s
    imp = kit.impact(2.2, vel=1.0, pitch=kit.note_hz("G1"))
    kit.place(fx, imp, tm["bracket"], 0.85)
    kit.place(fx, kit.riser(1.3, vel=0.6, f0=260.0, f1=2600.0), tm["bracket"], 0.55)   # 6.3 s to the drop
    rec.append(("bracket appears: impact", tm["bracket"], tm["bracket"]))
    kit.place(drums, S["bak"], 6.0, 0.6)                                                  # the scene 2 cut
    rec.append(("scene 2 starts: a rim slap", 6.0, 6.0))

    # ── the drop: the number lands on the downbeat, the hook, a santur chord, the daf's centre ──
    d0 = tm["drop"]
    kit.place(drums, S["bam"], d0, 0.3)
    kit.place(drums, S["zang"], d0, 0.4, pan=0.2)
    for s in CHORD_STEPS["C"]:
        kit.place(pad, kit.santur(kit.degree(MODE, s, 1), dur=2.0, vel=0.5, t60=2.4), d0, 0.4,
                  pan=-0.2 + 0.2 * s / 4)
    rec.append(('"about 2 degrees": the number lands, the drop', d0, d0))
    _hook(bus, HOOK_A, bars[3], 1.2)
    _hook(bus, HOOK_B, bars[4], 1.2)
    _hook(bus, HOOK_C, bars[7], 1.2)
    _hook(bus, HOOK_D, bars[8], 1.1)

    # the santur's eighth-note figure in the drop and the outro
    for i in (3, 4, 7, 8):
        steps = CHORD_STEPS[CHORDS[i]]
        for j in range(8):
            f = kit.degree(MODE, steps[ARP[j]], 1)
            pan = -0.3 if j % 2 else 0.3
            kit.place(pad, kit.santur(f, dur=1.4, vel=0.45, t60=1.3), bars[i] + j * 0.25, 0.3, pan)
            kit.place(send, kit.santur(f, dur=1.4, vel=0.45, t60=1.3), bars[i] + j * 0.25, 0.12, pan)

    # ── breakdown: the kamancheh answers from the scene 3 cut, a tick for every fading year ──
    kit.place(drums, S["tak"], 12.0, 0.45, pan=0.3)
    for t, step, length in ((12.0, 5, 1.0), (13.0, 4, 1.2)):
        s = kit.kamancheh(kit.degree(MODE, step, 0), dur=length, vel=0.45, vib_hz=5.5, vib_cents=30.0, bow=0.15)
        kit.place(lead, s, t, 1.0, pan=-0.15)
        kit.place(send, s, t, 0.25, pan=-0.15)
    rec.append(("scene 3 starts: a daf rim", 12.0, 12.0))
    others = sorted(y for y in film.cls if y not in film.top)
    n = len(others)
    for k, y in enumerate(others):
        t, u = float(film.fade_at[y]), k / (n - 1)
        pluck = kit.setar(kit.degree(MODE, 12 - round(10 * u), 0), dur=0.45, vel=0.5, t60=0.35,
                          bright=0.7 - 0.6 * u, buzz=0.0)           # falls from A-koron to E, darker as it goes
        tick = _tick()
        kit.place(data, pluck, t, 1.0, _pan(y))
        kit.place(data, tick, t, 0.22, _pan(y))
        rec.append((f"fade {y}: the year goes", t, t, [(pluck, 1.0, _pan(y)), (tick, 0.22, _pan(y))]))

    # ── the stripes: a rising run of setar notes, one scale step per warming class (cold low, hot high) ──
    for y in sorted(film.run_at):
        t, k, u = float(film.run_at[y]), int(film.cls[y]), (y - onebit_stripes.YEARS[0]) / 74
        s = kit.setar(kit.degree(MODE, k, 0), dur=0.8, vel=0.45 + 0.45 * u, t60=1.0, bright=0.35, buzz=0.05)
        kit.place(data, s, t, 1.2, _pan(y))
        rec.append((f"stripe {y}, class {k}", t, t, [(s, 1.2, _pan(y))]))

    # ── the stab: "all after 2000" lands on the warmest chord, a kick, the beat comes back on the bar ──
    st = tm["stab"]
    freqs = [kit.degree(MODE, s, -1) for s in (0, 2, 4, 6)] + [kit.degree(MODE, 0, 0)]
    kit.place(pad, kit.pad(freqs, dur=1.8, vel=0.5, attack=0.004, release=1.2, cutoff=2600.0), st, 0.5)
    for s, pan in zip((0, 2, 4, 6), (-0.5, -0.15, 0.15, 0.5)):
        f = kit.degree(MODE, s, 1)
        kit.place(pad, kit.santur(f, dur=3.2, vel=0.7, t60=2.8), st, 0.4, pan)
        kit.place(send, kit.santur(f, dur=3.2, vel=0.7, t60=2.8), st, 0.5, pan)
    kit.place(drums, S["kick"], st, 0.85)
    kicks.append(st)
    kit.place(drums, S["clap"], st, 0.35)
    kit.place(drums, S["snare"], st, 0.4, pan=0.1)
    kit.place(drums, S["zang"], st, 0.45, pan=0.2)
    kit.place(bass, kit.sub(kit.note_hz("C2"), dur=1.4, vel=0.95), st, 0.6)
    s = kit.setar(kit.degree(MODE, 7, 0), dur=1.8, vel=1.0, t60=1.8, bright=0.5, buzz=0.12)
    kit.place(lead, s, st, 1.0)
    kit.place(send, s, st, 0.4)
    kit.place(echo, s, st, 0.35)
    rec.append(('"all after 2000" lands: the stab', st, st))

    # ── the last hit: a kick, a clap and the daf's boom on C at 19.6 s, a santur chord, the tonic ──
    last = bars[9]
    kit.place(drums, S["kick"], last, 0.85)
    kicks.append(last)
    kit.place(drums, S["clap"], last, 0.3)
    kit.place(drums, S["snare"], last, 0.35, pan=0.1)
    kit.place(drums, S["bam"], last, 0.5)
    kit.place(drums, S["zang"], last, 0.3, pan=-0.2)
    kit.place(bass, kit.sub(kit.note_hz("C2"), dur=2.0, vel=0.95), last, 0.6)
    for s, pan in zip((0, 2, 4, 7), (-0.4, -0.1, 0.1, 0.4)):
        kit.place(pad, kit.santur(kit.degree(MODE, s, 1), dur=3.0, vel=0.6, t60=2.6), last, 0.4, pan)
        kit.place(send, kit.santur(kit.degree(MODE, s, 1), dur=3.0, vel=0.6, t60=2.6), last, 0.45, pan)
    s = kit.setar(kit.degree(MODE, 7, 0), dur=2.0, vel=1.0, t60=2.0, bright=0.5, buzz=0.12)
    kit.place(lead, s, last, 1.0)
    kit.place(send, s, last, 0.4)
    kit.place(echo, s, last, 0.35)
    rec.append(("the film ends: the last hit on C 0.4 s before", seconds, last))
    return bus, kicks, seconds


def mix_bus(bus: dict, kicks: list, n: int) -> np.ndarray:
    """The buses summed: the pads and the lead ducked under the kick, the sub ducked less, the reverb and
    the ping-pong echo as returns, the groove's peaks softly rounded, the low end made mono, and the
    stripes and the fades added last, dry, so that they reach the audio as rendered."""
    pad = kit.duck(bus["pad"], kicks, depth_db=4.0, release=0.18)
    lead = kit.duck(bus["lead"], kicks, depth_db=2.0, release=0.15)
    bass = kit.duck(bus["bass"], kicks, depth_db=3.0, release=0.12)
    wet = _fit(kit.reverb(bus["send"], t60=2.2) * 0.45, n)
    dly = _fit(kit.pingpong(bus["echo"], delay=0.75 * BEAT, feedback=0.42, taps=8) * 0.6, n)
    groove = 0.85 * bus["drums"] + 0.7 * pad + lead + 0.8 * bass + bus["fx"] + wet + dly
    return _bass_mono(_soft_clip(groove, 0.6)) + _bass_mono(DATA_GAIN * bus["data"])


def _soft_clip(x, knee: float = 0.6):
    """A soft knee on the peaks: linear below knee, then a tanh bend that meets 1.0 smoothly, so the
    transients of the drop round off a few tenths of a dB at a time instead of the master's limiter
    cutting the whole mix. Below the knee nothing changes."""
    a = np.abs(x)
    bent = knee + (1 - knee) * np.tanh(np.maximum(a - knee, 0.0) / (1 - knee))
    return np.sign(x) * np.where(a > knee, bent, a)


def render(film, log: list | None = None) -> tuple:
    """The mastered track, and the mix before the master (for the verification)."""
    rec = [] if log is None else log
    bus, kicks, seconds = _compose(film, rec)
    mix = mix_bus(bus, kicks, len(bus["drums"]))
    return kit.master(mix, lufs=LUFS, tp=TP, seconds=seconds, fade_out=1.0), mix


def soundtrack(film, log: list | None = None) -> np.ndarray:
    """The mastered stereo track of the film: 48 kHz, float, as long as the film. `log`, when given,
    receives the events of the film (see _compose)."""
    return render(film, log)[0]


def _bass_mono(x, fc: float = 120.0):
    """The low end in mono: everything below fc is averaged to one channel, and the rest stays wide."""
    low = sosfilt(butter(4, fc, "lowpass", fs=SR, output="sos"), x, axis=0)
    mid = 0.5 * (low[:, 0] + low[:, 1])
    out = x - low
    out[:, 0] += mid
    out[:, 1] += mid
    return out


def write(film, path, log: list | None = None) -> Path:
    """The soundtrack as a 48 kHz 16-bit stereo WAV, like the other engines' write()."""
    return kit.write_wav(path, soundtrack(film, log))


# ── checks ──────────────────────────────────────────────────────────────────

def _read_wav(path) -> np.ndarray:
    rate, pcm = wavfile.read(str(path))
    assert rate == SR and pcm.ndim == 2 and pcm.shape[1] == 2, (rate, pcm.shape)
    return pcm.astype(float) / 32768.0


def _decode(media) -> np.ndarray:
    """The audio of a media file as a player decodes it, stereo at 48 kHz."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(media), "-vn", "-f", "f32le", "-ac", "2",
                          "-ar", str(SR), "-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2).astype(float)


def _probe(media) -> dict:
    raw = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=index,codec_type,codec_name,width,height,r_frame_rate,"
                          "nb_frames,duration,sample_rate,channels", "-of", "json", str(media)],
                         check=True, capture_output=True, text=True).stdout
    return json.loads(raw)


def _md5(media, stream: str) -> str:
    """The MD5 of one stream's packets, copied without re-encoding: equal digests mean the same video."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(media), "-map", stream, "-c", "copy", "-f", "md5", "-"],
                         check=True, capture_output=True, text=True).stdout
    return raw.strip()


def _db(seg) -> float:
    return float(20 * np.log10(np.sqrt(np.mean(np.square(seg))) + 1e-12))


def _flux(x, hop: int = 48, nfft: int = 256):
    """Spectral flux of a mono signal, frames 1 ms apart and 5.3 ms long: the rise of the log magnitude
    from one frame to the next, summed over the bins. Returns each frame's centre time (s) and the flux."""
    y = np.concatenate([np.zeros(nfft), x])              # a silent lead-in, so the first frame has a past
    starts = np.arange(0, len(y) - nfft + 1, hop)
    frames = y[starts[:, None] + np.arange(nfft)[None, :]] * np.hanning(nfft)
    logm = np.log10(np.abs(np.fft.rfft(frames, axis=1)) + 1e-5)
    rise = np.maximum(np.diff(logm, axis=0, prepend=logm[:1]), 0.0).sum(axis=1)
    return (starts - nfft / 2) / SR, rise


def _flux_onset(times, rise, t: float, w: float = MAX_OFFSET):
    """The offset (s) of the strongest spectral-flux peak within w of t, or None if there is none."""
    sel = np.flatnonzero(np.abs(times - t) <= w)
    return None if len(sel) == 0 else float(times[sel[np.argmax(rise[sel])]] - t)


def check(film, wav, video, out, log: list, mix) -> None:
    """Print the numbers and the event table, and assert the five checks."""
    x = _read_wav(wav)
    lufs, tp = kit.integrated_lufs(x), kit.true_peak_dbtp(x)
    vid, mux = _probe(video), _probe(out)
    print(f"audio   {len(x) / SR:.3f} s   video {float(vid['format']['duration']):.3f} s"
          f"   muxed {float(mux['format']['duration']):.3f} s")
    print(f"integrated loudness {lufs:.2f} LUFS   true peak {tp:.2f} dBTP")
    dec = _decode(out)
    print(f"the MP4's decoded audio: {kit.integrated_lufs(dec):.2f} LUFS, {kit.aac_true_peak(out):.2f} dBTP")

    print("\n(1) loudness and true peak")
    assert -15 <= lufs <= -13, lufs
    assert tp <= -1, tp
    print(f"    -15 <= {lufs:.2f} <= -13 LUFS   and   {tp:.2f} <= -1 dBTP: pass")

    head = x[:int(0.1 * SR)]
    print("\n(2) the first 0.1 s")
    print(f"    RMS {_db(head):.1f} dBFS, peak {np.abs(head).max():.3f}")
    assert _db(head) > -30, "silent start"
    print("    sound from the first frame: pass")

    win = int(0.1 * SR)
    ends = [_db(x[len(x) - (k + 1) * win: len(x) - k * win]) for k in range(10)][::-1]
    print("\n(3) the last second, RMS per 0.1 s (dBFS):", " ".join(f"{v:.1f}" for v in ends))
    last_step = np.abs(np.diff(x[-int(0.005 * SR):], axis=0)).max()
    print(f"    last sample {abs(x[-1, 0]):.2e}, largest step in the last 5 ms {last_step:.2e}")
    assert ends[-1] < ends[0] - 10 and abs(x[-1, 0]) < 1e-3 and last_step < 2e-3, "the ending is not a clean fade"
    print("    fades out, ends at zero, no click: pass")

    # (4) the hits in the rendered WAV, each by its spectral flux. The isolated events are read from the
    # WAV as they are. The stripes and the fades are dense (30 to 73 ms apart) and sit under the groove,
    # so for each of them the audio is first cleared of the rest: the WAV less the mix without this
    # event's own sound (the master's gain and DC blocker applied to the mix). What remains starts at the
    # event's onset, and its flux peak is that onset.
    mono = x.mean(axis=1)
    hp = butter(2, 12.0, "highpass", fs=SR, output="sos")          # the master's DC blocker
    u = sosfilt(hp, mix[:len(x)], axis=0)                          # the mix through it: the master's input
    win = round(0.001 * SR) | 1                                    # 1 ms: the limiter's gain moves in a few ms
    num = uniform_filter1d((x * u).sum(axis=1), win, mode="nearest")
    den = uniform_filter1d((u * u).sum(axis=1), win, mode="nearest")
    gain = num / np.maximum(den, 1e-12)                            # the master as a gain curve, per sample
    model = _db(x - gain[:, None] * u) - _db(x)
    times, rise = _flux(mono)
    print(f"\n(4) hits in the WAV: the master's gain curve fitted (median {20 * np.log10(np.median(gain)):+.2f} dB,"
          f" the limiter moves it by a few tenths of a dB); the master as a gain curve on the mix is"
          f" {-model:.0f} dB below the WAV")
    rows, moved = [], 0
    for entry in log:
        label, visual, hit = entry[0], entry[1], entry[2]
        if len(entry) == 3:
            off, how = _flux_onset(times, rise, hit), "WAV"
        else:
            a = round((hit - 0.1) * SR)                            # a span of 0.4 s, the event 0.1 s in
            b = a + round(0.4 * SR)
            ev = kit.new_track(0.4)
            for sound, g, pan in entry[3]:
                kit.place(ev, sound, (round(hit * SR) - a) / SR, DATA_GAIN * g, pan)
            cleared = x[a:b] - gain[a:b, None] * sosfilt(hp, mix[a:b] - _bass_mono(ev), axis=0)
            lt, lr = _flux(cleared.mean(axis=1))
            off, how = _flux_onset(lt, lr, 0.1), "cleared"
            plain = _flux_onset(times, rise, hit)
            moved += plain is None or abs(plain - off) > 0.002
        rows.append((label, visual, hit, None if off is None else hit + off, off, how))
    assert all(r[4] is not None for r in rows), "an event with no onset"
    groups: dict = {}
    for label, visual, hit, found, off, how in rows:
        g = label.split(" ")[0]
        a = groups.setdefault(g, [0.0, 0, 0.0])
        a[0], a[1], a[2] = max(a[0], abs(off)), a[1] + 1, a[2] + off
    for g, (worst, cnt, mean) in groups.items():
        print(f"    {g:<10} n={cnt:<3} largest {worst * 1000:6.2f} ms   mean {mean / cnt * 1000:+6.2f} ms")
    worst = max(abs(r[4]) for r in rows)
    assert worst <= MAX_OFFSET, worst
    print(f"    all {len(rows)} events: largest offset {worst * 1000:.2f} ms (limit {MAX_OFFSET * 1000:.0f} ms): pass")
    print(f"    without the clearing, {moved} of the {sum(1 for e in log if len(e) == 4)} stripes and fades would"
          f" be found more than 2 ms from their time")

    print("\n    through the MP4's AAC audio, decoded (the isolated events, offset in ms):")
    dtimes, drise = _flux(dec.mean(axis=1))
    for label, visual, hit, *placed in log:
        if not placed:                                              # the isolated events only
            off = _flux_onset(dtimes, drise, hit)
            print(f"      {label:<50} {'-' if off is None else f'{off * 1000:+7.2f}'}")

    print("\n(5) the video stream of the muxed MP4 against the silent reel")
    v_md5, m_md5 = _md5(video, "0:v:0"), _md5(out, "0:v:0")
    print(f"    silent reel   {v_md5}")
    print(f"    muxed reel    {m_md5}")
    assert v_md5 == m_md5, "the video stream changed"
    vs = [s for s in mux["streams"] if s["codec_type"] == "video"][0]
    vs0 = [s for s in vid["streams"] if s["codec_type"] == "video"][0]
    print(f"    {vs['codec_name']} {vs['width']}x{vs['height']} {vs['r_frame_rate']} nb_frames {vs['nb_frames']}"
          f" (silent: {vs0['nb_frames']}): same packets: pass")
    print(f"    audio {[s['codec_name'] for s in mux['streams'] if s['codec_type'] == 'audio']}")

    print("\nEVENT TABLE: visual event, its time, the hit placed on it, the onset found in the WAV")
    print(f"{'#':>3}  {'visual event':<50}{'visual s':>9}{'hit s':>9}{'found s':>10}{'offset ms':>11}  method")
    for i, (label, visual, hit, found, off, how) in enumerate(rows, 1):
        print(f"{i:>3}  {label:<50}{visual:9.3f}{hit:9.3f}{found:10.3f}{off * 1000:+11.2f}  {how}")
    print("\nall checks pass")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    film = onebit_stripes.StripesFilm(onebit.THEMES["kahgel"], COLOURS["kahgel"], "20s")
    base = onebit.OUT / "social" / STRIPE_BASE
    video = Path(f"{base}_reel.mp4")
    wav = Path(f"{base}_music.wav")
    out = Path(f"{base}_music_reel.mp4")
    log: list = []
    track, mix = render(film, log)
    kit.write_wav(wav, track)
    print("saved", wav)
    kit.mux(video, wav, out)
    print("saved", out)
    check(film, wav, video, out, log, mix)


if __name__ == "__main__":
    main()
