# Cycle 1: MVP Skeleton and Runnable Demo Loop

## 1. Objective

Build the smallest complete loop that can be demonstrated end to end:

user input -> image/task ingestion -> rule retrieval -> prompt assembly -> mock model output -> tool execution -> final response -> trace output

This cycle is the highest priority and should avoid all non-essential complexity.

## 2. Scope

### In scope

* `tools/` FastAPI mock service
* `rag/` local KB loading and deterministic retrieval
* `agent/` runtime protocol, prompt assembly, parser, executor, planner
* `demo/cli_demo.py`
* minimal `README.md`
* `requirements.txt`
* minimal `runs/` trace persistence

### Out of scope

* real ms-swift inference
* full dataset generation
* eval scripts
* large-scale tests

## 3. Module Tasks

### `tools/`

Implement:

* `GET /product/{product_id}`
* `GET /inventory/{product_id}`
* `POST /task/create`
* `POST /copy/generate`

Requirements:

* Use Pydantic request/response models.
* Use in-memory mock data only.
* Keep response fields stable.
* Return 404 for missing products.

### `agent/tool_registry.py`

Implement as the single schema source:

* prompt-facing tool schema export
* training-facing tool schema export
* executor map export

This file is the contract center of the whole project and should be locked down early.

### `rag/`

Implement:

* markdown KB loader
* stable paragraph chunking
* deterministic retrieval
* top-k sorted results
* retrieval trace dump

### `agent/models.py`

Define runtime contracts:

* `ToolCall`
* `ModelRuntimeOutput`
* `ToolExecutionRecord`
* `RunTrace`

### `agent/prompt.py`

Implement two prompt builders:

* `runtime_json_prompt`
* `swift_agent_prompt`

The runtime prompt must explicitly require strict JSON output.

### `agent/parser.py`

Implement:

* JSON extraction from raw model output
* schema validation
* normalized parse error structure

### `agent/executor.py`

Implement:

* sequential tool execution
* input/output/error collection
* continue-on-error behavior

### `agent/planner.py`

Implement orchestration:

* validate input
* call retriever
* build prompt
* call `mock_model`
* parse output
* execute tools
* assemble final response
* save trace files

### `demo/cli_demo.py`

Implement a polished CLI entry:

* accepts `--image`, `--product-id`, `--query`
* prints modular sections for interview demo
* supports `--save-trace/--no-save-trace`

## 4. Deliverables

At the end of Cycle 1, the repo should include:

* runnable tool service
* runnable CLI demo in mock mode
* stable runtime JSON contract
* basic KB retrieval
* trace files under `runs/<timestamp>_<case_id>/`

## 5. Acceptance Checklist

* Tool service starts with Uvicorn.
* CLI can complete one full demo case.
* Trace contains at least:
  * `input.json`
  * `retrieval.json`
  * `prompt.txt`
  * `raw_model_output.txt`
  * `parsed_output.json`
  * `tool_results.json`
  * `final_response.txt`
* Mock mode requires no GPU or external model.

## 6. Implementation Notes

* Prefer simple keyword logic for `mock_model()`.
* Stabilize filenames and JSON field names now to reduce future churn.
* Do not block the demo on perfect retrieval quality.
* If a requirement conflicts with delivery speed, choose the simpler implementation that keeps the demo chain intact.

