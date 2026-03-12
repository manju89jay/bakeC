# Architecture

## The Embedded Coder Pipeline

MATLAB Embedded Coder uses a 5-stage pipeline to turn Simulink models into production C:

1. **Simulink Model** — graphical block diagram with typed signals and parameters
2. **`.rtw` file** — Real-Time Workshop intermediate representation: a flat text dump of every block, signal, parameter, data type, and sample time in the model
3. **TLC templates** — Target Language Compiler files that walk the `.rtw` data and emit C code. Separated into system-level (top-level lifecycle) and block-level (per-algorithm) templates
4. **Generated C** — struct-based I/O, `init`/`step`/`terminate` lifecycle, static allocation, MISRA-compatible
5. **Build** — makefile or IDE project targeting a specific MCU toolchain

The key architectural insight is **separation of data extraction from code emission**. The `.rtw` file captures *what* the model computes; TLC templates decide *how* to express that in C for a given target. Changing the target (desktop vs. Cortex-M4) changes templates and compiler flags, not the model.

## This Project's Architecture

bakeC reproduces this pattern with modern tooling:

```
 YAML Model          Platform YAML
 (lung_mnarx.yaml)   (cortex_m4.yaml)
       │                    │
       ▼                    ▼
 ┌──────────┐        ┌───────────┐
 │  Parser  │        │  Parser   │
 └────┬─────┘        └─────┬─────┘
      │  Python dict (IR)   │
      ▼                     ▼
 ┌─────────────────────────────────┐
 │        Validator                │
 └──────────────┬──────────────────┘
                ▼
 ┌─────────────────────────────────┐
 │     CodegenEngine (Jinja2)      │
 │  ┌───────────────────────────┐  │
 │  │ controller.c.j2           │  │
 │  │ controller.h.j2           │  │
 │  │ controller_data.c.j2      │  │
 │  │ controller_types.h.j2     │  │
 │  │ blocks/basis_function.c.j2│  │
 │  │ blocks/pid.c.j2           │  │
 │  └───────────────────────────┘  │
 └──────────────┬──────────────────┘
                ▼
 ┌─────────────────────────────────┐
 │     Writer → generated/*.c/.h   │
 └──────────────┬──────────────────┘
                ▼
 ┌─────────────────────────────────┐
 │   CMake build (per platform)    │
 └─────────────────────────────────┘
```

The Python dict returned by the parser is the equivalent of the `.rtw` file — a normalized, validated representation of the model that templates consume without needing to re-parse YAML.

## TLC ↔ Jinja2 Mapping

| TLC Construct | Jinja2 Equivalent | Notes |
|---|---|---|
| `%assign var = value` | `{% set var = value %}` | Variable binding |
| `%foreach idx = count` | `{% for idx in range(count) %}` | Iteration |
| `%if condition` | `{% if condition %}` | Conditional emission |
| `%<variable>` | `{{ variable }}` | Value interpolation |
| `%openfile "out.c"` | `engine.py` output routing | Engine maps template → output filename |
| Block-level `.tlc` | `blocks/*.c.j2` | Per-block-type template fragments |
| System-level `.tlc` | `controller.c.j2` | Top-level lifecycle template |
| `system_target_file` | `platforms/*.yaml` | Target hardware configuration |
| `%include "block.tlc"` | `{% include "blocks/block.c.j2" %}` | Template composition |

## Why This Architecture Scales

The engine is model-agnostic. Extension happens at three points without modifying generator code:

**New model** — add a YAML file under `models/`. The parser validates it against the same schema. The engine feeds it to the same templates. If the model uses only existing block types, zero code changes are needed.

**New platform** — add a YAML file under `platforms/` and a CMake toolchain file under `build/`. The platform config controls type mappings (`real_T` → `float` vs `double`), literal suffixes, compiler flags, and constraint toggles (assertions, printf). Templates already parameterize on these.

**New block type** — add a template under `templates/blocks/`, a corresponding `{% elif %}` in `controller.c.j2`, and validation logic in `validator.py`. The engine's rendering loop handles it automatically.

## Automotive Mapping

| bakeC Concept | AUTOSAR Equivalent |
|---|---|
| Model YAML | ARXML application description |
| Platform config | ECU extract / target configuration |
| Generated `_controller.c` | Software Component (SWC) implementation |
| `_ExtU_T` / `_ExtY_T` structs | Rte port interfaces (sender-receiver) |
| `_initialize` / `_step` / `_terminate` | Runnable entities with periodic/init triggers |
| `_controller_data.c` | ASAP2/A2L calibration parameter file |
| Quality rules (MISRA subset) | MISRA C:2012 compliance (ISO 26262 Part 6) |
| `@trace` tags + sha256 hashes | Requirements traceability (DOORS → code) |

## Safety Context

bakeC targets IEC 61508 (functional safety for E/E/PE systems) and its domain-specific derivatives: IEC 62304 for medical device software and ISO 26262 for automotive. These standards require that code generation tools either be qualified (IEC 61508 T3) or that their output be independently verified.

The traceability infrastructure — `@trace` tags linking every generated function back to its YAML source path, sha256 content hashes in file banners, and the quality checker — provides the evidence chain that safety assessors require. Each generated file can be independently verified against its model source.

Generated code follows MISRA C:2012 guidelines: no dynamic memory allocation, no recursion, C99-compliant declarations, `static` internal linkage for helper functions, and explicit type widths via `stdint.h` typedefs. The `quality/check_generated.py` script enforces a subset of these rules automatically.

The separation of calibration data (`_data.c`) from algorithm code (`_controller.c`) supports the common automotive workflow where parameters are tuned on-target without recompiling the algorithm — analogous to ASAP2/XCP calibration in production ECU software.
