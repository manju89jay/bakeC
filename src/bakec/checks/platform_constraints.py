"""Platform constraint verification for generated code.

Parses the platform path from each file's provenance banner, loads the
platform YAML, and verifies that generated code respects the declared
constraints (types, I/O restrictions, literal suffixes).
"""

import re
import logging
from pathlib import Path
from typing import Any

import yaml

from bakec.checks.runner import CheckResult

logger = logging.getLogger("bakec")

_BANNER_PLATFORM_RE = re.compile(
    r"Platform:\s+([\w/\\._-]+\.yaml)\s+\[sha256:"
)
_COMMENT_RE = re.compile(r'//.*?$|/\*.*?\*/', re.MULTILINE | re.DOTALL)


def _extract_platform_path(content: str) -> str | None:
    """Extract platform YAML path from the file's provenance banner."""
    m = _BANNER_PLATFORM_RE.search(content)
    return m.group(1) if m else None


def _load_platform(platform_path: str, platforms_dir: Path) -> dict[str, Any] | None:
    """Load platform YAML relative to the platforms directory.

    Args:
        platform_path: Relative path from banner (e.g., 'platforms/cortex_m4.yaml').
        platforms_dir: Root directory to resolve relative paths against.

    Returns:
        Platform dict or None if file not found.
    """
    # Banner contains e.g. "platforms/cortex_m4.yaml" — resolve from project root
    full_path = platforms_dir.parent / platform_path
    if not full_path.exists():
        # Try resolving relative to platforms_dir directly
        full_path = platforms_dir / Path(platform_path).name
    if not full_path.exists():
        logger.warning("Platform file not found: %s", platform_path)
        return None
    with open(full_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("platform") if data else None


def _strip_comments(content: str) -> str:
    """Remove C comments from source text."""
    return _COMMENT_RE.sub('', content)


def _find_line(content: str, pos: int) -> int:
    """Return 1-based line number for a character position."""
    return content[:pos].count('\n') + 1


def check_real_t_typedef(
    content: str, filename: str, platform: dict[str, Any]
) -> list[CheckResult]:
    """PLAT-001: Verify real_T typedef matches platform type declaration."""
    if not filename.endswith("_types.h"):
        return []

    expected_type = platform.get("types", {}).get("real_T")
    if not expected_type:
        return []

    typedef_re = re.compile(r"typedef\s+(\w+)\s+real_T\s*;")
    m = typedef_re.search(content)
    if not m:
        return [CheckResult(
            file=filename,
            line=1,
            severity="error",
            check_id="PLAT-001",
            message="No 'typedef ... real_T' found",
            suggestion=f"Add 'typedef {expected_type} real_T;'",
        )]

    actual_type = m.group(1)
    if actual_type != expected_type:
        return [CheckResult(
            file=filename,
            line=_find_line(content, m.start()),
            severity="error",
            check_id="PLAT-001",
            message=f"real_T is '{actual_type}', expected '{expected_type}'",
            suggestion=f"Change typedef to '{expected_type}'",
        )]
    return []


def check_literal_suffix(
    content: str, filename: str, platform: dict[str, Any]
) -> list[CheckResult]:
    """PLAT-002: Verify float literal suffixes match platform type_suffix."""
    if not filename.endswith(".c"):
        return []

    expected_suffix = platform.get("type_suffix", "")
    stripped = _strip_comments(content)

    results = []
    # Match float literals: digits.digits optionally followed by f
    literal_re = re.compile(r'(?<!\w)(\d+\.\d+)(f?)\b')

    for m in literal_re.finditer(stripped):
        actual_suffix = m.group(2)
        if expected_suffix == "f" and actual_suffix != "f":
            results.append(CheckResult(
                file=filename,
                line=_find_line(stripped, m.start()),
                severity="error",
                check_id="PLAT-002",
                message=f"Literal '{m.group(0)}' missing 'f' suffix",
                suggestion=f"Use '{m.group(1)}f' for single-precision platform",
            ))
        elif expected_suffix == "" and actual_suffix == "f":
            results.append(CheckResult(
                file=filename,
                line=_find_line(stripped, m.start()),
                severity="error",
                check_id="PLAT-002",
                message=f"Literal '{m.group(0)}' has unexpected 'f' suffix",
                suggestion=f"Use '{m.group(1)}' for double-precision platform",
            ))
    return results


def check_no_printf(
    content: str, filename: str, platform: dict[str, Any]
) -> list[CheckResult]:
    """PLAT-003: No stdio when printf_allowed is false."""
    constraints = platform.get("constraints", {})
    if constraints.get("printf_allowed", True):
        return []

    results = []
    stripped = _strip_comments(content)

    if "#include <stdio.h>" in stripped:
        pos = stripped.index("#include <stdio.h>")
        results.append(CheckResult(
            file=filename,
            line=_find_line(stripped, pos),
            severity="error",
            check_id="PLAT-003",
            message="stdio.h included on platform with printf_allowed=false",
            suggestion="Remove #include <stdio.h> for embedded target",
        ))

    for pattern in (r'\bprintf\s*\(', r'\bfprintf\s*\(', r'\bputs\s*\('):
        for m in re.finditer(pattern, stripped):
            func_name = m.group().rstrip('( ')
            results.append(CheckResult(
                file=filename,
                line=_find_line(stripped, m.start()),
                severity="error",
                check_id="PLAT-003",
                message=f"'{func_name}' used on platform with printf_allowed=false",
                suggestion="Remove stdio calls for embedded target",
            ))
    return results


def check_no_assert(
    content: str, filename: str, platform: dict[str, Any]
) -> list[CheckResult]:
    """PLAT-004: No assert.h when assertions is false."""
    constraints = platform.get("constraints", {})
    if constraints.get("assertions", True):
        return []

    results = []
    stripped = _strip_comments(content)

    if "#include <assert.h>" in stripped:
        pos = stripped.index("#include <assert.h>")
        results.append(CheckResult(
            file=filename,
            line=_find_line(stripped, pos),
            severity="error",
            check_id="PLAT-004",
            message="assert.h included on platform with assertions=false",
            suggestion="Remove #include <assert.h> for embedded target",
        ))

    for m in re.finditer(r'\bassert\s*\(', stripped):
        results.append(CheckResult(
            file=filename,
            line=_find_line(stripped, m.start()),
            severity="error",
            check_id="PLAT-004",
            message="assert() used on platform with assertions=false",
            suggestion="Remove assert calls for embedded target",
        ))
    return results


def check_no_stdlib(
    content: str, filename: str, platform: dict[str, Any]
) -> list[CheckResult]:
    """PLAT-005: No stdlib.h when dynamic_memory is false."""
    constraints = platform.get("constraints", {})
    if constraints.get("dynamic_memory", True):
        return []

    stripped = _strip_comments(content)
    if "#include <stdlib.h>" in stripped:
        pos = stripped.index("#include <stdlib.h>")
        return [CheckResult(
            file=filename,
            line=_find_line(stripped, pos),
            severity="error",
            check_id="PLAT-005",
            message="stdlib.h included on platform with dynamic_memory=false",
            suggestion="Remove #include <stdlib.h> for embedded target",
        )]
    return []


def run_platform_constraint_checks(
    content: str,
    filename: str,
    platforms_dir: Path,
    rules_config: dict[str, Any] | None = None,
) -> list[CheckResult]:
    """Run all platform constraint checks on a single file.

    Extracts the platform path from the file banner, loads the platform
    YAML, and runs all PLAT-xxx checks.

    Args:
        content: File content string.
        filename: Filename for reporting.
        platforms_dir: Directory containing platform YAML files.
        rules_config: Optional rules configuration.

    Returns:
        List of CheckResult findings.
    """
    platform_path = _extract_platform_path(content)
    if not platform_path:
        logger.debug("No platform banner in %s, skipping constraint checks", filename)
        return []

    platform = _load_platform(platform_path, platforms_dir)
    if not platform:
        return [CheckResult(
            file=filename,
            line=1,
            severity="warning",
            check_id="PLAT-000",
            message=f"Could not load platform '{platform_path}' for constraint checks",
            suggestion="Ensure platform YAML is accessible via --platforms-dir",
        )]

    results: list[CheckResult] = []
    results.extend(check_real_t_typedef(content, filename, platform))
    results.extend(check_literal_suffix(content, filename, platform))
    results.extend(check_no_printf(content, filename, platform))
    results.extend(check_no_assert(content, filename, platform))
    results.extend(check_no_stdlib(content, filename, platform))
    return results
