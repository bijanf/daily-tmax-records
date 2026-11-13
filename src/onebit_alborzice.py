"""«یخچال‌های البرز» (alborzice_fa): the silent reel, stepped through headless Chromium frame by frame.

The words, the numbers and the clock come from src/alborzice.py (film.json and the pictures); the page
src/alborzice_page/ draws any moment; this file steps it through every frame and encodes the silent reel with the
machinery of src/onebit_elnino26i.py (its server, its page loader, its frame worker, its encoder). The owner's voice
arrives later; the face video of the two face scenes (face1, close) is composited later by someone else, so
--overlay writes ONLY their overlay texts (name tag, subtitle, closing cards) as transparent PNG frames.

    outputs/onebit/social/alborzice_fa_reel.mp4 (silent), _cover.png, _t<sec>.png (stills)
    outputs/onebit/alborzice/overlay/<scene>/f00000.png ... and overlay.json (start and length of each scene)

    python -I src/alborzice.py                    # film.json and the pictures (first)
    python -I src/onebit_alborzice.py --stills    # the cover and two stills per scene
    python -I src/onebit_alborzice.py --at 5 20   # stills at these times only
    python -I src/onebit_alborzice.py --overlay   # transparent overlay frames of the face scenes
    python -I src/onebit_alborzice.py             # the silent reel
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
PAGE = ROOT / "src" / "alborzice_page"
BUILD = ROOT / "outputs" / "onebit" / "alborzice"
STEM = "alborzice_fa"
FACE = ("face1", "close")
base.Handler.mount = dict(page=PAGE, build=BUILD, fonts=base.FONTS)      # this film's page and pictures


def open_overlay(pw, port: int):
    """The page in overlay mode: a transparent background, only the overlay texts of the face scenes."""
    browser = pw.chromium.launch(args=["--force-color-profile=srgb", "--font-render-hinting=none"])
    page = browser.new_page(viewport=dict(width=base.SIZE[0], height=base.SIZE[1]), device_scale_factor=1)
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://127.0.0.1:{port}/page/film.html?cut=a&overlay=1")
    page.wait_for_function("window.READY === true || window.FAILED", timeout=60000)
    failed = page.evaluate("window.FAILED || ''")
    assert not failed and not errors, (failed, errors)
    return browser, page


def overlay(port: int, film: dict, workers: int) -> None:
    from playwright.sync_api import sync_playwright
    scenes = {s["key"]: s for s in film["cuts"]["a"]["scenes"]}
    out = BUILD / "overlay"
    info = {}
    with sync_playwright() as pw:
        browser, page = open_overlay(pw, port)
        for k in FACE:
            s = scenes[k]
            n = round(s["length"] * base.FPS)
            folder = out / k
            if folder.exists():
                shutil.rmtree(folder)
            folder.mkdir(parents=True)
            for i in range(n):
                page.evaluate("t => window.renderAt(t)", s["start"] + i / base.FPS)
                page.screenshot(path=str(folder / f"f{i:05d}.png"), type="png", omit_background=True)
            info[k] = dict(start=s["start"], length=s["length"], frames=n, fps=base.FPS, size=film["size"], folder=f"overlay/{k}")
            print("saved", folder, f"({n} frames)")
        browser.close()
    (out / "overlay.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", out / "overlay.json")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true", help="cover and two stills per scene only, no video")
    ap.add_argument("--at", type=float, nargs="*", help="stills at these times only")
    ap.add_argument("--overlay", action="store_true", help="transparent PNG frames of the face scenes' overlay texts only")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    film = json.loads((BUILD / "film.json").read_text(encoding="utf-8"))
    cut = film["cuts"]["a"]
    n = round(cut["end"] * base.FPS)
    base.SOCIAL.mkdir(parents=True, exist_ok=True)
    stem = base.SOCIAL / STEM
    srv = base.serve()
    port = srv.server_address[1]
    if args.overlay:
        overlay(port, film, args.workers)
        return
    if args.stills or args.at:
        from playwright.sync_api import sync_playwright
        times = args.at or sorted({0.0} | {round(s["start"] + f * s["length"], 2) for s in cut["scenes"] for f in (0.45, 0.95)})
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
    folder = Path(tempfile.mkdtemp(prefix="alborzice_", dir=BUILD))
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
