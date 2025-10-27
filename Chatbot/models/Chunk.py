from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from BE.db.session import Base
import uuid


class Chunk(Base):
    """
    Chunk entity - Represents a text chunk from a document
    Schema: chunks table
    Relationship: Many Chunks -> 1 Document, 1 Chunk -> 1 Embedding
    """
    __tablename__ = "chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    idx = Column(Integer, nullable=False)  # Index of chunk in document
    text = Column(Text, nullable=False)
    tokens = Column(Integer, nullable=True)  # Token count
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="chunks")
    embedding = relationship("Embedding", back_populates="chunk", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Chunk(id={self.id}, doc_id={self.document_id}, idx={self.idx})>"

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "idx": self.idx,
            "text": self.text,
            "tokens": self.tokens,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
