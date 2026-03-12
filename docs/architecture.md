# Architecture

bakeC mirrors the MATLAB Embedded Coder pipeline — YAML models in, validated
embedded C out — with a two-pipeline architecture: **Generate** (model to code)
and **Validate** (code to evidence).

## System Context (C4 Level 1)

```
  ┌──────────────┐     ┌──────────────┐
  │  Model YAML  │     │ Platform YAML│
  │  (lung_mnarx │     │ (cortex_m4   │
  │   pid_ctrl)  │     │  desktop)    │
  └──────┬───────┘     └──────┬───────┘
         │                    │
         ▼                    ▼
  ┌─────────────────────────────────────┐
  │             bakeC CLI               │
  │                                     │
  │   generate        validate          │
  │   ────────        ────────          │
  │   YAML → C        C → report       │
  └──────────┬─────────────┬────────────┘
             │             │
             ▼             ▼
  ┌──────────────┐  ┌──────────────────┐
  │ Generated C  │  │ Validation Report│
  │ (.c, .h)     │  │ (MISRA, trace,   │
  │              │  │  safety, regress) │
  └──────────────┘  └──────────────────┘
```

## Container View (C4 Level 2)

### Generate Pipeline

```
  YAML Model ──► Parser ──► Python dict (IR) ──► Validator
                                                     │
  Platform YAML ──► Parser ──► Platform dict ────────┤
                                                     ▼
                                              CodegenEngine
                                              (Jinja2 templates)
                                                     │
                                                     ▼
                                                  Writer
                                                     │
                                                     ▼
                                           generated/*.c, *.h
```

The Parser converts YAML to Python dicts (equivalent of MATLAB's `.rtw`
intermediate representation). The Validator checks semantic constraints
(coefficient counts, knot ordering, sample rates). The CodegenEngine feeds
the validated IR into Jinja2 templates — one template per output file, with
block-level fragments in `templates/blocks/`. The Writer emits files to disk.

**Key files:**
[parser.py](../src/bakec/parser.py),
[validator.py](../src/bakec/validator.py),
[engine.py](../src/bakec/engine.py),
[writer.py](../src/bakec/writer.py)

### Validate Pipeline

```
  generated/*.c, *.h ──► File Reader ──► Per-file checks:
                              │            ├─ MISRA C:2012 (10 rules)
                              │            ├─ Traceability (5 checks)
                              │            └─ Safety patterns (6 checks)
                              │
                              ├──────────► Baseline comparison (if provided):
                              │            ├─ Regression (9 checks)
                              │            └─ API stability (6 checks)
                              │
                              ▼
                         CheckReport
                         (errors, warnings, info)
```

The validate pipeline operates on generated C files, not on YAML models. Each
check module is a pure function: `(content, filename) -> list[CheckResult]`.
Regression and API stability checks compare two directories (target vs
baseline) to detect unintended structural changes.

**Key files:**
[runner.py](../src/bakec/checks/runner.py),
[misra.py](../src/bakec/checks/misra.py),
[traceability.py](../src/bakec/checks/traceability.py),
[safety.py](../src/bakec/checks/safety.py),
[regression.py](../src/bakec/checks/regression.py),
[api_stability.py](../src/bakec/checks/api_stability.py)

## Extension Points

**New model** — add a YAML file under `models/`. If it uses existing block
types, zero code changes are needed.

**New platform** — add a YAML file under `platforms/` and a CMake toolchain
file. Platform config controls type mappings, literal suffixes, compiler flags.

**New block type** — add a template in `templates/blocks/`, extend the
`{% elif %}` dispatch in `controller.c.j2`, and add validation logic.

**New check** — add a module in `src/bakec/checks/`, register it in
`runner.py`'s orchestrator, and add a section to `rules.yaml`.

## Design Decisions

- [ADR-001: Template Engine](decisions/001-template-engine.md) — Jinja2 over string concatenation or Mako
- [ADR-002: YAML Models](decisions/002-yaml-models.md) — YAML over JSON or TOML for model definitions
- [ADR-003: Static Allocation](decisions/003-static-allocation.md) — no malloc/free in generated code
- [ADR-004: Type Abstraction](decisions/004-type-abstraction.md) — portable typedefs per platform
- [ADR-005: Basis Function Unrolling](decisions/005-basis-function-unrolling.md) — N<=8 unrolled, N>8 loop
- [ADR-006: Traceability](decisions/006-traceability.md) — provenance banners and @trace tags

## Related Documentation

- [TLC to Jinja2 Mapping](tlc-mapping.md) — detailed construct-level mapping with examples
- [Automotive Mapping](automotive-mapping.md) — AUTOSAR concept equivalences
- [Safety Context](safety-context.md) — IEC 61508, IEC 62061, ISO 13849-1, MISRA C:2012
