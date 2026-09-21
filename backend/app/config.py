from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_api_mode: Literal["chat_completions", "responses"] = "chat_completions"
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:4321"]
    )
    max_history: int = Field(default=8, ge=0)
    max_message_chars: int = Field(default=2000, ge=1)
    llm_timeout_seconds: float = Field(default=30.0, gt=0)
    rag_retrieval: Literal["vector", "lexical", "hybrid"] = "hybrid"
    embedding_model: str = "intfloat/multilingual-e5-small"
    chroma_path: str = "data/chroma"
    vector_collection: str = "wu_yu_knowledge_v2"
    vector_top_k: int = Field(default=4, ge=1, le=8)
    vector_max_distance: float = Field(default=0.096, gt=0)
    embedding_timeout_seconds: float = Field(default=30.0, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
