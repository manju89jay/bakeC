"""Tests for regression checks between generated code versions."""

from pathlib import Path

from bakec.checks.regression import run_regression_checks


def _write_files(tmp_path: Path, subdir: str, files: dict[str, str]) -> Path:
    """Write a set of files into a subdirectory and return its path."""
    d = tmp_path / subdir
    d.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (d / name).write_text(content, encoding="utf-8")
    return d


BASELINE_C = """\
#include "controller.h"

typedef struct {
    real_T flow;
    real_T volume;
} ExtU_T;

extern const real_T coeffs[];

void controller_initialize(void) {}
void controller_step(void) {}
void controller_terminate(void) {}
"""

BASELINE_H = """\
#ifndef CONTROLLER_H
#define CONTROLLER_H
extern void controller_initialize(void);
extern void controller_step(void);
extern void controller_terminate(void);
#endif
"""


# --- REG-FILE-ADD / REG-FILE-DEL ---

def test_file_added(tmp_path):
    baseline = _write_files(tmp_path, "baseline", {"a.c": "int x;"})
    target = _write_files(tmp_path, "target", {"a.c": "int x;", "b.c": "int y;"})
    results = run_regression_checks(target, baseline)
    ids = [r.check_id for r in results]
    assert "REG-FILE-ADD" in ids


def test_file_deleted(tmp_path):
    baseline = _write_files(tmp_path, "baseline", {"a.c": "int x;", "b.c": "int y;"})
    target = _write_files(tmp_path, "target", {"a.c": "int x;"})
    results = run_regression_checks(target, baseline)
    del_results = [r for r in results if r.check_id == "REG-FILE-DEL"]
    assert len(del_results) == 1
    assert del_results[0].severity == "error"


# --- REG-FUNC-ADD / REG-FUNC-DEL / REG-FUNC-SIG ---

def test_function_added(tmp_path):
    baseline = _write_files(tmp_path, "baseline", {"a.c": "void foo(void) {}"})
    target = _write_files(tmp_path, "target", {"a.c": "void foo(void) {}\nvoid bar(void) {}"})
    results = run_regression_checks(target, baseline)
    assert any(r.check_id == "REG-FUNC-ADD" and "bar" in r.message for r in results)


def test_function_deleted(tmp_path):
    baseline = _write_files(tmp_path, "baseline", {"a.c": "void foo(void) {}\nvoid bar(void) {}"})
    target = _write_files(tmp_path, "target", {"a.c": "void foo(void) {}"})
    results = run_regression_checks(target, baseline)
    del_results = [r for r in results if r.check_id == "REG-FUNC-DEL"]
    assert len(del_results) == 1
    assert del_results[0].severity == "error"


def test_function_signature_changed(tmp_path):
    baseline = _write_files(tmp_path, "baseline", {"a.c": "void foo(int x) {}"})
    target = _write_files(tmp_path, "target", {"a.c": "void foo(int x, int y) {}"})
    results = run_regression_checks(target, baseline)
    sig_results = [r for r in results if r.check_id == "REG-FUNC-SIG"]
    assert len(sig_results) == 1


# --- REG-STRUCT ---

def test_struct_member_removed(tmp_path):
    baseline_code = "typedef struct { real_T x; real_T y; } Point_T;"
    target_code = "typedef struct { real_T x; } Point_T;"
    baseline = _write_files(tmp_path, "baseline", {"a.h": baseline_code})
    target = _write_files(tmp_path, "target", {"a.h": target_code})
    results = run_regression_checks(target, baseline)
    struct_results = [r for r in results if r.check_id == "REG-STRUCT" and r.severity == "error"]
    assert len(struct_results) == 1


def test_struct_member_added(tmp_path):
    baseline_code = "typedef struct { real_T x; } Point_T;"
    target_code = "typedef struct { real_T x; real_T y; } Point_T;"
    baseline = _write_files(tmp_path, "baseline", {"a.h": baseline_code})
    target = _write_files(tmp_path, "target", {"a.h": target_code})
    results = run_regression_checks(target, baseline)
    struct_results = [r for r in results if r.check_id == "REG-STRUCT" and r.severity == "warning"]
    assert len(struct_results) == 1


# --- REG-PARAM ---

def test_const_array_changed(tmp_path):
    baseline_code = "const real_T coeffs[] = { 1.0, 2.0, 3.0 };"
    target_code = "const real_T coeffs[] = { 1.0, 2.5, 3.0 };"
    baseline = _write_files(tmp_path, "baseline", {"a.c": baseline_code})
    target = _write_files(tmp_path, "target", {"a.c": target_code})
    results = run_regression_checks(target, baseline)
    param_results = [r for r in results if r.check_id == "REG-PARAM"]
    assert len(param_results) >= 1


# --- REG-INCLUDE ---

def test_include_changed(tmp_path):
    baseline_code = '#include "controller.h"\n#include <assert.h>'
    target_code = '#include "controller.h"\n#include <math.h>'
    baseline = _write_files(tmp_path, "baseline", {"a.c": baseline_code})
    target = _write_files(tmp_path, "target", {"a.c": target_code})
    results = run_regression_checks(target, baseline)
    inc_results = [r for r in results if r.check_id == "REG-INCLUDE"]
    assert len(inc_results) == 1


# --- REG-LINECOUNT ---

def test_linecount_change(tmp_path):
    baseline_code = "\n".join([f"int x{i} = {i};" for i in range(100)])
    target_code = "\n".join([f"int x{i} = {i};" for i in range(150)])
    baseline = _write_files(tmp_path, "baseline", {"a.c": baseline_code})
    target = _write_files(tmp_path, "target", {"a.c": target_code})
    results = run_regression_checks(target, baseline)
    lc_results = [r for r in results if r.check_id == "REG-LINECOUNT"]
    assert len(lc_results) == 1
    assert lc_results[0].severity == "info"


# --- Identical baseline ---

def test_identical_no_findings(tmp_path):
    baseline = _write_files(tmp_path, "baseline", {"a.c": BASELINE_C, "a.h": BASELINE_H})
    target = _write_files(tmp_path, "target", {"a.c": BASELINE_C, "a.h": BASELINE_H})
    results = run_regression_checks(target, baseline)
    assert len(results) == 0
