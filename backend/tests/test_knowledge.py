from app.knowledge import load_knowledge
from app.models import ChatMessage
from app.prompts import build_messages


def test_load_knowledge_returns_the_two_verified_sources() -> None:
    documents = load_knowledge()

    assert [document.source for document in documents] == ["个人资料", "SPMTrack 项目资料"]
    assert all(document.content.strip() for document in documents)
    assert "2026 届" in documents[0].content
    assert "SPMTrack" in documents[1].content


def test_build_messages_contains_corpus_and_grounding_rule() -> None:
    documents = load_knowledge()

    messages = build_messages(
        question="你做过什么项目？",
        history=[],
        documents=documents,
        max_history=8,
    )

    assert messages[0]["role"] == "system"
    assert "2026 届" in messages[0]["content"]
    assert "SPMTrack" in messages[0]["content"]
    assert "information is unavailable" in messages[0]["content"].lower()
    assert "do not speculate" in messages[0]["content"].lower()
    assert messages[-1] == {"role": "user", "content": "你做过什么项目？"}


def test_build_messages_caps_history_at_explicit_limit() -> None:
    history = [
        ChatMessage(role="user", content="old question"),
        ChatMessage(role="assistant", content="old answer"),
        ChatMessage(role="user", content="recent question"),
    ]

    messages = build_messages(
        question="当前问题",
        history=history,
        documents=load_knowledge(),
        max_history=2,
    )

    assert messages[1:-1] == [
        {"role": "assistant", "content": "old answer"},
        {"role": "user", "content": "recent question"},
    ]
    assert len(messages) == 4
