from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.knowledge import load_knowledge
from app.llm import ConfigurationError, ModelUnavailableError, generate_answer
from app.models import ChatRequest, ChatResponse
from app.prompts import build_messages


app = FastAPI(title="Wu Yu Personal Knowledge Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    if len(request.message) > settings.max_message_chars:
        raise HTTPException(status_code=422, detail="message exceeds configured limit")
    if len(request.history) > settings.max_history:
        raise HTTPException(status_code=422, detail="history exceeds configured limit")

    documents = load_knowledge()
    messages = build_messages(
        question=request.message,
        history=request.history,
        documents=documents,
        max_history=settings.max_history,
    )
    try:
        answer = await generate_answer(messages, settings)
    except ConfigurationError as error:
        raise HTTPException(status_code=503, detail="模型配置不可用") from error
    except ModelUnavailableError as error:
        raise HTTPException(status_code=502, detail="模型服务暂时不可用") from error

    return ChatResponse(
        answer=answer,
        sources=[document.source for document in documents],
        mode="remote",
    )
