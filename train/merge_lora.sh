#!/usr/bin/env bash
set -eux

source "$(dirname "$0")/common.sh"

MODEL_NAME="${MODEL_NAME:-${1:-$MODEL_NAME_DEFAULT}}"
ADAPTER_PATH="${ADAPTER_PATH:-${2:-$ADAPTER_PATH_DEFAULT}}"
MERGED_PATH="${MERGED_PATH:-${3:-output/seller_copilot_merged}}"
AGENT_TEMPLATE="${AGENT_TEMPLATE:-${4:-$AGENT_TEMPLATE_DEFAULT}}"
TOOLS_PROMPT="${TOOLS_PROMPT:-${5:-$TOOLS_PROMPT_DEFAULT}}"
SEED="${SEED:-${6:-$SEED_DEFAULT}}"
LOAD_ARGS="${LOAD_ARGS:-${7:-$LOAD_ARGS_DEFAULT}}"

print_runtime_alignment

echo "MERGED_PATH=${MERGED_PATH}"
echo "LOAD_ARGS=${LOAD_ARGS}"

cmd=(swift export --model "$MODEL_NAME" --output_dir "$MERGED_PATH")

if [ -n "$ADAPTER_PATH" ]; then
  cmd+=(--adapters "$ADAPTER_PATH")
fi

if [ "$LOAD_ARGS" = "true" ]; then
  cmd+=(--load_args true)
else
  cmd+=(--load_args false)
fi

cmd+=(--merge_lora true)

"${cmd[@]}"
