"""Validation must distinguish a clean run from absent inputs or skipped work."""
import sys
from unittest.mock import patch

import pytest

from bakec.cli import main, _print_report
from bakec.checks.runner import run_all_checks


def test_empty_target_fails_cli(tmp_path, capsys):
    (tmp_path / "README.txt").write_text("not C")
    with patch.object(sys, "argv", ["bakec", "validate", "--target", str(tmp_path)]):
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert "No relevant .c or .h files" in output
    assert "All checks passed" not in output


@pytest.mark.parametrize("baseline_kind", ["missing", "file", "empty", "irrelevant", "self"])
def test_invalid_baseline_fails(tmp_path, baseline_kind):
    target = tmp_path / "target"
    target.mkdir()
    (target / "api.h").write_text("void step(void);\n")
    baseline = tmp_path / "baseline"
    if baseline_kind == "file":
        baseline.write_text("not a directory")
    elif baseline_kind in ("empty", "irrelevant"):
        baseline.mkdir()
        if baseline_kind == "irrelevant":
            (baseline / "note.txt").write_text("not C")
    elif baseline_kind == "self":
        baseline = target
    report = run_all_checks(target, baseline)
    assert report.errors == 1
    assert report.results[0].check_id == "VALIDATE-BASELINE"
    assert report.executed == []
    with patch.object(sys, "argv", ["bakec", "validate", "--target", str(target),
                                   "--baseline", str(baseline)]):
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 1


def test_omitted_baseline_reports_skips(tmp_path, capsys):
    (tmp_path / "sample.c").write_text("void step(void) {}\n")
    report = run_all_checks(tmp_path)
    assert report.files_checked == 1
    assert report.executed == ["misra", "traceability", "safety"]
    assert report.skipped["regression"] == "no baseline supplied"
    assert report.skipped["api_stability"] == "no baseline supplied"
    _print_report(report)
    output = capsys.readouterr().out
    assert "Skipped regression: no baseline supplied" in output
    assert "Skipped api_stability: no baseline supplied" in output
    assert "All checks passed" not in output


def test_independent_baseline_executes_and_detects_api_change(tmp_path):
    target = tmp_path / "target"
    baseline = tmp_path / "baseline"
    target.mkdir()
    baseline.mkdir()
    (baseline / "api.h").write_text("void removed(void);\nvoid step(void);\n")
    (target / "api.h").write_text("void step(void);\n")
    report = run_all_checks(target, baseline)
    assert "regression" in report.executed
    assert "api_stability" in report.executed
    assert any(r.check_id == "API-BREAK-FUNC" for r in report.results)


def test_disabled_category_is_reported(tmp_path):
    (tmp_path / "sample.c").write_text("void step(void) {}\n")
    report = run_all_checks(tmp_path, rules={"misra": {"enabled": False}})
    assert "misra" not in report.executed
    assert report.skipped["misra"] == "disabled by configuration"
