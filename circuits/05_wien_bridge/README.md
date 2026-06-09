# 05 — Wien-Bridge Oscillator

```
       ┌──[ RS1 10k ]──[ CS1 15.9n ]──┐
       │                              ├ p ──┤+\
       │            [ RP1 10k ]──┬────┘     │  >──┬── out
       │            [ CP1 15.9n ]┴─ GND   ┌─┤−/   │
       │                                  n│      │
       │               GND ─[ R4 10k ]────┼──[ R3 22k ]─┐
       │                                  └─────────────┤
       └────────────────────────────────────────────────┴── out
```

## Design

The Wien network (series RC feeding parallel RC) has zero phase shift and a
transfer ratio of exactly **1/3** at:

$$f_{osc} = \frac{1}{2\pi RC} = 1001.0 \text{ Hz}$$

Barkhausen criterion: the amplifier must supply gain ≥ 3. The non-inverting
gain is 1 + R3/R4 = **3.2**, guaranteeing startup; amplitude is stabilized by
the amplifier's soft tanh saturation (±11 V rails), which compresses the loop
gain back to exactly 3 at the limit cycle.

Two simulation-craft details worth noting:

- `tran ... uic` with `.ic v(p)=10m` — the zero state is an (unstable)
  equilibrium, so the simulation seeds a 10 mV kick instead of waiting for
  numerical noise.
- The behavioral amplifier output gets a 100 Ω / 100 pF RC (τ = 10 ns) so the
  transient solver has a state variable to integrate through the initial step.

## Verified results

| Quantity | Theory | ngspice | Error |
|----------|--------|---------|-------|
| f_osc | 1001.0 Hz | 984.2 Hz | −1.7% (soft-clipping pulls fosc slightly) |
| Amplitude | ≈ rail (11 V) | 10.9 V | ✓ |
| Sustained oscillation | — | amplitude stable over 80 ms | ✓ |

![Plots](../../docs/plots/05_wien_bridge.png)
