"""
FastAPI dependency injection setup.
Implements Dependency Inversion Principle.
"""

from fastapi import Depends, HTTPException

from app.application.factory import ProviderFactory
from app.application.services import DocumentService, RAGService
from app.config.settings import settings


async def get_rag_service(
    embedding_provider: str = None, llm_provider: str = None, vector_store: str = None
) -> RAGService:
    """Get RAG service with specified providers."""
    try:
        embedding_provider = embedding_provider or settings.default_embedding_provider
        llm_provider = llm_provider or settings.default_llm_provider
        vector_store = vector_store or settings.default_vector_store

        embedding = ProviderFactory.get_embedding_provider(embedding_provider)
        llm = ProviderFactory.get_llm_provider(llm_provider)
        vector = await ProviderFactory.get_vector_store(vector_store)
        processor = ProviderFactory.get_document_processor()
        doc_service = DocumentService(processor)

        return RAGService(embedding, llm, vector, doc_service)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize RAG service: {str(e)}"
        )


async def get_document_service() -> DocumentService:
    """Get document service."""
    processor = ProviderFactory.get_document_processor()
    return DocumentService(processor)
