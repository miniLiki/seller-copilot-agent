from __future__ import annotations

from typing import Any, Callable

import requests

ToolExecutor = Callable[[dict[str, Any]], dict[str, Any]]

_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "get_product_info",
        "description": "Get basic product information by product ID.",
        "parameters": {
            "type": "object",
            "properties": {"product_id": {"type": "string", "description": "The product identifier."}},
            "required": ["product_id"],
        },
        "method": "GET",
        "path": "/product/{product_id}",
    },
    {
        "name": "get_inventory_status",
        "description": "Get inventory status and risk level for a product.",
        "parameters": {
            "type": "object",
            "properties": {"product_id": {"type": "string", "description": "The product identifier."}},
            "required": ["product_id"],
        },
        "method": "GET",
        "path": "/inventory/{product_id}",
    },
    {
        "name": "create_opt_task",
        "description": "Create an optimization task for the product.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string"},
                "task_type": {"type": "string", "enum": ["creative_refresh", "detail_page_fix", "title_rewrite"]},
                "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                "reason": {"type": "string"},
            },
            "required": ["product_id", "task_type", "priority", "reason"],
        },
        "method": "POST",
        "path": "/task/create",
    },
    {
        "name": "generate_ad_copy",
        "description": "Generate ad copy variations for the product.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string"},
                "market": {"type": "string"},
                "angle": {"type": "string", "enum": ["benefit_driven", "pain_point", "discount"]},
                "num_variants": {"type": "integer", "minimum": 1, "maximum": 5},
            },
            "required": ["product_id", "market", "angle", "num_variants"],
        },
        "method": "POST",
        "path": "/copy/generate",
    },
]


def get_tool_schemas_for_prompt() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": item["name"],
                "description": item["description"],
                "parameters": item["parameters"],
            },
        }
        for item in _TOOL_DEFINITIONS
    ]


def get_tool_schemas_for_training() -> list[dict[str, Any]]:
    return get_tool_schemas_for_prompt()


def get_tool_definition_map() -> dict[str, dict[str, Any]]:
    return {item["name"]: item for item in _TOOL_DEFINITIONS}


def _perform_request(*, base_url: str, method: str, path: str, arguments: dict[str, Any]) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}" + path.format(**arguments)
    if method == "GET":
        response = requests.get(url, timeout=10)
    else:
        response = requests.post(url, json=arguments, timeout=10)
    response.raise_for_status()
    return response.json()


def get_tool_executor_map(tool_base_url: str) -> dict[str, ToolExecutor]:
    definition_map = get_tool_definition_map()
    executors: dict[str, ToolExecutor] = {}
    for name, definition in definition_map.items():
        executors[name] = (
            lambda arguments, definition=definition: _perform_request(
                base_url=tool_base_url,
                method=definition["method"],
                path=definition["path"],
                arguments=arguments,
            )
        )
    return executors

