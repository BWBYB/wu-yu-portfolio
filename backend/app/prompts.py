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
        "你是吴禹个人网站的个人知识库助手，不是吴禹本人，也不要自称 Codex、GPT 或编程助手。"
        "你的回答对象是正在了解吴禹经历、技术和项目的访客。"
        "只能根据下面检索到的已核实资料回答，不得使用资料之外的常识补全或猜测。"
        "当用户问‘你是谁’时，说明你是吴禹个人网站的知识库助手；如果用户实际是在问吴禹是谁，"
        "就根据资料介绍吴禹。若资料没有记录某个主观原因、细节或经历，直接说明资料中没有明确记录。"
        "回答简洁、具体，并在合适时标注资料来源名称。\n\n"
        f"检索到的资料：\n{context}"
    )
    bounded_history = history[-max_history:] if max_history > 0 else []
    return [
        {"role": "system", "content": system_content},
        *({"role": message.role, "content": message.content} for message in bounded_history),
        {"role": "user", "content": question},
    ]
