"""
RetrieverService - Handles retrieval of relevant chunks from vector index
"""
from typing import List, Optional, Dict
import numpy as np
from sqlalchemy.orm import Session
from Chatbot.dao.VectorIndexDAO import VectorIndexDAO
from Chatbot.dao.ChunkDAO import ChunkDAO
from Chatbot.dao.DocumentDAO import DocumentDAO
from Chatbot.entities.RetrievalHit import RetrievalHit


class RetrieverService:
    """
    Service for retrieving relevant document chunks
    Combines vector search with database hydration
    """

    def __init__(self, db: Session):
        """
        Initialize retriever service

        Args:
            db: SQLAlchemy database session
        """
        self.vidx = VectorIndexDAO(db)
        self.chunk_dao = ChunkDAO(db)
        self.doc_dao = DocumentDAO(db)

    def search(
        self,
        namespace: Optional[str],
        query_vector: np.ndarray,
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[RetrievalHit]:
        """
        Search for relevant chunks using vector similarity

        Args:
            namespace: Namespace/collection identifier (None = search all namespaces)
            query_vector: Query embedding vector
            top_k: Number of results to return
            filters: Optional filters (e.g., document_id, date range)

        Returns:
            List of RetrievalHit objects with chunk, document, and score
        """
        # Step 1: Vector search to get (chunk_id, score) pairs
        chunk_scores = self.vidx.query(namespace, query_vector, top_k, filters)

        if not chunk_scores:
            return []

        # Step 2: Hydrate chunks from database
        chunk_ids = [chunk_id for chunk_id, _ in chunk_scores]
        chunks = self.chunk_dao.find_by_ids(chunk_ids)

        # Create chunk map for quick lookup
        chunk_map = {chunk.id: chunk for chunk in chunks}

        # Step 3: Hydrate documents
        doc_ids = list(set(chunk.document_id for chunk in chunks))
        docs = {doc_id: self.doc_dao.find_by_id(doc_id) for doc_id in doc_ids}

        # Step 4: Build RetrievalHit objects
        hits = []
        for chunk_id, score in chunk_scores:
            chunk = chunk_map.get(chunk_id)
            if chunk:
                doc = docs.get(chunk.document_id)
                hit = RetrievalHit(
                    chunk_id=chunk_id,
                    score=score,
                    chunk=chunk.to_dict(),
                    doc=doc.to_dict() if doc else None
                )
                hits.append(hit)

        return hits

    def rerank(self, hits: List[RetrievalHit], query: str) -> List[RetrievalHit]:
        """
        Re-rank retrieved hits using cross-encoder or BM25
        (Optional enhancement - currently just returns as-is)

        Args:
            hits: Initial retrieval results
            query: User's query

        Returns:
            Re-ranked hits
        """
        # TODO: Implement cross-encoder re-ranking
        # For now, just return original ranking
        return hits

    def filter_by_score_threshold(
        self,
        hits: List[RetrievalHit],
        threshold: float = 0.5
    ) -> List[RetrievalHit]:
        """
        Filter hits by minimum similarity score

        Args:
            hits: Retrieval results
            threshold: Minimum score (0-1)

        Returns:
            Filtered hits
        """
        return [hit for hit in hits if hit.score >= threshold]

    def deduplicate_by_document(self, hits: List[RetrievalHit]) -> List[RetrievalHit]:
        """
        Remove duplicate chunks from the same document
        Keeps only the highest-scoring chunk per document

        Args:
            hits: Retrieval results

        Returns:
            Deduplicated hits
        """
        seen_docs = set()
        unique_hits = []

        for hit in hits:
            doc_id = hit.doc.get("id") if hit.doc else None
            if doc_id not in seen_docs:
                unique_hits.append(hit)
                seen_docs.add(doc_id)

        return unique_hits
