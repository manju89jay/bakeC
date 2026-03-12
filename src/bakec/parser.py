"""Parse model and platform YAML files into intermediate representation."""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("bakec")


def parse_model(path: Path) -> dict[str, Any]:
    """Parse a model YAML file and return the model dictionary.

    Args:
        path: Path to the model YAML file.

    Returns:
        Parsed model dictionary with top-level keys: schema_version, model.

    Raises:
        FileNotFoundError: If the model file does not exist.
        yaml.YAMLError: If the YAML is malformed.
        ValueError: If required top-level keys are missing.
            Required model keys: name, sample_time_s, inputs, outputs, blocks.
    """
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")

    logger.info("Parsing model file: %s", path)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "model" not in data:
        raise ValueError(f"{path}: YAML must contain a 'model' key")

    model = data["model"]
    required_keys = ["name", "sample_time_s", "inputs", "outputs", "blocks"]
    for key in required_keys:
        if key not in model:
            raise ValueError(f"{path}: model must contain '{key}'")

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
        ValueError: If required top-level keys are missing.
            Required platform keys: name, types, constraints.
    """
    if not path.exists():
        raise FileNotFoundError(f"Platform file not found: {path}")

    logger.info("Parsing platform file: %s", path)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "platform" not in data:
        raise ValueError(f"{path}: YAML must contain a 'platform' key")

    platform = data["platform"]
    required_keys = ["name", "types", "constraints"]
    for key in required_keys:
        if key not in platform:
            raise ValueError(f"{path}: platform must contain '{key}'")

    logger.info("Parsed platform '%s'", platform["name"])
    return data
