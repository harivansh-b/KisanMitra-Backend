"""FastAPI entrypoint: uvicorn app.main:app --reload"""
from fastapi import FastAPI

from app.services.chatbot.router import router as chatbot_router


app = FastAPI(title="KisanMitra API", version="0.1.0",
              description="Market intelligence & price discovery (SIH26132) — chatbot is DB-aware SQL agent.")


@app.get("/health")
def health():
    return {"status": "ok", "service": "kisanmitra", "version": "0.1.0"}


app.include_router(chatbot_router, prefix="/api/v1", tags=["chatbot"])
