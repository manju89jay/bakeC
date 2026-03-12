"""Embedded safety pattern checks for generated code.

Enforces static allocation, no recursion, bounded loops, no function
pointers, typed variables, and no variable-length arrays.
"""

import re
import logging
from typing import Any

from bakec.checks.runner import CheckResult

logger = logging.getLogger("bakec")

_COMMENT_RE = re.compile(r'//.*?$|/\*.*?\*/', re.MULTILINE | re.DOTALL)


def _strip_comments(content: str) -> str:
    """Remove C comments from source text."""
    return _COMMENT_RE.sub('', content)


def _find_line(content: str, pos: int) -> int:
    """Return 1-based line number for a character position."""
    return content[:pos].count('\n') + 1


def check_no_dynamic_memory(content: str, filename: str) -> list[CheckResult]:
    """SAFE-001: No malloc/calloc/realloc/free."""
    results = []
    stripped = _strip_comments(content)
    for pattern in (r'\bmalloc\s*\(', r'\bcalloc\s*\(', r'\brealloc\s*\(', r'\bfree\s*\('):
        for m in re.finditer(pattern, stripped):
            func_name = m.group().rstrip('( ')
            results.append(CheckResult(
                file=filename,
                line=_find_line(stripped, m.start()),
                severity="error",
                check_id="SAFE-001",
                message=f"Dynamic memory function '{func_name}' used",
                suggestion="Use static allocation for embedded targets",
            ))
    return results


def check_no_recursion(content: str, filename: str) -> list[CheckResult]:
    """SAFE-002: No recursive function calls."""
    results = []
    stripped = _strip_comments(content)
    func_pattern = re.compile(
        r'^(\w[\w\s\*]*?)\s+(\w+)\s*\(([^)]*)\)\s*\{',
        re.MULTILINE,
    )
    for m in func_pattern.finditer(stripped):
        name = m.group(2)
        if name in ('if', 'while', 'for', 'switch'):
            continue
        brace_count = 1
        idx = m.end()
        while idx < len(stripped) and brace_count > 0:
            if stripped[idx] == '{':
                brace_count += 1
            elif stripped[idx] == '}':
                brace_count -= 1
            idx += 1
        body = stripped[m.end():idx - 1]
        call_pattern = re.compile(r'\b' + re.escape(name) + r'\s*\(')
        if call_pattern.search(body):
            results.append(CheckResult(
                file=filename,
                line=_find_line(stripped, m.start()),
                severity="error",
                check_id="SAFE-002",
                message=f"Function '{name}' appears recursive",
                suggestion="Refactor to iterative implementation",
            ))
    return results


def check_bounded_loops(content: str, filename: str) -> list[CheckResult]:
    """SAFE-003: Every for/while loop must have a visible bound."""
    results = []
    stripped = _strip_comments(content)

    # Check while loops — condition should contain a comparison or literal
    while_pattern = re.compile(r'\bwhile\s*\(([^)]+)\)')
    for m in while_pattern.finditer(stripped):
        cond = m.group(1).strip()
        if cond == '1' or cond == 'true':
            results.append(CheckResult(
                file=filename,
                line=_find_line(stripped, m.start()),
                severity="warning",
                check_id="SAFE-003",
                message="Unbounded while loop (while(1) or while(true))",
                suggestion="Add explicit loop bound or termination condition",
            ))

    # Check for loops — condition should contain a literal or defined constant
    for_pattern = re.compile(r'\bfor\s*\([^;]*;([^;]*);[^)]*\)')
    for m in for_pattern.finditer(stripped):
        cond = m.group(1).strip()
        if not cond:
            results.append(CheckResult(
                file=filename,
                line=_find_line(stripped, m.start()),
                severity="warning",
                check_id="SAFE-003",
                message="for loop with empty condition (unbounded)",
                suggestion="Add explicit loop bound",
            ))
    return results


def check_no_function_pointers(content: str, filename: str) -> list[CheckResult]:
    """SAFE-004: No function pointers."""
    results = []
    stripped = _strip_comments(content)
    # Match function pointer declarations: (*name) or typedef ... (*name)
    fp_pattern = re.compile(r'\(\s*\*\s*\w+\s*\)\s*\(')
    for m in fp_pattern.finditer(stripped):
        results.append(CheckResult(
            file=filename,
            line=_find_line(stripped, m.start()),
            severity="warning",
            check_id="SAFE-004",
            message="Function pointer detected",
            suggestion="Use direct function calls instead",
        ))
    return results


def check_typed_variables(content: str, filename: str) -> list[CheckResult]:
    """SAFE-005: No raw int/float/double in variable declarations."""
    results = []
    stripped = _strip_comments(content)
    allowed_types = {
        'real_T', 'int32_T', 'uint32_T', 'int16_T', 'uint16_T',
        'int8_T', 'uint8_T', 'void', 'char', 'size_t', 'bool',
    }
    # Match variable declarations at start of line or after semicolon
    # Skip typedef lines, #include, #define, struct/enum definitions
    for i, line in enumerate(stripped.split('\n'), 1):
        trimmed = line.strip()
        if not trimmed or trimmed.startswith('#') or trimmed.startswith('typedef'):
            continue
        if trimmed.startswith('//') or trimmed.startswith('/*') or trimmed.startswith('*'):
            continue
        if trimmed.startswith('struct') or trimmed.startswith('enum'):
            continue
        if trimmed.startswith('extern') or trimmed.startswith('return'):
            continue
        # Check for raw type declarations
        raw_decl = re.match(
            r'(?:static\s+|const\s+)*\b(int|float|double|short|long|unsigned)\b\s+\w+',
            trimmed,
        )
        if raw_decl:
            raw_type = raw_decl.group(1)
            results.append(CheckResult(
                file=filename,
                line=i,
                severity="warning",
                check_id="SAFE-005",
                message=f"Raw type '{raw_type}' used in declaration",
                suggestion=f"Use platform-specific typedef (e.g., real_T, int32_T)",
            ))
    return results


def check_no_vla(content: str, filename: str) -> list[CheckResult]:
    """SAFE-006: No variable-length arrays."""
    results = []
    stripped = _strip_comments(content)
    # Match array declarations where size is a variable (not literal or #define)
    # Pattern: type name[variable] where variable is not a number or UPPER_CASE macro
    vla_pattern = re.compile(
        r'\b\w+\s+(\w+)\s*\[\s*([a-z]\w*)\s*\]',
    )
    for m in vla_pattern.finditer(stripped):
        var_name = m.group(1)
        size_expr = m.group(2)
        # Skip if it looks like array indexing rather than declaration
        # Check context: should be preceded by a type
        pre = stripped[max(0, m.start() - 50):m.start()]
        if re.search(r'\b(?:real_T|int32_T|uint32_T|int16_T|uint16_T|int8_T|uint8_T|int|float|double|char)\s*$', pre):
            results.append(CheckResult(
                file=filename,
                line=_find_line(stripped, m.start()),
                severity="warning",
                check_id="SAFE-006",
                message=f"Possible variable-length array '{var_name}[{size_expr}]'",
                suggestion="Use compile-time constant for array size",
            ))
    return results


def run_safety_checks(
    content: str,
    filename: str,
    rules_config: dict[str, Any] | None = None,
) -> list[CheckResult]:
    """Run all safety checks on a single file.

    Args:
        content: File content string.
        filename: Filename for reporting.
        rules_config: Optional safety rules configuration.

    Returns:
        List of CheckResult findings.
    """
    results: list[CheckResult] = []
    results.extend(check_no_dynamic_memory(content, filename))
    results.extend(check_no_recursion(content, filename))
    results.extend(check_bounded_loops(content, filename))
    if not (rules_config or {}).get("allow_function_pointers", False):
        results.extend(check_no_function_pointers(content, filename))
    results.extend(check_typed_variables(content, filename))
    if not (rules_config or {}).get("allow_vla", False):
        results.extend(check_no_vla(content, filename))
    return results
