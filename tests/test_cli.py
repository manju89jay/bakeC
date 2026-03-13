"""Tests for the CLI module."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from bakec.cli import main, _print_report
from bakec.checks.runner import CheckReport, CheckResult


# --- _print_report ---

def test_print_report_clean(capsys):
    report = CheckReport(target_dir="gen/", baseline_dir=None, results=[])
    _print_report(report)
    output = capsys.readouterr().out
    assert "OK" in output


def test_print_report_with_errors(capsys):
    report = CheckReport(target_dir="gen/", baseline_dir=None, results=[
        CheckResult(file="test.c", line=10, severity="error",
                    check_id="SAFE-001", message="malloc used",
                    suggestion="Use static allocation"),
    ])
    _print_report(report)
    output = capsys.readouterr().out
    assert "SAFE-001" in output
    assert "malloc" in output
    assert "1 error(s)" in output


def test_print_report_with_warning(capsys):
    report = CheckReport(target_dir="gen/", baseline_dir=None, results=[
        CheckResult(file="test.c", line=None, severity="warning",
                    check_id="TRACE-003", message="Missing DO NOT EDIT"),
    ])
    _print_report(report)
    output = capsys.readouterr().out
    assert "TRACE-003" in output
    assert "1 warning(s)" in output


# --- generate subcommand ---

def test_generate_end_to_end(tmp_path, capsys):
    output_dir = tmp_path / "out"
    test_args = [
        "bakec", "generate",
        "--model", "models/lung_mnarx.yaml",
        "--platform", "platforms/desktop.yaml",
        "--output", str(output_dir),
    ]
    with patch.object(sys, "argv", test_args):
        main()
    output = capsys.readouterr().out
    assert "bakeC v" in output
    assert "mnarx_lung" in output
    assert output_dir.is_dir()
    c_files = list(output_dir.glob("*.c"))
    assert len(c_files) > 0


def test_generate_missing_model(tmp_path):
    test_args = [
        "bakec", "generate",
        "--model", str(tmp_path / "nonexistent.yaml"),
        "--platform", "platforms/desktop.yaml",
        "--output", str(tmp_path / "out"),
    ]
    with patch.object(sys, "argv", test_args):
        with pytest.raises((SystemExit, FileNotFoundError, Exception)):
            main()


def test_generate_verbose(tmp_path, capsys):
    output_dir = tmp_path / "out"
    test_args = [
        "bakec", "generate",
        "--model", "models/pid_controller.yaml",
        "--platform", "platforms/cortex_m4.yaml",
        "--output", str(output_dir),
        "--verbose",
    ]
    with patch.object(sys, "argv", test_args):
        main()
    output = capsys.readouterr().out
    assert "pid_pressure" in output


# --- validate subcommand ---

def test_validate_generated_desktop(capsys):
    test_args = [
        "bakec", "validate",
        "--target", "generated/desktop/",
        "--rules", "src/bakec/checks/rules.yaml",
    ]
    with patch.object(sys, "argv", test_args):
        main()
    output = capsys.readouterr().out
    assert "OK" in output or "checks" in output.lower()


def test_validate_with_platforms_dir(capsys):
    test_args = [
        "bakec", "validate",
        "--target", "generated/cortex_m4/",
        "--rules", "src/bakec/checks/rules.yaml",
        "--platforms-dir", "platforms/",
    ]
    with patch.object(sys, "argv", test_args):
        main()
    output = capsys.readouterr().out
    assert "OK" in output


def test_validate_nonexistent_target(capsys):
    test_args = [
        "bakec", "validate",
        "--target", "nonexistent_dir/",
    ]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


def test_validate_verbose(capsys):
    test_args = [
        "bakec", "validate",
        "--target", "generated/desktop/",
        "--rules", "src/bakec/checks/rules.yaml",
        "--verbose",
    ]
    with patch.object(sys, "argv", test_args):
        main()


# --- no subcommand ---

def test_no_subcommand():
    test_args = ["bakec"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
