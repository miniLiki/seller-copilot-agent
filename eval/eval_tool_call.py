from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from agent.parser import parse_model_output
from agent.planner import mock_model


CASES = [
    {
        "product_id": "SKU_001",
        "query": "请创建整改任务并生成两条广告文案",
        "expected_tools": ["create_opt_task", "generate_ad_copy"],
    },
    {
        "product_id": "SKU_002",
        "query": "请创建整改任务",
        "expected_tools": ["create_opt_task"],
    },
]


def main() -> None:
    exact_matches = 0
    name_matches = 0
    total_expected = 0
    for case in CASES:
        raw = mock_model(user_query=case["query"], product_id=case["product_id"], retrieved_rules=[])
        parsed, error = parse_model_output(raw)
        if error:
            continue
        predicted = parsed.tool_calls
        predicted_names = [item.name for item in predicted]
        total_expected += len(case["expected_tools"])
        name_matches += sum(name in predicted_names for name in case["expected_tools"])
        if predicted_names == case["expected_tools"]:
            exact_matches += 1
    result = {
        "tool_name_accuracy": name_matches / total_expected if total_expected else 0.0,
        "argument_exact_match": exact_matches / len(CASES) if CASES else 0.0,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
