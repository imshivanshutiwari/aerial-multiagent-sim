# Physics Model Documentation

## Aircraft Dynamics

Each aircraft is a point mass with four state variables:
- **Position** (x, y) in km
- **Velocity magnitude** in m/s
- **Heading** in degrees (0 = +x, 90 = +y)

### Turn Rate
Turn rate limited by maximum G-load:
```
max_turn_rate = (G_limit × 9.81) / velocity_ms  [rad/s]
```
Blue aircraft: max speed 600 m/s, max G 9, combat radius 1000 km.
Red aircraft: identical capability.

### Position Update
```
x_new = x + v × cos(heading) × dt / 1000
y_new = y + v × sin(heading) × dt / 1000
```

## Radar Model

Swerling Type 1 detection probability:
```
P_detect(R) = 1 - exp(-(R_max_eff / R)^4)
```

When target is jamming: `R_max_eff = R_max × 0.6` (40% reduction).

- Blue radar R_max = 150 km
- Red radar R_max = 120 km
- Baseline RCS = 3.0 m²

## Missile Model

Active radar homing missile (AMRAAM / Astra Mk2 class).

### Phases
1. **Boost** (0–3s): acceleration 30 m/s², fly toward predicted intercept
2. **Midcourse** (3–30s): inertial guidance to updated intercept point
3. **Terminal** (>30s): active seeker, proportional navigation

### PN Guidance Law
```
a_commanded = N × V_closing × dθ_LOS/dt
```
where N = 4 (navigation constant).

### Specifications
- Max speed: 1200 m/s
- Range: ~100 km
- Fuel: 40 seconds
- Each aircraft carries 4 missiles

## Kill Probability

```
miss ≤ 30m:     P_kill = 0.85
30m < miss ≤ 100m: P_kill = 0.85 × exp(-(miss - 30) / 20)
miss > 100m:    P_kill = 0.0
```

## Electronic Countermeasures

### Jammer
- Reduces enemy radar R_max by 40%
- Energy budget: 60 seconds continuous

### Chaff
- 6 cartridges per aircraft
- Success probability: 0.35 (Blue) / 0.30 (Red)
- Breaks missile radar lock → missile flies ballistic
