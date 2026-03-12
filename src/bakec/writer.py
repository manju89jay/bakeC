"""Write generated files to the output directory."""

import logging
from pathlib import Path

logger = logging.getLogger("bakec")


def write_generated_files(
    files: dict[str, str], output_dir: Path
) -> list[tuple[str, int]]:
    """Write generated file contents to disk.

    Args:
        files: Dictionary mapping filename to content string.
        output_dir: Directory to write files into. Created if not exists.

    Returns:
        List of (filename, line_count) tuples in insertion order.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, int]] = []

    for filename, content in files.items():
        filepath = output_dir / filename
        filepath.write_text(content, encoding="utf-8")
        line_count = content.count("\n")
        results.append((filename, line_count))
        logger.info("Wrote %s (%d lines)", filepath, line_count)

    return results
