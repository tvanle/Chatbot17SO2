"""
ChunkDAO - Data Access Object for Chunk entity
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from Chatbot.models.Chunk import Chunk


class ChunkDAO:
    """
    DAO for Chunk operations
    Handles CRUD operations for chunks table
    """

    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, chunk_id: str) -> Optional[Chunk]:
        """
        Find chunk by ID

        Args:
            chunk_id: Chunk UUID

        Returns:
            Chunk object or None
        """
        return self.db.query(Chunk).filter(Chunk.id == chunk_id).first()

    def find_by_ids(self, chunk_ids: List[str]) -> List[Chunk]:
        """
        Find multiple chunks by IDs

        Args:
            chunk_ids: List of chunk UUIDs

        Returns:
            List of Chunk objects (maintains order of input IDs when possible)
        """
        if not chunk_ids:
            return []

        chunks = self.db.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()

        # Maintain order of input IDs
        chunk_map = {chunk.id: chunk for chunk in chunks}
        return [chunk_map[cid] for cid in chunk_ids if cid in chunk_map]

    def insert(self, chunk: Chunk) -> str:
        """
        Insert a new chunk

        Args:
            chunk: Chunk object to insert

        Returns:
            Chunk ID
        """
        self.db.add(chunk)
        self.db.commit()
        self.db.refresh(chunk)
        return chunk.id

    def insert_batch(self, chunks: List[Chunk]) -> List[str]:
        """
        Insert multiple chunks in batch

        Args:
            chunks: List of Chunk objects

        Returns:
            List of created chunk IDs
        """
        self.db.add_all(chunks)
        self.db.commit()
        for chunk in chunks:
            self.db.refresh(chunk)
        return [chunk.id for chunk in chunks]

    def find_by_document(self, document_id: str) -> List[Chunk]:
        """
        Find all chunks belonging to a document

        Args:
            document_id: Parent document UUID

        Returns:
            List of Chunk objects ordered by idx
        """
        return (
            self.db.query(Chunk)
            .filter(Chunk.document_id == document_id)
            .order_by(Chunk.idx)
            .all()
        )

    def delete(self, chunk_id: str) -> bool:
        """
        Delete chunk by ID (cascades to embedding)

        Args:
            chunk_id: Chunk UUID

        Returns:
            True if deleted, False if not found
        """
        chunk = self.find_by_id(chunk_id)
        if chunk:
            self.db.delete(chunk)
            self.db.commit()
            return True
        return False

    def count_by_document(self, document_id: str) -> int:
        """
        Count chunks for a document

        Args:
            document_id: Parent document UUID

        Returns:
            Number of chunks
        """
        return self.db.query(Chunk).filter(Chunk.document_id == document_id).count()
