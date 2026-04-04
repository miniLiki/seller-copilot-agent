from pathlib import Path

from rag.kb_loader import load_kb_documents
from rag.retrieve import retrieve_rules


KB_DIR = Path(__file__).resolve().parents[1] / "data" / "kb"


def test_kb_loader_loads_markdown_documents() -> None:
    documents = load_kb_documents(KB_DIR)
    assert len(documents) >= 4


def test_retriever_returns_ranked_results() -> None:
    results = retrieve_rules("美国站主图广告文案 clarity", KB_DIR, top_k=3)
    assert len(results) == 3
    assert results[0]["score"] >= results[-1]["score"]
    assert {"source", "chunk_id", "score", "content"}.issubset(results[0])
