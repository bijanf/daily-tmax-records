"""The 31-s score of the land-subsidence reel with the news cards (subsidence_fa, 26 s + 5 s of headlines).

The 26-s score of onebit_score_subsidence is composed as it is, but not wrapped at 26 s: what rings past 26 s (the
question's notes, the room, the reversed strike that swells into 26.0 s) now plays on under the cards. At 26.0 s the
opening sounds again (the santur strike D2 D3 A3 and the tombak, with the drone and the air from 0 s: both are exactly
periodic over 26 s, so they run on without a seam), without the count; each card enters on a setar note a step lower
(A4, G4, F#4, the labels' motif) with a soft daf. Over 30.4-31.0 s the bed eases down 9 dB into the loop point, where the
strike opens the reel again. What rings past 31 s is wrapped onto the start.

The narrated cut: the same sentences, their timing and the same ducking (depth and lead per sentence) as the 26-s score
(nothing is spoken after 25.7 s); the voice keeps the level it has in the 26-s mix. Writes subsidence_fa_music.wav and
subsidence_fa_voice.wav (48 kHz, 16 bit, exactly 31.000 s, -14 LUFS, true peak -2 dBTP or lower) and checks them.

    python -I src/onebit_score_subsidence_news.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from scipy.signal import butter, sosfiltfilt  # noqa: E402

import onebit_persian as kit  # noqa: E402
import onebit_score_subsidence as S  # noqa: E402

SR = S.SR
END = 31.0                                       # s: the reel with the cards (onebit_subsidence.END)
NE = int(round(END * SR))
HEAD = END - S.DUR                               # 5 s: the opening again, under the cards
CARDS = ((26.0, "A4", -0.25), (26.7, "G4", 0.25), (27.4, "F#4", -0.25))   # onebit_subsidence.NEWS_IN
LIFT = (30.4, 31.0)
LIFT_DB = -9.0


def unwrapped(bus: dict, c: dict) -> np.ndarray:
    """S.music_bus without the wrap: the buses and the room, N + TAIL samples."""
    n = len(bus["fx"])
    room = S._fit(kit.reverb(bus["send"], t60=2.6, predelay=0.02), n) * 0.55
    t = np.arange(n) / SR
    dip = 1.0 - 0.5 * np.clip((t - c["cut"]) / 0.05, 0, 1) * np.clip((c["land"] - t) / 0.02, 0, 1)
    room *= dip[:, None]
    return sum(bus[k] for k in S.BUSES if k != "send") + room


def head(bus: dict) -> np.ndarray:
    """The 5 s under the cards (HEAD + TAIL samples): the drone and the air of 0-5 s, the strike, the cards' notes, the
    room on them, the bed eased down over LIFT."""
    h = kit.new_track(HEAD, S.TAIL)
    m = round(HEAD * SR)
    bed = bus["drone"][:m] + bus["air"][:m]
    tt = 26.0 + np.arange(m) / SR
    bed = bed * (10 ** (LIFT_DB / 20 * np.clip((tt - LIFT[0]) / (LIFT[1] - LIFT[0]), 0, 1)))[:, None]
    h[:m] += bed
    send = kit.new_track(HEAD, S.TAIL)
    strike = S.santur_note("D3", 0.13, dur=4.0, t60=3.2) + S.santur_note("A3", 0.08, dur=4.0, t60=3.0) \
        + S.santur_note("D2", 0.08, dur=4.0, t60=3.4)
    tom = kit.tombak("tom", pitch=S.hz("D2"))
    kit.place(h, strike, 0.0, 1.0, 0.0)
    kit.place(send, strike, 0.0, S.SENDS["hook"], 0.0)
    kit.place(h, tom, 0.0, 0.12, 0.0)
    kit.place(send, tom, 0.0, 0.12 * S.SENDS["perc"], 0.0)
    bam = kit.daf("bam", pitch=S.hz("D2"))
    for t, note, pan in CARDS:
        x = S.setar_note(note, 0.32)
        kit.place(h, x, t - 26.0, 0.8, pan)
        kit.place(send, x, t - 26.0, 0.8 * S.SENDS["setar"], pan)
        kit.place(h, bam, t - 26.0, 0.5 * 10 ** (-10 / 20), 0.0)
    room = S._fit(kit.reverb(send, t60=2.6, predelay=0.02), len(h)) * 0.55
    return h + room


def assemble(body: np.ndarray, h: np.ndarray) -> np.ndarray:
    """The 31-s loop: the body from 0 s, the head at 26 s, what passes 31 s wrapped onto the start."""
    x = np.zeros((NE + round(S.TAIL * SR) + 1, 2))
    x[:len(body)] += body
    i = round(S.DUR * SR)
    x[i:i + len(h)] += h
    out = x[:NE].copy()
    tail = x[NE:]
    out[:len(tail)] += tail
    return out


def finish(mix: np.ndarray) -> np.ndarray:
    """S.finish for 31 s."""
    y = kit.master(mix, lufs=S.LUFS, tp=S.TP - 0.5, seconds=END, fade_out=0.0)
    y = S.edges(S._bass_mono(S.edges(y)))
    assert len(y) == NE, len(y)
    return y


def main() -> None:
    c = S.clock()
    log: list = []
    bus, _ = S.compose(c, log)
    music = assemble(unwrapped(bus, c), head(bus))
    track_m = finish(S._air_cut(music))
    # the narration exactly as in the 26-s score: its voice (level set against the 26-s music) and its ducking
    rows = S.layout()
    narr = S.narrate(S.music_bus(bus, c), rows)
    target = np.zeros(NE)
    core = np.zeros(NE, bool)
    for r in rows:
        i0, i1 = max(0, round((r["start"] - r["duck_lead"]) * SR)), round(r["end"] * SR)
        target[i0:i1] = np.minimum(target[i0:i1], -r["duck_db"])
        core[round(r["start"] * SR):round(r["end"] * SR)] = True
    gain = S.duck_gain(target)
    assert np.allclose(gain[:S.N], narr["gain"], atol=1e-9), "the ducking differs from the 26-s score's"
    voice = np.zeros((NE, 2))
    voice[:S.N] = narr["voice"]
    music_d = music * gain[:, None]
    total = sosfiltfilt(butter(2, 20.0, "highpass", fs=SR, output="sos"), S._air_cut(music_d + voice), axis=0)
    track_v = finish(total)
    pm = S.write_wav(S.SOCIAL / f"{S.BASE}_music.wav", track_m)
    pv = S.write_wav(S.SOCIAL / f"{S.BASE}_voice.wav", track_v)
    # checks: length, loudness, true peak; the voice over the ducked music per sentence (pre-master, as in the score)
    for p in (pm, pv):
        y = S._read_wav(p)
        lufs, tp = S.ffmpeg_ebur128(p)
        print(f"{p.name}: {len(y) / SR:.3f} s, {lufs:.1f} LUFS, true peak {tp:.1f} dBTP")
        assert len(y) == NE and abs(lufs - S.LUFS) <= 0.5 and tp <= -1.5, (p.name, len(y), lufs, tp)
    rms = lambda z: float(np.sqrt(np.mean(np.square(z))) + 1e-12)  # noqa: E731
    for r in rows:
        a, b = round(r["start"] * SR), round(r["end"] * SR)
        ratio = 20 * np.log10(rms(voice[a:b, 0]) / rms(music_d[a:b]))
        print(f"  {r['name']}: voice over music {ratio:5.1f} dB")
        assert ratio >= 10.0, (r["name"], ratio)
    m = S._read_wav(pm)
    for lab, t0, t1 in (("under the cards 26-30 s", 26.0, 30.0), ("the last 0.3 s", 30.7, 31.0),
                        ("the first 0.3 s", 0.0, 0.3)):
        print(f"  music {lab}: {S._db(m[round(t0 * SR):round(t1 * SR)]):.1f} dBFS rms")


if __name__ == "__main__":
    main()
