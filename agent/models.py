from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Normalized tool call emitted by the runtime model."""

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ModelRuntimeOutput(BaseModel):
    """Structured runtime contract shared across planner, parser, and executor."""

    task_understanding: str = ""
    evidence: list[str] = Field(default_factory=list)
    need_rag: bool = True
    need_tool_call: bool = False
    tool_calls: list[ToolCall] = Field(default_factory=list)
    final_response: str = ""


class ToolExecutionRecord(BaseModel):
    """Captures one tool execution and its outcome."""

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    success: bool
    status_code: int | None = None
    response: dict[str, Any] | None = None
    error: str | None = None


class RunTrace(BaseModel):
    """Serializable trace artifact for one end-to-end run."""

    run_id: str
    timestamp: str
    input_payload: dict[str, Any]
    retrieval_results: list[dict[str, Any]] = Field(default_factory=list)
    prompt_text: str = ""
    raw_model_output: str = ""
    parsed_output: dict[str, Any] = Field(default_factory=dict)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    final_response: str = ""
    config_snapshot: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)

