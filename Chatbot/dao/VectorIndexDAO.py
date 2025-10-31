"""
VectorIndexDAO - Data Access Object for Vector Index operations
Powered by Qdrant Vector Database for fast similarity search

Replaced old database-backed storage with Qdrant for better performance
"""
from typing import List, Tuple, Optional, Dict
import numpy as np
import uuid
import logging

logger = logging.getLogger(__name__)


class VectorIndexDAO:
    """
    DAO for vector index operations using Qdrant
    Replaces old database-backed vector storage with dedicated vector DB

    Provides same interface as before, but with Qdrant backend for better performance
    """

    def __init__(self, db=None, host: str = None, port: int = None, collection_name: str = None):
        """
        Initialize VectorIndexDAO with Qdrant backend

        Args:
            db: SQLAlchemy session (ignored, kept for backward compatibility)
            host: Qdrant server host (default: from config)
            port: Qdrant server port (default: from config)
            collection_name: Collection name (default: from config)
        """
        # Load from config if not provided
        from Chatbot.config.rag_config import get_rag_config
        config = get_rag_config()

        self.host = host or config.qdrant_host
        self.port = port or config.qdrant_port
        self.collection_name = collection_name or config.qdrant_collection_name
        self._client = None
        self._connect()

    def _connect(self):
        """Connect to Qdrant server"""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams

            self._client = QdrantClient(
                host=self.host,
                port=self.port,
                timeout=30
            )

            # Create collection if not exists
            collections = self._client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=384,  # Default dimension for all-MiniLM-L6-v2
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Using existing Qdrant collection: {self.collection_name}")

        except ImportError:
            logger.error("qdrant-client not installed. Install with: pip install qdrant-client")
            self._client = None
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant at {self.host}:{self.port} - {e}")
            self._client = None

    def query(
        self,
        namespace: str,
        query_vector: np.ndarray,
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Tuple[str, float]]:
        """
        Query vector index for similar chunks

        Args:
            namespace: Namespace/collection identifier
            query_vector: Query embedding vector
            top_k: Number of results to return
            filters: Optional filters (not implemented yet)

        Returns:
            List of (chunk_id, similarity_score) tuples, sorted by score descending
        """
        if self._client is None:
            logger.warning("Qdrant client not available, returning empty results")
            return []

        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # Build filter for namespace
            query_filter = None
            if namespace:
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="namespace",
                            match=MatchValue(value=namespace)
                        )
                    ]
                )

            # Search in Qdrant
            search_results = self._client.search(
                collection_name=self.collection_name,
                query_vector=query_vector.tolist() if isinstance(query_vector, np.ndarray) else query_vector,
                limit=top_k,
                query_filter=query_filter,
                with_payload=True,
                with_vectors=False
            )

            # Format results as (chunk_id, score)
            results = []
            for result in search_results:
                chunk_id = result.payload.get("chunk_id")
                if chunk_id:
                    results.append((chunk_id, float(result.score)))

            return results

        except Exception as e:
            logger.error(f"Qdrant query failed: {e}")
            return []

    def upsert(self, namespace: str, pairs: List[Tuple[str, np.ndarray]]) -> None:
        """
        Insert or update embeddings in Qdrant

        Args:
            namespace: Namespace/collection identifier
            pairs: List of (chunk_id, vector) tuples
        """
        if self._client is None:
            logger.warning("Qdrant client not available, skipping upsert")
            return

        try:
            from qdrant_client.models import PointStruct

            # Prepare points for batch upsert
            points = []
            for chunk_id, vector in pairs:
                point_id = str(uuid.uuid4())  # Generate unique point ID

                # Convert numpy array to list
                if isinstance(vector, np.ndarray):
                    vector = vector.tolist()

                point = PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "chunk_id": chunk_id,
                        "namespace": namespace
                    }
                )
                points.append(point)

            # Batch upsert to Qdrant
            if points:
                self._client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                    wait=True
                )
                logger.info(f"Upserted {len(points)} vectors to Qdrant namespace '{namespace}'")

        except Exception as e:
            logger.error(f"Qdrant upsert failed: {e}")

    def delete_by_chunk_id(self, chunk_id: str) -> bool:
        """
        Delete embedding by chunk ID

        Args:
            chunk_id: Chunk UUID

        Returns:
            True if deleted, False otherwise
        """
        if self._client is None:
            return False

        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # Delete by filtering on chunk_id payload
            self._client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="chunk_id",
                            match=MatchValue(value=chunk_id)
                        )
                    ]
                ),
                wait=True
            )
            logger.info(f"Deleted chunk {chunk_id} from Qdrant")
            return True

        except Exception as e:
            logger.error(f"Qdrant delete failed: {e}")
            return False

    def delete_by_namespace(self, namespace: str):
        """
        Delete all embeddings in a namespace

        Args:
            namespace: Namespace identifier
        """
        if self._client is None:
            return

        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # Delete all points with matching namespace
            self._client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="namespace",
                            match=MatchValue(value=namespace)
                        )
                    ]
                ),
                wait=True
            )
            logger.info(f"Deleted all vectors in namespace '{namespace}'")

        except Exception as e:
            logger.error(f"Qdrant delete by namespace failed: {e}")

    def get_stats(self) -> Dict:
        """
        Get Qdrant collection statistics

        Returns:
            Dictionary with collection stats
        """
        if self._client is None:
            return {"status": "disconnected"}

        try:
            collection_info = self._client.get_collection(self.collection_name)
            return {
                "status": "connected",
                "points_count": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
                "collection": self.collection_name,
                "host": f"{self.host}:{self.port}"
            }
        except Exception as e:
            logger.error(f"Failed to get Qdrant stats: {e}")
            return {"status": "error", "message": str(e)}

    def health_check(self) -> bool:
        """
        Check if Qdrant is healthy

        Returns:
            True if healthy, False otherwise
        """
        if self._client is None:
            return False

        try:
            self._client.get_collections()
            return True
        except:
            return False
