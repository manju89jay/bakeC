"""Command-line interface for bakeC.

Usage:
    bakec generate --model <path> --platform <path> --output <path> [--verbose]
    bakec validate --target <dir> [--baseline <dir>] [--rules <path>] [--verbose]
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import yaml

from bakec import __version__
from bakec.parser import parse_model, parse_platform
from bakec.validator import validate_model
from bakec.engine import CodegenEngine
from bakec.writer import write_generated_files
from bakec.checks.runner import run_all_checks, CheckReport

logger = logging.getLogger("bakec")

_SEVERITY_ICON = {
    "error": "X",
    "warning": "!",
    "info": "i",
}


def _print_report(report: CheckReport) -> None:
    """Print a human-readable validation report."""
    for r in report.results:
        icon = _SEVERITY_ICON.get(r.severity, "?")
        loc = f"{r.file}"
        if r.line:
            loc += f":{r.line}"
        print(f"  {icon} [{r.check_id}] {loc} -- {r.message}")
        if r.suggestion:
            print(f"    -> {r.suggestion}")

    print()
    parts = []
    if report.errors:
        parts.append(f"{report.errors} error(s)")
    if report.warnings:
        parts.append(f"{report.warnings} warning(s)")
    if report.infos:
        parts.append(f"{report.infos} info(s)")

    if parts:
        print(f"  {', '.join(parts)}")
    else:
        print("  OK -- All checks passed")


def _cmd_generate(args: argparse.Namespace) -> None:
    """Handle the generate subcommand."""
    t0 = time.time()

    print(f"bakeC v{__version__}\n")

    model_data = parse_model(args.model)
    platform_data = parse_platform(args.platform)

    model = model_data["model"]
    platform = platform_data["platform"]

    print(f"Model:     {model['name']} ({args.model})")
    print(f"Platform:  {platform['name']} ({args.platform})")
    print(f"Output:    {args.output}/\n")

    print("Validating model... ", end="")
    errors = validate_model(model_data)
    if errors:
        print("FAILED\n")
        for err in errors:
            print(f"  {args.model} \u2192 {err}")
        print(f"\n{len(errors)} error(s). Generation aborted.")
        sys.exit(1)
    print("OK")

    for block in model.get("blocks", []):
        params = block.get("params", {})
        if block["type"] == "basis_function_sum":
            n = params["num_basis_functions"]
            d = params.get("basis_order", 0)
            print(f"  {n} {block['name']} basis functions (M={n}, d={d})")
    sample_ms = model["sample_time_s"] * 1000
    sample_hz = 1.0 / model["sample_time_s"]
    print(f"  Sample time: {sample_ms:.1f}ms ({sample_hz:.1f} Hz)\n")

    print("Generating code...")
    engine = CodegenEngine(
        template_dir=Path("templates"),
        model=model_data,
        platform=platform_data,
        model_path=str(args.model),
        platform_path=str(args.platform),
    )
    files = engine.render_all()

    results = write_generated_files(files, args.output)
    max_name_len = max(len(name) for name, _ in results)
    for name, lines in results:
        print(f"  {name:<{max_name_len}}  ({lines} lines)")

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.2f}s")


def _cmd_validate(args: argparse.Namespace) -> None:
    """Handle the validate subcommand."""
    t0 = time.time()

    print(f"bakeC v{__version__}\n")

    target_dir = args.target
    baseline_dir = args.baseline
    rules_path = args.rules

    print(f"Target:    {target_dir}/")
    if baseline_dir:
        print(f"Baseline:  {baseline_dir}/")
    print()

    if not target_dir.is_dir():
        print(f"Error: target directory '{target_dir}' does not exist")
        sys.exit(1)

    rules = {}
    if rules_path and rules_path.exists():
        with open(rules_path, "r", encoding="utf-8") as f:
            rules = yaml.safe_load(f) or {}

    print("Running checks...")
    report = run_all_checks(target_dir, baseline_dir, rules)
    print()

    _print_report(report)

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.2f}s")

    if report.errors:
        sys.exit(1)


def main() -> None:
    """Entry point. Parse args and dispatch to subcommand."""
    parser = argparse.ArgumentParser(prog="bakec", description="bakeC code generator")
    subparsers = parser.add_subparsers(dest="command")

    gen_parser = subparsers.add_parser("generate", help="Generate C code from model")
    gen_parser.add_argument("--model", required=True, type=Path, help="Path to model YAML")
    gen_parser.add_argument("--platform", required=True, type=Path, help="Path to platform YAML")
    gen_parser.add_argument("--output", required=True, type=Path, help="Output directory")
    gen_parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    val_parser = subparsers.add_parser("validate", help="Validate generated code")
    val_parser.add_argument("--target", required=True, type=Path, help="Target directory with generated files")
    val_parser.add_argument("--baseline", type=Path, default=None, help="Baseline directory for regression checks")
    val_parser.add_argument("--rules", type=Path, default=None, help="Rules YAML file")
    val_parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.command not in ("generate", "validate"):
        parser.print_help()
        sys.exit(1)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    if args.command == "generate":
        _cmd_generate(args)
    elif args.command == "validate":
        _cmd_validate(args)


if __name__ == "__main__":
    main()
