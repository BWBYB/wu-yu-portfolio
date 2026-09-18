from app.knowledge import KnowledgeChunk
from app.models import ChatMessage


def build_messages(
    question: str,
    history: list[ChatMessage],
    chunks: tuple[KnowledgeChunk, ...],
    max_history: int,
) -> list[dict[str, str]]:
    context = "\n\n".join(
        f"[Source: {chunk.source}]\n[Section: {chunk.heading or '未标注'}]\n{chunk.content.strip()}"
        for chunk in chunks
    )
    if not context:
        context = "(No matching verified context was retrieved.)"
    system_content = (
        "You are a personal knowledge-base assistant. Answer using only the verified context below. "
        "If the information is unavailable in the context, say that it is unavailable and do not speculate. "
        "Keep answers faithful to the source documents and cite the available source names when relevant.\n\n"
        f"Retrieved context:\n{context}"
    )
    bounded_history = history[-max_history:] if max_history > 0 else []
    return [
        {"role": "system", "content": system_content},
        *({"role": message.role, "content": message.content} for message in bounded_history),
        {"role": "user", "content": question},
    ]
