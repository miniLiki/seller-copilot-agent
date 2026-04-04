from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from .models import ModelRuntimeOutput


def _extract_json_object(raw_output: str) -> str:
    stripped = raw_output.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        return stripped
    return stripped[start : end + 1]


def parse_model_output(raw_output: str) -> tuple[ModelRuntimeOutput | None, dict[str, Any] | None]:
    candidate = _extract_json_object(raw_output)
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return None, {"error": "MODEL_OUTPUT_PARSE_ERROR", "raw_output": raw_output}
    try:
        parsed = ModelRuntimeOutput.model_validate(payload)
    except ValidationError as exc:
        return None, {
            "error": "MODEL_OUTPUT_SCHEMA_ERROR",
            "raw_output": raw_output,
            "details": exc.errors(),
        }
    return parsed, None

