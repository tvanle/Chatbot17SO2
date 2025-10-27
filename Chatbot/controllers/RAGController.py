"""
RAGController - HTTP endpoints for RAG operations
Implements answer() and ingest() following the sequence diagrams
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from BE.db.session import get_db
from Chatbot.entities.AnswerRequest import AnswerRequest
from Chatbot.entities.AnswerResult import AnswerResult
from Chatbot.entities.IngestRequest import IngestRequest
from Chatbot.entities.IngestResult import IngestResult
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

# Initialize services (singleton pattern)
vectorizer_service = VectorizerService(embed_model="sentence-transformers/all-MiniLM-L6-v2")
generator_service = GeneratorService(model_name="gpt-3.5-turbo", backend="openai")


@router.post("/answer", response_model=AnswerResult)
async def answer(request: AnswerRequest, db: Session = Depends(get_db)):
    """
    Answer endpoint - RAG query flow

    Sequence (from kichban.txt):
    1. Vectorize question
    2. Retrieve similar chunks from vector index
    3. Hydrate chunks and documents from DB
    4. Take contexts within token budget
    5. Generate answer using LLM
    6. Return answer with citations

    Args:
        request: AnswerRequest with question and parameters
        db: Database session

    Returns:
        AnswerResult with generated answer and citations
    """
    try:
        # Step 1: Vectorize question (Sequence diagram line 12-13)
        query_vector = vectorizer_service.embed(request.question)

        # Step 2-4: Retrieve relevant chunks (Sequence diagram line 15-24)
        retriever = RetrieverService(db)
        hits = retriever.search(
            namespace=request.namespace_id,
            query_vector=query_vector,
            top_k=request.top_k,
            filters=None
        )

        if not hits:
            return AnswerResult(
                answer="Xin lỗi, tôi không tìm thấy thông tin liên quan đến câu hỏi của bạn.",
                citations=[]
            )

        # Step 5: Take contexts within token budget (Sequence diagram line 26)
        context_texts = [hit.chunk["text"] for hit in hits if hit.chunk]
        contexts = fit_within_budget(context_texts, request.token_budget)

        # Step 6-8: Generate answer using LLM (Sequence diagram line 28-32)
        answer_text = generator_service.generate(
            question=request.question,
            contexts=contexts,
            language="vi"
        )

        # Step 9: Return result with citations (Sequence diagram line 34)
        return AnswerResult(
            answer=answer_text,
            citations=hits
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing answer request: {str(e)}")


@router.post("/ingest", response_model=IngestResult)
async def ingest(request: IngestRequest, db: Session = Depends(get_db)):
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
        chunk_texts = chunk_text(
            request.content,
            chunk_size=512,
            chunk_overlap=50
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
        vectors = vectorizer_service.embed_batch(chunk_texts_list)

        # Step 9-10: Upsert vectors to index (Sequence diagram line 27-28)
        vidx = VectorIndexDAO(db)
        pairs = [(chunk.id, vector) for chunk, vector in zip(chunks, vectors)]
        vidx.upsert(request.namespace_id, pairs)

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
async def health_check():
    """
    Health check endpoint for RAG service

    Returns:
        Service status
    """
    return {
        "status": "healthy",
        "service": "RAG API",
        "vectorizer_model": vectorizer_service.embed_model,
        "generator_model": generator_service.client.model_name
    }
