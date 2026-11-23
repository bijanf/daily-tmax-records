"""A slow, deep score for the documentary cut of the ice-age film (cycles_fa, cut "d"; no narration). The owner on
23 November 2026: the plucked scores are "very, very boring"; he asked for "very slower music ... penetrating into the
brain". So nothing here is plucked in a row: one sustained ground (a pad on D and A with a sub under it) runs through the
whole film, a bowed kamancheh sings long notes of Homayoun on D over it, one or two to a bar of four seconds, a frame
drum beats like a slow heart, and the room is large. The music follows the story of the cut:

    gulf   the ground alone and a low, brooding D - E flat - D (the half step that names Homayoun)
    thaw   the line climbs with the curve: D, E flat, F sharp, G
    life   it arrives on A and circles it (A, B flat, A, G, F sharp, A): a tune that stays in a narrow band, as the
           temperature does; the ground gains the major third, a santur chimes when each marker lands, and the tune
           rises to the octave when the conclusion comes in over Persepolis
    exit   the third leaves, E flat comes into the ground, the heart beats faster, a rise and a low blow when the curve
           breaks out of the corridor; the tune goes up and does not come home (D, E flat above it)
    co2    low again, D and E flat, a second, softer rise to the carbon dioxide's spike
    send   the corridor's tune comes back, quieter, and stops on the fifth

    python -I src/onebit_score_cycles_deep.py     # outputs/onebit/social/cycles_fa_doc_deep_music.wav and, when the
                                                  # silent reel is there, cycles_fa_doc_deep_music_reel.mp4
                                                  # (the picture untouched); pass "light" for the light look's reel
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
from onebit_score_khazar_soft import LUFS, MASTER_TP, TP_AAC  # noqa: E402  (the same level as the soft scores)

ROOT = Path(__file__).resolve().parents[1]
FILM = ROOT / "outputs" / "onebit" / "cycles" / "film.json"
BASE = "cycles_fa_doc"
SR = kit.SR
MODE = "homayoun"                                     # D, E flat, F sharp, G, A, B flat, C
TONIC = kit.note_hz("D4")
ROOM, ROOM_T60 = 0.36, 3.4                            # a large room, well in
TOP_HZ = 5200.0                                       # nothing above this: a dark top


def hz(step: int, octave: int = 0) -> float:
    return kit.degree(MODE, step, octave, TONIC)


def score(film: dict) -> tuple:
    cut = film["cuts"]["d"]
    c = {s["key"]: (s["start"], s["start"] + s["length"]) for s in cut["scenes"]}
    q, end = film["cues"], cut["end"]
    rng = np.random.default_rng(41)
    track = kit.new_track(end, 6.0)
    onsets: list[float] = []

    def put(sound, t: float, gain: float = 1.0, pan: float = 0.0) -> None:
        kit.place(track, sound, max(0.0, t), gain, pan)
        onsets.append(max(0.0, t))

    # ── the ground: a pad under every scene, each one swelling in before its scene and out after it ──
    # (D3 and up: a phone's speaker plays next to nothing under 150 Hz, so the ground lives where it can be heard)
    low = dict(D=kit.note_hz("D3"), A=kit.note_hz("A3"), d=kit.note_hz("D4"), Fs=kit.note_hz("F#4"), Eb=kit.note_hz("Eb4"), a=kit.note_hz("A4"))
    ground = dict(gulf=("D", "A", "d"), thaw=("D", "A", "d"), life=("D", "A", "d", "Fs", "a"), exit=("D", "A", "d", "Eb"),
                  co2=("D", "A", "d", "Eb"), send=("D", "A", "d", "Fs"))
    level = dict(gulf=0.20, thaw=0.21, life=0.22, exit=0.25, co2=0.23, send=0.20)
    for i, (key, notes) in enumerate(ground.items()):
        t0, t1 = c[key]
        a, r = (0.5 if i == 0 else 2.2), 2.8
        start, stop = (t0 if i == 0 else t0 - 1.4), min(t1 + 1.6, end + 3.0)
        put(kit.pad([low[n] for n in notes], stop - start, vel=level[key], width=0.85, detune=6.0, cutoff=1300.0 if key != "exit" else 1900.0, attack=a, release=r), start)
        put(kit.sub(low["D"] / 2, stop - start - 0.4, vel=0.045, drive=0.5), start + 0.2)    # D2, quiet: depth for headphones
    put(kit.setar(low["D"], dur=4.0, vel=0.34, t60=3.2, bright=0.15, buzz=0.04), 0.0, 1.0, 0.0)   # the first sound, at frame 0

    # ── the heart: a frame drum, two soft strokes, slow; faster where the curve leaves the corridor ──
    beat = dict(gulf=(2.9, 0.20), thaw=(2.9, 0.18), life=(3.6, 0.13), exit=(1.45, 0.26), co2=(2.0, 0.20), send=(3.6, 0.12))
    for key, (every, vel) in beat.items():
        t = c[key][0] + 0.9
        while t < c[key][1] - 0.5:
            for k, (dt, g) in enumerate(((0.0, 1.0), (0.34, 0.62))):
                put(kit.daf("bam", vel=0.8 * vel * g * (1 + rng.normal(0, 0.05)), pitch=104.0 - 8.0 * k), t + dt + rng.normal(0, 0.006))
            t += every

    # ── the voice: a kamancheh, long bows, with its own octave under it ──
    def sing(t: float, dur: float, step: int, octave: int = 0, vel: float = 0.5, deep: bool = True) -> None:
        f = hz(step, octave)
        put(kit.kamancheh(f, dur=dur + 0.25, vel=vel, vib_hz=4.6, vib_cents=22.0, bow=min(0.7, 0.3 * dur)), t, 1.0, -0.12)
        if deep:
            put(kit.kamancheh(f / 2, dur=dur + 0.25, vel=0.42 * vel, vib_hz=4.2, vib_cents=14.0, bow=min(0.9, 0.36 * dur)), t + 0.03, 1.0, 0.16)

    g0, th0, l0, e0, c0, s0 = (c[k][0] for k in ("gulf", "thaw", "life", "exit", "co2", "send"))
    m1, m2, m3 = q["life"]["marks"]                       # the corridor's tune keeps the scene's own time: a long A under its
    last = q["life"]["last"]                              # headline, a turn at each marker, the octave when the conclusion comes
    for t, dur, step, octave, vel in (
            (g0 + 0.7, 3.1, 0, -1, 0.44), (g0 + 4.0, 2.5, 1, -1, 0.42), (g0 + 6.7, 3.0, 0, -1, 0.44),                      # gulf: D, E flat, D, low
            (th0 + 0.2, 2.3, 0, 0, 0.46), (th0 + 2.5, 1.5, 1, 0, 0.44), (th0 + 4.0, 2.0, 2, 0, 0.48), (th0 + 6.0, 2.1, 3, 0, 0.5),   # thaw: the climb
            (l0 + 0.15, m1 - 0.7, 4, 0, 0.52), (l0 + m1 - 0.2, 1.5, 5, 0, 0.44), (l0 + m1 + 1.4, m2 - m1 - 1.6, 4, 0, 0.5),        # life: around A
            (l0 + m2 - 0.1, 1.6, 3, 0, 0.44), (l0 + m2 + 1.6, m3 - m2 - 1.8, 2, 0, 0.44), (l0 + m3 - 0.1, last - m3 - 0.1, 4, 0, 0.54),
            (l0 + last, 3.2, 7, 0, 0.5),
            (e0 + 0.15, 1.3, 5, 0, 0.5), (e0 + 1.5, 2.4, 7, 0, 0.56), (e0 + 3.95, 2.9, 8, 0, 0.52),                          # exit: up, and not home
            (c0 + 0.15, 3.0, 0, -1, 0.46), (c0 + 3.25, 1.9, 1, -1, 0.46), (c0 + 6.1, 3.4, 0, -1, 0.44),                      # co2: low again
            (s0 + 0.15, 2.5, 2, 0, 0.44), (s0 + 2.75, 1.3, 3, 0, 0.42), (s0 + 4.1, 3.6, 4, 0, 0.46)):                        # send: the tune, and the fifth
        sing(t, dur, step, octave, vel)

    # ── the chimes: a santur when each marker of the corridor lands, and at the end ──
    for t in [l0 + m for m in q["life"]["marks"]] + [s0 + 6.4]:
        for k, (step, octave) in enumerate(((0, 1), (4, 1), (0, 2))):
            put(kit.santur(hz(step, octave), dur=3.6, vel=0.20 - 0.03 * k, t60=2.8, detune=2.0, spread=0.35, bright=0.28), t + 0.11 * k, 1.0, 0.3 - 0.3 * k)

    # ── the break: a rise and a low blow where the red line goes through the corridor's top; a softer one at the carbon dioxide's spike ──
    out = e0 + 0.5 * sum(q["exit"]["spike"])
    put(kit.riser(1.4, vel=0.22, f0=140.0, f1=900.0), out - 1.4)
    put(kit.impact(2.6, vel=0.42, pitch=49.0), out)
    up = c0 + q["co2"]["spike"][1]
    put(kit.riser(1.1, vel=0.15, f0=120.0, f1=700.0), up - 1.1)
    put(kit.impact(2.2, vel=0.26, pitch=49.0), up)

    wet = kit.reverb(track, t60=ROOM_T60, predelay=0.03, seed=17)[:len(track)]
    track = track + ROOM * wet
    track = sosfiltfilt(butter(4, TOP_HZ, "lowpass", fs=SR, output="sos"), track, axis=0)
    return light._bass_mono(track), sorted(onsets), end


def build(film: dict, look: str) -> list:
    social = onebit.OUT / "social"
    video = social / (f"{BASE}_reel.mp4" if look == "night" else f"{BASE}_{look}_reel.mp4")
    wav = social / f"{BASE}_deep_music.wav"
    mp4 = social / (f"{BASE}_deep_music_reel.mp4" if look == "night" else f"{BASE}_{look}_deep_music_reel.mp4")
    kit.reseed(67)
    track, onsets, end = score(film)
    music = kit.master(track, lufs=LUFS, tp=MASTER_TP, seconds=end, fade_out=1.6)
    light.write_wav(wav, music)
    m = light._read_wav(wav)
    lufs, tp = kit.integrated_lufs(m), kit.true_peak_dbtp(m)
    mono = m.mean(axis=1)
    rms = [20 * np.log10(np.sqrt(np.mean(mono[k:k + SR] ** 2)) + 1e-12) for k in range(0, len(mono) - SR, SR // 10)]
    body = rms[:int((end - 2.0) * 10)]
    spec = np.abs(np.fft.rfft(mono * np.hanning(len(mono))))
    freq = np.fft.rfftfreq(len(mono), 1 / SR)
    share = lambda lo, hi: float((spec[(freq >= lo) & (freq < hi)] ** 2).sum() / (spec ** 2).sum())   # noqa: E731
    fails = []
    print(f"\ndeep\nlevel     {lufs:+.2f} LUFS (aim {LUFS:+.0f}); true peak WAV {tp:+.2f} dBTP")
    if abs(lufs - LUFS) > 0.5:
        fails.append("level")
    print(f"evenness  one-second windows before the ending: quietest {min(body):.1f} dBFS, loudest {max(body):.1f} dBFS")
    if min(body) < -60 or max(body) - min(body) > 16:
        fails.append("uneven")
    print(f"spectrum  energy below 150 Hz {100 * share(0, 150):.0f} %, 150-800 Hz {100 * share(150, 800):.0f} %, above 800 Hz {100 * share(800, 24000):.0f} %")
    if share(150, 24000) < 0.25:
        fails.append("too little above 150 Hz for a phone speaker")
    print(f"notes     {len(onsets)}; first at {onsets[0]:.3f} s")
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
    return fails


def main() -> None:
    look = sys.argv[1] if len(sys.argv) > 1 else "night"
    assert look in ("night", "light"), look
    film = json.loads(FILM.read_text(encoding="utf-8"))
    fails = build(film, look)
    if fails:
        sys.exit("CHECKS NOT PASSED: " + "; ".join(fails))
    print("\nall checks pass")


if __name__ == "__main__":
    main()
