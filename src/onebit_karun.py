"""«آبِ کارون کجا می‌رود؟» (karun_fa): two places on the Karun from space, the satellite picture as the whole frame.

The words, the numbers and the clock come from src/karun.py (film.json and the pictures); the page
src/karun_page/ draws any moment; this file steps it through every frame in headless Chromium and encodes the
silent reel, with the machinery of src/onebit_elnino26i.py (its server, its page loader, its encoder).

    outputs/onebit/social/karun_fa_reel.mp4 (silent), _cover.png, _t<sec>.png (stills)

    python -I src/karun.py                    # film.json and the pictures (first)
    python -I src/onebit_karun.py --stills    # the cover and stills
    python -I src/onebit_karun.py --at 0 1.1  # stills at these times
    python -I src/onebit_karun.py             # the silent reel
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
PAGE = ROOT / "src" / "karun_page"
BUILD = ROOT / "outputs" / "onebit" / "karun"
STEM = "karun_fa"
base.Handler.mount = dict(page=PAGE, build=BUILD, fonts=base.FONTS)      # this film's page and pictures


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true", help="cover and stills only, no video")
    ap.add_argument("--at", type=float, nargs="*", help="stills at these times only")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=Path, help="folder for the stills of --at (default: the social folder)")
    args = ap.parse_args()
    film = json.loads((BUILD / "film.json").read_text(encoding="utf-8"))
    n = round(film["end"] * base.FPS)
    assert film["fps"] == base.FPS and tuple(film["size"]) == base.SIZE
    base.SOCIAL.mkdir(parents=True, exist_ok=True)
    stem = base.SOCIAL / STEM
    srv = base.serve()
    port = srv.server_address[1]
    if args.stills or args.at is not None:
        from playwright.sync_api import sync_playwright
        times = args.at or [0.0, 1.4, 2.6, film["cover_t"], 6.2, 8.0, 11.0, 14.3, 15.9, 17.0, 19.6, 23.0, 26.5, 31.0, 36.0, 37.9]
        folder = args.out or base.SOCIAL
        folder.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as pw:
            browser, page = base.open_page(pw, port, "a")
            if not args.at:
                base.shoot(page, film["cover_t"], Path(f"{stem}_cover.png"))
                for old in base.SOCIAL.glob(f"{STEM}_t*.png"):
                    old.unlink()
            for t in times:
                out = folder / f"{STEM}_t{t:05.2f}.png"
                base.shoot(page, t, out)
                print("saved", out)
            browser.close()
        return
    folder = Path(tempfile.mkdtemp(prefix="karun_", dir=BUILD))
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
