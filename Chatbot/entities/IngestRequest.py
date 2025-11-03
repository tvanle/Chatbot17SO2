from pydantic import BaseModel, Field
from typing import Optional, Dict


class IngestRequest(BaseModel):
    """
    Request DTO for ingest endpoint
    Admin uploads a document to be indexed

    ENHANCED: Now supports domain categorization and metadata
    """
    namespace_id: str = Field(..., description="Namespace/collection identifier for vector storage")
    document_title: str = Field(..., description="Title of the document")
    content: str = Field(..., description="Full text content of the document")
    category: Optional[str] = Field(
        default=None,
        description="Domain category: 'admission', 'tuition', 'regulations', 'general'"
    )
    metadata: Optional[Dict] = Field(
        default=None,
        description="Additional metadata (year, tags, author, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "namespace_id": "ptit_admission",
                "document_title": "Điểm chuẩn xét tuyển 2024",
                "content": "Điểm chuẩn xét tuyển Học viện PTIT năm 2024...",
                "category": "admission",
                "metadata": {
                    "year": "2024",
                    "tags": ["tuyển sinh", "điểm chuẩn"],
                    "source": "https://tuyensinh.ptit.edu.vn"
                }
            }
        }
