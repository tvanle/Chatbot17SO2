"""
Vector Database API routes.
Handles document upload, search, and management in vector store.
"""

import logging
import os
import tempfile
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.application.factory import ProviderFactory
from app.application.services import DocumentService, RAGService
from app.config.settings import settings
from app.core.models import (
    DatabaseStats,
    DeleteResponse,
    ListDocumentsResponse,
    SearchRequest,
    SearchResponse,
    UploadRequest,
    UploadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vectordb", tags=["vectordb"])


async def get_rag_service() -> RAGService:
    """Get RAG service instance."""
    try:
        embedding = ProviderFactory.get_embedding_provider()
        llm = ProviderFactory.get_llm_provider()
        vector = await ProviderFactory.get_vector_store()
        processor = ProviderFactory.get_document_processor()
        doc_service = DocumentService(processor)
        cache_client = (
            await ProviderFactory.get_redis_client() if settings.enable_cache else None
        )
        return RAGService(embedding, llm, vector, doc_service, cache_client)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize service: {str(e)}"
        )


@router.post("/upload", response_model=UploadResponse)
async def vectordb_upload(request: UploadRequest):
    """
    Upload documents to vector database.

    Options:
    - collection: Organize documents in collections
    - chunk_config: Control chunking strategy and size
    - metadata: Custom metadata for filtering
    """
    try:
        rag_service = await get_rag_service()

        # Override chunk settings
        rag_service.document_service.chunk_size = request.chunk_config.chunk_size
        rag_service.document_service.chunk_overlap = request.chunk_config.chunk_overlap

        # Add collection to metadata
        metadata = {**request.metadata, "collection": request.collection}

        if request.content:
            result = await rag_service.ingest_text(request.content, metadata)
        elif request.file_path:
            result = await rag_service.ingest_file(request.file_path, metadata)
        else:
            raise HTTPException(
                status_code=400, detail="Either content or file_path must be provided"
            )

        return UploadResponse(
            doc_ids=result["doc_ids"],
            chunk_count=result["chunk_count"],
            collection=request.collection,
            message=f"Successfully uploaded {result['chunk_count']} chunks to collection '{request.collection}'",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/file", response_model=UploadResponse)
async def vectordb_upload_file(
    file: UploadFile = File(...),
    collection: str = Query(default="default"),
    chunk_size: int = Query(default=512, ge=100, le=4000),
    chunk_overlap: int = Query(default=50, ge=0, le=500),
):
    """Upload file directly to vector database."""
    try:
        rag_service = await get_rag_service()

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=os.path.splitext(file.filename)[1]
        ) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        metadata = {
            "filename": file.filename,
            "content_type": file.content_type,
            "collection": collection,
        }

        result = await rag_service.ingest_file(tmp_path, metadata)
        os.unlink(tmp_path)

        return UploadResponse(
            doc_ids=result["doc_ids"],
            chunk_count=result["chunk_count"],
            collection=collection,
            message=f"File '{file.filename}' uploaded successfully",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResponse)
async def vectordb_search(request: SearchRequest):
    """
    Search vector database with filters.

    Options:
    - collection: Search specific collection
    - similarity_threshold: Minimum similarity score
    - metadata_filter: Filter by document metadata
    - embedding_provider: Choose embedding model
    """
    try:
        rag_service = await get_rag_service()

        # Get query embedding
        query_embedding = await rag_service.embedding_provider.embed_text(request.query)

        # Search
        results = await rag_service.vector_store.search(
            query_embedding=query_embedding, top_k=request.top_k
        )

        # Filter by collection and threshold
        filtered_results = [
            r
            for r in results
            if r.get("metadata", {}).get("collection") == request.collection
            and r.get("similarity", 0) >= request.similarity_threshold
        ]

        # Apply metadata filter if provided
        if request.metadata_filter:
            filtered_results = [
                r
                for r in filtered_results
                if all(
                    r.get("metadata", {}).get(k) == v
                    for k, v in request.metadata_filter.items()
                )
            ]

        return SearchResponse(
            results=filtered_results,
            count=len(filtered_results),
            metadata={
                "collection": request.collection,
                "top_k": request.top_k,
                "threshold": request.similarity_threshold,
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=ListDocumentsResponse)
async def vectordb_list(
    collection: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    vector_store: Optional[str] = Query(default=None),
):
    """List documents in vector database with pagination."""
    try:
        # This is a simplified version - would need actual implementation in vector stores
        return ListDocumentsResponse(
            documents=[], total_count=0, limit=limit, offset=offset
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{doc_id}", response_model=DeleteResponse)
async def vectordb_delete(
    doc_id: str, vector_store: Optional[str] = Query(default=None)
):
    """Delete document by ID."""
    try:
        vector = await ProviderFactory.get_vector_store()
        await vector.delete([doc_id])

        return DeleteResponse(
            deleted_count=1, message=f"Document {doc_id} deleted successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections", response_model=List[str])
async def vectordb_collections(vector_store: Optional[str] = Query(default=None)):
    """List all collections from vector store."""
    try:
        store = await ProviderFactory.get_vector_store()
        collections = await store.get_collections()
        return collections
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list collections: {str(e)}"
        )


@router.get("/stats", response_model=DatabaseStats)
async def vectordb_stats(
    collection: Optional[str] = Query(default=None),
):
    """Get database statistics with actual counts."""
    try:
        store = await ProviderFactory.get_vector_store()

        # Get stats
        stats = await store.get_stats(collection=collection)

        # Get collections list
        collections = await store.get_collections()

        return DatabaseStats(
            total_documents=stats.get("total_documents", 0),
            total_chunks=stats.get("total_chunks", 0),
            collections=collections,
            vector_store="qdrant",  # Only Qdrant is used now
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

