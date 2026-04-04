from __future__ import annotations

import json
from typing import Any

from .models import ModelRuntimeOutput
from .tool_registry import get_tool_schemas_for_prompt

RUNTIME_JSON_SCHEMA = {
    "task_understanding": "string",
    "evidence": ["string"],
    "need_rag": True,
    "need_tool_call": False,
    "tool_calls": [{"name": "tool_name", "arguments": {}}],
    "final_response": "string",
}


def _render_image_placeholders(image_count: int) -> str:
    if image_count <= 0:
        return ""
    return "\n".join("<image>" for _ in range(image_count))


def runtime_json_prompt(*, user_query: str, retrieved_rules: list[dict[str, Any]], image_count: int) -> str:
    rules_text = "\n\n".join(
        f"[{item['chunk_id']}] ({item['source']}, score={item['score']})\n{item['content']}"
        for item in retrieved_rules
    ) or "No rules retrieved."
    tools_text = json.dumps(get_tool_schemas_for_prompt(), ensure_ascii=False, indent=2)
    image_text = _render_image_placeholders(image_count)
    parts = [
        "Role: You are a seller copilot agent for cross-border ecommerce operations.",
        "You must return strict JSON only. Do not output markdown or explanatory text.",
        "Required output schema:",
        json.dumps(RUNTIME_JSON_SCHEMA, ensure_ascii=False, indent=2),
        "Available tools:",
        tools_text,
        "Retrieved rules:",
        rules_text,
        "User task:",
        f"{image_text}\n{user_query}".strip(),
    ]
    return "\n\n".join(parts)


def swift_agent_prompt(*, user_query: str, retrieved_rules: list[dict[str, Any]], images: list[str]) -> str:
    return runtime_json_prompt(
        user_query=user_query,
        retrieved_rules=retrieved_rules,
        image_count=len(images),
    )


def serialize_runtime_output(output: ModelRuntimeOutput) -> str:
    return json.dumps(output.model_dump(), ensure_ascii=False, indent=2)

