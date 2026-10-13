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
    executed: list[str] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)
    files_checked: int = 0

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
    platforms_dir: Path | None = None,
    project_root: Path | None = None,
) -> CheckReport:
    """Run all enabled checks against target directory.

    Args:
        target_dir: Directory containing generated .c and .h files.
        baseline_dir: Optional baseline directory for regression/API checks.
        rules: Optional rules dict. Defaults enable all applicable checks.
        platforms_dir: Directory containing platform YAML files for constraint checks.
        project_root: Optional project root for resolving source paths
            in traceability hash verification.

    Returns:
        CheckReport with all findings.
    """
    from bakec.checks.misra import run_misra_checks
    from bakec.checks.traceability import run_traceability_checks
    from bakec.checks.safety import run_safety_checks
    from bakec.checks.regression import run_regression_checks
    from bakec.checks.api_stability import run_api_stability_checks
    from bakec.checks.platform_constraints import run_platform_constraint_checks

    if rules is None:
        rules = {}

    report = CheckReport(
        target_dir=str(target_dir),
        baseline_dir=str(baseline_dir) if baseline_dir else None,
    )

    if not target_dir.is_dir():
        report.results.append(CheckResult(str(target_dir), None, "error", "VALIDATE-TARGET",
                                          "Target must be an existing directory"))
        return report
    c_h_files = sorted(
        p for p in target_dir.iterdir()
        if p.is_file() and p.suffix in (".c", ".h")
    )
    if not c_h_files:
        report.results.append(CheckResult(str(target_dir), None, "error", "VALIDATE-EMPTY",
                                          "No relevant .c or .h files to validate"))
        return report
    if baseline_dir is not None:
        if (not baseline_dir.is_dir()
                or not any(p.is_file() and p.suffix in (".c", ".h")
                           for p in baseline_dir.iterdir())):
            report.results.append(CheckResult(str(baseline_dir), None, "error", "VALIDATE-BASELINE",
                                              "Baseline must be a directory containing .c or .h files"))
            return report
        if baseline_dir.resolve() == target_dir.resolve():
            report.results.append(CheckResult(str(baseline_dir), None, "error", "VALIDATE-BASELINE",
                                              "Baseline must be independent of the target directory"))
            return report

    for category in ("misra", "traceability", "safety", "platform_constraints",
                     "regression", "api_stability"):
        if not rules.get(category, {}).get("enabled", True):
            report.skipped[category] = "disabled by configuration"
        elif category in ("regression", "api_stability") and baseline_dir is None:
            report.skipped[category] = "no baseline supplied"
        elif category == "platform_constraints" and platforms_dir is None:
            report.skipped[category] = "no platforms directory supplied"
        else:
            report.executed.append(category)
    report.files_checked = len(c_h_files)

    for filepath in c_h_files:
        content = filepath.read_text(encoding="utf-8")
        filename = filepath.name

        misra_rules = rules.get("misra", {})
        if misra_rules.get("enabled", True):
            report.results.extend(run_misra_checks(content, filename, misra_rules))

        trace_rules = rules.get("traceability", {})
        if trace_rules.get("enabled", True):
            report.results.extend(
                run_traceability_checks(content, filename, project_root)
            )

        safety_rules = rules.get("safety", {})
        if safety_rules.get("enabled", True):
            report.results.extend(run_safety_checks(content, filename, safety_rules))

        if platforms_dir:
            plat_rules = rules.get("platform_constraints", {})
            if plat_rules.get("enabled", True):
                report.results.extend(
                    run_platform_constraint_checks(
                        content, filename, platforms_dir, plat_rules
                    )
                )

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
