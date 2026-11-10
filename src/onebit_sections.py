"""THE FOUR CROSS-SECTIONS UNDER TEHRAN in the newsroom look (the owner's request of 9 Nov 2026: «make the graphic
better»), for the voiced long cut of the dams explainer (src/onebit_damsexplain2v.py):

    rain     src/onebit_section_rain.py     where the storm's water goes, on the real section Tochal → Tehran
    soil     src/onebit_section_soil.py     how deep a few days of rain wet the soil
    ground   src/onebit_section_table.py    the water table under the plain, 1372 → 1400
    sink     src/onebit_section_sink.py     pumped clay compacts: the ground sinks

Each module has SECONDS (its slide's length in the voiced cut), CUE (when each thing appears, in scene-local
seconds, on the owner's words) and scene(w, h, t, words, tp=None, cue=CUE) → the finished box as an RGB picture.
The voiced film draws all four (10 Nov 2026); the music long cut (src/onebit_damsexplain2.py) keeps the earlier
drawings of src/onebit_ground.py.
The kit is src/onebit_section.py, the scenery src/onebit_scenery.py. The words on screen are those of
onebit_damsexplain2.words2() (fact check of 9 Nov 2026) and nothing else.

    python -I src/onebit_sections.py ground --sheet                  a contact sheet over the scene's length
    python -I src/onebit_sections.py ground --at 2.2 7.4 inf         stills at these scene-local seconds
    python -I src/onebit_sections.py ground --strip 4.0              8 frames in a row (1/30 s apart) from 4.0 s
    python -I src/onebit_sections.py ground --check                  every 0.5 s: asserts hold; seconds per frame
    (--out DIR: where the pictures go; default outputs/onebit/sections)
"""

from __future__ import annotations

import argparse
import importlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

MODULES = dict(rain="onebit_section_rain", soil="onebit_section_soil", ground="onebit_section_table",
               sink="onebit_section_sink")
BOX = (828, 800)                                    # onebit_damsexplain2.BOX[2:]
FPS = 30


def module(name: str):
    return importlib.import_module(MODULES[name])


def scene(name: str, w: int, h: int, t: float, words: dict, tp: float | None = None, **kw) -> Image.Image:
    im = module(name).scene(w, h, t, words, tp=tp, **kw)
    assert im.size == (w, h) and im.mode == "RGB", (name, im.size, im.mode)
    return im


def words() -> dict:
    """The film's words without the film: the labels and the number formats."""
    import onebit_damsexplain2 as two
    return two.words2()


def cue_times(cue: dict) -> list:
    out = []
    for v in cue.values():
        out += [float(x) for x in (v if isinstance(v, (tuple, list)) else (v,))]
    return out


def tag(im: Image.Image, text: str) -> Image.Image:
    im = im.copy()
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 13 * len(text) + 14, 30], fill=(255, 255, 255))
    d.text((7, 4), text, fill=(0, 0, 0), font_size=22)
    return im


def sheet(pics: list, cols: int, scale: float = 0.5) -> Image.Image:
    w, h = (int(round(v * scale)) for v in pics[0].size)
    rows = -(-len(pics) // cols)
    out = Image.new("RGB", (cols * (w + 8) + 8, rows * (h + 8) + 8), (255, 255, 255))
    for k, im in enumerate(pics):
        out.paste(im.resize((w, h), Image.LANCZOS), (8 + (k % cols) * (w + 8), 8 + (k // cols) * (h + 8)))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", choices=sorted(MODULES))
    ap.add_argument("--at", type=float, nargs="*", help="stills at these scene-local seconds (inf: the end state)")
    ap.add_argument("--sheet", action="store_true", help="a contact sheet: 12 times over the scene")
    ap.add_argument("--n", type=int, default=12, help="pictures on the sheet")
    ap.add_argument("--strip", type=float, help="8 consecutive frames from this second, side by side")
    ap.add_argument("--check", action="store_true", help="draw every 0.5 s and time it")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    import onebit
    out = args.out or onebit.OUT / "sections"
    out.mkdir(parents=True, exist_ok=True)
    mod, W = module(args.name), words()
    w, h = BOX
    draw = lambda t: scene(args.name, w, h, t, W, tp=None if np.isfinite(t) else mod.SECONDS)   # noqa: E731
    print(args.name, "seconds", mod.SECONDS, "cue", mod.CUE)
    assert max(cue_times(mod.CUE)) < mod.SECONDS, "a cue after the slide's end"
    if args.at:
        for t in args.at:
            path = out / f"{args.name}_t{t:05.2f}.png"
            draw(t).save(path)
            print(path)
    if args.sheet:
        times = [round(float(v), 2) for v in np.linspace(0.4, mod.SECONDS - 0.05, args.n)]
        path = out / f"{args.name}_sheet.png"
        sheet([tag(draw(t), f"{t:.2f} s") for t in times], 4).save(path)
        print(path, times)
    if args.strip is not None:
        path = out / f"{args.name}_strip_{args.strip:05.2f}.png"
        sheet([tag(draw(args.strip + k / FPS), f"+{k}") for k in range(8)], 8, 0.42).save(path)
        print(path)
    if args.check:
        draw(0.0)
        t0, n = time.time(), 0
        for t in np.arange(0.0, mod.SECONDS + 1e-9, 0.5):
            draw(float(t))
            n += 1
        draw(np.inf)
        print(f"check: {n} frames and the end state drawn; {(time.time() - t0) / n:.2f} s a frame")


if __name__ == "__main__":
    main()
