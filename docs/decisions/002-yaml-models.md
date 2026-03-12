# ADR-002: YAML for Model Definitions

## Status
Accepted

## Context
MATLAB Embedded Coder represents models as `.slx` (binary Simulink) files
compiled to `.rtw` (structured text) before code generation. We need a
human-readable, version-controllable format that captures the same
information: blocks, parameters, sample rates, and I/O declarations.

Alternatives considered:
- **JSON** — no comments, verbose for nested structures.
- **TOML** — limited nesting depth, awkward for arrays of tables.
- **YAML** — supports comments, compact nested structures, and
  human-readable lists. Widely used for configuration in embedded
  toolchains (e.g., PlatformIO, Zephyr).

## Decision
Use YAML for both model definitions (`models/*.yaml`) and platform
configurations (`platforms/*.yaml`). The parser emits a Python dict
intermediate representation consumed by the engine, equivalent to the
`.rtw` → TLC data flow in MATLAB.

## Consequences
- Models are diffable and reviewable in pull requests.
- YAML's implicit typing can cause subtle bugs (e.g., `1.0e-10` parsed
  as string in some loaders) — the parser must use `yaml.safe_load` and
  validate types explicitly.
- Schema validation is performed in Python, not by the YAML spec itself.
