"""
Speech-to-Text API routes.
Handles audio transcription endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.application.factory import ProviderFactory
from app.application.stt_service import STTService
from app.core.auth import get_current_user_optional
from fastapi import Depends

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stt", tags=["Speech-to-Text"])


# ============================================================================
# Request/Response Models
# ============================================================================

class TranscriptionResponse(BaseModel):
    """Response model for transcription."""
    text: str = Field(..., description="Transcribed text")
    confidence: float = Field(..., description="Confidence score (0-1)")
    duration: float = Field(..., description="Audio duration in seconds")
    language: str = Field(..., description="Language used")
    model: str = Field(..., description="Model name")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "xin chào tôi tên là nguyễn văn a",
                "confidence": 0.92,
                "duration": 3.5,
                "language": "vi",
                "model": "nguyenvulebinh/wav2vec2-base-vi-vlsp2020",
                "metadata": {
                    "sample_rate": 16000,
                    "use_lm": True,
                    "filename": "audio.wav"
                }
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    service: str
    status: str
    provider: str
    details: dict


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    summary="Transcribe audio to text",
    description="Upload an audio file and get Vietnamese text transcription",
)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file (wav, mp3, m4a, flac, ogg)"),
    language: str = Form("vi", description="Language code (currently only 'vi' supported)"),
    use_lm: bool = Form(True, description="Use language model for better accuracy"),
    model_size: str = Form("base", description="Model size: 'base' (faster) or 'large' (better)"),
    include_alternatives: bool = Form(False, description="Include transcription without LM"),
    _current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Transcribe audio file to Vietnamese text.
    
    **Supported Formats:**
    - WAV (.wav)
    - MP3 (.mp3)
    - M4A (.m4a)
    - FLAC (.flac)
    - OGG (.ogg)
    - OPUS (.opus)
    - WebM (.webm)
    
    **Models:**
    - `base`: wav2vec2-base-vi-vlsp2020 (faster, ~375M parameters)
    - `large`: wav2vec2-large-vi-vlsp2020 (better accuracy, ~315M parameters)
    
    **Parameters:**
    - `use_lm=True`: Use language model for better accuracy (recommended)
    - `use_lm=False`: Raw transcription without LM (faster but lower quality)
    
    **Returns:**
    - Transcribed Vietnamese text
    - Confidence score
    - Audio duration
    - Metadata
    """
    try:
        logger.info(
            f"Transcription request: {audio.filename} "
            f"(size: {audio.size if hasattr(audio, 'size') else 'unknown'}, "
            f"content_type: {audio.content_type}, "
            f"model: {model_size}, use_lm: {use_lm})"
        )
        
        # Validate model size
        if model_size not in ["base", "large"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model size: {model_size}. Must be 'base' or 'large'"
            )
        
        # Get STT provider and service
        stt_provider = ProviderFactory.get_stt_provider(model=model_size)
        stt_service = STTService(stt_provider)
        
        # Validate audio format
        if not stt_service.validate_audio_format(audio.filename):
            supported = stt_service.get_supported_formats()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported audio format. Supported: {', '.join(supported)}"
            )
        
        # Read audio data
        audio_data = await audio.read()
        
        if not audio_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio file is empty"
            )
        
        # Transcribe
        result = await stt_service.transcribe_audio(
            audio_data=audio_data,
            filename=audio.filename,
            language=language,
            use_lm=use_lm,
            include_alternatives=include_alternatives,
        )
        
        logger.info(
            f"✓ Transcription complete: {len(result['text'])} chars, "
            f"confidence: {result['confidence']:.2f}"
        )
        
        return TranscriptionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}"
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="STT health check",
    description="Check if Speech-to-Text service is ready",
)
async def health_check(
    model_size: str = "base",
    _current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Check STT service health.
    
    Returns model status, capabilities, and system info.
    """
    try:
        stt_provider = ProviderFactory.get_stt_provider(model=model_size)
        stt_service = STTService(stt_provider)
        
        health = await stt_service.health_check()
        
        return HealthResponse(**health)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.get(
    "/models",
    summary="List available STT models",
    description="Get list of available Speech-to-Text models",
)
async def list_models(
    _current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    List available STT models.
    
    Returns information about available models and their characteristics.
    """
    return {
        "models": [
            {
                "id": "base",
                "name": "nguyenvulebinh/wav2vec2-base-vi-vlsp2020",
                "description": "Base model for Vietnamese speech recognition",
                "parameters": "~375M",
                "speed": "fast",
                "accuracy": "good",
                "recommended": True,
            },
            {
                "id": "large",
                "name": "nguyenvulebinh/wav2vec2-large-vi-vlsp2020",
                "description": "Large model for Vietnamese speech recognition",
                "parameters": "~315M",
                "speed": "slower",
                "accuracy": "better",
                "recommended": False,
            },
        ],
        "default_model": "base",
        "supported_languages": ["vi"],
        "supported_formats": [".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".webm"],
    }


@router.get(
    "/capabilities",
    summary="Get STT capabilities",
    description="Get detailed capabilities of the STT service",
)
async def get_capabilities(
    _current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Get STT service capabilities.
    
    Returns detailed information about features and limitations.
    """
    return {
        "features": {
            "language_model": True,
            "streaming": False,  # Not implemented yet
            "speaker_diarization": False,  # Not implemented
            "timestamps": False,  # Not implemented
            "confidence_scores": True,
        },
        "languages": {
            "supported": ["vi"],
            "default": "vi",
        },
        "audio": {
            "formats": [".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".webm"],
            "target_sample_rate": 16000,
            "channels": "mono (auto-converted)",
            "max_duration": None,  # No limit
        },
        "models": {
            "available": ["base", "large"],
            "default": "base",
        },
        "performance": {
            "base_model": {
                "speed": "~1-2x realtime (CPU)",
                "memory": "~2GB RAM",
                "accuracy": "Good for general use",
            },
            "large_model": {
                "speed": "~0.5-1x realtime (CPU)",
                "memory": "~4GB RAM",
                "accuracy": "Better for difficult audio",
            },
        },
    }


