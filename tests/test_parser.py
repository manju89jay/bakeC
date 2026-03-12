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
