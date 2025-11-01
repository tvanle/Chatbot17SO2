"""
RAGController - HTTP endpoints for RAG operations

TOÀN BỘ LOGIC RAG Ở ĐÂY - Controller là nơi xử lý chính
Không cần RAGService trung gian, logic trực tiếp trong controller
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from BE.db.session import get_db
from Chatbot.config.rag_config import get_rag_config
from Chatbot.entities.AnswerRequest import AnswerRequest
from Chatbot.entities.AnswerResult import AnswerResult
from Chatbot.entities.IngestRequest import IngestRequest
from Chatbot.entities.IngestResult import IngestResult
from Chatbot.entities.RetrievalHit import RetrievalHit
from Chatbot.services.VectorizerService import VectorizerService
from Chatbot.services.RetrieverService import RetrieverService
from Chatbot.services.GeneratorService import GeneratorService
from Chatbot.dao.DocumentDAO import DocumentDAO
from Chatbot.dao.ChunkDAO import ChunkDAO
from Chatbot.dao.VectorIndexDAO import VectorIndexDAO
from Chatbot.models.Document import Document
from Chatbot.models.Chunk import Chunk
from Chatbot.utils.chunker import chunk_text
from Chatbot.utils.token_counter import estimate_tokens, fit_within_budget

# Create FastAPI router
router = APIRouter(prefix="/api/rag", tags=["RAG"])


def get_vectorizer_service(request: Request = None):
    """
    Get VectorizerService from app.state
    Falls back to creating new instance if not in app.state (for backward compatibility)
    """
    if request and hasattr(request.app.state, 'vectorizer') and request.app.state.vectorizer:
        return request.app.state.vectorizer
    # Fallback: create new (shouldn't happen if startup ran correctly)
    print("⚠️  WARNING: Creating new VectorizerService (app.state not available)")
    return VectorizerService()


def get_generator_service(request: Request = None, model_name: str = None):
    """
    Get GeneratorService from app.state
    Falls back to creating new instance if not in app.state
    """
    if request and hasattr(request.app.state, 'generator') and request.app.state.generator:
        # Check if model matches
        config = get_rag_config()
        model_to_use = model_name or config.llm_model
        if request.app.state.generator.client.model_name == model_to_use:
            return request.app.state.generator
    # Fallback or different model requested
    print(f"⚠️  WARNING: Creating new GeneratorService (app.state not available or model mismatch)")
    return GeneratorService(model_name=model_name)


@router.post("/answer", response_model=AnswerResult)
async def answer(answer_request: AnswerRequest, request: Request, db: Session = Depends(get_db)):
    """
    Answer endpoint - RAG query flow

    TOÀN BỘ LOGIC RAG PIPELINE Ở ĐÂY:
    1. Vectorize question
    2. Retrieve similar chunks
    3. Generate answer with LLM
    4. Return với citations

    Args:
        answer_request: AnswerRequest with question and parameters
        request: FastAPI Request (for accessing app.state)
        db: Database session

    Returns:
        AnswerResult with generated answer and citations
    """
    try:
        # ===== STEP 1: Vectorize question =====
        vectorizer = get_vectorizer_service(request)
        query_vector = vectorizer.embed(answer_request.question)

        # ===== STEP 2: Retrieve relevant chunks =====
        retriever = RetrieverService(db)
        hits = retriever.search(
            namespace=request.namespace_id,
            query_vector=query_vector,
            top_k=request.top_k,
            filters=None
        )

        if not hits:
            return AnswerResult(
                answer="Xin lỗi, tôi không tìm thấy thông tin liên quan đến câu hỏi của bạn trong cơ sở dữ liệu. "
                       "Bạn có thể hỏi về quy chế đào tạo, thông tin tuyển sinh, hoặc các chính sách của PTIT.",
                citations=[]
            )

        # ===== STEP 3: Fit contexts within token budget =====
        context_texts = [hit.chunk["text"] for hit in hits if hit.chunk]
        contexts = fit_within_budget(context_texts, token_budget=request.token_budget)

        # ===== STEP 4: Generate answer with LLM (dynamic model) =====
        # Enhanced: Now supports conversation history for multi-turn conversations
        generator = get_generator_service(request.model)
        answer_text = generator.generate(
            question=request.question,
            contexts=contexts,
            language="vi",
            conversation_history=request.conversation_history
        )

        # ===== STEP 5: Return result =====
        return AnswerResult(
            answer=answer_text,
            citations=hits
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing answer request: {str(e)}")


@router.post("/ingest", response_model=IngestResult)
async def ingest(ingest_request: IngestRequest, request: Request, db: Session = Depends(get_db)):
    """
    Ingest endpoint - Document ingestion flow

    Sequence (from kichban.txt):
    1. Upsert document to DB
    2. Split content into chunks
    3. Insert chunks to DB
    4. Embed chunks (batch)
    5. Upsert vectors to vector index
    6. Return result

    Args:
        request: IngestRequest with document data
        db: Database session

    Returns:
        IngestResult with doc_id and chunk_count
    """
    try:
        # Step 1: Upsert document (Sequence diagram line 12-13)
        doc_dao = DocumentDAO(db)
        document = Document(
            source_uri=request.namespace_id,  # Using namespace as source_uri for now
            title=request.document_title,
            text=request.content
        )
        doc_id = doc_dao.upsert(document)

        # Step 2-3: Split content into chunks (Sequence diagram line 15-16)
        config = get_rag_config()
        chunk_texts = chunk_text(
            request.content,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap
        )

        # Step 4-6: Create and insert chunks (Sequence diagram line 18-22)
        chunk_dao = ChunkDAO(db)
        chunks = []
        for idx, text in enumerate(chunk_texts):
            chunk = Chunk(
                document_id=doc_id,
                idx=idx,
                text=text,
                tokens=estimate_tokens(text)
            )
            chunk_id = chunk_dao.insert(chunk)
            chunk.id = chunk_id  # Update with generated ID
            chunks.append(chunk)

        # Step 7-8: Embed chunks in batch (Sequence diagram line 24-25)
        chunk_texts_list = [chunk.text for chunk in chunks]
        vectorizer = get_vectorizer_service(request)  # Sử dụng singleton
        vectors = vectorizer.embed_batch(chunk_texts_list)

        # Step 9-10: Upsert vectors to index (Sequence diagram line 27-28)
        vidx = VectorIndexDAO(db)
        pairs = [(chunk.id, vector) for chunk, vector in zip(chunks, vectors)]
        vidx.upsert(ingest_request.namespace_id, pairs)

        # Step 11: Return result (Sequence diagram line 30)
        return IngestResult(
            doc_id=doc_id,
            chunk_count=len(chunks)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing ingest request: {str(e)}")


@router.get("/documents")
async def list_documents(limit: int = 10, offset: int = 0, db: Session = Depends(get_db)):
    """
    List all documents with pagination

    Args:
        limit: Max results per page
        offset: Starting position
        db: Database session

    Returns:
        List of documents
    """
    try:
        doc_dao = DocumentDAO(db)
        documents = doc_dao.find_all(limit=limit, offset=offset)
        return {"documents": [doc.to_dict() for doc in documents]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching documents: {str(e)}")


@router.get("/documents/{doc_id}")
async def get_document(doc_id: str, db: Session = Depends(get_db)):
    """
    Get document by ID with its chunks

    Args:
        doc_id: Document UUID
        db: Database session

    Returns:
        Document with chunks
    """
    try:
        doc_dao = DocumentDAO(db)
        chunk_dao = ChunkDAO(db)

        document = doc_dao.find_by_id(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        chunks = chunk_dao.find_by_document(doc_id)

        return {
            "document": document.to_dict(),
            "chunks": [chunk.to_dict() for chunk in chunks]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document: {str(e)}")


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, db: Session = Depends(get_db)):
    """
    Delete document and its chunks/embeddings (cascade)

    Args:
        doc_id: Document UUID
        db: Database session

    Returns:
        Success message
    """
    try:
        doc_dao = DocumentDAO(db)
        deleted = doc_dao.delete(doc_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found")

        return {"message": "Document deleted successfully", "doc_id": doc_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")


@router.get("/health")
async def health_check(request: Request):
    """
    Health check endpoint for RAG service

    Returns:
        Service status including vector backend information
    """
    try:
        from Chatbot.config.rag_config import get_rag_config
        config = get_rag_config()

        vectorizer = get_vectorizer_service(request)
        generator = get_generator_service(request)

        # Check Qdrant backend (VectorIndexDAO now uses Qdrant)
        vector_backend_info = {
            "backend": "qdrant",
            "status": "unknown"
        }

        try:
            from Chatbot.dao.VectorIndexDAO import VectorIndexDAO
            vidx = VectorIndexDAO()
            if vidx.health_check():
                stats = vidx.get_stats()
                vector_backend_info.update({
                    "status": stats.get("status", "unknown"),
                    "host": f"{vidx.host}:{vidx.port}",
                    "collection": vidx.collection_name,
                    "points_count": stats.get("points_count", 0)
                })
            else:
                vector_backend_info["status"] = "disconnected"
        except Exception as e:
            vector_backend_info["status"] = "error"
            vector_backend_info["error"] = str(e)

        # Check Redis cache
        cache_info = {
            "enabled": config.enable_cache,
            "status": "disabled"
        }
        if config.enable_cache:
            try:
                from Chatbot.infrastructure.cache import RedisCache
                cache = RedisCache()
                if cache.is_available():
                    stats = cache.get_stats()
                    cache_info.update(stats)
                else:
                    cache_info["status"] = "disconnected"
            except Exception as e:
                cache_info["status"] = "error"
                cache_info["error"] = str(e)

        return {
            "status": "healthy",
            "service": "RAG API",
            "vectorizer": {
                "model": vectorizer.embed_model,
                "dimension": vectorizer.get_dimension(),
                "loaded": vectorizer.model is not None,
                "cache_enabled": vectorizer.enable_cache
            },
            "generator": {
                "model": generator.client.model_name if generator.client else "mock",
                "backend": generator.client.backend if generator.client else "mock",
                "loaded": generator.client is not None
            },
            "vector_store": vector_backend_info,
            "cache": cache_info
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "RAG API",
            "error": str(e)
        }
