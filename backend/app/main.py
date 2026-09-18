from fastapi import Depends, FastAPI, HTTPException

from app.config import Settings, get_settings
from app.models import ChatRequest, ChatResponse


app = FastAPI(title="Wu Yu Personal Knowledge Agent")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    """Placeholder endpoint; model integration is added in a later task."""
    if len(request.message) > settings.max_message_chars:
        raise HTTPException(status_code=422, detail="message exceeds configured limit")
    if len(request.history) > settings.max_history:
        raise HTTPException(status_code=422, detail="history exceeds configured limit")
    return ChatResponse(
        answer=f"已收到问题：{request.message}",
        sources=[],
        mode="remote",
    )
