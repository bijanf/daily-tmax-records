"""The light score of «یخچال‌های البرز» (alborzice_fa; the owner's own voice goes over it, recorded later).

Dashti (kit.MODES["dashti"], G4 tonic: G, A-koron, Bb, C, D, Eb, F), a setar line with long rests, a soft pad, a
very soft low pulse. The clock is READ from outputs/onebit/alborzice/film.json (cuts.a.scenes: key, start, length;
cuts.a.end) and every event sits at a scene's start or at a FRACTION of its length; no time in this file is a
number of seconds. The fractions are those of the film's own page (src/alborzice_page/film.js), so when the voice
changes the scene lengths the score follows the pictures:

    hook    D5 at 0.00 s (sound in the first 0.1 s), then a falling line D5 C5 A-koron4 G4 over the rewind
    face1   two soft notes
    dam     one soft setar note per measured summer (film.json dam.years) as its bar appears (u 0.03-0.50), pitched
            by that summer's km2 (more white, higher: a G minor pentatonic G3-G5); the run dam.run on the two
            lowest notes, darker and a little longer
    takht   the same for takht.years (u 0.22-0.56), the two medians (u 0.58 and 0.64), the run takht.run
    mech    one small note per packet at its impact (u 0.034 + 0.043 k + 0.012 s): bright and high where it bounces,
            dull and low where it sinks in (the film's own bounce/sink rule from film.json mech); then the ring: a
            note each time the arrow passes a word (the arrow turns faster, so the figure speeds up)
    budget  a soft pair for the two pictures, a falling line for the gauge (u 0.60-0.80)
    thr     one held tone, D4, that bends down a whole step when the bar reaches the threshold (u 0.45-0.56)
    fut     two falling lines, the second falling further
    close   A-koron falls to the home note G, the pad holds G and D, a clean 1-s fade at the end

Outputs (48 kHz), in outputs/onebit/social/:
    alborzice_fa_music.wav   the music alone, -14 LUFS, true peak at most -1 dBTP
    alborzice_fa_bed.wav     the same music at -24 LUFS, for under the voice
    alborzice_fa_music_reel.mp4   only if alborzice_fa_reel.mp4 exists (video stream copied)

    python -I src/onebit_score_alborzice_light.py
"""

from __future__ import annotations

import json
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit_persian as kit  # noqa: E402
import onebit_score_air_light as light  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FILM = ROOT / "outputs" / "onebit" / "alborzice" / "film.json"
SOCIAL = ROOT / "outputs" / "onebit" / "social"
BASE = "alborzice_fa"
SR = kit.SR
MODE = "dashti"
LUFS_MUSIC, LUFS_BED, TP = -14.0, -24.0, -1.5      # dBTP: a little under the -1 limit
TAIL = 3.0
STEPS_PENT = (0, 2, 3, 4, 6)                        # G Bb C D F: a minor pentatonic of dashti (no semitone, no koron)


def hz(step: int, octave: int = 0) -> float:
    """Dashti step (0 G, 1 A-koron, 2 Bb, 3 C, 4 D, 5 Eb, 6 F) on the G4 tonic; octave 0 starts at G4."""
    return kit.degree(MODE, step, octave)


PENT = [hz(s, o) for o in (-1, 0) for s in STEPS_PENT] + [hz(0, 1)]            # G3 Bb3 C4 D4 F4 G4 Bb4 C5 D5 F5 G5
HOME_LO, HOME, HOME_HI = hz(0, -1), hz(0, 0), hz(0, 1)


@lru_cache(maxsize=8)
def _lp_sos(fc: float):
    return butter(4, fc, "lowpass", fs=SR, output="sos")


def pluck(f: float, vel: float, t60: float = 1.1, bright: float = 0.15, dur: float = 2.6, lp: float = 1600.0):
    x = np.asarray(kit.setar(float(f), dur=dur, vel=vel, t60=t60, bright=bright, buzz=0.0), float)
    return sosfilt(_lp_sos(float(lp)), x)


def held(f0: float, dur: float, vel: float, bend_a: float, bend_b: float, cents: float) -> np.ndarray:
    """A held soft tone (sine with two soft overtones, a slow vibrato) that glides by `cents` between the times
    bend_a and bend_b (seconds from its start), faded in over 0.7 s and out over 1.2 s. Mono."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.clip((t - bend_a) / (bend_b - bend_a), 0.0, 1.0)
    glide = cents * (3 * s ** 2 - 2 * s ** 3)
    vib = 5.0 * np.sin(2 * np.pi * 5.0 * t) * np.clip((t - 0.8) / 1.0, 0.0, 1.0)
    f = f0 * 2 ** ((glide + vib) / 1200)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.30 * np.sin(2 * ph) + 0.10 * np.sin(3 * ph)
    env = np.minimum(1.0, t / 0.7) * np.minimum(1.0, (dur - t) / 1.2)
    x = sosfilt(_lp_sos(1100.0), x * env)
    return vel * x / max(1e-9, float(np.abs(x).max()))


def build(film: dict) -> tuple:
    """(events, end, scene table). An event is a dict: t (s, from the film's clock), scene, what, kind, f, vel ..."""
    cut = film["cuts"]["a"]
    end = float(cut["end"])
    sc = {s["key"]: (float(s["start"]), float(s["length"])) for s in cut["scenes"]}
    ev: list = []

    warps = {s["key"]: [[0.0, 0.0]] + [list(map(float, q)) for q in s.get("warp", [])] + [[1.0, 1.0]] for s in cut["scenes"]}

    def at(key: str, u: float) -> float:
        """The time of the picture's fraction u: the film warps a scene so that its turns fall on the narrator's sentences
        (scene "warp": knots [time fraction, picture fraction]); without knots the two are the same."""
        a, n = sc[key]
        k = warps[key]
        for (r0, d0), (r1, d1) in zip(k, k[1:]):
            if u <= d1 + 1e-12:
                return a + (r0 + (r1 - r0) * (u - d0) / max(1e-9, d1 - d0)) * n
        return a + u * n

    def add(key, u, what, kind, f, vel, **kw):
        ev.append(dict(t=at(key, u), scene=key, u=u, what=what, kind=kind, f=float(f), vel=vel, **kw))

    # ---- hook: a note at 0.00 s, then the falling line over the rewind ----
    for u, f, v, w in ((0.00, hz(4, 0), 0.80, "D5 the first sound"), (0.22, hz(3, 0), 0.55, "C5"),
                       (0.45, hz(1, 0), 0.55, "A-koron4"), (0.68, hz(0, 0), 0.60, "G4")):
        add("hook", u, w, "setar", f, v)
    # ---- face1: two soft notes ----
    add("face1", 0.18, "Bb4", "setar", hz(2, 0), 0.45)
    add("face1", 0.62, "D5", "setar", hz(4, 0), 0.45)

    # ---- dam and takht: one note per summer as the bar appears ----
    def years_notes(key: str, u0: float, u1: float, last_u: float, first_u: float | None = None):
        d = film[key]
        ys, run = d["years"], d["run"]
        n = len(ys)
        vmax = max(max(y["km2"] for y in film["dam"]["years"]), max(y["km2"] for y in film["takht"]["years"]))
        for i, y in enumerate(ys):
            u = u0 + (u1 - u0) * i / (n - 2) if i < n - 1 else last_u     # the newest summer comes later, on its own
            if i == 0 and first_u is not None:
                u = first_u
            idx = int(round(y["km2"] / vmax * (len(PENT) - 1)))
            inrun = run[0] <= y["py"] <= run[1]
            if inrun:
                idx = 0 if y["km2"] <= 0.25 else 1             # the lowest, darkest notes
                add(key, u, f"{y['py']} {y['km2']:.2f} km2 RUN", "setar", PENT[idx], 0.62,
                    t60=1.7, bright=0.0, lp=700.0, dur=3.2)
            else:
                add(key, u, f"{y['py']} {y['km2']:.2f} km2", "setar", PENT[idx], 0.42, t60=0.8, dur=1.8)
        return vmax

    vmax = years_notes("dam", 0.03, 0.50, 0.81)
    years_notes("takht", 0.26, 0.48, 0.86, first_u=0.22)
    for u, k in ((0.51, "median_early"), (0.56, "median_late")):
        idx = int(round(film["takht"][k] / vmax * (len(PENT) - 1)))
        add("takht", u, f"median {film['takht'][k]}", "setar", PENT[idx], 0.5, t60=1.6)

    # ---- mech: ten packets on each slab, then the ring that turns faster ----
    M = film["mech"]
    IMP0, DI = 0.034, 0.043                                        # the film's own: first impact, gap between rounds
    k_bright = 0
    for k in range(10):
        for s in (0, 1):
            bounce = (k != M["snow_sink"]) if s == 0 else (k == M["ice_bounce"])
            u = IMP0 + DI * k + 0.012 * s
            if bounce:
                idx = min(len(PENT) - 1, 6 + k_bright // 2)
                k_bright += 1
                add("mech", u, f"packet {k} on {'snow' if s == 0 else 'ice'}: bounce", "setar", PENT[idx], 0.34,
                    t60=0.55, bright=0.45, lp=2200.0, dur=1.2)
            else:
                add("mech", u, f"packet {k} on {'snow' if s == 0 else 'ice'}: sinks in", "setar", PENT[0], 0.30,
                    t60=0.22, bright=0.0, lp=420.0, dur=0.6)
    T0, THETA = 0.62, lambda tau: 0.9 * tau + 0.5 * 1.15 * tau * tau      # the film's arrow: it turns faster and faster
    a, n = sc["mech"]
    cyc = (hz(0, 0), hz(2, 0), hz(4, 0))                            # G4 Bb4 D5: the three words
    j = 1
    while True:
        th = j * 2 * math.pi / 3
        tau = (-0.9 + math.sqrt(0.81 + 2 * 1.15 * th)) / 1.15
        u = T0 + tau / n
        if u > 0.985:
            break
        step = j // 3
        f = cyc[j % 3] * (2 if step >= 2 else 1)
        add("mech", u, f"ring turn {j} (every {2 * math.pi / 3 / (0.9 + 1.15 * tau):.2f} s)", "setar", f,
            0.38 + 0.03 * min(step, 4), t60=0.9, bright=0.3)
        j += 1

    # ---- budget: two pictures, then the gauge falls (u 0.60-0.80) ----
    add("budget", 0.04, "G4", "setar", hz(0, 0), 0.45)
    add("budget", 0.36, "swap of picture: D5", "setar", hz(4, 0), 0.5)
    for i, (s_, o_) in enumerate(((4, 0), (3, 0), (2, 0), (0, 0), (6, -1), (4, -1), (3, -1))):
        add("budget", 0.60 + 0.20 * i / 6, f"gauge tick {i}", "setar", hz(s_, o_), 0.38, t60=1.0)

    # ---- thr: the held note (a tone), bending when the bar reaches the threshold ----
    a, n = sc["thr"]
    add("thr", 0.20, "the red dot Bb4", "setar", hz(2, 0), 0.45)
    t0, t1 = at("thr", 0.27), at("thr", 0.85)
    ev.append(dict(t=t0, scene="thr", u=0.27, what="held D4 starts (the bar fills)", kind="held", f=hz(4, 0) / 2,
                   vel=0.03, dur=t1 - t0, bend=(at("thr", 0.45) - t0, at("thr", 0.56) - t0), cents=-200.0))
    ev.append(dict(t=at("thr", 0.45), scene="thr", u=0.45, what="the bar reaches the threshold: the note bends down a tone",
                   kind="mark", f=0.0, vel=0.0))

    # ---- fut: two falling lines ----
    for i, (s_, o_) in enumerate(((4, 0), (3, 0), (2, 0), (0, 0))):
        add("fut", 0.12 + 0.26 * i / 3, f"line 1 note {i}", "setar", hz(s_, o_), 0.48)
    long_line = ((4, 0), (3, 0), (2, 0), (0, 0), (6, -1), (4, -1), (3, -1), (0, -1))
    for i, (s_, o_) in enumerate(long_line):
        last = i == len(long_line) - 1
        add("fut", 0.46 + 0.40 * i / 7, f"line 2 note {i}" + (" lowest" if last else ""), "setar", hz(s_, o_),
            0.50 if not last else 0.62, t60=1.2 if not last else 2.0, lp=1600.0 if not last else 800.0)

    # ---- close: A-koron falls to home, the pad holds G and D ----
    add("close", 0.06, "D5", "setar", hz(4, 0), 0.45)
    add("close", 0.26, "Bb4", "setar", hz(2, 0), 0.45)
    add("close", 0.46, "A-koron4 (dashti's lean)", "setar", hz(1, 0), 0.50, t60=1.4)
    add("close", 0.58, "G4 home", "setar", HOME, 0.72, t60=2.6, dur=4.0)
    add("close", 0.58, "G3 home (low)", "setar", HOME_LO, 0.55, t60=2.6, dur=4.0, lp=900.0)
    ev.sort(key=lambda e: e["t"])
    return ev, end, sc


# the pad's chord for each scene (MIDI-free: dashti steps, octave on the G4 tonic)
PADS = {"hook": ((0, -1), (4, -1), (2, 0)), "face1": ((0, -1), (4, -1), (2, 0)), "dam": ((0, -1), (4, -1)),
        "takht": ((0, -1), (4, -1)), "mech": ((5, -2), (2, -1), (0, 0)), "budget": ((5, -2), (2, -1), (0, 0)),
        "thr": ((3, -2), (0, -1), (2, -1)), "fut": ((5, -2), (2, -1), (0, 0)), "close": ((0, -1), (4, -1), (0, 0))}
PAD_VEL, PULSE_VEL = 0.085, 0.10
PULSE_SCENES = ("face1", "dam", "takht", "budget", "fut")


def pulse_times(sc: dict) -> list:
    """A very soft pulse once per 2 beats of the films' 60 BPM grid, counted from each scene's start."""
    out = []
    for k in PULSE_SCENES:
        a, n = sc[k]
        t = a + 1.0
        while t < a + n - 1.0:
            out.append((k, t))
            t += 2.0
    return out


def render(ev: list, end: float, sc: dict) -> np.ndarray:
    kit.reseed(61)
    track = kit.new_track(end, TAIL)
    for i, e in enumerate(ev):
        pan = 0.2 if i % 2 == 0 else -0.2
        if e["kind"] == "setar":
            kit.place(track, pluck(e["f"], e["vel"], e.get("t60", 1.1), e.get("bright", 0.15), e.get("dur", 2.6),
                                   e.get("lp", 1600.0)), e["t"], 1.0, pan)
        elif e["kind"] == "held":
            kit.place(track, held(e["f"], e["dur"], e["vel"], e["bend"][0], e["bend"][1], e["cents"]), e["t"], 1.0, 0.0)
    for k, (a, n) in sc.items():                    # the pad: one chord per scene, overlapping the next
        extra = 0.0 if k == "close" else 1.0
        chord = [hz(s_, o_) for s_, o_ in PADS[k]]
        kit.place(track, kit.pad(chord, n + extra, vel=PAD_VEL, cutoff=650.0, attack=0.9, release=1.0), a)
    for k, t in pulse_times(sc):                    # the very soft pulse: a low muffled stroke
        x = sosfilt(_lp_sos(320.0), np.asarray(kit.tombak("tom", 1.0), float))
        kit.place(track, PULSE_VEL * x / max(1e-9, float(np.abs(x).max())), t, 1.0, 0.0)
    k = round(0.004 * SR)
    track[:k] *= np.linspace(0.0, 1.0, k)[:, None]
    return light._bass_mono(light._air_cut(track))


def band_db(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """RMS per second (dB) of the mono mix between lo and hi Hz."""
    m = x.mean(axis=1)
    y = sosfilt(butter(4, [lo, hi], "bandpass", fs=SR, output="sos"), m)
    n = len(y) // SR
    r = np.sqrt((y[:n * SR].reshape(n, SR) ** 2).mean(axis=1))
    return 20 * np.log10(np.maximum(r, 1e-9))


def main() -> None:
    film = json.loads(FILM.read_text(encoding="utf-8"))
    ev, end, sc = build(film)
    stem = render(ev, end, sc)
    music = kit.master(stem, lufs=LUFS_MUSIC, tp=TP, seconds=end, fade_out=1.0)
    bed = kit.master(stem, lufs=LUFS_BED, tp=TP, seconds=end, fade_out=1.0)
    wav, bedwav, mp4 = SOCIAL / f"{BASE}_music.wav", SOCIAL / f"{BASE}_bed.wav", SOCIAL / f"{BASE}_music_reel.mp4"
    kit.write_wav(wav, music)
    kit.write_wav(bedwav, bed)
    video = SOCIAL / f"{BASE}_reel.mp4"
    if video.exists():
        kit.mux(video, wav, mp4)
    else:
        print(f"(no {video.name}: no muxed mp4 written)")
    print(f"clock from {FILM.name}: end {end:.2f} s; scenes " + ", ".join(f"{k} {a:.2f}+{n:.2f}" for k, (a, n) in sc.items()))
    print("event table (t from the film's clock; u = fraction of the scene):")
    for e in ev:
        if e["kind"] != "mark":
            print(f"  {e['t']:7.2f} s  {e['scene']:<6} u={e['u']:.3f}  {e['f']:7.1f} Hz  vel {e['vel']:.2f}  {e['what']}")
        else:
            print(f"  {e['t']:7.2f} s  {e['scene']:<6} u={e['u']:.3f}  ---  {e['what']}")
    for p in pulse_times(sc)[:1]:
        print(f"  pulse: every 2 s from {p[0]} +1 s in {', '.join(PULSE_SCENES)} ({len(pulse_times(sc))} strokes)")
    out = []
    for name, path in (("music", wav), ("bed", bedwav)):
        x = light._read_wav(path)
        out.append((name, x))
        print(f"{name}: {kit.integrated_lufs(x):+.2f} LUFS, true peak {kit.true_peak_dbtp(x):+.2f} dBTP, "
              f"{len(x) / SR:.2f} s, {SR} Hz")
    m = out[0][1]
    rms = np.sqrt((m.mean(axis=1)[:len(m) // SR * SR].reshape(-1, SR) ** 2).mean(axis=1))
    db = 20 * np.log10(np.maximum(rms, 1e-9))
    print("music RMS per second (dB):", " ".join(f"{v:.0f}" for v in db))
    first = float(np.abs(m[:int(0.1 * SR)]).max())
    print(f"peak in the first 0.1 s: {20 * np.log10(max(first, 1e-9)):.1f} dBFS")
    quiet = np.where(db < -50)[0]
    print(f"seconds below -50 dB RMS: {len(quiet)} (silence longer than 4 s: "
          f"{'YES' if any(np.all(db[i:i + 4] < -50) for i in range(len(db) - 3)) else 'no'})")
    on = sorted(e["t"] for e in ev if e["kind"] in ("setar", "held"))
    gaps = np.diff(on)
    print(f"longest rest between setar onsets: {gaps.max():.2f} s (after {on[int(np.argmax(gaps))]:.2f} s)")
    b = out[1][1]
    mid = band_db(b, 300.0, 3000.0)
    print(f"bed 300 Hz-3 kHz RMS per second: max {mid.max():.1f} dBFS, median {np.median(mid):.1f} dBFS "
          f"(whole bed {kit.integrated_lufs(b):+.1f} LUFS)")


if __name__ == "__main__":
    main()
