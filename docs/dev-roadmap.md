# Seller Copilot Agent Development Roadmap

## 1. Goal

Based on `require`, this roadmap splits the project into 4 development cycles. The sequencing follows three principles:

1. Deliver a demoable end-to-end loop first.
2. Add training assets and repository conventions second.
3. Add testing, evaluation, and real-model extensibility after the MVP is stable.

This plan is suitable for an interview-style project: prioritize runnable demos, clear structure, and explainability over production complexity.

## 2. Cycle Overview

| Cycle | Theme | Priority Mapping | Main Outcome |
| --- | --- | --- | --- |
| Cycle 1 | MVP skeleton and runnable loop | P0 | Tool service, RAG, agent mock mode, CLI demo, basic README |
| Cycle 2 | Data assets and training preparation | P1 | KB content, dataset samples, scripts, config, AGENTS guide, placeholder assets |
| Cycle 3 | Quality, contracts, and evaluation | P1 + partial P2 | Tests, contract checks, dataset validation, eval scripts, stronger traceability |
| Cycle 4 | Swift integration and project hardening | P2 | Real-model adapter placeholder, training/inference consistency, reproducibility polish |

## 3. Suggested Delivery Rhythm

### Cycle 1

Focus on "can run, can show, can explain".

Exit criterion:

* `uvicorn tools.app:app --reload --port 8000` starts successfully.
* `python -m demo.cli_demo ...` completes successfully in `mock` mode.
* `runs/` saves a minimal trace.

### Cycle 2

Focus on "can train later, can clone and reproduce".

Exit criterion:

* KB files, images, and train/val datasets are complete.
* `scripts/generate_seed_data.py` can generate seed samples.
* `scripts/validate_dataset.py` passes the bundled dataset.

### Cycle 3

Focus on "can verify, can evaluate, can prevent drift".

Exit criterion:

* `pytest -q` passes.
* Schema contract checks cover registry, prompt, and generated dataset.
* `eval/*.py` can output basic metrics.

### Cycle 4

Focus on "can switch from mock to swift without rewriting architecture".

Exit criterion:

* Runtime config clearly controls `mock` and `swift`.
* `train/` scripts and runtime config use aligned template settings.
* README and `train/README.md` explain how to replace the model and adapter.

## 4. Dependency Order

1. `tools/` and `agent/tool_registry.py` must stabilize first because they are the schema source for prompt, runtime, and training.
2. `rag/` must stabilize before CLI demo trace and eval can be trusted.
3. Runtime JSON protocol must stabilize before dataset generation and parser tests.
4. Dataset validation and contract tests should be added before real-model integration, otherwise debugging cost rises quickly.

## 5. Recommended Branch / PR Strategy

* PR 1: repository skeleton + tools + registry + models
* PR 2: RAG + prompt + parser + executor + planner
* PR 3: CLI demo + trace saving + README + env/config
* PR 4: KB/data/scripts/train assets
* PR 5: tests + eval + contract checks
* PR 6: swift adapter + train docs + reproducibility polish

## 6. Risks to Watch

* Schema drift between FastAPI models, tool registry, prompts, and training data
* Inconsistent runtime JSON format between mock mode and future swift mode
* Dataset samples using `<image>` incorrectly
* Trace files missing enough detail for interview demo and debugging
* Overbuilding P2 before the MVP demo is stable

## 7. Final Acceptance Mapping

The project can be considered complete when:

* Cycle 1 guarantees the demo loop.
* Cycle 2 guarantees assets and training preparation.
* Cycle 3 guarantees quality and observability.
* Cycle 4 guarantees extensibility to real inference.

This decomposition keeps the critical path clear while preserving all requirements in `require`.

