from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from rag.chunking import chunk_markdown
from rag.kb_loader import load_kb_documents


def main() -> None:
    kb_dir = PROJECT_ROOT / "data" / "kb"
    documents = load_kb_documents(kb_dir)
    chunks = [chunk for doc in documents for chunk in chunk_markdown(doc["source"], doc["content"])]
    print(json.dumps({"documents": len(documents), "chunks": len(chunks)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
