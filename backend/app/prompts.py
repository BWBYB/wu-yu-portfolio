from app.knowledge import KnowledgeDocument
from app.models import ChatMessage


def build_messages(
    question: str,
    history: list[ChatMessage],
    documents: list[KnowledgeDocument],
    max_history: int,
) -> list[dict[str, str]]:
    corpus = "\n\n".join(
        f"[Source: {document.source}]\n{document.content.strip()}"
        for document in documents
    )
    system_content = (
        "You are a personal knowledge-base assistant. Answer using only the verified corpus below. "
        "If the information is unavailable in the corpus, say that it is unavailable and do not speculate. "
        "Keep answers faithful to the source documents.\n\n"
        f"Verified corpus:\n{corpus}"
    )
    bounded_history = history[-max_history:] if max_history > 0 else []
    return [
        {"role": "system", "content": system_content},
        *({"role": message.role, "content": message.content} for message in bounded_history),
        {"role": "user", "content": question},
    ]
