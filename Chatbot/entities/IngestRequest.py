from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """
    Request DTO for ingest endpoint
    Admin uploads a document to be indexed
    """
    namespace_id: str = Field(..., description="Namespace/collection identifier for vector storage")
    document_title: str = Field(..., description="Title of the document")
    content: str = Field(..., description="Full text content of the document")

    class Config:
        json_schema_extra = {
            "example": {
                "namespace_id": "ptit_docs",
                "document_title": "Quy chế đào tạo đại học hệ chính quy 2024",
                "content": "Điều 1. Phạm vi và đối tượng áp dụng\n1. Quy chế này quy định về..."
            }
        }
