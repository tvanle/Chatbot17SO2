"""
Core abstract interfaces following Interface Segregation Principle.
Each interface defines a single, focused contract.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IEmbeddingProvider(ABC):
    """Interface for text embedding providers."""

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass


class ILLMProvider(ABC):
    """Interface for large language model providers."""

    @abstractmethod
    async def generate(
        self, prompt: str, context: Optional[str] = None, **kwargs
    ) -> str:
        pass

    @abstractmethod
    async def stream_generate(
        self, prompt: str, context: Optional[str] = None, **kwargs
    ):
        pass


class IVectorStore(ABC):
    """Interface for vector storage and retrieval."""

    @abstractmethod
    async def add_documents(
        self, documents: List[Dict[str, Any]], embeddings: List[List[float]]
    ) -> List[str]:
        pass

    @abstractmethod
    async def search(
        self, query_embedding: List[float], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def delete(self, doc_ids: List[str]) -> None:
        pass


class IDocumentProcessor(ABC):
    """Interface for document processing."""

    @abstractmethod
    async def process(self, file_path: str) -> str:
        pass


class ICache(ABC):
    """Interface for caching operations."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        pass


class IDatabase(ABC):
    """Interface for database operations."""

    @abstractmethod
    async def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        pass

    @abstractmethod
    async def fetch_one(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def fetch_all(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        pass


class IStorageProvider(ABC):
    """Interface for file storage providers (S3, MinIO, etc.)."""

    @abstractmethod
    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
        path_prefix: Optional[str] = None,
    ) -> str:
        """Upload file and return URL."""
        pass

    @abstractmethod
    async def get_presigned_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        """Get temporary signed URL for private file access."""
        pass

    @abstractmethod
    async def delete_file(self, object_name: str) -> bool:
        """Delete file from storage."""
        pass

    @abstractmethod
    async def file_exists(self, object_name: str) -> bool:
        """Check if file exists."""
        pass


class IImageProvider(ABC):
    """Interface for AI image generation and vision providers."""

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        style: str = "natural",
    ) -> bytes:
        """Generate image from text prompt."""
        pass

    @abstractmethod
    async def analyze_image(
        self,
        image_url: str,
        question: str = "What's in this image?",
        detail: str = "auto",
    ) -> Dict[str, Any]:
        """Analyze image and return description, labels, etc."""
        pass

    @abstractmethod
    async def extract_text_ocr(self, image_url: str) -> Optional[str]:
        """Extract text from image using OCR."""
        pass


class ISTTProvider(ABC):
    """Interface for Speech-to-Text (STT) providers."""

    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "vi",
        use_lm: bool = True,
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text.
        
        Args:
            audio_data: Audio file bytes
            language: Language code (default: "vi" for Vietnamese)
            use_lm: Use language model for better accuracy
            
        Returns:
            Dict with:
                - text: Transcribed text
                - confidence: Confidence score (if available)
                - language: Detected/specified language
                - duration: Audio duration in seconds
                - model: Model name used
        """
        pass

    @abstractmethod
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
            Same as transcribe()
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check if STT service is ready.
        
        Returns:
            Dict with status and model info
        """
        pass
