from __future__ import annotations

import re

import pytest

from agentbook_rag.chunking import chunk_markdown, heading_path_at


class WordTokenizer:
    """Small deterministic tokenizer double; each whitespace-delimited word is one token."""

    def __call__(self, text: str, *, add_special_tokens: bool, return_offsets_mapping: bool):
        offsets = [
            [match.start(), match.end()]
            for match in re.finditer(r"\S+", text)
        ]
        return {"input_ids": list(range(len(offsets))), "offset_mapping": offsets}


def test_fixed_window_and_overlap():
    text = " ".join(f"token-{i}" for i in range(700))
    chunks = chunk_markdown(
        text,
        WordTokenizer(),
        source_repo="repo",
        commit="commit",
        file="book/chapter1.md",
        chunk_size=10,
        overlap=2,
    )

    assert len(chunks) == 88
    assert chunks[0].text.split()[:2] == ["token-0", "token-1"]
    assert chunks[1].text.split()[:2] == ["token-8", "token-9"]
    assert chunks[-1].text.split()[-1] == "token-699"


def test_heading_path_ignores_fenced_code():
    text = "# Root\n\n## Section\nbody\n```python\n# not a heading\n```\n### Child\ncontent"
    assert heading_path_at(text, text.index("body")) == ["Root", "Section"]
    assert heading_path_at(text, text.index("# not")) == ["Root", "Section"]
    assert heading_path_at(text, text.index("content")) == ["Root", "Section", "Child"]


def test_chunk_contains_static_embedding_context():
    chunks = chunk_markdown(
        "# Chapter\n\nhello world",
        WordTokenizer(),
        source_repo="bojieli/ai-agent-book",
        commit="abc123",
        file="book/chapter1.md",
        chunk_size=10,
        overlap=1,
    )
    assert chunks[0].heading_path == ["Chapter"]
    assert "Source repository: bojieli/ai-agent-book" in chunks[0].embedding_text
    assert "Source commit: abc123" in chunks[0].embedding_text
    assert "# Chapter" in chunks[0].text


def test_invalid_overlap_is_rejected():
    with pytest.raises(ValueError):
        chunk_markdown("hello", WordTokenizer(), source_repo="r", commit="c", file="f", chunk_size=4, overlap=4)
