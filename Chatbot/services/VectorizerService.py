"""
VectorizerService - Handles text-to-vector embedding
"""
from typing import List, Optional
import numpy as np
from Chatbot.config.rag_config import get_rag_config


class VectorizerService:
    """
    Service for generating embeddings from text
    Uses sentence-transformers for creating dense vector representations
    """

    def __init__(self, embed_model: Optional[str] = None):
        """
        Initialize vectorizer with embedding model

        Args:
            embed_model: Model name for sentence-transformers (optional, uses config if None)
        """
        config = get_rag_config()
        self.embed_model = embed_model or config.embedding_model
        self.embedding_dimension = config.embedding_dimension
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load the embedding model (lazy loading)"""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.embed_model)
            print(f"Loaded embedding model: {self.embed_model}")
        except ImportError:
            print("WARNING: sentence-transformers not installed. Install with: pip install sentence-transformers")
            self.model = None
        except Exception as e:
            print(f"Error loading embedding model: {e}")
            self.model = None

    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text

        Args:
            text: Input text string

        Returns:
            Embedding vector as numpy array
        """
        if self.model is None:
            # Fallback: return random vector if model not loaded
            return np.random.rand(self.embedding_dimension).astype('float32')

        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.astype('float32')
        except Exception as e:
            print(f"Error generating embedding: {e}")
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
