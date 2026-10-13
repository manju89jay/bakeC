# ADR-004: Platform-Specific Type Abstraction

## Status
Accepted

## Context
Embedded targets vary in floating-point capability. A Cortex-M4F has
single-precision FPU; a desktop simulation uses double precision. Raw C
types (`float`, `double`, `int`) are non-portable and violate MISRA-10.1
when used inconsistently. MATLAB Embedded Coder solves this with
`real_T`, `int32_T`, etc., defined per target in `rtwtypes.h`.

## Decision
Generated code uses portable typedefs (`real_T`, `int32_T`, `uint32_T`,
etc.) defined in a per-target `_types.h` file. The platform YAML
specifies the underlying type (e.g., `real_type: float` for Cortex-M4,
`real_type: double` for desktop). Model values use the `c_real` template filter for round-trip literal precision,
with suffixes derived from `real_T`. Non-finite values, overflow and rounding
to zero are rejected. Fixed constants also carry the target suffix.

## Consequences
- Models can generate single- and double-precision code; each configuration
  requires numerical tests. Typedefs alone do not establish equivalent behavior.
- SAFE-005 enforces that no raw `int`/`float`/`double` appears in
  generated declarations.
- Adding a new target only requires a new platform YAML — no template
  changes needed.
