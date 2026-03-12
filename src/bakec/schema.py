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
                    },
                },
                "blocks": {"type": "array"},
            },
        },
    },
}
