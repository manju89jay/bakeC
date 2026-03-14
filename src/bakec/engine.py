"""Code generation engine — renders Jinja2 templates with model and platform data.

Architecture (mirrors MATLAB Embedded Coder / TLC):
- Model data (from YAML) = equivalent of .rtw intermediate representation
- Jinja2 templates = equivalent of TLC template files
- Platform config = equivalent of system target file
"""

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jinja2

from bakec import __version__

logger = logging.getLogger("bakec")


class CodegenEngine:
    """Template-based code generation engine."""

    def __init__(
        self,
        template_dir: Path,
        model: dict[str, Any],
        platform: dict[str, Any],
        model_path: str,
        platform_path: str,
    ) -> None:
        """Initialize the engine.

        Sets up the Jinja2 environment and builds the template context.
        Use jinja2.StrictUndefined so missing variables cause errors.
        Use trim_blocks=True, lstrip_blocks=True for clean output.

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
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(template_dir)),
            undefined=jinja2.StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        model_data = model["model"]
        platform_data = platform["platform"]
        name = model_data["name"]

        # Compute file hashes (first 16 chars of sha256)
        model_hash = hashlib.sha256(
            Path(model_path).read_bytes()
        ).hexdigest()[:16]
        platform_hash = hashlib.sha256(
            Path(platform_path).read_bytes()
        ).hexdigest()[:16]

        # Build block contexts with unroll flag
        blocks = []
        for block in model_data.get("blocks", []):
            block_ctx = dict(block)
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
            "type_suffix": platform_data.get("type_suffix", ""),
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
