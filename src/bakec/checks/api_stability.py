"""API stability checks for generated header files.

Compares public API surface between target and baseline .h files to
detect breaking changes, compatibility issues, and guard modifications.
"""

import re
import logging
from pathlib import Path

from bakec.checks.runner import CheckResult

logger = logging.getLogger("bakec")


def _get_h_files(directory: Path) -> dict[str, str]:
    """Read all .h files in a directory into a name->content dict."""
    files = {}
    for p in sorted(directory.iterdir()):
        if p.is_file() and p.suffix == '.h':
            files[p.name] = p.read_text(encoding='utf-8')
    return files


def _extract_public_functions(content: str) -> dict[str, str]:
    """Extract non-static function declarations from a header file.

    Returns dict of function name -> full declaration string.
    """
    funcs = {}
    pattern = re.compile(
        r'^(?!.*\bstatic\b)\s*(?:extern\s+)?(\w[\w\s\*]*?)\s+(\w+)\s*\(([^)]*)\)\s*;',
        re.MULTILINE,
    )
    for m in pattern.finditer(content):
        ret = m.group(1).strip()
        name = m.group(2)
        params = m.group(3).strip()
        if name in ('if', 'while', 'for', 'switch', 'return'):
            continue
        funcs[name] = f"{ret} {name}({params})"
    return funcs


def _extract_typedefs(content: str) -> dict[str, str]:
    """Extract typedef name -> full typedef line."""
    typedefs = {}
    # Match simple typedefs (not struct typedefs)
    pattern = re.compile(r'typedef\s+(?!struct\b)(\w[\w\s\*]*?)\s+(\w+)\s*;')
    for m in pattern.finditer(content):
        name = m.group(2)
        typedefs[name] = m.group(0).strip()
    return typedefs


def _extract_structs(content: str) -> dict[str, list[str]]:
    """Extract struct name -> list of 'type name' member strings."""
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


def _extract_header_guard(content: str) -> str | None:
    """Extract the header guard name from #ifndef."""
    m = re.search(r'#ifndef\s+(\w+)', content)
    return m.group(1) if m else None


def run_api_stability_checks(
    target_dir: Path,
    baseline_dir: Path,
) -> list[CheckResult]:
    """Run API stability checks comparing target headers against baseline.

    Only processes .h files. Detects breaking changes (removed functions,
    structs, typedefs), compatibility issues (changed signatures, added
    struct fields), and guard modifications.

    Args:
        target_dir: Directory with current generated header files.
        baseline_dir: Directory with baseline generated header files.

    Returns:
        List of CheckResult findings.
    """
    results: list[CheckResult] = []

    target_files = _get_h_files(target_dir)
    baseline_files = _get_h_files(baseline_dir)

    common = sorted(set(target_files) & set(baseline_files))

    for name in common:
        t_content = target_files[name]
        b_content = baseline_files[name]

        # --- Functions ---
        t_funcs = _extract_public_functions(t_content)
        b_funcs = _extract_public_functions(b_content)

        # API-BREAK-FUNC: public function removed
        for fname in sorted(set(b_funcs) - set(t_funcs)):
            results.append(CheckResult(
                file=name, line=None, severity="error",
                check_id="API-BREAK-FUNC",
                message=f"Public function '{fname}' removed from API",
                suggestion="Restore function or provide migration path",
            ))

        # API-COMPAT-FUNC: signature changed
        for fname in sorted(set(t_funcs) & set(b_funcs)):
            if t_funcs[fname] != b_funcs[fname]:
                results.append(CheckResult(
                    file=name, line=None, severity="warning",
                    check_id="API-COMPAT-FUNC",
                    message=f"Signature changed for '{fname}': "
                            f"'{b_funcs[fname]}' -> '{t_funcs[fname]}'",
                ))

        # --- Structs ---
        t_structs = _extract_structs(t_content)
        b_structs = _extract_structs(b_content)

        # API-BREAK-STRUCT: struct removed or field removed
        for sname in sorted(set(b_structs) - set(t_structs)):
            results.append(CheckResult(
                file=name, line=None, severity="error",
                check_id="API-BREAK-STRUCT",
                message=f"Struct '{sname}' removed from API",
            ))

        for sname in sorted(set(t_structs) & set(b_structs)):
            removed = [m for m in b_structs[sname] if m not in t_structs[sname]]
            added = [m for m in t_structs[sname] if m not in b_structs[sname]]
            if removed:
                results.append(CheckResult(
                    file=name, line=None, severity="error",
                    check_id="API-BREAK-STRUCT",
                    message=f"Struct '{sname}': fields removed: {removed}",
                ))
            if added:
                results.append(CheckResult(
                    file=name, line=None, severity="info",
                    check_id="API-COMPAT-STRUCT",
                    message=f"Struct '{sname}': fields added: {added}",
                ))

        # --- Typedefs ---
        t_types = _extract_typedefs(t_content)
        b_types = _extract_typedefs(b_content)

        # API-BREAK-TYPE: typedef removed
        for tname in sorted(set(b_types) - set(t_types)):
            results.append(CheckResult(
                file=name, line=None, severity="error",
                check_id="API-BREAK-TYPE",
                message=f"Typedef '{tname}' removed from API",
            ))

        # --- Header guard ---
        t_guard = _extract_header_guard(t_content)
        b_guard = _extract_header_guard(b_content)
        if t_guard and b_guard and t_guard != b_guard:
            results.append(CheckResult(
                file=name, line=None, severity="warning",
                check_id="API-COMPAT-GUARD",
                message=f"Header guard changed: '{b_guard}' -> '{t_guard}'",
            ))

    return results
