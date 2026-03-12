"""Orchestrator for generated code validation checks."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("bakec")


@dataclass
class CheckResult:
    """Single check finding."""

    file: str
    line: int | None
    severity: str  # "error" | "warning" | "info"
    check_id: str
    message: str
    suggestion: str | None = None


@dataclass
class CheckReport:
    """Aggregated results from all checks."""

    target_dir: str
    baseline_dir: str | None
    results: list[CheckResult] = field(default_factory=list)

    @property
    def errors(self) -> int:
        """Count of error-severity results."""
        return sum(1 for r in self.results if r.severity == "error")

    @property
    def warnings(self) -> int:
        """Count of warning-severity results."""
        return sum(1 for r in self.results if r.severity == "warning")

    @property
    def infos(self) -> int:
        """Count of info-severity results."""
        return sum(1 for r in self.results if r.severity == "info")


def _load_rules(rules_path: Path | None) -> dict[str, Any]:
    """Load rules YAML, returning empty dict on missing file."""
    if rules_path and rules_path.exists():
        with open(rules_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def run_all_checks(
    target_dir: Path,
    baseline_dir: Path | None = None,
    rules: dict[str, Any] | None = None,
) -> CheckReport:
    """Run all enabled checks against target directory.

    Args:
        target_dir: Directory containing generated .c and .h files.
        baseline_dir: Optional baseline directory for regression/API checks.
        rules: Optional rules dict. If None, all checks run with defaults.

    Returns:
        CheckReport with all findings.
    """
    from bakec.checks.misra import run_misra_checks
    from bakec.checks.traceability import run_traceability_checks
    from bakec.checks.safety import run_safety_checks
    from bakec.checks.regression import run_regression_checks
    from bakec.checks.api_stability import run_api_stability_checks

    if rules is None:
        rules = {}

    report = CheckReport(
        target_dir=str(target_dir),
        baseline_dir=str(baseline_dir) if baseline_dir else None,
    )

    c_h_files = sorted(
        p for p in target_dir.iterdir()
        if p.is_file() and p.suffix in (".c", ".h")
    )

    for filepath in c_h_files:
        content = filepath.read_text(encoding="utf-8")
        filename = filepath.name

        misra_rules = rules.get("misra", {})
        if misra_rules.get("enabled", True):
            report.results.extend(run_misra_checks(content, filename, misra_rules))

        trace_rules = rules.get("traceability", {})
        if trace_rules.get("enabled", True):
            report.results.extend(run_traceability_checks(content, filename))

        safety_rules = rules.get("safety", {})
        if safety_rules.get("enabled", True):
            report.results.extend(run_safety_checks(content, filename, safety_rules))

    if baseline_dir and baseline_dir.is_dir():
        reg_rules = rules.get("regression", {})
        if reg_rules.get("enabled", True):
            report.results.extend(
                run_regression_checks(target_dir, baseline_dir, reg_rules)
            )

        api_rules = rules.get("api_stability", {})
        if api_rules.get("enabled", True):
            report.results.extend(
                run_api_stability_checks(target_dir, baseline_dir)
            )

    logger.info(
        "Checks complete: %d errors, %d warnings, %d info",
        report.errors, report.warnings, report.infos,
    )
    return report
