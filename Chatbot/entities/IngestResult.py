from pydantic import BaseModel, Field


class IngestResult(BaseModel):
    """
    Response DTO for ingest endpoint
    Returns result of document ingestion
    """
    doc_id: str = Field(..., description="ID of the created document")
    chunk_count: int = Field(..., description="Number of chunks created from the document")

    class Config:
        json_schema_extra = {
            "example": {
                "doc_id": "550e8400-e29b-41d4-a716-446655440000",
                "chunk_count": 42
            }
        }
