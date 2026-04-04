from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

VALID_TOOL_ROLES = {"tool_call", "tool_response"}


def _parse_tools(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return ast.literal_eval(value)
    raise ValueError("Unsupported tools payload type")


def validate_dataset(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"Missing dataset file: {path}"]
    for index, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        sample = json.loads(raw_line)
        messages = sample.get("messages")
        if not messages:
            errors.append(f"{path.name} line {index}: missing messages")
            continue
        images = sample.get("images", [])
        image_token_count = sum(message.get("content", "").count("<image>") for message in messages)
        if images:
            for image in images:
                image_path = path.parent.parent / image
                if not image_path.exists():
                    errors.append(f"{path.name} line {index}: missing image {image}")
        if image_token_count != len(images):
            errors.append(f"{path.name} line {index}: <image> count {image_token_count} != images {len(images)}")
        if "tools" in sample:
            try:
                _parse_tools(sample["tools"])
            except Exception as exc:
                errors.append(f"{path.name} line {index}: invalid tools payload ({exc})")
        roles = [message.get("role") for message in messages]
        for role_index, role in enumerate(roles):
            if role == "tool_response" and role_index == 0:
                errors.append(f"{path.name} line {index}: tool_response cannot be first")
            if role == "tool_response" and roles[role_index - 1] != "tool_call":
                errors.append(f"{path.name} line {index}: tool_response must follow tool_call")
            if role == "tool_call" and role_index > 0 and roles[role_index - 1] == "tool_response":
                continue
            if role in VALID_TOOL_ROLES and not messages[role_index].get("content"):
                errors.append(f"{path.name} line {index}: empty {role} content")
    return errors


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    dataset_paths = [project_root / "data" / "train.jsonl", project_root / "data" / "val.jsonl"]
    all_errors: list[str] = []
    for dataset_path in dataset_paths:
        all_errors.extend(validate_dataset(dataset_path))
    if all_errors:
        print(json.dumps({"status": "failed", "errors": all_errors}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    print(json.dumps({"status": "ok", "checked": [str(path.name) for path in dataset_paths]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

