"""Tests for embedded safety pattern checks."""

from bakec.checks.safety import (
    check_no_dynamic_memory,
    check_no_recursion,
    check_bounded_loops,
    check_no_function_pointers,
    check_typed_variables,
    check_no_vla,
    run_safety_checks,
)


# --- SAFE-001: No dynamic memory ---

def test_safe_no_dynamic_memory_clean():
    code = "void init(void) { static int32_T buf[10]; }"
    assert check_no_dynamic_memory(code, "test.c") == []


def test_safe_no_dynamic_memory_malloc():
    code = "void init(void) { int *p = malloc(64); }"
    results = check_no_dynamic_memory(code, "test.c")
    assert len(results) == 1
    assert results[0].check_id == "SAFE-001"
    assert results[0].severity == "error"


def test_safe_no_dynamic_memory_calloc_realloc():
    code = "void f(void) { calloc(1, 4); realloc(p, 8); }"
    results = check_no_dynamic_memory(code, "test.c")
    assert len(results) == 2


# --- SAFE-002: No recursion ---

def test_safe_no_recursion_clean():
    code = "void foo(void) { bar(); }"
    assert check_no_recursion(code, "test.c") == []


def test_safe_no_recursion_detected():
    code = "int fib(int n) { return fib(n-1) + fib(n-2); }"
    results = check_no_recursion(code, "test.c")
    assert len(results) == 1
    assert results[0].check_id == "SAFE-002"


# --- SAFE-003: Bounded loops ---

def test_bounded_loops_clean():
    code = "void f(void) { for (int i = 0; i < 10; i++) { } }"
    assert check_bounded_loops(code, "test.c") == []


def test_bounded_loops_while_true():
    code = "void f(void) { while(true) { } }"
    results = check_bounded_loops(code, "test.c")
    assert len(results) == 1
    assert results[0].check_id == "SAFE-003"


def test_bounded_loops_while_1():
    code = "void f(void) { while(1) { } }"
    results = check_bounded_loops(code, "test.c")
    assert len(results) == 1


def test_bounded_loops_empty_for_condition():
    code = "void f(void) { for (;;) { } }"
    results = check_bounded_loops(code, "test.c")
    assert len(results) == 1


# --- SAFE-004: No function pointers ---

def test_no_function_pointers_clean():
    code = "void foo(void) { bar(); }"
    assert check_no_function_pointers(code, "test.c") == []


def test_no_function_pointers_detected():
    code = "typedef void (*callback_t)(int);"
    results = check_no_function_pointers(code, "test.c")
    assert len(results) == 1
    assert results[0].check_id == "SAFE-004"


# --- SAFE-005: Typed variables ---

def test_typed_variables_clean():
    code = "real_T pressure = 0.0;\nint32_T count = 0;"
    assert check_typed_variables(code, "test.c") == []


def test_typed_variables_raw_int():
    code = "int count = 0;"
    results = check_typed_variables(code, "test.c")
    assert len(results) == 1
    assert results[0].check_id == "SAFE-005"
    assert "int" in results[0].message


def test_typed_variables_raw_double():
    code = "double pressure = 0.0;"
    results = check_typed_variables(code, "test.c")
    assert len(results) == 1


def test_typed_variables_skips_typedef():
    code = "typedef double real_T;"
    assert check_typed_variables(code, "test.c") == []


def test_typed_variables_skips_preprocessor():
    code = "#define MAX_SIZE 100"
    assert check_typed_variables(code, "test.c") == []


# --- SAFE-006: No VLA ---

def test_no_vla_clean():
    code = "real_T buf[10];"
    assert check_no_vla(code, "test.c") == []


def test_no_vla_clean_uppercase_macro():
    code = "int32_T buf[MAX_SIZE];"
    assert check_no_vla(code, "test.c") == []


def test_no_vla_clean_indexing():
    code = "buf[i] = 0;"
    assert check_no_vla(code, "test.c") == []


def test_no_vla_detected():
    code = "real_T arr[size];"
    results = check_no_vla(code, "test.c")
    assert len(results) == 1
    assert results[0].check_id == "SAFE-006"


def test_no_vla_detected_int():
    code = "int arr[count];"
    results = check_no_vla(code, "test.c")
    assert len(results) == 1
    assert results[0].check_id == "SAFE-006"


# --- Orchestrator ---

def test_run_safety_checks_runs_all():
    code = "void init(void) { static int32_T buf[10]; }"
    results = run_safety_checks(code, "test.c")
    assert isinstance(results, list)


def test_run_safety_checks_allow_function_pointers():
    code = "typedef void (*callback_t)(int);"
    results_default = run_safety_checks(code, "test.c")
    results_allowed = run_safety_checks(code, "test.c", {"allow_function_pointers": True})
    fp_default = [r for r in results_default if r.check_id == "SAFE-004"]
    fp_allowed = [r for r in results_allowed if r.check_id == "SAFE-004"]
    assert len(fp_default) == 1
    assert len(fp_allowed) == 0


def test_run_safety_checks_allow_vla():
    code = "real_T arr[size];"
    results_default = run_safety_checks(code, "test.c")
    results_allowed = run_safety_checks(code, "test.c", {"allow_vla": True})
    vla_default = [r for r in results_default if r.check_id == "SAFE-006"]
    vla_allowed = [r for r in results_allowed if r.check_id == "SAFE-006"]
    assert len(vla_default) == 1
    assert len(vla_allowed) == 0
