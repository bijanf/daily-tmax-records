"""Poster style: a dark, cinematic look with very few words.

Pure black canvas with a soft colour glow behind the hero data, Inter / Inter
Display type (open-source, close to Apple's system font), Apple dark-mode
system colours, one headline, one short line, a tiny footnote.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.colors import to_rgb  # noqa: E402
from matplotlib.path import Path as MplPath  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402
from scipy.special import erf  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "data" / "fonts" / "inter" / "ttf"

BLACK = "#000000"
INK = "#F5F5F7"
GRAY = "#86868B"
DIM = "#2C2C2E"
RED = "#FF453A"
ORANGE = "#FF9F0A"
BLUE = "#0A84FF"
YELLOW = "#FFD60A"

W, H, DPI = 7.2, 9.0, 300
LEFT = 0.08
SIGNATURE = "Bijan Fallah"

for _ttf in FONTS.glob("*.ttf"):
    font_manager.fontManager.addfont(str(_ttf))
DISPLAY = "Inter Display" if any(f.name == "Inter Display" for f in font_manager.fontManager.ttflist) else "Lato"
TEXT_FONT = "Inter" if DISPLAY == "Inter Display" else "Lato"


def apply_style() -> None:
    """Poster defaults; call again after importing modules that set their own style."""
    plt.rcParams.update({
        "font.family": TEXT_FONT,
        "font.sans-serif": [TEXT_FONT, "DejaVu Sans"],
        "figure.facecolor": BLACK,
        "savefig.facecolor": BLACK,
        "axes.facecolor": "none",
        "text.color": INK,
        "xtick.color": GRAY,
        "ytick.color": GRAY,
        "pdf.fonttype": 42,
    })


apply_style()


def new_poster(glow: str | None = None, at=(0.5, 0.45), size=0.35, alpha=0.18):
    """Black canvas; optional radial glow centred at `at` (figure coordinates)."""
    fig = plt.figure(figsize=(W, H), dpi=DPI, facecolor=BLACK)
    if glow:
        bg = fig.add_axes([0, 0, 1, 1], zorder=-10)
        bg.axis("off")
        ny, nx = 900, 720
        yy, xx = np.mgrid[0:1:complex(ny), 0:1:complex(nx)]
        r2 = ((xx - at[0]) / size) ** 2 + ((yy - at[1]) / (size * W / H)) ** 2
        img = np.zeros((ny, nx, 4))
        img[..., :3] = to_rgb(glow)
        img[..., 3] = alpha * np.exp(-r2)
        bg.imshow(img, extent=(0, 1, 0, 1), origin="lower", aspect="auto", interpolation="bilinear")
        bg.set_xlim(0, 1)
        bg.set_ylim(0, 1)
    return fig


def headline(fig, text, y=0.935, size=58):
    fig.text(LEFT, y, text, fontfamily=DISPLAY, fontweight="bold", fontsize=size, color=INK,
             va="top", ha="left", linespacing=0.95)


def subline(fig, text, y, size=13):
    fig.text(LEFT, y, text, fontfamily=TEXT_FONT, fontweight="medium", fontsize=size, color=GRAY,
             va="top", ha="left", linespacing=1.25)


def footnote(fig, text):
    fig.text(LEFT, 0.035, text, fontsize=5.8, color=GRAY, va="bottom", ha="left", linespacing=1.45)
    fig.text(1 - LEFT, 0.035, SIGNATURE, fontsize=6.2, fontweight="semibold", color=INK,
             va="bottom", ha="right")


def bare(ax):
    for side in ax.spines.values():
        side.set_visible(False)
    ax.tick_params(length=0, pad=4, labelsize=7, colors=GRAY)
    ax.set_facecolor("none")


def px_per_unit(ax):
    p0, p1 = ax.transData.transform((0, 0)), ax.transData.transform((1, 1))
    return abs(p1[0] - p0[0]), abs(p1[1] - p0[1])


def top_rounded_bar(ax, x, h, width, color, alpha=1.0, radius_px=10, zorder=3):
    """One path from 0 to h: square base, rounded far end (circular on screen); h may be negative.
    Axes limits must be final."""
    sx, sy = px_per_unit(ax)
    sign, h = (1, h) if h >= 0 else (-1, -h)
    rx, ry = min(radius_px / sx, width / 2), min(radius_px / sy, h)
    x0, x1, k = x - width / 2, x + width / 2, 0.5523
    verts = [(x0, 0), (x1, 0), (x1, h - ry),
             (x1, h - ry + k * ry), (x1 - rx + k * rx, h), (x1 - rx, h),
             (x0 + rx, h),
             (x0 + rx - k * rx, h), (x0, h - ry + k * ry), (x0, h - ry),
             (x0, 0)]
    verts = [(vx, sign * vy) for vx, vy in verts]
    codes = [MplPath.MOVETO, MplPath.LINETO, MplPath.LINETO,
             MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
             MplPath.LINETO,
             MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
             MplPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MplPath(verts, codes), fc=color, ec="none", alpha=alpha, zorder=zorder))


def glow_box(ax, x0, x1, y0, y1, color, sigma_px=45, strength=0.55, zorder=2):
    """Gaussian-blurred rectangle of light behind a mark, drawn past the axes edges."""
    sx, sy = px_per_unit(ax)
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    s2 = sigma_px * np.sqrt(2)
    X0, X1 = x0 - 3 * sigma_px / sx, x1 + 3 * sigma_px / sx
    Y0, Y1 = y0 - 3 * sigma_px / sy, y1 + 3 * sigma_px / sy
    xs, ys = np.linspace(X0, X1, 240), np.linspace(Y0, Y1, 480)
    gx = 0.5 * (erf((xs - x0) * sx / s2) - erf((xs - x1) * sx / s2))
    gy = 0.5 * (erf((ys - y0) * sy / s2) - erf((ys - y1) * sy / s2))
    img = np.zeros((len(ys), len(xs), 4))
    img[..., :3] = to_rgb(color)
    img[..., 3] = strength * np.outer(gy, gx)
    im = ax.imshow(img, extent=(X0, X1, Y0, Y1), origin="lower", aspect="auto", zorder=zorder,
                   interpolation="bilinear")
    im.set_clip_on(False)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)


def halo(ax, x, y, color, size=60, layers=6, zorder=5):
    """Soft glow around a point: stacked translucent discs."""
    for k in range(layers, 0, -1):
        ax.scatter([x], [y], s=size * (1 + 1.6 * k) ** 2 / 4, color=color, alpha=0.05,
                   linewidth=0, zorder=zorder, clip_on=False)
    ax.scatter([x], [y], s=size, color=color, edgecolor=INK, linewidth=1.0, zorder=zorder + 1,
               clip_on=False)


def save(fig, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    print(path)
