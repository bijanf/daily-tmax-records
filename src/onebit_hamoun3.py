"""«آبِ هامون کجا رفت؟» (hamoun3_fa): the Hamoun lakes from space, the satellite picture as the whole frame, in two
parts without narration (12 Nov 2026):

    p1   «آبِ هامون کجا رفت؟»     the wipe 1377 -> 1405, the border, the forty springs, the rain, the dams, this spring
    p2   «وقتی هامون خالی است»    the dust storm of 31 Shahrivar 1402, the people, the dry years, the dispute, the full lake

The words, the numbers and each part's clock come from src/hamoun3.py (film.json and the pictures); the page
src/hamoun3_page/ draws any moment of a part (film.html?cut=p1); this file steps it through every frame in headless
Chromium and encodes the silent reel, with the machinery of src/onebit_elnino26i.py (its server, its page loader,
its encoder).

    outputs/onebit/social/hamoun3_fa_<part>_reel.mp4 (silent), _cover.png, _t<sec>.png (stills)

    python -I src/hamoun3.py                              # film.json and the pictures (first)
    python -I src/onebit_hamoun3.py --cut p1 --stills     # the cover and stills of part 1
    python -I src/onebit_hamoun3.py --cut p2 --at 0 1.1   # stills at these times
    python -I src/onebit_hamoun3.py --cut p1              # the silent reel of part 1
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
PAGE = ROOT / "src" / "hamoun3_page"
BUILD = ROOT / "outputs" / "onebit" / "hamoun3"
STEM = "hamoun3_fa"
CUTS = ("p1", "p2")
base.Handler.mount = dict(page=PAGE, build=BUILD, fonts=base.FONTS)      # this film's page and pictures


def rest_times(cut: dict) -> list:
    """One still where each scene rests (just before it ends), the first and the last frame."""
    out = {0.0, cut["cover_t"], cut["end"]}
    for a, b in cut["scenes"].values():
        out.add(round(b - 0.4, 2))
    return sorted(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cut", required=True, choices=CUTS, help="the part")
    ap.add_argument("--stills", action="store_true", help="cover and stills only, no video")
    ap.add_argument("--at", type=float, nargs="*", help="stills at these times only")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=Path, help="folder for the stills of --at (default: the social folder)")
    args = ap.parse_args()
    film = json.loads((BUILD / "film.json").read_text(encoding="utf-8"))
    cut = film["cuts"][args.cut]
    n = round(cut["end"] * base.FPS)
    assert film["fps"] == base.FPS and tuple(film["size"]) == base.SIZE
    base.SOCIAL.mkdir(parents=True, exist_ok=True)
    name = f"{STEM}_{args.cut}"
    stem = base.SOCIAL / name
    srv = base.serve()
    port = srv.server_address[1]
    if args.stills or args.at is not None:
        from playwright.sync_api import sync_playwright
        times = args.at or rest_times(cut)
        folder = args.out or base.SOCIAL
        folder.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as pw:
            browser, page = base.open_page(pw, port, args.cut)
            if not args.at:
                base.shoot(page, cut["cover_t"], Path(f"{stem}_cover.png"))
                for old in base.SOCIAL.glob(f"{name}_t*.png"):
                    old.unlink()
            for t in times:
                out = folder / f"{name}_t{t:05.2f}.png"
                base.shoot(page, t, out)
                print("saved", out)
            browser.close()
        return
    folder = Path(tempfile.mkdtemp(prefix=f"{name}_", dir=BUILD))
    try:
        jobs = [(port, args.cut, list(range(k, n, args.workers)), str(folder)) for k in range(args.workers)]
        with mp.get_context("spawn").Pool(args.workers) as pool:
            done = sum(pool.map(base.worker, jobs))
        assert done == n and len(list(folder.glob("*.png"))) == n, (done, n)
        base.encode(folder, n, Path(f"{stem}_reel.mp4"))
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    print("saved", f"{stem}_reel.mp4", f"({n} frames)")


if __name__ == "__main__":
    main()
