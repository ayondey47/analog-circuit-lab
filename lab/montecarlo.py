"""Monte Carlo component-tolerance analysis.

Samples component values from a truncated gaussian (sigma = tolerance/3,
clipped at +/-tolerance — the usual model for binned commercial parts),
renders the netlist template per run, simulates, and measures the cutoff
frequency of each sample.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from .metrics import cutoff_frequency
from .runner import run_netlist
from .wrdata import load_wrdata

TEMPLATE = Path(__file__).resolve().parent.parent / "circuits" / "08_monte_carlo" / "sallen_key_mc.template.cir"

NOMINAL = {"r1": 11.25e3, "r2": 11.25e3, "c1": 2e-9, "c2": 1e-9}


def nominal_cutoff() -> float:
    """Analytical cutoff for nominal component values."""
    n = NOMINAL
    return 1.0 / (2.0 * np.pi * np.sqrt(n["r1"] * n["r2"] * n["c1"] * n["c2"]))


def sample_components(rng: np.random.Generator, tolerance: float) -> dict[str, float]:
    """Draw one set of component values from the tolerance distribution."""
    sampled = {}
    for name, nominal in NOMINAL.items():
        deviation = rng.normal(0.0, tolerance / 3.0)
        deviation = float(np.clip(deviation, -tolerance, tolerance))
        sampled[name] = nominal * (1.0 + deviation)
    return sampled


def run_monte_carlo(
    n_runs: int = 200, tolerance: float = 0.05, seed: int = 42
) -> np.ndarray:
    """Run the Monte Carlo study. Returns the measured cutoff of every sample."""
    template = TEMPLATE.read_text()
    rng = np.random.default_rng(seed)
    cutoffs = np.empty(n_runs)
    with tempfile.TemporaryDirectory(prefix="mc_sallen_key_") as tmp:
        netlist = Path(tmp) / "sample.cir"
        datafile = Path(tmp) / "mc_ac.txt"
        for i in range(n_runs):
            values = sample_components(rng, tolerance)
            netlist.write_text(template.format(**values))
            run_netlist(netlist)
            freq, (gain_db,) = load_wrdata(datafile)
            cutoffs[i] = cutoff_frequency(freq, gain_db)
    return cutoffs
