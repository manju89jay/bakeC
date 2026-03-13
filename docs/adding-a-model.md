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

  outputs:
    - name: "command"
      description: "Output signal"
      unit: "mA"
      data_type: "real_T"

  state:                   # optional, for stateful blocks
    - name: "accumulator"
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
    misra_compliant: true
```

**Required fields:** `name`, `description`, `sample_time_s`, `inputs`, `outputs`, `blocks`.
**Optional fields:** `state`, `constraints`.

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
4. Use `{{ type_suffix }}` after float literals for platform portability
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

Fix any MISRA, traceability, or safety warnings before proceeding.

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
