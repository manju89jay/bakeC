# bakeC

Raw YAML model definitions in, production-quality embedded C code out.

bakeC is a template-based code generation toolchain that mirrors the [MATLAB Embedded Coder](https://www.mathworks.com/products/embedded-coder.html) / TLC pipeline using modern open-source tools: YAML for model definitions, Jinja2 for templates, and Python for orchestration.

## Quick Start

```bash
pip install -e ".[dev]"

# Generate C code for the mNARX lung model targeting desktop
python -m bakec.cli generate \
  --model models/lung_mnarx.yaml \
  --platform platforms/desktop.yaml \
  --output generated/desktop/

# Generate for ARM Cortex-M4 (float instead of double)
python -m bakec.cli generate \
  --model models/lung_mnarx.yaml \
  --platform platforms/cortex_m4.yaml \
  --output generated/cortex_m4/
```

## What Gets Generated

Each model + platform combination produces four files:

| File | Purpose |
|---|---|
| `{name}_controller.h` | Public API: I/O structs, lifecycle function prototypes |
| `{name}_controller.c` | Algorithm: init/step/terminate with block implementations |
| `{name}_controller_data.c` | Calibration data: coefficients, knot vectors (replaceable independently) |
| `{name}_controller_types.h` | Platform-specific type definitions (real_T, int32_T, etc.) |

Generated code follows MATLAB Embedded Coder conventions: struct-based I/O, static allocation only (no malloc), `@trace` tags linking every function back to the source YAML, and sha256 content hashes for traceability.

## Project Structure

```
src/bakec/          Python package (parser, validator, engine, writer, cli)
models/             YAML model definitions
templates/          Jinja2 templates (mirrors TLC file structure)
  blocks/           Per-block-type template fragments
platforms/          Target platform configurations
generated/          Output directory (committed for review)
tests/              Python and C tests
quality/            Generated code quality checks
build/              CMake build for compiling generated C
```

## Models

- **mNARX Lung** (`models/lung_mnarx.yaml`) — Modified nonlinear autoregressive lung mechanics model with B-spline basis functions. See [docs/model_background.md](docs/model_background.md).
- **PID Controller** (`models/pid_controller.yaml`) — PID pressure controller for hydraulic valve systems. Demonstrates toolchain generality with a different computational pattern.

## Platforms

- **Desktop** (`platforms/desktop.yaml`) — GCC, `double` precision, assertions enabled, `-O2`
- **ARM Cortex-M4** (`platforms/cortex_m4.yaml`) — `arm-none-eabi-gcc`, `float` precision, no printf, `-Os`

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run Python tests
python -m pytest tests/ -v

# Run quality checks on generated code
python quality/check_generated.py generated/

# Build and test generated C (requires CMake + GCC)
cmake -B build/out -S build -DPLATFORM=desktop
cmake --build build/out
ctest --test-dir build/out --output-on-failure
```

## Architecture

bakeC follows the same separation-of-concerns as MATLAB Embedded Coder:

1. **Parser** — reads YAML, produces a Python dict intermediate representation (equivalent of `.rtw`)
2. **Validator** — semantic checks on the IR (sample times, coefficient counts, knot ordering)
3. **Engine** — feeds the IR into Jinja2 templates (equivalent of TLC) to emit C code
4. **Writer** — writes rendered files to disk with line counts
5. **CLI** — orchestrates the pipeline with progress output

See [docs/architecture.md](docs/architecture.md) for the full architectural mapping between TLC and Jinja2, and how the design maps to AUTOSAR concepts.

## License

MIT
