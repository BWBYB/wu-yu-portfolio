from fastapi import FastAPI

from app.models import ChatRequest, ChatResponse


app = FastAPI(title="Wu Yu Personal Knowledge Agent")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Placeholder endpoint; model integration is added in a later task."""
    return ChatResponse(
        answer=f"已收到问题：{request.message}",
        sources=[],
        mode="remote",
    )
