from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from BE.db.session import Base
import uuid


class Document(Base):
    """
    Document entity - Represents a source document in the RAG system
    Schema: documents table
    """
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_uri = Column(String(512), nullable=True)
    title = Column(String(255), nullable=True)
    text = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # Domain category: admission, tuition, regulations, general
    metadata_json = Column(Text, nullable=True)  # JSON string for additional metadata (year, tags, etc.)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship: 1 Document -> Many Chunks
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(id={self.id}, title={self.title})>"

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "source_uri": self.source_uri,
            "title": self.title,
            "text": self.text,
            "category": self.category,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
