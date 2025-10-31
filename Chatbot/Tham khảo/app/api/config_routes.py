"""
Configuration and health check API routes.
Provides system status, available models, and provider information.
"""

import logging
from typing import List

from fastapi import APIRouter

from app.application.factory import ProviderFactory
from app.config.settings import settings
from app.core.models import ModelInfo, ProviderStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/models", response_model=List[ModelInfo])
async def config_models():
    """List all available models and their configuration."""
    models = [
        # LLM Models (OpenAI only, with thinking modes)
        ModelInfo(
            name="openai-fast",
            type="llm",
            available=bool(settings.openai_api_key),
        ),
        ModelInfo(
            name="openai-balance",
            type="llm",
            available=bool(settings.openai_api_key),
        ),
        ModelInfo(
            name="openai-thinking",
            type="llm",
            available=bool(settings.openai_api_key),
        ),
        # Embedding (HuggingFace only)
        ModelInfo(name="huggingface", type="embedding", available=True),
        # Vector Store (Qdrant only)
        ModelInfo(name="qdrant", type="vector_store", available=True),
    ]
    return models


@router.get("/providers", response_model=ProviderStatus)
async def config_providers():
    """Get provider status and configuration."""
    return ProviderStatus(
        providers={
            "llm": [
                ModelInfo(
                    name="openai", type="llm", available=bool(settings.openai_api_key)
                ),
            ],
            "embedding": [
                ModelInfo(name="huggingface", type="embedding", available=True),
            ],
            "vector_store": [
                ModelInfo(name="qdrant", type="vector_store", available=True),
            ],
        },
        default_providers={
            "llm": "openai",
            "embedding": "huggingface",
            "vector_store": "qdrant",
        },
    )


@router.get("/health")
async def config_health():
    """Detailed health check with actual database connection tests."""
    health_status = {
        "status": "healthy",
        "providers": {
            "openai": bool(settings.openai_api_key),
            "huggingface": True,
        },
        "databases": {"mongodb": "unknown", "redis": "unknown", "qdrant": "unknown"},
        "services": {
            "llm": "openai",
            "embedding": "huggingface",
            "vector_store": "qdrant",
        },
    }

    # Check MongoDB
    try:
        mongodb_client = await ProviderFactory.get_mongodb_client()
        await mongodb_client.db.command("ping")
        health_status["databases"]["mongodb"] = "ok"
    except Exception as e:
        health_status["databases"]["mongodb"] = f"error: {str(e)[:50]}"
        health_status["status"] = "degraded"

    # Check Redis
    try:
        redis_client = await ProviderFactory.get_redis_client()
        await redis_client.ping()
        health_status["databases"]["redis"] = "ok"
    except Exception as e:
        health_status["databases"]["redis"] = f"error: {str(e)[:50]}"
        health_status["status"] = "degraded"

    # Check Qdrant
    try:
        qdrant_client = await ProviderFactory.get_qdrant_client()
        # Simple health check by getting collections
        await qdrant_client.client.get_collections()
        health_status["databases"]["qdrant"] = "ok"
    except Exception as e:
        health_status["databases"]["qdrant"] = f"error: {str(e)[:50]}"
        health_status["status"] = "degraded"

    return health_status

