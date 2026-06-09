"""Measurement functions for simulation waveforms.

Every function takes plain numpy arrays so it works on any simulator output,
and every returned figure of merit is directly comparable to hand analysis.
"""

from __future__ import annotations

import numpy as np


def cutoff_frequency(freq: np.ndarray, gain_db: np.ndarray, drop_db: float = 3.0) -> float:
    """Frequency where gain falls `drop_db` below its maximum (log-interpolated)."""
    ref = np.max(gain_db)
    target = ref - drop_db
    below = np.where(gain_db < target)[0]
    if below.size == 0:
        raise ValueError("Gain never drops below the target level.")
    i = below[0]
    if i == 0:
        return float(freq[0])
    # Interpolate in log-frequency for accuracy on decade sweeps.
    f1, f2 = np.log10(freq[i - 1]), np.log10(freq[i])
    g1, g2 = gain_db[i - 1], gain_db[i]
    logf = f1 + (target - g1) * (f2 - f1) / (g2 - g1)
    return float(10.0 ** logf)


def slope_db_per_decade(
    freq: np.ndarray, gain_db: np.ndarray, f_low: float, f_high: float
) -> float:
    """Average gain slope between two frequencies, in dB/decade."""
    g_low = float(np.interp(np.log10(f_low), np.log10(freq), gain_db))
    g_high = float(np.interp(np.log10(f_high), np.log10(freq), gain_db))
    return (g_high - g_low) / (np.log10(f_high) - np.log10(f_low))


def midband_gain_db(freq: np.ndarray, gain_db: np.ndarray, f_at: float) -> float:
    """Gain (dB) interpolated at a specific frequency."""
    return float(np.interp(np.log10(f_at), np.log10(freq), gain_db))


def _steady(t: np.ndarray, v: np.ndarray, t_start: float) -> tuple[np.ndarray, np.ndarray]:
    mask = t >= t_start
    if mask.sum() < 2:
        raise ValueError("Not enough samples after t_start.")
    return t[mask], v[mask]


def dc_average(t: np.ndarray, v: np.ndarray, t_start: float = 0.0) -> float:
    """Time-weighted average of v over the window after t_start."""
    ts, vs = _steady(t, v, t_start)
    trapezoid = getattr(np, "trapezoid", np.trapz)
    return float(trapezoid(vs, ts) / (ts[-1] - ts[0]))


def ripple_pp(t: np.ndarray, v: np.ndarray, t_start: float = 0.0) -> float:
    """Peak-to-peak ripple after t_start."""
    _, vs = _steady(t, v, t_start)
    return float(np.max(vs) - np.min(vs))


def amplitude(t: np.ndarray, v: np.ndarray, t_start: float = 0.0) -> float:
    """Half the peak-to-peak swing after t_start."""
    return ripple_pp(t, v, t_start) / 2.0


def dominant_frequency(t: np.ndarray, v: np.ndarray, t_start: float = 0.0) -> float:
    """Fundamental frequency from rising zero crossings of the AC component.

    Linear interpolation at each crossing gives sub-sample resolution; the
    result is averaged over all full periods in the window.
    """
    ts, vs = _steady(t, v, t_start)
    vs = vs - np.mean(vs)
    sign = np.signbit(vs)
    rising = np.where(sign[:-1] & ~sign[1:])[0]
    if rising.size < 2:
        raise ValueError("Fewer than two rising zero crossings; cannot measure frequency.")
    crossings = []
    for i in rising:
        frac = -vs[i] / (vs[i + 1] - vs[i])
        crossings.append(ts[i] + frac * (ts[i + 1] - ts[i]))
    crossings = np.asarray(crossings)
    period = (crossings[-1] - crossings[0]) / (crossings.size - 1)
    return float(1.0 / period)
