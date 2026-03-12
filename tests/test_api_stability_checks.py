"""Tests for API stability checks on generated header files."""

from pathlib import Path

from bakec.checks.api_stability import run_api_stability_checks


def _write_headers(tmp_path: Path, subdir: str, files: dict[str, str]) -> Path:
    """Write header files into a subdirectory and return its path."""
    d = tmp_path / subdir
    d.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (d / name).write_text(content, encoding="utf-8")
    return d


BASELINE_H = """\
#ifndef CONTROLLER_H
#define CONTROLLER_H

#include "controller_types.h"

typedef struct {
    real_T flow;
    real_T volume;
} ExtU_T;

typedef struct {
    real_T Paw;
} ExtY_T;

extern void controller_initialize(void);
extern void controller_step(void);
extern void controller_terminate(void);

extern ExtU_T controller_U;
extern ExtY_T controller_Y;

#endif /* CONTROLLER_H */
"""


# --- API-BREAK-FUNC: public function removed ---

def test_function_removed_detected(tmp_path):
    target_h = BASELINE_H.replace(
        "extern void controller_terminate(void);\n", ""
    )
    baseline = _write_headers(tmp_path, "baseline", {"controller.h": BASELINE_H})
    target = _write_headers(tmp_path, "target", {"controller.h": target_h})
    results = run_api_stability_checks(target, baseline)
    break_results = [r for r in results if r.check_id == "API-BREAK-FUNC"]
    assert len(break_results) == 1
    assert break_results[0].severity == "error"
    assert "controller_terminate" in break_results[0].message


# --- API-COMPAT-FUNC: signature changed ---

def test_function_signature_changed(tmp_path):
    target_h = BASELINE_H.replace(
        "extern void controller_step(void);",
        "extern int32_T controller_step(void);",
    )
    baseline = _write_headers(tmp_path, "baseline", {"controller.h": BASELINE_H})
    target = _write_headers(tmp_path, "target", {"controller.h": target_h})
    results = run_api_stability_checks(target, baseline)
    compat_results = [r for r in results if r.check_id == "API-COMPAT-FUNC"]
    assert len(compat_results) == 1
    assert compat_results[0].severity == "warning"


# --- API-BREAK-STRUCT: struct removed ---

def test_struct_removed(tmp_path):
    target_h = BASELINE_H.replace(
        "typedef struct {\n    real_T Paw;\n} ExtY_T;\n\n", ""
    )
    baseline = _write_headers(tmp_path, "baseline", {"controller.h": BASELINE_H})
    target = _write_headers(tmp_path, "target", {"controller.h": target_h})
    results = run_api_stability_checks(target, baseline)
    struct_results = [r for r in results if r.check_id == "API-BREAK-STRUCT"]
    assert len(struct_results) >= 1
    assert any(r.severity == "error" for r in struct_results)


# --- API-BREAK-STRUCT: struct field removed ---

def test_struct_field_removed(tmp_path):
    target_h = BASELINE_H.replace(
        "    real_T flow;\n    real_T volume;",
        "    real_T flow;",
    )
    baseline = _write_headers(tmp_path, "baseline", {"controller.h": BASELINE_H})
    target = _write_headers(tmp_path, "target", {"controller.h": target_h})
    results = run_api_stability_checks(target, baseline)
    break_results = [r for r in results if r.check_id == "API-BREAK-STRUCT"]
    assert len(break_results) >= 1
    assert break_results[0].severity == "error"


# --- API-COMPAT-STRUCT: struct field added ---

def test_struct_field_added(tmp_path):
    target_h = BASELINE_H.replace(
        "    real_T Paw;",
        "    real_T Paw;\n    real_T Paw_filtered;",
    )
    baseline = _write_headers(tmp_path, "baseline", {"controller.h": BASELINE_H})
    target = _write_headers(tmp_path, "target", {"controller.h": target_h})
    results = run_api_stability_checks(target, baseline)
    compat_results = [r for r in results if r.check_id == "API-COMPAT-STRUCT"]
    assert len(compat_results) >= 1
    assert compat_results[0].severity == "info"


# --- API-BREAK-TYPE: typedef removed ---

def test_typedef_removed(tmp_path):
    baseline_h = BASELINE_H + "\ntypedef real_T pressure_T;\n"
    baseline = _write_headers(tmp_path, "baseline", {"controller.h": baseline_h})
    target = _write_headers(tmp_path, "target", {"controller.h": BASELINE_H})
    results = run_api_stability_checks(target, baseline)
    type_results = [r for r in results if r.check_id == "API-BREAK-TYPE"]
    assert len(type_results) == 1
    assert type_results[0].severity == "error"
    assert "pressure_T" in type_results[0].message


# --- API-COMPAT-GUARD: header guard changed ---

def test_header_guard_changed(tmp_path):
    target_h = BASELINE_H.replace("CONTROLLER_H", "CTRL_H")
    baseline = _write_headers(tmp_path, "baseline", {"controller.h": BASELINE_H})
    target = _write_headers(tmp_path, "target", {"controller.h": target_h})
    results = run_api_stability_checks(target, baseline)
    guard_results = [r for r in results if r.check_id == "API-COMPAT-GUARD"]
    assert len(guard_results) == 1
    assert guard_results[0].severity == "warning"


# --- Identical headers ---

def test_identical_no_findings(tmp_path):
    baseline = _write_headers(tmp_path, "baseline", {"controller.h": BASELINE_H})
    target = _write_headers(tmp_path, "target", {"controller.h": BASELINE_H})
    results = run_api_stability_checks(target, baseline)
    assert len(results) == 0


# --- Only .h files processed ---

def test_ignores_c_files(tmp_path):
    baseline = _write_headers(tmp_path, "baseline", {"controller.h": BASELINE_H})
    target = _write_headers(tmp_path, "target", {"controller.h": BASELINE_H})
    # Add .c files that differ — should not affect API stability
    (tmp_path / "baseline" / "controller.c").write_text("void foo(void) {}", encoding="utf-8")
    (tmp_path / "target" / "controller.c").write_text("void bar(void) {}", encoding="utf-8")
    results = run_api_stability_checks(target, baseline)
    assert len(results) == 0
