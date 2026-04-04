from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .chunking import chunk_markdown
from .kb_loader import load_kb_documents

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_\u4e00-\u9fff]+")


def _tokenize(text: str) -> set[str]:
    return {match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)}


def retrieve_rules(
    query: str,
    kb_dir: str | Path,
    *,
    top_k: int = 3,
    category: str | None = None,
    market: str | None = None,
    deterministic: bool = True,
) -> list[dict[str, Any]]:
    documents = load_kb_documents(kb_dir)
    query_text = " ".join(part for part in [query, category or "", market or ""] if part)
    query_tokens = _tokenize(query_text)
    scored_chunks: list[dict[str, Any]] = []
    for document in documents:
        for chunk in chunk_markdown(document["source"], document["content"]):
            chunk_tokens = _tokenize(chunk["content"])
            overlap = query_tokens & chunk_tokens
            score = float(len(overlap))
            if market and market.lower() in chunk["content"].lower():
                score += 0.5
            scored_chunks.append({**chunk, "score": score})
    if deterministic:
        scored_chunks.sort(key=lambda item: (-item["score"], item["source"], item["chunk_id"]))
    else:
        scored_chunks.sort(key=lambda item: -item["score"])
    return scored_chunks[:top_k]


def dump_retrieval_trace(results: list[dict[str, Any]], run_dir: str | Path) -> Path:
    path = Path(run_dir)
    path.mkdir(parents=True, exist_ok=True)
    trace_file = path / "retrieval.json"
    trace_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return trace_file

