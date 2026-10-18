"""Markdown metadata parsing and fixed-token chunking."""

from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Any, Protocol


class OffsetTokenizer(Protocol):
    def __call__(
        self,
        text: str,
        *,
        add_special_tokens: bool,
        return_offsets_mapping: bool,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class Chunk:
    source_repo: str
    commit: str
    file: str
    heading_path: list[str]
    chunk_index: int
    text: str
    embedding_text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_HEADING_RE = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_PANDOC_ATTR_RE = re.compile(r"[ \t]+\{[^}]+\}[ \t]*$")


def _heading_events(markdown: str) -> list[tuple[int, int, str]]:
    """Return headings outside fenced code as (character position, level, title)."""
    events: list[tuple[int, int, str]] = []
    path_start = 0
    fence_char: str | None = None
    fence_length = 0

    for line in markdown.splitlines(keepends=True):
        line_without_newline = line.rstrip("\r\n")
        fence = _FENCE_RE.match(line_without_newline)
        if fence:
            marker = fence.group(1)
            if fence_char is None:
                fence_char = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_length:
                fence_char = None
                fence_length = 0
            path_start += len(line)
            continue

        if fence_char is None:
            heading = _HEADING_RE.match(line_without_newline)
            if heading:
                title = _PANDOC_ATTR_RE.sub("", heading.group(2)).strip()
                # A heading's path is reconstructed at the chunk boundary.
                events.append((path_start, len(heading.group(1)), title))
        path_start += len(line)

    return events


def heading_path_at(markdown: str, character_position: int) -> list[str]:
    """Resolve the active Markdown heading path at a character position."""
    path: list[str] = []
    for position, level, title in _heading_events(markdown):
        if position > character_position:
            break
        path = path[: level - 1]
        path.append(title)
    return path


def _embedding_context(
    *, source_repo: str, commit: str, file: str, heading_path: list[str], text: str
) -> str:
    heading = " > ".join(heading_path) if heading_path else "(document root)"
    return (
        f"Source repository: {source_repo}\n"
        f"Source commit: {commit}\n"
        f"File: {file}\n"
        f"Heading path: {heading}\n\n"
        f"{text}"
    )


def chunk_markdown(
    markdown: str,
    tokenizer: OffsetTokenizer,
    *,
    source_repo: str,
    commit: str,
    file: str,
    chunk_size: int = 512,
    overlap: int = 64,
) -> list[Chunk]:
    """Split Markdown into fixed tokenizer windows while preserving raw text."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    encoded = tokenizer(
        markdown,
        add_special_tokens=False,
        return_offsets_mapping=True,
    )
    token_ids = encoded["input_ids"]
    offsets = encoded["offset_mapping"]
    if hasattr(token_ids, "tolist"):
        token_ids = token_ids.tolist()
    if hasattr(offsets, "tolist"):
        offsets = offsets.tolist()
    if not token_ids:
        return []
    if len(token_ids) != len(offsets):
        raise ValueError("tokenizer returned mismatched input_ids and offset_mapping")

    step = chunk_size - overlap
    chunks: list[Chunk] = []
    for chunk_index, token_start in enumerate(range(0, len(token_ids), step)):
        token_end = min(token_start + chunk_size, len(token_ids))
        start_char = offsets[token_start][0]
        end_char = offsets[token_end - 1][1]
        if end_char <= start_char:
            raise ValueError("tokenizer returned an empty character span")
        raw_text = markdown[start_char:end_char]
        heading_path = heading_path_at(markdown, start_char)
        chunks.append(
            Chunk(
                source_repo=source_repo,
                commit=commit,
                file=file,
                heading_path=heading_path,
                chunk_index=chunk_index,
                text=raw_text,
                embedding_text=_embedding_context(
                    source_repo=source_repo,
                    commit=commit,
                    file=file,
                    heading_path=heading_path,
                    text=raw_text,
                ),
            )
        )
        if token_end == len(token_ids):
            break
    return chunks
