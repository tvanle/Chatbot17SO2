"""
RAG Configuration
Settings for embedding models, LLM, vector store, and chunking
"""
import os
from typing import Optional
from pydantic import BaseModel


class RAGConfig(BaseModel):
    """
    Configuration for RAG system
    Can be loaded from environment variables or .env file
    """

    # ===== Embedding Model Settings =====
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384  # MiniLM dimension

    # Alternative embedding models:
    # - "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2" (384 dim, multilingual)
    # - "sentence-transformers/all-mpnet-base-v2" (768 dim, better quality)
    # - "BAAI/bge-small-en-v1.5" (384 dim, state-of-the-art)
    # - "intfloat/multilingual-e5-base" (768 dim, multilingual)

    # ===== LLM Settings =====
    llm_backend: str = "openai"  # "openai", "anthropic", "local"
    llm_model: str = "gpt-3.5-turbo"
    llm_max_tokens: int = 512
    llm_temperature: float = 0.7
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")

    # LLM model options:
    # OpenAI: "gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"
    # Anthropic: "claude-3-sonnet-20240229", "claude-3-opus-20240229"
    # Local: Path to local model or HuggingFace model ID

    # ===== Vector Store Settings =====
    vector_store_type: str = "database"  # "database", "faiss", "chromadb", "pinecone"
    use_faiss: bool = False  # Enable FAISS for faster search
    vector_store_path: Optional[str] = "./data/vector_store"  # Path for file-based stores

    # ===== Chunking Settings =====
    chunk_size: int = 512  # Characters per chunk
    chunk_overlap: int = 50  # Overlapping characters
    chunk_separator: str = "\n\n"  # Primary separator (paragraphs)

    # ===== Retrieval Settings =====
    default_top_k: int = 10  # Number of chunks to retrieve (increased for better coverage)
    default_token_budget: int = 2000  # Max tokens for context
    similarity_threshold: float = 0.3  # Minimum similarity score (0-1, lowered for broader matching)
    enable_reranking: bool = False  # Enable cross-encoder re-ranking

    # ===== Database Settings =====
    # Inherits from BE.core.config, but can override here
    db_echo: bool = False  # Log SQL queries

    # ===== Other Settings =====
    default_namespace: str = "ptit_docs"  # Default namespace for documents
    answer_language: str = "vi"  # "vi" or "en"
    enable_citations: bool = True  # Include citations in answers

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton instance
_config: Optional[RAGConfig] = None


def get_rag_config() -> RAGConfig:
    """
    Get RAG configuration singleton

    Returns:
        RAGConfig instance
    """
    global _config
    if _config is None:
        _config = RAGConfig()
    return _config


# Example usage:
# from Chatbot.config import get_rag_config
# config = get_rag_config()
# print(config.embedding_model)
