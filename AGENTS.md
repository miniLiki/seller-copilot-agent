# AGENTS Guide

## Project Goal

Build a mock-first seller copilot agent for hero-image diagnosis, rule retrieval, tool calling, and interview-friendly traces.

## Directory Notes

- `tools/`: FastAPI mock tools.
- `rag/`: local markdown retrieval.
- `agent/`: prompt, parser, planner, executor, runtime models.
- `demo/`: CLI entry.
- `data/`: KB, images, and datasets.
- `train/`: ms-swift scripts and notes.

## Working Rules

- Prefer `mock` mode first; do not break the CLI demo path.
- Treat `agent/tool_registry.py` as the single source of tool schema truth.
- Keep training protocol separate from runtime JSON protocol.
- Preserve stable JSON fields and trace file names.
- Favor simple, readable changes over premature abstraction.

