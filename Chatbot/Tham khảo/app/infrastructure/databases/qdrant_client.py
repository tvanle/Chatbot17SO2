"""
Qdrant client implementation following Single Responsibility Principle.
Handles connection pooling and basic operations with Qdrant vector database.
"""

import logging
from typing import Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

logger = logging.getLogger(__name__)


class QdrantClient:
    """
    Async Qdrant client wrapper with connection management.
    Follows SRP: Only responsible for Qdrant connection and basic operations.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize Qdrant client.

        Args:
            host: Qdrant server host
            port: Qdrant server port
            api_key: Optional API key for authentication
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.port = port
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[AsyncQdrantClient] = None
        logger.info(f"Initialized QdrantClient config: {host}:{port}")

    async def connect(self) -> None:
        """Establish connection to Qdrant server."""
        try:
            self._client = AsyncQdrantClient(
                host=self.host,
                port=self.port,
                api_key=self.api_key,
                timeout=self.timeout,
                https=False,  # Use HTTP instead of HTTPS for local development
                prefer_grpc=False,  # Use REST API instead of gRPC
            )
            
            # Test connection
            collections = await self._client.get_collections()
            logger.info(
                f"✓ Connected to Qdrant at {self.host}:{self.port} "
                f"(Collections: {len(collections.collections)})"
            )
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise ConnectionError(f"Qdrant connection failed: {str(e)}")

    async def disconnect(self) -> None:
        """Close Qdrant connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("✓ Qdrant connection closed")

    @property
    def client(self) -> AsyncQdrantClient:
        """
        Get the underlying Qdrant client.

        Returns:
            AsyncQdrantClient instance

        Raises:
            RuntimeError: If client is not connected
        """
        if not self._client:
            raise RuntimeError(
                "Qdrant client not connected. Call connect() first."
            )
        return self._client

    async def health_check(self) -> bool:
        """
        Check if Qdrant server is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            await self._client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

    async def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE,
        on_disk_payload: bool = True,
    ) -> None:
        """
        Create a new collection if it doesn't exist.

        Args:
            collection_name: Name of the collection
            vector_size: Dimension of vectors
            distance: Distance metric (COSINE, EUCLID, DOT)
            on_disk_payload: Whether to store payload on disk
        """
        try:
            # Check if collection exists
            collections = await self.client.get_collections()
            existing = [c.name for c in collections.collections]

            if collection_name in existing:
                logger.debug(f"Collection '{collection_name}' already exists")
                return

            # Create collection
            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance,
                    on_disk=on_disk_payload,
                ),
            )
            logger.info(
                f"✓ Created Qdrant collection '{collection_name}' "
                f"(size={vector_size}, distance={distance.value})"
            )

        except Exception as e:
            logger.error(f"Failed to create collection '{collection_name}': {e}")
            raise RuntimeError(
                f"Collection creation failed: {str(e)}"
            )

    async def delete_collection(self, collection_name: str) -> None:
        """
        Delete a collection.

        Args:
            collection_name: Name of the collection to delete
        """
        try:
            await self.client.delete_collection(collection_name=collection_name)
            logger.info(f"✓ Deleted collection '{collection_name}'")
        except Exception as e:
            logger.error(f"Failed to delete collection '{collection_name}': {e}")
            raise RuntimeError(f"Collection deletion failed: {str(e)}")

    async def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists.

        Args:
            collection_name: Name of the collection

        Returns:
            True if collection exists, False otherwise
        """
        try:
            collections = await self.client.get_collections()
            return collection_name in [c.name for c in collections.collections]
        except Exception as e:
            logger.error(f"Failed to check collection existence: {e}")
            return False

    async def get_collection_info(self, collection_name: str) -> dict:
        """
        Get information about a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Dictionary with collection info
        """
        try:
            info = await self.client.get_collection(collection_name=collection_name)
            
            # Safely get optimizer status
            optimizer_status = "unknown"
            try:
                if hasattr(info.optimizer_status, 'status'):
                    optimizer_status = info.optimizer_status.status.value
                elif hasattr(info.optimizer_status, 'value'):
                    optimizer_status = info.optimizer_status.value
            except AttributeError:
                pass
            
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "status": info.status.value,
                "optimizer_status": optimizer_status,
            }
        except Exception as e:
            logger.error(
                f"Failed to get collection info for '{collection_name}': {e}"
            )
            raise RuntimeError(f"Failed to get collection info: {str(e)}")

