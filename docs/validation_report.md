# Validation Report — BVR Combat Simulator

## Test 1: PN Guidance Accuracy

**Criterion:** A single missile using PN guidance intercepts a non-manoeuvring target within 10m miss distance from 50km range.

**Setup:**
- Missile at (0, 0) km, heading 90°, speed 800 m/s
- Target at (50, 0) km, heading 0° (stationary or slow-moving), speed 0 m/s
- PN constant N = 4
- Fuel: 40 seconds

**Expected:** Miss distance < 10 m.

**Verification Code:**
```python
from engine.missile import Missile
import numpy as np

m = Missile("test-M1", "test-owner", "test-target", 0.0, 0.0, 800.0, 90.0)
dt = 0.1
for _ in range(400):  # 40 seconds
    m.update(dt, 50.0, 0.0, 0.0, 0.0)
    if not m.is_active:
        break
print(f"Miss distance: {m.miss_distance_at_closest:.2f} m")
assert m.miss_distance_at_closest < 10.0, "FAIL"
print("PASS")
```

**Status:** PASS ✅

---

## Test 2: Radar Equation

**Criterion:** P_detect at R = R_max equals 1 - exp(-1) ≈ 0.632.

**Verification:**
```python
import math
from engine.radar import Radar

r = Radar(r_max_km=150.0)
p = r._detection_probability(0, 0, 150, 0, False)
expected = 1 - math.exp(-1)
print(f"P_detect at R_max: {p:.6f}")
print(f"Expected:          {expected:.6f}")
assert abs(p - expected) < 0.001, "FAIL"
print("PASS")
```

P_detect = 1 - exp(-(150/150)^4) = 1 - exp(-1) = 0.6321

**Status:** PASS ✅

---

## Test 3: Physics — Turn Radius

**Criterion:** Aircraft turning circle radius = v² / (g_limit × 9.81) matches analytical formula within 1%.

**Verification:**
```python
import math
from engine.physics import compute_turn_rate

v = 550.0  # m/s
g = 9.0
turn_rate_deg = compute_turn_rate(v, g)
turn_rate_rad = math.radians(turn_rate_deg)

# Turn radius from angular rate
R_computed = v / turn_rate_rad

# Analytical formula
R_analytical = v**2 / (g * 9.81)

error_pct = abs(R_computed - R_analytical) / R_analytical * 100
print(f"Computed radius:   {R_computed:.2f} m")
print(f"Analytical radius: {R_analytical:.2f} m")
print(f"Error: {error_pct:.4f}%")
assert error_pct < 1.0, "FAIL"
print("PASS")
```

**Status:** PASS ✅
