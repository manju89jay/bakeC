# Model Background

## The mNARX Lung Mechanics Model

The mNARX (modified Non-Linear Autoregressive) lung mechanics model predicts
airway pressure from flow and volume measurements in mechanically ventilated
ARDS patients. It was published by Jayaramaiah, M., Laufer, B., Kretschmer, J.
and Moller, K. (2016), "A New Lung Mechanics Model and Its Evaluation with
Clinical Data", *Journal of Biomedical Science and Engineering*, 9, 107-115
(DOI: 10.4236/jbise.2016.910B014).

### Core Equation

Equation 5 from the paper decomposes airway pressure into three terms:

```
Paw(t) = Sum_i ai * Phi_i,d(Paw) * V(t)     elastance
       + Sum_j bj * Pi_j,d(Paw)  * Vdot(t)   resistance
       + c * P0(t)                             offset
```

- **Elastance term** (M=5): First-order B-spline basis functions Phi_i,1(Paw)
  weighted by coefficients ai, multiplied by volume V(t). Captures
  pressure-dependent lung stiffness.
- **Resistance term** (L=20): First-order B-spline basis functions Pi_j,1(Paw)
  weighted by coefficients bj, multiplied by flow Vdot(t). Captures
  pressure-dependent airway resistance.
- **Offset term**: PEEP offset pressure P0(t) scaled by coefficient c.

### Basis Functions

The basis functions are piecewise linear (order d=1), defined over evenly
spaced knot vectors. Each basis function is nonzero over at most two adjacent
knot intervals, giving the model local sensitivity -- a change in one pressure
region does not affect the fit elsewhere.

### Key Innovation

The "modified" structure uses pressure-dependent basis functions for both
elastance and resistance. This achieves equivalent accuracy with L=20
resistance basis functions versus L=350 in the original NARX formulation,
with better noise robustness. The model was validated on 25 ARDS patient
datasets from 8 German hospitals.

## Why This Model for Code Generation

The mNARX model exercises the code generator in ways that toy examples cannot:

- **Nonlinear computation** -- B-spline evaluation with knot lookups, not
  simple multiply-accumulate.
- **Multiple block types** -- two `basis_function_sum` blocks plus an `offset`
  block, testing heterogeneous composition.
- **Unroll vs. loop** -- elastance (M=5, <=8) is unrolled; resistance (L=20,
  >8) uses a for loop. Both paths must generate correct code.
- **Data separation** -- patient-specific coefficients live in `_data.c`,
  demonstrating calibration data independence.
- **Autoregressive feedback** -- Paw feeds back as input to basis functions at
  the next timestep, requiring state management across `_step()` calls.
- **Published and validated** -- a peer-reviewed, clinically validated model
  demonstrates real engineering problems, not contrived tests.

The basis function sum pattern is architecturally identical to lookup tables
and piecewise interpolation in engine management, transmission control, and
other industrial embedded systems.
