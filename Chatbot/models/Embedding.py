from sqlalchemy import Column, String, Integer, LargeBinary, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from BE.db.session import Base
import uuid
import numpy as np
import pickle


class Embedding(Base):
    """
    Embedding entity - Stores vector embeddings for chunks
    Schema: embeddings table
    Relationship: 1 Embedding -> 1 Chunk (1-to-1)
    """
    __tablename__ = "embeddings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chunk_id = Column(String(36), ForeignKey("chunks.id"), nullable=False, unique=True)
    model_name = Column(String(128), nullable=False)  # e.g., "sentence-transformers/all-MiniLM-L6-v2"
    dim = Column(Integer, nullable=False)  # Embedding dimension
    vector_blob = Column(LargeBinary, nullable=False)  # Serialized vector (pickle or bytes)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship: 1-to-1 with Chunk
    chunk = relationship("Chunk", back_populates="embedding")

    def __repr__(self):
        return f"<Embedding(id={self.id}, chunk_id={self.chunk_id}, model={self.model_name}, dim={self.dim})>"

    def set_vector(self, vector: np.ndarray):
        """Serialize and store vector as blob"""
        self.vector_blob = pickle.dumps(vector)
        self.dim = len(vector)

    def get_vector(self) -> np.ndarray:
        """Deserialize vector from blob"""
        if self.vector_blob:
            return pickle.loads(self.vector_blob)
        return None

    def to_dict(self):
        return {
            "id": self.id,
            "chunk_id": self.chunk_id,
            "model_name": self.model_name,
            "dim": self.dim,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
