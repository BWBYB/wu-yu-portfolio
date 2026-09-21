from app.knowledge import KnowledgeChunk, build_chunks, load_knowledge
from app.models import ChatMessage
from app.prompts import build_messages


def test_load_knowledge_returns_the_two_verified_sources() -> None:
    documents = load_knowledge()

    assert [document.source for document in documents] == ["个人资料", "SPMTrack 项目资料"]
    assert all(document.content.strip() for document in documents)
    assert "2026 届" in documents[0].content
    assert "SPMTrack" in documents[1].content


def test_build_messages_contains_only_selected_chunks() -> None:
    selected = (
        KnowledgeChunk("个人资料:0", "个人资料", "技术栈", "React、FastAPI"),
    )

    messages = build_messages(
        question="你的技术栈是什么？",
        history=[],
        chunks=selected,
        max_history=8,
    )

    assert messages[0]["role"] == "system"
    assert "React、FastAPI" in messages[0]["content"]
    assert "SPMTrack" not in messages[0]["content"]
    assert "资料中没有明确记录" in messages[0]["content"]
    assert "不得使用资料之外的常识补全或猜测" in messages[0]["content"]
    assert messages[-1] == {"role": "user", "content": "你的技术栈是什么？"}


def test_build_messages_preserves_grounding_rule_without_matches() -> None:
    messages = build_messages(
        question="你最喜欢什么颜色？",
        history=[],
        chunks=(),
        max_history=8,
    )

    assert "React" not in messages[0]["content"]
    assert "资料中没有明确记录" in messages[0]["content"]


def test_build_messages_defines_website_assistant_identity() -> None:
    messages = build_messages(
        question="你是谁？",
        history=[],
        chunks=(
            KnowledgeChunk(
                "个人资料:0",
                "个人资料",
                "基本信息",
                "吴禹，2026 届华侨大学计算机科学与技术专业毕业生。",
            ),
        ),
        max_history=8,
    )

    system_content = messages[0]["content"]
    assert "吴禹个人网站" in system_content
    assert "个人知识库助手" in system_content
    assert "不要自称 Codex" in system_content
    assert "只能根据下面检索到的已核实资料" in system_content


def test_build_messages_caps_history_at_explicit_limit() -> None:
    history = [
        ChatMessage(role="user", content="old question"),
        ChatMessage(role="assistant", content="old answer"),
        ChatMessage(role="user", content="recent question"),
    ]

    messages = build_messages(
        question="当前问题",
        history=history,
        chunks=build_chunks(tuple(load_knowledge())),
        max_history=2,
    )

    assert messages[1:-1] == [
        {"role": "assistant", "content": "old answer"},
        {"role": "user", "content": "recent question"},
    ]
    assert len(messages) == 4
