"""
Redis cache client with connection pooling.
Uses redis-py async for high-performance caching operations.
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Async Redis client with connection pooling for caching.
    Optimized for embedding and query result caching.
    """

    def __init__(
        self,
        host: str,
        port: int,
        password: Optional[str] = None,
        db: int = 0,
        max_connections: int = 50,
        decode_responses: bool = True,
    ):
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self.max_connections = max_connections
        self.decode_responses = decode_responses
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None

    async def connect(self) -> None:
        """Initialize connection pool and client."""
        try:
            self._pool = ConnectionPool(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                max_connections=self.max_connections,
                decode_responses=self.decode_responses,
            )
            self._client = Redis(connection_pool=self._pool)

            # Test connection
            await self._client.ping()
            logger.info(f"Redis connected: {self.host}:{self.port} (db={self.db})")

        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self) -> None:
        """Close Redis connection and pool."""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()
        logger.info("Redis disconnected")

    async def ping(self) -> bool:
        """Check if Redis is responsive."""
        try:
            return await self._client.ping()
        except RedisError as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    # Basic operations

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value by key, automatically deserializing JSON.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        try:
            value = await self._client.get(key)
            if value:
                return json.loads(value) if isinstance(value, str) else value
            return None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error getting key '{key}': {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set key-value pair with optional TTL.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        try:
            serialized = json.dumps(value) if not isinstance(value, str) else value
            if ttl:
                return await self._client.setex(key, ttl, serialized)
            else:
                return await self._client.set(key, serialized)
        except (RedisError, json.JSONEncodeError) as e:
            logger.error(f"Error setting key '{key}': {e}")
            return False

    async def delete(self, key: str) -> int:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            Number of keys deleted
        """
        try:
            return await self._client.delete(key)
        except RedisError as e:
            logger.error(f"Error deleting key '{key}': {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return await self._client.exists(key) > 0
        except RedisError as e:
            logger.error(f"Error checking key '{key}': {e}")
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        """Set TTL for existing key."""
        try:
            return await self._client.expire(key, seconds)
        except RedisError as e:
            logger.error(f"Error setting expire for '{key}': {e}")
            return False

    async def ttl(self, key: str) -> int:
        """
        Get remaining TTL for key.

        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist
        """
        try:
            return await self._client.ttl(key)
        except RedisError as e:
            logger.error(f"Error getting TTL for '{key}': {e}")
            return -2

    # Batch operations

    async def mget(self, keys: List[str]) -> List[Optional[Any]]:
        """Get multiple values by keys."""
        try:
            values = await self._client.mget(keys)
            return [json.loads(v) if v and isinstance(v, str) else v for v in values]
        except RedisError as e:
            logger.error(f"Error in mget: {e}")
            return [None] * len(keys)

    async def mset(self, mapping: Dict[str, Any]) -> bool:
        """Set multiple key-value pairs."""
        try:
            serialized = {
                k: json.dumps(v) if not isinstance(v, str) else v
                for k, v in mapping.items()
            }
            return await self._client.mset(serialized)
        except RedisError as e:
            logger.error(f"Error in mset: {e}")
            return False

    # Specialized methods for RAG caching

    def _hash_text(self, text: str) -> str:
        """Create hash for text to use as cache key."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    async def cache_embedding(
        self,
        text: str,
        embedding: List[float],
        provider: str,
        model: str,
        ttl: int = 3600,
    ) -> bool:
        """
        Cache embedding for text.

        Args:
            text: Source text
            embedding: Embedding vector
            provider: Provider name (openai, huggingface)
            model: Model name
            ttl: Cache TTL in seconds

        Returns:
            True if cached successfully
        """
        text_hash = self._hash_text(text)
        key = f"emb:{provider}:{model}:{text_hash}"
        return await self.set(key, embedding, ttl)

    async def get_cached_embedding(
        self, text: str, provider: str, model: str
    ) -> Optional[List[float]]:
        """
        Get cached embedding for text.

        Args:
            text: Source text
            provider: Provider name
            model: Model name

        Returns:
            Cached embedding or None
        """
        text_hash = self._hash_text(text)
        key = f"emb:{provider}:{model}:{text_hash}"
        return await self.get(key)

    async def cache_query_result(
        self, query: str, result: Any, ttl: int = 3600
    ) -> bool:
        """
        Cache query result.

        Args:
            query: Search query
            result: Query result
            ttl: Cache TTL in seconds

        Returns:
            True if cached successfully
        """
        query_hash = self._hash_text(query)
        key = f"query:{query_hash}"
        return await self.set(key, result, ttl)

    async def get_cached_query_result(self, query: str) -> Optional[Any]:
        """Get cached query result."""
        query_hash = self._hash_text(query)
        key = f"query:{query_hash}"
        return await self.get(key)

    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "emb:*")

        Returns:
            Number of keys deleted
        """
        try:
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = await self._client.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted += await self._client.delete(*keys)
                if cursor == 0:
                    break
            return deleted
        except RedisError as e:
            logger.error(f"Error clearing pattern '{pattern}': {e}")
            return 0

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
