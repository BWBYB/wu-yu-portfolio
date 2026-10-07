from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from .config import Settings


class DifyConfigurationError(Exception):
    """Raised when Dify cannot be called because required settings are missing."""


class DifyUnavailableError(Exception):
    """Raised when the Dify service cannot produce a response."""


class DifyResponseError(Exception):
    """Raised when Dify returns a response outside the expected contract."""


@dataclass(frozen=True)
class DifyChatResult:
    answer: str
    conversation_id: str
    sources: list[str]


async def run_chatflow(
    *,
    message: str,
    conversation_id: str | None,
    settings: Settings,
    transport: httpx.AsyncBaseTransport | None = None,
) -> DifyChatResult:
    if not settings.dify_base_url or not settings.dify_api_key:
        raise DifyConfigurationError("Dify configuration is incomplete")

    url = f"{settings.dify_base_url.rstrip('/')}/v1/chat-messages"
    payload = {
        "inputs": {},
        "query": message,
        "response_mode": "blocking",
        "conversation_id": conversation_id or "",
        "user": settings.dify_user,
    }
    headers = {
        "Authorization": f"Bearer {settings.dify_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(
            timeout=settings.dify_timeout_seconds,
            transport=transport,
        ) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
    except DifyResponseError:
        raise
    except (httpx.HTTPError, ValueError) as error:
        raise DifyUnavailableError("Dify service unavailable") from error

    if not isinstance(data, Mapping):
        raise DifyResponseError("Dify response must be an object")
    answer = data.get("answer")
    returned_conversation_id = data.get("conversation_id")
    if not isinstance(answer, str) or not answer.strip():
        raise DifyResponseError("Dify response has no answer")
    if not isinstance(returned_conversation_id, str):
        raise DifyResponseError("Dify response has no conversation id")

    return DifyChatResult(
        answer=_normalize_answer(answer),
        conversation_id=returned_conversation_id,
        sources=_extract_sources(data.get("metadata")),
    )


def _normalize_answer(answer: str) -> str:
    """Keep the user-facing scope wording aligned with the three-chapter app."""
    return answer.strip().replace("前两章资料未覆盖这个问题", "前三章资料未覆盖这个问题")


def _extract_sources(metadata: Any) -> list[str]:
    if not isinstance(metadata, Mapping):
        return []
    resources = metadata.get("retriever_resources")
    if not isinstance(resources, list):
        return []

    sources: list[str] = []
    for resource in resources:
        if not isinstance(resource, Mapping):
            continue
        name = resource.get("document_name") or resource.get("dataset_name")
        if isinstance(name, str) and name.strip() and name not in sources:
            sources.append(name)
    return sources
