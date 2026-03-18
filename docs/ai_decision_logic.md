# AI Decision Logic Documentation

## Overview

Each aircraft agent runs a 5-step decision cycle every **2 simulated seconds**.
Blue and Red agents use identical logic structures but with asymmetric parameters.

## Decision Cycle

### Step 1 — Threat Assessment

For each detected enemy:
```
threat_score = (1 / range_km) × enemy_missile_count × tracking_factor
```
where `tracking_factor = 1.0` if enemy radar is tracking this aircraft, `0.3` otherwise.

Enemies sorted by threat score descending. Highest = primary threat.

### Step 2 — Missile Defence Check

**Trigger:** An enemy missile is within 40 km AND in terminal phase.
**Actions:**
1. **Notch:** Turn 90° perpendicular to missile line-of-sight
2. **Chaff:** If missile within 15 km, dispense chaff (35% chance to break lock)

> ⚠ This step **overrides** all other decisions. Survival takes priority.

### Step 3 — Engagement Decision

Fire a missile if ALL conditions met:
- Primary threat within missile range (100 km Blue / 80 km Red)
- Estimated P_kill > 0.55
- Aircraft has missiles remaining
- No friendly missile already targeting this enemy (deconfliction)

Estimated PK: `0.85 × (1 - (R/R_max)²) × tracking_quality`

### Step 4 — Positioning

Utility-based selection among three manoeuvres:

| Manoeuvre | Utility Formula | Action |
|-----------|----------------|--------|
| Close to optimal range | `\|optimal - current\| / optimal` | Fly toward/away from threat |
| Maintain energy | `1 - (velocity / max_velocity)` | Accelerate to energy floor |
| Support wingman | Urgency × distance factor | Move toward threatened wingman |

Highest utility manoeuvre selected.

### Step 5 — Formation Check (Blue Only)

Blue aircraft fly in pairs (lead + wingman). Maintain 15 km lateral separation.
If separation exceeds 30 km → wingman manoeuvres to rejoin.

Red force does **not** use formation logic (simulating less disciplined opponent).

## Parameter Comparison

| Parameter | Blue | Red |
|-----------|------|-----|
| Radar R_max | 150 km | 120 km |
| Missile range | 100 km | 80 km |
| Chaff success | 35% | 30% |
| Formation | Pair-based | None |
| Max speed | 600 m/s | 600 m/s |
| Max G | 9 | 9 |
| Missiles | 4 | 4 |
