# bakeC

![CI](https://github.com/manju89jay/bakeC/actions/workflows/ci.yml/badge.svg)

A study of how MATLAB Embedded Coder's code generation architecture translates
to modern open-source tooling -- YAML models, Jinja2 templates, and a Python
orchestration layer that generates production-quality embedded C with
traceability, MISRA compliance checking, and multi-platform support.

## What It Does

bakeC takes a YAML model definition and a platform configuration, and produces
four C files per model: public API header, algorithm implementation, calibration
data, and platform-specific type definitions. It then validates the generated
output against 36 automated checks spanning MISRA C:2012, traceability,
embedded safety patterns, regression detection, and API stability.

```
$ python -m bakec.cli validate --target generated/desktop/

bakeC v0.1.0

Target:    generated/desktop/

Running checks...

  OK -- All checks passed
```

## Prerequisites

- Python 3.10+

For compiling and testing the generated C code (optional):
- Linux/macOS: GCC and CMake (pre-installed on most systems)
- Windows: [MSYS2](https://www.msys2.org/) with MinGW-w64 GCC (`pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake`)

## Quick Start

```bash
git clone https://github.com/manju89jay/bakeC.git
cd bakeC
pip install -e ".[dev]"    # install bakec + dev dependencies (pytest, coverage)
make all                    # generate → compile → test → validate
```

`make all` runs the full pipeline: generates C code for all models and platforms,
compiles the desktop target with GCC, runs 113 Python tests + 2 C test executables,
and validates the output against 36 automated checks. If you only have Python
installed (no GCC/CMake), the individual commands still work:

```bash
# Generate code for one model + platform
python -m bakec.cli generate \
  --model models/lung_mnarx.yaml \
  --platform platforms/desktop.yaml \
  --output generated/desktop/

# Validate generated output (no compiler needed)
python -m bakec.cli validate --target generated/desktop/

# Run Python tests
python -m pytest tests/ -v
```

## Architecture

bakeC reproduces the MATLAB Embedded Coder pipeline with two command paths:

**Generate:** YAML model + platform -> Parser -> Validator -> Jinja2 engine -> C files
**Validate:** C files [+ baseline] -> MISRA + traceability + safety + regression checks -> report

```
src/bakec/
  parser.py          YAML -> Python dict (equivalent of .rtw)
  validator.py       Semantic checks on model IR
  engine.py          Jinja2 template rendering
  writer.py          File output with metadata
  cli.py             CLI with generate and validate subcommands
  checks/
    runner.py        Check orchestrator (CheckResult, CheckReport)
    misra.py         10 MISRA C:2012 rules
    traceability.py  5 provenance/trace checks
    safety.py        6 embedded safety patterns
    regression.py    9 structural comparison checks
    api_stability.py 6 API contract checks
    rules.yaml       Check configuration
```

## Models

- **mNARX Lung** (`models/lung_mnarx.yaml`) -- Modified nonlinear autoregressive
  lung mechanics model with pressure-dependent B-spline basis functions.
  Based on [Jayaramaiah et al. (2016)](https://www.scirp.org/journal/paperinformation?paperid=70763),
  developed during my master thesis. See [model background](docs/model_background.md).
- **PID Controller** (`models/pid_controller.yaml`) -- PID pressure controller
  for hydraulic valve systems.

## Platforms

- **Desktop** (`platforms/desktop.yaml`) -- GCC, `double` precision, assertions, `-O2`
- **ARM Cortex-M4** (`platforms/cortex_m4.yaml`) -- `arm-none-eabi-gcc`, `float` precision, `-Os`
- **AURIX TC397** (`platforms/aurix_tc397.yaml`) -- `tricore-elf-gcc`, `float` precision,
  SIL 2 / PLd safety constraints, EtherCAT fieldbus, `-Os`

## Generated Output

Each model + platform produces four files:

| File | Purpose |
|---|---|
| `{name}_controller.h` | Public API: I/O structs, lifecycle prototypes |
| `{name}_controller.c` | Algorithm: init/step/terminate |
| `{name}_controller_data.c` | Calibration data (independently replaceable) |
| `{name}_controller_types.h` | Platform-specific typedefs |

## Validation Checks

| Category | Count | Scope |
|---|---|---|
| MISRA C:2012 | 10 | Per-file static analysis |
| Traceability | 5 | Provenance, @trace tags, hashes |
| Safety | 6 | Static allocation, bounded loops, typed vars |
| Regression | 9 | Baseline structural comparison |
| API stability | 6 | Header contract verification |

## Documentation

- [Architecture](docs/architecture.md) -- system design with C4 diagrams
- [TLC Mapping](docs/tlc-mapping.md) -- MATLAB TLC to Jinja2 equivalences
- [Automotive Mapping](docs/automotive-mapping.md) -- AUTOSAR concept parallels
- [Safety Context](docs/safety-context.md) -- IEC 61508, ISO 13849-1, MISRA
- [Model Background](docs/model_background.md) -- mNARX lung mechanics
- [Architecture Decision Records](docs/decisions/) -- 6 ADRs
- [Adding a Model](docs/adding-a-model.md) -- step-by-step guide

## Development

Individual Makefile targets:

| Target | What it does | Requires |
|--------|-------------|----------|
| `make install` | Install bakec + dev dependencies | Python |
| `make generate` | Generate C for all 6 model x platform combos | Python |
| `make validate` | Run 36 checks (MISRA, traceability, safety, regression, API) | Python |
| `make test` | Run Python tests (113) + C tests (2 executables) | Python + GCC |
| `make build` | Compile desktop target with GCC/CMake | GCC + CMake |
| `make all` | All of the above in sequence | Python + GCC + CMake |

Cross-compilation targets (cortex_m4, aurix_tc397) are generated and validated but not
compiled — cross-compilers are not required. This matches the industry pattern where CI
validates generated code quality; firmware compilation happens in the target build system.

## License

MIT
