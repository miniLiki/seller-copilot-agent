from __future__ import annotations

import json
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from rag.retrieve import dump_retrieval_trace, retrieve_rules

from .executor import execute_tool_calls
from .model_adapter import call_model, mock_model
from .models import RunTrace
from .parser import parse_model_output
from .prompt import runtime_json_prompt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = {
    "model_mode": "mock",
    "model_name": "Qwen/Qwen2.5-VL-7B-Instruct",
    "adapter_path": "",
    "agent_template": "qwen2_vl",
    "tools_prompt": "json",
    "seed": 7,
    "tool_base_url": "http://127.0.0.1:8000",
    "save_run_trace": True,
    "run_dir": "runs",
    "kb_dir": "data/kb",
    "swift_infer_script": "train/infer.sh",
    "swift_timeout_seconds": 900,
    "infer_backend": "pt",
    "max_new_tokens": 512,
    "temperature": 0.0,
    "load_args": False,
}
PATH_KEYS = ("adapter_path", "run_dir", "kb_dir", "swift_infer_script")



def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}



def _resolve_path(value: str) -> str:
    if not value:
        return value
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str((PROJECT_ROOT / path).resolve())



def _normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(config)
    normalized["seed"] = int(normalized.get("seed", 7))
    normalized["swift_timeout_seconds"] = int(normalized.get("swift_timeout_seconds", 900))
    normalized["max_new_tokens"] = int(normalized.get("max_new_tokens", 512))
    normalized["temperature"] = float(normalized.get("temperature", 0.0))
    normalized["save_run_trace"] = _coerce_bool(normalized.get("save_run_trace", True))
    normalized["load_args"] = _coerce_bool(normalized.get("load_args", False))
    for key in PATH_KEYS:
        value = str(normalized.get(key, ""))
        normalized[key] = _resolve_path(value) if value else value
    return normalized



def load_runtime_config(config_path: str | Path) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    path = Path(config_path)
    if path.exists():
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        config.update(loaded)
    env_map = {
        "TOOL_BASE_URL": "tool_base_url",
        "MODEL_MODE": "model_mode",
        "MODEL_NAME": "model_name",
        "ADAPTER_PATH": "adapter_path",
        "AGENT_TEMPLATE": "agent_template",
        "TOOLS_PROMPT": "tools_prompt",
        "SEED": "seed",
        "RUN_DIR": "run_dir",
        "KB_DIR": "kb_dir",
        "SWIFT_INFER_SCRIPT": "swift_infer_script",
        "SWIFT_TIMEOUT_SECONDS": "swift_timeout_seconds",
        "INFER_BACKEND": "infer_backend",
        "MAX_NEW_TOKENS": "max_new_tokens",
        "TEMPERATURE": "temperature",
        "LOAD_ARGS": "load_args",
    }
    for env_name, key in env_map.items():
        if os.getenv(env_name):
            config[key] = os.getenv(env_name)
    if os.getenv("SAVE_RUN_TRACE") is not None:
        config["save_run_trace"] = os.getenv("SAVE_RUN_TRACE", "true")
    return _normalize_config(config)



def get_runtime_summary(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "model_mode": config["model_mode"],
        "model_name": config["model_name"],
        "adapter_path": config.get("adapter_path", ""),
        "agent_template": config["agent_template"],
        "tools_prompt": config["tools_prompt"],
        "seed": config["seed"],
        "infer_backend": config["infer_backend"],
        "swift_infer_script": config["swift_infer_script"],
        "tool_base_url": config["tool_base_url"],
    }



def _build_run_trace_dir(run_root: Path, product_id: str) -> tuple[str, str, Path]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"{timestamp}_{product_id.lower()}"
    return run_id, timestamp, run_root / run_id



def save_run_trace(trace: RunTrace, run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "input.json").write_text(json.dumps(trace.input_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    dump_retrieval_trace(trace.retrieval_results, run_dir)
    (run_dir / "prompt.txt").write_text(trace.prompt_text, encoding="utf-8")
    (run_dir / "raw_model_output.txt").write_text(trace.raw_model_output, encoding="utf-8")
    (run_dir / "parsed_output.json").write_text(json.dumps(trace.parsed_output, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "tool_results.json").write_text(json.dumps(trace.tool_results, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "final_response.txt").write_text(trace.final_response, encoding="utf-8")
    (run_dir / "config.json").write_text(json.dumps(trace.config_snapshot, ensure_ascii=False, indent=2), encoding="utf-8")



def run_agent(
    *,
    image_path: Path,
    user_query: str,
    product_id: str,
    config_path: str | Path = "configs/runtime.yaml",
    save_trace: bool | None = None,
) -> RunTrace:
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    config = load_runtime_config(config_path)
    random.seed(config["seed"])
    run_root = Path(str(config.get("run_dir", PROJECT_ROOT / "runs")))
    run_id, timestamp, run_dir = _build_run_trace_dir(run_root, product_id)
    retrieval_results = retrieve_rules(
        user_query,
        config.get("kb_dir", str(PROJECT_ROOT / "data" / "kb")),
        market="US",
    )
    prompt_text = runtime_json_prompt(user_query=user_query, retrieved_rules=retrieval_results, image_count=1)

    errors: list[str] = []
    model_call_error: str | None = None
    try:
        raw_output = call_model(
            prompt=prompt_text,
            image_path=image_path,
            user_query=user_query,
            product_id=product_id,
            retrieved_rules=retrieval_results,
            config=config,
            run_dir=run_dir,
        )
    except Exception as exc:
        model_call_error = str(exc)
        raw_output = json.dumps({"error": "MODEL_CALL_ERROR", "detail": model_call_error}, ensure_ascii=False, indent=2)
        errors.append(model_call_error)

    if model_call_error is not None:
        final_response = "Model call failed. Check raw_model_output.txt and swift_stderr.log."
        tool_results: list[dict[str, Any]] = []
        parsed_payload = {"error": "MODEL_CALL_ERROR", "detail": model_call_error}
    else:
        parsed_output, parse_error = parse_model_output(raw_output)
        if parse_error:
            errors.append(parse_error["error"])
            final_response = f"Model output parse failed: {parse_error['error']}"
            tool_results = []
            parsed_payload = parse_error
        else:
            tool_records = execute_tool_calls(parsed_output.tool_calls, str(config["tool_base_url"]))
            tool_results = [record.model_dump() for record in tool_records]
            parsed_payload = parsed_output.model_dump()
            final_response = parsed_output.final_response
            failed_tools = [record for record in tool_records if not record.success]
            if failed_tools:
                final_response += " Tool execution had failures. Check tool_results.json."
                errors.extend(record.error or "Unknown tool execution error" for record in failed_tools)

    trace = RunTrace(
        run_id=run_id,
        timestamp=timestamp,
        input_payload={
            "image_path": str(image_path),
            "product_id": product_id,
            "user_query": user_query,
        },
        retrieval_results=retrieval_results,
        prompt_text=prompt_text,
        raw_model_output=raw_output,
        parsed_output=parsed_payload,
        tool_results=tool_results,
        final_response=final_response,
        config_snapshot=config,
        errors=errors,
    )
    should_save = config.get("save_run_trace", True) if save_trace is None else save_trace
    if should_save:
        save_run_trace(trace, run_dir)
    return trace

