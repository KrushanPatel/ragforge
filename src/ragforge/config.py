"""Settings, read from env vars (prefix ``RAGFORGE_``) and ``.env``.

Task 1a layers YAML files on top of this class; keep it the single config entry point.
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RAGFORGE_", env_file=".env", extra="ignore")

    embed_model: str = "BAAI/bge-small-en-v1.5"
    # bge v1.5 retrieves a little better when short queries carry this instruction.
    embed_query_prefix: str = "Represent this sentence for searching relevant passages: "
    index_dir: Path = Path(".ragforge")
    top_k: int = Field(default=5, ge=1)
    chunk_chars: int = Field(default=800, ge=100)
    chunk_overlap_lines: int = Field(default=2, ge=0)
