from __future__ import annotations

from .models import ToolExecutionRecord
from .tool_registry import get_tool_executor_map


def execute_tool_calls(tool_calls, tool_base_url: str) -> list[ToolExecutionRecord]:
    executors = get_tool_executor_map(tool_base_url)
    records: list[ToolExecutionRecord] = []
    for tool_call in tool_calls:
        executor = executors.get(tool_call.name)
        if executor is None:
            records.append(
                ToolExecutionRecord(
                    name=tool_call.name,
                    arguments=tool_call.arguments,
                    success=False,
                    error=f"Unknown tool: {tool_call.name}",
                )
            )
            continue
        try:
            response = executor(tool_call.arguments)
            records.append(
                ToolExecutionRecord(
                    name=tool_call.name,
                    arguments=tool_call.arguments,
                    success=True,
                    status_code=200,
                    response=response,
                )
            )
        except Exception as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            records.append(
                ToolExecutionRecord(
                    name=tool_call.name,
                    arguments=tool_call.arguments,
                    success=False,
                    status_code=status_code,
                    error=str(exc),
                )
            )
    return records

