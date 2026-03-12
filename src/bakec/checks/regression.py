"""Regression checks between two versions of generated code.

Compares target and baseline directories for structural and semantic
changes in generated C files.
"""

import re
import logging
from pathlib import Path
from typing import Any

from bakec.checks.runner import CheckResult

logger = logging.getLogger("bakec")


def _get_c_h_files(directory: Path) -> dict[str, str]:
    """Read all .c and .h files in a directory into a name→content dict."""
    files = {}
    for p in sorted(directory.iterdir()):
        if p.is_file() and p.suffix in ('.c', '.h'):
            files[p.name] = p.read_text(encoding='utf-8')
    return files


def _extract_signatures(content: str) -> dict[str, str]:
    """Extract function name → full signature string from C source."""
    sigs = {}
    pattern = re.compile(
        r'^((?:static\s+|extern\s+|const\s+)*\w[\w\s\*]*?)\s+(\w+)\s*\(([^)]*)\)\s*[{;]',
        re.MULTILINE,
    )
    for m in pattern.finditer(content):
        ret = m.group(1).strip()
        name = m.group(2)
        params = m.group(3).strip()
        if name in ('if', 'while', 'for', 'switch', 'return'):
            continue
        sigs[name] = f"{ret} {name}({params})"
    return sigs


def _extract_structs(content: str) -> dict[str, list[str]]:
    """Extract struct name → list of 'type name' member strings."""
    structs = {}
    pattern = re.compile(r'typedef\s+struct\s*\{([^}]*)\}\s*(\w+)\s*;', re.DOTALL)
    for m in pattern.finditer(content):
        body = m.group(1)
        name = m.group(2)
        members = []
        for line in body.strip().split('\n'):
            line = line.strip().rstrip(';').strip()
            if line and not line.startswith('/*') and not line.startswith('//'):
                members.append(line)
        structs[name] = members
    return structs


def _extract_const_arrays(content: str) -> dict[str, list[str]]:
    """Extract const array name → list of value strings."""
    arrays = {}
    pattern = re.compile(
        r'const\s+\w+\s+(\w+)\s*\[\s*\]\s*=\s*\{([^}]*)\}',
        re.DOTALL,
    )
    for m in pattern.finditer(content):
        name = m.group(1)
        values = [v.strip() for v in m.group(2).split(',') if v.strip()]
        arrays[name] = values
    return arrays


def _extract_includes(content: str) -> list[str]:
    """Extract sorted list of #include directives."""
    return sorted(re.findall(r'#include\s+[<"][^>"]+[>"]', content))


def run_regression_checks(
    target_dir: Path,
    baseline_dir: Path,
    rules_config: dict[str, Any] | None = None,
) -> list[CheckResult]:
    """Run regression checks comparing target against baseline.

    Args:
        target_dir: Directory with current generated files.
        baseline_dir: Directory with baseline generated files.
        rules_config: Optional configuration (line_count_threshold).

    Returns:
        List of CheckResult findings.
    """
    if rules_config is None:
        rules_config = {}

    threshold = rules_config.get("line_count_threshold", 0.20)
    results: list[CheckResult] = []

    target_files = _get_c_h_files(target_dir)
    baseline_files = _get_c_h_files(baseline_dir)

    target_names = set(target_files.keys())
    baseline_names = set(baseline_files.keys())

    # REG-FILE-ADD
    for name in sorted(target_names - baseline_names):
        results.append(CheckResult(
            file=name, line=None, severity="info",
            check_id="REG-FILE-ADD",
            message=f"New file '{name}' not in baseline",
        ))

    # REG-FILE-DEL
    for name in sorted(baseline_names - target_names):
        results.append(CheckResult(
            file=name, line=None, severity="error",
            check_id="REG-FILE-DEL",
            message=f"File '{name}' removed (present in baseline)",
        ))

    # Compare matching files
    common = sorted(target_names & baseline_names)
    for name in common:
        t_content = target_files[name]
        b_content = baseline_files[name]

        t_sigs = _extract_signatures(t_content)
        b_sigs = _extract_signatures(b_content)

        # REG-FUNC-ADD
        for fname in sorted(set(t_sigs) - set(b_sigs)):
            results.append(CheckResult(
                file=name, line=None, severity="info",
                check_id="REG-FUNC-ADD",
                message=f"New function '{fname}'",
            ))

        # REG-FUNC-DEL
        for fname in sorted(set(b_sigs) - set(t_sigs)):
            results.append(CheckResult(
                file=name, line=None, severity="error",
                check_id="REG-FUNC-DEL",
                message=f"Function '{fname}' removed",
            ))

        # REG-FUNC-SIG
        for fname in sorted(set(t_sigs) & set(b_sigs)):
            if t_sigs[fname] != b_sigs[fname]:
                results.append(CheckResult(
                    file=name, line=None, severity="error",
                    check_id="REG-FUNC-SIG",
                    message=f"Signature changed for '{fname}': "
                            f"'{b_sigs[fname]}' → '{t_sigs[fname]}'",
                ))

        # REG-STRUCT
        t_structs = _extract_structs(t_content)
        b_structs = _extract_structs(b_content)
        for sname in sorted(set(t_structs) & set(b_structs)):
            t_members = t_structs[sname]
            b_members = b_structs[sname]
            removed = [m for m in b_members if m not in t_members]
            added = [m for m in t_members if m not in b_members]
            if removed:
                results.append(CheckResult(
                    file=name, line=None, severity="error",
                    check_id="REG-STRUCT",
                    message=f"Struct '{sname}': members removed: {removed}",
                ))
            if added:
                results.append(CheckResult(
                    file=name, line=None, severity="warning",
                    check_id="REG-STRUCT",
                    message=f"Struct '{sname}': members added: {added}",
                ))

        # REG-PARAM
        t_arrays = _extract_const_arrays(t_content)
        b_arrays = _extract_const_arrays(b_content)
        for aname in sorted(set(t_arrays) & set(b_arrays)):
            t_vals = t_arrays[aname]
            b_vals = b_arrays[aname]
            if t_vals != b_vals:
                # Report specific differences
                for i, (tv, bv) in enumerate(zip(t_vals, b_vals)):
                    if tv != bv:
                        results.append(CheckResult(
                            file=name, line=None, severity="warning",
                            check_id="REG-PARAM",
                            message=f"{aname}[{i}]: {bv} → {tv}",
                        ))
                if len(t_vals) != len(b_vals):
                    results.append(CheckResult(
                        file=name, line=None, severity="warning",
                        check_id="REG-PARAM",
                        message=f"{aname} length changed: {len(b_vals)} → {len(t_vals)}",
                    ))

        # REG-INCLUDE
        t_includes = _extract_includes(t_content)
        b_includes = _extract_includes(b_content)
        if t_includes != b_includes:
            added_inc = set(t_includes) - set(b_includes)
            removed_inc = set(b_includes) - set(t_includes)
            parts = []
            if added_inc:
                parts.append(f"added {added_inc}")
            if removed_inc:
                parts.append(f"removed {removed_inc}")
            results.append(CheckResult(
                file=name, line=None, severity="warning",
                check_id="REG-INCLUDE",
                message=f"Include list changed: {', '.join(parts)}",
            ))

        # REG-LINECOUNT
        t_lines = t_content.count('\n')
        b_lines = b_content.count('\n')
        if b_lines > 0:
            change = abs(t_lines - b_lines) / b_lines
            if change > threshold:
                direction = "+" if t_lines > b_lines else "-"
                results.append(CheckResult(
                    file=name, line=None, severity="info",
                    check_id="REG-LINECOUNT",
                    message=f"{b_lines} → {t_lines} lines ({direction}{change:.1%})",
                ))

    return results
