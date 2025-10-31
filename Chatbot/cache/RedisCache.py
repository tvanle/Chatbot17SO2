"""
Redis Cache Client for RAG System
Implements caching for embeddings and query results
Following reference implementation pattern
"""
import json
import hashlib
import logging
from typing import Optional, List, Any
import redis
from Chatbot.config.rag_config import get_rag_config

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis-based caching for RAG system
    Caches embeddings and query results to reduce API costs and latency
    """

    def __init__(self, host: str = None, port: int = None, db: int = 0):
        """
        Initialize Redis cache client

        Args:
            host: Redis server host (default from config)
            port: Redis server port (default from config)
            db: Redis database number
        """
        config = get_rag_config()
        self.host = host or config.redis_host
        self.port = port or config.redis_port
        self.db = db
        self._client = None
        self._connect()

    def _connect(self):
        """Connect to Redis server"""
        try:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=False,  # We'll handle encoding ourselves
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test connection
            self._client.ping()
            logger.info(f"✓ Connected to Redis at {self.host}:{self.port}")
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")
            self._client = None
        except Exception as e:
            logger.warning(f"Redis initialization error: {e}. Caching disabled.")
            self._client = None

    def is_available(self) -> bool:
        """
        Check if Redis is available

        Returns:
            True if connected, False otherwise
        """
        if self._client is None:
            return False
        try:
            self._client.ping()
            return True
        except:
            return False

    def _generate_key(self, prefix: str, data: str) -> str:
        """
        Generate cache key from data

        Args:
            prefix: Key prefix (e.g., "embedding", "query")
            data: Data to hash

        Returns:
            Cache key
        """
        hash_obj = hashlib.sha256(data.encode('utf-8'))
        return f"{prefix}:{hash_obj.hexdigest()[:16]}"

    # ===== Embedding Cache =====

    def get_cached_embedding(
        self,
        text: str,
        provider: str = "huggingface",
        model: str = "all-MiniLM-L6-v2"
    ) -> Optional[List[float]]:
        """
        Get cached embedding for text

        Args:
            text: Input text
            provider: Embedding provider
            model: Model name

        Returns:
            Cached embedding or None
        """
        if not self.is_available():
            return None

        try:
            cache_key = self._generate_key(
                f"emb:{provider}:{model}",
                text
            )
            cached = self._client.get(cache_key)
            if cached:
                embedding = json.loads(cached.decode('utf-8'))
                logger.debug(f"Embedding cache HIT for text: {text[:50]}...")
                return embedding
            return None
        except Exception as e:
            logger.warning(f"Failed to get cached embedding: {e}")
            return None

    def cache_embedding(
        self,
        text: str,
        embedding: List[float],
        provider: str = "huggingface",
        model: str = "all-MiniLM-L6-v2",
        ttl: int = 7 * 24 * 3600  # 7 days default
    ) -> bool:
        """
        Cache embedding for text

        Args:
            text: Input text
            embedding: Embedding vector
            provider: Embedding provider
            model: Model name
            ttl: Time-to-live in seconds

        Returns:
            True if cached successfully
        """
        if not self.is_available():
            return False

        try:
            cache_key = self._generate_key(
                f"emb:{provider}:{model}",
                text
            )
            value = json.dumps(embedding)
            self._client.setex(cache_key, ttl, value)
            logger.debug(f"Cached embedding for text: {text[:50]}...")
            return True
        except Exception as e:
            logger.warning(f"Failed to cache embedding: {e}")
            return False

    # ===== Query Result Cache =====

    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value by key

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self.is_available():
            return None

        try:
            cached = self._client.get(key)
            if cached:
                return json.loads(cached.decode('utf-8'))
            return None
        except Exception as e:
            logger.warning(f"Failed to get cached value: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Set cache value

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds

        Returns:
            True if cached successfully
        """
        if not self.is_available():
            return False

        try:
            serialized = json.dumps(value)
            self._client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Failed to set cache: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete cache entry

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        if not self.is_available():
            return False

        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Failed to delete cache: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern

        Args:
            pattern: Key pattern (e.g., "emb:*")

        Returns:
            Number of keys deleted
        """
        if not self.is_available():
            return 0

        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Failed to clear pattern: {e}")
            return 0

    def flush_all(self) -> bool:
        """
        Clear entire cache database

        Returns:
            True if flushed successfully
        """
        if not self.is_available():
            return False

        try:
            self._client.flushdb()
            logger.info("✓ Flushed entire Redis cache")
            return True
        except Exception as e:
            logger.error(f"Failed to flush cache: {e}")
            return False

    def get_stats(self) -> dict:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        if not self.is_available():
            return {"status": "disconnected"}

        try:
            info = self._client.info()
            return {
                "status": "connected",
                "host": f"{self.host}:{self.port}",
                "db": self.db,
                "keys_count": self._client.dbsize(),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "uptime_days": info.get("uptime_in_days")
            }
        except Exception as e:
            logger.error(f"Failed to get Redis stats: {e}")
            return {"status": "error", "message": str(e)}
