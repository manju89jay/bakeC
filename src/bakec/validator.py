"""Semantic validation of parsed model data."""

import logging
from typing import Any

logger = logging.getLogger("bakec")


def validate_model(data: dict[str, Any]) -> list[str]:
    """Validate a parsed model for semantic correctness.

    Returns a list of error strings. Empty list means valid.

    Checks performed:
    - sample_time_s must be > 0
    - All inputs must have name and data_type
    - All outputs must have name and data_type
    - Each block is validated by type:

    For basis_function_sum blocks:
    - num_basis_functions must be a positive integer
    - len(coefficients) must equal num_basis_functions
    - len(knots) must equal num_basis_functions + 1
    - knots must be strictly increasing
    - basis_order must be 0 or 1

    For pid blocks:
    - Kp, Ki, Kd are required
    - output_min must be < output_max (if both provided)

    For offset blocks:
    - coefficient is required
    - input_signal is required
    """
    errors: list[str] = []
    model = data.get("model", {})

    # Check sample_time_s
    sample_time = model.get("sample_time_s", 0)
    if sample_time <= 0:
        errors.append(f"sample_time_s must be > 0, got {sample_time}")

    # Check inputs
    for i, inp in enumerate(model.get("inputs", [])):
        if "name" not in inp:
            errors.append(f"inputs[{i}]: missing 'name'")
        if "data_type" not in inp:
            errors.append(f"inputs[{i}]: missing 'data_type'")

    # Check outputs
    for i, out in enumerate(model.get("outputs", [])):
        if "name" not in out:
            errors.append(f"outputs[{i}]: missing 'name'")
        if "data_type" not in out:
            errors.append(f"outputs[{i}]: missing 'data_type'")

    # Check blocks
    for block in model.get("blocks", []):
        block_type = block.get("type", "")
        block_name = block.get("name", "unknown")
        params = block.get("params", {})

        if block_type == "basis_function_sum":
            n = params.get("num_basis_functions", 0)
            if not isinstance(n, int) or n <= 0:
                errors.append(f"block '{block_name}': num_basis_functions must be a positive integer")

            coeffs = params.get("coefficients", [])
            if len(coeffs) != n:
                errors.append(
                    f"block '{block_name}': expected {n} coefficients, got {len(coeffs)}"
                )

            knots = params.get("knots", [])
            if len(knots) != n + 1:
                errors.append(
                    f"block '{block_name}': expected {n + 1} knots, got {len(knots)}"
                )

            for j in range(len(knots) - 1):
                if knots[j] >= knots[j + 1]:
                    errors.append(
                        f"block '{block_name}': knots must be strictly increasing "
                        f"(knots[{j}]={knots[j]} >= knots[{j+1}]={knots[j+1]})"
                    )
                    break

            basis_order = params.get("basis_order", -1)
            if basis_order not in (0, 1):
                errors.append(f"block '{block_name}': basis_order must be 0 or 1")

        elif block_type == "pid":
            for gain in ("Kp", "Ki", "Kd"):
                if gain not in params:
                    errors.append(f"block '{block_name}': missing required parameter '{gain}'")

            if "output_min" in params and "output_max" in params:
                if params["output_min"] >= params["output_max"]:
                    errors.append(
                        f"block '{block_name}': output_min ({params['output_min']}) "
                        f"must be < output_max ({params['output_max']})"
                    )

        elif block_type == "offset":
            if "coefficient" not in params:
                errors.append(f"block '{block_name}': missing required parameter 'coefficient'")
            if "input_signal" not in params:
                errors.append(f"block '{block_name}': missing required parameter 'input_signal'")

    if errors:
        logger.warning("Validation found %d error(s)", len(errors))
    else:
        logger.info("Model validation passed")

    return errors
