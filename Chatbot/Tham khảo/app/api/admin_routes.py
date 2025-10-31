"""
Admin routes for document management.
Protected by JWT authentication - requires ADMIN role.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.api.auth_dependencies import get_current_admin_user
from app.application.factory import ProviderFactory
from app.core.models import ReindexRequest, ReindexResponse
from app.core.mongodb_models import (
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdate,
    UserInDB,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/documents", tags=["admin"])


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    is_active: Optional[bool] = Query(default=None),
    collection: Optional[str] = Query(default=None),
    current_admin: UserInDB = Depends(get_current_admin_user),
):
    """
    List all documents with pagination and filtering.
    Admin only.
    """
    mongodb = await ProviderFactory.get_mongodb_client()
    
    # Get documents
    documents_data = await mongodb.list_documents(
        skip=skip, limit=limit, is_active=is_active
    )
    
    # Filter by collection if specified
    if collection:
        documents_data = [doc for doc in documents_data if doc.get("collection") == collection]
    
    # Count total
    filter_dict = {}
    if is_active is not None:
        filter_dict["is_active"] = is_active
    if collection:
        filter_dict["collection"] = collection
    total = await mongodb.db.documents.count_documents(filter_dict)
    
    documents = [
        DocumentResponse(
            id=doc["_id"],
            filename=doc["filename"],
            collection=doc["collection"],
            file_path=doc.get("file_path"),
            file_size=doc.get("file_size"),
            mime_type=doc.get("mime_type"),
            vector_id=doc.get("vector_id"),
            chunk_count=doc.get("chunk_count", 0),
            metadata=doc.get("metadata", {}),
            is_active=doc["is_active"],
            uploaded_by=doc.get("uploaded_by"),
            created_at=doc["created_at"],
            updated_at=doc.get("updated_at"),
        )
        for doc in documents_data
    ]
    
    return DocumentListResponse(
        documents=documents,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document_endpoint(
    document_id: str,
    current_admin: UserInDB = Depends(get_current_admin_user),
):
    """
    Get document details by ID.
    Admin only.
    """
    mongodb = await ProviderFactory.get_mongodb_client()
    
    document = await mongodb.get_document(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    return DocumentResponse(
        id=document["_id"],
        filename=document["filename"],
        collection=document["collection"],
        file_path=document.get("file_path"),
        file_size=document.get("file_size"),
        mime_type=document.get("mime_type"),
        vector_id=document.get("vector_id"),
        chunk_count=document.get("chunk_count", 0),
        metadata=document.get("metadata", {}),
        is_active=document["is_active"],
        uploaded_by=document.get("uploaded_by"),
        created_at=document["created_at"],
        updated_at=document.get("updated_at"),
    )


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    file: UploadFile = File(...),
    collection: str = Query(default="default"),
    current_admin: UserInDB = Depends(get_current_admin_user),
):
    """
    Upload and process a new document.
    Creates document metadata in MongoDB and vectors in Qdrant.
    Admin only.
    """
    import os
    import tempfile
    from datetime import datetime
    
    mongodb = await ProviderFactory.get_mongodb_client()
    rag_service = await ProviderFactory.get_vector_store()
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=os.path.splitext(file.filename)[1]
    ) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Process document and create vectors
        from app.application.services import DocumentService, RAGService
        
        processor = ProviderFactory.get_document_processor()
        doc_service = DocumentService(processor)
        embedding = ProviderFactory.get_embedding_provider()
        llm = ProviderFactory.get_llm_provider()
        cache = await ProviderFactory.get_redis_client()
        
        rag = RAGService(embedding, llm, rag_service, doc_service, cache)
        
        # Ingest file to vector store
        metadata = {
            "filename": file.filename,
            "collection": collection,
            "uploaded_by": current_admin.username,
        }
        result = await rag.ingest_file(tmp_path, metadata)
        
        # Create document record in MongoDB
        doc_data = {
            "filename": file.filename,
            "collection": collection,
            "file_path": tmp_path,
            "file_size": len(content),
            "mime_type": file.content_type,
            "vector_id": result["doc_ids"][0] if result["doc_ids"] else None,
            "chunk_count": result["chunk_count"],
            "metadata": metadata,
            "is_active": True,
            "uploaded_by": current_admin.username,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        
        doc_id = await mongodb.create_document(doc_data)
        
        # Create vector mapping
        for vector_id in result["doc_ids"]:
            await mongodb.create_vector_mapping(
                vector_id=vector_id,
                document_id=doc_id,
                collection=collection,
            )
        
        # Get created document
        document = await mongodb.get_document(doc_id)
        
        return DocumentResponse(
            id=document["_id"],
            filename=document["filename"],
            collection=document["collection"],
            file_path=document.get("file_path"),
            file_size=document.get("file_size"),
            mime_type=document.get("mime_type"),
            vector_id=document.get("vector_id"),
            chunk_count=document.get("chunk_count", 0),
            metadata=document.get("metadata", {}),
            is_active=document["is_active"],
            uploaded_by=document.get("uploaded_by"),
            created_at=document["created_at"],
            updated_at=document.get("updated_at"),
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}",
        )
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    document_update: DocumentUpdate,
    current_admin: UserInDB = Depends(get_current_admin_user),
):
    """
    Update document metadata (rename, change collection, etc).
    Does not update vector data.
    Admin only.
    """
    from datetime import datetime
    
    mongodb = await ProviderFactory.get_mongodb_client()
    
    # Check if document exists
    existing_doc = await mongodb.get_document(document_id)
    if not existing_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    # Prepare update data
    update_data = {}
    if document_update.filename:
        update_data["filename"] = document_update.filename
    if document_update.collection:
        update_data["collection"] = document_update.collection
    if document_update.metadata:
        update_data["metadata"] = {
            **existing_doc.get("metadata", {}),
            **document_update.metadata,
        }
    
    if update_data:
        update_data["updated_at"] = datetime.now()
        await mongodb.update_document(document_id, update_data)
    
    # Get updated document
    document = await mongodb.get_document(document_id)
    
    return DocumentResponse(
        id=document["_id"],
        filename=document["filename"],
        collection=document["collection"],
        file_path=document.get("file_path"),
        file_size=document.get("file_size"),
        mime_type=document.get("mime_type"),
        vector_id=document.get("vector_id"),
        chunk_count=document.get("chunk_count", 0),
        metadata=document.get("metadata", {}),
        is_active=document["is_active"],
        uploaded_by=document.get("uploaded_by"),
        created_at=document["created_at"],
        updated_at=document.get("updated_at"),
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_document(
    document_id: str,
    current_admin: UserInDB = Depends(get_current_admin_user),
):
    """
    Soft delete a document (mark as inactive).
    Does NOT delete from vector store or database.
    Admin only.
    """
    mongodb = await ProviderFactory.get_mongodb_client()
    vector_store = await ProviderFactory.get_vector_store()
    
    # Check if document exists
    document = await mongodb.get_document(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    # Soft delete in MongoDB
    await mongodb.delete_document(document_id)
    
    # Soft delete associated vectors in Qdrant
    vector_mappings = await mongodb.get_vector_mappings(document_id=document_id)
    vector_ids = [vm["vector_id"] for vm in vector_mappings]
    
    if vector_ids:
        await vector_store.soft_delete(vector_ids)
    
    return None


@router.post("/{document_id}/restore", response_model=DocumentResponse)
async def restore_document(
    document_id: str,
    current_admin: UserInDB = Depends(get_current_admin_user),
):
    """
    Restore a soft-deleted document.
    Admin only.
    """
    from datetime import datetime
    
    mongodb = await ProviderFactory.get_mongodb_client()
    vector_store = await ProviderFactory.get_vector_store()
    
    # Check if document exists
    document = await mongodb.get_document(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    # Restore in MongoDB
    await mongodb.update_document(
        document_id,
        {"is_active": True, "updated_at": datetime.now()}
    )
    
    # Restore associated vectors in Qdrant
    vector_mappings = await mongodb.get_vector_mappings(document_id=document_id)
    vector_ids = [vm["vector_id"] for vm in vector_mappings]
    
    if vector_ids:
        await vector_store.restore(vector_ids)
    
    # Get updated document
    document = await mongodb.get_document(document_id)
    
    return DocumentResponse(
        id=document["_id"],
        filename=document["filename"],
        collection=document["collection"],
        file_path=document.get("file_path"),
        file_size=document.get("file_size"),
        mime_type=document.get("mime_type"),
        vector_id=document.get("vector_id"),
        chunk_count=document.get("chunk_count", 0),
        metadata=document.get("metadata", {}),
        is_active=document["is_active"],
        uploaded_by=document.get("uploaded_by"),
        created_at=document["created_at"],
        updated_at=document.get("updated_at"),
    )


@router.put("/{document_id}/reindex")
async def reindex_document_endpoint(
    document_id: str,
    request: ReindexRequest,
    current_admin: UserInDB = Depends(get_current_admin_user),
):
    """
    Re-index a document with updated embeddings.
    Admin only.
    
    Use cases:
    - Document content changed
    - Change chunking strategy
    - Update metadata
    - Upgrade embedding model
    
    Returns new vector IDs and statistics.
    """
    from datetime import datetime
    
    mongodb = await ProviderFactory.get_mongodb_client()
    
    try:
        # Step 1: Validate document exists
        document = await mongodb.get_document(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        if not document.get("is_active"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot re-index deleted document. Restore it first."
            )
        
        # Step 2: Get file path
        file_path = document.get("file_path")
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document has no file_path. Cannot re-index."
            )
        
        # Check file exists
        import os
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File not found: {file_path}"
            )
        
        # Step 3: Get old vector mappings
        vector_mappings = await mongodb.get_vector_mappings(document_id=document_id)
        old_vector_ids = [vm["vector_id"] for vm in vector_mappings]
        
        if not old_vector_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No vector mappings found. Document may not be properly ingested."
            )
        
        # Step 4: Prepare metadata
        collection = document.get("collection", "default")
        existing_metadata = document.get("metadata", {})
        
        # Merge metadata if update provided
        if request.update_metadata:
            metadata = {**existing_metadata, **request.update_metadata}
        else:
            metadata = existing_metadata
        
        metadata["reindexed_by"] = current_admin.username
        metadata["reindexed_at"] = datetime.now().isoformat()
        
        # Step 5: Initialize RAG service
        embedding = ProviderFactory.get_embedding_provider()
        llm = ProviderFactory.get_llm_provider()
        vector_store = await ProviderFactory.get_vector_store()
        
        from app.application.services import DocumentService, RAGService
        processor = ProviderFactory.get_document_processor()
        doc_service = DocumentService(processor)
        cache = await ProviderFactory.get_redis_client()
        
        rag_service = RAGService(embedding, llm, vector_store, doc_service, cache)
        
        # Step 6: Re-index
        result = await rag_service.reindex_document(
            document_id=document_id,
            file_path=file_path,
            old_vector_ids=old_vector_ids,
            collection=collection,
            metadata=metadata,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            chunk_strategy=request.chunk_strategy,
        )
        
        # Step 7: Update MongoDB mappings
        # Delete old mappings
        await mongodb.db.vector_mappings.delete_many({"document_id": document_id})
        
        # Create new mappings
        for i, vector_id in enumerate(result["new_vector_ids"]):
            await mongodb.create_vector_mapping(
                vector_id=vector_id,
                document_id=document_id,
                collection=collection,
                metadata={"chunk_index": i}
            )
        
        # Step 8: Update document in MongoDB
        await mongodb.update_document(document_id, {
            "chunk_count": result["new_chunk_count"],
            "updated_at": datetime.now(),
            "metadata": metadata,
        })
        
        logger.info(
            f"Re-indexed document {document_id}: "
            f"{result['old_chunk_count']} -> {result['new_chunk_count']} chunks"
        )
        
        # Return response
        return ReindexResponse(
            success=True,
            document_id=document_id,
            old_chunk_count=result["old_chunk_count"],
            new_chunk_count=result["new_chunk_count"],
            old_vector_ids=result["old_vector_ids"],
            new_vector_ids=result["new_vector_ids"],
            processing_time_seconds=result["processing_time_seconds"],
            collection=collection,
            message=f"Document re-indexed successfully. Chunks: {result['old_chunk_count']} → {result['new_chunk_count']}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to re-index document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Re-indexing failed: {str(e)}"
        )


@router.get("/collections/list", response_model=List[str])
async def list_collections(
    current_admin: UserInDB = Depends(get_current_admin_user),
):
    """
    List all unique collection names.
    Admin only.
    """
    mongodb = await ProviderFactory.get_mongodb_client()
    
    collections = await mongodb.db.documents.distinct("collection")
    return collections

