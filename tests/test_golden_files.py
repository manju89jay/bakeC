"""Golden-file regression tests.

Regenerates all 9 (model x platform) combinations and compares against
the committed files in generated/. Timestamp and hash lines are excluded
from comparison since they change on every run.
"""

import difflib
import re
from pathlib import Path

import pytest

from bakec.parser import parse_model, parse_platform
from bakec.engine import CodegenEngine
from bakec.writer import write_generated_files

MODELS = [
    "models/lung_mnarx.yaml",
    "models/pid_controller.yaml",
    "models/lookup_table_1d.yaml",
]
PLATFORMS = [
    "models/../platforms/desktop.yaml",
    "models/../platforms/cortex_m4.yaml",
    "models/../platforms/aurix_tc397.yaml",
]
PLATFORM_DIRS = {
    "Desktop Simulation": "desktop",
    "ARM Cortex-M4": "cortex_m4",
    "AURIX TC397": "aurix_tc397",
}

# Lines matching these patterns are excluded from comparison
_SKIP_RE = re.compile(r'^\s*\*\s*Date:|sha256:')


def _strip_volatile_lines(text: str) -> list[str]:
    """Remove lines that change on every generation (timestamps, hashes)."""
    return [line for line in text.splitlines(keepends=True)
            if not _SKIP_RE.search(line)]


def _generate_combo(model_path: str, platform_path: str) -> dict[str, str]:
    """Generate code for one model/platform combo, return {filename: content}."""
    model = parse_model(Path(model_path))
    platform = parse_platform(Path(platform_path))
    engine = CodegenEngine(
        model=model,
        platform=platform,
        model_path=model_path,
        platform_path=platform_path,
    )
    return engine.render_all()


def _combos():
    """Yield (model_path, platform_path, platform_dir) for parametrize."""
    for model in MODELS:
        for platform in PLATFORMS:
            plat_data = parse_platform(Path(platform))
            plat_name = plat_data["platform"]["name"]
            plat_dir = PLATFORM_DIRS[plat_name]
            yield model, platform, plat_dir


@pytest.mark.parametrize("model_path,platform_path,platform_dir", list(_combos()))
def test_golden_file_match(model_path, platform_path, platform_dir):
    """Verify regenerated output matches committed golden files."""
    generated = _generate_combo(model_path, platform_path)
    golden_dir = Path("generated") / platform_dir

    for filename, new_content in generated.items():
        golden_path = golden_dir / filename
        assert golden_path.exists(), f"Golden file missing: {golden_path}"

        golden_content = golden_path.read_text(encoding="utf-8")
        golden_lines = _strip_volatile_lines(golden_content)
        new_lines = _strip_volatile_lines(new_content)

        if golden_lines != new_lines:
            diff = difflib.unified_diff(
                golden_lines, new_lines,
                fromfile=f"golden/{platform_dir}/{filename}",
                tofile=f"regenerated/{filename}",
                lineterm="",
            )
            diff_text = "\n".join(diff)
            pytest.fail(
                f"Golden file mismatch: {golden_path}\n{diff_text}"
            )
