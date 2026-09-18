import json
import logging
import os
import time
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.knowledge import load_knowledge
from app.llm import ConfigurationError, ModelUnavailableError, generate_answer
from app.models import ChatRequest, ChatResponse
from app.prompts import build_messages


app = FastAPI(title="Wu Yu Personal Knowledge Agent")
request_logger = logging.getLogger("agent.request")


@app.middleware("http")
async def log_request_metadata(request: Request, call_next):
    request_id = uuid4().hex
    started_at = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        request.state.error_category = "internal"
        raise
    finally:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        status_code = getattr(locals().get("response"), "status_code", 500)
        error_category = getattr(request.state, "error_category", None)
        if error_category is None:
            error_category = {
                422: "validation",
                429: "rate_limit",
                502: "provider",
                503: "configuration",
            }.get(status_code, "none" if status_code < 400 else "http")
        metadata = {
            "request_id": request_id,
            "environment": os.getenv("VERCEL_ENV", "local"),
            "commit_sha": os.getenv("VERCEL_GIT_COMMIT_SHA"),
            "route": request.url.path,
            "status": status_code,
            "duration_ms": duration_ms,
            "message_length": getattr(request.state, "message_length", None),
            "history_count": getattr(request.state, "history_count", None),
            "sources_count": getattr(request.state, "sources_count", None),
            "error_category": error_category,
        }
        request_logger.info(json.dumps(metadata, ensure_ascii=False, sort_keys=True))
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    http_request.state.message_length = len(request.message)
    http_request.state.history_count = len(request.history)
    if len(request.message) > settings.max_message_chars:
        http_request.state.error_category = "validation"
        raise HTTPException(status_code=422, detail="message exceeds configured limit")
    if len(request.history) > settings.max_history:
        http_request.state.error_category = "validation"
        raise HTTPException(status_code=422, detail="history exceeds configured limit")

    documents = load_knowledge()
    http_request.state.sources_count = len(documents)
    messages = build_messages(
        question=request.message,
        history=request.history,
        documents=documents,
        max_history=settings.max_history,
    )
    try:
        answer = await generate_answer(messages, settings)
    except ConfigurationError as error:
        http_request.state.error_category = "configuration"
        raise HTTPException(status_code=503, detail="模型配置不可用") from error
    except ModelUnavailableError as error:
        http_request.state.error_category = "provider"
        raise HTTPException(status_code=502, detail="模型服务暂时不可用") from error

    return ChatResponse(
        answer=answer,
        sources=[document.source for document in documents],
        mode="remote",
    )
