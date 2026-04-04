# Cycle 2: Data Assets and Training Preparation

## 1. Objective

After the MVP loop is stable, add the assets and scripts that make the repository trainable, reproducible, and friendly for collaboration.

## 2. Scope

### In scope

* `data/kb/*.md`
* `data/train.jsonl`
* `data/val.jsonl`
* `data/images/*`
* `scripts/generate_seed_data.py`
* `scripts/validate_dataset.py`
* `scripts/generate_placeholder_images.py`
* `.env.example`
* `configs/runtime.yaml`
* `AGENTS.md`
* `train/*.sh`
* `train/README.md`

### Out of scope

* full benchmark-quality dataset
* real model training verification on GPU

## 3. Data Work Breakdown

### Knowledge base

Prepare at least four markdown SOP/rule files:

* `sop_ad_creative.md`
* `sop_title_rules.md`
* `sop_detail_page.md`
* `inventory_policy.md`

Each file should contain 3 to 8 rules and be easy for paragraph chunking.

### Training samples

Prepare mixed-format samples covering:

* image diagnosis
* tool-calling Agent format
* runtime JSON stabilization

Dataset constraints:

* train >= 20
* val >= 5
* at least 5 multimodal samples with `<image>`
* most tool-calling samples should use `tool_call` / `tool_response`

## 4. Script Work Breakdown

### `scripts/generate_seed_data.py`

Responsibilities:

* generate 20+ seed examples
* reuse `agent/tool_registry.py`
* cover the required business themes from `require`

### `scripts/validate_dataset.py`

Responsibilities:

* validate `messages`
* validate image path existence
* validate `<image>` count
* validate `tools`
* validate `tool_call` / `tool_response` ordering
* print a readable report with sample indices

### `scripts/generate_placeholder_images.py`

Responsibilities:

* create placeholder local assets so the repo runs after clone
* keep paths aligned with dataset references

## 5. Config and Collaboration Assets

### `.env.example`

Must include:

* `TOOL_BASE_URL`
* `MODEL_MODE`
* `MODEL_NAME`
* `ADAPTER_PATH`
* recommended extras such as `AGENT_TEMPLATE`, `TOOLS_PROMPT`, `SEED`, `RUN_DIR`

### `configs/runtime.yaml`

Must centralize:

* model mode
* template choice
* tools prompt strategy
* adapter path
* seed
* tool base URL
* trace switch

### `AGENTS.md`

Document:

* project goal
* directory meaning
* mock-first principle
* schema single source in `agent/tool_registry.py`
* separation of training protocol and runtime protocol
* safe modification rules for coding assistants

## 6. Deliverables

At the end of Cycle 2, the repo should be cloneable and understandable by another developer without additional explanation.

## 7. Acceptance Checklist

* Dataset files exist and pass validation.
* Placeholder images exist at referenced paths.
* Training shell scripts are executable and clearly parameterized.
* `AGENTS.md` and config files match the actual repo structure.
* Documentation makes it obvious how mock mode and future swift mode fit together.

## 8. Implementation Notes

* Treat `tool_registry.py` as the only source for tool definitions.
* Keep training data protocol and runtime JSON protocol explicitly separate.
* Prefer stable, readable sample quality over synthetic quantity inflation.

