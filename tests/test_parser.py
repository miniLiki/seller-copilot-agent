from agent.parser import parse_model_output


def test_parse_model_output_accepts_valid_json() -> None:
    payload = '{"task_understanding": "diag", "evidence": ["a"], "need_rag": true, "need_tool_call": false, "tool_calls": [], "final_response": "ok"}'
    parsed, error = parse_model_output(payload)
    assert error is None
    assert parsed is not None
    assert parsed.final_response == "ok"


def test_parse_model_output_rejects_invalid_json() -> None:
    parsed, error = parse_model_output('{invalid json')
    assert parsed is None
    assert error is not None
    assert error["error"] == "MODEL_OUTPUT_PARSE_ERROR"
