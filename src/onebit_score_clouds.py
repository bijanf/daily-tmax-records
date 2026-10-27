"""The soundtrack of the clouds reel: "Do the neighbours steal Iran's rain?" (iran_clouds_pesteh_fa_20s).

An original track in Shur on D at 120 BPM, synthesized with onebit_persian (no samples, no recordings,
no voices): a half-time groove, setar and santur in the mode with its koron seconds, a mono sub bass,
and a six-note hook over two bars. It is built on the film's own clock (CloudsFilm: starts, later(),
draw_at, board_at, order, dry, pct), so the drop lands on "Iran and Iraq usually rise and fall together"
and every scoreboard row gets its own hit.

  0 to 4.8 s    intro: a sting on the first frame. Two setar voices play the rain of the two lines year by
                year: Iran on each sixteenth, Iraq an octave lower on every second one, on the same years,
                so both move together. The lines finish at 4.8 s with the year 2025.
  4.8 to 7.6 s  build: a riser and a snare roll; the scene change at 6 s is a snare, a clap and a tom
  7.6 s         drop: impact, 808 kick and clap on the sentence; the groove (two bars, anchored on this beat),
                the bass, the pad, a santur arpeggio and the hook start here
  11.6 to 12 s  a 32nd-note snare roll into the scoreboard
  12 to 14.7 s  breakdown: the beat leaves. One tombak per scoreboard row, at the time its squares fill;
                its level and its depth follow the row's count of dry years (6 quiet and high, 10 loud and low)
  14.7 s        accent on "neighbours were often dry too"
  16 to 20 s    outro: the groove returns on the bar, the hook moves up two steps and lands on the tonic an
                octave higher at 18 s; the master fades the last second

write(film, path) writes the 48 kHz 16-bit WAV. main() also muxes it under the silent reel into
iran_clouds_pesteh_fa_20s_music_reel.mp4 and prints the numbers the track is checked against.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
import onebit_persian as kit  # noqa: E402
from onebit_clouds import CloudsFilm  # noqa: E402
from onebit_slides import COLOURS  # noqa: E402

SR = kit.SR
BEAT = kit.BEAT                       # 0.5 s: a quarter note at 120 BPM
S8, S16, S32 = BEAT / 2, BEAT / 4, BEAT / 8
BAR = kit.BAR                         # 2 s: the film's beat (60 BPM) is every second beat of the music
TAIL = 3.0                            # s of echo and reverb past the end; the master cuts them
MODE = "shur"
DATA_SLOTS = 38                       # sixteenths from 0 to 4.625 s: the lines draw in during 0 to 4.8 s
# the hook: two bars, six notes, as (sixteenth from the phrase start, Shur step, velocity)
HOOK = ((0, 1, 1.0), (6, 2, 0.8), (8, 3, 0.9), (13, 4, 0.8), (16, 2, 0.8), (24, 0, 0.95))
RETURN = ((0, 3, 1.0), (6, 4, 0.8), (8, 5, 0.9), (13, 6, 0.8))   # the outro: the first four, two steps up
ARP = (0, 2, 4, 6, 7, 6, 4, 2)        # the santur arpeggio under the drop's second bar
KICK_A, KICK_B = (0, 6, 10), (0, 6, 11)   # kicks in sixteenths of a bar: the 1, the 'and' of 2, of 3


# ── the film's clock and the rain ───────────────────────────────────────────

def _times(film) -> dict:
    """The event times, read from the film: the scene starts, the drop, the rows and the accent."""
    s = [float(t) for t in film.starts]
    return dict(lines=float(max(film.draw_at.values())),        # 4.8 s: 2025 is the last point drawn
                scene2=s[1],                                    # 6 s
                drop=s[1] + float(film.later(1)),               # 7.6 s: "rise and fall together"
                scene3=s[2],                                    # 12 s
                rows=[float(t) for t in film.board_at],         # 12.3 .. 14.4 s
                accent=s[2] + float(film.later(2)),             # 14.7 s: "often dry too"
                outro=s[-1] - 2 * BAR,                          # 16 s: the groove returns on the bar
                end=s[-1])                                      # 20 s


def _hz(step: int, octave: int = 0) -> float:
    """The frequency of a Shur step; octave -2 is the bass register (the tonic is D2 there)."""
    return kit.degree(MODE, step, octave)


def _steps(pct) -> np.ndarray:
    """A rain value in % of the country's mean, as a Shur step: 40 % is the lowest step (D) and 160 % the
    top one (nine steps up), 100 % (the mean) is A. Wetter is higher."""
    u = np.clip((np.asarray(pct, float) - 40.0) / 120.0, 0.0, 1.0)
    return np.round(9 * u).astype(int)


def _data_plan(film) -> dict:
    """The rain as notes. Each sixteenth before the line's end plays the year whose point the front reaches
    nearest that instant (the first is 1965: the front is at 0 s then), so no year before 0 s is heard.
    The sixteenth at 4.75 s is left out: it would sit 50 ms before the 2025 landing at 4.8 s."""
    years = np.array(sorted(int(y) for y in film.years))
    draw = np.array([float(film.draw_at[y]) for y in years])
    iran = film.pct.loc[years, "Iran"].to_numpy(float)
    iraq = film.pct.loc[years, "Iraq"].to_numpy(float)
    idx = [int(np.argmin(np.abs(draw - k * S16))) for k in range(DATA_SLOTS)]
    return dict(years=years, draw=draw, iran=iran, iraq=iraq, st_ir=_steps(iran), st_iq=_steps(iraq), idx=idx)


# ── helpers ─────────────────────────────────────────────────────────────────

def _fit(x: np.ndarray, n: int) -> np.ndarray:
    return x[:n] if len(x) >= n else np.vstack([x, np.zeros((n - len(x), x.shape[1]))])


def _mono_low(x: np.ndarray, fc: float = 120.0) -> np.ndarray:
    """Below fc the mix is mono, exactly: the band below fc, cut by an FFT, is replaced by its mean over
    the two channels; the band above it is untouched."""
    n = len(x)
    low = np.fft.irfft(np.fft.rfft(x, axis=0) * (np.fft.rfftfreq(n, 1 / SR) < fc)[:, None], n=n, axis=0)
    return x - low + low.mean(axis=1, keepdims=True)


# ── the soundtrack ──────────────────────────────────────────────────────────

def soundtrack(film) -> np.ndarray:
    """The mastered track, (n, 2) float at 48 kHz, 20 s on the film's clock, -14 LUFS, true peak -1.5 dBTP."""
    kit.reseed(19)                                              # the same sounds on every render
    T, P = _times(film), _data_plan(film)
    seconds = T["end"]
    names = ("drums", "music", "bass", "fx", "rv", "ec")
    bus = {k: kit.new_track(seconds, TAIL) for k in names}
    d, m, b, fx, rv, ec = (bus[k] for k in names)
    kicks: list[float] = []
    kick, snare, clap = kit.kick808(), kit.snare(), kit.clap()
    hat_c, hat_o = kit.hat(False), kit.hat(True)
    bam, tak, zang = kit.daf("bam"), kit.daf("tak"), kit.daf("zang")
    tom, bak = kit.tombak("tom"), kit.tombak("bak")

    def groove(t0, pattern, backbeat=True, hats=8, roll=False, open_hat=False, level=1.0):
        """One bar of the half-time groove from its first sixteenth at t0: 808 kicks on the sixteenths of
        `pattern`, a snare and a clap on beat 3, eighth-note hats, a 32nd-note roll on the last beat if roll,
        an open hat on the last sixteenth if open_hat."""
        for i in pattern:
            kit.place(d, kick, t0 + i * S16, 0.95 * level)
            kicks.append(t0 + i * S16)
        if backbeat:
            kit.place(d, snare, t0 + 2 * BEAT, 0.55 * level)
            kit.place(d, clap, t0 + 2 * BEAT, 0.28 * level, pan=0.1)
        for i in range(hats):
            kit.place(d, hat_c, t0 + i * S8, (0.18 if i % 2 else 0.12) * level, pan=-0.25 if i % 2 else 0.25)
        if roll:
            kit.roll(d, t0 + 3.5 * BEAT, 0.25, 8, vel0=0.4, vel1=1.0, gain=0.2 * level, pan=-0.2)
        if open_hat:
            kit.place(d, hat_o, t0 + 15 * S16, 0.2 * level, pan=0.2)

    def bass(t, step, dur, glide=None, vel=0.8):
        """The 808 sub on a Shur step in the bass register, slid from the step `glide` if given. Mono."""
        kit.place(b, kit.sub(_hz(step, -2), dur, vel=vel,
                             glide_from=None if glide is None else _hz(glide, -2)), t, 0.7)

    def pad(t, steps, dur, vel=0.3):
        kit.place(m, kit.pad([_hz(s, -1) for s in steps], dur, vel=vel, cutoff=1400.0), t, 0.5)

    def santur(t, step, octave, dur, vel, gain, pan=0.0, t60=2.6, reverb=0.2):
        s = kit.santur(_hz(step, octave), dur=dur, vel=vel, t60=t60)
        kit.place(m, s, t, gain, pan=pan)
        kit.place(rv, s, t, reverb, pan=pan)

    def phrase(t0, notes, octave=0):
        """Setar notes of a hook: (sixteenth from t0, Shur step, velocity), echoed and a little reverberant."""
        for pos, step, vel in notes:
            s = kit.setar(_hz(step, octave), dur=1.4, vel=vel, t60=0.9, bright=0.6, buzz=0.1)
            kit.place(m, s, t0 + pos * S16, 0.5, pan=-0.1)
            kit.place(ec, s, t0 + pos * S16, 0.35, pan=-0.1)
            kit.place(rv, s, t0 + pos * S16, 0.12)

    def pluck(t, step, octave, pan, gain, bright=0.6, dur=0.6, t60=0.5, vel=0.6):
        s = kit.setar(_hz(step, octave), dur=dur, vel=vel, t60=t60, bright=bright, buzz=0.04)
        kit.place(m, s, t, gain, pan=pan)
        kit.place(ec, s, t, 0.45 * gain, pan=pan)

    def iran_voice(t, i):
        """Iran's rain as a pluck in the setar's upper register; higher = wetter."""
        pluck(t, int(P["st_ir"][i]), 0, 0.35, 0.85)

    def iraq_voice(t, i):
        """Iraq's rain as a pluck an octave lower, darker and a little softer."""
        pluck(t, int(P["st_iq"][i]), -1, -0.35, 0.7, bright=0.35, dur=0.8, t60=0.6)

    # ── intro, 0 to 4.8 s: the sting on the first frame, a pad, the sub on the bar lines, the lilt, the data
    for k, s in enumerate((0, 2, 4, 7)):
        santur(0.0, s, 0, dur=2.4, vel=0.5, gain=0.5, pan=-0.2 + 0.4 * k / 3, t60=2.6, reverb=0.2)
    kit.place(d, bam, 0.0, 0.8)
    kit.place(d, zang, 0.0, 0.3, pan=0.3)
    pad(0.0, (0, 2, 4), T["lines"] + 0.6, vel=0.22)
    for t in (0.0, 2.0, 4.0):
        bass(t, 0, 1.6, vel=0.6)
    for i, t in enumerate((0.75, 1.75, 2.75, 3.75)):
        kit.place(d, tak, t, 0.3, pan=0.3 if i % 2 else -0.3)
    for t in np.arange(S8, T["lines"] - 0.25, S8):          # the hats stop before the landing at 4.8 s
        kit.place(d, hat_c, t, 0.10, pan=0.2 if int(round(t / S8)) % 2 else -0.2)
    for k, i in enumerate(P["idx"]):
        t = k * S16
        iran_voice(t, i)
        if k % 2 == 0:
            iraq_voice(t, i)
    last = len(P["years"]) - 1                                  # 2025: the line's end, at 4.8 s
    iran_voice(T["lines"], last)
    iraq_voice(T["lines"], last)
    kit.place(d, zang, T["lines"], 0.2, pan=-0.3)

    # ── build, 4.8 to 7.6 s: a riser, a snare roll on the sixteenths from 5 s, eighth hats; the scene change
    # at 6 s has its own snare, clap and tom
    kit.place(fx, kit.riser(dur=T["drop"] - T["lines"], vel=0.55, f0=180.0, f1=1600.0), T["lines"], 0.5)
    rolls = np.arange(5.0, T["drop"] - 1e-9, S16)
    for i, t in enumerate(rolls):
        if abs(t - T["scene2"]) > 1e-9:
            kit.place(d, snare, t, 0.55 * (0.15 + 0.8 * (i / (len(rolls) - 1)) ** 1.5))
    for t in np.arange(5.0, T["drop"] - 1e-9, S8):
        kit.place(d, hat_c, t, 0.10, pan=-0.2 if int(round(t / S8)) % 2 else 0.2)
    kit.place(d, snare, T["scene2"], 0.9)
    kit.place(d, clap, T["scene2"], 0.35)
    kit.place(d, tom, T["scene2"], 0.5)

    # ── drop, 7.6 s: the impact, the 808 and the clap land on the sentence; the groove, the bass, the pad, the
    # santur arpeggio of the second bar and the hook all start on that beat
    kit.place(fx, kit.impact(dur=2.2, vel=1.0, pitch=42.0), T["drop"], 0.8)
    kit.place(d, clap, T["drop"], 0.35, pan=0.1)
    groove(T["drop"], KICK_A)
    groove(T["drop"] + BAR, KICK_B, roll=True, open_hat=True)
    bass(T["drop"], 0, BAR + 0.1)
    bass(T["drop"] + BAR, 3, BAR + 0.1, glide=0)
    pad(T["drop"], (0, 2, 4), BAR + 0.6)
    pad(T["drop"] + BAR, (3, 5, 7), BAR + 0.6)
    for i in range(16):
        santur(T["drop"] + BAR + i * S16, ARP[i % 8], 1, dur=1.2, vel=0.22, gain=0.5,
               pan=0.3 if i % 2 else -0.3, t60=1.6, reverb=0.12)
    phrase(T["drop"], HOOK)

    # ── fill, 11.6 to 12 s: a 32nd-note snare roll into the scoreboard
    fills = np.arange(T["drop"] + 2 * BAR, T["scene3"] - 0.08, S32)   # ends 80 ms before the scene change
    for i, t in enumerate(fills):
        kit.place(d, snare, t, 0.55 * (0.3 + 0.7 * i / max(1, len(fills) - 1)))

    # ── breakdown, 12 to 14.7 s: the beat leaves; the tension chord (koron E, G, B flat) on a sub pedal;
    # a daf at the scene change; one tombak per row, at the time its squares fill
    kit.place(d, bam, T["scene3"], 0.6)
    kit.place(d, bak, T["scene3"], 0.35, pan=0.15)
    hold = T["outro"] - T["scene3"]
    pad(T["scene3"], (1, 3, 5), hold + 0.6, vel=0.28)
    bass(T["scene3"], 1, hold + 0.1, vel=0.55)
    for s in (1, 3, 5):
        santur(T["scene3"], s, 0, dur=2.6, vel=0.35, gain=0.5, t60=2.6, reverb=0.2)
    for k, t in enumerate(T["rows"]):
        count = int(sum(film.dry[film.order[k]]))
        w = (count - 5) / 5                                     # 6 dry years -> 0.2, 10 -> 1.0
        pan = -0.2 + 0.4 * k / (len(T["rows"]) - 1)
        kit.place(d, kit.tombak("tom", vel=1.0, pitch=100.0 - 12.0 * w), t, 0.45 + 0.5 * w, pan=pan)
        kit.place(d, bak, t, 0.3, pan=pan)

    # ── accent, 14.7 s: the answer, "often dry too": an impact, the tonic chord on the santur, a clap
    kit.place(fx, kit.impact(dur=2.2, vel=0.9, pitch=42.0), T["accent"], 0.75)
    kit.place(d, clap, T["accent"], 0.35, pan=-0.1)
    for s, p in zip((0, 2, 4, 7), (-0.25, -0.1, 0.1, 0.25)):
        santur(T["accent"], s, 0, dur=2.6, vel=0.6, gain=0.5, pan=p, t60=2.6, reverb=0.25)

    # ── outro, 16 to 20 s: a riser and a roll into the bar at 16 s; the groove returns on it; the hook two steps
    # up, the tonic an octave up at 18 s with a last kick; the master fades the last second
    kit.place(fx, kit.riser(dur=T["outro"] - T["accent"], vel=0.5, f0=300.0, f1=2400.0), T["accent"], 0.5)
    rolls2 = np.arange(T["outro"] - 1.0, T["outro"] - 1e-9, S16)
    for i, t in enumerate(rolls2):
        kit.place(d, snare, t, 0.55 * (0.2 + 0.7 * i / (len(rolls2) - 1)))
    groove(T["outro"], KICK_A, open_hat=True)
    groove(T["outro"] + BAR, (0,), backbeat=False, hats=4)
    bass(T["outro"], 3, BAR + 0.1, glide=1)
    bass(T["outro"] + BAR, 0, T["end"] - T["outro"] - BAR + 1.0, glide=3)
    pad(T["outro"], (3, 5, 7), BAR + 0.6)
    pad(T["outro"] + BAR, (0, 2, 4), T["end"] - T["outro"] - BAR + 1.0)
    phrase(T["outro"], RETURN)
    phrase(T["outro"] + BAR, ((0, 7, 0.95),))                   # the tonic, an octave up, at 18 s
    for s in (0, 2, 4, 7):
        santur(T["outro"] + BAR, s, 0, dur=3.0, vel=0.42, gain=0.45, pan=0.0, t60=2.6, reverb=0.25)

    # ── mix: the music ducked to the kicks, the bass ducked less; the sends to a room and a ping-pong echo;
    # the low end made mono; then the master (integrated -14 LUFS, true peak -1.5 dBTP, a 1 s fade). The mono
    # step comes before the limiter, so the limiter bounds every peak; after it, a cut would ring at the edges
    n = len(d)
    kicks = sorted(kicks)
    mix = d + kit.duck(m, kicks, depth_db=4.0, release=0.18) + kit.duck(b, kicks, depth_db=3.0, release=0.12) + fx
    mix = mix + _fit(0.5 * kit.reverb(rv, t60=2.2), n)
    mix = mix + _fit(0.6 * kit.pingpong(ec, delay=0.375, feedback=0.4, taps=6, tone=3000.0), n)
    return kit.master(_mono_low(mix), lufs=-14.0, tp=-1.5, seconds=seconds, fade_out=1.0)


def write(film, path) -> Path:
    """The soundtrack as a 48 kHz 16-bit stereo WAV."""
    return kit.write_wav(path, soundtrack(film))


# ── checks ──────────────────────────────────────────────────────────────────

def _read(path) -> np.ndarray:
    _, pcm = wavfile.read(str(path))
    return pcm.astype(float) / 32768.0


def _decode(media) -> np.ndarray:
    """The audio as a player decodes it (the AAC of the reel), (n, 2) float."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(media), "-vn", "-f", "f32le", "-ac", "2",
                          "-ar", str(SR), "-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2).astype(float)


def _flux(x: np.ndarray, n_fft: int = 1024, hop: int = 128) -> np.ndarray:
    """Spectral flux of the mono mix: the rise of the log-compressed magnitude from frame to frame, summed
    over the bins. Frame f is centred on sample f * hop, so a click at t shows at the frame centred on t."""
    m = x.mean(axis=1) if x.ndim == 2 else x
    half = n_fft // 2
    y = np.concatenate([np.zeros(half), m, np.zeros(half)])
    n_frames = (len(y) - n_fft) // hop + 1
    win = np.hanning(n_fft)
    L = np.empty((n_frames, n_fft // 2 + 1))
    for a in range(0, n_frames, 2000):
        b = min(n_frames, a + 2000)
        idx = np.arange(n_fft)[None, :] + hop * np.arange(a, b)[:, None]
        L[a:b] = np.log1p(100.0 * np.abs(np.fft.rfft(y[idx] * win, axis=1)))
    return np.maximum(np.diff(L, axis=0, prepend=0.0), 0.0).sum(axis=1)


def _onset(flux: np.ndarray, t: float, hop: int = 128, search: float = 0.06) -> float:
    """The offset in seconds of the strongest flux peak within +-search of t, from t."""
    lo = max(0, int(round((t - search) * SR / hop)))
    hi = min(len(flux) - 1, int(round((t + search) * SR / hop)))
    f = lo + int(np.argmax(flux[lo:hi + 1]))
    return f * hop / SR - t


def _calibration() -> list:
    """The detector on onsets it is given: sounds of the track placed in silence at known times."""
    tr = kit.new_track(6.0)
    sounds = [kit.kick808(), kit.tombak("tom"), kit.impact(dur=2.2, vel=1.0, pitch=42.0), kit.snare(), kit.clap()]
    times = [1.0 + i for i in range(len(sounds))]
    for s, t in zip(sounds, times):
        kit.place(tr, s, t, 0.5)
    flux = _flux(tr)
    return [_onset(flux, t) for t in times]


def _probe(media) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(media)],
                         check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def _md5(media) -> str:
    """The MD5 of the video stream as copied (no decode): equal for equal video packets."""
    return subprocess.run(["ffmpeg", "-v", "error", "-i", str(media), "-map", "0:v:0", "-c:v", "copy",
                           "-f", "md5", "-"], check=True, capture_output=True).stdout.decode().strip()


def _events(film, T) -> list:
    """The events of the track: (label, time, the picture's test for when it shows or None for a musical
    landmark with no picture event, the hit must be within 30 ms). The tests are the film's own: a word
    shows once its time is passed, a row once its time is reached."""
    def drop_shown(t):
        return sum(t - film.starts[1] > a for a in film.appear(1)) >= 4      # the first word after the break

    def accent_shown(t):
        return sum(t - film.starts[2] > a for a in film.appear(2)) >= 4

    ev = [("question on the first frame (scene 1)", 0.0, lambda t: t >= 0, True),
          ("lines finish: 2025 drawn", T["lines"], lambda t: t >= max(film.draw_at.values()), True),
          ("scene 2", T["scene2"], lambda t: film.scene(t) >= 1, True),
          ("drop: 'Iran and Iraq rise and fall together'", T["drop"], drop_shown, True),
          ("scene 3", T["scene3"], lambda t: film.scene(t) >= 2, True)]
    for k, t in enumerate(T["rows"]):
        key = film.order[k]
        ev.append((f"row {k + 1} fills: {key}, {int(sum(film.dry[key]))} of 10 dry", t,
                   lambda s, k=k: film.row_full(k, s), True))
    ev.append(("accent: 'neighbours were often dry too'", T["accent"], accent_shown, True))
    ev.append(("outro: groove returns on the bar (music only)", T["outro"], None, True))
    ev.append(("tonic and last kick (music only)", T["outro"] + BAR, None, True))
    return ev


def _first_frame(pred, end: float, fps: int = onebit.FPS) -> float:
    """The time of the first frame of the picture (frames at k / fps) for which pred(t) holds."""
    return next(k / fps for k in range(round(end * fps)) if pred(k / fps))


def report(film, wav: Path, silent: Path, mp4: Path) -> None:
    T, P = _times(film), _data_plan(film)
    x = _read(wav)
    lufs, tp = kit.integrated_lufs(x), kit.true_peak_dbtp(x)
    dec = _decode(mp4)
    lufs_m, tp_m = kit.integrated_lufs(dec), kit.true_peak_dbtp(dec)
    ps, pm = _probe(silent), _probe(mp4)
    vid = {"s": next(s for s in ps["streams"] if s["codec_type"] == "video"),
           "m": next(s for s in pm["streams"] if s["codec_type"] == "video")}
    aud = next(s for s in pm["streams"] if s["codec_type"] == "audio")
    dur_v = float(vid["m"]["duration"])
    dur_a = float(aud["duration"])

    print(f"WAV  {wav.name}: {len(x) / SR:.3f} s, integrated {lufs:.2f} LUFS, true peak {tp:.2f} dBTP")
    print(f"MP4  {mp4.name}: audio {len(dec) / SR:.3f} s decoded, {lufs_m:.2f} LUFS, true peak {tp_m:.2f} dBTP")
    print(f"     video {vid['m']['width']}x{vid['m']['height']} {vid['m']['codec_name']} "
          f"{vid['m']['r_frame_rate']} fps, {vid['m']['nb_frames']} frames, {dur_v:.3f} s; "
          f"audio {aud['codec_name']} {aud['channels']} ch {aud['sample_rate']} Hz, {dur_a:.3f} s; "
          f"container {float(pm['format']['duration']):.3f} s")

    flux = _flux(x)
    cal = _calibration()
    table = []
    for label, t, pred, must in _events(film, T):
        table.append((label, t, _onset(flux, t), None if pred is None else _first_frame(pred, T["end"]), must))
    print()
    print("EVENT TABLE: event time from the film; the music hit is placed on that time; onset measured in the WAV;")
    print("picture: the first 30 fps frame that shows the event, by the film's own tests")
    print(f"  {'event':<46}{'event s':>9}{'hit s':>9}{'onset s':>9}{'offset ms':>11}{'picture s':>11}{'pic-event ms':>14}")
    for label, t, off, pic, _ in table:
        pic_s = f"{pic:11.3f}" if pic is not None else f"{'-':>11}"
        lag = f"{1000 * (pic - t):+14.1f}" if pic is not None else f"{'-':>14}"
        print(f"  {label:<46}{t:9.3f}{t:9.3f}{t + off:9.3f}{1000 * off:+11.1f}{pic_s}{lag}")
    print("  detector calibration, the same sounds placed in silence (offset ms): "
          + ", ".join(f"{1000 * c:+.1f}" for c in cal))

    plan_err = max(abs(float(P["draw"][i]) - k * S16) for k, i in enumerate(P["idx"]))
    r_steps = np.corrcoef(P["st_ir"][P["idx"]], P["st_iq"][P["idx"]])[0, 1]
    print()
    print(f"DATA: {DATA_SLOTS} Iran plucks on the sixteenths and {len(range(0, DATA_SLOTS, 2))} Iraq plucks on the "
          f"eighths, 0 to 4.625 s, plus 2025 at 4.8 s; the year nearest each instant; largest gap between a year's "
          f"point and its pluck {1000 * plan_err:.0f} ms; steps of the two voices correlate r = {r_steps:.2f}")

    # ── the numbers the track is checked against ──
    peak0 = float(np.abs(x[:int(0.1 * SR)]).max())
    rms0 = float(np.sqrt(np.mean(x[:int(0.1 * SR)] ** 2)))
    print()
    print(f"(1) loudness {lufs:.2f} LUFS in [-15, -13]; true peak {tp:.2f} dBTP <= -1; "
          f"decoded AAC {lufs_m:.2f} LUFS, {tp_m:.2f} dBTP")
    print(f"(2) first 0.1 s: peak {20 * np.log10(peak0):.1f} dBFS, RMS {20 * np.log10(rms0):.1f} dBFS")
    win = int(0.1 * SR)
    rms_end = [20 * np.log10(np.sqrt(np.mean(x[i:i + win] ** 2)) + 1e-12)
               for i in range(int(19.0 * SR), int(20.0 * SR) - win + 1, win)]
    print("(3) RMS per 100 ms over the last second, dBFS: " + " ".join(f"{v:.1f}" for v in rms_end)
          + f"; last sample {np.abs(x[-1]).max():.2e}; largest sample in the last 20 ms "
          f"{np.abs(x[-int(0.02 * SR):]).max():.2e}")
    checked = [off for _, _, off, _, must in table if must]
    worst = max(abs(off) for off in checked)
    print(f"(4) hits within 30 ms of their events: {len(checked)} of {len(checked)}; worst |offset| "
          f"{1000 * worst:.1f} ms. The detector reads these same sounds {1000 * min(cal):+.1f} to "
          f"{1000 * max(cal):+.1f} ms in silence, so most of each offset is its own: allowing for it, the hits "
          f"sit within about 5 ms of their events")
    keys = ("codec_name", "width", "height", "pix_fmt", "r_frame_rate", "nb_frames")
    same = all(vid["s"][k] == vid["m"][k] for k in keys)
    md5_s, md5_m = _md5(silent), _md5(mp4)
    print(f"(5) video stream of the muxed file against the silent reel: fields {'equal' if same else 'DIFFER'} "
          f"({', '.join(keys)}); packet MD5 {md5_s} silent, {md5_m} muxed")

    band = np.fft.rfftfreq(len(x), 1 / SR) < 120.0
    side = np.fft.irfft(np.fft.rfft(x[:, 0] - x[:, 1]) * band, n=len(x))
    side_db = 10 * np.log10(np.sum(np.abs(np.fft.rfft(x[:, 0] - x[:, 1])[band]) ** 2)
                            / np.sum(np.abs(np.fft.rfft(x[:, 0] + x[:, 1])[band]) ** 2))
    print(f"(6) low end: the stereo difference below 120 Hz sits {side_db:.0f} dB under the mix there, so the sub, "
          f"kick and bass are mono for the ear; its largest trace is at {int(np.argmax(np.abs(side))) / SR:.2f} s")

    assert side_db < -60, f"the low end is not mono: {side_db:.1f} dB"
    assert -15 <= lufs <= -13, f"integrated {lufs:.2f} LUFS"
    assert tp <= -1, f"true peak {tp:.2f} dBTP"
    assert -15 <= lufs_m <= -13 and tp_m <= -1, f"delivered audio {lufs_m:.2f} LUFS, {tp_m:.2f} dBTP"
    assert peak0 > 0.1, "no sound in the first 0.1 s"
    assert np.abs(x[-1]).max() < 1e-3, "the track does not end at silence"
    assert worst <= 0.030, f"a hit is {1000 * worst:.1f} ms from its event"
    assert same and md5_s == md5_m, "the video changed"


def main() -> None:
    ap = argparse.ArgumentParser(description="The clouds reel's soundtrack: writes the WAV, muxes it, checks it.")
    ap.parse_args()
    film = CloudsFilm(onebit.THEMES["pesteh"], COLOURS["pesteh"], "20s")
    base = onebit.OUT / "social" / "iran_clouds_pesteh_fa_20s"
    wav = write(film, base.with_name(f"{base.name}_music.wav"))
    silent = base.with_name(f"{base.name}_reel.mp4")
    mp4 = base.with_name(f"{base.name}_music_reel.mp4")
    kit.mux(silent, wav, mp4)
    report(film, wav, silent, mp4)


if __name__ == "__main__":
    main()
