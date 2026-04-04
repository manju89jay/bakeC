"""Parse model and platform YAML files into intermediate representation."""

import logging
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from bakec.schema import MODEL_SCHEMA, PLATFORM_SCHEMA

logger = logging.getLogger("bakec")


def _validate_schema(data: dict, schema: dict, path: Path) -> None:
    """Validate data against a JSON Schema, raising ValueError on failure.

    Args:
        data: Parsed YAML data to validate.
        schema: JSON Schema dict.
        path: Source file path (for error messages).

    Raises:
        ValueError: If schema validation fails, with the JSON path and message.
    """
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as exc:
        json_path = " → ".join(str(p) for p in exc.absolute_path) or "(root)"
        raise ValueError(f"{path}: schema error at {json_path}: {exc.message}") from exc


def parse_model(path: Path) -> dict[str, Any]:
    """Parse a model YAML file and return the model dictionary.

    Args:
        path: Path to the model YAML file.

    Returns:
        Parsed model dictionary with top-level keys: schema_version, model.

    Raises:
        FileNotFoundError: If the model file does not exist.
        yaml.YAMLError: If the YAML is malformed.
        ValueError: If required top-level keys are missing or schema
            validation fails.
    """
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")

    logger.info("Parsing model file: %s", path)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "model" not in data:
        raise ValueError(f"{path}: YAML must contain a 'model' key")

    _validate_schema(data, MODEL_SCHEMA, path)

    model = data["model"]
    logger.info("Parsed model '%s' with %d blocks", model["name"], len(model["blocks"]))
    return data


def parse_platform(path: Path) -> dict[str, Any]:
    """Parse a platform YAML file and return the platform dictionary.

    Args:
        path: Path to the platform YAML file.

    Returns:
        Parsed platform dictionary with top-level key: platform.

    Raises:
        FileNotFoundError: If the platform file does not exist.
        yaml.YAMLError: If the YAML is malformed.
        ValueError: If required top-level keys are missing or schema
            validation fails.
    """
    if not path.exists():
        raise FileNotFoundError(f"Platform file not found: {path}")

    logger.info("Parsing platform file: %s", path)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "platform" not in data:
        raise ValueError(f"{path}: YAML must contain a 'platform' key")

    _validate_schema(data, PLATFORM_SCHEMA, path)

    platform = data["platform"]
    logger.info("Parsed platform '%s'", platform["name"])
    return data
