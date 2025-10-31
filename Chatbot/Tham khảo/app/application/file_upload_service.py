"""
File Upload Service.
Business logic for file uploads with validation, processing, and storage.
"""

import logging
import magic
from datetime import datetime
from io import BytesIO
from typing import Optional, Tuple

from PIL import Image

from app.application.chat_history_service import ChatHistoryService
from app.core.mongodb_models import ChatMessageCreate, ChatMessageRole, FileType
from app.infrastructure.databases.mongodb_client import MongoDBClient
from app.infrastructure.storage.minio_storage import MinIOStorage

logger = logging.getLogger(__name__)


class FileUploadService:
    """
    Service for file uploads.
    Handles validation, processing, thumbnail generation, and storage.
    """
    
    # File size limits (bytes)
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50MB
    
    # Allowed MIME types
    ALLOWED_IMAGE_TYPES = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    ]
    
    ALLOWED_DOCUMENT_TYPES = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    ]
    
    def __init__(
        self,
        storage: MinIOStorage,
        mongodb: MongoDBClient,
        chat_history_service: Optional[ChatHistoryService] = None,
    ):
        self.storage = storage
        self.mongodb = mongodb
        self.chat_history = chat_history_service
        logger.info("FileUploadService initialized")
    
    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        user_id: str,
        session_id: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> dict:
        """
        Upload file with validation and processing.
        
        Args:
            file_data: File bytes
            filename: Original filename
            user_id: User ID
            session_id: Optional chat session ID
            content_type: Optional MIME type (will be detected if not provided)
            
        Returns:
            Dictionary with file info (file_id, url, thumbnail_url, etc.)
        """
        try:
            logger.info(f"Uploading file for user {user_id}: {filename}")
            
            # 1. Detect MIME type if not provided
            if not content_type:
                content_type = self._detect_mime_type(file_data)
            
            # 2. Validate file
            self._validate_file(file_data, content_type, filename)
            
            # 3. Process based on file type
            if content_type.startswith("image/"):
                return await self._upload_image(
                    file_data=file_data,
                    filename=filename,
                    user_id=user_id,
                    session_id=session_id,
                    content_type=content_type,
                )
            else:
                return await self._upload_document(
                    file_data=file_data,
                    filename=filename,
                    user_id=user_id,
                    session_id=session_id,
                    content_type=content_type,
                )
            
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            raise RuntimeError(f"Failed to upload file: {str(e)}")
    
    async def _upload_image(
        self,
        file_data: bytes,
        filename: str,
        user_id: str,
        session_id: Optional[str],
        content_type: str,
    ) -> dict:
        """Upload and process image file."""
        # 1. Resize/compress if needed
        processed_data, width, height = self._process_image(file_data)
        
        # 2. Upload to MinIO
        from app.infrastructure.storage.minio_storage import MinIOStorage
        path_prefix = MinIOStorage.build_upload_path(
            user_id=user_id,
            session_id=session_id,
            file_type="images"
        )
        
        url = await self.storage.upload_file(
            file_data=processed_data,
            filename=filename,
            content_type=content_type,
            path_prefix=path_prefix,
        )
        
        # 3. Generate thumbnail
        thumbnail_url = await self._generate_thumbnail(
            processed_data,
            user_id,
            session_id
        )
        
        # 4. Save metadata
        file_id = await self._save_file_metadata(
            user_id=user_id,
            url=url,
            thumbnail_url=thumbnail_url,
            filename=filename,
            original_name=filename,
            size=len(processed_data),
            mime_type=content_type,
            width=width,
            height=height,
            session_id=session_id,
            file_type=FileType.UPLOADED,
        )
        
        # 5. Add to chat if session_id provided
        message_id = None
        if session_id and self.chat_history:
            message_id = await self._create_upload_message(
                user_id=user_id,
                session_id=session_id,
                file_id=file_id,
                url=url,
                thumbnail_url=thumbnail_url,
                filename=filename,
                size=len(processed_data),
                mime_type=content_type,
                width=width,
                height=height,
            )
        
        logger.info(f"✓ Image uploaded: {file_id}")
        
        return {
            "file_id": file_id,
            "url": url,
            "thumbnail_url": thumbnail_url,
            "filename": filename,
            "size": len(processed_data),
            "mime_type": content_type,
            "width": width,
            "height": height,
            "message_id": message_id,
        }
    
    async def _upload_document(
        self,
        file_data: bytes,
        filename: str,
        user_id: str,
        session_id: Optional[str],
        content_type: str,
    ) -> dict:
        """Upload document file."""
        # Upload to MinIO
        from app.infrastructure.storage.minio_storage import MinIOStorage
        path_prefix = MinIOStorage.build_upload_path(
            user_id=user_id,
            session_id=session_id,
            file_type="documents"
        )
        
        url = await self.storage.upload_file(
            file_data=file_data,
            filename=filename,
            content_type=content_type,
            path_prefix=path_prefix,
        )
        
        # Save metadata
        file_id = await self._save_file_metadata(
            user_id=user_id,
            url=url,
            thumbnail_url=None,
            filename=filename,
            original_name=filename,
            size=len(file_data),
            mime_type=content_type,
            width=None,
            height=None,
            session_id=session_id,
            file_type=FileType.UPLOADED,
        )
        
        logger.info(f"✓ Document uploaded: {file_id}")
        
        return {
            "file_id": file_id,
            "url": url,
            "filename": filename,
            "size": len(file_data),
            "mime_type": content_type,
        }
    
    def _detect_mime_type(self, file_data: bytes) -> str:
        """Detect MIME type from file data."""
        try:
            mime = magic.Magic(mime=True)
            return mime.from_buffer(file_data)
        except Exception:
            # Fallback to basic detection
            return "application/octet-stream"
    
    def _validate_file(self, file_data: bytes, content_type: str, filename: str):
        """Validate file size and type."""
        file_size = len(file_data)
        
        # Check MIME type
        if content_type.startswith("image/"):
            if content_type not in self.ALLOWED_IMAGE_TYPES:
                raise ValueError(f"Image type not allowed: {content_type}")
            if file_size > self.MAX_IMAGE_SIZE:
                raise ValueError(f"Image too large: {file_size} bytes (max {self.MAX_IMAGE_SIZE})")
        elif content_type in self.ALLOWED_DOCUMENT_TYPES:
            if file_size > self.MAX_DOCUMENT_SIZE:
                raise ValueError(f"Document too large: {file_size} bytes (max {self.MAX_DOCUMENT_SIZE})")
        else:
            raise ValueError(f"File type not allowed: {content_type}")
        
        logger.debug(f"File validated: {filename} ({content_type}, {file_size} bytes)")
    
    def _process_image(self, image_data: bytes) -> Tuple[bytes, int, int]:
        """
        Process image: resize if too large, compress.
        
        Returns:
            (processed_bytes, width, height)
        """
        try:
            img = Image.open(BytesIO(image_data))
            
            # Get original dimensions
            width, height = img.size
            
            # Resize if too large (max 1920x1080)
            MAX_WIDTH = 1920
            MAX_HEIGHT = 1080
            
            if width > MAX_WIDTH or height > MAX_HEIGHT:
                ratio = min(MAX_WIDTH / width, MAX_HEIGHT / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height), Image.LANCZOS)
                width, height = new_width, new_height
                logger.debug(f"Image resized to {width}x{height}")
            
            # Compress to 85% quality
            output = BytesIO()
            img.save(output, format=img.format or "PNG", quality=85, optimize=True)
            processed_bytes = output.getvalue()
            
            logger.debug(f"Image processed: {len(image_data)} → {len(processed_bytes)} bytes")
            
            return processed_bytes, width, height
            
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            # Return original if processing fails
            img = Image.open(BytesIO(image_data))
            return image_data, img.width, img.height
    
    async def _generate_thumbnail(
        self,
        image_data: bytes,
        user_id: str,
        session_id: Optional[str],
    ) -> str:
        """Generate thumbnail for image."""
        try:
            img = Image.open(BytesIO(image_data))
            img.thumbnail((300, 300))
            
            thumb_buffer = BytesIO()
            img.save(thumb_buffer, format="PNG")
            thumb_bytes = thumb_buffer.getvalue()
            
            # Upload thumbnail
            from app.infrastructure.storage.minio_storage import MinIOStorage
            thumb_path = MinIOStorage.build_upload_path(
                user_id=user_id,
                session_id=session_id,
                file_type="thumbnails"
            )
            thumb_filename = f"thumb_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            thumbnail_url = await self.storage.upload_file(
                file_data=thumb_bytes,
                filename=thumb_filename,
                content_type="image/png",
                path_prefix=thumb_path,
            )
            
            return thumbnail_url
            
        except Exception as e:
            logger.error(f"Thumbnail generation failed: {e}")
            return ""
    
    async def _save_file_metadata(
        self,
        user_id: str,
        url: str,
        thumbnail_url: Optional[str],
        filename: str,
        original_name: str,
        size: int,
        mime_type: str,
        width: Optional[int],
        height: Optional[int],
        session_id: Optional[str],
        file_type: FileType,
    ) -> str:
        """Save file metadata to MongoDB."""
        object_name = self.storage.get_object_name_from_url(url)
        
        file_data = {
            "filename": filename,
            "original_name": original_name,
            "user_id": user_id,
            "url": url,
            "thumbnail_url": thumbnail_url,
            "storage_provider": "minio",
            "bucket": self.storage.bucket,
            "path": object_name or "",
            "mime_type": mime_type,
            "size": size,
            "width": width,
            "height": height,
            "session_id": session_id,
            "message_id": None,
            "file_type": file_type.value,
            "generation_prompt": None,
            "model_used": None,
            "vision_analysis": None,
            "status": "processed",
            "is_deleted": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        
        result = await self.mongodb.db.files.insert_one(file_data)
        return str(result.inserted_id)
    
    async def _create_upload_message(
        self,
        user_id: str,
        session_id: str,
        file_id: str,
        url: str,
        thumbnail_url: str,
        filename: str,
        size: int,
        mime_type: str,
        width: int,
        height: int,
    ) -> Optional[str]:
        """Create chat message with uploaded file."""
        if not self.chat_history:
            return None
        
        try:
            attachment = {
                "file_id": file_id,
                "type": "image" if mime_type.startswith("image/") else "document",
                "url": url,
                "thumbnail_url": thumbnail_url,
                "filename": filename,
                "size": size,
                "mime_type": mime_type,
                "width": width,
                "height": height,
                "generated": False,
            }
            
            content = f"Uploaded: {filename}"
            if mime_type.startswith("image/"):
                content = f"📷 {filename}"
            
            message = await self.chat_history.add_message(
                session_id=session_id,
                user_id=user_id,
                message_create=ChatMessageCreate(
                    session_id=session_id,
                    role=ChatMessageRole.USER,
                    content=content,
                    attachments=[attachment],
                ),
            )
            
            return message.id if message else None
            
        except Exception as e:
            logger.error(f"Failed to create upload message: {e}")
            return None

