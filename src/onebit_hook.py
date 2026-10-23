"""Put a short face-to-camera hook in front of a reel.

Cuts the spoken phrases out of a phone video (dropping the silence around them), burns the
words in as captions (a light chip, {braces} in the hot colour, [brackets] in the cold one,
words appearing in step with each phrase), optionally dithers the face to 1 bit in the
theme's colours, switches the screen off like an old monitor, and joins the reel after it. The
voice is set to -12 LUFS and the reel's sound to the voice's loudness (only ever turned down),
so the music does not jump in louder than the words.

    python -I src/onebit_hook.py IMG_6378.mov outputs/onebit/social/europe_race_beton_reel.mp4 \\
        --cut 1.40-4.60:"Europe is breaking {heat} records." \\
        --cut 6.15-7.85:"How about the [cold] ones?" --cut 9.60-10.50:"Watch!" --theme beton

writes <reel>_hook_raw.mp4 and <reel>_hook_1bit.mp4 next to the reel.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import onebit  # noqa: E402
from onebit import BOLD, FPS, SOCIAL_CRF, _font, dither, smooth  # noqa: E402

W, H = 1080, 1920
OFF = 0.35          # seconds of the screen switching off at the end of the hook


def frames(src: Path, t0: float, t1: float):
    """RGB frames (H, W, 3) of src between t0 and t1, upright and filling 1080 x 1920."""
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t0}", "-to", f"{t1}", "-i", str(src), "-an",
           "-vf", f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)


def one_bit(rgb: np.ndarray, th: onebit.Theme, dot: int = 2) -> np.ndarray:
    """The frame as 2 x 2 px Floyd–Steinberg dots of ink on the theme's field."""
    grey = np.asarray(Image.fromarray(rgb).convert("L").resize((W // dot, H // dot)), float) / 255
    lo, hi = np.percentile(grey, (2, 98))
    ink = onebit.blocks(dither(1 - np.clip((grey - lo) / max(hi - lo, 1e-3), 0, 1) ** 0.9), dot, (H, W))
    out = np.empty((H, W, 3), np.uint8)
    out[:] = Image.new("RGB", (1, 1), th.field).getpixel((0, 0))
    out[ink] = Image.new("RGB", (1, 1), th.ink).getpixel((0, 0))
    return out


def caption(im: Image.Image, text: str, p: float, th: onebit.Theme):
    """The phrase on a light chip in the upper third; words appear as p runs from 0 to 1. In a
    two-colour theme the accents are inverse video, as in the reel's caption band."""
    d = ImageDraw.Draw(im)
    words = [(w, {"{": th.hot, "[": th.cold}.get(part[0])) for part in re.split(r"(\{[^}]*\}|\[[^]]*\])", text)
             if part for w in part.strip("{}[]").split()]
    font = _font(BOLD, 78)
    space, lines, line, width = font.getlength(" "), [], [], 0
    for w, colour in words:                              # wrap to the chip's width
        wl = font.getlength(w)
        if line and width + space + wl > W - 220:
            lines.append(line)
            line, width = [], 0
        line.append((w, colour, wl))
        width += (space if width else 0) + wl
    lines.append(line)
    shown = int(np.ceil(len(words) * min(1.0, p * 1.6)))
    lead, top = 92, 360
    box_w = max(sum(wl for _, _, wl in ln) + space * (len(ln) - 1) for ln in lines) + 70
    x0 = (W - box_w) / 2
    d.rectangle([x0, top - 70, x0 + box_w, top - 70 + lead * len(lines) + 40], fill=th.paper, outline=th.ink, width=3)
    k = 0
    for j, ln in enumerate(lines):
        x = (W - (sum(wl for _, _, wl in ln) + space * (len(ln) - 1))) / 2
        for w, colour, wl in ln:
            if k < shown:
                if colour and th.mono:                   # two colours only: the accent in inverse video
                    y = top + j * lead
                    d.rectangle([x - 8, y - 66, x + wl + 8, y + 20], fill=th.ink)
                    colour = th.field
                d.text((x, top + j * lead), w, font=font, fill=colour or th.ink, anchor="ls")
            x += wl + space
            k += 1


def switch_off(im: Image.Image, p: float, th: onebit.Theme) -> Image.Image:
    """An old monitor switching off: the frame squeezes into a line, the line into a dot."""
    out = Image.new("RGB", im.size, th.field)
    if p < 0.6:
        nh = max(2, round(H * (1 - smooth(p / 0.6)) ** 2))
        out.paste(im.resize((W, nh), Image.BILINEAR), (0, (H - nh) // 2))
    else:
        nw = round(W * (1 - smooth((p - 0.6) / 0.4)))
        if nw > 0:
            ImageDraw.Draw(out).rectangle([(W - nw) // 2, H // 2 - 2, (W + nw) // 2, H // 2 + 2], fill=th.ink)
    return out


def hook(src: Path, cuts, th: onebit.Theme, dithered: bool, out: Path) -> float:
    """The hook as its own MP4 (video and voice); returns its length in seconds."""
    tmp = Path(tempfile.mkdtemp())
    pieces = []
    for i, (t0, t1, _) in enumerate(cuts):           # voice of every phrase, with short fades
        piece = tmp / f"a{i}.wav"
        dur = t1 - t0
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0}", "-to", f"{t1}", "-i", str(src), "-vn",
                        "-af", f"afade=t=in:d=0.02,afade=t=out:st={dur - 0.04:.3f}:d=0.04", "-ar", "48000", "-ac",
                        "2", str(piece)], check=True)
        pieces.append(piece)
    (tmp / "list.txt").write_text("".join(f"file '{p}'\n" for p in pieces))
    voice = tmp / "voice.wav"
    total = sum(t1 - t0 for t0, t1, _ in cuts) + OFF     # padded with silence to the hook's length
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
                    "-af", f"loudnorm=I=-12:TP=-1.5:LRA=7,apad=whole_dur={total:.3f}", "-ar", "48000", str(voice)],
                   check=True)
    video = []
    for t0, t1, text in cuts:
        clip = frames(src, t0, t1)
        for k, rgb in enumerate(clip):
            im = Image.fromarray(one_bit(rgb, th) if dithered else rgb)
            caption(im, text, k / max(len(clip) - 1, 1), th)
            video.append(im)
    n_off = round(OFF * FPS)
    last = video[-1]
    video += [switch_off(last, (k + 1) / n_off, th) for k in range(n_off)]
    seconds = len(video) / FPS
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", str(voice), "-t", f"{seconds:.3f}", "-c:a", "aac", "-b:a", "192k",
           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx264", "-preset", "slow",
           "-crf", str(SOCIAL_CRF), "-profile:v", "high", "-colorspace", "bt709", "-color_primaries", "bt709",
           "-color_trc", "bt709", str(out)]
    with subprocess.Popen(cmd, stdin=subprocess.PIPE) as ff:
        for im in video:
            ff.stdin.write(im.tobytes())
        ff.stdin.close()
    return seconds


def loudness(path: Path) -> float:
    """Integrated loudness of a file's sound in LUFS (EBU R128)."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "ebur128", "-f", "null",
                          "-"], capture_output=True, text=True, check=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])


def join(first: Path, second: Path, out: Path) -> None:
    """The hook, then the reel, re-encoded as one file; the reel's sound no louder than the voice."""
    gain = min(0.0, loudness(first) - loudness(second))
    print(f"reel sound {gain:+.1f} dB to meet the voice")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(first), "-i", str(second), "-filter_complex",
                    f"[1:a]volume={gain:.2f}dB[b];[0:v][0:a][1:v][b]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", "slow", "-crf", str(SOCIAL_CRF), "-profile:v", "high",
                    "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)], check=True)
    print("saved", out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path, help="phone video of the hook")
    ap.add_argument("reel", type=Path, help="the reel that follows it")
    ap.add_argument("--cut", action="append", required=True, help='"t0-t1:caption" in seconds of the video')
    ap.add_argument("--theme", default="beton", choices=list(onebit.THEMES))
    args = ap.parse_args()
    cuts = []
    for c in args.cut:
        span, text = c.split(":", 1)
        t0, t1 = (float(v) for v in span.split("-"))
        cuts.append((t0, t1, text))
    th = onebit.THEMES[args.theme]
    for name, dithered in (("raw", False), ("1bit", True)):
        part = args.reel.with_name(f"{args.reel.stem}_hook_{name}_part.mp4")
        seconds = hook(args.video, cuts, th, dithered, part)
        print(f"hook ({name}): {seconds:.2f} s")
        join(part, args.reel, args.reel.with_name(args.reel.stem.removesuffix("_reel") + f"_hook_{name}_reel.mp4"))
        part.unlink()


if __name__ == "__main__":
    main()
