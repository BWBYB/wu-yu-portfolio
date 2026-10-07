import httpx
import asyncio
import json

from app.config import Settings
from app.dify import DifyConfigurationError, DifyResponseError, run_chatflow


def test_run_chatflow_posts_query_and_user_to_dify() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["json"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "answer": "来自 Agent Book 的回答",
                "conversation_id": "conversation-1",
                "metadata": {
                    "retriever_resources": [
                        {"document_name": "chapter3.md", "score": 0.93}
                    ]
                },
            },
        )

    settings = Settings(
        dify_base_url="http://dify.local",
        dify_api_key="dify-key",
        dify_user="portfolio-user",
    )
    transport = httpx.MockTransport(handler)

    result = asyncio.run(
        run_chatflow(
            message="用户记忆和知识库有什么区别？",
            conversation_id=None,
            settings=settings,
            transport=transport,
        )
    )

    assert captured["url"] == "http://dify.local/v1/chat-messages"
    assert captured["json"] == {
        "inputs": {},
        "query": "用户记忆和知识库有什么区别？",
        "response_mode": "blocking",
        "conversation_id": "",
        "user": "portfolio-user",
    }
    assert result.answer == "来自 Agent Book 的回答"
    assert result.conversation_id == "conversation-1"
    assert result.sources == ["chapter3.md"]


def test_run_chatflow_reuses_conversation_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["conversation_id"] == "conversation-1"
        return httpx.Response(200, json={"answer": "继续回答", "conversation_id": "conversation-1"})

    settings = Settings(
        dify_base_url="http://dify.local",
        dify_api_key="dify-key",
        dify_user="portfolio-user",
    )

    result = asyncio.run(
        run_chatflow(
            message="继续",
            conversation_id="conversation-1",
            settings=settings,
            transport=httpx.MockTransport(handler),
        )
    )

    assert result.conversation_id == "conversation-1"
    assert result.sources == []


def test_run_chatflow_rejects_missing_configuration() -> None:
    try:
        asyncio.run(
            run_chatflow(
                message="测试",
                conversation_id=None,
                settings=Settings(_env_file=None),
                transport=httpx.MockTransport(lambda request: httpx.Response(200)),
            )
        )
    except DifyConfigurationError:
        return
    raise AssertionError("missing Dify configuration should fail")


def test_run_chatflow_rejects_invalid_dify_response() -> None:
    settings = Settings(
        dify_base_url="http://dify.local",
        dify_api_key="dify-key",
        dify_user="portfolio-user",
    )

    try:
        asyncio.run(
            run_chatflow(
                message="测试",
                conversation_id=None,
                settings=settings,
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(200, json={"answer": ""})
                ),
            )
        )
    except DifyResponseError:
        return
    raise AssertionError("invalid Dify response should fail")


def test_run_chatflow_normalizes_legacy_two_chapter_scope_phrase() -> None:
    settings = Settings(
        dify_base_url="http://dify.local",
        dify_api_key="dify-key",
        dify_user="portfolio-user",
    )

    result = asyncio.run(
        run_chatflow(
            message="测试",
            conversation_id=None,
            settings=settings,
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={
                        "answer": "前两章资料未覆盖这个问题。",
                        "conversation_id": "conversation-legacy",
                    },
                )
            ),
        )
    )

    assert result.answer == "前三章资料未覆盖这个问题。"
