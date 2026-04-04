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
        "query": "请分析这张主图并创建整改任务",
        "expected_evidence": ["主图适配性需要结合主体清晰度、文案合规性和背景干扰度判断。"],
        "expected_phrase": "已准备创建整改工单",
    },
    {
        "query": "请分析这张主图并生成两条广告文案",
        "expected_evidence": ["已检索到 0 条规则片段参与判断。"],
        "expected_phrase": "已准备生成广告文案",
    },
]


def main() -> None:
    evidence_hits = 0
    evidence_total = 0
    action_hits = 0
    for case in CASES:
        raw = mock_model(user_query=case["query"], product_id="SKU_001", retrieved_rules=[])
        parsed, error = parse_model_output(raw)
        if error:
            continue
        evidence_total += len(case["expected_evidence"])
        evidence_hits += sum(item in parsed.evidence for item in case["expected_evidence"])
        if case["expected_phrase"] in parsed.final_response:
            action_hits += 1
    result = {
        "evidence_item_hit_rate": evidence_hits / evidence_total if evidence_total else 0.0,
        "final_action_correctness": action_hits / len(CASES) if CASES else 0.0,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
