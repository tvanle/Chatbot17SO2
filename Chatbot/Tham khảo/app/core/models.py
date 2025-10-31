"""
Domain models and DTOs.
Comprehensive request/response models with extensive configuration options.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ThinkingMode(str, Enum):
    """
    Thinking modes mapping to OpenAI models.
    - fast: gpt-4-1106-preview (fastest, most cost-effective)
    - balance: gpt-4-0125-preview (balanced speed & quality)
    - thinking: o4-mini (deep reasoning, slowest but most accurate)
    """

    FAST = "fast"
    BALANCE = "balance"
    THINKING = "thinking"


class ChunkConfig(BaseModel):
    """Configuration for document chunking."""

    chunk_size: int = Field(default=512, ge=100, le=4000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)
    strategy: Literal["fixed", "semantic", "sentence"] = "fixed"


class RAGConfig(BaseModel):
    """Configuration for RAG retrieval."""

    enabled: bool = True
    top_k: int = Field(default=5, ge=1, le=50)
    similarity_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    rerank: bool = False
    include_sources: bool = True
    metadata_filter: Optional[Dict[str, Any]] = None


class WebSearchConfig(BaseModel):
    """Configuration for web search using Firecrawl."""

    enabled: bool = False
    query: Optional[str] = Field(
        default=None,
        description="Search query. If None, uses the last user message"
    )
    max_results: int = Field(default=5, ge=1, le=10)
    timeout: int = Field(default=30000, ge=5000, le=60000)
    formats: List[str] = Field(default=["markdown"])
    include_in_context: bool = Field(
        default=True,
        description="Include search results in RAG context"
    )


class GenerationConfig(BaseModel):
    """Configuration for LLM generation."""

    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=100000)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    stop_sequences: Optional[List[str]] = None


class Message(BaseModel):
    """Chat message model."""

    role: Literal["system", "user", "assistant"] = "user"
    content: str


class ChatRequest(BaseModel):
    """Chat request with RAG support, web search, and thinking modes."""

    messages: List[Message]
    thinking_mode: ThinkingMode = ThinkingMode.BALANCE
    system_prompt: Optional[str] = None
    rag_config: RAGConfig = Field(default_factory=RAGConfig)
    web_search_config: WebSearchConfig = Field(default_factory=WebSearchConfig)
    generation_config: GenerationConfig = Field(default_factory=GenerationConfig)
    collection: str = "default"
    stream: bool = False
    
    # Chat history integration
    session_id: Optional[str] = Field(
        default=None,
        description="Chat session ID to save conversation history"
    )
    auto_generate_title: bool = Field(
        default=True,
        description="Auto-generate session title from first messages"
    )


class ChatResponse(BaseModel):
    """Chat response model."""

    message: Message
    sources: Optional[List[Dict[str, Any]]] = None
    web_sources: Optional[List[Dict[str, Any]]] = None
    usage: Optional[Dict[str, int]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Chat history fields
    session_id: Optional[str] = Field(
        default=None,
        description="Chat session ID if conversation was saved"
    )


class UploadRequest(BaseModel):
    """Document upload request."""

    content: Optional[str] = None
    file_path: Optional[str] = None
    collection: str = "default"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    chunk_config: ChunkConfig = Field(default_factory=ChunkConfig)


class UploadResponse(BaseModel):
    """Document upload response."""

    doc_ids: List[str]
    chunk_count: int
    collection: str
    message: str


class SearchRequest(BaseModel):
    """Vector search request."""

    query: str
    collection: str = "default"
    top_k: int = Field(default=5, ge=1, le=50)
    similarity_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata_filter: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Vector search response."""

    results: List[Dict[str, Any]]
    count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentInfo(BaseModel):
    """Document information model."""

    id: str
    content: str
    metadata: Dict[str, Any]
    collection: str
    created_at: datetime
    embedding_dims: Optional[int] = None


class ListDocumentsRequest(BaseModel):
    """List documents request."""

    collection: Optional[str] = None
    metadata_filter: Optional[Dict[str, Any]] = None
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    vector_store: Optional[str] = None


class ListDocumentsResponse(BaseModel):
    """List documents response."""

    documents: List[DocumentInfo]
    total_count: int
    limit: int
    offset: int


class DeleteResponse(BaseModel):
    """Delete operation response."""

    deleted_count: int
    message: str


class ReindexRequest(BaseModel):
    """Request model for re-indexing a document."""
    
    chunk_size: Optional[int] = Field(None, ge=100, le=4000, description="Override chunk size")
    chunk_overlap: Optional[int] = Field(None, ge=0, le=500, description="Override chunk overlap")
    chunk_strategy: Literal["fixed", "semantic", "sentence"] = Field(
        default="fixed",
        description="Chunking strategy to use"
    )
    update_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata to merge with existing"
    )


class ReindexResponse(BaseModel):
    """Response model for re-indexing operation."""
    
    success: bool
    document_id: str
    old_chunk_count: int
    new_chunk_count: int
    old_vector_ids: List[str]
    new_vector_ids: List[str]
    processing_time_seconds: float
    message: str
    collection: str


class ModelInfo(BaseModel):
    """Model/provider information."""

    name: str
    type: Literal["llm", "embedding", "vector_store"]
    available: bool
    config: Dict[str, Any] = Field(default_factory=dict)


class ProviderStatus(BaseModel):
    """Provider status information."""

    providers: Dict[str, List[ModelInfo]]
    default_providers: Dict[str, str]


class DatabaseStats(BaseModel):
    """Vector database statistics."""

    total_documents: int
    total_chunks: int
    collections: List[str]
    storage_size: Optional[str] = None
    vector_store: str


class CrawlStatus(str, Enum):
    """Status of a crawl task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class CrawlTask(BaseModel):
    """Task for crawling a URL."""

    url: str
    title: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    output_filename: Optional[str] = None
    status: CrawlStatus = CrawlStatus.PENDING
    error: Optional[str] = None


class CrawlResult(BaseModel):
    """Result of a crawl operation."""

    task: CrawlTask
    success: bool
    content: Optional[str] = None
    content_length: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0
    saved_path: Optional[str] = None


class CrawlBatchReport(BaseModel):
    """Report for a batch of crawl operations."""

    total_tasks: int
    completed: int
    failed: int
    skipped: int
    duration_seconds: float
    results: List[CrawlResult]
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
# IMAGE GENERATION & VISION MODELS
# ============================================================================


class ImageGenerationRequest(BaseModel):
    """Request to generate an image from text prompt."""
    
    prompt: str = Field(..., min_length=1, max_length=1000, description="Image description")
    session_id: Optional[str] = Field(default=None, description="Chat session ID")
    size: Literal["1024x1024", "1792x1024", "1024x1792"] = Field(
        default="1024x1024",
        description="Image dimensions"
    )
    style: str = Field(default="natural", description="Image style")


class ImageGenerationResponse(BaseModel):
    """Response from image generation."""
    
    message_id: Optional[str] = Field(default=None, description="Chat message ID if added to session")
    file_id: str = Field(..., description="Unique file ID")
    url: str = Field(..., description="Public URL to generated image")
    thumbnail_url: str = Field(..., description="Thumbnail URL")
    prompt: str = Field(..., description="Original prompt")
    size: str = Field(..., description="Image size")
    model: str = Field(default="gpt-4.1-mini", description="Model used")


class ImageVisionRequest(BaseModel):
    """Request to analyze an image."""
    
    file_id: Optional[str] = Field(default=None, description="File ID from database")
    image_url: Optional[str] = Field(default=None, description="Direct image URL")
    question: str = Field(
        default="What's in this image?",
        description="Question to ask about the image"
    )
    session_id: Optional[str] = Field(default=None, description="Chat session ID")
    detail: Literal["auto", "low", "high"] = Field(
        default="auto",
        description="Level of detail for analysis"
    )


class ImageVisionResponse(BaseModel):
    """Response from image vision analysis."""
    
    message_id: Optional[str] = Field(default=None, description="Chat message ID if added to session")
    description: str = Field(..., description="AI description of image")
    labels: List[str] = Field(default_factory=list, description="Detected objects/concepts")
    ocr_text: Optional[str] = Field(default=None, description="Extracted text if any")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score")
    analyzed_file_id: Optional[str] = Field(default=None, description="ID of analyzed file")


class FileUploadRequest(BaseModel):
    """Request to upload a file."""
    
    session_id: Optional[str] = Field(default=None, description="Chat session ID")
    auto_analyze: bool = Field(default=False, description="Automatically analyze image after upload")


class FileAttachment(BaseModel):
    """File attachment in message."""
    
    file_id: str
    type: Literal["image", "document", "audio", "video"]
    url: str
    thumbnail_url: Optional[str] = None
    filename: str
    size: int
    mime_type: str
    
    # Image-specific
    width: Optional[int] = None
    height: Optional[int] = None
    
    # Generated image
    generated: bool = False
    generation_prompt: Optional[str] = None
    
    # Vision analysis
    vision_analysis: Optional[Dict[str, Any]] = None
