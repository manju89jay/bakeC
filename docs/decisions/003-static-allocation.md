# ADR-003: Static Memory Allocation Only

## Status
Accepted

## Context
Embedded safety-critical systems (IEC 61508 SIL 2+, ISO 26262 ASIL B+)
prohibit or strongly discourage dynamic memory allocation. `malloc`,
`calloc`, and `free` introduce non-deterministic timing, fragmentation,
and failure modes that are difficult to bound analytically. MATLAB
Embedded Coder enforces static allocation by default.

## Decision
All generated code uses static allocation exclusively. No `malloc`,
`calloc`, `realloc`, or `free` calls appear in any generated output.
Coefficient arrays and I/O structs are declared as file-scope or extern
variables. This is enforced by both MISRA-21.3 and SAFE-001 checks in
the validation pipeline.

## Consequences
- Maximum memory usage is known at compile time and can be verified
  against target constraints.
- Adding variable-size data structures (e.g., runtime-configurable
  coefficient counts) would require a design change — currently all
  sizes are fixed at generation time from the YAML model.
- Stack depth is bounded since recursion is also prohibited (MISRA-17.2).
