# 06 — Buck Converter (Open-Loop, Non-Synchronous)

```
 12V ──[ S1 ]──┬ sw ──[ L1 100µ ]──┬── out
        PWM    │                   ├──[ ESR 50m ]──[ C1 100µ ]── GND
      100kHz  [D1]                 │
       D=0.5   │                 [ RL 6Ω ]  (1 A load)
              GND                  │
                                  GND
```

## Design

| Quantity | Formula | Value |
|----------|---------|-------|
| Ideal output | D·V_in | 6.0 V |
| Inductor ripple | ΔI_L = (V_in−V_out)·D/(f_sw·L) | 0.3 A pk-pk |
| CCM check | I_L(avg) = 1 A ≫ ΔI_L/2 | ✓ continuous conduction |
| Output ripple | ΔI_L·ESR + ΔI_L/(8·f_sw·C) | ≈ 19 mV + switching artifacts |
| LC corner | 1/(2π√LC) | 1.59 kHz (visible as startup ringing) |

Being non-synchronous, the freewheeling diode conducts for (1−D) of each
period, costing roughly (1−D)·V_f ≈ 0.36 V of output — the measured 5.74 V
is the textbook value, not a bug.

## Verified results

| Quantity | Theory | ngspice | Notes |
|----------|--------|---------|-------|
| V_out | 6.0 V ideal | 5.736 V | diode drop accounted |
| Ripple | ~tens of mV | 38.9 mV pk-pk | < 0.7% of V_out |
| Switch node | 0 ↔ 12 V | full swing | diode clamps low side |

![Plots](../../docs/plots/06_buck_converter.png)
