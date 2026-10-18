from __future__ import annotations

from agentbook_rag.bm25 import BM25Index, tokenize
from agentbook_rag.chunking import Chunk


def make_chunk(index: int, text: str) -> Chunk:
    return Chunk("repo", "commit", "book/chapter1.md", [], index, text, text)


def test_tokenize_keeps_terms_and_makes_chinese_searchable():
    assert tokenize("RRF 融合 LangGraph") == ["rrf", "融", "合", "langgraph"]


def test_bm25_returns_unified_ranked_results():
    index = BM25Index.from_chunks(
        [
            make_chunk(0, "BM25 关键词检索"),
            make_chunk(1, "Dense 语义检索"),
            make_chunk(2, "BM25 和 RRF 融合"),
        ]
    )

    results = index.search("BM25", top_k=2)

    assert {result.chunk.chunk_index for result in results} == {0, 2}
    assert [result.rank for result in results] == [1, 2]
    assert {result.retriever for result in results} == {"bm25"}
    assert all(result.score >= 0 for result in results)
    assert index.search("zzzznotterm") == []


def test_bm25_saves_and_loads(tmp_path):
    index = BM25Index.from_chunks([make_chunk(0, "RRF 融合")])
    index.save(tmp_path)

    loaded = BM25Index.load(tmp_path)
    results = loaded.search("RRF")

    assert results[0].chunk.chunk_index == 0
    assert loaded.manifest["retriever"] == "bm25"
