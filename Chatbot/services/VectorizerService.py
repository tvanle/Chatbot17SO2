"""
VectorizerService - Handles text-to-vector embedding
Enhanced with Redis caching support
"""
from typing import List, Optional
import numpy as np
import logging
from Chatbot.config.rag_config import get_rag_config

logger = logging.getLogger(__name__)


class VectorizerService:
    """
    Service for generating embeddings from text
    Uses sentence-transformers for creating dense vector representations
    With optional Redis caching to reduce API calls and improve performance
    """

    def __init__(self, embed_model: Optional[str] = None, enable_cache: bool = None):
        """
        Initialize vectorizer with embedding model

        Args:
            embed_model: Model name for sentence-transformers (optional, uses config if None)
            enable_cache: Enable Redis caching (optional, uses config if None)
        """
        config = get_rag_config()
        self.embed_model = embed_model or config.embedding_model
        self.embedding_dimension = config.embedding_dimension
        self.model = None
        self._cache = None

        logger.info(f"   Model: {self.embed_model}")
        logger.info(f"   Dimension: {self.embedding_dimension}")

        # DISABLE CACHE FOR NOW - causing issues
        self.enable_cache = False
        logger.info("   Cache DISABLED (hardcoded for debugging)")

        logger.info("   Calling _load_model()...")
        print("   Calling _load_model()...")
        self._load_model()
        logger.info("✓ VectorizerService.__init__() completed")
        print("✓ VectorizerService.__init__() completed")

    def _init_cache(self):
        """Initialize Redis cache"""
        try:
            from Chatbot.infrastructure.cache import RedisCache
            self._cache = RedisCache()
            if self._cache.is_available():
                logger.info("✓ Redis cache enabled for embeddings")
            else:
                logger.warning("Redis cache initialization failed, proceeding without cache")
                self._cache = None
        except ImportError:
            logger.warning("redis package not installed, caching disabled")
            self._cache = None
        except Exception as e:
            logger.warning(f"Failed to initialize cache: {e}")
            self._cache = None

    def _load_model(self):
        """Load the embedding model (lazy loading)"""
        try:
            import sys
            logger.info(f"🔄 Attempting to load embedding model: {self.embed_model}")
            logger.info(f"   Python: {sys.executable}")
            logger.info(f"   sys.path[0]: {sys.path[0]}")

            from sentence_transformers import SentenceTransformer
            logger.info("✓ sentence_transformers imported successfully")

            self.model = SentenceTransformer(self.embed_model)
            logger.info(f"✅ Loaded embedding model: {self.embed_model}")
            logger.info(f"   Dimension: {self.model.get_sentence_embedding_dimension()}")
            print(f"✅ Loaded embedding model: {self.embed_model}")
        except ImportError as e:
            logger.error(f"❌ ImportError: sentence-transformers not installed - {e}")
            print(f"WARNING: sentence-transformers not installed. Install with: pip install sentence-transformers")
            self.model = None
        except Exception as e:
            logger.error(f"❌ Exception loading embedding model: {e}", exc_info=True)
            print(f"Error loading embedding model: {e}")
            import traceback
            traceback.print_exc()
            self.model = None

    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text with optional caching

        Args:
            text: Input text string

        Returns:
            Embedding vector as numpy array
        """
        # Try cache first
        if self._cache and self._cache.is_available():
            cached_embedding = self._cache.get_cached_embedding(
                text=text,
                provider="huggingface",
                model=self.embed_model
            )
            if cached_embedding is not None:
                return np.array(cached_embedding, dtype='float32')

        # Model not loaded fallback
        if self.model is None:
            logger.warning("Embedding model not loaded, returning random vector")
            return np.random.rand(self.embedding_dimension).astype('float32')

        try:
            # Generate embedding
            embedding = self.model.encode(text, convert_to_numpy=True)
            embedding = embedding.astype('float32')

            # Cache the result
            if self._cache and self._cache.is_available():
                self._cache.cache_embedding(
                    text=text,
                    embedding=embedding.tolist(),
                    provider="huggingface",
                    model=self.embed_model
                )

            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return np.random.rand(self.embedding_dimension).astype('float32')

    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts (more efficient)

        Args:
            texts: List of input text strings

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        if self.model is None:
            # Fallback: return random vectors
            return [np.random.rand(self.embedding_dimension).astype('float32') for _ in texts]

        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return [emb.astype('float32') for emb in embeddings]
        except Exception as e:
            print(f"Error generating batch embeddings: {e}")
            return [np.random.rand(self.embedding_dimension).astype('float32') for _ in texts]

    def get_dimension(self) -> int:
        """
        Get embedding dimension

        Returns:
            Dimension of embedding vectors
        """
        if self.model is None:
            return self.embedding_dimension

        try:
            return self.model.get_sentence_embedding_dimension()
        except:
            return self.embedding_dimension
