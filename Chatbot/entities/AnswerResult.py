from pydantic import BaseModel, Field
from typing import List, Optional
from .RetrievalHit import RetrievalHit


class AnswerResult(BaseModel):
    """
    Response DTO for answer endpoint
    Contains generated answer and source citations
    """
    answer: str = Field(..., description="Generated answer from LLM")
    citations: List[RetrievalHit] = Field(default_factory=list, description="Retrieved chunks used as context")
    domain: Optional[str] = Field(None, description="Domain service that handled the question (for debugging)")
    namespace: Optional[str] = Field(None, description="Namespace used for retrieval (for debugging)")

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "Sinh viên PTIT phải hoàn thành đủ số tín chỉ theo chương trình, có điểm trung bình tích lũy >= 2.0...",
                "citations": [
                    {
                        "chunk_id": "abc123",
                        "score": 0.89,
                        "chunk": {"text": "Điều kiện tốt nghiệp..."},
                        "doc": {"title": "Quy chế đào tạo"}
                    }
                ]
            }
        }
