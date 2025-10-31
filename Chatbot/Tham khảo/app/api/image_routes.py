"""
Image API routes.
Endpoints for image generation, vision analysis, and file uploads.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.auth_dependencies import get_current_user
from app.application.chat_history_service import ChatHistoryService
from app.application.file_upload_service import FileUploadService
from app.application.image_generation_service import ImageGenerationService
from app.application.image_vision_service import ImageVisionService
from app.application.factory import ProviderFactory
from app.config.settings import settings
from app.core.models import (
    ImageGenerationRequest,
    ImageGenerationResponse,
    ImageVisionRequest,
    ImageVisionResponse,
)
from app.core.mongodb_models import UserInDB
from app.infrastructure.images.openai_image_provider import OpenAIImageProvider
from app.infrastructure.storage.minio_storage import MinIOStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["images"])


# ============================================================================
# DEPENDENCY INJECTIONS
# ============================================================================


async def get_image_generation_service() -> ImageGenerationService:
    """Dependency for image generation service."""
    try:
        image_provider = OpenAIImageProvider(settings.openai_api_key)
        storage = MinIOStorage(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            bucket=settings.minio_bucket,
            secure=settings.minio_secure,
        )
        mongodb = await ProviderFactory.get_mongodb_client()
        chat_history = ChatHistoryService(mongodb)
        
        return ImageGenerationService(
            image_provider=image_provider,
            storage=storage,
            mongodb=mongodb,
            chat_history_service=chat_history,
        )
    except Exception as e:
        logger.error(f"Failed to initialize ImageGenerationService: {e}")
        raise HTTPException(status_code=500, detail=f"Service initialization failed: {str(e)}")


async def get_image_vision_service() -> ImageVisionService:
    """Dependency for image vision service."""
    try:
        image_provider = OpenAIImageProvider(settings.openai_api_key)
        mongodb = await ProviderFactory.get_mongodb_client()
        chat_history = ChatHistoryService(mongodb)
        
        return ImageVisionService(
            image_provider=image_provider,
            mongodb=mongodb,
            chat_history_service=chat_history,
        )
    except Exception as e:
        logger.error(f"Failed to initialize ImageVisionService: {e}")
        raise HTTPException(status_code=500, detail=f"Service initialization failed: {str(e)}")


async def get_file_upload_service() -> FileUploadService:
    """Dependency for file upload service."""
    try:
        storage = MinIOStorage(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            bucket=settings.minio_bucket,
            secure=settings.minio_secure,
        )
        mongodb = await ProviderFactory.get_mongodb_client()
        chat_history = ChatHistoryService(mongodb)
        
        return FileUploadService(
            storage=storage,
            mongodb=mongodb,
            chat_history_service=chat_history,
        )
    except Exception as e:
        logger.error(f"Failed to initialize FileUploadService: {e}")
        raise HTTPException(status_code=500, detail=f"Service initialization failed: {str(e)}")


# ============================================================================
# IMAGE GENERATION ENDPOINTS
# ============================================================================


@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image(
    request: ImageGenerationRequest,
    current_user: UserInDB = Depends(get_current_user),
    service: ImageGenerationService = Depends(get_image_generation_service),
):
    """
    Generate an image from text prompt using AI.
    
    **Features:**
    - Uses GPT-4.1-mini with image_generation tool
    - Saves to MinIO storage
    - Optionally adds to chat session
    - Returns public URL
    
    **Example:**
    ```json
    {
      "prompt": "A cat wearing a wizard hat",
      "session_id": "session123",
      "size": "1024x1024",
      "style": "natural"
    }
    ```
    
    **UI Button:** Place a "🎨 Generate Image" button in the chat interface
    """
    try:
        result = await service.generate_and_save(
            request=request,
            user_id=current_user.id,
        )
        return result
    except Exception as e:
        logger.error(f"Failed to generate image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# IMAGE VISION/ANALYSIS ENDPOINTS
# ============================================================================


@router.post("/analyze", response_model=ImageVisionResponse)
async def analyze_image(
    request: ImageVisionRequest,
    current_user: UserInDB = Depends(get_current_user),
    service: ImageVisionService = Depends(get_image_vision_service),
):
    """
    Analyze an image using AI vision (GPT-4 Vision).
    
    **Features:**
    - AI description of image content
    - Object/concept detection (labels)
    - Optional OCR text extraction
    - Optionally adds analysis to chat
    
    **Example:**
    ```json
    {
      "file_id": "file123",
      "question": "What's in this image?",
      "session_id": "session123",
      "detail": "auto"
    }
    ```
    
    Provide either `file_id` (from uploaded file) or `image_url` (direct URL).
    """
    try:
        result = await service.analyze_and_respond(
            request=request,
            user_id=current_user.id,
        )
        return result
    except Exception as e:
        logger.error(f"Failed to analyze image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FILE UPLOAD ENDPOINTS
# ============================================================================


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    current_user: UserInDB = Depends(get_current_user),
    service: FileUploadService = Depends(get_file_upload_service),
):
    """
    Upload an image or document file.
    
    **Features:**
    - Validates file type and size
    - Resizes/compresses images
    - Generates thumbnails
    - Uploads to MinIO storage
    - Optionally adds to chat session
    - Returns URLs
    
    **Limits:**
    - Images: max 10MB (JPEG, PNG, WebP, GIF)
    - Documents: max 50MB (PDF, DOC, DOCX, TXT)
    
    **Usage:**
    ```javascript
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('session_id', 'session123');
    
    fetch('/api/v1/images/upload', {
      method: 'POST',
      body: formData,
      headers: { 'Authorization': `Bearer ${token}` }
    });
    ```
    """
    try:
        # Read file data
        file_data = await file.read()
        
        # Upload file
        result = await service.upload_file(
            file_data=file_data,
            filename=file.filename,
            user_id=current_user.id,
            session_id=session_id,
            content_type=file.content_type,
        )
        
        return {
            **result,
            "message": "File uploaded successfully",
        }
        
    except ValueError as e:
        # Validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CHAT-INTEGRATED ENDPOINTS
# ============================================================================


@router.post("/sessions/{session_id}/generate")
async def generate_image_in_chat(
    session_id: str,
    request: ImageGenerationRequest,
    current_user: UserInDB = Depends(get_current_user),
    service: ImageGenerationService = Depends(get_image_generation_service),
):
    """
    Generate image and add to specific chat session.
    Convenience endpoint that auto-fills session_id.
    """
    try:
        # Override session_id from path
        request.session_id = session_id
        
        result = await service.generate_and_save(
            request=request,
            user_id=current_user.id,
        )
        return result
    except Exception as e:
        logger.error(f"Failed to generate image in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/analyze")
async def analyze_image_in_chat(
    session_id: str,
    request: ImageVisionRequest,
    current_user: UserInDB = Depends(get_current_user),
    service: ImageVisionService = Depends(get_image_vision_service),
):
    """
    Analyze image and add results to specific chat session.
    Convenience endpoint that auto-fills session_id.
    """
    try:
        # Override session_id from path
        request.session_id = session_id
        
        result = await service.analyze_and_respond(
            request=request,
            user_id=current_user.id,
        )
        return result
    except Exception as e:
        logger.error(f"Failed to analyze image in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/upload")
async def upload_file_to_chat(
    session_id: str,
    file: UploadFile = File(...),
    auto_analyze: bool = Form(False),
    current_user: UserInDB = Depends(get_current_user),
    upload_service: FileUploadService = Depends(get_file_upload_service),
    vision_service: ImageVisionService = Depends(get_image_vision_service),
):
    """
    Upload file and add to specific chat session.
    Optionally auto-analyze image after upload.
    """
    try:
        # Read file data
        file_data = await file.read()
        
        # Upload file
        result = await upload_service.upload_file(
            file_data=file_data,
            filename=file.filename,
            user_id=current_user.id,
            session_id=session_id,
            content_type=file.content_type,
        )
        
        # Auto-analyze if requested and it's an image
        if auto_analyze and result.get("mime_type", "").startswith("image/"):
            try:
                analysis = await vision_service.analyze_and_respond(
                    request=ImageVisionRequest(
                        file_id=result["file_id"],
                        session_id=session_id,
                    ),
                    user_id=current_user.id,
                )
                result["analysis"] = {
                    "description": analysis.description,
                    "labels": analysis.labels,
                }
            except Exception as e:
                logger.warning(f"Auto-analysis failed: {e}")
        
        return {
            **result,
            "message": "File uploaded successfully",
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to upload file to chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

