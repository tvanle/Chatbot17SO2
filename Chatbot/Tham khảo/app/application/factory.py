"""
Provider factory for creating instances of different providers.
Follows Factory Pattern and Dependency Inversion Principle.
Simplified to only use required providers: OpenAI LLM, HuggingFace Embeddings, Qdrant.
"""

import logging
from typing import Any, Dict

from app.config.settings import settings
from app.core.interfaces import (
    IDocumentProcessor,
    IEmbeddingProvider,
    ILLMProvider,
    ISTTProvider,
    IVectorStore,
)
from app.infrastructure.databases.mongodb_client import MongoDBClient
from app.infrastructure.databases.qdrant_client import QdrantClient
from app.infrastructure.databases.redis_client import RedisClient
from app.infrastructure.embeddings.huggingface_embeddings import HuggingFaceEmbeddings
from app.infrastructure.llms.openai_llm import OpenAILLM
# from app.infrastructure.stt.wav2vec2_stt import Wav2Vec2STT  # Requires rebuild: docker compose build backend
from app.infrastructure.tools.markitdown_processor import MarkItDownProcessor
from app.infrastructure.vector_stores.qdrant_store import QdrantVectorStore

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating and managing provider instances with singleton pattern."""

    _instances: Dict[str, Any] = {}

    @classmethod
    def get_embedding_provider(cls) -> IEmbeddingProvider:
        """
        Get HuggingFace embedding provider instance (singleton).
        Uses Vietnamese document embedding model.

        Returns:
            IEmbeddingProvider instance
        """
        cache_key = "embedding_huggingface"
        if cache_key not in cls._instances:
            logger.info("Creating HuggingFace embedding provider")
            cls._instances[cache_key] = HuggingFaceEmbeddings(
                model_name=settings.huggingface_embedding_model
            )

        return cls._instances[cache_key]

    @classmethod
    def get_llm_provider(cls, model: str = "balance") -> ILLMProvider:
        """
        Get OpenAI LLM provider instance (singleton).
        
        Args:
            model: Thinking mode - 'fast', 'balance', or 'thinking'
                - fast: gpt-4-1106-preview (nano)
                - balance: gpt-4-0125-preview (mini)  
                - thinking: o4-mini (reasoning)

        Returns:
            ILLMProvider instance
        """
        cache_key = f"llm_openai_{model}"
        if cache_key not in cls._instances:
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            
            # Map thinking modes to OpenAI models
            model_map = {
                "fast": "gpt-4-1106-preview",      # GPT-4 Turbo (fast)
                "balance": "gpt-4-0125-preview",   # GPT-4 Turbo (balanced)
                "thinking": "o4-mini"               # O1 Mini (reasoning)
            }
            
            openai_model = model_map.get(model, "gpt-4-0125-preview")
            logger.info(f"Creating OpenAI LLM provider with model: {openai_model}")
            
            cls._instances[cache_key] = OpenAILLM(
                api_key=settings.openai_api_key,
                model=openai_model
            )

        return cls._instances[cache_key]

    @classmethod
    async def get_vector_store(cls) -> IVectorStore:
        """
        Get Qdrant vector store instance (singleton).

        Returns:
            IVectorStore instance
        """
        cache_key = "vector_qdrant"
        if cache_key not in cls._instances:
            logger.info("Creating Qdrant vector store")
            
            # Get QdrantClient
            qdrant_client = await cls.get_qdrant_client()
            store = QdrantVectorStore(
                qdrant_client=qdrant_client,
                collection_name=settings.qdrant_collection_name,
                vector_size=settings.embedding_dimension,
            )
            await store.initialize()
            cls._instances[cache_key] = store

        return cls._instances[cache_key]

    @classmethod
    async def get_redis_client(cls) -> RedisClient:
        """
        Get RedisClient instance (singleton).

        Returns:
            RedisClient instance with connection pool
        """
        if "redis" not in cls._instances:
            logger.info("Creating RedisClient")
            client = RedisClient(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db,
                max_connections=settings.redis_max_connections,
            )
            await client.connect()
            cls._instances["redis"] = client
            logger.info("✓ RedisClient connected")

        return cls._instances["redis"]

    @classmethod
    async def get_qdrant_client(cls) -> QdrantClient:
        """
        Get QdrantClient instance (singleton).

        Returns:
            QdrantClient instance
        """
        if "qdrant" not in cls._instances:
            logger.info("Creating QdrantClient")
            client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                api_key=settings.qdrant_api_key,
            )
            await client.connect()
            cls._instances["qdrant"] = client
            logger.info("✓ QdrantClient connected")

        return cls._instances["qdrant"]

    @classmethod
    async def get_mongodb_client(cls) -> MongoDBClient:
        """
        Get MongoDBClient instance (singleton).

        Returns:
            MongoDBClient instance with connection pool
        """
        if "mongodb" not in cls._instances:
            logger.info("Creating MongoDBClient")
            client = MongoDBClient(
                host=settings.mongodb_host,
                port=settings.mongodb_port,
                user=settings.mongodb_user,
                password=settings.mongodb_password,
                database=settings.mongodb_db,
                connection_url=settings.get_mongodb_url(),
            )
            await client.connect()
            cls._instances["mongodb"] = client
            logger.info("✓ MongoDBClient connected")

        return cls._instances["mongodb"]

    @classmethod
    def get_document_processor(cls) -> IDocumentProcessor:
        """
        Get document processor instance (singleton).

        Returns:
            IDocumentProcessor instance
        """
        if "processor" not in cls._instances:
            logger.info("Creating MarkItDownProcessor")
            cls._instances["processor"] = MarkItDownProcessor()

        return cls._instances["processor"]
    
    # Temporarily disabled - requires backend rebuild with STT dependencies
    # @classmethod
    # def get_stt_provider(cls, model: str = "base") -> ISTTProvider:
    #     """
    #     Get Speech-to-Text provider instance (singleton).
    #     
    #     Args:
    #         model: Model size - 'base' or 'large'
    #             - base: wav2vec2-base-vi-vlsp2020 (faster, smaller)
    #             - large: wav2vec2-large-vi-vlsp2020 (slower, better accuracy)
    #     
    #     Returns:
    #         ISTTProvider instance
    #     """
    #     cache_key = f"stt_wav2vec2_{model}"
    #     if cache_key not in cls._instances:
    #         # Map model size to HuggingFace model name
    #         model_map = {
    #             "base": "nguyenvulebinh/wav2vec2-base-vi-vlsp2020",
    #             "large": "nguyenvulebinh/wav2vec2-large-vi-vlsp2020",
    #         }
    #         
    #         model_name = model_map.get(model, model_map["base"])
    #         logger.info(f"Creating Wav2Vec2STT provider with model: {model_name}")
    #         
    #         from app.infrastructure.stt.wav2vec2_stt import Wav2Vec2STT
    #         cls._instances[cache_key] = Wav2Vec2STT(
    #             model_name=model_name,
    #             lazy_load=True,  # Load model on first use to avoid startup delay
    #         )
    #     
    #     return cls._instances[cache_key]

    @classmethod
    async def cleanup(cls):
        """Cleanup all connections and instances."""
        logger.info("Cleaning up ProviderFactory instances...")

        # Close database connections
        if "mongodb" in cls._instances:
            await cls._instances["mongodb"].disconnect()
            logger.info("✓ MongoDBClient disconnected")

        if "redis" in cls._instances:
            await cls._instances["redis"].disconnect()
            logger.info("✓ RedisClient disconnected")

        if "qdrant" in cls._instances:
            await cls._instances["qdrant"].disconnect()
            logger.info("✓ QdrantClient disconnected")

        # Clear all instances
        cls._instances.clear()
        logger.info("✓ All instances cleared")
