# ADR-005: Basis Function Loop Unrolling Strategy

## Status
Accepted

## Context
B-spline basis function sums are the core computation in the mNARX lung
model. Each term evaluates a basis function and multiplies by a
coefficient and input signal. The number of terms (N) varies: the
elastance block has N=5, the resistance block has N=20.

Full unrolling produces straight-line code with no branch overhead and
better instruction cache behavior on small MCUs. Loop-based code is
smaller and easier to read for larger N.

## Decision
Basis function sums with N <= 8 are fully unrolled; sums with N > 8 use
a `for` loop. The threshold is applied at generation time by the engine
(`engine.py`, `unroll` flag in block context).

## Consequences
- The elastance block (N=5) generates 5 explicit addition statements.
- The resistance block (N=20) generates a compact `for` loop.
- The threshold is hardcoded at 8. If a different threshold is needed
  per platform (e.g., always unroll on Cortex-M4 for timing
  determinism), the platform YAML would need an `unroll_threshold` field.
