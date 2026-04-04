"""MISRA C:2012 inspired code quality checks.

Regex-based approximations of a small MISRA C:2012 subset. These are NOT
a substitute for a certified MISRA analyzer (cppcheck --addon=misra,
PC-lint, Polyspace). They catch common violations via text pattern
matching but may produce false positives and will miss violations that
require semantic analysis (type promotion, pointer arithmetic, side
effects in controlling expressions, etc.).

Each check function takes file content and filename, returns a list of
CheckResult.
"""

import re
import logging
from typing import Any

from bakec.checks.runner import CheckResult

logger = logging.getLogger("bakec")

# Regex to strip C block and line comments
_COMMENT_RE = re.compile(r'//.*?$|/\*.*?\*/', re.MULTILINE | re.DOTALL)


def _strip_comments(content: str) -> str:
    """Remove C comments from source text."""
    return _COMMENT_RE.sub('', content)


def _find_line(content: str, pos: int) -> int:
    """Return 1-based line number for a character position."""
    return content[:pos].count('\n') + 1


def _extract_functions(content: str) -> list[dict]:
    """Extract function definitions with name, params, body, and line number.

    Returns list of dicts with keys: name, params, body, line, full_match.
    """
    stripped = _strip_comments(content)
    # Match return_type function_name(params) { ... }
    # Use a simpler approach: find function headers then match braces
    pattern = re.compile(
        r'^(\w[\w\s\*]*?)\s+(\w+)\s*\(([^)]*)\)\s*\{',
        re.MULTILINE,
    )
    functions = []
    for m in pattern.finditer(stripped):
        ret_type = m.group(1).strip()
        name = m.group(2)
        params = m.group(3)
        line = stripped[:m.start()].count('\n') + 1
        # Find matching closing brace
        brace_count = 1
        idx = m.end()
        while idx < len(stripped) and brace_count > 0:
            if stripped[idx] == '{':
                brace_count += 1
            elif stripped[idx] == '}':
                brace_count -= 1
            idx += 1
        body = stripped[m.end():idx - 1] if idx <= len(stripped) else ""
        functions.append({
            "ret_type": ret_type,
            "name": name,
            "params": params,
            "body": body,
            "line": line,
        })
    return functions


def check_no_dynamic_memory(content: str, filename: str) -> list[CheckResult]:
    """MISRA-21.3: No dynamic memory allocation.

    Regex approximation. Catches direct calls to malloc/calloc/realloc/free.
    Limitation: misses calls through macros, wrappers, or function pointers.
    """
    results = []
    stripped = _strip_comments(content)
    for pattern in (r'\bmalloc\s*\(', r'\bcalloc\s*\(', r'\brealloc\s*\(', r'\bfree\s*\('):
        for m in re.finditer(pattern, stripped):
            results.append(CheckResult(
                file=filename,
                line=_find_line(stripped, m.start()),
                severity="error",
                check_id="MISRA-21.3",
                message=f"Dynamic memory function '{m.group().rstrip('(')}' used",
                suggestion="Use static allocation instead",
            ))
    return results


def check_no_recursion(content: str, filename: str) -> list[CheckResult]:
    """MISRA-17.2: No recursive function calls.

    Regex approximation. Only detects direct self-recursion (A calls A).
    Limitation: misses indirect recursion (A→B→A) and calls through
    function pointers.
    """
    results = []
    for func in _extract_functions(content):
        # Check if function name appears as a call inside its own body
        call_pattern = re.compile(r'\b' + re.escape(func["name"]) + r'\s*\(')
        if call_pattern.search(func["body"]):
            results.append(CheckResult(
                file=filename,
                line=func["line"],
                severity="error",
                check_id="MISRA-17.2",
                message=f"Function '{func['name']}' appears to call itself (recursion)",
                suggestion="Refactor to iterative implementation",
            ))
    return results


def check_explicit_return_type(content: str, filename: str) -> list[CheckResult]:
    """MISRA-8.1: All function definitions must have explicit return type.

    Regex approximation. Checks for bare identifier( at line start.
    Limitation: may false-positive on macros that expand to function-like
    syntax; misses multi-line return types.
    """
    results = []
    stripped = _strip_comments(content)
    # Find lines that look like function definitions without a return type
    # Pattern: identifier(params) { at the start of a line without a type prefix
    for m in re.finditer(r'^(\w+)\s*\(([^)]*)\)\s*\{', stripped, re.MULTILINE):
        name = m.group(1)
        # These keywords are types or qualifiers, not bare function names
        if name not in ('if', 'while', 'for', 'switch', 'return', 'sizeof'):
            # Check if the previous non-whitespace on the same logical line is not a type
            line_start = stripped.rfind('\n', 0, m.start()) + 1
            prefix = stripped[line_start:m.start()].strip()
            if not prefix:
                results.append(CheckResult(
                    file=filename,
                    line=_find_line(stripped, m.start()),
                    severity="warning",
                    check_id="MISRA-8.1",
                    message=f"Function '{name}' may be missing explicit return type",
                ))
    return results


def check_implicit_type_conversion(content: str, filename: str) -> list[CheckResult]:
    """MISRA-10.1: Flag obvious narrowing assignments without cast.

    Regex approximation. Checks 3 hardcoded narrowing patterns only.
    Limitation: misses narrowing through return values, function args,
    casts, or types not in its pattern list.
    """
    results = []
    stripped = _strip_comments(content)
    # Look for int32_T = int16_T or similar narrowing patterns
    narrow_patterns = [
        (r'\bint16_T\s+\w+\s*=\s*\w*int32_T', "int32_T assigned to int16_T"),
        (r'\bint8_T\s+\w+\s*=\s*\w*int16_T', "int16_T assigned to int8_T"),
        (r'\bint8_T\s+\w+\s*=\s*\w*int32_T', "int32_T assigned to int8_T"),
    ]
    for pattern, msg in narrow_patterns:
        for m in re.finditer(pattern, stripped):
            results.append(CheckResult(
                file=filename,
                line=_find_line(stripped, m.start()),
                severity="warning",
                check_id="MISRA-10.1",
                message=msg,
                suggestion="Add explicit cast",
            ))
    return results


def check_else_termination(content: str, filename: str) -> list[CheckResult]:
    """MISRA-15.7: if/else-if chains must be terminated with final else.

    Regex approximation. Limitation: the [^}]* pattern cannot handle
    nested braces, so non-trivial if/else-if chains with nested blocks
    may be missed.
    """
    results = []
    stripped = _strip_comments(content)
    # Find "} else if (...) { ... }" NOT followed by "} else {"
    pattern = re.compile(
        r'\}\s*else\s+if\s*\([^)]*\)\s*\{[^}]*\}\s*(?!\s*else\b)',
        re.DOTALL,
    )
    for m in pattern.finditer(stripped):
        # Verify this is truly the end of the chain (no else after)
        after = stripped[m.end():m.end() + 20].strip()
        if not after.startswith('else'):
            results.append(CheckResult(
                file=filename,
                line=_find_line(stripped, m.start()),
                severity="warning",
                check_id="MISRA-15.7",
                message="if/else-if chain not terminated with final else",
                suggestion="Add a final else clause",
            ))
    return results


def check_unused_parameters(content: str, filename: str) -> list[CheckResult]:
    """MISRA-2.7: Function parameters should be referenced in body.

    Regex approximation. Limitation: simple word-boundary search may miss
    usage through pointer arithmetic or struct member access patterns.
    """
    results = []
    for func in _extract_functions(content):
        if not func["params"].strip() or func["params"].strip() == "void":
            continue
        # Parse parameter names
        for param_decl in func["params"].split(','):
            param_decl = param_decl.strip()
            if not param_decl:
                continue
            # Extract the parameter name (last word, strip * and [])
            tokens = re.findall(r'\w+', param_decl)
            if len(tokens) < 2:
                continue
            param_name = tokens[-1]
            # Check if it appears in the body
            if not re.search(r'\b' + re.escape(param_name) + r'\b', func["body"]):
                results.append(CheckResult(
                    file=filename,
                    line=func["line"],
                    severity="info",
                    check_id="MISRA-2.7",
                    message=f"Parameter '{param_name}' in '{func['name']}' not referenced",
                    suggestion=f"Remove or use parameter '{param_name}'",
                ))
    return results


def check_extern_has_definition(content: str, filename: str) -> list[CheckResult]:
    """MISRA-8.4: extern declarations should have matching definitions.

    Regex approximation. Checks single-file scope only.
    Limitation: cannot verify cross-file linkage; misses extern
    definitions split across translation units.
    """
    results = []
    stripped = _strip_comments(content)
    # Only check .c files — extern in .h is expected
    if not filename.endswith('.c'):
        return results
    extern_pattern = re.compile(r'\bextern\s+.*?\b(\w+)\s*[;\[\(]', re.MULTILINE)
    for m in extern_pattern.finditer(stripped):
        name = m.group(1)
        # Check if the name appears outside extern lines
        lines_with_name = []
        for i, line in enumerate(stripped.split('\n'), 1):
            if name in line and 'extern' not in line:
                lines_with_name.append(i)
        if not lines_with_name:
            results.append(CheckResult(
                file=filename,
                line=_find_line(stripped, m.start()),
                severity="warning",
                check_id="MISRA-8.4",
                message=f"extern '{name}' has no visible definition in this file",
            ))
    return results


def check_loop_var_modification(content: str, filename: str) -> list[CheckResult]:
    """MISRA-14.2: Loop variable should not be modified in loop body.

    Regex approximation. Only parses for(type var = ...; ...; var++) style.
    Limitation: breaks on multi-variable loops, complex increment
    expressions, or loops where the variable name collides with other
    identifiers.
    """
    results = []
    stripped = _strip_comments(content)
    # Find for loops: for (type var = ...; ...; var++)
    for_pattern = re.compile(
        r'\bfor\s*\(\s*(?:\w+\s+)?(\w+)\s*=[^;]*;[^;]*;[^)]*\)\s*\{',
    )
    for m in for_pattern.finditer(stripped):
        loop_var = m.group(1)
        # Find matching brace for loop body
        brace_count = 1
        idx = m.end()
        while idx < len(stripped) and brace_count > 0:
            if stripped[idx] == '{':
                brace_count += 1
            elif stripped[idx] == '}':
                brace_count -= 1
            idx += 1
        body = stripped[m.end():idx - 1]
        # Check for assignment to loop variable in body (not the increment)
        assign_pattern = re.compile(
            r'\b' + re.escape(loop_var) + r'\s*(?:=(?!=)|[+\-*/%]=|\+\+|--)',
        )
        if assign_pattern.search(body):
            results.append(CheckResult(
                file=filename,
                line=_find_line(stripped, m.start()),
                severity="warning",
                check_id="MISRA-14.2",
                message=f"Loop variable '{loop_var}' may be modified in loop body",
            ))
    return results


def check_no_stdio(content: str, filename: str, exceptions: list[str] | None = None) -> list[CheckResult]:
    """MISRA-21.6: No stdio functions unless exceptions apply.

    Regex approximation. Catches direct calls to printf/fprintf/scanf/puts.
    Limitation: misses calls through macros or wrappers; the exception
    mechanism only checks for string presence (e.g. SIMULATION_MODE).
    """
    if exceptions:
        for exc in exceptions:
            if exc in content:
                return []
    results = []
    stripped = _strip_comments(content)
    for pattern in (r'\bprintf\s*\(', r'\bfprintf\s*\(', r'\bscanf\s*\(', r'\bputs\s*\('):
        for m in re.finditer(pattern, stripped):
            func_name = m.group().split('(')[0].strip()
            results.append(CheckResult(
                file=filename,
                line=_find_line(stripped, m.start()),
                severity="warning",
                check_id="MISRA-21.6",
                message=f"stdio function '{func_name}' used",
                suggestion="Remove stdio calls for embedded targets",
            ))
    return results


def check_const_pointer_params(content: str, filename: str) -> list[CheckResult]:
    """MISRA-8.13: Pointer parameters that could be const.

    Regex approximation. Checks for direct array assignment or
    dereference assignment only. Limitation: misses modification through
    passed-to-function, pointer arithmetic, or cast patterns.
    """
    results = []
    for func in _extract_functions(content):
        if not func["params"].strip() or func["params"].strip() == "void":
            continue
        for param_decl in func["params"].split(','):
            param_decl = param_decl.strip()
            if '*' not in param_decl or 'const' in param_decl:
                continue
            tokens = re.findall(r'\w+', param_decl)
            if len(tokens) < 2:
                continue
            param_name = tokens[-1]
            # Check if the pointer target is ever assigned to
            assign_pat = re.compile(
                r'\b' + re.escape(param_name) + r'\s*\[[^\]]*\]\s*='
                r'|'
                r'\*\s*' + re.escape(param_name) + r'\s*=',
            )
            if not assign_pat.search(func["body"]):
                results.append(CheckResult(
                    file=filename,
                    line=func["line"],
                    severity="info",
                    check_id="MISRA-8.13",
                    message=f"Parameter '{param_name}' in '{func['name']}' could be const",
                    suggestion="Add const qualifier",
                ))
    return results


def run_misra_checks(
    content: str,
    filename: str,
    rules_config: dict[str, Any] | None = None,
) -> list[CheckResult]:
    """Run all enabled MISRA checks on a single file.

    Args:
        content: File content string.
        filename: Filename for reporting.
        rules_config: Optional rules configuration dict.

    Returns:
        List of CheckResult findings.
    """
    if rules_config is None:
        rules_config = {}

    rule_settings = rules_config.get("rules", {})
    results: list[CheckResult] = []

    checks = [
        ("MISRA-21.3", lambda: check_no_dynamic_memory(content, filename)),
        ("MISRA-17.2", lambda: check_no_recursion(content, filename)),
        ("MISRA-8.1", lambda: check_explicit_return_type(content, filename)),
        ("MISRA-10.1", lambda: check_implicit_type_conversion(content, filename)),
        ("MISRA-15.7", lambda: check_else_termination(content, filename)),
        ("MISRA-2.7", lambda: check_unused_parameters(content, filename)),
        ("MISRA-8.4", lambda: check_extern_has_definition(content, filename)),
        ("MISRA-14.2", lambda: check_loop_var_modification(content, filename)),
        ("MISRA-21.6", lambda: check_no_stdio(
            content, filename,
            rule_settings.get("MISRA-21.6", {}).get("exceptions"),
        )),
        ("MISRA-8.13", lambda: check_const_pointer_params(content, filename)),
    ]

    for check_id, check_fn in checks:
        settings = rule_settings.get(check_id, {})
        if not settings.get("enabled", True):
            continue
        check_results = check_fn()
        # Override severity if configured
        configured_severity = settings.get("severity")
        if configured_severity:
            for r in check_results:
                r.severity = configured_severity
        results.extend(check_results)

    return results
