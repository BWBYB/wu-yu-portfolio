from __future__ import annotations

from .config import Settings, get_settings
from .embeddings import LocalEmbeddingProvider
from .knowledge import build_chunks, load_knowledge
from .vector_store import ChromaVectorStore, resolve_chroma_path


def build_index(settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    documents = load_knowledge()
    chunks = build_chunks(tuple(documents))
    provider = LocalEmbeddingProvider(settings.embedding_model)
    embeddings = provider.embed_documents([chunk.content for chunk in chunks])
    store = ChromaVectorStore(
        str(resolve_chroma_path(settings.chroma_path)),
        settings.vector_collection,
    )
    count = store.rebuild(chunks, embeddings)
    print(f"model={settings.embedding_model}")
    print(f"chunks={count}")
    print(f"path={resolve_chroma_path(settings.chroma_path)}")
    return count


if __name__ == "__main__":
    build_index()
