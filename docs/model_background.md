# Model Background

## The mNARX Lung Mechanics Model

The mNARX (modified Non-Linear Autoregressive) lung mechanics model predicts airway pressure from flow and volume measurements in mechanically ventilated ARDS patients. It was published by Jayaramaiah, M., Laufer, B., Kretschmer, J. and Möller, K. (2016), "A New Lung Mechanics Model and Its Evaluation with Clinical Data", *Journal of Biomedical Science and Engineering*, 9, 107–115 (DOI: 10.4236/jbise.2016.910B014).

The core equation (Eq. 5 from the paper) decomposes airway pressure into three terms:

```
Paw(t) = Σ ai·Φi,d(Paw)·V(t) + Σ bj·Πj,d(Paw)·V̇(t) + c·P0(t)
          ├── elastance ──┤     ├── resistance ──┤     ├ offset ┤
```

- **Elastance term**: M=5 first-order B-spline basis functions Φi,1(Paw) weighted by coefficients ai, multiplied by volume V(t). Captures pressure-dependent lung stiffness.
- **Resistance term**: L=20 first-order B-spline basis functions Πj,1(Paw) weighted by coefficients bj, multiplied by flow V̇(t). Captures pressure-dependent airway resistance.
- **Offset term**: PEEP offset pressure P0(t) scaled by coefficient c.

The basis functions are piecewise linear (order d=1), defined over evenly spaced knot vectors. Each basis function is nonzero only over two adjacent knot intervals, giving the model local sensitivity — a change in one pressure region does not affect the fit elsewhere.

The key innovation over standard NARX models is the "modified" structure: by using pressure-dependent basis functions for both elastance and resistance, the mNARX model achieves equivalent accuracy with L=20 resistance basis functions versus L=350 in the original NARX formulation, while exhibiting better noise robustness. The model was validated on 25 ARDS patient datasets collected across 8 German hospitals.

## Why This Model for Code Generation

The mNARX model was chosen as bakeC's primary example because it exercises the code generator in ways that toy examples cannot:

- **Nonlinear computation** — B-spline basis function evaluation with knot lookups, not simple multiply-accumulate.
- **Multiple block types** — Two `basis_function_sum` blocks (elastance, resistance) plus an `offset` block, testing the template system's ability to compose heterogeneous computations.
- **Unroll vs. loop decision** — The elastance block (M=5, ≤8) is unrolled; the resistance block (L=20, >8) uses a for loop. Both paths must generate correct code.
- **Calibration data separation** — Patient-specific coefficients and knot vectors live in `_data.c`, demonstrating the same data/algorithm separation used in production ECU calibration workflows.
- **Autoregressive feedback** — The output Paw feeds back as an input to the basis functions at the next timestep, requiring state management across step calls.
- **Published and validated** — A peer-reviewed, clinically validated model establishes that the toolchain handles real engineering problems, not contrived tests.

The basis function sum pattern is architecturally identical to the lookup tables and piecewise interpolation found in engine management, transmission control, and other industrial embedded systems — making the generated code structure directly transferable.
