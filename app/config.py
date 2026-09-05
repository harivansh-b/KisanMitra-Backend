"""Runtime config — Supabase direct Postgres + Ollama local LLM."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    DATABASE_URL: str = "sqlite:///./kisanmitra.db"
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    ASSISTANT_MODEL: str = "qwen3:8b"
    OLLAMA_HOST: str = "http://localhost:11434"
    BHASHINI_USER_ID: str = ""
    BHASHINI_API_KEY: str = ""


settings = Settings()
