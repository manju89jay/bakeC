"""Tests for MISRA C:2012 subset checks."""

from bakec.checks.misra import (
    check_no_dynamic_memory,
    check_no_recursion,
    check_explicit_return_type,
    check_implicit_type_conversion,
    check_else_termination,
    check_unused_parameters,
    check_extern_has_definition,
    check_loop_var_modification,
    check_no_stdio,
    check_const_pointer_params,
    run_misra_checks,
)


# --- MISRA-21.3: No dynamic memory ---

def test_no_dynamic_memory_clean():
    code = "void init(void) { static int32_T buf[10]; }"
    assert check_no_dynamic_memory(code, "test.c") == []


def test_no_dynamic_memory_malloc():
    code = "void init(void) { int *p = malloc(sizeof(int)); }"
    results = check_no_dynamic_memory(code, "test.c")
    assert len(results) == 1
    assert results[0].check_id == "MISRA-21.3"
    assert results[0].severity == "error"


def test_no_dynamic_memory_free():
    code = "void cleanup(void) { free(ptr); }"
    results = check_no_dynamic_memory(code, "test.c")
    assert len(results) == 1
    assert results[0].check_id == "MISRA-21.3"


# --- MISRA-17.2: No recursion ---

def test_no_recursion_clean():
    code = "void foo(void) { bar(); }"
    assert check_no_recursion(code, "test.c") == []


def test_no_recursion_detected():
    code = "int factorial(int n) { return n * factorial(n - 1); }"
    results = check_no_recursion(code, "test.c")
    assert len(results) == 1
    assert results[0].check_id == "MISRA-17.2"


# --- MISRA-8.1: Explicit return type ---

def test_explicit_return_type_clean():
    code = "void init(void) { }"
    assert check_explicit_return_type(code, "test.c") == []


def test_explicit_return_type_missing():
    code = "init(void) { }"
    results = check_explicit_return_type(code, "test.c")
    assert len(results) == 1
    assert results[0].check_id == "MISRA-8.1"


# --- MISRA-10.1: Implicit type conversion ---

def test_implicit_conversion_clean():
    code = "int32_T x = (int32_T)some_value;"
    assert check_implicit_type_conversion(code, "test.c") == []


def test_implicit_conversion_narrowing():
    code = "int16_T x = some_int32_T;"
    results = check_implicit_type_conversion(code, "test.c")
    assert len(results) == 1
    assert results[0].check_id == "MISRA-10.1"


# --- MISRA-15.7: else termination ---

def test_else_termination_clean():
    code = "if (a) { x; } else if (b) { y; } else { z; }"
    assert check_else_termination(code, "test.c") == []


def test_else_termination_missing():
    code = "if (a) { x; } else if (b) { y; }"
    results = check_else_termination(code, "test.c")
    assert len(results) >= 1
    assert results[0].check_id == "MISRA-15.7"


# --- MISRA-2.7: Unused parameters ---

def test_unused_parameters_clean():
    code = "void foo(int x) { return x + 1; }"
    assert check_unused_parameters(code, "test.c") == []


def test_unused_parameters_detected():
    code = "void foo(int x, int y) { return x + 1; }"
    results = check_unused_parameters(code, "test.c")
    assert len(results) == 1
    assert results[0].check_id == "MISRA-2.7"
    assert "y" in results[0].message


# --- MISRA-8.4: extern has definition ---

def test_extern_has_definition_in_header():
    code = "extern void mnarx_lung_initialize(void);"
    assert check_extern_has_definition(code, "test.h") == []


def test_extern_has_definition_clean():
    code = "extern int32_T count;\nint32_T count = 0;"
    assert check_extern_has_definition(code, "test.c") == []


def test_extern_has_definition_missing():
    code = "extern int32_T orphan_var;"
    results = check_extern_has_definition(code, "test.c")
    assert len(results) == 1
    assert results[0].check_id == "MISRA-8.4"


# --- MISRA-14.2: Loop variable modification ---

def test_loop_var_modification_clean():
    code = "void f(void) { for (int i = 0; i < 10; i++) { x[i] = 0; } }"
    assert check_loop_var_modification(code, "test.c") == []


def test_loop_var_modification_detected():
    code = "void f(void) { for (int i = 0; i < 10; i++) { i = i + 2; } }"
    results = check_loop_var_modification(code, "test.c")
    assert len(results) == 1
    assert results[0].check_id == "MISRA-14.2"


# --- MISRA-21.6: No stdio ---

def test_no_stdio_clean():
    code = "void init(void) { int x = 42; }"
    assert check_no_stdio(code, "test.c") == []


def test_no_stdio_printf():
    code = 'void debug(void) { printf("hello"); }'
    results = check_no_stdio(code, "test.c")
    assert len(results) == 1
    assert results[0].check_id == "MISRA-21.6"


def test_no_stdio_exception():
    code = '#ifdef SIMULATION_MODE\nvoid debug(void) { printf("x"); }\n#endif'
    assert check_no_stdio(code, "test.c", exceptions=["SIMULATION_MODE"]) == []


# --- MISRA-8.13: Const pointer params ---

def test_const_pointer_params_clean():
    code = "void foo(const int *p) { return *p; }"
    assert check_const_pointer_params(code, "test.c") == []


def test_const_pointer_params_detected():
    code = "void foo(int *p) { return *p + 1; }"
    results = check_const_pointer_params(code, "test.c")
    assert len(results) == 1
    assert results[0].check_id == "MISRA-8.13"


# --- Orchestrator ---

def test_run_misra_checks_runs_all():
    code = "void init(void) { static int32_T buf[10]; }"
    results = run_misra_checks(code, "test.c")
    assert isinstance(results, list)


def test_run_misra_checks_disable_rule():
    code = "void init(void) { int *p = malloc(sizeof(int)); }"
    config = {"rules": {"MISRA-21.3": {"enabled": False}}}
    results = run_misra_checks(code, "test.c", config)
    assert all(r.check_id != "MISRA-21.3" for r in results)


def test_run_misra_checks_override_severity():
    code = "void init(void) { int *p = malloc(sizeof(int)); }"
    config = {"rules": {"MISRA-21.3": {"severity": "info"}}}
    results = run_misra_checks(code, "test.c", config)
    misra_21_3 = [r for r in results if r.check_id == "MISRA-21.3"]
    assert all(r.severity == "info" for r in misra_21_3)
