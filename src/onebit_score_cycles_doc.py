"""The sound of the documentary cut of the ice-age film (cycles_fa, cut "d"; no narration): a layer of sound tied to
what the picture does, and three scores over it for the owner's ear to choose from. On 23 November 2026 he called the
plucked scores "very, very boring", asked for "very slower music ... penetrating into the brain", and then for more work
"on the music and the style". The scores are written without being heard (the writer has no ears): each is checked for
level, evenness and how much of it a phone's speaker can play, and that is all; the choice is his.

    the sound layer (in every version): a low blow and air at frame 0; the sea coming into the Gulf as a wash; a tick
        for every thousand years the counters run through; a whoosh into each scene; a chime when each marker of the
        corridor lands; a rise, a blow and a crack where the red line breaks out of the corridor; two soft knocks for
        the icons of the call
    deep    one sustained ground on D and A, a bowed kamancheh in Homayoun on D, one or two long notes to a bar of four
            seconds, a frame drum like a slow heart: brooding at the Gulf, climbing with the thaw, circling A in the
            corridor (a tune that stays in a narrow band, as the temperature does), up and not home at the break-out
    pulse   the same ground and tune over a groove of daf and tombak at about 100 beats a minute and a santur figure in
            eighths: sparse at the Gulf, in full in the corridor, a silence just before the break-out, harder after it
    epic    no tune: a clock's tick (two a second) through the whole film, the ground swelling scene by scene, a low
            horn-like call at the head of each scene, a long rise into the break-out, and after it only the tick

    python -I src/onebit_score_cycles_doc.py [deep pulse epic sfx]   # outputs/onebit/social/cycles_fa_doc_<kind>_music.wav and,
                                                                     # when the silent reel is there, ..._<kind>_music_reel.mp4
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
import onebit_persian as kit  # noqa: E402
import onebit_score_air_light as light  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FILM = ROOT / "outputs" / "onebit" / "cycles" / "film.json"
BASE = "cycles_fa_doc"
SR = kit.SR
KINDS = ("deep", "pulse", "epic", "sfx")
# the level: Meta publishes no target for Reels and evens loudness out at playback (its engineering blog, 11 Apr 2023);
# the practice of mastering engineers for short video is about -14 LUFS with the true peak at or under -1 dBTP. The
# owner found his earlier scores (-22) "boring"; this is 6 dB up from them and still 2 dB under that practice.
LUFS, MASTER_TP, TP_AAC = -16.0, -1.5, -1.0
MODE = "homayoun"                                     # D, E flat, F sharp, G, A, B flat, C
TONIC = kit.note_hz("D4")
ROOM, ROOM_T60 = 0.34, 3.2                            # a large room, well in
TOP_HZ = 5600.0                                       # a dark top


def hz(step: int, octave: int = 0) -> float:
    return kit.degree(MODE, step, octave, TONIC)


# ── sounds the kit does not have ──
def whoosh(rng, dur: float = 0.7, vel: float = 0.3, lo: float = 280.0, hi: float = 3400.0) -> np.ndarray:
    """Air passing from left to right: noise that moves from a low band to a high one under a rounded swell."""
    n = int(dur * SR)
    u = np.arange(n) / n
    x = rng.standard_normal(n)
    y = (1 - u) * kit._bp(x, lo, 3 * lo) + u * kit._bp(x, hi / 3, hi)
    y = kit._peak(y * np.sin(np.pi * u) ** 2, 1.0)
    pan = (-0.7 + 1.4 * u + 1) * np.pi / 4
    return vel * np.stack([y * np.cos(pan), y * np.sin(pan)], axis=1)


def wash(rng, dur: float, vel: float = 0.25) -> np.ndarray:
    """The sea coming in: low noise in stereo that swells, breathes and settles."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    u = t / dur
    x = kit._lp(rng.standard_normal((n, 2)), 1100.0) + 0.35 * kit._bp(rng.standard_normal((n, 2)), 1500.0, 4000.0)
    env = np.sin(np.pi * np.clip(u, 0, 1)) ** 1.4 * (0.8 + 0.2 * np.sin(2 * np.pi * 2.3 * t))
    return vel * kit._peak(x * env[:, None], 1.0)


def tick(vel: float = 0.1, f: float = 1900.0) -> np.ndarray:
    """A small wooden click."""
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    return vel * (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * 2.7 * f * t)) * np.exp(-t / 0.007) / 1.5


def crack(rng, vel: float = 0.3) -> np.ndarray:
    """Something giving way: a short burst of bright noise and two later splinters."""
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    x = kit._hp(rng.standard_normal(n), 2200.0) * np.exp(-t / 0.035)
    for d in (0.09, 0.2):
        k = int(d * SR)
        x[k:] += 0.5 * kit._hp(rng.standard_normal(n - k), 3000.0) * np.exp(-t[:n - k] / 0.02)
    return vel * kit._peak(x, 1.0)


def horn(freq: float, dur: float = 2.6, vel: float = 0.3) -> np.ndarray:
    """A low, horn-like call: the pad's sawtooths on one note and its fifth, quick in and slow out."""
    return kit.pad([freq, 1.5 * freq, 2 * freq], dur, vel=vel, width=0.5, detune=9.0, cutoff=700.0, attack=0.12, release=1.8)


class Mix:
    def __init__(self, end: float, seed: int):
        self.track = kit.new_track(end, 6.0)
        self.onsets: list[float] = []
        self.rng = np.random.default_rng(seed)

    def put(self, sound, t: float, gain: float = 1.0, pan: float = 0.0) -> None:
        kit.place(self.track, sound, max(0.0, t), gain, pan)
        self.onsets.append(max(0.0, t))


def layer(mx: Mix, c: dict, q: dict, level: float = 1.0) -> None:
    """The sound layer: what the picture does, heard."""
    rng, put = mx.rng, mx.put
    put(kit.impact(2.0, vel=0.26 * level, pitch=55.0), 0.0)                              # frame 0
    put(whoosh(rng, 0.9, 0.16 * level, 200.0, 2200.0), 0.0)
    a0, a1, old, young = q["gulf"]["age"]
    put(wash(rng, a1 - a0 + 1.2, 0.2 * level), c["gulf"][0] + a0)                          # the sea
    for key in ("gulf", "thaw"):                                                           # the counters: a tick a thousand years
        a0, a1, old, young = q[key]["age"]
        for k, ka in enumerate(np.arange(np.floor(old) - 1, young - 0.5, -1.0)):
            p = (old - ka) / (old - young)                                                 # the page eases the age in and out: p = 3u^2 - 2u^3
            u = float(np.clip(np.roots([-2.0, 3.0, 0.0, -p])[1].real, 0, 1)) if 0 < p < 1 else p
            put(tick(0.085 * level, 1700.0 + 60.0 * (k % 3)), c[key][0] + a0 + u * (a1 - a0), 1.0, 0.25 * (-1) ** k)
    for key in ("thaw", "life", "exit", "send"):                                           # into each scene
        put(whoosh(rng, 0.6, 0.2 * level), c[key][0] - 0.42)
        put(kit.daf("bam", vel=0.2 * level, pitch=70.0), c[key][0] + 0.02)
    put(whoosh(rng, 0.5, 0.14 * level), c["gulf"][0] + q["gulf"]["turn"] - 0.35)           # the headline turns
    for k, m in enumerate(q["life"]["marks"]):                                             # the markers: a chime, and the photograph landing
        t = c["life"][0] + m
        for j, (step, octave) in enumerate(((0, 1), (4, 1), (0, 2))):
            put(kit.santur(hz(step, octave), dur=3.4, vel=(0.2 - 0.03 * j) * level, t60=2.6, detune=2.0, spread=0.35, bright=0.28), t + 0.1 * j, 1.0, 0.3 - 0.3 * j)
        put(kit.tombak("tom", vel=0.16 * level, pitch=82.0), t - 0.5)
    out = c["exit"][0] + 0.5 * sum(q["exit"]["spike"])                                     # the break-out
    put(kit.riser(1.5, vel=0.22 * level, f0=140.0, f1=950.0), out - 1.5)
    put(kit.impact(2.6, vel=0.44 * level, pitch=49.0), out)
    put(crack(rng, 0.24 * level), out + 0.02, 1.0, 0.3)
    for k, dt in enumerate((0.0, 0.16)):                                                   # the icons of the call
        put(kit.tombak("bak", vel=0.1 * level, pitch=520.0 + 80.0 * k), c["send"][0] + q["send"]["icon"] + dt, 1.0, -0.2 + 0.4 * k)


def ground(mx: Mix, c: dict, levels: dict, bright: float = 1.0) -> None:
    """One pad under every scene, swelling in before it and out after it (D3 and up: a phone plays nothing under 150 Hz)."""
    low = dict(D=kit.note_hz("D3"), A=kit.note_hz("A3"), d=kit.note_hz("D4"), Fs=kit.note_hz("F#4"), Eb=kit.note_hz("Eb4"), a=kit.note_hz("A4"))
    notes = dict(gulf=("D", "A", "d"), thaw=("D", "A", "d"), life=("D", "A", "d", "Fs", "a"), exit=("D", "A", "d", "Eb"), send=("D", "A", "d", "Fs"))
    end = max(b for _, b in c.values())
    for i, key in enumerate(k for k in notes if k in c):
        t0, t1 = c[key]
        start, stop = (t0 if i == 0 else t0 - 1.4), min(t1 + 1.6, end + 3.0)
        mx.put(kit.pad([low[n] for n in notes[key]], stop - start, vel=levels[key], width=0.85, detune=6.0,
                       cutoff=(1300.0 if key != "exit" else 1900.0) * bright, attack=0.5 if i == 0 else 2.2, release=2.8), start)
        mx.put(kit.sub(low["D"] / 2, stop - start - 0.4, vel=0.045, drive=0.5), start + 0.2)


def voice(mx: Mix, c: dict, q: dict, level: float = 1.0) -> None:
    """The kamancheh, long bows, with its own octave under it: the tune keeps the scenes' own times."""
    def sing(t: float, dur: float, step: int, octave: int = 0, vel: float = 0.5) -> None:
        f = hz(step, octave)
        mx.put(kit.kamancheh(f, dur=dur + 0.25, vel=vel * level, vib_hz=4.6, vib_cents=22.0, bow=min(0.7, 0.3 * dur)), t, 1.0, -0.12)
        mx.put(kit.kamancheh(f / 2, dur=dur + 0.25, vel=0.42 * vel * level, vib_hz=4.2, vib_cents=14.0, bow=min(0.9, 0.36 * dur)), t + 0.03, 1.0, 0.16)

    g0, th0, l0, e0, s0 = (c[k][0] for k in ("gulf", "thaw", "life", "exit", "send"))
    m1, m2, m3 = q["life"]["marks"]
    last = q["life"]["last"]
    x1 = q["exit"]["small"][-1]
    for t, dur, step, octave, vel in (
            (g0 + 0.7, 3.1, 0, -1, 0.44), (g0 + 4.0, 2.5, 1, -1, 0.42), (g0 + 6.7, 2.6, 0, -1, 0.44),                         # gulf: D, E flat, D, low
            (th0 + 0.2, 2.3, 0, 0, 0.46), (th0 + 2.5, 1.5, 1, 0, 0.44), (th0 + 4.0, 2.0, 2, 0, 0.48), (th0 + 6.0, 2.1, 3, 0, 0.5),   # thaw: the climb
            (l0 + 0.15, m1 - 0.7, 4, 0, 0.52), (l0 + m1 - 0.2, 1.5, 5, 0, 0.44), (l0 + m1 + 1.4, m2 - m1 - 1.6, 4, 0, 0.5),         # life: around A
            (l0 + m2 - 0.1, 1.5, 3, 0, 0.44), (l0 + m2 + 1.5, m3 - m2 - 1.7, 2, 0, 0.44), (l0 + m3 - 0.1, last - m3 - 0.1, 4, 0, 0.54),
            (l0 + last, 3.2, 7, 0, 0.5),
            (e0 + 0.15, 1.3, 5, 0, 0.5), (e0 + 1.5, 2.4, 7, 0, 0.56), (e0 + 3.95, x1 - 3.7, 8, 0, 0.52), (e0 + x1 + 0.3, 2.8, 7, 0, 0.44),   # exit: up, and not home
            (s0 + 0.15, 2.5, 2, 0, 0.44), (s0 + 2.75, 1.3, 3, 0, 0.42), (s0 + 4.1, 3.6, 4, 0, 0.46)):                           # send: the tune, and the fifth
        sing(t, dur, step, octave, vel)


def heart(mx: Mix, c: dict, beat: dict) -> None:
    """A frame drum, two soft strokes, slow; faster where the curve leaves the corridor."""
    for key, (every, vel) in beat.items():
        t = c[key][0] + 0.9
        while t < c[key][1] - 0.5:
            for k, (dt, g) in enumerate(((0.0, 1.0), (0.34, 0.62))):
                mx.put(kit.daf("bam", vel=0.8 * vel * g * (1 + mx.rng.normal(0, 0.05)), pitch=104.0 - 8.0 * k), t + dt + mx.rng.normal(0, 0.006))
            t += every


def groove(mx: Mix, c: dict, q: dict) -> None:
    """Daf, tombak and a santur figure in eighths, about 100 beats a minute; every scene holds a whole number of beats."""
    beats = dict(gulf=16, thaw=14, life=28, exit=16, send=14)
    drum = dict(gulf=0.45, thaw=0.75, life=1.0, exit=1.2, send=0.5)                       # how much of the groove a scene gets
    figure = dict(gulf=(0, 4, 7, 4), thaw=(0, 4, 7, 4), life=(0, 2, 4, 7), exit=(0, 1, 4, 7), send=(0, 4, 7, 4))   # scale steps, an eighth each
    out = c["exit"][0] + 0.5 * sum(q["exit"]["spike"])
    for key, nb in beats.items():
        t0, t1 = c[key]
        b = (t1 - t0) / nb
        assert 0.52 < b < 0.68, (key, b)
        g = drum[key]
        for k in range(nb):
            tb = t0 + k * b
            if out - 0.45 < tb < out - 0.02:
                continue                                                                   # the breath before the break-out
            hard = 1.25 if key == "exit" and tb >= out else 1.0
            j = lambda s=0.006: mx.rng.normal(0, s)                                        # noqa: E731
            if k % 2 == 0:
                mx.put(kit.daf("bam", vel=0.34 * g * hard, pitch=112.0), tb + j())     # high enough for a phone to play its body (250 to 700 Hz with its partials)
                if g >= 0.7:
                    mx.put(kit.daf("tak", vel=0.15 * g * hard), tb + 0.75 * b + j())
                    mx.put(kit.tombak("tom", vel=0.13 * g, pitch=165.0), tb + 0.5 * b + j())
            else:
                if g >= 0.7:
                    mx.put(kit.daf("tak", vel=0.18 * g * hard), tb + 0.5 * b + j())
                    mx.put(kit.tombak("bak", vel=0.08 * g), tb + 0.25 * b + j(), 1.0, 0.3)
                if g >= 1.0:
                    mx.put(kit.daf("zang", vel=0.05 * g), tb + j())
            for e in range(2):                                                             # the santur, two eighths a beat
                step = figure[key][(2 * k + e) % 4]
                mx.put(kit.santur(hz(step % 7, step // 7), dur=1.4, vel=(0.13 if e == 0 and k % 2 == 0 else 0.09) * min(1.0, 0.55 + 0.5 * g),
                                  t60=1.1, detune=2.0, spread=0.3, bright=0.3), tb + 0.5 * e * b + j(0.004), 1.0, 0.35 if e else -0.35)


def clockwork(mx: Mix, c: dict, q: dict) -> None:
    """No tune: a clock's tick through the whole film, a horn-like call at the head of each scene, a long rise."""
    end = max(b for _, b in c.values())
    out = c["exit"][0] + 0.5 * sum(q["exit"]["spike"])
    t, k = 0.25, 0
    while t < end - 1.5:
        mx.put(tick(0.16 if k % 4 == 0 else 0.1, 1500.0 if k % 2 == 0 else 1250.0), t, 1.0, 0.15 if k % 2 else -0.15)
        t, k = t + 0.5, k + 1
    for key, f, vel in (("gulf", "D2", 0.26), ("thaw", "D2", 0.28), ("life", "A2", 0.26), ("exit", "D2", 0.34), ("send", "D2", 0.22)):
        mx.put(horn(kit.note_hz(f) * 2, 2.8, vel), c[key][0] + 0.05)
    mx.put(kit.riser(3.2, vel=0.2, f0=110.0, f1=1100.0), out - 3.2)                        # the long rise into the break-out
    l0 = c["life"][0]
    for k, m in enumerate(q["life"]["marks"]):                                             # one long note for each picture, a third apart
        mx.put(kit.kamancheh(hz((2, 4, 7)[k], 0), dur=3.0, vel=0.3, vib_hz=4.4, vib_cents=16.0, bow=0.9), l0 + m - 0.1)


def score(film: dict, kind: str) -> tuple:
    cut = film["cuts"]["d"]
    c = {s["key"]: (s["start"], s["start"] + s["length"]) for s in cut["scenes"]}
    q, end = film["cues"], cut["end"]
    mx = Mix(end, 41 + KINDS.index(kind))
    layer(mx, c, q, level=1.25 if kind == "sfx" else 1.0)
    if kind == "deep":
        ground(mx, c, dict(gulf=0.20, thaw=0.21, life=0.22, exit=0.25, send=0.20))
        heart(mx, c, dict(gulf=(2.9, 0.20), thaw=(2.9, 0.18), life=(3.6, 0.13), exit=(1.45, 0.26), send=(3.6, 0.12)))
        voice(mx, c, q)
    elif kind == "pulse":
        ground(mx, c, dict(gulf=0.15, thaw=0.16, life=0.17, exit=0.2, send=0.16))
        groove(mx, c, q)
        voice(mx, c, q, level=0.9)
    elif kind == "epic":
        ground(mx, c, dict(gulf=0.16, thaw=0.2, life=0.24, exit=0.3, send=0.18), bright=1.15)
        clockwork(mx, c, q)
    wet = kit.reverb(mx.track, t60=ROOM_T60, predelay=0.03, seed=17)[:len(mx.track)]
    track = mx.track + (ROOM if kind != "sfx" else 0.22) * wet
    track = sosfiltfilt(butter(4, TOP_HZ if kind != "sfx" else 9000.0, "lowpass", fs=SR, output="sos"), track, axis=0)
    return light._bass_mono(track), sorted(mx.onsets), end


def build(film: dict, kind: str, look: str) -> list:
    social = onebit.OUT / "social"
    video = social / (f"{BASE}_reel.mp4" if look == "night" else f"{BASE}_{look}_reel.mp4")
    wav = social / f"{BASE}_{kind}_music.wav"
    mp4 = social / (f"{BASE}_{kind}_music_reel.mp4" if look == "night" else f"{BASE}_{look}_{kind}_music_reel.mp4")
    kit.reseed(67 + KINDS.index(kind))
    track, onsets, end = score(film, kind)
    music = kit.master(track, lufs=LUFS if kind != "sfx" else LUFS - 6.0, tp=MASTER_TP, seconds=end, fade_out=1.6)
    light.write_wav(wav, music)
    m = light._read_wav(wav)
    lufs, tp = kit.integrated_lufs(m), kit.true_peak_dbtp(m)
    mono = m.mean(axis=1)
    rms = [20 * np.log10(np.sqrt(np.mean(mono[k:k + SR] ** 2)) + 1e-12) for k in range(0, len(mono) - SR, SR // 10)]
    body = rms[:int((end - 2.0) * 10)]
    spec = np.abs(np.fft.rfft(mono * np.hanning(len(mono)))) ** 2
    freq = np.fft.rfftfreq(len(mono), 1 / SR)
    share = lambda lo, hi: float(spec[(freq >= lo) & (freq < hi)].sum() / spec.sum())   # noqa: E731
    aim = LUFS if kind != "sfx" else LUFS - 6.0
    fails = []
    print(f"\n{kind}\nlevel     {lufs:+.2f} LUFS (aim {aim:+.0f}); true peak WAV {tp:+.2f} dBTP")
    if abs(lufs - aim) > 0.6:
        fails.append("level")
    print(f"evenness  one-second windows before the ending: quietest {min(body):.1f} dBFS, loudest {max(body):.1f} dBFS")
    if kind != "sfx" and (min(body) < -60 or max(body) - min(body) > 18):
        fails.append("uneven")
    print(f"spectrum  energy below 150 Hz {100 * share(0, 150):.0f} %, 150-800 Hz {100 * share(150, 800):.0f} %, above 800 Hz {100 * share(800, 24000):.0f} %")
    if share(150, 24000) < 0.4:
        fails.append("too little above 150 Hz for a phone speaker")
    print(f"sounds    {len(onsets)}; first at {onsets[0]:.3f} s")
    print("saved", wav)
    if video.exists():
        kit.mux(video, wav, mp4)
        aac = kit.aac_true_peak(mp4)
        print(f"decoded AAC true peak {aac:+.2f} dBTP")
        if aac > TP_AAC:
            fails.append("AAC peak")
        if light._md5(video, "0:v:0") != light._md5(mp4, "0:v:0"):
            fails.append("the picture changed")
        print("saved", mp4)
    else:
        print("no silent reel yet:", video.name)
    return [f"{kind}: {f}" for f in fails]


def main() -> None:
    args = [a for a in sys.argv[1:] if a not in ("night", "light")]
    look = "light" if "light" in sys.argv[1:] else "night"
    kinds = args or list(KINDS)
    assert all(k in KINDS for k in kinds), kinds
    film = json.loads(FILM.read_text(encoding="utf-8"))
    fails = [f for k in kinds for f in build(film, k, look)]
    if fails:
        sys.exit("CHECKS NOT PASSED: " + "; ".join(fails))
    print("\nall checks pass")


if __name__ == "__main__":
    main()
