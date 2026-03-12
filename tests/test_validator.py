"""Tests for model semantic validation."""

from bakec.validator import validate_model


def _make_model(**overrides):
    base = {
        "model": {
            "name": "test",
            "sample_time_s": 0.01,
            "inputs": [{"name": "x", "data_type": "real_T"}],
            "outputs": [{"name": "y", "data_type": "real_T"}],
            "blocks": [],
            "state": [],
        }
    }
    base["model"].update(overrides)
    return base


def test_valid_model():
    errors = validate_model(_make_model())
    assert errors == []


def test_negative_sample_time():
    errors = validate_model(_make_model(sample_time_s=-1.0))
    assert any("sample_time_s" in e for e in errors)


def test_basis_function_coefficient_mismatch():
    model = _make_model(blocks=[{
        "type": "basis_function_sum",
        "name": "test_block",
        "params": {
            "num_basis_functions": 5,
            "basis_order": 1,
            "coefficients": [1.0, 2.0, 3.0],
            "knots": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
            "input_signal": "x",
            "basis_input": "P",
        }
    }])
    errors = validate_model(model)
    assert any("coefficients" in e for e in errors)


def test_basis_function_knots_count():
    model = _make_model(blocks=[{
        "type": "basis_function_sum",
        "name": "test_block",
        "params": {
            "num_basis_functions": 5,
            "basis_order": 1,
            "coefficients": [1.0, 2.0, 3.0, 4.0, 5.0],
            "knots": [0.0, 1.0, 2.0],
            "input_signal": "x",
            "basis_input": "P",
        }
    }])
    errors = validate_model(model)
    assert any("knots" in e for e in errors)


def test_basis_function_knots_not_increasing():
    model = _make_model(blocks=[{
        "type": "basis_function_sum",
        "name": "test_block",
        "params": {
            "num_basis_functions": 3,
            "basis_order": 1,
            "coefficients": [1.0, 2.0, 3.0],
            "knots": [0.0, 5.0, 3.0, 10.0],
            "input_signal": "x",
            "basis_input": "P",
        }
    }])
    errors = validate_model(model)
    assert any("strictly increasing" in e for e in errors)


def test_pid_missing_gains():
    model = _make_model(blocks=[{
        "type": "pid",
        "name": "ctrl",
        "params": {"Kp": 1.0}
    }])
    errors = validate_model(model)
    assert any("Ki" in e for e in errors)
    assert any("Kd" in e for e in errors)


def test_pid_invalid_output_limits():
    model = _make_model(blocks=[{
        "type": "pid",
        "name": "ctrl",
        "params": {
            "Kp": 1.0, "Ki": 0.5, "Kd": 0.1,
            "output_min": 100.0,
            "output_max": -100.0,
        }
    }])
    errors = validate_model(model)
    assert any("output_min" in e for e in errors)
