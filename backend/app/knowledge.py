from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re


@dataclass(frozen=True)
class KnowledgeDocument:
    source: str
    content: str


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    source: str
    heading: str
    content: str


_DOCUMENTS = (
    ("个人资料", "knowledge/profile.md"),
    ("SPMTrack 项目资料", "knowledge/spmtrack.md"),
)


def load_knowledge() -> list[KnowledgeDocument]:
    repository_root = Path(__file__).resolve().parents[2]
    return [
        KnowledgeDocument(source=source, content=(repository_root / relative_path).read_text(encoding="utf-8"))
        for source, relative_path in _DOCUMENTS
    ]


_HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+?)\s*$")
_SPLIT_MARKERS = "。；;"
_MAX_CHUNK_CHARS = 900


@lru_cache(maxsize=8)
def build_chunks(documents: tuple[KnowledgeDocument, ...]) -> tuple[KnowledgeChunk, ...]:
    """Convert Markdown documents into stable, bounded semantic chunks."""
    chunks: list[KnowledgeChunk] = []
    source_indexes: dict[str, int] = {}
    for document in documents:
        heading = ""
        paragraph: list[str] = []

        def flush_paragraph() -> None:
            nonlocal paragraph
            content = "\n".join(paragraph).strip()
            paragraph = []
            if not content:
                return
            for part in _split_content(content):
                index = source_indexes.get(document.source, 0)
                source_indexes[document.source] = index + 1
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"{document.source}:{index}",
                        source=document.source,
                        heading=heading,
                        content=part,
                    )
                )

        for line in document.content.splitlines():
            heading_match = _HEADING_PATTERN.match(line.strip())
            if heading_match:
                flush_paragraph()
                heading = heading_match.group(1)
            elif line.strip():
                paragraph.append(line.strip())
            else:
                flush_paragraph()
        flush_paragraph()
    return tuple(chunks)


def _split_content(content: str) -> list[str]:
    parts: list[str] = []
    remaining = content.strip()
    while len(remaining) > _MAX_CHUNK_CHARS:
        boundary = max(remaining.rfind(marker, 0, _MAX_CHUNK_CHARS + 1) for marker in _SPLIT_MARKERS)
        if boundary < 1:
            boundary = _MAX_CHUNK_CHARS
            end = boundary
        else:
            end = boundary + 1
        parts.append(remaining[:end].strip())
        remaining = remaining[end:].strip()
    if remaining:
        parts.append(remaining)
    return parts
