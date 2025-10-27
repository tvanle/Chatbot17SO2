"""
VectorIndexDAO - Data Access Object for Vector Index operations
Handles vector similarity search using in-memory or external vector stores
"""
from typing import List, Tuple, Optional, Dict
import numpy as np
from sqlalchemy.orm import Session
from Chatbot.models.Embedding import Embedding
from Chatbot.models.Chunk import Chunk
import pickle


class VectorIndexDAO:
    """
    DAO for vector index operations
    Supports both:
    1. Database-backed search (PostgreSQL with pgvector or SQLite with manual search)
    2. In-memory FAISS index (optional, faster for large datasets)

    This minimal implementation uses database + numpy for simplicity
    """

    def __init__(self, db: Session, use_faiss: bool = False):
        self.db = db
        self.use_faiss = use_faiss
        self.faiss_index = None  # Optional FAISS index
        self.id_map = {}  # Maps FAISS index position to chunk_id

    def query(
        self,
        namespace: str,
        query_vector: np.ndarray,
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Tuple[str, float]]:
        """
        Query vector index for similar chunks

        Args:
            namespace: Namespace/collection identifier (for multi-tenancy)
            query_vector: Query embedding vector
            top_k: Number of results to return
            filters: Optional filters (e.g., document_id, date range)

        Returns:
            List of (chunk_id, similarity_score) tuples, sorted by score descending
        """
        if self.use_faiss and self.faiss_index is not None:
            return self._query_faiss(query_vector, top_k)
        else:
            return self._query_database(namespace, query_vector, top_k, filters)

    def _query_database(
        self,
        namespace: str,
        query_vector: np.ndarray,
        top_k: int,
        filters: Optional[Dict] = None
    ) -> List[Tuple[str, float]]:
        """
        Query using database (slower but simpler)
        Computes cosine similarity with all embeddings
        """
        # Fetch all embeddings (in production, you'd filter by namespace)
        embeddings = self.db.query(Embedding).all()

        if not embeddings:
            return []

        # Compute cosine similarities
        similarities = []
        for emb in embeddings:
            vec = emb.get_vector()
            if vec is not None and len(vec) == len(query_vector):
                # Cosine similarity: dot(A, B) / (||A|| * ||B||)
                similarity = np.dot(query_vector, vec) / (
                    np.linalg.norm(query_vector) * np.linalg.norm(vec)
                )
                similarities.append((emb.chunk_id, float(similarity)))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Return top-k
        return similarities[:top_k]

    def _query_faiss(self, query_vector: np.ndarray, top_k: int) -> List[Tuple[str, float]]:
        """
        Query using FAISS index (faster for large datasets)
        Requires FAISS library installed
        """
        try:
            import faiss
            # Search in FAISS index
            query_vector = query_vector.reshape(1, -1).astype('float32')
            distances, indices = self.faiss_index.search(query_vector, top_k)

            # Map indices back to chunk IDs
            results = []
            for idx, dist in zip(indices[0], distances[0]):
                if idx != -1:  # Valid result
                    chunk_id = self.id_map.get(idx)
                    if chunk_id:
                        # Convert distance to similarity (assuming L2 distance)
                        similarity = 1 / (1 + dist)
                        results.append((chunk_id, float(similarity)))

            return results
        except ImportError:
            # Fallback to database if FAISS not available
            return self._query_database("default", query_vector, top_k, None)

    def upsert(self, namespace: str, pairs: List[Tuple[str, np.ndarray]]) -> None:
        """
        Insert or update embeddings in vector index

        Args:
            namespace: Namespace/collection identifier
            pairs: List of (chunk_id, vector) tuples
        """
        for chunk_id, vector in pairs:
            # Check if embedding exists
            existing = self.db.query(Embedding).filter(Embedding.chunk_id == chunk_id).first()

            if existing:
                # Update existing embedding
                existing.set_vector(vector)
            else:
                # Create new embedding
                embedding = Embedding(
                    chunk_id=chunk_id,
                    model_name="sentence-transformers/all-MiniLM-L6-v2",  # Default model
                    dim=len(vector)
                )
                embedding.set_vector(vector)
                self.db.add(embedding)

        self.db.commit()

        # Optionally rebuild FAISS index
        if self.use_faiss:
            self._rebuild_faiss_index()

    def _rebuild_faiss_index(self):
        """
        Rebuild FAISS index from database embeddings
        Call this after bulk inserts/updates
        """
        try:
            import faiss

            # Fetch all embeddings
            embeddings = self.db.query(Embedding).all()
            if not embeddings:
                return

            # Get dimension
            dim = embeddings[0].dim

            # Create FAISS index (L2 distance)
            self.faiss_index = faiss.IndexFlatL2(dim)

            # Add vectors
            vectors = []
            self.id_map = {}
            for idx, emb in enumerate(embeddings):
                vec = emb.get_vector()
                if vec is not None:
                    vectors.append(vec)
                    self.id_map[idx] = emb.chunk_id

            if vectors:
                vectors_array = np.array(vectors).astype('float32')
                self.faiss_index.add(vectors_array)

        except ImportError:
            # FAISS not available, skip
            pass

    def delete_by_chunk_id(self, chunk_id: str) -> bool:
        """
        Delete embedding by chunk ID

        Args:
            chunk_id: Chunk UUID

        Returns:
            True if deleted, False if not found
        """
        embedding = self.db.query(Embedding).filter(Embedding.chunk_id == chunk_id).first()
        if embedding:
            self.db.delete(embedding)
            self.db.commit()
            return True
        return False

    def delete_by_namespace(self, namespace: str):
        """
        Delete all embeddings in a namespace
        (Implementation depends on how namespace is stored - e.g., via document metadata)
        """
        # This is a placeholder - in production, you'd filter by namespace
        pass
