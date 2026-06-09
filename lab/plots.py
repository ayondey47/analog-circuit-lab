"""Shared plot styling and annotation helpers.

One consistent visual language for every figure in the lab: light theme,
muted grid, a small fixed palette, and measurement annotations drawn the
same way everywhere.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

INK = "#1E293B"        # slate-800: axes, text
PRIMARY = "#0E7490"    # cyan-700: simulated traces
ACCENT = "#D97706"     # amber-600: annotations, markers
THEORY = "#94A3B8"     # slate-400: analytical overlays
EXTRA = "#7C3AED"      # violet-600: secondary traces


def apply_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "figure.dpi": 110,
            "savefig.dpi": 160,
            "savefig.bbox": "tight",
            "axes.facecolor": "#FBFDFE",
            "axes.edgecolor": INK,
            "axes.labelcolor": INK,
            "axes.titleweight": "bold",
            "axes.titlesize": 11.5,
            "axes.labelsize": 10,
            "axes.grid": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": "#CBD5E1",
            "grid.linewidth": 0.6,
            "grid.alpha": 0.45,
            "xtick.color": INK,
            "ytick.color": INK,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.frameon": False,
            "legend.fontsize": 9,
            "font.family": "DejaVu Sans",
            "lines.linewidth": 1.8,
        }
    )


def mark_point(ax, x: float, y: float, label: str) -> None:
    """Drop an annotated measurement marker on a trace."""
    ax.plot([x], [y], "o", color=ACCENT, markersize=6, zorder=5)
    ax.annotate(
        label,
        xy=(x, y),
        xytext=(12, -18),
        textcoords="offset points",
        fontsize=8.5,
        color=INK,
        bbox=dict(boxstyle="round,pad=0.3", fc="#FFFBEB", ec=ACCENT, lw=0.8),
        arrowprops=dict(arrowstyle="-", color=ACCENT, lw=0.8),
    )


def info_box(ax, text: str, loc: str = "upper right") -> None:
    """Place a measurement summary box on the axes."""
    positions = {
        "upper right": (0.97, 0.95, "right", "top"),
        "upper left": (0.03, 0.95, "left", "top"),
        "lower left": (0.03, 0.05, "left", "bottom"),
        "lower right": (0.97, 0.05, "right", "bottom"),
    }
    x, y, ha, va = positions[loc]
    ax.text(
        x,
        y,
        text,
        transform=ax.transAxes,
        ha=ha,
        va=va,
        fontsize=8.5,
        color=INK,
        bbox=dict(boxstyle="round,pad=0.45", fc="#F0FDFA", ec=PRIMARY, lw=0.9),
    )
