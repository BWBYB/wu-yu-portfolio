import re

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


def retrieve_chunks(
    question: str,
    chunks: tuple[KnowledgeChunk, ...],
    top_k: int = 4,
    min_score: int = 3,
) -> tuple[KnowledgeChunk, ...]:
    """Return the highest-scoring chunks without adding a runtime dependency."""
    tokens = _extract_tokens(question)
    if not tokens or top_k <= 0:
        return ()

    scored: list[tuple[int, int, KnowledgeChunk]] = []
    for position, chunk in enumerate(chunks):
        content = chunk.content.lower()
        heading = chunk.heading.lower()
        score = 0
        for token in tokens:
            if token in content:
                score += 3
            if token in heading:
                score += 2
        if score >= min_score:
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
                add(run[index : index + width])

    return tuple(tokens)
