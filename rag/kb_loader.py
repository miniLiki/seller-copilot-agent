from __future__ import annotations

from pathlib import Path


def load_kb_documents(kb_dir: str | Path) -> list[dict[str, str]]:
    kb_path = Path(kb_dir)
    markdown_files = sorted(kb_path.glob("*.md"))
    if not markdown_files:
        raise FileNotFoundError(f"No markdown knowledge-base files found in: {kb_path}")
    documents: list[dict[str, str]] = []
    for path in markdown_files:
        documents.append({"source": path.name, "content": path.read_text(encoding="utf-8")})
    return documents

