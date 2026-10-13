# Adding a New Model

This guide walks through adding a new model to bakeC, from YAML definition
to generated code and tests.

## 1. Define the Model YAML

Create a file in `models/`, e.g. `models/my_controller.yaml`:

```yaml
schema_version: "1.0"

model:
  name: "my_controller"
  description: "Short description of what this controller does."
  sample_time_s: 0.001    # step period in seconds

  inputs:
    - name: "setpoint"
      description: "Desired value"
      unit: "bar"
      data_type: "real_T"
    - name: "measured"
      description: "Measured pressure"
      unit: "bar"
      data_type: "real_T"

  outputs:
    - name: "command"
      description: "Output signal"
      unit: "mA"
      data_type: "real_T"

  state:                   # optional, for stateful blocks
    - name: "integral"
      description: "Internal state"
      data_type: "real_T"
      initial_value: 0.0

  blocks:
    - type: "pid"          # must match a template in templates/blocks/
      name: "controller"
      params:
        Kp: 1.0
        Ki: 0.5
        Kd: 0.05
        output_min: -100.0
        output_max: 100.0
        anti_windup: true

  constraints:
    no_dynamic_memory: true
```

**Required fields:** `name`, `sample_time_s`, `inputs`, `outputs`, `blocks`.
**Optional fields:** `description`, `state`, `constraints`. Missing state is
normalized to an empty collection; omitted initial values default to zero.
PID inputs are ordered: setpoint first, measured value second. A single PID
uses declared `integral` and `prev_error` states, or block-qualified names
(e.g. `controller_integral`) when supplied. Undeclared PID states are created
with zero initial values. Multiple PID blocks use block-qualified names to
keep their state independent. Initialization restores all those initial values.

### Supported block types

| Type | Template | Description |
|------|----------|-------------|
| `pid` | `templates/blocks/pid.c.j2` | PID controller with optional anti-windup and saturation |
| `basis_function_sum` | `templates/blocks/basis_function.c.j2` | Weighted sum of B-spline basis functions |
| `offset` | (inline in controller.c.j2) | Scalar coefficient times an input signal |

## 2. Add a Template Block (if needed)

If your model uses a new block type not listed above:

1. Create `templates/blocks/<type>.c.j2`
2. The template receives `block` (name, params) and `meta` (traceability) context
3. It should define a `static` compute function
4. Use `{{ value | c_real }}` for model-derived real literals; never fixed decimal formatting
5. Use `real_T` / `int32_T` types, never raw `float` / `int`
6. Include `@trace` tags linking back to the model

See `templates/blocks/pid.c.j2` for reference.

## 3. Generate Code

```bash
python -m bakec.cli generate \
  --model models/my_controller.yaml \
  --platform platforms/desktop.yaml \
  --output generated/desktop/
```

This produces four files:
- `my_controller_controller.h` -- public API
- `my_controller_controller.c` -- algorithm implementation
- `my_controller_controller_data.c` -- calibration data
- `my_controller_controller_types.h` -- platform type definitions

Generate for other platforms by swapping the `--platform` argument.

## 4. Validate

```bash
python -m bakec.cli validate \
  --target generated/desktop/ \
  --rules src/bakec/checks/rules.yaml
```

Review heuristic findings and compile and test the generated behavior.
Baseline comparisons require `--baseline` pointing to an independent prior
output directory; without it, regression and API-stability checks are skipped.

## 5. Add Tests

- **Python integration test** in `tests/test_integration.py`: add a test case
  that runs the full generate pipeline for your model.
- **C unit test** in `tests/c/test_<name>.c`: follow the pattern in
  `test_pid_controller.c` (init, step with known inputs, verify outputs).
- Update `build/CMakeLists.txt` to build your C test.

## 6. Update Makefile

Add generate and validate commands for all relevant platform combinations
to the `generate:` and `validate:` targets in the Makefile.

## 7. Commit

Commit the model YAML, any new templates, generated output, and tests.
