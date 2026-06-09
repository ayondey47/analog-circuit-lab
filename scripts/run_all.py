"""Run every simulation in the lab, regenerate all plots, and write the
measured-vs-theory results table to docs/RESULTS.md.

Usage:  python scripts/run_all.py [--mc-runs N]
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt

from lab import metrics, plots
from lab.montecarlo import NOMINAL, nominal_cutoff, run_monte_carlo
from lab.runner import run_netlist
from lab.wrdata import load_wrdata

CIRCUITS = ROOT / "circuits"
PLOTS = ROOT / "docs" / "plots"

results: list[tuple[str, str, str, str, str]] = []


def fmt(value: float, unit: str) -> str:
    text = f"{value:,.0f}" if abs(value) >= 1000 else f"{value:.4g}"
    return f"{text} {unit}"


def record(circuit: str, quantity: str, theory: float, simulated: float, unit: str) -> None:
    err = 100.0 * (simulated - theory) / theory
    results.append(
        (circuit, quantity, fmt(theory, unit), fmt(simulated, unit), f"{err:+.2f}%")
    )


def save(fig, name: str) -> None:
    path = PLOTS / name
    fig.savefig(path)
    plt.close(fig)
    print(f"  wrote {path.relative_to(ROOT)}")


# ---------------------------------------------------------------- 01: RC LPF
def rc_lowpass() -> None:
    print("[01] RC low-pass filter")
    d = CIRCUITS / "01_rc_lowpass"
    run_netlist(d / "rc_lowpass.cir")
    freq, (gain_db, phase_rad) = load_wrdata(d / "rc_lowpass_ac.txt")
    phase_deg = np.degrees(phase_rad)

    fc_theory = 1.0 / (2.0 * math.pi * 10e3 * 10e-9)
    fc = metrics.cutoff_frequency(freq, gain_db)
    record("01 RC low-pass", "Cutoff f-3dB", fc_theory, fc, "Hz")

    gain_theory = -10.0 * np.log10(1.0 + (freq / fc_theory) ** 2)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    ax1.semilogx(freq, gain_theory, "--", color=plots.THEORY, label="theory  1/(1+jf/fc)")
    ax1.semilogx(freq, gain_db, color=plots.PRIMARY, label="ngspice")
    ax1.set_ylabel("Gain (dB)")
    ax1.set_title("First-Order RC Low-Pass — Bode Response (R=10k, C=10n)")
    plots.mark_point(ax1, fc, -3.0, f"f₋₃dB = {fc:,.0f} Hz\n(theory {fc_theory:,.0f} Hz)")
    ax1.legend(loc="lower left")

    ax2.semilogx(freq, phase_deg, color=plots.EXTRA)
    ax2.set_ylabel("Phase (°)")
    ax2.set_xlabel("Frequency (Hz)")
    phase_at_fc = float(np.interp(np.log10(fc), np.log10(freq), phase_deg))
    plots.mark_point(ax2, fc, phase_at_fc, f"{phase_at_fc:.1f}° at f₋₃dB")
    save(fig, "01_rc_lowpass_bode.png")


# ------------------------------------------------- 02: Sallen-Key Butterworth
def sallen_key() -> None:
    print("[02] Sallen-Key Butterworth filter")
    d = CIRCUITS / "02_sallen_key"
    run_netlist(d / "sallen_key.cir")
    freq, (gain_db, _) = load_wrdata(d / "sallen_key_ac.txt")

    fc_theory = 1.0 / (2.0 * math.pi * 11.25e3 * math.sqrt(2e-9 * 1e-9))
    fc = metrics.cutoff_frequency(freq, gain_db)
    slope = metrics.slope_db_per_decade(freq, gain_db, 1e6, 8e6)
    record("02 Sallen-Key", "Cutoff f-3dB", fc_theory, fc, "Hz")
    record("02 Sallen-Key", "Stopband slope", -40.0, slope, "dB/dec")

    gain_theory = -10.0 * np.log10(1.0 + (freq / fc_theory) ** 4)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.semilogx(freq, gain_theory, "--", color=plots.THEORY, label="ideal 2nd-order Butterworth")
    ax.semilogx(freq, gain_db, color=plots.PRIMARY, label="ngspice")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Gain (dB)")
    ax.set_title("Sallen-Key Butterworth Low-Pass (Q = 0.707, fc = 10 kHz)")
    plots.mark_point(ax, fc, -3.0, f"f₋₃dB = {fc/1e3:,.2f} kHz")
    plots.info_box(ax, f"stopband slope: {slope:.1f} dB/decade", loc="lower left")
    ax.legend(loc="upper right")
    save(fig, "02_sallen_key_bode.png")


# --------------------------------------------------- 03: BJT common emitter
def common_emitter() -> None:
    print("[03] BJT common-emitter amplifier")
    d = CIRCUITS / "03_common_emitter"
    run_netlist(d / "common_emitter.cir")
    _, (vc, vb, ve) = load_wrdata(d / "ce_bias.txt")
    freq, (gain_db, _) = load_wrdata(d / "ce_ac.txt")
    t, (vin, vc_t) = load_wrdata(d / "ce_tran.txt")

    ic = (12.0 - vc[0]) / 2.2e3
    re = 0.02585 / ic
    ro = 100.0 / ic
    rc_eff = 2.2e3 * ro / (2.2e3 + ro)
    gain_theory_db = 20.0 * math.log10(rc_eff / (re + 100.0))
    gain = metrics.midband_gain_db(freq, gain_db, 10e3)
    record("03 Common-emitter", "Midband gain", gain_theory_db, gain, "dB")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    ax1.semilogx(freq, gain_db, color=plots.PRIMARY)
    ax1.set_xlabel("Frequency (Hz)")
    ax1.set_ylabel("Gain (dB)")
    ax1.set_title("Frequency Response")
    plots.info_box(
        ax1,
        f"midband gain: {gain:.1f} dB\nre-model theory: {gain_theory_db:.1f} dB\n"
        f"bias: IC = {ic*1e3:.2f} mA, VC = {vc[0]:.2f} V",
        loc="lower left",
    )

    ms = t * 1e3
    ax2.plot(ms, vin * 1e3, color=plots.THEORY, label="input (mV)")
    ax2.plot(ms, (vc_t - np.mean(vc_t[t > 1e-3])) * 1e3, color=plots.ACCENT, label="output, AC-coupled (mV)")
    ax2.set_xlim(1.0, 1.6)
    ax2.set_xlabel("Time (ms)")
    ax2.set_ylabel("Amplitude (mV)")
    ax2.set_title("5 mV / 5 kHz Input vs Output (inverting)")
    ax2.legend(loc="upper right")
    fig.suptitle("BJT Common-Emitter Amplifier", fontweight="bold", y=1.02)
    save(fig, "03_common_emitter.png")


# ------------------------------------------------ 04: MOSFET differential pair
def diff_pair() -> None:
    print("[04] MOSFET differential pair")
    d = CIRCUITS / "04_diff_pair"
    run_netlist(d / "diff_pair.cir")
    _, (d1b, d2b, sb) = load_wrdata(d / "dp_bias.txt")
    freq, (gain_db,) = load_wrdata(d / "dp_ac.txt")
    vg, (d1, d2) = load_wrdata(d / "dp_dc.txt")

    vds = d1b[0] - sb[0]
    gm = math.sqrt(2.0 * 200e-6 * 10.0 * 0.5e-3 * (1.0 + 0.01 * vds))
    ro = (1.0 + 0.01 * vds) / (0.01 * 0.5e-3)
    adm_theory = 20.0 * math.log10(gm * (10e3 * ro) / (10e3 + ro))
    adm = metrics.midband_gain_db(freq, gain_db, 1e3)
    record("04 Diff pair", "Differential gain", adm_theory, adm, "dB")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    ax1.plot(vg * 1e3, d1, color=plots.PRIMARY, label="V(d1)")
    ax1.plot(vg * 1e3, d2, color=plots.EXTRA, label="V(d2)")
    ax1.set_xlabel("Differential input (mV)")
    ax1.set_ylabel("Drain voltage (V)")
    ax1.set_title("DC Transfer — Current Steering")
    ax1.legend()

    ax2.semilogx(freq, gain_db, color=plots.PRIMARY)
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("|Adm| (dB)")
    ax2.set_title("Differential Gain")
    plots.info_box(
        ax2,
        f"Adm = {adm:.2f} dB\ngm·(RD∥ro) theory = {adm_theory:.2f} dB",
        loc="lower left",
    )
    fig.suptitle("MOSFET Differential Pair (ITAIL = 1 mA)", fontweight="bold", y=1.02)
    save(fig, "04_diff_pair.png")


# ----------------------------------------------------- 05: Wien-bridge oscillator
def wien_bridge() -> None:
    print("[05] Wien-bridge oscillator")
    d = CIRCUITS / "05_wien_bridge"
    run_netlist(d / "wien_bridge.cir")
    t, (vout,) = load_wrdata(d / "wien_tran.txt")

    fosc_theory = 1.0 / (2.0 * math.pi * 10e3 * 15.9e-9)
    fosc = metrics.dominant_frequency(t, vout, t_start=0.04)
    record("05 Wien bridge", "Oscillation freq", fosc_theory, fosc, "Hz")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    ax1.plot(t * 1e3, vout, color=plots.PRIMARY, lw=0.8)
    ax1.set_xlabel("Time (ms)")
    ax1.set_ylabel("V(out) (V)")
    ax1.set_title("Startup — Exponential Growth to Limit Cycle")

    mask = (t >= 0.060) & (t <= 0.065)
    ax2.plot(t[mask] * 1e3, vout[mask], color=plots.ACCENT)
    ax2.set_xlabel("Time (ms)")
    ax2.set_ylabel("V(out) (V)")
    ax2.set_title("Steady State")
    plots.info_box(
        ax2,
        f"f = {fosc:,.1f} Hz\n1/(2πRC) = {fosc_theory:,.1f} Hz",
        loc="lower left",
    )
    fig.suptitle("Wien-Bridge Oscillator (R = 10k, C = 15.9n)", fontweight="bold", y=1.02)
    save(fig, "05_wien_bridge.png")


# ------------------------------------------------------------- 06: Buck converter
def buck_converter() -> None:
    print("[06] Buck converter")
    d = CIRCUITS / "06_buck_converter"
    run_netlist(d / "buck_converter.cir")
    t, (vout, vsw) = load_wrdata(d / "buck_tran.txt")

    vavg = metrics.dc_average(t, vout, t_start=4e-3)
    ripple = metrics.ripple_pp(t, vout, t_start=4e-3)
    record("06 Buck converter", "Output voltage", 6.0, vavg, "V")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    ax1.plot(t * 1e3, vout, color=plots.PRIMARY, lw=1.0)
    ax1.axhline(6.0, ls="--", color=plots.THEORY)
    ax1.text(3.2, 6.12, "ideal D·Vin = 6 V", fontsize=8.5, color=plots.INK)
    ax1.set_xlabel("Time (ms)")
    ax1.set_ylabel("V(out) (V)")
    ax1.set_title("Startup Transient (LC ringing → steady state)")

    mask = (t >= 4.95e-3) & (t <= 4.99e-3)
    ax2.plot((t[mask] - 4.95e-3) * 1e6, vout[mask], color=plots.ACCENT)
    ax2.set_xlabel("Time (µs)")
    ax2.set_ylabel("V(out) (V)")
    ax2.set_title("Steady-State Ripple")
    plots.info_box(
        ax2,
        f"Vout = {vavg:.3f} V\nripple = {ripple*1e3:.1f} mV pk-pk\nfsw = 100 kHz, D = 0.5",
        loc="lower right",
    )
    fig.suptitle("Buck Converter — 12 V → 6 V @ 1 A", fontweight="bold", y=1.02)
    save(fig, "06_buck_converter.png")


# ------------------------------------------------------- 07: Bridge rectifier
def bridge_rectifier() -> None:
    print("[07] Bridge rectifier")
    d = CIRCUITS / "07_bridge_rectifier"
    run_netlist(d / "bridge_rectifier.cir")
    t, (vpos, vsrc) = load_wrdata(d / "rect_tran.txt")

    vdc = metrics.dc_average(t, vpos, t_start=0.2)
    ripple = metrics.ripple_pp(t, vpos, t_start=0.2)
    ripple_theory = vdc / (100.0 * 2.0 * 60.0 * 1000e-6)
    record("07 Bridge rectifier", "Ripple pk-pk", ripple_theory, ripple, "V")

    mask = t >= 0.24
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(t[mask] * 1e3, vsrc[mask], color=plots.THEORY, lw=1.0, label="AC source (12 Vrms)")
    ax.plot(t[mask] * 1e3, vpos[mask], color=plots.PRIMARY, label="rectified + filtered")
    ax.axhline(vdc, ls="--", color=plots.ACCENT, lw=1.0)
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Voltage (V)")
    ax.set_title("Full-Wave Bridge Rectifier with 1000 µF Filter")
    plots.info_box(
        ax,
        f"Vdc = {vdc:.2f} V\nripple = {ripple:.2f} V pk-pk @ 120 Hz\n"
        f"I/(2fC) formula: {ripple_theory:.2f} V",
        loc="lower right",
    )
    ax.legend(loc="upper left")
    save(fig, "07_bridge_rectifier.png")


# ------------------------------------------------------------ 08: Monte Carlo
def monte_carlo(n_runs: int) -> None:
    print(f"[08] Monte Carlo tolerance analysis ({n_runs} runs)")
    cutoffs = run_monte_carlo(n_runs=n_runs, tolerance=0.05, seed=42)
    nominal = nominal_cutoff()
    record("08 Monte Carlo", "Mean cutoff", nominal, float(np.mean(cutoffs)), "Hz")

    rel = (cutoffs - nominal) / nominal
    yield_5pct = 100.0 * np.mean(np.abs(rel) <= 0.05)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(cutoffs / 1e3, bins=30, color=plots.PRIMARY, alpha=0.75, edgecolor="white")
    ax.axvline(nominal / 1e3, color=plots.INK, ls="--", lw=1.2)
    ax.text(nominal / 1e3, ax.get_ylim()[1] * 0.97, " nominal", fontsize=8.5, va="top")
    ax.axvline(np.mean(cutoffs) / 1e3, color=plots.ACCENT, lw=1.4)
    ax.set_xlabel("Measured f₋₃dB (kHz)")
    ax.set_ylabel("Samples")
    ax.set_title(f"Sallen-Key Cutoff Distribution — {n_runs} runs, 5% component tolerance")
    plots.info_box(
        ax,
        f"mean = {np.mean(cutoffs)/1e3:.3f} kHz\nσ = {100*np.std(rel):.2f}%\n"
        f"yield within ±5%: {yield_5pct:.1f}%",
        loc="upper left",
    )
    save(fig, "08_monte_carlo.png")


def write_results_md() -> None:
    out = ROOT / "docs" / "RESULTS.md"
    lines = [
        "# Measured vs. Theoretical Results",
        "",
        "Auto-generated by `scripts/run_all.py`. Every value below comes from an",
        "actual ngspice simulation compared against hand analysis.",
        "",
        "| Circuit | Quantity | Theory | Simulated | Error |",
        "|---------|----------|--------|-----------|-------|",
    ]
    for row in results:
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  wrote {out.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mc-runs", type=int, default=300)
    args = parser.parse_args()

    PLOTS.mkdir(parents=True, exist_ok=True)
    plots.apply_style()

    rc_lowpass()
    sallen_key()
    common_emitter()
    diff_pair()
    wien_bridge()
    buck_converter()
    bridge_rectifier()
    monte_carlo(args.mc_runs)
    write_results_md()
    print("\nAll simulations complete.")


if __name__ == "__main__":
    main()
