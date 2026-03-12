"""Command-line interface for bakeC.

Usage:
    bakec generate --model <path> --platform <path> --output <path> [--verbose]

Output format on success:
    bakeC v0.1.0

    Model:     mnarx_lung (models/lung_mnarx.yaml)
    Platform:  ARM Cortex-M4 (platforms/cortex_m4.yaml)
    Output:    generated/cortex_m4/

    Validating model... OK
      5 elastance basis functions (M=5, d=1)
      20 resistance basis functions (L=20, d=1)
      Sample time: 16.0ms (62.5 Hz)

    Generating code...
      mnarx_lung_controller.h        (48 lines)
      mnarx_lung_controller.c        (185 lines)
      mnarx_lung_controller_data.c   (72 lines)
      mnarx_lung_controller_types.h  (22 lines)

    Quality check... OK
      MISRA subset: 0 violations
      Traceability: all functions traced

    Done in 0.18s

Output format on error:
    bakeC v0.1.0

    Model:     broken_model (models/broken.yaml)
    Platform:  Desktop Simulation (platforms/desktop.yaml)

    Validating model... FAILED

      models/broken.yaml → parameters.elastance
      Expected 6 knots for 5 basis functions (M+1), found 4.

    1 error. Generation aborted.
"""

import argparse
import logging
import sys
import time
from pathlib import Path

from bakec import __version__
from bakec.parser import parse_model, parse_platform
from bakec.validator import validate_model
from bakec.engine import CodegenEngine
from bakec.writer import write_generated_files

logger = logging.getLogger("bakec")


def main() -> None:
    """Entry point. Parse args and dispatch to generate command."""
    parser = argparse.ArgumentParser(prog="bakec", description="bakeC code generator")
    subparsers = parser.add_subparsers(dest="command")

    gen_parser = subparsers.add_parser("generate", help="Generate C code from model")
    gen_parser.add_argument("--model", required=True, type=Path, help="Path to model YAML")
    gen_parser.add_argument("--platform", required=True, type=Path, help="Path to platform YAML")
    gen_parser.add_argument("--output", required=True, type=Path, help="Output directory")
    gen_parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.command != "generate":
        parser.print_help()
        sys.exit(1)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    t0 = time.time()

    print(f"bakeC v{__version__}\n")

    # Parse
    model_data = parse_model(args.model)
    platform_data = parse_platform(args.platform)

    model = model_data["model"]
    platform = platform_data["platform"]

    print(f"Model:     {model['name']} ({args.model})")
    print(f"Platform:  {platform['name']} ({args.platform})")
    print(f"Output:    {args.output}/\n")

    # Validate
    print("Validating model... ", end="")
    errors = validate_model(model_data)
    if errors:
        print("FAILED\n")
        for err in errors:
            print(f"  {args.model} → {err}")
        print(f"\n{len(errors)} error(s). Generation aborted.")
        sys.exit(1)
    print("OK")

    # Print block summary
    for block in model.get("blocks", []):
        params = block.get("params", {})
        if block["type"] == "basis_function_sum":
            n = params["num_basis_functions"]
            d = params.get("basis_order", 0)
            print(f"  {n} {block['name']} basis functions (M={n}, d={d})")
    sample_ms = model["sample_time_s"] * 1000
    sample_hz = 1.0 / model["sample_time_s"]
    print(f"  Sample time: {sample_ms:.1f}ms ({sample_hz:.1f} Hz)\n")

    # Generate
    print("Generating code...")
    engine = CodegenEngine(
        template_dir=Path("templates"),
        model=model_data,
        platform=platform_data,
        model_path=str(args.model),
        platform_path=str(args.platform),
    )
    files = engine.render_all()

    # Write
    results = write_generated_files(files, args.output)
    max_name_len = max(len(name) for name, _ in results)
    for name, lines in results:
        print(f"  {name:<{max_name_len}}  ({lines} lines)")

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.2f}s")


if __name__ == "__main__":
    main()
