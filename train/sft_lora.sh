#!/usr/bin/env bash
set -eux

source "$(dirname "$0")/common.sh"

MODEL_NAME="${MODEL_NAME:-${1:-$MODEL_NAME_DEFAULT}}"
OUTPUT_DIR="${OUTPUT_DIR:-${2:-output/seller_copilot_lora}}"
AGENT_TEMPLATE="${AGENT_TEMPLATE:-${3:-$AGENT_TEMPLATE_DEFAULT}}"
TOOLS_PROMPT="${TOOLS_PROMPT:-${4:-$TOOLS_PROMPT_DEFAULT}}"
SEED="${SEED:-${5:-$SEED_DEFAULT}}"

print_runtime_alignment

echo "OUTPUT_DIR=${OUTPUT_DIR}"

swift sft \
  --model "$MODEL_NAME" \
  --train_type lora \
  --dataset data/train.jsonl \
  --val_dataset data/val.jsonl \
  --split_dataset_ratio 0.0 \
  --torch_dtype bfloat16 \
  --num_train_epochs 3 \
  --per_device_train_batch_size 1 \
  --gradient_accumulation_steps 8 \
  --learning_rate 1e-4 \
  --lora_rank 8 \
  --lora_alpha 32 \
  --target_modules all-linear \
  --max_length 4096 \
  --remove_unused_columns false \
  --agent_template "$AGENT_TEMPLATE" \
  --output_dir "$OUTPUT_DIR" \
  --seed "$SEED"
