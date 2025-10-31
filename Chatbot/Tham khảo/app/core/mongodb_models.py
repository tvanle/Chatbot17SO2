"""
MongoDB Pydantic models for documents and users.
Clean data models following domain-driven design.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    """User roles for access control."""
    
    ADMIN = "admin"
    USER = "user"


class UserBase(BaseModel):
    """Base user model."""
    
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER
    is_active: bool = True


class UserCreate(UserBase):
    """Model for creating a new user."""
    
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Model for updating user information."""
    
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)


class UserInDB(UserBase):
    """User model as stored in database."""
    
    id: str = Field(alias="_id")
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None

    class Config:
        populate_by_name = True


class UserResponse(UserBase):
    """User model for API responses (without sensitive data)."""
    
    id: str
    created_at: datetime
    last_login: Optional[datetime] = None


class DocumentBase(BaseModel):
    """Base document model."""
    
    title: str = Field(..., min_length=1, max_length=500)
    file_name: str = Field(..., min_length=1, max_length=255)
    content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    is_active: bool = True


class DocumentCreate(DocumentBase):
    """Model for creating a new document."""
    
    collection: str = "default"


class DocumentUpdate(BaseModel):
    """Model for updating document metadata."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    file_name: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class DocumentInDB(DocumentBase):
    """Document model as stored in database."""
    
    id: str = Field(alias="_id")
    collection: str = "default"
    chunk_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: Optional[str] = None  # User ID
    
    class Config:
        populate_by_name = True


class DocumentResponse(BaseModel):
    """Document model for API responses."""
    
    id: str
    filename: str
    collection: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    vector_id: Optional[str] = None
    chunk_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    uploaded_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class VectorMapping(BaseModel):
    """Mapping between MongoDB document and Qdrant vector point."""
    
    document_id: str
    qdrant_point_id: str
    chunk_index: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LoginRequest(BaseModel):
    """Login request model."""
    
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model."""
    
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class Token(BaseModel):
    """JWT token model."""
    
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""
    
    username: Optional[str] = None
    role: Optional[str] = None


class DocumentListResponse(BaseModel):
    """Paginated document list response."""
    
    documents: List[DocumentResponse]
    total: int
    skip: int
    limit: int


class UserListResponse(BaseModel):
    """Paginated user list response."""
    
    users: List[UserResponse]
    total: int
    skip: int
    limit: int


# ============================================================================
# CHAT HISTORY MODELS
# ============================================================================


class ChatMessageRole(str, Enum):
    """Message role in conversation."""
    
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessageBase(BaseModel):
    """Base chat message model."""
    
    role: ChatMessageRole
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatMessageCreate(ChatMessageBase):
    """Model for creating a new message."""
    
    session_id: str
    attachments: List[Dict[str, Any]] = Field(default_factory=list)


class ChatMessageInDB(ChatMessageBase):
    """Chat message as stored in database."""
    
    id: str = Field(alias="_id")
    session_id: str
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    edited_at: Optional[datetime] = None
    is_deleted: bool = False
    
    class Config:
        populate_by_name = True


class ChatMessageUpdate(BaseModel):
    """Model for updating a message."""
    
    content: str


class ChatMessageResponse(BaseModel):
    """Chat message for API responses."""
    
    id: str
    session_id: str
    role: ChatMessageRole
    content: str
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    edited_at: Optional[datetime] = None


class ChatSessionBase(BaseModel):
    """Base chat session model."""
    
    title: str = Field(default="New Conversation", max_length=500)
    summary: Optional[str] = Field(default=None, max_length=2000)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    is_archived: bool = False


class ChatSessionCreate(BaseModel):
    """Model for creating a new chat session."""
    
    title: Optional[str] = Field(default="New Conversation", max_length=500)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class ChatSessionUpdate(BaseModel):
    """Model for updating chat session."""
    
    title: Optional[str] = Field(None, max_length=500)
    summary: Optional[str] = Field(None, max_length=2000)
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    is_archived: Optional[bool] = None


class ChatSessionInDB(ChatSessionBase):
    """Chat session as stored in database."""
    
    id: str = Field(alias="_id")
    user_id: str
    message_count: int = 0
    last_message_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_deleted: bool = False
    
    class Config:
        populate_by_name = True


class ChatSessionResponse(BaseModel):
    """Chat session for API responses."""
    
    id: str
    title: str
    summary: Optional[str] = None
    message_count: int
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    is_archived: bool = False


class ChatSessionWithMessages(ChatSessionResponse):
    """Chat session with messages included."""
    
    messages: List[ChatMessageResponse] = Field(default_factory=list)


class ChatSessionListResponse(BaseModel):
    """Paginated chat session list response."""
    
    sessions: List[ChatSessionResponse]
    total: int
    skip: int
    limit: int


class SummarizeRequest(BaseModel):
    """Request to summarize a chat session."""
    
    session_id: str
    max_length: int = Field(default=200, ge=50, le=1000)


class SummarizeResponse(BaseModel):
    """Response from summarization."""
    
    session_id: str
    title: str
    summary: str
    message_count: int


# ============================================================================
# FILE & IMAGE MODELS
# ============================================================================


class FileType(str, Enum):
    """Type of file."""
    
    UPLOADED = "uploaded"
    GENERATED = "generated"
    AVATAR = "avatar"
    THUMBNAIL = "thumbnail"


class FileMetadata(BaseModel):
    """File metadata stored in MongoDB."""
    
    id: str = Field(alias="_id")
    filename: str
    original_name: Optional[str] = None
    user_id: str
    
    # Storage info
    url: str
    thumbnail_url: Optional[str] = None
    storage_provider: str = "minio"
    bucket: str
    path: str
    
    # File info
    mime_type: str
    size: int
    width: Optional[int] = None
    height: Optional[int] = None
    
    # Context
    session_id: Optional[str] = None
    message_id: Optional[str] = None
    
    # Type
    file_type: FileType = FileType.UPLOADED
    
    # Generation info (if generated image)
    generation_prompt: Optional[str] = None
    model_used: Optional[str] = None
    
    # Vision analysis (if analyzed)
    vision_analysis: Optional[Dict[str, Any]] = None
    
    # Status
    status: str = "processed"  # pending, processing, processed, failed
    is_deleted: bool = False
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True


class FileAttachmentDB(BaseModel):
    """File attachment in chat message (embedded in message)."""
    
    file_id: str
    type: str  # image, document, audio, video
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

