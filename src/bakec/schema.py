"""JSON Schema definitions for model and platform validation."""

MODEL_SCHEMA: dict = {
    "type": "object",
    "required": ["model"],
    "properties": {
        "schema_version": {"type": "string"},
        "model": {
            "type": "object",
            "required": ["name", "sample_time_s", "inputs", "outputs", "blocks"],
            "properties": {
                "name": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"},
                "description": {"type": "string"},
                "sample_time_s": {"type": "number", "exclusiveMinimum": 0},
                "inputs": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["name", "data_type"],
                        "properties": {
                            "name": {"type": "string"},
                            "data_type": {
                                "type": "string",
                                "enum": ["real_T", "int32_T", "uint16_T", "int16_T"],
                            },
                        },
                    },
                },
                "outputs": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["name", "data_type"],
                        "properties": {
                            "name": {"type": "string"},
                            "data_type": {
                                "type": "string",
                                "enum": ["real_T", "int32_T", "uint16_T", "int16_T"],
                            },
                        },
                    },
                },
                "blocks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["type", "name"],
                        "properties": {
                            "type": {"type": "string"},
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "params": {"type": "object"},
                        },
                    },
                },
                "state": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name"],
                        "properties": {
                            "name": {"type": "string"},
                            "initial_value": {"type": "number"},
                        },
                    },
                },
            },
        },
    },
}

PLATFORM_SCHEMA: dict = {
    "type": "object",
    "required": ["platform"],
    "properties": {
        "platform": {
            "type": "object",
            "required": ["name", "types", "constraints"],
            "properties": {
                "name": {"type": "string"},
                "compiler": {"type": "string"},
                "types": {
                    "type": "object",
                    "required": ["real_T", "int_T"],
                    "properties": {
                        "real_T": {"type": "string"},
                        "int_T": {"type": "string"},
                    },
                },
                "constraints": {
                    "type": "object",
                    "properties": {
                        "dynamic_memory": {"type": "boolean"},
                        "printf_allowed": {"type": "boolean"},
                        "assertions": {"type": "boolean"},
                        "floating_point": {
                            "type": "string",
                            "enum": ["single", "double"],
                        },
                    },
                },
                "type_suffix": {"type": "string"},
                "compiler_flags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
    },
}
