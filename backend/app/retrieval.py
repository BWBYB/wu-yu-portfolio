import re
from types import MappingProxyType

from app.knowledge import KnowledgeChunk


_WORD_PATTERN = re.compile(r"[a-z0-9][a-z0-9_+#.-]*", re.IGNORECASE)
_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]+")
_STOPWORDS = {
    "什么",
    "怎么",
    "如何",
    "目前",
    "关于",
    "可以",
    "一下",
    "以及",
    "已经",
    "进行",
    "其中",
    "这个",
    "那个",
    "你的",
    "我的",
}
_CJK_EDGE_PARTICLES = frozenset("的了在把请和与或不")
_LOW_SIGNAL_TOKENS = frozenset(
    {
        "吴禹",
        "spmtrack",
        "系统",
        "项目",
        "工作",
        "服务",
        "大学",
        "资料",
        "一个",
        "信息",
        "情况",
        "相关",
        "用户",
        "真实",
        "数量",
    }
)
_QUERY_ALIASES = MappingProxyType({
    "英语": ("语言能力", "cet-6"),
    "英语水平": ("语言能力", "cet-6"),
    "求职方向": ("寻找", "岗位"),
    "岗位发展": ("寻找", "岗位"),
    "贡献": ("负责", "参与"),
    "解决什么问题": ("视觉跟踪", "视频目标跟踪", "web 系统"),
    "主要解决": ("视觉跟踪", "视频目标跟踪", "web 系统"),
    "后端": ("spring boot", "fastapi"),
    "组件": ("组成",),
    "多物体追踪": ("多目标", "spmtrack_mot"),
    "容器": ("docker", "容器部署"),
})
_BLOCKED_INTENT_GROUPS = (
    (
        frozenset({"编造", "虚构", "伪造", "强行声称", "直接声称", "编成"}),
        frozenset({"经历", "事实", "结果", "准确率", "奖项", "后端", "算法", "职责", "贡献"}),
    ),
    (
        frozenset({"泄露", "输出", "显示", "返回"}),
        frozenset({"系统提示", "提示词", "隐藏配置", "内部指令", "开发者消息", "密钥"}),
    ),
    (
        frozenset({"读取", "打开", "返回", "贴出"}),
        frozenset({"服务器文件", "本地文件", "主机配置", "配置文件", "任意文件"}),
    ),
)


def retrieve_chunks(
    question: str,
    chunks: tuple[KnowledgeChunk, ...],
    top_k: int = 4,
    min_score: int = 3,
) -> tuple[KnowledgeChunk, ...]:
    """Return the highest-scoring chunks without adding a runtime dependency."""
    if _is_blocked_request(question):
        return ()

    tokens = _expand_tokens(question, _extract_tokens(question))
    if not tokens or top_k <= 0:
        return ()

    scored: list[tuple[int, int, KnowledgeChunk]] = []
    for position, chunk in enumerate(chunks):
        content = chunk.content.lower()
        heading = chunk.heading.lower()
        score = 0
        evidence_match = False
        for token in tokens:
            content_match = token in content
            heading_match = token in heading
            if content_match:
                score += 3
            if heading_match:
                score += 2
            if (content_match or heading_match) and _is_evidence_token(token):
                evidence_match = True
        if evidence_match and score >= min_score:
            scored.append((score, position, chunk))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return tuple(chunk for _, _, chunk in scored[:top_k])


def _extract_tokens(text: str) -> tuple[str, ...]:
    tokens: list[str] = []
    seen: set[str] = set()

    def add(token: str) -> None:
        normalized = token.lower()
        if len(normalized) < 2 or normalized in _STOPWORDS or normalized in seen:
            return
        seen.add(normalized)
        tokens.append(normalized)

    for match in _WORD_PATTERN.finditer(text.lower()):
        add(match.group(0))

    for match in _CJK_PATTERN.finditer(text):
        run = match.group(0)
        for width in (2, 3):
            for index in range(len(run) - width + 1):
                token = run[index : index + width]
                if token[0] in _CJK_EDGE_PARTICLES or token[-1] in _CJK_EDGE_PARTICLES:
                    continue
                add(token)

    return tuple(tokens)


def _expand_tokens(text: str, tokens: tuple[str, ...]) -> tuple[str, ...]:
    """Add auditable corpus terms for a small set of query paraphrases."""
    expanded = list(tokens)
    seen = set(tokens)
    normalized = text.lower()
    for alias, replacements in _QUERY_ALIASES.items():
        if alias not in normalized:
            continue
        for replacement in replacements:
            token = replacement.lower()
            if token not in seen:
                seen.add(token)
                expanded.append(token)
    return tuple(expanded)


def _is_evidence_token(token: str) -> bool:
    return bool(token.strip()) and token.lower() not in _LOW_SIGNAL_TOKENS


def _is_blocked_request(text: str) -> bool:
    normalized = text.lower()
    return any(
        any(action in normalized for action in actions)
        and any(target in normalized for target in targets)
        for actions, targets in _BLOCKED_INTENT_GROUPS
    )
