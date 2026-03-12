"""Tests for the code generation engine."""

from pathlib import Path
from bakec.parser import parse_model, parse_platform
from bakec.engine import CodegenEngine


def _create_engine(model_file="models/lung_mnarx.yaml",
                   platform_file="platforms/desktop.yaml"):
    model = parse_model(Path(model_file))
    platform = parse_platform(Path(platform_file))
    return CodegenEngine(
        template_dir=Path("templates"),
        model=model,
        platform=platform,
        model_path=model_file,
        platform_path=platform_file,
    )


def test_render_all_produces_four_files():
    files = _create_engine().render_all()
    assert len(files) == 4
    assert "mnarx_lung_controller.h" in files
    assert "mnarx_lung_controller.c" in files
    assert "mnarx_lung_controller_data.c" in files
    assert "mnarx_lung_controller_types.h" in files


def test_header_guard_present():
    header = _create_engine().render_all()["mnarx_lung_controller.h"]
    assert "#ifndef MNARX_LUNG_CONTROLLER_H" in header
    assert "#define MNARX_LUNG_CONTROLLER_H" in header
    assert "#endif" in header


def test_traceability_comments_present():
    source = _create_engine().render_all()["mnarx_lung_controller.c"]
    assert "@trace" in source
    assert "bakeC v" in source
    assert "sha256:" in source


def test_no_malloc_in_generated():
    for name, content in _create_engine().render_all().items():
        assert "malloc" not in content, f"malloc found in {name}"
        assert "calloc" not in content, f"calloc found in {name}"
        assert "free(" not in content, f"free() found in {name}"


def test_cortex_m4_uses_float():
    types = _create_engine(platform_file="platforms/cortex_m4.yaml") \
        .render_all()["mnarx_lung_controller_types.h"]
    assert "typedef float real_T" in types


def test_desktop_uses_double():
    types = _create_engine().render_all()["mnarx_lung_controller_types.h"]
    assert "typedef double real_T" in types


def test_pid_model_generates():
    files = _create_engine(
        model_file="models/pid_controller.yaml"
    ).render_all()
    assert len(files) == 4
    assert "pid_pressure_controller.c" in files


def test_step_function_exists():
    source = _create_engine().render_all()["mnarx_lung_controller.c"]
    assert "void mnarx_lung_step(void)" in source


def test_init_function_exists():
    source = _create_engine().render_all()["mnarx_lung_controller.c"]
    assert "void mnarx_lung_initialize(void)" in source
