"""
Configuration management using pydantic-settings.
Simplified settings for OpenAI LLM, HuggingFace Embeddings, Qdrant, MongoDB.
"""

import os
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # Application
    app_name: str = "AMI RAG System - PTIT Assistant"
    app_port: int = Field(default=6008, ge=1, le=65535)
    debug: bool = False

    # OpenAI (Only LLM Provider)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # Firecrawl (Web Scraping)
    firecrawl_api_key: str = os.getenv("FIRECRAWL_API_KEY", "")

    # MongoDB Configuration (Document & User Management)
    mongodb_url: str | None = None  # If set, this takes precedence
    mongodb_host: str = Field(default="localhost")
    mongodb_port: int = Field(default=27017, ge=1, le=65535)
    mongodb_user: str = Field(default=os.getenv("MONGO_USER", "admin"))
    mongodb_password: str = Field(default=os.getenv("MONGO_PASSWORD", "admin_password"))
    mongodb_db: str = Field(default=os.getenv("MONGO_DB", "ami_db"))

    # Redis Configuration (Caching)
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_password: str = Field(default="redis_password")
    redis_db: int = Field(default=0, ge=0)
    redis_max_connections: int = Field(default=50, ge=1)

    # Qdrant Configuration (Vector Store)
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333, ge=1, le=65535)
    qdrant_grpc_port: int = Field(default=6334, ge=1, le=65535)
    qdrant_api_key: str = Field(default="himlam")
    qdrant_collection_name: str = Field(default="ami_documents")

    # MinIO Configuration (File Storage)
    minio_endpoint: str = Field(default="localhost:9000")
    minio_access_key: str = Field(default=os.getenv("MINIO_ACCESS_KEY", "admin"))
    minio_secret_key: str = Field(default=os.getenv("MINIO_SECRET_KEY", "admin_password"))
    minio_bucket: str = Field(default="ami")  # Main bucket
    minio_secure: bool = Field(default=False)  # Use HTTPS if True

    # Embedding Model (HuggingFace for Vietnamese)
    huggingface_embedding_model: str = os.getenv(
        "HUGGINGFACE_EMBEDDING_MODEL", "keepitreal/vietnamese-sbert"
    )
    embedding_dimension: int = 768  # HuggingFace model dimension

    # OpenAI Models for Thinking Modes
    openai_model_fast: str = os.getenv("OPENAI_MODEL_FAST", "gpt-4-1106-preview")
    openai_model_balance: str = os.getenv("OPENAI_MODEL_BALANCE", "gpt-4-0125-preview")
    openai_model_thinking: str = os.getenv("OPENAI_MODEL_THINKING", "o4-mini")

    # Chunking Configuration
    chunk_size: int = Field(default=512, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)

    # RAG Configuration
    retrieval_top_k: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    # Cache Configuration
    cache_ttl: int = Field(default=3600, ge=0)  # seconds
    enable_cache: bool = True

    # Authentication & Security
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=1440, ge=1)  # 24 hours

    # CORS
    cors_origins: str = Field(default="http://localhost:6009,http://localhost:6010,http://localhost:6008")
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    def get_mongodb_url(self) -> str:
        """MongoDB connection URL with auth database."""
        # Prioritize MONGODB_URL env var (for Docker), fallback to constructed URL
        if self.mongodb_url:
            return self.mongodb_url
        return f"mongodb://{self.mongodb_user}:{self.mongodb_password}@{self.mongodb_host}:{self.mongodb_port}/?authSource=admin"

    @property
    def redis_url(self) -> str:
        """Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def qdrant_url(self) -> str:
        """Qdrant HTTP API URL."""
        return f"http://{self.qdrant_host}:{self.qdrant_port}"


settings = Settings()
