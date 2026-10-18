from agentbook_rag.rewrite import parse_rewrite_response
from agentbook_rag.rewrite import rewrite_query


def test_parse_rewrite_response_limits_and_deduplicates():
    assert parse_rewrite_response(
        '{"queries":["工作流 vs Agent","工作流 vs Agent","第二个","第三个"]}',
        max_rewrites=2,
    ) == ["工作流 vs Agent", "第二个"]


def test_parse_rewrite_response_accepts_fenced_json():
    assert parse_rewrite_response("```json\n{\"queries\": []}\n```") == []


class _FakeCompletions:
    def create(self, **kwargs):
        assert kwargs["messages"][1]["content"] == "问题"
        return {"choices": [{"message": {"content": '{"queries":["改写"]}'}}]}


class _FakeClient:
    def __init__(self):
        self.chat = type("Chat", (), {"completions": _FakeCompletions()})()


def test_rewrite_query_uses_compatible_client():
    assert rewrite_query("问题", client=_FakeClient()) == ["改写"]
