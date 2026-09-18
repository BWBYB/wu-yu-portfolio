import logging

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app import main
from app.knowledge import KnowledgeDocument
from app.main import app
from app.models import ChatResponse
from app.llm import ConfigurationError, ModelUnavailableError


client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_health_alias_returns_ok() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_empty_message_is_rejected() -> None:
    response = client.post("/api/chat", json={"message": ""})

    assert response.status_code == 422


def test_oversized_message_is_rejected() -> None:
    response = client.post("/api/chat", json={"message": "a" * 2001})

    assert response.status_code == 422


def test_default_message_limit_rejects_2001_chars() -> None:
    response = client.post("/api/chat", json={"message": "a" * 2001})

    assert response.status_code == 422


def test_custom_settings_limits_are_enforced_at_api_boundary(monkeypatch) -> None:
    custom_settings = Settings(max_message_chars=3, max_history=1)
    app.dependency_overrides[get_settings] = lambda: custom_settings
    async def fake_generate_answer(messages, settings):
        return "测试回答"

    monkeypatch.setattr(main, "generate_answer", fake_generate_answer)
    try:
        accepted = client.post("/api/chat", json={"message": "abc"})
        oversized = client.post("/api/chat", json={"message": "abcd"})
        too_many_history = client.post(
            "/api/chat",
            json={
                "message": "ok",
                "history": [
                    {"role": "user", "content": "one"},
                    {"role": "assistant", "content": "two"},
                ],
            },
        )
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert accepted.status_code == 200
    assert oversized.status_code == 422
    assert too_many_history.status_code == 422


def test_allowed_origins_loads_comma_separated_environment_value(monkeypatch) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:4321, https://example.com")

    settings = Settings(_env_file=None)

    assert settings.allowed_origins == ["http://localhost:4321", "https://example.com"]


def test_chat_response_schema_has_remote_contract() -> None:
    response = ChatResponse(
        answer="回答",
        sources=["个人资料"],
        mode="remote",
    )

    assert response.model_dump() == {
        "answer": "回答",
        "sources": ["个人资料"],
        "mode": "remote",
    }


def test_chat_builds_grounded_messages_and_returns_sources(monkeypatch) -> None:
    captured = {}

    def fake_load_knowledge():
        return [
            KnowledgeDocument(source="个人资料", content="profile-doc"),
            KnowledgeDocument(source="SPMTrack 项目资料", content="spmtrack-doc"),
        ]

    def fake_build_messages(question, history, documents, max_history):
        captured.update(
            question=question,
            history=history,
            documents=documents,
            max_history=max_history,
        )
        return [{"role": "user", "content": question}]

    async def fake_generate_answer(messages, settings):
        captured["messages"] = messages
        return "来自知识库的回答"

    monkeypatch.setattr(main, "load_knowledge", fake_load_knowledge)
    monkeypatch.setattr(main, "build_messages", fake_build_messages)
    monkeypatch.setattr(main, "generate_answer", fake_generate_answer)

    response = client.post(
        "/api/chat",
        json={
            "message": "我是谁？",
            "history": [{"role": "user", "content": "你好"}],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "来自知识库的回答",
        "sources": ["个人资料", "SPMTrack 项目资料"],
        "mode": "remote",
    }
    assert captured["question"] == "我是谁？"
    assert captured["history"][0].content == "你好"
    assert captured["max_history"] == 8


def test_success_log_contains_metadata_without_question_or_answer(monkeypatch, caplog) -> None:
    async def fake_generate_answer(messages, settings):
        return "不会出现在日志里的回答"

    monkeypatch.setattr(main, "generate_answer", fake_generate_answer)
    caplog.set_level(logging.INFO, logger="agent.request")

    response = client.post("/api/chat", json={"message": "不会出现在日志里的问题"})

    assert response.status_code == 200
    messages = "\n".join(record.getMessage() for record in caplog.records if record.name == "agent.request")
    assert '"route": "/api/chat"' in messages
    assert '"status": 200' in messages
    assert '"message_length": 11' in messages
    assert '"history_count": 0' in messages
    assert "不会出现在日志里的问题" not in messages
    assert "不会出现在日志里的回答" not in messages


def test_provider_failure_log_contains_category_without_raw_error(monkeypatch, caplog) -> None:
    async def raise_model_error(messages, settings):
        raise ModelUnavailableError("provider raw response that must stay private")

    monkeypatch.setattr(main, "generate_answer", raise_model_error)
    caplog.set_level(logging.INFO, logger="agent.request")

    response = client.post("/api/chat", json={"message": "测试失败日志"})

    assert response.status_code == 502
    messages = "\n".join(record.getMessage() for record in caplog.records if record.name == "agent.request")
    assert '"error_category": "provider"' in messages
    assert "provider raw response that must stay private" not in messages


def test_missing_model_configuration_returns_stable_503(monkeypatch) -> None:
    async def raise_configuration_error(messages, settings):
        raise ConfigurationError("provider secret details")

    monkeypatch.setattr(main, "generate_answer", raise_configuration_error)

    response = client.post("/api/chat", json={"message": "测试"})

    assert response.status_code == 503
    assert response.json() == {"detail": "模型配置不可用"}
    assert "provider" not in response.text


def test_model_failure_returns_stable_502(monkeypatch) -> None:
    async def raise_model_error(messages, settings):
        raise ModelUnavailableError("provider response details")

    monkeypatch.setattr(main, "generate_answer", raise_model_error)

    response = client.post("/api/chat", json={"message": "测试"})

    assert response.status_code == 502
    assert response.json() == {"detail": "模型服务暂时不可用"}
    assert "provider" not in response.text


def test_cors_exposes_configured_frontend_origin() -> None:
    response = client.options(
        "/api/chat",
        headers={
            "Origin": "http://localhost:4321",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:4321"
