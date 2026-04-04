"""Tests for model and platform parsing."""

import pytest
from pathlib import Path
from bakec.parser import parse_model, parse_platform


def test_parse_lung_model():
    model = parse_model(Path("models/lung_mnarx.yaml"))
    assert model["model"]["name"] == "mnarx_lung"
    assert model["model"]["sample_time_s"] == 0.016
    assert len(model["model"]["inputs"]) == 2
    assert len(model["model"]["outputs"]) == 1
    assert len(model["model"]["blocks"]) == 3


def test_parse_pid_model():
    model = parse_model(Path("models/pid_controller.yaml"))
    assert model["model"]["name"] == "pid_pressure"
    assert model["model"]["sample_time_s"] == 0.001
    assert len(model["model"]["blocks"]) == 1


def test_parse_desktop_platform():
    platform = parse_platform(Path("platforms/desktop.yaml"))
    assert platform["platform"]["types"]["real_T"] == "double"


def test_parse_cortex_platform():
    platform = parse_platform(Path("platforms/cortex_m4.yaml"))
    assert platform["platform"]["types"]["real_T"] == "float"


def test_missing_model_file():
    with pytest.raises(FileNotFoundError):
        parse_model(Path("models/nonexistent.yaml"))


def test_missing_model_key(tmp_path):
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("something: else\n")
    with pytest.raises(ValueError, match="must contain a 'model' key"):
        parse_model(bad_file)


# --- Schema validation tests ---


def test_schema_rejects_non_numeric_sample_time(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "model:\n"
        "  name: test\n"
        "  sample_time_s: not_a_number\n"
        "  inputs: [{name: x, data_type: real_T}]\n"
        "  outputs: [{name: y, data_type: real_T}]\n"
        "  blocks: []\n"
    )
    with pytest.raises(ValueError, match="schema error.*sample_time_s"):
        parse_model(bad)


def test_schema_rejects_negative_sample_time(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "model:\n"
        "  name: test\n"
        "  sample_time_s: -1.0\n"
        "  inputs: [{name: x, data_type: real_T}]\n"
        "  outputs: [{name: y, data_type: real_T}]\n"
        "  blocks: []\n"
    )
    with pytest.raises(ValueError, match="schema error.*sample_time_s"):
        parse_model(bad)


def test_schema_rejects_invalid_data_type(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "model:\n"
        "  name: test\n"
        "  sample_time_s: 0.01\n"
        "  inputs: [{name: x, data_type: banana}]\n"
        "  outputs: [{name: y, data_type: real_T}]\n"
        "  blocks: []\n"
    )
    with pytest.raises(ValueError, match="schema error.*data_type"):
        parse_model(bad)


def test_schema_rejects_block_without_name(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "model:\n"
        "  name: test\n"
        "  sample_time_s: 0.01\n"
        "  inputs: [{name: x, data_type: real_T}]\n"
        "  outputs: [{name: y, data_type: real_T}]\n"
        "  blocks:\n"
        "    - type: pid\n"
        "      params: {Kp: 1.0}\n"
    )
    with pytest.raises(ValueError, match="schema error.*name"):
        parse_model(bad)


def test_schema_rejects_invalid_model_name(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "model:\n"
        "  name: Invalid-Name\n"
        "  sample_time_s: 0.01\n"
        "  inputs: [{name: x, data_type: real_T}]\n"
        "  outputs: [{name: y, data_type: real_T}]\n"
        "  blocks: []\n"
    )
    with pytest.raises(ValueError, match="schema error.*name"):
        parse_model(bad)


def test_platform_schema_rejects_missing_types(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "platform:\n"
        "  name: test\n"
        "  constraints: {}\n"
    )
    with pytest.raises(ValueError, match="schema error.*types"):
        parse_platform(bad)


def test_platform_schema_rejects_missing_real_T(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "platform:\n"
        "  name: test\n"
        "  types:\n"
        "    int_T: int32_t\n"
        "  constraints: {}\n"
    )
    with pytest.raises(ValueError, match="schema error.*real_T"):
        parse_platform(bad)
