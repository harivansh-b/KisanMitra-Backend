"""KisanMitra chatbot — DB-aware SQL agent + pgvector RAG.

Local-first: Ollama (qwen3:8b default, swap via ASSISTANT_MODEL env).
Supabase direct Postgres + pgvector. Read-only SELECT.

Usage:
    from app.services.chatbot.router import router
    app.include_router(router, prefix="/api/v1", tags=["chatbot"])
"""
from .agent import chat_once  # noqa: F401
from .client import OllamaClient  # noqa: F401
from .router import router  # noqa: F401

__all__ = ["OllamaClient", "chat_once", "router"]
