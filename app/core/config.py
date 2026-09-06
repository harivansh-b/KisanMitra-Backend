import json
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Agri Market Linkage Platform"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Supabase Credentials
    SUPABASE_URL: str = "https://mock-project.supabase.co"
    SUPABASE_ANON_KEY: str = "mock-anon-key"
    SUPABASE_SERVICE_ROLE_KEY: str = "mock-service-role-key"
    SUPABASE_JWT_SECRET: Optional[str] = "super-secret-jwt-key-for-local-development-and-testing-32-chars-minimum"
    # Clerk verifies browser-issued session JWTs. This is server-only.
    CLERK_SECRET_KEY: str = ""
    CLERK_JWKS_URL: str = ""
    CLERK_ISSUER: str = ""

    # Database
    DATABASE_URL: str = "sqlite:///./kisanmitra.db"

    # CORS
    # Keep credential-bearing browser requests scoped to known origins.
    # Deployments should set CORS_ORIGINS explicitly.
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    FRONTEND_URL: str = "http://localhost:3000"

    # Optional server-only official market-feed configuration.
    MANDI_API_URL: str = ""
    MANDI_API_KEY: str = ""

    # Storage Buckets
    STORAGE_BUCKET_DOCUMENTS: str = "documents"
    STORAGE_BUCKET_PRODUCE: str = "produce-images"
    STORAGE_BUCKET_PROFILES: str = "profile-images"

    # Chatbot — local LLM (SIH2026 local-first, no API bill)
    ASSISTANT_MODEL: str = "qwen3:8b"
    OLLAMA_HOST: str = "http://localhost:11434"
    BHASHINI_USER_ID: str = ""
    BHASHINI_API_KEY: str = ""

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        return v if isinstance(v, list) else ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
