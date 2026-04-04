# Training Guide

## Config Alignment

The runtime adapter and the training scripts are aligned around the same keys:

- `MODEL_NAME`
- `ADAPTER_PATH`
- `AGENT_TEMPLATE`
- `TOOLS_PROMPT`
- `SEED`
- `LOAD_ARGS`

`configs/runtime.yaml` is the reference shape for runtime values, while the shell scripts expose the same keys as environment variables or positional arguments.

## LoRA Training

```bash
bash train/sft_lora.sh \
  Qwen/Qwen2.5-VL-7B-Instruct \
  output/seller_copilot_lora \
  qwen2_vl \
  react_en \
  7
```

## Runtime Swift Inference

The runtime adapter calls `train/infer.sh` and writes a one-sample dataset under `runs/<case>/swift_request.jsonl`.

You can also call the script manually:

```bash
bash train/infer.sh \
  Qwen/Qwen2.5-VL-7B-Instruct \
  output/seller_copilot_lora \
  qwen2_vl \
  react_en \
  7 \
  runs/example/swift_request.jsonl \
  runs/example/swift_result.jsonl \
  pt \
  512 \
  0 \
  false
```

## Merge LoRA Weights

```bash
bash train/merge_lora.sh \
  Qwen/Qwen2.5-VL-7B-Instruct \
  output/seller_copilot_lora \
  output/seller_copilot_merged \
  qwen2_vl \
  react_en \
  7 \
  false
```

## Notes

- Keep `MODEL_MODE=mock` as the default for demos without a real checkpoint.
- Switch to `MODEL_MODE=swift` only after `swift` is installed and the adapter path is valid.
- The runtime adapter stores `swift_stdout.log`, `swift_stderr.log`, `swift_request.jsonl`, and `swift_result.jsonl` in the run directory when swift mode is used.
