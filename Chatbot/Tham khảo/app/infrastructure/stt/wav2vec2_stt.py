"""
Vietnamese Speech-to-Text using Wav2Vec2 model.
Model: nguyenvulebinh/wav2vec2-base-vi-vlsp2020
"""

import asyncio
import io
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import librosa
import numpy as np
import torch
import torchaudio
from transformers import Wav2Vec2ProcessorWithLM
from transformers.file_utils import cached_path, hf_bucket_url
from importlib.machinery import SourceFileLoader

from app.core.interfaces import ISTTProvider

logger = logging.getLogger(__name__)


class Wav2Vec2STT(ISTTProvider):
    """
    Vietnamese Speech-to-Text provider using Wav2Vec2.
    
    Features:
    - Vietnamese language optimized
    - Language Model support for better accuracy
    - Automatic audio resampling to 16kHz
    - Multiple audio format support (wav, mp3, m4a, flac, ogg)
    - Lazy model loading (loads on first use)
    """
    
    SUPPORTED_FORMATS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".webm"}
    TARGET_SAMPLE_RATE = 16000
    
    def __init__(
        self,
        model_name: str = "nguyenvulebinh/wav2vec2-base-vi-vlsp2020",
        device: Optional[str] = None,
        lazy_load: bool = True,
    ):
        """
        Initialize Wav2Vec2 STT provider.
        
        Args:
            model_name: HuggingFace model identifier
                - "nguyenvulebinh/wav2vec2-base-vi-vlsp2020" (default, faster)
                - "nguyenvulebinh/wav2vec2-large-vi-vlsp2020" (slower, better)
            device: Device to run model on ("cuda", "cpu", or None for auto)
            lazy_load: If True, load model on first use (default)
        """
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.lazy_load = lazy_load
        
        # Model components (loaded lazily)
        self.model = None
        self.processor = None
        self._model_loaded = False
        self._loading_lock = asyncio.Lock()
        
        logger.info(
            f"Wav2Vec2STT initialized (model: {model_name}, device: {self.device}, "
            f"lazy_load: {lazy_load})"
        )
        
        # Load immediately if not lazy
        if not lazy_load:
            asyncio.create_task(self._load_model())
    
    async def _load_model(self):
        """Load model and processor (thread-safe)."""
        async with self._loading_lock:
            if self._model_loaded:
                return
            
            try:
                logger.info(f"Loading Wav2Vec2 model: {self.model_name}...")
                
                # Run in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._load_model_sync)
                
                self._model_loaded = True
                logger.info(f"✓ Model loaded successfully (device: {self.device})")
                
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                raise RuntimeError(f"Model loading failed: {str(e)}")
    
    def _load_model_sync(self):
        """Synchronous model loading (runs in thread pool)."""
        try:
            # Load model with custom handling
            model_path = cached_path(
                hf_bucket_url(self.model_name, filename="model_handling.py")
            )
            model_loader = SourceFileLoader("model", model_path).load_module()
            
            self.model = model_loader.Wav2Vec2ForCTC.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()  # Set to evaluation mode
            
            # Load processor with Language Model
            self.processor = Wav2Vec2ProcessorWithLM.from_pretrained(self.model_name)
            
            logger.debug(f"Model architecture: {self.model.__class__.__name__}")
            logger.debug(f"Processor type: {self.processor.__class__.__name__}")
            
        except Exception as e:
            logger.error(f"Error in _load_model_sync: {e}")
            raise
    
    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "vi",
        use_lm: bool = True,
    ) -> Dict[str, Any]:
        """
        Transcribe audio bytes to text.
        
        Args:
            audio_data: Audio file bytes (any supported format)
            language: Language code (currently only "vi" supported)
            use_lm: Use language model for better accuracy
            
        Returns:
            Dict with transcription result
        """
        # Ensure model is loaded
        if not self._model_loaded:
            await self._load_model()
        
        try:
            # Save to temporary file for processing
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(audio_data)
                tmp_path = tmp_file.name
            
            try:
                # Process the file
                result = await self.transcribe_file(
                    file_path=tmp_path,
                    language=language,
                    use_lm=use_lm,
                )
                return result
                
            finally:
                # Clean up temp file
                Path(tmp_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {str(e)}")
    
    async def transcribe_file(
        self,
        file_path: str,
        language: str = "vi",
        use_lm: bool = True,
    ) -> Dict[str, Any]:
        """
        Transcribe audio file to text.
        
        Args:
            file_path: Path to audio file
            language: Language code
            use_lm: Use language model
            
        Returns:
            Dict with:
                - text: Transcribed text
                - text_no_lm: Transcription without LM (for comparison)
                - confidence: Confidence score (if available)
                - language: Language used
                - duration: Audio duration in seconds
                - model: Model name
                - sample_rate: Audio sample rate
        """
        # Ensure model is loaded
        if not self._model_loaded:
            await self._load_model()
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        if file_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported audio format: {file_path.suffix}. "
                f"Supported: {', '.join(self.SUPPORTED_FORMATS)}"
            )
        
        try:
            logger.info(f"Transcribing audio: {file_path.name}")
            
            # Load and preprocess audio in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._transcribe_sync,
                str(file_path),
                use_lm,
            )
            
            result["language"] = language
            result["model"] = self.model_name
            
            logger.info(
                f"✓ Transcription complete: {len(result['text'])} chars, "
                f"{result['duration']:.2f}s audio"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed for {file_path.name}: {e}")
            raise RuntimeError(f"Transcription failed: {str(e)}")
    
    def _transcribe_sync(self, file_path: str, use_lm: bool) -> Dict[str, Any]:
        """Synchronous transcription (runs in thread pool)."""
        try:
            # Load audio
            audio, sample_rate = self._load_and_resample_audio(file_path)
            
            # Calculate duration
            duration = len(audio) / self.TARGET_SAMPLE_RATE
            
            # Prepare input for model
            input_data = self.processor.feature_extractor(
                audio,
                sampling_rate=self.TARGET_SAMPLE_RATE,
                return_tensors='pt'
            )
            
            # Move to device
            input_data = {k: v.to(self.device) for k, v in input_data.items()}
            
            # Run inference
            with torch.no_grad():
                output = self.model(**input_data)
            
            # Decode without LM (baseline)
            text_no_lm = self.processor.tokenizer.decode(
                output.logits.argmax(dim=-1)[0].detach().cpu().numpy()
            )
            
            # Decode with LM (better accuracy)
            if use_lm:
                text_with_lm = self.processor.decode(
                    output.logits.cpu().detach().numpy()[0],
                    beam_width=100
                ).text
            else:
                text_with_lm = text_no_lm
            
            # Calculate confidence (average of max probabilities)
            probs = torch.nn.functional.softmax(output.logits, dim=-1)
            max_probs = probs.max(dim=-1)[0]
            confidence = max_probs.mean().item()
            
            return {
                "text": text_with_lm,
                "text_no_lm": text_no_lm,
                "confidence": confidence,
                "duration": duration,
                "sample_rate": self.TARGET_SAMPLE_RATE,
            }
            
        except Exception as e:
            logger.error(f"Error in _transcribe_sync: {e}")
            raise
    
    def _load_and_resample_audio(self, file_path: str) -> tuple:
        """
        Load audio file and resample to 16kHz if needed.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Tuple of (audio_array, sample_rate)
        """
        try:
            # Try torchaudio first (faster for wav files)
            audio, sample_rate = torchaudio.load(file_path)
            
            # Convert stereo to mono if needed
            if audio.shape[0] > 1:
                audio = audio.mean(dim=0, keepdim=True)
            
            # Resample if needed
            if sample_rate != self.TARGET_SAMPLE_RATE:
                resampler = torchaudio.transforms.Resample(
                    orig_freq=sample_rate,
                    new_freq=self.TARGET_SAMPLE_RATE
                )
                audio = resampler(audio)
            
            # Convert to numpy array
            audio_array = audio.squeeze().numpy()
            
            logger.debug(
                f"Loaded audio: {len(audio_array)} samples, "
                f"{sample_rate}Hz -> {self.TARGET_SAMPLE_RATE}Hz"
            )
            
            return audio_array, self.TARGET_SAMPLE_RATE
            
        except Exception as e:
            # Fallback to librosa (supports more formats)
            logger.debug(f"torchaudio failed, trying librosa: {e}")
            
            try:
                audio_array, sample_rate = librosa.load(
                    file_path,
                    sr=self.TARGET_SAMPLE_RATE,
                    mono=True
                )
                
                logger.debug(
                    f"Loaded audio with librosa: {len(audio_array)} samples, "
                    f"{self.TARGET_SAMPLE_RATE}Hz"
                )
                
                return audio_array, self.TARGET_SAMPLE_RATE
                
            except Exception as e2:
                logger.error(f"Failed to load audio with librosa: {e2}")
                raise RuntimeError(f"Failed to load audio: {str(e2)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check if STT service is ready.
        
        Returns:
            Dict with status, model info, and capabilities
        """
        try:
            # Check if model is loaded
            if self._model_loaded:
                model_status = "loaded"
                model_device = str(self.device)
            else:
                model_status = "not_loaded"
                model_device = "N/A"
            
            # Get CUDA info if available
            cuda_available = torch.cuda.is_available()
            cuda_devices = torch.cuda.device_count() if cuda_available else 0
            
            return {
                "status": "healthy",
                "model": {
                    "name": self.model_name,
                    "status": model_status,
                    "device": model_device,
                    "lazy_load": self.lazy_load,
                },
                "capabilities": {
                    "language_model": True,
                    "supported_languages": ["vi"],
                    "supported_formats": list(self.SUPPORTED_FORMATS),
                    "target_sample_rate": self.TARGET_SAMPLE_RATE,
                },
                "system": {
                    "cuda_available": cuda_available,
                    "cuda_devices": cuda_devices,
                    "torch_version": torch.__version__,
                },
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "model": {"name": self.model_name},
            }
    
    async def warm_up(self):
        """
        Warm up model by loading it and running a test inference.
        Useful for production to avoid cold start latency.
        """
        try:
            logger.info("Warming up STT model...")
            
            # Load model
            if not self._model_loaded:
                await self._load_model()
            
            # Create dummy audio (1 second of silence)
            dummy_audio = np.zeros(self.TARGET_SAMPLE_RATE, dtype=np.float32)
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                import soundfile as sf
                sf.write(tmp_file.name, dummy_audio, self.TARGET_SAMPLE_RATE)
                tmp_path = tmp_file.name
            
            try:
                # Run test transcription
                await self.transcribe_file(tmp_path, use_lm=False)
                logger.info("✓ STT model warmed up successfully")
                
            finally:
                Path(tmp_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.warning(f"Warm-up failed (non-critical): {e}")


