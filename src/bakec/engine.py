"""Code generation engine — renders Jinja2 templates with model and platform data.

Architecture (mirrors MATLAB Embedded Coder / TLC):
- Model data (from YAML) = equivalent of .rtw intermediate representation
- Jinja2 templates = equivalent of TLC template files
- Platform config = equivalent of system target file
"""

import hashlib
import logging
import math
import struct
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jinja2

from bakec import __version__

logger = logging.getLogger("bakec")


def target_real(value: float, real_type: str) -> float:
    """Round to the supported IEEE target type; reject loss of range."""
    if real_type not in ("float", "double"):
        raise ValueError(f"Unsupported real_T: {real_type}")
    try:
        number = float(value)
        rounded = (struct.unpack("!f", struct.pack("!f", number))[0]
                   if real_type == "float" else number)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{value!r} is not representable as {real_type}") from exc
    if not math.isfinite(rounded) or (value != 0 and rounded == 0):
        raise ValueError(f"{value!r} is not representable as finite nonzero {real_type}")
    return rounded


def c_real_literal(value: float, real_type: str) -> str:
    """Emit round-trip precision, including a decimal point or exponent."""
    number = target_real(value, real_type)
    text = format(number, ".9g") if real_type == "float" else repr(number)
    if "." not in text and "e" not in text.lower():
        text += ".0"
    return text + ("f" if real_type == "float" else "")


class CodegenEngine:
    """Template-based code generation engine."""

    _DEFAULT_TEMPLATE_DIR = Path(__file__).parent / "templates"

    def __init__(
        self,
        model: dict[str, Any],
        platform: dict[str, Any],
        model_path: str,
        platform_path: str,
        template_dir: Path | None = None,
    ) -> None:
        """Initialize the engine.

        Sets up the Jinja2 environment and builds the template context.
        Use jinja2.StrictUndefined so missing variables cause errors.
        Use trim_blocks=True, lstrip_blocks=True for clean output.

        Args:
            model: Parsed model dict (from parse_model).
            platform: Parsed platform dict (from parse_platform).
            model_path: Path to the model YAML file (for traceability).
            platform_path: Path to the platform YAML file (for traceability).
            template_dir: Override template directory. Defaults to the
                templates shipped inside the bakec package.

        The template context (self.context) must contain:
        - model: the model dict (from data["model"])
        - platform: the platform dict (from data["platform"])
        - blocks: list of block contexts with 'unroll' flag
          (unroll=True if num_basis_functions <= 8)
        - name: model name string
        - step_function: "{name}_step"
        - init_function: "{name}_initialize"
        - terminate_function: "{name}_terminate"
        - header_guard: "{NAME}_CONTROLLER_H"
        - types_guard: "{NAME}_CONTROLLER_TYPES_H"
        - real_T: resolved type string from platform
        - int_T: resolved type string from platform
        - type_suffix: "f" for float platforms, "" for double
        - meta: dict with generator_version, timestamp, model_path,
          platform_path, model_hash (first 16 chars of sha256),
          platform_hash (first 16 chars of sha256)
        """
        resolved_dir = template_dir if template_dir is not None else self._DEFAULT_TEMPLATE_DIR
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(resolved_dir)),
            undefined=jinja2.StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        model_data = deepcopy(model["model"])
        model_data.setdefault("state", [])
        for state in model_data["state"]:
            state.setdefault("initial_value", 0.0)
        platform_data = platform["platform"]
        real_type = platform_data["types"]["real_T"]
        self.env.filters["c_real"] = lambda value: c_real_literal(value, real_type)
        # Validate even when a custom template omits the sample period.
        target_real(model_data["sample_time_s"], real_type)
        name = model_data["name"]

        # Compute file hashes (first 16 chars of sha256)
        # Normalize line endings to LF before hashing so the hash is
        # identical on Windows (CRLF) and Linux (LF).
        model_hash = hashlib.sha256(
            Path(model_path).read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()[:16]
        platform_hash = hashlib.sha256(
            Path(platform_path).read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()[:16]

        # Build block contexts with unroll flag
        blocks = []
        pid_count = sum(b["type"] == "pid" for b in model_data.get("blocks", []))
        states = {s["name"]: s for s in model_data["state"]}
        for block in model_data.get("blocks", []):
            block_ctx = dict(block)
            if block["type"] == "pid":
                for role in ("integral", "prev_error"):
                    # Preserve the supplied single-PID model's state names.
                    # Multiple PIDs use block-qualified state names.
                    state_name = f"{block['name']}_{role}"
                    if state_name not in states and pid_count == 1 and role in states:
                        state_name = role
                    if state_name not in states:
                        states[state_name] = {"name": state_name, "initial_value": 0.0}
                        model_data["state"].append(states[state_name])
                    block_ctx[f"{role}_state"] = f"{name}_{state_name}"
                params = block["params"]
                if "output_min" in params and "output_max" in params:
                    if target_real(params["output_min"], real_type) >= target_real(params["output_max"], real_type):
                        raise ValueError(f"PID limits collapse in {real_type}: {block['name']}")
            for key in ("knots", "breakpoints"):
                if key in block.get("params", {}):
                    values = [target_real(v, real_type) for v in block["params"][key]]
                    if any(a >= b for a, b in zip(values, values[1:])):
                        raise ValueError(f"{block['name']}: {key} must remain strictly increasing in {real_type}")
            if block["type"] == "basis_function_sum":
                n = block["params"]["num_basis_functions"]
                block_ctx["unroll"] = n <= 8
            elif block["type"] == "lookup_table":
                n = len(block["params"]["breakpoints"])
                block_ctx["unroll"] = n <= 8
            blocks.append(block_ctx)

        name_upper = name.upper()

        self.context: dict[str, Any] = {
            "model": model_data,
            "platform": platform_data,
            "blocks": blocks,
            "name": name,
            "step_function": f"{name}_step",
            "init_function": f"{name}_initialize",
            "terminate_function": f"{name}_terminate",
            "header_guard": f"{name_upper}_CONTROLLER_H",
            "types_guard": f"{name_upper}_CONTROLLER_TYPES_H",
            "real_T": platform_data["types"]["real_T"],
            "int_T": platform_data["types"]["int_T"],
            "type_suffix": "f" if real_type == "float" else "",
            "meta": {
                "generator_version": __version__,
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "model_path": model_path.replace("\\", "/"),
                "platform_path": platform_path.replace("\\", "/"),
                "model_hash": model_hash,
                "platform_hash": platform_hash,
            },
        }

        logger.info("Engine initialized for model '%s' on platform '%s'",
                     name, platform_data["name"])

    def render_all(self) -> dict[str, str]:
        """Render all output files.

        Returns dict mapping output filename to rendered content.
        Output filenames follow the pattern: {name}_controller.h,
        {name}_controller.c, {name}_controller_data.c,
        {name}_controller_types.h

        Templates to render:
        - controller.h.j2 → {name}_controller.h
        - controller.c.j2 → {name}_controller.c
        - controller_data.c.j2 → {name}_controller_data.c
        - controller_types.h.j2 → {name}_controller_types.h
        """
        name = self.context["name"]
        template_map = {
            "controller.h.j2": f"{name}_controller.h",
            "controller.c.j2": f"{name}_controller.c",
            "controller_data.c.j2": f"{name}_controller_data.c",
            "controller_types.h.j2": f"{name}_controller_types.h",
        }

        files: dict[str, str] = {}
        for template_name, output_name in template_map.items():
            template = self.env.get_template(template_name)
            files[output_name] = template.render(**self.context)
            logger.info("Rendered %s", output_name)

        return files
