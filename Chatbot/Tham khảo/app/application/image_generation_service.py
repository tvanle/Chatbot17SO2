"""
Image Generation Service.
Business logic for AI image generation from text prompts.
"""

import logging
from datetime import datetime
from io import BytesIO
from typing import Optional

from PIL import Image

from app.application.chat_history_service import ChatHistoryService
from app.core.models import ImageGenerationRequest, ImageGenerationResponse
from app.core.mongodb_models import (
    ChatMessageCreate,
    ChatMessageRole,
    FileType,
)
from app.infrastructure.databases.mongodb_client import MongoDBClient
from app.infrastructure.images.openai_image_provider import OpenAIImageProvider
from app.infrastructure.storage.minio_storage import MinIOStorage

logger = logging.getLogger(__name__)


class ImageGenerationService:
    """
    Service for AI image generation.
    Generates images from text prompts using OpenAI and saves to MinIO.
    """
    
    def __init__(
        self,
        image_provider: OpenAIImageProvider,
        storage: MinIOStorage,
        mongodb: MongoDBClient,
        chat_history_service: Optional[ChatHistoryService] = None,
    ):
        self.image_provider = image_provider
        self.storage = storage
        self.mongodb = mongodb
        self.chat_history = chat_history_service
        logger.info("ImageGenerationService initialized")
    
    async def generate_and_save(
        self,
        request: ImageGenerationRequest,
        user_id: str,
    ) -> ImageGenerationResponse:
        """
        Generate image from prompt and save to storage.
        
        Args:
            request: Generation request with prompt
            user_id: User ID
            
        Returns:
            Generation response with URLs
        """
        try:
            logger.info(f"Generating image for user {user_id}: {request.prompt[:80]}...")
            
            # 1. Generate image using OpenAI
            image_bytes = await self.image_provider.generate_image(
                prompt=request.prompt,
                size=request.size,
                style=request.style,
            )
            
            # 2. Upload to MinIO
            path_prefix = MinIOStorage.build_generated_path(content_type="images")
            
            filename = f"gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            url = await self.storage.upload_file(
                file_data=image_bytes,
                filename=filename,
                content_type="image/png",
                path_prefix=path_prefix,
            )
            
            # 3. Generate thumbnail
            thumbnail_url = await self._generate_thumbnail(
                image_bytes,
                path_prefix,
                user_id
            )
            
            # 4. Get image dimensions
            width, height = self._get_image_dimensions(image_bytes)
            
            # 5. Save metadata to MongoDB
            file_id = await self._save_file_metadata(
                user_id=user_id,
                url=url,
                thumbnail_url=thumbnail_url,
                filename=filename,
                size=len(image_bytes),
                width=width,
                height=height,
                session_id=request.session_id,
                generation_prompt=request.prompt,
            )
            
            # 6. If session_id provided, add message to chat
            message_id = None
            if request.session_id and self.chat_history:
                message_id = await self._create_chat_message(
                    user_id=user_id,
                    session_id=request.session_id,
                    file_id=file_id,
                    url=url,
                    thumbnail_url=thumbnail_url,
                    filename=filename,
                    size=len(image_bytes),
                    width=width,
                    height=height,
                    prompt=request.prompt,
                )
            
            logger.info(f"✓ Image generated and saved: {file_id}")
            
            return ImageGenerationResponse(
                message_id=message_id,
                file_id=file_id,
                url=url,
                thumbnail_url=thumbnail_url,
                prompt=request.prompt,
                size=request.size,
            )
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise RuntimeError(f"Failed to generate image: {str(e)}")
    
    async def _generate_thumbnail(
        self,
        image_bytes: bytes,
        path_prefix: str,
        user_id: str,
    ) -> str:
        """Generate thumbnail from image."""
        try:
            img = Image.open(BytesIO(image_bytes))
            img.thumbnail((300, 300))
            
            thumb_buffer = BytesIO()
            img.save(thumb_buffer, format="PNG")
            thumb_bytes = thumb_buffer.getvalue()
            
            # Upload thumbnail
            year_month = datetime.now().strftime("%Y/%m")
            thumb_path = f"thumbnails/{user_id}/{year_month}"
            thumb_filename = f"thumb_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            thumbnail_url = await self.storage.upload_file(
                file_data=thumb_bytes,
                filename=thumb_filename,
                content_type="image/png",
                path_prefix=thumb_path,
            )
            
            return thumbnail_url
            
        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            # Return original URL as fallback
            return ""
    
    def _get_image_dimensions(self, image_bytes: bytes) -> tuple:
        """Get image width and height."""
        try:
            img = Image.open(BytesIO(image_bytes))
            return img.width, img.height
        except Exception:
            return 1024, 1024  # Default dimensions
    
    async def _save_file_metadata(
        self,
        user_id: str,
        url: str,
        thumbnail_url: str,
        filename: str,
        size: int,
        width: int,
        height: int,
        session_id: Optional[str],
        generation_prompt: str,
    ) -> str:
        """Save file metadata to MongoDB."""
        object_name = self.storage.get_object_name_from_url(url)
        
        file_data = {
            "filename": filename,
            "original_name": None,
            "user_id": user_id,
            "url": url,
            "thumbnail_url": thumbnail_url,
            "storage_provider": "minio",
            "bucket": self.storage.bucket,
            "path": object_name or "",
            "mime_type": "image/png",
            "size": size,
            "width": width,
            "height": height,
            "session_id": session_id,
            "message_id": None,
            "file_type": FileType.GENERATED.value,
            "generation_prompt": generation_prompt,
            "model_used": "gpt-4.1-mini",
            "vision_analysis": None,
            "status": "processed",
            "is_deleted": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        
        result = await self.mongodb.db.files.insert_one(file_data)
        return str(result.inserted_id)
    
    async def _create_chat_message(
        self,
        user_id: str,
        session_id: str,
        file_id: str,
        url: str,
        thumbnail_url: str,
        filename: str,
        size: int,
        width: int,
        height: int,
        prompt: str,
    ) -> Optional[str]:
        """Create chat message with generated image."""
        if not self.chat_history:
            return None
        
        try:
            attachment = {
                "file_id": file_id,
                "type": "image",
                "url": url,
                "thumbnail_url": thumbnail_url,
                "filename": filename,
                "size": size,
                "mime_type": "image/png",
                "width": width,
                "height": height,
                "generated": True,
                "generation_prompt": prompt,
            }
            
            message = await self.chat_history.add_message(
                session_id=session_id,
                user_id=user_id,
                message_create=ChatMessageCreate(
                    session_id=session_id,
                    role=ChatMessageRole.ASSISTANT,
                    content=f"I've generated an image based on your prompt: {prompt}",
                    attachments=[attachment],
                    metadata={
                        "image_generation": {
                            "requested": True,
                            "prompt": prompt,
                            "model": "gpt-4.1-mini",
                        }
                    },
                ),
            )
            
            return message.id if message else None
            
        except Exception as e:
            logger.error(f"Failed to create chat message: {e}")
            return None

