"""EL NIÑO AND IRAN'S RAIN AS AN INFOGRAPHIC (elnino26i_fa): the reviewed reel, drawn again by a web page.

The words, the numbers and the two clocks are those of the reviewed films (src/onebit_elnino26x.py, 86 s, and
src/onebit_elnino26s.py, 35.5 s): src/elnino26i.py builds the film object, runs its asserts and writes film.json and
the pictures; the page src/elnino26i_page/ (film.html, film.css, film.js) draws the frame of any time t; this file
steps the page through every frame in headless Chromium (Playwright), encodes the silent reel as the other films do
(H.264, BT.709, 30 frames a second) and puts the existing soundtracks under it, unchanged: the owner's own voice
with the light score. No sound is made here.

    cut a   35.5 s, 1065 frames: hook, autumn, iran, winter, answer (the narrated reel's clock)
    cut b   86 s, 2580 frames: hook, what, record, autumn, iran, winter, strong, answer (the explainer's clock)

    outputs/onebit/social/elnino26i_fa_<35s|86s>_reel.mp4 (silent), _cover.png, _t<sec>.png (stills)

    python -I src/elnino26i.py                              # film.json and the pictures (first)
    python -I src/onebit_elnino26i.py --cut a --stills      # the cover and stills
    python -I src/onebit_elnino26i.py --cut a               # the silent reel
    python -I src/onebit_elnino26i.py --cut a --sound W.wav --tag voice   # the reel with a soundtrack under it
"""

from __future__ import annotations

import argparse
import http.server
import json
import multiprocessing as mp
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "src" / "elnino26i_page"
BUILD = ROOT / "outputs" / "onebit" / "elnino26i"
FONTS = ROOT / "data" / "fonts"
SOCIAL = ROOT / "outputs" / "onebit" / "social"
BASE = "elnino26i_fa"
NAME = dict(a="35s", b="86s")
FPS = 30
CRF = 16                                             # as onebit.SOCIAL_CRF (asserted in main)
SIZE = (1080, 1920)


class Handler(http.server.SimpleHTTPRequestHandler):
    """/page/, /build/ and /fonts/ of the three folders; nothing else."""
    mount = dict(page=PAGE, build=BUILD, fonts=FONTS)

    def translate_path(self, path: str) -> str:
        parts = [p for p in path.split("?", 1)[0].split("#", 1)[0].split("/") if p and p not in (".", "..")]
        if not parts or parts[0] not in self.mount:
            return str(PAGE / "__missing__")
        return str(self.mount[parts[0]].joinpath(*parts[1:]))

    def log_message(self, *args) -> None:
        pass

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def serve() -> http.server.ThreadingHTTPServer:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def open_page(pw, port: int, cut: str):
    browser = pw.chromium.launch(args=["--force-color-profile=srgb", "--font-render-hinting=none"])
    page = browser.new_page(viewport=dict(width=SIZE[0], height=SIZE[1]), device_scale_factor=1)
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://127.0.0.1:{port}/page/film.html?cut={cut}")
    page.wait_for_function("window.READY === true || window.FAILED", timeout=60000)
    failed = page.evaluate("window.FAILED || ''")
    assert not failed and not errors, (failed, errors)
    return browser, page


def shoot(page, t: float, path: Path) -> None:
    page.evaluate("t => window.renderAt(t)", t)
    page.screenshot(path=str(path), type="png")


def worker(args) -> int:
    port, cut, frames, folder = args
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser, page = open_page(pw, port, cut)
        for k in frames:
            shoot(page, k / FPS, Path(folder) / f"{k:05d}.png")
        browser.close()
    return len(frames)


def encode(folder: Path, n: int, out: Path) -> None:
    """The silent reel, encoded as onebit.video does (an empty stereo track, so the file has an audio stream)."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(folder / "%05d.png"),
           "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-frames:v", str(n), "-shortest", "-c:a", "aac",
           "-b:a", "192k", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx264",
           "-preset", "slow", "-crf", str(CRF), "-profile:v", "high", "-colorspace", "bt709", "-color_primaries",
           "bt709", "-color_trc", "bt709", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cut", default="a", choices=["a", "b"], help="a: 35.5 s (narrated reel), b: 86 s (explainer)")
    ap.add_argument("--stills", action="store_true", help="cover and stills only, no video")
    ap.add_argument("--at", type=float, nargs="*", help="stills at these times only")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--sound", type=Path, help="a finished soundtrack (WAV) to put under the silent reel")
    ap.add_argument("--tag", default="voice", help="the name of the cut with sound: <base>_<tag>_reel.mp4")
    args = ap.parse_args()
    import onebit
    assert CRF == onebit.SOCIAL_CRF and FPS == onebit.FPS and SIZE == tuple(onebit.SIZES["reel"])
    film = json.loads((BUILD / "film.json").read_text(encoding="utf-8"))
    cut = film["cuts"][args.cut]
    n = round(cut["end"] * FPS)
    assert n == {"a": 1065, "b": 2580}[args.cut], n
    SOCIAL.mkdir(parents=True, exist_ok=True)
    base = SOCIAL / f"{BASE}_{NAME[args.cut]}"
    silent = Path(f"{base}_reel.mp4")
    srv = serve()
    port = srv.server_address[1]
    if args.stills or args.at:
        from playwright.sync_api import sync_playwright
        times = args.at or sorted({0.0} | {round(s["start"] + f * s["length"], 2) for s in cut["scenes"]
                                           for f in (0.02, 0.4, 0.96)})
        with sync_playwright() as pw:
            browser, page = open_page(pw, port, args.cut)
            shoot(page, film["cover_t"], Path(f"{base}_cover.png"))
            if not args.at:
                for old in SOCIAL.glob(f"{base.name}_t*.png"):
                    old.unlink()
            for t in times:
                shoot(page, t, Path(f"{base}_t{t:05.2f}.png"))
                print("saved", f"{base}_t{t:05.2f}.png")
            browser.close()
        return
    if not args.sound or not silent.exists():
        folder = Path(tempfile.mkdtemp(prefix="elnino26i_", dir=BUILD))
        try:
            jobs = [(port, args.cut, list(range(k, n, args.workers)), str(folder)) for k in range(args.workers)]
            with mp.get_context("spawn").Pool(args.workers) as pool:
                done = sum(pool.map(worker, jobs))
            assert done == n and len(list(folder.glob("*.png"))) == n, (done, n)
            encode(folder, n, silent)
        finally:
            shutil.rmtree(folder, ignore_errors=True)
        print("saved", silent, f"({n} frames)")
    if args.sound:
        import onebit_persian as kit
        out = Path(f"{base}_{args.tag}_reel.mp4")
        kit.mux(silent, args.sound, out)
        print("saved", out)


if __name__ == "__main__":
    main()
