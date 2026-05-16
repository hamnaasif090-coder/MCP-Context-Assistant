"""
config.py – centralised settings loaded from .env
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = Field("MCP-Context-Assistant", env="APP_NAME")
    app_version: str = Field("1.0.0", env="APP_VERSION")
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("./logs/app.log", env="LOG_FILE")

    # LLM
    llm_provider: str = Field("anthropic", env="LLM_PROVIDER")   # anthropic | ollama
    llm_model: str = Field("claude-haiku-4-5-20251001", env="LLM_MODEL")
    anthropic_api_key: str = Field("", env="ANTHROPIC_API_KEY")
    ollama_base_url: str = Field("http://localhost:11434", env="OLLAMA_BASE_URL")

    # Embeddings (free local)
    embedding_model: str = Field("all-MiniLM-L6-v2", env="EMBEDDING_MODEL")

    # Vector DB
    chroma_persist_dir: str = Field("./vector_store", env="CHROMA_PERSIST_DIR")
    chroma_collection: str = Field("knowledge_base", env="CHROMA_COLLECTION")

    # Retrieval
    top_k_results: int = Field(5, env="TOP_K_RESULTS")
    similarity_threshold: float = Field(0.3, env="SIMILARITY_THRESHOLD")
    max_context_tokens: int = Field(3000, env="MAX_CONTEXT_TOKENS")
    memory_max_turns: int = Field(10, env="MEMORY_MAX_TURNS")

    # Security
    secret_key: str = Field("dev-secret-key", env="SECRET_KEY")
    internal_api_key: str = Field("dev-secret-key", env="INTERNAL_API_KEY")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
