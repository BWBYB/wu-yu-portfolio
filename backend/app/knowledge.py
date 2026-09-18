from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KnowledgeDocument:
    source: str
    content: str


_DOCUMENTS = (
    ("profile", "knowledge/profile.md"),
    ("spmtrack", "knowledge/spmtrack.md"),
)


def load_knowledge() -> list[KnowledgeDocument]:
    repository_root = Path(__file__).resolve().parents[2]
    return [
        KnowledgeDocument(source=source, content=(repository_root / relative_path).read_text(encoding="utf-8"))
        for source, relative_path in _DOCUMENTS
    ]
