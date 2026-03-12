"""Quality checks on generated C code."""

import sys
from pathlib import Path

FORBIDDEN_PATTERNS = ["malloc", "calloc", "realloc", "free(", "new ", "delete "]


def check_directory(directory: Path) -> int:
    violations = 0
    c_files = list(directory.rglob("*.c")) + list(directory.rglob("*.h"))

    if not c_files:
        print(f"  No generated files found in {directory}")
        return 0

    for filepath in c_files:
        content = filepath.read_text()
        violations += _check_forbidden_patterns(filepath, content)
        violations += _check_header_guards(filepath, content)
        violations += _check_traceability(filepath, content)

    return violations


def _check_forbidden_patterns(filepath: Path, content: str) -> int:
    violations = 0
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in content:
            print(f"  VIOLATION: {filepath.name} contains '{pattern}'")
            violations += 1
    return violations


def _check_header_guards(filepath: Path, content: str) -> int:
    if filepath.suffix != ".h":
        return 0
    if "#ifndef" not in content or "#define" not in content:
        print(f"  VIOLATION: {filepath.name} missing header guards")
        return 1
    return 0


def _check_traceability(filepath: Path, content: str) -> int:
    if filepath.suffix != ".c":
        return 0
    if "@trace" not in content:
        print(f"  WARNING: {filepath.name} has no @trace tags")
        return 1
    return 0


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: check_generated.py <directory>")
        sys.exit(1)

    directory = Path(sys.argv[1])
    if not directory.exists():
        print(f"Directory not found: {directory}")
        sys.exit(1)

    total_violations = 0
    for subdir in sorted(directory.iterdir()):
        if subdir.is_dir():
            print(f"Checking {subdir}/...")
            total_violations += check_directory(subdir)

    if total_violations > 0:
        print(f"\n{total_violations} violation(s) found.")
        sys.exit(1)
    else:
        print("\nAll quality checks passed.")


if __name__ == "__main__":
    main()
