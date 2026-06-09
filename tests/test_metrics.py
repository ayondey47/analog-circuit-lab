"""Unit tests for waveform measurement functions, using synthetic data
with known analytical answers."""

import numpy as np
import pytest

from lab import metrics


@pytest.fixture
def first_order_lowpass():
    """Ideal first-order low-pass response with fc = 1 kHz."""
    fc = 1000.0
    freq = np.logspace(1, 6, 500)
    gain = 1.0 / np.sqrt(1.0 + (freq / fc) ** 2)
    return freq, 20.0 * np.log10(gain), fc


def test_cutoff_frequency(first_order_lowpass):
    freq, gain_db, fc = first_order_lowpass
    measured = metrics.cutoff_frequency(freq, gain_db)
    assert measured == pytest.approx(fc, rel=0.01)


def test_slope_of_first_order_rolloff(first_order_lowpass):
    freq, gain_db, fc = first_order_lowpass
    slope = metrics.slope_db_per_decade(freq, gain_db, 50e3, 500e3)
    assert slope == pytest.approx(-20.0, abs=0.5)


def test_midband_gain(first_order_lowpass):
    freq, gain_db, _ = first_order_lowpass
    assert metrics.midband_gain_db(freq, gain_db, 20.0) == pytest.approx(0.0, abs=0.01)


def test_cutoff_raises_when_gain_is_flat():
    freq = np.logspace(1, 4, 50)
    gain_db = np.zeros_like(freq)
    with pytest.raises(ValueError):
        metrics.cutoff_frequency(freq, gain_db)


def test_dc_average_of_offset_sine():
    t = np.linspace(0, 0.1, 20001)
    v = 5.0 + 2.0 * np.sin(2 * np.pi * 100 * t)
    assert metrics.dc_average(t, v, t_start=0.0) == pytest.approx(5.0, abs=0.01)


def test_ripple_pp_of_sine():
    t = np.linspace(0, 0.1, 20001)
    v = 5.0 + 0.5 * np.sin(2 * np.pi * 100 * t)
    assert metrics.ripple_pp(t, v, t_start=0.0) == pytest.approx(1.0, rel=0.01)


def test_dominant_frequency_of_sine():
    t = np.linspace(0, 0.05, 50001)
    v = 3.3 * np.sin(2 * np.pi * 997.0 * t + 0.3)
    assert metrics.dominant_frequency(t, v, t_start=0.0) == pytest.approx(997.0, rel=0.001)


def test_dominant_frequency_ignores_dc_offset():
    t = np.linspace(0, 0.05, 50001)
    v = 12.0 + 0.1 * np.sin(2 * np.pi * 2500.0 * t)
    assert metrics.dominant_frequency(t, v, t_start=0.0) == pytest.approx(2500.0, rel=0.001)


def test_amplitude_of_sine():
    t = np.linspace(0, 0.05, 50001)
    v = 1.5 * np.sin(2 * np.pi * 1000.0 * t)
    assert metrics.amplitude(t, v, t_start=0.0) == pytest.approx(1.5, rel=0.01)
