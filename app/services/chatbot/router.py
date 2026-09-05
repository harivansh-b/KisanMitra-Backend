"""FastAPI router — POST /chat : DB-aware Q&A.

Include from app.main:  app.include_router(router, prefix="/api/v1", tags=["chatbot"])
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .agent import chat_once
from .client import OllamaClient

router = APIRouter()

# lazy engine — honors DATABASE_URL env, falls back to sqlite dev
_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine
    import os

    url = os.environ.get("DATABASE_URL", "sqlite:///./kisanmitra.db")
    if url.startswith("sqlite"):
        _engine = create_engine(url, connect_args={"check_same_thread": False})
    else:
        _engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)
    return _engine


def get_client() -> OllamaClient:
    return OllamaClient()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[dict] = Field(default_factory=list, description="Prior {role,content} turns")
    language: str = Field(default="auto", description="mr|hi|en|auto")


class ChatResponse(BaseModel):
    answer: str
    sql: str | None = None
    columns: list[str] | None = None
    rows: list[dict] | None = None
    truncated: bool = False
    schema_tables: list[str] = Field(default_factory=list)


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, engine: Engine = Depends(get_engine), client: OllamaClient = Depends(get_client)):  # noqa: B008
    try:
        res = chat_once(engine, client, req.message, req.history)
    except ConnectionError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"chat failed: {e}") from e
    return ChatResponse(
        answer=res["answer"],
        sql=res.get("sql"),
        columns=res.get("columns"),
        rows=res.get("rows"),
        truncated=bool(res.get("truncated")),
        schema_tables=res.get("schema_tables", []),
    )


@router.get("/chat/schema")
def chat_schema(engine: Engine = Depends(get_engine)):  # noqa: B008
    from .schema import get_schema

    return get_schema(engine, force=True)


@router.get("/health")
def health():
    return {"status": "ok", "service": "kisanmitra-chatbot"}
