"""«یخچال‌های البرز» WITH THE OWNER'S VOICE AND FACE: the last step, picture and sound put together.

Needs, in this order:
    python -I src/alborzice_voice.py                       the voice pieces and their manifest (the film's clock)
    python -I src/alborzice.py                             film.json on that clock
    python -I src/onebit_alborzice.py                      the silent reel
    python -I src/onebit_alborzice.py --overlay            the face scenes' texts on a transparent background
    python -I src/onebit_score_alborzice_light.py          the score and its quiet bed on the same clock
    python -I src/onebit_alborzice_final.py                this file

The sound: each piece of the owner's voice starts LEAD after its scene; the voice is cleaned (a high-pass at
75 Hz, a gentle noise reduction, a compressor), set to -16 LUFS, and the score's bed is held 13 LU under it while
he speaks and comes up by 4 dB in the gaps; the mix is mastered to -14 LUFS, true peak -1 dBTP.

The picture: in a scene that is seen on camera the owner's video (cropped to fill 1080 x 1920) takes the place of
the film from the scene's start for as long as the manifest says, with the film's own overlay (name tag, subtitle)
on top; after that the film's picture returns. Without a face entry the film's fallback picture stays.

    outputs/onebit/social/alborzice_fa_voice_reel.mp4          voice, bed and, when recorded, the face
    outputs/onebit/social/alborzice_fa_voice_noface_reel.mp4   the same sound on the film's own pictures
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.ndimage import maximum_filter1d, uniform_filter1d

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit_persian as kit  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CUT = os.environ.get("ALBORZICE_CUT", "")                  # as in src/alborzice.py
LONG = ROOT / "outputs" / "onebit" / "alborzice"
BUILD = ROOT / "outputs" / "onebit" / ("alborzice_" + CUT if CUT else "alborzice")
SOCIAL = ROOT / "outputs" / "onebit" / "social"
VOICE = ROOT / "data" / "alborzice" / "voice"
STEM = f"alborzice_{CUT}_fa" if CUT else "alborzice_fa"
SR = kit.SR
VOICE_LUFS, UNDER, UP = -16.0, 13.0, 4.0


def clean(src: Path, dst: Path) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af",
                    "highpass=f=75,afftdn=nr=8:nf=-50,acompressor=threshold=-22dB:ratio=3:attack=8:release=180:makeup=3dB",
                    "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", str(dst)], check=True)


def sound(film: dict, man: dict) -> Path:
    cut = film["cuts"]["a"]
    start = {s["key"]: s["start"] for s in cut["scenes"]}
    n = int(round(cut["end"] * SR))
    voice = np.zeros(n)
    with tempfile.TemporaryDirectory() as tmp:
        for q in man["pieces"]:
            if q["scene"] not in start:               # a cut leaves scenes out
                continue
            w = Path(tmp) / "v.wav"
            clean(VOICE / f"v_{q['scene']}.wav", w)
            _, x = wavfile.read(w)
            x = x.astype(np.float64) / 32768.0
            x *= 10 ** ((VOICE_LUFS - kit.integrated_lufs(x)) / 20)       # every piece at the same loudness: memo and camera differ
            i = int(round((start[q["scene"]] + man["lead"]) * SR))
            m = min(len(x), n - i)
            voice[i:i + m] += x[:m]
    voice *= 10 ** ((VOICE_LUFS - kit.integrated_lufs(voice)) / 20)
    _, bed = wavfile.read(SOCIAL / "alborzice_fa_bed.wav")
    bed = bed.astype(np.float64) / 32768.0
    if bed.ndim == 1:
        bed = np.stack([bed, bed], axis=1)
    if CUT:                                            # a cut keeps the long film's music: each scene's own stretch of the bed,
        whole = {q["key"]: q for q in json.loads((LONG / "film.json").read_text(encoding="utf-8"))["cuts"]["a"]["scenes"]}
        out, xf, at_end = np.zeros((0, 2)), int(0.6 * SR), None           # a 0.6-s crossfade where two stretches were not neighbours
        for q in cut["scenes"]:
            w = whole[q["key"]]
            assert abs(w["length"] - q["length"]) < 1e-6, q["key"]
            i0 = int(round(w["start"] * SR))
            piece = bed[i0:i0 + int(round(q["length"] * SR))]
            if at_end is not None and abs(at_end - i0) > 2:
                lead = bed[max(0, i0 - xf):i0]
                r = np.linspace(0.0, 1.0, len(lead))[:, None]
                out[-len(lead):] = out[-len(lead):] * (1 - r) + lead * r
            out = np.vstack([out, piece])
            at_end = i0 + len(piece)
        bed = out
    bed = np.vstack([bed, np.zeros((max(0, n - len(bed)), 2))])[:n]
    bed *= 10 ** ((VOICE_LUFS - UNDER - kit.integrated_lufs(bed)) / 20)
    # the bed comes up in the gaps: voice activity (50-ms level), held 0.25 s, smoothed over 0.4 s
    lvl = np.sqrt(np.maximum(uniform_filter1d(voice ** 2, int(0.05 * SR)), 0.0))
    act = maximum_filter1d((lvl > 10 ** (-45 / 20)).astype(float), int(0.25 * SR))
    env = uniform_filter1d(act, int(0.4 * SR))
    gain = 10 ** (UP * (1 - env) / 20)
    mix = bed * gain[:, None] + voice[:, None]
    out = kit.master(mix, lufs=-14.0, tp=-1.0, seconds=cut["end"], fade_out=1.0)
    path = SOCIAL / f"{STEM}_voice.wav"
    kit.write_wav(path, out)
    print(f"voice {kit.integrated_lufs(voice):.1f} LUFS, bed {kit.integrated_lufs(bed):.1f} LUFS under it, "
          f"mix {kit.integrated_lufs(out):.1f} LUFS, true peak {kit.true_peak_dbtp(out):.1f} dBTP, {len(out) / SR:.2f} s")
    return path


def picture(film: dict, man: dict) -> Path | None:
    """The silent reel with the owner's video in the scenes that are seen on camera."""
    cut = film["cuts"]["a"]
    sc = {s["key"]: s for s in cut["scenes"]}
    faces = [q for q in man["pieces"] if "face" in q and q["scene"] in sc]
    if not faces:
        return None
    reel = SOCIAL / f"{STEM}_reel.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(reel)]
    flt, last = [], "0:v"
    for k, q in enumerate(faces):
        f, s = q["face"], sc[q["scene"]]
        shown = min(f["shown"], s["length"])
        n0 = int(round(f.get("from", 0.0) * film["fps"]))              # the face comes in here (a J-cut: the voice is already on)
        nfr = int(round(shown * film["fps"])) - n0
        cmd += ["-ss", f"{max(0.0, f['video_start'] + n0 / film['fps']):.3f}", "-t", f"{(nfr + 10) / film['fps']:.3f}", "-i", f["video"],
                "-framerate", str(film["fps"]), "-start_number", str(n0), "-i", str(BUILD / "overlay" / q["scene"] / "f%05d.png")]
        a, o = 1 + 2 * k, 2 + 2 * k
        t0 = s["start"] + n0 / film["fps"]
        t1 = t0 + nfr / film["fps"]
        flt += [f"[{a}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps={film['fps']},setsar=1,"
                f"format=yuv420p,trim=end_frame={nfr + 10},setpts=PTS-STARTPTS[c{k}]",      # a few frames to spare: the window below ends it
                f"[{o}:v]setpts=PTS-STARTPTS[o{k}]",
                f"[c{k}][o{k}]overlay=0:0:format=auto,setpts=PTS-STARTPTS+{t0:.4f}/TB[f{k}]",
                f"[{last}][f{k}]overlay=0:0:enable='between(t,{t0:.4f},{t1 - 0.5 / film['fps']:.4f})':eof_action=pass[v{k}]"]
        last = f"v{k}"
    out = SOCIAL / f"{STEM}_face_silent.mp4"
    cmd += ["-filter_complex", ";".join(flt), "-map", f"[{last}]", "-an", "-c:v", "libx264", "-crf", "17", "-preset", "medium",
            "-pix_fmt", "yuv420p", "-r", str(film["fps"]), "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    return out


def main() -> None:
    film = json.loads((BUILD / "film.json").read_text(encoding="utf-8"))
    man = json.loads((VOICE / "manifest.json").read_text(encoding="utf-8"))
    assert film["voice_from_manifest"], "film.json was built without the voice manifest: run src/alborzice.py again"
    wav = sound(film, man)
    plain = SOCIAL / f"{STEM}_reel.mp4"
    face = picture(film, man)
    if face is not None:
        kit.mux(face, wav, SOCIAL / f"{STEM}_voice_reel.mp4")
        kit.mux(plain, wav, SOCIAL / f"{STEM}_voice_noface_reel.mp4")
        print("saved", SOCIAL / f"{STEM}_voice_reel.mp4", "and the no-face cut")
    else:
        kit.mux(plain, wav, SOCIAL / f"{STEM}_voice_reel.mp4")
        print("saved", SOCIAL / f"{STEM}_voice_reel.mp4", "(no face recorded: the film's own pictures)")


if __name__ == "__main__":
    main()
