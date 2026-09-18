from fastapi.testclient import TestClient

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
