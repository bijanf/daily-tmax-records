"""«زمین همیشه گرم و سرد شده؟» (cycles_fa): the reel that answers "the Earth has always warmed and cooled".

The words, numbers, pictures and clock come from src/cycles.py; the page src/cycles_page/ draws any moment; this file
steps it through every frame in headless Chromium and encodes the silent reel, with the machinery of
src/onebit_elnino26i.py. No sound is made here: src/onebit_score_cycles_soft.py writes the score.

    outputs/onebit/social/cycles_fa_reel.mp4 (silent), _cover.png, _t<sec>.png (stills)

    python -I src/cycles.py                    # film.json, world.jpg, agemap.png (first)
    python -I src/onebit_cycles.py --stills    # the cover and stills
    python -I src/onebit_cycles.py             # the silent reel
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit_elnino26i as base  # noqa: E402  (the server, the page loader, the frame worker, the encoder)

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "src" / "cycles_page"
BUILD = ROOT / "outputs" / "onebit" / "cycles"
STEM = "cycles_fa"
base.Handler.mount = dict(page=PAGE, build=BUILD, fonts=base.FONTS)      # this film's page and pictures


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true", help="cover and stills only, no video")
    ap.add_argument("--at", type=float, nargs="*", help="stills at these times only")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--theme", choices=("light", "night"), help="the look of the page (film.html?theme=); light for the cut a, night for d")
    ap.add_argument("--cut", choices=("a", "d"), default="a", help="a: the eight scenes; d: the documentary cut (the corridor of life)")
    args = ap.parse_args()
    film = json.loads((BUILD / "film.json").read_text(encoding="utf-8"))
    cut = film["cuts"][args.cut]
    args.theme = args.theme or ("night" if args.cut == "d" else "light")
    n = round(cut["end"] * base.FPS)
    base.SOCIAL.mkdir(parents=True, exist_ok=True)
    name = STEM if args.cut == "a" else f"{STEM}_doc"
    stem = base.SOCIAL / (name if args.theme == ("light" if args.cut == "a" else "night") else f"{name}_{args.theme}")
    cut_q = f"{args.cut}&theme={args.theme}"         # open_page asks for film.html?cut=<this>
    srv = base.serve()
    port = srv.server_address[1]
    if args.stills or args.at:
        from playwright.sync_api import sync_playwright
        times = args.at or sorted({0.0} | {round(s["start"] + f * s["length"], 2) for s in cut["scenes"] for f in (0.5, 0.97)})
        with sync_playwright() as pw:
            browser, page = base.open_page(pw, port, cut_q)
            base.shoot(page, film["cover_t"], Path(f"{stem}_cover.png"))
            if not args.at:
                for old in base.SOCIAL.glob(f"{stem.name}_t*.png"):
                    old.unlink()
            for t in times:
                base.shoot(page, t, Path(f"{stem}_t{t:05.2f}.png"))
                print("saved", f"{stem}_t{t:05.2f}.png")
            browser.close()
        return
    folder = Path(tempfile.mkdtemp(prefix="cycles_", dir=BUILD))
    try:
        jobs = [(port, cut_q, list(range(k, n, args.workers)), str(folder)) for k in range(args.workers)]
        with mp.get_context("spawn").Pool(args.workers) as pool:
            done = sum(pool.map(base.worker, jobs))
        assert done == n and len(list(folder.glob("*.png"))) == n, (done, n)
        base.encode(folder, n, Path(f"{stem}_reel.mp4"))
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    print("saved", f"{stem}_reel.mp4", f"({n} frames)")


if __name__ == "__main__":
    main()
