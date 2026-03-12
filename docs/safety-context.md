# Safety Standards Context

bakeC generates code intended for safety-related embedded systems. The
design decisions and validation checks align with requirements from
several international safety standards.

## Applicable Standards

### IEC 61508 — Functional Safety of E/E/PE Systems
The foundational standard for safety-critical electronic systems.
bakeC addresses several IEC 61508 Part 3 (software) recommendations:
- **Static allocation** (Table B.1) — no dynamic memory, bounded stack.
- **Traceability** (Clause 7.4.4) — every generated function traces to
  its model source via `@trace` tags.
- **Coding standards** (Table B.1) — MISRA C:2012 subset enforcement.
- **Defensive programming** (Table B.1) — assertions, bounded loops,
  no recursion.

### IEC 62061 — Safety of Machinery
Sector-specific application of IEC 61508 for machinery control systems.
The lung ventilator controller modeled in bakeC falls under this scope.
Key requirements addressed:
- Deterministic execution timing (static allocation, no recursion).
- Separation of calibration data from algorithm code.

### ISO 13849-1 — Safety-Related Parts of Control Systems
Complements IEC 62061 with a simpler category-based approach. bakeC's
generated code supports Category 2-4 architectures by providing:
- Reproducible, verifiable code generation from declared models.
- Regression detection for unintended changes between versions.
- API stability checks to prevent breaking interface contracts.

### MISRA C:2012
The de facto C coding standard for safety-critical embedded systems.
bakeC enforces a subset of MISRA C:2012 rules through text-based
static analysis:
- **Rule 21.3** — No dynamic memory allocation (error)
- **Rule 17.2** — No recursion (error)
- **Rule 8.1** — Explicit return types (warning)
- **Rule 10.1** — No implicit narrowing conversions (warning)
- **Rule 15.7** — if/else-if chains terminated with else (warning)
- **Rule 21.6** — No stdio in production code (warning)

## Validation Pipeline

The `bakec validate` command enforces these safety properties on every
generated output:

| Check Category    | Checks | Scope               |
|-------------------|--------|---------------------|
| MISRA C:2012      | 10     | Per-file analysis   |
| Traceability      | 5      | Per-file analysis   |
| Safety patterns   | 6      | Per-file analysis   |
| Regression        | 9      | Baseline comparison |
| API stability     | 6      | Baseline comparison |

Running validation as part of the build pipeline (via `make validate`)
ensures that safety properties are continuously verified, not just at
release time.
