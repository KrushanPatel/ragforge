from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Override any value in .env with the RAG_ prefix, e.g. RAG_TOP_K=8."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="RAG_", extra="ignore")

    qdrant_path: Path = Path("storage/qdrant")
    collection: str = "ragforge"

    embed_model: str = "BAAI/bge-small-en-v1.5"
    chunk_size: int = 500
    chunk_overlap: int = 80
    top_k: int = 3

    ollama_url: str = "http://localhost:11434"
    llm_model: str = "llama3.1:8b"
    llm_temperature: float = 0.1
    llm_timeout: float = 300.0


settings = Settings()
