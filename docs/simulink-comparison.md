# bakeC vs MATLAB Simulink Embedded Coder

If you've used Embedded Coder, every concept in bakeC will look familiar. Same architecture, same separation of concerns, same output structure. The difference is that bakeC's entire pipeline fits in your head — and in a single git repo.

## Architecture Mapping

| Simulink Embedded Coder | bakeC | Purpose |
|---|---|---|
| `.slx` / `.mdl` model | `models/*.yaml` | System definition (blocks, signals, parameters) |
| Target Language Compiler (`.tlc`) | `templates/*.j2` (Jinja2) | Code generation templates |
| System Target File (STF) | `platforms/*.yaml` | Target hardware config (types, compiler flags, constraints) |
| `rtwtypes.h` | `*_controller_types.h` | Platform-dependent type definitions (`real_T`, `int_T`, etc.) |
| Model data file | `*_controller_data.c` | Static parameter arrays and constants |
| Generated model `.c` / `.h` | `*_controller.c` / `.h` | Step/init/terminate functions |

## Type System

Both systems use `real_T` to decouple the model from hardware precision. Same idea, same typedef names, same reason: write the algorithm once, deploy it on single- or double-precision targets without touching a line of model code.

| Platform | EC `real_T` | bakeC `real_T` |
|---|---|---|
| Desktop / simulation | `double` | `double` |
| ARM Cortex-M4 | `real32_T` / `float` | `float` |
| Infineon AURIX TC397 | `real32_T` / `float` | `float` |

The generated `*_controller_types.h` contains `typedef double real_T;` or `typedef float real_T;` based on the platform YAML, plus fixed-width integer types from `<stdint.h>`. Swap the platform file, get the right types. Nothing else changes.

## Block Type Mapping

| Simulink Block | bakeC Block Type | Notes |
|---|---|---|
| Lookup Table (1-D) | `lookup_table` | Linear interpolation, clamped extrapolation |
| PID Controller | `pid` | Proportional + Integral + Derivative with output saturation |
| MATLAB Function (basis) | `basis_function_sum` | B-spline basis function sum (order 0/1) |
| Constant + Gain | `offset` | Simple coefficient * input + offset |

### Unrolling

Both EC and bakeC decide at generation time whether to unroll or loop. Small N means straight-line code with zero branch overhead. Large N means a compact loop that doesn't blow up the instruction cache.

- **EC**: configurable via "Loop unrolling threshold" in code generation settings
- **bakeC**: N <= 8 unrolls, N > 8 generates a `for` loop (applies to `basis_function_sum` coefficients and `lookup_table` breakpoints)

The threshold is hardcoded at 8. Opinions were had.

## Pipeline Comparison

Eight steps. Same order in both systems. Different tools, same job.

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

## Traceability

EC generates `/* Block: '<Root>/PID'` comments linking code back to model blocks. bakeC does the same thing with `@trace` doc-comment tags pointing back to the model YAML path, plus a file banner with model path, platform path, generator version, and SHA-256 content hash. An auditor can verify that generated code matches a specific model version by checking the embedded hashes. No proprietary viewer required.

## What bakeC Does NOT Implement

bakeC reimplements the core pipeline, not the entire MathWorks ecosystem. These are deliberate scope boundaries, not TODO items:

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

Twelve things Embedded Coder does that bakeC doesn't. On the other hand, bakeC has a readable codebase, a `git log`, and no license dongle.
