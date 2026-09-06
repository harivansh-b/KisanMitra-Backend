from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import api_v1_router
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.exceptions import register_exception_handlers
from app.services.crop_service import crop_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Seed initial crops if needed
    try:
        db = SessionLocal()
        count = crop_service.seed_default_crops(db)
        if count > 0:
            print(f"[Startup] Automatically seeded {count} default crops into database.")
        db.close()
    except Exception as e:
        print(f"[Startup Warning] Could not seed crops on startup: {e}")
    yield
    # Shutdown logic if needed


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Agri Market Linkage Platform - Three-Sided Marketplace connecting Farmers, FPOs, and Buyers.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Custom Exception Handlers
register_exception_handlers(app)

# Include API Routers (marketplace + chatbot)
app.include_router(api_v1_router, prefix=settings.API_V1_STR)

# Chatbot — DB-aware SQL agent (auto-discovers all marketplace tables)
from app.services.chatbot.router import router as chatbot_router  # noqa: E402

app.include_router(chatbot_router, prefix=settings.API_V1_STR, tags=["chatbot"])


@app.get("/", tags=["Health"])
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "api_v1": settings.API_V1_STR,
        "status": "online",
    }


@app.get("/health", tags=["Health"])
def health_check():
    db_status = "ok"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "ok" else "degraded",
        "database": db_status,
        "environment": settings.ENVIRONMENT,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
