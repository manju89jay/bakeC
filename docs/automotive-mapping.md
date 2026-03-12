# Automotive and Industrial Mapping

bakeC's architecture parallels concepts from AUTOSAR (AUTomotive Open
System ARchitecture) and industrial code generation practices, adapted
for a lightweight Python toolchain.

## Concept Mapping

| AUTOSAR / Industrial Concept     | bakeC Equivalent                      |
|----------------------------------|---------------------------------------|
| Software Component (SWC)         | Model YAML (one per controller)       |
| Runnable Entity                  | `_step()` function                    |
| Port Interface (Sender/Receiver) | `ExtU_T` / `ExtY_T` I/O structs      |
| RTE (Runtime Environment)        | Extern variable access pattern        |
| Base Software (BSW)              | Platform YAML + `_types.h`            |
| Calibration Parameters           | `_data.c` (const arrays)              |
| Application Parameter (A2L)      | YAML model `parameters` section       |
| System Target File               | Platform YAML                         |
| ARXML description                | YAML model + platform files           |
| Build Integration (Makefile)     | CMake + Makefile targets              |

## Architectural Parallels

The generated code follows the AUTOSAR Software Component pattern: each
model produces a self-contained unit with explicit input/output
interfaces (`ExtU_T`, `ExtY_T`), a deterministic lifecycle
(`initialize`, `step`, `terminate`), and separated calibration data.
This mirrors AUTOSAR's separation between application logic (runnables)
and infrastructure (RTE, BSW).

The platform YAML serves the role of AUTOSAR's ECU Configuration
Description, specifying target-specific properties like floating-point
precision, compiler flags, and available peripherals. Switching from a
desktop simulation to an ARM Cortex-M4 target only requires changing the
platform file — the model and templates remain unchanged, just as
AUTOSAR enables SWC portability across ECUs.

Calibration data in `_data.c` corresponds to AUTOSAR's concept of
calibratable parameters. The const arrays (coefficients, knot vectors)
can be updated independently of the algorithm code, supporting
flash-based calibration workflows common in automotive ECU development.
