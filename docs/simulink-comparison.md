# bakeC vs MATLAB Simulink Embedded Coder

bakeC explores selected patterns also used by MATLAB Embedded Coder. The mappings below explain design inspiration; they do not imply feature equivalence, identical semantics or equivalent verification.

---

## Architecture mapping

Selected conceptual parallels:

| Simulink Embedded Coder | bakeC | Purpose |
|---|---|---|
| `.slx` / `.mdl` model | `models/*.yaml` | System definition (blocks, signals, parameters) |
| Target Language Compiler (`.tlc`) | `templates/*.j2` (Jinja2) | Code generation templates |
| System Target File (STF) | `platforms/*.yaml` | Target hardware config (types, compiler flags, constraints) |
| `rtwtypes.h` | `*_controller_types.h` | Platform-dependent type definitions (`real_T`, `int_T`, etc.) |
| Model data file | `*_controller_data.c` | Static parameter arrays and constants |
| Generated model `.c` / `.h` | `*_controller.c` / `.h` | Step/init/terminate functions |

---

## Type system

Both systems use `real_T` to decouple the model from hardware precision. The platform configuration selects single or double precision. Numerical behavior needs verification for each target.

| Platform | EC `real_T` | bakeC `real_T` |
|---|---|---|
| Desktop / simulation | `double` | `double` |
| ARM Cortex-M4 | `real32_T` / `float` | `float` |
| Infineon AURIX TC397 | `real32_T` / `float` | `float` |

The generated `*_controller_types.h` contains `typedef double real_T;` or `typedef float real_T;` based on the platform YAML, plus fixed-width integer types from `<stdint.h>`. Swap the platform file, get the right types. Nothing else changes.

---

## Block type mapping

| Simulink Block | bakeC Block Type | Notes |
|---|---|---|
| Lookup Table (1-D) | `lookup_table` | Linear interpolation, clamped extrapolation |
| PID Controller | `pid` | Proportional + Integral + Derivative with output saturation |
| MATLAB Function (basis) | `basis_function_sum` | B-spline basis function sum (order 0/1) |
| Constant + Gain | `offset` | Scalar coefficient times a named model state |

### Unrolling

bakeC selects unrolled or loop-based code at generation time. Actual performance depends on the compiler and target.

- **EC**: configurable via "Loop unrolling threshold" in code generation settings
- **bakeC**: N <= 8 unrolls, N > 8 generates a `for` loop (applies to `basis_function_sum` coefficients and `lookup_table` breakpoints)

The threshold is currently fixed at 8.

---

## Pipeline comparison

A comparison of broad development stages:

| Step | Embedded Coder | bakeC |
|---|---|---|
| 1. Define model | Simulink block diagram (`.slx`) | YAML model file |
| 2. Configure target | System Target File + hardware config | Platform YAML |
| 3. Parse model | RTW build → `.rtw` intermediate | `parser.py` → Python dict |
| 4. Validate | Model Advisor checks | `validator.py` (per-block rules) |
| 5. Generate code | TLC template expansion | Jinja2 template rendering (`engine.py`) |
| 6. Write output | EC file packaging | `writer.py` → `generated/{platform}/` |
| 7. Quality checks | Polyspace, Model Advisor | `checks/` suite (MISRA, safety, traceability, regression, API stability) |
| 8. Compile | Toolchain integration | CMake + platform toolchain |

---

## Traceability

EC generates `/* Block: '<Root>/PID'` comments linking code back to model blocks. bakeC does the same thing with `@trace` doc-comment tags pointing back to the model YAML path, plus a file banner with model path, platform path, generator version, and SHA-256 content hash.

Embedded hashes identify the source version. Behavioral equivalence requires additional verification.

---

## What bakeC does NOT implement

bakeC implements a focused personal code-generation pipeline. Its scope excludes:

- **Graphical modeling** — no block diagram editor; models are hand-written YAML
- **Stateflow** — no state machine / chart support
- **Continuous-time solvers** — discrete-time only (fixed sample rate)
- **Multi-rate / multi-tasking** — single-rate execution only
- **Simulink Bus / Variant** — no bus objects or variant subsystems
- **Hardware-in-the-loop (HIL)** — no PIL/SIL/HIL test harness generation
- **Signal routing** — no Mux/Demux/Bus Creator/Selector blocks
- **Solver configuration** — no ODE solvers (ode45, ode3, etc.)
- **Subsystem reuse / libraries** — no shared library or model reference support
- **Data dictionary** — parameters live in the model YAML, no external data dictionary
- **AUTOSAR / ASAM** — no AUTOSAR-compliant interface generation
- **Custom Storage Classes** — all data is statically allocated with a fixed layout

The project focuses on readable generated C and testing the supported patterns.
