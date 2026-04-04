from __future__ import annotations

from pathlib import Path


def chunk_markdown(source: str, content: str) -> list[dict[str, str]]:
    normalized = content.replace("\r\n", "\n")
    paragraphs = [part.strip() for part in normalized.split("\n\n") if part.strip()]
    chunks: list[dict[str, str]] = []
    for index, paragraph in enumerate(paragraphs, start=1):
        chunk_id = f"{Path(source).name}:{index:03d}"
        chunks.append({"source": source, "chunk_id": chunk_id, "content": paragraph})
    return chunks

