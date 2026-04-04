# Cycle 4: Swift Integration and Project Hardening

## 1. Objective

Preserve the mock-first architecture while making the project ready for a future switch to ms-swift inference and LoRA training.

## 2. Scope

### In scope

* `swift` mode runtime adapter placeholder
* training/inference config alignment
* `train/README.md`
* reproducibility polish
* README completion and interview-facing refinement

### Out of scope

* guaranteeing real GPU training in the current environment
* production deployment concerns

## 3. Work Breakdown

### Runtime model abstraction

Define a clean boundary such as:

* `mock_model`
* `swift_model_adapter`
* a shared call interface used by `planner.py`

The key requirement is zero rewrite of the planner when switching model mode.

### Training and inference alignment

Ensure these settings are visible and aligned across scripts and runtime config:

* `agent_template`
* `tools_prompt`
* `seed`
* `adapter_path`
* model name

### Reproducibility

Add:

* fixed default seeds
* config snapshot in `runs/`
* startup logging of critical configuration
* `train/README.md` explaining how to replace the base model and adapter

### README hardening

Complete the final README sections:

* architecture diagram
* install steps
* tool service startup
* CLI demo
* training scripts
* evaluation scripts
* project highlights

## 4. Deliverables

At the end of Cycle 4, the repository should feel complete even if real model execution is still optional in the default environment.

## 5. Acceptance Checklist

* `MODEL_MODE=mock` remains the default and still works.
* `MODEL_MODE=swift` has a documented adapter path and clear interface.
* Training scripts, runtime config, and docs use consistent terminology.
* README is complete enough for third-party reproduction.

## 6. Implementation Notes

* Keep swift integration thin and replaceable.
* Do not let optional real-model support destabilize the interview demo path.
* Any swift-specific complexity should live behind an adapter boundary, not leak into prompt, parser, or tool logic.

