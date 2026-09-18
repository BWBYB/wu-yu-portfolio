from collections.abc import Mapping
from typing import Any

from openai import AsyncOpenAI

from .config import Settings


class ConfigurationError(Exception):
    """Raised when the server cannot be configured for model access."""


class ModelUnavailableError(Exception):
    """Raised when the configured model cannot produce an answer."""


async def generate_answer(
    messages: list[dict[str, str]], settings: Settings
) -> str:
    """Generate an answer through the configured OpenAI-compatible provider."""
    if not settings.openai_api_key:
        raise ConfigurationError("model configuration is incomplete")

    client_kwargs: dict[str, Any] = {
        "api_key": settings.openai_api_key,
        "timeout": settings.llm_timeout_seconds,
    }
    if settings.openai_base_url:
        client_kwargs["base_url"] = settings.openai_base_url

    try:
        client = AsyncOpenAI(**client_kwargs)
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
        )
        answer = _extract_text(response)
        if not answer:
            raise ModelUnavailableError("model unavailable")
        return answer.strip()
    except ModelUnavailableError:
        raise
    except Exception as error:
        raise ModelUnavailableError("model unavailable") from error


def _extract_text(response: Any) -> str:
    """Extract the first choice's text without depending on SDK response types."""
    choices = response.get("choices") if isinstance(response, Mapping) else response.choices
    first_choice = choices[0]
    message = (
        first_choice.get("message")
        if isinstance(first_choice, Mapping)
        else first_choice.message
    )
    content = message.get("content") if isinstance(message, Mapping) else message.content
    return content.strip() if isinstance(content, str) else ""
