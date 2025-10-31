"""
Ingestion service for processing and storing documents in the RAG system.
Handles document processing, chunking, embedding generation, and storage.
"""

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.interfaces import IEmbeddingProvider, IVectorStore
from app.infrastructure.databases.redis_client import RedisClient

logger = logging.getLogger(__name__)


class IngestionService:
    """Service for ingesting documents into the RAG system with caching."""

    def __init__(
        self,
        embedding_provider: IEmbeddingProvider,
        vector_store: IVectorStore,
        redis_client: Optional[RedisClient] = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ):
        """
        Initialize ingestion service.

        Args:
            embedding_provider: Provider for generating embeddings
            vector_store: Vector store for storing embeddings
            redis_client: Redis client for caching
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.redis = redis_client
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        logger.info(
            f"IngestionService initialized (chunk_size={chunk_size}, overlap={chunk_overlap})"
        )

    async def ingest_document(
        self, file_path: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ingest a single document.

        Args:
            file_path: Path to markdown file
            metadata: Document metadata (title, source, collection, etc.)

        Returns:
            Dictionary with ingestion results
        """
        try:
            # Read file content
            content = await self._read_markdown(file_path)

            if not content or not content.strip():
                logger.warning(f"Empty content for {file_path}")
                return {
                    "success": False,
                    "doc_id": None,
                    "chunk_count": 0,
                    "error": "Empty content",
                }

            # Chunk text
            chunks = self._chunk_text(content)
            logger.debug(f"Created {len(chunks)} chunks from {file_path}")

            # Generate embeddings (with cache)
            embeddings = await self._get_embeddings_cached(chunks)

            # Create document objects
            documents = [
                {
                    "content": chunk,
                    "metadata": {
                        **metadata,
                        "chunk_index": i,
                        "source_file": str(Path(file_path).name),
                    },
                }
                for i, chunk in enumerate(chunks)
            ]

            # Store in vector store
            collection = metadata.get("collection", "default")
            chunk_ids = await self.vector_store.add_documents(
                documents=documents,
                embeddings=embeddings,
                collection=collection,
                doc_metadata=metadata,
            )

            logger.info(f"✓ Ingested {len(chunks)} chunks from {Path(file_path).name}")

            return {
                "success": True,
                "doc_id": metadata.get("doc_id"),
                "chunk_count": len(chunks),
                "chunk_ids": chunk_ids,
                "collection": collection,
            }

        except Exception as e:
            logger.error(f"Failed to ingest {file_path}: {e}")
            return {
                "success": False,
                "doc_id": metadata.get("doc_id"),
                "chunk_count": 0,
                "error": str(e),
            }

    async def _read_markdown(self, file_path: str) -> str:
        """Read markdown file content."""
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            return content.strip()

        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise

    def _chunk_text(self, text: str) -> List[str]:
        """
        Chunk text into fixed-size chunks with overlap.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + self.chunk_size
            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            # Move forward by chunk_size minus overlap
            start += self.chunk_size - self.chunk_overlap

            # Prevent infinite loop
            if self.chunk_overlap >= self.chunk_size:
                break

        return chunks

    async def _get_embeddings_cached(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for texts with Redis caching.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not self.redis:
            # No caching, generate all
            return await self.embedding_provider.embed_batch(texts)

        embeddings = []
        uncached_indices = []
        uncached_texts = []

        # Check cache for each text
        for i, text in enumerate(texts):
            cached = await self.redis.get_cached_embedding(text, "huggingface", "vietnamese-document-embedding")

            if cached:
                embeddings.append(cached)
            else:
                embeddings.append(None)
                uncached_indices.append(i)
                uncached_texts.append(text)

        # Generate uncached embeddings
        if uncached_texts:
            logger.debug(
                f"Generating {len(uncached_texts)}/{len(texts)} uncached embeddings"
            )
            new_embeddings = await self.embedding_provider.embed_batch(uncached_texts)

            # Insert into result and cache
            for idx, embedding in zip(uncached_indices, new_embeddings):
                embeddings[idx] = embedding
                # Cache for 7 days
                await self.redis.cache_embedding(texts[idx], embedding, "huggingface", "vietnamese-document-embedding", ttl=7 * 24 * 3600)
        else:
            logger.debug(f"All {len(texts)} embeddings found in cache")

        return embeddings

    def _hash_text(self, text: str) -> str:
        """Generate hash key for text."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]
