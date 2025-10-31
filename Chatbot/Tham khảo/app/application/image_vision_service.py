"""
Image Vision Service.
Business logic for AI image analysis and vision capabilities.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.application.chat_history_service import ChatHistoryService
from app.core.models import ImageVisionRequest, ImageVisionResponse
from app.core.mongodb_models import ChatMessageCreate, ChatMessageRole
from app.infrastructure.databases.mongodb_client import MongoDBClient
from app.infrastructure.images.openai_image_provider import OpenAIImageProvider

logger = logging.getLogger(__name__)


class ImageVisionService:
    """
    Service for AI image vision/analysis.
    Analyzes images using GPT-4 Vision and saves results.
    """
    
    def __init__(
        self,
        image_provider: OpenAIImageProvider,
        mongodb: MongoDBClient,
        chat_history_service: Optional[ChatHistoryService] = None,
    ):
        self.image_provider = image_provider
        self.mongodb = mongodb
        self.chat_history = chat_history_service
        logger.info("ImageVisionService initialized")
    
    async def analyze_and_respond(
        self,
        request: ImageVisionRequest,
        user_id: str,
    ) -> ImageVisionResponse:
        """
        Analyze image and optionally add response to chat.
        
        Args:
            request: Vision request
            user_id: User ID for authorization
            
        Returns:
            Vision response with analysis
        """
        try:
            # 1. Get image URL
            image_url = request.image_url
            file_id = request.file_id
            
            if not image_url and file_id:
                # Get URL from MongoDB
                from bson import ObjectId
                file_data = await self.mongodb.db.files.find_one({
                    "_id": ObjectId(file_id),
                    "user_id": user_id,
                    "is_deleted": False,
                })
                if file_data:
                    image_url = file_data.get("url")
                else:
                    raise ValueError("File not found or access denied")
            
            if not image_url:
                raise ValueError("No image URL or file_id provided")
            
            logger.info(f"Analyzing image for user {user_id}: {image_url[:80]}...")
            
            # 2. Analyze with OpenAI Vision
            analysis = await self.image_provider.analyze_image(
                image_url=image_url,
                question=request.question,
                detail=request.detail,
            )
            
            # 3. Extract OCR text if needed
            ocr_text = None
            if "text" in request.question.lower() or "read" in request.question.lower():
                ocr_text = await self.image_provider.extract_text_ocr(image_url)
            
            # 4. Update file metadata with analysis (if file_id provided)
            if file_id:
                await self._update_file_with_analysis(file_id, analysis, ocr_text)
            
            # 5. If session_id, add assistant message with analysis
            message_id = None
            if request.session_id and self.chat_history:
                message_id = await self._create_analysis_message(
                    user_id=user_id,
                    session_id=request.session_id,
                    file_id=file_id,
                    analysis=analysis,
                    ocr_text=ocr_text,
                )
            
            logger.info(f"✓ Image analyzed successfully")
            
            return ImageVisionResponse(
                message_id=message_id,
                description=analysis.get("description", ""),
                labels=analysis.get("labels", []),
                ocr_text=ocr_text,
                confidence=0.95,  # Placeholder confidence score
                analyzed_file_id=file_id,
            )
            
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            raise RuntimeError(f"Failed to analyze image: {str(e)}")
    
    async def _update_file_with_analysis(
        self,
        file_id: str,
        analysis: Dict[str, Any],
        ocr_text: Optional[str],
    ):
        """Update file metadata with vision analysis results."""
        try:
            from bson import ObjectId
            
            vision_analysis = {
                **analysis,
                "analyzed_at": datetime.now(),
                "ocr_text": ocr_text,
            }
            
            await self.mongodb.db.files.update_one(
                {"_id": ObjectId(file_id)},
                {
                    "$set": {
                        "vision_analysis": vision_analysis,
                        "updated_at": datetime.now(),
                    }
                }
            )
            
            logger.debug(f"Updated file {file_id} with vision analysis")
            
        except Exception as e:
            logger.error(f"Failed to update file metadata: {e}")
    
    async def _create_analysis_message(
        self,
        user_id: str,
        session_id: str,
        file_id: Optional[str],
        analysis: Dict[str, Any],
        ocr_text: Optional[str],
    ) -> Optional[str]:
        """Create chat message with vision analysis."""
        if not self.chat_history:
            return None
        
        try:
            description = analysis.get("description", "")
            labels = analysis.get("labels", [])
            
            # Build content
            content = f"Here's what I see in the image:\n\n{description}"
            
            if labels:
                content += f"\n\nKey elements detected: {', '.join(labels)}"
            
            if ocr_text:
                content += f"\n\nExtracted text:\n{ocr_text}"
            
            message = await self.chat_history.add_message(
                session_id=session_id,
                user_id=user_id,
                message_create=ChatMessageCreate(
                    session_id=session_id,
                    role=ChatMessageRole.ASSISTANT,
                    content=content,
                    metadata={
                        "vision_analysis": {
                            "analyzed_image_id": file_id,
                            "labels": labels,
                            "model": analysis.get("model", "gpt-4.1-mini"),
                            "has_ocr": ocr_text is not None,
                        }
                    },
                ),
            )
            
            return message.id if message else None
            
        except Exception as e:
            logger.error(f"Failed to create analysis message: {e}")
            return None

