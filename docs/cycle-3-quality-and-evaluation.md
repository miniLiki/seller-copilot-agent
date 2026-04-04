# Cycle 3: Quality, Contracts, and Evaluation

## 1. Objective

Add the quality layer that prevents regressions and makes the project credible in an interview or review setting.

## 2. Scope

### In scope

* `tests/test_tools.py`
* `tests/test_retriever.py`
* `tests/test_parser.py`
* `tests/test_contracts.py`
* `eval/eval_tool_call.py`
* `eval/eval_diag.py`
* `eval/eval_e2e.py`
* stronger trace observability

## 3. Testing Strategy

### API tests

Verify:

* product query
* task creation
* ad copy generation
* error behavior for invalid product IDs when needed

### Retriever tests

Verify:

* KB loads correctly
* chunking is stable
* retrieval result count is correct
* result ordering follows score descending

### Parser tests

Verify:

* valid JSON parses successfully
* malformed JSON returns normalized error
* schema-invalid tool calls are rejected cleanly

### Contract tests

Verify:

* FastAPI schemas and registry schemas match
* prompt-exposed tool definitions match registry output
* generated dataset `tools` field matches registry output

Contract tests are especially important because the project explicitly requires a single schema source.

## 4. Evaluation Work Breakdown

### `eval_tool_call.py`

Metrics:

* tool name accuracy
* argument exact match

### `eval_diag.py`

Metrics:

* evidence item hit rate
* final action correctness

### `eval_e2e.py`

Metrics:

* end-to-end success rate

All three scripts should use a small hand-curated sample set and print concise, interpretable outputs.

## 5. Observability Upgrades

Strengthen the trace contract so each run preserves:

* config snapshot
* raw prompt
* raw model output
* parsed output
* tool execution details
* final response

If possible in this cycle, add trace IDs or case IDs that make repeated evaluation easier to compare.

## 6. Deliverables

At the end of Cycle 3, the repository should support both manual demo and machine-verifiable checks.

## 7. Acceptance Checklist

* `pytest -q` passes.
* Contract tests guard against schema drift.
* Eval scripts run independently and report metrics.
* Trace files are sufficient for debugging a failed demo or failed eval case.

## 8. Implementation Notes

* Keep eval logic lightweight; do not over-engineer benchmarking.
* Prefer deterministic fixtures so test failures are actionable.
* If a module is still unstable, lock the contract first before expanding test coverage.

