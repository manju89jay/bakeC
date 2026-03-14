"""Integration test: full pipeline from YAML to generated C."""

import subprocess
import sys
from pathlib import Path


def test_full_pipeline_lung_desktop(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "bakec.cli", "generate",
         "--model", "models/lung_mnarx.yaml",
         "--platform", "platforms/desktop.yaml",
         "--output", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"CLI failed:\n{result.stderr}\n{result.stdout}"
    assert (tmp_path / "mnarx_lung_controller.h").exists()
    assert (tmp_path / "mnarx_lung_controller.c").exists()
    assert (tmp_path / "mnarx_lung_controller_data.c").exists()
    assert (tmp_path / "mnarx_lung_controller_types.h").exists()

    source = (tmp_path / "mnarx_lung_controller.c").read_text()
    assert len(source) > 100
    assert "mnarx_lung_step" in source
    assert "DO NOT EDIT" in source


def test_full_pipeline_pid_desktop(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "bakec.cli", "generate",
         "--model", "models/pid_controller.yaml",
         "--platform", "platforms/desktop.yaml",
         "--output", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"CLI failed:\n{result.stderr}\n{result.stdout}"
    assert (tmp_path / "pid_pressure_controller.c").exists()


def test_full_pipeline_cortex_m4(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "bakec.cli", "generate",
         "--model", "models/lung_mnarx.yaml",
         "--platform", "platforms/cortex_m4.yaml",
         "--output", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"CLI failed:\n{result.stderr}\n{result.stdout}"
    types_content = (tmp_path / "mnarx_lung_controller_types.h").read_text()
    assert "typedef float real_T" in types_content


def test_full_pipeline_lung_aurix_tc397(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "bakec.cli", "generate",
         "--model", "models/lung_mnarx.yaml",
         "--platform", "platforms/aurix_tc397.yaml",
         "--output", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"CLI failed:\n{result.stderr}\n{result.stdout}"
    types_content = (tmp_path / "mnarx_lung_controller_types.h").read_text()
    assert "typedef float real_T" in types_content
    source = (tmp_path / "mnarx_lung_controller.c").read_text()
    assert "mnarx_lung_step" in source
    assert "DO NOT EDIT" in source
    assert "#include <assert.h>" not in source


def test_full_pipeline_pid_aurix_tc397(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "bakec.cli", "generate",
         "--model", "models/pid_controller.yaml",
         "--platform", "platforms/aurix_tc397.yaml",
         "--output", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"CLI failed:\n{result.stderr}\n{result.stdout}"
    assert (tmp_path / "pid_pressure_controller.c").exists()


def test_full_pipeline_lookup_table_desktop(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "bakec.cli", "generate",
         "--model", "models/lookup_table_1d.yaml",
         "--platform", "platforms/desktop.yaml",
         "--output", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"CLI failed:\n{result.stderr}\n{result.stdout}"
    assert (tmp_path / "temp_sensor_controller.h").exists()
    assert (tmp_path / "temp_sensor_controller.c").exists()
    assert (tmp_path / "temp_sensor_controller_data.c").exists()
    assert (tmp_path / "temp_sensor_controller_types.h").exists()

    source = (tmp_path / "temp_sensor_controller.c").read_text()
    assert "ntc_linearize_interpolate" in source
    assert "DO NOT EDIT" in source


def test_full_pipeline_lookup_table_cortex_m4(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "bakec.cli", "generate",
         "--model", "models/lookup_table_1d.yaml",
         "--platform", "platforms/cortex_m4.yaml",
         "--output", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"CLI failed:\n{result.stderr}\n{result.stdout}"
    types_content = (tmp_path / "temp_sensor_controller_types.h").read_text()
    assert "typedef float real_T" in types_content
    data = (tmp_path / "temp_sensor_controller_data.c").read_text()
    assert "0.5000f" in data
