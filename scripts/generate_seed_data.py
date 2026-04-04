from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from agent.tool_registry import get_tool_schemas_for_training


def build_seed_samples() -> list[dict[str, Any]]:
    tools_json = json.dumps(get_tool_schemas_for_training(), ensure_ascii=False)
    themes = [
        ("SKU_001", "主图主体不突出，需要创建整改任务", True, False),
        ("SKU_001", "卖点不明确，请创建整改任务并生成两条广告文案", True, True),
        ("SKU_002", "主图背景干扰较大，请生成广告文案", False, True),
        ("SKU_002", "存在绝对化用语违规，请创建整改任务", True, False),
        ("SKU_001", "促销信息不一致，请创建整改任务并生成两条广告文案", True, True),
    ]
    samples: list[dict[str, Any]] = []
    for index in range(25):
        product_id, issue, need_task, need_copy = themes[index % len(themes)]
        image_path = f"data/images/{product_id.lower()}_main.jpg"
        messages = [{"role": "user", "content": f"<image> {issue}。商品ID 是 {product_id}。"}]
        if need_task:
            messages.append(
                {
                    "role": "tool_call",
                    "content": json.dumps(
                        {
                            "name": "create_opt_task",
                            "arguments": {
                                "product_id": product_id,
                                "task_type": "creative_refresh",
                                "priority": "high",
                                "reason": issue,
                            },
                        },
                        ensure_ascii=False,
                    ),
                }
            )
            messages.append(
                {
                    "role": "tool_response",
                    "content": json.dumps({"task_id": f"TASK_{index + 1:03d}", "status": "created"}, ensure_ascii=False),
                }
            )
        if need_copy:
            messages.append(
                {
                    "role": "tool_call",
                    "content": json.dumps(
                        {
                            "name": "generate_ad_copy",
                            "arguments": {
                                "product_id": product_id,
                                "market": "US",
                                "angle": "benefit_driven",
                                "num_variants": 2,
                            },
                        },
                        ensure_ascii=False,
                    ),
                }
            )
            messages.append(
                {
                    "role": "tool_response",
                    "content": json.dumps(
                        {"product_id": product_id, "copies": ["copy 1", "copy 2"]},
                        ensure_ascii=False,
                    ),
                }
            )
        messages.append(
            {
                "role": "assistant",
                "content": "已完成诊断，并根据需要执行工单创建和广告文案生成。",
            }
        )
        samples.append({"messages": messages, "images": [image_path], "tools": tools_json})
    return samples


def main() -> None:
    train_path = PROJECT_ROOT / "data" / "train.jsonl"
    val_path = PROJECT_ROOT / "data" / "val.jsonl"
    samples = build_seed_samples()
    train_samples = samples[:20]
    val_samples = samples[20:25]
    train_path.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in train_samples) + "\n", encoding="utf-8")
    val_path.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in val_samples) + "\n", encoding="utf-8")
    print(json.dumps({"train": len(train_samples), "val": len(val_samples)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
