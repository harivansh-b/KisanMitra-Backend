"""FastAPI router — POST /chat : DB-aware Q&A over live marketplace tables.

Uses app.core.database.engine (Supabase Postgres + PostGIS; SQLite in tests).
Auto-discovers all tables via schema.py — no hard-coded model list.

Register: already included from app.main (prefix /api/v1, tag chatbot).
Paths:
  POST /api/v1/chat        → DB-aware answer + SQL + rows
  GET  /api/v1/chat/schema → live schema dump
  GET  /api/v1/chat/health → chatbot health
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine

from app.core.database import engine as core_engine  # single source of truth
from .agent import chat_once
from .client import OllamaClient
from .executor import run_query

router = APIRouter()


def get_engine() -> Engine:
    return core_engine


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
        # Keep the assistant useful when the optional local Ollama service is not running.
        # This safe, read-only fallback returns the latest market rows rather than a 502.
        try:
            result = run_query(engine, "SELECT commodity_name, modal_price, arrival_date FROM mandi_prices ORDER BY arrival_date DESC LIMIT 5")
            rows = result.get("rows", [])
            summary = "; ".join(f"{row['commodity_name']}: ₹{row['modal_price']} ({row['arrival_date']})" for row in rows)
            return ChatResponse(answer=f"The full assistant model is temporarily unavailable. Latest market records: {summary or 'no mandi price records found.'}", columns=result.get("columns"), rows=rows, schema_tables=["mandi_prices"])
        except Exception:
            raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        # Log diagnostics server-side without exposing database/provider details.
        print(f"[Chatbot Error] {e}")
        raise HTTPException(status_code=500, detail="The market assistant could not complete that request.") from e
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


@router.get("/chat/health")
def chat_health():
    return {"status": "ok", "service": "kisanmitra-chatbot"}
