"""The score of the winter NO2 reel (air_tehran_fa, 24 s): an original track built from the Persian sound kit
(onebit_persian, the Shur set) and timed to the film's own clock. Everything is synthesized here: no samples,
no voices.

The counter is the music's data. The film shows, for each month of the dial, the Tehran-Karaj box's NO2 as a
multiple of the summer reference (film.ratio). A sustained note (the drone) follows it: its pitch is the counter
on the seven steps of Shur, from the summer's D3 (step 0, x1.0) up to step 6 at x3.4, the top of the scale. One
soft tick sounds at each month of the dial, and the drone's pitch changes at the same instant. The drone's
brightness falls with the counter: its upper partials are taken away as the winter arrives, so the sound darkens
with the air.

    0.00 s           the drone on step 6: the winter's pitch, as the picture opens
    1.00 s           the reset: the drone falls to step 0 (the summer reference) and one soft tick
    1.50-9.96 s      the dial, November 2025 to October 2026 at 1.3 months a second: a tick per month
                     (1.50, 2.27, ... 9.96 s), the drone's pitch on that month's step
    9.96 s           the turn back to the winter: the pad of D, F, A (dark, at the low octave) swells in
                     through 1.5 s, the drone to step 6
    11.00 s          the first line of the winter's reason: a santur chord, D, F, A
    16.00 s          the second line (what this is not): a santur chord on E-koron and G
    21.00 s          the open ending: A and E-koron (steps 4 and 1), no tonic; the master's fade takes the tails
                     to 24 s

Mix: -14 LUFS integrated, true peak -1.5 dBTP in the WAV. The top octave (above 12 kHz) is taken out before the
master (the AAC overshoot), and the bass below 120 Hz is one channel in the spectrum (mono), as in the Karaj score.

    python -I src/onebit_score_air.py

writes outputs/onebit/social/air_tehran_fa_music.wav and muxes it under the silent reel into
air_tehran_fa_music_reel.mp4 (the silent reel is not rewritten). The silent reel must be newer than
src/onebit_air.py: render the film first with python -I src/onebit_air.py. The script prints the loudness and
the true peak of the WAV and of the MP4's decoded audio, the drone's pitch against the counter, the side against
the mid below each frequency, the onsets of every event, and the video stream against the silent reel.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter, sosfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import air  # noqa: E402
import onebit  # noqa: E402
import onebit_air  # noqa: E402
import onebit_persian as kit  # noqa: E402

SR = kit.SR
MODE = "shur"                                   # the dastgah of the score: the Shur set (koron second, minor third)
TONIC = kit.note_hz("D3")                       # step 0 of the drone: the summer reference
STEPS = 6                                       # the counter on steps 0-6 of Shur, from x1.0 to x3.4
RMAX = 3.4                                      # the counter's top on the scale (the scale's last step)
GLIDE = 0.12                                    # s: the drone's glide between steps (one-pole time constant)
TAIL = 3.0                                      # s of room past the end, for the reverb and the echo
AIR = 12000.0                                   # Hz: above this the mix has no content (the AAC overshoot)
BASS = 120.0                                    # Hz: below this the two channels are one
MAX_OFFSET = 0.030                              # s: a hit may sit at most this far from its event
BASE = "air_tehran_fa"
SEED = 41
ACCENTS = {"why": (onebit_air.WHY_AT, ((0, 0), (2, 0), (4, 0))),        # santur: D, F, A
           "pm": (onebit_air.PM_AT, ((1, 0), (3, 0))),                  # santur: E-koron, G
           "end": (21.0, ((4, 0), (1, 0)))}                              # santur: A, E-koron (open)
LUFS, TP = -14.0, -1.5                          # -1.5 dBTP: the decoded AAC stays under -1 once the top octave is cut


def step_of(ratio: float) -> int:
    """The counter's step: x1.0 is step 0, RMAX is the top step."""
    return int(round(min(max((ratio - 1.0) / (RMAX - 1.0), 0.0), 1.0) * STEPS))


def freq_of(step: int, octave: int = 0) -> float:
    return kit.degree(MODE, step, octave, tonic_hz=TONIC)


def timing(film) -> dict:
    """The film's clock, read from the film: the reset, the twelve month ticks, the turn and the end."""
    ticks = [onebit_air.DIAL_START + k / onebit_air.RATE for k in range(len(onebit_air.MONTHS))]
    tm = dict(reset=onebit_air.RESET, ticks=ticks, turn=film.dial_end, end=float(film.L.end),
              months=list(onebit_air.MONTHS))
    assert abs(tm["ticks"][-1] - tm["turn"]) < 1e-9 and tm["turn"] + onebit_air.TURN < 11.0, tm
    assert tm["end"] == 24.0 and ACCENTS["why"][0] > tm["turn"] + 1.0, tm
    return tm


def counter_steps(film, tm) -> list:
    """(time, step) of the drone: the start on the winter, the reset, each month's step, the turn to the winter."""
    winter = step_of(film.winter)
    out = [(0.0, winter), (tm["reset"], step_of(1.0))]          # the reset: the summer reference, x1.0
    out += [(t, step_of(film.ratio[ym])) for t, ym in zip(tm["ticks"], tm["months"])]
    out += [(tm["turn"], winter)]
    return out


def counter_level(film, tm, t: np.ndarray) -> np.ndarray:
    """The counter as a share of the way to winter (0 summer, 1 winter), per sample: the brightness of the drone."""
    tt, vals = [0.0, tm["reset"]], [film.winter, 1.0]
    for t_k, ym in zip(tm["ticks"], tm["months"]):
        tt.append(t_k)
        vals.append(film.ratio[ym])
    tt.append(tm["turn"] + onebit_air.TURN)
    vals.append(film.winter)
    level = np.interp(t, tt, vals)
    return np.clip((level - 1.0) / (film.winter - 1.0), 0.0, 1.0)


def drone(film, tm, n: int) -> tuple:
    """The sustained note: its frequency (Hz, per sample, after the glide) and the stereo-less track."""
    t = np.arange(n) / SR
    keys = counter_steps(film, tm)
    target = np.empty(n)
    for k, (t0, step) in enumerate(keys):
        t1 = keys[k + 1][0] if k + 1 < len(keys) else np.inf
        target[(t >= t0) & (t < t1)] = freq_of(step)
    a = math.exp(-1.0 / (SR * GLIDE))
    freq = lfilter([1.0 - a], [1.0, -a], target)            # one-pole glide to each step
    phase = 2 * np.pi * np.cumsum(freq) / SR
    level = counter_level(film, tm, t)
    x = np.zeros(n)
    for h in range(1, 6):
        weight = (1.0 / h) * (1.0 if h == 1 else 1.0 - 0.7 * level)     # the upper partials go as winter comes
        x += weight * np.sin(h * phase)
    lp = butter(2, 2200.0, "lowpass", fs=SR, output="sos")
    x = sosfilt(lp, x)
    attack = np.minimum(1.0, t / 0.002)
    end_fade = np.minimum(1.0, (t[-1] - t) / 0.5)
    return 0.22 * x * attack * end_fade, freq


def _tick() -> np.ndarray:
    """A soft tick: a band-passed click of 3 ms, with its own noise seed (as the Karaj score)."""
    n = int(0.02 * SR)
    t = np.arange(n) / SR
    noise = np.random.default_rng(31).standard_normal(n)
    x = sosfilt(butter(2, (1500.0, 5000.0), "bandpass", fs=SR, output="sos"), noise) * np.exp(-t / 0.003)
    x = x * np.minimum(1.0, t / 0.0005)
    return x / np.abs(x).max()


def _fit(x, n: int):
    return x[:n] if len(x) >= n else np.concatenate([x, np.zeros((n - len(x),) + x.shape[1:])])


def _air_cut(x, fc: float = AIR) -> np.ndarray:
    """The top octave removed, exactly, in the spectrum. Zero-padded, so the wrap of the FFT does not reach the sound."""
    n = len(x)
    m = n + 2 * SR
    spec = np.fft.rfft(np.asarray(x, float), n=m, axis=0)
    spec[np.fft.rfftfreq(m, 1.0 / SR) > fc] = 0.0
    return np.fft.irfft(spec, n=m, axis=0)[:n]


def _bass_mono(x, fc: float = BASS) -> np.ndarray:
    """The low end in mono, exactly: below fc the two channels are averaged in the spectrum."""
    n = len(x)
    m = n + 2 * SR
    spec = np.fft.rfft(np.asarray(x, float), n=m, axis=0)
    low = np.fft.rfftfreq(m, 1.0 / SR) < fc
    mid = 0.5 * (spec[low, 0] + spec[low, 1])
    spec[low, 0] = mid
    spec[low, 1] = mid
    return np.fft.irfft(spec, n=m, axis=0)[:n]


def compose(film, rec: list):
    """Lay the score on its buses. Returns (buses, the drone's bus alone, the drone's frequency per sample)."""
    kit.reseed(SEED)
    tm = timing(film)
    end = tm["end"]
    bus = {k: kit.new_track(end, TAIL) for k in ("ticks", "drone", "pad", "santur", "fx")}
    n = len(bus["fx"])
    tick = _tick()

    def event(label, t, items):
        for name, sound, gain, pan in items:
            kit.place(bus[name], sound, t, gain, pan)
        rec.append((label, t, t, [(s, g, p) for _, s, g, p in items]))

    d, freq = drone(film, tm, n)
    bus["drone"][:, 0] += d
    bus["drone"][:, 1] += d
    rec.append(("drone: attack", 0.0, 0.0, []))

    # the reset tick, and one soft tick per month of the dial
    event("reset: tick", tm["reset"], [("ticks", tick, 0.36, 0.0)])
    for t, ym in zip(tm["ticks"], tm["months"]):
        event(f"month {ym}: tick", t, [("ticks", tick, 0.36, 0.0)])

    # the winter's pad: D, F, A at the low octave, swelling in at the turn; dark (its cutoff low)
    pad = kit.pad([freq_of(s, -1) for s, _ in ((0, 0), (2, 0), (4, 0))], dur=end - tm["turn"], vel=0.22,
                  width=0.9, cutoff=700.0, attack=1.5, release=1.5)
    kit.place(bus["pad"], pad, tm["turn"], 1.0)

    # the accents: santur chords on the lines of the story, and the open ending
    for key, (t, pairs) in ACCENTS.items():
        items = [("santur", kit.santur(freq_of(s, o) * 2, dur=(3.2 if key != "end" else end - t), vel=0.6,
                                       t60=(2.4 if key != "end" else 3.0)), 0.8, 0.0) for s, o in pairs]
        event(f"{key} accent at {t:.2f} s", t, items)
    return bus, n


def mix_bus(bus: dict, n: int) -> np.ndarray:
    """The buses summed, the top octave cut. The pad has a room; the drone is dry."""
    room = kit.reverb(kit.widen(bus["pad"], 0.3), t60=1.8) * 0.25
    mix = bus["drone"] + bus["pad"] + _fit(room, n) + bus["ticks"] + bus["santur"] + bus["fx"]
    return _air_cut(mix)


def render(film, log: list | None = None):
    """The mastered track (bass in mono) and the mix before the master (for the verification)."""
    rec = [] if log is None else log
    bus, n = compose(film, rec)
    mix = mix_bus(bus, n)
    track = kit.master(mix, lufs=LUFS, tp=TP - 0.5, seconds=float(film.L.end), fade_out=1.0)   # the master settles above its ceiling on this track: 0.5 dB more headroom
    return _bass_mono(track), mix, bus


# ── checks ──────────────────────────────────────────────────────────────────

def _read_wav(path) -> np.ndarray:
    rate, pcm = wavfile.read(str(path))
    assert rate == SR and pcm.ndim == 2 and pcm.shape[1] == 2, (rate, pcm.shape)
    return pcm.astype(float) / 32768.0


def _decode(media) -> np.ndarray:
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
    return subprocess.run(["ffmpeg", "-v", "error", "-i", str(media), "-map", stream, "-c", "copy", "-f", "md5", "-"],
                          check=True, capture_output=True, text=True).stdout.strip()


def _db(seg) -> float:
    return float(20 * np.log10(np.sqrt(np.mean(np.square(seg))) + 1e-12))


def _side_db(x, fc: float) -> float:
    spec = np.fft.rfft(np.asarray(x, float), axis=0)
    low = np.fft.rfftfreq(len(x), 1.0 / SR) < fc
    side = 0.5 * (spec[low, 0] - spec[low, 1])
    mid = 0.5 * (spec[low, 0] + spec[low, 1])
    return float(10 * np.log10(np.sum(np.abs(side) ** 2) / max(np.sum(np.abs(mid) ** 2), 1e-30)))


def _flux(x, hop: int = 48, nfft: int = 256):
    y = np.concatenate([np.zeros(nfft), x])
    starts = np.arange(0, len(y) - nfft + 1, hop)
    frames = y[starts[:, None] + np.arange(nfft)[None, :]] * np.hanning(nfft)
    logm = np.log10(np.abs(np.fft.rfft(frames, axis=1)) + 1e-5)
    rise = np.maximum(np.diff(logm, axis=0, prepend=logm[:1]), 0.0).sum(axis=1)
    return (starts - nfft / 2) / SR, rise


def _flux_onset(times, rise, t: float, w: float = MAX_OFFSET, first: bool = True):
    """The offset (s) of the onset within w of t, or None. The onset is the earliest local peak of the flux that
    reaches half the strongest one in the window (first=False: the strongest peak)."""
    sel = np.flatnonzero(np.abs(times - t) <= w)
    if len(sel) == 0:
        return None
    if not first:
        return float(times[sel[np.argmax(rise[sel])]] - t)
    top = rise[sel].max()
    peaks = [k for k in sel if 0 < k < len(rise) - 1 and rise[k] >= rise[k - 1] and rise[k] >= rise[k + 1]
             and rise[k] >= 0.5 * top]
    k = peaks[0] if peaks else sel[np.argmax(rise[sel])]
    return float(times[k] - t)


def fundamental(x: np.ndarray, t0: float, t1: float, lo: float = 80.0, hi: float = 400.0) -> float:
    """The strongest frequency (Hz) of x between t0 and t1, zero-padded for a fine grid."""
    seg = x[int(t0 * SR):int(t1 * SR)]
    seg = seg * np.hanning(len(seg))
    nfft = 2 ** 20
    spec = np.abs(np.fft.rfft(seg, nfft))
    f = np.fft.rfftfreq(nfft, 1.0 / SR)
    m = np.flatnonzero((f >= lo) & (f <= hi))
    k = m[np.argmax(spec[m])]
    a, b, c = np.log(spec[k - 1]), np.log(spec[k]), np.log(spec[k + 1])
    shift = 0.5 * (a - c) / (a - 2 * b + c)                 # parabolic peak in the log magnitude
    return float(f[k] + shift * (f[1] - f[0]))


def check_audio(film, wav, out, log: list, mix, bus) -> None:
    x = _read_wav(wav)
    lufs, tp = kit.integrated_lufs(x), kit.true_peak_dbtp(x)
    dec = _decode(out)
    aac_lufs, aac_tp = kit.integrated_lufs(dec), kit.aac_true_peak(out)
    a_dur = [float(s["duration"]) for s in _probe(out)["streams"] if s["codec_type"] == "audio"][0]
    tm = timing(film)
    print(f"times from the film: reset {tm['reset']:.2f} s, dial {tm['ticks'][0]:.2f}-{tm['ticks'][-1]:.2f} s "
          f"({len(tm['ticks'])} ticks), turn {tm['turn']:.2f} s, end {tm['end']:.2f} s")
    print(f"durations: WAV {len(x) / SR:.3f} s; muxed MP4 audio {a_dur:.3f} s")

    print("\n(1) loudness and true peak")
    print(f"    WAV            {lufs:+.2f} LUFS   {tp:+.2f} dBTP   (limit -1.5 dBTP)")
    print(f"    MP4 (decoded)  {aac_lufs:+.2f} LUFS   {aac_tp:+.2f} dBTP   (limit -1 dBTP)")
    assert -14.5 <= lufs <= -13.5 and -14.5 <= aac_lufs <= -13.5, (lufs, aac_lufs)
    assert tp <= -1.5 and aac_tp <= -1.0, (tp, aac_tp)
    air_mix, air_wav = _share_above(mix, AIR), _share_above(x, AIR)
    print(f"    the top octave (above {AIR / 1000:.0f} kHz): the mix before the master {air_mix:+.1f} dB of its energy, "
          f"the WAV {air_wav:+.1f} dB")
    assert air_mix < -60.0, air_mix

    print("\n(2) the first 0.1 s: sound from the first frame")
    head = x[:int(0.1 * SR)]
    loud = np.flatnonzero(np.abs(x).max(axis=1) > 0.1)
    assert loud.size, "no sound above -20 dBFS"
    first_ms = 1000 * loud[0] / SR
    peak_db = 20 * np.log10(np.abs(head).max())
    print(f"    RMS {_db(head):.1f} dBFS, peak {peak_db:.1f} dBFS, first sample above -20 dBFS at {first_ms:.2f} ms")
    assert peak_db > -20 and first_ms < 20, "no sound in the first frame"

    print("\n(3) the last second, RMS per 0.1 s (dBFS)")
    win = int(0.1 * SR)
    ends = [_db(x[len(x) - (k + 1) * win:len(x) - k * win]) for k in range(10)][::-1]
    last_step = np.abs(np.diff(x[-int(0.005 * SR):], axis=0)).max()
    print("    " + " ".join(f"{v:.1f}" for v in ends))
    print(f"    last sample {abs(x[-1, 0]):.2e}, largest step in the last 5 ms {last_step:.2e}")
    assert ends[-1] < ends[0] - 10 and abs(x[-1, 0]) < 1e-3 and last_step < 2e-3, "the ending is not a clean fade"

    print("\n(4) the drone's pitch against the counter (the drone alone, from 0.45 s after each change)")
    drone_track = bus["drone"].mean(axis=1)
    keys = counter_steps(film, tm)
    worst = 0.0
    for k, (t0, step) in enumerate(keys[:-1]):
        t1 = keys[k + 1][0]
        if t1 - t0 < 0.75:
            continue
        f_meas = fundamental(drone_track, t0 + 0.45, t1 - 0.01)
        f_want = freq_of(step)
        cents = 1200 * math.log2(f_meas / f_want)
        worst = max(worst, abs(cents))
        ym = "start" if k == 0 else ("reset" if k == 1 else tm["months"][k - 2] if k - 2 < len(tm["months"]) else "turn")
        ratio = film.ratio.get(ym, film.winter if ym == "turn" else float("nan"))
        print(f"    {t0:6.2f} s  {ym:>8}  counter x{ratio:4.2f}  step {step}  {f_want:7.1f} Hz  "
              f"measured {f_meas:7.1f} Hz  ({cents:+5.1f} cents)")
    print(f"    largest error {worst:.1f} cents (limit 25)")
    assert worst <= 25.0, worst
    steps_seen = [s for _, s in keys]
    assert len(set(steps_seen)) >= 4, steps_seen

    print("\n(5) the bass in mono: the side against the mid in the spectrum of the WAV, below each frequency")
    marks = {f: _side_db(x, f) for f in (60.0, 90.0, 120.0)}
    print("    " + "   ".join(f"below {f:.0f} Hz {v:+.1f} dB" for f, v in marks.items()))
    assert marks[120.0] < -60, "the bass is not mono"

    print("\n(6) the events' onsets: each event's own sound, and the same in the WAV")
    events = [e for e in log if e[3]]
    own = []
    for label, visual, hit_t, items in events:
        a = round((hit_t - 0.1) * SR)
        ev = kit.new_track(0.4)
        for sound, g, pan in items:
            kit.place(ev, sound, (round(hit_t * SR) - a) / SR, g, pan)
        lt, lr = _flux(_air_cut(ev.mean(axis=1)))
        own.append(_flux_onset(lt, lr, 0.1))
    assert all(v is not None for v in own), "an event with no onset"
    worst_own = max(abs(v) for v in own)
    print(f"    the sounds on their own, {len(own)} events: largest first-rise offset {worst_own * 1000:.2f} ms "
          f"(limit {MAX_OFFSET * 1000:.0f} ms)")
    assert worst_own <= MAX_OFFSET, worst_own
    mm = mix.mean(axis=1)
    from scipy.ndimage import uniform_filter1d
    hp = butter(2, 12.0, "highpass", fs=SR, output="sos")
    mx = x.mean(axis=1)
    u = sosfilt(hp, mm[:len(mx)])
    w1 = round(0.001 * SR) | 1
    gain = (uniform_filter1d(mx * u, w1, mode="nearest")
            / np.maximum(uniform_filter1d(u * u, w1, mode="nearest"), 1e-12))
    wav_off = []
    for label, visual, hit_t, items in events:
        a = round((hit_t - 0.1) * SR)
        b = a + round(0.4 * SR)
        ev = kit.new_track(0.4)
        for sound, g, pan in items:
            kit.place(ev, sound, (round(hit_t * SR) - a) / SR, g, pan)
        evm = _air_cut(ev.mean(axis=1))
        cleared = mx[a:b] - gain[a:b] * (u[a:b] - sosfilt(hp, evm))
        lt, lr = _flux(cleared)
        wav_off.append(_flux_onset(lt, lr, 0.1, first=False))
    assert all(v is not None for v in wav_off), "an event with no onset in the WAV"
    worst_wav = max(abs(v) for v in wav_off)
    print(f"    the WAV: largest strongest-peak offset {worst_wav * 1000:.2f} ms (limit {MAX_OFFSET * 1000:.0f} ms)")
    assert worst_wav <= MAX_OFFSET, worst_wav
    for (label, visual, _h, _i), o, wv in zip(events, own, wav_off):
        print(f"    {label:<40}{visual:8.3f} s  own {o * 1000:+7.2f} ms  WAV {wv * 1000:+7.2f} ms")

    print("\n    through the MP4's AAC audio, decoded (the strongest flux peak, offset in ms):")
    dtimes, drise = _flux(dec.mean(axis=1))
    worst_dec = 0.0
    for label, visual, hit_t, _items in events:
        off = _flux_onset(dtimes, drise, hit_t, first=False)
        assert off is not None and abs(off) <= MAX_OFFSET, (label, off)
        worst_dec = max(worst_dec, abs(off))
    print(f"    the decoded events are within the limit (largest {worst_dec * 1000:.2f} ms)")


def _share_above(x, fc: float) -> float:
    x = np.asarray(x, float)
    x = x.mean(axis=1) if x.ndim == 2 else x
    p = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    return float(10 * np.log10(max(p[f > fc].sum(), 1e-30) / max(p.sum(), 1e-30)))


def check_video(video, out, untouched: bool) -> None:
    vid, mux_p = _probe(video), _probe(out)
    print(f"\ndurations: silent reel video {float(vid['format']['duration']):.3f} s; "
          f"muxed MP4 {float(mux_p['format']['duration']):.3f} s")
    print("\n(7) the video stream of the muxed MP4 against the silent reel")
    v_md5, m_md5 = _md5(video, "0:v:0"), _md5(out, "0:v:0")
    print(f"    silent reel {v_md5}")
    print(f"    muxed reel  {m_md5}")
    assert v_md5 == m_md5, "the video stream changed"
    assert untouched, "the silent reel was rewritten"
    print("    the same packets; the silent reel was not rewritten")


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    film = onebit_air.AirFilm()
    base = onebit.OUT / "social" / BASE
    video = Path(f"{base}_reel.mp4")
    wav = Path(f"{base}_music.wav")
    out = Path(f"{base}_music_reel.mp4")
    if video.stat().st_mtime < Path(onebit_air.__file__).stat().st_mtime:
        sys.exit(f"{video.name} is older than src/onebit_air.py: render the film first "
                 f"(python -I src/onebit_air.py), then run this score again")
    st = os.stat(video)
    before = (st.st_size, st.st_mtime_ns)
    log: list = []
    track, mix, bus = render(film, log)
    kit.write_wav(wav, track)
    print("saved", wav)
    kit.mux(video, wav, out)
    print("saved", out)
    check_audio(film, wav, out, log, mix, bus)
    st2 = os.stat(video)
    check_video(video, out, untouched=before == (st2.st_size, st2.st_mtime_ns))
    print("\nall checks pass")


if __name__ == "__main__":
    main()
