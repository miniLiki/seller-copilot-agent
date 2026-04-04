#!/usr/bin/env bash
set -eux

source "$(dirname "$0")/common.sh"

MODEL_NAME="${MODEL_NAME:-${1:-$MODEL_NAME_DEFAULT}}"
ADAPTER_PATH="${ADAPTER_PATH:-${2:-$ADAPTER_PATH_DEFAULT}}"
AGENT_TEMPLATE="${AGENT_TEMPLATE:-${3:-$AGENT_TEMPLATE_DEFAULT}}"
TOOLS_PROMPT="${TOOLS_PROMPT:-${4:-$TOOLS_PROMPT_DEFAULT}}"
SEED="${SEED:-${5:-$SEED_DEFAULT}}"
DATASET_PATH="${DATASET_PATH:-${6:-}}"
RESULT_PATH="${RESULT_PATH:-${7:-}}"
INFER_BACKEND="${INFER_BACKEND:-${8:-$INFER_BACKEND_DEFAULT}}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-${9:-$MAX_NEW_TOKENS_DEFAULT}}"
TEMPERATURE="${TEMPERATURE:-${10:-$TEMPERATURE_DEFAULT}}"
LOAD_ARGS="${LOAD_ARGS:-${11:-$LOAD_ARGS_DEFAULT}}"

print_runtime_alignment

echo "INFER_BACKEND=${INFER_BACKEND}"
echo "MAX_NEW_TOKENS=${MAX_NEW_TOKENS}"
echo "TEMPERATURE=${TEMPERATURE}"
echo "LOAD_ARGS=${LOAD_ARGS}"

cmd=(swift infer --model "$MODEL_NAME" --infer_backend "$INFER_BACKEND" --seed "$SEED" --max_new_tokens "$MAX_NEW_TOKENS" --temperature "$TEMPERATURE" --stream false)

if [ -n "$ADAPTER_PATH" ]; then
  cmd+=(--adapters "$ADAPTER_PATH")
fi

if [ -n "$AGENT_TEMPLATE" ]; then
  cmd+=(--agent_template "$AGENT_TEMPLATE")
fi

if [ -n "$DATASET_PATH" ]; then
  cmd+=(--val_dataset "$DATASET_PATH")
fi

if [ -n "$RESULT_PATH" ]; then
  cmd+=(--result_path "$RESULT_PATH")
fi

if [ "$LOAD_ARGS" = "true" ]; then
  cmd+=(--load_args true)
else
  cmd+=(--load_args false)
fi

"${cmd[@]}"
