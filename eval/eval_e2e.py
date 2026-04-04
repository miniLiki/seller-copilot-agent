from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from agent.planner import run_agent


CASES = [
    {
        "image": "data/images/sku_001_main.jpg",
        "product_id": "SKU_001",
        "query": "请分析这张商品主图是否适合美国站投放，如不适合请直接创建整改任务并生成两条广告文案。",
    }
]


def main() -> None:
    success = 0
    for case in CASES:
        trace = run_agent(
            image_path=PROJECT_ROOT / case["image"],
            product_id=case["product_id"],
            user_query=case["query"],
            save_trace=False,
        )
        if trace.parsed_output and trace.final_response:
            success += 1
    result = {"end_to_end_success_rate": success / len(CASES) if CASES else 0.0}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
