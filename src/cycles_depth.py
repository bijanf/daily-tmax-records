"""Depth for the photographs of the ice-age film's documentary cut (cycles_fa, cut "d"): one grey picture for each
photograph of the build folder, white = near, black = far, so that the page can move the near things against the far
ones while the camera drifts (the "2.5D" of documentary films: a still that moves like a shot).

The depth is estimated, not measured: Depth Anything V2 Small (Yang et al. 2024; Apache-2.0; weights from Hugging Face,
depth-anything/Depth-Anything-V2-Small-hf, about 100 MB, fetched once into the Hugging Face cache) through the
transformers library on the CPU. It is used for the look of a camera move only; no number of the film depends on it.

    python -I src/cycles.py          # first: photo_<key>.jpg in outputs/onebit/cycles
    python -I src/cycles_depth.py    # depth_<key>.png beside them (810 x 1440, blurred a little so edges do not tear)
    python -I src/cycles_depth.py outputs/onebit/kerman   # the same for another film's build folder
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "outputs" / "onebit" / "cycles"
MODEL = "depth-anything/Depth-Anything-V2-Small-hf"


def main() -> None:
    from transformers import pipeline
    build = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else BUILD          # another film's build folder (e.g. outputs/onebit/kerman)
    photos = sorted(build.glob("photo_*.jpg"))
    if not photos:
        sys.exit("no photographs in the build folder: run src/cycles.py first")
    todo = [p for p in photos if not (build / p.name.replace("photo_", "depth_").replace(".jpg", ".png")).exists()
            or (build / p.name.replace("photo_", "depth_").replace(".jpg", ".png")).stat().st_mtime < p.stat().st_mtime]
    if not todo:
        print("depth is up to date")
        return
    pipe = pipeline("depth-estimation", model=MODEL, device="cpu")
    for p in todo:
        im = Image.open(p).convert("RGB")
        d = np.asarray(pipe(im.resize((756, 1344), Image.LANCZOS))["depth"], dtype=float)      # the model's own "near is bright"
        lo, hi = np.percentile(d, [1, 99])
        d = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
        out = Image.fromarray(np.round(255 * d).astype(np.uint8), "L").resize((810, 1440), Image.BICUBIC).filter(ImageFilter.GaussianBlur(5))
        dst = build / p.name.replace("photo_", "depth_").replace(".jpg", ".png")
        out.save(dst, optimize=True)
        print("saved", dst, f"(near {100 * float((d > 0.66).mean()):.0f} %, far {100 * float((d < 0.33).mean()):.0f} % of the frame)")


if __name__ == "__main__":
    main()
