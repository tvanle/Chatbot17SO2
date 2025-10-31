from pydantic import BaseModel, Field
from typing import Optional


class AnswerRequest(BaseModel):
    """
    Request DTO for answer endpoint
    User asks a question, system returns answer with citations
    """
    namespace_id: str = Field(..., description="Namespace/collection identifier for vector search")
    question: str = Field(..., description="User's question")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    token_budget: int = Field(default=2000, ge=100, le=8000, description="Max tokens for context")
    model: Optional[str] = Field(default="gpt-3.5-turbo", description="LLM model to use for generation")

    class Config:
        json_schema_extra = {
            "example": {
                "namespace_id": "ptit_docs",
                "question": "Điều kiện tốt nghiệp của sinh viên PTIT là gì?",
                "top_k": 5,
                "token_budget": 2000
            }
        }
