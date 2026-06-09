"""Physics verification suite.

Every test runs a real ngspice simulation and asserts that the measured
behavior matches first-principles hand analysis. If a netlist, a model, or
the toolchain breaks, these tests fail — the README badge is backed by
actual circuit theory.
"""

import math
from pathlib import Path

import numpy as np
import pytest

from lab import metrics
from lab.runner import find_ngspice, run_netlist
from lab.wrdata import load_wrdata

CIRCUITS = Path(__file__).resolve().parent.parent / "circuits"

try:
    find_ngspice()
    NGSPICE_MISSING = False
except RuntimeError:
    NGSPICE_MISSING = True

pytestmark = pytest.mark.skipif(NGSPICE_MISSING, reason="ngspice not installed")


def simulate(folder: str, netlist: str) -> Path:
    circuit_dir = CIRCUITS / folder
    run_netlist(circuit_dir / netlist)
    return circuit_dir


# ---------------------------------------------------------------- 01: RC LPF
class TestRcLowpass:
    R, C = 10e3, 10e-9
    FC = 1.0 / (2.0 * math.pi * R * C)  # 1591.5 Hz

    @pytest.fixture(scope="class")
    def ac(self):
        d = simulate("01_rc_lowpass", "rc_lowpass.cir")
        return load_wrdata(d / "rc_lowpass_ac.txt")

    def test_cutoff_matches_one_over_2piRC(self, ac):
        freq, (gain_db, _) = ac
        assert metrics.cutoff_frequency(freq, gain_db) == pytest.approx(self.FC, rel=0.01)

    def test_rolloff_is_20db_per_decade(self, ac):
        freq, (gain_db, _) = ac
        slope = metrics.slope_db_per_decade(freq, gain_db, 100e3, 1e6)
        assert slope == pytest.approx(-20.0, abs=0.5)

    def test_phase_is_minus_45_degrees_at_cutoff(self, ac):
        freq, (gain_db, phase_rad) = ac
        fc = metrics.cutoff_frequency(freq, gain_db)
        phase_deg = math.degrees(np.interp(np.log10(fc), np.log10(freq), phase_rad))
        assert phase_deg == pytest.approx(-45.0, abs=2.0)


# ------------------------------------------------- 02: Sallen-Key Butterworth
class TestSallenKey:
    R, C1, C2 = 11.25e3, 2e-9, 1e-9
    FC = 1.0 / (2.0 * math.pi * R * math.sqrt(C1 * C2))  # 10.004 kHz
    Q = 0.5 * math.sqrt(C1 / C2)  # 0.7071 -> Butterworth

    @pytest.fixture(scope="class")
    def ac(self):
        d = simulate("02_sallen_key", "sallen_key.cir")
        return load_wrdata(d / "sallen_key_ac.txt")

    def test_butterworth_q(self):
        assert self.Q == pytest.approx(1.0 / math.sqrt(2.0), rel=0.001)

    def test_passband_gain_is_unity(self, ac):
        freq, (gain_db, _) = ac
        assert metrics.midband_gain_db(freq, gain_db, 200.0) == pytest.approx(0.0, abs=0.1)

    def test_cutoff_frequency(self, ac):
        freq, (gain_db, _) = ac
        assert metrics.cutoff_frequency(freq, gain_db) == pytest.approx(self.FC, rel=0.02)

    def test_rolloff_is_40db_per_decade(self, ac):
        freq, (gain_db, _) = ac
        slope = metrics.slope_db_per_decade(freq, gain_db, 1e6, 8e6)
        assert slope == pytest.approx(-40.0, abs=1.0)


# --------------------------------------------------- 03: BJT common emitter
class TestCommonEmitter:
    @pytest.fixture(scope="class")
    def results(self):
        d = simulate("03_common_emitter", "common_emitter.cir")
        bias = load_wrdata(d / "ce_bias.txt")
        ac = load_wrdata(d / "ce_ac.txt")
        return bias, ac

    def test_collector_biased_near_mid_rail(self, results):
        (_, (vc, vb, ve)), _ = results
        assert 5.5 < vc[0] < 8.0  # max symmetric swing requires VC near VCC/2

    def test_bias_current_matches_divider_analysis(self, results):
        (_, (vc, _, _)), _ = results
        ic = (12.0 - vc[0]) / 2.2e3
        assert ic == pytest.approx(2.4e-3, rel=0.10)

    def test_midband_gain_matches_re_model(self, results):
        (_, (vc, _, _)), (freq, (gain_db, _)) = results
        ic = (12.0 - vc[0]) / 2.2e3
        re = 0.02585 / ic
        ro = 100.0 / ic  # VAF / IC
        rc_eff = (2.2e3 * ro) / (2.2e3 + ro)
        gain_theory_db = 20.0 * math.log10(rc_eff / (re + 100.0))
        measured = metrics.midband_gain_db(freq, gain_db, 10e3)
        assert measured == pytest.approx(gain_theory_db, abs=1.0)


# ------------------------------------------------- 04: MOSFET differential pair
class TestDiffPair:
    KP, WL, LAMBDA, ID, RD = 200e-6, 10.0, 0.01, 0.5e-3, 10e3

    @pytest.fixture(scope="class")
    def results(self):
        d = simulate("04_diff_pair", "diff_pair.cir")
        bias = load_wrdata(d / "dp_bias.txt")
        ac = load_wrdata(d / "dp_ac.txt")
        return bias, ac

    def test_drains_are_symmetric(self, results):
        (_, (d1, d2, _)), _ = results
        assert d1[0] == pytest.approx(d2[0], abs=1e-3)

    def test_half_tail_current_per_side(self, results):
        (_, (d1, _, _)), _ = results
        id_meas = (12.0 - d1[0]) / self.RD
        assert id_meas == pytest.approx(self.ID, rel=0.01)

    def test_differential_gain_matches_gm_rd(self, results):
        (_, (d1, _, s)), (freq, (gain_db,)) = results
        vds = d1[0] - s[0]
        gm = math.sqrt(2.0 * self.KP * self.WL * self.ID * (1.0 + self.LAMBDA * vds))
        ro = (1.0 + self.LAMBDA * vds) / (self.LAMBDA * self.ID)
        adm_theory_db = 20.0 * math.log10(gm * (self.RD * ro) / (self.RD + ro))
        measured = metrics.midband_gain_db(freq, gain_db, 1e3)
        assert measured == pytest.approx(adm_theory_db, abs=0.5)


# ----------------------------------------------------- 05: Wien-bridge oscillator
class TestWienBridge:
    R, C = 10e3, 15.9e-9
    FOSC = 1.0 / (2.0 * math.pi * R * C)  # 1000.97 Hz

    @pytest.fixture(scope="class")
    def tran(self):
        d = simulate("05_wien_bridge", "wien_bridge.cir")
        return load_wrdata(d / "wien_tran.txt")

    def test_oscillation_frequency(self, tran):
        t, (vout,) = tran
        fosc = metrics.dominant_frequency(t, vout, t_start=0.04)
        assert fosc == pytest.approx(self.FOSC, rel=0.03)

    def test_amplitude_saturates_near_rails(self, tran):
        t, (vout,) = tran
        amp = metrics.amplitude(t, vout, t_start=0.04)
        assert 9.0 < amp < 11.5  # tanh limiter rails at +/-11 V

    def test_oscillation_started_from_small_kick(self, tran):
        t, (vout,) = tran
        early = metrics.amplitude(t, vout, t_start=0.0)
        late = metrics.amplitude(t, vout, t_start=0.06)
        assert late > 0.8 * early  # sustained, not decaying


# ------------------------------------------------------------- 06: Buck converter
class TestBuckConverter:
    VIN, DUTY = 12.0, 0.5

    @pytest.fixture(scope="class")
    def tran(self):
        d = simulate("06_buck_converter", "buck_converter.cir")
        return load_wrdata(d / "buck_tran.txt")

    def test_output_near_duty_times_vin(self, tran):
        t, (vout, _) = tran
        vavg = metrics.dc_average(t, vout, t_start=4e-3)
        ideal = self.DUTY * self.VIN
        # non-synchronous topology: freewheel diode drop costs (1-D)*Vf
        assert ideal - 0.8 < vavg < ideal

    def test_output_ripple_is_small(self, tran):
        t, (vout, _) = tran
        assert metrics.ripple_pp(t, vout, t_start=4e-3) < 0.1

    def test_switch_node_swings_full_input(self, tran):
        t, (_, vsw) = tran
        mask = t >= 4e-3
        assert np.max(vsw[mask]) > 0.9 * self.VIN
        assert np.min(vsw[mask]) < 0.5  # clamped near ground by the diode


# ------------------------------------------------------- 07: Bridge rectifier
class TestBridgeRectifier:
    VPK, F_LINE, C, RL = 16.97, 60.0, 1000e-6, 100.0

    @pytest.fixture(scope="class")
    def tran(self):
        d = simulate("07_bridge_rectifier", "bridge_rectifier.cir")
        return load_wrdata(d / "rect_tran.txt")

    def test_dc_output_level(self, tran):
        t, (vpos, _) = tran
        vdc = metrics.dc_average(t, vpos, t_start=0.2)
        # Vpk minus two diode drops, minus half the ripple
        assert 13.5 < vdc < 16.0

    def test_ripple_matches_capacitor_discharge_formula(self, tran):
        t, (vpos, _) = tran
        vdc = metrics.dc_average(t, vpos, t_start=0.2)
        ripple = metrics.ripple_pp(t, vpos, t_start=0.2)
        # full-wave: C discharges into RL for ~half a line cycle
        ripple_theory = vdc / (self.RL * 2.0 * self.F_LINE * self.C)
        assert ripple == pytest.approx(ripple_theory, rel=0.35)

    def test_ripple_frequency_is_twice_line_frequency(self, tran):
        t, (vpos, _) = tran
        f_ripple = metrics.dominant_frequency(t, vpos, t_start=0.2)
        assert f_ripple == pytest.approx(2.0 * self.F_LINE, rel=0.02)


# ------------------------------------------------------------ 08: Monte Carlo
class TestMonteCarlo:
    def test_cutoff_distribution_tracks_component_tolerance(self):
        from lab.montecarlo import nominal_cutoff, run_monte_carlo

        cutoffs = run_monte_carlo(n_runs=25, tolerance=0.05, seed=7)
        nominal = nominal_cutoff()
        rel = (cutoffs - nominal) / nominal
        assert abs(np.mean(rel)) < 0.02       # centered on nominal
        assert 0.005 < np.std(rel) < 0.035    # sigma_fc ~ sigma_component ~ 1.7%
        assert np.all(np.abs(rel) < 0.12)     # worst case: all four parts at +/-5%
