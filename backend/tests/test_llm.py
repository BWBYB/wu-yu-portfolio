import pytest
from pydantic import ValidationError

from app.config import Settings
from app.llm import ConfigurationError, ModelUnavailableError, generate_answer


class FakeEndpoint:
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
    chat_response = None
    chat_error = None
    responses_response = None
    responses_error = None
    close_error = None

    def __init__(self, **kwargs):
        self.constructor_kwargs = kwargs
        self.closed = False
        self.chat = type("Chat", (), {})()
        self.chat.completions = FakeEndpoint(self.chat_response, self.chat_error)
        self.responses = FakeEndpoint(self.responses_response, self.responses_error)
        self.__class__.instances.append(self)

    async def close(self):
        self.closed = True
        if self.close_error is not None:
            raise self.close_error


def chat_response_with_content(content):
    return type(
        "Response",
        (),
        {"choices": [type("Choice", (), {"message": type("Message", (), {"content": content})()})()]},
    )()


def responses_response_with_output_text(content):
    return type("Response", (), {"output_text": content})()


@pytest.fixture
def fake_client(monkeypatch):
    from app import llm

    FakeClient.instances = []
    FakeClient.chat_response = chat_response_with_content("  model answer  ")
    FakeClient.chat_error = None
    FakeClient.responses_response = responses_response_with_output_text(
        "  responses answer  "
    )
    FakeClient.responses_error = None
    FakeClient.close_error = None
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


def test_generate_answer_uses_responses_api_with_system_instructions(fake_client):
    settings = Settings(
        openai_api_key="test-key",
        openai_base_url="https://example.test",
        openai_model="test-model",
        openai_api_mode="responses",
    )
    messages = [
        {"role": "system", "content": "Use only verified facts."},
        {"role": "user", "content": "Earlier question"},
        {"role": "assistant", "content": "Earlier answer"},
        {"role": "user", "content": "Current question"},
    ]

    answer = __import__("asyncio").run(generate_answer(messages, settings))

    assert answer == "responses answer"
    client = fake_client.instances[0]
    assert client.responses.messages == {
        "model": "test-model",
        "instructions": "Use only verified facts.",
        "input": [
            {"role": "user", "content": "Earlier question"},
            {"role": "assistant", "content": "Earlier answer"},
            {"role": "user", "content": "Current question"},
        ],
    }
    assert client.chat.completions.messages is None
    assert client.closed is True


def test_settings_rejects_unknown_api_mode():
    with pytest.raises(ValidationError):
        Settings(openai_api_mode="unknown")


def test_generate_answer_rejects_missing_api_key(monkeypatch):
    settings = Settings(openai_api_key=None)

    with pytest.raises(ConfigurationError):
        __import__("asyncio").run(generate_answer([], settings))


@pytest.mark.parametrize("content", [None, "", "   "])
def test_generate_answer_maps_empty_model_output(fake_client, content):
    fake_client.chat_response = chat_response_with_content(content)
    settings = Settings(openai_api_key="test-key")

    with pytest.raises(ModelUnavailableError, match="model unavailable"):
        __import__("asyncio").run(generate_answer([], settings))
    assert fake_client.instances[0].closed is True


@pytest.mark.parametrize("content", [None, "", "   "])
def test_generate_answer_maps_empty_responses_output(fake_client, content):
    fake_client.responses_response = responses_response_with_output_text(content)
    settings = Settings(openai_api_key="test-key", openai_api_mode="responses")

    with pytest.raises(ModelUnavailableError, match="model unavailable"):
        __import__("asyncio").run(generate_answer([], settings))
    assert fake_client.instances[0].closed is True


def test_generate_answer_maps_provider_exception_without_leaking_text(fake_client):
    fake_client.chat_error = RuntimeError(
        "provider secret response"
    )
    settings = Settings(openai_api_key="test-key")

    with pytest.raises(ModelUnavailableError, match="model unavailable") as error:
        __import__("asyncio").run(generate_answer([], settings))

    assert "provider secret response" not in str(error.value)
    assert fake_client.instances[0].closed is True


def test_generate_answer_maps_responses_exception_without_leaking_text(fake_client):
    fake_client.responses_error = RuntimeError("provider secret response")
    settings = Settings(openai_api_key="test-key", openai_api_mode="responses")

    with pytest.raises(ModelUnavailableError, match="model unavailable") as error:
        __import__("asyncio").run(generate_answer([], settings))

    assert "provider secret response" not in str(error.value)
    assert fake_client.instances[0].closed is True


def test_generate_answer_maps_client_cleanup_failure(fake_client):
    fake_client.close_error = RuntimeError("cleanup secret response")
    settings = Settings(openai_api_key="test-key")

    with pytest.raises(ModelUnavailableError, match="model unavailable") as error:
        __import__("asyncio").run(generate_answer([], settings))

    assert "cleanup secret response" not in str(error.value)
    assert fake_client.instances[0].closed is True
