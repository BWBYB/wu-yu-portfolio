import pytest

from app.config import Settings
from app.llm import ConfigurationError, ModelUnavailableError, generate_answer


class FakeCompletions:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.messages = None

    async def create(self, **kwargs):
        self.messages = kwargs
        if self.error is not None:
            raise self.error
        return self.response


class FakeClient:
    instances = []
    response = None
    error = None

    def __init__(self, **kwargs):
        self.constructor_kwargs = kwargs
        self.closed = False
        self.chat = type("Chat", (), {})()
        self.chat.completions = FakeCompletions(self.response, self.error)
        self.__class__.instances.append(self)

    async def close(self):
        self.closed = True


def response_with_content(content):
    return type(
        "Response",
        (),
        {"choices": [type("Choice", (), {"message": type("Message", (), {"content": content})()})()]},
    )()


@pytest.fixture
def fake_client(monkeypatch):
    from app import llm

    FakeClient.instances = []
    FakeClient.response = response_with_content("  model answer  ")
    FakeClient.error = None
    monkeypatch.setattr(llm, "AsyncOpenAI", FakeClient)
    return FakeClient


def test_generate_answer_extracts_and_strips_model_text(fake_client):
    settings = Settings(
        openai_api_key="test-key",
        openai_base_url="https://example.test/v1",
        openai_model="test-model",
        llm_timeout_seconds=12.5,
    )

    answer = __import__("asyncio").run(
        generate_answer([{"role": "user", "content": "hello"}], settings)
    )

    assert answer == "model answer"
    client = fake_client.instances[0]
    assert client.constructor_kwargs == {
        "api_key": "test-key",
        "base_url": "https://example.test/v1",
        "timeout": 12.5,
    }
    assert client.chat.completions.messages == {
        "model": "test-model",
        "messages": [{"role": "user", "content": "hello"}],
    }
    assert client.closed is True


def test_generate_answer_rejects_missing_api_key(monkeypatch):
    settings = Settings(openai_api_key=None)

    with pytest.raises(ConfigurationError):
        __import__("asyncio").run(generate_answer([], settings))


@pytest.mark.parametrize("content", [None, "", "   "])
def test_generate_answer_maps_empty_model_output(fake_client, content):
    fake_client.response = response_with_content(content)
    settings = Settings(openai_api_key="test-key")

    with pytest.raises(ModelUnavailableError, match="model unavailable"):
        __import__("asyncio").run(generate_answer([], settings))


def test_generate_answer_maps_provider_exception_without_leaking_text(fake_client):
    fake_client.error = RuntimeError("provider secret response")
    settings = Settings(openai_api_key="test-key")

    with pytest.raises(ModelUnavailableError, match="model unavailable") as error:
        __import__("asyncio").run(generate_answer([], settings))

    assert "provider secret response" not in str(error.value)
