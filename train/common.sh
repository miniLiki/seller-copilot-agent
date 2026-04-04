#!/usr/bin/env bash
set -euo pipefail

MODEL_NAME_DEFAULT="Qwen/Qwen2.5-VL-7B-Instruct"
ADAPTER_PATH_DEFAULT="output/seller_copilot_lora"
AGENT_TEMPLATE_DEFAULT="qwen2_vl"
TOOLS_PROMPT_DEFAULT="react_en"
SEED_DEFAULT="7"
INFER_BACKEND_DEFAULT="pt"
MAX_NEW_TOKENS_DEFAULT="512"
TEMPERATURE_DEFAULT="0"
LOAD_ARGS_DEFAULT="false"

print_runtime_alignment() {
  echo "MODEL_NAME=${MODEL_NAME}"
  echo "ADAPTER_PATH=${ADAPTER_PATH}"
  echo "AGENT_TEMPLATE=${AGENT_TEMPLATE}"
  echo "TOOLS_PROMPT=${TOOLS_PROMPT}"
  echo "SEED=${SEED}"
}
