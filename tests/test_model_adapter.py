from pathlib import Path

from agent.model_adapter import build_swift_infer_command, load_swift_result



def test_build_swift_infer_command_contains_aligned_runtime_values(tmp_path: Path) -> None:
    script_path = tmp_path / "infer.sh"
    request_path = tmp_path / "request.jsonl"
    result_path = tmp_path / "result.jsonl"
    command = build_swift_infer_command(
        script_path=script_path,
        config={
            "model_name": "Qwen/Qwen2.5-VL-7B-Instruct",
            "adapter_path": "output/seller_copilot_lora",
            "agent_template": "qwen2_vl",
            "tools_prompt": "react_en",
            "seed": 7,
            "infer_backend": "pt",
            "max_new_tokens": 512,
            "temperature": 0.0,
            "load_args": False,
        },
        request_path=request_path,
        result_path=result_path,
    )
    assert command[:2] == ["bash", str(script_path)]
    assert str(request_path) in command
    assert str(result_path) in command
    assert "qwen2_vl" in command
    assert "react_en" in command



def test_load_swift_result_extracts_response_field(tmp_path: Path) -> None:
    result_path = tmp_path / "swift_result.jsonl"
    result_path.write_text('{"response": "{\\"final_response\\": \\"ok\\"}"}\n', encoding="utf-8")
    assert load_swift_result(result_path) == '{"final_response": "ok"}'
