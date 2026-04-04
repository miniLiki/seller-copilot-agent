from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .models import ModelRuntimeOutput

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SwiftAdapterError(RuntimeError):
    """Raised when the swift adapter cannot complete an inference request."""



def mock_model(*, user_query: str, product_id: str, retrieved_rules: list[dict[str, Any]]) -> str:
    """Return deterministic runtime JSON based on simple keyword rules."""

    lower_query = user_query.lower()
    create_task = any(keyword in user_query for keyword in ["创建整改任务", "创建工单", "整改任务", "工单"])
    generate_copy = any(keyword in user_query for keyword in ["广告文案", "生成文案", "文案", "copy"])
    evidence = [
        "主图适配性需要结合主体清晰度、文案合规性和背景干扰度判断。",
        f"已检索到 {len(retrieved_rules)} 条规则片段参与判断。",
    ]
    if retrieved_rules:
        evidence.append(f"最高分规则来自 {retrieved_rules[0]['source']}。")
    tool_calls: list[dict[str, Any]] = []
    if create_task:
        tool_calls.append(
            {
                "name": "create_opt_task",
                "arguments": {
                    "product_id": product_id,
                    "task_type": "creative_refresh",
                    "priority": "high",
                    "reason": "hero image needs clearer focal point and cleaner selling message",
                },
            }
        )
    if generate_copy:
        num_variants = 2 if "两条" in user_query or "2" in lower_query else 3
        angle = "discount" if "折扣" in user_query else "benefit_driven"
        tool_calls.append(
            {
                "name": "generate_ad_copy",
                "arguments": {
                    "product_id": product_id,
                    "market": "US" if any(token in user_query for token in ["美国", "US", "us"]) else "US",
                    "angle": angle,
                    "num_variants": num_variants,
                },
            }
        )
    final_bits = ["已完成主图诊断"]
    if create_task:
        final_bits.append("已准备创建整改工单")
    if generate_copy:
        final_bits.append("已准备生成广告文案")
    payload = ModelRuntimeOutput(
        task_understanding="诊断商品主图是否适合当前市场投放，并在需要时执行整改任务和广告文案生成。",
        evidence=evidence,
        need_rag=True,
        need_tool_call=bool(tool_calls),
        tool_calls=tool_calls,
        final_response="，".join(final_bits) + "。",
    )
    return json.dumps(payload.model_dump(), ensure_ascii=False, indent=2)



def build_swift_request_sample(*, prompt: str, image_path: Path) -> dict[str, Any]:
    """Build a one-sample jsonl payload for batch inference via swift infer."""

    return {
        "messages": [{"role": "user", "content": prompt}],
        "images": [str(image_path)],
    }



def build_swift_infer_command(
    *,
    script_path: Path,
    config: dict[str, Any],
    request_path: Path,
    result_path: Path,
) -> list[str]:
    """Build the shell command used by the runtime swift adapter."""

    return [
        "bash",
        str(script_path),
        str(config["model_name"]),
        str(config.get("adapter_path", "")),
        str(config.get("agent_template", "")),
        str(config.get("tools_prompt", "")),
        str(config.get("seed", 7)),
        str(request_path),
        str(result_path),
        str(config.get("infer_backend", "transformers")),
        str(config.get("max_new_tokens", 512)),
        str(config.get("temperature", 0)),
        str(config.get("load_args", False)).lower(),
    ]



def _extract_text_from_result_record(record: dict[str, Any]) -> str | None:
    """Try several common result layouts produced by inference wrappers."""

    candidates: list[Any] = [
        record.get("response"),
        record.get("result"),
        record.get("assistant"),
        record.get("generated_text"),
    ]
    choices = record.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {})
        candidates.append(message.get("content"))
    responses = record.get("responses")
    if isinstance(responses, list) and responses:
        first_response = responses[0]
        if isinstance(first_response, dict):
            candidates.append(first_response.get("content"))
        else:
            candidates.append(first_response)
    messages = record.get("messages")
    if isinstance(messages, list) and messages:
        last_message = messages[-1]
        if isinstance(last_message, dict) and last_message.get("role") == "assistant":
            candidates.append(last_message.get("content"))
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None



def load_swift_result(result_path: Path) -> str:
    """Extract the assistant text from a swift batch result file."""

    if not result_path.exists():
        raise SwiftAdapterError(f"Swift result file was not created: {result_path}")
    lines = [line.strip() for line in result_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise SwiftAdapterError(f"Swift result file is empty: {result_path}")
    for line in reversed(lines):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        extracted = _extract_text_from_result_record(record)
        if extracted:
            return extracted
    raise SwiftAdapterError(f"No assistant content could be extracted from: {result_path}")



def swift_model_adapter(*, prompt: str, image_path: Path, config: dict[str, Any], run_dir: Path) -> str:
    """Run one inference request through a local swift infer wrapper script."""

    script_path = Path(str(config.get("swift_infer_script", PROJECT_ROOT / "train" / "infer.sh")))
    if not script_path.exists():
        raise SwiftAdapterError(f"Swift infer script not found: {script_path}")
    if not image_path.exists():
        raise SwiftAdapterError(f"Image not found for swift inference: {image_path}")

    run_dir.mkdir(parents=True, exist_ok=True)
    request_path = run_dir / "swift_request.jsonl"
    result_path = run_dir / "swift_result.jsonl"
    stdout_path = run_dir / "swift_stdout.log"
    stderr_path = run_dir / "swift_stderr.log"

    sample = build_swift_request_sample(prompt=prompt, image_path=image_path)
    request_path.write_text(json.dumps(sample, ensure_ascii=False) + "\n", encoding="utf-8")
    command = build_swift_infer_command(
        script_path=script_path,
        config=config,
        request_path=request_path,
        result_path=result_path,
    )
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=int(config.get("swift_timeout_seconds", 900)),
        check=False,
    )
    stdout_path.write_text(completed.stdout or "", encoding="utf-8")
    stderr_path.write_text(completed.stderr or "", encoding="utf-8")
    if completed.returncode != 0:
        raise SwiftAdapterError(
            "Swift inference command failed. "
            f"Exit code: {completed.returncode}. stderr: {(completed.stderr or '').strip()}"
        )
    return load_swift_result(result_path)



def call_model(
    *,
    prompt: str,
    image_path: Path,
    user_query: str,
    product_id: str,
    retrieved_rules: list[dict[str, Any]],
    config: dict[str, Any],
    run_dir: Path,
) -> str:
    """Dispatch to the configured model backend."""

    mode = str(config.get("model_mode", "mock")).lower()
    if mode == "mock":
        return mock_model(user_query=user_query, product_id=product_id, retrieved_rules=retrieved_rules)
    if mode == "swift":
        return swift_model_adapter(prompt=prompt, image_path=image_path, config=config, run_dir=run_dir)
    raise ValueError(f"Unsupported model_mode: {mode}")
