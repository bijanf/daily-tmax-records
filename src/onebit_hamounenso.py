"""«ال‌نینو برای هامون آب می‌آورد؟» (hamounenso_fa): the Hamoun's springs after El Niño, neutral and La Niña winters,
the satellite picture as the whole frame, one film without narration (16 Nov 2026).

The words, the numbers and the clock come from src/hamounenso.py (film.json and the pictures); the page
src/hamounenso_page/ draws any moment (film.html?cut=main); this file steps it through every frame in headless
Chromium and encodes the silent reel, with the machinery of src/onebit_elnino26i.py (its server, its page loader, its
frame worker, its encoder), as src/onebit_hamoun3.py does.

    outputs/onebit/social/hamounenso_fa_reel.mp4 (silent), _cover.png, _t<sec>.png (stills)

    python -I src/hamounenso.py                       # film.json and the pictures (first)
    python -I src/onebit_hamounenso.py --stills       # the cover and a still where each scene rests
    python -I src/onebit_hamounenso.py --at 0 1.2     # stills at these times
    python -I src/onebit_hamounenso.py                # the silent reel
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
PAGE = ROOT / "src" / "hamounenso_page"
BUILD = ROOT / "outputs" / "onebit" / "hamounenso"
STEM = "hamounenso_fa"
CUT = "main"
base.Handler.mount = dict(page=PAGE, build=BUILD, fonts=base.FONTS)      # this film's page and pictures


def rest_times(cut: dict) -> list:
    """One still where each scene rests (just before it ends), the first and the last frame."""
    out = {0.0, cut["cover_t"], cut["end"]}
    for a, b in cut["scenes"].values():
        out.add(round(b - 0.4, 2))
    return sorted(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true", help="cover and stills only, no video")
    ap.add_argument("--at", type=float, nargs="*", help="stills at these times only")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=Path, help="folder for the stills of --at (default: the social folder)")
    args = ap.parse_args()
    film = json.loads((BUILD / "film.json").read_text(encoding="utf-8"))
    cut = film["cuts"][CUT]
    n = round(cut["end"] * base.FPS)
    assert film["fps"] == base.FPS and tuple(film["size"]) == base.SIZE
    base.SOCIAL.mkdir(parents=True, exist_ok=True)
    stem = base.SOCIAL / STEM
    srv = base.serve()
    port = srv.server_address[1]
    if args.stills or args.at is not None:
        from playwright.sync_api import sync_playwright
        times = args.at or rest_times(cut)
        folder = args.out or base.SOCIAL
        folder.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as pw:
            browser, page = base.open_page(pw, port, CUT)
            if not args.at:
                base.shoot(page, cut["cover_t"], Path(f"{stem}_cover.png"))
                for old in base.SOCIAL.glob(f"{STEM}_t*.png"):
                    old.unlink()
            for t in times:
                out = folder / f"{STEM}_t{t:05.2f}.png"
                base.shoot(page, t, out)
                print("saved", out)
            browser.close()
        return
    folder = Path(tempfile.mkdtemp(prefix=f"{STEM}_", dir=BUILD))
    try:
        jobs = [(port, CUT, list(range(k, n, args.workers)), str(folder)) for k in range(args.workers)]
        with mp.get_context("spawn").Pool(args.workers) as pool:
            done = sum(pool.map(base.worker, jobs))
        assert done == n and len(list(folder.glob("*.png"))) == n, (done, n)
        base.encode(folder, n, Path(f"{stem}_reel.mp4"))
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    print("saved", f"{stem}_reel.mp4", f"({n} frames)")


if __name__ == "__main__":
    main()
