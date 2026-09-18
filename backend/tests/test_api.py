from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.models import ChatResponse


client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")

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


def test_custom_settings_limits_are_enforced_at_api_boundary() -> None:
    custom_settings = Settings(max_message_chars=3, max_history=1)
    app.dependency_overrides[get_settings] = lambda: custom_settings
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
