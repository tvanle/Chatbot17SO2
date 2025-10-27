from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class RetrievalHit(BaseModel):
    """
    Retrieval result containing chunk, document, and similarity score
    Used in answer citations
    """
    chunk_id: str = Field(..., description="ID of the retrieved chunk")
    score: float = Field(..., description="Similarity score (0-1, higher is better)")
    chunk: Optional[Dict[str, Any]] = Field(default=None, description="Chunk data (text, tokens, etc.)")
    doc: Optional[Dict[str, Any]] = Field(default=None, description="Parent document data (title, source_uri, etc.)")

    class Config:
        json_schema_extra = {
            "example": {
                "chunk_id": "abc123",
                "score": 0.89,
                "chunk": {
                    "id": "abc123",
                    "text": "Sinh viên phải tích lũy tối thiểu 120 tín chỉ...",
                    "tokens": 45,
                    "idx": 3
                },
                "doc": {
                    "id": "doc456",
                    "title": "Quy chế đào tạo 2024",
                    "source_uri": "https://portal.ptit.edu.vn/quyche.pdf"
                }
            }
        }
