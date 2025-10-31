"""
Speech-to-Text Service
Handles audio transcription using STT provider.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.interfaces import ISTTProvider

logger = logging.getLogger(__name__)


class STTService:
    """
    Service for Speech-to-Text operations.
    
    Handles:
    - Audio transcription (bytes or file)
    - Audio format validation
    - Result formatting
    - Error handling
    """
    
    def __init__(self, stt_provider: ISTTProvider):
        """
        Initialize STT service.
        
        Args:
            stt_provider: STT provider implementation (e.g., Wav2Vec2STT)
        """
        self.stt_provider = stt_provider
        logger.info(f"STTService initialized with provider: {stt_provider.__class__.__name__}")
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        filename: Optional[str] = None,
        language: str = "vi",
        use_lm: bool = True,
        include_alternatives: bool = False,
    ) -> Dict[str, Any]:
        """
        Transcribe audio bytes to text.
        
        Args:
            audio_data: Audio file bytes
            filename: Original filename (for format detection)
            language: Language code (default: "vi")
            use_lm: Use language model for better accuracy
            include_alternatives: Include text without LM for comparison
            
        Returns:
            Dict with:
                - text: Transcribed text
                - confidence: Confidence score
                - duration: Audio duration in seconds
                - language: Language used
                - model: Model name
                - metadata: Additional info
        """
        try:
            logger.info(
                f"Transcribing audio (size: {len(audio_data)} bytes, "
                f"filename: {filename}, language: {language}, use_lm: {use_lm})"
            )
            
            # Validate audio data
            if not audio_data:
                raise ValueError("Audio data is empty")
            
            # Transcribe
            result = await self.stt_provider.transcribe(
                audio_data=audio_data,
                language=language,
                use_lm=use_lm,
            )
            
            # Format response
            response = {
                "text": result["text"],
                "confidence": result.get("confidence", 0.0),
                "duration": result.get("duration", 0.0),
                "language": result.get("language", language),
                "model": result.get("model", "unknown"),
                "metadata": {
                    "sample_rate": result.get("sample_rate"),
                    "use_lm": use_lm,
                    "filename": filename,
                },
            }
            
            # Include alternative transcription if requested
            if include_alternatives and "text_no_lm" in result:
                response["metadata"]["text_no_lm"] = result["text_no_lm"]
            
            logger.info(
                f"✓ Transcription complete: {len(response['text'])} chars, "
                f"confidence: {response['confidence']:.2f}"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    async def transcribe_file(
        self,
        file_path: str,
        language: str = "vi",
        use_lm: bool = True,
        include_alternatives: bool = False,
    ) -> Dict[str, Any]:
        """
        Transcribe audio file to text.
        
        Args:
            file_path: Path to audio file
            language: Language code
            use_lm: Use language model
            include_alternatives: Include alternatives
            
        Returns:
            Same as transcribe_audio()
        """
        try:
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                raise FileNotFoundError(f"Audio file not found: {file_path}")
            
            logger.info(f"Transcribing file: {file_path_obj.name}")
            
            # Transcribe
            result = await self.stt_provider.transcribe_file(
                file_path=str(file_path_obj),
                language=language,
                use_lm=use_lm,
            )
            
            # Format response
            response = {
                "text": result["text"],
                "confidence": result.get("confidence", 0.0),
                "duration": result.get("duration", 0.0),
                "language": result.get("language", language),
                "model": result.get("model", "unknown"),
                "metadata": {
                    "sample_rate": result.get("sample_rate"),
                    "use_lm": use_lm,
                    "filename": file_path_obj.name,
                    "file_size": file_path_obj.stat().st_size,
                },
            }
            
            if include_alternatives and "text_no_lm" in result:
                response["metadata"]["text_no_lm"] = result["text_no_lm"]
            
            logger.info(f"✓ File transcription complete: {file_path_obj.name}")
            
            return response
            
        except Exception as e:
            logger.error(f"File transcription failed: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check STT service health.
        
        Returns:
            Health status dict
        """
        try:
            health = await self.stt_provider.health_check()
            
            return {
                "service": "stt",
                "status": health.get("status", "unknown"),
                "provider": self.stt_provider.__class__.__name__,
                "details": health,
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "service": "stt",
                "status": "unhealthy",
                "error": str(e),
            }
    
    def get_supported_formats(self) -> list:
        """
        Get list of supported audio formats.
        
        Returns:
            List of file extensions (e.g., ['.wav', '.mp3', '.m4a'])
        """
        if hasattr(self.stt_provider, 'SUPPORTED_FORMATS'):
            return list(self.stt_provider.SUPPORTED_FORMATS)
        return ['.wav', '.mp3', '.m4a', '.flac', '.ogg']
    
    def validate_audio_format(self, filename: str) -> bool:
        """
        Validate if audio format is supported.
        
        Args:
            filename: Audio filename
            
        Returns:
            True if supported, False otherwise
        """
        suffix = Path(filename).suffix.lower()
        supported = self.get_supported_formats()
        return suffix in supported


