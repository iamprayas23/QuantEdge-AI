"""QuantEdge Application Settings & Configuration"""
import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    ENV: str = os.getenv("ENV", "development")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-quantedge-secret-key-change-in-production-1234567890")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://quant:quantpass@localhost:5432/quantedge")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    USE_IN_MEMORY_QUEUE: bool = os.getenv("USE_IN_MEMORY_QUEUE", "true").lower() in ("true", "1")

    DEFAULT_SYMBOL: str = os.getenv("DEFAULT_SYMBOL", "XAUUSD")
    DEFAULT_TIMEFRAME: str = os.getenv("DEFAULT_TIMEFRAME", "1H")
    DATA_DIR: str = os.getenv("DATA_DIR", "./data")

    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    CLOUD_LLM_API_KEY: str = os.getenv("CLOUD_LLM_API_KEY", "")
    CLOUD_LLM_BASE_URL: str = os.getenv("CLOUD_LLM_BASE_URL", "https://api.openai.com/v1")
    CLOUD_LLM_MODEL: str = os.getenv("CLOUD_LLM_MODEL", "gpt-4o-mini")


settings = Settings()
