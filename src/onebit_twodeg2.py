"""«۲ درجه گرم‌تر، یعنی چه؟» (twodeg2_fa): the reel that explains what a global mean of 2 degrees means.

The words, the numbers (IPCC AR6 WG1 SPM, read at source) and the clock come from src/twodeg2.py; the page
src/twodeg2_page/ draws any moment; this file steps it through every frame in headless Chromium and encodes the
silent reel, with the machinery of src/onebit_elnino26i.py (its server, its page loader, its encoder). The owner
narrates over the silent reel; no sound is made here.

    outputs/onebit/social/twodeg2_fa_reel.mp4 (silent, 76 s, 2280 frames), _cover.png, _t<sec>.png (stills)

    python -I src/twodeg2.py                    # film.json and the world map (first)
    python -I src/onebit_twodeg2.py --stills    # the cover and stills
    python -I src/onebit_twodeg2.py             # the silent reel
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
PAGE = ROOT / "src" / "twodeg2_page"
BUILD = ROOT / "outputs" / "onebit" / "twodeg2"
STEM = "twodeg2_fa"
base.Handler.mount = dict(page=PAGE, build=BUILD, fonts=base.FONTS)      # this film's page and pictures


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true", help="cover and stills only, no video")
    ap.add_argument("--at", type=float, nargs="*", help="stills at these times only")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    film = json.loads((BUILD / "film.json").read_text(encoding="utf-8"))
    cut = film["cuts"]["a"]
    n = round(cut["end"] * base.FPS)
    base.SOCIAL.mkdir(parents=True, exist_ok=True)
    stem = base.SOCIAL / STEM
    srv = base.serve()
    port = srv.server_address[1]
    if args.stills or args.at:
        from playwright.sync_api import sync_playwright
        times = args.at or sorted({0.0} | {round(s["start"] + f * s["length"], 2) for s in cut["scenes"] for f in (0.5, 0.97)})
        with sync_playwright() as pw:
            browser, page = base.open_page(pw, port, "a")
            base.shoot(page, film["cover_t"], Path(f"{stem}_cover.png"))
            if not args.at:
                for old in base.SOCIAL.glob(f"{STEM}_t*.png"):
                    old.unlink()
            for t in times:
                base.shoot(page, t, Path(f"{stem}_t{t:05.2f}.png"))
                print("saved", f"{stem}_t{t:05.2f}.png")
            browser.close()
        return
    folder = Path(tempfile.mkdtemp(prefix="twodeg2_", dir=BUILD))
    try:
        jobs = [(port, "a", list(range(k, n, args.workers)), str(folder)) for k in range(args.workers)]
        with mp.get_context("spawn").Pool(args.workers) as pool:
            done = sum(pool.map(base.worker, jobs))
        assert done == n and len(list(folder.glob("*.png"))) == n, (done, n)
        base.encode(folder, n, Path(f"{stem}_reel.mp4"))
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    print("saved", f"{stem}_reel.mp4", f"({n} frames)")


if __name__ == "__main__":
    main()
