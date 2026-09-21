import pytest
from pydantic import ValidationError

from app.config import Settings


def test_vector_settings_have_local_retrieval_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.rag_retrieval == "hybrid"
    assert settings.embedding_model == "intfloat/multilingual-e5-small"
    assert settings.chroma_path == "data/chroma"
    assert settings.vector_collection == "wu_yu_knowledge_v2"
    assert settings.vector_top_k == 4
    assert settings.vector_max_distance == 0.096
    assert settings.embedding_timeout_seconds == 30.0


def test_vector_settings_reject_unknown_retrieval_mode() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, rag_retrieval="bm25")
