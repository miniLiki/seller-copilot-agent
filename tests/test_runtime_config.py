from pathlib import Path

from agent.planner import get_runtime_summary, load_runtime_config



def test_load_runtime_config_normalizes_types_and_paths(tmp_path: Path) -> None:
    config_path = tmp_path / "runtime.yaml"
    config_path.write_text(
        """
model_mode: swift
seed: "11"
save_run_trace: "false"
load_args: "true"
run_dir: runs
swift_infer_script: train/infer.sh
""".strip(),
        encoding="utf-8",
    )
    config = load_runtime_config(config_path)
    assert config["model_mode"] == "swift"
    assert config["seed"] == 11
    assert config["save_run_trace"] is False
    assert config["load_args"] is True
    assert Path(config["run_dir"]).is_absolute()
    assert Path(config["swift_infer_script"]).is_absolute()



def test_get_runtime_summary_contains_swift_alignment_keys() -> None:
    summary = get_runtime_summary(
        {
            "model_mode": "swift",
            "model_name": "Qwen/Qwen2.5-VL-7B-Instruct",
            "adapter_path": "output/seller_copilot_lora",
            "agent_template": "qwen2_vl",
            "tools_prompt": "react_en",
            "seed": 7,
            "infer_backend": "pt",
            "swift_infer_script": "train/infer.sh",
            "tool_base_url": "http://127.0.0.1:8000",
        }
    )
    assert summary["agent_template"] == "qwen2_vl"
    assert summary["tools_prompt"] == "react_en"
    assert summary["infer_backend"] == "pt"
